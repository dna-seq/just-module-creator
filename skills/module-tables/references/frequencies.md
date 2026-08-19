# frequencies.csv — how common is this allele, and in whose samples

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

## What it is

`frequencies.csv` answers one question per row: *in this ancestry group, in this release of this
reference database, how many copies of this one ALT were counted, out of how many called alleles.*
It exists so the compiler can hold a frequency without ever fetching one — the enricher's gnomAD
pass writes it, the compiler only reads it, materializes `frequencies.parquet` and hashes it by
facts. Its audience is twofold: a curator who wants to see whether a variant they called pathogenic
is actually common (the ACMG BA1 conversation), and a downstream consumer that wants a filtering
allele frequency without doing arithmetic or holding a 742 GB VCF. The module's own annotation
tables never join to it; the compiler only *cross-checks* against it
(`compiler.py:5477 _cross_check_frequencies`, matched at position level, not on `variant_key`).

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.frequency.FrequencyRow` (`schema/src/just_dna_format/frequency.py`) |
| Parquet | `frequencies.parquet` — in `ARTIFACT_PARQUETS` (`compiler.py:288`), so in `artifact.digest` |
| Natural / dedup key | `(variant_key, population)` — the enricher's merge key, `frequencies.py:… existing[(row.variant_key, row.population)]` |
| Authored or machine-produced | **machine-produced**, human-overridable by design. Not an `AuthoredModel`; `extra="forbid"` |
| Who writes it | `just_dna_enricher.frequencies.enrich_frequencies` — `just-dna-enricher frequencies <dir>` |
| Fact signature | `integrity.frequency_signature` over `frequency.FREQUENCY_FACT_FIELDS` (14 of 19 fields) → `manifest.frequency.signature` |
| In `content_signature`? | **No.** `_INPUT_FILES` (`compiler.py:267`) is `module_spec.yaml`, `variants.csv`, `studies.csv` and the table kinds — nothing else |
| In `artifact.digest`? | **Yes**, via its parquet. Also byte-hashed into `manifest.derived[]` (transport only, `compiler.py:346`) |
| Location | root or `derived/frequencies.csv` (`layout.DERIVED_SUBDIR`); one spelling only. Both places at once = `layout.SidecarCollision`, an error, never a merge |

## Who populates what

- **enricher pass** — *everything*. `enrich_frequencies` (pass 2, `just-dna-enricher frequencies <dir>`,
  or our `enrich_facts(passes=["frequencies"])`) fills `variant_key`, `rsid`, `chrom`, `start`,
  `ref`, `alt`, `genome_build`, `population`, `allele_count`, `allele_number`, `homozygote_count`,
  `hemizygote_count`, `faf95`, `dataset`, `vrs_id`, `caid`, `source`, `status`, `fetched_at`. It reads
  `resolution.csv`, **not** `variants.csv` — the resolution table is where an rsID has already become
  `chrom-pos-ref-alt`, which is the key gnomAD wants, and it sidesteps the multi-allelic-rsID problem
  the resolver already solved.
- **author** — no column is *expected* of a human, and every column *may* be written by one. The
  design is explicit that this is intended, not tolerated: "a curator editing `frequencies.csv` is
  doing the intended thing" (SCHEMAS.md:1381), and the fact hash drops `None` and ignores row order
  precisely so a hand-filled table with the same numbers hashes equal to a gnomAD-filled one
  (`integrity.fact_signature`). The honest way to record a hand-added row is `source` = something
  other than `gnomad` — the column's own description is "gnomad|manual|reversed (open)".
- **drafter** — none. No `clinvar_draft` / `pgx_draft` / `clinpgx_draft` touches this table, and
  there is no `<<REPLACE>>` stub for it.
- **compiler-stamped** — nothing in the CSV. The compiler *adds two columns on the way to parquet*
  and neither is a stamped CSV column: `module` (the module name) and `allele_frequency` = AC/AN as a
  real `Float64` (`compiler.py:5377 _build_frequencies`). `allele_frequency` is a **property on the
  model, not a field**, so writing it into the CSV is refused by `extra="forbid"` — see Gotchas.
- **registry-stamped** — nothing. `normalize.IDENTITY_AUTHORITY_KEYS` is `{namespace, owner,
  canonical_id}` and lives on the manifest identity, not on any sidecar row.
- **nobody, ever** — no permanently-unwritten column. `hemizygote_count` is the closest: it is only
  ever non-zero on X/Y outside the PAR and on MT, so on an autosomal panel it is a column of zeros.

**Cells no tool may fill even though it could.** `hints.REDUNDANCY_BEARING` and
`hints.ATTESTATION_BEARING` do not reach this table in the way they reach an authored one. Measured
against format 0.6.1: `set(FrequencyRow.model_fields) & set(hints.REDUNDANCY_BEARING)` =
`{rsid, chrom, start, ref}`, and the attestation intersection is **empty** — this table has no
`provenance_quote` / `provenance_regex`, so no attestation-bearing cell exists here at all. The
refusal that matters runs the *other* direction: **never fill `variants.csv`'s `chrom`/`start`/`ref`
/`rsid` from a row of `frequencies.csv`.** Those are the redundancy-bearing columns, the frequency
sidecar carries gnomAD's own spelling of them, and `_cross_check_frequencies` compares the two — copy
one across and the check compares gnomAD against gnomAD and agrees perfectly. Likewise never author
a `clin_sig` after reading this table: `_check_ba1_lint` exists to make the tension between a
`pathogenic` call and a common allele visible, and adjusting the call to silence the warning deletes
the finding rather than answering it.

## What moving this table moves

Measured, not asserted. `reference_examples/hboc_palb2` (144 frequency rows, 24 alleles) compiled
into a scratch tree with `compile_module(resolve_with_ensembl=True, ensembl_cache=None)`, once per
row of this table, comparing `artifact.digest`, `content_signature`, `manifest.frequency.signature`
and `manifest.verification.module_hash`. Baseline, compiled twice: **byte-identical** (digest
`6876cc79…`, content `43ad8ac1…`, freq signature `3095ee67…`, module_hash `527abadc…`).

| An edit here | `content_signature` | `frequency.signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add or delete a row | unmoved | **moves** | **moves** | unmoved — still closed |
| edit a fact cell (`allele_count` 13→14) | unmoved (`43ad8ac1…`) | **moves** (`3095ee67…`→`596a1e54…`) | **moves** (`→59dad222…`) | unmoved (`527abadc…`) |
| edit a provenance-only cell (`fetched_at`, `source`, `status`) | unmoved | **unmoved** | **moves** (`→11847a0e…`) | unmoved |
| reorder rows | unmoved | **unmoved** (order-independent hash) | **moves** (`→104e0439…`) | unmoved |
| re-run the producing pass | unmoved | moves only if a *fact* changed | moves if any byte changed | unmoved |
| delete the file and re-derive | unmoved | **the whole `frequency` block disappears** while deleted (`→eb2bf102…`) | **moves** | unmoved |
| recompile under a newer toolchain | unmoved | unmoved | may move (polars / compiler version) | unmoved |

