---
name: module-close
description: >-
  End the authoring phase deliberately and write down how it was done. Covers what a closure binds,
  what re-opens a module and what no longer does, the way closing can throw your check records away,
  why a closed module is not a checked module, and where the methodology actually lives — `weighting:`,
  `authorship:` and `verification.json` rather than prose. Also the README, which becomes the catalog
  card.
  Triggers: "close the module", "closure", "methodology", "authorship", "who wrote this", "records no
  closure", "is it finished", "write the README", "dropped_checks", "verification.json is stale",
  "re-close", "closed_by".
---

# Stage 6b — close, and write the methodology

**Lifecycle stage:** 6b. The second of the two places only a human may reach; curation is the first.

Authoring had no end, so every check that wanted to know whether a stub was still a stub was guessing.
**This is the end.**

## What a closure is

```
close_module(spec_dir="spec", closed_by="your-name")
```

It writes a `closure` into the module's `verification.json`, naming the hash of `module_spec.yaml` and
the authored CSVs **as they stand right now**. Edit any of them afterwards and the hash moves, the
compiler drops the closure, and the module is open again. That is the design, not a bug — **re-close
when you are finished again.**

Three things worth being exact about:

- **Nothing does it for you and nothing should.** `validate_module` stays read-only however cleanly it
  passes. A record stamped by whatever happened to run says only that something ran; a closure says a
  person decided.
- **It does not refuse on warnings.** An unresolved rsID or an ungrounded threshold is a legitimate
  state to call finished. Only a spec that will not validate is refused.
- **`closed_by` is legibility, not proof** — a string nobody checks. Signing a closure needs a private
  key, and this server deliberately takes none: a key that reaches a tool argument has been logged. Use
  `just-dna-compiler close <spec-dir> --private-key …` if you want the act attributed rather than
  merely recorded.

An unclosed module still compiles and still publishes; it carries a warning saying nobody has declared
it done. Requiring a closure is filed for format 1.0 (RM73).

## What re-opens a module, and what no longer does

There is no `reopen` command and none is needed.

| Un-closes | Does not |
|---|---|
| any changed **value** in `module_spec.yaml` or an authored CSV | line endings — `\r\n` reads as `\n` since format 0.6 (RM82) |
| a row added, removed or reordered | a re-enrichment that rewrites a derived sidecar |
| a cell requoted, a column reordered | a README, changelog or logo edit |
| **an `authorship:` entry appended** | |

**A BOM, trailing whitespace and a missing final newline are still edits** — a human typed those. The
line-ending exemption is the *binding* only: `manifest.inputs[]` still lists the raw hash and size, so
that entry does move on a rewrite. Two questions, two answers: *is this the same module* versus *are
these the exact bytes*.

**An appended `authorship:` entry un-closes the module and that is correct**, however unwelcome it
looks: a review that changes nothing is an attestation *of* zero changes, made by somebody who had not
made it before. The old closure is genuinely spent, and the reviewer is exactly the person who should
re-close. `module-revise` owns the review pass.

## 🚧 ROADWORKS — closing can throw your check records away

A record attested over bytes that no longer match is **dropped**, and named in
`CloseResult.dropped_checks`. Dropping is correct — carrying it across would re-bind a claim to
different bytes — but the loss is nearly invisible:

- it is a **field on the result**; the Typer CLI prints one line for it and a library caller that
  ignores the field is told nothing;
- it is **not a compile warning**;
- **nothing about the loss reaches `manifest.verification`**, so the published module simply shows
  `{closed: true, checks: []}`.

It has already happened in the format repo's own history: **15 of its 16 reference examples record zero
checks**, all sharing the empty-list signature `sha256:4f53cda1…`.

**Guard, three parts:** close through the CLI **or** read `dropped_checks` explicitly and fail on a
non-empty list; **run the checks after closing**, so the records describe the bytes you actually
closed; and treat an empty `verification.json` on a closed module as *"the records were dropped"* until
proven otherwise.

> **A closed module is not a checked module.** A closure says *a human declared these bytes final*. It
> says nothing about whether anything was verified, and the two are separately visible in the manifest
> for exactly that reason.

## The methodology has a machine-readable home, and prose does not replace it

Three places, each answering a different question:

| Where | Answers |
|---|---|
| `weighting:` in `module_spec.yaml` | what the weights **mean** — the scale, the convention, or that there are none |
| `authorship:` | **who did what**, and whether they were human |
| `verification.json` | **what was checked**, and what was skipped rather than passed |

