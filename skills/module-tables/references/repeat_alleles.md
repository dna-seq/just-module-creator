# `repeat_alleles.csv` — what a repeat count means, for a locus that has no coordinate

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

One row per **band of repeat counts** at one tandem-repeat locus, plus one sentinel for "no count was
supplied". It answers: *the consumer's caller reported N copies of motif M at gene G — what does that
mean?* The module holds **no measurement**; the count arrives at query time from ExpansionHunter,
adVNTR or another span genotyper, and this table is only the lookup that turns it into a phenotype
(`binning.py:11-15`, "Data-agnostic (design north star)").

Its audience is a clinical-threshold author: HTT CAG, FMR1 CGG, DMPK CTG, ATXN* CAG. It is one of
**four** binning kinds subclassing `binning.MeasureBinRow` — the others are `activity_phenotype.csv`
(activity score), `copynumbers.csv` (copy number) and `heteroplasmy.csv` (allele fraction). Everything
except `gene`/`repeat_unit`/`measure_kind` is inherited from that base, so most of what follows is
shared and is flagged where it is not.

## Identity card

| | |
|---|---|
| Model | `binning.RepeatAlleleRow` (`just_dna_format.binning`, `schema/src/just_dna_format/binning.py:548`), subclass of `binning.MeasureBinRow:237` |
| Parquet | `repeat_alleles.parquet` — registered in `compiler._TABLE_KINDS` (`compiler/src/just_dna_compiler/compiler.py:226`) and in `compiler.ARTIFACT_PARQUETS` |
| Natural / dedup key | `_KEY_FIELDS = ("gene", "repeat_unit")` (`binning.py:555`), **plus `trait_efo_id`**, added by `_bin_groups` (`binning.py:694`). **No coordinate anywhere.** |
| Dedup rule | **Not** in `compiler._TABLE_DUPE_KEYS` (`compiler.py:236-239`): the duplicate rule for a binning kind is *overlap*, not key equality, so `draft.natural_key` returns `None` for it (`draft.py:204-214`) |
| Authored or machine-produced | **Authored, entirely.** No drafter, no enricher pass writes a cell (see below) |
| Who writes it | a human or AI co-author; `compiler.scaffold_module` creates the header + stub rows |
| Fact signature | **none.** It is not a derived-fact table, so there is no `repeat_signature` and no manifest block of its own. Its identity is `content_signature` + `artifact.digest`. |
| In `content_signature`? | **Yes** — `compiler.content_signature` loops `_TABLE_KINDS` (`compiler.py:3866-3886`) |
| In `artifact.digest`? | **Yes**, via `repeat_alleles.parquet` in `ARTIFACT_PARQUETS` |
| In the attestation binding? | **Yes** — `repeat_alleles.csv` is in `compiler._INPUT_FILES:267`, which `authored_input_entries:361` hashes |

## Who populates what

There is no `clinvar_draft`, `pgx_draft` or `clinpgx_draft` provider for this table. Grepping the
whole enricher for `repeat_alleles` returns two hits: the `template` CLI help string
(`enricher/src/just_dna_enricher/cli.py:837`) and the literature pass reading bin `pmid`s. **Every
authored cell here is the author's**, which is unusual and is the single most important fact about
authoring it: unlike `variants.csv`, nothing arrives pre-filled and nothing can be regenerated.

| Column(s) | Who |
|---|---|
| `gene`, `repeat_unit` | **author.** Required. The key. |
| `conclusion` | **author.** The only other required column. |
| `measure_min`, `measure_max` | **author.** The clinical judgement the whole table exists to record. |
| `measure_tiling` | **author**, and normally left empty — absence means the kind's default (`quantised` for `repeat_count`), never a value (`binning.py` `DEFAULT_MEASURE_TILING`). |
| `measure_kind` | **author**, defaulted to `repeat_count` and pinned by `_EXPECTED_KIND` (`binning.py:551`); a mismatch is rejected. |
| `unresolved` | **author.** `scaffold_module` stubs one `true` row for you (measured below). |
| `direction`, `phenotype`, `trait_efo_id` | **author.** Intent-bearing: only the author knows which trait these bins are about. |
| `clin_sig` | **author, and no tool may fill it** — `hints.REDUNDANCY_BEARING["clin_sig"] = "enricher.clinical.verify_clin_sig (authored call vs ClinVar's)"`. Filling it from ClinVar makes that comparison compare ClinVar with itself. |
| `pmid` | **author, and no tool may fill it** — `hints.REDUNDANCY_BEARING["pmid"] = "enricher.literature (authored pmid vs PubMed's record: LiteratureRow.exists)"`. `lookup_citation` reports a PMID with `applied: false`; carry that through as the provider's own answer. |
| `source_field`, `source_element` | **author.** Declarative pointers, not derivable — see the gotchas. |
| `module` (parquet only) | **compiler-stamped** at build (`compiler._build_table:461`, `{"module": module_name, …}`). Not an authored column; it exists so `reverse_module` can recover the module name from any parquet. |
| anything registry-owned | **n/a** — no `normalize.IDENTITY_AUTHORITY_KEYS` column lands on this table; identity lives in `module_spec.yaml`. |

