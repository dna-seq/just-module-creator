# clinical_assertions.csv — what a clinical archive says about one allele, and how much review sits behind it

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

> **Correction, 2026-08-20 (later than the banner above).** This file says `describe_table`
> refuses this table and quotes that refusal's wording. Both were true when written and are not
> now: **ask `describe_machine_table`**, which answers the live columns of all seven
> machine-produced tables and carries `hand_authored=False` in its own schema. Nothing about
> *you read this, you never hand-finish it* has changed — that signal is now carried by the tool
> split rather than by a refusal.

## What it is

`clinical_assertions.csv` answers one question per row: *for this one ALT allele at this one
coordinate, what does ClinVar call it, under which review status, at what star rating, and under
which record id.* It is the sixth derived-fact sidecar (0.6, RM25), written by the enricher's
`assertions` pass and never fetched by the compiler.

It exists because the star rating was a number this workspace already computed and then threw away,
twice. `clinical.ClinSigFinding.confidence` rendered it into a warning string
(`enricher/src/just_dna_enricher/clinical.py:85-87`) and `clinvar_draft.draft_gene_panel` used it as a
*drafting filter* (default 2) and kept nothing (`clinvar_draft.py:503`, `:516`). The consequence:
"a compiled module flattened a one-star single submission and a practice guideline to the same
`clin_sig`" (`schema/src/just_dna_format/assertions.py:10-19`). Its audience is a consumer that wants
to weight a clinical call by the evidence behind it, and a curator who wants to see whether the
module's own flat `clin_sig` is hiding a per-allele disagreement.

