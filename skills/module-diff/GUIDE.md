---
name: module-diff
description: >-
  Work out what moved in a module and what it means. Covers the identity ledger, the decision tree over
  content-signature versus the eight fact signatures versus artifact.digest, the canary that is the only
  way to detect an upstream source revising an answer, how to find what exactly changed when nothing
  computes it, and the honest fact that no tier compares two versions. Triggers: "what changed", "why
  did the digest move", "diff two versions", "canary", "did the source change", "content_signature",
  "compare modules", "compare_modules", "is this stale", "fact signature", "the digest moved and I changed nothing",
  "resolution_signature", "did upstream change its answer".
---

# What moved, and what that means

**Lifecycle stage:** read from 6 (compile) and 10 (feedback). Reached from `module-revise` and
[`module-refresh`](../module-refresh/GUIDE.md).

A module's hashes are not just dedup keys — **paired, they are a diagnostic instrument**, and the only
one this format has for detecting that the world moved underneath a module. Read them as a decision
tree, never as a single bit.

## The numbers to watch — count them, do not assume

Three families, and you compare them **across two compiles of the same module**, not across two
different modules.

| | Where it lives | Hashes |
|---|---|---|
| `content_signature` | manifest, top level | the **authored** rows as parsed, before resolution |
| a **fact signature** | one per derived table, in that table's own manifest block | that table's *facts*, not its bytes |
| `artifact.digest` | `manifest.artifact.digest` | the compiled **parquet bytes**, as a Merkle root |

**There are eight fact-signature families**, one per derived table:
`compilation.resolution_signature`, and `signature` inside `frequency`, `gene_metrics`, `literature`,
`gene_validity`, `clinical_assertions`, `gwas_effects` and `sources`. **An absent block means the
module carries no such table** — it does not mean the signature is missing.

> **Count the ones your module actually publishes and watch those.** A module carries between one and
> eight. Do not take a number from any prose, including this file: `reference_examples/hfe_hemochromatosis`
> was famously "three numbers to watch" and today publishes **four** — it gained a `gwas_effects.csv`
> since that was written. Read the manifest.

## The decision tree

| `content_signature` | a fact signature | `artifact.digest` | What happened |
|---|---|---|---|
| same | same | same | nothing. A recompile |
| same | same | **moved** | **something *you* did** — see the three routes below |
| same | **moved** | moved | **the canary.** Nobody authored anything and a derived fact changed: **the upstream source said something different this time** |
| **moved** | any | moved | somebody edited the module |

**Row 3 is the only row that means the world moved.** Every other row is an act by the holder of the
module. That is the whole value of the pairing, and it is why the placement of individual columns is
deliberate: `dataset` is **inside** `SOURCE_FACT_FIELDS`, so widening a module from a newer snapshot
shows up as a moved `source_signature` rather than a silent byte, while `draft_digest` is **outside**
it, so a re-stamp lands in row 2. Both placements exist to keep the rows distinguishable.

### Row 2 has three routes, not two

Upstream's own account of this row names two — a delete-and-re-derive, and a toolchain change — and
concludes that nothing upstream can produce it. **That conclusion holds. The enumeration is short by
one:**

1. **You deleted a sidecar and re-derived it** against an unchanged source. Fresh `fetched_at`, same
   facts, so the bytes move and no signature does.
2. **The toolchain moved under you.** Parquet is not byte-deterministic across polars/arrow versions,
   which is why reproducibility is scoped to a fixed `compiler_version` — and why dedup surfaces key
   on `content_signature` rather than the digest.
3. **You reordered authored rows.** Measured on `hfe_hemochromatosis`: reversing `variants.csv`'s rows
   leaves `content_signature` at `sha256:44ad4449…` — *identical* — and moves `artifact.digest` from
   `sha256:6c6e103d…` to `sha256:83635ace…`. Authored row order is preserved into the parquet, so the
   bytes move; `content_signature` does not read order, so it does not.

Route 3 is still a deliberate act by the holder, so **row 3 remains the only canary** — but an author
who reordered rows and sees a moved digest will hunt for a delete or a toolchain change and find
neither. Filed upstream.

**A provenance column also moves the digest and no signature** — but note that is the *mechanism*
demonstrated by hand, not what a re-run does. No merge restamps `fetched_at`.

### The trap on the other side: `content_signature` moves and the rows look identical

