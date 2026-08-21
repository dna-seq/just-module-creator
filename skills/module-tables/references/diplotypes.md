# diplotypes.csv — a pair of haplotypes → a phenotype, and what a guideline says about it

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

Reference for an agent about to author, draft or read this table. Every claim below was read out of a
file or measured; measurements say so and name the probe. Verified against **format / compiler 0.6.1,
enricher 0.6.4, registry 0.18.2** (`importlib.metadata.version`, 2026-08-19).

## What it is

The table answers *"this person's two copies of this gene are `*2` and `*17` — so what?"* It is the
**actionable** layer of pharmacogenomics: the clinic prescribes against a diplotype (`CYP2C19 *2/*17`),
not against an rsID (`pgx_draft.py:7-9`). One row maps a canonicalized haplotype pair → a metabolizer
phenotype and a human-readable conclusion, optionally plus a drug, CPIC's recommendation strength and
the clinical setting that recommendation is scoped to.

It is the third of the four tables of the PGx model (`pgx.py:1-18`): `haplotypes.csv` says which
variants make an allele, `allele_function.csv` says what one allele does, **this** says what a pair
means, and `activity_phenotype.csv` bins a score. The format supplies the tables; a **consumer's
star-allele caller** supplies the phased diplotype and CN/SV calls. Nothing here reads a VCF, and this
is the one PGx table that carries no coordinate at all — so it also has no rsID, no VRS id and no
resolution.