**It records; it does not adjudicate.** Whether the *author's* `clin_sig` agrees with ClinVar's is
`enricher.clinical.verify_clin_sig`'s question, which warns in **both** modes on purpose — "failing
would make the format arbitrate a clinical dispute" (`docs/FAQ.md:142-146`). Nothing in this table or
its pass moves that line, and the compiler's own check over it is a position-orphan check and nothing
more (`compiler.py:5756 _cross_check_clinical_assertions`).

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.assertions.ClinicalAssertionRow` (`schema/src/just_dna_format/assertions.py:77`) |
| Parquet | `clinical_assertions.parquet` — in `ARTIFACT_PARQUETS` (`compiler.py:294`), so inside `artifact.digest`. Registered in `_FACT_TABLES` (`compiler.py:329`) |
| Natural / dedup key | `(variant_key, variation_id)` — the enricher's merge key (`enricher/assertions.py:269`, `:302`); a `not_found` row is carried under `(variant_key, None)` (`:283`). **Not enforced by the compiler** — `_TABLE_DUPE_KEYS` (`compiler.py:249`) covers authored table kinds only |
| Authored or machine-produced | **machine-produced, human-overridable by design.** Standalone `BaseModel`, not an `AuthoredModel`; `extra="forbid"` so a typo'd column is refused rather than dropped (`assertions.py:78-85`) |
| Who writes it | `just_dna_enricher.assertions.enrich_clinical_assertions` — `just-dna-enricher assertions <dir>` (`enricher/cli.py:498-546`). **One producer, and no MCP tool** — see Gotcha 2 |
| Fact signature | `integrity.clinical_assertion_signature` (`schema/src/just_dna_format/integrity.py:331`) over `assertions.CLINICAL_ASSERTION_FACT_FIELDS` (`assertions.py:60`) — **13 of 17 fields**. Out: `rsid`, `source`, `status`, `fetched_at` → `manifest.clinical_assertions.signature` |
| In `content_signature`? | **No.** `content_signature` reads `variants.csv`, `studies.csv` and `_TABLE_KINDS` only (`compiler.py:3868-3872`); `_INPUT_FILES` (`compiler.py:267`) does not list it |
| In `artifact.digest`? | **Yes**, via its parquet. Also byte-hashed into `manifest.derived[]` — transport only (`compiler.py:342-358`) |
| Manifest block | `manifest.clinical_assertions` = `ClinicalAssertions` (`schema/manifest.py:441`), built by `compiler.py:4759 _clinical_assertions_block`; **absent** (`None`) when the module carries no such sidecar |
| Licence layer | `clinical_assertion` ∈ `vocab.VALID_SOURCE_LAYERS` (`schema/vocab.py:554-566`) — fact-class, so it never taints a module the way `annotation` does |
| Location | root or `derived/clinical_assertions.csv`, routed through `licensing.sidecar_path`. Both at once = `layout.SidecarCollision`, an error, never a merge |

## Who populates what

- **enricher pass — every column.** `enrich_clinical_assertions` (`enricher/assertions.py:150`,
  `just-dna-enricher assertions <dir>`) fills all seventeen. Its input is **`resolution.csv`, not
  `variants.csv`** (`assertions.py:180-184`, refuses with "run `just-dna-enricher enrich` first"), because
  "a clinical record is per *allele at a coordinate*" — which is also what keeps it clear of the
  multi-allelic-rsID problem: `rs33922842` in HBB carries a pathogenic, a benign and an uncertain
  allele at one locus, so an rsID-level lookup "would manufacture disagreements out of ClinVar
  agreeing with itself" (`enricher/assertions.py:11-15`).
  - `variant_key` / `chrom` / `start` / `ref` / `alt` — from the resolution row, one entry per ALT,
    re-keyed per allele with `derive_variant_key(None, chrom, start, ref, alt, build=…)`
    (`assertions.py:126-131`).
  - `rsid` — **from the module's own `resolution.csv`, not from ClinVar.** The lookup is allele-exact
    and returns no rsID at all (`assertions.py:129-134`). This is why it sits outside the fact set.
  - `clin_sig` / `clin_sig_raw` / `review_status` / `review_stars` / `condition` / `variation_id` —
    straight from `clinvar.lookup_clin_sig` (`enricher/clinvar.py:113`), which returns a **list** per
    allele ordered best-reviewed first (`ORDER BY … review_stars DESC, variation_id`, `clinvar.py:146`).
  - `genome_build` — pinned to `ASSERTION_GENOME_BUILD = "GRCh38"` (`assertions.py:58`), never copied
    from the resolution row.
  - `dataset` — the snapshot's own `release.json` (`snapshot_dataset`, `assertions.py:137`);
    `clinvar_unknown` when the snapshot cannot state one, "rather than a fabricated date".
  - `source="clinvar"`, `status` ∈ `resolved|not_found`, `fetched_at` — provenance, all three outside
    the fact hash.
- **author** — no column is *expected* of a human and every column *may* be written by one.
  `source` is open and names `clinvar|manual|reversed` (`assertions.py:185-190`), so `manual` is the
  declared route for a curator override, and MODULE_LIFECYCLE §6.3 lists "curator overrides" as what
  deleting this file costs (`docs/MODULE_LIFECYCLE.md:416`). Read Gotcha 5 before writing one.
- **drafter** — **none for this table.** `clinvar_draft` drafts `variants.csv` / `studies.csv` and
  writes the star rating into free prose there instead (`clinvar_draft.py:321-325`, e.g.
  `conclusion = "ClinVar: pathogenic (3★) — …"`). No `<<REPLACE>>` stub exists here.
- **compiler-stamped** — nothing in the CSV. The compiler adds exactly one column **in the parquet
  only**: `module` (measured on the compiled artifact — parquet schema is the model's 17 fields plus
  a leading `module: String`). No column here is `base.stamped_identity_field`, `COMPILER_MANAGED` or
  `reject_compiler_filled`.
- **registry-stamped** — nothing. The registry parses the CSV header only, to drop unknown columns on
  an upgrade (`just-dna-registry/src/just_dna_registry/services/upgrade.py:169`, `:471`, `:478`); it
  interprets no cell.
- **nobody, ever** — no column is permanently unwritten. All seventeen are populated by the one pass.

**Cells no tool may fill even though it easily could.** Neither `hints.REDUNDANCY_BEARING` nor
`hints.ATTESTATION_BEARING` names any column of *this* table (verified against installed compiler
0.6.1: the redundancy map's fourteen keys are `acmg_sf, alts, chrom, clin_sig, doi, evidence_level,
function_status, p_value_num, pmid, provenance_quote, provenance_regex, ref, rsid, start`, and
attestation is `provenance_quote, provenance_regex`). The relevant refusal points the *other* way:
`clin_sig` **on `variants.csv`** is redundancy-bearing, with the reason
`"enricher.clinical.verify_clin_sig (authored call vs ClinVar's)"`. So the standing rule is —
**never copy a `clin_sig` out of this sidecar into `variants.csv`.** That is filling a cell from the
source that checks it, and it makes `verify_clin_sig` compare ClinVar against ClinVar and agree
perfectly, while the row moves from honestly unverified to apparently verified.

## What moving this table moves

Measured, not asserted: `reference_examples/hboc_palb2` compiled with installed compiler 0.6.1 into a
scratch dir, baseline twice (byte-identical), then one mutation per row.

| An edit here | `content_signature` | `clinical_assertion_signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| baseline, compiled twice | `43ad8ac13609` (same) | `3a3b263c3c69` (same) | `6876cc793dec` (same) | `verification` block published |
| add a row (an orphan ClinVar record) | unmoved | **moved** → `13205c4b1143` | **moved** → `31528fba70ef` | still published; one **warning** |
| edit an authored fact cell (`review_stars` 0→1) | unmoved | **moved** → `cf4366973fd2` | **moved** → `a3a2c86f227c` | still published |
| edit a provenance-only cell (`fetched_at`) | unmoved | **unmoved** | **moved** → `d79c406ba3da` | still published |
| reorder every row + rewrite as CRLF | unmoved | **unmoved** (order-independent) | **moved** → `a0d3057cf45b` | still published |
| re-run the producing pass with nothing new | unmoved | unmoved (merge-not-clobber re-states, adds nothing) | unmoved | still published |
| delete the file and re-derive | unmoved | same facts → same signature; a fresh `fetched_at` alone | **moved** | still published |
| delete the file entirely | unmoved | block **absent** (`None`) | **moved** → `19088b41440b` | still published |
| recompile under a newer toolchain | unmoved | unmoved | may move (compiler/polars bytes) | unchanged |
| *contrast:* edit one byte of `variants.csv` | **moved** → `f9a24a64295e` | unmoved | moved | **verification DROPPED** — "verification.json is stale: the attestation was computed over different module bytes" |

