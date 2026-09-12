"""The thin-client half: ask a registry what it can do, and have it derive what we cannot.

Two tools, and they answer different questions. `registry_caches` compares this machine's
snapshot lanes against an instance's, so an author can find out *which of these tools will
work here* before anything else. `remote_derive` has the instance build the `derived/`
tree — `resolution.csv` above all, which is what places rsID-authored rows onto coordinates
and which the compiler will never fetch for itself.

**Why `remote_derive` is its own tool rather than a flag on `enrich_module`.** It sends the
module: every authored CSV, `module_spec.yaml` and the `logs/` subtree go up as multipart.
That is outward-facing, and a tool may not decide to do it on the author's behalf to be
helpful — so routing is automatic for reads (see `routing.py`) and explicit here. It also
needs an argument the local form does not, since the archive is addressed
`POST /modules/{ns}/{name}/derived`.

**The capture rule is the hard part and it generalises `refresh_sidecar`'s.** The uploaded
spec carries the existing sidecars, and the server runs the enricher's own `enrich_spec`,
which gap-fills rather than clobbers — so a hand-curated `source="manual"` row normally
travels up and comes back. Normally is not always: a pass that could not reach its source,
and the concordance pair, which is rewritten whole by design. (The third case used to be the
`licensing.csv`/`sources.csv` two spellings, and that one is closed rather than surfaced —
`_dest_for` writes to the file the author already has.) So the local bytes are
captured and **the capture is read back and hashed** before a single file is replaced, and
any row the incoming tree does not carry is a decision line rather than an applied edit.
"""

from __future__ import annotations

import csv
import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import hints
from just_dna_format.layout import (
    SIDECAR_SPELLINGS,
    SidecarCollision,
    sidecar_write_path,
)
from just_dna_registry.specfiles import (
    DERIVED_FILES,
    DERIVED_REPORT_FILE,
    RECOGNIZED_SPEC_FILES,
)
from mcp.types import ToolAnnotations

from just_module_creator import routing
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CacheReport,
    DerivedTreeReport,
    DraftArchiveReport,
    LaneStatus,
)
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import client_for, describe
from just_module_creator.tools._shared import offline_for, resolve_dir
from just_module_creator.tools.refresh import capture_dir, capture_now, finalize_capture

log = get_logger()

#: The two tables the diff skips, and the reason is not "they are noisy". Their producer
#: replaces both whole on every run by design — a subject the authorities stopped
#: contesting has to LEAVE the record — so every row would read as withdrawn on every
#: run and the decision list would be noise that hides the real lines.
_WHOLE_REWRITE = frozenset({"clin_sig_concordance.csv", "clin_sig_authority_calls.csv"})

#: Where the archive puts the tables. The folder is a layout for readers: on disk after
#: enrichment they are at the spec root, and the split is constructed on the way out.
_ARCHIVE_PREFIX = "derived/"


def _lane_rows(target: RegistryTarget, remote: Any | None) -> list[LaneStatus]:
    """One row per lane, local presence beside whatever the instance said.

    Walks `CACHE_LANES` rather than the instance's list, so a lane the deployment has
    never heard of still appears with `remote=None` — *not asked* rather than *absent*.
    """
    remote_by_name: dict[str, Any] = {}
    for lane in getattr(remote, "lanes", []) or []:
        remote_by_name[getattr(lane, "name", "")] = lane

    def _reason(far: Any | None) -> str | None:
        if far is None:
            return None
        return getattr(far, "licence_skip", None) or getattr(far, "route_reason", None)

    rows: list[LaneStatus] = []
    for lane in routing.CACHE_LANES:
        far = remote_by_name.get(lane.name)
        rows.append(
            LaneStatus(
                lane=lane.name,
                serves=lane.serves,
                local=lane.resolve() is not None,
                remote=getattr(far, "state", None) if far is not None else None,
                remote_reason=_reason(far),
                env_var=lane.env_var,
                build_command=lane.build_command,
            )
        )

    # **An enricher predating the lane registry still gets a useful report**, and that is
    # exactly the install the proxy exists for: it has no lanes to enumerate, so the rows
    # come from what the instance said instead, with `local=None` — cannot ask, never
    # "holds none". Falling back to an empty list here would hide the remote half from
    # the only caller who has nothing else.
    if not routing.LANES_KNOWN:
        rows = [
            LaneStatus(
                lane=getattr(far, "name", ""),
                serves=getattr(far, "serves", None),
                local=None,
                remote=getattr(far, "state", None),
                remote_reason=_reason(far),
                # Null rather than reconstructed: the variable is the lane's own
                # attribute upstream precisely so it cannot name one the resolver
                # ignores, and `JUST_DNA_<NAME>_CACHE` is a guess that is already wrong
                # for `constraint` (`JUST_DNA_GNOMAD_CONSTRAINT_CACHE`).
                env_var=None,
                build_command=getattr(far, "build_command", None),
            )
            for far in (getattr(remote, "lanes", []) or [])
        ]
    return rows


