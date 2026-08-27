"""Drafting from a published source, and the sidecar fact passes.

These are the tools that close the hole in the middle of the taught workflow.
The skill teaches `scaffold -> draft -> curate -> enrich -> check -> compile`,
and until now `draft` was CLI-only, so an agent following it left the tool
surface at step 2 and came back at step 4.

Two rules run through everything here.

**`use` is required and never defaulted.** Upstream defaults
`declared_use="unstated"`; inheriting that default would silently skip
licence-bearing sources, and defaulting to anything else would assert a licence
position the caller never took. So it is a required argument on every drafter.

**A licence refusal is not a failure.** When `declared_use` does not satisfy a
source's terms, upstream fetches nothing and returns `skipped=True` with the
reason — an acquisition-time refusal, because taking the data is what accepts the
terms. That arrives as a first-class `skipped` field rather than `success=False`,
because a failure invites retrying with a different `use`, which is exactly
fabricating a licence position to make a tool work.

`draft_from_clinvar` and `enrich_module` are steps 2 and 6 of the taught order.
They are the only two tools that fetch and then write into a spec directory,
which is why they share a module with the bulk passes below.

`register_bulk_passes` holds the two PGx drafters and the three fact passes. They
were the extended tier until 0.21.0, on a cost argument that is still true and is
now stated where the caller reads it rather than enforced by hiding the tool: a
fact pass rewrites many rows at once instead of answering about the one thing you
named, and `enrich_gwas_effects` is the sharpest version — its budget is `1 + 2N`
requests for a variant with N published associations, measured at **382 requests
for one real module**, sized by how much has been published rather than by
anything the caller named. Say that in the docstring; do not spend a session's
whole task on it, which is what the flag did.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_enricher.clingen import (
    ClinGenError,
    ClinGenUnavailable,
    enrich_dosage_sensitivity,
)
from just_dna_enricher.clinpgx_draft import ClinPgxEnrichmentError, draft_pharm_variants
from just_dna_enricher.clinvar_draft import ClinVarDraftError, draft_gene_panel
from just_dna_enricher.cpic import CpicError
from just_dna_enricher.enrich import EnrichmentError, enrich
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
from just_dna_enricher.gwas import GwasError, enrich_gwas
from just_dna_enricher.literature import LiteratureEnrichmentError, enrich_literature
from just_dna_enricher.pgx_draft import draft_gene
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    DraftedTable,
    DraftResult,
    EnrichReport,
    FactPassReport,
    GwasReport,
    LiteratureReport,
)
from just_module_creator.net import NetworkServices
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import offline_for, resolve_dir

log = get_logger()

VALID_USE = ("unstated", "non_commercial", "commercial")

_REGENERATE_NOTE = (
    "An existing sidecar is authoritative and merged, never clobbered. To "
    "regenerate resolution.csv after changing the spec you must DELETE it first, "
    "or stale rows persist silently. Moving it aside and re-enriching is also the "
    "only way to ask whether an injected table still agrees with the sources."
)

_REGENERATE = (
    "An existing sidecar is authoritative and MERGED, never clobbered. To regenerate "
    "it after changing the spec you must DELETE the file first, or stale rows persist "
    "silently."
)

_FACT_PASSES = ("frequencies", "gene_metrics", "dosage")

#: `gwas_effects.csv` is the one sidecar an author is actively tempted to mine for an
#: authored cell, so the regeneration rule travels with the refusal rather than only in
#: the docstring above the call.
_GWAS_NOTE = (
    _REGENERATE
    + " These effects are NOT weights and no tool writes one from them: a published beta "
    "belongs to its own study's scale, many of them name no effect allele at all, and "
    "`weight` stays your model of the finding. The two columns sit side by side and a "
    "consumer chooses between them wholesale."
)

#: The Catalog's own marker for a variant it published nothing about, on `GwasEffectRow.status`.
#: Upstream exports no constant for that vocabulary, so the literal is owned here — and it has to
#: be, because a `not_found` row's null `effect_allele` means "no association exists" while a
#: recorded association's null means "the study never established which allele carries the
#: effect", and counting them together would report the first as if it were the second.
_GWAS_NOT_FOUND = "not_found"


#: Upstream words its errors for its own CLI, so they name flags these tools do
#: not have. The message is kept **verbatim** — rewriting it would corrupt the
#: CLI commands it legitimately contains, and upstream's wording is often the
#: most accurate thing available — with a translation appended instead.
_FLAG_TO_ARG = {
    "--offline": "offline=false",
    "--snapshot": "snapshot=<path>",
    "--use": "use=<unstated|non_commercial|commercial>",
}


def _translate(message: str) -> str:
    """Upstream's message, plus how its CLI flags map onto this tool's arguments."""
    mentioned = [f"{flag} -> {arg}" for flag, arg in _FLAG_TO_ARG.items() if flag in message]
    if not mentioned:
        return message
    return (
        f"{message}\n\nThat message is the enricher's, written for its CLI. On this tool the "
        f"equivalent arguments are: {'; '.join(mentioned)}."
    )


# Parents only, in ONE tuple. Since enricher 0.6.2 each pass raises its own type with
# unavailability as a *subclass* (`FrequencyUnavailable(FrequencyEnrichmentError)` and
# five siblings), so listing the parents catches strictly more than it used to and
# nothing less. The shape matters: two separate `except` arms with the parent first
# would send every outage into the parent arm and leave the outage arm dead, silently.
# `tests/test_passes.py::test_no_except_arm_is_shadowed_by_an_earlier_one` walks this
# module's AST for exactly that, because it is the failure that raises nothing.
_SOURCE_ERRORS = (
    ClinVarDraftError,
    CpicError,
    ClinPgxEnrichmentError,
    FrequencyEnrichmentError,
    GeneMetricsEnrichmentError,
    ClinGenError,
)

# Narrow-first, and only ever used where the two verdicts are reported differently.
_PASS_UNAVAILABLE = {
    "frequencies": FrequencyUnavailable,
    "gene_metrics": GeneMetricsUnavailable,
    "dosage": ClinGenUnavailable,
}
_PASS_ERROR = {
    "frequencies": FrequencyEnrichmentError,
    "gene_metrics": GeneMetricsEnrichmentError,
    "dosage": ClinGenError,
}


async def _guard(call):
    """Run an upstream pass, restating a source failure in our own vocabulary.

    These really are errors — there is no data source, so there is nothing to
    report — but upstream words them for its CLI. Raising the message verbatim
    sends an agent looking for a `--snapshot` flag that no tool here has.
    """
    try:
        return await run_sync(call)
    except _SOURCE_ERRORS as exc:
        raise ToolError(_translate(str(exc))) from exc


def _check_use(use: str) -> str:
    """Validate the licence declaration. Never defaulted, never guessed."""
    normalized = use.strip().replace("-", "_").lower()
    if normalized not in VALID_USE:
        raise ToolError(
            f"`use` must be one of {', '.join(VALID_USE)} — got {use!r}. This is your licence "
            "position and there is no default: 'unstated' silently skips licence-bearing "
            "sources, and anything else asserts a position you may not hold."
        )
    return normalized


def _tables(result: Any, *, written: bool) -> list[DraftedTable]:
    """Project upstream's per-CSV reports, keeping all four row statuses.

    `differs` is report-never-repair: the source disagrees with a row you
    authored, and upstream leaves yours alone. Collapsing the statuses into one
    count would hide exactly the rows worth looking at.
    """
    out: list[DraftedTable] = []
    for report in getattr(result, "reports", []) or []:
        differences = [
            f"{r.key}: "
            + ", ".join(
                f"{col} {ours!r} vs source {theirs!r}"
                for col, (ours, theirs) in r.differences.items()
            )
            for r in report.differs
        ]
        out.append(
            DraftedTable(
                csv=report.csv_name,
                added=len(report.added),
                already_present=len(report.already_present),
                differs=len(report.differs),
                invalid=len(report.invalid),
                differences=differences,
                shifted=len(getattr(report, "shifted", []) or []),
                written=written and bool(report.written),
            )
        )
    return out


def _draft_result(
    result: Any, *, spec_dir: Path, source: str, use: str, dry_run: bool
) -> DraftResult:
    skipped = bool(getattr(result, "skipped", False))
    tables = _tables(result, written=not dry_run)
    if skipped:
        next_step = (
            "Nothing was fetched: your declared use does not satisfy this source's terms. "
            "That is the gate working. Do NOT re-run with a different `use` to get past it — "
            "either you may use the data that way or you may not."
        )
    elif dry_run:
        next_step = "Preview only, nothing written. Re-run with dry_run=false to apply."
    else:
        next_step = (
            "Curate the stubbed cells — genotype, state, weight, conclusion are yours — then "
            "lint_rows before validating. Rows under `differs` were left as you wrote them and "
            "are the ones worth reading."
        )
    return DraftResult(
        spec_dir=str(spec_dir),
        source=source,
        declared_use=use,
        skipped=skipped,
        tables=tables,
        warnings=list(getattr(result, "warnings", []) or []),
        dry_run=dry_run,
        next_step=next_step,
    )


def register_passes(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the always-on drafting tool (ClinVar -> variants + studies)."""

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from ClinVar",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def draft_from_clinvar(
        spec_dir: str,
        genes: list[str],
        use: str,
        snapshot: str | None = None,
        clin_sig: list[str] | None = None,
        min_review_stars: int = 2,
        max_citations: int = 3,
        dry_run: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft `variants.csv` and `studies.csv` for one or more genes from ClinVar.

        This is step 2 of the workflow — the one place an author used to have to
        leave the tool surface. Re-runnable and additive: rows already in the files
        are left exactly as they are.

        **If this module was drafted before enricher 0.6.3, read the superseded-row
        warning before you do anything else.** Below 0.6.3 the drafter keyed a site
        on `ref`, so an ordinary ClinVar dup/del mirror pair collapsed onto one row
        and the second record was dropped silently (upstream S41). Re-running here
        recovers every dropped record — but "additive" cuts both ways: the collapsed
        rsid-only rows are not retracted, so the module ends up asserting both the
        right answer and the wrong one for the same locus. Measured on one gene: 0
        records still missing, 31 stale identities left behind.

        Since enricher 0.6.4 this run **names them** — *"N row(s) already in
        variants.csv identify by rsID alone … this run writes those rsIDs with their
        full coordinate"* — counted, with examples. Nothing deletes them, and that is
        deliberate: by re-draft time a drafted row is authored material and yours may
        have been curated since, so removing it is your call. Delete each once its
        records are covered by the coordinate rows.

        **The warning is the safety net, not the plan.** A file-level check cannot
        find these rows — a coordinate row carries no `rsid`, so no column separates
        a stale row from a legitimate rsid-only one, and only the drafting run knows
        which rsIDs it is deliberately writing by coordinate. Drafting into a
        **fresh directory** and reconciling against it stays the cleaner
        remediation; the notice exists for the author who re-ran in place.

        **`use` is required.** Pass `unstated`, `non_commercial` or `commercial`.
        There is no default because both possible defaults are wrong: `unstated`
        would silently skip licence-bearing sources, and anything else asserts a
        position you may not hold. If `skipped=true` comes back, the terms were
        not satisfied and nothing was fetched — **that is the gate working, and
        re-running with a different `use` to get past it is fabricating a licence
        position.**

        `max_citations` drafts study rows from ClinVar's literature links, which is
        what makes the panel compilable — a variant row needs grounding evidence.
        `min_review_stars` defaults to 2 (multiple submitters, no conflicts).

        Read `differs` in the result: those are rows where ClinVar disagrees with
        something you already authored. They are **left unchanged** — rewriting
        your value would destroy the evidence of the disagreement, and only you
        know which side is right.

        Drafted rows carry `<<REPLACE>>` in the cells only a human can decide.
        That placeholder makes every loader refuse the file, `enrich_module`
        included, so curate before you enrich.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        if not genes:
            raise ToolError("Provide at least one gene symbol.")

        if ctx:
            await ctx.info(f"Drafting {', '.join(genes)} from ClinVar into {target.name}")
            await ctx.report_progress(progress=1, total=2)

        # `clin_sig` is omitted rather than defaulted when unset: upstream owns
        # that default (likely_pathogenic + pathogenic) and restating it here
        # would be hardcoding a schema fact that can move underneath us.
        extra: dict[str, Any] = {"clin_sig": frozenset(clin_sig)} if clin_sig else {}
        result = await _guard(
            lambda: draft_gene_panel(
                target,
                genes,
                snapshot=Path(snapshot).expanduser() if snapshot else None,
                min_review_stars=min_review_stars,
                max_citations=max_citations,
                declared_use=declared,
                offline=eff_offline,
                dry_run=dry_run,
                **extra,
            )
        )
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(
            result, spec_dir=target, source="clinvar", use=declared, dry_run=dry_run
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Enrich a spec (resolve coordinates)",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def enrich_module(
        spec_dir: str,
        strict: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> EnrichReport:
        """Resolve rsIDs to coordinates and mint VRS ids, writing resolution.csv.

        The only step that fetches, and the only thing that can catch the mistake
        no offline gate can: it compares your authored `ref` against the actual
        genome and reports `ref mismatch: N row(s) — coordinate shifted 1 base`.
        **Read that line as being about `start`, not `ref`** — it is what
        subtracting one from a VCF position produces. It is a floor, not a total:
        only rows whose neighbouring base differs from `ref` are visible.

        **It blocks, and on a large module it blocks for a long time.** It is
        declared task-capable, but that only makes tasks *optional*: a client that
        sends no task metadata — and the usual ones do not — gets an ordinary
        synchronous call, so there is no task id and nothing to poll. This said
        otherwise until 2026-08-22, and a run planning around the promise had
        nothing to plan with. Progress is reported once before the work and once
        after, never during, so a client idle timeout is what you will hit rather
        than a duration one. Measured: 32 variants return in seconds; 330 and 474
        were both killed client-side at 1800s.

        **Nothing is written until the very end.** The single `resolution.csv` write
        happens after every network link, so a run that is interrupted at any point
        persists nothing — thirty minutes of successful resolution is discarded, and
        merge-not-clobber does not save you because there was no partial write to
        merge. Worse, an interruption is *client-side only*: the work continues here
        and still writes when it finishes, so a call you were told had failed can
        overwrite this file later, after a second call has already reported success
        against it. If a call timed out, count the rows in `resolution.csv` against
        the authored subject count before trusting anything downstream, and treat a
        `success` issued while an aborted call may still be running as unverified.

        Curate before you enrich. A `<<REPLACE>>` anywhere makes every loader
        refuse the file, this one included — deliberately, since forward
        resolution is allele-aware and a placeholder genotype would skip the
        allele filter on exactly the rsIDs that need it.

        `offline=true` restricts to local caches, where the ref check does not
        run at all. A check that could not run is not a check that passed.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"

        if ctx:
            await ctx.info(
                f"Enriching {target.name} (mode={mode}, "
                f"{'cache-only' if eff_offline else 'network'})"
            )
            await ctx.report_progress(progress=1, total=3)

        started = _ENRICHMENTS_IN_FLIGHT.get(target)
        if started is not None:
            raise ToolError(
                f"An enrichment of {target} started at {started} and is still running. "
                "It rewrites resolution.csv when it finishes, so anything this call wrote "
                "would be overwritten without warning — which is why this refuses instead "
                "of succeeding. A worker thread cannot be cancelled: if the earlier call "
                "was aborted by a client timeout, the work did not stop, and waiting for "
                "it is the only safe option. When it lands, count resolution.csv against "
                "the authored subject count before trusting it."
            )

        _ENRICHMENTS_IN_FLIGHT[target] = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            # Released in `finally` rather than on request cancellation, and that ordering
            # is the point: `run_sync` defaults to `abandon_on_cancel=False`, so the await
            # does not unwind until the thread returns. The claim therefore outlives an
            # aborted request for exactly as long as the write it is protecting against.
            result = await run_sync(
                lambda: enrich(target, mode=mode, offline=eff_offline, write=True)
            )
        except EnrichmentError as exc:
            return EnrichReport(
                success=False,
                spec_dir=str(target),
                mode=mode,
                offline=eff_offline,
                resolved=0,
                unresolved=[],
                sources=[],
                ref_mismatches=[],
                clin_sig_conflicts=[],
                stale_rsids=[],
                warnings=[str(exc)],
                note=_REGENERATE_NOTE,
            )
        finally:
            _ENRICHMENTS_IN_FLIGHT.pop(target, None)

        if ctx:
            await ctx.report_progress(progress=3, total=3)

        vrs = getattr(result, "vrs", None)
        mismatches = [str(m) for m in getattr(result, "ref_mismatches", []) or []]
        warnings: list[str] = []
        if eff_offline and not mismatches:
            warnings.append(
                "No ref mismatches reported — but this ran offline, where the check "
                "needs sequence access and therefore did not run at all."
            )
        return EnrichReport(
            success=True,
            spec_dir=str(target),
            mode=mode,
            offline=eff_offline,
            resolved=len(getattr(result, "rows", []) or []),
            unresolved=[str(u) for u in getattr(result, "unresolved", []) or []],
            sources=[str(s) for s in getattr(result, "sources", []) or []],
            ref_mismatches=mismatches,
            clin_sig_conflicts=[str(c) for c in getattr(result, "clin_sig_conflicts", []) or []],
            clin_sig_not_checked=getattr(result, "clin_sig_not_checked", None),
            stale_rsids=[str(s) for s in getattr(result, "stale_rsids", []) or []],
            vrs_minted=getattr(vrs, "minted", None) if vrs else None,
            warnings=warnings,
            note=_REGENERATE_NOTE,
        )


#: Spec directories with an enrichment in flight, mapped to when it started (UTC).
#:
#: `enrich_module` dispatches the enricher into a worker thread, and a worker thread
#: cannot be interrupted — so a client that gives up on the request leaves the work
#: running, and it still rewrites `resolution.csv` when it finishes. That produced a
#: measured data-integrity failure: an aborted 330-variant run was still alive when the
#: author restored the published sidecar and re-enriched; the second call read the
#: restored file, reported `resolved: 330` correctly, and the first call then wrote its
#: partial result over it, leaving 162 distinct rsIDs. The module validated, closed and
#: compiled green, because every count in it was internally consistent.
#:
#: In-process and per-server, which is the honest limit: it cannot see an enrichment
#: started by a different process, and there is no lockfile anywhere in this tree or
#: upstream's. What it does stop is the sequence that actually happened, where both
#: calls came from one session.
_ENRICHMENTS_IN_FLIGHT: dict[Path, str] = {}


def register_bulk_passes(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the PGx drafters, the sidecar fact passes and the GWAS Catalog pass."""

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from CPIC",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def draft_from_cpic(
        spec_dir: str,
        gene: str,
        use: str,
        drugs: list[str] | None = None,
        alleles: list[str] | None = None,
        population: str | None = None,
        dry_run: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft `haplotypes.csv`, `allele_function.csv` and `diplotypes.csv` from CPIC.

        **`use` is required** — see `draft_from_clinvar` for why, and note every PGx
        upstream (ClinPGx, CPIC, PharmVar) is CC BY-SA **plus a no-sale clause**, so
        none of them is sellable. Do not read a bare "CC BY-SA" as permission.

        `population` **filters, it does not decide.** Every clinical context is
        drafted and kept apart by `clinical_context`, so the consumer picks at
        query time — the right owner, since which indication a patient is being
        treated for is knowable then and not at authoring time. Leave it unset to
        get them all. An unrecognised value is an error listing what CPIC
        publishes, so a typo cannot quietly draft nothing.

        **Budget: a whole-source draft, not one question.** It pulls every allele
        CPIC publishes for the gene and writes three tables from it, so the work
        is sized by what has been published rather than by anything you named.

        `alleles` is how you keep a large star-allele gene tractable: *n* alleles
        is *n(n+1)/2* diplotypes, and unfiltered CYP2D6 is 16,290 rows. Your real
        bound is the allele set your caller emits. The filter covers all three
        tables and `*1` is always kept.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)

        if ctx:
            await ctx.info(f"Drafting {gene} from CPIC into {target.name}")
            await ctx.report_progress(progress=1, total=2)

        result = await _guard(
            lambda: draft_gene(
                target,
                gene,
                drugs=tuple(drugs or ()),
                alleles=tuple(alleles or ()),
                population=population,
                declared_use=declared,
                dry_run=dry_run,
                offline=eff_offline,
            )
        )
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(result, spec_dir=target, source="cpic", use=declared, dry_run=dry_run)

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from ClinPGx",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def draft_from_clinpgx(
        spec_dir: str,
        snapshot: str,
        use: str,
        genes: list[str] | None = None,
        drugs: list[str] | None = None,
        min_evidence_level: str | None = None,
        dry_run: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft `pharm_variants.csv` from a built ClinPGx snapshot.

        `snapshot` is **required** — unlike the other drafters this one has no live
        API path, and the snapshot is built with the CLI
        (`just-dna-enricher clinpgx build`). **`use` is required** too; ClinPGx
        carries a no-sale clause.

        A `pharm_variants` module carries **no** `variants.csv` and needs no
        `studies.csv`. Author the rsID rather than a coordinate: resolution is
        applied to `weights.parquet` only, so these rows arrive with null
        `chrom`/`start` in the artifact even when `resolution.csv` covers the
        variant, and a consumer joins them on `rsid` + `genotype`.

        **A module drafted before enricher 0.6.3 is missing rows here too, and
        unlike `draft_from_clinvar` a plain re-run is the whole repair.** Below
        0.6.3 the genotype gate was narrower than the schema it writes into: it
        took only the doubled single-base form, so `CTT/CTT` — already separated
        by the source — and the bare haploid spelling ClinPGx uses for mtDNA were
        declined, costing CFTR F508del and every MT-RNR1 annotation (upstream
        S44). Those rows were **skipped**, not written under a wrong identity, so
        **Budget: a whole-source draft.** Every pharmacogenomic variant the
        snapshot holds for the gene, sized by what has been published rather than
        by anything you named — and building the snapshot itself is the larger
        cost, paid once, outside this tool.

        nothing stale is left to retract and re-running converges on exactly what
        a fresh draft produces — measured at 0 stale and 0 missing keys. That is
        the difference from the ClinVar case, where the identity itself moved.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        snapshot_path = Path(snapshot).expanduser()
        if not snapshot_path.is_dir():
            raise ToolError(
                f"{snapshot_path} is not a directory. Build one first: "
                "`just-dna-enricher clinpgx build --out <dir>`."
            )

        if ctx:
            await ctx.report_progress(progress=1, total=2)
        result = await _guard(
            lambda: draft_pharm_variants(
                target,
                snapshot=snapshot_path,
                genes=tuple(genes or ()),
                drugs=tuple(drugs or ()),
                min_evidence_level=min_evidence_level,
                declared_use=declared,
                dry_run=dry_run,
            )
        )
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(
            result, spec_dir=target, source="clinpgx", use=declared, dry_run=dry_run
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Fill literature.csv",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def enrich_literature_pass(
        spec_dir: str,
        strict: bool = False,
        check_fulltext: bool = True,
        check_doi: bool = True,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> LiteratureReport:
        """Resolve every citation in `studies.csv` into `literature.csv`.

        Checks that each PMID exists (PubMed), that each authored DOI exists
        (Crossref), and — where the text is retrievable — that each
        `provenance_quote` really appears in the paper.

        **`quotes_unchecked` is not a failure count.** It means nothing was
        retrievable to check against, and an abstract miss is not a verdict: the
        claim may still be in the full paper.

        **`titles_as_quotes` is the opposite reading and the more dangerous one.**
        A `provenance_quote` that is the article's own title passes the quote
        check every time — a title is inside its own fulltext — so the row counts
        as covered while witnessing nothing about the claim. Ask of any green
        check whether it could have failed.

        **`doi_conflicts` are reported, never rewritten.** Your authored DOI and
        the registry's disagree for that PMID, which means one of the two
        citations is the wrong paper — and only you know which.

        **Budget: one or more requests per citation in the module**, so the cost
        rises with the corpus you have cited rather than with anything named in
        this call. A module with hundreds of studies is a long run.

        `offline=true` makes this a **no-op**: there is no offline literature
        snapshot and there will not be one. Once `literature.csv` is written it
        *is* the pin, and every later compile reads it rather than the network.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"

        if ctx:
            await ctx.info(f"Resolving citations for {target.name}")
            await ctx.report_progress(progress=1, total=2)

        try:
            result = await run_sync(
                lambda: enrich_literature(
                    target,
                    mode=mode,
                    offline=eff_offline,
                    check_fulltext=check_fulltext,
                    check_doi=check_doi,
                    write=True,
                    eutils=services.lookup_clients.eutils,
                    europepmc=services.lookup_clients.europepmc,
                    crossref=services.lookup_clients.crossref,
                )
            )
        except LiteratureEnrichmentError as exc:
            return LiteratureReport(
                success=False,
                spec_dir=str(target),
                mode=mode,
                rows=0,
                warnings=[str(exc)],
                note=_REGENERATE,
            )

        if ctx:
            await ctx.report_progress(progress=2, total=2)
        skipped = bool(getattr(result, "skipped_offline", False))
        warnings: list[str] = []
        if skipped:
            warnings.append(
                "Offline: this pass did NOTHING. Any existing literature.csv is unchanged and "
                "remains the pin; a missing one is still missing."
            )
        if result.missing:
            warnings.append(
                f"{len(result.missing)} citation(s) did not resolve — do not ship these."
            )
        titles_as_quotes = [str(pmid) for pmid in getattr(result, "titles_as_quotes", ())]
        if titles_as_quotes:
            warnings.append(
                f"{len(titles_as_quotes)} row(s) quote the article's own TITLE. That quote is "
                "always inside its own fulltext, so the check cannot fail on it and the coverage "
                "figure above witnesses nothing: "
                f"{', '.join(titles_as_quotes[:5])}"
                f"{' …' if len(titles_as_quotes) > 5 else ''}. Replace each with a passage that "
                "states the finding, and record who located it in `curator`."
            )
        return LiteratureReport(
            success=True,
            spec_dir=str(target),
            mode=mode,
            rows=len(result.rows),
            missing=list(result.missing),
            doi_conflicts=[str(c) for c in result.doi_conflicts],
            quotes_authored=result.quotes_authored,
            quotes_found=result.quotes_found,
            quotes_unchecked=result.quotes_unchecked,
            titles_as_quotes=titles_as_quotes,
            coverage=str(getattr(result, "coverage", "") or ""),
            skipped_offline=skipped,
            warnings=warnings,
            note=_REGENERATE,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Run the sidecar fact passes",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def enrich_facts(
        spec_dir: str,
        passes: list[str] | None = None,
        use: str = "unstated",
        strict: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> FactPassReport:
        """Fill the sidecars the compile gate reads: frequencies, constraint, dosage.

        `passes` defaults to all three. They share one shape — spec in, sidecar
        out — which is why they are one tool; `dosage` writes onto
        `gene_metrics.csv` rather than a file of its own, so it pairs naturally
        with `gene_metrics`.

        **`use` applies only to `dosage`**, the one pass reading a licence-bearing
        source (ClinGen). The result says so in `declared_use_applied_to` rather
        than letting the argument look universally meaningful.

        gnomAD paces at roughly one batch per six seconds, so this is a background
        task. An existing sidecar is merged, never clobbered — delete the file to
        regenerate it.

        **Budget: every subject in the module, three sources deep.** A fact pass
        rewrites many rows at once instead of answering about the one thing you
        named, so its request count is set by the module's size. That is a run to
        plan, not a lookup to fire off.

        `missing` is not proof of absence: a gene gnomAD has no constraint entry
        for and a gene the pass could not reach look the same in the file, which
        is why the offline flag is reported separately.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"
        wanted = list(passes) if passes else list(_FACT_PASSES)
        unknown = [p for p in wanted if p not in _FACT_PASSES]
        if unknown:
            raise ToolError(
                f"Unknown pass(es): {', '.join(unknown)}. Valid: {', '.join(_FACT_PASSES)}."
            )
        declared = _check_use(use) if "dosage" in wanted else use

        rows: dict[str, int] = {}
        covered: dict[str, list[str]] = {}
        missing: dict[str, list[str]] = {}
        skipped: list[str] = []
        unreachable: dict[str, str] = {}
        failed: dict[str, str] = {}
        warnings: list[str] = []
        ran: list[str] = []

        for index, name in enumerate(wanted, start=1):
            if ctx:
                await ctx.info(f"Running {name} on {target.name}")
                await ctx.report_progress(progress=index, total=len(wanted) + 1)
            # One pass per `try`, so one source's outage costs one source's findings.
            # Sharing a `try` across the loop discarded every pass that had already
            # succeeded on its way out — three sources' work lost to one source being
            # down, which is the shape upstream fixed in its own PGx legs.
            #
            # The `*Unavailable` arm MUST come first: since 0.6.2 it is a subclass of
            # the arm below it, so parent-first would catch every outage as a data
            # error and this field would read `{}` on a run where gnomAD was down.
            try:
                result = await run_sync(
                    lambda n=name: _run_pass(n, target, mode, eff_offline, declared)
                )
            except _PASS_UNAVAILABLE[name] as exc:
                unreachable[name] = str(exc)
                continue
            except _PASS_ERROR[name] as exc:
                failed[name] = str(exc)
                continue
            ran.append(name)
            rows[name] = len(getattr(result, "rows", []) or [])
            covered[name] = [str(c) for c in (getattr(result, "covered", []) or [])]
            missing[name] = [str(m) for m in (getattr(result, "missing", []) or [])]
            if getattr(result, "skipped_offline", False):
                skipped.append(name)

        if skipped:
            warnings.append(
                f"Offline, so these did nothing: {', '.join(skipped)}. Their sidecars are "
                "unchanged — an absent row means UNCHECKED, not absent."
            )
        if unreachable:
            warnings.append(
                f"Source never answered for: {', '.join(sorted(unreachable))}. Those passes "
                "asked nothing, so their absence from `covered` is silence, not a negative "
                "result — re-run them rather than reading the sidecar as complete."
            )
        if failed:
            warnings.append(
                f"Failed on something that is not an outage: {', '.join(sorted(failed))}. "
                "The source answered; read `failed` for what it refused."
            )
        if ctx:
            await ctx.report_progress(progress=len(wanted) + 1, total=len(wanted) + 1)
        return FactPassReport(
            # A pass that never reached its source did not complete, and a report that
            # called that success would be the `covered: 0` trap one field over.
            success=not unreachable and not failed,
            spec_dir=str(target),
            passes_run=ran,
            rows_written=rows,
            covered=covered,
            missing=missing,
            declared_use_applied_to=["dosage"] if "dosage" in ran else [],
            skipped_offline=skipped,
            unreachable=unreachable,
            failed=failed,
            warnings=warnings,
            note=_REGENERATE,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Fill gwas_effects.csv",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def enrich_gwas_effects(
        spec_dir: str,
        strict: bool = False,
        use: str = "unstated",
        study_facts: bool = True,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> GwasReport:
        """Record the GWAS Catalog's published effect sizes for this module's rsIDs.

        One row per published **association**, not per variant — rs1800562 alone
        carries 189 of them across different traits and papers. Queried by rsID, so a
        coordinate-only variant row has no subject here and is simply absent.

        **It does not fill `weight`, and the numbers it does record are not candidates
        for one.** A published beta belongs to its own study's scale: on one real
        module a single variant carried **12 distinct `effect_unit` values**, several
        of them the Catalog's uninformative `unit`, and **33 of 186** recorded
        associations named no effect allele at all — the study never established which
        allele carries the effect, so the row has no direction a genotype could be
        matched against. Both counts come back on the result
        (`effect_units`, `associations_without_effect_allele`) precisely so that is
        readable rather than assumed. `weight` remains your model of the finding, and
        these sit beside it.

        **`strict` here is not a correctness gate, and it fails on the usual answer.**
        It escalates on the Catalog's own shape — associations served without an id to
        key on, and p-values the Catalog publishes below float64's range — and never on
        `missing`. Measured: `reference_examples/hfe_hemochromatosis`, a shipped
        flagship module, carries **six** such underflows, so strict refuses it while
        nothing about it is wrong. It also escalates *after* the write, so on a strict
        failure `gwas_effects.csv` holds everything `best_effort` would have written;
        a fetch failure mid-pass writes nothing. The message says which.

        A variant the Catalog holds nothing for gets a **`not_found` row** rather than
        silence: no published genome-wide association *is* a fact about the variant,
        and it is true of most clinically authored ones.

        The budget is `1 + 2N` requests per variant — pmid, trait, ancestry and study
        accession all sit behind `_links` — measured at 382 for one real module against
        somebody else's rate limit, which is why this runs as a background task.
        `study_facts=false` cuts that to one request per variant, and the cut is
        **sticky**: the merge is keyed on `association_id`, so a later run with study
        facts on skips those rows and never backfills them. Delete the file to
        re-derive.

        `offline=true` makes this a **no-op**, not a failure — the Catalog publishes a
        bulk download but this pass reads the REST API and has no snapshot.

        `use` is recorded on the licence row and gates nothing: EMBL-EBI names no
        licence, so `commercial_use` is written **unknown** rather than permitted. Do
        not read that as permission — the terms of the thousands of publications the
        Catalog summarizes are not settled by its terms page.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"
        declared = _check_use(use)

        if ctx:
            await ctx.info(
                f"Reading the GWAS Catalog for {target.name} (mode={mode}, "
                f"study_facts={'on' if study_facts else 'off'})"
            )
            await ctx.report_progress(progress=1, total=2)

        # ONE arm, and `GwasNotFound` deliberately does not get its own. It is a subclass of
        # `GwasError`, so an arm for it would have to come first — but it cannot arrive here:
        # `associations_for` catches the Catalog's 404 and returns the empty ANSWER, which the
        # pass records as a `not_found` row, and `follow` catches it so an association whose
        # study record moved keeps null study facts instead of sinking the pass. An except arm
        # for a type that never arrives is worse than none: it reads as if it did.
        # `tests/test_passes.py::test_no_except_arm_is_shadowed_by_an_earlier_one` is what stops
        # a second arm from being added parent-first.
        try:
            result = await run_sync(
                lambda: enrich_gwas(
                    target,
                    mode=mode,
                    offline=eff_offline,
                    declared_use=declared,
                    study_facts=study_facts,
                    write=True,
                )
            )
        except GwasError as exc:
            warnings: list[str] = [str(exc)]
            if strict:
                warnings.append(
                    "This ran strict, where the ladder escalates on the CATALOG's shape — "
                    "associations served without an id to key on, p-values below float64's "
                    "range — and does so AFTER the write. So read the message: an escalation "
                    "means gwas_effects.csv holds everything best_effort would have written, "
                    "while a fetch failure means nothing was written. Neither says your module "
                    "is wrong; re-run with strict=false to record what is holdable."
                )
            # Every counter stays `null`. The pass raised before it reported any of them, and
            # `0` would be a real answer — on a strict escalation a wrong one, since the message
            # itself names non-zero counts and the sidecar is already on disk. A counter that
            # nothing counted is not a counter that counted nothing.
            return GwasReport(
                success=False,
                spec_dir=str(target),
                mode=mode,
                offline=eff_offline,
                study_facts=study_facts,
                declared_use=declared,
                warnings=warnings,
                note=_GWAS_NOTE,
            )

        if ctx:
            await ctx.report_progress(progress=2, total=2)

        rows = list(getattr(result, "rows", []) or [])
        published = [r for r in rows if getattr(r, "status", None) != _GWAS_NOT_FOUND]
        no_allele = sum(1 for r in published if not getattr(r, "effect_allele", None))
        units = sorted({str(r.effect_unit) for r in published if getattr(r, "effect_unit", None)})
        skipped = bool(getattr(result, "skipped_offline", False))
        underflows = int(getattr(result, "p_value_underflows", 0) or 0)
        unusable = int(getattr(result, "unusable", 0) or 0)

        # Aggregated by reason with a count, one line each — never one per row, which over a
        # well-studied variant's dozens of associations is a wall nobody reads. Upstream warns
        # about the first two through `logging`, which goes to stderr and reaches no MCP caller.
        warnings: list[str] = []
        if skipped:
            warnings.append(
                "Offline: this pass did NOTHING. There is no snapshot of the Catalog's REST API, "
                "so any existing gwas_effects.csv is unchanged and a missing one is still missing."
            )
        if underflows:
            warnings.append(
                f"{underflows} association(s) carry a p-value the Catalog publishes below "
                "float64's range, so `p_value_num` is withheld and the verbatim `p_value` string "
                "carries what the source said. The rows are all there."
            )
        if unusable:
            warnings.append(
                f"{unusable} association(s) were served without an id this pass can key on and "
                "are in no row. Every usable association was still recorded."
            )
        if no_allele:
            warnings.append(
                f"{no_allele} of {len(published)} recorded association(s) name no effect allele — "
                "the study never established which one carries the effect. Real evidence with no "
                "direction a genotype can be matched against, so it cannot become a weight."
            )
        if len(units) > 1:
            warnings.append(
                f"{len(units)} distinct effect_unit value(s) across this table: "
                f"{', '.join(units)}. These betas are on different and possibly uninterpretable "
                "scales and do not combine."
            )
        if not study_facts:
            warnings.append(
                "study_facts was off, so pmid, trait, trait_efo_id, ancestry and study_accession "
                "are null on every row this run wrote. The merge is keyed on association_id, so a "
                "later run with study facts on will SKIP these rows rather than backfill them — "
                "delete gwas_effects.csv to re-derive them."
            )

        return GwasReport(
            success=True,
            spec_dir=str(target),
            mode=mode,
            offline=eff_offline,
            # On a no-op the pass returns no rows, which says nothing about the file: an existing
            # gwas_effects.csv keeps whatever it held, so `0` would assert something unchecked.
            rows=None if skipped else len(rows),
            covered=[str(c) for c in (getattr(result, "covered", []) or [])],
            missing=[str(m) for m in (getattr(result, "missing", []) or [])],
            requests_made=int(getattr(result, "requests_made", 0) or 0),
            requests_saved=int(getattr(result, "requests_saved", 0) or 0),
            p_value_underflows=underflows,
            unusable=unusable,
            associations_without_effect_allele=no_allele,
            effect_units=units,
            study_facts=study_facts,
            declared_use=declared,
            skipped_offline=skipped,
            warnings=warnings,
            note=_GWAS_NOTE,
        )



def _run_pass(name: str, target: Path, mode: str, offline: bool, use: str) -> Any:
    """Dispatch one fact pass. Explicit rather than a table of partials."""
    if name == "frequencies":
        return enrich_frequencies(target, mode=mode, offline=offline, write=True)
    if name == "gene_metrics":
        return enrich_gene_metrics(target, mode=mode, offline=offline, write=True)
    if name == "dosage":
        return enrich_dosage_sensitivity(
            target, mode=mode, declared_use=use, offline=offline, write=True
        )
    raise ValueError(f"unknown pass {name}")