Its readers: a report generator looking up a called diplotype, and a prescriber-facing surface
selecting rows by `drug` and `clinical_context`.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.pgx.DiplotypeRow` (`pgx.py:218`), subclass of `base.AuthoredModel` |
| Parquet | `diplotypes.parquet` — in `compiler._TABLE_KINDS` (`compiler.py:230`) and in `compiler.ARTIFACT_PARQUETS` |
| Dedup key | `(gene, haplotype_a, haplotype_b, trait_efo_id, drug, clinical_context)` — `compiler._TABLE_DUPE_KEYS[DiplotypeRow]`, `compiler.py:258-260`. Six-part, and every part earned by real CPIC data |
| Authored or machine | **Authored.** `pgx_draft` writes real rows from CPIC; a human/AI owns them afterwards. `enrich-pgx` deliberately never generates them (`pgx.py` enricher, lines 13-18: "having a network pass write them would blur exactly the authored/derived line") |
| Who writes it | the author; `just-dna-enricher draft --gene <G>` (MCP: `draft_from_cpic`, extended tier). The compiler stamps one parquet-only column (`module`) |
| Fact signature | **none.** Authored table, not a derived sidecar — see *What moving this table moves* |
| In `content_signature`? | **Yes**, every authored cell |
| In `artifact.digest`? | **Yes**, as `diplotypes.parquet` bytes |
| Positional? | **No.** `DiplotypeRow` declares no `chrom`/`start`, so it is absent from `compiler._POSITIONAL_TABLE_KINDS` (derived at `compiler.py:1146-1150` from which models carry both columns). No resolution, no VRS, no `UNJOINABLE_PHRASE` |

Run `describe_table("diplotypes.csv")` / `table_requirements("diplotypes.csv")` for the live columns,
requirements and vocabularies. Never trust a list in prose, including the ones below.

## Who populates what

Measured with `draft.authoring_requirements("diplotypes.csv")` and `draft.stub_template`:
required = `gene`, `haplotype_a`, `haplotype_b`, `conclusion`; the other nine optional; `any_of` empty.
`stub_template` writes `<<REPLACE>>` into exactly those four and leaves the rest blank.

| Cell(s) | Who | Notes |
|---|---|---|
| `gene`, `haplotype_a`, `haplotype_b` | **author**, or **drafter** | `pgx_draft` splits CPIC's `*1/*2` string on `/` (`pgx_draft.py:137`) and hands the halves straight to the model, which then canonicalizes them |
| `conclusion` | **author**, or **drafter** | required. `pgx_draft` writes `f"{gene} {diplotype}: {phenotype}"` for a phenotype row (`pgx_draft.py:426`) and, for a drug row, CPIC's *implication* + *recommendation* concatenated verbatim — transcribed, never summarized (`pgx_draft.py:241-245`) |
| `phenotype` | **author**, or **drafter** | free text, no vocabulary, no cross-check. `pgx_draft` copies CPIC's `generesult` |
| `drug`, `recommendation_strength`, `clinical_context` | **author**, or **drafter** | `_recommendation_rows` (`pgx_draft.py:186-250`) fills all three from CPIC's `recommendation` table. `recommendation_strength` is closed-vocabulary (`vocab.VALID_RECOMMENDATION_STRENGTH`, `vocab.py:380`) |
| `trait_efo_id`, `direction`, `response` | **author only.** No drafter writes any of them | measured over `reference_examples/cyp2c19_star_alleles`: `response` null on 1190/1190 rows. `direction`/`trait_efo_id` are authored in `hfe_compound_het` and `apoe_epsilon`, both hand-written |
| `clin_sig` | **author only** — and see the refusal note below | closed vocabulary via `AuthoredModel`'s shared validator (`base.SHARED_VOCABULARIES`) |
| `evidence_level` | **author only** — and see the refusal note below | closed vocabulary `vocab.VALID_EVIDENCE_LEVELS` (PharmGKB `1A`…`4`) |
| `module` (parquet only) | **compiler-stamped** | added by `_build_table` (`compiler.py:447-464`) so `reverse_module` can recover the module name. Not a CSV column; authoring one fails with `Extra inputs are not permitted` |
| — | **nobody, ever** | there is no permanently-unwritten column on this table |

**No column here is registry-stamped.** `normalize.IDENTITY_AUTHORITY_KEYS` (`namespace`, `owner`,
`canonical_id`) are `module_spec.yaml` keys, not row columns.

**No `stamped_identity_field` on this model at all.** Unlike `HaplotypeRow`/`PharmVariantRow`, there is
no `variant_key`, no `authored_ident`, no compiler-filled `alts` — nothing on this table refuses an
authored value, because nothing on it is compiler-owned identity.

### The cells no tool may fill, and the exact refusal

Two of this table's columns are on `hints.REDUNDANCY_BEARING` (`hints.py:81-104`), so a lookup reports
them and refuses to write them. Measured by running `hints.inspect_rows("diplotypes.csv", …)` on a
two-row fixture; both came back as `Finding(row=None, level="info")`:

- `clin_sig` — *"left to the author on purpose: `enricher.clinical.verify_clin_sig` (authored call vs
  ClinVar's) compares it against a source, and filling it from that same source would make the check
  vacuous"*.
- `evidence_level` — same sentence, checker `enricher.clinpgx` (authored level vs the ClinPGx snapshot).

⚠️ **Neither of those checkers sees a diplotype row, and `describe_table` says so as of 0.6.6.**
`hints.REDUNDANCY_BEARING` is keyed on a **bare column name**, so the advisory printed wherever the
column appeared: `verify_clin_sig` is driven from `variants.csv` and the ClinPGx leg keys out of the
PGx annotation tables. `REDUNDANCY_BEARING_TABLES` (upstream RM123) scopes the *explanation* — the
refusal stays column-keyed on purpose, since whether a provider should start filling `clin_sig` on a
diplotype row is a separate decision nobody has taken. Our `describe_table` appends the scope to the
entry, so the reason no longer outruns the checker.

**The advice is unchanged and it matters more here, not less:** author both cells yourself. Combined
with gotcha 12 below — `enrich-pgx` never opens `diplotypes.csv` — **nothing cross-examines either
cell**, so an independent reading is the only thing standing behind them, and a green enrich is not
agreement with ClinVar or ClinPGx.

`hints.ATTESTATION_BEARING` is `{provenance_quote, provenance_regex}` (`hints.py:72`) — **neither column
exists on this table**, so nothing here is attestation-bearing. This table carries no citation and no
quoted passage; grounding for a diplotype module lives nowhere (see *What does not exist*).

**But read the two refusals with a caveat, because their stated reason does not hold here.** Verified
by reading both passes: `enricher/clinical.py` is typed against `just_dna_format.spec.VariantRow` and
loads no other table; `enricher/clinpgx.py:186-201` loads `pharm_variants.csv` and nothing else, and
keys every comparison on `row.rsid` — which a `DiplotypeRow` does not have. So on *this* CSV both
info lines name a check that can never run. The **withholding is still correct** — a machine writing
`evidence_level` from ClinPGx onto a diplotype row is filling a checked-looking cell from a source —
but do not read the info line as "a check will catch it if I get this wrong". Nothing will. Flagged
below as a probable upstream defect.

The one thing that *does* read `DiplotypeRow.clin_sig` is `_cross_validate_phase_ambiguity`, which
includes it in the disagreement tuple `(conclusion, phenotype, direction, clin_sig)`
(`compiler.py:3072`). That is a use, not a check against a source.

## What moving this table moves

Measured by compiling `reference_examples/cyp2c19_star_alleles` seven times with one mutation each
(`compile_module(strict=False, resolve_with_ensembl=True, ensembl_cache=None)`), comparing
`content_signature`, `artifact.digest`, the `diplotypes.parquet` entry, the `manifest.inputs[]` entry
for `diplotypes.csv`, and whether `manifest.verification` survived.

| An edit here | `content_signature` | this table's fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row | **moves** | n/a — none exists | **moves** | **dropped** |
| edit an authored cell (`conclusion`) | **moves** (`13aec2…`→`0727a4…`) | n/a | **moves** | **dropped** |
| write the pair in the other order (`*11,*10`) | **unmoved** | n/a | **unmoved** — parquet byte-identical | **dropped** |
| reorder rows | **unmoved** | n/a | **moves** (`5a831e…`→`e4814d…`) | **dropped** |
| a provenance-only cell | — | — | — | — (this table has no `fetched_at`, `source` or `status` column) |
| re-run the producing pass (`draft` again) | moves iff it appended a row; a re-run that appends nothing changes nothing | n/a | same | dropped iff bytes changed |
| delete the file and re-derive it | **moves** while absent (`89d6da…`); a re-draft under a filter that reproduces the same rows returns to the original | n/a | **moves**; `artifact.files` drops from 4 to 3 | **dropped** |
| recompile under a newer toolchain | unmoved | n/a | may move (parquet writer / polars) | **stands** — bytes unchanged |
| rewrite CRLF → LF | **unmoved** | n/a | **unmoved** | **stands** (RM82) — `manifest.inputs[]` moved and nothing else |

1. **Is this table inside `content_signature`?** Yes. It is an authored `_TABLE_KINDS` member, so
   `integrity.content_signature` hashes its rows as `model_dump(mode="json", exclude_none=True)`,
   sorted, order-independent (`integrity.py:189-255`). It has **no fact signature** — that mechanism
   (`integrity.fact_signature` and the `FREQUENCY_FACT_FIELDS`-shaped constants) is for the derived
   sidecars only, and this table has no provenance column to exclude from one.
2. **Is it inside `artifact.digest`?** Yes, via `diplotypes.parquet`, which `ARTIFACT_PARQUETS` lists.
   The **authored CSV bytes are not** in the digest — they are in `manifest.inputs[]`, which is a
   separate listing over raw bytes (`file_entries(spec_dir, _INPUT_FILES)`).
3. **Does an edit here un-close the module?** **Yes, for any byte change except a newline rewrite.**
   `diplotypes.csv` is in `compiler._INPUT_FILES`, so it is inside `authored_input_entries`
   (`compiler.py:361-386`) and therefore inside `verification.json`'s `module_hash`. Measured: swapping
   `haplotype_a`/`haplotype_b` on one row of 1190 dropped the attestation with *"verification.json is
   stale: the attestation was computed over different module bytes"* while moving **no** identity at
   all — not the content signature, not the digest, not the parquet. Measured the other way too:
   CRLF→LF kept it (RM82's newline normalization). Note the converse asymmetry, from
   MODULE_LIFECYCLE §5: an `authorship:` append un-closes a module while moving no identity either.
4. **Is this table part of the §5.1 canary?** **No, and it cannot be.** The canary reads
   *content unmoved + a fact signature moved* = the upstream source changed its answer
   (MODULE_LIFECYCLE.md:260-300). This table publishes no fact signature, so it can only ever produce
   row 1 or row 4 of that table. If CPIC silently revises a diplotype's phenotype, **nothing in a
   compiled module detects it** — a re-`draft` merges rather than re-asks, and there is no signature to
   compare. The delete-and-re-derive operation the canary needs has no meaning here, because deleting
   `diplotypes.csv` deletes the authored table itself, not a re-derivable sidecar.

## Required to exist

- A module needs **at least one** recognized table; `diplotypes.csv` alone satisfies that
  (`compiler.py:3602-3607`, *"module has no recognized table: add variants.csv or a 0.4 table (e.g.
  pharm_variants.csv, diplotypes.csv, pgs.csv)"*).
- It **drags in nothing**. `studies.csv` is required iff `variants.csv` is present, and the 0.4 tables
  are exempt — not because they carry their own evidence but because `StudyRow` can only name a
  *variant*, so for a gene-keyed table the requirement would be unsatisfiable rather than merely unmet
  (`compiler.py:3609-3617`, S19/RM47).
- `haplotypes.csv` is **optional and not implied**. A module may legitimately carry a diplotype table
  alone and lean on the caller's own allele definitions. Two cross-checks only fire when
  `haplotypes.csv` is present (`compiler.py:2932-2967`, `2995-3028`) — so a diplotype-only module gets
  *less* checking, not more.
- If any row came from CPIC, `licensing.csv` is effectively required: CPIC's terms forbid sale, the
  drafter writes a `SourceRow` declaring that, and the compile licence gate refuses on a missing
  `declared_use` (the `cyp2c19_star_alleles` README: *"strip its `declared_use` and the compile fails"*).

## The columns that carry judgement

- **`haplotype_a` / `haplotype_b`** — an identity, not a grammar. The rule is
  `pgx.HAPLOTYPE_NAME_PATTERN` = `^\S+$` (`pgx.py:55`): non-empty, no whitespace. `STAR_ALLELE_PATTERN`
  (`pgx.py:39`) still exists and `pgx_draft` checks it at three sites (`_haplotype_rows`,
  `_split_diplotype`, and `draft_gene`'s allele loop — the "four sites" figure comes from a stale
  comment at `schema/…/pgx.py:42-43`), but it is **not** the naming rule
  here — enforcing it made APOE's `e2`/`e3`/`e4` unstateable and produced "used but not defined" for an
  author who spelled one allele two ways across two tables.
- **`conclusion`** — required, and the only place a reader learns what the pair *means*. Transcribe a
  guideline's own words; do not summarize two halves into one.
- **`phenotype`** — free text with no vocabulary and no cross-check. You choose whether the module
  spells it `Poor Metabolizer` or `PM`, and nothing anywhere reconciles that with
  `activity_phenotype.csv`'s `phenotype` (also free text, `binning.py:319`).
- **`clinical_context`** — the setting a recommendation is scoped to, and part of the row key. See the
  gotchas; this is the column most likely to be misread as a population.
- **`recommendation_strength` vs `evidence_level`** — two bodies, two questions. CPIC grades *how
  firmly it tells a prescriber to act*; PharmGKB grades *how well established the association is*
  (`vocab.py:366-378`). A provider fills only its own. In `cyp2c19_star_alleles`, `evidence_level` is
  empty on all 1190 rows deliberately, and the README says so.
- **`direction` / `clin_sig`** — closed vocabularies from `AuthoredModel`'s shared validators. They are
  what makes a diplotype row comparable to a variant row, and `clin_sig` also feeds the
  phase-ambiguity disagreement test.

## Gotchas

Ordered by how likely a first-timer is to hit it.

1. **The pair is canonicalized `a <= b` LEXICOGRAPHICALLY, so `*10 < *2` and `*17 < *2`.**
   `_canonicalize_pair` (`pgx.py:306-312`) swaps on `>` over strings, not over star numbers. Measured
   with `hints.inspect_rows`: an authored `*2,*17` comes back as `*17,*2`, and the committed
   `cyp2c19_star_alleles/diplotypes.csv` begins `*10/*10, *10/*11, *10/*12` — measured 0 of 1190 rows
   violate the order. **Cost:** a consumer that sorts numerically, or does not sort at all, silently
   misses the row and reports nothing rather than erroring. Sort your lookup key the same way the model
   does, or look up both orders.
2. **Canonicalization happens at LOAD, so a committed CSV need not be canonical — and writing it the
   other way un-closes the module while moving no identity.** Measured: `hfe_compound_het/diplotypes.csv`
   ships one row as `C282Y-H63D,C282Y` (1 of 8 violates `a <= b`), and it is perfectly legal. Measured
   the consequence on `cyp2c19_star_alleles`: swapping one row's two haplotype cells left
   `content_signature`, `artifact.digest` and `diplotypes.parquet` **byte-identical** and dropped the
   verification attestation. `hints.inspect_rows` reports the swap as a `normalized` alteration with
   `applied: true` precisely so this is not a surprise (`hints.py:465-476` — *"`DiplotypeRow` swaps
   `haplotype_a`/`haplotype_b` without saying so"*).
3. **`clinical_context` is part of the dedup key, is whitespace-stripped on load, and the settings
   genuinely disagree.** CPIC scopes clopidogrel to `CVI ACS PCI`, `CVI non-ACS non-PCI` and `NVI`, and
   the same `*2/*2` Poor Metabolizer is `strong` in the first and `moderate` in the third
   (`pgx.py:264-275`; the `cyp2c19_star_alleles` README states it too). Three of CPIC's sixteen live
   values carry trailing whitespace (`'CVI ACS PCI '`, `'CBZ use >3mos '`), so `_normalize_clinical_context`
   strips (`pgx.py:291-297`). **Cost, measured:** authoring one row `'CVI ACS PCI'` and another
   `'CVI ACS PCI '` compiles to `diplotypes.csv: duplicate row for key ('CYP2C19', '*10', '*10', None,
   'clopidogrel', 'CVI ACS PCI')` — an **error**, not a merge. Two spellings of one setting is one row,
   and the compiler refuses rather than picking.
4. **It is deliberately NOT called `population`, and `population` is not a legal column.** Measured:
   `DiplotypeRow(..., population="EUR")` → `Extra inputs are not permitted`.
   `FrequencyRow.population` is an ancestry group with a validated vocabulary; this is indication, age
   band, prior-treatment status or dose band. Probed upstream against CPIC's live `recommendation`
   table (2,115 rows, 2026-08-03): `general` on 1,912, then `CVI ACS PCI`, `NVI`, `pediatrics`,
   `adults`, `PHT naive`, `<= 1g per day`. Reusing the name would spend the one ancestry will want here
   later (`pgx.py:264-275`). It is open text on purpose — DPWG and CPNDS scope differently.
5. **Two row families coexist for one pair, and that is the design.** Measured on
   `diplotypes.parquet`: 1190 rows = 595 with `drug` null (what the pair *is*) + 595 with
   `drug=clopidogrel` (what CPIC *advises*), over 595 distinct pairs. They survive because `drug` is in
   the dedup key. **Cost:** a consumer that does not filter on `drug` double-reports every diplotype.
   And the reverse cost, measured: adding a second unscoped row for a pair fails with
   `duplicate row for key ('CYP2C19', '*2', '*2', None, None, None)` — you cannot carry two unscoped
   conclusions for one pair, however different they are. Use `trait_efo_id`, `drug` or
   `clinical_context` to key them apart, or merge the prose.
6. **`--allele` is not optional on a big gene.** `draft --gene CYP2D6` unfiltered is 16,290 diplotype
   rows, 73% of them `Indeterminate` — every row a faithful transcription and a module no human can
   read (`pgx_draft.py:150-172`, RM34). *n* alleles is *n(n+1)/2* pairs; six alleles collapse CYP2D6 to
   21. `*1` is always kept, because it is *defined* by carrying no variants and excluding it would make
   `*1/*2` undraftable. An unknown allele name is an **error** listing what CPIC publishes, never a
   quietly smaller module.
7. **A diplotype is already a statement about two homologs, so compound heterozygosity needs no
   predicate language — but no column can say the two rows are indistinguishable.**
   `reference_examples/hfe_compound_het/` writes cis and trans as two rows: `C282Y/H63D` (in trans, no
   wild-type protein, at-risk) and `C282Y-H63D` + `wt` (both on one chromosome, one intact copy,
   carrier). They present the identical unphased genotype and carry opposite conclusions.
   `_cross_validate_phase_ambiguity` (`compiler.py:2995-3130`) reports that as a **warning**; measured
   with `validate_spec` on that example: *"HFE: 1 group(s) of diplotype rows are indistinguishable
   without phase — same unphased genotype, different conclusions … e.g. C282Y/H63D, C282Y-H63D/wt"*.
   It reports **two classes**, and the distinction matters: *"defines them identically"* means phase
   does not help at all (CYP2D6 `*10`, `*100`, `*101`, `*147` carry identical defining-variant sets, so
   a real draft produced 378 such groups and 20 genuinely phase-ambiguous ones); *"indistinguishable
   without phase"* means a phased consumer resolves it. Telling an author to go buy phasing for the
   first class would be wrong.
8. **The check is closed-world and only runs with `haplotypes.csv`.** It compares the rows a module
   states, never the ones it omits. `apoe_epsilon` is the standing illustration: ε2/ε4 vs ε1/ε3 is the
   textbook unphased collision, the module carries no ε1 (measured: haplotypes are exactly
   `e2`, `e3`, `e4`), and nothing fires — correctly, since the module makes no ε1 claim.
9. **A star allele used here and defined nowhere is dead weight, and the cure is subtraction.**
   `_cross_validate_haplotype_definitions` (`compiler.py:2932-2967`) warns when
   `allele_function.csv`/`diplotypes.csv` name an allele `haplotypes.csv` does not define; `*1` is
   exempt by definition. CPIC pairs every allele it knows, including ones whose defining variants it
   does not publish in a holdable form — `*36`, `*37`, `*42` arrived across 71 diplotype rows with
   nothing defining them, and the curation was to **drop** them, 666 → 595 (the example's README). It
   is a warning, not an error, because a module leaning on an external caller's definitions may keep
   them.
10. **Nothing joins this table to a VCF.** No `chrom`, no `start`, no `rsid`, no `variant_key`, no
    `alts`, no VRS id. It is absent from `_POSITIONAL_TABLE_KINDS`, gets no `resolution.csv` row, and
    `enrich`'s subject collection reads `variants.csv`, `pharm_variants.csv`, `haplotypes.csv` and
    `heteroplasmy.csv` and **not** this one (`enricher/enrich.py:85-92`, `:156-175`). Measured on `cyp2c19_star_alleles`:
    `positional_rows: 106` (all from `haplotypes.csv`), `vrs_alleles: 57`, and
    `resolution_subjects: 0` with `fully_resolved: true` — the empty-`all()` trap. Read
    `fully_resolved` only together with `resolution_subjects`.
11. **A diplotype-only module published `genes: []` before compiler 0.6.6.** `manifest.stats` for
    `cyp2c19_star_alleles` was `gene_count: 0, genes: [], variant_count: 0` while all 1190 rows carry
    `gene=CYP2C19`. **Fixed in compiler 0.6.6** (upstream **RM121**): `module_stats` takes the gene facets over every authored table, `variant_stats` keeps its `variants.csv` promise, and a module already published carries the stats its compile wrote — recompile and re-publish to be findable by gene. Re-measured on `cyp2c19_star_alleles`: `gene_count: 1, genes: ['CYP2C19']`. `variant_count` is still 0 there, and correctly so — it counts
    what `variants.csv` holds.
12. **The drafter and the enricher never verify a single cell of this table.** `enrich-pgx` reads
    `haplotypes.csv` and `allele_function.csv` and cross-checks `function_status` against PharmVar and
    CPIC; it does not open `diplotypes.csv` (grepped: zero occurrences of `diplotype` in
    `enricher/pgx.py`). So a phenotype, a recommendation strength or a conclusion here is **unverified
    by construction**, and no warning says so.

    > 🚧 **ROADWORKS — a diplotype-only module is the *least*-checked shape, not the most.**
    > **Current state.** Confirmed. Both PGx cross-checks are driven from `haplotypes.csv`: without
    > that file `_cross_validate_haplotype_definitions` and the enricher's function-status check
    > early-return, and `enrich-pgx` never opens this table at all. A module that is *only*
    > `diplotypes.csv` therefore passes every gate having had no cell of it compared with anything —
    > and the compile output looks identical to a thoroughly checked one.
    > **Expected state.** There is no verification route for a bare diplotype table and none is
    > designed. Nothing will tell you it was skipped.
    > **Guard.** Ship `haplotypes.csv` and `allele_function.csv` beside your diplotypes even when the
    > diplotypes are the point — that is what turns the cross-checks on. If you cannot, say in the
    > module's README that these rows are unverified, because no artifact field records it.
13. **`reverse_module` widens the CSV from the columns you wrote to all thirteen.** Measured:
    reversing `cyp2c19_star_alleles`' artifact re-emits `diplotypes.csv` with all 13 columns (the
    authored file has 7), 1190 rows, 0 order violations — and recompiling reproduced both
    `content_signature` and `artifact.digest` exactly. The round-trip is content-lossless and
    byte-lossy, so it un-closes the module.
14. **The committed flagship example predates its own key column.** `cyp2c19_star_alleles/diplotypes.csv`
    has no `clinical_context` column at all; measured, the compiled parquet has it null on 1190/1190
    rows including the 595 clopidogrel ones. The setting exists only in the README and the module
    description ("for the CVI ACS PCI population"). Flagged below. Do not copy its header as a template
    — ask `describe_table`.

## What does not exist

- **A `requires_phase` column: proposed and refused.** It would make an author restate what the data
  already determines, and go stale the moment a haplotype is edited; the compiler already holds both
  tables and the computation is pure and offline, which is the validate-by-redundancy class it belongs
  to (`compiler.py:3010-3016`, `docs/COMPILER.md:139`, `docs/ROADMAP_0_7.md:108`). Do not re-propose it.
- **A `population` column: refused by name.** See gotcha 4. `clinical_context` is the answer and it is
  deliberately not ancestry.
- **A predicate / expression language for cis-vs-trans: refused.** `haplotypes.csv` is a junction table
  so a haplotype is same-strand conjunction, and a diplotype is already a statement about two homologs
  — cis and trans are two rows (`compiler.py:2997-3003`; `schema/spec.py:490` points a `VariantRow`
  author here for the same reason). `docs/FAQ.md:241` refuses expressions module-wide.
- **`requires_callable` / `callable_from`: absent, and known-absent.** They are `VariantRow`-only, so a
  star-allele module cannot record CPIC's own core assumption — that an uncalled position is reference.
  Open as **RM70** (`docs/ROADMAP_0_7.md:464-489`), found dogfooding 2026-08-13, deferred because an
  authored column is the most expensive addition the format makes and the owner-table question
  (`haplotypes.csv` and `pharm_variants.csv` name a position; `diplotypes.csv` does not) is unsettled.
- **No citation, no PMID, no provenance quote.** `StudyRow` can only name a variant, so grounding a
  diplotype row is unsatisfiable rather than merely unmet (S19/RM47). There is nowhere to record
  *which paper* a conclusion came from except the `conclusion` prose itself.
- **No activity score.** CPIC's `totalactivityscore` is read by the drafter and deliberately not
  stored: `n/a` means CPIC did not score the pair (an absence → empty cell), while `≥3.0` is a real
  bound the numeric bin columns cannot hold, and the two are reported as different findings
  (`pgx_draft.py:412-419`). Binning a score is `activity_phenotype.csv`'s job, and computing one is the
  consumer's (`binning.py:425-427`).
- **No cross-check between this table's `phenotype` and `activity_phenotype.csv`'s.** Verified against
  the compiler's own audit inventory (`docs/audit/COMPILER_FROM_CODE.md:566-567`): the only two PGx
  cross-checks are haplotype-definition coverage and phase ambiguity. The four-table model's third
  and fourth tables are joined by a free-text string nobody validates.
- **No copy-number notation.** CPIC writes `*4x≥3/*95`; `≥` is neither a nucleotide nor a star-string
  character, so the drafter skips such pairs with an aggregated warning — a real CYP2D6 draft skips 546
  of them (`pgx_draft.py:401-409`). Copy number lives on `AlleleFunctionRow` as an attribute of the
  *cis* allele-unit, and `*2x2/*4` ≠ `*2/*4x2` (`pgx.py:14-18`).

## Consumption today

**Nothing reads a row of this table.** That is the finding, and it is precise: the table is
*discovered*, *published*, *validated*, *counted* and *migrated* — and never read for its content.

| Site | What it does |
|---|---|
| `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/module_config.py:491-502` | `LEAD_TABLES` includes `diplotypes` third, after `weights` and `pharm_variants`. This is what makes a diplotype-led directory count as a module at all — discovery, listing, editing and the HuggingFace publisher all key on it |
| …`module_config.py:518-530` (`find_lead_table`) | probes `diplotypes.parquet` on disk to answer "is this a module" |
| …`annotation/hf_logic.py:222-250` (`_lead_join_strategy`) | classifies it **`unsupported`** — no populated coordinates and no `rsid`+`genotype` to fall back on. Classified by schema, not family name, so it absorbs new families for free |
| …`hf_logic.py:107`, `:304`, `:602` | raises `UnsupportedLeadTable` and the per-module loop records it in `skipped[]` and continues. It used to raise `ColumnNotFoundError` and abort every other selected module with it |
| …`v1_port/publish.py:90` | a 0.4-family-led module publishes like any other |
| `just-dna-registry/src/just_dna_registry/specfiles.py:56-67` | `diplotypes.csv` is a recognized spec file, so it survives store → `revalidate` → `upgrade` round-trips |
| …`services/upgrade.py:159` | `_ROW_MODELS["diplotypes.csv"] = DiplotypeRow`, used by `offending_columns` / `trim_unknown_columns` so a pre-0.4 spec's stray column is reported or trimmed rather than crashing the recompile planner |
| …`models/api.py:500-507` | `SpecStats.table_rows` carries per-CSV row counts from `validate_spec`. Measured: `{"haplotypes.csv": 106, "allele_function.csv": 36, "diplotypes.csv": 1190}` |
| …`db/repository.py:663` | inserts `manifest.stats.genes` into `version_genes`, which `db/repository.py:1003-1009` joins for the `gene=` search facet |
| **not** `services/enrich.py:349-353` | `ENRICHMENT_SUBJECT_TABLES` is `pharm_variants.csv`, `haplotypes.csv`, `heteroplasmy.csv`. `diplotypes.csv` rows are **not** counted against `enrich_max_variants` |
| `just-prs` | nothing. `just_prs/scoring.py:60`'s `is_diplotype` is the PGS Catalog's own scoring-file column, unrelated to this table |
| `just-dna-lite/webui`, `src/` | nothing. Grepped: zero hits |

Downstream of that: `just-dna-lite/docs/V1_PARITY.md:110-114` records `lnewco` (the APOE diplotype
module) as *"unblocked by 0.5, not yet built"* — the only Gen-I module with no Gen-II counterpart. The
tables it needs shipped over a year of releases ago and
`../just-dna-format/reference_examples/apoe_epsilon/` is a worked example of exactly that locus.
`data/interim/v1_port/GAPS.md:48-54` still describes the blocker as a missing schema extension, which
is stale.

## Blanks for just-dna-lite

- **Ask: read `diplotypes.parquet` by diplotype, not by position.** Unread today —
  `_lead_join_strategy` classifies it `unsupported` and `hf_logic.py:602` skips it. A reader needs no
  VCF join: it needs the caller's `(gene, hap_a, hap_b)` and a lexicographic sort, then one lookup.
  **What breaks today:** a published CYP2C19 module annotates zero rows and appears in
  `skipped[module_name]` with *"lead table has no populated coordinates and no rsid + genotype"* —
  which reads as a defective module rather than as "this module answers a question we do not ask".
  `lnewco` (APOE ε) is the concrete first customer and has been waiting since 0.5.
- **Ask: select on `drug` + `clinical_context` before reporting.** Unread today — nothing in the
  consumer knows either column exists. Measured on the reference module: 1190 rows over 595 pairs,
  half of them drug rows, so a naive reader double-reports every diplotype; and CPIC's settings
  disagree (`strong` in `CVI ACS PCI`, `moderate` in `NVI`), so a reader that ignores
  `clinical_context` picks a clinical setting on the patient's behalf. **What breaks today:** nothing
  visible, because nothing reads it — which is why this is cheap to get right before the first reader
  ships rather than after.
- **Ask: propagate the compiler's phase-ambiguity warning into the report, and withhold on it.**
  Unread today — the warning lands in `manifest.compilation.warnings` and no consumer parses it. The
  compiler's own sentence states the required behaviour: *"a consumer with unphased calls must
  withhold rather than pick one; a phased consumer resolves it"*. **What breaks today:** if a
  diplotype reader is built without this, HFE `C282Y/H63D` versus `C282Y-H63D`+`wt` — identical
  unphased genotype, opposite conclusions — will either manufacture an at-risk finding or suppress
  one, silently. Note the two warning classes are different asks: one is resolved by phasing, one
  cannot be resolved at all.
- **Shipped: `genes` is surfaced for a table-kind-led module** (compiler 0.6.6, upstream RM121). It
  was `variants.csv`-only, so `registry_search(gene="CYP2C19")` could not find a CYP2C19 star-allele
  module while the gene sat on every row. A module published before that release needs a recompile.

## Ask the live schema

```
list_tables()                                # every table kind and which model owns it
describe_table("diplotypes.csv")             # current columns, categories, vocabularies,
                                             #   redundancy_bearing / attestation_bearing
table_requirements("diplotypes.csv")         # always / any_of / defaulted / optional, from the model
authoring_reference()                        # the cross-table rules, dedup keys and cofactor columns
get_template("diplotypes.csv")               # the header and a <<REPLACE>> stub row
lint_rows("diplotypes.csv", <csv text>)      # canonicalization shown as `normalized` alterations,
                                             #   duplicate keys against the compiler's own key,
                                             #   and the info lines for the cells left to you
validate_module(<spec_dir>, strict=True)     # the two PGx cross-checks, as warnings
```

In Python, when you need the constants themselves rather than a tool's rendering of them:
`just_dna_format.pgx.DiplotypeRow.model_fields`, `just_dna_format.vocab.VALID_RECOMMENDATION_STRENGTH`,
`just_dna_format.vocab.VALID_EVIDENCE_LEVELS`, `just_dna_format.base.SHARED_VOCABULARIES`
(`direction`, `clin_sig`), `just_dna_compiler.compiler._TABLE_DUPE_KEYS[DiplotypeRow]`,
`just_dna_compiler.hints.REDUNDANCY_BEARING`, `just_dna_compiler.draft.authoring_requirements("diplotypes.csv")`.