**Change `genome_build` in `module_spec.yaml` and nothing else.** `content_signature` moves — correctly,
because the declared build is part of the content: HFE C282Y is `6:26,093,141` on GRCh37 and
`6:26,092,913` on GRCh38, so identical coordinate rows on two assemblies describe **loci 228 bp apart**.
Upstream made the signature build-aware for exactly this reason.

**But a row-level comparison reports zero changed rows, in every table.** Measured on
`pathogenic_clinvar`: `239c81da…` → `5210c3fe…`, and the key lists are character-for-character
identical across the two builds, because `draft.natural_key` is build-independent. So the two sides
name the same keys and mean different places, **and the reassuring answer is the dangerous one.**

The realistic way to hit it is not contrived: "lift over" a GRCh37 panel by editing the yaml and not
the coordinates.

> **So read `genome_build` first, before any row count.** If the declared builds differ, the row
> comparison is **not comparable** rather than clean — and no count from it means anything.

### Two identity scopes, not one

`content_signature` reads the **authored** tables. `licensing.csv` is authored **and outside it** — a
licence fact edit leaves `content_signature` at `44ad4449…` on `hfe_hemochromatosis` and moves
`source_signature` alone. So "authored" and "in `content_signature`" are different sets, and a diff
that lumps them reports a licence correction as a content change. Label the scope per table.

### Why this is worth doing at all — a measured case

The published catalog contains **an unrecorded change and an unrecorded revert**, both found in one
command. `big_five_personality_snps` 1.0.1 rewrote `state` on **990 of 990 rows** while its changelog
names three other columns; 2.0.0 reverted it while saying *"variant set unchanged from 1.0.0"*. Neither
is visible from the version numbers, the changelog, or the card. **A changelog is a claim; the tables
are the record.**

## The canary — an operation, not a signal

Here is the part that catches people. **Merge-not-clobber means a source that quietly revised an
existing answer moves nothing at all** — no stamp, no signature, no digest. The row was already
recorded, so the re-run never re-asks. **Silence is not evidence that nothing changed.**

So detecting upstream drift *is* the delete-and-re-derive. There is no passive check.

**Run `refresh_sidecar` rather than doing it by hand.** It is in every tier, and it exists because the
manual sequence is destructive: it captures the sidecar first, deletes, re-derives, classifies every
row, reapplies what is provably yours, and **reports what it cannot tell apart.** The one thing that
can slow you down is naming `literature.csv` or `gwas_effects.csv` — those two
raise, and the refusal names what is reachable. [`module-refresh`](../module-refresh/GUIDE.md) owns the tool.

**By hand, when the tool refused the sidecar you need:**

```
1. note the table's fact signature from the manifest
2. save every hand-authored row out of the sidecar   <- NOT OPTIONAL
     resolution.csv -> the source=manual rows; genuinely not reproducible
     others         -> any row whose `source` is not the fetcher's
3. delete the sidecar
4. re-derive it
5. compare the fact signature
     moved -> the source changed its answer under you
     same  -> it did not
6. re-apply your saved rows
7. re-run the checks and close again
```

**And either way, one bucket cannot be resolved.** A fetched row whose facts differ from what you had
is *either* your cell edit *or* upstream's revision, and **two data points cannot say which.** Nothing
distinguishes them unless `source` was changed too — which is exactly why `source` sits **outside**
every fact-field set, and why marking an override honestly is worth doing at the time you make it. A
tool that guessed here would be inventing a verdict, so the report is the honest output **for as long
as `source` is the only marker there is** — a filled authoring log would settle it outright, and
`CLAUDE.md` §2 now requires every authoring move to go through one. The ambiguity is a consequence of
what we record, not a principle.

Deleting the sidecar is also what discards curator overrides — so the drift detector and the override
problem are one problem, tracked upstream as **RM83**.

## What exactly changed — `compare_modules`

Signatures tell you **what kind** of thing moved. They cannot tell you **what**. `compare_modules`
does, offline:

```
compare_modules(left_dir="./v1", right_dir="./v2")
```

It answers at three grains in one report, because the caller does not yet know which one they need:
`content` and `frame`, then per-table presence and counts, then **rows grouped by the set of columns
that changed**. That grouping is the reason the row level is readable at all — 1,190 rows moving in one
column for one reason is one fact printed 1,190 times, and grouped it is one line.

**Read `frame` first.** When the two sides declare different builds the row comparison is *not
comparable* rather than clean: the natural key is build-independent, so two assemblies produce
character-identical keys naming loci hundreds of bases apart, and "zero rows changed" is then the
dangerous answer.

