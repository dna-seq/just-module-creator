# gwas_effects.csv — what a study actually measured, and on what scale, beside the weight nobody may fill from it

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

`gwas_effects.csv` answers one question per row: *for this one published association, what magnitude
did the study report, what unit is that magnitude in, which allele is it relative to, and which paper
said so.* One row is **one published association**, not one variant — rs1800562 alone carries 186 of
them. It exists because a consumer asked for the opposite thing and was refused: fill an empty
`weight` from a GWAS effect (S36). That refusal shaped the design: the effect lands in its own table
beside the authored column and a consumer picks **one wholesale**, never blends row by row
(`schema/src/just_dna_format/gwas.py:8-19`). Its audience is a curator deciding whether their
authored `weight` is defensible, and a downstream reader who wants published magnitudes per trait.
No annotation table joins to it; the compiler only cross-checks it (`compiler.py:5795`).

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.gwas.GwasEffectRow` (`schema/src/just_dna_format/gwas.py:84`) |
| Parquet | `gwas_effects.parquet` — in `ARTIFACT_PARQUETS` (`compiler.py:298`), so in `artifact.digest`. Position in that tuple is load-bearing (it *is* digest order) |
| Natural / dedup key | **the enricher's merge key only** — `association_id` alone (`gwas.py:_merge_key`). There is no compiler-side duplicate-row key for this table: it has no `_TABLE_DUPE_KEYS` entry, so a duplicated `association_id` compiles green. Per record, **not** per variant: a coarse per-rsID skip pins a module to whatever the Catalog held the first time |
| Authored or machine-produced | **machine-produced**, human-writable. Not an `AuthoredModel`; `extra="forbid"` |
| Who writes it | `just_dna_enricher.gwas.enrich_gwas` — via our `enrich_gwas_effects` (extended tier), or `just-dna-enricher gwas <spec-dir>` |
| Fact signature | `integrity.gwas_effect_signature` over `gwas.GWAS_FACT_FIELDS` (18 of 22 fields, `gwas.py:62`) → `manifest.gwas_effects.signature` |
| In `content_signature`? | **No.** `_INPUT_FILES` (`compiler.py:267`) is `module_spec.yaml`, `variants.csv`, `studies.csv` and the authored table kinds — this is a `_FACT_TABLES` member (`compiler.py:330`) |
| In `artifact.digest`? | **Yes**, via its parquet. Also byte-hashed into `manifest.derived[]` — transport only (`compiler.py:353`) |
| Location | root or `derived/gwas_effects.csv`. One spelling only; the `licensing.csv`/`sources.csv` two-name rule does **not** apply here |

## Who populates what

- **enricher pass — every column.** `enrich_gwas` (`just-dna-enricher gwas <dir>`, also reachable as
  `just-dna-pipelines enrich gwas <dir>`, `just-dna-lite/just-dna-pipelines/.../cli.py:40`) fills all
  22. Subjects come from `variants.csv` — `(rsid, variant_key)` for **every row that has an rsID**,
  `gwas.py:_module_subjects`. A coordinate-only variant row has no subject and is silently absent
  from the table; on `hfe_hemochromatosis` that is 2 of its 13 variant rows.
- **author — permitted, and the model says so.** `source` is documented
  `gwas_catalog|manual|reversed (open)`, and the fact hash ignores `source`/`status`/`fetched_at`, so
  a hand-transcribed row hashes equal to a Catalog-fetched one carrying the same facts. **Measured:**
  a hand-written file replacing the real one (columns `association_id,variant_key,rsid,effect_size,
  effect_measure,effect_unit,dataset,source=manual,status=resolved` — the *model's* minimum is the
  three `association_id`, `variant_key`, `dataset`, each with a non-empty validator)
  **validates and compiles clean**, and `content_signature` did not move (`44ad4449…` both ways). The
  honest way to add a row you read out of a paper yourself is `source: manual`.
- **drafter — none.** No `clinvar_draft` / `pgx_draft` / `clinpgx_draft` touches this table and there
  is no `<<REPLACE>>` stub for it. It is not in `draft.DRAFTABLE`.
- **compiler-stamped — one column, parquet-only.** `_build_table(rows, GwasEffectRow, module_name)`
  adds `module`; the parquet has 23 columns to the model's 22 (measured with polars). It is not a CSV
  column and `extra="forbid"` refuses it there.
- **registry-stamped — nothing.** `normalize.IDENTITY_AUTHORITY_KEYS` is
  `{namespace, owner, canonical_id}` and lives on the manifest identity, not on any sidecar row.
- **nobody, ever — no such column**, but three are permanently empty on a `not_found` row by
  construction: such a row carries only `association_id` (`<rsid>:not_found`), `variant_key`, `rsid`,
  `dataset`, `source`, `status`, `fetched_at`.

**Cells no tool may fill, and the direction the rule runs here.** Verified against format 0.6.1:
`set(GwasEffectRow.model_fields) & hints.REDUNDANCY_BEARING` = `{rsid, pmid, p_value_num}`, and the
`hints.ATTESTATION_BEARING` intersection is **empty** — this table has no `provenance_quote` /
`provenance_regex`, so no attestation-bearing cell exists here at all. On this table the redundancy
rule **inverts**: the Catalog's rsID, PMID and p-value *are the subject of the row*, so the pass
writing them is not a check filling its own answer. The refusal that matters runs outward:

- **Never copy `effect_size` into `variants.csv.weight` or `studies.csv.effect_size`.** Barred twice —
  MODULE_LIFECYCLE § Stage 3 names `weight`/`direction`/`effect_size` among the cells no tool fills,
  and every check in the tier reports rather than repairs. A null `weight` means *the author has not
  modelled this*, not *nobody has computed this yet*.
- **Never copy `pmid` into `studies.csv` and call it evidence.** The PMID here arrived from a `_links`
  follow, so nobody has read that paper yet — go and read it. Since `RM15` (2026-08-20) you may quote
  a passage from a fulltext you fetched; what you may not do is move an id across and let the row
  imply an evidence review that never happened. Read the article, quote the passage that supports
  **this row's** claim, and never the title.
- **Never copy `effect_direction` into `VariantRow.direction`.** Different axis; see Gotchas.

## What moving this table moves

Measured, not asserted. `reference_examples/hfe_hemochromatosis` (195 rows) copied into a scratch
tree and compiled once per row of this table with `just-dna-compiler compile`, comparing
`artifact.digest`, `content_signature`, `manifest.gwas_effects.signature` and
`manifest.verification` closure. Control: the untouched module compiled **twice** gives a
byte-identical digest (`sha256:6c6e103d…`), so every "MOVED" below is the edit and not noise.

| An edit here | `content_signature` | `gwas_effects.signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row (`…-probe`, 195→196) | unmoved | **moves** | **moves** | unmoved — still closed |
| delete a row (195→194) | unmoved | **moves** | **moves** | unmoved |
| edit a fact cell (`effect_unit` `s.d.`→`SD`) | unmoved (`44ad4449…`) | **moves** | **moves** | unmoved |
| edit a provenance-only cell (`fetched_at`, `source`) | unmoved | **unmoved** | **moves** | unmoved |
| edit the `trait` label (free prose) | unmoved | **unmoved** | **moves** | unmoved |
| reorder rows (reversed) | unmoved | **unmoved** (order-independent hash) | **moves** | unmoved |
| re-run the pass | unmoved | moves only if a *fact* was added | moves if any byte changed | unmoved |
| delete the file and re-derive | unmoved | the whole `gwas_effects` block **disappears** while deleted | **moves** | unmoved |
| recompile under a newer toolchain | unmoved | unmoved | may move (polars / compiler version) | unmoved |

