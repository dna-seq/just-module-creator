# activity_phenotype.csv — the metabolizer phenotype an activity score bins into

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

A per-gene lookup table: *given an activity score, which metabolizer phenotype*. It is one of the
four binning kinds, all subclassing `just_dna_format.binning.MeasureBinRow`, and it carries **no
measurement**. The score is computed by the consumer as `Σ activity(allele_i) × copies_i` over the
two phased allele-units (`docs/REFERENCE_EXAMPLES.md:191`) from a star-allele caller's diplotype;
this table only says where the boundaries are. The audience is a PGx author who has already written
`allele_function.csv` (allele → activity value) and needs to state the CPIC phenotype cut-points as
**data, editable by consensus, so the 2019 CPIC threshold shift is a data edit and not a code
change** (`docs/REFERENCE_EXAMPLES.md:206`).

It is the only binning kind whose axis this schema declines to describe at all — see the tiling
gotcha, which is where most of this file's value is.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.binning.ActivityPhenotypeRow` (`schema/src/just_dna_format/binning.py:425`), extending `MeasureBinRow` (`:237`) → `base.AuthoredModel` (`extra="forbid"` + reserved-namespace guard) |
| Parquet | `activity_phenotype.parquet` — registered in `compiler._TABLE_KINDS` (`compiler/src/just_dna_compiler/compiler.py:224`), 4th entry of `ARTIFACT_PARQUETS` (`:278`), and in `LEAD_PARQUETS` (`:308`) so it can lead a module |
| Group / dedup key | `_KEY_FIELDS = ("gene",)` **plus `trait_efo_id`**, joined in `binning._bin_groups` (`:687`). Overlap across different `trait_efo_id` is legal (pleiotropy) |
| Duplicate-row check | **none.** Binning kinds are deliberately absent from `_TABLE_DUPE_KEYS` — an exact duplicate resolved bin is caught as an *overlap*, duplicate sentinels by a separate rule (`compiler.py:236-241`) |
| Authored or machine-produced | **fully authored.** No drafter and no enricher pass writes a row here (see below) |
| Fact signature | **none.** Fact signatures (`integrity.fact_signature` and friends) exist only for the seven derived sidecars in `_FACT_TABLES`; this is an authored DSL table |
| In `content_signature`? | **yes** — `compiler.content_signature` (`:3848`) hashes `variants.csv`, `studies.csv` and every present entry of `_TABLE_KINDS` |
| In `artifact.digest`? | **yes**, via its parquet's bytes in `ARTIFACT_PARQUETS` order |

Parquet shape, measured on `reference_examples/cyp2d6_structural`: **15 columns = the 14 authored
fields + a compiler-stamped `module`**, authored row order preserved.

## Who populates what

Column by column. As of format 0.6.1 — run `describe_table` for the live list.

| Column | Who writes it |
|---|---|
| `gene` | **author.** Required. |
| `conclusion` | **author.** Required — the human-readable sentence for this bin. |
| `measure_min` / `measure_max` | **author.** The whole judgement of the table. |
| `measure_kind` | **author, but it has exactly one legal value.** Defaulted to `activity_score` and pinned by `_EXPECTED_KIND` (`binning.py:429`); the field carries its own one-member vocabulary `measure_kind_activity_score` rather than `VALID_MEASURE_KINDS`, because offering the full set would offer values this model rejects. |
| `measure_tiling` | **author — and on this kind the right answer is almost always to leave it empty.** See gotcha 2. |
| `unresolved` | **author.** `stub_template` stamps the sentinel row for you (`draft.py:278`, `_unresolved_cell` `:312`); nothing else ever writes it. |
| `direction`, `phenotype`, `trait_efo_id` | **author.** `direction` is a closed vocabulary (`neutral/protective/risk/unknown`) — an axis, not a magnitude. |
| `clin_sig` | **author, and no tool may fill it** — `hints.REDUNDANCY_BEARING["clin_sig"]` (`compiler/src/just_dna_compiler/hints.py:81`) registers it against `enricher.clinical.verify_clin_sig`, which compares the authored call against ClinVar's. Filling it from ClinVar makes that comparison compare ClinVar with itself. |
| `pmid` | **author, and no tool may fill it** — `REDUNDANCY_BEARING["pmid"]` = *"enricher.literature (authored pmid vs PubMed's record: LiteratureRow.exists)"*. A lookup reports the id with `applied: false` and its refusal; preserve both. |
| `source_field`, `source_element` | **author.** Declarative VCF pointers, never expressions. |
| `module` (parquet only) | **compiler-stamped.** Not on the model, so `extra="forbid"` refuses it in a CSV. |
| registry-stamped | **nothing.** `normalize.IDENTITY_AUTHORITY_KEYS` covers `module:` yaml keys, not table cells. |