def _key_columns(csv_name: str) -> tuple[str, ...]:
    """The columns the writing pass itself keys on, or empty when the kind declares none.

    `hints.key_fields` reads the row model's own `_KEY_FIELDS`, generated since format
    0.6.5 (our `S48`) precisely so a hand-kept map cannot name a column upstream has
    deprecated — which is what `modifier_cn` cost for a whole minor. Empty means the
    kind declares no key, and then the diff below withholds rather than guessing at a
    row identity: a wrong key would report every row as displaced.
    """
    key: hints.TableKey | None = hints.key_fields(csv_name)
    return tuple(key.columns) if key is not None else ()


def _read_local_keys(
    path: Path, csv_name: str
) -> tuple[set[tuple[str, ...]], list[dict[str, str]]]:
    """The key tuples in a local sidecar, plus its rows, for the displacement diff.

    The key comes from `hints.key_fields`, which reads each model's own `_KEY_FIELDS` —
    generated since format 0.6.5 (our `S48`) exactly so that a hand-kept map cannot name
    a column upstream has deprecated, which is what `modifier_cn` cost for a whole minor.
    """
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return set(), []
    rows = list(csv.DictReader(io.StringIO(text)))
    columns = _key_columns(csv_name)
    if not columns:
        return set(), rows
    keys = {tuple((row.get(c) or "").strip() for c in columns) for row in rows}
    return keys, rows


#: Filename back to the key `sidecar_write_path` answers about. **Asking it with the
#: filename the archive uses does NOT follow the file you read**, which is the opposite of
#: what its docstring promises a careless reader: `SIDECAR_SPELLINGS` is keyed on the table
#: key `sources.csv` — the name `sources.parquet` and `manifest.sources` keep — so
#: `sidecar_spellings("licensing.csv")` is a one-tuple with no alias in it, and a write over
#: a spec carrying `sources.csv` creates the *second* spelling instead of following the
#: first. Measured 2026-09-11 on format 0.7.0. Derived from their map rather than written
#: out, so a second aliased table needs nothing here.
_TABLE_KEY_FOR: dict[str, str] = {
    spelling: key
    for key, spellings in SIDECAR_SPELLINGS.items()
    for spelling in spellings
}


def _dest_for(directory: Path, csv_name: str) -> Path:
    """Where an incoming derived table goes — the spelling already on disk, else upstream's.

    One line of translation, and it is the difference between installing over the author's
    `sources.csv` and leaving them two copies of one table, which the next upload refuses
    rather than merges. `SidecarCollision` propagates: a spec already carrying both is a
    refusal, not something to pick a side in.
    """
    return sidecar_write_path(directory, _TABLE_KEY_FOR.get(csv_name, csv_name))


