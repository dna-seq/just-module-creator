"""ESSENTIALS — comparing two spec directories offline, and one against the catalog.

`RM19`, built from `docs/DESIGN-version-compare.md`. **Essentials because the cost
is bounded by the two directories the caller named** — no network, no compile, no
parquet, and nothing here is sized by a corpus. The largest reference example
compares in under a fifth of a second.

It is also the tool the taught workflow needs: `module-diff`'s standing advice is
*download both versions and diff the CSVs*, which is a shell recipe an author in a
chat session cannot run, and a tier that teaches a step it cannot run is the
failure mode this repo tests for by name.

``compare_to_published`` is the second half of the same `RM19`, and stays essentials
for the same reason by a different route: **one or two bounded GETs and no
download**. Reading one named published record over the network is already
essentials — ``registry_get_module`` and ``registry_is_published`` both are — and
this is the same bounded read. It never fetches the published module's authored
rows, so it answers *whether* content differs and never *which rows*; the handover
for that is named in the result rather than escalated to a tier of its own.
"""

from __future__ import annotations

from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler
from just_dna_registry import RegistryError
from mcp.types import ToolAnnotations

from just_module_creator import compare
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    ChangeGroupOut,
    ComparedSide,
    DerivedComparison,
    FileDelta,
    FrameVerdict,
    MetadataDelta,
    ModuleComparison,
    PublishedComparison,
    TableComparison,
    Unknown,
)
from just_module_creator.settings import Settings
from just_module_creator.targets import (
    RegistryTarget,
    client_for,
    describe,
    instance_note,
)
from just_module_creator.tools._shared import resolve_dir
from just_module_creator.tools.refresh import ROSTER

log = get_logger()

_FRAME_SAME = "Both sides declare the same build, so the counts below are comparable."
_FRAME_MOVED = (
    "The two sides declare DIFFERENT builds, so the row comparison below is **not comparable** "
    "rather than clean. Identical coordinate rows on two assemblies name loci hundreds of bases "
    "apart, and the natural key is build-independent — so a row-level report of 'nothing changed' "
    "is the dangerous answer, not the reassuring one. Read this line before any count."
)
_FRAME_UNKNOWN = (
    "At least one side declares no build, or its `module_spec.yaml` could not be read. The row "
    "comparison is reported, and it is not known to be comparable."
)


def _verdict(left: object, right: object) -> str:
    if left is None or right is None:
        return "unknown"
    return "same" if left == right else "moved"


