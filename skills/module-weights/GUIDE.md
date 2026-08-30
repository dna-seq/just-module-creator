---
name: module-weights
description: >-
  What `weight` means, who may write it, and why no tool fills it. Covers the sign convention and the
  warning that cannot fire, declaring a scale in `weighting:`, why a published GWAS beta is not a
  weight and sits beside the column rather than inside it, what `pgs.csv` actually is, and how the
  reference corpus and real submitted modules are exact inverses of each other on this one column.
  Triggers: "weight", "what weight should I use", "GWAS beta", "effect size", "can I use the GWAS
  value", "weighting", "scale", "normalise weights", "PRS weights", "pgs.csv", "net weight",
  "effect_unit".
---

# Weights — the column everyone fills and nobody declares

**Read by:** stage 3 (curate), and any later pass that touches numbers. Reached from [`module-curate`](../module-curate/GUIDE.md).

The most-requested and least-documented decision in the format. Every real authoring session spent its
time here, every one invented a method, and none declared it.

## The population fact, first, because it reframes the question

| Corpus | `weight` authored |
|---|---|
| the sixteen reference examples | **0 of 42 cells** — the column appears in four modules and is blank in all of them |
| 27 real submitted bundles | **2,439 of 2,439** — 26 distinct values, all bounded in `[-1.5, 1.5]` |

They are exact inverses. The fixtures show a format where nobody weights anything; real authors weight
**everything**, on a scale none of them wrote down. One reference module declares `weighting:` at all,
and it is a *negative* declaration — *"scale: none — this module authors no weights"*, pointing a reader
at `gwas_effects.parquet` instead. That is a good declaration, not an empty one.

## Who may write it

**`weights.parquet.weight` is 100% authored.** No tool fills it, no lookup offers it, and no consumer
blends it row by row. `gwas_effects.csv` **refuses a `weight` column outright at the schema level** —
`Extra inputs are not permitted` — which is the format saying, in the only way a schema can, that a
published effect size is not this cell.

That refusal has been proposed and declined twice. The reason is below.

## The sign convention, and the warning that cannot save you

**`weight` is a contribution to a wellness-style score, not a hazard ratio.** So:

| | wants |
|---|---|
| `state='risk'` or `direction='risk'` | **`weight < 0`** |
| `protective` | `weight > 0` |
| `neutral` | `0.0` is a real answer |

Getting it backwards is a **warning**, not an error, so it compiles.

⚠️ **CHECK — the sign warning cannot fire on an honest GWAS module.** It keys on `state` or `direction`
being `risk`. Withholding the axis is *correct* when the direction is unknown — and doing so disables
the only check the column has. So on exactly the modules where a mechanical fill would be most tempting,
nothing is watching. **Check the sign by hand; a green run is not evidence.**

## Why a published beta is not a weight

`rs1800562` carries **186 associations** in the GWAS Catalog spanning **12 distinct `effect_unit`s** —
three of them merely spellings of one — and **42 of 195** name no effect allele at all. Pick one and
you have chosen a trait, a population, a model and a unit, silently.

Then the sign inverts: **a beta is positive on the effect allele; `weight` is positive-is-protective.**
A mechanical fill therefore flips the claim on exactly the rows nobody re-reads, and produces a module
that is internally consistent, compiles green, and asserts the opposite of the literature.

**Where the machine-held number goes instead:** `gwas_effects.csv`, **beside** the authored column, with
its own `effect_unit`, its own study and its own p-value. `enrich_gwas_effects` fills it
— budget `1 + 2N` requests per variant, measured at **382 for one real module**, which is why the
tool says so in its own description and why `--no-study-facts` exists. Reading that table is how you *justify* a weight; it is not
where the weight lives.

## Declare the scale

`weighting:` in `module_spec.yaml` is where you say what the numbers mean: the scale, the direction
convention, the normalisation if you applied one, or that the module authors none. It is **invisible by
construction** — `scaffold_module` omits every optional block, and until 0.19.0
`describe_table("module_spec.yaml")` answered *"Unknown table kind"* rather than pointing anywhere,
which is why several real sessions concluded the field did not exist. **`describe_spec_file()` now
answers it**, block by block, generated from the model that validates the file — so the scale and its
three fields are one call away. Still write it at scaffold time; [`module-start`](../module-start/GUIDE.md) says so for the same
reason, because nothing prompts you later.

