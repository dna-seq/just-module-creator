"""Pydantic models used as structured tool inputs/outputs.

These are deliberately *trimmed* views of the upstream result objects rather
than the upstream models themselves. Two reasons:

* ``CompilationResult.manifest`` is a deep nested ``ModuleManifest``; inlining
  its schema into every tool's output contract costs an agent more context than
  the answer is worth. We surface the handful of manifest fields an author acts
  on and point at ``manifest.json`` for the rest.
* Upstream distinguishes ``error`` / ``warning`` / ``info`` and
  ``applied`` / ``refusal``. Those distinctions are load-bearing, so they are
  preserved field-for-field here rather than flattened to a boolean. Note what
  that preservation is *for*: an ``applied: false`` is upstream reporting what
  **it** did, and rewriting it would misreport another layer's act. It is not a
  claim that this layer may not write — see CLAUDE.md §2, which says the
  opposite — and three-valued answers stay three-valued because a check that
  could not run is not a check that passed.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from just_module_creator.overrides import OverrideRecord, QueuedOverride


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
    target: str | None = Field(
        default=None,
        description=(
            "Which instance answered: 'prod' (the published catalog) or 'test' (the polygon, "
            "where a publish is a rehearsal and can be deleted again). Kept on the result "
            "because nothing in a registry payload says which one it came from."
        ),
    )
    registry_url: str | None = Field(
        default=None, description="The instance this token was stored against."
    )
    message: str = Field(description="Human-readable summary.")


class RegistrationResult(BaseModel):
    """Result of ``registry_register`` — a freshly minted account and API key.

    Both secrets travel back to the caller because neither can be recovered from
    anywhere else: the registry has no email and no admin, so the install-id IS
    the account, and the token is what a later session authenticates with.
    """

    registered: bool = Field(description="Whether the registry minted a token.")
    account: str | None = Field(
        default=None,
        description=(
            "The account name the REGISTRY reports, which is authoritative. It differs from the "
            "name you asked for when the install-id already belonged to an account — see message."
        ),
    )
    namespaces: list[str] = Field(
        default_factory=list,
        description="Namespaces this account already owns. Empty on a brand-new account.",
    )
    token: str | None = Field(
        default=None,
        description=(
            "The API key. SECRET — put it in .env as JMC_API_KEY for production or "
            "JMC_TEST_API_KEY for the polygon; never commit it, and never write it into a "
            "module, fixture or doc. It is only valid on the instance that issued it."
        ),
    )
    install_id: str | None = Field(
        default=None,
        description=(
            "The proof-of-work id bound to this account. SAVE IT: it is the account's ONLY "
            "recovery path — re-registering it reissues a key for the same account, and there is "
            "no email or admin to recover through. Put it in .env as JMC_INSTALL_ID."
        ),
    )
    install_id_origin: str | None = Field(
        default=None,
        description="Where the install-id came from: 'argument', 'environment' or 'generated'.",
    )
    stored_for_session: bool = Field(
        default=False,
        description="Whether the token was stored in THIS session, so registry tools now work.",
    )
    target: str | None = Field(
        default=None,
        description=(
            "Which instance answered: 'prod' (the published catalog) or 'test' (the polygon, "
            "where a publish is a rehearsal and can be deleted again). Kept on the result "
            "because nothing in a registry payload says which one it came from."
        ),
    )
    registry_url: str | None = Field(default=None, description="The registry that was addressed.")
    message: str = Field(description="Human-readable summary, or why registration failed.")


class NamespaceAvailability(BaseModel):
    """Whether a namespace could be claimed — the pre-flight for an irreversible claim.

    ``valid`` and ``available`` are kept apart deliberately. An illegal name is
    not a free one, and collapsing the two into a single boolean would answer
    "can I claim this?" with the same value for "no, it is taken" and "no, that
    is not a legal namespace" — two different problems with different fixes.
    """

    namespace: str = Field(description="The namespace that was checked.")
    valid: bool = Field(
        description="Whether the name is a legal namespace: lowercase alphanumeric with hyphens."
    )
    available: bool = Field(description="Whether no account owns it yet.")
    target: str | None = Field(
        default=None,
        description=(
            "Which instance answered: 'prod' (the published catalog) or 'test' (the polygon, "
            "where a publish is a rehearsal and can be deleted again). Kept on the result "
            "because nothing in a registry payload says which one it came from."
        ),
    )
    registry_url: str | None = Field(default=None, description="The registry that was asked.")
    requires_allow_test_data: bool | None = Field(
        default=None,
        description=(
            "True when the name is claimable here but only if the caller asks explicitly — a "
            "`test-`prefixed namespace on production. **`available: true` with this set is not a "
            "green light**: the plain claim is refused, and this server does not offer the "
            "override. null means the instance did not report it (pre-0.14)."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="The instance's own warnings about claiming this name. Read them.",
    )
    message: str = Field(description="Human-readable summary.")


# --------------------------------------------------------------------------- #
# Schema discovery
# --------------------------------------------------------------------------- #
class SchemaVersions(BaseModel):
    """Which installed packages produced a generated schema answer.

    Stamped on every answer whose content is derived from the upstream pydantic
    models, so the answer carries the provenance of its own content.
    """

    format_version: str = Field(
        description=(
            "Installed `just-dna-format` version, read from package metadata at import. "
            "COMPARE IT against the version you expect: every column list, vocabulary and "
            "requirement on this answer was generated from that release's models, so a "
            "version older than the one you installed means a stale process is serving the "
            "answer — a cached plugin build, most often — and the schema it describes is "
            "not the schema the compiler will apply. Nothing else in the answer reveals that."
        )
    )
    compiler_version: str = Field(
        description=(
            "Installed `just-dna-compiler` version, on the same terms. It is here because "
            "the table roster, the requirement shapes, the templates and the "
            "redundancy/attestation maps are the compiler's projection of the format's "
            "models, so a skew in either package moves this answer."
        )
    )


_PRODUCED_BY_WHY = (
    "The installed packages whose live models generated this answer. Read it whenever a "
    "column, vocabulary or requirement here disagrees with what you expected: this answer "
    "is only as current as the process serving it, and the version is the only thing in it "
    "that says so."
)


class TableKind(BaseModel):
    """One authorable table kind and what its rows are about."""

    csv: str = Field(description="File name inside the spec directory.")
    model: str = Field(description="Pydantic model backing the rows.")
    subject: str = Field(description="What one row is about — how to choose this kind.")
    keyed_on: str = Field(
        description="The columns that decide whether two rows are the same row — what an append "
        "collides on. On a binning kind (a measure with thresholds) it is the GROUP key instead: "
        "equality is not the duplicate rule there, overlapping ranges are, so two bins can "
        "conflict while sharing no key and two identical keys are not a duplicate."
    )
    companions: list[str] = Field(
        default_factory=list,
        description="Kinds that must be present alongside this one (studies.csv <-> variants.csv).",
    )
    deprecated: bool = Field(
        default=False,
        description="True when this is an older spelling of another kind on this list. It still "
        "reads, and it is removed at format 1.0. Never create one.",
    )
    preferred: str | None = Field(
        default=None,
        description="The spelling a NEW file takes, when it differs from `csv`. Both spellings "
        "back the same model, and a module carrying both is refused rather than merged — so "
        "write to the file that is already there, and use this name only when neither exists.",
    )


class TableList(BaseModel):
    """The authorable table kinds, plus the machine-produced sidecars."""

    tables: list[TableKind] = Field(description="Hand-authored table kinds.")
    sidecars: list[str] = Field(
        description="Machine-produced files: an enricher pass writes each one and the compiler "
        "fact-hashes it. Read them, never hand-finish them — `describe_machine_table` answers the "
        "columns of any name on this list. Derived from the installed toolchain rather than "
        "listed, so it grows when upstream adds a fact table. `licensing.csv` (formerly "
        "`sources.csv`) is "
        "deliberately NOT here: it is the one fact sidecar a human writes, so it is a table kind "
        "above, with a template and a linter like any other."
    )
    note: str = Field(description="The composition rule in one line.")
    produced_by: SchemaVersions = Field(description=_PRODUCED_BY_WHY)


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
    produced_by: SchemaVersions = Field(description=_PRODUCED_BY_WHY)


class TableDescription(BaseModel):
    """Full generated description of a table kind: columns, vocabularies, pick-lists."""

    csv: str = Field(description="The table kind.")
    model: str = Field(description="Pydantic model backing the rows.")
    hand_authored: Literal[True] = Field(
        default=True,
        description="Always true on this answer, and it is here so the distinction is readable "
        "without prose: `describe_table` answers only about tables a human writes. A "
        "machine-produced table is answered by `describe_machine_table`, whose answer carries "
        "this key as `false`.",
    )
    columns: list[dict] = Field(description="Per-column type, category and vocabulary.")
    requirements: dict = Field(description="Same content as `table_requirements`.")
    redundancy_bearing: dict[str, str] = Field(
        default_factory=dict,
        description="column -> the check that later cross-examines it. Filling one from the "
        "source that checks it makes the check vacuous.",
    )
    attestation_bearing: list[str] = Field(
        default_factory=list,
        description=(
            "Columns whose content asserts that a HUMAN read something. A stronger refusal "
            "than redundancy: filling one from a document a tool just fetched states something "
            "FALSE rather than merely unverifiable, because the cell means 'a curator read this "
            "passage in this paper' and no lookup can make that true. These also appear in "
            "`redundancy_bearing`; this names the sharper reason to refuse on."
        ),
    )
    produced_by: SchemaVersions = Field(description=_PRODUCED_BY_WHY)


class MachineTableDescription(BaseModel):
    """Full generated description of a MACHINE-produced table — read it, never write it.

    A separate model from ``TableDescription`` rather than a flag on it, because the
    two answers are different questions. ``TableDescription`` carries
    ``requirements`` (what an author must supply), ``redundancy_bearing`` and
    ``attestation_bearing`` (which cells an author must reason out independently) —
    three fields whose whole subject is authoring, and every one of them would have
    to be filled with an empty value here. An empty ``requirements`` reads as *no
    requirements*, which is a different claim from *the question does not apply*.

    So the fields that only make sense for an author are absent, and what is left is
    the columns plus a refusal.
    """

    csv: str = Field(description="The sidecar's file name inside the spec directory.")
    model: str = Field(description="Pydantic model backing the rows.")
    hand_authored: Literal[False] = Field(
        default=False,
        description="Always false. This table is written by a machine — an enricher pass — and "
        "fact-hashed by the compiler. Nothing on this surface offers a template for it or lints "
        "rows for it, and that is deliberate rather than missing.",
    )
    columns: list[dict] = Field(
        description="Per-column type, category, description and vocabulary, generated from the "
        "live model. Read these to understand a sidecar the passes produced — several of these "
        "facts exist nowhere else in the module."
    )
    refusal: str = Field(
        description="What a hand-written cell in a machine-produced sidecar costs, and how to "
        "write one honestly if you must. Not a bar on writing — an unmarked cell is the "
        "problem, because nothing downstream can tell it from a fetched fact."
    )
    produced_by: SchemaVersions = Field(description=_PRODUCED_BY_WHY)


class TemplateResult(BaseModel):
    """A CSV template for one table kind."""

    csv: str = Field(description="The table kind.")
    content: str = Field(description="CSV text: header only, or header plus stub rows.")
    stub: bool = Field(description="Whether placeholder rows are included.")
    note: str = Field(description="What to do with it.")
    produced_by: SchemaVersions = Field(description=_PRODUCED_BY_WHY)


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
    source: str = Field(
        default="upstream",
        description=(
            "Which layer computed this finding: `upstream` for the compiler's own, carried "
            "across field-for-field, or `just-module-creator` for one this authoring layer "
            "computed itself. Read it before quoting a finding as the compiler's — the two "
            "have different reach, and an authoring-layer finding does not block a compile "
            "the way an upstream `error` does."
        ),
    )
    line: int | None = Field(
        default=None,
        description=(
            "1-based line in the file, header included — the number an editor shows, so "
            "`row` and `line` legitimately differ for the same finding. null when upstream "
            "did not locate one; never inferred from `row` here."
        ),
    )


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
    authored_findings: list[LintFinding] = Field(
        default_factory=list,
        description=(
            "Findings THIS layer computed over the authored tables, kept out of `errors` / "
            "`warnings` / `info` so upstream's own strings stay exactly as they arrived. They "
            "do not move `valid`: the compiler would still build this module. Read them anyway "
            "— they cover shapes no compiler check can see, such as one identical "
            "`provenance_quote` across every row citing a paper."
        ),
    )
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
        default=None,
        description="Whether every row reached a coordinate. Read `resolution_subjects` beside "
        "it: over an empty list this is vacuously true, not evidence of anything.",
    )
    resolution_subjects: int | None = Field(
        default=None,
        description="The denominator `fully_resolved` quantifies over, counted AFTER rsID "
        "expansion. `0` beside `fully_resolved: true` means nothing was resolved because there "
        "was nothing to resolve. **null is not 0** — it means this compiler did not count.",
    )
    positional_rows: int | None = Field(
        default=None,
        description="Rows on the positional/PGx side. **null is not 0**: `0` says the module has "
        "none, null says nothing counted them.",
    )
    positional_rows_placed: int | None = Field(
        default=None,
        description="How many of `positional_rows` actually join to a VCF. Complete is "
        "`placed == rows` — two parts, deliberately not a ratio.",
    )
    expanded_keys: int | None = Field(
        default=None,
        description="Authored keys that resolved onto more than one locus. Expansion is expected "
        "and correct; deleting rows to suppress it is not.",
    )
    expanded_rows: int | None = Field(
        default=None,
        description="Rows those keys became. `expanded_rows - expanded_keys` is NOT the "
        "unmatchable-row count — that needs a number the manifest does not carry.",
    )
    files: list[str] = Field(default_factory=list, description="Artifact file names.")


class ClosureResult(BaseModel):
    """Outcome of declaring a module's authoring phase finished.

    Closing is the one thing in the pipeline no check does for you. A record
    stamped by whatever happened to pass says only that something ran; this says
    a person decided the module was done, over the exact authored bytes.
    """

    closed: bool = Field(description="Whether the closure was written.")
    spec_dir: str = Field(description="The spec directory.")
    path: str | None = Field(
        default=None, description="The verification.json the closure was written into."
    )
    module_hash: str | None = Field(
        default=None,
        description="Hash of module_spec.yaml plus the authored CSVs as they stand. Edit any of "
        "them and this moves, the compiler drops the closure, and the module is open again.",
    )
    signed: bool = Field(
        default=False,
        description="False means change-evident but not attributed: it records that someone "
        "closed the module, not which party did.",
    )
    dropped_checks: list[str] = Field(
        default_factory=list,
        description="Check records attested over different bytes, dropped as no longer binding. "
        "Re-run those checks against the closed module.",
    )
    errors: list[str] = Field(default_factory=list, description="Why the close was refused.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Advisory. Closing deliberately does NOT refuse on warnings — an unresolved "
        "rsID is a legitimate state to call finished.",
    )


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
    """Whether a citation exists, and **which paper it actually names**.

    PMIDs are densely allocated, so a recalled 8-digit number is usually a real
    record for a *different* paper and comes back `pmid_exists=true`. Existence
    therefore never settles identity — `title` does. Compare the title against the
    paper you meant; if they disagree, the id is wrong however true
    `pmid_exists` is.
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
    title: str | None = Field(
        default=None,
        description=(
            "The title of the record this id actually names — the field that decides identity. "
            "Read it and compare against the paper you meant. null means unchecked, not "
            "'no such paper'."
        ),
    )
    journal: str | None = Field(default=None, description="Journal name. null means unchecked.")
    year: str | None = Field(default=None, description="Publication year. null means unchecked.")
    first_author: str | None = Field(
        default=None, description="First author. null means unchecked."
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
    """Currency of every gene symbol and trait CURIE in a spec.

    Writes no authored cell. It does write `verification.json` — an attestation
    that the question was put, never a value. See `tools/checks.py`.
    """

    spec_dir: str = Field(description="The spec directory.")
    genes: list[IdentifierStatus] = Field(description="Gene symbol verdicts.")
    traits: list[IdentifierStatus] = Field(description="Trait CURIE verdicts.")
    stale: list[str] = Field(description="Identifiers needing attention, summarised.")
    gene_locus_conflicts: list[str] = Field(
        default_factory=list,
        description=(
            "Rows whose `gene` sits on a different chromosome than the row's own variant. "
            "**Read these even when every identifier is current** — the relationship is false "
            "while both halves are individually true, so nothing else catches it. It is the "
            "signature of a generated row: a real gene symbol beside an invented rsID, which "
            "resolves anyway because dbSNP is dense. Reported rather than corrected, and for a "
            "reason no policy change reaches: **which half is wrong is not something a lookup "
            "can know.** Fixing the gene and fixing the rsID produce different modules."
        ),
    )
    gene_locus_check_skipped: str | None = Field(
        default=None,
        description=(
            "Why the gene/chromosome comparison did not run, or null when it did. An empty "
            "`gene_locus_conflicts` means 'nothing disagreed' ONLY when this is null — "
            "otherwise it means the comparison never happened, which is not a pass."
        ),
    )
    attested: bool = Field(
        default=False,
        description=(
            "Whether this run wrote a record into `verification.json`. The record says the "
            "checks RAN and over how many rows — it is not a verdict, and a module carrying "
            "one is not thereby a module whose identifiers are current. False is never a "
            "failure on its own: read `attestation_note` for which of the two reasons it is."
        ),
    )
    attestation_note: str | None = Field(
        default=None,
        description=(
            "Why no record was written, or null when one was. Two different facts arrive "
            "here and a caller must not merge them: the check did not APPLY (no variants.csv, "
            "so there was no gene or trait to have an opinion about — not a skip), or the "
            "check ran and only the write failed, in which case the findings above stand."
        ),
    )


# --------------------------------------------------------------------------- #
# Literature discovery (network, read-only, never writes an authored cell)
# --------------------------------------------------------------------------- #
class SourceStatus(BaseModel):
    """What one source did — the field to read before believing an empty result."""

    source: str = Field(description="pubmed | europepmc | semanticscholar | preprints | unpaywall.")
    queried: bool = Field(
        description=(
            "False means never asked: excluded by policy, missing credential, or not requested."
        )
    )
    results: int | None = Field(
        default=None,
        description=(
            "How many it returned. **null means the source could not answer** — a timeout, a "
            "rate limit, an outage. NEVER 0 for that case: 0 is reserved for a source that "
            "genuinely answered with nothing, and an author acts differently on each."
        ),
    )
    reason: str | None = Field(
        default=None, description="Why it was not asked, or how it failed. null when it answered."
    )
    rate_limited: bool = Field(default=False, description="The source asked us to slow down.")


class SourceLicenseNote(BaseModel):
    """A source consulted, and the `licensing.csv` row nothing will write for it.

    Deliberately carries no `license`, `commercial_use` or `share_alike`: pointing
    at the terms is help, asserting them is a guess, and `declared_use` is a
    licence position only the author can take. Upstream's `TERMS_BY_SOURCE` has no
    entry for any literature service, which is filed rather than papered over.
    """

    source: str = Field(description="The join value for licensing.csv, e.g. `pubmed`.")
    layer: str = Field(description="`literature` for the sidecar; `annotation` if you quote text.")
    terms_url: str | None = Field(default=None, description="Where to read the terms.")
    stateable_upstream: bool = Field(
        description="Whether `licensing.TERMS_BY_SOURCE` can state this source's terms today."
    )
    note: str = Field(description="What the author still has to do.")


class LiteratureCandidate(BaseModel):
    """One paper a search found. A candidate to *read*, never a row to paste."""

    pmid: str | None = Field(default=None, description="PubMed id, when the record has one.")
    pmcid: str | None = Field(default=None, description="PMC id, when open access.")
    doi: str | None = Field(
        default=None,
        description=(
            "An addressing key, NOT a cell to author. `doi` is redundancy-bearing; see `withheld`."
        ),
    )
    arxiv_id: str | None = Field(default=None, description="arXiv id, for a preprint.")
    title: str | None = Field(
        default=None,
        description="**The point of a search** — how you tell this paper from another.",
    )
    authors: list[str] = Field(default_factory=list, description="As the source spells them.")
    year: int | None = Field(default=None, description="Publication year.")
    venue: str | None = Field(default=None, description="Journal or repository.")
    abstract: str | None = Field(default=None, description="When the source returned one.")
    citation_count: int | None = Field(
        default=None, description="null means the source did not say."
    )
    is_open_access: bool | None = Field(default=None, description="null means unchecked.")
    preprint: bool | None = Field(
        default=None,
        description=(
            "True means **not peer-reviewed and no PMID** — so it cannot ground a studies.csv row "
            "on its own, since `pmid` is required there. It may still inform a hedged conclusion."
        ),
    )
    url: str | None = Field(default=None, description="Where the source points.")
    found_in: list[str] = Field(
        default_factory=list, description="Every source that returned this paper."
    )
    rank: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Each source's own 1-based position for it. Deliberately NOT combined into one score: "
            "a synthesized rank is a convention with no source behind it, and it invites citing "
            "the top hit without reading it."
        ),
    )


