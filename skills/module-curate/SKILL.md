---
name: module-curate
description: >-
  The stage where a module is actually written: genotypes, weights, state and direction, conclusions a
  layperson can read, and how many rows belong in a report at all. Covers the cells only a pilot can
  settle and why, the one cell/source pairing that must stay independent, the coordinate mistake no
  offline gate catches, the genotype spellings that decide whether a row can ever match, and trimming
  a GWAS dump into an annotation.
  Triggers: "curate", "write conclusions", "what weight", "state or direction", "the report is huge",
  "too many SNPs", "which rows to keep", "genotype", "conclusion", "trait_efo_id", "lint_rows",
  "off by one", "1-based", "unresolved sentinel", "requires_callable".
---

# Stage 3 — curate what only a pilot can settle

**Lifecycle stage:** 3 — and **the stage a second pass normally re-enters at**, so read this on a
module that already exists as readily as on a new one.

Deciding what the module *claims*. Every other stage prepares this one or checks it. A drafter can
produce rows; nothing but a pilot can decide what they mean.

## What this layer may do, and what it must surface

**This layer writes.** The old framing — *report, never repair* — was the **format's** rule, correct
for a compiler that cannot record who decided a value. Here that decision is delegated to us, so
filling or correcting a cell is legitimate. What is owed is an honest split:

| | |
|---|---|
| **evident and mechanical** — a rename, a deprecated spelling, a column that moved, a defaulted cell left empty | **apply it, say nothing** |
| **checked or authored** — `genotype`, `weight`, `clin_sig`, `state`, `direction`, a `conclusion`, a `provenance_quote` | **never write it quietly. Surface it** |

**When you cannot tell which side a case is on, surface it.** Over-surfacing is recoverable; a silent
wrong write is not.

And the hazard that makes this more than bookkeeping: **a mismatch against a source is not a defect
report.** Archives lag the edge — a retraction, a refuting meta-analysis, a bigger cohort. A row that
disagrees with ClinVar may be **the module being right and current while the archive is stale**, so
conforming it silently *degrades* the module, and the check then agrees with itself and reports green.
Editing against a source needs a reason that outranks the source, **and that reason gets written
down** — `record_override` is where it goes, after the mismatch has been reported and never before.

## The cells a drafter deliberately leaves

| Cell | Why it is a decision |
|---|---|
| `genotype` | Sources publish **alleles, not genotypes**. Whether one copy is informative follows from the condition's inheritance mode. **Except on a non-diploid contig**, where only one genotype is expressible and `draft-panel` writes it for you |
| `state` (when stubbed) | The record is `uncertain_significance` and **no vocabulary member means "undecided"** — `neutral` says benign, `risk` says a direction. If you can justify neither, **drop the row** rather than pick one to make the compile pass |
| `weight`, `direction`, `effect_size` | Your model of the finding. ClinVar publishes no effect statistic. `module-weights` owns the whole question |
| `trait_efo_id` | A source's condition is free text or MedGen. Mapping it to an ontology is inference |
| `conclusion` | What the module *says*. Keep it hedged where the biology is — penetrance, tissue, co-factors |

To write a genotype you need the alleles. Ask, without writing anything:

```
lookup_variant(rsid="rs1801133")                     # loci, ref, alts — plus what it withholds
lookup_variant(rsid="rs334", ambiguity=True)         # warn when the answer is not unique
lookup_variant(chrom="1", start=11796321, ref="G", alts="A")   # allele-exact by coordinate
literature_search(gene="MTHFR", trait="homocysteine")          # the papers — with titles
lookup_citation(pmid="7647779")                                # exists? and WHICH paper — read the title
lookup_identifier(kind="trait", identifier="EFO_0004541")      # current | obsolete | absent
lookup_identifier(kind="gene", identifier="MTHFR")             # approved | retired | unknown
```

Then lint before you write — `lint_rows` takes CSV **text**, needs no file, and writes nothing:

```
lint_rows("variants.csv", "rsid,genotype,state,conclusion\nrs1801133,A/G,risk,…\n")
```

Read all three levels. `error` blocks a compile. `warning` does not — **and several of the traps on
this page arrive only as warnings.** `info` names the columns left to you.

Findings carry a `source`, and it is worth reading: `upstream` is the compiler's own, and
`just-module-creator` is one this layer computed, which does not block a compile whatever its level.
On `variants.csv` those are the two conclusion rules — see *What this stage cannot do*.

## The one pairing that must stay independent

`rsid`, `chrom`, `start`, `ref`, `alts`, `clin_sig`, `doi`, `acmg_sf`, `function_status`,
`evidence_level` and `p_value_num` are **redundancy-bearing**: a later check compares your
independently authored value against a source, so filling it **from that source** makes the check
compare the source with itself.

`lookup_variant` shows you the value and does not apply it — it comes back in `withheld` with
`applied: false`, a `refusal` and a `note`. **That is not a general bar on writing.** It is this one
pairing, and the cost is specifically ours: the row moves from **honestly unverified** to
**apparently verified**, and we are the layer handing somebody a module to trust. An unverified row is
honest; a falsely verified one is not, and nothing downstream can tell them apart.

> **Ask of any green check: could this have failed?** A value that satisfies a check *vacuously* is as
> bad as one copied from the checker. The worked case is `provenance_quote` set to the article's
> **title** — a title always occurs in its own fulltext, so `quotes_found` matches every time. Four
> published modules carry a quote on all **3668** rows, exactly one distinct string per PMID, and every
> one is the title. Full coverage, witnessing nothing. `find-evidence` owns what may honestly go in
> that cell, and **an agent may locate and write one** — verbatim, for this row's claim, never the
> title, saying who found it.

`describe_table` names the same columns under `redundancy_bearing`.

**A redundancy advisory can name a checker that never sees your table, and `describe_table` says so.**
`hints.REDUNDANCY_BEARING` is keyed on a **bare column name**, so the `clin_sig` advisory reaches
binning tables and `clin_sig` / `evidence_level` reach `diplotypes.csv`, while the checkers are driven
from `variants.csv` and the PGx annotation tables. Since 0.6.6 the entry carries the scope — *that
checker does not read this table; it loads X only* — so you can tell the two cases apart. The advice is
the same in both and the stakes are higher in the second: **a green run there is not evidence of
agreement with anything**, and your own independent reading is all that stands behind the cell.

## The mistake nothing offline can catch

Worth its own heading because it has happened at scale, to a careful author: **3,038 variants across
four modules** that passed every gate.

**`start` is the 1-based VCF position. Copy it as printed; never subtract one.** Here is what does
*not* happen when you get it wrong: `validate_module` passes, `compile_module --strict` passes, the
manifest says `fully_resolved: true`, and every `ga4gh:VA.…` id is minted and then reported
**verified**. A content-addressed id is a correct digest of whatever it is handed, so it certifies the
wrong locus without hesitating. The module is internally consistent, reproducible, signed — and about
the wrong bases.

### Where the wrong number comes from

Nobody decides to subtract one. It arrives with the source, and **the dangerous sources use both
conventions in different places**:

| Convention | Where you meet it |
|---|---|
| **1-based, inclusive — what `start` wants** | VCF `POS`, Ensembl (browser and REST), dbSNP, ClinVar, gnomAD, GTF/GFF, SAM, HGVS `g.` |
| **0-based, half-open (interbase)** | BED, bedtools, BigBed/bigWig, BAM internals, GA4GH VRS |
| **Both, in one tool** | **UCSC** — the position box and browser display are 1-based, the Table Browser's `chromStart` / `txStart` / `cdsStart` columns are 0-based. **pysam** — `record.pos` is 1-based, `record.start` is 0-based |

So the rule is not *know your source*, it is **know which field of your source**. A number lifted from a
UCSC table dump or a `pysam` `.start` is already one lower than `start` wants, and subtracting again is
not what goes wrong — **not adding one back** is.