1. **Inside `content_signature`? No.** `content_signature` covers the authored rows only —
   `_INPUT_FILES` is `module_spec.yaml`, `variants.csv`, `studies.csv` and the ten table kinds. This
   table's identity is its **fact** hash, `frequency_signature(rows)` over `FREQUENCY_FACT_FIELDS`:
   `variant_key`, `rsid`, `chrom`, `start`, `ref`, `alt`, `population`, `allele_count`,
   `allele_number`, `homozygote_count`, `hemizygote_count`, `faf95`, `dataset`, `genome_build`.
   Left out: `source`, `status`, `fetched_at` (provenance — so a human-filled and a gnomAD-filled
   table with the same numbers hash equal) and `vrs_id`, `caid` (cross-references to the allele the
   coordinate already names, not independent measurements). `dataset` is deliberately **inside**: a
   v4.1 count and a v2.1.1 count are different facts about the world, so a release swap must hash
   differently.
2. **Inside `artifact.digest`? Yes** — `frequencies.parquet` is in `ARTIFACT_PARQUETS`. So a
   provenance-only column no signature sees still moves the digest, because the parquet bytes differ:
   measured above with a single `fetched_at` edit. Row **order** does the same, which is the one that
   surprises people — the fact hash sorts rows, the parquet does not.
