"""Pydantic models used as structured tool inputs/outputs.

These are deliberately *trimmed* views of the upstream result objects rather
than the upstream models themselves. Two reasons:

* ``CompilationResult.manifest`` is a deep nested ``ModuleManifest``; inlining
  its schema into every tool's output contract costs an agent more context than
  the answer is worth. We surface the handful of manifest fields an author acts
  on and point at ``manifest.json`` for the rest.
* Upstream distinguishes ``error`` / ``warning`` / ``info`` and
  ``applied`` / ``refusal``. Those distinctions are load-bearing (see CLAUDE.md:
  "report, never repair" and "withhold rather than assert"), so they are
  preserved field-for-field here rather than flattened to a boolean.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Generic envelopes
# --------------------------------------------------------------------------- #
class OpResult(BaseModel):
    """Generic success/failure envelope for fallible tools.

    Tools return this (with ``success=False``) instead of raising, so an agent
    gets an actionable message rather than a protocol-level error.
    """

    success: bool = Field(description="Whether the operation succeeded.")
    message: str = Field(description="Human-readable summary or error.")
    data: dict | None = Field(default=None, description="Optional payload.")


class AuthResult(BaseModel):
    """Result of an ``authenticate`` call (scoped to the calling session)."""

    authenticated: bool = Field(description="Whether the token was accepted.")
    unlocked_tools: list[str] = Field(
        default_factory=list, description="Registry tools now usable in THIS session."
    )
    message: str = Field(description="Human-readable summary.")


# --------------------------------------------------------------------------- #
# Schema discovery
# --------------------------------------------------------------------------- #
class TableKind(BaseModel):
    """One authorable table kind and what its rows are about."""

    csv: str = Field(description="File name inside the spec directory.")
    model: str = Field(description="Pydantic model backing the rows.")
    subject: str = Field(description="What one row is about — how to choose this kind.")
    keyed_on: str = Field(description="Columns forming the row's uniqueness key.")
    companions: list[str] = Field(
        default_factory=list,
        description="Kinds that must be present alongside this one (studies.csv <-> variants.csv).",
    )


class TableList(BaseModel):
    """The authorable table kinds, plus the machine-produced sidecars."""

    tables: list[TableKind] = Field(description="Hand-authored table kinds.")
    sidecars: list[str] = Field(
        description="Enricher-produced files. Do not hand-author (except sources.csv "
        "when rows were copied from a source by hand)."
    )
    note: str = Field(description="The composition rule in one line.")


class TableRequirements(BaseModel):
    """The three shapes of requiredness for one table kind.

    ``defaulted`` is the one a plain schema dump hides: not required, and yet an
    empty cell arrives as ``None`` and fails on type. Write the default out.
    """

    csv: str = Field(description="The table kind.")
    always: list[str] = Field(description="Columns required on every row.")
    any_of: list[list[str]] = Field(
        description="Alternative identity groups; satisfy at least one group."
    )
    defaulted: dict[str, Any] = Field(
        description="column -> default. NEVER leave these empty: an empty cell is "
        "None, not the default, and fails on type."
    )
    optional: list[str] = Field(description="Columns that may be omitted or blank.")


class TableDescription(BaseModel):
    """Full generated description of a table kind: columns, vocabularies, pick-lists."""

    csv: str = Field(description="The table kind.")
    model: str = Field(description="Pydantic model backing the rows.")
    columns: list[dict] = Field(description="Per-column type, category and vocabulary.")
    requirements: dict = Field(description="Same content as `table_requirements`.")
    redundancy_bearing: dict[str, str] = Field(
        default_factory=dict,
        description="column -> why it is yours to author. Filling these from the "
        "source that later checks them makes the check vacuous.",
    )


class TemplateResult(BaseModel):
    """A CSV template for one table kind."""

    csv: str = Field(description="The table kind.")
    content: str = Field(description="CSV text: header only, or header plus stub rows.")
    stub: bool = Field(description="Whether placeholder rows are included.")
    note: str = Field(description="What to do with it.")


# --------------------------------------------------------------------------- #
# Authoring
# --------------------------------------------------------------------------- #
class ScaffoldResult(BaseModel):
    """Outcome of scaffolding a spec directory. Never overwrites."""

    spec_dir: str = Field(description="The spec directory.")
    created: list[str] = Field(description="Files created (or that would be created).")
    refused: list[str] = Field(
        description="Files left alone, each with the reason. Scaffold never overwrites."
    )
    warnings: list[str] = Field(default_factory=list, description="Advisory notes.")
    written: bool = Field(description="False when this was a dry run.")
    next_step: str = Field(description="What the author must do next.")


class LintFinding(BaseModel):
    """One finding from a lint pass. ``level`` is load-bearing — read it."""

    row: int | None = Field(default=None, description="0-based data row, or null if table-wide.")
    column: str | None = Field(default=None, description="Column, or null if row-wide.")
    level: str = Field(description="error | warning | info.")
    message: str = Field(description="What was found.")


class LintAlteration(BaseModel):
    """A value the linter would change — or deliberately refuses to change."""

    row: int = Field(description="0-based data row.")
    column: str = Field(description="Column.")
    before: str = Field(description="Authored value.")
    after: str = Field(description="Proposed value.")
    kind: str = Field(description="normalized (applied) | derived | advisory.")
    applied: bool = Field(
        description="Whether it was applied to `normalized_csv`. False means the tool "
        "declines to write this cell for you — see `refusal`."
    )
    source: str = Field(description="What produced the suggestion.")
    refusal: str | None = Field(
        default=None, description="Why it was NOT applied. A refusal is a feature."
    )
    note: str = Field(default="", description="Extra context.")


class LintResult(BaseModel):
    """Result of linting CSV text. Writes nothing, anywhere."""

    csv: str = Field(description="The table kind.")
    rows_in: int = Field(description="Data rows inspected.")
    errors: int = Field(description="Count of error-level findings.")
    warnings: int = Field(description="Count of warning-level findings.")
    findings: list[LintFinding] = Field(description="All findings, in order.")
    alterations: list[LintAlteration] = Field(
        description=(
            "Normalizations that were applied. Often empty on a valid table — the "
            "redundancy-bearing columns arrive as `info` findings here, not as refusals. "
            "Refusals with `applied=false` come from the lookup tools."
        )
    )
    normalized_csv: str = Field(
        description="The input with `applied` normalizations only. Never invents a value."
    )


# --------------------------------------------------------------------------- #
# Validate / compile
# --------------------------------------------------------------------------- #
class ValidationReport(BaseModel):
    """Pre-flight for a compile. Pass the SAME mode you intend to compile with."""

    valid: bool = Field(description="Whether the spec would compile in this mode.")
    strict: bool = Field(description="The mode this answer is for.")
    errors: list[str] = Field(description="Refusals.")
    warnings: list[str] = Field(
        description="Not refusals — but most known traps arrive here on a green run. Read them."
    )
    info: list[str] = Field(default_factory=list, description="Advisory notes.")
    stats: dict = Field(description="Variant/study/gene counts and table row counts.")


class CompileReport(BaseModel):
    """Outcome of a compile: parquet artifact + manifest.json."""

    success: bool = Field(description="Whether the artifact was written.")
    output_dir: str | None = Field(default=None, description="Where the artifact landed.")
    errors: list[str] = Field(description="Refusals.")
    warnings: list[str] = Field(description="Read these — a green compile is not a correct module.")
    stats: dict = Field(description="Counts from the compile.")
    artifact_digest: str | None = Field(
        default=None, description="Merkle root over the artifact files: its content identity."
    )
    content_signature: str | None = Field(
        default=None, description="Signature of the raw authored data."
    )
    resolution_signature: str | None = Field(default=None, description="Signature of resolution.")
    fully_resolved: bool | None = Field(
        default=None, description="Whether every row reached a coordinate."
    )
    files: list[str] = Field(default_factory=list, description="Artifact file names.")


class SignatureResult(BaseModel):
    """The content signature of the raw authored data — no compile, no network."""

    spec_dir: str = Field(description="The spec directory.")
    content_signature: str = Field(description="sha256:… over the authored content.")
    note: str = Field(description="What this signature does and does not cover.")


class VerifyResult(BaseModel):
    """Integrity verification of a compiled artifact."""

    verified: bool = Field(description="Whether every digest re-computed correctly.")
    module_dir: str = Field(description="The artifact directory.")
    artifact_digest: str | None = Field(default=None, description="The recomputed digest.")
    canonical_id: str | None = Field(default=None, description="namespace/name@version.")
    signature_checked: bool = Field(
        description="Whether a public key was supplied. False means the signature was NOT checked."
    )
    message: str = Field(description="Verdict or the first failure.")


# --------------------------------------------------------------------------- #
# Lookups (network, read-only, never write an authored cell)
# --------------------------------------------------------------------------- #
class VariantLookup(BaseModel):
    """What is known about one variant — and what of it stays the author's to write."""

    rsid: str | None = Field(default=None, description="The queried/current rsID.")
    rsid_state: str | None = Field(
        default=None, description="current | merged | withdrawn | absent — or null if unchecked."
    )
    loci: list[dict] = Field(
        description="{chrom, start, ref, alts} per mapping. `start` is the 1-based VCF "
        "position — paste it, never convert it. More than one locus means the rsID is "
        "paralogous or pseudoautosomal."
    )
    rsid_candidates: list[str] = Field(default_factory=list, description="Alternate rsIDs.")
    clin_sig: list[dict] = Field(default_factory=list, description="ClinVar significance records.")
    populations: list[dict] = Field(default_factory=list, description="gnomAD frequencies.")
    vrs_id: str | None = Field(default=None, description="ga4gh:VA.… when mintable.")
    findings: list[LintFinding] = Field(default_factory=list, description="Notes and warnings.")
    withheld: list[LintAlteration] = Field(
        default_factory=list,
        description="Values deliberately NOT written for you, each with its reason. "
        "Read the allele pair here to decide a genotype yourself.",
    )
    checked: list[str] = Field(default_factory=list, description="Which tiers were consulted.")
    offline: bool = Field(description="Whether this ran cache-only.")


