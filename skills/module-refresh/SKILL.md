---
name: module-refresh
description: >-
  Bring a module up to date with a source that has moved. Covers merge-not-clobber and why a re-run refreshes nothing, what deleting each sidecar costs, writing to the file you read, and what a re-draft does and does not repair.
  Triggers: "re-run enrich", "why did it not update", "refresh", "newer ClinVar", "delete resolution.csv", "stale sidecar", "re-draft", "source released".
---

# Refresh a source, re-derive a sidecar

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 2 or 4, re-entered

## What this skill owns

The operational half of a second pass. Every derived sidecar is human-overridable by design, which
is exactly why a re-run will not refresh it and why deleting one costs something.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § 6.3, § 6.4 | what must be deleted, what deleting costs, what a re-draft moves |
| `ENRICHER.md` § the caches, § snapshot-first | provisioning, releases, and `--offline` |
| `FAQ.md` § sidecars, re-runs and regeneration | the questions already answered |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `resolution.md` - hand-authored `source=manual` rows are not reproducible
- `frequencies.md`, `gene_metrics.md`, `literature.md`, `gene_validity.md` - per-sidecar delete costs
- `licensing.md` - `dataset` blanked, `draft_digest` re-stamped

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **A re-run does not refresh anything already recorded.** To re-derive you delete first, and deleting
  discards every hand-curated row along with the stale ones.
- **Write to the file you read.** Two copies of one sidecar is an error naming both paths - never a
  merge, never newest-wins.
- **`gene-metrics` crashes on a second run** - `UnboundLocalError`, reproduced through the library and
  the CLI, online and offline.
- **13 of 13 `literature.csv` rows in the corpus lack `doi_checked`**, because merge-not-clobber never
  re-asks; only deleting the sidecar clears a stale DOI verdict.
- **A ClinGen re-curation appends beside the old row with nothing marking it superseded**, because the
  assertion id embeds the curation timestamp: `definitive` (2019) and `moderate` (2026) for one key,
  both in the manifest, nothing saying which is current.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