3. **Does an edit here un-close the module? No.** The attestation binds the authored bytes only
   (`compiler.authored_input_entries`, `compiler.py:361`, newline-normalized since RM82). Measured:
   `manifest.verification.module_hash` stayed `527abadc…` across a fact edit, a `fetched_at` edit, a
   reorder and outright deletion of the file. So a re-enrichment leaves a closed module closed. (An
   `authorship:` append, by contrast, un-closes a module while moving no identity at all — different
   file, different rule.)
4. **Part of the canary? Yes, and it is one of six tables that can produce the reading.**
   MODULE_LIFECYCLE.md § 5.1: content unmoved + fact signature **moved** = nobody authored anything
   and gnomAD said something different this time. Watch `manifest.frequency.signature`. Two caveats:
   detecting it requires **delete-and-re-derive**, because merge-not-clobber never re-asks an allele
   already recorded; and this table sits in row 2 of that decision tree more often than any sibling
   — a `fetched_at`-only or reorder-only change moves the digest with both signatures unmoved.

## Required to exist

Nothing requires `frequencies.csv`. Its `manifest.frequency` block is simply absent on a module that
carries none (`compiler.py:4704 _frequency_block` returns `None` on an empty row list), and the
registry projects `has_frequencies = 0` for that, honestly rather than as "unknown".

What it **needs**, and what it **drags in**:

- **`resolution.csv` must exist and must parse**, or the pass raises `FrequencyEnrichmentError`
  ("the frequency pass reads resolved coordinates, so run `just-dna-enricher enrich` first").
- **`licensing.csv` gains a row.** The pass calls `record_source_terms({sources}, "frequency", …)`, so
  a gnomAD run writes `gnomad,frequency,CC0-1.0,…` (see `hboc_palb2/licensing.csv:6`). The reverse
  also bites: a `licensing.csv` declaring the `frequency` layer on a module with **no**
  `frequencies.csv` warns as a stale declaration, and that narrowing is deliberate — the table is
  machine-written *with* a `source` column, so the declaration really is stale.
- **A GRCh38 module.** `_alleles_from_resolution` skips any resolution row whose `genome_build` is not
  `gnomad.FREQUENCY_GENOME_BUILD` and logs one counted warning naming the build. gnomAD v4's variant
  id (`chrom-pos-ref-alt`) carries no assembly, so a GRCh37 coordinate is a well-formed request that
  returns whatever GRCh38 variant sits at that number — a wrong-variant fact rather than an error.
  A GRCh37 module (`reference_examples/cyp2c9_warfarin_grch37`) therefore gets no frequencies at all.

  > 🚧 **ROADWORKS — a GRCh37 module gets zero frequencies, and the skip barely surfaces.**
  > **Current state.** The skip is correct — a GRCh37 coordinate sent to gnomAD v4 would return a
  > *different variant's* frequency — but the only trace is one counted log line. There is no
  > `off_build` field on the result a caller can read, and the compiled module looks exactly like one
  > for which gnomAD simply had nothing. (The clinical-assertions pass does expose `off_build`; this
  > one does not.)
  > **Expected state.** The skip reported as a first-class outcome, the way *nobody-asked* is
  > distinguished from *asked-and-absent* everywhere else in this format. It is not.
  > **Guard.** On a non-GRCh38 module, do not run this pass expecting rows, and do not read an empty
  > `frequencies.csv` as "gnomAD has nothing". Either lift the module to GRCh38 first, or state in
  > the README that frequencies were never queried — no artifact field records it.

