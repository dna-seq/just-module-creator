---
name: module-start
description: >-
  Triage a source you were handed, decide which tables the module needs, and create the spec directory. Covers the three questions to answer first, declaring the module kind, licensing, authorship, contact email, and declaring `weighting:` at birth.
  Triggers: "start a module", "new module", "scaffold", "I have a zip", "triage these sources", "which tables do I need", "module_spec.yaml".
---

# Stage 0-1 - origin and scaffold

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 0 (origin) and 1 (scaffold)

## What this skill owns

Getting from a theme plus some sources to a legal spec directory that declares what it is. The
stage nobody documents - upstream calls Stage 0 out of scope and our procedure starts at scaffold -
yet every real session began with a handed bundle.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § Stage 0, Stage 1 | the origin picks the shape of the second pass, and nothing records it (RM85) |
| `SCHEMAS.md` § the authored surface | which tables exist and what each is for |
| `create-module` §§ 0-1 | the current procedure text to move across |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `module_spec.md` - every block, and `weighting:` in particular
- `readme.md` - what a handed bundle really looks like, and `MODULE.md`
- `licensing.md` - the one fact table a human writes

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **`weighting:` is invisible by construction and must be written here.** `scaffold.py:88-90` omits
  every optional block, and `describe_table("module_spec.yaml")` refuses without pointing at
  `authoring_reference()`. Two real sessions concluded the field did not exist.
- **26 of 27 real submitted bundles carry `MODULE.md`, not `README.md`**, and `_collect_readme` returns
  `None` for it, so a local compile silently yields `manifest.readme: null`. Rename on intake.
- **A handed bundle is 0.1-era and that is fine**: 0 genuine breaks across 27 bundles under 0.6.1,
  24/27 still validate. Classify each discrepancy as era gap / live deprecation / genuine break, and
  keep plain author defects out of all three.
- **Do not trust a bundle's own README** - one asserted allele validation performed over coordinates
  that were shifted by one base.
- Record which shape of second pass this origin implies: a source-drafted module inherits a release
  cadence, a paper-drafted one inherits the literature's.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