class LiteratureSearchResult(BaseModel):
    """Papers matching a question, plus an honest account of who was asked."""

    query: str = Field(description="What was searched for.")
    papers: list[LiteratureCandidate] = Field(
        description="Merged across sources, deterministic order."
    )
    sources: list[SourceStatus] = Field(
        description="One per source. **Read this before believing an empty `papers`.**"
    )
    withheld: list[LintAlteration] = Field(
        default_factory=list,
        description="Values shown but not written — the DOI of each candidate, with its refusal.",
    )
    findings: list[LintFinding] = Field(default_factory=list, description="Notes and warnings.")
    licensing: list[SourceLicenseNote] = Field(
        default_factory=list,
        description="The licensing.csv rows you now owe, and why none was written.",
    )


class OpenAccessLocation(BaseModel):
    """One place a paper may legally be read."""

    url: str = Field(description="Where it is.")
    version: str | None = Field(default=None, description="publishedVersion | acceptedVersion | …")
    license: str | None = Field(
        default=None,
        description=(
            "The **article's** licence (cc-by, cc-by-nc, bronze…), which is what decides whether a "
            "quote may travel inside a module you publish. null means the host did not say."
        ),
    )
    host_type: str | None = Field(default=None, description="publisher | repository.")


class OpenAccessResult(BaseModel):
    """Where a paper may be read, and on what terms. Free to read is not free to reuse."""

    doi: str | None = Field(default=None, description="The DOI asked about.")
    is_open_access: bool | None = Field(default=None, description="null means unchecked.")
    best_location: OpenAccessLocation | None = Field(
        default=None, description="The host's own pick."
    )
    locations: list[OpenAccessLocation] = Field(default_factory=list, description="All of them.")
    sources: list[SourceStatus] = Field(default_factory=list, description="Who answered.")
    findings: list[LintFinding] = Field(default_factory=list, description="Notes and warnings.")