## The columns that carry judgement

- **`variant_key`** — **authored and required** here rather than compiler-managed. (Not the only
  place: measured, `is_required()` is `True` on `ResolutionRow`, `FrequencyRow`, `GwasEffectRow` and
  `ClinicalAssertionRow` — four of the derived sidecars, two of them with an explicit non-empty
  validator on top. The coordinate-first minting rule below is what is special about this one.) It is coordinate-derived (`base.derive_variant_key(None, chrom, start,
  ref, alt, build=…)`), never rsID-derived, because a one-to-many rsID is re-keyed to distinct
  coordinate keys when the compiler expands it and an rsID-keyed row would fail to line up.
- **`alt`** — **one** allele, singular, unlike `resolution.csv`'s comma-joined `alts`. A frequency is
  per-allele, so a multi-allelic site is several rows. Hand-writing `A,G` here is not a shortcut, it
  is a different (wrong) fact.
- **`population`** — an **open, seeded** vocabulary (`vocab.RECOMMENDED_ANCESTRY_GROUPS`, 11 members
  as of format 0.6.1). `validate_population` enforces only that the label is a non-empty lowercase
  `[a-z0-9_]+` token; an unfamiliar label is kept, because TOPMed / ALFA / 1000G name their groups
  differently and a closed set would turn a source swap into a schema change. What makes a label
  interpretable is the row's `dataset`, not membership. **Never merge this with
  `pgs.VALID_TRAINING_ANCESTRY`** — those are 1000G superpopulations describing which cohort a *score*
  was trained on, a different axis that happens to share three letters.
- **`dataset`** — a **fact, not provenance**, and inside the fact hash. `gnomad_v4.1_joint` is what the
  pass stamps (`gnomad.FREQUENCY_DATASET_LABEL`); `--dataset` overrides the label without changing
  what was queried, so overriding it is a way to record a lie.
- **`status`** — three-valued and every member load-bearing: `resolved` (the source served counts),
  `not_found` (asked, absent — a **fact** about a locus the source *does* cover), `not_covered` (the
  locus is outside the callset, so no answer exists and none can be inferred). Not `unchecked`, which
  is this codebase's word for a question never put.
- **`faf95`** — the filtering allele frequency, 95% CI lower bound, and the number an ACMG BA1/BS1
  filter actually uses. The source reports **one** faf95 with a named owning group, so it lands on
  that group's row and is null everywhere else. A null `faf95` on ten of eleven rows is correct, not
  missing data.
- **`allele_number`** — the denominator, and `0` is a real answer meaning *this group has no coverage
  here*. See the next section.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **`allele_frequency` is in the parquet and must never be in the CSV.** It is a `@property` on
   `FrequencyRow`, not a field, and the model closes its namespace with `extra="forbid"`. Measured:
   adding an `allele_frequency` column to `hboc_palb2/frequencies.csv` produced **144 validation
   errors — one per row** (`frequencies.csv line 2 [allele_frequency]: Extra inputs are not
   permitted`). The reason it is derived rather than stored: integers round-trip through CSV exactly,
   while a stored float invites `0.0482` vs `0.048200000000000004` formatting drift, a Principle 7
   idempotency hazard. `reverse_module` relies on the same asymmetry — it drops any parquet column the
   model does not declare, so the round trip is lossless by construction.
2. **`AN = 0` yields `allele_frequency = None`, not `0.0`.** `if self.allele_count is None or not
   self.allele_number: return None`. No coverage means *no information*, not "frequency zero", and a
   consumer that coalesces the null to zero converts an unknown into a confident absence. Same rule
   one level up: `not_covered` is an unknown, and the pass logs it as "This is an unknown, not a
   zero."
