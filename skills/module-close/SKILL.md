---
name: module-close
description: >-
  End the authoring phase deliberately: record the closure, write the methodology and the README, declare authorship. Covers what closing means, what un-closes a module, and why the closure is the one record a machine may not stamp.
  Triggers: "close the module", "closure", "methodology", "authorship", "who wrote this", "records no closure", "is it finished", "write the README".
---

# Stage 6b - close, and write the methodology

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 6b (close) - the second place only a human may reach

## What this skill owns

Saying the authoring is finished, and writing down how it was done. The stage that turns a spec
somebody is editing into a module somebody stands behind.

## Write it from these

| Source | Why |
|---|---|
| `SCHEMAS.md` § the closure (RM73) | what it binds, and why `validate` may not stamp it |
| `MODULE_LIFECYCLE.md` § 6.2, § 6.5 | the consequence matrix, and the attestation across passes |
| `create-module` § 6b | the current procedure text to move across |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `verification.md` - the closure, and `close` dropping records
- `module_spec.md` - `authorship`, `weighting`, `license`
- `readme.md` - the module card, and prose as a claim rather than a receipt

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **A closed module is not a checked module.** 16 of 16 reference examples are closed and 15 record
  zero checks, all sharing `sha256:4f53cda1...` = `verification_signature([])`.
- **`close` silently destroys check records**: with any authored byte moved it returns `closed: true`,
  `warnings: []`, drops every record into `dropped_checks`, and the next compile publishes
  `{{closed: true, checks: []}}`. Run the checks *after* closing, and read `dropped_checks`.
- **The methodology has a machine-readable home and prose does not replace it**: `weighting:` for what
  the weights mean, `authorship` for who did what, `verification.json` for what was checked.
- **Prose goes stale across versions with nothing warning** - real evidence: a bundle whose prose is
  byte-identical to two versions earlier while its variant count more than doubled.
- **Closing is deliberate**: a record stamped by whatever happened to execute says only that a tool
  ran, which is the defect the closure exists to fix.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