**The other direction has a decoy: VCF anchors an indel on the base before it.** An insertion a paper
describes at position X appears in VCF at `POS` X−1, with the anchor base leading both `ref` and `alts`
(`A` → `AG`). That looks exactly like an off-by-one somebody forgot to fix, and it is not. Copy the VCF
`POS` as printed.

### Catching it in one call, before you write 3,000 rows

Author **one** row, then ask the source that is not yours:

```
lookup_variant(rsid="rs4988235")
```

It answers with the locus — `rs4988235` is `2:135851076 G>A` — and the same numbers come back in
`withheld`, each with `applied: false`. Compare `start` with the number you were about to paste. **The
signal is not "close" — it is exact.** A match means your convention is right and the rest of the file
inherits it. A difference of exactly 1, in the same direction, is conversion rather than a typo, and it
will be in every row you write from that source. Anything else is a different problem: wrong build,
wrong variant, or a paralogous rsID with several loci.

**Reading that number is allowed; pasting it is the previous section's mistake.** You are checking which
convention your *source* uses, not sourcing the cell. Do this **once per source**, before the bulk pass.

**Then prefer the rsID and let enrichment find the coordinate.** An rsid-only row cannot carry a
coordinate mistake, and the resolution table it produces is the independent second value the cross-check
needs. Author coordinates only when you must: no rsID exists, one rsID names several alleles and the row
must say which, or the module is not GRCh38.

**Never author both sides of a redundancy check.** Hand-writing `resolution.csv` *and* the coordinates
in `variants.csv` makes the coordinate cross-check compare your convention against itself. If you
inherited a `resolution.csv` you did not generate, **move it aside and re-enrich; comparing the two is
the check** — and no command does it for you.

The only thing that catches this is `enrich_module` run **online**: *"ref mismatch: N row(s) —
coordinate shifted 1 base…"*. Read that line as being about `start`, not `ref`, and read the count as a
**floor** — it can only see rows where the neighbouring base differs from your `ref`, roughly three in
four. `module-enrich` owns the report.

## Genotype spellings that decide whether a row can ever match

- **A genotype is `C/C`, not `CC`.** `CC` parses as a single two-base allele. ClinPGx writes the
  unslashed form; disambiguate using the resolved ref/alt.
- **Unphased genotypes are alphabetically sorted** (`A/G`, never `G/A`) — an unphased genotype is a
  *set*, and two spellings of one call would be two rows. Phased uses `|` and order is significant.
- **Indels are spelled out, reference-anchored**: `A/AG`, `C/CTT`.
- **Alleles must be drawn from `{ref} ∪ alts` at that locus.** A genotype whose alleles are not at the
  locus can never match a VCF — a warning normally, an **error** under strict.
- **`chrom=MT` is not diploid.** Use a single allele for a homoplasmic or hemizygous call. A mixed
  mitochondrial population is heteroplasmy and belongs in `heteroplasmy.csv`, not in a het genotype.
- **`chrom=Y` is not "never diploid": PAR1 and PAR2 are diploid in every karyotype.** The verdict is
  **per locus**, never per gene or per module — `XG` and `SPRY3` each straddle a boundary.
- **A pseudoautosomal variant is recorded once, on X** — the spelling every annotation source uses, and
  a standard GRCh38 analysis set hard-masks the Y PAR.
- **Identity is filled whole or not at all** — the rsID, else the complete `chrom`/`start`/`ref`/`alts`.
  A lone `alts` on a position-only row changes *which variant the row is*: it makes the key a VRS
  `ga4gh:VA.…` id instead of `chrom:start:ref`.
- **Do not author `variant_key` or `authored_ident`.** The compiler derives them, and `variant_key` is
  frozen at load, so an authored one is not overwritten.