3. **The arithmetic checks are ERRORS in both modes, and `validate` catches them now too.** Measured
   on a doctored row (`allele_count 1613661` vs `allele_number 1613660`): `validate_spec` returns
   `valid=False` **and** `compile_module` returns `success=False`, with no `--strict` anywhere. Two
   integer relations refuse: `allele_count > allele_number`, and `2 × homozygote_count >
   allele_count`. Exact arithmetic, so there is no tolerance argument to have and a violation is
   corruption. The parity was a real gap — `_check_frequency_arithmetic` was compile-only, so a plain
   `validate` reported `valid` on a module a plain `compile` refused (RM93, `@parity-by-check`).
4. **Merge-not-clobber, so a re-run refreshes nothing.** Existing rows are authoritative and keyed on
   `(variant_key, population)`; the pass only fetches alleles no existing row covers. To pick up a
   newer gnomAD you must **delete the file first**. MODULE_LIFECYCLE.md:413 rates the cost of deleting
   this particular sidecar as "nothing hand-written normally" — the lowest of the seven — which is why
   it is the safest of the family to delete and re-derive. It is also the only way to make the canary
   reading of § 5.1 available at all.
5. **`not_covered` sits outside the `strict` gate, on purpose.** `strict` refuses on
   `result.missing` (`not_found`) and never on `result.uncovered`. A locus outside gnomAD's callset is
   perfectly reproducible — it will be outside it on every run — so refusing "would make a
   pseudoautosomal module uncompilable under `strict` for a reason no authored edit could fix". The
   motivating case is real and probed live 2026-08-04: gnomAD hard-masks the **Y** PAR (X PAR1
   640000-641500 serves 880 variants, the identical interval on Y serves none), so a Y-PAR row used to
   be written as `not_found` — ten absences nobody had established. See
   `reference_examples/shox_par1/README.md:95` and `par_boundary/README.md:50`.
6. **Online only, permanently.** v4.1's sites VCFs are 58 GB (exomes) / 742 GB (genomes), so there is
   no slice to ship and there will not be one (FAQ.md:251, answered *no*). `--offline` makes the pass
   a **no-op with a warning**, keeps any existing file as the pin, and returns `skipped_offline=True`
   with `missing` holding every allele no existing row pins. That last field is a trap by itself:
   surfaced verbatim it says gnomAD was asked about 57 alleles and had none of them, having asked
   about nothing — `unchecked` reported as `not_found`. The registry's own wrapper had to add a
   warning distinguishing the two (`just-dna-registry/src/just_dna_registry/services/enrich.py:1074`,
   "a coverage gap, not an absence from gnomAD").
7. **`strict` here means "every resolved allele has a frequency", which is often the wrong thing to
   want.** gnomAD genuinely lacks rare and private alleles. Measured on `hboc_palb2`: 24 alleles, **12
   resolved (11 group rows each = 132) and 12 `not_found` (one `global` row each)** — exactly half the
   panel. `mode="strict"` would refuse that module, and the panel is correct. The pass's own error
   message says so: "this is often correct data rather than a fetch failure".
8. **BA1 fires in `compile` and not in `validate`.** Measured: raising the `nfe` `faf95` on a
   `likely_pathogenic` PALB2 allele to `0.06` produced the BA1 warning under `compile_module` and
   **not** under `validate_spec`. Warning only, in both modes, threshold overridable
   (`--ba1-threshold`, registry default `0.05` at `config.py:93`) — the 5% default is ACMG's, not a
   constant of nature, and a common recessive carrier allele legitimately sits above it. `faf95` wins
   over a raw AF regardless of magnitude; otherwise the maximum per-group `allele_frequency`.
9. **Rate limiting shapes the pass, so budget time.** gnomAD allows 10 requests / IP / 60 s. The
   client batches **20** GraphQL aliases per POST behind a **6.0 s** pacing gate — probed: 20 and 25
   worked, 29 returned HTTP 400 — which is ~200 variants/minute. A genome-wide panel is hours. Our
   `enrich_facts` is a background task for exactly this reason.