def _displacement_lines(
    spec_dir: Path, incoming: dict[str, bytes]
) -> tuple[list[str], list[Path]]:
    """Rows a local sidecar has and the incoming tree does not, as decision lines.

    **Not a defect report, and the wording has to keep that.** A row missing from the
    incoming tree has two readings and only the author can tell them apart: the source
    withdrew the answer, or the remote run could not ask. §2's discriminator, at file
    grain — and `source="manual"` is called out because a row nobody fetched is one
    nothing will reproduce.
    """
    lines: list[str] = []
    displaced: list[Path] = []
    for csv_name, data in sorted(incoming.items()):
        local_path = _dest_for(spec_dir, csv_name)
        if not local_path.is_file():
            continue
        displaced.append(local_path)
        if csv_name in _WHOLE_REWRITE:
            lines.append(
                f"{local_path.name}: replaced whole rather than diffed — its producer "
                "rewrites both concordance tables on every run by design, so a row "
                "leaving the record means the authorities stopped contesting that "
                "subject. Nothing to decide here."
            )
            continue
        before, rows = _read_local_keys(local_path, csv_name)
        after, _ = _read_local_keys_from_bytes(data, csv_name)
        gone = sorted(before - after)
        if not gone:
            continue
        columns = _key_columns(csv_name)
        manual = {
            tuple((row.get(c) or "").strip() for c in columns)
            for row in rows
            if (row.get("source") or "").strip() == "manual"
        }
        for key in gone[:40]:
            hand = " — source=\"manual\", so nothing will re-derive it" if key in manual else ""
            lines.append(f"{local_path.name}: {' / '.join(key)} is not in the new tree{hand}")
        if len(gone) > 40:
            lines.append(f"{local_path.name}: and {len(gone) - 40} more rows not listed")
    return lines, displaced


def _read_local_keys_from_bytes(
    data: bytes, csv_name: str
) -> tuple[set[tuple[str, ...]], list[dict[str, str]]]:
    """`_read_local_keys` over bytes, so the incoming archive is read the same way."""
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    columns = _key_columns(csv_name)
    if not columns:
        return set(), rows
    return {tuple((row.get(c) or "").strip() for c in columns) for row in rows}, rows


def _unpack(archive: bytes) -> tuple[dict[str, bytes], list[str], list[str] | None]:
    """The sidecars out of the tar, the extra members by name, and what was NOT produced.

    Members are taken by their basename under `derived/` and nothing else is written, so
    a path traversal in a member name cannot reach outside the spec directory — the
    archive is a third party's bytes and is treated as such.

    **The third answer is three-valued and that is the point.** `None` means the archive
    carried no report, so the question could not be put; `[]` means it was put and nothing
    was missing. Collapsing the two would report an old deployment's silence as a clean
    run — and the whole reason the field exists is that a gated pass writes nothing and
    says nothing, so silence is exactly the state that must stay distinguishable.
    """
    tables: dict[str, bytes] = {}
    extras: list[str] = []
    absent: list[str] | None = None
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            data = handle.read()
            name = member.name
            if name.startswith(_ARCHIVE_PREFIX):
                base = Path(name).name
                if base in DERIVED_FILES:
                    tables[base] = data
                continue
            base = Path(name).name
            extras.append(base)
            if base == DERIVED_REPORT_FILE:
                absent = _absent_from(data)
    return tables, extras, absent


def _absent_from(report: bytes) -> list[str] | None:
    """`files_absent` out of the run's own report, or `None` when it does not say.

    A third party's bytes, so a report that is not JSON, is not an object, or carries the
    key as something other than a list of strings answers `None` — *it did not say* —
    rather than raising or being read as an empty list. Same reason as `_unpack`'s: the
    two silences are different facts.
    """
    try:
        parsed = json.loads(report.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    listed = parsed.get("files_absent")
    if not isinstance(listed, list):
        return None
    return sorted({str(item) for item in listed})


#: Every spec file name a draft archive may legitimately carry, so a member outside the
#: set contributes nothing rather than being written. Derived from the registry's own
#: roster: a drafter that starts writing a new table appears here with no edit, and a
#: traversing member name has nowhere to land.
_DRAFTABLE_NAMES = frozenset(RECOGNIZED_SPEC_FILES)


def _unpack_draft(archive: bytes) -> tuple[dict[str, bytes], list[tuple[str, bytes]]]:
    """Spec files out of a draft archive, plus the extras, keyed by relative name.

    Same containment rule as `_unpack`: a member is taken only where its **basename** is
    a recognised spec file, so `../../etc/passwd` is dropped rather than resolved. The
    archive is a third party's bytes.
    """
    rows: dict[str, bytes] = {}
    extras: list[tuple[str, bytes]] = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            data = handle.read()
            base = Path(member.name).name
            if base in _DRAFTABLE_NAMES:
                rows[base] = data
            else:
                extras.append((base, data))
    return rows, extras


def _draft_report(extras: list[tuple[str, bytes]]) -> dict[str, Any]:
    """`draft-report.json`'s contents, or an empty mapping when the archive carried none.

    **Empty is not zero.** Every count read off it defaults to 0 downstream, and that is
    only honest because an absent report means the archive did not describe itself —
    which `notes` then says. Nothing here invents a count from the rows, because the
    server's `already_present` and `differs` are about the merge it performed and cannot
    be recovered from the merged result.
    """
    for name, data in extras:
        if name != "draft-report.json":
            continue
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}