1. **Inside `content_signature`? No.** `content_signature` covers the authored rows only. This
   table's identity is its fact hash over `GWAS_FACT_FIELDS` — 18 fields. Left **out**: `source`,
   `status`, `fetched_at` (provenance, so hand-filled and Catalog-filled hash equal) and **`trait`**,
   because the Catalog re-words a reported trait between releases for an unchanged ontology term. In,
   and each for a stated reason: `effect_unit` (a magnitude in `umol/l` and the same magnitude in
   `unit` are different facts); `trait_efo_id` (the label churns, the id is the fact); `dataset` (a
   re-curated effect size is a different fact); and **`rsid`, which inverts
   `CLINICAL_ASSERTION_FACT_FIELDS`** — there the archive returns no rsID so the column comes from
   the module's own `resolution.csv`, here the Catalog is *queried by* it and echoes it back inside
   `riskAlleleName`, so it is part of what the source said (`integrity.py:348-364`).
2. **Inside `artifact.digest`? Yes.** So a provenance-only cell no signature sees still moves the
   digest, because the parquet bytes differ — measured with a single `fetched_at` edit. **Row order
   does too**, and that is the one that surprises people: the fact hash sorts, the parquet does not
   (measured — reversing the CSV moved the digest and left the signature identical). The pass emits
   in a deterministic order (`_sort_key`: `variant_key, trait_efo_id, study_accession,
   association_id`), so leave the ordering it wrote alone; re-sorting by hand costs a digest for
   nothing.