1. **Is this table inside `content_signature`?** No. `content_signature` reads only
   `module_spec.yaml`'s defaults plus `variants.csv`, `studies.csv` and the authored table kinds
   (`compiler.py:3868-3872`). Its identity is instead the **fact** hash
   `clinical_assertion_signature` over `CLINICAL_ASSERTION_FACT_FIELDS` — thirteen fields.
   Deliberately left out: `source`, `status`, `fetched_at` (provenance, "so a hand-curated and a
   ClinVar-filled table carrying the same assertions hash equal", `assertions.py:41-43`) and **`rsid`**,
   which is the one that inverts a sibling: `FREQUENCY_FACT_FIELDS` keeps its rsID because gnomAD
   reports one, while here "the archive lookup is allele-exact … and returns no rsID at all"
   (`integrity.py:339-345`). `review_status` **and** `review_stars` are both inside although one
   determines the other — the mapping is a ClinVar convention this tier does not hold, "so the two
   columns are independent inputs here" (`assertions.py:56-58`).
2. **Is it inside `artifact.digest`?** Yes, via `clinical_assertions.parquet` in `ARTIFACT_PARQUETS`
   (`compiler.py:294`) — confirmed present in `manifest.artifact.files` on the compiled example. So a
   provenance-only edit no signature sees still moves the digest, because the bytes differ (row 4
   above). The CSV is additionally byte-hashed into `manifest.derived[]` (`compiler.py:342-358`) —
   **transport only**; a consumer that reads that hash as identity "will see a reverse→recompile cycle
   as tampering".
3. **Does an edit here un-close the module?** **No.** The attestation binds
   `compiler.authored_input_entries` (`compiler.py:361`), which is `_INPUT_FILES` newline-normalized —
   `module_spec.yaml`, `variants.csv`, `studies.csv`, the table kinds. This sidecar is not in that set,
   for the stated reason that "the derived sidecars carry per-run noise (`fetched_at`) that would
   invalidate an attestation on a re-enrichment that changed nothing anyone claimed"
   (`compiler.py:374-376`). Measured: every mutation of this file above left `verification` published;
   one byte of `variants.csv` dropped it. Note the asymmetry the other way — an `authorship:` append
   un-closes a module while moving no identity at all.
4. **Is this table part of the canary?** **Yes, and it is one of the better instruments for it.**
   MODULE_LIFECYCLE §5.1 row 3 — content unmoved + a fact signature moved + digest moved — reads as
   "nobody authored anything and a derived fact changed: the upstream source said something different
   this time" (`docs/MODULE_LIFECYCLE.md:269`). This table can produce that reading, and a re-review is
   *precisely* the change it was built to make visible: `dataset` is inside the fact set, so a newer
   ClinVar release under an unchanged call still moves the signature. **But detecting it requires
   delete-and-re-derive**: merge-not-clobber "means a re-run never re-asks about a row already
   recorded, so a source that quietly revised an existing answer moves nothing at all"
   (`MODULE_LIFECYCLE.md:301-306`). No command performs that sequence; it is RM83.

## Required to exist

- **Nothing requires it.** It is optional, always: absent → `manifest.clinical_assertions` is
  `None`, the registry facet is `0`, and no validation complains.
- **It requires `resolution.csv`.** The pass refuses without one — *"no resolution.csv in {dir} — the
  clinical-assertion pass reads resolved coordinates, so run `just-dna-enricher enrich` first"*
  (`enricher/assertions.py:182-184`). Which in turn means the module must already have variants with
  identities the resolver could place.
- **It drags in a licence row.** On every successful write the pass calls `record_source_terms(…,
  "clinical_assertion", …)` (`assertions.py:359`), adding a `clinvar` / `clinical_assertion` row to
  `licensing.csv` — and raises `ClinicalAssertionError` if it cannot. On `hboc_palb2` that row exists
  beside three other `clinvar` rows on different layers.
- **It requires a ClinVar snapshot.** With none reachable the pass is a **no-op with a warning**, not a
  failure (`assertions.py:219-227`) — see Gotcha 6.

## The columns that carry judgement

Not the full list — run `authoring_reference` for that. These are the ones a reader misreads.

- **`review_stars`** — the whole reason the table exists, and **tri-state**. `None` means the archive
  stated no review status **or** stated a wording this release does not model; `0` is ClinVar's own
  rating "no assertion criteria provided". "An unrecognized wording is also `None`, not `0` — a
  wording this release does not model is an unknown, and answering `0` would record a definite rating
  where none was read" (`enricher/clinvar_build.py:169-183`). Stored rather than derived, inverting
  the house pattern for a convenience number, because the CLNREVSTAT→0-4 mapping is a **ClinVar
  convention** and Principle 2 keeps those out of the schema tier; the schema holds only `ge=0, le=4`.
  The mapping lives in exactly one place, `clinvar_build._REVIEW_STARS` (`:140`).
- **`review_status`** — ClinVar's verbatim wording, **open, not a vocabulary**: "it is ClinVar's
  phrasing and it changes on ClinVar's schedule, so closing it here would make a future release
  unloadable for no gain" (`assertions.py:142-149`). Read it, never match on it exactly.
- **`clin_sig` vs `clin_sig_raw`** — the first is normalized to `vocab.VALID_CLIN_SIG` at the enricher
  boundary; the second is the archive's verbatim token (`Pathogenic/Likely_pathogenic`), kept "so the
  normalization above stays auditable and a value the mapping does not model is still visible".
  Neither is an adjudication.
- **`genome_build`** — **load-bearing, not decorative.** The snapshot's lookup key is
  `(chrom, start, ref, alt)` and carries no assembly, so a GRCh37 coordinate is a *well-formed* query
  returning a different variant's clinical call under this module's key (`assertions.py:117-125`).
- **`alt`** — **one** allele, singular, unlike `resolution.csv`'s comma-joined `alts`, "because a
  clinical call is per-allele" (`assertions.py:111-118`).
- **`condition`** — descriptive, outside nothing (it *is* in the fact set) but see Gotcha 8: it is a
  pipe-joined list of every condition on that record, not one condition per row.
- **`status`** — `not_found` is a **fact**: "the archive was consulted and has no record for this
  allele", materially different from an allele that was never queried, which has no row at all
  (`assertions.py:192-199`). Do not read an absent row as a negative.
- **`dataset`** — a fact, inside the hash. `clinvar_2026-06-27`. Never a route; which release answered
  is this column's job and `source`'s is only to name the source.
- **`variation_id`** — the archive's stable record id, the thing a consumer cites and the join key
  back into ClinVar. Inside the fact set for that reason.

## Gotchas

Ordered by how likely a first-timer is to hit them.

**1 — `variant_key` mostly does NOT join to `weights.parquet`, despite what the field says.** The
field description reads *"Coordinate-derived identity of the allele (matches the post-expansion
weights key)"* (`assertions.py:91-93`). Measured on the compiled `hboc_palb2`: **4 of 24** assertion
keys match any weights key, and **4 of 18** weights rows have a matching assertion key. The reason is
`base.derive_variant_key` case 1 — *"an rsid row keeps its rsid, unchanged"* (`base.py:241`) — and
`VariantRow` **freezes** that key at load from the authored columns (RM43). So an rsID-only authored
row keeps `variant_key = "rs118203998"` forever, while the assertion row for the same allele carries
`ga4gh:VA.PxEq86dy…`. The clause is only true for the case it names: a one-to-many rsID *is*
re-keyed by the expansion, and those are exactly the four that matched (`rs587776418` and
`rs1555461597`, two loci each). **Cost:** a naive `join(on="variant_key")` silently returns 4 rows
where the author expected 18. Join at position level (`chrom:start:ref`), which is what the compiler's
own cross-check does (`compiler.py:5776-5788`). Candidate upstream doc defect — see the summary.

