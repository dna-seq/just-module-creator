---
name: module-refresh
description: >-
  Bring a module up to date with a source that has moved, or re-derive a sidecar that went stale.
  Covers merge-not-clobber and why a re-run refreshes nothing, what deleting each sidecar costs table
  by table, writing to the file you read, what a re-draft repairs and what it cannot, and the two
  passes that break on a second run. Load this whenever you are re-running something that already ran.
  Triggers: "re-run enrich", "why did it not update", "refresh", "refresh_sidecar", "newer ClinVar",
  "delete resolution.csv", "stale sidecar", "re-draft", "source released", "it did not change",
  "already present", "re-enrich", "newer gnomAD", "why is this still the old value", "will I lose my
  overrides", "re-derive without losing curation".
---

# Refresh a source, re-derive a sidecar

**Lifecycle stage:** 2 or 4, re-entered. Reached from `module-revise`.

## The one fact that governs everything here

> **A re-run does not refresh anything already recorded. To re-derive a sidecar it has to be deleted
> first — and the delete is what discards hand-curated rows along with the stale ones.**

Every derived sidecar is **merge-not-clobber**: an existing row is authoritative and a re-run *adds*
to it rather than replacing it. That is not a limitation — it is the rule that makes these tables
human-overridable, which is the whole reason a curator may correct one.

So the failure mode is silence. You re-run the pass, it reports success, and nothing changed. **If you
expected a value to move and it did not, the file is still there.**

### `refresh_sidecar` is the interface. Do not do the delete by hand

**It is in every tier — there is no flag to set and nothing to switch on.** If you were about to write
`rm resolution.csv`, this is the tool you were reaching for, and it is strictly better than the `rm`:

It copies the sidecar out, **reads the copy back and hashes it**, and only then deletes — so a capture
that did not verify means nothing is touched. Then it re-derives, classifies every row against the live
fact fields, **reapplies the rows it can prove a human wrote**, and **reports the rest without picking a
side.** It also tells you whether the table's fact signature moved, which is the canary in `module-diff`.

**It resumes if it dies mid-sequence** — a capture is never taken over an unfinished one, so a second
attempt is a repair rather than a second loss.

**One gate, and it is on the argument rather than on the tool.** A sidecar whose pass is sized by how
much the world has published, rather than by the rows you wrote, still needs `JMC_MODE=extended`:
`literature.csv` searches per variant across the corpus, and `gwas_effects.csv` costs `1 + 2N` requests
per variant, measured at 382 for one real module. Naming one of those in the default tier **raises**,
and the refusal lists the names that are reachable — read it from there rather than from any file,
because it is generated from the roster the tests pin. Everything else, `resolution.csv` included, runs
in the default tier.

**Five honest limits, because a tool that hid them would be worse than the manual route:**

- **It refuses offline**, up front, before touching anything. A re-derivation with no egress is not a
  re-derivation.
- **It refuses `licensing.csv`.** That sidecar has no producer — a licence row is a side effect of a
  pass that took data, and a hand-copied row has none — so there is nothing to re-derive it from.
- **It refuses to classify against a partial re-derivation.** An unreachable source, a pass that did
  nothing, an empty fresh table → your bytes are restored verbatim. A table that was never filled would
  otherwise report every real row as one the source withdrew.
- **It refuses the two corpus-sized sidecars outside the extended tier**, as above — and the refusal is
  the only thing standing between you and the by-hand sequence further down.
- **A `source="manual"` row is not always reapplied, and this one will surprise you.** An online run
  that reaches Ensembl writes a `status="not_found"` row for an rsID it cannot resolve. So your manual
  row's subject *is* present in the fresh table, and it lands in **conflicts** — reported, left on
  disk in the capture, not put back. When no link ran for that rsID there is no fresh row and the
  manual row **is** reapplied. Read the report rather than assuming which happened.

The by-hand sequence is still documented below, and it has shrunk to one job: refreshing
`literature.csv` or `gwas_effects.csv` on a server you cannot widen. It is no longer what you do on an
ordinary refresh, and reaching for it there costs you the verified capture, the row classification and
the canary.

## What deleting each sidecar costs

**Read this before deleting by hand — and prefer not to.** The cost column is what a bare `rm` plus a
re-run will not give you back. `refresh_sidecar` reapplies the provably-authored rows from its capture
and reports the rest instead of losing them, which is the whole difference between the two routes.