3. **Does an edit here un-close the module? No.** The attestation binds the **authored** bytes only
   (`compiler.authored_input_entries`, `compiler.py:361`, newline-normalized since RM82) and this
   file is not among them. Measured: the closure survived a fact edit, a `fetched_at` edit, a
   reorder, a row deletion and outright deletion of the file. So a re-enrichment leaves a closed
   module closed. The counterweight: `hfe_hemochromatosis` **was** re-closed when this table landed,
   because its `weighting:` block lives in `module_spec.yaml`, whose bytes the binding does cover.
4. **Part of the canary? Yes — and MODULE_LIFECYCLE § 5.1 does not currently say so.** Content
   unmoved + fact signature moved = the Catalog said something different this time. That reading is
   available on `manifest.gwas_effects.signature`, but § 5.1's enumeration of the per-table
   signatures names `frequency / gene_metrics / literature / gene_validity / clinical_assertions /
   sources` and omits this one; see What does not exist. Detecting drift also requires
   **delete-and-re-derive**, because merge-not-clobber never re-asks an `association_id` already
   recorded — and this table is the worst case for that, since the Catalog *grows*: a re-run adds new
   associations but will never notice that an existing one's effect size was re-curated.

## Required to exist

Nothing requires `gwas_effects.csv`; `manifest.gwas_effects` is simply absent on a module that
carries none (`compiler.py:4786` returns `None` on an empty list), and the registry projects
`has_gwas_effects = 0` for that, honestly.

What it needs and what it drags in:

- **At least one `variants.csv` row with an `rsid`.** With none, the pass logs *"GWAS pass has no
  subjects"*, fetches nothing and writes nothing. A coordinate-only module gets no table at all.
- **The network.** `--offline` is a **no-op with a warning, not a failure** — the Catalog publishes a
  bulk download but this pass reads the REST API and has no snapshot to fall back on. An injected
  `client` still wins.
- **`licensing.csv` gains a row.** `merge_sources_file` writes `gwas_catalog` at layer `gwas_effect`
  (`vocab.py:561`). If you then delete `gwas_effects.csv` and leave the licence row, the compile
  warns *"declares 1 source(s) no table in this module uses"* — measured.
- **It does not need `resolution.csv`**, unlike `frequencies.csv`. The Catalog is queried by rsID.

## The columns that carry judgement

Ask the live model for the full list (below). These are the ones that get misread.

- **`effect_unit`** — the point of the table. Verbatim from `betaUnit`, **including the Catalog's
  uninformative `unit`**, because "these betas are on unknown and possibly different scales" is the
  fact a consumer must have. Null for an `OR`, which is dimensionless. Inside the fact hash.
- **`effect_allele`** — the allele `effect_size` is stated relative to, parsed out of
  `riskAlleleName` (`rs4149056-C` → `C`). **Null when the source wrote `-?`** — a fact, not a gap.
- **`effect_direction`** — the Catalog's `betaDirection`, `increase|decrease`
  (`vocab.VALID_EFFECT_DIRECTIONS`, closed). About the **measured trait**.
  `VariantRow.direction` is `protective|risk|neutral|unknown`, a clinical judgement. Increasing HDL
  and increasing LDL are both `increase`.