**2 — the authoring plugin cannot produce this table, and cannot describe it.**
`src/just_module_creator/tools/passes.py:93` — `_FACT_PASSES = ("frequencies", "gene_metrics",
"dosage")`, and `enrich_facts` rejects anything else (`:712-716`). `clinical_assertions.csv` is not in
`draft.DRAFTABLE`, so `describe_table` / `table_requirements` / `get_template` / `lint_rows` all
refuse: *"Unknown table kind 'clinical_assertions.csv'. Authorable kinds: activity_phenotype.csv, …"*
(probed against the installed compiler). **The only route is the enricher CLI**:
`just-dna-enricher assertions <spec_dir>` (`skills/module-101/references/CLI.md:84`, listed there
under "no MCP tool"). A module authored end to end through the MCP surface can never acquire one.

**3 — `--strict` on this pass fails on ordinary, correct data.** `mode == "strict"` raises when *any*
resolved allele has no ClinVar record (`assertions.py:349-354`), and the error says so itself: *"Most
variants are not in ClinVar at all, so this is usually correct data rather than a read failure — use
mode='best_effort'."* Default is `--best-effort`; do not reach for `--strict` because other passes
take it.

> 🚧 **ROADWORKS — `--strict` here refuses the *usual* answer.**
> **Current state.** The gate fires on "this allele has no ClinVar record", which is true of most
> alleles in most modules. So `--strict` is not a stricter version of the same run; it is a run that
> fails on correct data. The same shape sits on the gene-metrics pass, whose gate fires on a gene
> gnomAD has no constraint row for.
> **Expected state.** A strict ladder that escalates only on a *read failure* — the distinction the
> error message itself draws. It is not implemented; the flag is all-or-nothing.
> **Guard.** Run this pass at its default. If your pipeline sets `--strict` globally, exempt the
> assertions and gene-metrics passes explicitly, and do not read the resulting failure as evidence
> that the module is wrong.

