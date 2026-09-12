# expression_effects.csv — what a model predicts a variant does to one gene's expression

> **Written 2026-09-13 against format 0.7.0 / compiler 0.7.0 / enricher 0.7.0 / registry 0.25.2,
> read from the code and from the installed models.** The table landed with format's AlphaGenome
> work in 0.7 and reached the registry's rosters in 0.25.0. Anchor on symbol names —
> `expression.ExpressionEffectRow`, `enricher.expression.enrich_expression`,
> `integrity.EXPRESSION_FACT_FIELDS` — never on `file:line`.
>
> **Columns, types, requiredness and vocabularies are generated upstream**, at
> <https://just-dna.life/just-dna-compiler/tables/expression_effects/>, and live in-session from
> `describe_machine_table("expression_effects.csv")`. This file keeps the half a model cannot
> state: who decides which cell, what it costs to fill, and the symptom when it is read wrong.

## In one paragraph

`expression_effects.csv` is a **prediction table**, and it is the first one this format carries.
Every other derived sidecar records what some archive *observed* — an allele count, a submitted
classification, a published effect size. This one records what a neural model **guessed** about a
variant it has never seen measured. One row is one `(variant, gene)` pair: which way the variant
moves that gene's predicted expression, how many tissue tracks agree on the sign, and how far the
variant sits from the gene. It is written by `enrich_expression_effects` from the AlphaGenome Atlas
and read back by `top_expression_effects`.

