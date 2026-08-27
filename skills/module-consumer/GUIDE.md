---
name: module-consumer
description: >-
  The obligations on the far side of the seam, and what an author can do to make a module readable.
  Covers the three-state join contract and why absence is not a reference call, the unobservable-allele
  marker, the callability columns nothing reads, float32 comparison, expansion rows that assert
  nothing, the bin lookup no consumer implements, and the fact that a rendered report cannot be tied
  back to the module bytes that produced it.
  Triggers: "how is this read", "consumer", "join to a VCF", "no-call", "hom-ref", "requires_callable",
  "star in a genotype", "float comparison", "locus_count", "will this match", "expansion rows", "bin
  lookup", "does anything read this".
---

# Will a consumer read this right

**Lifecycle stage:** 9 (install and join) — and every earlier stage that decides how a row will be read.

**A module supplies the annotation; the consumer supplies the measurement.** That split leaves
normative obligations on the reader, and several of them are ways to get a well-formed number and a
wrong answer. You are not writing the consumer, but every one of these is something an author can make
easier or impossible.

## The join is three-valued, and the third state is the whole point

A conforming consumer must distinguish:

| At the module's locus, the sample is | Means |
|---|---|
| **called, and matches the row's genotype** | the row applies |
| **called, and is reference** | the row does not apply — *screened, negative* |
| **not called** | **unknown** — *not screened* |

**Absence from a variant-only callset is not a reference call.** A variant-only VCF lists what differs
from the reference and says nothing about the rest, so reading a missing row as hom-reference converts
*"we never looked"* into *"we looked and it was fine"*. That is the difference between **screened
negative** and **not screened**, and it is the single most consequential misread available on this seam.

**`*` is unknown, never reference.** A `*` allele marks a site the caller could not observe, usually
because an overlapping deletion took it. Dropping it turns `*/A` into a reference-like `A` — a genotype
the sample does not have.

## What an author can do about it

- **Set `requires_callable=true` wherever the *absence* of a variant is the informative call**, and give
  `callable_from` so a reader knows where the proof would live. A pathogenic-variant panel reporting
  "clear" is asserting coverage, not observing it.
- **Keep three axes apart.** `requires_callable` (a negative must be *proven*) and `callable_from`
  (where the proof lives) ask whether the **position was seen**. `quality_from` / `min_quality` ask
  whether the call is **good enough to act on**. Different questions; do not fold them.
- **Write the `conclusion` so it survives being read alone.** A consumer renders that cell; it may
  render nothing else from the row.

🚧 **ROADWORKS — the callability quartet is read nowhere.** No consumer today reads `requires_callable`,
`callable_from`, `quality_from` or `min_quality`, so a `requires_callable` conclusion is presented with
**no proof of callability whatsoever**. **Guard:** fill them anyway — they are the only machine-readable
record of the obligation — and say the coverage requirement in the `conclusion` prose as well, because
prose is the half that currently reaches a reader.

## Comparisons that look safe and are not

**Compare in float32.** Every VCF `Float` is 32 bits. Widening one to float64 before comparing against a
bound moves it in a direction that depends on the decimal, so **both directions lose a row**: some
values fall below a threshold they should meet and others rise above one they should not. Bin bounds,
allele fractions and quality thresholds are all exposed to it.

**A VCF `ID` column holds a list, not a value.** A row keyed by rsID matches if the id appears among
them; equality against the whole field misses.

`SCHEMAS.md` § *reading the VCF the pointers point at* is normative for the rest of that surface —
QUAL's meaning, `MIN_DP` in a gVCF block, and the pointer columns generally. Read it there rather than
from any prose here.

## Rows that assert nothing

**An expansion row asserts nothing on its own.** When one rsID resolves to several genuinely distinct
loci, the compiler writes one row per locus and the predicate for a reader is `locus_count > 1` — gated
on `expanded_keys`, because the column **defaults to 1** and an unexpanded module would otherwise look
identical. A consumer that treats each expanded row as an independent finding double-counts one
observation.

For the author: **do not delete rows to suppress an expansion warning.** *"maps to N loci; expanded to N
rows"* is normal for a paralogous rsID. To count *findings* rather than rows, count distinct `rsid` in
`weights.parquet` — the expanded rows keep it.