**No drafter exists for this table.** `DRAFTABLE` (`draft.py:82`) includes `activity_phenotype.csv`,
but that is *template* draftability (`blank_template` / `stub_template`) and not a source provider.
Grepped every `append_rows` / `append_partial_rows` call in the enricher: `clinvar_draft` writes
`variants.csv` + `studies.csv`, `clinpgx_draft` writes `pharm_variants.csv`, and `pgx_draft` (CPIC)
writes `haplotypes.csv`, `allele_function.csv`, `diplotypes.csv` (`pgx_draft.py:505-509`) — **and
nothing else.** The recorded reason is in `enricher/src/just_dna_enricher/cpic.py:25-27`: CPIC's
`gene_result.activityscore` is an inequality *string* (`"≥3.0"`, `"n/a"`), *"so it does not drop
into `MeasureBinRow`'s numeric `measure_min`/`measure_max`. The raw string is carried and the
parsing left to a human, because guessing a bound from `≥3.0` means inventing the upper one."*
`pgx_draft.py:413-419` reports those as a warning bucket and drops the value.

**`attestation_bearing` is empty here.** `hints.ATTESTATION_BEARING` is exactly
`{provenance_quote, provenance_regex}` (`hints.py:72`), and neither column exists on this model —
those live on `StudyRow`. Nothing in this table asserts that anybody read anything — and on
`StudyRow`, where it does, the reader may be an agent provided the module says so (`RM15`).

**One enricher pass *reads* it and writes nothing to it:** the literature pass loads every binning
table through `compiler.load_binning_rows` (`compiler.py:1779`, called at
`enricher/src/just_dna_enricher/literature.py:761`) and collects the bin `pmid`s via
`binning_citations` (`:1811`) so they are checked alongside `studies.csv`. Since 0.6 a module with
**no** `studies.csv` but a `pmid` on a bin row is enrichable; before that the pass refused it.

## What moving this table moves

Measured, not asserted: `reference_examples/cyp2d6_structural` copied to a scratch dir and compiled
once per edit with `compile_module(strict=False)`, format/compiler **0.6.1**.

Baseline: `content_signature sha256:d8f5995255aafa80…`, `artifact.digest sha256:cb0f28939b0c5282…`,
`activity_phenotype.parquet sha256:2fa845748ec4…`, `manifest.verification` **present**.

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| Add a bin (sharp `[1.1, 1.1]`) | **moved** `aa633bb6…` | n/a — this table has none | **moved** `19f0e7d8…` | **dropped**; "verification.json is stale … the spec has been edited" |
| Move a bound (`2.25` → `2.3`) | **moved** `a16b28a4…` | n/a | **moved** `e8d1eddd…` | **dropped** |
| Reword a `conclusion` | **moved** `66da6ba7…` | n/a | **moved** `c1abd8a5…` | **dropped** |
| Strip every `pmid` | **moved** `ced5d7e4…` | n/a | **moved** `d680a646…` | **dropped** |
| Declare `measure_tiling: continuous` on every row | **moved** `fcaf82e6…` | n/a | **moved** `302dccd1…` | **dropped** (+ 3 spurious gap warnings — gotcha 2) |
| **Reorder the rows** | **unchanged** `d8f5995255aafa80…` | n/a | **moved** `841e5796…` | **dropped** |
| Omit a defaulted column entirely vs. writing its default | **unchanged** | n/a | **unchanged** (byte-identical parquet) | unchanged |
| `reverse_module` → recompile `--strict` | **fixed point** `d8f5995…` | n/a | **fixed point** `cb0f289…` | reverse warns it is dropping the attestation; the reversed spec is open |
| Re-running the producing pass | **no such pass exists** — nothing machine-writes this table | | | |
| Delete and re-derive | **not possible** — deleting the file deletes the annotation | | | |
| Recompile under a newer toolchain | unchanged (it hashes parsed rows) | n/a | **can move** — parquet bytes depend on the compiler/polars version | unchanged (binds authored bytes only) |