**`tables[].identity_scope` is the field to read second.** It says *which hash your edit will move* —
and `licensing.csv` is authored and **outside `content_signature`**, so a licence edit that looks
invisible is not: it moves `sources.signature` alone.

For two published versions, the acquisition is still yours and the comparison is not:

```
registry_download(target="prod", namespace=ns, name=name, version="1.0.0", dest="./v1")
registry_download(target="prod", namespace=ns, name=name, version="2.0.0", dest="./v2")
compare_modules(left_dir="./v1", right_dir="./v2")
```

The download verifies the bytes as it fetches — a failure raises rather than
leaving you comparing a module you cannot trust — and it brings the authored inputs unless you pass
`include_inputs=false`, which is what makes the comparison a comparison of specs rather than of
parquet. Both trees arrive in the same flat shape, because the tool does not expose a layout choice;
`derived/` is only a presentation and [`module-tables`](../module-tables/GUIDE.md) → `references/LAYOUT.md` has it.

**What it will not do**, and none of it is "not yet": no write path and no parameter that could become
one; no verdict on which side is right; **no pairing of rows whose natural key changed** — one removed
and one added, never one changed, because pairing asserts *this row became that row*; no changelog
prose; no version-bump suggestion. For the raw cells, run `diff` — it does not reproduce that, badly.

**It cannot perform the canary either.** Detecting that a source revised an answer means deleting a
sidecar and re-deriving it, and only `refresh_sidecar` knows which side it just derived. A comparator
sees two recorded files. What it adds is the case refresh cannot serve: two states no single refresh
run produced — two versions, or a local spec against a downloaded one.

*(`compare_to_published` — "am I ahead of the catalog", manifest-only, no download — is specified in
`docs/DESIGN-version-compare.md` and is **not built**. `RM19`.)*

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** re-pinning a stored `artifact_digest` after a compiler upgrade; reading
`genome_build` before any row count, and reporting the comparison as *not comparable* when the declared
builds differ; downloading both versions `--layout flat` so the two trees have the same shape.

**Surface it, and let a pilot settle it:**

- **Which side of an ambiguous row is right.** The tool will not pick and neither will the format. The
  source is not automatically newer or better than what you authored.
- **Whether a moved digest matters.** A digest move with every signature still is, by construction,
  something you did — but *you* know whether reordering rows or swapping a toolchain was intended.
- **Whether the module is now stale.** Nothing computes staleness. `resolution.trusted` is a
  registry projection about resolution, not a verdict on your annotations.

## What this stage cannot do

**Nothing relates two versions in the artifact or the catalog.** No changelog generation, no parent
digest, no monotonic-stats requirement; the registry records **no content relationship between
versions at all** — the one cross-version rule is the duplicate-content gate, and it exempts a later
version of the same module. `compare_modules` compares two directories you already have; it does not
create a relationship, and nothing stores its answer.

**No consumer is notified that a new version exists.** No badge, no SemVer comparison anywhere in the
install path. Installed-vs-current is exact version-string equality, and a new version replaces the old
one in place — two versions of one module cannot coexist locally.

**An annotation run records no module version.** The output manifest names each module by *name* and
carries no version, no digest and no source URL. So a rendered report cannot be tied to the module
bytes that produced it, and **nothing can answer "which of my saved results are stale"**.

**A digest match is not a correctness claim.** `--strict`, a digest match and a reproducible build all
mean *reproducible*. A module shifted one base reproduces perfectly.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream text to cause and action. What you will meet
here is usually not a message but a surprise:

- *the digest moved and I changed nothing* → row 2. Check the three routes, reordering included.
- *I re-ran the pass and nothing changed* → merge-not-clobber. You did not delete the file.
- *`verification.json` is stale* → an authored edit un-closed the module. `module-revise`.

## Where to go next

| You need | Load |
|---|---|
| to actually re-derive without losing curation | [`module-refresh`](../module-refresh/GUIDE.md) |
| which kind of second pass you are in | `module-revise` |
| what a table contributes to which signature | [`module-tables`](../module-tables/GUIDE.md) → `references/<name>.md` |
| what a consumer will and will not notice | [`module-consumer`](../module-consumer/GUIDE.md) |
| the download layouts | [`module-tables`](../module-tables/GUIDE.md) → `references/LAYOUT.md` |