10. **`FrequencyUnavailable` is a *subclass* of `FrequencyEnrichmentError`, so the narrow arm must come
    first.** Since enricher 0.6.2 / RM101 the outage case has its own type; a parent-first `except`
    ordering makes the outage arm dead code, silently, raising nothing. See
    `services/enrich.py:1030` for the correct ordering and the history it replaces (a 502 used to
    answer `/check` with a 500). Before RM101 a `GnomadError` travelled straight out through a
    `try/finally` with no `except` at all.
11. **A first row wins on gnomAD's duplicates, and sex splits are dropped.** The payload, probed on
    `11-5227002-T-A`, carries sex-stratified ids (`nfe_XX`, `XY`) beside ancestry groups, lists
    `XX`/`XY` **twice**, and names the whole-dataset row with a bare empty id. `_populations_from_joint`
    drops the sex splits (sex is a second axis, not a `population` label), keeps the first of a
    duplicate pair, and maps the bare id to `global`. Server order is discarded; emission order is
    `(variant_key, alt, population_sort_key(population))` with `global` first.
12. **The frequency-arithmetic warning is emitted twice.** See *What does not exist* — an upstream
    defect, measured.

## What does not exist

- **No offline snapshot, ever.** Refused with a reason (FAQ.md:251). Not a reproducibility hole:
  `frequencies.csv` *is* the pin once written, and every later compile reads it offline and
  deterministically. Do not propose a slice.
- **No `af` column from the source.** gnomAD's `VariantPopulation` deliberately exposes `ac`/`an` and
  **no `af`** — the frequency is ours to compute, which is why the split above exists at all.
- **No sex axis.** `nfe_XX` is not a `population` value and never will be; folding it in would be the
  `state`-overloading mistake 0.3 unwound. There is no column for it, so a module that needs
  sex-stratified counts cannot express them here.
- **No `ambiguous` status.** Deliberately absent: a frequency row names one allele in one population,
  so there is nothing for a source to be ambiguous between.
- **No second `faf95` column and no `faf95_population`.** One value with a named owning group lands on
  that group's row. A reader wanting "which group owns the faf95" reads the row it is on.
- **No `describe_table("frequencies.csv")`.** This is the gap that matters most for an authoring
  agent. `hints.describe_table` raises `DraftError: 'frequencies.csv' is not an authored table of
  this format`, and so do `table_requirements`, `get_template` and `lint_rows`, all of which gate on
  `draft.DRAFTABLE`. `licensing.csv` / `sources.csv` **is** in `DRAFTABLE`; the other six fact
  sidecars are not. So there is no live-schema tool for this table — see *Ask the live schema* for
  what to do instead.
- **No cross-check against the module's `AF`.** `variants.csv` has no allele-frequency column and the
  compiler compares nothing between the two; the only linkage is the position-level orphan warning
  and the BA1 lint.
