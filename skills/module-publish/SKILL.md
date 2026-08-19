---
name: module-publish
description: >-
  Rehearse on the polygon and then promote to the catalog. Covers the two instances and what differs, the three cost-free pre-flights, what the server fills, and why a content claim is name-independent and survives a yank.
  Triggers: "publish", "rehearse", "polygon", "registry", "namespace", "would_publish", "duplicate content", "yank", "publish to production".
---

# Stages 7-8 - rehearse, then publish

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 7 (rehearse) and 8 (publish)

## What this skill owns

Getting a module into a catalog without spending something irreversible. The polygon exists because
on production a botched publish is permanent in two ways at once.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` §§ 7-8, § 6.7 | the two instances, the gates, what v2 costs |
| the registry's own docs | the client surface and the amend endpoints |
| `create-module` § 7 | the current procedure text to move across |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `readme.md` - the card, and `MODULE.md` renamed on upload
- `logs.md` - what publishes that you did not intend
- `licensing.md` - the gate that refuses in both modes

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **Publish to the polygon unless the user names the catalog.** A novice's "put it on your site" means
  somewhere their friends can see it, not an immutable registry.
- **You upload the spec, not the parquets**: the server enriches, strict-compiles and stores the
  artifact itself, which is why a published digest is trusted rather than claimed.
- **A stray `*.log` publishes silently** - real bundles carry system prompts and local paths, up to
  4 MB, swept in by every compile with no opt-out.
- **The content claim is name-independent and `yank` does not release it**, so a botched publish spends
  the version *and* the right to publish that data under any other name.
- **Prose costs no version** - changelog, logo and readme each have an amend endpoint.
- Two modules differing only in `weighting:` are `409 duplicate_content`, because that block is outside
  `content_signature`.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