There is no provenance-only column on this table — no `fetched_at`, no `source`, no `status` — so
the "moves the digest and no signature" row that derived sidecars have has no instance here.

1. **Inside `content_signature`? Yes.** `compiler.content_signature` (`:3848`) parses every present
   `_TABLE_KINDS` CSV and hands the rows to `integrity.content_signature`, which normalizes with
   `model_dump(mode="json", exclude_none=True)` and sorts. Consequences worth knowing: a reordered
   file hashes **equal** (measured above), `2.50` and `2.5` hash equal, and an optional column left
   unset is omitted — which is why writing a default explicitly and omitting the column produce the
   identical signature *and* the identical parquet.
2. **Inside `artifact.digest`? Yes**, through `activity_phenotype.parquet`'s bytes. Row order is
   preserved in the parquet, which is exactly why a reorder moves the digest while leaving
   `content_signature` still — the two are different identities on purpose (a byte-reproducibility
   digest vs. a content-dedup key).
3. **Does an edit un-close the module? Yes, every time.** `compiler.authored_input_entries`
   (`:361`) hashes `_INPUT_FILES`, which includes every table-kind CSV, newline-normalized since
   RM82. Any edit to this file — including one that moves no identity, such as a row reorder —
   drops `manifest.verification` and raises *"verification.json is stale"*. This table is on the
   **authored** side of the binding; a re-enrichment of a derived sidecar is not.
4. **Part of the §5.1 canary? No, and it cannot be.** The canary reads *content unmoved + a fact
   signature moved* = the upstream source said something different. This table has no fact
   signature and no producing pass, so it can never occupy that row. Every move it makes is row 4
   of `MODULE_LIFECYCLE.md § 5.1` — *somebody edited the module* — which is honest: nothing
   upstream can change these bins, because nothing upstream writes them.

## Required to exist

- **Nothing requires this table**, and it requires nothing. `studies.csv` is required *iff*
  `variants.csv` is present (`compiler.py:3609`); the binning kinds are exempt, and the recorded
  reason is not "they carry their own evidence" — it is that `StudyRow` could only name a variant,
  so for a `(gene)`-keyed table the requirement would be **unsatisfiable rather than merely unmet**
  (S19 → RM47).
- A module must carry **at least one** recognized table (`compiler.py:3602`); this one satisfies it
  alone. **Measured**: a directory of `module_spec.yaml` + `activity_phenotype.csv` compiles
  successfully and produces a one-parquet artifact with no `weights.parquet`.
- If the module records **no** `studies.csv` rows at all *and* some bin has no `pmid`,
  `_check_binning_grounding` (`compiler.py:1383`) warns — measured on a solo module with the pmids
  stripped: *"activity_phenotype.csv: 4 of 4 bin(s) state a threshold and the module records no
  grounding evidence at all (no studies.csv rows, no bin pmid)"*, with the remedy naming
  `pmid` + a `studies.csv` row that since 0.6 need not name a variant. Warning in both modes.

## The columns that carry judgement

- **`measure_min` / `measure_max`** — the table. Inclusive at **both** ends on every kind:
  `min == max` is a sharp value, a null bound is open-ended. The score is a float64 parsed from
  your decimal while a VCF `Float` is 32-bit (RM62), so the *comparison* is the consumer's problem
  and the rule is stated on `measure_max`'s own description: narrow the bound to float32 the same
  way the measurement was narrowed, never use an epsilon.
- **`conclusion`** — required, and the only cell on the sentinel row that says anything.
- **`unresolved`** — the tri-state carrier. `true` = *no measurement was available*. It is **not**
  "the measurement matched no bin", which is a distinct third state the consumer must keep apart
  (`docs/SCHEMAS.md:273`, `:734`). A missing score selects this row and **never** the lowest or
  reference bin: no activity score ⇒ **not** Normal Metabolizer.