Write the README as well, but never *instead*. **Prose goes stale across versions with nothing warning
you**: in the real corpus a bundle's prose is byte-identical to two versions earlier while its variant
count more than doubled, and one pair carries an identical `content_signature` while claiming a
"maintenance update". Nothing checks a README against the rows beneath it.

### The README is the catalog card

The registry projects `README.md` onto the published module, so **a module without one has a blank card
in the catalog** — which is what a browsing consumer sees first. Write it for someone deciding whether
to install:

- what the module claims, in a sentence a non-specialist can read;
- **which population the evidence came from**;
- what it does **not** cover — including the things no field can record: the module's origin, a
  non-GRCh38 build's consequences, and which genes it covers when it carries no `variants.csv`
  (`manifest.stats` is computed from `variants.csv` alone, so `registry_search(gene=…)` cannot find such
  a module however many rows carry a `gene` cell);
- which parts you did and which you did not — *"coordinates corrected, conclusions not re-read"* is a
  better sentence than silence.

**`MODULE.md` is the old name.** It still uploads and is renamed on the way in with a note, but a
**local** compile of such a bundle yields `manifest.readme: null` in silence. Rename it on intake.

**README and logo sit outside both identities and outside the binding**, so fixing a caveat costs no
version and no closure — the registry has amend endpoints for exactly that. `module-publish` owns them.

## Before you call a module done

- [ ] `validate_module(strict=True)` passes, and `compile_module(strict=True)` after it
- [ ] every weighted row has a coordinate, or you can say why not
- [ ] **if you authored any `start` yourself**: one row per source checked against `lookup_variant` and
      the position matched **exactly** — no offline gate catches a whole file shifted by one
- [ ] genotypes sorted; single-allele on `MT` / `Y` outside PAR; alleles drawn from the locus
- [ ] every PMID's **title** read back against the paper meant, 1–8 digits, reachable from a weighted row
- [ ] `check_identifiers` run, `gene_locus_conflicts` empty **with** `gene_locus_check_skipped` null
- [ ] `resolution.csv` and `literature.csv` committed alongside the CSVs
- [ ] `licensing.csv` present, covering every source cited, and consistent with `license:`
- [ ] `module.version` is a **quoted** SemVer string, with no warning that it "was read as SemVer"
- [ ] `authorship:` declares the kind honestly, `[ai, agent]` included where it applies
- [ ] `weighting:` declared — including the negative declaration, if the module authors no weights
- [ ] a second **compile** of the untouched spec reproduces the same `artifact_digest`
- [ ] `close_module` run, **checks re-run afterwards**, and `dropped_checks` read

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** re-closing after an edit you already applied; renaming `MODULE.md` to
`README.md`; quoting a bare `version:`; re-running the checks after a close so the records describe the
bytes you closed.

**Surface it, and let a pilot settle it:**

- **Whether the authoring is finished.** That is the whole content of the act.
- **Whether the prose still tells the truth.** Nothing checks it, ever.
- **What to disclose that no field holds** — the origin, the population, what was not re-read.
- **Whether to sign.** A recorded closure and an attributed one are different claims.

## What this stage cannot do

**It cannot verify anything.** Closing is a declaration, not a check; the checks are `module-check`.

**It cannot preserve a record it invalidated.** A check attested over different bytes is dropped, and
no flag keeps it.

**It cannot make a module trustworthy.** Trust accumulates from what the module *records* —
`authorship`, the checks, the closure — and from later contributors. Hedging the prose does not
substitute, and neither does withholding the publish.

**`reverse` cannot restore it.** The closure, the verification record and `authorship` are all outside
the round trip. The module in your repository is the source of truth.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action:

- *"This module records no closure"* — a true statement about a module still being written. Close it
  when it is done, not to clear the warning.
- *"verification.json is stale: the attestation was computed over different module bytes"* — an
  authored edit re-opened the module. Re-run the checks and close again.
- An empty `checks: []` on a closed module — read it as *the records were dropped*, per the 🚧 above.

## Where to go next

| You need | Load |
|---|---|
| the checks whose records this stage can drop | `module-check` |
| rehearsing and then publishing | `module-publish` |
| what a second pass does to the closure | `module-revise` |
| the closure and the attestation in full | `module-tables` → `references/verification.md` |
| the README as an artifact of its own | `module-tables` → `references/readme.md` |
