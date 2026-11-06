# HFE haemochromatosis — a gene panel drafted from ClinVar

The first module in this repo authored end-to-end with the 0.5 authoring surface. Its point is not
the biology: it is what a drafting provider will and will not decide for you, and what that costs a
curator in practice.

## How it was built

```bash
just-dna-compiler scaffold reference_examples/hfe_hemochromatosis --name hfe_hemochromatosis
just-dna-enricher draft-panel reference_examples/hfe_hemochromatosis \
    --gene HFE --snapshot data/interim/clinvar
# ... curation, below ...
just-dna-enricher enrich reference_examples/hfe_hemochromatosis \
    --offline --clinvar-cache data/interim/clinvar
just-dna-compiler compile reference_examples/hfe_hemochromatosis out/
```

The draft produced 12 variant rows and 33 study rows and then **refused to finish**, which is the
behaviour being demonstrated:

```
warning: 1 rsID(s) name more than one allele here (rs773443949) — written with their full
         coordinate, since an rsID alone cannot say which allele the row is about.
warning: 103 further ClinVar citation(s) not drafted (--max-citations 3).
warning: 12 row(s) carry an unreplaced genotype placeholder and will not compile until you
         decide the zygosity each finding is about.
```

## What the curator decided, and why the tool could not

`VariantRow.genotype` is required, and ClinVar publishes **alleles, not genotypes**. Whether carrying
a pathogenic HFE allele once is informative does not follow from the allele — it follows from the
condition's inheritance mode, which ClinVar does not state. So every drafted row arrived carrying
`<<REPLACE>>`, and nothing compiles until a human replaces it.

The rule applied here, in one line: **HFE-related haemochromatosis type 1 is autosomal recessive, so
the informative call is homozygous for the pathogenic allele.** Every drafted row became `alt/alt`.

The thirteenth row is the whole argument. `rs1800562` (C282Y) also appears **heterozygous**, and that
row says something different from its homozygous twin:

| genotype | `clin_sig` | `state` | conclusion |
|---|---|---|---|
| `A/A` | `pathogenic` | `risk` | two pathogenic alleles — the genotype the disease is described for |
| `A/G` | `pathogenic` | `neutral` | one pathogenic allele: a carrier, not expected to overload iron alone |

Same variant, same ClinVar call, opposite clinical meaning. `clin_sig` describes the **allele**;
`state`/`direction` describe the **finding for that genotype**. A provider that guessed a genotype
would have had to pick one of these two rows and would have been wrong half the time — which is why
it does not guess. (The orthogonal-axes rule, Principle 5, is what lets both rows coexist honestly.)

Penetrance is deliberately in the prose: C282Y homozygosity commonly produces biochemical iron
overload and much less often clinical disease. The module states the association ClinVar records; it
does not predict an outcome.

## What is *not* in these rows

`weight`, `direction` beyond the coarse call, `effect_size`, `effect_measure` — ClinVar publishes no
effect statistic, and a weight is the author's model of the finding. No `trait_efo_id`: ClinVar's
`condition` is free text and MedGen, not EFO, and mapping it is inference. No `acmg_sf`. `curator`
and `method` come from the spec's `defaults:` block.

## Two things drafting a real panel taught the tooling

Both were found here and fixed in the provider rather than worked around in this file:

1. **One rsID can name two alleles.** ClinVar lists `rs773443949` at 6:26091590 as both `G>A` and
   `G>T`. An rsid-only row cannot say which, so the two collapsed into one and an allele was silently
   lost. Such variants are now written with their **full coordinate** instead — visible here as the
   two rows that carry `chrom`/`start`/`ref`/`alts` and no rsID.
2. **A study must carry the identity its variant row got.** The study rows for that variant were
   still keyed by rsID, so they referenced a variant `variants.csv` no longer named by rsID, and the
   compiler's orphan check caught it.

## Grounding evidence

`studies.csv` is drafted from ClinVar's own literature links (`var_citations.txt`, ingested with
`just-dna-enricher clinvar citations`). Before that existed the provider could not produce a
compilable module at all: `studies.csv` is mandatory and the ClinVar VCF carries no PMIDs. Citations
are capped at three per variant — `rs1800562` alone carries 84 — and the number dropped is always
reported, because a silent cap reads as "this is everything".

## Files

| file | authored by |
|---|---|
| `module_spec.yaml` | `just-dna-compiler scaffold`, then filled by hand |
| `variants.csv` | `draft-panel`, genotypes and conclusions by the curator |
| `studies.csv` | `draft-panel`, from ClinVar's citation links |
| `sources.csv` | `draft-panel` (ClinVar is public domain; recorded because attribution is asked for) |
| `resolution.csv` | `just-dna-enricher enrich --offline` |
| `gwas_effects.csv` | `just-dna-enricher gwas` (RM90) |

**This module deliberately keeps the deprecated `sources.csv` spelling.** 0.6 accepts `licensing.csv`
as a second name for it and the other examples were renamed; this one was held back so the deprecation
path stays exercised on a real module rather than only in a fixture — the compile prints a rename
notice and reads the file exactly as before. Renaming it changes nothing that is hashed: all eleven
examples kept their exact `artifact.digest`, `content_signature`, `resolution_signature` and
`source_signature` across the four that moved, which is the measurement behind the claim that the
filename enters no identity.


## What the GWAS pass broke here, and what its output shows (0.6, RM90/RM92)

This module was the probe for `gwas_effects.csv`, and it broke the new pass **twice** — neither
failure reachable from a recorded fixture, which is the whole argument for running a tool against a
real module rather than a written one.

* **A 404 is the Catalog's empty answer, not an outage.** The Catalog holds only variants with a
  published genome-wide association, so it 404s on a rare clinical one. The pass read that as a
  transport failure and died on `rs111033563` — the **first** variant in this file — which means it
  could never have completed on any clinically-authored module. Nine of this module's ten rsIDs are
  in that state and now carry an honest `not_found` row.
* **`pvalue: 0.0` is an underflow the Catalog really publishes**, past float64's subnormal boundary.
  `p_value_num` refuses it, correctly — that is not a probability — but the pass let the resulting
  error discard the *whole association*. Six of them here. The number is now withheld, the verbatim
  `p_value` string keeps what the source said, and the row survives: 189 rows became 195.

**And the output is the clearest statement of why `weight` needed a declared scale.** `rs1800562`
alone carries 186 published associations, across **62 EFO traits in 12 distinct effect units**. Three
of those units are spellings of one thing — `SD units`, `SD`, `s.d.` — and two more differ only in
case (`g/dL`, `g/dl`); 138 rows carry the Catalog's uninformative `unit`. **42 of the 195 rows name no
effect allele at all**, because the study never established which allele carries the effect, and those
cannot be weighted in any direction.

Nothing in that set is poolable into one score, which is why this module's `weighting:` block says so
in as many words rather than leaving a reader to find out. The block is also why the module was
**re-closed**: it lives in `module_spec.yaml`, whose bytes the attestation binds.

The `weight` column here has been present and entirely blank since the module was written, which is
the other half of the point — it is a column nobody has ever filled, now with a declaration saying so.
