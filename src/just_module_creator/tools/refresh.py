"""Re-deriving one derived sidecar without destroying what a human put in it.

Every derived sidecar is **merge-not-clobber**: a pass that finds a row already
recorded leaves it exactly as it is. That is what makes a hand-corrected number
survive a re-run, and it is also why a re-run refreshes *nothing*. To ask a
source whether it still says what the file says, the file has to be **deleted
first** — and deleting it discards the author's rows along with the stale ones.
`resolution.csv`'s `source="manual"` rows are the case that is not recoverable by
re-running: nothing fetches them, because a human worked them out.

So the only upstream-drift detector this format has is a destructive,
irreversible, manual sequence. `refresh_sidecar` turns it into a reversible
reported one:

1. **capture** the file to a durable location *outside* the spec directory, and
   read the copy back and hash it before anything is deleted;
2. **delete** it — never without a verified capture;
3. **re-derive** it by running the upstream pass (or passes) that own it;
4. **classify** every row by subject and by fact;
5. **reapply** only what is provably the author's, and **report** the rest.

Three decisions are worth stating here, because each is a place where a more
helpful-looking tool would be a worse one.

**The capture never goes into the spec directory.** An invented file there is not
in `just_dna_registry.specfiles.RECOGNIZED_SPEC_FILES`, so a server-side rebuild
drops it silently — the failure that lost `licensing.csv` before registry 0.16.2
and README files before 0.14. It goes to a resolved cache/workspace path, through
`_shared.resolve_dir`, so `JMC_WORKSPACE` containment still holds.

**A conflict is reported and not resolved — and RM15 asked whether that is
physics or inherited policy. It is physics, but conditionally, and the condition
is worth knowing.** When a subject is present in both copies with differing
facts, the fetched row is *either* a cell the author edited *or* a revision the
source published. With only the captured value and the fresh value, nothing can
separate those: it is two data points and three explanations. So nothing here
guesses, prefers a side or merges.

**The condition:** it is two data points because we do not keep a third. An
authoring log recording that this cell was edited, by whom and why, would settle
it outright — and CLAUDE.md §2 now requires exactly that of every authoring
move. The `logs/` surface exists and is empty. So this refusal is honest today
and is **not permanent**: when the log is filled, a conflict whose edit is
recorded stops being ambiguous, and this tool should read it rather than keep
shrugging. Do not harden the current answer into a principle.

Where `source` proves a human wrote the row, that is surfaced per row and is
still not acted on, for a reason the log does not touch: knowing *who* wrote a
row does not settle *which of two answers about the world* is right. The source
may equally be the stale one — an archive lags the edge — so preferring it
because it is the source would be the mindless correction §2 forbids.

**A partial re-derivation is never classified against.** If a pass is offline, a
source is unreachable, or the fresh table comes back empty, the captured bytes go
back verbatim and the run reports why. Classifying against a table that was never
filled would report every real row as one the source had withdrawn — which is the
exact false negative this tool exists to prevent.

Extended tier, on the cost rule and not on usefulness: a refresh runs whichever
pass owns the sidecar, and `gwas_effects.csv`'s pass is measured at 382 requests
for one real module. Registering this in essentials would let the default tier
spend an extended-tier budget through a different door.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler.compiler import load_csv_rows
from just_dna_enricher.assertions import ClinicalAssertionError, enrich_clinical_assertions
from just_dna_enricher.clingen import ClinGenError, ClinGenUnavailable, enrich_dosage_sensitivity
from just_dna_enricher.enrich import EnrichmentError, IdentifierUnavailable, enrich
from just_dna_enricher.frequencies import (
    FrequencyEnrichmentError,
    FrequencyUnavailable,
    enrich_frequencies,
)
from just_dna_enricher.gene_metrics import (
    GeneMetricsEnrichmentError,
    GeneMetricsUnavailable,
    enrich_gene_metrics,
)
from just_dna_enricher.gene_validity import (
    GeneValidityError,
    GeneValidityUnavailable,
    enrich_gene_validity,
)
from just_dna_enricher.gwas import GwasError, enrich_gwas
from just_dna_enricher.literature import (
    LiteratureEnrichmentError,
    LiteratureUnavailable,
    enrich_literature,
)
from just_dna_format.assertions import CLINICAL_ASSERTION_FACT_FIELDS, ClinicalAssertionRow
from just_dna_format.frequency import FREQUENCY_FACT_FIELDS, FrequencyRow
from just_dna_format.gene_metrics import GENE_METRICS_FACT_FIELDS, GeneMetricsRow
from just_dna_format.gene_validity import GENE_VALIDITY_FACT_FIELDS, GeneValidityRow
from just_dna_format.gwas import GWAS_FACT_FIELDS, GwasEffectRow
from just_dna_format.integrity import (
    clinical_assertion_signature,
    frequency_signature,
    gene_metrics_signature,
    gene_validity_signature,
    gwas_effect_signature,
    literature_signature,
    resolution_signature,
)
from just_dna_format.layout import (
    SidecarCollision,
    preferred_spelling,
    resolve_sidecar,
    sidecar_write_path,
)
from just_dna_format.literature import LITERATURE_FACT_FIELDS, LiteratureRow
from just_dna_format.resolution import RESOLUTION_FACT_FIELDS, ResolutionRow
from just_dna_format.vocab import VALID_DECLARED_USE
from just_dna_registry.specfiles import FACT_CSVS, LICENSING_CSV, RESOLUTION_CSV, SOURCES_CSV
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    LintFinding,
    SidecarConflict,
    SidecarRefreshReport,
    SidecarRow,
)
from just_module_creator.net import NetworkServices
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import offline_for, resolve_dir, schema_versions

log = get_logger()

#: How many rows of any one bucket are listed. The counts are always complete; a
#: real `gwas_effects.csv` refresh can move thousands of rows and a full listing
#: would cost more context than the answer is worth.
MAX_LISTED = 40

#: The in-flight capture. Named rather than timestamped so a crashed run leaves
#: something a later run can *find*: a timestamped file would be indistinguishable
#: from the audit trail beside it.
PENDING_CSV = "pending.csv"
PENDING_STATE = "pending.json"

#: Where captures go when no workspace is configured. Deliberately under the
#: user's cache root rather than anywhere near a spec directory.
CACHE_SUBPATH = (".cache", "just-module-creator", "sidecar-captures")

#: Directory name used for captures when `JMC_WORKSPACE` is set. The cache root
#: would be outside the containment boundary, and a workspace is a boundary
#: rather than a preference.
WORKSPACE_SUBDIR = ".jmc-sidecar-captures"


# --------------------------------------------------------------------------- #
# The roster: which pass owns which sidecar
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SidecarPass:
    """One upstream pass, and how its outage is told apart from its failure.

    ``unavailable`` and ``error`` are separate tuples and are caught **narrow
    first**. Since enricher 0.6.2 each ``*Unavailable`` is a subclass of the type
    beside it, so a parent-first pair of arms sends every outage into the parent
    arm and leaves the outage arm dead — silently, raising nothing. An empty
    ``unavailable`` tuple is a pass whose family publishes no outage type; ``except
    ():`` matches nothing, which is the honest encoding of "there is none".
    """

    name: str
    run: Callable[..., Any]
    unavailable: tuple[type[BaseException], ...] = ()
    error: tuple[type[BaseException], ...] = ()
    reads_licence_bearing_source: bool = False


@dataclass(frozen=True)
class Sidecar:
    """A derived sidecar, its row model, its fact contract and its producers."""

    csv: str
    model: type[BaseModel]
    fact_fields: tuple[str, ...]
    signature: Callable[[Sequence[BaseModel]], str]
    passes: tuple[SidecarPass, ...]


def _run_resolution(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    # `enrich`'s own defaults everywhere else. Note this is not `compile_module`'s
    # `resolve_with_ensembl` trap: `enrich` has no such master switch.
    return enrich(spec_dir, mode=mode, offline=offline, write=True)


def _run_frequencies(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    return enrich_frequencies(spec_dir, mode=mode, offline=offline, write=True)


def _run_gene_metrics(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    return enrich_gene_metrics(spec_dir, mode=mode, offline=offline, write=True)


def _run_dosage(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    return enrich_dosage_sensitivity(
        spec_dir, mode=mode, declared_use=use, offline=offline, write=True
    )


def _run_literature(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    return enrich_literature(
        spec_dir,
        mode=mode,
        offline=offline,
        write=True,
        eutils=services.lookup_clients.eutils,
        europepmc=services.lookup_clients.europepmc,
        crossref=services.lookup_clients.crossref,
    )


def _run_gene_validity(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    return enrich_gene_validity(spec_dir, mode=mode, offline=offline, write=True)


def _run_clinical_assertions(
    spec_dir: Path, mode: str, offline: bool, use: str, services: Any
) -> Any:
    return enrich_clinical_assertions(spec_dir, mode=mode, offline=offline, write=True)


def _run_gwas(spec_dir: Path, mode: str, offline: bool, use: str, services: Any) -> Any:
    return enrich_gwas(spec_dir, mode=mode, offline=offline, write=True, declared_use=use)


#: The sidecars a pass can re-derive, and every pass that writes each one.
#:
#: **`gene_metrics.csv` has TWO producers and both have to run.** The constraint
#: pass fills the gnomAD columns; `enrich_dosage_sensitivity` writes ClinGen's
#: haploinsufficiency / triplosensitivity onto the *same* file rather than one of
#: its own. Re-deriving with only the first would rebuild half the table and then
#: report every dosage row as one the source had withdrawn.
#:
#: The models are paired with the file names by hand, because there is no public
#: `csv -> row model` route for the machine-written tables (upstream `S47`; the
#: private `compiler._FACT_TABLES` is exactly this and is not ours to import).
#: `test_refresh.py` pins the roster's keys against the public roster, so an
#: eighth fact table fails the suite rather than being silently unsupported.
#: Everything *inside* each entry is upstream's own public constant.
ROSTER: dict[str, Sidecar] = {
    RESOLUTION_CSV: Sidecar(
        csv=RESOLUTION_CSV,
        model=ResolutionRow,
        fact_fields=RESOLUTION_FACT_FIELDS,
        signature=resolution_signature,
        passes=(
            SidecarPass(
                "enrich",
                _run_resolution,
                unavailable=(IdentifierUnavailable,),
                error=(EnrichmentError,),
            ),
        ),
    ),
    "frequencies.csv": Sidecar(
        csv="frequencies.csv",
        model=FrequencyRow,
        fact_fields=FREQUENCY_FACT_FIELDS,
        signature=frequency_signature,
        passes=(
            SidecarPass(
                "enrich_frequencies",
                _run_frequencies,
                unavailable=(FrequencyUnavailable,),
                error=(FrequencyEnrichmentError,),
            ),
        ),
    ),
    "gene_metrics.csv": Sidecar(
        csv="gene_metrics.csv",
        model=GeneMetricsRow,
        fact_fields=GENE_METRICS_FACT_FIELDS,
        signature=gene_metrics_signature,
        passes=(
            SidecarPass(
                "enrich_gene_metrics",
                _run_gene_metrics,
                unavailable=(GeneMetricsUnavailable,),
                error=(GeneMetricsEnrichmentError,),
            ),
            SidecarPass(
                "enrich_dosage_sensitivity",
                _run_dosage,
                unavailable=(ClinGenUnavailable,),
                error=(ClinGenError,),
                reads_licence_bearing_source=True,
            ),
        ),
    ),
    "literature.csv": Sidecar(
        csv="literature.csv",
        model=LiteratureRow,
        fact_fields=LITERATURE_FACT_FIELDS,
        signature=literature_signature,
        passes=(
            SidecarPass(
                "enrich_literature",
                _run_literature,
                unavailable=(LiteratureUnavailable,),
                error=(LiteratureEnrichmentError,),
            ),
        ),
    ),
    "gene_validity.csv": Sidecar(
        csv="gene_validity.csv",
        model=GeneValidityRow,
        fact_fields=GENE_VALIDITY_FACT_FIELDS,
        signature=gene_validity_signature,
        passes=(
            SidecarPass(
                "enrich_gene_validity",
                _run_gene_validity,
                unavailable=(GeneValidityUnavailable,),
                error=(GeneValidityError,),
            ),
        ),
    ),
    "clinical_assertions.csv": Sidecar(
        csv="clinical_assertions.csv",
        model=ClinicalAssertionRow,
        fact_fields=CLINICAL_ASSERTION_FACT_FIELDS,
        signature=clinical_assertion_signature,
        passes=(
            SidecarPass(
                "enrich_clinical_assertions",
                _run_clinical_assertions,
                error=(ClinicalAssertionError,),
            ),
        ),
    ),
    "gwas_effects.csv": Sidecar(
        csv="gwas_effects.csv",
        model=GwasEffectRow,
        fact_fields=GWAS_FACT_FIELDS,
        signature=gwas_effect_signature,
        passes=(
            SidecarPass(
                "enrich_gwas",
                _run_gwas,
                error=(GwasError,),
                reads_licence_bearing_source=True,
            ),
        ),
    ),
}

#: `licensing.csv` / `sources.csv` is the one derived sidecar with **no**
#: re-deriving pass. Nothing fetches a licence row on its own: each is written as
#: a side effect of a pass that *took* data, and a row copied out of a source by
#: hand has no producer at all. So deleting it discards the entire declaration the
#: compile gate reads, with nothing to put back. Refused rather than attempted.
UNREFRESHABLE = {
    SOURCES_CSV: (
        "no pass derives this table. Every other sidecar has a producer that can be re-run; "
        "licence rows are written as a side effect of a pass that took data, and a row you "
        "copied out of a source by hand has no producer at all. Deleting the file would "
        "discard the whole declaration the compile gate reads, and nothing would rebuild it. "
        "It is also the one table whose `source` column is its own subject rather than its "
        "provenance, so the authorship test the other seven use does not exist here. Edit it "
        "in place instead, at the spelling that is already there."
    ),
}
UNREFRESHABLE[LICENSING_CSV] = UNREFRESHABLE[SOURCES_CSV]


# --------------------------------------------------------------------------- #
# Row identity, derived from the live models
# --------------------------------------------------------------------------- #
def subject_fields(sidecar: Sidecar) -> tuple[str, ...]:
    """The columns that decide whether two rows are the same row.

    Derived, never written down: the table's own ``*_FACT_FIELDS`` tuple narrowed
    to the columns its row model marks **required**. That reproduces each pass's
    merge key on five of the seven tables and is *coarser* on the other two, and
    coarser is the safe direction — a coarse subject reports more rows as
    conflicting, and a conflict is never auto-resolved.

    The exact key exists nowhere public: each pass keys its own `existing` dict on
    a local expression (`(row.variant_key, row.population)` inside
    `enrich_frequencies`, and so on). Filed upstream as `S51`; until it lands this
    derivation is reported on every call rather than assumed.
    """
    fields = sidecar.model.model_fields
    return tuple(
        name
        for name in sidecar.fact_fields
        if name in fields and fields[name].is_required()
    )


def canonical(row: BaseModel, fields: Sequence[str]) -> str:
    """One row reduced to ``fields``, nulls dropped, canonically encoded.

    The same normalization ``integrity.fact_signature`` hashes, so a fact key
    computed here and the signature published in the manifest agree about what
    "the same fact" means rather than being two conventions.
    """
    wanted = set(fields)
    dumped = row.model_dump(mode="json")
    return json.dumps(
        {key: value for key, value in dumped.items() if key in wanted and value is not None},
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass(frozen=True)
class Table:
    """A sidecar read twice: as validated models, and as the text on disk."""

    path: Path
    header: list[str]
    raw: list[dict[str, str]]
    rows: list[BaseModel]


def read_table(path: Path, sidecar: Sidecar) -> tuple[Table | None, list[str]]:
    """Read a sidecar as models *and* as raw cells, or report why it cannot be.

    Both, because the two answer different questions: the models decide identity,
    and the raw cells are what gets written back — a reapplied row keeps the text
    it had, so nothing here can reformat `1.00` into `1.0` on a row it promised
    not to touch.
    """
    rows, errors, _ = load_csv_rows(path, sidecar.model, path.name)
    if errors:
        return None, errors
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        raw = [{k: (v or "") for k, v in row.items() if k is not None} for row in reader]
    if len(raw) != len(rows):
        return None, [
            f"{path.name}: {len(raw)} line(s) on disk but {len(rows)} validated row(s) — "
            "the two cannot be aligned, so nothing here will classify or delete it."
        ]
    return Table(path=path, header=header, raw=raw, rows=rows), []


def to_sidecar_rows(
    table: Table,
    sidecar: Sidecar,
    subjects: Sequence[str],
    fetcher_sources: frozenset[str] | None,
) -> list[SidecarRow]:
    """Project a table's rows for the report, one `SidecarRow` per line.

    ``fetcher_sources`` is the set of `source` values the *freshly derived* table
    uses — derived from the data, never a written-down list of provider names. A
    row whose `source` is outside it was not written by this pass. ``None`` means
    the fresh table named no source at all, so the question could not be put and
    the answer stays `null` rather than becoming `false`.
    """
    out: list[SidecarRow] = []
    for row, raw in zip(table.rows, table.raw, strict=True):
        source = getattr(row, "source", None)
        # Three-valued on purpose: `None` where the question could not be put.
        proves: bool | None = (
            None if fetcher_sources is None else bool(source) and source not in fetcher_sources
        )
        out.append(
            SidecarRow(
                subject=canonical(row, subjects),
                fact_key=canonical(row, sidecar.fact_fields),
                source=source,
                source_proves_authored=proves,
                cells=dict(raw),
            )
        )
    return out


def differing_fact_fields(
    left: Sequence[SidecarRow], right: Sequence[SidecarRow], fields: Sequence[str]
) -> list[str]:
    """Which fact columns the two sides of a conflict disagree on, sorted."""
    def values(rows: Sequence[SidecarRow], name: str) -> frozenset[str]:
        return frozenset(row.cells.get(name, "") for row in rows)

    return sorted(name for name in fields if values(left, name) != values(right, name))


# --------------------------------------------------------------------------- #
# The durable capture
# --------------------------------------------------------------------------- #
def capture_root(settings: Settings) -> Path:
    """Where captures live: inside the workspace when one is set, else the cache.

    A configured ``JMC_WORKSPACE`` is a containment boundary rather than a
    preference, and the user's cache root sits outside it — so a workspace moves
    the captures rather than being ignored. Either way it is **never** the spec
    directory: a file invented there is not in the registry's recognised set and a
    server-side rebuild drops it without saying so.
    """
    if settings.workspace:
        return Path(settings.workspace).expanduser() / WORKSPACE_SUBDIR
    return Path.home().joinpath(*CACHE_SUBPATH)


def capture_dir(settings: Settings, spec_dir: Path, csv_name: str) -> Path:
    """One directory per (spec directory, sidecar), stable across runs.

    The spec directory's absolute path is hashed into the name so two modules with
    the same folder name cannot share a capture, while the readable half keeps the
    tree navigable by a human looking for their rows back.

    Resolved through ``_shared.resolve_dir`` like every other path this server
    writes to, so a configured workspace contains the captures too and a symlinked
    cache root cannot escape it.
    """
    digest = hashlib.sha256(str(spec_dir).encode("utf-8")).hexdigest()[:12]
    wanted = capture_root(settings) / f"{spec_dir.name}-{digest}" / Path(csv_name).stem
    return resolve_dir(str(wanted), settings, must_exist=False)


def capture_now(directory: Path, source: Path, state: dict[str, Any]) -> tuple[Path, bool]:
    """Copy ``source`` into ``directory``, then read it back and verify the bytes.

    Verification is the point, not ceremony: the caller deletes the original next,
    and a capture nobody read back is a promise rather than a copy. Returns the
    capture path and whether the two hashes agreed — on `False` the caller must
    not delete anything.
    """
    directory.mkdir(parents=True, exist_ok=True)
    original = source.read_bytes()
    pending = directory / PENDING_CSV
    pending.write_bytes(original)
    verified = hashlib.sha256(pending.read_bytes()).hexdigest() == hashlib.sha256(
        original
    ).hexdigest()
    (directory / PENDING_STATE).write_text(
        json.dumps(state, indent=2, sort_keys=True), encoding="utf-8"
    )
    return pending, verified


def finalize_capture(directory: Path, stamp: str) -> Path:
    """Retire the in-flight capture into the audit trail, keeping its bytes.

    Renamed rather than removed. The capture is the only copy of a row this run
    reported but did not put back, so deleting it here would quietly close the one
    route back to it — that deletion is the author's to make.
    """
    pending = directory / PENDING_CSV
    state = directory / PENDING_STATE
    kept = directory / f"{stamp}.csv"
    if pending.is_file():
        pending.replace(kept)
    if state.is_file():
        state.replace(directory / f"{stamp}.json")
    return kept


# --------------------------------------------------------------------------- #
# Writing the refreshed file
# --------------------------------------------------------------------------- #
def write_merged(
    path: Path, fresh: Table, extra: Sequence[dict[str, str]]
) -> None:
    """Put ``extra`` rows back into the freshly derived file, cells verbatim.

    A CSV writer, never string concatenation: several cells legitimately contain
    commas, and a hand-built line surfaces three columns away as a validation
    error about something else entirely.

    The header is the fresh file's plus any column only the reapplied rows fill.
    When it has to grow the whole file is rewritten from the text already in it,
    so an existing cell keeps its exact spelling and only its line number moves.
    """
    union = list(fresh.header) + [
        name for row in extra for name in row if name not in fresh.header
    ]
    seen: list[str] = []
    for name in union:
        if name not in seen:
            seen.append(name)
    if seen == list(fresh.header) and fresh.header:
        with path.open("a", encoding="utf-8", newline="") as handle:
            # A file whose last line has no terminator would glue the first
            # reapplied row onto it — a row this function promised not to touch.
            if not path.read_bytes().endswith(b"\n"):
                handle.write(csv.excel.lineterminator)
            writer = csv.DictWriter(
                handle, fieldnames=seen, restval="", extrasaction="ignore"
            )
            writer.writerows(extra)
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=seen, restval="", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(list(fresh.raw) + list(extra))


def aggregate(counted: Sequence[tuple[int, str]]) -> list[str]:
    """One warning per reason, with its count. Never one line per row."""
    return [f"{count} {reason}" for count, reason in counted if count]


# --------------------------------------------------------------------------- #
# Argument checks
# --------------------------------------------------------------------------- #
def check_sidecar(name: str) -> Sidecar:
    """Resolve a sidecar name, with a usable error and the honest refusals."""
    wanted = name.strip()
    if not wanted.endswith(".csv"):
        wanted = f"{wanted}.csv"
    if wanted in ROSTER:
        return ROSTER[wanted]
    if wanted in UNREFRESHABLE:
        raise ToolError(f"{wanted} cannot be refreshed: {UNREFRESHABLE[wanted]}")
    raise ToolError(
        f"Unknown sidecar {name!r}. Refreshable: {', '.join(sorted(ROSTER))}. "
        f"Authored tables are not refreshable at all — nothing re-derives a row you wrote."
    )


def check_use(sidecar: Sidecar, use: str | None) -> str:
    """Validate the licence declaration where a pass reads one. Never defaulted.

    Same rule the drafters hold: upstream defaults ``declared_use="unstated"``, and
    inheriting that would silently skip a licence-bearing source, while defaulting
    to anything else asserts a position the caller never took. The vocabulary is
    the format's own ``VALID_DECLARED_USE``, not a list written here.
    """
    needed = [p.name for p in sidecar.passes if p.reads_licence_bearing_source]
    if not needed:
        return "unstated"
    if use is None:
        raise ToolError(
            f"`use` is required for {sidecar.csv}: {', '.join(needed)} reads a licence-bearing "
            f"source, and taking the data is what accepts the terms. Pass one of "
            f"{', '.join(sorted(VALID_DECLARED_USE))}. There is no default because both possible "
            f"defaults are wrong — 'unstated' silently skips the source, and anything else "
            f"asserts a position you may not hold."
        )
    normalized = use.strip().replace("-", "_").lower()
    if normalized not in VALID_DECLARED_USE:
        raise ToolError(
            f"`use` must be one of {', '.join(sorted(VALID_DECLARED_USE))} — got {use!r}."
        )
    return normalized


# --------------------------------------------------------------------------- #
# The tool
# --------------------------------------------------------------------------- #
def register_refresh(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the non-destructive sidecar refresh (extended tier)."""

    @mcp.tool(
        tags={"extended"},
        task=True,
        annotations=ToolAnnotations(
            title="Refresh a derived sidecar",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def refresh_sidecar(
        spec_dir: str,
        sidecar: str,
        use: str | None = None,
        strict: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> SidecarRefreshReport:
        """Re-derive one derived sidecar against its source, keeping your own rows.

        Every derived sidecar is **merge-not-clobber**: a re-run adds rows and
        refreshes nothing already recorded. So asking a source whether it still
        says what the file says means deleting the file first — and that discards
        the rows a human worked out along with the stale ones. This does the
        sequence reversibly: it copies the file somewhere durable *outside* the
        spec directory and verifies the copy before deleting anything, re-runs the
        pass that owns the table, classifies every row, puts back what is provably
        yours, and reports everything else.

        **Read `signature_moved` first. It is the canary.** A moved fact signature
        with nothing reapplied and no conflict means the upstream source changed
        its answer — the only drift this format can detect at all. An unmoved one
        means the source still says exactly what your file said.

        **It does not resolve a conflict.** A subject present in both copies whose
        facts differ is *either* a cell you edited *or* a revision the source
        published, and the two values alone cannot separate those — two data
        points, three explanations. So nothing here guesses, prefers a side or
        merges: `conflicts` lists both sides and you decide. Note this is a limit
        of the *evidence available*, not a rule against acting: a filled authoring
        log would settle which cells you edited, and `logs/` is empty today.

        Where the captured row's `source` is a value no fresh row uses,
        `source_proves_authored` says so per row — that narrows what happened and
        is still **not acted on**, because knowing who wrote a row does not settle
        which of two answers about the world is right. The captured copy stays on
        disk at `capture` for as long as you keep it.

        **What is put back is a narrow, provable set**: rows whose *subject* the
        fresh derivation does not mention at all AND whose `source` proves a human
        wrote them. Everything else is reported. In particular, for
        `resolution.csv` an online run that reaches Ensembl writes a
        `status="not_found"` row for an rsID it cannot resolve — so a
        `source="manual"` row for that same variant lands in `conflicts` rather
        than in `reapplied`, and putting it back beside the fetched row is your
        call. Where no link ran for that rsID no fresh row exists at all, and the
        manual row is reapplied.

        **Nothing is classified against a partial re-derivation.** If a source is
        unreachable, a pass does nothing, or the fresh table comes back empty, the
        captured bytes go back verbatim and `restored` says so — a table that was
        never filled would report every real row as one the source withdrew.
        `offline` refuses up front with nothing touched, for the same reason: a
        cache-relative refresh compares the file against a cache rather than
        against the source, which is a different question.

        **A crash cannot lose your rows.** The capture is written and hashed before
        the delete, and a run that dies mid-cycle leaves it findable: re-running
        continues from it rather than capturing over it. A sidecar with no verified
        capture is never deleted.

        `use` is required for `gene_metrics.csv` and `gwas_effects.csv`, whose
        passes read a licence-bearing source. `licensing.csv` cannot be refreshed
        at all — no pass derives it.
        """
        target = resolve_dir(spec_dir, settings)
        chosen = check_sidecar(sidecar)
        declared = check_use(chosen, use)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"
        subjects = subject_fields(chosen)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

        def report(**fields: Any) -> SidecarRefreshReport:
            base: dict[str, Any] = {
                "spec_dir": str(target),
                "sidecar": chosen.csv,
                "offline": eff_offline,
                "fact_fields": list(chosen.fact_fields),
                "subject_fields": list(subjects),
                "declared_use_applied_to": [
                    p.name for p in chosen.passes if p.reads_licence_bearing_source
                ],
                "note": _NOTE,
                "produced_by": schema_versions(),
            }
            base.update(fields)
            return SidecarRefreshReport(**base)

        if not subjects:
            return report(
                success=False,
                refused=(
                    f"{chosen.csv}'s row model marks none of its fact columns required, so this "
                    "release gives no derivable subject key and two rows cannot be told apart. "
                    "Nothing was touched. Refresh it by hand, or upgrade the toolchain."
                ),
            )

        if eff_offline:
            return report(
                success=False,
                refused=(
                    "Offline, so nothing was touched. A refresh exists to ask the SOURCE whether "
                    "it still says what your file says; offline it would compare it against a "
                    "local cache, and an empty re-derivation would read like 'upstream has "
                    "nothing'. Re-run with network access. (JMC_OFFLINE is a ceiling: a per-call "
                    "offline=false cannot lift it.)"
                ),
            )

        try:
            existing = resolve_sidecar(target, chosen.csv)
        except SidecarCollision as exc:
            return report(success=False, refused=str(exc))

        directory = capture_dir(settings, target, chosen.csv)
        pending = directory / PENDING_CSV
        state_file = directory / PENDING_STATE

        captured: Table | None = None
        capture_path: Path | None = None
        verified = False
        resumed = False
        read_from = existing

        # ------------------------------------------------------------------ #
        # 1. Capture, or resume from one a crashed run left behind.
        # ------------------------------------------------------------------ #
        if pending.is_file() and state_file.is_file():
            stored = json.loads(state_file.read_text(encoding="utf-8"))
            recorded = stored.get("read_from")
            read_from = Path(recorded) if recorded else existing
            same_bytes = bool(
                existing
                and existing.is_file()
                and existing.read_bytes() == pending.read_bytes()
            )
            captured, errors = read_table(pending, chosen)
            if captured is None:
                return report(
                    success=False,
                    capture=str(pending),
                    refused=(
                        f"A capture from a previous run is at {pending} and does not validate, so "
                        f"nothing here will act on it: {errors[0]}. Nothing was touched."
                    ),
                    findings=_as_errors(errors),
                )
            capture_path = pending
            verified = True
            if existing is not None and existing.is_file() and not same_bytes:
                # The pass already ran; the file on disk IS the fresh derivation.
                resumed = True
            elif existing is not None and existing.is_file():
                existing.unlink()
            else:
                resumed = True
        elif existing is not None and existing.is_file():
            captured, errors = read_table(existing, chosen)
            if captured is None:
                return report(
                    success=False,
                    read_from=str(existing),
                    refused=(
                        f"{chosen.csv} does not validate, so it cannot be classified — and a file "
                        f"this tool cannot classify is a file it will not delete. Nothing was "
                        f"touched. First error: {errors[0]}"
                    ),
                    findings=_as_errors(errors),
                )
            capture_path, verified = capture_now(
                directory,
                existing,
                {
                    "spec_dir": str(target),
                    "sidecar": chosen.csv,
                    "read_from": str(existing),
                    "captured_at": datetime.now(UTC).isoformat(),
                    "rows": len(captured.rows),
                    "fact_signature": chosen.signature(captured.rows),
                },
            )
            if not verified:
                return report(
                    success=False,
                    read_from=str(existing),
                    capture=str(capture_path),
                    capture_verified=False,
                    refused=(
                        f"The capture at {capture_path} did not read back byte-identical, so "
                        f"{chosen.csv} was NOT deleted and nothing was refreshed. A sidecar "
                        f"with no verified capture is never deleted."
                    ),
                )
            existing.unlink()

        if ctx:
            await ctx.info(f"Re-deriving {chosen.csv} in {target.name} (mode={mode})")
            await ctx.report_progress(progress=1, total=len(chosen.passes) + 2)

        # ------------------------------------------------------------------ #
        # 2. Re-derive. A partial derivation is never classified against.
        # ------------------------------------------------------------------ #
        ran: list[str] = []
        broke: str | None = None
        did_nothing: list[str] = []
        if not resumed or existing is None or not existing.is_file():
            for index, step in enumerate(chosen.passes, start=1):
                if ctx:
                    await ctx.report_progress(
                        progress=1 + index, total=len(chosen.passes) + 2
                    )
                # Narrow-first, always: since enricher 0.6.2 each `*Unavailable` is a
                # subclass of the type beside it, so a parent-first pair would catch
                # every outage in the parent arm and leave this one dead.
                try:
                    result = await run_sync(
                        lambda s=step: s.run(target, mode, eff_offline, declared, services)
                    )
                except step.unavailable as exc:
                    broke = (
                        f"{step.name}: the source never answered ({exc}). Nothing was classified "
                        f"— a table that was never filled would report every real row as one the "
                        f"source withdrew."
                    )
                    break
                except step.error as exc:
                    broke = (
                        f"{step.name} failed on something that is not an outage ({exc}). The "
                        f"source answered; the problem is not upstream's reachability."
                    )
                    break
                ran.append(step.name)
                if getattr(result, "skipped_offline", False):
                    did_nothing.append(step.name)

        fresh_path = sidecar_write_path(target, chosen.csv)
        fresh: Table | None = None
        fresh_errors: list[str] = []
        if broke is None and fresh_path.is_file():
            fresh, fresh_errors = read_table(fresh_path, chosen)

        if broke is None and did_nothing:
            broke = (
                f"These passes did nothing: {', '.join(did_nothing)}. A no-op derivation is not "
                f"evidence about the source."
            )
        if broke is None and fresh is None:
            broke = (
                f"The re-derived {chosen.csv} could not be read back"
                + (f": {fresh_errors[0]}" if fresh_errors else " — no file was written")
                + "."
            )
        elif broke is None and fresh is not None and not fresh.rows:
            broke = (
                f"The re-derivation produced an EMPTY {chosen.csv} while online. That is itself "
                f"worth reading — it can mean the source now publishes nothing for this module — "
                f"but it is not something to classify against. Compare against a run you trust "
                f"before concluding anything."
            )

        if broke is not None or fresh is None:
            restored = _restore(capture_path, read_from, fresh_path)
            if captured is not None:
                # Report where the copy IS, not the in-flight name it no longer has.
                capture_path = finalize_capture(directory, stamp)
            # The restoration sentence is appended AFTER the restore, from what it
            # actually returned. Baked into the message above it would claim a
            # restoration that had not happened yet — and would be plainly false on
            # a module that had no sidecar to begin with, where there is nothing to
            # put back and `restored` says so one field over.
            outcome = (
                " Your file was restored exactly as it was."
                if restored
                else " There was no prior file to restore, so nothing was lost and nothing "
                "was put back."
            )
            return report(
                success=False,
                read_from=str(read_from) if read_from else None,
                capture=str(capture_path) if capture_path else None,
                capture_verified=verified,
                resumed=resumed,
                restored=restored,
                refused=(broke or f"{chosen.csv} could not be read after the pass ran.") + outcome,
                next_step=(
                    "Nothing was refreshed and nothing was lost. Fix what the refusal names and "
                    "run this again; your copy is at `capture` either way."
                ),
                passes_run=ran,
                rows_before=len(captured.rows) if captured else None,
                fact_signature_before=chosen.signature(captured.rows) if captured else None,
                findings=_as_errors(fresh_errors),
            )

        # ------------------------------------------------------------------ #
        # 3. Classify.
        # ------------------------------------------------------------------ #
        fetched_sources = frozenset(
            str(s) for s in (getattr(row, "source", None) for row in fresh.rows) if s
        )
        available: frozenset[str] | None = fetched_sources or None
        fresh_rows = to_sidecar_rows(fresh, chosen, subjects, available)
        captured_rows = (
            to_sidecar_rows(captured, chosen, subjects, available) if captured else []
        )

        fresh_by_subject: dict[str, list[SidecarRow]] = {}
        for row in fresh_rows:
            fresh_by_subject.setdefault(row.subject, []).append(row)
        captured_by_subject: dict[str, list[SidecarRow]] = {}
        for row in captured_rows:
            captured_by_subject.setdefault(row.subject, []).append(row)

        only_capture: list[SidecarRow] = []
        conflicts: list[SidecarConflict] = []
        for subject in sorted(captured_by_subject):
            mine = captured_by_subject[subject]
            theirs = fresh_by_subject.get(subject)
            if theirs is None:
                only_capture.extend(mine)
                continue
            if {r.fact_key for r in mine} == {r.fact_key for r in theirs}:
                continue
            conflicts.append(
                SidecarConflict(
                    subject=subject,
                    captured=mine,
                    rederived=theirs,
                    differing_fact_fields=differing_fact_fields(
                        mine, theirs, chosen.fact_fields
                    ),
                    unresolvable=_UNRESOLVABLE,
                )
            )
        only_fresh = [
            row for row in fresh_rows if row.subject not in captured_by_subject
        ]

        reapplied = [row for row in only_capture if row.source_proves_authored]
        withheld = [row for row in only_capture if not row.source_proves_authored]

        # ------------------------------------------------------------------ #
        # 4. Reapply the provable set, and put the file back where it lived.
        # ------------------------------------------------------------------ #
        if reapplied:
            write_merged(fresh_path, fresh, [row.cells for row in reapplied])
        final_path = _relocate(fresh_path, read_from)
        after, after_errors = read_table(final_path, chosen)

        before_signature = chosen.signature(captured.rows) if captured else None
        if after is None:
            # The capture is deliberately NOT finalized here: the file on disk does
            # not validate, so the audit copy is the only readable version of the
            # table and its in-flight name is what a re-run looks for.
            return report(
                success=False,
                read_from=str(read_from) if read_from else None,
                capture=str(capture_path) if capture_path else None,
                capture_verified=verified,
                resumed=resumed,
                passes_run=ran,
                rows_before=len(captured.rows) if captured else None,
                rows_rederived=len(fresh.rows),
                fact_signature_before=before_signature,
                next_step=(
                    "Do not compile this. Read the finding, then either repair the file or put "
                    "your captured copy back — its path is in `capture` and it was left in place."
                ),
                refused=(
                    f"{final_path} does not validate after the refresh, so nothing about it is "
                    f"reported as a finding about your rows. Your captured copy is intact at "
                    f"{capture_path} and this run's capture was left in place, so re-running "
                    f"continues from it. First error: "
                    f"{after_errors[0] if after_errors else 'unreadable'}"
                ),
                findings=_as_errors(after_errors),
            )
        after_signature = chosen.signature(after.rows)
        moved: bool | None = None
        if before_signature is not None:
            moved = before_signature != after_signature

        if captured is not None:
            capture_path = finalize_capture(directory, stamp)

        warnings = aggregate(
            [
                (
                    len(conflicts),
                    "subject(s) are described by both copies with differing facts and were LEFT "
                    "ALONE: an author's cell edit and an upstream revision are indistinguishable "
                    "from two data points, so this is yours to decide.",
                ),
                (
                    len(withheld),
                    "row(s) present only in your copy were NOT put back, because their `source` is "
                    "a value the fresh derivation also writes — so nothing proves a human wrote "
                    "them rather than the source having withdrawn them. They are in the capture.",
                ),
                (
                    len(only_fresh),
                    "row(s) are on subjects your copy did not have. The source added these.",
                ),
            ]
        )
        if available is None:
            warnings.append(
                "The re-derived table names no `source` at all, so the authorship question could "
                "not be put on any row and nothing was put back. `source_proves_authored` is null "
                "rather than false throughout — a question that could not be asked is not a "
                "question answered no."
            )
        if read_from is not None and final_path != fresh_path:
            warnings.append(
                f"The pass wrote to {fresh_path.name} at the spec root because the file it would "
                f"have followed was deleted; it has been moved back to {final_path} so this "
                f"refresh does not migrate the module's layout."
            )
        truncated = any(
            len(bucket) > MAX_LISTED
            for bucket in (only_capture, only_fresh, conflicts, reapplied, withheld)
        )
        if truncated:
            warnings.append(
                f"Row listings are capped at {MAX_LISTED} each. Every COUNT above is complete; "
                f"only the listings are cut."
            )

        if ctx:
            await ctx.report_progress(
                progress=len(chosen.passes) + 2, total=len(chosen.passes) + 2
            )
        return report(
            success=True,
            read_from=str(read_from) if read_from else None,
            capture=str(capture_path) if capture_path else None,
            capture_verified=verified,
            resumed=resumed,
            passes_run=ran,
            fact_signature_before=before_signature,
            fact_signature_after=after_signature,
            signature_moved=moved,
            rows_before=len(captured.rows) if captured else None,
            rows_rederived=len(fresh.rows),
            rows_after=len(after.rows),
            only_in_capture=only_capture[:MAX_LISTED],
            only_in_rederived=only_fresh[:MAX_LISTED],
            conflicts=conflicts[:MAX_LISTED],
            reapplied=reapplied[:MAX_LISTED],
            withheld=withheld[:MAX_LISTED],
            listing_truncated=truncated,
            findings=_as_errors(after_errors),
            warnings=warnings,
            next_step=_next_step(moved, conflicts, reapplied, captured is None),
        )


# --------------------------------------------------------------------------- #
# Helpers used by the tool body
# --------------------------------------------------------------------------- #
_UNRESOLVABLE = (
    "Left exactly as both sides wrote it. A fetched row whose facts differ from your captured "
    "copy is either a cell you edited or a revision the source published, and two data points "
    "cannot tell those apart — so nothing here prefers a side, merges them or guesses. Read both "
    "lists and decide; your copy is in the capture. Where `source_proves_authored` is true on a "
    "captured row it proves a human wrote that row, which narrows what happened and still does "
    "not settle which of the two answers about the world is right."
)

_NOTE = (
    "Row identity here is DERIVED: `fact_fields` is the format's own fact tuple and "
    "`subject_fields` is that tuple narrowed to the columns the row model marks required. Each "
    "pass's real merge key is a local expression inside the pass and is published nowhere, so on "
    "two of the seven tables the subject used here is coarser than the real one — which reports "
    "MORE rows as conflicting and therefore repairs fewer. `fact_signature_*` comes from the same "
    "function the manifest publishes, so it is comparable with what a compile recorded. It is a "
    "content identity and not a correctness gate: an unmoved signature means the source still "
    "says what your file said, never that the file is right. `artifact.digest` may move on the "
    "next compile for a reason that is not a content change — reapplied rows are appended, so "
    "sidecar row order can differ while every fact is the same."
)


def _as_errors(messages: Sequence[str]) -> list[LintFinding]:
    """Upstream's parse errors as findings, `level` kept at what they are."""
    return [LintFinding(level="error", message=str(m)) for m in messages]


def _restore(capture: Path | None, read_from: Path | None, fresh_path: Path) -> bool:
    """Put the captured bytes back where the file was. Returns whether it happened.

    Reads from the **capture**, never from the original: by this point the original
    is gone, which is the whole reason the capture is written and hashed first.

    Anything the pass managed to write is removed first: leaving a half-derived
    file beside the restored one is two claims about the same table, which is the
    collision `layout.resolve_sidecar` refuses for exactly this reason.
    """
    if capture is None or read_from is None or not capture.is_file():
        return False
    if fresh_path.is_file() and fresh_path != read_from:
        fresh_path.unlink()
    read_from.parent.mkdir(parents=True, exist_ok=True)
    read_from.write_bytes(capture.read_bytes())
    return True


def _relocate(fresh_path: Path, read_from: Path | None) -> Path:
    """Move the refreshed file back to where the module kept it.

    With the original deleted, `sidecar_write_path` creates the preferred spelling
    at the spec root — correct for a fresh file and wrong here, because a module
    that keeps its sidecars under `derived/`, or under the deprecated spelling,
    would have its layout migrated by a refresh. Write to the file you read.
    """
    if read_from is None or read_from == fresh_path or not fresh_path.is_file():
        return fresh_path
    read_from.parent.mkdir(parents=True, exist_ok=True)
    fresh_path.replace(read_from)
    return read_from


def _next_step(
    moved: bool | None,
    conflicts: Sequence[SidecarConflict],
    reapplied: Sequence[SidecarRow],
    fresh_start: bool,
) -> str:
    """What to do with this result, in the order it matters."""
    if fresh_start:
        return (
            "There was no sidecar to capture, so this was a plain derivation and nothing was at "
            "risk. Commit the file; from here a refresh has something to compare against."
        )
    parts: list[str] = []
    if conflicts:
        parts.append(
            f"Read the {len(conflicts)} conflict(s) first — they are the only thing here that "
            "needs a decision, and nothing was changed on either side."
        )
    if moved is True:
        parts.append(
            "The fact signature MOVED. If nothing was reapplied and nothing conflicts, that is "
            "the source having changed its answer, which is the whole point of running this."
        )
    elif moved is False:
        parts.append(
            "The fact signature did not move: the source still says exactly what your file said."
        )
    if reapplied:
        parts.append(
            f"{len(reapplied)} row(s) of yours were appended back; they are at the end of the "
            "file rather than in the pass's sort order."
        )
    parts.append("Then re-run validate_module and compile_module — the sidecar changed.")
    return " ".join(parts)


#: The public roster this module must cover, for the test that pins it. Derived
#: from the registry's own recognised set rather than restated: an eighth fact
#: table then fails our suite instead of being silently unrefreshable.
REFRESHABLE_ROSTER = frozenset(FACT_CSVS) | {RESOLUTION_CSV}

#: The one member of that roster with no producer, so its absence from `ROSTER` is
#: a decision rather than an omission. Read through `preferred_spelling` so the
#: 0.6 rename is followed rather than restated.
UNPRODUCED = {SOURCES_CSV, preferred_spelling(SOURCES_CSV)}