| Sidecar | A re-run… | Delete to re-derive when | Deleting costs |
|---|---|---|---|
| `resolution.csv` | skips every `variant_key` already covered | an identity column changed, or a locus resolved wrongly | **hand-authored `source=manual` rows** — real, and not reproducible. `reference_examples/cyp2c9_warfarin_grch37` carries three |
| `frequencies.csv` | merges; existing rows win | the variant set changed, or you want a newer gnomAD | normally nothing hand-written |
| `gene_metrics.csv` | merges, and a `source="manual"` row suppresses the fetch for its `(gene, dataset)` since enricher 0.6.6 | the gene set changed | curator overrides |
| `literature.csv` | refetches nothing, and **will not back-fill** the 0.6 licence columns onto older rows | you need the licence columns, or a `doi_checked` verdict re-put | a curator's deliberate **blank**, which merge cannot distinguish from an absent value |
| `gene_validity.csv`, `clinical_assertions.csv` | merge, on the same governing rule | the source cut a newer release | curator overrides |
| `licensing.csv` | never clobbers a row — **except** `withdraw_stale_dataset` blanking `dataset` when rows were actually added, and `draft_digest` being re-stamped | rarely; those two machine-owned columns maintain themselves | the curator's hand-written **terms** — which is exactly what never-clobber exists to protect |
| `verification.json` | replaces **per check**, and never erases a check this run did not put | never by hand | the record of every other check |

**13 of 13 `literature.csv` rows in the corpus lack `doi_checked`**, because merge-not-clobber never
re-asks. Only deleting the sidecar clears a stale DOI verdict. That is the shape of this whole table:
the absence is not "nobody checked", it is "nobody deleted".

**A no-op run writes nothing rather than a zero.** `literature --offline` on a module that already has
a `literature.csv` writes no records at all — because the verification merge replaces per check, and a
true `subjects=5, findings=1` must not become *"never asked"* on a run that changed nothing.

## Two rules that only bite on a second pass

**Write to the file you read.** A module carrying the old `sources.csv` spelling, or carrying its
sidecars under `derived/`, must be written back the same way. Both copies present is an **error naming
both paths** (`layout.SidecarCollision`) — never a merge, never newest-wins, because two fact-hashed
human-overridable copies are two legitimate claims. `module-tables` → `references/LAYOUT.md` has the
normalisation in full.

**A derived column you expect to move needs the file gone, not the pass re-run.** The article licence
rights are the sharpest case: `article_terms` has exactly one call site, in the enricher's fetch loop,
and its values are **persisted onto the row**. The compiler reads `row.commercial_use` and never
re-derives anything. So after changing a licence mapping or correcting a `license` cell, **delete
`literature.csv` and re-run** — otherwise every stale right survives, silently. Several upstream docs
said the opposite and were wrong.

## What a re-draft does, and what it cannot repair

**A re-draft appends and reports; it never rewrites.** A row whose key already exists comes back
`already_present` or `differs`.

- `already_present` is **inert**. Nothing happened and nothing needed to.
- `differs` is the interesting one: **the source disagrees with something you already authored.** It is
  left unchanged deliberately, because only you know which side is right. This is a decision, not a
  warning to clear.
- A **partial** row matches on its *identity* columns rather than its natural key, so a re-draft after
  a human filled a stubbed `genotype` adds nothing rather than duplicating.

**A re-draft that appends nothing is inert** — it does not even move the digest. `merge_sources_csv` is
`setdefault`, `stamp_draft_digest` is a no-op with nothing appended, and `withdraw_stale_dataset` fires
only when rows were actually added; running `record_source_terms` twice against one spec directory
gives a byte-identical file.

**And a drafter fix does not reach a module already drafted.** This is the trap, and the two shapes
need opposite remediations:

| The old bug | A plain re-run | What you must do |
|---|---|---|
| **skipped** rows | converges exactly — the skipped rows are simply added | re-run, and you are done |
| **wrote** rows under an identity that has since **moved** | restores the lost records and **leaves the collapsed ones beside them** | re-run, then delete the stale rows by hand |

Measured on MLH1 after enricher 0.6.3: the ClinVar fix moved identities → **0 missing, 31 stale**; the
ClinPGx fix only skipped → **0 stale, 0 missing**. *Skipped converges; moved does not.* Since enricher
**0.6.4** the ClinVar drafter **names** the superseded rows and deletes nothing, so you can act on the
report instead of diffing.

🚧 **ROADWORKS — that supersession sweep does not reach `studies.csv`.** `_superseded_rsid_rows` has
one call site and is handed the **`variants.csv`** append report. So a ClinVar re-draft leaves both the
stale rsid-only study row and its coordinate-keyed replacement — and it surfaces only as a *"Studies
reference variants not in variants.csv"* orphan warning, which **blames the citation** rather than the
re-draft. **Guard:** after any re-draft, diff `studies.csv`'s rsIDs against `variants.csv`'s and delete
the stale rows before compiling.

