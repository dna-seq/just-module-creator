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

from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_enricher.identifiers import (
    IdentifierUnavailable,
    unreachable_records,
    verification_records,
)
from just_dna_enricher.identifiers import (
    check_identifiers as _check_identifiers,
)
from just_dna_enricher.verification import record_verification
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import IdentifierReport, IdentifierStatus, IdentifierTally
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import resolve_dir

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
_CURRENT_STATES = frozenset({"approved", "current"})


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
        detail: bool = False,
    ) -> IdentifierReport:
        """Check every gene symbol (HGNC) and trait CURIE (OLS4) in a spec is current.

        Reports rather than corrects: rewriting an authored value would destroy the
        evidence that the identifier moved, and a rename is exactly the kind of
        change an author needs to see rather than inherit. What it *does* write is
        `verification.json` — an attestation that the checks ran and over how many
        rows, never a value. A consumer holding the artifact has no other way to
        tell "asked and clean" from "never asked".

        `check_genes` and `check_traits` are recorded in the attestation, so
        narrowing a run narrows what the record claims. Turning one off does not
        make its half pass — it makes the record say it was not asked.

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
        if not check_genes and not check_traits:
            raise ToolError(
                "Both halves are off, so there is no question to put. Enable check_genes or "
                "check_traits — an attestation for a check nobody asked for would assert nothing."
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
                    spec_dir=target, check_traits=check_traits, check_genes=check_genes
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
            verification_records(report, check_traits=check_traits, check_genes=check_genes),
            target,
        )

        stale = [
            f"{s.kind} {s.identifier}: {s.state}" + (f" -> {s.current}" if s.current else "")
            for s in genes + traits
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
            attested=attested,
            attestation_note=note,
            detail=detail,
        )
