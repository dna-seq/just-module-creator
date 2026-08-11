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

`draft_from_clinvar` is registered in **every** mode: the essentials tier has to
be able to take a variants module from nothing to compiled. The two PGx drafters
and the fact passes are extended — a PGx module is the specialist path, and
`draft_from_clinpgx` needs a snapshot only a CLI-only builder produces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_enricher.clingen import ClinGenError, enrich_dosage_sensitivity
from just_dna_enricher.clinpgx_draft import ClinPgxEnrichmentError, draft_pharm_variants
from just_dna_enricher.clinvar_draft import ClinVarDraftError, draft_gene_panel
from just_dna_enricher.cpic import CpicError
from just_dna_enricher.frequencies import FrequencyEnrichmentError, enrich_frequencies
from just_dna_enricher.gene_metrics import GeneMetricsEnrichmentError, enrich_gene_metrics
from just_dna_enricher.literature import LiteratureEnrichmentError, enrich_literature
from just_dna_enricher.pgx_draft import draft_gene
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    DraftedTable,
    DraftResult,
    FactPassReport,
    LiteratureReport,
)
from just_module_creator.net import NetworkServices
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import offline_for, resolve_dir

log = get_logger()

VALID_USE = ("unstated", "non_commercial", "commercial")

_REGENERATE = (
    "An existing sidecar is authoritative and MERGED, never clobbered. To regenerate "
    "it after changing the spec you must DELETE the file first, or stale rows persist "
    "silently."
)

_FACT_PASSES = ("frequencies", "gene_metrics", "dosage")


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


_SOURCE_ERRORS = (
    ClinVarDraftError,
    CpicError,
    ClinPgxEnrichmentError,
    FrequencyEnrichmentError,
    GeneMetricsEnrichmentError,
    ClinGenError,
)


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


def register_extended_passes(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the PGx drafters and the sidecar fact passes."""

    @mcp.tool(
        tags={"extended"},
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
        tags={"extended"},
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
        tags={"extended"},
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

        **`doi_conflicts` are reported, never rewritten.** Your authored DOI and
        the registry's disagree for that PMID, which means one of the two
        citations is the wrong paper — and only you know which.

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
            coverage=str(getattr(result, "coverage", "") or ""),
            skipped_offline=skipped,
            warnings=warnings,
            note=_REGENERATE,
        )

    @mcp.tool(
        tags={"extended"},
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
        warnings: list[str] = []
        ran: list[str] = []

        for index, name in enumerate(wanted, start=1):
            if ctx:
                await ctx.info(f"Running {name} on {target.name}")
                await ctx.report_progress(progress=index, total=len(wanted) + 1)
            result = await run_sync(
                lambda n=name: _run_pass(n, target, mode, eff_offline, declared)
            )
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
        if ctx:
            await ctx.report_progress(progress=len(wanted) + 1, total=len(wanted) + 1)
        return FactPassReport(
            success=True,
            spec_dir=str(target),
            passes_run=ran,
            rows_written=rows,
            covered=covered,
            missing=missing,
            declared_use_applied_to=["dosage"] if "dosage" in ran else [],
            skipped_offline=skipped,
            warnings=warnings,
            note=_REGENERATE,
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