It sits **outside `content_signature`**, with two consequences: an edit there costs no content identity,
and two modules differing *only* in that block collide as `409 duplicate_content` at the registry.

🚧 **ROADWORKS — a consumer already sums weights per module and prints a "Net weight" headline, and
your declaration is not wired to it.** The caveat you write lands three lines from the number and nothing
connects them. **Guard:** write the scale into `weighting:` **and** into the README, and keep the row's
own `conclusion` self-sufficient — a reader may see the sum without ever seeing the scale.

## What `pgs.csv` is, and is not

**Per-variant PGS weights are not in the format.** `pgs.csv` is a **manifest of published scores** — a
pointer to a PGS Catalog id plus the envelope it is valid in — not a table of per-variant coefficients.
This plugin does not compute a polygenic score, and neither does anything downstream of it today.

⚠️ **CHECK — a fabricated PGS id validates, lints clean and compiles.** Nothing resolves the identifier
against the Catalog, anywhere on the surface. **Guard:** take the id from a Catalog record you actually opened, and
say in the README which score it names.

`pgs.csv` also carries **no coordinate columns at all**, so resolution never reaches it and a consumer
joins it on `rsid` + `genotype`. That is a different fact from the positional tables' fill, with a
different remedy — [`module-curate`](../module-curate/GUIDE.md) has the split.

## How to choose a number, defensibly

There is no house scale, and inventing one silently is what every real session did. What makes a weight
defensible is not its magnitude:

1. **State the axis first.** If no located paper says which allele carries the risk, there is no
   direction, and a weighted row asserting one is a coin flip that will look exactly as authoritative as
   a real one. Drop the row instead — [`module-curate`](../module-curate/GUIDE.md).
2. **Pick a scale and write it down.** Bounded in `[-1, 1]`, or *"log-odds from the named study"*, or
   ranks. Any of them is fine; an undeclared one is not.
3. **Keep it ordinal within the module.** The comparison a reader can actually make is between two rows
   of *this* module, so internal consistency beats external calibration.
4. **Cite what moved the number.** The study belongs in `studies.csv`; the published effect belongs in
   `gwas_effects.csv`. The weight is your model of the finding, and the two tables are what make it
   reviewable rather than arbitrary.
5. **A zero is a claim too** — it says *this genotype changes nothing*, which is different from a blank.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** writing the `weighting:` block the scaffold omitted, including the negative
declaration; moving a published effect size out of `weight` and into `gwas_effects.csv` where it belongs.

**Surface it, and let a pilot settle it:**

- **The number.** Every cell of it, on every row.
- **The scale, and whether the module has one.**
- **Whether the direction is knowable at all.** Withholding is correct and is not a gap to fill.
- **Whether a published beta is close enough to reuse** — and if you do reuse one, saying so, in
  `weighting:`, with the unit.

## What this stage cannot do

**No tool fills `weight`, and none will.** Filling it from a source would make the row's only
independent judgement a copy.

**Nothing normalises across modules.** Two modules' weights are not comparable and nothing says so at
the point of use.

**Nothing computes a polygenic score here.** `pgs.csv` points at one; it does not carry one.

**Nothing checks a weight against anything.** The one warning keys on an axis you may correctly have
withheld.

## Symptoms

`../module-101/references/SYMPTOMS.md` has the full map. Here:

- *"state='risk' but weight=1.0 > 0"* — a **warning**, so it still compiles. The convention is inverted
  from the one most people assume.
- *"direction must be one of ['neutral', 'protective', 'risk', 'unknown']"* — `direction` is not a
  magnitude; it is the same axis as `state`.
- `Extra inputs are not permitted` on a `weight` column in `gwas_effects.csv` — working as intended.

## Where to go next

| You need | Load |
|---|---|
| the rest of the cells only an author writes | [`module-curate`](../module-curate/GUIDE.md) |
| the effects table in full | [`module-tables`](../module-tables/GUIDE.md) → `references/gwas_effects.md` |
| the score pointer table in full | [`module-tables`](../module-tables/GUIDE.md) → `references/pgs.md` |
| where `weighting:` lives in the spec | [`module-tables`](../module-tables/GUIDE.md) → `references/module_spec.md` |
| what a consumer does with the number | [`module-consumer`](../module-consumer/GUIDE.md) |
