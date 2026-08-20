---
name: module-weights
description: >-
  What `weight` means, who may write it, and why no tool fills it. Covers the sign convention, declaring a scale in `weighting:`, published GWAS effects sitting beside the authored column rather than inside it, and why per-variant PGS weights are not in the format.
  Triggers: "weight", "what weight should I use", "GWAS beta", "effect size", "can I use the GWAS value", "weighting", "scale", "normalise weights", "PRS weights", "pgs.csv".
---

# Weights - the column everyone fills and nobody declares

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** read by stage 3, and by any second pass that touches numbers

## What this skill owns

The most-requested and least-documented decision in the format. Every real authoring session spent
its time here, every one invented a method, and none declared it.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § Stage 3 | where a machine-held effect size goes instead |
| `SCHEMAS.md` § the GWAS-effect table, § `PgsRow` | `effect_unit`, and RM16 |
| `FAQ.md` § sidecars | why the fill was refused, twice |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `gwas_effects.md` - the effects, their units, and the refusal
- `pgs.md` - published scores, and what `just-prs` would need
- `module_spec.md` - `weighting:`, and why it is invisible today
- `variants.md` - the sign check that cannot fire

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **`weights.parquet.weight` is 100% authored.** No tool fills it, no consumer blends it row by row,
  and `gwas_effects.csv` refuses a `weight` column outright at the schema level.
- **Published betas are not weights**: rs1800562 carries 186 associations spanning 12 distinct
  `effect_unit`s - three of them spellings of one - and 42 of 195 name no effect allele at all.
- **The sign trap**: `weight` is positive-is-protective while a beta is positive on the effect allele,
  so a silent fill inverts the claim on exactly the rows nobody re-reads.
- **Declare the scale in `weighting:`** - and know that a consumer already sums weights per module and
  prints a "Net weight" headline three lines from the cell that would caveat it, unwired.
- **Per-variant PGS weights are RM16 and not in the format.** `pgs.csv` is a manifest of Catalog ids,
  and a fabricated id validates, lints clean and compiles.
- **The population fact**: 0 of 42 cells authored in the reference corpus, 2,439 of 2,439 in real
  submitted bundles, 26 distinct values bounded in [-1.5, 1.5].

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What needs a pilot, and what you may simply fix** - the two sides of the discriminator, with
  the reason each cell sits on the side it does. Evident and mechanical (a rename, a deprecated
  spelling, a column that moved) is applied silently; a checked or authored value (`genotype`,
  `weight`, `clin_sig`, a conclusion, a `provenance_quote`) is surfaced, never written quietly.
  **Not a list of refusals** - RM15 retired that framing. This layer may write; what it owes is a
  logged move and an honest split between the two kinds.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../module-101/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