- **`effect_measure`** — `OR` or `beta` in practice, **open** vocabulary
  (`vocab.RECOMMENDED_EFFECT_MEASURES`). Mapped from two mutually exclusive Catalog keys
  (`orPerCopyNum`, `betaNum`), so it is exact rather than the download TSV's one ambiguous column.
- **`p_value` vs `p_value_num`** — the string is verbatim; the number is `gt=0, le=1` and is
  **withheld** on an underflow. Three-valued: a null `p_value_num` beside a non-null `p_value` means
  *the Catalog published a p-value this column cannot hold*, not *no p-value*.
- **`risk_allele_frequency`** — the Catalog's `NR` is an **absence** and arrives as null, distinct
  from a reported `0`.
- **`status`** — `resolved|not_found|ambiguous`. **`not_found` is a fact**: the Catalog was consulted
  and holds no published association for this variant. A variant never queried has no row at all.
- **`trait` vs `trait_efo_id`** — the label is descriptive and **outside** the fact hash; the id is
  the fact. `trait_efo_id` may be a comma-joined list (7 of 62 distinct cells on `hfe`).
- **`dataset`** — required, non-empty. Which Catalog release. A fact, inside the hash.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **You cannot add a `weight` column, and the error says so.** Measured: appending `weight` to the
   header gives `gwas_effects.csv line 2 [weight]: Extra inputs are not permitted` on every row.
   `extra="forbid"` forecloses the S36 repair at the schema level, not merely by policy. Neither is
   there a per-row precedence rule anywhere — "use the GWAS value where `weight` is null" was
   proposed and **refused**, because it puts two methodologies in one summable column (the reported
   defect) and leaves no single scale for `weighting:` to declare.
2. **The sign trap.** `VariantRow.weight` is documented positive = **protective**; a GWAS beta is
   positive on the **effect allele**. Transcribing one into the other inverts the claim on exactly
   the rows nobody re-reads. This is half of why the fill is barred.
3. **These betas are not poolable, and one module proves it.** `hfe_hemochromatosis`, measured off
   the shipped CSV: 195 rows, **12 distinct `effect_unit` values** — `SD units` (8), `SD` (4) and
   `s.d.` (4) are three spellings of one; `g/dL` and `g/dl` differ only in case; **138 rows carry the
   bare `unit`** — across 62 distinct `trait_efo_id` cells (58 atomic EFO/OBA ids). Read them **per
   trait**, and read `manifest.gwas_effects.units` before combining anything.
4. **42 of 195 rows name no effect allele**, because the study never established which one carries
   the effect. Real evidence; **unusable as a weight in any direction**. Kept and counted rather than
   filtered, so that neither dropping them nor keeping them can happen by accident
   (`with_effect_allele` = 153, `without_effect_allele` = 42 in the manifest — measured).
5. **The request budget is `1 + 2N` per variant and the cache does not save you.** `pmid`,
   `study_accession`, `ancestry`, `trait` and `trait_efo_id` all sit behind `_links`. `_LinkCache`
   was built expecting associations to share studies; on this module it saved **nothing** — **382
   requests, 0 hits**, because rs1800562's associations name **175 distinct study accessions** across
   186 rows (measured off the CSV). `--no-study-facts` drops it to one request per variant and keeps
   the effects, losing pmid/trait/ancestry. Decide before you script it: the largest bundle in the
   real submitted corpus carries **177 rsIDs**.
6. **A 404 is the empty answer, not an outage.** The Catalog holds only variants with a published
   genome-wide association, so it 404s on a rare clinical one. `GwasNotFound` keeps that typed and
   `associations_for` converts it into a `not_found` row. The first version of this pass read it as a
   transport failure and **died on the first variant of the first real module it met** — 9 of
   `hfe`'s 10 rsIDs are in that state. Do not "fix" a `not_found` row by deleting it.
7. **`pvalue: 0.0` is a real Catalog underflow, and the row survives it.** Past float64's subnormal
   boundary the Catalog publishes exactly `0.0`; `p_value_num` refuses it (correctly — that is not a
   probability), the verbatim string is kept and the **row stays**. Six of them on `hfe`; the fix
   took the file from 189 rows to 195. The pass warns once, aggregated by reason.
