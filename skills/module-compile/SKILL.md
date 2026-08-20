---
name: module-compile
description: >-
  Build the artifact and read what the build says. Covers strict versus best-effort, the warnings that matter on a green run, the one check that discards an authored row, and the difference between the byte identity and the content identity.
  Triggers: "compile", "validate", "strict", "artifact.digest", "content_signature", "verify_artifact", "sign", "why did my digest change", "manifest.json".
---

# Stage 6 - compile, verify, sign

> **STATUS: SCAFFOLD.** A planned split of `create-module`, not yet written.
> **Until it is, load `create-module`** — it remains the one canonical copy of the procedure for
> stages 1-8. Do not restate it here; move the relevant passage across when this file is written, and
> delete it there in the same change.

**Lifecycle stage:** 6 (compile, verify, sign)

## What this skill owns

Producing the parquet set and the manifest, reproducibly. The stage that proves a module is
well-formed and self-consistent, and says nothing about whether it is true.

## Write it from these

| Source | Why |
|---|---|
| `COMPILER.md` § the compile pipeline, § resolution | the ordered steps and the precedence rules |
| `SCHEMAS.md` § identity & integrity | the hash family and what each answers |
| `MODULE_LIFECYCLE.md` § 5, § 5.1 | the identity ledger and the canary |

**Dossiers** (`../module-tables/references/`, non-invokable, read on demand):
- every dossier's `## What moving this table moves`
- `module_spec.md` - what an edit there costs
- `logs.md`, `logo.md`, `readme.md` - what travels beside the data

> The dossiers were **audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, with
> the code as arbiter. **Anchor on the symbol name, never on `file:line`** — the reasoning held, the line
> numbers drifted. Read the 🚧 ROADWORKS and ⚠️ CHECK markers; `module-tables` states what they mean, and
> a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.

## Seeds - established, still to be written up

- **`--strict` means reproducible, never right.** The compiler never fetches, so it holds no reference
  to check a coordinate against.
- **The two identities answer different questions**: `content_signature` is *this data, however
  compiled*; `artifact.digest` is *these bytes, from this compiler*.
- **A row reorder moves the digest, leaves the content signature, and un-closes the module** - measured
  on several tables. So does deleting a final newline. CRLF does not (RM82).
- **A lengthless symbolic allele is the one check that discards an authored row**, and the warning must
  say DROPPED, because `reverse` cannot re-emit what never reached the parquet.
- **Warnings are the interesting output on a green run**, and several are unclearable by any authored
  edit - VRS coverage on a structural module, `not_covered` frequencies, a skipped positional fill.

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
