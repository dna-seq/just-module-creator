---
name: module-status
description: >-
  Work out what a module directory is, how far it got, and what somebody has to decide next. A reading rather than a stage: it authors nothing and hands off to whoever owns the next step.
  Triggers: "where am I", "what next", "what stage is this module at", "resume", "pick up where I left off", "somebody handed me a spec directory", "what is left to do", "is this module finished", "is it ready to publish", "what still needs deciding", "status", "did this ever get enriched", "has this been closed", "what is missing", "I inherited this module", "look at this module".
---

# Where a module stands, and what has to be decided next

**This is a reading, not a stage.** Nothing here authors, checks or repairs anything. It answers one
question — *what state is this spec directory in, and what does a human have to choose before the next
step can run* — and then hands off to the skill that owns that step.

You need it because the lifecycle is spread across eight stage skills and a spec directory carries no
progress marker. The state is only inferable from which files exist and what they contain, and the
inference goes wrong in a specific way: **a file existing proves a pass ran once, never that its answer
is still the current one.**

## If there is no directory yet, fetch one

This skill reads a disk. When nobody handed you anything and the module exists only in the catalog,
the acquisition comes first and it is one call:

```
registry_download(target="prod", namespace=ns, name=name, version="1.0.0", dest="./work")
```

Every tier, no flag. It verifies the bytes as it fetches, and its default `include_inputs=true` is
what brings the authored CSVs down beside the parquets — without them there is almost nothing here to
read, because every marker in the table below is an authored file. `target` is required and the two
instances share no database. Which version to name is `registry_get_module`'s answer, not this skill's.

**That is acquisition, not a status read.** Once the directory exists, the four passes below run on the
disk and nothing else, for the reason in the next paragraph.

## Read it in four passes, cheapest first

1. **The names on disk.** Which files are there at all. That alone brackets the stage.
2. **What `module_spec.yaml` declares.** The module kind, `genome_build`, `weighting:`,
   `authorship:`, the licence position. These are declared once at birth and never re-asked
   ([`module-start`](../module-start/GUIDE.md)), so an absence here is an absence for the module's whole life.
3. **`verification.json`.** Which checks ran, which were skipped and why, and whether a closure
   survives.
4. **One `validate_module`.** Cheap, offline, and it is the only step that reads the rows rather than
   the filenames. Do this last, because the three passes above usually explain whatever it reports.

Do not run `enrich_module`, `compile_module` or a catalog read to find out where you are. A status read
is free; those are not, two of them change the directory, and what the registry holds is a different
question from what this directory says.

**The roster of names a spec directory may legitimately carry is not ours to write down.** It is
`just_dna_registry.specfiles.RECOGNIZED_SPEC_FILES`, and [`module-tables`](../module-tables/GUIDE.md) →
`references/LAYOUT.md` explains what each roster governs. Read it from there rather than from memory —
and note the consequence for anything you find that is *not* on it: an unrecognised name is tolerated by
the compiler and dropped by the next server-side rebuild, so a file somebody invented beside the spec is
a file that will not survive a re-publish.

## What each file marks, and what it does not prove

