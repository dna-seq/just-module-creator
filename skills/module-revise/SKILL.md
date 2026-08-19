---
name: module-revise
description: >-
  What to do the second, third and twenty-fifth time somebody opens a module. Covers the six kinds of second pass, which stage each re-enters, what each invalidates, semantic versioning without a contract, and why prose costs nothing.
  Triggers: "update a module", "second pass", "new version", "revise", "review pass", "bump the version", "which version", "already published", "amend".
---

# Pass two and beyond - revise

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 10 -> back to 3, 2, 1 or 6

## What this skill owns

The half of the lifecycle nothing documented, and the half every real session was in. A second pass
normally re-enters at curate, and the version number is not how you tell the kinds apart.

## Write it from these

| Source | Why |
|---|---|
| `MODULE_LIFECYCLE.md` § 6 in full | the six kinds, the consequence matrix, the identity ledger |
| `MODULE_LIFECYCLE.md` § 6.0, § 6.6 | no versioning contract, and `authorship` across passes |
| `SCHEMAS.md` § the closure | what un-closes a module |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- every dossier's `## What moving this table moves`
- `verification.md` - the attestation and closure across passes
- `readme.md` - real version chains, and prose that went stale

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **Six kinds**: prose, review, evidence, data, source refresh, rebuild. They compose, and they differ
  in what they invalidate rather than in what they are called.
- **There is no versioning contract.** `2.0.0` does not mean reviewed; the registry enforces SemVer
  well-formedness and uniqueness and nothing else. No agent may withhold a publish waiting for a
  milestone that does not exist.
- **A review pass is: append the `authorship` entry, re-run the checks, close again, publish.** The
  append moves no identity and drops both claims - correctly, because a review that changes nothing is
  an attestation *of* zero changes.
- **Do not spend a version on prose** - three amend endpoints move no digest and no content claim.
- **Real evidence exists now**: 21 distinct bundles under 27 filenames, nine version chains, prose
  identical across versions whose data doubled, and one pair with an identical `content_signature`
  claiming a "maintenance update".

## Required sections when written

- **What this stage is for** - one paragraph, and who acts.
- **The order inside the stage** - what must precede what, and where deviating deadlocks.
- **What only an author may decide** - the cells no tool fills, with the refusal reasons.
- **What moving through this stage moves** - identities, the attestation, the closure.
- **Symptoms** - the messages this stage produces. Link `../create-module/references/SYMPTOMS.md`
  rather than copying it.
- **What this stage cannot do** - the `MODULE_LIFECYCLE.md` §7 absences scoped to here, so an agent
  stops inventing a tool.