**4 — a GRCh37 module gets zero rows and one warning line.** Rows whose `genome_build` is not GRCh38
are never queried (`assertions.py:112-114`), reported in `off_build` — deliberately **kept apart from
`missing`**, "because nobody asked about them", and deliberately **outside the strict gate**, since
"refusing would make a GRCh37 module uncompilable for a reason no authored edit could fix"
(`assertions.py:345-348`). The signal is one aggregated `logger.warning` naming the build, plus a
yellow stderr line from the CLI (`enricher/cli.py:542-547`). `reference_examples/cyp2c9_warfarin_grch37`
and `grch37_build` carry no `clinical_assertions.csv`, and this is why.

**5 — merge-not-clobber, with exactly one withdrawal.** Existing rows are authoritative and merged on
`(variant_key, variation_id)`; to regenerate you delete the file first, which discards curator
overrides with the stale rows (`MODULE_LIFECYCLE.md:416`, RM83). **Two behaviours that differ from
`enrich_frequencies` and matter:** every in-scope allele is re-queried on *every* run, not skipped
when a row exists — "ClinVar *grows*: skipping on `variant_key` meant a newly-published record could
never reach an allele the table already mentioned" (`assertions.py:233-240`). And a `not_found` row is
**withdrawn** once the archive answers: "this is the one place the pass removes a row it wrote
earlier … `not_found` is this pass's own bookkeeping and it stops being true the moment a record
exists" (`assertions.py:326-334`). A `resolved` row, and any row a curator wrote, both survive.

**6 — no snapshot means a green run with no table.** With no ClinVar snapshot found and `--offline`,
or with provisioning failing, the pass logs *"Clinical-assertion pass skipped: no ClinVar snapshot is
reachable … Any existing clinical_assertions.csv is kept as the pin"* and returns
`skipped_no_snapshot=True` (`assertions.py:219-227`). Same outcome for a snapshot that is present but
unloadable (`_unusable`, `:242-266`) — the published ClinVar repo still carries a pre-split
`clinvar.parquet` whose columns are raw VCF INFO fields, so this is not hypothetical. A compile after
that is clean and the manifest block is simply absent; **absence is not "ClinVar had nothing".**

**7 — the star rating already lives in the module as prose, and the two can disagree.** The drafter
writes `conclusion = "ClinVar: pathogenic (3★) — <conditions>"` into `variants.csv`
(`clinvar_draft.py:321-325`); verified on `hboc_palb2`'s `variants.csv`, every row carries one. That
string is a snapshot taken at draft time and **nothing ever updates it**. Re-derive
`clinical_assertions.csv` against a newer release and the structured `review_stars` moves while the
prose does not. Trust the column, not the sentence.