- **`pmid`** — grounds *this boundary*, which is a different question from what grounds the module.
  The rule is: **the bin row cites, `studies.csv` describes** (RM47). It carries a pointer only —
  population, effect size and the provenance quote stay in `studies.csv`. Redundancy-bearing.
- **`clin_sig`** — closed VEP vocabulary, redundancy-bearing. Rarely the right column on a
  metabolizer bin; `phenotype` + `direction` usually carry the meaning.

  > ⚠️ **CHECK — the redundancy advisory on `clin_sig` names a check that cannot run here.**
  > **Current state.** `hints.REDUNDANCY_BEARING` is keyed on a **bare column name**, with no model
  > attached, so `_flag_advisory_columns` prints the `clin_sig` advisory on every table that happens
  > to have that column — including this one. The checker it names,
  > `enricher.clinical.verify_clin_sig`, is driven from `variants.csv`: it walks `VariantRow`s and a
  > bin row is never handed to it. So the cell is advertised as cross-examined and is in fact
  > **never** compared with anything.
  > **Expected state.** Authoring it by hand is still right — the advisory's advice holds — but do
  > not treat a green compile as evidence that your `clin_sig` agrees with ClinVar on a binning table.
  > It was not checked. The same is true of `clin_sig`/`ref` advisories on the PGx tables.

## Gotchas

Ordered by how likely a first-timer is to hit them.

### 1. A shared endpoint is a hard error, and a hole is silent — the two rules are opposite here

`activity_score` is the **third answer** in `DEFAULT_MEASURE_TILING` (`binning.py:196`): not
`quantised`, not `continuous`, but `None`. It is in neither `_DENSE_KINDS` (`:184`) nor
`_CONTINUOUS_GAP_KINDS` (`:175`). What that buys, in `validate_bins` (`:951`):

- **Two adjacent bins may not touch.** `lo == prev_hi` with `dense == False` raises. Measured:
  editing the NM bin to `1.0–2.25` beside the IM bin `0.25–1.0` fails the compile with
  *"overlapping bins for key ('CYP2D6', None): [0.25, 1.0] and [1.0, 2.25] both select a phenotype
  for a measurement in the overlap"*.
- **An interior hole is never reported.** `is_gap = False` unconditionally (`:1067-1068`).

That combination is deliberate and it is what lets CPIC's real table author cleanly.
`reference_examples/cyp2d6_structural/activity_phenotype.csv` states `0.0–0.0 / 0.25–1.0 /
1.25–2.25 / 2.5–6.0` with **deliberate holes at 1.0→1.25 and 2.25→2.5**, and compiles with **zero**
warnings on this table (measured — the only two warnings on that module are `copynumbers.csv`'s
RM55/RM56 pair). The holes are real: scores are summed from per-allele values on a 0.25 grid, so
1.1 is not a measurement this gene produces.

**What it costs.** The schema does not know the step, so it cannot tell a real hole from a typo. A
bin written `1.35–2.25` instead of `1.25–2.25` strands every score of 1.25 with no finding at all.
`quantised` would not help: its step is hardcoded to 1 (`binning.py:1053-1061`), and there is no
`measure_step` column — that is a full-cost authored column nobody has asked for, deliberately
deferred. **Check your own boundaries against the grid; nothing else will.**

### 2. Declaring `measure_tiling` on this table invents findings

`measure_tiling` is legal on every binning kind, and `resolve_tiling` (`:791`) honours a declared
value over the kind's default. On `activity_score` that is a trap, and `resolve_tiling`'s own
docstring names it: reading a fractional activity score as continuous *"would invent findings rather
than reveal them"*. **Measured** — adding `measure_tiling: continuous` to every row of the reference
example produces exactly three new warnings:

```
coverage gap for key ('CYP2D6', None): no bin covers (0.0, 0.25)
coverage gap for key ('CYP2D6', None): no bin covers (1.0, 1.25)
coverage gap for key ('CYP2D6', None): no bin covers (2.25, 2.5)
```

…for intervals no activity score can land in. Note also that the *inference* path cannot reach this
table: a fractional bound moves a group off its default only where the default is `quantised`, and
this kind's default is `None` (`:836-842`). So the column here is a manual foot-gun and nothing
else. **Leave it empty.** Absence means the kind's default, never a value.

