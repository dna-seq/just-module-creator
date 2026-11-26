# Shared risk for age-related disease

263 common variants that a 2026 multivariate GWAS linked to the genetic liability shared across
five age-related diseases, and that the same study showed to be enriched — as a set — for
association with surviving beyond the 90th percentile of their birth cohort.

## Where this module came from

One paper, read in full, plus its supplementary workbook:

> Dinh PA, Han H, Kim S, Guo Q, Zhang ZD, Vijg J, Suh Y. **Genetic links between multimorbidity and
> human aging.** *GeroScience* 2026. PMID 41405793. doi:10.1007/s11357-025-02044-3. CC BY 4.0.

The authors ran genomic structural equation modelling over GWAS summary statistics for heart attack,
high cholesterol, hypertension, stroke and type 2 diabetes, and extracted a single latent factor they
call **mvARD** — the genetic liability those five conditions share. A multivariate GWAS of that factor
(effective N = 475,203) produced **263 independent lead SNPs across 180 loci** at P < 5e-8.

Every row here comes from two sheets of supplementary file `11357_2025_2044_MOESM2_ESM.xlsx` (ESM 2):

| Sheet | What it gave |
|---|---|
| **ST5** — Functional Annotation of Lead SNPs in mvARD | rsID, alleles, MAF, beta, SE, p-value, nearest gene, SNP function, Q heterogeneity |
| **ST9** — Proxy-phenotype analyses of 263 SNPs in GWAS on extreme longevity | the same 263 SNPs with their effect in the Deelen 2019 extreme-longevity GWAS |

The two sheets were reconciled before anything was authored: identical rsID sets (263 = 263), and
zero disagreements on alleles, betas or positions. The sign-discordance flag in ST9 was recomputed
from the two betas and agreed on all 263 rows.

## What each row claims, and what it does not

**This is the distinction the module turns on.**

- **Per variant, the claim is mvARD.** Each of the 263 is genome-wide significant for the shared
  age-related-disease factor. That is what `state`, `direction`, `weight` and `effect_size` encode.
- **The longevity claim is set-level, not per-variant.** 199 of 263 (76%) point the opposite way in
  the extreme-longevity GWAS (one-sided P = 1.36e-17); 49 of 263 (18.6%) reach nominal significance
  there against 8.4% expected (P = 1.17e-7); Mann-Whitney P = 9.73e-12. **No single row carries a
  demonstrated longevity effect**, and none claims one. The set-level finding is recorded once, in
  the variant-less `studies.csv` row, which is the only row quoting the article body.

A row's conclusion says so in plain words. Where that variant's *own* longevity estimate did reach
nominal significance (49 rows) the conclusion says which way it pointed; otherwise it says the link
holds for the 263 together and not for that one.

## Row shape

789 variant rows = 263 variants x 3 genotypes.

| Genotype | `state` | `weight` | Note |
|---|---|---|---|
| reference homozygote | `neutral` | `0.0` | the baseline; `requires_callable=true`, because a no-call is not a hom-ref |
| heterozygote | risk / protective | +/- dosage 1 | |
| alternate homozygote | risk / protective | +/- dosage 2 | |

**The effect allele was re-anchored, and this is the trap in the source data.** The summary
statistics were harmonised with `gwas-sumstats-harmoniser`, which sets the effect allele to the
*reference* allele — true for all 263 here, confirmed against Ensembl. Carrying the paper's sign
through unchanged would have put the module's largest weights on homozygous-reference calls, i.e. on
the genotype most people carry. Every `effect_size` and `weight` here is therefore stated **per copy
of the alternate allele**, with the published beta's sign flipped. `effect_allele` names the alternate
allele on every row. The published values, on the paper's own effect allele, are preserved verbatim in
the `provenance_quote` of each `studies.csv` row.

`weight` is defined in `weighting:` in `module_spec.yaml`. Read it before combining these numbers with
anything: they are ordinal within this module only, the factor has no natural units, and summing them
does not produce a validated polygenic score.

## Evidence rows

527 study rows: two per variant, plus one for the module.

- **PMID 41405793** (Dinh), `phenotype_class: MULTIVARIATE_AGEING` — the mvARD estimate.
  `provenance_quote` is that variant's row of Supplementary Table S5, extracted programmatically from
  the workbook. **`quotes_found: 0` on these rows is expected and means nothing**: the checker searches
  the article body Europe PMC indexes, and a supplementary workbook is not in it.