**8 — "one row per (allele, record)" does not mean one row per condition.** The docstring justifies
the grain with "ClinVar genuinely holds several records for one allele under different conditions"
(`schema/assertions.py:28-31`), which reads as though conditions split rows. Measured on `hboc_palb2`:
**zero** alleles carry more than one record, and one `condition` cell holds up to **15** pipe-joined
conditions (`rs180177132` `C>T`). What actually multiplies rows there is the ALT allele — six of
sixteen rsIDs carry 2–3 alleles each. A consumer wanting per-condition granularity must split the
cell, and cannot recover which condition drove which submitter's call.

**9 — the compiler never errors over this table, in either mode.** `_clinical_assertion_checks`
returns `([], warnings)` unconditionally (`compiler.py:4435-4436`), so the only output is the
position-orphan warning: *"clinical_assertions.csv describes N coordinate(s) no variant in this module
sits at"* — measured, on both `--strict` and default. That is by design: an over-broad sidecar is the
ordinary result of enriching and then narrowing a variant list.

**10 — `rs33922842`-shaped disagreements are real and the table is where they surface.** On
`hboc_palb2`, `variants.csv` states a flat `clin_sig` for `rs118203998` (`pathogenic`) while the
assertion table records `G>A uncertain_significance (0★)`, `G>C pathogenic (2★)`, `G>T pathogenic
(3★)` under three different VariationIDs. Likewise `rs878855123`: `C>A pathogenic (3★)`,
`C>G uncertain_significance (1★)`, `C>T conflicting (1★)`. **The flat value is not wrong** — the
author's `genotype` names the specific allele — but any consumer that reads `clin_sig` off the variant
row and applies it to whatever ALT it observed will call a 0-star VUS pathogenic.

**11 — the drafter's identity collapse upstream of this table.** ClinVar's ordinary dup/del mirror
pair at one position collapsed to one drafted row before enricher 0.6.3, and the survivor was chosen
by allele spelling rather than star rating — *"on `cancer` the kept row is the lower-starred one in
400 of 1,481 collapses"* (`docs/CONSUMER_SUGGESTIONS_HISTORY.md:1940-1944`, S41). Records that never
reached `variants.csv` never reach `resolution.csv` and so never reach this table. **A module drafted
before 0.6.3 has an assertion table that is complete with respect to its own variant list and
incomplete with respect to ClinVar**, and no signature says so.

## What does not exist

- **No escalation of the `clin_sig` cross-check, ever, even against an expert panel.** Asked and
  refused: *"Tempting and not taken, for the same reason. The confidence *is* surfaced
  (`ClinSigFinding.confidence`) — surface it, let the consumer route on it, do not decide for them"*
  (`docs/FAQ.md:147-150`). Do not propose it again.
- **No `submitter` column.** `GeneValidityRow` has one and keys on it, because GenCC is an aggregate
  of nineteen submitters (`schema/gene_validity.py:22-24`). ClinVar's submitter set is not projected
  here; `review_status` is the only proxy, and it counts submitters without naming them.
- **No `date_last_evaluated`, no ACMG criteria codes, no per-submitter breakdown, no conflict detail.**
  A `conflicting` call arrives as one token and one star; what conflicted is not in the table.
- **No per-condition row.** See Gotcha 8. Splitting the pipe-joined cell is the consumer's job and it
  is lossy.
- **No `describe_table`, no template, no lint route** — this is not an authored table kind, by design.
- **No refresh command.** The only way to re-ask is delete-and-re-derive, which discards curator
  overrides; that is **RM83** (`docs/ROADMAP_0_7.md:884`), and §5.1's canary is unperformable until it
  closes.
- **No `ClinicalAssertionsInfo` on the registry's module detail.** `GwasEffects` gets one (row counts,
  units, traits — `just-dna-registry/src/just_dna_registry/services/catalog.py:222-238`); this table
  gets a single boolean. See *Consumption today*.
- **The shape is not frozen.** COMPILER.md marks the `clinical_assertions.csv` path **"provisional
  shape"** (`docs/COMPILER.md:1451`), same standing as `gene_metrics.csv` and `literature.csv`.
- **`fetched_at` will be renamed** to `updated_at`/`recorded_at` at 1.0, bundled with the
  `sources.parquet` rename. **No signature moves** — it is outside all seven fact sets — only
  `artifact.digest` (`docs/ROADMAP_1_0.md:121`). Nobody authors it, so no author action is owed.

## Consumption today

**No consumer anywhere opens `clinical_assertions.parquet` or reads a `ClinicalAssertionRow` field.**
Zero hits across every consumer repo for `clin_sig_raw`, `review_status`, `off_build`,
`unrated_count`, `max_review_stars` or `CLINICAL_ASSERTION_FACT_FIELDS`. The table exists to consumers
as a name in an artifact list, a presence bit, and prose. (`/data/sources/just-dna-marketplace` is a
byte-identical checkout of `just-dna-registry`; its hits are the same lines.)

