# `fto_bmi` plus the AlphaGenome Atlas: one variant, two genes, and what the expression pass reported about it

A reference example from the tester seat's probe on 2026-11-09, plugin 0.48.3. It is the first live run of
`enrich_expression_effects` against the Atlas; until then only the window loop had been tested, with the
upstream call replaced (`F105`). The authored files are `assets/fto_bmi` unchanged. The pass added
`expression_effects.csv` and an `alphagenome_atlas` row in `licensing.csv`.

- **The module is now non-commercial.** That is the Atlas's licence, and the tool says so when it writes.
- **It has never been published.** Its name is not `test_`-prefixed, so it must not be rehearsed as it stands.
- **`verification.json` is left out.** The one in `assets/fto_bmi` was closed on 2026-08-18, before the Atlas
  rows existed, and would attest bytes this directory no longer has.

## Why this variant

rs1421085 is a one-row module where the variant's `gene` (FTO, the gene it sits in) is not the gene it acts
on. The module's own study (Claussnitzer 2015, PMID 26287746) says the C allele "doubles IRX3 and IRX5
expression", and IRX3 is about 516 kb away. The pass was built around a variant and its own gene, so this is
the two-gene case the design has to survive.

## What was run

| call | window | took |
|---|---|---|
| `rows=true` (plans from the row: FTO) | 16:53767032-53767052, 63 candidates | 3 min 2 s |
| the same, on a fresh copy | same | 4 s |
| `gene="IRX3"`, that interval | same | 1 min 5 s |
| the same, on a fresh copy | same | 2 min 45 s |
| `gene="IRX3"` again, merged into the FTO copy (this directory) | same | 9 s |

The dry run promised "about 2 s" for the window. Repeated calls wrote identical rows, apart from `fetched_at`.

What the Atlas predicts for rs1421085 T>C (both rows are in `expression_effects.csv`):

| gene | effect_size | direction | tracks agreeing | distance |
|---|---|---|---|---|
| FTO | −0.0026 | decrease | 314 of 371 | 0 |
| IRX3 | −0.0039 | decrease | 220 of 371 | 516,262 bp |

The study measured IRX3 and IRX5 doubling in the cells the paper edited. The model predicts a small decrease
in IRX3, with 59 % of its tracks agreeing. **That is model against literature, not a defect.** It is the case
the tool's own words anticipate: a predicted direction is not a clinical direction, and a row written from one
is the author's judgement. Nothing in `variants.csv` was changed.

## What it broke (findings in `docs/dogfooding.md`)

- **F140.** `top_expression_effects(module_rows_only=true)` gives the FTO rows a status that describes the
  model, but it is read off what the sidecar happens to hold.
  - With only the IRX3 query in the sidecar, both rows read `gene_not_at_locus`, which the docstring explains
    as "the row's `gene` label is not one the Atlas scores there".
  - The Atlas does score FTO there: the `rows=true` run wrote it, and once both queries are merged the same
    rows read `scored`.
  - `rows=true` can only ask about a row's own gene, so reaching IRX3 took the interval form, and nothing on
    the `rows` path says so.
- **F141.** The dry run's cost is a constant two seconds per window, not a measurement. Four of the five calls
  above took 30 to 90 times that, and the host moved two of them to the background at 120 s. What made them
  slow is not known; the identical repeats show that it varies from run to run.

- **F142.** In 24 of this sidecar's 126 rows, the sign of `effect_size` contradicts `effect_direction`; one is
  16:53767047 A>T, +0.0044, `decrease`. The enricher intends this: the size is the single strongest tissue track,
  and the direction is the majority vote. But format's description of `effect_size` calls it an aggregate, and
  neither of our tools says so.

## Reproduce

These calls need `ALPHAGENOME_API_KEY`, and each one makes the target directory non-commercial. Work on a
copy.

1. `enrich_expression_effects(spec_dir=<copy of assets/fto_bmi>, rows=true)`
2. `enrich_expression_effects(spec_dir=<another copy>, gene="IRX3", chrom="16", start=53767032, end=53767052)`
3. `top_expression_effects(spec_dir=<each copy>, module_rows_only=true)` on each copy. It is offline, and on
   this directory it reads `scored: 2`.