`hints.ATTESTATION_BEARING` is `{provenance_quote, provenance_regex}` and **neither column exists on
this model** — those live on `StudyRow`. So this table carries a citation *pointer* and never an
attestation: it can say *which paper*, never *that anybody read it*. (Who the reader was is
`authorship`'s business, and may be an agent — `RM15`, 2026-08-20.) `describe_table` confirms the
split, reporting `redundancy_bearing` on `clin_sig` and `pmid` and `null` on the other thirteen
columns (run it; measured against format 0.6.1).

**Nobody, ever:** nothing. Every column is reachable by an author, and 14 of the model's **15**
fields appear filled somewhere in the two-module corpus (`measure_tiling` and `unresolved`-with-a-`pmid` are the
unexercised ones). Measured: `len(RepeatAlleleRow.model_fields) == 15`, all 15 authored, no stamped
columns — which is also what `describe_table` reports as 2 redundancy-bearing + 13 null.

## What moving this table moves

Measured, not asserted: `reference_examples/htt_repeat_expansion` copied to a scratch dir, mutated,
and recompiled with `compile_module(..., strict=False)` under format/compiler **0.6.1**. Hashes are
12-hex prefixes of the sha256. Baseline: `content_signature 86abcb8b1ec6`, `artifact.digest
de935e4b3418`, `module_binding 2841bad0b61e` (which matches the shipped `verification.json`, so the
module compiles **closed**).

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| recompile, nothing touched | same `86abcb8b` | n/a — none exists | same `de935e4b` | closed, `verification` published |
| **add a row** (split `40+` into `40–59` / `60+`) | **moved** `f3dcf4b2` | n/a | **moved** `78b50b02` | **un-closed** |
| **edit an authored cell** (`36–39` → `37–39`) | **moved** `b26b9dc0` | n/a | **moved** `a0703a45` | **un-closed** |
| **add a `pmid` column and fill it** | **moved** `9ddf56f1` | n/a | **moved** `88fca4d6` | **un-closed** |
| edit a provenance-only cell | **impossible** — this table has no `fetched_at`/`source`/`status` column | — | — | — |
| **reorder rows** | **same** `86abcb8b` | n/a | **moved** `cf6675e5` | **un-closed** |
| reformat: `HTT,CAG` → `"HTT","CAG"` | same `86abcb8b` | n/a | same `de935e4b` | **un-closed** (binding `1cb32a8a`) |
| rewrite `\n` as `\r\n` | same | n/a | same | **stays closed** (binding unchanged — RM82) |
| declare `measure_tiling: quantised` (the kind's own default; semantically a no-op) | **moved** `05942b65` | n/a | moved | un-closed |
| append `authorship:` to `module_spec.yaml` | same `86abcb8b` | n/a | same `de935e4b` | **un-closed** (binding `817e69fb`) |
| `reverse` → recompile | same `86abcb8b` | n/a | same `de935e4b` | **verification is gone** — reverse warns it holds no authority to declare someone else's authoring finished |
| delete the file and re-derive | **not possible** — nothing re-derives it | — | — | — |
| recompile under a newer toolchain | same | n/a | same *unless a parquet column set changes*; `manifest.compilation.compiler_version` moves and is outside both hashes | unaffected |

1. **Inside `content_signature`?** Yes. It is an authored table, hashed as parsed rows —
   `model_dump(mode="json", exclude_none=True)`, sorted by canonical JSON, so **row order and CSV
   quoting are invisible** to it (`integrity.py:189-250`). It has no fact signature and no manifest
   block, because it is not multi-producer; the fact-hash discipline (`integrity.fact_signature:256`,
   `FREQUENCY_FACT_FIELDS` and friends) exists for the enricher's sidecars and this is not one.
2. **Inside `artifact.digest`?** Yes, through `repeat_alleles.parquet`. The digest **preserves
   authored row order** — deliberately unlike `content_signature` — which is why reordering rows moves
   one hash and not the other. There is no provenance-only column here, so the usual "a timestamp no
   signature sees still moves the digest" trap does not have an instance on this table.
3. **Does an edit un-close the module?** Yes — `repeat_alleles.csv` is in `_INPUT_FILES`, so it is
   inside `authored_input_entries` and any byte change re-hashes `module_hash`. Since RM82 the bytes
   are newline-normalized, so a CRLF rewrite is forgiven and **re-quoting a cell is not** — measured
   above: identical content, identical digest, module un-closed. Note also that an `authorship:` append
   un-closes while moving no identity at all.
4. **Part of the §5.1 canary?** **No, and it cannot be.** The canary is *content unmoved + a fact
   signature moved* (`docs/MODULE_LIFECYCLE.md:260-299`). This table has no fact signature and no
   upstream source that could say something different, so it can only ever produce row 1 or row 4 of
   that table. Nothing about a repeat threshold can drift under you without an author editing it —
   which is also why nothing warns when the literature moves on.

## Required to exist

- **A module needs at least one recognised table; this alone is enough.** `htt_repeat_expansion` is
  three files: `module_spec.yaml`, `repeat_alleles.csv`, `verification.json`. No `variants.csv`, no
  `studies.csv`, no `resolution.csv`.
- **It drags in nothing.** `studies.csv` is required *iff* `variants.csv` is present, so a bin-only
  module compiles green under `--strict` citing nothing at all. Since 0.5.4 that produces a warning
  (`_check_binning_grounding`, `compiler.py:1383`), never an error.
- **`studies.csv` is accepted with no `variants.csv` and, since 0.6/RM47, with no subject either.**
  `fmr1_cgg_repeat/studies.csv` has exactly two columns, `pmid,conclusion`, and names no variant. That
  is the honest way to describe an ACMG technical standard which is about thresholds, not loci.
- Genome build: declared in `module_spec.yaml` and part of `content_signature` when non-default, but
  meaningless here — there are no coordinates for it to frame.

## The columns that carry judgement

- **`measure_min` / `measure_max`** — inclusive at both ends on every kind. `min == max` is a sharp
  value, a null bound is open-ended. These *are* the clinical claim; where 36 rather than 35 CAG
  becomes "reduced penetrance" is the most interpretive number the whole format carries.
- **`repeat_unit`** — part of the key, not decoration. "A count of 40 means nothing without the motif
  it counted, and two callers using different motif definitions produce incomparable numbers"
  (`htt_repeat_expansion/README.md`). Two motifs on one gene are two independent groups: measured,
  `HTT,CCG,6,26` beside `HTT,CAG,6,26` validates clean with no overlap.
- **`unresolved`** — the sentinel a consumer selects when *no count arrived*. It carries no bounds
  (enforced by `_validate_range`, `binning.py:400`). "Falling through to the lowest bin would report a
  possible expansion carrier as normal" — this is the dangerous failure this row exists to prevent.
- **`trait_efo_id`** — silently part of the group key. Overlap *across* traits is legal (pleiotropy);
  overlap within one is an error. Getting it wrong merges or splits groups invisibly.
- **`pmid`** — a pointer *only*. Population, `p_value_num`, `effect_size`, `provenance_quote` stay on
  `StudyRow`. "The bin row cites, the citation table describes."
- **`source_field` + `source_element`** — declarative addressing, never an expression. Together they
  say *which number in the VCF is the count this table bins*. Read the gotcha; a wrong `source_element`
  is the one error in this table that yields a confidently wrong clinical answer.
- **`measure_tiling`** — leave it empty unless you mean to depart from `quantised`. Writing the
  default explicitly is semantically a no-op and **moves `content_signature`** (measured).
- **`clin_sig`** — a closed VEP vocabulary, and redundancy-bearing. Note the oddity: this is a
  *threshold band*, not a variant, and `htt_repeat_expansion` still labels `27–35` as
  `uncertain_significance`. That is a convention, not a schema requirement.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **The scaffold's first row does not validate, by design.** `scaffold_module(kinds=["repeat_alleles.csv"])`
   writes two rows: one `unresolved=false` with both bounds empty, one `unresolved=true`. The first
   fails `_validate_range` with *"a resolved bin needs at least one of measure_min/measure_max"* until
   you fill it. Measured. Fill the bounds before running anything else.
2. **`source_element` is where a well-formed number becomes the wrong answer.** `FORMAT/REPCN` returns
   one count per allele and Huntington disease is dominant, so the clinical rule is *the longer of the
   two*. Before 0.6 there was nowhere to say that: "a consumer that averaged the pair, took the first,
   or took the shorter allele got a well-formed number and a wrong answer, and every offline gate
   passed — including `--strict`" (`htt_repeat_expansion/README.md`). Use `largest`, not
   `largest_alt`: `REPCN` has no reference element, and the longer allele may be the reference-length
   one. `vocab.ELEMENT_RULE_MEANINGS` (`vocab.py:240`) is the normative sentence per rule and is
   printed by `describe_table`.
3. **"Element" is not a VCF `Number` slot.** ExpansionHunter packs both alleles into **one** cell as
   `17/42`. A rule defined over `Number` would have had nothing to say about the case it was built
   for. That is also why the compiler stays *silent* on `REPCN` — it is ExpansionHunter's key, not the
   spec's, so this tier will not assert its cardinality. Point the same table at bare `AD` instead and
   two warnings fire at once (measured: an INFO/FORMAT collision warning and a *"points at a field the
   spec defines as multi-valued and states no element rule"* warning). **Silence on `REPCN` is not
   approval.**
4. **`largest` on a hemizygous contig.** FMR1 is on chrX; a male sample's `REPCN` carries one value,
   and fragile X in males is the flagship presentation. The rule is still correct (the greatest of one
   value is that value) but its old documentation said "the longer of the sample's two alleles", which
   is false there. Fixed in 0.6 (`fmr1_cgg_repeat/README.md` finding 1, D5-1) — the sentence now speaks
   of *the longest tract the record reports, whether the record carries one value or several*. Do not
   reason from ploidy.
5. **A measurement with a confidence interval can span several bins, and the policy is *withhold*.**
   `RUC` travels with `CIRUC`, whose missing upper bound means *unbounded* (VCF 4.4 §3), so a real
   `RUC=38, CIRUC=-5,5` spans `[33,43]` and crosses HTT's 35/36 **and** 39/40 thresholds: benign,
   uncertain and fully penetrant, with no honest answer among them. Until the policy vocabulary lands
   (RM56), a conforming consumer **withholds** — and *withholding is not the `unresolved` row*, which
   means no measurement was available and is a different claim. The warning fires once per table
   whenever any group has ≥2 bins; both worked examples carry it.
6. **The `unresolved` sentinel is documented as mandatory and is not enforced at compile.** The
   schema docstring's heading reads "**`unresolved` (T1) is mandatory**" while its own next sentence
   says a table *can* state it. Measured: delete the sentinel from `htt_repeat_expansion` and
   `validate_spec` returns `valid=True` and `compile_module(strict=True)` succeeds with no mention of
   it. The only warning lives in `hints._check_bins` (`hints.py:578-584`), i.e. in `lint_rows` — a tool
   an author may never run. **Run `lint_rows` on this table; `validate_module` will not catch this.**
   *Two* sentinels for one key group **is** a hard error (`compiler.py:3199-3206`).
7. **The sentinel in both worked examples sits in a different group from the bins.** HTT's bins carry
   `trait_efo_id=MONDO_0007739`; its `unresolved` row leaves the column blank, so the overlap message
   names `('HTT','CAG','MONDO_0007739')` while the sentinel-count check names `('HTT','CAG',None)` —
   measured. FMR1 has no `trait_efo_id` column at all. Whether a consumer grouping by
   `(gene, repeat_unit, trait_efo_id)` should find the blank-trait sentinel is **not established**
   anywhere; no consumer implements the lookup, so nothing has decided. Fill `trait_efo_id` on the
   sentinel to match its bins if you want the question not to arise.
8. **`repeat_count` bins must NOT touch — by default only.** Under the kind's default `quantised`
   tiling, a shared endpoint is a real overlap and a **hard error**: measured, `[36,40]` beside
   `[40,∞)` refuses with *"both select a phenotype for a measurement in the overlap"*. Since 0.6 that
   is a default and not a law — `measure_tiling: continuous` flips it, and the group is *read* as
   continuous without being asked if it carries any fractional bound. Any doc that states "integer
   bins must not touch" flatly is describing the pre-0.6 rule. **Checked 2026-08-20:** the skill's body was correct and keyed the
   rule on `measure_tiling` as 0.6 does; only its beginner summary row stated it flatly, and that row
   was fixed before the skill was split. `module-curate` and this dossier now agree.
9. **A fractional bound silently changes the rules for the whole group, and then invents gaps.**
   Measured: change one bound to `35.5` and the module still compiles, but you get *"tiling inferred
   … so this group was read as continuous"* plus **three new coverage-gap warnings** for
   `(26,27)`, `(35,35.5)` and `(39,40)` — intervals that were perfectly tiled a moment earlier.
   The inference runs one way only (fractional ⇒ continuous; integral implies nothing) and it
   announces itself. An explicit `quantised` beside a fraction **stands**, and warns instead.
10. **A hole of exactly one grid step is invisible, and RUC is a Float.** Under `quantised` the gap
    check only reports a hole wider than one (`binning.py`, `is_gap = hole > 1 + 1e-9`). Measured:
    `[0,0] [1,1] [2,2] [3,∞)` validates clean with **no** gap warning, and a measured `2.4` matches
    nothing at all. VCF 4.4 §3 types `RUC` as a **Float**, so this is not hypothetical — it is what
    the RM55 warning on every quantised repeat table is about. Do not read *"no coverage gap"* as
    *"every measurement lands somewhere"*.
11. **`quantised`'s step is hardcoded to 1 and there is no way to state another.** Right for repeat
    counts; a limit elsewhere. There is no `measure_step` column and it is deliberately deferred.
12. **A separator slip in `measure_kind` is accepted and canonicalised.** Measured: `repeat-count`
    loads, compiles and is stored as `repeat_count` (RM95 — before that fix the raw spelling reached
    `content_signature`). Not a trap any more, but do not conclude the column is strict about form.
13. **The grounding warning counts bins, not rows.** `4 of 4 bin(s) state a threshold and the module
    records no grounding evidence at all` — the sentinel is excluded, and a single `pmid` anywhere in
    `studies.csv` silences the whole message. HTT is **deliberately left uncited** so the corpus keeps
    an example of the gap; do not copy it as a template.
14. **`reverse` drops the closure.** Round-tripping is a fixed point on both hashes (measured:
    identical `86abcb8b` / `de935e4b`) and the reversed CSV differs only in column order and quoting —
    but `verification.json` is not in the artifact, so the reversed spec is **open** and warns as such.

## What does not exist

- **No coordinate columns, and that is a known gap rather than a property of the thing.** The
  compiler's own comment used to claim these tables are unjoinable "which is a property of what they
  describe"; 0.6 corrected it as false (`compiler.py:1130-1147`). VCF 4.4 §5.6/§5.7 make a tandem
  repeat a locus with published coordinates, so "a consumer holding an ExpansionHunter or `<CNV:TR>`
  VCF has to annotate a gene symbol for themselves to reach our HTT row." Adding `chrom`/`start`
  is **RM65**, deferred pending a real repeat-caller VCF, and it carries an RM87 obligation (the
  reverse writer hardcodes `locus_index = 0`).
- **No way to state a multi-motif allele — RM66, deferred.** VCF 4.4 §5.7 lets one `<CNV:TR>` allele
  encode several motifs (`RUS=CAG,TG,CAGG`). HTT's `(CAG)n(CAA)(CAG)` interruption structure and
  FMR1's AGG interruption pattern are both real, both published as affecting outcome, and both
  unsayable: `(gene, repeat_unit)` binds one count to one motif, and two motifs read as two unrelated
  groups. FMR1 records the limitation in a `studies.csv` row (Nolin 2015) rather than pretending.
- **No policy column for a spanning measurement — RM56, deferred.** Its grain (per table or per row)
  is deliberately undecided. Widening the *measurement* into an interval was refused outright: that
  would put a measurement in the module.
- **No `bin_evidence.csv` join table.** Refused: it would have to key on the thresholds, and they are
  floats — "re-authoring `40` as `40.0` orphans the evidence with nothing able to notice."
- **`StudyRow`'s provenance columns will not be copied here one at a time.** Refused: it would restate
  the bin inside its own evidence. So a bin can name a paper and never attests a reading of it.
- **No sixth `measure_kind` for a continuous repeat count.** Refused as the wrong axis (P5) — tiling
  and kind are independent questions, and folding them is a product rather than a sum.
- **`measure_tiling` cannot be derived from the rows with no column.** Refused: absence of a fractional
  value implies nothing, so it would read the ambiguous table one way, silently, with no way to correct
  it.
- **No `measure_step`.** A full-cost authored column nobody has asked for.
- **5-HTTLPR `S`/`L` does not belong here.** They are not nucleotides — that is the symbolic-allele
  gap (RM5), not something to smuggle into a count.
- **Forensic microvariant notation does not belong here.** `TH01 9.3` means nine repeats plus three
  bases; it is an allele *name*, not the decimal 9.3, and never a numeric bound.
- **No repeat drafter, in any tier.** Nothing publishes repeat thresholds in a machine-readable form
  this ecosystem consumes.
> ⚠️ **CHECK — requiredness has a fourth shape here, and no tool reports it.**
> **Current state.** `authoring_requirements` publishes three shapes — `always`, `any_of`,
> `defaulted` — and the bounds rule on a binning row is none of them. What the model actually
> enforces is a **disjunction over two columns conditioned on a third**: `unresolved=true` means
> both `measure_min` and `measure_max` must be **empty**, and `unresolved=false` means at least the
> lower bound must be present. That constraint lives in the validator and is invisible to
> `table_requirements` / `describe_table`, which will list both bounds as merely `optional`.
> **Expected state.** There is no field-level flag that could carry it, so it will keep arriving as
> a validation error rather than as a requirement. Read the bounds rule out of this file, not out of
> the requirements call.

- **No `gene`/`trait_efo_id` currency check.** `enricher.identifiers.check_identifiers` reads
  `variants.csv` only (`identifiers.py:520-525`), so a retired gene symbol or a stale MONDO id on a bin
  row is never questioned.

## Consumption today

**Nothing bins a measurement. Not one consumer implements the lookup this table was designed for.**

| Site | What it does |
|---|---|
| `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/module_config.py:498` | `repeat_alleles` is in `LEAD_TABLES`, so a directory holding `repeat_alleles.parquet` **is** a module — discovery and the HF publisher key on this list |
| `.../module_config.py:515-519` (`LEAD_TABLE_CSVS`) | derives `repeat_alleles.csv` as the authored table whose row count the registry's enrichment ceiling counts |
| `.../module_config.py:520-533` (`find_lead_table` / `has_lead_table`) | probes `repeat_alleles.parquet` to answer "is this a compiled module" |
| `.../annotation/hf_modules.py:157-233` (`_find_lead_table`) | the fsspec twin; sets `lead_table="repeat_alleles"`, `weights_url=None` |
| `.../annotation/hf_logic.py:222-250` (`_lead_join_strategy`) | classifies it `unsupported` — no populated coordinates, no `rsid`+`genotype` |
| `.../annotation/hf_logic.py:302-304` | **raises `UnsupportedLeadTable`** and the module is skipped with the reason logged |
| `just-dna-lite/webui/src/webui/state.py:6014`, `6043-6050` | `_authored_row_count` reads the CSV's line count for the registry `/check` routing decision |
| `just-dna-marketplace/src/just_dna_registry/specfiles.py:60` | `repeat_alleles.csv` is a recognised spec file, carried through storage |
| `.../services/upgrade.py:155` | maps it to `RepeatAlleleRow` so `--trim` can drop unknown columns on an old version |
| `.../db/repository.py:663`, `db/schema.py:76` | `version_genes` is the gene facet — populated from `manifest.stats.genes` |

So: **discoverable, publishable, storable, upgradable, and un-annotatable.** The bin rows travel
end-to-end and no code path ever compares a number to `measure_min`. There is no `REPCN` reader, no
`source_element` implementation, and no `unresolved` fallback anywhere in `just-dna-lite` — grepping
the consumer for `REPCN`, `source_element`, `RUC` and `ExpansionHunter` returns zero hits outside
comments. `just-prs` and `just-prs-mcp` do not mention the table at all.

## Blanks for just-dna-lite

- **Implement the bin-a-measure lookup — one code path for all four binning kinds.** Unread today:
  every column of every binning table. The rule is fully specified in `binning.py` (group on
  `_KEY_FIELDS` + `trait_efo_id`; select the greatest `measure_min ≤ x`; compare **in float32**, never
  with an epsilon; a missing measurement selects the `unresolved` row and never the lowest bin). What
  breaks today: `hf_logic._lead_join_strategy` classifies the whole family `unsupported` and
  `annotate_vcf_with_module_weights` raises `UnsupportedLeadTable`, so a published HTT or FMR1 module
  is installable and produces no annotation at all.
- **Read `source_field` + `source_element` instead of hardcoding a field.** Unread: both columns. A
  reader could extract `FORMAT/REPCN`, split ExpansionHunter's packed `17/42` cell, apply `largest`,
  and bin it — the module already states all of that declaratively. What breaks today: nothing reads
  the pointer, so any future annotator will hardcode a field name and silently take the wrong element
  on a dominant locus, which is the exact wrong answer RM54 was built to prevent.
- **Withhold on a spanning confidence interval, and say so distinguishably from `unresolved`.**
  Unread: `CIRUC`/`CICN` on the consumer side, and the format's stated placeholder policy. A reader
  could report *four* states (bin matched / no bin matched / measurement absent / measurement spans
  bins) rather than three. What breaks today: no consumer exists to get this wrong yet — which is
  exactly why the state should be in the report-card shape from the start rather than retrofitted.
- **A binning module's genes reach the catalog card as of compiler 0.6.6.** `manifest.stats.genes`
  came from `variants.csv` alone until then, and the shipped HTT manifest reads `gene_count: 0,
  genes: []` — verified in `data/interim/allcheck/htt_repeat_expansion/manifest.json`, so
  `registry_search(gene="HTT")` cannot find *that published version*. **Fixed in compiler 0.6.6** (upstream **RM121**): `module_stats` takes the gene facets over every authored table, `variant_stats` keeps its `variants.csv` promise, and a module already published carries the stats its compile wrote — recompile and re-publish to be findable by gene. Re-measured on `cyp2c19_star_alleles`: `gene_count: 1, genes: ['CYP2C19']`.
- **Check bin `pmid`s at revalidation.** `registry/services/revalidate.py:130-141` (`gather_pmids`)
  reads `studies.csv` only. Since 0.6 a threshold's citation may live *only* on the bin row — the
  case `fmr1_cgg_repeat`'s README says it probed — and such a module's PMIDs are never verified by
  `revalidate --check-pmids`. The enricher's literature pass already reads both sites via
  `compiler.binning_citations` / `load_binning_rows` (`enricher/literature.py:761-764`), so the two
  halves of the ecosystem disagree about where citations live.

## Ask the live schema

Never write a column list, a vocabulary or a requirement from this file — all of it is generated from
live pydantic models and drifts every release. Everything quoted above is **as of format 0.6.1 /
compiler 0.6.1 / enricher 0.6.4**.

```
describe_table("repeat_alleles.csv")     # columns, descriptions, vocabularies, redundancy_bearing,
                                         # and source_element's per-rule `notes`
table_requirements("repeat_alleles.csv") # always / any_of / defaulted / optional
                                        #   (but see the CHECK below — it cannot express the
                                        #    bounds rule)
authoring_reference()                    # the whole schema, incl. vocabulary_notes
get_template("repeat_alleles.csv")       # header-only CSV in the model's own field order
lint_rows("repeat_alleles.csv", <text>)  # overlap, gaps, tiling notices, deprecations,
                                         # AND the missing-sentinel warning nothing else reports
validate_module(spec_dir, strict=True)
```

CLI equivalents: `just-dna-compiler describe repeat_alleles.csv`,
`just-dna-compiler reference`, `just-dna-enricher template repeat_alleles.csv`.
