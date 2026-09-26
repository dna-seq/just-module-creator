"""ESSENTIALS (network) — put a question to a registry, and record that it was put.

Split out of ``research.py`` under `RM9`. That module opens by promising that
**no tool in it writes to a spec directory**, and the promise was true, load-bearing
and quietly costing something: a check that leaves no trace is indistinguishable, to
everyone downstream, from a check nobody ran.

The alternative was to narrow the promise to "writes no authored cell" — upstream's
own wording. It was rejected deliberately: a module whose opening sentence is a
literal claim keeps it literal, and a boundary a reader can rely on beats one
qualified by an exception. **Nothing about the tiers moved with the split.** The tier
line is cost, not read-versus-write, and a check bounded by one spec directory is
cheap, so these stay essentials.

**What gets written is an attestation, never a value.** `verification.json` records
that the question was put and over how many rows. It is not a cell, not a
correction, and not a pass — a green record says the comparison ran, and says
nothing about whether the answer was right. The distinction is the whole reason the
file exists: `RM45`/`RM72` upstream, and `F33`'s shape here, where our own pin was
what kept an author off a surface that already worked.

Three rules inherited from the enricher's own CLI, each of which looks like an
oversight until it is read as a decision:

* **A check that does not APPLY is not a check that was skipped.** A module with no
  `variants.csv` has no gene or trait for these checks to have an opinion about.
  Recording one would mine a nonce and create a `verification.json` on a module that
  never asked for one, so nothing is written and the report says why.
* **An outage is attested too, and that is the run where it matters most.** When the
  registry never answers, the report comes back empty — and an empty report with no
  record reads exactly like a clean one. `unreachable_records` is what keeps those
  apart.
* **One call for every record.** The proof-of-work binds the whole document, so a
  per-check write would pay it three times for one guarantee.
"""

from __future__ import annotations

import json
from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_enricher.acmg import (
    AcmgListUnavailable,
    AcmgReport,
    AcmgSfError,
    verify_acmg_sf,
)
from just_dna_enricher.acmg import verification_record as acmg_record
from just_dna_enricher.clinpgx import ClinPgxEnrichmentError, enrich_clinpgx
from just_dna_enricher.identifiers import (
    IdentifierUnavailable,
    unreachable_records,
    verification_records,
)
from just_dna_enricher.identifiers import (
    check_identifiers as _check_identifiers,
)
from just_dna_enricher.licensing import LicenseRefusal
from just_dna_enricher.litvar import LitvarError
from just_dna_enricher.litvar import check_literature_coverage as check_literature_coverage_
from just_dna_enricher.litvar import verification_records as litvar_records
from just_dna_enricher.pgx import PgxEnrichmentError, enrich_pgx
from just_dna_enricher.strchive import (
    REPEAT_ALLELES_CSV,
    StrchiveError,
    format_group_key,
)
from just_dna_enricher.strchive import check_repeat_bands as check_repeat_bands_
from just_dna_enricher.verification import record_verification
from just_dna_enricher.verification import skipped as acmg_skipped
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    AcmgReportModel,
    AcmgVerdictRow,
    BandDifference,
    ClinPgxCheckReport,
    EvidenceConflictRow,
    FunctionConflictRow,
    IdentifierReport,
    IdentifierStatus,
    IdentifierTally,
    LiteratureCoverageReportModel,
    LocusCoverageRow,
    PgxCheckReport,
    RepeatBandReport,
)
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import normalize_declared_use, offline_for, resolve_dir

log = get_logger()

#: Why no attestation was written. Never an empty string — a caller reading
#: `attested=false` is owed the reason in the same breath, because "did not apply"
#: and "the write failed" are different facts about the module.
NOT_APPLICABLE = (
    "no variants.csv — the check does not apply, which is not a skip, so no "
    "verification.json was created"
)


#: The states that mean "this identifier is current". Everything else is flagged —
#: including `unchecked`, a trait whose prefix this check cannot resolve, because a
#: check that could not run is not a check that passed.
#:
#: **One predicate, three consumers.** The `stale` summary, the filtered rosters and
#: the counts all read `_flagged` below. Two of them restating the same set is how a
#: counted claim and the list it counts drift apart, which is the shape this file's own
#: history is full of.
#: `known` is the PGS Catalog's clean state, and it joins the ontology ones rather than
#: getting a predicate of its own: no gene or trait verdict can be `known`, so one
#: `_flagged` still answers for all three halves. Without it every PGS row would read as
#: needing attention — the tally would be honest about nothing.
_CURRENT_STATES = frozenset({"approved", "current", "known"})