🚧 **ROADWORKS — a homozygous genotype at an indel locus can never be contradicted.**
`hosting_verdict` returns `None` — no warning, no strict error — for a homozygous genotype, for a
symbolic allele on either side, and for same-length different-content alleles; and it returns `True`
outright for a resolution row carrying no `alts`. **Guard:** check homozygous genotypes at indel loci by
hand against `ref` and `alts`, and never read "no genotype warnings" as "every genotype was compared".

## `state`, `direction` and the sign

- **A `risk` weight is negative.** `weight` contributes to a wellness-style score, not a hazard ratio,
  so `state='risk'` or `direction='risk'` wants `weight < 0` and `protective` wants `weight > 0`.
  Getting it backwards is a **warning**, so it compiles.
- **`direction` is not a magnitude.** Its members are the same axis as `state` —
  `neutral` / `protective` / `risk` / `unknown` — not `increase` / `decrease`.
- **`direction` is authored or it is empty; nothing computes it.** `state` is required; the compiler
  never fills a blank `direction` from `state`, because that would assert a claim you did not make
  (`state='significant'` names no direction at all). So a module carrying only `state` compiles fine and
  ships an empty `direction` column, and a consumer keying on `direction` sees nothing. **Write it on
  every row it applies to, or on none.**
- ⚠️ **CHECK — the sign warning cannot fire on an honest GWAS module.** It keys on `state` or
  `direction` being `risk`, and withholding the axis is *correct* when the direction is unknown — which
  disables the only check the weight column has.

## How many rows is a report

**The trim is a curation decision and no tool makes it.** Three of four real authoring sessions
independently complained that the output read as a polygenic score decomposed into rows — while
`validate` and `compile` were green at **1,613 SNPs**. Green says nothing about whether anybody can read
the result.

A defensible way to decide:

1. **Ask what a reader does differently because of this row.** A row that changes nothing a reader would
   do is a row in a scoring table, not an annotation.
2. **Require a stated direction from a located paper.** If nothing says which allele carries the effect,
   the row goes — a guessed `direction` is a coin flip that will look exactly as authoritative as a real
   one.
3. **Collapse LD.** Variants in strong linkage tag one finding; two rows double-count it. Keep the one
   with the mechanism behind it.
4. **Send the aggregate where aggregates live.** If the point *is* the sum, that is `pgs.csv` — a
   pointer to a published score — or `gwas_effects.csv` beside the annotation. A PRS decomposed into
   1,613 annotation rows asserts 1,613 claims nobody wrote.
5. **Curate by subtraction when a source is generous.** The largest reference module is 1,190 diplotypes
   reached by *removing* what a caller cannot emit — and six alleles turn CYP2D6's 16,290 diplotypes
   into 21.

For calibration: the sixteen reference modules run from **three files and no coordinates** up to 330
drafted-then-curated rows. There is no minimum. `assets/fto_bmi` is one locus and is a perfectly good
module.

## Withhold rather than assert

The house algebra is **three-valued: true / false / unknown**, and `None` is never `False`.

- **A blank cell means "not stated" and is always legitimate.** Do not write `false` to silence a
  reminder.
- **On licensing, unknown terms are undetermined, never permitted** — `share_alike` / `commercial_use`
  left blank do not mean allowed.
- **Set `requires_callable=true` (with `callable_from`)** wherever the *absence* of a variant is the
  informative call: a no-call is not a reference call. `module-consumer` has what a reader does with it,
  including the fact that nothing reads it yet.
- **`unchecked` / `unknown` in a report means the question was never put.**

### Binning tables: author the sentinel per group

**Every binning table needs an `unresolved` sentinel** — a consumer selects it when the measurement is
**absent**, so never route a missing measurement to the lowest bin.

🚧 **ROADWORKS — the sentinel is a contract nobody enforces, and the two surfaces disagree about
scope.** The compile path refuses a **second** sentinel per bin group and refuses **zero** nowhere, so a
sentinel-less binning table compiles green under `--strict`. The presence half is an *authoring hint*
(reachable through `lint_rows`) and asks `not any(...)` over the **whole table** — so on a table whose
key fragments it into several groups, one sentinel anywhere satisfies the hint while most groups have
none. **Guard: run the hint, then count sentinels per group by hand**, repeating that group's key cells
verbatim and leaving only the bounds empty.