| On disk | The stage it marks | What it does **not** prove |
|---|---|---|
| `module_spec.yaml` | scaffolded (1) | that the declarations are right, or that `weighting:` / `authorship:` were ever considered — both are commonly just absent |
| an authored table CSV | rows exist (2–3) | that they are curated. Grep for `<<REPLACE>>`: a drafted row is a stub with a placeholder where a human must decide |
| `studies.csv` | claims have receipts (3) | that anyone read the papers. A `provenance_quote` that is the article title passes every check there is |
| `resolution.csv` | enrichment ran once (4) | that it is current, or that it was machine-derived — a hand-injected `source="manual"` row looks the same |
| any other machine-written sidecar | that pass ran once (4) | same. These merge rather than clobber, so a re-run adds and never replaces |
| `licensing.csv` / `sources.csv` | a licence position was taken (0–1) | anything about which spelling is preferred — read `layout.preferred_spelling`, do not decide it here |
| `verification.json` with checks | cross-checking ran (5) | that anything passed. Read the `skipped` reasons before the findings |
| `verification.json` with a closure | a human declared the bytes final (6b) | that the module was checked. A closure and a check record are different claims |
| `README.md` | the catalog card is not blank | that its claims match the data. A handed bundle's README is a claim, not a receipt |
| `out/manifest.json` | it compiled (6) | correctness. `--strict` means reproducible |
| `published.json` | this plugin published it at least once (7–8) | the registry's current state. It is a local receipt and is never uploaded; ask `registry_get_module` |
| `provenance.json` | somebody recorded why an authored value outranks a source | that the override is still right. Read them back with `review_queue` |
| `logs/*.log` | the authoring pipeline left a trail | that it is safe to publish unread — logs are swept into every compile with no opt-out |

Two absences say as much as any presence. **No `studies.csv` beside rows that make clinical claims is a
hole**, not a choice — and the claim-bearing tables are not just `variants.csv`. **Every table whose
model carries `clin_sig` makes a clinical claim**, several of the binning kinds among them, so a PGx
module with a thousand rows and no receipts is the same hole. Do not carry the list: `audit_module`
computes the set from the live models and reads whichever of those tables are here. **No `variants.csv` at all is usually correct** — a PGx, binning or pointer module carries none,
and adding an empty one to tidy the picture is the repair [`module-tables`](../module-tables/GUIDE.md) warns against by name.

## The one call that reads the whole directory at once

```
audit_module(spec_dir="spec")     # offline, writes nothing; decisions | clear | not_computed
```

**Run it first on a module you did not create.** The table above tells you which stage a file marks;
this tells you what somebody still has to *choose* — whether `weighting:` says what the `weight` column
means, whether any recorded check ran over zero subjects, whether a check counted disagreements and
kept none of them, whether an `effect_size` is really the Z of its own p-value, and whether clinical
claims have receipts. Plus a per-column fill count for every authored table, which is the cheapest way
to see what is there to curate.

Read its three lists as three different things. `decisions` is the short list somebody must act on.
`clear` computed and found nothing. **`not_computed` is not a pass** — the file that signal reads is
absent, so nothing about it is established, and each entry says which file and so what.

## Presence is not currency

Four ways a directory that looks finished is not, each with the skill that owns it:

- **A sidecar that is present is authoritative and will not be refreshed by re-running the pass.** If
  you expected a value to move and it did not, the file is still there. → [`module-refresh`](../module-refresh/GUIDE.md)
- **A closure is dropped the moment the authored bytes move.** So a module with edits after its last
  close reads as closed in the file and open to the compiler. → [`module-close`](../module-close/GUIDE.md)
- **A green strict compile is a determinism result.** The compiler never fetches, so nothing in it can
  contradict a coordinate. → [`module-compile`](../module-compile/GUIDE.md)
- **A check that could not run is not a check that passed.** `skipped`, `unverifiable` and `null` are
  not passes, and they are the readings most likely to be summarised away. → [`module-check`](../module-check/GUIDE.md)

## The output is a decision list

**Not a diff, not a findings dump, not a summary of what you read.** If a human has to choose, it goes
in the list. If nothing has to be chosen, it does not appear at all — the noise about work nobody had
to do is what buries the two or three items that mattered.

Each entry says three things and stops:

1. **What has to be chosen** — in the author's terms, not the schema's.
2. **What turns on it** — which step is blocked, or what a consumer would see either way.
3. **Where the choice gets made** — the stage skill, or the tool call.

Shaped like this, and this short:

