---
name: module-diff
description: >-
  Work out what moved in a module and what it means. Covers the identity ledger, the content-signature versus fact-signature versus digest decision tree, the three numbers actually worth watching, and the honest fact that nothing compares two versions.
  Triggers: "what changed", "why did the digest move", "diff two versions", "canary", "did the source change", "content_signature", "compare modules", "is this stale".
---

# Read what changed - the canary

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** a reading, not a stage

## What this skill owns

The only diagnostic instrument this format has for detecting that the world moved under a module. A
procedure over signatures and CSV diffs, not a tool - because nothing in any tier compares two
versions of a module.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § 5, § 5.1 | the identity ledger and the canary decision tree |
| `MODULE_LIFECYCLE.md` § 7 | the absences: no diff, no changelog, no predecessor |
| `SCHEMAS.md` § identity & integrity | the hash family, one row each |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- every dossier's `## What moving this table moves`
- `resolution.md` - why the canary needs a deliberate delete
- `gwas_effects.md`, `gene_validity.md` - tables whose fact signature moves on a release label

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **Content unmoved + a fact signature moved = the upstream source said something different this
  time.** That is the one reading meaning the world moved; every other row is something you did.
- **§5.1's worked example is stale**: it says three numbers to watch where a compile today produces
  four, and quotes a `sources.signature` that has since moved. Copy the method, not the numbers.
- **The canary is an operation, not a signal.** Merge-not-clobber means a source that revised an answer
  moves nothing, so detecting drift *is* delete-and-re-derive - which also discards overrides (RM83).
- **Row reordering is a third route to "content unmoved, digest moved"**, which §5.1 says has exactly
  two. Measured.
- **Nothing compares two versions**: no diff in any tier, no changelog generation, no parent digest in
  the artifact.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