### 3. Capping the top bin strands everything above it, silently

The reference example writes the top bin `2.5–6.0` with the recorded reason that *"CPIC publishes
open-ended scores here as inequality strings (>=3.0), which the numeric bounds cannot hold — 6.0 is
the highest score its own diplotype table states."* `docs/REFERENCE_EXAMPLES.md:213` writes the same
bin **open**: `2.5,` with `measure_max` empty.

The open spelling is the safer one. `validate_bins` checks only *interior* holes between sorted
spans; there is no check above the highest bin or below the lowest (the docstring says edge coverage
below is a consumer-contract matter and would false-positive without a known domain floor). So on
the capped version a score of 6.25 — three `*1x2` copies is not exotic — matches **no bin**, and
nothing warns, in either mode. It is a legal table stating an unintended ceiling. If the source
publishes `≥3.0`, that is `measure_min=2.5, measure_max=` and not a number you picked.

- **`source_field` / `source_element`** — where the consumer reads the score from and which of that
  field's values it means. `source_element` is a closed set of **named rules**
  (`largest|largest_alt|smallest|smallest_alt|sum|sum_alt|annotated_alt|reference`,
  `vocab.VALID_ELEMENT_RULES:217`), never an index, because `AD[1]` is the first line of an
  expression grammar and Principle 1 refuses it. Each ranging rule comes in a pair: the bare name
  counts the reference element, the `_alt` name does not. Per-member prose lives in
  `vocab.ELEMENT_RULE_MEANINGS:240` and `describe_table` prints it.
- **`measure_tiling`** — see gotcha 2. On this kind, the judgement is usually *don't*.

> 🚧 **ROADWORKS — nothing checks coverage above the highest bin or below the lowest.**
> **Current state.** The gap check runs *between* bins only, in both tilings. A closed top bin on an
> unbounded axis therefore strands every measurement above it: it matches no bin, and not the
> `unresolved` sentinel either, because a measurement *was* made. Below-lowest is documented as out
> of scope (*"it would false-positive without a known domain floor"*); above-highest is simply absent.
> **Expected state.** Neither edge check can exist without a declared domain, and there is no column
> for one. Do not expect this to change.
> **Guard.** Leave the top bin unbounded — blank `measure_max` — unless the axis really ends, and
> check both edges by hand.

### 4. The `unresolved` sentinel is documented as mandatory and is not enforced on the compile path

`binning.py`'s module docstring says **"`unresolved` (T1) is mandatory"**, `docs/SCHEMAS.md:631`
calls it *"the mandatory no-call sentinel on every binning table"*, and `draft._unresolved_cell:313`
calls it *"the mandatory `unresolved` companion row"*. **Measured: a table with no sentinel row
compiles green under `--strict` with zero warnings.** The only mechanism that produces one is
`stub_template`, which appends it as an extra last row (`rows=1` yields two rows: one stub, one
sentinel). Delete it, or start the file from a copied example, and the compile says nothing.

> ⚠️ **CHECK — "enforced by nothing" is one surface too wide.**
> **Current state.** The *authoring* surface does notice. `hints._check_bins` emits
> `warning | unresolved | "no unresolved sentinel row…"`, so `inspect_rows` — the plugin's
> `lint_rows`, CLI `just-dna-compiler hint <kind>` — reports a sentinel-less table. What is true, and
> is the whole point of the gotcha, is that **no check on the compile path requires one**: `validate`
> and `compile --strict` both stay green.
> **Expected state.** The two surfaces disagree on purpose and neither is going to change soon, so
> treat the hint as the only thing that will tell you. Worse, the hint is `not any(...)` over the
> **whole table** while the compile-path rule that refuses a *second* sentinel is **per bin group** —
> so on a table whose key fields fragment it into several groups (see `copynumbers.md` gotcha 3), one
> sentinel anywhere satisfies the hint and most groups can still have none. **Run the hint, then
> count sentinels per group yourself.**