class CitationLookup(BaseModel):
    """Whether a citation **exists** — which is not the same as being the right one.

    PMIDs are densely allocated, so a recalled 8-digit number is usually a real
    record for a *different* paper, and this comes back `pmid_exists=true`. Nothing
    here carries a title, so identity cannot be checked from this result. Use
    `literature_search(pmids=[...])` when the question is "does this id name the
    paper I meant".
    """

    pmid: str | None = Field(default=None, description="The PMID.")
    doi: str | None = Field(default=None, description="The DOI.")
    pmid_exists: bool | None = Field(
        default=None, description="null means UNCHECKED, which is not the same as false."
    )
    doi_exists: bool | None = Field(default=None, description="null means unchecked.")
    registry_doi: str | None = Field(default=None, description="The DOI PubMed records.")
    pmcid: str | None = Field(default=None, description="PMC id, when open access.")
    open_access: bool | None = Field(default=None, description="null means unchecked.")
    abstract_available: bool | None = Field(
        default=None,
        description=(
            "Whether Europe PMC holds an abstract — it returns one for paywalled records too. "
            "null means unchecked."
        ),
    )
    findings: list[LintFinding] = Field(default_factory=list, description="Notes and warnings.")
    withheld: list[LintAlteration] = Field(
        default_factory=list,
        description=(
            "Values shown but NOT written, each with its refusal. PubMed's DOI arrives here "
            "rather than as a cell to paste: `doi` is redundancy-bearing, so filling it from the "
            "record that supplied the PMID makes the DOI cross-check compare a source with itself."
        ),
    )