class FullTextResult(BaseModel):
    """A document to read. Never a passage, and never a suggested quote."""

    pmid: str | None = Field(default=None, description="The PMID, when known.")
    pmcid: str | None = Field(default=None, description="The PMC id used to retrieve.")
    doi: str | None = Field(default=None, description="The DOI, when known.")
    retrieved: bool = Field(description="Whether any text came back.")
    text: str | None = Field(default=None, description="The document, whitespace-normalized.")
    text_source: str | None = Field(
        default=None,
        description=(
            "`fulltext` | `abstract` | null. **null means nothing was retrieved**, not that the "
            "paper has no text — and an abstract is named as the substitute rather than passed "
            "off as the article."
        ),
    )
    truncated: bool = Field(default=False, description="Whether `max_chars` cut the text.")
    locations: list[OpenAccessLocation] = Field(
        default_factory=list, description="Where to read it, when the text could not be fetched."
    )
    findings: list[LintFinding] = Field(
        default_factory=list,
        description=(
            "Includes the standing note that no passage was extracted for you, and what that "
            "costs: once you read a fulltext here, `quotes_found` on that row stops being "
            "independent evidence and becomes a citation-pairing check."
        ),
    )


class CitationGraph(BaseModel):
    """Papers citing this one, or cited by it — the 'has it been replicated' question."""

    paper_id: str = Field(description="What was asked about.")
    direction: str = Field(description="citing | cited_by.")
    papers: list[LiteratureCandidate] = Field(description="The neighbours.")
    sources: list[SourceStatus] = Field(default_factory=list, description="Who answered.")
    withheld: list[LintAlteration] = Field(default_factory=list, description="DOIs, with refusals.")


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
    target: str | None = Field(
        default=None,
        description=(
            "Which instance answered: 'prod' (the published catalog) or 'test' (the polygon, "
            "where a publish is a rehearsal and can be deleted again). Kept on the result "
            "because nothing in a registry payload says which one it came from."
        ),
    )
    registry_url: str = Field(description="Which registry answered.")


