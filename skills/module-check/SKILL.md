---
name: module-check
description: >-
  Compare what the module claims against what the sources say, and record that the question was put. Covers every check and its severity, the ones that deliberately never escalate, the tautology skips, and reading a green run's warnings.
  Triggers: "cross-check", "verify", "check identifiers", "clin_sig conflict", "ACMG SF", "gene locus", "validate strict", "why is this a warning", "verification.json".
---

# Stage 5 - cross-check what you asserted

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 5 (cross-check) - the second stage that fetches

## What this skill owns

Reporting, never repairing. The stage that turns an assertion into a checked assertion, and records
which checks ran so a later reader can tell silence from a pass.

## Write it from these

| Source | Why |
|---|---|
| `ENRICHER.md` § the check table, § verification.json | every check, its severity, the skip vocabulary |
| `COMPILER.md` § what the compiler can and cannot validate | the three validation classes and the blind spots |
| `create-module` § 5 | the current procedure text to move across |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `verification.md` - what a record means, and what `close` does to records
- `clinical_assertions.md`, `gene_validity.md` - the tables that record rather than adjudicate
- `literature.md` - existence, identity, and the quote

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **A check that could not run is not a check that passed**, and the skip key proves it: `subjects=0`
  with no `skipped` means it ran over nothing; a `skipped` key means it did not run.
- **Some attestations record a check nobody could have run** - three instances: `enrich_pgx` grading
  CPIC's own table, `hints._flag_advisory_columns` naming checkers that cannot see the table quoted,
  and our `enrich_facts` collapsing "no constraint" into "not asked".
- **Two checks deliberately warn even under `--strict`** - the ClinVar `clin_sig` and allele-function
  comparisons - because failing would make the format arbitrate between authorities it depends on.
- **15 of 17 check members have live emitters** (RM72, enricher 0.6.4); the widely-cited "five of
  seventeen" is stale.
- **`enrich_pgx(mode="strict")` does not raise** - `mode` is stored and never read, while the docstring
  and the CLI both advertise a failure.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