**just-dna-lite / just-dna-pipelines — the annotation consumer**
- `just-dna-pipelines/src/just_dna_pipelines/annotation/hf_modules.py:36` —
  `MODULE_TABLES = ["annotations", "studies", "weights", "sources"]`. The table universe **excludes**
  it, so `ModuleTable` (`:495-503`) has no member for it and `get_module_table_url` (`:513`) cannot
  build a URL. `annotation/hf_assets.py:174` iterates that list, so the parquet is never downloaded.
- `annotation/report_logic.py:562` scans `weights.parquet`; `:575-580` joins only annotations and
  studies; `:700-702` calls `_effective_clin_sig(row["clin_sig"], row["pathogenic"], row["benign"],
  row["clinvar"])`; `:300-321` prefers the **authored** `clin_sig` column and falls back to
  `clin_sig_from_booleans`. Rendered at `:625` as `("ClinVar interpretation", clin_sig_label)`.
  **So `clin_sig` comes from the compiled `variants.csv` and nothing else, and no star, submitter
  count or conflict flag is read anywhere in `annotation/`.**
- `v1_port/publish.py:39` — `_ALLOW_PATTERNS = [*ARTIFACT_PARQUETS, …]`, so the parquet **is uploaded
  to HF** (`:136`) and presence-checked (`:87`), never opened. `tests/test_format_0_6.py:82-90`
  asserts membership only.
