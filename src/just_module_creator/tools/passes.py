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

import csv
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler.draft import DraftError
from just_dna_enricher.civic_draft import CivicDraftError, draft_panel_from_civic
from just_dna_enricher.clingen import (
    ClinGenError,
    ClinGenUnavailable,
    enrich_dosage_sensitivity,
)
from just_dna_enricher.clinpgx_draft import ClinPgxEnrichmentError, draft_pharm_variants
from just_dna_enricher.clinvar_draft import ClinVarDraftError, draft_gene_panel
from just_dna_enricher.cpic import CpicError
from just_dna_enricher.enrich import EnrichmentError, enrich
from just_dna_enricher.expression import (
    ExpressionError,
    ExpressionUnavailable,
    enrich_expression,
)
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
from just_dna_enricher.licensing import (
    CIVIC_TERMS,
    CLINPGX_TERMS,
    CLINVAR_TERMS,
    CPIC_TERMS,
    MITOMAP_TERMS,
    PUBMIND_TERMS,
    STRCHIVE_TERMS,
    LicenseRefusal,
    check_declared_use,
)
from just_dna_enricher.literature import LiteratureEnrichmentError, enrich_literature
from just_dna_enricher.mitomap_draft import (
    MitomapDraftError,
    draft_panel_from_mitomap_miss,
)
from just_dna_enricher.pgx_draft import draft_gene
from just_dna_enricher.pubmind_draft import (
    DEFAULT_CLIN_SIG,
    PubMindDraftError,
    draft_gene_panel_from_pubmind,
)
from just_dna_enricher.strchive_draft import StrchiveDraftError, draft_repeat_loci
from just_dna_format.vocab import VALID_DECLARED_USE
from mcp.types import ToolAnnotations

from just_module_creator.expression import (
    ROW_STATUSES,
    effect_key,
    module_sites,
    plan_windows,
    report_rows,
)
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    DraftedTable,
    DraftResult,
    EnrichReport,
    ExpressionRanking,
    ExpressionReport,
    FactPassReport,
    GwasReport,
    LiteratureReport,
    RankedExpressionEffect,
)
from just_module_creator.net import NetworkServices
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import (
    narrate,
    normalize_declared_use,
    offline_for,
    resolve_dir,
)

log = get_logger()

# Kept only for the message in `_pass_argument_help`; the *check* reads format's
# own `VALID_DECLARED_USE` through `normalize_declared_use`. A second literal here
# is the hardcoded-vocabulary defect, and it stays a display string for that reason.
VALID_USE = tuple(sorted(VALID_DECLARED_USE))

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


# Two upstream remedies that name something this surface does not have, each keyed on the
# placeholder so a genuinely broken authored row is not misdiagnosed as a scaffold stub
# (F100, measured 2026-09-20 on a fresh three-kind PGx scaffold; upstream half is S103).
# `spec_genome_build` says "pass genome_build= explicitly", and no drafter here — nor
# upstream's `draft_gene` — takes one: the build is read from the spec, so the only
# repair is the spec. `draft.merge_rows` refuses a table that does not validate, and a
# scaffold stub is `<<REPLACE>>` in every required cell.
_SPEC_PLACEHOLDER_REMEDY = (
    "No tool here takes a genome_build argument: the build is read from module_spec.yaml, "
    "so the repair is the spec itself. Replace the <<REPLACE>> in the field it names and "
    "re-run; a scaffold's other stubs no longer block a draft (enricher 0.7.1)."
)
_STUB_ROW_REMEDY = (
    "That row is the scaffold's stub. A drafter creates and fills the table, so delete the "
    "stub row (keep the header line), or scaffold that kind with rows=0, and re-run."
)


def _translate(message: str) -> str:
    """Upstream's message, plus how its CLI flags map onto this tool's arguments."""
    mentioned = [f"{flag} -> {arg}" for flag, arg in _FLAG_TO_ARG.items() if flag in message]
    out = message
    if mentioned:
        out = (
            f"{message}\n\nThat message is the enricher's, written for its CLI. On this tool the "
            f"equivalent arguments are: {'; '.join(mentioned)}."
        )
    if "<<REPLACE>>" in message and "cannot read the module's genome_build" in message:
        out = f"{out}\n\n{_SPEC_PLACEHOLDER_REMEDY}"
    if "<<REPLACE>>" in message and "does not validate, so a draft cannot be keyed" in message:
        out = f"{out}\n\n{_STUB_ROW_REMEDY}"
    return out


