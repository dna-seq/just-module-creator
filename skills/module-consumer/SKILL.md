---
name: module-consumer
description: >-
  The obligations on the far side of the seam, and what an author can do to make a module readable. Covers the three-state join contract, the unobservable-allele marker, callability pointers, float32 comparison, and expansion rows that assert nothing.
  Triggers: "how is this read", "consumer", "join to a VCF", "no-call", "hom-ref", "requires_callable", "star in a genotype", "float comparison", "locus_count", "will this match".
---

# Will a consumer read this right

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 9 (install and join) - and every stage that decides how a row will be read

## What this skill owns

A module supplies the annotation and the consumer supplies the measurement. That split leaves
normative obligations on the reader, several of them ways to get a well-formed number and a wrong
answer.

## Write it from these

| Source | Why |
|---|---|
| `SCHEMAS.md` § the consumer join contract | the three states, `*`, and the pointer columns |
| `SCHEMAS.md` § reading the VCF the pointers point at | QUAL inversion, MIN_DP, float32, ID lists |
| `COMPILER.md` § resolution | expansion, and `hosting_verdict` |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `variants.md` - expansion rows, and the callability quartet nobody reads
- `heteroplasmy.md`, `repeat_alleles.md`, `copynumbers.md`, `activity_phenotype.md` - the bin lookup
- `clinical_assertions.md` - per-allele calls versus a module's flat one

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **A conforming consumer must distinguish a covered reference call from a no-call**, and must not read
  absence from a variant-only callset as hom-reference. That is the difference between "screened
  negative" and "not screened".
- **`*` is unknown, never reference**, and dropping it turns `*/A` into a reference-like `A`.
- **Compare in float32**: every VCF `Float` is 32-bit, and widening moves a bound in a direction that
  depends on the decimal, so both directions lose a row.
- **Expansion rows assert nothing** - `locus_count > 1` is the predicate, gated on `expanded_keys`
  because the column defaults to 1.
- **Nothing downstream implements the bin lookup**, so four table kinds annotate nothing today; and the
  callability quartet is read nowhere, so a `requires_callable` conclusion is asserted with no proof of
  callability.

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