> - **Fourteen rows in `variants.csv` still carry `<<REPLACE>>` in `genotype`.** Every loader refuses
>   the file until they are decided, so nothing downstream can run. → [`module-curate`](../module-curate/GUIDE.md)
> - **`weighting:` is undeclared and four rows carry a `weight`.** A reader cannot tell what the
>   numbers mean. Declare the scale, or declare that the module authors none. → [`module-weights`](../module-weights/GUIDE.md)
> - **The licence is unstated and the rows came from a PGx source.** The compile gate reads
>   `licensing.csv` and nothing else. → [`module-start`](../module-start/GUIDE.md)

**Everything evident and mechanical is applied silently and never listed.** A rename, a deprecated
spelling, a column that moved: no judgement exists to exercise, so exercising one is noise. Anything
**checked or authored** — a genotype, a `weight`, a `clin_sig`, a conclusion, a `provenance_quote` —
goes in the list untouched. `module-revise` carries that discriminator as a table and owns it; when you
cannot tell which side a case falls on, surface it, because over-surfacing is recoverable and a silent
wrong write is not.

### The voice

**A module that is behind the current release is out of date, not defective.** It usually met the
requirements that existed when it was written, and those are different claims about somebody's work.
Never *broken*, *invalid* or *failing* about a module being brought forward — say **"this needs these
decisions to work in the latest"** and then list them. Failure language is reserved for a module wrong
on its own terms: a shifted coordinate, a quote that is not in the paper.

**A published module is not behind either.** It is a module whose next version has decisions waiting,
and there is no schedule it is late for. There is no versioning contract, no milestone a module owes
anybody, and no agent may withhold a publish or a bump waiting for one. `module-revise` has the whole
argument.

## Two readings that change everything and are easy to skip

**Is this the module's first pass, or its twenty-fifth?** A directory with a closure, an `authorship:`
block or a `published.json` is somebody's finished work, and the correct entry point is `module-revise`
rather than the spine. Almost every real session is a second pass.

**Was this authored here, or handed over?** A bundle from an outside session typically arrives with the
deprecated sidecar spelling, no attestation, no closure and coordinates nobody has checked. Triage it
before extending it, and do not assume the previous author's convention — [`module-start`](../module-start/GUIDE.md) owns the
triage and carries the case where four modules shipped thousands of shifted coordinates through every
offline gate.

## Where to go next

| The reading says | Load |
|---|---|
| nothing exists yet, or a bundle needs triage | [`module-start`](../module-start/GUIDE.md) |
| the module is published and you have no copy of it | fetch it with `registry_download`, then re-read here |
| a source publishes rows nobody drafted | [`module-draft`](../module-draft/GUIDE.md) |
| placeholders, or cells only a pilot can settle | [`module-curate`](../module-curate/GUIDE.md) |
| no coordinates, no ids, or a stale sidecar | [`module-enrich`](../module-enrich/GUIDE.md) |
| assertions nobody compared against a source | [`module-check`](../module-check/GUIDE.md) |
| rows are settled and nothing is built | [`module-compile`](../module-compile/GUIDE.md) |
| built, but no closure and no methodology | [`module-close`](../module-close/GUIDE.md) |
| finished and unpublished, or rehearsing | `module-publish` |
| the module already exists and something moved | `module-revise` |
| a pass has to be re-run over what it already wrote | [`module-refresh`](../module-refresh/GUIDE.md) |
| you need to know what actually changed between two states | [`module-diff`](../module-diff/GUIDE.md) |
| where a file may sit, and the full name roster | [`module-tables`](../module-tables/GUIDE.md) → `references/LAYOUT.md` |
| a message you do not recognise | `module-symptom` |

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action. Two readings
belong to this skill rather than to a stage, because they are what a status pass turns up:

- *"This module records no closure"* — the authoring was never declared finished, or a later edit moved
  the hash and dropped it. Not a defect; a decision about whether the module is done.
- *"`sources.csv` is the deprecated spelling of this table"* — evident and mechanical. Rename it, say
  nothing, and do not finish the rename into `sources.parquet` or `manifest.sources`.