class PublishedVersion(BaseModel):
    """One published version built from the same authored data."""

    canonical_id: str = Field(description="namespace/name@version.")
    namespace: str = Field(description="Namespace.")
    name: str = Field(description="Module name.")
    version: str = Field(description="Version.")
    yanked: bool = Field(description="Whether it has been yanked. A yank does NOT free the data.")


class DuplicateCheck(BaseModel):
    """Whether this spec's authored data is already published, under any name."""

    content_signature: str = Field(
        description=(
            "The signature of the authored rows — computed locally, no upload. This names the "
            "*data*, not a compiled artifact, so it catches a rename or a rebrand that a digest "
            "would miss."
        )
    )
    published_as: list[PublishedVersion] = Field(
        default_factory=list,
        description=(
            "Versions already built from identical data. **Non-empty means a publish would 409 "
            "duplicate_content.** On production that is permanent: the claim is not released by "
            "yanking the version that made it."
        ),
    )
    free_to_publish: bool = Field(
        description=(
            "True only when nothing matched. This is a *duplicate* verdict and nothing more — it "
            "says the data is unclaimed, never that the spec is valid or publishable."
        )
    )
    target: str = Field(description="Which instance answered: 'prod' or 'test' (the polygon).")
    registry_url: str = Field(description="Which registry answered.")


class InstanceHealth(BaseModel):
    """What one registry instance says about itself."""

    reachable: bool = Field(description="Whether it answered at all.")
    target: str = Field(description="The target you asked for: 'prod' or 'test'.")
    registry_url: str = Field(description="The URL that was called.")
    status: str | None = Field(default=None, description="Its own status string, e.g. 'ok'.")
    version: str | None = Field(default=None, description="The registry version it runs.")
    mode: str | None = Field(
        default=None,
        description=(
            "The deployment's own answer to 'am I production or the polygon?' — 'prod' | 'test'. "
            "**null means it did not say**, which is not a pass: an instance too old to report "
            "its mode cannot have the target verified against it, and every write tool refuses "
            "rather than guessing."
        ),
    )
    mode_matches_target: bool | None = Field(
        default=None,
        description=(
            "Whether the instance's own mode agrees with the target you named. null when it "
            "reported no mode — never False, because unreported is not disagreement."
        ),
    )
    catalog: dict = Field(default_factory=dict, description="Its module/version counts, if given.")
    message: str = Field(description="What this means, in one line.")


class PublishPreflight(BaseModel):
    """A server-side dry run: would this spec publish, and what stops it.

    Two verdicts, deliberately separate, and **neither is named "will publish"**.
    ``module_level_clear`` covers the gates that do not scale with variant count;
    ``verdict`` is the whole dry run including the network tier, and is null when
    that tier did not run.
    """

    spec_dir: str = Field(description="The spec directory that was sent.")
    namespace: str = Field(description="Namespace it was checked against.")
    name: str = Field(description="Module name it was checked against.")
    strict: bool = Field(description="The mode the findings were graded under.")

    valid: bool = Field(description="Whether the spec validates under `strict`.")
    errors: list[str] = Field(default_factory=list, description="Blocking findings.")
    warnings: list[str] = Field(default_factory=list, description="Non-blocking findings.")
    info: list[str] = Field(
        default_factory=list,
        description="Accepted but noteworthy — keys the server dropped, a version it coerced.",
    )

    module_level_clear: bool = Field(
        description=(
            "**Read this as 'nothing module-level blocks this', never as 'this will publish'.** "
            "It composes exactly three gates: the spec validates under strict, `module.name` "
            "matches the path, and no version is already built from identical data. It says "
            "nothing about the network tier, so a clear answer here is not a green light."
        )
    )
    name_matches_path: bool = Field(
        description="Whether the spec's `module.name` matches `name`. A publish 422s if not."
    )
    published_as: list[PublishedVersion] = Field(
        default_factory=list,
        description="Versions already built from identical data — a publish would 409.",
    )
    content_signature: str | None = Field(
        default=None,
        description="Content identity of the authored rows; null when a data CSV will not parse.",
    )

    verdict: bool | None = Field(
        default=None,
        description=(
            "The full dry run's answer, including the network tier. **null means the dry run did "
            "not reach a verdict** — the enrichment tier was skipped (see `verdict_unavailable`) "
            "— and null is never a pass. Only `registry_check` sets this; `registry_validate` "
            "leaves it null because it never runs that tier at all."
        ),
    )
    verdict_unavailable: str | None = Field(
        default=None,
        description=(
            "Why `verdict` is null. e.g. `invalid_spec` — nothing to enrich yet, so the errors "
            "above are already the answer."
        ),
    )
    rerun_rather_than_fix: list[str] = Field(
        default_factory=list,
        description=(
            "rsIDs live Ensembl could not be *asked* about, so their absence is unchecked rather "
            "than established. **A false `verdict` alongside these means 're-run', not 'go fix "
            "your spec'** — a strict publish against an unreachable Ensembl really does refuse, "
            "but the variant may be perfectly findable."
        ),
    )
    unchecked: list[str] = Field(
        default_factory=list,
        description=(
            "Checks that did not run, each with the reason. A check the operator disabled or has "
            "no snapshot for is not a defect in your module and never blocks a publish — but it "
            "is not a passed check either, which is why it is listed rather than dropped."
        ),
    )
    blocking: list[str] = Field(
        default_factory=list,
        description="What actually stands between this spec and a publish, in one list.",
    )
    non_blocking: list[str] = Field(
        default_factory=list,
        description=(
            "Findings worth reading that do NOT move the verdict — identifier currency among "
            "them, because a publish does not run that pass, so a finding predicts nothing "
            "about one."
        ),
    )
    stats: dict = Field(default_factory=dict, description="What the server counted in the spec.")
    elapsed_seconds: float | None = Field(
        default=None, description="How long the dry run took server-side."
    )
    target: str = Field(description="Which instance answered: 'prod' or 'test' (the polygon).")
    registry_url: str = Field(description="Which registry answered.")
    next_step: str = Field(description="What to do with this result.")