**A per-allele archive call is not a module's flat one.** `clinical_assertions.csv` records the
archive's call *and the review behind it*, per allele; a module's `clin_sig` is one cell on one row. A
consumer reading the flat cell as if it carried the archive's review depth is over-reading it, and an
author copying the archive's call into the flat cell has made the module's own check vacuous —
[`module-curate`](../module-curate/GUIDE.md) owns that rule.

## 🚧 ROADWORKS — the bin lookup is specified, and nothing implements it

The binning family — `repeat_alleles.csv`, `copynumbers.csv`, `heteroplasmy.csv`,
`activity_phenotype.csv` — needs a consumer that takes a **measured quantity** and selects the row whose
`[measure_min, measure_max]` contains it. **No consumer implements that lookup today**, so those four
table kinds annotate nothing downstream, however correct they are. `just-dna-lite` touches all four
kinds in exactly two places and both count rows.

**What changed in 0.6.6 is that the rule is now normative rather than inferable** (our `S58`, upstream
RM122): `SCHEMAS.md` carries the **measure lookup** beside the genotype join contract — scope to the
group, select the row whose inclusive range contains the value, greatest `measure_min` on a shared
endpoint, compare in float32, `unresolved` on a missing measurement and withhold on no match, and
`trait_efo_id` multiplies the answer rather than disambiguating it. A family specified ahead of its
consumers is deliberate, and it is upstream's own framing.

**What it means for you as an author:** the bins have one right reading now, so **write what they mean
into the README** — the reader who eventually implements this has your prose and the spec, and nothing
else says what a bin is *for*.

**Guard for an author:** the tables are still worth writing — they are correct, publishable and will be
read the day the lookup lands — but **do not promise an author that a heteroplasmy module will produce a
report today**, and say in the README what the bins mean in plain words, because prose is the only path
to a reader right now.

**And always author the `unresolved` sentinel**, per bin group. A consumer selects it when the
measurement is **absent** — so never route a missing measurement to the lowest bin, which would report a
non-measurement as a normal one. Nothing on the compile path refuses a table with **zero** sentinels;
[`module-curate`](../module-curate/GUIDE.md) has the enforcement gap in full.

## What a consumer cannot tell you

**An annotation run records no module version.** The output manifest names each module by *name* and
carries no version, no digest and no source URL. So **a rendered report cannot be tied to the module
bytes that produced it**, and nothing can answer *"which of my saved results are stale"*.

**Installed-versus-current is exact version-string equality**, and a new version replaces the old one in
place: two versions of one module cannot coexist locally, and nothing notifies anybody that a newer one
exists.

**A module compiled before compiler 0.6.6 cannot be found by gene unless it has a `variants.csv`.**
`manifest.stats` took its gene facets from `variants.csv` alone until then and the registry's gene
index reads `stats.genes`, so a PGx, copy-number or activity-bin module published `genes: []`. The
compiler now takes them over every gene-bearing authored table, but a published manifest is immutable —
what is in the catalog today is what its own compile wrote. **Never add an empty `variants.csv` to fix
it**; name the genes in the README and in the display prose, where a text search finds them.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** filling `callable_from` beside a `requires_callable` you already set;
naming the module's genes in the README when it carries no `variants.csv`.

**Surface it, and let a pilot settle it:**

- **Whether a negative needs proof** — `requires_callable` is a claim about what your conclusion means.
- **Whether the conclusion reads correctly alone**, without the row around it.
- **What to say in the README about what the module does not cover.** It is the only channel that
  reaches a reader for every gap on this page.

## What this stage cannot do

**Nothing here reads a sample.** A module never contains a genotype under test or a measured value.

**Nothing validates a consumer.** The obligations above are normative and unenforced; a non-conforming
reader produces confident wrong answers and no part of this toolchain sees it.

**Nothing renders a bin today**, though the lookup is specified. See the 🚧 above.

## Where to go next

| You need | Load |
|---|---|
| the cells that decide how a row reads | [`module-curate`](../module-curate/GUIDE.md) |
| the expansion and the resolution behind it | [`module-enrich`](../module-enrich/GUIDE.md) |
| which table a measurement belongs in | [`module-tables`](../module-tables/GUIDE.md) |
| the per-table dossiers for the binning four | [`module-tables`](../module-tables/GUIDE.md) → `references/heteroplasmy.md`, `repeat_alleles.md`, `copynumbers.md`, `activity_phenotype.md` |
| what a published module looks like on disk | [`module-tables`](../module-tables/GUIDE.md) → `references/LAYOUT.md` |