def _flagged(status: IdentifierStatus) -> bool:
    """Whether this verdict needs somebody's attention."""
    return status.state not in _CURRENT_STATES


def _tally(statuses: list[IdentifierStatus], asked: bool) -> IdentifierTally:
    """Counts for one half — all null when the half was not asked.

    `asked=False` is not `checked=0`: one says nothing was established about the genes
    in this module, the other says the module has none. Collapsing them would let a
    narrowed run read as a clean one.
    """
    if not asked:
        return IdentifierTally()
    flagged = sum(1 for s in statuses if _flagged(s))
    return IdentifierTally(checked=len(statuses), clean=len(statuses) - flagged, flagged=flagged)


def _statuses(report: object) -> tuple[list[IdentifierStatus], list[IdentifierStatus]]:
    """Upstream's two report halves, projected field-for-field."""
    genes = [
        IdentifierStatus(
            identifier=g.symbol,
            kind="gene",
            state=g.state,
            current=g.current,
            label=g.hgnc_id,
        )
        for g in getattr(report, "genes", []) or []
    ]
    traits = [
        IdentifierStatus(
            identifier=t.curie,
            kind="trait",
            state=t.state,
            current=t.replaced_by,
            label=t.label,
        )
        for t in getattr(report, "traits", []) or []
    ]
    return genes, traits


def _pgs_statuses(report: object) -> list[IdentifierStatus]:
    """The PGS half, projected into the same shape as the other two.

    **This half was running and reaching nobody.** Upstream's `check_identifiers` takes
    `check_pgs=True` by default and `verification_records` writes a PGS record on the same
    default — so before this existed the module was attested as having had its accessions
    checked while the answer reached no field of ours. An attestation for a check whose
    result the caller never sees is worse than not running it.
    """
    return [
        IdentifierStatus(
            identifier=s.pgs_id,
            kind="pgs",
            state=s.state,
            current=None,
            label=s.name,
        )
        for s in getattr(report, "pgs", []) or []
    ]


def _pgs_drift_lines(report: object) -> list[str]:
    """One sentence per drifted cell, in upstream's own terms.

    Named rather than corrected: the Catalog re-releases, so a disagreement may be the
    module being current against a record that moved under it.
    """
    comparison = getattr(report, "pgs_metadata", None)
    return [
        f"{d.pgs_id} {d.field_name}: authored {d.authored!r}, the Catalog now publishes "
        f"{d.published!r}"
        for d in (getattr(comparison, "drift", []) or [])
    ]


def _attest(records: list, target: Path) -> tuple[bool, str | None]:
    """Write the records, and report a failed write rather than losing the check.

    The check itself already succeeded and its findings are in hand. An attestation
    failure must not be raised as though the check had failed — that would tell the
    author about the wrong problem, which is the distinction the enricher's own
    "CHECKED, BUT NOT ATTESTED" message exists to draw. `OSError` sits beside the
    translated error because `record_verification` translates only a sidecar
    collision, so a read-only spec directory arrives untranslated.
    """
    try:
        record_verification(records, target, error=ToolError)
    except (ToolError, OSError) as exc:
        log.warning("checked, but not attested: %s", exc)
        return False, f"the check ran and is reported above; writing the record failed: {exc}"
    return True, None


def _recorded(target: Path, check: str) -> bool:
    """Whether `verification.json` now carries a record for `check`.

    The two PGx passes attest themselves — `pgx._attest` and `clinpgx._attest` write
    the file on `write=True` — so the wrapper must not write a second record. What it
    can honestly report is what is on disk afterwards, read back rather than inferred
    from the call having returned: a pass that declined to mint a record on a module
    with nothing in scope returns normally and leaves the file untouched.
    """
    path = target / "verification.json"
    if not path.exists():
        return False
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return any(r.get("check") == check for r in document.get("records", []) if isinstance(r, dict))


def _by_gene(verdicts: object) -> list[AcmgVerdictRow]:
    """Upstream's own gene grouping, projected.

    `AcmgReport.by_gene` yields `(gene, rows, message)`; every verdict is a statement
    about a gene, so a per-row list would print one sentence once per variant in it.
    That is §5's aggregate-repeated-warnings rule, and upstream already does the
    grouping — re-deriving it here would put a second wording in front of one finding.
    """
    return [
        AcmgVerdictRow(gene=gene, rows=list(rows), message=message)
        for gene, rows, message in AcmgReport.by_gene(verdicts)  # type: ignore[arg-type]
    ]


