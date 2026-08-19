# variants.csv — one row per (variant, genotype): what this module says about someone carrying that call

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

`variants.csv` is the module's answer to *"the sample's call at this locus is X — what do I tell the
reader?"* One row is one **(locus, genotype) pair** plus the prose conclusion for it. It is the only
table whose rows a consumer joins directly against a VCF genotype, and the only lead table that
carries the general annotation axes (clinical significance, direction, effect size, callability,
quality floor). Its audience is two-sided: an author decides zygosity and prose, and a consumer's
annotation engine matches sample calls against it row by row.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.spec.VariantRow` (`schema/src/just_dna_format/spec.py:380`) |
| Becomes | **two** parquets: `weights.parquet` (`compiler.py:5251`, `_build_weights`) and `annotations.parquet` (`compiler.py:5823`, `_build_annotations`). Both in `compiler.ARTIFACT_PARQUETS`; `weights.parquet` is a `LEAD_PARQUETS` member |
| Natural / dedup key | `(variant_key, genotype)`. Duplicates are an **error** (`_cross_validate_variants`, `compiler.py:869-873`) |
| Authored or machine-produced | **authored.** A drafter can stub rows; nothing machine-produced finishes one |
| Who writes it | the author; `clinvar_draft.draft_gene_panel` appends partial rows. No enricher pass ever rewrites a cell in it |
| Fact signature | **none.** Authored tables have no fact hash — see `integrity.py` for the six that do (`RESOLUTION_FACT_FIELDS`, `FREQUENCY_FACT_FIELDS`, …) |
| In `content_signature`? | **yes**, as parsed rows (`compiler.content_signature`, `compiler.py:3849-3887`) |
| In `artifact.digest`? | **yes**, via both parquets |
| In the attestation binding? | **yes** — `variants.csv` is in `compiler._INPUT_FILES` (`compiler.py:267`), so it is in `manifest.inputs[]` (raw bytes) *and* in `authored_input_entries` (newline-normalized) |

**What splits between the two parquets, and why.** `weights.parquet` gets the whole authored surface
*except* `gene` / `phenotype` / `category`; `annotations.parquet` gets exactly nine columns —
`rsid`, `variant_key`, `genotype`, `conclusion`, `negatives`, `module`, `gene`, `phenotype`,
`category`. So **`gene`, `phenotype` and `category` exist in the artifact only in
`annotations.parquet`**, and a consumer reading `weights.parquet` alone cannot see a gene symbol.
`annotations` is keyed `(variant_key, genotype, conclusion, negatives)`, first occurrence wins;
`genotype` joined that key in 0.6 (RM80) after a consumer reported the table was unique on nothing
joinable. It stores `genotype` as the **authored string** while `weights` stores a sorted allele
**list** plus a `phased` bool — S30, and it is the shape difference every consumer trips on. The
three grouping columns default to `""`, not null, in `annotations`.

## Who populates what

- **author** — `genotype`, `state`, `conclusion` (all three required); `negatives`, `priority`,
  `gene`, `phenotype`, `category`, `curator`, `method`, `direction`, `stat_significance`,
  `effect_size`, `effect_measure`, `effect_allele`, `flags`, `trait_efo_id`, `requires_callable`,
  `callable_from`, `quality_from`, `min_quality`, `actionability`, `weight`. Thirty-three authorable
  columns in total; run `table_requirements("variants.csv")` for the live list.
- **drafter** — `clinvar_draft` (`enricher/…/clinvar_draft.py:307-341`, `_row_cells`), from the
  ClinVar VCF snapshot: it states the identity columns, `gene`, `clin_sig`, `clinvar=True`,
  `phenotype`, a transcribed `conclusion`, and the folded `pathogenic`/`benign` boolean. It leaves
  **`genotype`** as `<<REPLACE>>` (zygosity is a judgement, not a datum), and leaves **`state`** as
  `<<REPLACE>>` wherever `clin_sig` gives no honest direction — `VALID_STATES` has no "uncertain"
  member, so a VUS row cannot state one. On a haploid contig it can decide `genotype` itself
  (`sole_expressible_genotype`). Re-runs are additive and never mutate an existing cell.
- **enricher pass** — **none writes into this file.** Every pass reads it and writes a *sidecar*:
  `enrich` → `resolution.csv`; `gene_metrics` / `gene_validity` / `clingen` → `gene_metrics.csv`,
  `gene_validity.csv` (gene set taken from the `gene` column); `gwas` → `gwas_effects.csv`;
  `frequencies` / `assertions` read `resolution.csv`, not this table. `acmg.check_acmg_sf` and
  `clinical.verify_clin_sig` **report** on `acmg_sf` / `clin_sig` and write nothing.
- **compiler-stamped** — `variant_key`, `authored_ident`, `locus_index`, `locus_count`. All four are
  `COMPILER_MANAGED`, absent from the authored surface, and materialized to `weights.parquet` only.
  They are *stamped*, not *refused*: an authored `variant_key="BOGUS"` or `locus_count=5` is
  **accepted and silently overwritten** by `_freeze_identity` (`spec.py:657-697`) — measured. (The
  positional PGx tables use `reject_compiler_filled` instead and *refuse*; `VariantRow` is the
  grandfathered exception.) `variant_key` is re-derived once more for a non-GRCh38 module
  (`_restamp_for_build`) and re-assigned on expansion.
- **registry-stamped** — nothing in this table. The registry stamps `module_spec.yaml`'s identity
  block (`normalize.IDENTITY_AUTHORITY_KEYS`) and re-signs; it never edits a variant row. It does
  **recompile from these CSVs at publish** and discard your uploaded parquets.
- **nobody, ever** — `weights.parquet.likely_pathogenic` and `.likely_benign`. Parquet columns with
  no authored field behind them; the compiler writes the literal `False` (`compiler.py:5307`,
  `:5309`). `extra="forbid"` refuses either name in a CSV — measured. `False` on every row of every
  module ever compiled since 0.1.0 (S43). Read `clin_sig`.

**Cells no tool may fill even though it easily could** — `hints.REDUNDANCY_BEARING`
(`compiler/…/hints.py:79-110`) names the check that would go vacuous:

| Cell | Refusal reason | The check it would make self-confirming |
|---|---|---|
| `rsid` | `redundancy_bearing` | `resolution._verify` (rsid ↔ coordinate) + `identifiers.check_rsids` |
| `chrom`, `start` | `redundancy_bearing` | `resolution._verify` — and for an rsid-only row `_verify` never runs at all, so filling it moves the row from *honestly unverified* to *verified against whatever filled it* |
| `ref` | `redundancy_bearing` | `enricher.sequences.verify_reference_alleles` (authored ref vs the genome) |
| `alts` | `redundancy_bearing` | the allele-membership check; `alts` is a resolution fact inside `artifact.digest` |
| `clin_sig` | `redundancy_bearing` | `enricher.clinical.verify_clin_sig` (authored call vs ClinVar's) |
| `acmg_sf` | `redundancy_bearing` | `enricher.acmg.check_acmg_sf` (authored flag vs the ACMG SF list) |
| `effect_allele` | `intent_bearing` | nothing checks it — only the author knows which allele the claim is about |

`ATTESTATION_BEARING` holds no `variants.csv` column; it is `provenance_quote` /
`provenance_regex`, which live in `studies.csv`. A `lookup_variant` / `lookup_identifier` result that
would fill one of the above comes back `applied: false` with the `refusal` string — pass both
through verbatim; the refusal is the output.

## What moving this table moves

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row | **moves** | n/a (none) | **moves** | **dropped** — module un-closed |
| edit an authored cell (`conclusion`) | **moves** | n/a | **moves** | **dropped** |
| edit a *stamped* cell (`variant_key`, `locus_count`) | unchanged | n/a | unchanged | unchanged — the value is overwritten at load |
| reorder rows | **unchanged** | n/a | **moves** | **dropped** |
| blank an already-blank optional column | unchanged | n/a | unchanged | unchanged |
| rewrite the file with CRLF terminators | unchanged | n/a | unchanged | **unchanged** (RM82 normalizes `\r\n`→`\n` in the binding only) |
| move a value between `defaults:` and the row (`curator`/`method`/`priority`) | unchanged | n/a | unchanged | binding moves (the yaml/CSV bytes changed) |
| delete the file and re-derive it (re-run `draft-panel`) | **moves** | n/a | **moves** | **dropped** |
| recompile under a newer toolchain | unchanged | n/a | **may move** | unchanged |

Measured on `reference_examples/hfe_hemochromatosis` with format/compiler 0.6.1: baseline
`content_signature sha256:44ad4449…`, `artifact.digest sha256:6c6e103d…`, binding
`sha256:99d2dc1b…`. A reversed row order gave `44ad4449… / 83635ace… / 15589d7a…` — content identical,
digest and binding both moved. A `csv.DictWriter` rewrite (CRLF) reproduced all three byte for byte.
A recompile with nothing touched reproduced all three.

1. **Inside `content_signature`?** Yes. It is an authored table, so its rows are hashed as parsed —
   `model_dump(mode="json", exclude_none=True)`, sorted, so the signature is **order-independent** and
   blind to CSV formatting and to an unset optional column. Two things are folded in first:
   `module_spec.yaml`'s `defaults:` (`_resolve_spec_defaults`, RM37) and the declared `genome_build`
   when non-default. The four stamped columns are `exclude=True` on the positional tables but
   **`VariantRow`'s `variant_key`/`authored_ident` are grandfathered *into*** the signature
   (`base.py:297-305`) — a known inconsistency, not a precedent; `locus_index`/`locus_count` use
   `stamped_identity_field` and stay out.
2. **Inside `artifact.digest`?** Yes, through both parquets. The digest **preserves authored row
   order** where `content_signature` does not, which is why a pure reorder moves one and not the other.
3. **Does an edit un-close the module?** Yes, immediately and for any byte change other than line
   endings. `variants.csv` is an authored input, so `module_binding(authored_input_entries(spec_dir))`
   moves and `record_verification` drops the whole `manifest.verification` block including the closure —
   measured above. The converse asymmetry is worth knowing: an `authorship:` append to
   `module_spec.yaml` un-closes a module while moving no identity at all.
4. **Part of the §5.1 canary?** No — the canary is *content unmoved + a **fact** signature moved*, and
   this table has no fact signature, so it can never produce that reading. It can produce canary **row
   2** (content unmoved, digest moved) by a bare row reorder. `MODULE_LIFECYCLE.md` § 5.1 says row 2 is
   reachable "by exactly two routes — a delete-and-re-derive, and a toolchain change"; a reorder is a
   third, and unlike those two it also moves the binding, which is the signal that separates them.

## Required to exist

`variants.csv` is optional (RM2) — a PGx, PRS or binning module carries none and that is correct. What
it drags in when present:

- **`studies.csv` becomes mandatory.** Every row is a claim; the PMID is its receipt. A study must
  carry the *same* identity shape its variant row got — coordinate-keyed variant, coordinate-keyed
  study — or the compiler reports an orphan.
- **A header-only `variants.csv` validates and compiles.** Measured: `validate_spec` returns
  `valid=True`, the compile succeeds, and **no `weights.parquet` and no `annotations.parquet` are
  written at all** (`compiler.py:4326-4332` guards on `if variants`). The manifest then reports
  `variant_count: 0`, `fully_resolved: true`, `resolution_subjects: 0` — the RM44 vacuous-flag shape.
  Delete the file rather than shipping an empty one.
- **`resolution.csv` is what makes it joinable.** 341 of the 381 authored rows in the reference corpus
  are **rsid-only** (38 coordinate-only, 2 both) — measured across the nine examples that carry the
  table. Without a resolution table those rows compile with `chrom=None` and join to no VCF by
  position; the compiler emits `UNJOINABLE_PHRASE` ("have no chrom+start") and the registry's
  `is_trusted` facet keys off it.

## The columns that carry judgement

- **`genotype`** — the required cell a drafter cannot fill. Slash-separated, **alphabetically sorted**
  for unphased (`G/A` is a load error; `A/G` is right), a pipe for phased, a single allele on a haploid
  or homoplasmic contig. `*` is a legal member since RM59.
- **`state`** — required, closed vocabulary, and it has no "uncertain" member. A VUS has no honest
  `state`; that is why the drafter stubs it rather than guessing.
- **`conclusion`** — the reader-facing prose, and part of `annotations.parquet`'s key. Two rows at one
  locus with different conclusions is legitimate poly-effect data, not a duplicate.
- **`weight`** — a magnitude with **positive = protective** and, without `module_spec.yaml`'s
  `weighting:` block (RM92), no declared scale, method or unit. Sign-checked only against a stated
  axis; see Gotchas.
- **`direction` / `state`** — orthogonal axes, not two spellings. `state` is the legacy required
  column; `direction` is the 0.3 axis. `effective_direction` derives one from the other *at read time*
  and the compiler **does not materialize the derivation** — the parquet column is a pure passthrough.
- **`effect_allele`** — which allele `direction`/`weight`/`effect_size` are *about*. `intent_bearing`:
  nothing can infer it and nothing checks it. Blank means the orientation of every magnitude on the row
  is unstated.
- **`requires_callable` / `callable_from`** — "the *absence* of this variant is the informative call"
  and "here is where the proof of callability lives". A pointer, never an expression. A bare `DP` is
  unqualified, and `INFO/DP` is the cohort's depth and says nothing about this sample.
- **`quality_from` + `min_quality`** — **both or neither**, enforced by a model validator
  (`spec.py:652-670`); half a floor is a validation error, measured. Inclusive floor; an unevaluable
  floor is *unknown*, never satisfied.
- **`clin_sig`** — the four-tier axis, and the only place the likely/definite distinction survives.
- **`acmg_sf` / `actionability`** — tri-state flag and closed vocabulary feeding a consumer's
  disclosure policy. `actionability` is **closed** despite `ACTIONABILITY_SEED`'s name — measured, a
  novel value is refused.
- **`clinvar` / `pathogenic` / `benign`** — genuinely tri-state in the parquet (nullable Boolean).
  `None` is "unstated", `False` is "the curator stated not-pathogenic". Do not collapse them.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **`weight` has never been authored, anywhere.** Measured over all 16 reference examples: the column
   is present in 4 modules (`hboc_palb2`, `hfe_hemochromatosis`, `par_boundary`, `shox_par1`), which
   between them hold 42 rows, and **all 42 cells are blank**. Thirteen other columns are in the same
   state corpus-wide — `priority`, `negatives`, `curator`, `method`, `stat_significance`,
   `effect_size`, `effect_measure`, `effect_allele`, `flags`, `acmg_sf`, `actionability`,
   `quality_from`, `min_quality`. So there is **no worked example of any of them**. If you author one
   you are the first, and the sign convention below is why that matters.
2. **The sign check keys on the axis, so withholding the axis buys silence.** The four warnings at
   `compiler.py:882-889` fire only on `state == "risk" | "protective"` or
   `direction == "risk" | "protective"`. A row with `state: significant` and a weight of any sign gets
   **no** sign check. `direction` is never filled from `state` in the artifact — the derivation exists
   as a read-time property (`effective_direction`) and `_build_weights` writes `v.direction` raw — so a
   `state`-only module has a null `direction` column and dodges half the check by construction.
   Measured: `state=risk, weight=1.5` warns twice (once per axis) when `direction=risk` is also set.
3. **A homozygous genotype at an indel locus can never be contradicted.** `resolution.hosting_verdict`
   is three-valued, and step 7 returns `None` for any genotype naming fewer than two distinct alleles —
   one string has no frame to be relative to. Measured: `hosting_verdict("T/T", "AGAG", "AG")` is
   `None`, so a wrong hom genotype at an indel produces **no warning and no strict error**. At a
   substitution locus it is `False` (`hosting_verdict("T/T","G","A")`). Also `None`: either side
   symbolic, or same-length different-content. And a resolution row with no `alts` returns `True`
   unconditionally (step 1). **`skills/create-module/SKILL.md` currently promises "a warning normally,
   an error under strict" for any genotype not drawn from `{ref} ∪ alts` — that is wrong for the
   homozygous and undecided cases.**

   > 🚧 **ROADWORKS — the genotype/allele cross-check has a hole you cannot see from its output.**
   > **Current state.** Re-confirmed: `hosting_verdict` withholds — returns `None`, so no warning and
   > no strict error — for a homozygous genotype, for a symbolic allele on either side, for
   > same-length different-content alleles, and for a resolution row with no `alts` (which returns
   > `True` outright). The withholding is *correct* under the house three-valued rule; the problem is
   > that a green compile is indistinguishable from a checked one.
   > **Expected state.** Nothing here is going to change — one string has no frame to be relative to.
   > What is missing is any surfaced count of *how many* genotypes went unchecked.
   > **Guard.** At an indel locus, check your homozygous genotypes by hand against `ref` and `alts`
   > before compiling. Do not read "no genotype warnings" as "every genotype was compared".
4. **A one-to-many rsID becomes rows the author never wrote, and they are well-formed** (S33 / RM87).
   K authored genotypes × N loci = K×N rows; only the member whose alleles can carry the genotype
   asserts anything. Measured on `hboc_palb2`: 16 authored rows → **18** weights rows and 18
   annotations rows, 4 of them expansion members over 2 authored rsIDs — ClinVar reciprocal
   duplication/deletion pairs (`rs587776418` at `16:23624054` as both `T→TTA` and `TTA→T`). A genotype
   written for the duplication lands beside the deletion's `ref` as a **reference homozygote asserting
   pathogenic**. This cost a consumer 3,762 false pathogenic findings across two panels, caught before
   rendering. The row-level predicate is **`locus_count > 1`**, not `locus_index` — which is `0` on a
   non-expanded row *and* on every expansion's first member. And gate on
   `manifest.compilation.expanded_keys`: `locus_count` defaults to `1`, so a module compiled with no
   resolution reads "nothing expanded" when the honest answer is "nothing was checked".
5. **`likely_pathogenic` and `likely_benign` are always `False`, and no author can change that** (S43).
   Not authorable (`extra="forbid"` refuses the name — measured), hardcoded `False` in the parquet, read
   by nothing, unwritten since 0.1.0. Filling or removing them is major-only, so this is permanent for
   the 0.x line. `clinvar_draft` folds `likely_pathogenic` into `pathogenic=True` deliberately (0.3
   compatibility, P8) — so `manifest.stats.pathogenic_count` counts **both** tiers. Facet on `clin_sig`.
6. **`variant_count` is not the row count, and neither is it the parquet row count.** It is
   `len({variant_key})` over the **authored** rows. Measured on `hfe_hemochromatosis`: 13 authored rows,
   12 distinct keys (`rs1800562` carries two genotypes), `variant_count: 12`, `weights_rows: 13`. On an
   expanded module the parquet has *more* rows than either. `pathogenic_count` counts authored rows too.
7. **A genotype the module never states is a subject with no answer, and the check only fires at a site
   you started.** `_check_genotype_coverage` (`compiler.py:2176`) warns per reason — reference
   homozygote missing, heterozygote missing — but **only at sites authoring two or more genotypes**, and
   **only in `validate_spec`**, in front of resolution. It never demands an alt/alt pair, never guesses
   a reference, and skips any site whose genotypes are not diploid nucleotide pairs (which is how MT and
   non-PAR Y stay out with no contig list). Measured on `hfe_hemochromatosis`: two warnings, 2 genotypes
   at 1 site missing a heterozygote and 2 genotypes at 2 sites missing the reference homozygote — in a
   shipped flagship example.
8. **The callability quartet is a claim, not a mechanism.** `requires_callable` /
   `callable_from` / `quality_from` / `min_quality` are read by **no consumer** (see below). Authoring
   them is still right — they are the only place a module can state where it stops applying — but do not
   assume they gate anything today. And do not state `min_quality` against `QUAL` on a
   `requires_callable` row: QUAL's sign flips with the record (VCF §1.6.1.6), so on the reference record
   a consumer must read to prove the absence, a *high* QUAL says the position is probably variant. The
   compiler warns (`_check_quality_inversion`, RM57) and deliberately does not refuse. Prefer `FORMAT/GQ`.
9. **`*` is not a symbolic allele and neither is `.`** (RM59 / RM58). `*` is legal in `genotype` only —
   measured: `effect_allele="*"` is refused — sorts first (`*/A`, not `A/*`), asserts *unobservable*, and
   is dropped from both sides of `hosting_verdict` before comparison so it never reads as a
   contradiction. `alts="."` asserts *no alternate exists* and is an identity defect: it folds into
   `derive_variant_key`, so `alts=.` and an empty cell describe one monomorphic site under two keys.
10. **A symbolic allele without its length loads and then vanishes.** `<DEL>/A` passes the model —
    measured — and the compiler warns and **drops the row** under `best_effort` (reverse will not
    re-emit it), refuses under `--strict`, and refuses in both modes if the drop would empty the table.
    So a green `best_effort` compile can quietly ship a smaller module. Give every symbolic allele its
    length: `<DEL:1500>`, `<CNV:TR:30>`.
11. **Coordinates are 1-based VCF POS — never subtract one.** `chrom` folds `chr`/`CHR` and `M`/`chrM`
    to `MT` (measured); an alt contig, scaffold or patch is refused, and the message names the other
    build when it can (RM48), because those rows arrive by pasting from a GRCh37 VCF.
12. **A GRCh37 module is keyed by coordinate, not by VRS.** `_restamp_for_build` re-derives every
    `variant_key` off GRCh38 and warns the keys will not join against GRCh38-keyed data; `genome_build`
    is recorded verbatim and **not honored** — the compiler is GRCh38-bound (RM15).
13. **A re-draft over an existing `variants.csv` never mutates a row.** Enricher 0.6.3 widened
    `multi_allelic_rsids`, so a panel drafted earlier holds one rsid-only row where two coordinate rows
    belonged; re-running adds both and leaves the stale one, which then carries the mislabelled
    expansion. 0.6.4's `_superseded_rsid_rows` **names** them ("N row(s) already in variants.csv
    identify by rsID alone …") and deletes nothing — that deletion is the author's call (S41/S45).

## What does not exist

- **No fact signature, and there should not be one.** Fact hashing exists to make a machine-filled and
  a human-filled derived table hash equal. This table is authored; `content_signature` is its identity.
- **No `callable_element` and no `quality_element`** (RM54). `callable_from` can name a multi-valued
  field (`FORMAT/AD`) and no module does; a `variants.csv` column is the most expensive addition this
  format makes. Both names are held in `vocab.RESERVED_NAMES_0_4` so they survive the one-way door, and
  authoring either is refused.
- **No grammar on `ref` / `alts`** — eleven columns across six models — and adding one stays refused: it
  would reject `N`, which is real, and break P3 for a module already carrying an odd cell. Only
  `genotype`, `effect_allele` and `HaplotypeRow.allele` have one.
- **No `SVLEN` column** — the length rides inside the allele token, because SVLEN is `Number=A` and a
  scalar column cannot describe `alts=<DEL:5>,<DUP:9>`.
- **No `##ALT=<ID=…>` mechanism, no named aliases, no IUPAC codes.** CPIC's `R`, `DELTCT` and
  `AAAGGGGCG(2)` notations are unexpressible. **No per-sample coverage, depth or quality, ever** — the
  three-state call is derivable from standard VCF fields, so the module holds pointers and the consumer
  holds the obligation.
- **The expansion will not be filtered.** Refused with a reason: `alts` comes from a source publishing
  submitted alleles, so a genotype not fitting a locus is at least as often a gap in the source as a
  module defect — and dropping the member would change what `reverse_module` reads back, which P7
  forbids. The contract paragraph plus `locus_count` is the answer instead.
- **`resolve_with_ensembl=False` is not a "skip Ensembl" switch.** It disables *all* resolution,
  injected `resolution.csv` included, and compiles every row with `chrom=None` **successfully**. A
  rename was proposed upstream and **refused** — the compiler has no network branch, so a
  `--no-ensembl` flag would assert something false. `compile_module` pins it `True`; the pin is permanent.
- **`unique_rsids` reaches no manifest.** `variant_stats` computes it (`compiler.py:3804`) and `Stats`
  (`manifest.py:164-172`) has no field for it, so it is dropped. It surfaces in
  `validate_module`'s stats dict and in the registry's `SpecStats` only.

## Consumption today

**`just-dna-lite` / `just-dna-pipelines` is the real consumer, and it reads both parquets.**

- `annotation/hf_modules.py:553-574` — `scan_module_table`, the single `pl.scan_parquet` for module
  tables; `MODULE_TABLES = ["annotations","studies","weights","sources"]` at `:36`.
  `annotation/hf_logic.py:222-249` — `_lead_join_strategy`: non-null `chrom` → join by **position**;
  else by `rsid` + `genotype`; else refuse.
- `hf_logic.py:351-401` — position path: semi-join on `(chrom, start)`, then left join on
  **`["chrom","start","genotype"]`**. `ref` is *not* a join key — it is kept under a suffix and used as
  a filter (`ref_module.is_null() | ref_module == ref`), discards logged.
- `hf_logic.py:333-342` — rsid path: left join on `["ID","genotype"]` vs `["rsid","genotype"]`, VCF
  `ID` exploded on `;` first. `hf_logic.py:139-148` — genotype matching is polars **list equality**; the
  VCF side is sorted unconditionally (`io.py:154-194`), the module side is not re-sorted.
- `report_logic.py:460-534` — `annotations.parquet` join, three eras: 0.6 on
  `["variant_key","genotype"]` with **no dedup** (deliberate, to keep poly-effect rows); 0.5 on
  `variant_key` after `.unique(keep="first")`; 0.3 on `rsid` after the same. `_genotype_key_expr`
  (`:450-457`) rebuilds the string key from the weights list **and reads `phased`**.
- Fields taken from `annotations.parquet`: only `gene`, `category`, `phenotype` (`report_logic.py:446`).
  `report_logic.py:282-321` — `_effective_direction` (`direction`, falling back to `state` + weight sign)
  and `_effective_clin_sig` (`clin_sig`, falling back to the booleans) — the read path S43 says is
  unaffected by the `likely_*` wart.
- `report_logic.py:331-367`, `:922`, `:1001-1003` — arithmetic on `weight`: sign, `abs`, colour
  intensity, sort, and a **`sum(weight)` "Net weight" headline**. `report_logic.py:695-756` — the view
  model reads `weight`, `genotype`, `rsid`, `state`, `direction`,
  `clin_sig`, `pathogenic`, `benign`, `clinvar`, `gene`, `ref`, `alts`, `conclusion`, `chrom`, `start`,
  `locus_count`, `locus_index`, plus `negatives`, `flags`, `priority`, `method`, `stat_significance`,
  `effect_size`, `effect_measure`, `effect_allele`, `trait_efo_id` as pass-through display strings.
  Template: `templates/longevity_report.html.j2:605-668`, including `locus_count > 1`.
- `restoration.py:266-334` — hom-ref restoration; requires `chrom,start,ref,genotype`, anti-joins loci
  with more than one `ref` spelling, and **filters `locus_count.fill_null(1) <= 1`** at `:327-328` —
  the RM87 predicate in production use.
- `vcf_export_logic.py:191-219` — joins on `["chrom","start","ref","alt"]` with
  `.unique(subset=join_cols)` (arbitrary winner) and **`genotype` excluded from the key** (it is in
  `_FORMAT_COLUMNS`, `:19`) — a genotype-blind key, different from the annotation engine's.
- `module_compiler/cli.py:38-42` — reads `weights.parquet` `chrom` only, counts nulls to warn about
  unresolved coordinates.

**The registry never opens a parquet.** Everything variant-shaped on a card comes from
`manifest.stats`: `CardStats` (`models/api.py:12-22`) → `variant_count`, `study_count`, `gene_count`,
`genes` (truncated to 3, `catalog.py:29`), `categories`, `clinvar_count`, `pathogenic_count`,
`benign_count`, filled at `catalog.py:241-249`. Search facets on `gene` and `category` via side tables
populated from `manifest.stats.genes`/`.categories` (`db/repository.py:663-668`, `:1003-1016`); the
`is_trusted` / `positionally_joinable` facets (`db/facets.py:44-194`) read the 0.6 resolution counters
and match the compiler's `UNJOINABLE_PHRASE`. At publish it **recompiles from your CSVs**
(`services/publish.py:536-573`, `resolve_with_ensembl=True`), gates duplicates on
`content_signature(spec_dir)` (`publish.py:506-516`, `:637-677`), and **discards every uploaded
parquet** (`publish.py:588-596`). No dataframe library is a dependency. Not filterable: trait, EFO id,
rsID, `acmg_sf`, `actionability`, `variant_count` range, weight scale.

**`just-prs` / `just-prs-mcp` read nothing from this table.** Zero hits for `just_dna_format`,
`weights.parquet` or `variants.csv` in either repo. Their weights notion is PGS-Catalog-native
(`just-prs/src/just_prs/scoring.py:44-80`, `effect_allele`/`effect_weight` from the Catalog scoring-file
spec) and their `trait_efo_id` is the Catalog's column, not a module's. The registry itself documents
the disjointness (`models/api.py:146-148`: `gwas_effects` "is **not** a substitute for the authored
`weight` … `weight` is positive-is-protective while a GWAS beta is positive on its effect allele").

## Blanks for just-dna-lite

- **Evaluate the callability quartet, or say you do not.** `requires_callable`, `callable_from`,
  `quality_from` and `min_quality` are read by nothing — grepped individually; `quality_from` and
  `min_quality` do not appear in consumer code at all, only in docs. The only quality gate is genome-wide
  and module-blind (`module_config.build_quality_filter_expr:91-121`, applied once at normalization).
  Today a `requires_callable` row's reference conclusion is asserted with no proof of callability, which
  is exactly the "not screened" reported as "screened negative" the normative contract forbids;
  `restoration.py:35-40` acknowledges it. A reader could withhold that row's conclusion, or evaluate the
  pointer and the floor and mark the row *unknown* rather than dropping it.
- **Account for no-calls separately from silence.** `io.py:154-194` maps `GT="./."` to an **empty
  list**, so the row fails the list-equality join and vanishes — indistinguishable in the report from
  "the module says nothing here". Worse, `restoration.py:239-244` builds `called_sites` from
  `select("chrom","start")` without inspecting GT, so a `./.` record counts as *called* and suppresses
  restoration at that exact site. Nothing counts, marks or logs either case. A reader could emit a
  third state and a count.
- **Make the genotype match phase-aware, or refuse a phased row loudly.** The join is polars list
  equality; the VCF side is `.list.sort()`ed unconditionally and the module side is not, so an authored
  `A|G` matches **nothing**, silently. `phased` is read at exactly one place
  (`report_logic.py:453`) and the annotation engine deliberately does not read it
  (`hf_logic.py:127-131`). `v1_port/runner.py:246-286` has the same hole on the authoring side: it splits
  on `/` only, so a phased genotype becomes one token and the membership check passes vacuously.
- **Use `locus_index`, or drop it.** It is read into the view model (`report_logic.py:751`) and never
  rendered or branched on. `locus_count` is used correctly in restoration; the annotation and reporting
  paths that *count* and *classify* rows do not gate on it, which is the half of S33 that produced 3,762
  false findings.
- **Read `acmg_sf` and `actionability`.** Neither is read anywhere. They are the two columns a module
  offers a disclosure policy, and a reader has no way today to separate an incidental secondary finding
  from a requested one.
- **Fix the 0.5 annotations dedup, or state the loss.** `report_logic.py:528-530` dedups on
  `variant_key` alone with `keep="first"` while the docstring at `:488` names the 0.5 identity as
  `(variant_key, conclusion, negatives)` — so a poly-effect variant in a pre-0.6 artifact silently
  loses its second annotation's `gene`/`phenotype`/`category`.
- **Say what `weight` is on.** `sum(weight)` becomes a "Net weight" headline (`report_logic.py:1001-1003`)
  across modules whose scale and method are declared nowhere unless `module_spec.yaml` carries
  `weighting:` (RM92, `WeightingInfo` at `models/api.py:112-128`). No reference example authors a weight
  at all, so the headline has never been exercised against real data; combining two modules' weights
  without reading `weighting` is arithmetic on unlike units.

## Ask the live schema

Never write a column list or a vocabulary from this file — everything above that is a *value* is
stamped "format 0.6.1" and drifts. Ask:

```
list_tables()                              # which table a finding belongs in at all
describe_table("variants.csv")             # every column, type, vocabulary, pick-list,
                                           #   plus redundancy_bearing / attestation_bearing
table_requirements("variants.csv")         # always / any_of / defaulted / optional — read all four
authoring_reference()                      # every vocabulary, generated from the field markers
get_template("variants.csv")               # a header row you can start from
lint_rows("variants.csv", "<csv text>")    # per-row findings without touching the disk
```

Then: `validate_module(spec_dir, strict=True)` → `enrich_module` → `compile_module(spec_dir, out,
strict=True)`. Read the **warnings on a green run** — the genotype-coverage gap, the expansion
sentences, the sign-convention lines and the symbolic-allele drops are all warnings, and every one is a
finding a consumer will otherwise inherit.