8. **`--strict` escalates on the wrong thing if you assume the sibling passes' rule.** It does
   **not** escalate on `missing` — the Catalog's silence is a fact about the variant and true of most
   variants, so escalating it would refuse nearly every module. It escalates on `unusable`
   (associations served without an id to key on) and `p_value_underflows`. So `--strict` will fail
   `hfe_hemochromatosis` for six underflows that are the Catalog's shape, not an authoring mistake.

   > 🚧 **ROADWORKS — `--strict` fails a shipped flagship module today.**
   > **Current state.** Re-confirmed: the strict gate escalates on `p_value_underflows`, and
   > `hfe_hemochromatosis` has six of them straight out of the Catalog. No authored edit fixes that —
   > the underflow is the source's, and withholding `p_value_num` is the *correct* three-valued
   > answer. No test covers this ladder either, so its behaviour is unpinned in both directions.
   > **Expected state.** An underflow is a recorded fact, not a read failure, and belongs outside the
   > gate the way `missing` already is. It is not.
   > **Guard.** Do not run this pass under `--strict` in CI. If a pipeline sets `--strict` globally,
   > exempt the GWAS pass by name, and read a strict failure here as "the Catalog underflowed",
   > not as "this module is wrong".
9. **Merge-not-clobber, keyed per association.** Existing rows are authoritative. A re-run adds new
   associations and never re-asks about one already recorded — so a re-curated effect size is
   invisible. To regenerate, delete the file first, which also discards any hand-edits in it.
10. **Only one caller-visible exception type, and it is the outage type too.** `enrich_gwas` raises
    `GwasError` for a dead EBI *and* for an invalid existing `gwas_effects.csv`. It is the one pass
    with **no `*Unavailable` subclass** (ENRICHER.md's contract table: *"— client and pass share the
    type"*), so the 0.6.2 narrow-first handler-ordering rule has nothing to order here. Do not invent
    a `GwasUnavailable`; check `dir(just_dna_enricher.gwas)` if you need to know whether one landed.
11. **A near-miss filename is silently ignored, but the compiler tells you.** `gwas_effect.csv`
    (singular) produced *"is not a table this compiler reads, and it is one small edit from
    'gwas_effects.csv' — if that is a typo, every row in it is being silently ignored"* — measured.
12. **An orphan row warns and never fails, in both modes.** A row whose `variant_key` matches no
    variant gives *"gwas_effects.csv carries associations for N identity(ies) no variant in this
    module carries"* — measured identical under `--strict`. That is deliberate: narrowing a variant
    list after enriching is the ordinary case. Note it fires at **compile**, not at `validate_spec` —
    this table's cross-check lives inside `compile_module` (`_cross_check_gwas_effects`' only call
    site is the compile-time `_gwas_effect_checks` closure), so a green `validate_module` says
    nothing about this table's coherence. **Do not generalize that to all six sidecars**:
    `_cross_check_literature` is *also* called from `validate_spec`, which is precisely why the
    literature checks carry a dedup filter and these do not.

## What does not exist

- **No coordinates on the row, deliberately.** The Catalog's association payload has none — they sit
  on the SNP object behind a link — and a coordinate copied from the module's own `resolution.csv`
  would be the module's fact, not the source's. `variant_key` joins to the weights rows; `rsid` is
  what the archive names. Consequence: the orphan cross-check matches on `variant_key`/`rsid` only,
  unlike `clinical_assertions.csv`, which matches on position.
- **No `weight` fill, no fallback mechanism, and no module split.** All three refused, each with its
  own reason (S36). Splitting was refused because the split criterion would be *source coverage*, and
  membership would churn every time a paper lands — routing an upstream fact into authored identity.
- **No mantissa/exponent pair**, though the Catalog publishes one. Half of the 0.5 rejection still
  applies: it is a catalogue-of-millions problem, and a module cites tens of associations.
- **No parsed confidence interval.** `confidence_interval` is a verbatim string including `[NR]`
  (5 rows on `hfe`), because the bracket forms vary and parsing would discard what does not fit.
