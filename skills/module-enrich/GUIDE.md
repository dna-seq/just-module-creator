---
name: module-enrich
description: >-
  Resolve rsIDs to coordinates, mint allele ids, and read the one report that can catch a mistake no
  offline gate can. Covers the resolver chain and what `--offline` really costs, the off-by-one
  signature and why the count is a floor, why unreachable is not absent, recovering an rsID from an
  old-assembly coordinate, what a filled coordinate changes downstream, and the edits that corrupt a
  minted id.
  Triggers: "enrich", "resolve coordinates", "resolution.csv", "ref mismatch", "unresolved rsID",
  "GRCh37 coordinate", "hint recover", "VRS", "not_found", "unreachable", "vrs_id", "expanded to N
  rows", "pseudoautosomal".
---

# Stage 4 — enrich

**Lifecycle stage:** 4. The first of the two stages that fetch, and **the only tier that may hold a
reference sequence** — so the only place these checks can live at all.

This stage turns what the author wrote into something a VCF can join, and reports every disagreement
between the module and the genome. **Curate before you enrich**: a drafted row leaves `<<REPLACE>>`
where a human must decide, and that placeholder makes every loader refuse the file — `enrich_module`
included, deliberately, because forward resolution is allele-aware and a placeholder genotype would skip
the allele filter on exactly the one-to-many rsIDs that need it.

## Running it

```
enrich_module(spec_dir="spec")                  # → resolution.csv: rsid ↔ coordinate, VRS ids, ref check
enrich_module(spec_dir="spec", strict=True)
enrich_module(spec_dir="spec", offline=True)    # caches only, zero egress — and the ref check does NOT run
```

It blocks, and there is no task id and nothing to poll — the tool is declared task-capable, but a client that sends no task metadata gets a plain synchronous call, and the usual ones do not send it. Progress is reported before the work and after, never during, so what you hit on a large module is a client idle timeout. Nothing is written until the end, so an interrupted run persists nothing; and the interruption is client-side only, so the work continues here and still writes when it finishes. After a timeout, count `resolution.csv` against the authored subject count before trusting anything downstream. Several links run in order —
**Ensembl cache → ClinVar snapshot → live Ensembl → gnomAD** — and three checks fold in: the reference
base, `clin_sig`, and rsID currency. Snapshots are provisioned from HuggingFace when absent.

**`offline=True` is not a cheaper version of the same run.** It restricts to local caches, and the
reference check — the only thing that can catch a shifted coordinate — **does not run at all**. An empty
result from an offline run means *unchecked*, never *clean*.

**Substitution VRS ids mint offline; indels and MNVs need the reference sequence.** Expect ~50% id
coverage on an indel-heavy module offline against ~99% online. Re-run `vrs mint` **without** `--offline`
to fill the rest.

## The one mistake nothing offline can catch

**`ref mismatch: N row(s) — coordinate shifted 1 base to the right: `start` is the 1-based VCF position
and must not be converted.`**

Read that line as being about **`start`**, not about `ref`. Your `ref` cells are right; your `start`
cells are each one too low, which is exactly what subtracting one from a VCF position produces. The
field that names it is `RefMismatch.shift`.

**Why this report matters more than any other in the toolchain:** a uniformly shifted module passes
`validate`, passes `compile --strict`, reports `fully_resolved: true`, and mints `ga4gh:VA.…` ids the
compiler then reports **verified**. It has happened at scale — **3,038 rows across four modules**, every
one of which cleared every offline gate. [`module-curate`](../module-curate/GUIDE.md) has the authoring-side rule and the one-call
check that catches it on row 1 instead of row 3,000.

**The count is a floor, not a total.** The check can only see rows where the neighbouring base differs
from your `ref` — roughly three in four. And **every id minted for a shifted row names the wrong place
and must be regenerated, not patched**: fix every `start`, delete `resolution.csv`, re-enrich.

Two neighbouring messages, different meanings:

- *"single-base ref disagrees at a position nothing else contradicts"* — the residue. Either the `ref`
  cell really is wrong, or it is a shifted row whose neighbours happen to carry the same base. If the
  run also reported a shift group, assume these belong to it.