def register_proxy(mcp: FastMCP, settings: Settings) -> None:
    """Register the two thin-client tools.

    Both are registered unconditionally and refuse with a named reason when the
    installed client cannot proxy. **A hidden tool answers a call by name with "Unknown
    tool" instead of the sentence that says what would make it work**, which is the dead
    end the tier axis cost us four times over.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Which snapshot caches exist, here and there",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def registry_caches(target: RegistryTarget) -> CacheReport:
        """Which snapshot lanes this machine holds, and which the registry holds for you.

        **Ask this first if a lookup or an enrichment behaved unexpectedly.** The
        enricher's answers come from snapshot caches — fifteen lanes, the Ensembl one
        about 14 GB — and a machine holding none of them cannot place an rsID at all. A
        registry that holds them can answer instead, which is what makes a laptop a
        usable authoring seat; `JMC_SNAPSHOT_ROUTE` decides whether that happens, and it
        decides **per lane**, so holding three of fifteen is a normal state rather than a
        broken one.

        `target` is required, like every other catalog read: this reports on one
        deployment and a rehearsal read back against the other tells you about the wrong
        box. Read `unreachable` first — those are lanes **neither** side holds, so no
        route can produce them from a snapshot and a tool needing one either fetches live
        or reports that the question was not put. `remote` is three-valued, and `partial`
        is the state provisioning refuses to act on rather than overwrite. A null
        `remote_count` means the instance was not asked, which is not zero.

        Costs one anonymous request and no credential.
        """
        gap = routing.proxy_gap()
        offline = offline_for(settings, False)
        remote: Any | None = None
        reach_note = ""
        if gap is None and not offline:
            client = client_for(target, settings)
            try:
                remote = await run_sync(client.cache_status)
            except Exception as exc:  # noqa: BLE001 — any transport failure is "not asked"
                reach_note = (
                    f" The instance could not be asked ({type(exc).__name__}: {exc}), so "
                    "every `remote` reads null — not asked, which is not absent."
                )
                log.warning("cache_status against %s failed: %s", target, exc)

        rows = _lane_rows(target, remote)
        local_count = sum(1 for r in rows if r.local) if routing.LANES_KNOWN else None
        remote_count = (
            sum(1 for r in rows if r.remote == "present") if remote is not None else None
        )
        unreachable = [
            r.lane for r in rows if not r.local and (r.remote not in ("present", None))
        ]

        here = (
            f"This machine holds {local_count} of {len(rows)} lanes"
            if local_count is not None
            else (
                "The installed just-dna-enricher predates the cache registry (0.7), so "
                "what this machine holds cannot be asked — `local` is null throughout, "
                "which is not the same as none"
            )
        )
        if offline:
            note = (
                f"{here}. The offline ceiling is set, and asking an instance what it "
                "holds is egress — so every `remote` reads null: the question was not "
                "put, which is not the same as the registry holding nothing. Clear "
                "`JMC_OFFLINE` to ask. `just-dna-enricher cache prepare` provisions "
                "what this machine can have either way."
            )
        elif gap:
            note = f"{here}. The proxy is unavailable, so nothing can answer for the rest: {gap}"
        elif remote is None:
            note = f"{here}; {describe(target, settings)} was not reached.{reach_note}"
        else:
            note = (
                f"{here} and {describe(target, settings)} holds {remote_count}. Lanes in "
                "`unreachable` are held by neither, so a tool needing one fetches live "
                "or reports the question as unasked. `just-dna-enricher cache prepare` "
                "provisions what this machine can have; a lane's `build_command` is how "
                "to make one it cannot pull."
            )

        return CacheReport(
            snapshot_route=settings.snapshot_route,
            target=target,
            lanes=rows,
            local_count=local_count,
            remote_count=remote_count,
            unreachable=unreachable,
            proxy_gap=gap,
            note=note,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Have a registry derive the tables this machine cannot",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def remote_derive(
        spec_dir: str,
        namespace: str,
        name: str,
        target: RegistryTarget = "test",
        dry_run: bool = True,
        ctx: Context | None = None,
    ) -> DerivedTreeReport:
        """Enrich a spec on a registry that holds the snapshots, and install the result.

        **The tool for a machine without the caches.** `resolution.csv` is what places
        rsID-authored rows onto coordinates and the compiler never fetches, so it has to
        travel with the spec — and producing it needs the Ensembl and ClinVar snapshots.
        Run `registry_caches` first: a lane the deployment lacks comes back naming that
        lane rather than failing vaguely.

        **This UPLOADS your module** — every authored CSV, `module_spec.yaml` and the
        `logs/` subtree — which is why it is a tool of its own rather than a flag, and
        why it is aimed with `target`. Nothing is written to any catalog, no identifier is
        claimed and no version is spent; the bearer token is an access bound on
        licence-gated snapshots, not a publish.

        **`dry_run` defaults to true and reports what installing would displace.** The
        uploaded spec carries your existing sidecars and the server gap-fills rather than
        clobbers, so a hand-curated row normally survives the round trip — but not always,
        and `decisions` is every row your files have that the new tree does not. Those are
        **not applied**: a missing row is either the source withdrawing an answer or the
        remote run being unable to ask, and only you can tell those apart. With
        `dry_run=false` the previous bytes are copied out and the copy is read back and
        hashed before anything is replaced.

        It runs what a publish runs, not what `registry_check` runs — no frequency,
        literature, identifier, ACMG or PGx pass, because those are egress spent on a
        verdict and this call is for the bytes. A spec too broken to enrich is a refusal
        here rather than an empty archive.
        """
        if offline_for(settings, False):
            raise ToolError(
                "JMC_OFFLINE is set and this route is egress: "
                "deriving a spec on a registry uploads every authored CSV, "
                "`module_spec.yaml` and the `logs/` subtree to it, and downloads "
                "the result. The offline ceiling is not "
                "loosened by a per-call argument, so this run answers locally or not "
                "at all — `enrich_module` and the `draft_from_*` tools work from this "
                "machine's own snapshot lanes, and `registry_caches` says which it "
                "holds."
            )

        gap = routing.proxy_gap()
        if gap:
            raise ToolError(gap)

        source = resolve_dir(spec_dir, settings)
        if not source.is_dir():
            raise ToolError(f"{source} is not a directory.")

        client = client_for(target, settings)
        if ctx:
            await ctx.info(f"Deriving {source.name} on {describe(target, settings)}")
            await ctx.report_progress(progress=1, total=3)

        try:
            archive = await run_sync(
                lambda: client.derived(namespace, name, source)
            )
        except Exception as exc:  # noqa: BLE001 — upstream's error text is the answer
            raise ToolError(
                f"the registry could not derive this spec: {exc}. A 503 naming a lane "
                "means the deployment lacks that snapshot — `registry_caches` says which "
                "it holds. A 422 means the spec did not validate there; this route's "
                "contract is to produce, so it refuses rather than returning an empty "
                "archive, and `registry_validate` is the tool that reports instead."
            ) from exc

        tables, extras, absent = _unpack(archive)
        try:
            lines, displaced = _displacement_lines(source, tables)
        except SidecarCollision as exc:
            raise ToolError(
                f"{exc} Nothing was written, and the derived tree is still on the "
                "server — this call is safe to re-run once one copy is gone."
            ) from exc

        if ctx:
            await ctx.report_progress(progress=2, total=3)

        capture: Path | None = None
        installed: list[str] = []
        if not dry_run and tables:
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            # The same rule `refresh_sidecar` holds, through the same two functions
            # rather than a second implementation of them: copy out, READ THE COPY BACK
            # and hash it, and only then replace. **A capture that did not verify means
            # nothing is touched at all** — not "nothing is touched for that one file",
            # because a half-installed tree is worse than an uninstalled one: the
            # sidecars are read together and a `resolution.csv` from this run beside a
            # `frequencies.csv` from the last describes no module that ever existed.
            for path in displaced:
                directory = capture_dir(settings, source, path.name)
                pending, verified = await run_sync(
                    lambda d=directory, s=path: capture_now(
                        d,
                        s,
                        {
                            "reason": "remote_derive",
                            "target": target,
                            "namespace": namespace,
                            "name": name,
                            "captured_at": stamp,
                        },
                    )
                )
                if not verified:
                    raise ToolError(
                        f"the capture of {path.name} did not verify — the copy at "
                        f"{pending} does not hash equal to the original, so nothing has "
                        "been replaced and your sidecars are untouched. This is a local "
                        "filesystem problem rather than anything to do with the "
                        "registry; the derived tree is still on the server and this call "
                        "is safe to re-run."
                    )
                capture = directory.parent
                await run_sync(
                    lambda d=directory: finalize_capture(d, stamp)
                )

            for csv_name, data in sorted(tables.items()):
                dest = _dest_for(source, csv_name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                installed.append(dest.name)

        if ctx:
            await ctx.report_progress(progress=3, total=3)

        # `not_produced` is a decision but not a ROW decision, so it stays out of
        # `decisions` — mixing the two grains is what makes a list unreadable. The
        # sentence below is what turns an enumerable fact into something to act on:
        # upstream deliberately refuses to say WHY a name is absent (a gated pass leaves
        # no note at all), so naming the two readings is ours to do and guessing between
        # them is not.
        missing = (
            " "
            + (
                f"{len(absent)} derived table(s) the run did not produce are in "
                "`not_produced` — that may be a gated pass or a snapshot this deployment "
                "lacks rather than anything about your module, and `registry_caches` "
                "answers the snapshot half."
            )
            if absent
            else ""
        )

        next_step = (
            (
                "Nothing was written. Read `decisions`: each line is a row your files "
                "carry and the new tree does not, and a `source=\"manual\"` one is hand "
                "curation nothing will re-derive. Re-run with `dry_run=false` when you "
                "have decided, then `validate_module` and `compile_module`." + missing
            )
            if dry_run
            else (
                f"Installed {len(installed)} table(s). Run `validate_module` then "
                "`compile_module(strict=true)`. A table you already carry under its "
                "deprecated spelling was written to that file rather than beside it, so "
                "this never leaves you two copies of one table." + missing
            )
        )

        return DerivedTreeReport(
            spec_dir=str(source),
            target=target,
            installed=installed,
            capture_dir=str(capture) if capture else None,
            decisions=lines,
            not_produced=absent,
            dry_run=dry_run,
            validation_errors=[],
            notes=[f"archive carried {m}" for m in sorted(extras)],
            next_step=next_step,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft rows on a registry that holds the snapshot",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def remote_draft(
        spec_dir: str,
        source: str,
        genes: list[str] | None = None,
        drugs: list[str] | None = None,
        alleles: list[str] | None = None,
        population: str | None = None,
        clin_sig: list[str] | None = None,
        min_review_stars: int | None = None,
        max_citations: int | None = None,
        min_confidence: int | None = None,
        min_evidence_level: str | None = None,
        use: str | None = None,
        target: RegistryTarget = "test",
        dry_run: bool = True,
        ctx: Context | None = None,
    ) -> DraftArchiveReport:
        """Draft spec rows from a source the registry holds a snapshot for.

        **It is not only a route — it is four drafters this plugin does not have.** The
        local tools cover ClinVar, CPIC and ClinPGx; `source` here also takes `pubmind`,
        `civic`, `mitomap-miss` and `strchive`. Run `registry_caches` first: a lane the
        deployment lacks comes back naming that lane, which is a different failure from
        the tier being absent and only one of the two is fixed by provisioning.

        **This UPLOADS your module**, so it is aimed with `target` and is never automatic.
        Nothing reaches a catalog; the token is an access bound on licence-gated
        snapshots. **Draft into a fresh spec directory**: drafting is append-only, so
        drafting twice into one tree puts corrected rows beside the ones they supersede,
        and `already_present` and `differs` are how that shows up. `dry_run` defaults to
        true, which is the documented first move.

        Every parameter is per source and a stray one is **refused rather than ignored**
        — `min_evidence_level` with `source="clinvar"` is an error, because a silently
        dropped filter produces a draft answering a different question from the one asked.
        `use` is the licence declaration those sources gate on.

        What comes back will not validate yet, by design: drafted rows carry a placeholder
        wherever only a curator can decide, so `needs_curation` names the tables that
        actually hold one. Snapshot-only and so it makes no outbound request of its own.
        """
        if offline_for(settings, False):
            raise ToolError(
                "JMC_OFFLINE is set and this route is egress: "
                "drafting on a registry sends the request out and downloads rows "
                "back. The offline ceiling is not "
                "loosened by a per-call argument, so this run answers locally or not "
                "at all — `enrich_module` and the `draft_from_*` tools work from this "
                "machine's own snapshot lanes, and `registry_caches` says which it "
                "holds."
            )

        gap = routing.proxy_gap()
        if gap:
            raise ToolError(gap)

        target_dir = resolve_dir(spec_dir, settings)
        if not target_dir.is_dir():
            raise ToolError(f"{target_dir} is not a directory.")

        client = client_for(target, settings)
        if ctx:
            await ctx.info(f"Drafting {source} on {describe(target, settings)}")
            await ctx.report_progress(progress=1, total=2)

        kwargs: dict[str, Any] = {"source": source, "dry_run": dry_run}
        for key, value in (
            ("gene", tuple(genes or ())),
            ("drug", tuple(drugs or ())),
            ("allele", tuple(alleles or ())),
            ("clin_sig", tuple(clin_sig or ())),
            ("population", population),
            ("min_review_stars", min_review_stars),
            ("max_citations", max_citations),
            ("min_confidence", min_confidence),
            ("min_evidence_level", min_evidence_level),
            ("declared_use", use),
        ):
            if value not in (None, ()):
                kwargs[key] = value

        try:
            archive = await run_sync(lambda: client.draft(target_dir, **kwargs))
        except Exception as exc:  # noqa: BLE001 — upstream's own text is the answer
            detail = str(exc)
            lane = None
            if "snapshot_unavailable" in detail:
                lane = detail.split("snapshot_unavailable")[-1].strip(" :\"'")[:60] or None
            raise ToolError(
                f"the registry could not draft from {source!r}: {detail}. "
                + (
                    f"It named the lane {lane!r}, so that deployment does not hold that "
                    "snapshot — `registry_caches` says which it holds, and the lane's "
                    "`build_command` is how an operator makes one. "
                    if lane
                    else ""
                )
                + "A 422 naming a parameter means that source does not read it, which is "
                "a refusal rather than a dropped filter: a silently ignored one would "
                "produce a draft answering a different question."
            ) from exc

        rows, extras = _unpack_draft(archive)
        report = _draft_report(extras)

        installed: list[str] = []
        if not dry_run:
            for rel, data in sorted(rows.items()):
                dest = target_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Append-only, exactly as the local drafters are: an existing file keeps
                # every row it has and the drafted ones go after. The server already did
                # the merge against the spec we uploaded, so these bytes ARE the merged
                # table — writing them whole is not a clobber, and `already_present`
                # counts what it left alone.
                dest.write_bytes(data)
                installed.append(rel)

        if ctx:
            await ctx.report_progress(progress=2, total=2)

        needs = [str(n) for n in (report.get("needs_curation") or [])]
        next_step = (
            (
                "Nothing was written. Read `differs` — those are rows where the source "
                "disagrees with something you authored, and a source that lags the edge "
                "is as likely to be the wrong side as your row is. Re-run with "
                "`dry_run=false` into a FRESH spec directory."
            )
            if dry_run
            else (
                f"Wrote {len(installed)} file(s). Decide the placeholder cells in "
                + (", ".join(needs) if needs else "nothing — no table holds one")
                + ", then `lint_rows`, then `validate_module(strict=true)`."
            )
        )

        return DraftArchiveReport(
            spec_dir=str(target_dir),
            source=source,
            target=target,
            added=int(report.get("added") or 0),
            already_present=int(report.get("already_present") or 0),
            differs=int(report.get("differs") or 0),
            needs_curation=needs,
            installed=installed,
            dry_run=dry_run,
            lane=None,
            next_step=next_step,
        )