# --------------------------------------------------------------------------- #
# Drafting and the fact passes
# --------------------------------------------------------------------------- #
class DraftedTable(BaseModel):
    """What a drafter did to one CSV. The four statuses are load-bearing."""

    csv: str = Field(description="The table kind written.")
    added: int = Field(description="Rows newly written.")
    already_present: int = Field(description="Rows the source proposed that you already had.")
    differs: int = Field(
        description=(
            "Rows where the source DISAGREES with what you authored — **left unchanged and "
            "reported**. A disagreement is not a defect report: archives lag the edge, so your "
            "row may be right and current while the source is stale. Conforming it would destroy "
            "the evidence that the two disagree AND could silently degrade the module, with the "
            "check then agreeing with itself. Editing against a source needs a reason that "
            "outranks the source."
        )
    )
    invalid: int = Field(description="Rows the source proposed that failed validation.")
    differences: list[str] = Field(
        default_factory=list, description="Column-level detail for the `differs` rows."
    )
    shifted: int = Field(
        default=0,
        description=(
            "Existing rows whose line NUMBER moved because a new row landed in their group. "
            "Their cells are byte-identical — this explains a digest change that is not a "
            "content change."
        ),
    )
    written: bool = Field(description="False on a dry run.")


class DraftResult(BaseModel):
    """Outcome of drafting from a published source."""

    spec_dir: str = Field(description="The spec directory.")
    source: str = Field(description="clinvar | cpic | clinpgx.")
    declared_use: str = Field(description="The licence position you declared.")
    skipped: bool = Field(
        description=(
            "**True means nothing was fetched, because your `use` does not satisfy the source's "
            "terms.** This is the gate working, not a failure — do NOT retry with a different "
            "`use` to make it pass. That would be asserting a licence position to get data."
        )
    )
    tables: list[DraftedTable] = Field(default_factory=list, description="Per-CSV outcome.")
    warnings: list[str] = Field(default_factory=list, description="Including the refusal reason.")
    dry_run: bool = Field(description="Whether this was a preview.")
    next_step: str = Field(description="What to do now.")


class LiteratureReport(BaseModel):
    """Outcome of the literature pass — the `literature.csv` pin."""

    success: bool = Field(description="Whether the pass completed.")
    spec_dir: str = Field(description="The spec directory.")
    mode: str = Field(description="strict | best_effort.")
    rows: int = Field(description="Rows in literature.csv after the merge.")
    missing: list[str] = Field(
        default_factory=list, description="PMIDs that did not resolve. Do not ship these."
    )
    doi_conflicts: list[str] = Field(
        default_factory=list,
        description=(
            "Your authored DOI disagrees with the registry's for this PMID. Reported, never "
            "rewritten: one of the two citations is the wrong paper and only you know which."
        ),
    )
    quotes_authored: int = Field(default=0, description="provenance_quote cells you wrote.")
    quotes_found: int = Field(default=0, description="Of those, located in retrievable text.")
    quotes_unchecked: int = Field(
        default=0,
        description="**Not failures** — nothing retrievable to check them against.",
    )
    coverage: str = Field(default="", description="Upstream's own prose summary.")
    skipped_offline: bool = Field(
        default=False,
        description=(
            "True means the pass did NOTHING. There is no offline literature snapshot and there "
            "will not be one; any existing literature.csv remains the pin."
        ),
    )
    warnings: list[str] = Field(default_factory=list, description="Advisory notes.")
    note: str = Field(default="", description="How to regenerate.")


class FactPassReport(BaseModel):
    """Outcome of one or more sidecar fact passes."""

    success: bool = Field(description="Whether every requested pass completed.")
    spec_dir: str = Field(description="The spec directory.")
    passes_run: list[str] = Field(description="Which passes actually ran.")
    rows_written: dict[str, int] = Field(
        default_factory=dict, description="pass -> rows in its sidecar after the merge."
    )
    covered: dict[str, list[str]] = Field(
        default_factory=dict, description="pass -> what it found."
    )
    missing: dict[str, list[str]] = Field(
        default_factory=dict,
        description="pass -> what it could not cover. Absence here is not proof of absence.",
    )
    declared_use_applied_to: list[str] = Field(
        default_factory=list,
        description=(
            "Which passes consumed `use`. Only `dosage` reads a licence-bearing source; the "
            "others take none, so `use` is silently irrelevant to them — named rather than hidden."
        ),
    )
    skipped_offline: list[str] = Field(
        default_factory=list, description="Passes that did nothing because the network was off."
    )
    unreachable: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "pass -> why its source never answered. This is NOT `missing`: a gene gnomAD has no "
            "entry for and a gene gnomAD never answered about both leave the sidecar row absent, "
            "and only this field tells them apart. A pass named here asked nothing, so its "
            "`covered: []` is silence rather than a negative result."
        ),
    )
    failed: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "pass -> why it failed on something that is not an outage: a table that will not "
            "load, a refused licence declaration. The source answered; the problem is here."
        ),
    )
    warnings: list[str] = Field(default_factory=list, description="Advisory notes.")
    note: str = Field(default="", description="How to regenerate.")