def register_comparison(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Compare two spec directories", readOnlyHint=True, idempotentHint=True
        )
    )
    async def compare_modules(
        left_dir: str,
        right_dir: str,
        max_groups: int = 12,
        examples_per_group: int = 2,
    ) -> ModuleComparison:
        """What moved between two spec directories. Offline; writes nothing, anywhere.

        Three grains in one report, because the caller does not yet know which one they
        need — that is why they called. `content` / `frame` says whether anything an
        author typed changed and whether the two sides even mean coordinates in the same
        assembly; `tables[]` gives presence, row counts, added and removed, plus
        `identity_scope`, which says *which hash your edit will move*; and
        `tables[].changed[]` groups rows by **the set of columns that changed**, which
        is what makes the row level readable — 1,190 rows changing in one column for one
        reason is one line rather than 1,190.

        **Read `frame` before any row count.** When the declared builds differ the
        comparison is *not comparable* rather than clean: the natural key is build-
        independent, so two assemblies produce character-identical keys naming loci
        hundreds of bases apart, and "zero rows changed" is then the dangerous answer.
        **`derived[]` is separate on purpose** — the authored side answers *did somebody
        edit this module*, the derived side *did a source say something different* — and
        sidecars are compared on fact signatures recomputed from disk, so a fresh
        `fetched_at` is excluded by construction rather than by filtering.

        **What it will not do, and none of it is "not yet".** No write path and no
        parameter that could become one. It never says which side is right: a later
        version is not automatically more correct, and the published corpus contains a
        version that reverted its predecessor. It never pairs rows whose natural key
        changed — one removed and one added, never one changed, because pairing asserts
        *this row became that row*. It writes no changelog prose and suggests no version
        bump. And it cannot perform the canary: detecting that a source revised an
        answer means deleting a sidecar and re-deriving it, which is `refresh_sidecar`'s
        job, because that tool knows which side it just derived. For raw cells, run
        `diff` — this reports what moved and groups it rather than reproducing a line-
        by-line diff badly.
        """
        left = resolve_dir(left_dir, settings)
        right = resolve_dir(right_dir, settings)

        def work() -> ModuleComparison:
            return _compare(left, right, max_groups, examples_per_group)

        result = await run_sync(work)
        log.info(
            "compared %s <-> %s: content %s", left.name, right.name, result.content
        )
        return result


    @mcp.tool(
        annotations=ToolAnnotations(
            title="Compare a spec against its published version",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def compare_to_published(
        target: RegistryTarget,
        spec_dir: str,
        namespace: str | None = None,
        name: str | None = None,
        version: str = "latest",
    ) -> PublishedComparison:
        """Am I ahead of the catalog, and how? One or two bounded GETs, no download.

        Reads the published version's **manifest** and compares what a manifest
        carries for free: `content_signature`, each authored file's recorded
        digest, every fact-signature block, and the metadata that sits outside
        every hash. `namespace` and `name` default from `module_spec.yaml`.

        **Read `content` first and let it govern.** It is the exact verdict on
        whether anything an author typed has changed. The per-file byte
        comparison beneath it is *subordinate*: byte equality is decisive, but
        byte inequality means almost nothing on its own — a CRLF, a reordered
        column, a reordered row and `1.00` written as `1.0` all move a file
        digest and leave `content_signature` untouched. Use `files` to decide
        where to look, never to conclude that content changed.

        **A moved fact signature under unchanged content is the interesting
        case**, and it is the only way this format reports that an upstream
        source revised an answer beneath you.

        **It does not download and it does not judge.** There is no staleness
        verdict and no "you are behind the catalog": versions carry no implicit
        contract here, so being different from the published version is a fact
        and not a defect. For row-level detail, `next_step` names the
        `registry_download` + `compare_modules` pair that gets it.

        `registry_is_published` is often the cheaper question and worth asking
        first — it answers "is my exact content already published, under any
        name" without needing a namespace at all.
        """
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        local = resolve_dir(spec_dir, settings)
        build, module_block = compare.read_build(local)
        ns = namespace or _text(module_block.get("namespace"))
        mod = name or _text(module_block.get("name"))
        if not ns or not mod:
            raise ToolError(
                "No namespace/name given and module_spec.yaml's `module:` block does not carry "
                f"both (namespace={ns!r}, name={mod!r}). Pass them explicitly."
            )

        def _fetch() -> tuple[str, object]:
            client = client_for(target, settings)
            resolved = client.resolve_version(ns, mod, version) if version == "latest" else version
            return resolved, client.manifest(ns, mod, resolved)

        try:
            resolved_version, manifest = await run_sync(_fetch)
        except RegistryError as exc:
            raise ToolError(
                f"{describe(target, settings)} could not answer for {ns}/{mod}@{version}: "
                f"{exc}{instance_note(exc)}"
            ) from exc

        return await run_sync(
            lambda: _compare_published(
                local, build, f"{ns}/{mod}@{resolved_version}", target, manifest
            )
        )


def _compare(
    left: Path, right: Path, max_groups: int, examples_per_group: int
) -> ModuleComparison:
    left_build, left_module = compare.read_build(left)
    right_build, right_module = compare.read_build(right)
    unknown: list[Unknown] = []

    left_tables = compare.authored_tables(left, left_build or "GRCh38")
    right_tables = compare.authored_tables(right, right_build or "GRCh38")

    frame_verdict = _verdict(left_build, right_build)
    frame = FrameVerdict(
        left_build=left_build,
        right_build=right_build,
        verdict=frame_verdict,
        note={"same": _FRAME_SAME, "moved": _FRAME_MOVED}.get(frame_verdict, _FRAME_UNKNOWN),
    )

    tables: list[TableComparison] = []
    for csv in sorted(set(left_tables) | set(right_tables)):
        diff, notes = compare.compare_table(
            csv, left_tables.get(csv), right_tables.get(csv), max_groups, examples_per_group
        )
        unknown += [Unknown(subject=s, reason=r) for s, r in notes]
        tables.append(
            TableComparison(
                csv=diff.csv,
                identity_scope=diff.identity_scope,
                presence=diff.presence,
                spelling_left=diff.spelling_left,
                spelling_right=diff.spelling_right,
                rows_left=diff.rows_left,
                rows_right=diff.rows_right,
                row_key=diff.row_key,
                key_collisions=diff.key_collisions,
                unchanged=diff.unchanged,
                added=diff.added,
                removed=diff.removed,
                changed=[
                    ChangeGroupOut(columns=g.columns, rows=g.rows, examples=g.examples)
                    for g in diff.changed
                ],
            )
        )

    derived_diffs, derived_notes = compare.compare_derived(left, right, ROSTER)
    unknown += [Unknown(subject=s, reason=r) for s, r in derived_notes]
    derived = [
        DerivedComparison(
            csv=d.csv,
            verdict=d.verdict,
            left_signature=d.left_signature,
            right_signature=d.right_signature,
            signature_source=d.signature_source,
            rows_left=d.rows_left,
            rows_right=d.rows_right,
        )
        for d in derived_diffs
    ]

    left_sig = compare.content_signature_of(left)
    right_sig = compare.content_signature_of(right)
    for side, sig, path in (("left", left_sig, left), ("right", right_sig, right)):
        if sig is None:
            unknown.append(
                Unknown(
                    subject=f"content_signature ({side})",
                    reason=f"{path.name} could not be read as a spec directory, so the "
                    "content verdict is unknown rather than moved.",
                )
            )

    metadata: list[MetadataDelta] = []
    for key in sorted(set(left_module) | set(right_module)):
        a, b = left_module.get(key), right_module.get(key)
        if a != b:
            metadata.append(
                MetadataDelta(what=f"module_spec.yaml:{key}", left=_text(a), right=_text(b))
            )
    for name in ("README.md", "logo.png"):
        a, b = (left / name).is_file(), (right / name).is_file()
        if a != b:
            metadata.append(
                MetadataDelta(
                    what=name,
                    left="present" if a else "absent",
                    right="present" if b else "absent",
                )
            )

    return ModuleComparison(
        left=ComparedSide(path=str(left), genome_build=left_build, tables=len(left_tables)),
        right=ComparedSide(path=str(right), genome_build=right_build, tables=len(right_tables)),
        frame=frame,
        content=_verdict(left_sig, right_sig),
        left_content_signature=left_sig,
        right_content_signature=right_sig,
        tables=tables,
        derived=derived,
        metadata=metadata,
        unknown=unknown,
        note=(
            "What moved, never which side is right. `metadata[]` carries what moved that no "
            "identity records, and `unknown[]` says what this report is not telling you. "
            "`artifact.digest` is deliberately absent: comparing it needs both manifests, and "
            "across two compiler versions it differs for a reason nobody asked about."
        ),
    )



#: The manifest's fact-signature blocks, and the local sidecar each is computed from.
#: Hand-kept because nothing public enumerates the pairing, and pinned by
#: `test_every_manifest_fact_block_is_a_live_field` so a rename fails here rather
#: than silently dropping a canary.
_FACT_BLOCKS = {
    "frequency": "frequencies.csv",
    "gwas_effects": "gwas_effects.csv",
    "gene_metrics": "gene_metrics.csv",
    "gene_validity": "gene_validity.csv",
    "clinical_assertions": "clinical_assertions.csv",
    "literature": "literature.csv",
}


def _compare_published(
    local: Path,
    build: str | None,
    canonical: str,
    target: str,
    manifest: object,
) -> PublishedComparison:
    """The pure half: a local spec directory against a fetched manifest.

    Separated from the tool so the network is the only thing the tool adds, which
    is what lets this be tested against a real manifest with no socket open.
    """
    unknown: list[Unknown] = []

    published_build = _text(getattr(manifest, "genome_build", None))
    frame_verdict = _verdict(build, published_build)
    frame = FrameVerdict(
        left_build=build,
        right_build=published_build,
        verdict=frame_verdict,
        note={"same": _FRAME_SAME, "moved": _FRAME_MOVED}.get(frame_verdict, _FRAME_UNKNOWN),
    )

    local_sig = compare.content_signature_of(local)
    published_sig = _text(getattr(manifest, "content_signature", None))
    if local_sig is None:
        unknown.append(
            Unknown(
                subject="content_signature (local)",
                reason=f"{local.name} could not be read as a spec directory, so the content "
                "verdict is unknown rather than moved.",
            )
        )
    if published_sig is None:
        unknown.append(
            Unknown(
                subject="content_signature (published)",
                reason="The published manifest carries no content_signature — it predates the "
                "field. Unknown, never 'moved': nothing was compared.",
            )
        )

    # Per-file bytes. Recomputed locally against what the manifest recorded, which
    # reproduces the published entries byte for byte when the files really match.
    inputs = list(getattr(manifest, "inputs", []) or [])
    published_files = {e.name: _text(getattr(e, "sha256", None)) for e in inputs}
    files: list[FileDelta] = []
    if published_files:
        names = sorted(published_files)
        try:
            # `file_entries`, NOT `newline_normalized_file_entries`. The comment here
            # used to claim the publisher hashes through `authored_input_entries`,
            # which normalizes newlines. It does not, and upstream's own RM82
            # docstring on that function says so in terms: "`manifest.inputs[]` is
            # deliberately not [newline-normalized] ... that field is filled
            # independently, by `file_entries(spec_dir, _INPUT_FILES)` over the raw
            # bytes, and the two were only ever equal by coincidence". The registry
            # runs the same compiler server-side, so a published entry follows the
            # same raw rule as a local one — there is no asymmetry to bridge.
            #
            # The normalization exists for exactly one consumer, the closure
            # attestation `verification.module_binding`, so that an editor rewriting
            # line endings cannot un-close a module. Borrowing it here inverted its
            # purpose: it fired on precisely the CRLF-carrying files it was meant to
            # protect, reporting 31 of 34 authored CSVs across eight published
            # modules as "moved" while they were byte-identical, and printing a
            # "local" digest matching no bytes anyone ever recorded — so an author
            # could not reconcile it by hand either.
            entries = compiler.file_entries(local, names)
        except (OSError, ValueError) as exc:
            entries = []
            unknown.append(
                Unknown(
                    subject="authored file digests",
                    reason=f"Local digests could not be computed ({exc}), so every per-file "
                    "verdict is unknown. `content` above is unaffected.",
                )
            )
        local_files = {e.name: _text(getattr(e, "sha256", None)) for e in entries}
        for filename in names:
            files.append(
                FileDelta(
                    name=filename,
                    verdict=_verdict(local_files.get(filename), published_files[filename]),
                    local_sha256=local_files.get(filename),
                    published_sha256=published_files[filename],
                )
            )
    else:
        unknown.append(
            Unknown(
                subject="authored file digests",
                reason="The published manifest lists no inputs, so there is nothing to compare "
                "the local bytes against.",
            )
        )

    # The canary. A moved fact signature under unchanged content is a source that
    # revised an answer, and nothing else in this format reports it.
    facts: list[DerivedComparison] = []
    for block, csv_name in sorted(_FACT_BLOCKS.items()):
        published_block = getattr(manifest, block, None)
        published_fact = _text(getattr(published_block, "signature", None))
        sidecar = ROSTER.get(csv_name)
        local_fact, rows_local, why = (
            compare._read_sidecar(local / csv_name, sidecar, csv_name)
            if sidecar is not None
            else (None, None, f"{csv_name} has no signature function here")
        )
        if published_fact is None and local_fact is None:
            continue
        if why:
            unknown.append(Unknown(subject=f"{csv_name} (local)", reason=why))
        facts.append(
            DerivedComparison(
                csv=csv_name,
                verdict=_verdict(local_fact, published_fact),
                left_signature=local_fact,
                right_signature=published_fact,
                signature_source="recomputed" if local_fact else "unavailable",
                rows_left=rows_local,
                rows_right=getattr(published_block, "row_count", None),
            )
        )

    # What moved with no identity behind it.
    metadata: list[MetadataDelta] = []
    readme = getattr(manifest, "readme", None)
    local_readme = (local / "README.md").is_file()
    if bool(readme) != local_readme:
        metadata.append(
            MetadataDelta(
                what="readme",
                left="present" if local_readme else "absent",
                right="present" if readme else "absent",
            )
        )
    closure = getattr(getattr(manifest, "verification", None), "closure", None)
    if closure is not None:
        metadata.append(
            MetadataDelta(
                what="closure",
                left="(not compared locally)",
                right=_text(getattr(closure, "module_hash", None)) or "present",
            )
        )
    published_compiler = _text(
        getattr(getattr(manifest, "compilation", None), "compiler_version", None)
    )
    if published_compiler:
        metadata.append(
            MetadataDelta(
                what="compiler_version",
                left="(this spec is not compiled here)",
                right=published_compiler,
            )
        )

    content = _verdict(local_sig, published_sig)
    return PublishedComparison(
        spec_dir=str(local),
        canonical_id=canonical,
        target=target,
        content=content,
        local_content_signature=local_sig,
        published_content_signature=published_sig,
        frame=frame,
        files=files,
        facts=facts,
        metadata=metadata,
        unknown=unknown,
        next_step=(
            f"For row-level detail: `registry_download` {canonical} (it fetches the authored "
            "inputs, and verifies every digest as it goes), then `compare_modules` against "
            "this directory. This tool deliberately does not download."
            if content != "same"
            else "Nothing to chase: every authored row matches what was published."
        ),
        note=(
            "`content` is the verdict; the per-file digests are only a pointer to where to "
            "look, because byte inequality moves on formatting that content_signature ignores. "
            "No staleness is computed and none is implied — differing from the published "
            "version is a fact about two versions, not a defect in either. `artifact.digest` "
            "is deliberately absent: across two compiler versions it differs for a reason "
            "nobody asked about."
        ),
    )


def _text(value: object) -> str | None:
    return None if value is None else str(value)