# Parents only, in ONE tuple. Since enricher 0.6.2 each pass raises its own type with
# unavailability as a *subclass* (`FrequencyUnavailable(FrequencyEnrichmentError)` and
# five siblings), so listing the parents catches strictly more than it used to and
# nothing less. The shape matters: two separate `except` arms with the parent first
# would send every outage into the parent arm and leave the outage arm dead, silently.
# `tests/test_passes.py::test_no_except_arm_is_shadowed_by_an_earlier_one` walks this
# module's AST for exactly that, because it is the failure that raises nothing.
#
# The last two are not source failures: `EnrichmentError` is what a drafter raises when it
# cannot read the spec's genome_build before touching a source, and `DraftError` is the
# compiler's refusal to key a draft against a table that does not validate. Both escaped
# raw until F100, so the remedy an agent read was written for the CLI.
_SOURCE_ERRORS = (
    ClinVarDraftError,
    CpicError,
    ClinPgxEnrichmentError,
    FrequencyEnrichmentError,
    GeneMetricsEnrichmentError,
    ClinGenError,
    EnrichmentError,
    DraftError,
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


#: Whose terms gate each drafting source, so a skip can be told apart from a licence
#: refusal rather than guessed at. Hand-kept — only the tool knows which source it calls —
#: and `test_every_upstream_drafting_source_has_a_tool` is what stops the roster drifting.
_SOURCE_TERMS = {
    "civic": CIVIC_TERMS,
    "clinpgx": CLINPGX_TERMS,
    "clinvar": CLINVAR_TERMS,
    "cpic": CPIC_TERMS,
    "mitomap": MITOMAP_TERMS,
    "pubmind": PUBMIND_TERMS,
    "strchive": STRCHIVE_TERMS,
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
    """Validate the licence declaration. Never defaulted, never guessed.

    Thin now: the rule and the vocabulary both live in `_shared`, so the hyphen is
    folded the same way here, in `refresh` and in the registry pre-flight, which is
    what `F74` found they did not do.
    """
    return normalize_declared_use(use)


def _tables(result: Any, *, written: bool) -> list[DraftedTable]:
    """Project upstream's per-CSV reports, keeping all four row statuses.

    `differs` is report-never-repair: the source disagrees with a row you
    authored, and upstream leaves yours alone. Collapsing the statuses into one
    count would hide exactly the rows worth looking at.
    """
    out: list[DraftedTable] = []
    # `strchive_draft` returns ONE `report`, every other drafter a `reports` list. Normalising
    # here rather than at four call sites keeps the projection the single place that knows the
    # shape — and a drafter that grows a second table needs no change on our side.
    reports = getattr(result, "reports", None)
    if reports is None:
        single = getattr(result, "report", None)
        reports = [single] if single is not None else []
    for report in reports or []:
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
    result: Any,
    *,
    spec_dir: Path,
    source: str,
    use: str,
    dry_run: bool,
    findings: Sequence[str] = (),
) -> DraftResult:
    skipped = bool(getattr(result, "skipped", False))
    tables = _tables(result, written=not dry_run)
    # `skipped` means "nothing was fetched" and upstream sets it for MORE than a licence
    # refusal — STRchive sets it when no catalogue is provisioned, which is a cache lane to
    # build rather than a licence to argue with. Telling that author their declared use was
    # rejected sends them to the wrong door entirely, so the reason is DECIDED by asking the
    # same public predicate the drafter asked, never inferred from the flag.
    terms = _SOURCE_TERMS.get(source)
    licence_refusal = None
    if skipped and terms:
        # THREE outcomes, not two: a reason string, None to go, and a RAISE for the direct
        # contradiction (a no-sale source against a commercial declaration). The raise is
        # itself a licence refusal, so catching it here classifies rather than recovers —
        # and handling only the first two read as "not a licence problem" on exactly the
        # clearest licence problem there is.
        try:
            licence_refusal = check_declared_use(terms, use)
        except LicenseRefusal as refusal:
            licence_refusal = str(refusal)
    if skipped and licence_refusal:
        next_step = (
            "Nothing was fetched: your declared use does not satisfy this source's terms. "
            "That is the gate working. Do NOT re-run with a different `use` to get past it — "
            "either you may use the data that way or you may not."
        )
    elif skipped:
        next_step = (
            "Nothing was fetched, and NOT because of your declared use — that was checked "
            "separately and is fine. The reason is in `warnings`, and for these sources it is "
            "usually a cache lane that has not been provisioned yet. Read it before changing "
            "anything about the module."
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
        # `None` rather than 0 where the drafter does not report one: a source that counted
        # nothing and a source that does not count are different answers.
        candidates=getattr(result, "candidates", None),
        withheld=dict(getattr(result, "withheld", {}) or {}),
        source_findings=list(findings or []),
        next_step=next_step,
    )


def register_passes(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the always-on drafting tool (ClinVar -> variants + studies)."""
    # Below enricher 0.6.3 the drafter keyed a site on `ref`, so an ordinary ClinVar dup/del
    # mirror pair collapsed onto one row and the second record was dropped silently (upstream
    # S41). Measured on one gene: re-running leaves 0 records missing and 31 stale identities.
    # Since 0.6.4 the run NAMES them, counted with examples, and deletes nothing — by re-draft
    # time a drafted row is authored material and may have been curated since. The warning is
    # the safety net rather than the plan: no file-level check can find these rows, because a
    # coordinate row carries no `rsid` and nothing separates a stale row from a legitimate rsid-
    # only one. Drafting into a fresh directory and reconciling stays the cleaner remediation.

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from ClinVar",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
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

        Step 2 of the workflow, re-runnable and additive: rows already in the files are
        left exactly as they are. **`use` is required** — `unstated`, `non_commercial`
        or `commercial`, with no default because both possible defaults are wrong — and
        `skipped=true` means the terms were not satisfied and nothing was fetched, which
        is the gate working rather than an argument to retry with a different `use`.
        Read `differs`: those are rows where ClinVar disagrees with something you
        authored, left unchanged because only you know which side is right.
        `max_citations` drafts the study rows that make a panel compilable,
        `min_review_stars` defaults to 2, and drafted rows carry `<<REPLACE>>` in the
        cells only a human can decide — which makes every loader refuse the file,
        `enrich_module` included, so curate before you enrich. **If this module was
        drafted before enricher 0.6.3, read the superseded-row warning first**: this run
        recovers the records that version dropped but does not retract the collapsed
        rows it wrote, so the module would assert both answers for one locus.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        if not genes:
            raise ToolError("Provide at least one gene symbol.")

        if ctx:
            await narrate(ctx, f"Drafting {', '.join(genes)} from ClinVar into {target.name}")
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

    # Declared task-capable, but that only makes tasks OPTIONAL: a client that sends no task
    # metadata — and the usual ones do not — gets an ordinary synchronous call. The docstring
    # said otherwise until 2026-08-22 and a run planning around the promise had nothing to plan
    # with. Progress is reported once before and once after, never during, so a client idle
    # timeout is what you hit. Measured: 32 variants return in seconds; 330 and 474 were killed
    # client-side at 1800s. The interruption is client-side only, which is why a `success`
    # issued while an aborted call may still be running is unverified.

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Enrich a spec (resolve coordinates)",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def enrich_module(
        spec_dir: str,
        strict: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> EnrichReport:
        """Resolve rsIDs to coordinates and mint VRS ids, writing resolution.csv.

        The only step that fetches, and the only thing that can catch the mistake no
        offline gate can: it compares your authored `ref` against the genome and reports
        `ref mismatch: N row(s) — coordinate shifted 1 base`. **Read that as being about
        `start`, not `ref`** — it is what subtracting one from a VCF position produces —
        and it is a floor rather than a total, since only rows whose neighbouring base
        differs from `ref` are visible. **It blocks, with no task id to poll**, and it
        reports progress in subjects; a killed run leaves its staged answers behind and
        the next run resumes from them rather than starting over. Two runs over one spec
        directory cannot overlap — the second is refused, not queued, and since 0.7 the
        refusal is upstream's own advisory `flock` on the directory, so it excludes
        another process too and not only another call of this tool. On a filesystem that
        will not take the lock it warns and proceeds unexcluded, which is a real state
        rather than a theoretical one: serialize enrichment yourself there. Curate first — a
        `<<REPLACE>>` anywhere makes this refuse, deliberately, since forward resolution
        is allele-aware. `offline=true` restricts to local caches, where the ref check
        does not run at all, and a check that could not run is not a check that passed.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"

        if ctx:
            await narrate(
                ctx,
                f"Enriching {target.name} (mode={mode}, "
                f"{'cache-only' if eff_offline else 'network'})",
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
            #
            # The denominator arrives from upstream now (0.7, RM128, our `S66` ask 4):
            # `progress` is called `(done, total)` over SUBJECTS, with `total` known
            # before the first call. So the elapsed-seconds heartbeat this replaces —
            # which reported time because we had no denominator and refused to invent one
            # — reports work instead.
            #
            # **The timer stays and only what it says has changed**, which is deliberate
            # and is not what the dismantle note predicted. Upstream's callback fires when
            # a subject completes, and the resolver batches, so the silences the heartbeat
            # existed for are still there — a caller with an idle timeout needs a tick on
            # the wall clock, not on somebody else's progress. What it can now say inside
            # that tick is a real (done, total) rather than a duration.
            #
            # The callback runs on the worker thread and `ctx.report_progress` is async on
            # the event loop, so the two meet through a plain cell rather than a portal: a
            # tuple assignment is atomic, the reader tolerates a stale read by definition
            # (it is a progress report), and `anyio.from_thread` would need a portal held
            # open for the whole call to gain nothing.
            latest: list[tuple[int, int] | None] = [None]

            def _note_progress(done: int, total: int) -> None:
                latest[0] = (done, total)

            async def _heartbeat() -> None:
                if ctx is None:
                    return
                started = datetime.now(UTC)
                while True:
                    await anyio.sleep(_HEARTBEAT_SECONDS)
                    seconds = int((datetime.now(UTC) - started).total_seconds())
                    seen = latest[0]
                    if seen is None:
                        # Before the first subject completes there is no denominator, so
                        # this says elapsed time and says why — which is the honest answer
                        # rather than a zero that looks like stalled work.
                        await ctx.report_progress(
                            progress=seconds,
                            message=(
                                f"enrich still running, {seconds}s elapsed — no subject "
                                "has completed yet, so there is no total to count "
                                "against. Expected on a first pass, not a stall."
                            ),
                        )
                        continue
                    done, total = seen
                    await ctx.report_progress(
                        progress=done,
                        total=total,
                        message=(
                            f"enrich: {done}/{total} subjects, {seconds}s elapsed. "
                            "Answers are staged as they arrive, so a killed run resumes "
                            "from them rather than starting over."
                        ),
                    )

            # `except*`, not `except`: the heartbeat's task group re-raises whatever the
            # enrichment threw wrapped in an `ExceptionGroup`, and a plain `except
            # EnrichmentError` does not catch a group. It did not, for every strict run
            # that had something to refuse — the caller got `unhandled errors in a
            # TaskGroup (1 sub-exception)` with no message and no unresolved list, while
            # the same spec under `best_effort` named all five. A clean strict run raises
            # nothing, so the dead arm was invisible until a module failed to resolve.
            try:
                async with anyio.create_task_group() as beat:
                    beat.start_soon(_heartbeat)
                    result = await run_sync(
                        lambda: enrich(
                            target,
                            mode=mode,
                            offline=eff_offline,
                            write=True,
                            progress=_note_progress,
                        )
                    )
                    beat.cancel_scope.cancel()
            except* Exception as group:
                # Unwrap ANY lone exception, not just `EnrichmentError`: every error the
                # enrichment can raise reaches its caller through this group, and a group
                # loses the type that every arm downstream — and every reader — matches
                # on. A group carrying more than one is re-raised whole, because picking
                # one of several would be discarding a failure to make a tidier message.
                if len(group.exceptions) == 1:
                    raise group.exceptions[0] from None
                raise
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
        # Before enricher 0.7.1 a row authored with BOTH an rsID and a coordinate took
        # upstream's last resolver branch — "nothing to resolve" — and the sidecar restated
        # the authored coordinate under `source=authored` with no `ref`, no `alts` and no
        # VRS id, so every CPIC-drafted module compiled at 0% VRS coverage (F103, upstream
        # S104, fixed in 0.7.1: such a row now takes the forward branch when the reference
        # knows its rsID). The shape still arrives from a sidecar written before the fix,
        # because a sidecar is merge-not-clobber, and the remedy is a re-derivation.
        restated = sum(
            1
            for row in getattr(result, "rows", []) or []
            if getattr(row, "status", None) == "resolved"
            and getattr(row, "source", None) == "authored"
            and getattr(row, "rsid", None)
            and not getattr(row, "vrs_id", None)
            and not getattr(row, "ref", None)
        )
        if restated:
            warnings.append(
                f"{restated} row(s) carry both an rsID and a coordinate and resolution.csv "
                "restates the authored position under source=authored with no ref, no alts "
                "and no VRS id — nothing Ensembl answered reached the sidecar, and the "
                "compile will warn that VRS identity covers 0 of these. That is a sidecar "
                "written before enricher 0.7.1 (upstream S104) and kept by merge-not-clobber: "
                "`refresh_sidecar(sidecar='resolution.csv')` re-derives it so the "
                "reference's answer is recorded."
            )
        return EnrichReport(
            success=True,
            spec_dir=str(target),
            mode=mode,
            offline=eff_offline,
            # `rows` is what was WRITTEN, and upstream writes a `status: not_found` row
            # for a subject it also lists in `unresolved` — so the row count reported
            # `resolved: 64` beside five unresolved keys on a 64-subject module, which
            # reads as "all of them, and also not five of them". Count the outcome, not
            # the file's length.
            resolved=sum(
                1
                for row in getattr(result, "rows", []) or []
                if getattr(row, "status", None) == "resolved"
            ),
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
#: How often the enrich heartbeat speaks. Thirty seconds is short enough that an
#: operator watching a silent tool learns it is alive before deciding it is not, and
#: long enough that a normal small module finishes without emitting one at all.
#: It is also what carries upstream's `progress` count to the caller, so it stays
#: now that the enricher reports one.
_HEARTBEAT_SECONDS = 30.0

_ENRICHMENTS_IN_FLIGHT: dict[Path, str] = {}


def register_bulk_passes(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the PGx drafters, the sidecar fact passes and the GWAS Catalog pass."""

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from CPIC",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
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
            await narrate(ctx, f"Drafting {gene} from CPIC into {target.name}")
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
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
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
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
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

        Checks that each PMID exists (PubMed), that each authored DOI exists (Crossref),
        and — where the text is retrievable — that each `provenance_quote` really
        appears in the paper.

        **`quotes_unchecked` is not a failure count**: nothing was retrievable to check
        against, and an abstract miss is not a verdict since the claim may still be in
        the full paper. **`titles_as_quotes` is the opposite reading and the more
        dangerous one** — a quote that is the article's own title passes every time,
        because a title is inside its own fulltext, so the row counts as covered while
        witnessing nothing. Ask of any green check whether it could have failed.
        **`doi_conflicts` are reported, never rewritten**: your DOI and the registry's
        disagree for that PMID, so one of the two citations is the wrong paper and only
        you know which.

        **Budget: one or more requests per citation in the module**, so the cost rises
        with the corpus you have cited rather than with anything named in this call — a
        module with hundreds of studies is a long run. `offline=true` makes this a **no-
        op**: there is no offline literature snapshot and there will not be one, because
        once `literature.csv` is written it *is* the pin.

        **No thin path: `remote_derive` does not run this.** That route runs what a
        publish runs, and the literature pass is one of the opt-in check passes — egress
        spent on a verdict rather than on the bytes a compile needs. So this is a local
        call whatever `JMC_SNAPSHOT_ROUTE` says, and there is no snapshot lane to be
        missing, because it reads none.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"

        if ctx:
            await narrate(ctx, f"Resolving citations for {target.name}")
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
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
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
        is why the offline flag is reported separately. **No thin path** — these are
        opt-in check passes that `remote_derive` deliberately skips, so each needs its
        snapshot lane *here*; `registry_caches` says which this machine holds.
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
                await narrate(ctx, f"Running {name} on {target.name}")
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

    # Measured: reference_examples/hfe_hemochromatosis, a shipped flagship module, carries six
    # p-value underflows, so `strict` refuses it while nothing about it is wrong.

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Fill gwas_effects.csv",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
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

        One row per published **association**, not per variant — rs1800562 alone carries
        189 across different traits and papers — and queried by rsID, so a coordinate-
        only variant row is simply absent. A variant the Catalog holds nothing for gets
        a **`not_found` row** rather than silence: no published genome-wide association
        is itself a fact about the variant, and it is true of most clinically authored
        ones.

        **It does not fill `weight`, and the numbers it records are not candidates for
        one.** A published beta belongs to its own study's scale: on one real module a
        single variant carried 12 distinct `effect_unit` values, and 33 of 186
        associations named no effect allele at all, so those rows have no direction a
        genotype could be matched against. Both counts come back on the result
        (`effect_units`, `associations_without_effect_allele`) precisely so that is
        readable rather than assumed; `weight` stays your model of the finding and these
        sit beside it.

        **`strict` here is not a correctness gate and it fails on the usual answer.** It
        escalates on the Catalog's own shape — associations served without an id to key
        on, p-values published below float64's range — and never on `missing`, and it
        escalates *after* the write, so a strict failure leaves everything `best_effort`
        would have written while a fetch failure mid-pass writes nothing.

        The budget is `1 + 2N` requests per variant, since pmid, trait, ancestry and
        study accession sit behind `_links` — measured at 382 for one real module
        against somebody else's rate limit. `study_facts=false` cuts that to one request
        per variant, and the cut is **sticky**: the merge is keyed on `association_id`,
        so a later run with study facts on skips those rows rather than backfilling
        them, and only deleting the file re-derives them. `offline=true` is a no-op, not
        a failure. `use` is recorded on the licence row and gates nothing — EMBL-EBI
        names no licence, so `commercial_use` is written **unknown**, which is not
        permission: the terms of the thousands of publications the Catalog summarizes
        are not settled by its terms page.

        **No thin path: `remote_derive` does not run this.** It is one of the opt-in
        check passes that route deliberately skips — egress spent on a verdict rather
        than on the bytes a compile needs. There is also no lane to be missing: the
        Catalog publishes no snapshot, so this is a live call from wherever it runs.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"
        declared = _check_use(use)

        if ctx:
            await narrate(
                ctx,
                f"Reading the GWAS Catalog for {target.name} (mode={mode}, "
                f"study_facts={'on' if study_facts else 'off'})",
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

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from CIViC",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def draft_from_civic(
        spec_dir: str,
        genes: list[str],
        use: str,
        dry_run: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft variant rows from CIViC's curated clinical evidence.

        CIViC is **CC0-1.0** — the one drafting source here with no licence friction at
        all — and it is expert-curated rather than mined, so its calls carry a named
        evidence level behind them.

        **The output worth reading is `source_findings`.** CIViC records refutations
        beside the claims they refute, and this reports the pairs it saw. A variant whose
        accepted claim sits next to a refuting one is not a row to draft and forget: it is
        the clearest signal in any of these sources that the literature is contested, and
        `direction=contested` exists in `variants.csv` for exactly that. Nothing is
        auto-resolved, because which side wins is a judgement.

        Identity comes back as a CAID from the ClinGen Allele Registry where CIViC gives a
        coordinate rather than an rsID, so rows resolve that could not be joined on rsID
        alone. `offline=true` uses only the local snapshot.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        if ctx:
            await narrate(ctx, f"Drafting {', '.join(genes)} from CIViC into {target.name}")
            await ctx.report_progress(progress=1, total=2)
        try:
            result = await run_sync(
                lambda: draft_panel_from_civic(
                    target,
                    tuple(genes),
                    declared_use=declared,
                    offline=eff_offline,
                    dry_run=dry_run,
                )
            )
        except CivicDraftError as exc:
            raise ToolError(str(exc)) from exc
        findings = [
            f"{variant}: an accepted claim sits beside a refuting one ({basis})"
            for variant, basis, _ in getattr(result, "refuted_beside_claim", []) or []
        ]
        if findings and getattr(result, "refutation_basis", None):
            findings.append(
                f"refutation basis: {result.refutation_basis}. Consider direction=contested "
                "rather than picking a side silently."
            )
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(
            result,
            spec_dir=target,
            source="civic",
            use=declared,
            dry_run=dry_run,
            findings=findings,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from MITOMAP",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def draft_from_mitomap(
        spec_dir: str,
        genes: list[str],
        use: str,
        dry_run: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft mitochondrial variant rows from MITOMAP's confirmed disease list.

        MITOMAP is **CC-BY-3.0** and the only source here for mtDNA. Positions come back
        on `MT` — the format folds `MT`, `chrMT`, `M` and `chrM` to `MT`, so a consumer
        VCF spelling it `chrM` still joins.

        **Read `source_findings` before the row counts.** It carries MITOMAP's *stale*
        identities: rows whose identity moved since a previous draft, which a plain re-run
        leaves behind under the old key rather than updating. That is the `S41` shape and
        it is why a re-draft over an existing spec can converge to *0 missing, N stale*
        rather than to nothing. It also names indefinite alleles and bracketed
        withholdings, both of which mean the source declined to state a definite change.

        **mtDNA is heteroplasmic and a variant row cannot say so.** A pathogenic mtDNA
        variant's effect usually depends on what fraction of a person's mitochondria carry
        it, and that is `heteroplasmy.csv`'s subject, not this table's. Drafting the
        variant is right; concluding from it without a heteroplasmy threshold is not.

        There is no `offline` argument, deliberately: this reads the `mitomap_miss` cache
        lane, so it is snapshot-backed rather than live.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        if ctx:
            await narrate(ctx, f"Drafting {', '.join(genes)} from MITOMAP into {target.name}")
            await ctx.report_progress(progress=1, total=2)
        try:
            result = await run_sync(
                lambda: draft_panel_from_mitomap_miss(
                    target, tuple(genes), declared_use=declared, dry_run=dry_run
                )
            )
        except MitomapDraftError as exc:
            raise ToolError(str(exc)) from exc
        findings = []
        stale = getattr(result, "stale", {}) or {}
        if stale:
            findings.append(
                f"{len(stale)} row(s) carry an identity MITOMAP has since moved. A plain re-run "
                "leaves these under the old key rather than updating them — read them before "
                "treating this draft as converged."
            )
        indefinite = getattr(result, "indefinite_alleles", []) or []
        if indefinite:
            findings.append(
                f"{len(indefinite)} allele(s) are indefinite in the source, e.g. "
                f"{', '.join(map(str, indefinite[:5]))} — the source declined to state a "
                "definite change, so no genotype can be written from them."
            )
        brackets = getattr(result, "withheld_brackets", {}) or {}
        if brackets:
            findings.append(f"bracketed withholdings by reason: {brackets}")
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(
            result,
            spec_dir=target,
            source="mitomap",
            use=declared,
            dry_run=dry_run,
            findings=findings,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft from PubMind",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def draft_from_pubmind(
        spec_dir: str,
        genes: list[str],
        use: str,
        clin_sig: list[str] | None = None,
        min_confidence: int = 1,
        dry_run: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft variant rows from PubMind's machine-extracted literature calls.

        **PubMind is an LLM's reading of the literature, not a curated archive.** Its
        clinical call is a model's extraction from a paper, with its own confidence and
        derivation; one real position carried ten records spanning conflicting, pathogenic
        and uncertain_significance at once. `min_confidence` and `clin_sig` narrow that;
        neither turns it into an expert call.

        **Drafting a clinical call from here makes the check that verifies one vacuous.**
        The enricher's clin_sig cross-check reads PubMind too, and `lookup_variant` already
        withholds its value for that reason. A row drafted here has not been independently
        checked — it was written by one of the things that would check it. Use it to find
        candidates; author the call yourself.

        **Its licence is unknown, so today this always skips.** Measured 2026-09-12:
        PubMind's terms record commercial use, share-alike and redistribution all as null,
        and upstream refuses an unestablished source under **every** declared use, so this
        returns `skipped=true` and writes nothing whatever you pass. That is their gate
        being conservative, and unknown is not permission. Wrapped anyway because the
        refusal is the useful answer, and it starts working the day terms are recorded.

        `genes` is required: this source is too large to draft unfiltered.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        if not genes:
            raise ToolError(
                "genes is required for PubMind: the corpus is too large to draft unfiltered, "
                "and an empty list would ask for all of it rather than for nothing."
            )
        if ctx:
            await narrate(ctx, f"Drafting {', '.join(genes)} from PubMind into {target.name}")
            await ctx.report_progress(progress=1, total=2)
        try:
            result = await run_sync(
                lambda: draft_gene_panel_from_pubmind(
                    target,
                    tuple(genes),
                    clin_sig=frozenset(clin_sig) if clin_sig else DEFAULT_CLIN_SIG,
                    min_confidence=min_confidence,
                    declared_use=declared,
                    offline=eff_offline,
                    dry_run=dry_run,
                )
            )
        except PubMindDraftError as exc:
            raise ToolError(str(exc)) from exc
        findings = [
            "Every clin_sig here was extracted by a model. It is redundancy-bearing: the check "
            "that verifies clin_sig reads PubMind too, so a drafted call is not an independently "
            "verified one. Author the call yourself and use these rows as candidates.",
        ]
        mapped = getattr(result, "mapped_positions", 0)
        spoken = getattr(result, "spoken_positions", 0)
        if spoken:
            findings.append(
                f"{mapped} of {spoken} position(s) the corpus speaks about could be mapped to a "
                "coordinate; the rest name a variant this pass could not place."
            )
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(
            result,
            spec_dir=target,
            source="pubmind",
            use=declared,
            dry_run=dry_run,
            findings=findings,
        )

    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Draft repeat loci from STRchive",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def draft_from_strchive(
        spec_dir: str,
        genes: list[str],
        use: str,
        dry_run: bool = False,
        ctx: Context | None = None,
    ) -> DraftResult:
        """Draft `repeat_alleles.csv` — repeat-expansion bands — from STRchive.

        **MIT-licensed, and the only drafter here that writes a BINNING table.** A repeat
        locus is not a variant with a genotype: the subject is a *count* with thresholds,
        so the rows are ranges (normal / intermediate / pathogenic) rather than
        `variants.csv` entries. `list_tables` is the router if that distinction is new;
        drafting HTT or FMR1 into `variants.csv` is the mistake this tool exists to stop.

        **`source_findings` carries the contested loci**, and they are the point. Published
        thresholds for the same repeat disagree between sources more often than for almost
        anything else in the format, and STRchive records where. A contested boundary is a
        decision for a pilot, not a number to copy — and a bin whose threshold no paper
        grounds is reported at compile time as `bins_ungrounded`.

        `fractional_ref_copies` and `with_locus_structure` come back on the result:
        a fractional reference count means the locus does not divide evenly into its
        repeat unit, which is a real property of the locus and not a rounding error.
        """
        declared = _check_use(use)
        target = resolve_dir(spec_dir, settings)
        if ctx:
            await narrate(ctx, f"Drafting repeat loci for {', '.join(genes)} into {target.name}")
            await ctx.report_progress(progress=1, total=2)
        try:
            result = await run_sync(
                lambda: draft_repeat_loci(
                    target, tuple(genes), declared_use=declared, dry_run=dry_run
                )
            )
        except StrchiveDraftError as exc:
            raise ToolError(str(exc)) from exc
        findings = [
            f"{locus}: published thresholds disagree ({why})"
            for locus, why in getattr(result, "contested", []) or []
        ]
        fractional = getattr(result, "fractional_ref_copies", 0)
        if fractional:
            findings.append(
                f"{fractional} locus/loci have a fractional reference copy count — the locus does "
                "not divide evenly into its repeat unit. A real property, not a rounding error."
            )
        if ctx:
            await ctx.report_progress(progress=2, total=2)
        return _draft_result(
            result,
            spec_dir=target,
            source="strchive",
            use=declared,
            dry_run=dry_run,
            findings=findings,
        )

    # The cost sentence is in the docstring rather than behind a flag because a caller can
    # weigh 47 minutes against what they are doing and a server-start flag cannot. Measured
    # upstream at 1,091 SNVs/s; a whole gene plus its +/-512 kb attribution flanks is ~3.1M
    # SNVs. That is why `chrom`/`start`/`end` exist and why this run did two 4 kb windows.
    @mcp.tool(
        task=True,
        annotations=ToolAnnotations(
            title="Fill expression_effects.csv from AlphaGenome",
            read_only_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
    )
    async def enrich_expression_effects(
        spec_dir: str,
        gene: str | None = None,
        rows: bool = False,
        chrom: str | None = None,
        start: int | None = None,
        end: int | None = None,
        min_score: float | None = None,
        max_rows: int = 50000,
        use: str = "non-commercial",
        dry_run: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> ExpressionReport:
        """Record AlphaGenome's predicted per-gene expression effects for an interval.

        One row per `(variant, gene)`: which way the variant moves that gene's predicted
        expression, how many of the tissue tracks agree on the sign, and how far it sits
        from the gene. It answers for **every scored variant in the window**, not just
        the ones your module authors — the distal ones are usually what the query was for.

        **CORPUS-SIZED, and the corpus is the interval rather than your rows.** A whole
        gene plus its attribution flanks is ~3.1M SNVs, about **47 minutes**; the cost is
        printed before the query runs. Pass `chrom`/`start`/`end` for a window — a 4 kb
        one is ~12,000 SNVs and takes seconds. `gene` is required, because the server-side
        gene filter is a requirement and not an optimisation. **`rows=true` aims the pass
        at the module instead**: windows are planned from variants.csv × resolution.csv,
        grouped by each row's own `gene` and chromosome, neighbours within 100 bp merged,
        ~21 bp each, and queried one after another at about two seconds a window
        (longevitymap: 377 windows for 1033 rows). `gene`, `chrom`, `start`, `end` are
        ignored. `row_status` then says per row whether it was
        scored; rows with no `gene` are reported, never given one. `dry_run` returns the
        plan and asks nothing.

        **This makes the module non-commercial and there is no way to run it otherwise.**
        AlphaGenome **Atlas** output is non-commercial-only, so `use` defaults to
        `non-commercial` and a run declaring anything else writes nothing. It lands an
        `alphagenome_atlas` row in licensing.csv with `commercial_use=false`, and the most
        restrictive term binds the whole artifact. `alphagenome_atlas` and
        `alphagenome_avi` are two sources with two licence classes; reading "AlphaGenome
        is permissive" off the AVI row and joining a table this wrote mis-licenses the
        module.

        **What comes back is not a clinical claim.** `effect_direction` is the sign of a
        predicted expression change. Raising a gene may be good, bad or neither, so the
        step from a direction to `risk`/`protective` on a variants.csv row is an authored
        judgement — surface it, log it with `record_override`, and say in the row's
        conclusion that no study grounds it. `directional_claims_without_studies` in
        `audit_module` will find such rows whether or not you say so.

        Needs `ALPHAGENOME_API_KEY` and the `atlas` extra. `offline=true` is a refusal
        rather than a no-op: this pass reads a live service and there is no snapshot lane.
        `dry_run=true` reports the cost and writes nothing. The sidecar is
        merge-not-clobber, so re-running never removes a row — delete the file to
        re-derive. Rank what it wrote with `top_expression_effects`.
        """
        target = resolve_dir(spec_dir, settings)
        declared = _check_use(use)
        # A rows-mode dry run is a plan read off local files and asks nothing, so it
        # answers under offline too; everything else below is egress.
        if rows and dry_run:
            return await _expression_for_rows(
                target,
                declared=declared,
                min_score=min_score,
                max_rows=max_rows,
                dry_run=True,
                ctx=ctx,
            )
        if offline_for(settings, offline):
            return ExpressionReport(
                success=False,
                spec_dir=str(target),
                gene=gene,
                warnings=[
                    "offline is in force, and this pass reads the AlphaGenome Atlas over the "
                    "network. There is no snapshot lane for it, so the question was not asked "
                    "rather than answered from a cache."
                ],
                next_step="Re-run without offline, or drop JMC_OFFLINE, if you meant to ask.",
            )

        if rows:
            return await _expression_for_rows(
                target,
                declared=declared,
                min_score=min_score,
                max_rows=max_rows,
                dry_run=dry_run,
                ctx=ctx,
            )
        if not gene:
            raise ToolError("Provide a gene, or rows=true to plan windows from the module's rows.")

        if ctx:
            await narrate(ctx, f"Querying the AlphaGenome Atlas for {gene} in {target.name}")
            await ctx.report_progress(progress=1, total=2)

        # Narrow-first: `ExpressionUnavailable` subclasses `ExpressionError`, so a
        # parent-first pair would make the outage arm dead code that raises nothing.
        # `tests/test_passes.py` walks the AST for exactly this.
        try:
            result = await run_sync(
                lambda: enrich_expression(
                    target,
                    gene,
                    chrom=chrom,
                    start=start,
                    end=end,
                    min_score=min_score,
                    max_rows=max_rows,
                    declared_use=declared,
                    write=not dry_run,
                )
            )
        except ExpressionUnavailable as exc:
            return ExpressionReport(
                success=False,
                spec_dir=str(target),
                gene=gene,
                warnings=[
                    str(exc),
                    "The Atlas could not be reached or no client could be built. Nothing was "
                    "written. Check ALPHAGENOME_API_KEY is set and that the `atlas` extra is "
                    "installed; this is an outage or a configuration gap, not a verdict on "
                    "the module.",
                ],
            )
        except ExpressionError as exc:
            return ExpressionReport(
                success=False,
                spec_dir=str(target),
                gene=gene,
                warnings=[
                    str(exc),
                    "Upstream writes expression_effects.csv BEFORE recording its licence row, so "
                    "a failure naming licensing.csv may still have left the data table on disk "
                    "(our F95, filed as format-tree S98). Check the file's row count before "
                    "re-running: the sidecar merges rather than clobbers, so a second run folds "
                    "the first one's rows in silently.",
                ],
            )

        interval = (
            f"{result.interval[0]}:{result.interval[1]}-{result.interval[2]}"
            if result.interval
            else None
        )
        on_disk = target / "expression_effects.csv"
        row_count = None
        if on_disk.is_file():
            with on_disk.open(newline="") as handle:
                row_count = sum(1 for _ in csv.DictReader(handle))
        return ExpressionReport(
            success=True,
            spec_dir=str(target),
            gene=result.gene or gene,
            interval=interval,
            dataset=result.dataset,
            candidates=result.candidates,
            written=result.written,
            rows=row_count,
            withheld=dict(result.withheld),
            accounts_for_every_candidate=result.accounts_for_every_candidate(),
            dry_run=dry_run,
            licence_note=(
                None
                if dry_run
                else (
                    "This module is now NON-COMMERCIAL. alphagenome_atlas is written into "
                    "licensing.csv with commercial_use=false, and the most restrictive term "
                    "binds the whole artifact regardless of what module_spec.yaml's `license:` "
                    "says. validate_module will report the disagreement and decline to "
                    "adjudicate it, which is correct — say which you meant in README.md."
                )
            ),
            warnings=list(result.warnings),
            next_step=(
                "Cost only; nothing was written. Drop dry_run to run it."
                if dry_run
                else "Rank these with top_expression_effects before authoring anything from them. "
                "A predicted direction is not a clinical direction: any variants.csv row you "
                "write from one is an authored judgement that needs record_override and a "
                "conclusion saying no study grounds it."
            ),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Rank expression_effects.csv",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def top_expression_effects(
        spec_dir: str,
        gene: str | None = None,
        min_consensus: float = 0.0,
        min_magnitude: float = 0.0,
        in_gene_only: bool = False,
        module_rows_only: bool = False,
        limit: int = 20,
    ) -> ExpressionRanking:
        """Read `expression_effects.csv` back, strongest predictions first. Offline.

        The pass answers for every scored variant in the window, so a 4 kb query returns
        ~12,000 rows and a gene-wide one millions. This is how an author finds the handful
        worth reading without paging through them: sorted by `|effect_size|`, filtered by
        track consensus, magnitude, gene, and optionally to variants inside the gene span.

        `module_rows_only=true` answers *which of MY variants does the model call
        disruptive*: it keeps only predictions for a `variants.csv` row's own gene and
        effect allele (the genotype's non-reference allele, placed via resolution.csv),
        and `row_status` says for every authored row whether it was scored and, if not,
        why. `direction_counts` is the tally to quote.

        `min_consensus` is `tracks_agreeing / tracks_total` — 1.0 is unanimous across the
        tissue tracks. **A row where no track agreed comes back with `effect_direction`
        null**, and those are counted in `direction_unknown` rather than dropped: a
        prediction with no direction is a real answer about the variant, not a gap.

        **Ranking is not endorsement.** The top row is the largest predicted expression
        change, which says nothing about whether the change matters clinically or which
        way it cuts. `rsid` being null is the common case here — the Atlas answers by
        coordinate — so check `lookup_variant` before calling anything novel.
        """
        target = resolve_dir(spec_dir, settings)
        path = target / "expression_effects.csv"
        if not path.is_file():
            return ExpressionRanking(
                spec_dir=str(target),
                total_rows=0,
                matched=0,
                returned=0,
                next_step=(
                    "expression_effects.csv is not here, so there is nothing to rank — which is "
                    "not the same as no effect being predicted. Run enrich_expression_effects."
                ),
            )
        with path.open(newline="") as handle:
            raw = list(csv.DictReader(handle))
        rows = report_rows(target) if module_rows_only else None

        def _f(row: dict, key: str) -> float | None:
            try:
                return float(row[key])
            except (KeyError, TypeError, ValueError):
                return None

        def _i(row: dict, key: str) -> int | None:
            try:
                return int(row[key])
            except (KeyError, TypeError, ValueError):
                return None

        ranked: list[tuple[float, RankedExpressionEffect]] = []
        unknown = 0
        directions: Counter[str] = Counter()
        for row in raw:
            if gene and (row.get("gene") or "").upper() != gene.upper():
                continue
            agreeing, total = _i(row, "tracks_agreeing"), _i(row, "tracks_total")
            consensus = (agreeing / total) if agreeing is not None and total else None
            effect = _f(row, "effect_size")
            distance = _i(row, "distance_to_gene")
            if consensus is not None and consensus < min_consensus:
                continue
            if effect is not None and abs(effect) < min_magnitude:
                continue
            if in_gene_only and distance != 0:
                continue
            if rows is not None and effect_key(row) not in rows.matched_keys:
                continue
            direction = (row.get("effect_direction") or "").strip()
            directions[direction or "unknown"] += 1
            if not direction:
                unknown += 1
            ranked.append(
                (
                    abs(effect) if effect is not None else -1.0,
                    RankedExpressionEffect(
                        chrom=row.get("chrom") or None,
                        start=_i(row, "start"),
                        ref=row.get("ref") or None,
                        alt=row.get("alt") or None,
                        rsid=row.get("rsid") or None,
                        gene=row.get("gene") or "",
                        effect_size=effect,
                        effect_direction=row.get("effect_direction") or None,
                        tracks_agreeing=agreeing,
                        tracks_total=total,
                        consensus=round(consensus, 4) if consensus is not None else None,
                        distance_to_gene=distance,
                    ),
                )
            )
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return ExpressionRanking(
            spec_dir=str(target),
            total_rows=len(raw),
            genes=sorted({(row.get("gene") or "") for row in raw} - {""}),
            matched=len(ranked),
            returned=min(limit, len(ranked)),
            direction_unknown=unknown,
            direction_counts=dict(sorted(directions.items())),
            row_status=(
                {status: rows.status.get(status, 0) for status in ROW_STATUSES}
                if rows is not None
                else None
            ),
            row_examples=rows.examples if rows is not None else {},
            effects=[effect for _, effect in ranked[:limit]],
            next_step=(
                "A large predicted effect is a reason to READ the variant, not a role to assign "
                "it. Check whether an rsID already describes it with lookup_variant, and if you "
                "author a row from one of these, its direction is your judgement rather than "
                "AlphaGenome's — say so in the conclusion and log it with record_override."
            ),
        )


async def _expression_for_rows(
    target: Path,
    *,
    declared: str,
    min_score: float | None,
    max_rows: int,
    dry_run: bool,
    ctx: Context | None,
) -> ExpressionReport:
    """The AlphaGenome pass over the module's own positions, one window at a time (F105).

    Stops at the first window that fails, because a failure may have left rows on disk
    (F95) and a merge-not-clobber sidecar folds a retry's rows in silently. What ran is
    reported, and `row_status` is read off the sidecar as it now stands.
    """
    windows = plan_windows(module_sites(target)[0])
    planned = len(windows)
    candidates = written = 0
    withheld: Counter[str] = Counter()
    warnings: list[str] = []
    datasets: set[str] = set()
    ran = 0
    failed = False
    if not dry_run:
        for gene, chrom, start, end in windows:
            if ctx:
                await narrate(ctx, f"Window {ran + 1}/{planned}: {gene} {chrom}:{start}-{end}")
                await ctx.report_progress(progress=ran, total=planned)
            try:
                result = await run_sync(
                    lambda g=gene, c=chrom, s=start, e=end: enrich_expression(
                        target,
                        g,
                        chrom=c,
                        start=s,
                        end=e,
                        min_score=min_score,
                        max_rows=max_rows,
                        declared_use=declared,
                        write=True,
                    )
                )
            except ExpressionUnavailable as exc:
                warnings += [
                    f"{gene} {chrom}:{start}-{end}: {exc}",
                    "The Atlas is unreachable "
                    "or unconfigured (ALPHAGENOME_API_KEY, the `atlas` extra); stopped.",
                ]
                failed = True
                break
            except ExpressionError as exc:
                warnings += [
                    f"{gene} {chrom}:{start}-{end}: {exc}",
                    "Stopped at this window: a "
                    "failure may have left rows on disk (F95), and a retry would fold "
                    "them in silently. Check expression_effects.csv before re-running.",
                ]
                failed = True
                break
            ran += 1
            candidates += result.candidates or 0
            written += result.written or 0
            withheld.update(dict(result.withheld))
            warnings += [f"{gene} {chrom}:{start}-{end}: {w}" for w in result.warnings]
            if result.dataset:
                datasets.add(result.dataset)
    report = report_rows(target)
    if not planned:
        warnings.append(
            "No window was planned: no row has a gene, a coordinate and a known non-reference "
            "allele together. row_status says which is missing; nothing was asked."
        )
    on_disk = target / "expression_effects.csv"
    rows_on_disk = None
    if on_disk.is_file():
        with on_disk.open(newline="") as handle:
            rows_on_disk = sum(1 for _ in csv.DictReader(handle))
    return ExpressionReport(
        success=not failed,
        spec_dir=str(target),
        dataset=", ".join(sorted(datasets)) or None,
        candidates=None if dry_run else candidates,
        written=None if dry_run else written,
        rows=rows_on_disk,
        withheld=dict(sorted(withheld.items())),
        accounts_for_every_candidate=(
            None
            if dry_run or failed or not planned
            else candidates == written + sum(withheld.values())
        ),
        dry_run=dry_run,
        windows=planned,
        windows_run=ran,
        row_status={status: report.status.get(status, 0) for status in ROW_STATUSES},
        row_examples=report.examples,
        licence_note=(
            None
            if dry_run or not ran
            else (
                "This module is now NON-COMMERCIAL: alphagenome_atlas is in licensing.csv with "
                "commercial_use=false, and the most restrictive term binds the whole artifact."
            )
        ),
        warnings=warnings,
        next_step=(
            "Nothing to ask the Atlas for. Read row_status: a row needs a gene, a coordinate "
            "(enrich_module fills resolution.csv) and a genotype with a non-reference allele."
            if not planned
            else f"Plan only: {planned} window(s), about {planned * 2} s at ~2 s each. Drop "
            "dry_run to run it."
            if dry_run
            else "Read the scored rows with top_expression_effects(module_rows_only=true). A "
            "predicted direction is not a clinical direction: a variants.csv role written from "
            "one is an authored judgement that needs record_override."
        ),
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