def _acmg_next_step(
    report: object, mismatches: list[AcmgVerdictRow], unverifiable: list[AcmgVerdictRow]
) -> str:
    """What the author has to decide, with the stale-list case named first."""
    if unverifiable:
        return (
            f"{len(unverifiable)} gene(s) disagree in a way the list cannot settle — read "
            "these first. ACMG republishes, so the module may be current against a list "
            "that moved under it; conforming a row to a stale archive is the failure this "
            "check must not cause. `record_override` is what keeps the reason when a row "
            "outranks the list."
        )
    if mismatches:
        return (
            f"{len(mismatches)} gene(s) state an acmg_sf the list disagrees with. Nothing "
            "was written: check both sides, because the row may be right and the archive "
            "behind. A change here is a decision, not a repair."
        )
    if not getattr(report, "version", None):
        return (
            "No list version was recorded, so nothing was actually compared — that is not "
            "a pass. Read `skipped` and `warnings`."
        )
    return "Every stated acmg_sf agrees with the list, and verification.json records it."


def register_checks(mcp: FastMCP, settings: Settings) -> None:
    """Register the checks that put a question and record having put it."""

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Check identifiers",
            # It writes `verification.json` — an attestation, never an authored
            # cell. Claiming read-only here would be the same lie the split exists
            # to avoid.
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_identifiers(
        spec_dir: str,
        check_genes: bool = True,
        check_traits: bool = True,
        check_pgs: bool = True,
        detail: bool = False,
    ) -> IdentifierReport:
        """Check every gene symbol (HGNC), trait CURIE (OLS4) and `pgs_id` (PGS Catalog) is current.

        Reports rather than corrects: rewriting an authored value would destroy the
        evidence that the identifier moved, and a rename is exactly the kind of
        change an author needs to see rather than inherit. What it *does* write is
        `verification.json` — an attestation that the checks ran and over how many
        rows, never a value. A consumer holding the artifact has no other way to
        tell "asked and clean" from "never asked".

        `check_genes`, `check_traits` and `check_pgs` are recorded in the attestation,
        so narrowing a run narrows what the record claims. Turning one off does not
        make its half pass — it makes the record say it was not asked.

        **The PGS half answers three ways and `unrecognised` is the interesting one**:
        the Catalog holds no score under that accession, which is a different finding
        from a malformed one. `pgs_drift` names authored cells the Catalog now publishes
        differently — not applied, because the Catalog re-releases and the row may be
        the current side. `pgs_check_skipped` is separate from the gene and trait halves
        on purpose: an outage at the Catalog says nothing about HGNC or OLS4.

        **The verdict is the answer; the roster is the raw material.** By default
        `genes` and `traits` carry only the records that need attention, and
        `gene_tally` / `trait_tally` say how many were checked and how many agreed.
        A clean real module measured 325 gene records at roughly 95 characters each,
        every one of them `approved`, to report an empty `stale` — so the interesting
        fields arrived last, after 30 kB of agreement. Pass `detail=true` for the full
        roster when you actually want to read it. Nothing else changes with the flag:
        the same check runs, the same attestation is written, and the counts hold
        either way.

        **`gene_locus_conflicts` is the one to read even when `stale` is empty.**
        It names rows whose gene sits on a different chromosome than the row's own
        variant — a relationship that is false while both halves are individually
        true, so no per-identifier check can catch it. That pairing is what a
        machine-written summary produces: a real symbol beside an invented rsID
        that resolves anyway. And an empty list only means "nothing disagreed"
        while `gene_locus_check_skipped` is null; otherwise the comparison never
        ran, which is not a pass.
        """
        target = resolve_dir(spec_dir, settings)

        # Everything decidable WITHOUT a network is decided first, and the offline
        # ceiling comes after. Same order `registry_publish` uses for its naming
        # refusal and for the same reason: answering "you are offline" to a call
        # that could never have succeeded sends the caller to fix the wrong thing.
        if not check_genes and not check_traits and not check_pgs:
            raise ToolError(
                "All three halves are off, so there is no question to put. Enable check_genes, "
                "check_traits or check_pgs — an attestation for a check nobody asked for would "
                "assert nothing."
            )

        # The enricher's own rule, and it is a decision rather than a guard: a module
        # with no `variants.csv` has no gene or trait for this to have an opinion
        # about, so the check does not apply. Writing a record would create a
        # `verification.json` on a module that never asked for one.
        #
        # **Returned early rather than checked after the call**, which is what the
        # first version got wrong: `check_identifiers` raises `ValueError` on a
        # missing file, so computing this and calling anyway produced a raw
        # traceback instead of the considered answer. Found by running the tool on
        # a module with no `variants.csv`; the enricher's own CLI returns early here
        # for the same reason.
        if not (target / "variants.csv").exists():
            return IdentifierReport(
                spec_dir=str(target),
                # Every count null rather than zero: the check did not apply, so
                # nothing was established about this module's genes or traits — which
                # is a different claim from "it has none".
                gene_tally=_tally([], asked=False),
                trait_tally=_tally([], asked=False),
                genes=[],
                traits=[],
                stale=[],
                gene_locus_conflicts=[],
                gene_locus_check_skipped=None,
                pgs_tally=_tally([], asked=False),
                pgs=[],
                pgs_drift=[],
                pgs_release=None,
                pgs_check_skipped=None,
                attested=False,
                attestation_note=NOT_APPLICABLE,
                detail=detail,
            )

        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE); this check needs HGNC and OLS4."
            )

        try:
            report = await run_sync(
                lambda: _check_identifiers(
                    spec_dir=target,
                    check_traits=check_traits,
                    check_genes=check_genes,
                    check_pgs=check_pgs,
                )
            )
        except ValueError as exc:
            # A `variants.csv` present but unreadable. Nothing is attested: there are
            # no bytes for an attestation to bind to and no question was reached,
            # which is the enricher's own reasoning on this path.
            raise ToolError(
                f"The rows could not be read, so no identifier check was put: {exc}"
            ) from exc
        except IdentifierUnavailable as exc:
            # The run a reader most needs a record for: the report would be empty, and
            # an empty report with no attestation reads exactly like a clean one.
            _attest(
                unreachable_records(
                    check_traits=check_traits, check_genes=check_genes, detail=str(exc)
                ),
                target,
            )
            raise ToolError(
                f"The identifier registries did not answer: {exc}. This is unreachable, not "
                f"absent — nothing about these identifiers has been established."
            ) from exc

        genes, traits = _statuses(report)
        attested, note = _attest(
            verification_records(
                report,
                check_traits=check_traits,
                check_genes=check_genes,
                check_pgs=check_pgs,
            ),
            target,
        )

        pgs = _pgs_statuses(report)
        stale = [
            f"{s.kind} {s.identifier}: {s.state}" + (f" -> {s.current}" if s.current else "")
            for s in genes + traits + pgs
            if _flagged(s)
        ]
        return IdentifierReport(
            spec_dir=str(target),
            # Counted off the FULL rosters, before either is trimmed below, so the
            # numbers describe the check rather than the answer's shape.
            gene_tally=_tally(genes, asked=check_genes),
            trait_tally=_tally(traits, asked=check_traits),
            genes=genes if detail else [g for g in genes if _flagged(g)],
            traits=traits if detail else [t for t in traits if _flagged(t)],
            stale=stale,
            # `str(conflict)` is upstream's own sentence, which already says which
            # chromosome each half claims and what to do about it. Reformatting it
            # here would put a second wording in front of one finding.
            gene_locus_conflicts=[str(c) for c in getattr(report, "gene_loci", []) or []],
            gene_locus_check_skipped=getattr(report, "gene_loci_not_checked", None),
            pgs_tally=_tally(pgs, asked=check_pgs),
            pgs=pgs if detail else [s for s in pgs if _flagged(s)],
            pgs_drift=_pgs_drift_lines(report),
            pgs_release=getattr(report, "pgs_release", None),
            # `pgs_not_checked` is a `(reason, detail)` pair upstream; the detail sentence
            # already names how many accessions had been answered when it stopped, so it
            # is carried rather than re-worded.
            pgs_check_skipped=(
                (getattr(report, "pgs_not_checked", None) or (None, None))[1] or None
            ),
            attested=attested,
            attestation_note=note,
            detail=detail,
        )

    # ----------------------------------------------------------------------- #
    # ACMG secondary findings
    # ----------------------------------------------------------------------- #
    # Wrapped 0.35.0. It is upstream's `check-acmg` and it was reachable here only as
    # `registry_check(acmg=True)` — a registry round-trip, a `target` and a token, to
    # answer a question about a directory on this disk. That is the shape §"Parity"
    # names: the surface knew the check existed and gave an author no way to run it.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Check acmg_sf against the ACMG secondary-findings list",
            readOnlyHint=False,  # writes verification.json — an attestation, not a cell
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_acmg(
        spec_dir: str,
        offline: bool = False,
        sf_list: str | None = None,
    ) -> AcmgReportModel:
        """Check every authored `acmg_sf` against the ACMG secondary-findings list.

        Reports and never fills: `acmg_sf` is an authored cell this asks a registry
        about, so writing it from the list would make the check compare the list with
        itself and agree perfectly. What it writes is `verification.json` — the record
        that the question was put and over how many rows, never a value.

        **Read `unverifiable` before `mismatches`.** ACMG republishes, so a
        disagreement the list cannot settle may be the module being current against an
        archive that moved under it. A mismatch is a decision for a pilot, not a repair
        to apply.

        `sf_list` points at a built ACMG snapshot directory; omit it and a snapshot in
        `$JUST_DNA_ACMG_CACHE` (or the shared cache base) is used, falling back to
        scraping NCBI's page, which still serves v3.2. `provision_caches` builds the
        lane — it is one of the five nobody may publish, since the list is Elsevier
        supplementary material. `offline` needs `sf_list`, or nothing is checked and
        `skipped` says so.
        """
        target = resolve_dir(spec_dir, settings)
        if not (target / "variants.csv").exists():
            return AcmgReportModel(
                spec_dir=str(target),
                attested=False,
                attestation_note=NOT_APPLICABLE,
                skipped="no variants.csv, so no row states an acmg_sf to check",
            )

        eff_offline = offline_for(settings, offline)
        snapshot = resolve_dir(sf_list, settings) if sf_list else None
        try:
            report = await run_sync(
                lambda: verify_acmg_sf(
                    spec_dir=target,
                    mode="best_effort",
                    offline=eff_offline,
                    snapshot_dir=snapshot,
                )
            )
        except AcmgListUnavailable as exc:
            # The one failure here that is a SKIP: the check applies and did not run,
            # so upstream's own skip record is written rather than silence. An empty
            # report with no record reads exactly like a clean one.
            attested, note = _attest(
                [acmg_skipped("acmg_secondary_findings", exc.skip, detail=str(exc), source="acmg")],
                target,
            )
            return AcmgReportModel(
                spec_dir=str(target),
                attested=attested,
                attestation_note=note,
                skipped=str(exc),
                next_step=(
                    "No list was obtained, so nothing was compared — this is not a pass. "
                    "`provision_caches` builds the `acmg` lane from the workbook that "
                    "ships with just-dna-format, or pass `sf_list` to a built snapshot."
                ),
            )
        except AcmgSfError as exc:
            # Nothing attested: a module whose rows will not load has no bytes for an
            # attestation to bind to. Upstream's sentence is the answer.
            raise ToolError(f"the ACMG check could not run: {exc}") from exc

        attested, note = _attest([acmg_record(report)], target)
        mismatches = _by_gene(report.mismatches)
        unverifiable = _by_gene(report.unverifiable)
        # `AcmgReport.clean` is a `Verdict` since enricher 0.7.1 (our `S100`): falsy when
        # it carries a code, and `offline` is a code, so a run that read no list is a
        # `no` upstream — a gate has to pick an exit status. This is not a gate, so the
        # house tri-state holds here: no list read is `null`, never `false`, and
        # `not_consulted` is upstream's own word for which arm that was.
        read_a_list = report.not_consulted != "offline"
        return AcmgReportModel(
            spec_dir=str(target),
            version=report.version,
            checked=report.checked if read_a_list else None,
            clean=bool(report.clean) if read_a_list else None,
            skipped=(
                None
                if read_a_list
                else (
                    "no ACMG secondary-findings list was obtained, so every row is "
                    "unchecked and nothing was compared — not a pass. `provision_caches` "
                    "builds the `acmg` lane, or pass `sf_list` to a built snapshot."
                )
            ),
            mismatches=mismatches,
            unverifiable=unverifiable,
            notes=_by_gene(report.notes),
            warnings=list(report.warnings),
            attested=attested,
            attestation_note=note,
            next_step=_acmg_next_step(report, mismatches, unverifiable),
        )

    # ----------------------------------------------------------------------- #
    # Repeat bands
    # ----------------------------------------------------------------------- #
    # Wrapped 0.35.0, and the pairing is why it is a bug rather than a gap: we ship
    # `draft_from_strchive` to WRITE `repeat_alleles.csv` and shipped nothing to check
    # one. A drafter with no checker is the surface teaching a step it cannot finish.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Check repeat bands against STRchive",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=False,  # reads a provisioned snapshot; no request of its own
        ),
    )
    async def check_repeat_bands(spec_dir: str, catalogue: str | None = None) -> RepeatBandReport:
        """Compare `repeat_alleles.csv`'s bands against STRchive's, and report what differs.

        **A difference never fails anything and is never applied.** Where a catalogue
        and an expert author draw a repeat threshold in different places, both are
        claims by an authority — so this reports and the compile does not care.

        **Read `compared` before `findings`.** It is the denominator: an empty findings
        list beside an empty `compared` means nothing was checked, which is a different
        answer from everything agreeing. `withheld` names groups the catalogue holds no
        band for, and `contested` the groups where the two disagree.

        The catalogue's `pathogenic_max` is reported as its own finding and never
        written: it is the longest allele the literature records, not a clinical
        ceiling, and a module importing it would silently answer nothing for a longer
        one. `catalogue` points at a built STRchive snapshot or a `STRchive-loci.json`;
        omit it and the provisioned lane is used — `provision_caches` builds it, MIT.
        """
        target = resolve_dir(spec_dir, settings)
        if not (target / REPEAT_ALLELES_CSV).exists():
            return RepeatBandReport(
                spec_dir=str(target),
                attested=False,
                attestation_note=(
                    f"no {REPEAT_ALLELES_CSV} — the check does not apply, which is not a "
                    "skip, so no verification.json was created"
                ),
                next_step=(
                    f"This module authors no {REPEAT_ALLELES_CSV}. `draft_from_strchive` "
                    "writes one from the same catalogue this would check it against."
                ),
            )

        source = resolve_dir(catalogue, settings) if catalogue else None
        try:
            # `write=True` is upstream's own attestation, written where the check ran.
            result = await run_sync(
                lambda: check_repeat_bands_(target, catalogue=source, mode="best_effort")
            )
        except StrchiveError as exc:
            raise ToolError(
                f"the repeat-band check could not run: {exc}. A missing catalogue is the "
                "usual cause — `provision_caches` builds the `strchive` lane, or pass "
                "`catalogue` to a built snapshot."
            ) from exc

        # `format_group_key` is upstream's, not `str(tuple)`: its docstring says the
        # rendered string is an API — `compile_module` copies these warnings into
        # `manifest.compilation.warnings` and a catalog reindexing has nothing else — so
        # rendering a key our own way would put a second spelling into somebody's report.
        # `str(finding)` is the whole sentence for the same reason.
        findings = [
            BandDifference(
                kind=f.kind,
                group_key=format_group_key(f.group_key),
                locus_id=f.locus_id,
                value=None if f.value is None else str(f.value),
                source_value=None if f.source_value is None else str(f.source_value),
                detail=str(f),
            )
            for f in result.findings
        ]
        return RepeatBandReport(
            spec_dir=str(target),
            compared=[format_group_key(g) for g in result.compared],
            withheld=[f"{format_group_key(key)}: {why}" for key, why in result.withheld],
            contested=["/".join(str(part) for part in key) for key in result.contested],
            findings=findings,
            warnings=list(result.warnings),
            mode=result.mode,
            dataset=result.dataset,
            attested=True,
            next_step=(
                f"{len(findings)} band difference(s) over {len(result.compared)} group(s) "
                "compared. Neither side is authoritative and nothing here fails a compile: "
                "a band you set deliberately stays. Change one only on evidence that "
                "outranks the catalogue, and `record_override` is what keeps the reason."
                if findings
                else f"{len(result.compared)} group(s) compared and no band differs."
                if result.compared
                else "Nothing was compared — read `withheld` and `warnings`. An empty "
                "findings list here is not agreement."
            ),
        )

    # ----------------------------------------------------------------------- #
    # LitVar coverage
    # ----------------------------------------------------------------------- #
    # Wrapped 0.35.0; new in enricher 0.7 and unwrapped until now.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Which papers a variant-literature index holds per locus",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_literature_coverage(
        spec_dir: str,
        offline: bool = False,
        detail: bool = False,
    ) -> LiteratureCoverageReportModel:
        """Report LitVar's literature coverage per locus, naming the tier that answered.

        **It answers *which papers discuss an allele that is already identified*. It
        does not answer *which allele a name meant*** — those read as the same question
        and are not. Measured upstream against two of the hardest records available
        (CIViC 1955 and 2131, four candidate alleles with registered CAIDs), the index
        returns no node for any of them: PubTator3 mines titles and abstracts, and
        those alleles live in a table inside a paywalled paper. Do not reach for this
        to recover an identity — `lookup_allele_identity` is that tool.

        Writes no row and no `sources.csv` entry, so the module does not *use* this
        source; what it writes is the attestation that the question was put. **Read
        `answered` as the denominator**: `total_loci - answered` were never established
        either way, and an `offline` run answers none of them, so a coverage number
        from one measures nothing.

        `position_only_residue` is the number worth reading — papers on a position node
        and on no allele node, meaning the index knows the site and not the allele.
        `detail=true` returns the per-locus rows; the summary holds otherwise.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        try:
            report = await run_sync(lambda: check_literature_coverage_(target, offline=eff_offline))
        except (ValueError, LitvarError) as exc:
            raise ToolError(f"the literature-coverage check could not run: {exc}") from exc

        attested, note = _attest(list(litvar_records(report)), target)
        tiers: dict[str, int] = {}
        for locus in report.loci:
            tiers[locus.tier or "unchecked"] = tiers.get(locus.tier or "unchecked", 0) + 1
        answered = len(report.answered)
        return LiteratureCoverageReportModel(
            spec_dir=str(target),
            total_loci=len(report.loci),
            answered=answered,
            offline=report.offline,
            tiers=dict(sorted(tiers.items())),
            position_only_residue=report.position_only_residue,
            degraded=[str(locus.rsid) for locus in report.degraded if locus.rsid],
            tables_read=list(report.tables_read),
            tables_not_read=dict(report.tables_not_read),
            loci=(
                [
                    LocusCoverageRow(
                        rsid=locus.rsid,
                        tier=locus.tier,
                        asked_tier=locus.asked_tier,
                        reason=locus.reason,
                        allele_pmids=locus.allele_pmids,
                        position_pmids=locus.position_pmids,
                        position_only_pmids=locus.position_only_pmids,
                        node_id=locus.node_id,
                    )
                    for locus in report.loci
                ]
                if detail
                else []
            ),
            attested=attested,
            attestation_note=note,
            next_step=(
                "Every locus is `unchecked` because the run was offline — that is not "
                "coverage of zero, it is no measurement. Re-run with the ceiling clear."
                if report.offline
                else f"{answered} of {len(report.loci)} loci were answered. PMIDs found "
                "here are candidates: take each one through `lookup_citation` before it "
                "reaches a row, because existence never settles identity."
            ),
        )

    # ----------------------------------------------------------------------- #
    # PGx: allele function against PharmVar and CPIC
    # ----------------------------------------------------------------------- #
    # Wrapped 0.36.0 (F101). `module-check` taught `just-dna-enricher pgx` as a bare CLI
    # line beside four tools, and eleven of a thirteen-module PGx run had no in-surface
    # way to run the one check that reads `function_status` back against an authority.
    # `mode` is deliberately not exposed: upstream stores it and never reads it, so a
    # `strict` here would advertise a gate that does not exist (the guide's ROADWORKS).
    # Upstream attests itself, so `_attest` is not called — see `_recorded`.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Check allele functions against PharmVar and CPIC",
            readOnlyHint=False,  # licensing.csv rows and verification.json, never a cell
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_pgx(
        spec_dir: str,
        use: str,
        offline: bool = False,
        pharmvar: bool = True,
        cpic: bool = True,
    ) -> PgxCheckReport:
        """Compare every authored `function_status` with PharmVar's and CPIC's, and report.

        **Reads `allele_function.csv` and `haplotypes.csv`, and never opens
        `diplotypes.csv`** — a green run says nothing about a diplotype's phenotype.
        A difference is reported and never applied: the two authorities disagree with
        each other, and a module drafted from CPIC is compared against its own source
        on that leg, which upstream names (`tautology`) rather than counting as
        agreement. Read `compared` as the denominator and `routes` for who answered.

        **`use` is required**: both sources carry a no-sale clause, so `unstated` skips
        them and `commercial` is refused. Each leg reads a built snapshot first and
        goes live only when there is none and the ceiling is clear; PharmVar live needs
        `PHARMVAR_API_KEY`. `offline` with no snapshot is a skip with a reason in
        `skipped_offline`, never a pass. Writes a `licensing.csv` row per source
        consulted and the `allele_function` record in `verification.json`.
        """
        declared = normalize_declared_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        try:
            result = await run_sync(
                lambda: enrich_pgx(
                    target,
                    mode="best_effort",
                    offline=eff_offline,
                    declared_use=declared,
                    use_pharmvar=pharmvar,
                    use_cpic=cpic,
                    write=True,
                )
            )
        except (PgxEnrichmentError, LicenseRefusal) as exc:
            raise ToolError(f"the PGx allele-function check could not run: {exc}") from exc

        conflicts = [
            FunctionConflictRow(
                gene=c.gene,
                allele=c.allele,
                authored=c.authored,
                reported=c.reported,
                source=c.source,
            )
            for c in result.conflicts
        ]
        answered = sorted(result.routes)
        return PgxCheckReport(
            spec_dir=str(target),
            compared=result.compared,
            conflicts=conflicts,
            routes=dict(result.routes),
            skipped=list(result.skipped),
            skipped_offline=list(result.skipped_offline),
            warnings=list(result.warnings),
            licence_rows=len(result.rows),
            declared_use=result.declared_use,
            attested=_recorded(target, "allele_function"),
            next_step=(
                f"{len(conflicts)} allele function(s) differ from {', '.join(answered)}. "
                "Neither side is authoritative: check both, and change a cell only on "
                "evidence that outranks the source — `record_override` keeps the reason."
                if conflicts
                else f"{result.compared} authored function(s) compared against "
                f"{', '.join(answered)} and none differs."
                if result.compared
                else "Nothing was compared — read `skipped`, `skipped_offline` and "
                "`warnings`. An empty conflicts list here is not agreement."
            ),
        )

    # ----------------------------------------------------------------------- #
    # PGx: evidence levels against the ClinPGx snapshot
    # ----------------------------------------------------------------------- #
    # Wrapped 0.36.0 (F101), the pairing of `draft_from_clinpgx`: a drafter shipped
    # with no checker. Unlike the drafter, `snapshot` is optional here because upstream
    # resolves the cache and, when the ceiling is clear, provisions one — the download
    # is gated on `offline` exactly as `enrich_module`'s is.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Check pharm_variants.csv against the ClinPGx snapshot",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_clinpgx(
        spec_dir: str,
        use: str,
        snapshot: str | None = None,
        offline: bool = False,
    ) -> ClinPgxCheckReport:
        """Compare every authored `evidence_level` in `pharm_variants.csv` with ClinPGx's.

        Reports and never fills. **Read `not_checked` before `conflicts`**: it is null
        only when the comparison ran, and an empty conflicts list with it set means
        nothing was compared — no table, no snapshot, a `use` that forbids it, or a
        module drafted from this very release whose values are still the drafter's.
        `unmatched` rows are unverified, not wrong.

        **`use` is required**; ClinPGx carries a no-sale clause. `snapshot` points at a
        built directory; omit it and the resolved cache is used, or one is provisioned
        from HuggingFace unless `offline` forbids it — there is no live ClinPGx API and
        there will not be one. Writes the `pgx_evidence_level` record in
        `verification.json`; a module with no `pharm_variants.csv` gets no record.
        """
        declared = normalize_declared_use(use)
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        reference = resolve_dir(snapshot, settings) if snapshot else None
        try:
            result = await run_sync(
                lambda: enrich_clinpgx(
                    target,
                    mode="best_effort",
                    declared_use=declared,
                    snapshot=reference,
                    offline=eff_offline,
                    download=not eff_offline,
                    write=True,
                )
            )
        except (ClinPgxEnrichmentError, LicenseRefusal) as exc:
            raise ToolError(f"the ClinPGx evidence-level check could not run: {exc}") from exc

        conflicts = [
            EvidenceConflictRow(
                rsid=c.rsid,
                drug=c.drug,
                genotype=c.genotype,
                authored=c.authored,
                reported=c.reported,
            )
            for c in result.conflicts
        ]
        return ClinPgxCheckReport(
            spec_dir=str(target),
            compared=result.compared,
            not_checked=result.not_checked,
            conflicts=conflicts,
            unmatched=list(result.unmatched),
            dataset=result.dataset,
            declared_use=result.declared_use,
            warnings=list(result.warnings),
            attested=_recorded(target, "pgx_evidence_level"),
            next_step=(
                f"{len(conflicts)} evidence level(s) differ from {result.dataset}. ClinPGx "
                "re-grades, so the archive may be the stale side: check both, and change a "
                "cell only on evidence that outranks it — `record_override` keeps the reason."
                if conflicts
                else f"{result.compared} evidence level(s) compared against {result.dataset} "
                "and none differs."
                if result.not_checked is None
                else f"Not compared: `{result.not_checked}` — read `warnings`. An empty "
                "conflicts list here is not agreement."
            ),
        )
