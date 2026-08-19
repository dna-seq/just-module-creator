---
name: module-enrich
description: >-
  Resolve rsIDs to coordinates, mint allele ids, and read the one report that can catch a mistake no offline gate can. Covers the resolver chain, the off-by-one signature, recovering an rsID from an old-assembly coordinate, and why unreachable is not absent.
  Triggers: "enrich", "resolve coordinates", "resolution.csv", "ref mismatch", "unresolved rsID", "GRCh37 coordinate", "hint recover", "VRS", "not_found".
---

# Stage 4 - enrich

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 4 (enrich) - one of the two stages that fetch

## What this skill owns

Turning what the author wrote into something a VCF can join, and reporting every disagreement
between the module and the genome. The only tier that may hold a reference, so the only place these
checks can live.

## Write it from these

| Source | Why |
|---|---|
| `ENRICHER.md` § `enrich()` - the resolver chain | the links, the order, what `--offline` changes |
| `ENRICHER.md` § the reference-allele check, § the old assembly | `shift`, and rs-number recovery |
| `MODULE_LIFECYCLE.md` § Stage 4 | merge-not-clobber and its consequences |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- `resolution.md` - the hinge between the tiers
- `variants.md` - expansion, `locus_count`, what a filled coordinate changes
- `frequencies.md`, `gene_metrics.md` - the passes that read what this one wrote

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **`start` is the 1-based VCF position.** A file shifted by one passes validate, strict compile,
  `fully_resolved: true`, and mints ids the compiler reports *verified*. It happened at scale - 3,038
  rows across four modules. `RefMismatch.shift` is the field that names it.
- **Unreachable is not absent.** A failed request writes no row and lands in `unreachable_rsids`; only
  that list is worth re-running. Deleting a variant because `enrich` missed it while `lookup_variant`
  resolves it is the wrong repair - it cost a real module `rs6265`.
- **`--no-resolve` ignores an injected table and still exits zero**: the digest is byte-identical to
  compiling with `resolution.csv` deleted.
- **`ResolutionRow.fetched_at` is never assigned by any code path** - blank on all 428 rows across 11
  reference tables.
- **A hand-edited coordinate on a VRS-minted row fails the compile** unless `vrs_id` is cleared; that
  is corruption, not a difference of opinion.

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