- **PMID 31413261** (Deelen 2019), `phenotype_class: EXTREME_SURVIVAL_CC` — the extreme-longevity
  estimate. **No `provenance_quote`, deliberately.** These numbers reached this module through Dinh's
  Supplementary Table S9; they are not printed in Deelen's paper, so no passage of it supports them.
  Each row's `conclusion` says so.
- **PMID 41405793, no variant** — the set-level enrichment, quoting the article body verbatim.

`enrich_literature_pass` resolved both PMIDs, confirmed both exist, found no DOI conflict and
reported `titles_as_quotes: []` — no quote here is an article title. It could check **none** of the
264 quotes against retrieved text (`quotes_unchecked: 264`), because it retrieved no fulltext for
either paper. For the 263 supplementary-sourced quotes that is expected. For the one body-sourced
quote it is **not** expected and is a limitation of this module's verification, not evidence against
the quote: `fetch_fulltext` retrieves PMC13601487 fine, and the passage
*"76% of SNPs showed the expected direction of effect"* was confirmed present in that text by hand
when it was authored. Nothing in the artifact records that confirmation, so treat the quote as
author-attested rather than machine-verified.

## What was corrected, and why

All of it is in `logs/authoring.log`, which publishes with the module.

- **`ARL 15.00` and `NPR 3.00`** in the source's `nearestGene` column are spreadsheet
  number-formatting corruptions of **ARL15** and **NPR3**. Both confirmed by the rows' own
  coordinates. Corrected.
- **11 HGNC-retired gene symbols** updated to their single named successors (PVRL2 to NECTIN2,
  GUCY1A3 to GUCY1A1, ZNF259 to ZPR1, and eight more). Nomenclature only; no locus was reassigned.
- **~61 symbols remain unresolvable** and were left exactly as the source wrote them. They are clone
  and scaffold identifiers (`RP11-...`, `AC...`, `Y_RNA`) and multi-gene composites that FUMA emits
  as the nearest feature for intergenic and non-coding loci. There is no successor to write, and
  inventing one would assert a gene assignment the source never made. On the 150 rows where such an
  identifier would have been read aloud to a layperson, the conclusion names the chromosome and says
  the position is not inside a named gene instead; the `gene` column still carries the source value.

**One error in the source paper, not corrected because it is not ours to correct.** The body text
names `rs6505080` as one of the six novel loci. That rsID is a real variant on chromosome 17 and is
not among the 263. The supplementary table gives `rs650508` (chr2, near PRKCE) in that position, and
the coordinates confirm the supplement. This module follows the supplement. Worth reporting to the
authors.

## Limits

- **European ancestry only.** Every input GWAS, the longevity GWAS, and the allele frequencies quoted
  in the conclusions (gnomAD v4.1, non-Finnish European). Effect sizes and frequencies do not transfer.
- **mvARD is a latent construct with no natural units.** The paper says so; it is why no effect here
  can be read as an odds ratio or a risk.
- **Individually negligible effects.** The largest absolute beta in the module is 0.0825 on a unitless
  factor. The study's finding is about 263 variants as a set.
- **98 of the 263 (Bonferroni-significant Q)** show heterogeneity, meaning their effect is probably
  *not* mediated by the shared factor alone but by disease-specific paths. They are kept, because the
  longevity enrichment was computed over all 263, and are marked `category=disease_specific` and
  flagged `qsnp_heterogeneous`. 176 are nominally Q-significant; the paper excluded those from its
  downstream functional work.
- **38 variants are strand-ambiguous** (A/T or C/G), flagged `strand_ambiguous`. Strand cannot be
  confirmed from the alleles alone, so a consumer joining against a differently-stranded callset could
  invert those rows.
- **`trait_efo_id` is empty on every variant row.** No EFO, MONDO, OBA or HP term names "shared
  liability to five age-related diseases"; the nearest, `EFO_0004300` (longevity), is obsolete and its
  successor is obsolete too. An invented or merely adjacent term would misstate what the row measures.
- **Nearest gene is not a causal gene.** The `gene` column is FUMA's nearest-feature annotation. The
  paper prioritised only four genes as high-confidence causal in blood — DCAF16, PHF13, MGA, GTF2B —
  and that is a different claim from anything this column makes.
- `clin_sig`, `clinvar` and `pathogenic` are empty throughout: these are common trait-associated
  variants, not clinical ones.

## Flags in use

`qsnp_heterogeneous` (98 variants) · `novel_locus` (6) · `strand_ambiguous` (38) ·
`longevity_nominal` (49, the variant's own longevity P < 0.05)

## Provenance

Authored end to end by an agent (`authorship:` records `[ai, agent]`). The human author holds
responsibility for it regardless. Supplementary quotes were located by the agent, recorded in
`curator` on every study row.