- *"multi-base ref disagrees, so the allele spans the wrong bases"* — the corrupting case, and the
  reason `ref` is checked at all: a multi-base `ref` **sets the interval**, so a wrong one mints a
  well-formed id for an allele you did not mean.

All three are **reported, never repaired** — upstream preserves the authored value so the evidence of
the disagreement survives, and that report is theirs, carried across this boundary field for field.

## Unreachable is not absent

**A failed request writes no row.** It lands in `unreachable_rsids`, and **that list is the only thing
worth re-running.** A row that is genuinely `not_found` is a real negative; a row that is missing because
Ensembl 500'd is a question nobody asked.

**Deleting a variant because `enrich` missed it while `lookup_variant` resolves it is the wrong repair**
— it cost a real module `rs6265`. Re-run the unreachable list before touching a row.

The same distinction runs through the downstream passes: `not_found` (the source has no record) is not
`not_covered` (the source cannot cover that locus at all — the Y PAR), and neither is a failure.

## What a filled coordinate changes

- **`resolution.csv` is the pin.** Once it and `literature.csv` exist, every later compile is offline
  and reproducible.
- **It reaches three positional tables as well as `variants.csv`** — `pharm_variants.csv`,
  `haplotypes.csv`, `heteroplasmy.csv` — in `validate` **and** `compile` since format 0.6. The set is
  derived, not listed: every table kind whose model carries both `chrom` and `start`.
- **`diplotypes.csv` and `pgs.csv` are not filled**, for a different reason with a different remedy:
  those models have **no coordinate columns at all**, so a consumer joins them on `rsid` + `genotype`.
- **One rsID may resolve to several loci.** *"maps to N loci; expanded to N rows"* is normal for a
  paralogous rsID — expected, not an error, and **do not delete rows to suppress it.**
- **A pseudoautosomal variant is recorded once, on X.** That is the spelling every annotation source
  uses, and a standard GRCh38 analysis set hard-masks the Y PAR. `--keep-par-twin` records both; use it
  only if your reference is unmasked. The message *"maps to 2 loci that are 1 place(s)"* is saying **one
  place spelled twice**.

## Edits that corrupt rather than disagree

**A hand-edited coordinate on a VRS-minted row fails the compile unless `vrs_id` is cleared.** A
`ga4gh:VA.…` for a substitution is computed from the coordinate and the alleles alone, with no reference
and no network, so the recomputation is deterministic: a disagreement can **only** mean the stored id is
wrong. That is an error in **both** modes and there is nothing to decide — clear the cell and re-mint, or
fix whichever of `chrom` / `start` / `ref` / `alts` is wrong.

**Never author both sides of a redundancy check.** Hand-writing `resolution.csv` *and* the coordinates in
`variants.csv` makes the cross-check compare your convention against itself, and it agrees perfectly. If
you inherited a `resolution.csv` you did not generate and want to know whether it is right: **move it
aside and re-enrich; comparing the two is the check**, and no command does it for you.

⚠️ **CHECK — `ResolutionRow.fetched_at` is never assigned by any code path.** Blank on all 428 rows
across the 11 reference tables. Do not read it as a staleness signal, and do not build one on it.

⚠️ **CHECK — `--no-resolve` ignores an injected table and still exits zero.** Despite the name it is the
master switch for **all** resolution: the resulting digest is byte-identical to compiling with
`resolution.csv` deleted. The MCP `compile_module` tool cannot reach that branch; the CLI can.
[`module-compile`](../module-compile/GUIDE.md) has the full trap.

## Off GRCh38

**Resolution and VRS minting have one refget table** (upstream **RM15**), so on a non-GRCh38 module no
link runs and **no row is recorded at all** — not even `not_found`, which would claim the source was
asked. Your authored coordinates are transcribed under your own build and the module compiles, keyed by
**build-relative** coordinates that will not join against gnomAD, ClinVar or ClinGen.

So on such a module: **author coordinates rather than rsIDs**, since an rsID is only resolvable against
GRCh38, and say so in the README.

