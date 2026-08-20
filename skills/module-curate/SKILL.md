---
name: module-curate
description: >-
  The stage where a module is actually written: genotypes, weights, state and direction, conclusions a layperson can read, and how many rows belong in a report at all. Covers the cells no tool fills and why, the sign convention, and trimming a GWAS dump into an annotation.
  Triggers: "curate", "write conclusions", "what weight", "state or direction", "the report is huge", "too many SNPs", "which rows to keep", "genotype", "conclusion".
---

# Stage 3 - curate what only an author decides

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 3 (curate) - and the stage a second pass re-enters at

## What this skill owns

Deciding what the module claims. Every other stage prepares this one or checks it. Upstream names
this as where pass two normally re-enters, so it must read well on a module that already exists.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § Stage 3 | the cells no tool fills, and where a machine-held effect goes instead |
| `SCHEMAS.md` § row models, § the three-valued algebra | what a cell may hold, and what a blank means |
| `create-module` § 3 | the current procedure text to move across |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `variants.md` - the biggest, and the sign check that cannot fire
- `studies.md` - the receipt for every claim
- `module-weights` (skill) - the whole weight question
- `module-tables` (skill) - which table a finding belongs in

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **The trim decision belongs here and no tool makes it.** Three of four real sessions independently
  complained the output was a PRS decomposed into rows, while validate and compile were green at 1,613
  SNPs. This skill must give an author a defensible way to decide how many rows is a report.
- **`weight` is what everyone fills and nobody declares**: 0 of 42 cells in the reference corpus,
  **2,439 of 2,439** across 27 real submitted bundles, 26 distinct values in [-1.5, 1.5].
- **The sign warning cannot fire on an honest GWAS module** - it keys on `state`/`direction == "risk"`,
  so withholding the axis, which is correct when unknown, disables the only check on the column.
- **A homozygous genotype at an indel locus can never be contradicted**: `hosting_verdict` returns
  `None`, so no warning and no strict error. Our skill currently promises otherwise.
- **`direction` is never derived from `state` in the artifact**; the fallback lives in Python and does
  not travel with the parquet.

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
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