- **No `commercial_use = true`.** `GWAS_CATALOG_TERMS` (`enricher/.../licensing.py:350`) is the first
  source here with **no named licence**: EBI permits use but conditions it on the original data
  owners' terms, which for an aggregator of thousands of publications are not established. So
  `commercial_use` stays **`None`** and `redistribution` is `True`. Unknown is neither permission nor
  refusal — `taints_commercial_use` requires an explicit `False`, so a null warns rather than gating.
  **Do not tidy it to `True`**; `enricher/tests/test_gwas.py:279` pins it.
- **No rate limit to respect, and that is stated rather than guessed.** EBI publishes no numeric
  budget. `DEFAULT_REQUEST_INTERVAL = 1.0` is a **courtesy, not a transcribed limit**, unlike
  gnomAD's real 10/60s. Nobody should "correct" it against a number that does not exist.
- **`describe_table("gwas_effects.csv")` does not work.** It gates on `draft.DRAFTABLE`, which holds
  the authored kinds plus `licensing.csv`/`sources.csv`. Verified against compiler 0.6.1:
  `hints.describe_table("gwas_effects.csv")` raises `DraftError: 'gwas_effects.csv' is not an
  authored table of this format`. `table_requirements`, `get_template` and `lint_rows` refuse for the
  same reason. Same as every fact sidecar — not a gwas-specific gap.
- **`enrich_gwas` IS wrapped now — this bullet said otherwise and was right when written.** Closed as
  our RM12 on 2026-08-20: `enrich_gwas_effects` in `tools/passes.py`, registered in
  `register_extended_passes`, so it needs `JMC_MODE=extended`. Extended rather than essentials on the
  cost rule: budget is `1 + 2N` requests per variant because pmid/trait/ancestry/study_accession all
  sit behind `_links`, measured at **382 requests and 0 cache hits** on one real module. The CLI route
  still works and is the fallback on an older build:
  `uv run just-dna-enricher gwas <spec-dir> [--no-study-facts] [--use …]`. Also
  note `list_tables().sidecars` (`tools/authoring.py:150`) lists only four sidecars and omits the
  format-0.6 three, `gwas_effects.csv` among them — the `resource://just-dna/tables` resource does
  name all three, so the two disagree.
- **Two upstream doc claims are stale, both verified against installed 0.6.1/0.6.4.**
  (a) `ENRICHER.md:2701` still lists `enrich_gwas(mode=…)` as *"accepted, defaulted, never read"* in
  its open-questions section; RM100 shipped the fix in enricher **0.6.1** and the installed 0.6.4
  reads it (`if mode == "strict" and (result.unusable or result.p_value_underflows)`). What *is*
  still true from that entry: **no test covers the ladder** — `strict` appears nowhere in
  `enricher/tests/test_gwas.py`.
  (b) `MODULE_LIFECYCLE.md:272-279` § 5.1 omits `gwas_effects` from its list of per-table fact
  signatures, and its worked `hfe_hemochromatosis` example is stale twice over: it says
  *"everything else absent — three numbers to watch, not nine"* and quotes
  `sources.signature sha256:b79154f1…`. Compiled today that module carries **four** signatures
  (`gwas_effects.signature sha256:46d4b76f…` is present) and its `sources.signature` is
  `sha256:0afb6361…`, because the GWAS pass appended a licence row and `dataset` is inside
  `SOURCE_FACT_FIELDS`. An operator following § 5.1 literally would not watch this table's canary.

## Consumption today