Consequence: a consumer with no score has no row to select and no way to tell that the author
declined to say anything from the author never having thought about it. Write the sentinel by hand
if you did not start from the template. What *is* enforced: **at most one** sentinel per
`(gene, trait_efo_id)` — measured, a duplicate fails with *"2 unresolved sentinel rows for key
('CYP2D6', None) — a consumer selects one when a measurement is absent, so at most one is
allowed"* — and a sentinel carrying a bound is refused by `_validate_range`.

### 5. A defaulted column with an empty cell is a hard error; the column omitted entirely is fine

The classic `field_category` trap, and this table has two instances: `measure_kind` and
`unresolved` both have defaults, so pydantic's `is_required()` is `False`, but `load_csv_rows` turns
an empty cell into `None` and keeps the key, so the model receives `None` instead of its default.
Measured on both:

```
activity_phenotype.csv line 2 [unresolved]: Input should be a valid boolean
activity_phenotype.csv line 2 [measure_kind]: Input should be a valid string
```

Dropping the whole column instead compiles, and produces a **byte-identical parquet and an identical
`content_signature`** to writing the defaults out. So: write `false` / `activity_score` in every
cell, or do not carry the column. Never a blank cell under a present header. `table_requirements`
reports this as its `defaulted` map — read all three of `always` / `defaulted` / `any_of`.

### 6. `source_field` is namespace-qualified, and a bare colliding key warns

`CN` is one of `vocab.VCF_COLLIDING_KEYS` (`:99`) — INFO and FORMAT both define it, and since VCF
4.4 §7.2 *"INFO/CN is the allele-specific copy number and FORMAT/CN is the sample's total copy
number … the two answers differ by a factor of the ploidy"*. `_check_vcf_pointers`
(`compiler.py:1669`) warns on a bare one, aggregated by reason, and is silent on `FORMAT/CN`. A bare
key stays legal and keeps meaning **unqualified** — that is why this is a warning and not a refusal;
guessing the namespace would convert *unstated* into a *stated* answer.

The second half of that check — "you pointed at a multi-valued field and stated no element rule" —
fires only where the spec's reserved tables know the field's `Number`. An activity score is not read
from a reserved VCF field at all, so in practice this table's pointers are unknown-cardinality and
the check withholds rather than accusing. Unknown is not multi-valued.

### 7. A model-level error message names no column

Measured: the sentinel-with-bounds refusal prints `activity_phenotype.csv line 6 []: Value error,
an unresolved row carries no measure_min/measure_max`. The `[]` is a `model_validator` finding with
no single column to name. Read the message, not the bracket.

## What does not exist

- **No `measure_step` column.** Named as a deliberate deferral in `validate_bins`
  (`binning.py:1059-1061`): it is a full-cost authored column nobody has asked for, so it waits for
  the demand that would fix its shape. Consequence: `quantised`'s step is 1 and nothing can say
  0.25.
- **No third `measure_tiling` member for this kind.** `VALID_MEASURE_TILINGS` has exactly two, and
  `activity_score`'s `None` is *a kind's default only* — a kind that genuinely answered the two
  questions apart would need an additive third member, and adding one is a deliberate act
  (`binning.py:190-195`). So you cannot spell "not dense, and gap-checked" at all.
- **A sixth `measure_kind` (`copy_number_continuous`) was proposed and refused** — the tiling is a
  different axis from the quantity, and folding them would be a product rather than a sum (P5).
  Recorded at `binning.py:169-176`. Do not propose it again.
- **Moving these kinds into `_DENSE_KINDS` was refused**: one line, and it silently re-reads every
  published table with no notice and no way to say otherwise (`binning.py` module docstring).
- **No spanning-measurement warning here.** RM56 (a measurement is an interval and can cross a
  threshold) fires only for kinds in `_VCF_MEASURE_FIELDS` (`:213`) — `copy_number` and
  `repeat_count` only. An activity score summed over two haplotypes with an uncertain copy number
  has the same problem and this tier says nothing about it. Not established whether that is a
  decision or an omission; the RM56 policy vocabulary (withhold / worst bin / point estimate) is
  deferred to 0.7 and its grain is deliberately undecided.
- **No `requires_callable` on any binning row.** It and `callable_from` are `VariantRow`-only; RM70
  records the same gap for the three PGx tables and is deferred pending a decision about which table
  owns the claim. `unresolved` is the nearest thing this table has, and it answers a narrower
  question.
