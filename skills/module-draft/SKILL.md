---
name: module-draft
description: >-
  Draft rows from a source that publishes them - ClinVar gene panels, CPIC star alleles, ClinPGx drug response - and read the report honestly. Covers appends-never-rewrites, partial rows and the placeholder, review-star floors, and what a re-draft does to a module drafted before a drafter fix.
  Triggers: "draft from ClinVar", "draft a panel", "draft from CPIC", "ClinPGx", "already_present", "differs", "REPLACE placeholder", "min_review_stars", "re-draft".
---

# Stage 2 - draft from a source

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 2 (draft)

## What this skill owns

Letting a provider write what it can and leaving loudly incomplete what only a human decides.
Drafting appends and never mutates, which is what makes this the one stage designed for repetition.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § Stage 2, § 6.4 | append-never-rewrite, and what a re-draft moves |
| `ENRICHER.md` § a gene panel is drafted, never decided | the providers, the placeholder, the star floor |
| `create-module` § 2 | the current procedure text to move across |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `variants.md` - what `draft_from_clinvar` leaves stubbed
- `pharm_variants.md`, `haplotypes.md`, `allele_function.md`, `diplotypes.md` - the PGx providers
- `licensing.md` - `dataset` and `draft_digest`, which decide whether a later check runs

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **`pgx_draft` drops 763 of CPIC's 1,361 alleles** - 693 of them names the model accepts - because the
  drafter checks `STAR_ALLELE_PATTERN` while the table checks only non-empty/no-whitespace. Eleven
  genes lose every allele; `draft --gene DPYD` emits 248 skips and adds 0 rows.
- **32% of CPIC function statuses map to a blank cell with no warning**, and a blank is unknown, so the
  later comparison skips the row.
- **S41 vs S44 vs S45**: a drafter fix either *skipped* rows or *wrote them under an identity that has
  since moved*, and only the second leaves anything behind. `_superseded_rsid_rows` names them and
  deletes nothing.
- **`min_review_stars` defaults to 2**; a panel mixing a 0-star submission with an expert panel without
  saying so is worse than one that names its floor.
- **The drafted-from marker decides whether a real check runs later**: without `dataset` and a matching
  `draft_digest`, `enrich_pgx` attested 34 CPIC alleles clean *against CPIC*.

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
