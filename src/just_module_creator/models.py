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
        description="Enricher-produced files. Do not hand-author. `sources.csv` used to "
        "carry an exception here and is now a table kind in its own right, listed above."
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
    """Currency of every gene symbol and trait CURIE in a spec. Writes nothing."""

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
            "resolves anyway because dbSNP is dense. Reported, never repaired: which half is "
            "wrong is not something a lookup can know."
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
    """A source consulted, and the `sources.csv` row nothing will write for it.

    Deliberately carries no `license`, `commercial_use` or `share_alike`: pointing
    at the terms is help, asserting them is a guess, and `declared_use` is a
    licence position only the author can take. Upstream's `TERMS_BY_SOURCE` has no
    entry for any literature service, which is filed rather than papered over.
    """

    source: str = Field(description="The join value for sources.csv, e.g. `pubmed`.")
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
        description="The sources.csv rows you now owe, and why none was written.",
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
            "reported**. Report, never repair: rewriting your value would destroy the evidence "
            "that the source and you disagree, and only you know which is right."
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
    warnings: list[str] = Field(default_factory=list, description="Advisory notes.")
    note: str = Field(default="", description="How to regenerate.")