**`just-dna-enricher hint recover`** tells you which rs-number GRCh37 dbSNP records at an hg19
coordinate — the fastest way to lift an old panel honestly, because recovering the **rsID** and letting
resolution place it is not a liftover and cannot shift anything. It reports and never fills.

🚧 **ROADWORKS — a non-GRCh38 module gets zero frequencies and the skip barely surfaces.** Any resolution
row off `FREQUENCY_GENOME_BUILD` is skipped — correctly, because gnomAD v4's variant id carries no
assembly, so a GRCh37 coordinate is a well-formed request that returns *a different variant's* frequency.
But the only trace is one counted log line: there is no `off_build` field on the result, and the compiled
module looks exactly like one gnomAD had nothing for. **Guard:** never read an empty `frequencies.csv` as
"gnomAD has nothing"; lift the module to GRCh38 or say so in the README, because no artifact field
records it.

## Re-running this stage

**An existing sidecar is authoritative and merged, never clobbered** — so a re-run after changing an
authored identity refreshes nothing, silently. The delete is the operation, and the delete is what costs
you `source="manual"` rows.

**[`module-refresh`](../module-refresh/GUIDE.md) owns all of it**: what deleting each sidecar costs, `refresh_sidecar`, and the two
passes that break on a second run (`enrich_gene_metrics`' `UnboundLocalError`, and the gene-metrics
override that duplicates instead of overriding). Load it before re-running anything.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** re-running the `unreachable_rsids` list; clearing a `vrs_id` that no longer
recomputes from its own row; recording the X spelling of a pseudoautosomal locus; recovering an rsID with
`hint recover` and letting resolution place it. None of these has a judgement in it.

**Surface it, and let a pilot settle it:**

- **Which side is right when the module and the genome disagree.** The report never repairs, and the
  authored value survives so the evidence does.
- **Whether an unresolved row should stay.** Unresolved is a legitimate state; deleting a row to make a
  counter look better is not.
- **Whether to author a coordinate at all.** Prefer the rsID; author the coordinate when the rsID cannot
  say which allele the row is about.
- **Whether a `source="manual"` resolution row is still right** after the sources moved.

## What this stage cannot do

**It cannot tell you a coordinate names the variant you meant** — only that the base at that position is
or is not the one you wrote, on the rows where those differ.

**It cannot lift a coordinate between assemblies.** It recovers the rsID instead, which is the honest
operation.

**It cannot mint an id for an indel offline**, and it cannot mint one at all off GRCh38.

**It cannot refresh what is already recorded.** That is [`module-refresh`](../module-refresh/GUIDE.md).

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action. The ones that
land here:

- *"ref mismatch: N row(s) — coordinate shifted 1 base"* — above; read it as being about `start`.
- *"<rsid>: not in the injected Ensembl snapshot"* (and the ClinVar twin) — the local snapshot lacks
  it, **not** a claim that the source does. It is no longer a claim about the position either: the
  trailing *"position remains unset"* was split off in enricher 0.6.6, because the live leg had not run
  yet when the line was written. `lookup_variant` says *"<rsid>: position remains unset"* once, at the
  end, when nothing placed the variant.
- *"cannot host the authored genotype … The event sizes differ"* — a real contradiction, and decidable:
  a different variant sharing the rsID.
- *"could not be decided here … the same size but different content"* — **not** a contradiction; the
  locus is kept and `--strict` still compiles.
- *"Enrichment is GRCh38-bound; the module declares genome_build='GRCh37'"* — expected, and the only
  honest answer.
- *"pseudoautosomal: kept the X spelling"* — informational, and printed so a half-size table is never a
  surprise.

## Where to go next

| You need | Load |
|---|---|
| the authoring rule behind the off-by-one | [`module-curate`](../module-curate/GUIDE.md) |
| to re-derive without losing curation | [`module-refresh`](../module-refresh/GUIDE.md) |
| the cross-checks that run after this | [`module-check`](../module-check/GUIDE.md) |
| the resolution table in full | [`module-tables`](../module-tables/GUIDE.md) → `references/resolution.md` |
| what a filled coordinate does to the artifact | [`module-compile`](../module-compile/GUIDE.md) |