class GwasReport(BaseModel):
    """Outcome of the GWAS Catalog pass — published effect sizes in `gwas_effects.csv`.

    One row per published **association**, not per variant: a well-studied
    variant carries dozens across different traits and papers. Nothing here is
    an authored cell, and `weight` is not among the columns it fills.
    """

    success: bool = Field(description="Whether the pass completed.")
    spec_dir: str = Field(description="The spec directory.")
    mode: str = Field(
        description=(
            "strict | best_effort. Under strict this pass escalates on the CATALOG's shape — "
            "`unusable` or `p_value_underflows` — never on `missing`, and never on anything "
            "you authored. A strict failure here is not a verdict on the module."
        )
    )
    offline: bool = Field(description="Whether the offline ceiling was in force.")
    rows: int | None = Field(
        default=None,
        description=(
            "Rows in gwas_effects.csv after the merge, existing ones included. **`null` means "
            "nothing counted them**, never zero rows: the pass failed, or it was a no-op offline "
            "and any existing file kept whatever it already held."
        ),
    )
    covered: list[str] = Field(
        default_factory=list, description="rsIDs the Catalog served at least one association for."
    )
    missing: list[str] = Field(
        default_factory=list,
        description=(
            "rsIDs the Catalog holds nothing for. **Not a shortfall** — no genome-wide "
            "association has been published for them, which is itself a fact about the variant, "
            "and each one is written as a `not_found` row rather than left silent. True of most "
            "clinically authored variants, which is why strict does not escalate on it."
        ),
    )
    requests_made: int | None = Field(
        default=None,
        description=(
            "Requests actually issued against EBI. The budget is `1 + 2N` per variant with N "
            "associations — measured at 382 for one real module — because pmid, trait, ancestry "
            "and study accession all sit behind `_links`. This is somebody else's rate limit. "
            "`null` when the pass failed before anything was counted."
        ),
    )
    requests_saved: int | None = Field(
        default=None,
        description=(
            "Requests a cache hit avoided. Often 0 — associations rarely share studies — and "
            "`null` when the pass failed before anything was counted."
        ),
    )
    p_value_underflows: int | None = Field(
        default=None,
        description=(
            "Associations whose p-value the Catalog reports below float64's range (it publishes "
            "0.0), so the queryable number is withheld and the verbatim `p_value` string keeps "
            "what the source said. The rows are all present. Not an authoring mistake — strict "
            "escalates on it because the artifact holds less than the Catalog published. `null` "
            "means the pass failed before anything was counted — read `warnings`, which carries "
            "upstream's own message and its counts."
        ),
    )
    unusable: int | None = Field(
        default=None,
        description=(
            "Associations the Catalog served without an id this pass can key on, so they are in "
            "no row. Counted rather than logged, and the other reason strict escalates. `null` "
            "means nothing counted them, not that there were none."
        ),
    )
    associations_without_effect_allele: int = Field(
        default=0,
        description=(
            "Of the associations recorded (`not_found` rows excluded), how many name no effect "
            "allele: the Catalog wrote `rs…-?`, meaning the study never established which allele "
            "carries the effect. Real evidence that has NO direction applicable to a genotype. "
            "Measured at 33 of 186 on one real module — read it before treating any of these "
            "effects as a weight."
        ),
    )
    effect_units: list[str] = Field(
        default_factory=list,
        description=(
            "Every distinct `effect_unit` in the table, sorted. Free text, kept verbatim "
            "including the Catalog's uninformative 'unit'. More than one means these betas are "
            "on different and possibly uninterpretable scales, so they do not combine — 12 "
            "distinct values on one real variant. This is why `weight` stays yours."
        ),
    )
    study_facts: bool = Field(
        default=True,
        description=(
            "Whether each association's study and trait links were followed. False drops pmid, "
            "trait, trait_efo_id, ancestry and study_accession to null for two thirds of the "
            "request budget — and the merge is keyed on `association_id`, so a later run WILL "
            "NOT backfill them. Delete the file to re-derive with study facts."
        ),
    )
    declared_use: str = Field(
        default="unstated",
        description=(
            "What was recorded on the licence row. It gates nothing here: EMBL-EBI names no "
            "licence, so `commercial_use` is written UNKNOWN rather than permitted, and the "
            "terms of the thousands of publications the Catalog summarizes are not settled by it."
        ),
    )
    skipped_offline: bool = Field(
        default=False,
        description=(
            "True means the pass did NOTHING. This reads the REST API and has no snapshot to "
            "fall back on, so offline is a no-op rather than a failure; any existing "
            "gwas_effects.csv is unchanged."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list, description="Advisory notes, aggregated by reason with a count."
    )
    note: str = Field(default="", description="How to regenerate, and what this table is not.")


# --------------------------------------------------------------------------- #
# Refreshing a derived sidecar (refresh.py)
# --------------------------------------------------------------------------- #
class SidecarRow(BaseModel):
    """One row of a derived sidecar, as it was read, with what is known about it.

    Cells travel as the **text they were**, never re-serialized from the parsed
    model: a float written `1.00` stays `1.00`, so nothing in a report or a
    reapply can silently reformat a value the author or the pass wrote.
    """

    subject: str = Field(
        description=(
            "The row's subject key — canonical JSON of the columns that decide whether two rows "
            "are the SAME row. Which columns those are is reported once per call in "
            "`subject_fields`; read it before reading this."
        )
    )
    fact_key: str = Field(
        description=(
            "Canonical JSON of the row's FACT columns with nulls dropped — the same normalization "
            "`integrity.fact_signature` hashes. Two rows with equal fact keys are the same fact, "
            "whoever wrote them: provenance (`source`, `status`, `fetched_at`) is outside every "
            "fact set except `sources.csv`'s, where `source` is the row's own subject."
        )
    )
    source: str | None = Field(
        default=None,
        description=(
            "The row's `source` cell, verbatim. `null` means the column was empty, which is not "
            "the same as a source named `''`."
        ),
    )
    source_proves_authored: bool | None = Field(
        default=None,
        description=(
            "Whether `source` is a value NO row of the freshly derived table uses — which proves "
            "the row was not written by this pass, so a human put it there. `false` means the "
            "value is one the fetcher also writes, which proves nothing either way. **`null` "
            "means the question could not be put** (the re-derived table named no sources at all), "
            "and a question that could not be put is not a question answered `false`."
        ),
    )
    cells: dict[str, str] = Field(
        default_factory=dict,
        description="The row's cells as text, so it can be read and, if wanted, pasted back.",
    )


class SidecarConflict(BaseModel):
    """A subject present in both copies whose facts differ. **Not resolvable here.**"""

    subject: str = Field(description="The subject both sides describe.")
    captured: list[SidecarRow] = Field(
        description="The rows the captured copy held for this subject."
    )
    rederived: list[SidecarRow] = Field(
        description="The rows the fresh derivation holds for this subject."
    )
    differing_fact_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Fact columns whose value set differs between the two sides — where to look first. "
            "Sorted, so two runs of the same conflict read the same."
        ),
    )
    unresolvable: str = Field(
        description=(
            "Why this is left alone. Two data points cannot separate an author's cell edit from an "
            "upstream revision, so nothing here guesses, prefers a side or merges. Read the two "
            "lists and decide; the captured copy is on disk at `capture` for as long as you "
            "keep it."
        )
    )