- **No positional key.** `(gene)` is the whole identity, and RM65/RM66 record that the
  non-joinability is a **schema gap** rather than a property of what these tables describe — gated
  on a real caller VCF. `reference_examples/cyp2d6_structural` is filed as that gating evidence, not
  as a defect.
- **No `variant_key`.** `_check_binning_grounding` reads `model.model_fields` rather than `hasattr`
  precisely to tell this table apart from `heteroplasmy.csv`, which has one and therefore gets a
  second grounding remedy this table does not.

## Consumption today

**Nothing reads `activity_phenotype.parquet`. Anywhere.** Verified across `just-dna-lite`
(including `just-dna-pipelines/`), `just-dna-registry` (`just-dna-marketplace` is a symlink to it),
`just-prs` and `just-prs-mcp`. `measure_min`, `measure_max`, `measure_tiling`, `source_field` and
`source_element` have **zero** occurrences in all five repos, in any file type.

Every occurrence of the table's name is a filename in a list or a comment:

| path:line | what it does |
|---|---|
| `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/module_config.py:500` | `"activity_phenotype"` in `LEAD_TABLES` — a *discovery* list. Probes for the parquet's existence to decide "is this directory a module". Never opens it |
| `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/annotation/hf_logic.py:222-243` | `_lead_join_strategy` classifies a lead table by schema. Its docstring: *"`unsupported` — neither. `diplotypes`, `pgs`, `allele_function` and the binning families carry no per-variant key at all; the caller skips them with the reason recorded"* |
| same file, `:302-304` | `strategy == "unsupported"` → `raise UnsupportedLeadTable`. This is the line that discards the module |
| `.../annotation/hf_modules.py:36` | `MODULE_TABLES = ["annotations", "studies", "weights", "sources"]` — four names, hardcoded, this table absent |
| `.../annotation/hf_modules.py:495-503` | `class ModuleTable(str, Enum)` — `ANNOTATIONS`, `STUDIES`, `WEIGHTS`, `SOURCES`, `LEAD`. The only vocabulary `scan_module_table` accepts |
| `just-dna-lite/webui/src/webui/state.py:6015` | a comment naming `activity_phenotype`; `_authored_row_count` counts **CSV lines** to pick a registry endpoint |
| `just-dna-registry/src/just_dna_registry/specfiles.py:56-58` | `TABLE_KIND_CSVS` — the allow-list of authored CSVs the registry stores and round-trips. Bytes in, bytes out |
| `just-dna-registry/src/just_dna_registry/services/upgrade.py:32,153` | `ActivityPhenotypeRow` in `_ROW_MODELS`, used only by `offending_columns()` / `trim_unknown_columns()` to check a legacy CSV *header* against the field names |

The registry never opens a parquet at all, and its `CardStats`
(`just-dna-registry/src/just_dna_registry/models/api.py:12-22`) has no activity, metabolizer, PGx or
binning field. Its search filters (`api/routers/modules.py:70-113`) include
`has_gene_validity`/`has_clinical_assertions`/`has_gwas_effects`/`has_frequencies` and **no**
table-kind facet. `just-prs` has no dependency on `just_dna_format` at all; its `prs_percentile`
work is the PGS Catalog reference distribution, a different thing sharing a word.

The asymmetry worth naming: `/data/sources/dna-agents/.claude/agents/pgx-module-creator.md:120-146`
carries a full authoring spec for this table, with the non-overlap and mandatory-sentinel rules. The
ecosystem knows exactly how to **write** `activity_phenotype.csv` and has no code anywhere that
**reads** it.

## Blanks for just-dna-lite

- **Implement the binning lookup rule — one code path serves all four kinds.** Nothing today reads
  a bin. The rule is *select the row with the greatest `measure_min ≤ x` within the group*, groups
  keyed `(gene, trait_efo_id)`. `hf_logic.py:222-243` (`_lead_join_strategy`) needs a fourth
  strategy beside `position`/`rsid`/`unsupported` — call it `measure` — and `:302-304` is the exact
  line that currently throws the module away. **What breaks today:** a module whose only content is
  CPIC's phenotype cut-points is discovered, digested, published, and then skipped with a logged
  reason. It annotates nothing.