**It answers for every scored variant in the interval, not for your rows.** That is the point
rather than an inefficiency: the distal variants — the ones no module authors and no drafter would
find — are usually what the query was for. A 4 kb window is ~12,000 rows. Expect to rank, not to
read.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.expression.ExpressionEffectRow`, `extra="forbid"` |
| One row is | one `(variant, gene)` prediction |
| Natural key | `(variant_key, gene)`, `rule="equality"` — run `hints.key_fields("expression_effects.csv")` |
| Becomes | `expression_effects.parquet` |
| Authored or machine-produced | **machine-produced.** No drafter, no `get_template`, not in `draft.DRAFTABLE` |
| Written by | `enrich_expression_effects` → upstream's `enricher.expression.enrich_expression` |
| Read back by | `top_expression_effects` (offline; sorts and filters, writes nothing) |
| Fact signature | **yes** — `integrity.EXPRESSION_FACT_FIELDS`, sixteen of the nineteen columns |
| Outside the signature | `source`, `status`, `fetched_at` — provenance, so a re-fetch of unchanged predictions hashes equal |
| In `content_signature`? | no. It is not authored input |
| In the attestation binding? | no |
| Overlayable | **yes** — `expression_effects.csv` is in `overrides.VALID_OVERRIDE_TABLES` |
| Merge behaviour | merge-not-clobber; re-running never removes a row |

## Five facts that change how you read it

### 1. A prediction is not a measurement, and the column names do not say which you have

`effect_size` here reads exactly like `effect_size` on `gwas_effects.csv` — a float, no unit — and
they are different kinds of claim. The GWAS number is what a study measured in a cohort. This one is
what a model output for a substitution that may never have been observed in a human. Nothing in the
schema separates them, so **the separation has to survive in the prose you write**: a
`variants.csv` conclusion grounded on this table and nothing else is grounded on a prediction, and
the row should say so.

`audit_module`'s `directional_claims_without_studies` finds such rows whether or not you say so
first. Being found by it is not an accusation — it is the signal that a `studies.csv` row is owed or
that the conclusion needs rewording.

### 2. Direction is a sign, not a verdict, and the step to `risk`/`protective` is authored

`effect_direction` is the sign of a predicted expression change. **Raising a gene may be good, bad
or neither**, and which it is depends on the gene, the tissue and the trait — none of which this
table knows. So the move from a direction here to a `state` or a `clin_sig` on a `variants.csv` row
is a judgement, it belongs to a pilot, and it goes through `record_override` so `logs/authoring.log`
carries who made it.

**A null `effect_direction` is a real answer.** It means no track agreed on a sign, and
`top_expression_effects` counts those in `direction_unknown` rather than dropping them. Reading null
as "no effect" is the three-valued mistake this format exists to prevent — the model answered, and
its answer was *the tracks disagree*.

### 3. Filling it makes the module non-commercial, and there is no other way to run it

AlphaGenome **Atlas** output is non-commercial-only. `enrich_expression_effects` defaults
`use="non-commercial"` and a run declaring anything else writes nothing at all. The pass lands an
`alphagenome_atlas` row in `licensing.csv` with `commercial_use=false`, and **the most restrictive
term binds the whole artifact** — one such row makes the module non-commercial however permissive
everything else is.

**`alphagenome_atlas` and `alphagenome_avi` are two sources with two licence classes.** Reading
"AlphaGenome is permissive" off the AVI row and then joining a table this pass wrote mis-licenses
the module, and nothing downstream will catch it: the licence gate reads `licensing.csv` and will
find the restrictive row and be correct, while the author's belief about the module is wrong.

That is a property of the *module*, decided by the data it used — never a reason to leave the tool
unwrapped or the table unfilled. Whether a module may be non-commercial is the author's call, made
once, in front of them.

### 4. The corpus is the interval, so the cost is the author's to aim

This is a corpus-sized pass and **the corpus is the window you ask for, not the rows you have**. A
whole gene plus its ±512 kb attribution flanks is ~3.1M SNVs — about **47 minutes**. A 4 kb window
is ~12,000 SNVs and takes seconds. `chrom`/`start`/`end` are how you aim it; `dry_run=true` reports
the cost and writes nothing.

`gene` is required either way, and that is a **requirement of the service** rather than an
optimisation — there is no gene-less query to fall back to.

### 5. There is no snapshot lane, so `offline` is a refusal rather than a cached answer

Every other enrichment pass has somewhere local to read from when the network is shut. This one does
not: `offline=true` returns a refusal saying the question was **not asked**, which is the honest
record and is different from *asked and nothing came back*. Needs `ALPHAGENOME_API_KEY` and the
`atlas` extra.

**Upstream writes the data table before it records the licence row.** So a failure whose message
names `licensing.csv` may still have left `expression_effects.csv` on disk — check the file before
concluding the run did nothing.

## What does not exist

- **No drafter and no template.** `describe_table`, `table_requirements`, `get_template` and
  `lint_rows` all gate on `draft.DRAFTABLE` and refuse this table. Use `describe_machine_table`.
- **No cross-check against `variants.csv`.** The compiler compares nothing between the two. A
  prediction that contradicts your authored `state` is not reported by anything; the concordance
  record covers `clin_sig` only, and there is no equivalent for expression direction.
- **No registry facet.** `_V017_COLUMNS` carries `has_gene_validity`, `has_clinical_assertions`,
  `has_gwas_effects` and `has_frequencies` and nothing else (re-measured 2026-09-13 against registry
  0.25.2), so "which modules carry expression predictions" is not searchable.
- **No unit, ever.** `effect_unit` is null on every AlphaGenome row because the service publishes
  none. The scores are comparable within one scorer's output and not across scorers, and the null is
  the honest record of that rather than a gap to fill.
- **No `rsid` in the common case.** The Atlas answers by coordinate and names no rsID, so the column
  is filled only where the module or its `resolution.csv` already knew one. Check `lookup_variant`
  before writing anything about a novel position.

## Refreshing it

**`refresh_sidecar` refuses this table, and the reason is neither the licence rows' nor the
concordance pair's.** The producer exists, works, and is wrapped here as
`enrich_expression_effects`. What cannot be re-run is the **question**. Every other sidecar's pass
re-reads the module's own subjects and re-asks the same thing; this one answers for a gene and an
**interval you aim**, and a row records `dataset` — the query's date — with no `chrom`/`start`/`end`,
no `min_score` and no `max_rows`. So the window that filled the file is not recoverable from the
file, and min/max of the rows on disk does not recover it either: they are filtered by `min_score`
and truncated by `max_rows`.

A refresh could therefore only default to the whole gene plus its flanks — a different question,
~47 minutes rather than seconds — and rows outside your original window would then read as ones the
source withdrew. That is §2's *never classify against a partial re-derivation*, biting from the
other side. It would also have to pass a `declared_use` on your behalf, and that is an assertion
about how the module will be used rather than a fact about the data.

The sidecar is merge-not-clobber, so re-running the pass **never removes a row** — a prediction the
model no longer makes stays on disk. A clean derivation means deleting the file yourself first, on a
machine that holds the credential, then re-running `enrich_expression_effects` and `validate_module`
/ `compile_module`. Nothing captures it for you, so copy it out first if any overlay work was keyed
to it.

Because the table is overlayable, an author's correction lives in `overrides.csv` and **not** in this
file. Editing a cell here directly is the repair the overlay exists to refuse: the next pass
overwrites it, and nothing records that it was ever changed. See
[`overrides.md`](overrides.md).

## Ask the live schema

```
describe_machine_table("expression_effects.csv")   # every column, type, meaning
enrich_expression_effects(spec_dir, gene, chrom=…, start=…, end=…, dry_run=True)
top_expression_effects(spec_dir, gene=…, min_consensus=0.8, limit=20)
record_override(...)                                # log any judgement taken off these rows
audit_module(spec_dir)                              # directional_claims_without_studies
```

Then read the **warnings on a green run**: the licence row this pass added is the one that decides
whether the module can be used commercially, and it arrives without being asked for.