class IdentifierStatus(BaseModel):
    """Currency of one gene symbol or trait CURIE."""

    identifier: str = Field(description="What was asked about.")
    kind: str = Field(description="gene | trait.")
    state: str = Field(description="e.g. approved | retired | current | obsolete | unknown.")
    current: str | None = Field(default=None, description="The replacement, when retired.")
    label: str | None = Field(default=None, description="Human-readable label.")


class IdentifierReport(BaseModel):
    """Currency of every gene symbol and trait CURIE in a spec. Writes nothing."""

    spec_dir: str = Field(description="The spec directory.")
    genes: list[IdentifierStatus] = Field(description="Gene symbol verdicts.")
    traits: list[IdentifierStatus] = Field(description="Trait CURIE verdicts.")
    stale: list[str] = Field(description="Identifiers needing attention, summarised.")


# --------------------------------------------------------------------------- #
# Enrichment
# --------------------------------------------------------------------------- #
class EnrichReport(BaseModel):
    """Outcome of a resolution pass. Writes ``resolution.csv`` unless dry."""

    success: bool = Field(description="Whether the pass completed.")
    spec_dir: str = Field(description="The spec directory.")
    mode: str = Field(description="strict | best_effort.")
    offline: bool = Field(description="Whether this ran cache-only.")
    resolved: int = Field(description="Loci recorded in resolution.csv.")
    unresolved: list[str] = Field(description="Variant keys that reached no coordinate.")
    sources: list[str] = Field(description="Which tiers contributed.")
    ref_mismatches: list[str] = Field(
        description="THE check nothing offline can catch. A 'coordinate shifted 1 base' "
        "line is about `start`, not `ref`: `start` is the 1-based VCF position. "
        "Empty under --offline means UNCHECKED, not clean."
    )
    clin_sig_conflicts: list[str] = Field(description="Authored clin_sig vs ClinVar. Never fatal.")
    clin_sig_not_checked: str | None = Field(
        default=None, description="Why the clin_sig check did not run, when it did not."
    )
    stale_rsids: list[str] = Field(description="rsIDs that were merged or withdrawn.")
    vrs_minted: int | None = Field(default=None, description="VRS allele ids stamped.")
    warnings: list[str] = Field(default_factory=list, description="Advisory notes.")
    note: str = Field(description="What to do next, including how to regenerate.")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
class RegistryModule(BaseModel):
    """One module as the registry catalog sees it."""

    canonical_id: str = Field(description="namespace/name@version.")
    namespace: str = Field(description="Owning namespace.")
    name: str = Field(description="Module name.")
    version: str | None = Field(default=None, description="Latest version.")
    title: str | None = Field(default=None, description="Display title.")
    description: str | None = Field(default=None, description="One-line description.")
    genes: list[str] = Field(default_factory=list, description="Genes covered.")
    variant_count: int | None = Field(default=None, description="Variants in the module.")
    license: str | None = Field(default=None, description="Declared licence.")


class RegistrySearchResult(BaseModel):
    """A page of registry search results."""

    total: int = Field(description="Total matches.")
    page: int = Field(description="1-based page number.")
    modules: list[RegistryModule] = Field(description="This page of results.")
    registry_url: str = Field(description="Which registry answered.")