- **Genuine upstream defect: the `faf95` warning is duplicated in `manifest.compilation.warnings`.**
  `compile_module` runs `validate_spec`, which since RM93 runs `_check_frequency_arithmetic` — and the
  compile-side `_frequency_checks` (`compiler.py:4412`) runs it again with no dedup. `_literature_checks`
  three lines below it *does* dedup, with a comment naming exactly this hazard ("a finding living in
  both places would otherwise print twice"). Measured on a doctored `hboc_palb2`: **15 warnings, 14
  distinct**, the `faf95 … exceeds the group's own allele frequency` line appearing twice. The
  integer *errors* are not duplicated (compile aborts first). `manifest.compilation.warnings` is a
  published field (RM44), so the duplicate is published.

  > 🚧 **ROADWORKS — the `faf95` warning is published twice.**
  > **Current state.** Independently confirmed on a clean run: `_check_frequency_arithmetic` runs on
  > both the validate and the compile side, and only the literature checks three lines away carry the
  > dedup filter — with a comment naming this exact hazard. The duplicate reaches
  > `manifest.compilation.warnings`, a published field.
  > **Expected state.** One `if w not in all_warnings` filter, matching the literature checks. The
  > same defect shape has already shipped a fix once elsewhere in the compiler, so the pattern is
  > settled; this site was missed.
  > **Guard.** If you count warnings — in CI, in a report, in a dashboard — **deduplicate on the
  > message string first**. A module with one arithmetic problem publishes two warnings, and a
  > consumer reading the count will overstate what is wrong.

## Consumption today

**The annotation consumer does not read this table at all.** That is the finding.

| Where | What it does |
|---|---|
| `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/module_compiler/cli.py:327-330,407` | passes `--ba1-threshold` through to the compiler at **authoring** time. The only frequency-aware line in the consumer, and it never reads a frequency |
| `just-dna-lite/webui/src/webui/state.py:5985-6007` | imports `ARTIFACT_PARQUETS` so the client-side digest covers `frequencies.parquet` **as bytes**. Identity only; nothing reads a column |
| `just-dna-lite/…/annotation/hf_modules.py:206-241`, `module_config.py:490-503` | module discovery and download build URLs for the lead table + `annotations` / `studies` / `sources` parquets. `ModuleInfo` (`hf_modules.py:39-64`) has **no `frequencies_url`**, so a module installed from HuggingFace may not carry the file locally at all |
| `just-dna-registry/src/just_dna_registry/specfiles.py:97-105` | `FACT_CSVS` — what `revalidate` and `upgrade` rebuild a spec directory from. Missing here = silently dropped on re-publish |
| `…/services/upgrade.py:165` | maps `frequencies.csv` → `FrequencyRow` to find and trim columns a newer model rejects (lossy) |
| `…/services/enrich.py:1006-1080` | `/check` preflight: runs the pass with `write=False`, reports `covered` / `missing` / `uncovered` / `unreachable` / `skipped_offline` as four distinct answers |
| `…/api/routers/publish.py:440`, `client.py:626-670`, `client_cli.py:447` | the `--frequencies` opt-in on `/check`. **Publish never runs the frequency pass** (`config.py:183-184`) |
| `…/db/facets.py:212`, `db/schema.py:288`, `db/repository.py:951,1021`, `api/routers/modules.py:101-133`, `client.py:316,343` | one boolean, `has_frequencies = int(manifest.frequency is not None)`, filterable in catalog search |
| `…/services/catalog.py:173` | the module card's `FactTablesInfo.frequencies` — the same boolean, read from the manifest rather than the column, so card and filter cannot disagree |
| `just-prs`, `just-prs-mcp` | **nothing.** No match for `frequencies`, `allele_frequency` or `gnomad` anywhere in either `src/` |

So: the registry knows *whether* a module has frequencies and can check them at preflight; nobody
reads a single AC, AN, `faf95` or `dataset` value downstream of publication.

## Blanks for just-dna-lite

- **Nothing reads `faf95`, so the ACMG BA1/BS1 filter the column exists for does not run on a user's
  VCF.** The compiler runs BA1 once, at authoring time, against `clin_sig` — and warns, correctly,
  that the threshold is disease-specific. A consumer could annotate each reported variant with its
  strongest available frequency and the group it came from, and let a report say "this pathogenic call
  sits at faf95 0.06 in nfe". Today the number ships inside `frequencies.parquet` and no report ever
  mentions it. Ask: add a frequency read to the annotation join, keyed at position level exactly as
  `compiler._cross_check_frequencies` does (`chrom:start:ref`, not `variant_key`), and prefer `faf95`
  over `max(allele_frequency)` because that is the statistic the rule uses.
- **Nothing reads `dataset`, so a consumer cannot say which gnomAD release it filtered against.**
  `manifest.Frequency.datasets` exists for precisely this and says so in its own field description:
  "A consumer reproducing an ACMG BA1/BS1 filter needs this to know it is filtering against the
  frequencies the curator saw." No reader exists. What breaks today: two modules in one report may
  carry `gnomad_v4.1_joint` and something else, and the report renders both as "the frequency" with no
  way to tell. Ask: surface `manifest.frequency.datasets` (and `populations`) on the module card and in
  the annotated output, before anything reads a count.
- **`frequencies.parquet` is not in the discovery/download surface, so a consumer cannot read it even
  if it wanted to.** `ModuleInfo` carries `lead_url`, `weights_url`, `annotations_url`, `studies_url`,
  `sources_url` — and no frequency URL; `get_module_table_url` falls through to a bare
  `f"{info.path}/{table_name}.parquet"` guess for anything else, which is exactly the probe-instead-of-
  attest path `_attested_files` was written to end. Ask: add `frequencies_url` (and the other five
  fact sidecars) to `ModuleInfo`, gated on `manifest.artifact.files` like the rest.
- **The three-valued `status` has no consumer, so `not_covered` is currently a distinction the format
  maintains for nobody.** A report that says "no gnomAD frequency" for a Y-PAR variant is making the
  exact false-absence claim the vocabulary member was added to prevent. Ask: whatever reads a
  frequency must branch on `status` and render `not_covered` as *unknown*, never as absent or as zero.
- **`AN = 0` will be read as zero by the first naive consumer.** The parquet's `allele_frequency` is
  `null` in that case, and a `fill_null(0)` anywhere in a polars pipeline converts "no coverage" into
  "absent from the population". Ask: pin this with a test on the consumer side before the first read
  site lands, not after.

## Ask the live schema

`describe_table` / `table_requirements` / `get_template` / `lint_rows` **all refuse this table** —
they gate on `draft.DRAFTABLE`, which holds the authored kinds plus `licensing.csv` / `sources.csv`
only. Verified against format 0.6.1 / compiler 0.6.1: `hints.describe_table("frequencies.csv")`
raises `DraftError: 'frequencies.csv' is not an authored table of this format`. Until that changes,
read the live model directly:

```bash
uv run python -c "
from just_dna_format.frequency import FrequencyRow, FREQUENCY_FACT_FIELDS
from just_dna_format.vocab import (
    VALID_FREQUENCY_STATUS, RECOMMENDED_ANCESTRY_GROUPS, POPULATION_ORDER,
)
for n, f in FrequencyRow.model_fields.items():
    print(f'{n:20} {f.annotation!s:22} required={f.is_required()}  {f.description}')
print('fact fields   :', FREQUENCY_FACT_FIELDS)
print('status vocab  :', sorted(VALID_FREQUENCY_STATUS))
print('groups (seed) :', sorted(RECOMMENDED_ANCESTRY_GROUPS))
print('emission order:', POPULATION_ORDER)
"
```

Related live sources of truth, none of which should be restated from memory:

- `just_dna_enricher.gnomad.FREQUENCY_DATASET_LABEL` / `FREQUENCY_GENOME_BUILD` — the release label
  stamped on every row, and the one assembly the pass will query.
- `just_dna_enricher.gnomad.covers_locus(chrom, start, build=…)` — three-valued; `None` means
  "cannot say" for a build whose PAR geometry is unknown.
- `just_dna_compiler.compiler.ARTIFACT_PARQUETS` — whether `frequencies.parquet` is still in
  `artifact.digest`, and in what position (position is load-bearing).
- `just_dna_format.integrity.frequency_signature(rows)` — recompute the fact hash yourself and
  compare against `manifest.frequency.signature` to read the canary.
- `just_dna_format.layout.sidecar_write_path(spec_dir, "frequencies.csv")` — write to the file you
  read; never join the name onto `spec_dir` by hand.

Verified with: format 0.6.1, compiler 0.6.1, enricher 0.6.4, registry 0.18.2
(`importlib.metadata.version`, 2026-08-19). Every measurement in this file was taken against
`reference_examples/hboc_palb2` compiled in a scratch tree; nothing was inferred from a changelog.
