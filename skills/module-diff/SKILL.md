---
name: module-diff
description: >-
  Work out what moved in a module and what it means. Covers the identity ledger, the decision tree over
  content-signature versus the eight fact signatures versus artifact.digest, the canary that is the only
  way to detect an upstream source revising an answer, how to find what exactly changed when nothing
  computes it, and the honest fact that no tier compares two versions. Triggers: "what changed", "why
  did the digest move", "diff two versions", "canary", "did the source change", "content_signature",
  "compare modules", "is this stale", "fact signature", "the digest moved and I changed nothing",
  "resolution_signature", "did upstream change its answer".
---

# What moved, and what that means

**Lifecycle stage:** read from 6 (compile) and 10 (feedback). Reached from `module-revise` and
`module-refresh`.

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

## The canary — an operation, not a signal

Here is the part that catches people. **Merge-not-clobber means a source that quietly revised an
existing answer moves nothing at all** — no stamp, no signature, no digest. The row was already
recorded, so the re-run never re-asks. **Silence is not evidence that nothing changed.**

So detecting upstream drift *is* the delete-and-re-derive. There is no passive check.

**Use the refresh tool if your build has one** (`refresh_sidecar` — check your tool list). It exists
because the manual sequence is destructive: it captures the sidecar first, deletes, re-derives,
classifies every row, reapplies what is provably yours, and **reports what it cannot tell apart.**

**By hand, if you have no such tool:**

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
tool that guessed here would be inventing a verdict; the report is the correct output.

Deleting the sidecar is also what discards curator overrides — so the drift detector and the override
problem are one problem, tracked upstream as **RM83**.

## What exactly changed — nothing computes it, and there is still an answer

Signatures tell you **what kind** of thing moved. They cannot tell you **what**. Two steps:

| Question | How |
|---|---|
| **What kind moved?** | the decision tree above, off the two manifests |
| **What exactly?** | download both versions with their inputs and diff the authored CSVs directly |

```
registry-client download <ns> <name> 1.0.0 ./v1 --with-inputs --layout flat
registry-client download <ns> <name> 2.0.0 ./v2 --with-inputs --layout flat
diff ./v1/variants.csv ./v2/variants.csv
```

**No tool does that second step for you.** It is still the answer, and it is two commands. Diff the
**authored** tables — `variants.csv`, `studies.csv`, the table kinds — because those are what
`content_signature` reads; a derived sidecar will differ for reasons that mean nothing.

Use `--layout flat` for this, not `split`: a diff is easier when both trees have the same shape, and
`derived/` is only a presentation. `module-tables` → `references/LAYOUT.md` has the layouts.

## What only an author may decide

- **Which side of an ambiguous row is right.** The tool will not pick and neither will the format. The
  source is not automatically newer or better than what you authored.
- **Whether a moved digest matters.** A digest move with every signature still is, by construction,
  something you did — but *you* know whether reordering rows or swapping a toolchain was intended.
- **Whether the module is now stale.** Nothing computes staleness. `resolution.trusted` is a
  registry projection about resolution, not a verdict on your annotations.

## What this stage cannot do

**Nothing compares two versions of a module.** No diff in any tier, no changelog generation, no parent
digest in the artifact, no monotonic-stats requirement. The registry records **no content relationship
between versions at all** — the one cross-version rule is the duplicate-content gate, and it exempts a
later version of the same module.

**No consumer is notified that a new version exists.** No badge, no SemVer comparison anywhere in the
install path. Installed-vs-current is exact version-string equality, and a new version replaces the old
one in place — two versions of one module cannot coexist locally.

**An annotation run records no module version.** The output manifest names each module by *name* and
carries no version, no digest and no source URL. So a rendered report cannot be tied to the module
bytes that produced it, and **nothing can answer "which of my saved results are stale"**.

**A digest match is not a correctness claim.** `--strict`, a digest match and a reproducible build all
mean *reproducible*. A module shifted one base reproduces perfectly.

## Symptoms

`../create-module/references/SYMPTOMS.md` maps upstream text to cause and action. What you will meet
here is usually not a message but a surprise:

- *the digest moved and I changed nothing* → row 2. Check the three routes, reordering included.
- *I re-ran the pass and nothing changed* → merge-not-clobber. You did not delete the file.
- *`verification.json` is stale* → an authored edit un-closed the module. `module-revise`.

## Where to go next

| You need | Load |
|---|---|
| to actually re-derive without losing curation | `module-refresh` |
| which kind of second pass you are in | `module-revise` |
| what a table contributes to which signature | `module-tables` → `references/<name>.md` |
| what a consumer will and will not notice | `module-consumer` |
| the download layouts | `module-tables` → `references/LAYOUT.md` |