class SidecarRefreshReport(BaseModel):
    """What a non-destructive re-derivation of one sidecar found, kept and refused.

    Three row buckets are three fields on purpose: `only_in_capture`,
    `only_in_rederived` and `conflicts` answer three different questions, and one
    list with a type tag would let a reader collapse them into "things that
    changed" — which is exactly the reading that turns an unresolvable conflict
    into an assumed upstream update.
    """

    success: bool = Field(
        description=(
            "Whether the cycle completed: captured, re-derived, classified, reapplied. `false` "
            "leaves the sidecar exactly as it was — see `restored` and `refused`."
        )
    )
    spec_dir: str = Field(description="The spec directory.")
    sidecar: str = Field(description="Which sidecar was refreshed.")
    read_from: str | None = Field(
        default=None,
        description=(
            "Where the sidecar actually was. A module may keep it at the spec root or under "
            "`derived/`, and the file is put back where it came from — a refresh must not migrate "
            "a module's layout as a side effect."
        ),
    )
    capture: str | None = Field(
        default=None,
        description=(
            "The durable copy of the sidecar as it was BEFORE anything was deleted, outside the "
            "spec directory. It is crash insurance and an audit trail, not part of the module: an "
            "invented file inside the spec directory is not in the registry's recognised set and "
            "would be dropped by a server-side rebuild. Nothing here deletes it — it is yours to "
            "keep or remove."
        ),
    )
    capture_verified: bool = Field(
        default=False,
        description=(
            "Whether the capture was read back and its bytes hashed equal to the original BEFORE "
            "the delete. `false` means nothing was deleted: a sidecar with no verified capture is "
            "not deleted, ever."
        ),
    )
    resumed: bool = Field(
        default=False,
        description=(
            "True when a previous run of this tool died between the delete and the reapply and "
            "this run continued from the capture it left. The capture is never overwritten while "
            "it is unfinished, which is what makes a re-run safe rather than a second loss."
        ),
    )
    restored: bool = Field(
        default=False,
        description=(
            "True when the captured bytes were put back verbatim because the re-derivation could "
            "not be trusted — the source was unreachable, a pass did nothing, or it produced an "
            "empty table. Classifying against a partial derivation would report every real row as "
            "one upstream withdrew."
        ),
    )
    refused: str | None = Field(
        default=None,
        description=(
            "Why the cycle stopped, in full. Present whenever `success` is false. A refusal here "
            "is the tool declining to delete or to classify on evidence it does not have."
        ),
    )
    offline: bool = Field(
        default=False,
        description=(
            "The effective offline ceiling (`JMC_OFFLINE` OR the argument). A refresh needs the "
            "source: offline it would compare the file against a local cache, which answers a "
            "different question, so it refuses rather than producing an empty re-derivation that "
            "reads like 'upstream has nothing'."
        ),
    )
    passes_run: list[str] = Field(
        default_factory=list,
        description=(
            "The upstream pass functions that re-derived the table. More than one where more than "
            "one writes it: `gene_metrics.csv` is written by the constraint pass AND by the dosage "
            "pass, so refreshing it without both would re-derive half a table and report the other "
            "half as withdrawn."
        ),
    )
    declared_use_applied_to: list[str] = Field(
        default_factory=list,
        description=(
            "Which of the passes consumed `use`. The rest read no licence-bearing source, so the "
            "argument is irrelevant to them — named rather than left looking universal."
        ),
    )
    fact_fields: list[str] = Field(
        default_factory=list,
        description=(
            "The table's fact columns, from the format's own `*_FACT_FIELDS` tuple. Row identity "
            "here is derived from this and never from a written-down column list."
        ),
    )
    subject_fields: list[str] = Field(
        default_factory=list,
        description=(
            "The columns used as the row's subject: the fact columns the row model marks REQUIRED. "
            "Derived from the live models, and reported because it is an approximation — each "
            "pass's own merge key is a local expression inside the pass and is published nowhere "
            "(filed upstream). Where it is coarser than the real key it reports MORE rows as "
            "conflicting, which is the direction that repairs less."
        ),
    )
    fact_signature_before: str | None = Field(
        default=None,
        description="The table's fact signature as captured, from `integrity.fact_signature`.",
    )
    fact_signature_after: str | None = Field(
        default=None, description="The fact signature of the file this run leaves behind."
    )
    signature_moved: bool | None = Field(
        default=None,
        description=(
            "Whether the fact signature changed. **This is the canary**: a moved signature with no "
            "reapplied row and no conflict means the upstream source changed its answer, which is "
            "the only drift detector this format has. `null` means one of the two could not be "
            "computed, and is never a 'no'."
        ),
    )
    rows_before: int | None = Field(
        default=None, description="Rows in the captured copy. `null` when there was no copy."
    )
    rows_rederived: int | None = Field(
        default=None, description="Rows the pass wrote before anything was put back."
    )
    rows_after: int | None = Field(
        default=None, description="Rows in the file this run leaves behind."
    )
    only_in_capture: list[SidecarRow] = Field(
        default_factory=list,
        description=(
            "Rows whose SUBJECT the fresh derivation does not mention at all. Either the author "
            "added them or the source withdrew them, and `source_proves_authored` is what "
            "separates the two. The proven ones are in `reapplied`."
        ),
    )
    only_in_rederived: list[SidecarRow] = Field(
        default_factory=list,
        description="Rows on subjects the captured copy did not have. The source added these.",
    )
    conflicts: list[SidecarConflict] = Field(
        default_factory=list,
        description=(
            "Subjects both copies describe with differing facts. **Nothing here is resolved, "
            "merged or preferred** — see each entry's `unresolvable`. A `source_proves_authored` "
            "row inside one narrows what happened and is still not acted on: proving who wrote a "
            "row does not settle which of two answers about the world is right."
        ),
    )
    reapplied: list[SidecarRow] = Field(
        default_factory=list,
        description=(
            "Rows put back into the refreshed file: exactly the `only_in_capture` rows whose "
            "`source` proves a human wrote them. Their original cells are appended verbatim, so no "
            "value is re-rendered. Everything else was reported and left out."
        ),
    )
    withheld: list[SidecarRow] = Field(
        default_factory=list,
        description=(
            "`only_in_capture` rows NOT put back, because nothing proves who wrote them: the "
            "source may simply have withdrawn the row. They are in the capture if you want them."
        ),
    )
    listing_truncated: bool = Field(
        default=False,
        description=(
            "True when a row list was capped for size. The COUNTS above are always complete; only "
            "the listings are cut, and `warnings` says by how much."
        ),
    )
    findings: list[LintFinding] = Field(
        default_factory=list,
        description=(
            "Upstream findings, `level` preserved verbatim — a parse error in either copy arrives "
            "as `error` and is why the cycle refused."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list, description="Advisory notes, aggregated by reason with a count."
    )
    next_step: str = Field(default="", description="What to do with this result.")
    note: str = Field(
        default="",
        description="What this tool does not decide, and what a moved signature means.",
    )
    produced_by: SchemaVersions = Field(description=_PRODUCED_BY_WHY)


# --------------------------------------------------------------------------- #
# Overrides — the record behind a value that outranks a source (RM16)
# --------------------------------------------------------------------------- #
class OverrideResult(BaseModel):
    """What was recorded, and where it went. Nothing here makes a check pass."""

    written_to: str = Field(description="The provenance.json this landed in.")
    logged_to: str = Field(
        description="The authoring log. It travels with the module and publishes with the compile."
    )
    replaced_existing: bool = Field(
        description="Whether a record for this (variant_key, field) was already on file. "
        "Replacing one is legitimate — a judgement can be revised — and it is reported "
        "rather than silent, because the previous reason is gone."
    )
    record: OverrideRecord = Field(description="Exactly what was written.")
    note: str = Field(description="What this does and does not do.")


class ReviewQueue(BaseModel):
    """The overridden rows, ranked worst-first. Offline; the archive half is partial."""

    spec_dir: str = Field(description="The module read.")
    total: int = Field(description="Records on file.")
    unbound: int = Field(
        description="Records whose authored cell has **changed** since — the reason no longer "
        "describes the value it is attached to. Read these first."
    )
    subject_absent: int = Field(
        default=0,
        description="Records whose cell could not be found at all: the row is gone, or "
        "`variants.csv` does not carry that column. **Not the same as unbound** — nobody edited "
        "anything, the question simply could not be put, and `still_bound` is null on these.",
    )
    retirable: int = Field(
        description="Records whose mismatch has resolved: the archive caught up and the "
        "override was vindicated. The only such evidence this format holds."
    )
    entries: list[QueuedOverride] = Field(description="Ranked; standing and unbound first.")
    other_provenance: list[str] = Field(
        default_factory=list,
        description="Provenance items in the file that are not ours. Kept, never rewritten — "
        "another writer's record is not this tool's to discard.",
    )


# --------------------------------------------------------------------------- #
# Comparing two spec directories (RM19)
# --------------------------------------------------------------------------- #
class ComparedSide(BaseModel):
    """One side of a comparison, as it was read."""

    path: str = Field(description="The spec directory.")
    genome_build: str | None = Field(
        default=None, description="What it declares. null when no spec file could be read."
    )
    tables: int = Field(description="Authored tables found on disk.")


class FrameVerdict(BaseModel):
    """The declared-build comparison. Read this before any row count."""

    left_build: str | None
    right_build: str | None
    verdict: str = Field(description="`same` | `moved` | `unknown`.")
    note: str = Field(
        description="When the builds differ the row counts below are **not comparable** rather "
        "than clean: identical coordinate rows on two assemblies describe different loci, and the "
        "reassuring answer is the dangerous one."
    )


class ChangeGroupOut(BaseModel):
    """Rows that changed **in the same set of columns** — one fact, once."""

    columns: list[str] = Field(description="The columns that differ, sorted.")
    rows: int = Field(description="How many rows changed in exactly this set.")
    examples: list[dict] = Field(
        description="A few keys with their before/after cells, truncated. For the raw cells, "
        "run `diff` — this tool deliberately does not reproduce it."
    )


class TableComparison(BaseModel):
    """One authored table, at the table and row grains."""

    csv: str = Field(description="Preferred spelling.")
    identity_scope: str = Field(
        description="Which hash an edit here moves: `content_signature`, or `sources.signature` "
        "for the licensing table — which is authored and **outside** `content_signature`, so a "
        "licence edit that looks invisible is not."
    )
    presence: str = Field(description="`both` | `left_only` | `right_only` | `unknown`.")
    spelling_left: str | None = Field(default=None)
    spelling_right: str | None = Field(default=None)
    rows_left: int | None = None
    rows_right: int | None = None
    row_key: str = Field(description="`keyed` | `unkeyed`. Unkeyed rows are counted, never paired.")
    key_collisions: int = Field(
        default=0, description="Rows sharing a natural key. Only the first of each was compared."
    )
    unchanged: int | None = None
    added: int | None = None
    removed: int | None = None
    changed: list[ChangeGroupOut] = Field(default_factory=list)


class DerivedComparison(BaseModel):
    """One machine-written sidecar, compared on its **facts** rather than its bytes."""

    csv: str
    verdict: str = Field(description="`same` | `moved` | `unknown`.")
    left_signature: str | None = None
    right_signature: str | None = None
    signature_source: str = Field(description="`recomputed` here — read from the files on disk.")
    rows_left: int | None = None
    rows_right: int | None = None


class MetadataDelta(BaseModel):
    """Something that moved which no identity records."""

    what: str
    left: str | None = None
    right: str | None = None
    in_hash: bool = Field(
        default=False,
        description="False throughout: the field exists to say **this moved and no hash will "
        "tell you**.",
    )


class Unknown(BaseModel):
    """One thing this report is not telling you, and why. Never a silent omission."""

    subject: str
    reason: str


class ModuleComparison(BaseModel):
    """What moved between two spec directories. Never which side is right."""

    left: ComparedSide
    right: ComparedSide
    frame: FrameVerdict
    content: str = Field(description="`same` | `moved` | `unknown`, over `content_signature`.")
    left_content_signature: str | None = None
    right_content_signature: str | None = None
    tables: list[TableComparison] = Field(default_factory=list)
    derived: list[DerivedComparison] = Field(default_factory=list)
    metadata: list[MetadataDelta] = Field(default_factory=list)
    unknown: list[Unknown] = Field(default_factory=list)
    note: str


# --------------------------------------------------------------------------- #
# Study facts already in the module (RM22)
# --------------------------------------------------------------------------- #
class StudyFact(BaseModel):
    """What the GWAS pass already recorded about one study, for authoring `studies.csv`."""

    pmid: str | None = Field(default=None, description="PubMed id, as the Catalog reported it.")
    study_accession: str | None = Field(
        default=None, description="GWAS Catalog accession, e.g. GCST006941."
    )
    ancestry: str | None = Field(
        default=None,
        description=(
            "The studied cohort's ancestry, free text exactly as the GWAS Catalog records it "
            "('European', 'East Asian', 'Hispanic or Latin American'). This is what "
            "`studies.csv`'s `population` is asking for. Null means the pass ran with "
            "`study_facts` off, or the Catalog published none — NOT that the cohort is unknown "
            "to anyone, and never a reason to write a citation label into the column instead."
        ),
    )
    trait: str | None = Field(default=None, description="Reported trait, as the Catalog names it.")
    trait_efo_id: str | None = Field(default=None, description="EFO CURIE for that trait.")
    rows: int = Field(description="How many `gwas_effects.csv` rows carry this study.")


class StudyFacts(BaseModel):
    """Per-study facts read out of a module's own `gwas_effects.csv`. Writes nothing.

    Surfaced rather than filled. `population` is not redundancy-bearing, so writing
    it from here would not make any check vacuous — but a study carries several
    ancestries and `ancestry` is a joined string, so which of them belongs in a
    given row is a judgement, and the discriminator says surface it.
    """

    spec_dir: str = Field(description="The spec directory read.")
    studies: list[StudyFact] = Field(
        default_factory=list, description="One entry per distinct study."
    )
    with_ancestry: int = Field(description="How many of them carry an ancestry.")
    note: str = Field(description="What was read, and what it does and does not settle.")


# --------------------------------------------------------------------------- #
# Comparison against a published version (RM19)
# --------------------------------------------------------------------------- #
class FileDelta(BaseModel):
    """One authored file, local bytes against the bytes the published manifest recorded."""

    name: str = Field(description="The authored file, as the manifest names it.")
    verdict: str = Field(
        description=(
            "`same` | `moved` | `unknown`. **Subordinate to `content`, always.** Byte equality "
            "is decisive — an identical hash is an identical file. Byte INEQUALITY means almost "
            "nothing on its own: a CRLF, a reordered column, a reordered row and `1.00` written "
            "as `1.0` each move this and leave `content_signature` exactly where it was. Use "
            "this to decide which files to look at, never to claim a content change."
        )
    )
    local_sha256: str | None = Field(default=None, description="Local digest, or null if absent.")
    published_sha256: str | None = Field(
        default=None,
        description="What the published manifest recorded, or null if it carried none.",
    )


class PublishedComparison(BaseModel):
    """This spec directory against one published version's manifest. No download.

    One or two bounded GETs and nothing else: `resolve_version` when the version
    is `latest`, then the manifest. It never fetches the published module's
    authored rows, so it can say *whether* content differs and never *which rows*
    — the handover for that is named in `next_step`.
    """

    spec_dir: str = Field(description="The local spec directory.")
    canonical_id: str = Field(description="namespace/name@version, as resolved.")
    target: str = Field(description="Which registry instance answered.")
    content: str = Field(
        description=(
            "`same` | `moved` | `unknown` on `content_signature` — the exact content verdict, "
            "and the first thing to read. `same` means every authored row matches what was "
            "published, whatever the per-file hashes below say."
        )
    )
    local_content_signature: str | None = Field(default=None)
    published_content_signature: str | None = Field(default=None)
    frame: FrameVerdict = Field(
        description=(
            "Declared genome build on each side. When these differ, nothing below is comparable."
        )
    )
    files: list[FileDelta] = Field(
        default_factory=list, description="Per-authored-file byte comparison. Read `content` first."
    )
    facts: list[DerivedComparison] = Field(
        default_factory=list,
        description=(
            "Each fact-signature block the published manifest carries, against this spec's own. "
            "A moved fact signature with unchanged content is the canary: a source revised an "
            "answer under you."
        ),
    )
    metadata: list[MetadataDelta] = Field(
        default_factory=list,
        description="What differs outside every hash — readme, closure, compiler version.",
    )
    unknown: list[Unknown] = Field(
        default_factory=list,
        description="What could not be compared, and why. Never a silent omission.",
    )
    next_step: str = Field(description="How to get row-level detail, if the verdict warrants it.")
    note: str = Field(description="What this report does and does not claim.")


# --------------------------------------------------------------------------- #
# Logs, read before they are published (RM25)
# --------------------------------------------------------------------------- #
class LogFinding(BaseModel):
    """One thing in one log the author may not mean to publish."""

    log: str = Field(description="The log file, relative to the spec directory.")
    kind: str = Field(
        description=(
            "`absolute_path` | `credential_shaped` | `very_long_line` | `large_file`. Named "
            "rather than scored: this is not a secret scanner and the question is narrow — "
            "would the author be surprised to see this in the catalog?"
        )
    )
    line: int | None = Field(
        default=None, description="1-based line, or null for a whole-file finding."
    )
    detail: str = Field(description="What was found, and why it is worth a second look.")


class LogReview(BaseModel):
    """Every log a compile would sweep up, and what is in them. Changes nothing.

    **Report, never strip.** A log is a provenance record and silently editing one
    is the opposite of what it exists for. Nothing here is a refusal: publishing a
    flagged log is a legitimate decision, and it is the author's.
    """

    spec_dir: str = Field(description="The spec directory read.")
    logs: list[str] = Field(
        default_factory=list,
        description="Every file a compile would collect — `logs/**/*.log` plus top-level `*.log`.",
    )
    total_bytes: int = Field(description="What would travel to the catalog, in bytes.")
    findings: list[LogFinding] = Field(
        default_factory=list, description="Ordered by log, then line."
    )
    note: str = Field(description="What this does and does not claim.")