- `v1_port/clinvar_panel.py:127-137`, `:461`, `:507` etc. do read `review_stars` — but against the
  **enricher's ClinVar snapshot** while drafting a panel, not against any module's table. Same for
  `variation_id` at `:299-321` (joined to the snapshot's citations to build `studies.csv`).
- Webui: zero relevant hits under `just-dna-lite/webui/src`.

**just-dna-registry**
- `db/facets.py:210` — `"has_clinical_assertions": int(manifest.clinical_assertions is not None)`.
  Column `db/schema.py:285`; filter `db/repository.py:949`/`:1019`; API query param
  `api/routers/modules.py:90`; client param `client.py:314`/`:341`.
- `services/catalog.py:171` — `clinical_assertions=manifest.clinical_assertions is not None` into
  `FactTablesInfo` (`models/api.py:232`). **A yes/no tick on the card, nothing else.**
- `specfiles.py:103` — `clinical_assertions.csv` ∈ `FACT_CSVS`, so revalidate/upgrade rebuild the spec
  dir with it. `services/upgrade.py:169`/`:471`/`:478` reads the CSV **header** to trim unknown
  columns; no cell is interpreted. `services/publish.py:522` and `revalidate.py:112` call
  `compile_module`, so the manifest block is built inside the compiler, not the registry.
- **No `min_review_stars` / `max_review_stars` / `unrated_count` / `not_found_count` / `variation_id`
  reaches a card, a facet, a filter or a detail model.** They travel only as raw bytes inside the
  `latest_manifest` passthrough (`models/api.py:306`).

**just-prs / just-prs-mcp** — zero hits, both repos.

**just-module-creator** — no read. `tools/authoring.py:661` names the file in a string telling the
model not to hand-author it; `verify_artifact` re-hashes the parquet by digest without opening it;
`tools/passes.py:253` threads `min_review_stars=2` into `draft_from_clinvar`, which filters the
**snapshot** while drafting `variants.csv`.

**Verdict: the whole point of the table is computed and then discarded one layer further out than
before.** `_clinical_assertions_block` (`compiler.py:4759-4783`) builds the signature, the counts and
the star range into the manifest; the registry reduces the block to `is not None`, the annotator
ignores it, and nothing anywhere renders a star. That is the same compute-and-discard shape RM25 was
built to end, now sitting between the compiler and its consumers.

## Blanks for just-dna-lite

- **Add `clinical_assertions` to `MODULE_TABLES` and `ModuleTable`**
  (`annotation/hf_modules.py:36`, `:495-503`). Unread today; the parquet is already published to HF by
  `v1_port/publish.py:136`, so this is a one-line list change plus a `ModuleTable` member, not a
  pipeline change. What breaks today: the annotator cannot see the table even when the module ships
  one.
- **Render review strength beside "ClinVar interpretation."** `report_logic.py:625` prints
  `"ClinVar interpretation: Pathogenic"` with no indication whether that is a 0★ single submitter or a
  3★ expert panel. `review_stars` and `review_status` are sitting in the parquet, keyed to the allele.
  What breaks today: a report presents a `no_assertion_criteria_provided` submission and a practice
  guideline identically — which is the exact defect RM25 exists to fix, still live at the last mile.
- **Resolve `clin_sig` per observed ALT, not per variant row.** `_effective_clin_sig`
  (`report_logic.py:300-321`) reads one flat authored value. On `hboc_palb2` that value is
  `pathogenic` for `rs118203998`, while the assertion table records `G>A` as
  `uncertain_significance (0★)`. Join at position level — `chrom:start:ref`, as
  `compiler.py:5776-5788` does, **not** on `variant_key`, which matched only 4 of 24 in measurement —
  then select by the ALT the sample actually carries. What breaks today: a consumer can report a
  0-star VUS as pathogenic on a locus the module was right about.
- **Surface `conflicting` as its own state rather than a `clin_sig` token.** `_clin_sig_label`
  (`report_logic.py:324`) renders it as one more tier. `hboc_palb2` carries one
  (`rs878855123 C>T`, `criteria_provided,_conflicting_classifications`, 1★) where the module's own row
  says `pathogenic`. What breaks today: a disagreement inside ClinVar is rendered as a settled call.
- **Registry: build a `ClinicalAssertionsInfo` on `ModuleDetail`.** `GwasEffectsInfo` already exists
  (`services/catalog.py:222-238`) and `models/api.py:224-227` states the intent — "the counts and
  facets live on the detail". The manifest already carries `row_count`, `variant_count`, `clin_sigs`,
  `min_review_stars`, `max_review_stars`, `unrated_count`, `not_found_count`. What breaks today: a
  catalog user can filter on *has a table* but cannot ask "modules whose clinical calls are all at
  2★ or better", which is the one query the star range was published for.
- **Do not average the stars.** The manifest publishes min and max as two counts deliberately —
  "published as the two counts rather than an average, which would be a number describing no record"
  (`schema/manifest.py:441-443`) — and `min`/`max` are `int | None` where `null` is not `0`
  (`compiler.py:4763-4767`). Any UI that coalesces null to zero reports a module's evidence as the
  weakest kind available.

## Ask the live schema

`clinical_assertions.csv` is **not an authored table kind**, so the plugin's authoring tools refuse
it. Do not work around that by writing the table by hand — ask the model itself.

```python
# the columns, their types, defaults and constraints — the current answer, always
from just_dna_format.assertions import ClinicalAssertionRow, CLINICAL_ASSERTION_FACT_FIELDS
ClinicalAssertionRow.model_fields          # names, types, defaults
ClinicalAssertionRow.model_json_schema()   # descriptions + vocabulary annotations
CLINICAL_ASSERTION_FACT_FIELDS             # exactly what the fact signature hashes

# the vocabularies it binds
from just_dna_format.vocab import VALID_CLIN_SIG, VALID_RESOLUTION_STATUS, VALID_SOURCE_LAYERS

# the star mapping, and the only copy of it
from just_dna_enricher.clinvar_build import review_stars, _REVIEW_STARS

# the manifest block a consumer reads
from just_dna_format.manifest import ClinicalAssertions
```

These MCP calls decline, because this table is not hand-authored — **ask `describe_machine_table`
instead**, which answers it:
`describe_table("clinical_assertions.csv")`, `table_requirements("clinical_assertions.csv")`,
`get_template("clinical_assertions.csv")`, `lint_rows(csv_name="clinical_assertions.csv", …)` — all
answer *"Unknown table kind … Authorable kinds: …"*. That is routing, not a refusal on principle: the
banner at the top of this file has said so since 2026-08-20 and this paragraph had not caught up.

These MCP calls **do** apply:
- `list_tables()` — confirms the authorable set this table is deliberately outside of.
- `validate_module(spec_dir)` / `compile_module(spec_dir, strict=True)` — load and hash the sidecar,
  and emit the position-orphan warning if it is over-broad.
- `verify_artifact(dir)` — re-hashes `clinical_assertions.parquet` as part of `artifact.digest`.
- `module_signature(spec_dir)` — `content_signature`, which this table is **not** in.

To produce or refresh the table there is one command, and no MCP tool wraps it:

```bash
just-dna-enricher enrich <spec_dir>            # resolution.csv first — required
just-dna-enricher assertions <spec_dir>        # default --best-effort; add --offline to pin
just-dna-enricher clinvar pull                 # provision a snapshot if the pass reports "skipped"
rm <spec_dir>/clinical_assertions.csv && just-dna-enricher assertions <spec_dir>   # the only refresh
```