| Read site | What it does with it |
|---|---|
| `just-dna-lite/…/v1_port/publish.py:37-39` | derives its upload allow-patterns from `ARTIFACT_PARQUETS`, so `gwas_effects.parquet` is **transported**. Bytes only |
| `just-dna-lite/…/tests/test_format_0_6.py:79-90` | asserts `gwas_effects.parquet` is in the allowlist — a regression test on transport, not a read |
| `just-dna-lite/webui/src/webui/state.py:6007` | imports `ARTIFACT_PARQUETS` so the client-side digest covers the file **as bytes**. Identity only |
| `just-dna-lite/…/annotation/hf_modules.py:39-64` | `ModuleInfo` carries `lead_url`, `weights_url`, `annotations_url`, `studies_url`, `sources_url` — **no gwas url**. A module installed from HuggingFace may not have the file locally at all |
| `just-dna-lite/…/annotation/hf_modules.py:632-652` + `report_logic.py:1238` | reads `manifest.weighting` and renders it verbatim into the report. On `hfe_hemochromatosis` that string is literally *"Read gwas_effects.parquet instead…"* — the consumer renders the pointer and **cannot follow it** |
| `just-dna-lite/…/cli.py:40` | mounts the enricher's Typer app whole, so `just-dna-pipelines enrich gwas <dir>` exists |
| `just-dna-registry/…/specfiles.py:104` | `FACT_CSVS` — what `revalidate` and `upgrade` rebuild a spec directory from. Missing here = silently dropped on re-publish |
| `just-dna-registry/…/services/upgrade.py:170` | maps `gwas_effects.csv` → `GwasEffectRow` to find and trim columns a newer model rejects (lossy) |
| `just-dna-registry/…/db/facets.py:211`, `db/schema.py:286,347`, `db/repository.py:950,1020`, `api/routers/modules.py:93-97`, `client.py:315,342` | one boolean, `has_gwas_effects = int(manifest.gwas_effects is not None)`, indexed and filterable. Tri-state at the API: omitting the filter says nothing |
| `just-dna-registry/…/services/catalog.py:222-238,361` + `models/api.py:131-160` | projects `GwasEffectsInfo` onto the module detail — `row_count`, `variant_count`, `with_/without_effect_allele`, `measures`, `units`, `traits`, `sources`, `datasets`. `units` and `without_effect_allele` are rendered **beside** the count on purpose, "because a row count alone reads as confidence" |
| `just-dna-registry/…/services/enrich.py:701-760` | the `/check` preflight offers `frequencies`, `literature`, `identifiers`, `acmg`, `pgx` — **no `gwas`**. The registry never runs or checks this pass |
| `just-prs`, `just-prs-mcp` | **nothing.** No match for `gwas_effects`, `GwasEffectRow` or `effect_unit` anywhere in either repo |

**Verdict: nothing reads a single value out of `gwas_effects.parquet`.** The registry reads the
manifest *block* and renders its facets on a module card; `just-dna-lite` transports the parquet,
hashes its bytes, and does not expose a URL for it. Not one `effect_size`, `effect_unit`,
`effect_allele` or `trait_efo_id` is read by any consumer. That is not unique to this table —
measured, `just-dna-lite` reads **zero** of the seven derived fact parquets (`frequencies`,
`gene_metrics`, `literature`, `gene_validity`, `clinical_assertions`, `gwas_effects`, `resolution`);
`sources.parquet` is the only sidecar it names.

## Blanks for just-dna-lite

- **The report already prints "read `gwas_effects.parquet`" and there is no code that can.**
  `_weighting_summary` renders `manifest.weighting.note` verbatim; the one module that declares a
  weighting block sends the reader to this table, and `ModuleInfo` has no field for it. **Ask:** add
  `gwas_effects_url` (and the other five fact sidecars) to `ModuleInfo`, gated on
  `manifest.artifact.files` like the rest — otherwise the block the consumer *does* read is an
  instruction it cannot execute.
- **Nothing gates on `units`, so the first read will pool unpoolable betas.** The manifest publishes
  the set precisely so this can be decided without touching the parquet. **Ask:** before any read
  site lands, branch on `len(manifest.gwas_effects.units) > 1` and refuse to aggregate; render per
  `trait_efo_id` only. What breaks today is latent rather than live — but the corpus that motivated
  the table is exactly the corpus that will hit it (see the last bullet).
- **Nothing reads `without_effect_allele`, so 42 of 195 rows have no defined handling.** Those
  associations cannot be weighted in any direction. **Ask:** whatever reads this table must render
  a null `effect_allele` as *direction unknown*, never drop the row and never assume the ALT — the
  count is published beside its complement specifically so that neither silent reading can happen.
