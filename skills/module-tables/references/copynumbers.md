# `copynumbers.csv` — whole-gene dosage → phenotype, as a range table the consumer measures against

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

One question, asked of an author who knows a gene's dosage matters: **for each copy-number range of
this gene, what does it mean?** SMN1 at 0 copies is spinal muscular atrophy; CYP2D6 at 0 copies has
nothing to metabolise with whatever its star alleles say. The table is pure annotation — a lookup
declaring `[measure_min, measure_max] → conclusion` — and the module holds **no measurement**. The
consumer supplies the copy-number call at query time and the table never sees a sample
(`binning.py:11-15`, "Data-agnostic (design north star)").

It is one of four kinds subclassing `binning.MeasureBinRow`, alongside `activity_phenotype.csv`
(`activity_score`), `repeat_alleles.csv` (`repeat_count`) and `heteroplasmy.csv`
(`allele_fraction`). Everything in *The columns that carry judgement* except `gene`,
`modifier_gene`, `modifier_cn` and `modifier_copy_number` is shared with those three; everything in
*Gotchas* about tiling applies to `repeat_alleles.csv` verbatim and to the other two by contrast.

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.binning.CopyNumberRow`, subclass of `binning.MeasureBinRow` → `base.AuthoredModel` (`extra="forbid"` + reserved-namespace guard) |
| Parquet | `copynumbers.parquet`. Registered in `compiler._TABLE_KINDS` (`compiler.py:225`), in `ARTIFACT_PARQUETS`, and in `LEAD_PARQUETS` — it can **lead** a module with no `variants.csv` at all |
| Natural / dedup key | Bin group = `_KEY_FIELDS` + `trait_efo_id` = `(gene, modifier_gene, effective_modifier_copy_number, trait_efo_id)`. There is **no** entry in `compiler._TABLE_DUPE_KEYS` — a duplicate resolved bin is caught as an *overlap* instead (`compiler.py:236-240`) |
| Authored or machine-produced | **Authored, entirely.** All 17 fields are authored (`authored_field_names(CopyNumberRow)` returns all 17; measured) |
| Who writes it | A human or AI co-author. No drafter, no enricher pass |
| Fact signature | **None.** Fact signatures exist only for the derived sidecars (`integrity.py:256-397`). This table's identity is `content_signature` over its raw authored rows |
| In `content_signature`? | **Yes** — `compiler.content_signature` loops `_TABLE_KINDS` (`compiler.py:3868-3872`) |
| In `artifact.digest`? | **Yes**, via `copynumbers.parquet` in `ARTIFACT_PARQUETS` |
| In the attestation binding? | **Yes** — `copynumbers.csv` is in `_INPUT_FILES`, so it is inside `authored_input_entries` (`compiler.py:267-272`, `:386`) |

## Who populates what

Every column here is **author**. There is no drafter and no pass. Measured: `grep -rn
"copynumbers\|CopyNumberRow" enricher/src/` returns **nothing**; `compiler/draft.py` has no
`copynumbers` reference beyond `DRAFTABLE`, which only gives you a *template*.

- **author** — `gene`, `measure_min`, `measure_max`, `measure_tiling`, `conclusion`, `direction`,
  `clin_sig`, `phenotype`, `trait_efo_id`, `unresolved`, `source_field`, `source_element`, `pmid`,
  `modifier_gene`, `modifier_copy_number`, `modifier_cn` (deprecated). `measure_kind` is
  **defaulted** to `copy_number` and pinned by `_EXPECTED_KIND`, so writing anything else is an
  error — it is a column you never fill.
- **drafter** — none. `draft.DRAFTABLE` includes `copynumbers.csv`, but only `draft.template`
  applies: `get_template(csv_name="copynumbers.csv", stub=True)` emits `<<REPLACE>>` in `gene` and
  `conclusion` plus a pre-built `unresolved=true` companion row (`draft.py:295-323`). No source
  provider publishes this table. ClinVar, CPIC and ClinPGx drafters do not touch it.
- **enricher pass** — none writes here. One pass **reads** one column: `enrich_literature` collects
  `MeasureBinRow.pmid` through `compiler.load_binning_rows` and checks it against PubMed alongside
  `studies.csv` (`enricher/literature.py:683-770`, RM47). That is the only downstream check any cell
  on this table gets.
- **compiler-stamped** — no *column* of the model. The parquet gains a `module` column at build
  (`compiler._build_table`, `compiler.py:457-461`); it is not a model field, so authoring a `module`
  column in the CSV is refused by `extra="forbid"` (measured: `ValidationError` naming `module`).
  Nothing here uses `stamped_identity_field` — contrast `HeteroplasmyRow.variant_key`, which does.
- **registry-stamped** — none. `normalize.IDENTITY_AUTHORITY_KEYS` acts on `module_spec.yaml`, not
  on table cells (`compiler.py:720-721`).
- **nobody, ever** — none permanently unwritten, but `modifier_cn` is a column you should
  **stop** writing (deprecated 0.6, removed at 1.0).

**Cells no tool may fill, and why.** `describe_table("copynumbers.csv")` returns
`redundancy_bearing = {clin_sig, pmid}` and `attestation_bearing = []` (measured — this table has
neither `provenance_quote` nor `provenance_regex`, so `hints.ATTESTATION_BEARING` is empty here).
`lint_rows` emits, per column, `info: "<col> is left to the author on purpose: <checker> compares it
against a source, and filling it from that same source would make the check vacuous"` — measured on
a real file for both columns.