Bounds themselves — inclusive `measure_max`, `min == max` for a sharp value, a null bound for
open-ended, and the `measure_tiling` rule that decides whether adjacent bins must touch — belong to the
per-table dossiers. Two things to carry with you: **`measure_tiling` is an authorable column and the
measure's kind only supplies the default**, and **nothing checks coverage above the highest bin or below
the lowest**, so leave the top bin's `measure_max` blank unless the axis really ends.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** a deprecated column spelling, a defaulted cell left empty, an unslashed
`CC` rewritten as `C/C`, an unsorted `G/A` sorted to `A/G`, a `variant_key` you should never have
authored being removed. None of these has a judgement in it and nothing re-checks them against a source.

**Surface it, and let a pilot settle it:**

- **`genotype`, `state`, `direction`, `weight`, `clin_sig`, `effect_size`, `trait_efo_id`,
  `conclusion`** — every one of them, on every row.
- **Which side is right when a source disagrees with an authored value.** The source may be the stale
  one. If you do edit against it, the reason that outranks the source gets written down, and the row
  keeps warning: *somebody decided this* never means green.
- **Whether a row belongs in the module at all** — the trim, and dropping a row for want of a stated
  direction.
- **Whether a hedge in the `conclusion` is still true** after the rows around it changed.

## What this stage cannot do

**Almost nothing checks a conclusion, and the two rules that do are narrow.** `lint_rows` and
`validate_module` now read `variants.csv` prose against the cells beside it, and only for two shapes:
a conclusion naming a genotype token built from alleles at **this rsID's own locus** that is not the
row's own (a `warning`, and roughly six in ten are real — the rest are comparative or quoted prose),
and one conclusion shared by genotypes that score differently (an `info`, because it is a question:
one association sentence over a het and a hom is reasonable when only the dose differs, and nothing
records that you decided it). Everything else about the prose is unchecked — whether it is true,
whether it matches the paper, whether it still holds after the rows around it changed. Neither rule
blocks a compile and neither is a substitute for reading the sentence.

**Nothing catches an off-by-one offline.** Every gate below the enricher passes a shifted module.

**Nothing fills `weight`, and nothing will.** `module-weights`.

**Nothing decides the trim.** `validate` and `compile` are as green at 1,613 rows as at 13.

**Nothing tells you a genotype is biologically wrong** — only that its alleles are not at the locus, and
only where `hosting_verdict` reaches a verdict at all.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action. The ones from
this stage:

- *"unreplaced template placeholder `<<REPLACE>>` … genotype"*, and the two-column variant naming
  `genotype, state` — the row is an undecided ClinVar record; decide it or drop it.
- *"Input should be a valid boolean, unable to interpret input"* on a column you wrote correctly — an
  unquoted comma split the row. **Write CSVs with a CSV writer**, never by splitting on commas.
- *"direction must be one of \[…\], got: 'increase'"* — `direction` is an axis, not a magnitude.
- *"state='risk' but weight=1.0 > 0"* — a warning, and the convention is inverted from the one most
  people assume.
- *"allele(s) C are not among the authored alleles at this locus (T/Y) — the genotype is not the
  problem: 'Y' is an IUPAC ambiguity code"* — an ambiguity code records an uncertainty and must never be
  expanded into the alleles it could stand for.
- *"chrom=MT is not diploid here"* — write the single allele.

## Where to go next

| You need | Load |
|---|---|
| what a `weight` means and what to declare | `module-weights` |
| finding, verifying and reading the evidence | `find-evidence` |
| which table a finding belongs in | `module-tables` |
| the variants table in full, and the sign check that cannot fire | `module-tables` → `references/variants.md` |
| to turn rsIDs into coordinates | `module-enrich` |
| the checks that will compare this against the sources | `module-check` |
| this module already exists and you are revising it | `module-revise` |