- **Implement the three-state contract, including the `unresolved` fallback.** A missing score
  selects the sentinel row and **never** the lowest bin; a score present but matching no bin is a
  *third* state ("no matching bin"), not the sentinel. **What breaks today:** nothing implements
  either, so the safety property the sentinel exists for — *no diplotype ⇒ unresolved, never Normal
  Metabolizer* — is asserted by the format and honoured by no consumer.
- **Give `activity_phenotype` a home in the table vocabulary.** `MODULE_TABLES`
  (`hf_modules.py:36`), `ModuleTable` (`:495-503`) and `ModuleInfo`'s URL fields (`:225-241`) name
  four tables plus `lead`. A binning module gets a `lead_url` and no reader. **What breaks today:**
  `get_module_table_url()` (`:513-547`) cannot even name the table, so a consumer that wanted to
  read it has no accessor to call.
- **Gene-keyed tables are indexed into `manifest.stats.genes` as of compiler 0.6.6.** Until then the
  gene set came **from `variants.csv` alone**, so an `activity_phenotype`-only CYP2D6 module published
  `gene_count: 0, genes: []` and `registry_search(gene="CYP2D6")` could not find it — the registry
  indexes `version_genes` straight off that field
  (`just-dna-registry/src/just_dna_registry/db/repository.py:664`). **Fixed in compiler 0.6.6** (upstream **RM121**): `module_stats` takes the gene facets over every authored table, `variant_stats` keeps its `variants.csv` promise, and a module already published carries the stats its compile wrote — recompile and re-publish to be findable by gene. Re-measured on `cyp2c19_star_alleles`: `gene_count: 1, genes: ['CYP2C19']`. It affected
  `copynumbers.csv`, `repeat_alleles.csv`, `allele_function.csv`,
  `haplotypes.csv` and `diplotypes.csv`.
- **Draft the bins from CPIC instead of leaving them hand-typed.** The CPIC snapshot's
  `diplotypes.parquet` carries `(gene, diplotype, phenotype, activity_score)`
  (`enricher/src/just_dna_enricher/cpic.py:628-641`), which is exactly what the reference example's
  author grouped by hand into four bins. `pgx_draft` already reads that table and currently discards
  the score. A drafter emitting bins with `<<REPLACE>>` on `conclusion` — leaving the inequality
  strings (`"≥3.0"`) as an explicit warning rather than a guessed bound — would remove the one
  authoring step this table has no tool for.
- **Surface `source_field` / `source_element` as the extraction contract.** Both are validated,
  vocabularied and printed by `describe_table`, and no consumer resolves either. **What breaks
  today:** an author who correctly writes `source_element: largest_alt` has stated something no code
  will ever act on, which is indistinguishable from writing nothing.

## Ask the live schema

Never write a column list or a vocabulary from this file — it is stamped **format 0.6.1** and the
models move. Ask:

```
describe_table("activity_phenotype.csv")      # every column, its vocabulary, its pick-list,
                                              # and the redundancy_bearing / attestation_bearing maps
table_requirements("activity_phenotype.csv")  # always / defaulted / any_of / optional — read all four
authoring_reference()                         # whole-schema view, generated from the live models
get_template("activity_phenotype.csv", stub=True, rows=3)
                                              # header + N stub rows + the unresolved sentinel row
```

In-process equivalents, when you want what is actually installed rather than what a long-running
server loaded: `just_dna_compiler.hints.describe_table`, `just_dna_compiler.draft.stub_template`,
`just_dna_format.binning.DEFAULT_MEASURE_TILING`, `just_dna_format.vocab.ELEMENT_RULE_MEANINGS`.

**One caution, observed while writing this file:** an MCP `describe_table` call returned the
**format 0.5** shape for this table — 11 columns, no `measure_tiling`, no `source_element`, no
`pmid`, and the pre-RM53 `source_field` description — while `importlib.metadata` reported
`just-dna-format 0.6.1` and the same call in-process returned all 14. A long-lived server process
holds the schema it imported at start-up. If a column this file names is missing from the tool's
answer, check the installed version before concluding the column does not exist.