- `pmid` — the refusal is honest and load-bearing. `enricher.literature` asks PubMed whether the
  **authored** pmid resolves and reports the record's title; filling it from NCBI's id converter
  would compare NCBI with itself. Any lookup reports it as an advisory with `applied: false`.
- `clin_sig` — **the refusal is stated but the check behind it does not exist for this table.**
  `enricher.clinical.verify_clin_sig(variants: list[VariantRow], …)` takes `VariantRow` only
  (`enricher/clinical.py:221-235`), so a `clin_sig` on a bin row is never compared with anything. The
  advisory is keyed on a global map (`hints._flag_advisory_columns` intersects `REDUNDANCY_BEARING`
  with the model's columns) and over-promises here. Author it from independent reading anyway — but
  know that nothing will catch you.

## What moving this table moves

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| Add a bin row | **moves** | n/a (none) | **moves** | **un-closes** |
| Edit an authored cell (`conclusion`, `measure_max`, …) | **moves** | n/a | **moves** | **un-closes** |
| Edit a "provenance-only" cell | n/a — **this table has none.** No `fetched_at`, no `source`, no `status`. Every cell is content | | | |
| Reorder rows | **unchanged** (rows are sorted by canonical JSON, `integrity.py:222-226`) | n/a | **moves** (digest preserves authored row order) | **un-closes** (byte hash) |
| Re-run the producing pass | n/a — no pass produces it | | | |
| Delete the file and re-derive | n/a — nothing re-derives it. Deleting it deletes the table | | | |
| Recompile under a newer toolchain | **unchanged** | n/a | **moves** | **held** |
| `modifier_cn: 2` → `modifier_copy_number: 2` | **moves** | n/a | **moves** | **un-closes** |
| Add `measure_tiling: quantised` on a group already read as quantised | **moves** (a set optional column is no longer `exclude_none`'d away) | n/a | **moves** | **un-closes** |

**Measured, not asserted.** Two spec dirs differing only in which spelling of the modifier dosage
they use, compiled with `just-dna-compiler` 0.6.1:

| | `content_signature` | `artifact.digest` | `compilation.warnings` |
|---|---|---|---|
| `modifier_cn=2` | `sha256:73e1bfd73f531…` | `sha256:8fff116f5d0db…` | 4 |
| `modifier_copy_number=2` | `sha256:ec9fcc019fcd7…` | `sha256:2e4d266349ccc…` | 3 |

`effective_modifier_copy_number` is `2.0` in both, the bin group is byte-identical, the parquet's
`measure_*` columns are identical — and both identities move anyway, because `content_signature`
hashes `model_dump(exclude_none=True)` and the *column name* changed. **What this costs a published
module:** a registry keyed on `content_signature` treats the migrated version as new content, so a
content-dedup surface will not recognise it as the same table; the warning count in
`manifest.compilation.warnings` drops by one (the deprecation notice); and closure is lost. Measured
on a closed module: `close` bound `sha256:2a2c7f5150431…`, the one-column rename moved it to
`sha256:8d1e25c5ce9a9…`, and the next compile reported *"verification.json is stale … the spec has
been edited"* plus *"This module records no closure"*. **Migrate before you close, or re-close after.**
`reverse_module` does not migrate for you — it re-emits whichever column the parquet carries
(measured: reversing the new-spelling artifact reproduced `content_signature` exactly).

1. **Inside `content_signature`?** Yes, as an authored table — `compiler.content_signature` reads
   `variants.csv`, `studies.csv` and every present `_TABLE_KINDS` CSV. It has **no** fact-field
   constant because it is not a derived table; there is nothing deliberately left out, because there
   is no provenance column to leave out.
2. **Inside `artifact.digest`?** Yes. `copynumbers.parquet` is in `ARTIFACT_PARQUETS`, and the
   digest is a Merkle root over those bytes. Note the parquet materializes **both** modifier columns
   plus a null (measured: 18 columns, `modifier_cn` `i64` and `modifier_copy_number` `f64`, one null
   per row), so the spelling reaches the digest twice over.
3. **Does an edit un-close the module?** Yes — `copynumbers.csv` is in `_INPUT_FILES`, hence in
   `authored_input_entries`, hence inside `module_binding`. Any value change drops the whole
   attestation and the closure with it (`compiler.close_module`). Since RM82 the bytes are
   newline-normalized, so a CRLF→LF rewrite alone does **not** un-close it. (For contrast: an
   `authorship:` append in `module_spec.yaml` un-closes a module while moving no identity at all —
   the yaml is in the same binding.)
4. **Part of the §5.1 canary?** **No, and it cannot be.** The canary is *content unmoved + a fact
   signature moved* = the upstream source said something different. This table has no fact
   signature, no producing pass and no upstream source, so it can never produce row 3 of
   MODULE_LIFECYCLE §5.1's table. Every move it makes is row 4, *somebody edited the module* — which
   is the honest reading for a hand-authored threshold table. The delete-and-re-derive that the
   canary needs has no meaning here: deleting this file deletes the annotation.

## Required to exist

- **Nothing requires it.** Every table kind is optional (RM2 composition); a module includes only
  the kinds it uses.
- **It drags in nothing.** `studies.csv` is required iff `variants.csv` is present — measured: a
  spec of `module_spec.yaml` + `copynumbers.csv` alone compiles clean under `--strict`.
- **`module_spec.yaml` still needs `module.name`, `module.title`, `module.report_title` and
  `module.description`** — measured, a spec missing the last two fails to compile even though
  `content_signature` still computes.
- **It can lead a module.** `copynumbers.parquet` is in `LEAD_PARQUETS`, so a spec with no variants
  at all is a legal, discoverable, publishable module. See *Consumption today* for what that buys.
- **A resolved bin needs at least one bound.** `_validate_range` refuses a row that is neither
  `unresolved=True` nor carrying a `measure_min` or a `measure_max`. `authoring_requirements` reports
  both bounds as merely `optional`, so this constraint is invisible to `table_requirements` — read
  it here or trip over the model validator.

## The columns that carry judgement

- **`measure_min` / `measure_max`** — inclusive on **both** ends, on every kind. `min == max` is a
  sharp dosage (`[0,0]` = exactly zero copies), `min < max` a range, a null bound open-ended. There
  is **no** `copy_number` column, deliberately.
- **`measure_tiling`** — the 0.6 axis (RM55). `quantised` = a grid; `continuous` = dense. **Empty
  means the kind's default, never a value** — which for `copy_number` is `quantised`. This is the
  single column that changes what every other bin in the group *means*.
- **`conclusion`** — the only required column besides `gene`. It is what a report prints.
- **`modifier_gene` + `modifier_copy_number`** — a *second locus read in context*, and a
  **group-key** column, not a measurement. On SMN1/SMN2 the tiled axis is SMN1's copy number and the
  SMN2 dosage is the condition. Set together or both null; the pair is enforced.
- **`pmid`** — the boundary citation (RM47, 0.6). *Where 36 rather than 35 becomes "reduced
  penetrance" is a clinical judgement drawn from a specific paper.* A **pointer only**: population,
  effect size and the quote stay in `studies.csv`. It is the one cell here with a real downstream
  check.
- **`unresolved`** — the sentinel a consumer selects when **no** copy number was called. The
  contract is that a missing measurement selects this row and **never the lowest or reference bin**:
  no CN ⇒ not "2 copies". It carries no bounds (enforced). Its `conclusion` is the whole content of
  the row: "what to say when nothing was measured."
- **`source_field` / `source_element`** — a declarative *pointer* at the VCF field the consumer
  extracts from, never an expression. `FORMAT/CN` and `INFO/CN` are **different numbers** — see
  Gotcha 6.
- **`clin_sig`** — routinely misread as verified. Nothing verifies it on this table.
- **`trait_efo_id`** — silently part of the bin group. Two bins that overlap under different
  `trait_efo_id` are legal (pleiotropy); two bins you *meant* to be one group but tagged with
  different trait ids will not be checked against each other at all.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **The two adjacent sharp bins everyone writes first answer nothing for a real caller.**
   `[0,0] [1,1] [2,2] [3,10]` is a legal quantised tiling and a measured `2.4` matches **no bin**.
   Measured on `reference_examples/cyp2d6_structural`: the module compiles green under `--strict`
   and carries the RM55 warning verbatim (*"copy_number bins here are tiled as whole numbers, but the
   field a consumer reads the measurement from (CN) is not a whole number in VCF 4.4"*). VCF 4.4 §7.2
   redefined `CN` to allow non-integer copy numbers, and §5.6 leaves the granularity undefined. **The
   coverage-gap check cannot see this hole**: under quantised tiling a hole is only reported when
   *wider than one step* — measured, `[0,0]` beside `[1,1]` returns `[]` from `validate_bins`, and the
   same pair declared `continuous` returns `coverage gap … no bin covers (0.0, 1.0)`. If your caller
   reports a segment mean rather than whole copies, write `measure_tiling: continuous` on **every row
   of the group** and let the bounds touch (`[0,1.5] [1.5,2.5] [2.5,]`).

2. **`modifier_cn` is deprecated and migrating it moves both identities and un-closes the module.**
   See *What moving this table moves* for the measured hashes. **Setting both is an error**, not a
   precedence rule (measured: `ValidationError`, *"two spellings of one dosage and exactly one may be
   set"*). Everything reads `effective_modifier_copy_number`, which coalesces with `is not None` and
   **never `or`** — SMN2 = 0 copies is a real dosage and a truthiness fallback would read it as
   unset (measured: `effective_modifier_copy_number == 0.0`).

3. **Each modifier group needs its own complete tiling and its own sentinel, and nothing tells you
   so.** Partitioning by `(modifier_gene, effective_modifier_copy_number)` fragments coverage. The
   SMN1 example in `docs/REFERENCE_EXAMPLES.md:161-167` states `[0,0]` for SMN2=3, `[0,0]` for
   SMN2=1, then `[1,1] [2,2] [3,]` and one sentinel — **all with the modifier null**. So the two
   SMN2-conditioned groups each hold a single bin and **no sentinel at all**, and the modifier-null
   group has no bin for 0 copies. Measured: `validate_spec` on that exact CSV reports the RM55/RM56
   warnings and the S19 grounding warning and **says nothing** about either problem. The sentinel
   check is asymmetric: `compiler._validate_table_kind` errors on *more than one* sentinel **per key
   group** (`compiler.py:3197-3207`), while `hints._check_bins` warns on *zero* sentinels **anywhere
   in the table** (`hints.py:578-585`). Neither notices a group with none. Edge coverage *below* the
   lowest bin is documented as out of scope: *"it would false-positive without a known domain floor."*

   > 🚧 **ROADWORKS — a closed top bin is a silent ceiling, and nothing checks the edges.**
   > **Current state.** The gap check runs **between** bins only. Nothing anywhere — compile,
   > validate or hint — looks above the highest bin or below the lowest, in either tiling. So
   > `[0,0] [1,1] [2,2] [3,4]` on an axis with no upper limit takes every CN of 5 or more and matches
   > **nothing**: not a bin, and not the `unresolved` sentinel either, because the measurement is
   > present. That is the "no matching bin" third state, which no consumer contract covers.
   > **Expected state.** An edge check would need a declared domain, and there is no column for one;
   > the below-lowest half is refused for exactly that reason and the above-highest half is simply
   > absent. Do not expect either to arrive.
   > **Guard.** Leave the top bin **unbounded** — blank `measure_max` — unless the axis genuinely
   > ends there, and say in `conclusion` what the open bin means. Check both edges by hand before
   > compiling; nothing else will.

4. **A fractional *bound* flips the group to continuous, and the compiler says it did. A fractional
   *modifier dosage* does not.** Measured: bins `[0,1.5] [1.5,3]` resolve to `continuous` with
   `inferred=True` and emit *"tiling inferred for key … measure_max is 1.5, which no quantised
   reading can hold"*; a group with `modifier_copy_number=2.5` and integral bounds stays `quantised`
   with `fractional=None`. `_fractional_values` deliberately reads only the bounds
   (`binning.py:728-757`), because letting the dosage vote produced a **legality flip** — one
   identical pair of bins refused at `2.0` and accepted at `2.5` — and **invented coverage gaps** on
   genuinely integral bounds. "It is a copy number too, so surely it counts" is named as the obvious
   wrong repair. The inference **runs one way only**: fractional-ness contradicts a stated grid;
   integer-ness contradicts nothing, since `[0,1] [2,3]` is what a continuous measure looks like when
   its author has only seen whole numbers.

5. **An explicit `quantised` beside a fractional value STANDS, and warns.** Measured:
   *"measure_tiling for key … is declared 'quantised' and the data contradicts it: measure_max is
   1.5, which is not a grid point. The declaration stands — nothing here overrides it either way."*
   Neither side silently wins. And two rows of one group declaring **different** tilings is an
   **error**, not a warning (measured: *"conflicting measure_tiling … got 'continuous' and
   'quantised'"*) — leave the column empty on the rows that do not state it; empty is absence, not a
   third answer.

6. **`FORMAT/CN` and `INFO/CN` differ by a factor of the ploidy, and a bare `CN` warns.** From
   `reference_examples/cyp2d6_structural/README.md`: *"INFO/CN is the allele-specific copy number and
   FORMAT/CN is the sample's total copy number … the two answers differ by a factor of the ploidy"*
   — and `FORMAT/CN` is silent. INFO and FORMAT collide on `DP`, `AD`, `ADF`, `ADR`, `MQ`, `AF` and,
   since 4.4, `CN`. **Qualify the namespace.** `source_element` then says *which* value when the
   field carries several — a closed set of named rules (`largest`, `largest_alt`, `smallest`, …),
   never an index, because `AD[1]` is the first line of an expression grammar.

7. **A duplicate row is reported as an overlap, not as a duplicate.** There is no `_TABLE_DUPE_KEYS`
   entry, so two identical resolved bins surface as *"overlapping bins for key (…)"* — check the
   group key first when that message surprises you. Two bins sharing a **lower** bound refuse under
   every tiling — but **not with the same message**, and the wording is the thing you will grep for.

   > ⚠️ **CHECK — the shared-lower-bound message is `continuous`-only.**
   > **Current state.** Measured: `[1,1]` beside `[1,3]` raises *"overlapping bins for key …"* under
   > `quantised` **and** under `activity_score`'s default `None`; only under `continuous` does it
   > reach *"bins with the same lower bound … the shared-endpoint rule (the higher bin owns it)
   > cannot separate them"*. `validate_bins`' own comment says so: *"Only reachable under continuous
   > tiling."*
   > **Expected state.** The **refusal** is universal; the **diagnosis** is not. Grep for
   > *"overlapping bins"* first, and only expect the lower-bound sentence on a table that declares
   > `measure_tiling: continuous`.

8. **RM56: a measurement can span several bins and there is no state for that.** A `CN` call travels
   with `CICN`, whose missing upper bound means *unbounded*, so a real measurement is an interval.
   The consumer contract has exactly three states — a bin matched, no bin matched, the measurement
   absent — and none of them is *the interval crosses two bins*. **The stated house default is
   withhold**, and withholding is explicitly *not* falling back to `unresolved`, which means no
   measurement was available and is a different claim. The warning fires once per table whenever the
   widest group holds ≥ 2 bins, in both modes, and **no authored edit clears it** — the policy
   vocabulary is deferred to 0.7 gated on a real CNV VCF.

9. **A `measure_kind` separator slip is accepted and canonicalised.** Measured: `measure_kind:
   copy-number` loads and stores `copy_number` (RM95, `binning.py:377-393`). Do not read that as
   licence — write the underscore.

10. **A float bound is compared in float32, not with an epsilon.** VCF 4.4 §1.3 makes every `Float`
    32-bit, so a VCF `0.3` arrives as `0.300000011920928955…` (above an authored `0.3`) and a VCF
    `0.9` as `0.899999976158142…` (below). The rule, stated on `measure_max`'s own description:
    narrow the bound the same way the measurement was narrowed and compare the two. **Neither bound
    is the safe one** and "narrow only the bound" loses rows. Author the decimal you mean.

11. **The grounding warning counts resolved bins only.** Measured on a 6-row table: *"5 of 5 bin(s)
    state a threshold and the module records no grounding evidence at all."* It fires only when the
    module has **no** `studies.csv` rows *at all* **and** some bin has no `pmid`. A bin carrying a
    `pmid` is not counted (S19, `compiler._check_binning_grounding`).

## What does not exist

- **No `copy_number` column.** A sharp dosage is `measure_min == measure_max`. Stated in the module
  docstring so nobody adds one.
- **No `measure_step`.** `quantised`'s step is **hardcoded to whole numbers**. Right for
  `copy_number`; a real limit elsewhere. A `measure_step` column *would* close it and is refused as
  "a full-cost authored column nobody has asked for" (P5's one-way door).
- **A sixth `measure_kind` (`copy_number_continuous`) was refused** — kind answers *what is
  measured*, tiling answers *how the axis is divided*; folding them is the overloaded-field
  anti-pattern (P5) and a product rather than a sum.
- **Moving `copy_number` into `_DENSE_KINDS` was refused.** One line, and it silently re-reads every
  published table with no notice and no way to say otherwise.
- **Deriving the tiling from the rows with no column at all was refused** — absence of a fractional
  value implies nothing, so it would read the ambiguous table one way, silently, with no correction
  path.
- **No retype of `modifier_cn`.** 1.0 inherits a **removal**, not a retype, which is what the
  parallel float column exists to buy. 1.0 also **removes the kind-keyed tiling defaults**
  (`ROADMAP_1_0.md:122`): *"If your `copy_number`/`repeat_count` bins are a genuine grid, state
  `measure_tiling: quantised` before 1.0 removes the default that assumed it."*
- **No `chrom`/`start`.** This table is not positional, so it is absent from
  `_POSITIONAL_TABLE_KINDS` and never joins `resolution.csv`. 0.6 **corrected the claim** that this
  is a property of what a copy number is: VCF 4.4 §5.6 has POS and `SVLEN` specify the interval a
  copy number is defined over, so the non-joinability is a **schema gap** (RM65), gated on a real CNV
  VCF and open for 0.7+. A consumer holding a `<CNV>` record at `22:42126400` has no column to join
  on and must annotate a gene symbol for itself.
- **No provenance columns.** No `fetched_at`, no `source`, no `status`, no `dataset`. Nothing here
  records where a bound came from except `pmid`.
- **No `requires_callable`.** That is `VariantRow`-only (RM70, open), so this table cannot state
  which loci a caller must be able to call — and a copy number from a seg-dup region like SMN1 is
  exactly the case that needs it.
- **No policy for an interval spanning bins.** RM56, deferred; see Gotcha 8.
- **No `verification.json` check records.** No enricher pass reads this table, so the attestation on
  a copy-number-only module holds a closure and an empty `checks` list.

## Consumption today

**Nothing annotates from this table. That is the finding.**

| Site | What it does |
|---|---|
| `/data/sources/just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/module_config.py:497` | `copynumbers` is in `LEAD_TABLES`, so a directory holding `copynumbers.parquet` **is** a module for discovery and for the HuggingFace publisher |
| `…/module_config.py:508-514` | `LEAD_TABLE_CSVS` derives `copynumbers.csv`, so the registry's enrichment ceiling counts this table's authored rows (it counted **zero** before the list was derived) |
| `…/module_config.py:519-533` | `find_lead_table` / `has_lead_table` probe `copynumbers.parquet` to answer "is this directory a module" |
| `/data/sources/just-dna-lite/webui/src/webui/state.py:6014-6017` | imports `LEAD_TABLE_CSVS` for `_authored_row_count`, which routes a module to `/check` vs `/validate` |
| `…/annotation/hf_logic.py:222-249` | `_lead_join_strategy` classifies a `copynumbers`-led module **`unsupported`** — "no per-variant key at all" |
| `…/annotation/hf_logic.py:302-304` | raises `UnsupportedLeadTable`; the per-module loop records and skips it |
| `…/annotation/cli_annotate.py:372-388` | prints `Skipped <module>: <reason>` from the run manifest |
| `/data/sources/just-dna-registry/src/just_dna_registry/specfiles.py:59` | `copynumbers.csv` in `TABLE_KIND_CSVS`, hence in `SPEC_DATA_FILES` and `SIGNATURE_INPUTS` — it is stored and re-split on download |
| `…/services/upgrade.py:154` | `CopyNumberRow` in `_ROW_MODELS`, so `offending_columns` / `trim_unknown_columns` run over it when replanning an old version |
| `…/db/repository.py:664` + `db/schema.py:128` | `version_genes` — the gene search index — is populated from `manifest.stats.genes` |
| `…/services/catalog.py:240-252` | the module card projects `variant_count`, `study_count`, `gene_count`, `genes`, `categories`, `clinvar_count`, `pathogenic_count`, `benign_count` — **all from `manifest.stats`** |
| `just-prs`, `just-prs-mcp` | nothing. `grep -rln "copynumbers\|copy_number"` returns no files |

Two consequences worth stating plainly, both measured on a `module_spec.yaml` +
`copynumbers.csv` module naming SMN1 and SMN2:

- `manifest.stats` reads **`variants.csv` only** (`compiler.variant_stats`, defined at
  `compiler.py:3792`, the gene set at `:3801`; `:5181-5191` is a *consumer* of its output, not the
  computation).
  Measured: `genes: []`, `gene_count: 0`, `variant_count: 0`, `study_count: 0`. `manifest.Stats` has
  no `table_rows` field, so the row count `validate_spec` computes never reaches the manifest.
  **Therefore `registry_search(gene="SMN1")` cannot find an SMN copy-number module** — the gene
  index is fed from `stats.genes`, and this table's genes are not in it.
- The full annotate path is: discovered → publishable → installable → **skipped by name** at
  annotation. `just-dna-lite` contains no `FORMAT/CN` read, no `INFO/CN` read, and no `copy_number`
  handling of any kind (`grep -rniE "FORMAT/CN|INFO/CN|copy.number"` over all `.py` returns nothing).
  So the consumer-side answer to *"does it read `CN` from `FORMAT` or `INFO`?"* is **neither, today**
  — the question is unanswered rather than answered wrongly, and `source_field` is a pointer no
  reader follows.

## Blanks for just-dna-lite

- **Implement the bin-a-measure lookup.** One code path serves all four binning kinds: *select the
  row with the greatest `measure_min ≤ x` within the group*, reading the group's **effective** tiling
  from `measure_tiling` (declared → else forced by a fractional bound → else
  `binning.DEFAULT_MEASURE_TILING[kind]`) rather than from `measure_kind`. Without it every binning
  module in the catalog is `UnsupportedLeadTable`, and an author who authors this table correctly
  gets a `Skipped` line.
- **Coalesce the modifier dosage in the parquet reader.** `effective_modifier_copy_number` is a
  Python **property**, not a parquet column: the file carries `modifier_cn` and
  `modifier_copy_number` side by side, one null (measured). A consumer that reads either column alone
  silently splits or drops a group. Contrast `HeteroplasmyRow.variant_key`, which RM43 promoted to a
  stamped field for exactly this reason — this pair did not get that treatment.
- **Decide `FORMAT/CN` vs `INFO/CN` and honour `source_field` / `source_element`.** They differ by a
  factor of the ploidy, and a module can already say which it means. Today nothing reads the pointer,
  so a correct annotation and a wrong-by-ploidy one are indistinguishable to the consumer.
- **Withhold on a spanning interval, and say so.** `CN` travels with `CICN` whose missing upper bound
  means unbounded. The stated house rule is withhold — not pick among the bins, and **not** fall back
  to `unresolved`, which is a different claim. A reader that quietly point-estimates makes RM56's
  deferral invisible.
- **Select the `unresolved` sentinel when no CN was called.** The contract is explicit that a missing
  measurement selects that row and never the lowest bin. There is no consumer implementing it, so
  today "no CN" and "2 copies" are the same output: nothing.
- **Feed the gene index from every table that names a gene.** `manifest.stats.genes` is
  variant-derived, so a copy-number module is invisible to `registry_search(gene=…)` and its catalog
  card reads 0/0/0. This is a registry-side ask as much as a consumer one, but the projection is what
  a reader sees.

## Ask the live schema

Never write a column list, a vocabulary or a requirement from this file — it is stamped
**format 0.6.1 / compiler 0.6.1 / enricher 0.6.4 / registry 0.18.2** (verified via
`importlib.metadata.version`) and drifts on every release. Ask:

```
list_tables()                                          # which table for which subject
describe_table(csv_name="copynumbers.csv")             # columns, categories, vocabularies,
                                                       #   redundancy_bearing, attestation_bearing
table_requirements(csv_name="copynumbers.csv")         # always / any_of / defaulted / optional
get_template(csv_name="copynumbers.csv", stub=True)    # header + <<REPLACE>> stubs + the
                                                       #   unresolved companion row
lint_rows(csv_name="copynumbers.csv", csv_text=…)      # overlap, gaps, tiling notices,
                                                       #   the deprecation notice, missing sentinel
authoring_reference(schemas=True)                      # the whole authored surface in one read
validate_module(spec_dir=…, strict=True)               # + the RM55 / RM56 / S19 warnings
compile_module(spec_dir=…, out_dir=…, strict=True)     # digest + content_signature
```

Two vocabularies you will want by name: `binning.VALID_MEASURE_KINDS` (this table is pinned to
`copy_number` by `_EXPECTED_KIND`) and `binning.VALID_MEASURE_TILINGS`. The per-kind defaults live in
`binning.DEFAULT_MEASURE_TILING`, derived from `_INTEGER_KINDS` / `_CONTINUOUS_GAP_KINDS` /
`_DENSE_KINDS` rather than restated. The refusal maps are `hints.REDUNDANCY_BEARING` and
`hints.ATTESTATION_BEARING` — the second is **empty for this table**.