## Two passes that break on a second run

**`enrich_gene_metrics` re-runs cleanly as of enricher 0.6.6** (upstream **RM104**). It used to raise
`UnboundLocalError` out of the pass on the **ordinary idempotent re-run** — every gene already carrying
a `gnomad*` row — and on any module with no `variants.csv`, because `reference` was bound inside
`if wanted:` and read below it. It was outside `GeneMetricsEnrichmentError`, so the one `except` that
exists for this caller did not hold. If you are on an older enricher, run the pass once and catch
`Exception` at that call site.

**A `source="manual"` correction on `gene_metrics.csv` now suppresses the fetch** (upstream **RM109**,
enricher 0.6.6): the suppression set is derived from the merge key `(gene, dataset)` rather than from a
`gnomad`-prefix scan over `source`, so an honest override no longer lands *beside* the fetched row as a
second row under one key, contradicting it with zero compiler warnings. The scoping is deliberate — a
ClinGen dosage row for the same gene carries a different `dataset`, so it is a different key and does
not suppress anything. **Check an inherited `gene_metrics.csv` for pairs written before 0.6.6**;
nothing removes them, because the merge keeps what is already there.

🚧 **ROADWORKS — a ClinGen re-curation appends beside the old row with nothing marking it superseded.**
ClinGen's `assertion_id` embeds the curation timestamp, so a re-curated assertion misses the merge key.
`manifest.gene_validity.classifications` can then publish a pair as far apart as
`["definitive", "refuted"]` — or `definitive` (2019) beside `moderate` (2026) — with no currency notion
anywhere. **Guard:** read `classifications` as *everything ever curated*, never as the module's current
call; sort by `classification_date` per `(gene, disease, moi, submitter)` and delete stale rows by hand
before publishing. Upstream **RM108**.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** deleting a sidecar you are about to re-derive, once the capture is
verified; writing a refreshed sidecar back to the file and spelling you read it from; re-running a pass
whose only failure was an outage; deleting a superseded rsid-only study row once the coordinate rows
demonstrably cover its records.

**Surface it, and let a pilot settle it:**

- **Which side of a `differs` is right.** No tool will pick. The source is not automatically newer or
  better than what you authored.
- **Whether a hand-curated row should survive.** Deleting to refresh is all-or-nothing per file. If one
  row in `resolution.csv` is `source=manual` and the rest are stale, you copy that row out first.
- **Whether a blank was deliberate.** Merge cannot tell a curator's considered blank from an absent
  value, so only you know whether re-deriving would overwrite a judgement.
- **Whether the prose still holds.** A refreshed module whose README describes the old data is worse
  than a stale module, because it now asserts something false. Nothing checks this.

## What refreshing moves

A re-run that only rewrites a derived sidecar **does not un-close the module** — the sidecars are
outside the attestation's binding. What un-closes is an authored edit, which is what a *re-draft* does
the moment it appends a row.

| You did | `content_signature` | `artifact.digest` | closure |
|---|---|---|---|
| re-ran a pass, nothing new | same | same | kept |
| re-ran a pass, sidecar grew | same | moved | kept |
| re-drafted, rows appended | **moved** | moved | **dropped** |
| re-drafted, nothing appended | same | same | kept |

**Currency of the source is a different question from the binding**, and is read off each record's own
`release` — never off whether the attestation still holds.

## What this stage cannot do

**Nothing tells you a source has moved.** No watch, no notification, no version check against ClinVar
or CPIC. You find out because you looked.

**Nothing merges two versions of a sidecar intelligently.** The choice is keep-everything or
delete-everything, per file. There is no three-way merge and no per-row refresh.

**Nothing repairs a module whose coordinates were wrong.** Deleting `resolution.csv` re-derives the
lookup; it does not fix an authored `start` that was off by one. `module-enrich` owns that.

**A refresh does not make a module reviewed.** Bringing data up to date is not the same as somebody
reading it — see `module-revise` for what a review pass actually is.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream text to cause and action. The three you will
meet here:

- *"Studies reference variants not in variants.csv"* after a re-draft — usually the stale rsid-only
  study row above, not a bad citation.
- `already_present` / `differs` — inert, and a decision, respectively.
- `UnboundLocalError` out of a gene-metrics re-run — an enricher older than 0.6.6, not your module.

## Where to go next

| You need | Load |
|---|---|
| which of the six second-pass kinds you are in | `module-revise` |
| what actually moved, and which signature says so | `module-diff` |
| the sidecar you are about to delete, in full | `module-tables` → `references/<name>.md` |
| the drafter's report, read properly | `module-draft` |
| re-resolving coordinates after an identity change | `module-enrich` |