- **The three-valued `status` has no consumer.** `not_found` means *the Catalog was asked and holds
  nothing*, which is a positive fact about a variant and is different from *not asked*. **Ask:** any
  reader must distinguish `not_found` from an absent row, and must not render either as "no
  association exists".
- **No consumer can say which Catalog release it read.** `datasets` is on the card and on the
  manifest; two modules in one report may carry different releases and nothing surfaces it. **Ask:**
  surface `manifest.gwas_effects.datasets` wherever a magnitude is shown, before anything reads a
  magnitude.
- **The population that needs this table does not have it, and the format's own corpus understates
  the problem.** Measured across the 27 submitted bundles in
  `/data/sources/just-dna-registry/data/input/`: **0 carry `gwas_effects.csv`** (era gap — the table
  did not exist), **27/27 carry rsIDs** (826 distinct, largest bundle 177), and **27/27 fill every
  `weight` cell — 2439 of 2439**, over 26 distinct values in `[-1.5, 1.5]`. Contrast the reference
  corpus, where `weight` is authored **zero** times in 42 cells. So S36's diagnosis is about the
  submitted corpus, none of which can yet be checked against a published effect. **Ask:** run
  `just-dna-enricher gwas --no-study-facts` over those bundles at re-publish and surface the
  resulting `units` set on the card, so a curator's 1.5 can be read beside what was actually
  measured. Budget it: 826 requests at `--no-study-facts`, unbounded with study facts on.

## Ask the live schema

`describe_table` / `table_requirements` / `get_template` / `lint_rows` **all refuse this table** (see
What does not exist). Two routes that do work:

```bash
# The plugin's own tool — GwasEffectRow IS in the reference, keyed by MODEL name, not CSV name.
authoring_reference()  ->  ["models"]["GwasEffectRow"]   # 22 column dicts, live descriptions
                       ->  ["vocabularies"]["effect_direction"]      # closed
                       ->  ["open_recommended"]["effect_measure"]    # open, seed values only
```

```bash
uv run python -c "
from just_dna_format.gwas import GwasEffectRow, GWAS_FACT_FIELDS
from just_dna_format.vocab import VALID_EFFECT_DIRECTIONS, RECOMMENDED_EFFECT_MEASURES, VALID_RESOLUTION_STATUS
for n, f in GwasEffectRow.model_fields.items():
    print(f'{n:22} {f.annotation!s:16} required={f.is_required()}  {f.description}')
print('fact fields  :', GWAS_FACT_FIELDS)
print('direction    :', sorted(VALID_EFFECT_DIRECTIONS))       # closed
print('measure seed :', sorted(RECOMMENDED_EFFECT_MEASURES))   # OPEN
print('status       :', sorted(VALID_RESOLUTION_STATUS))
"
```

Related live sources of truth, none to be restated from memory:

- `just_dna_enricher.gwas.DEFAULT_GWAS_ENDPOINT` / `DEFAULT_REQUEST_INTERVAL` — the API base and the
  courtesy interval (**not** a transcribed limit).
- `just_dna_enricher.licensing.GWAS_CATALOG_TERMS` — the licence row this pass writes, including the
  `commercial_use is None` that must not be tidied.
- `just_dna_compiler.compiler.ARTIFACT_PARQUETS` — whether `gwas_effects.parquet` is still in
  `artifact.digest`, and in what position (position is digest order).
- `just_dna_format.integrity.gwas_effect_signature(rows)` — recompute the fact hash yourself and
  compare against `manifest.gwas_effects.signature` to read the canary.
- `just_dna_format.manifest.GwasEffects` — the facets a consumer may gate on without a parquet read.
- `just_dna_format.layout.sidecar_write_path(spec_dir, "gwas_effects.csv")` — write to the file you
  read; never join the name onto `spec_dir` by hand.
- `dir(just_dna_enricher.gwas)` — check for a `GwasUnavailable` before assuming there is none.

Verified with: format 0.6.1, compiler 0.6.1, enricher 0.6.4, registry 0.18.2
(`importlib.metadata.version`, 2026-08-19). Every measurement in this file was taken against
`reference_examples/hfe_hemochromatosis` compiled in a scratch tree, or against the 27 bundles in
`just-dna-registry/data/input/`; nothing was inferred from a changelog.
