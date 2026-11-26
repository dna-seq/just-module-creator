# Longevity and shared risk of common diseases of ageing

Six common DNA spots that, in one large genetic study, raised the shared genetic risk of five
common diseases of ageing (heart attack, high cholesterol, high blood pressure, stroke and type 2
diabetes) **and** lowered the odds of reaching very old age. The other version of each spot does the
opposite. Each effect is small, and the six together explain very little of who reaches the top
10% of their birth cohort's survivors.

## Where this comes from

One paper, read in full:

> Dinh P-A, Han H, Kim S, Guo Q, Zhang ZD, Vijg J, Suh Y. **Genetic links between multimorbidity and
> human aging.** *GeroScience* 2026;48(5):7277–7292 (online 2025). doi:10.1007/s11357-025-02044-3,
> PMID 41405793, PMC13601487. CC BY 4.0.

The authors combined GWAS of the five diseases into one shared factor (**mvARD**, genomic SEM;
263 independent lead SNPs at 180 loci). They then looked up all 263 lead SNPs in an independent
extreme-longevity GWAS (Deelen et al. 2019, N = 36,745; cases survived beyond the 90th percentile of
their birth cohort) as a proxy phenotype. 76% of the 263 had the expected opposite sign, 49 were
nominally associated (P < 0.05), and **6 passed P < 0.05/263**. This module is those six.

| rsID | GRCh38 | Gene / region | Allele that lowered longevity odds | longevity beta (for paper's effect allele) | longevity P |
|---|---|---|---|---|---|
| rs6859 | 19:44878777 | NECTIN2 (APOE region) | A | A: −0.112 | 2.0e-8 |
| rs4803763 | 19:44854034 | NECTIN2 (APOE region) | C | G: +0.118 | 8.4e-7 |
| rs11754167 | 6:126856330 | intergenic (paper: near RPS4XP9) | C | T: +0.090 | 6.3e-6 |
| rs10004996 | 4:38382012 | LINC02513 (paper: RP11-83C7.1) | T | T: −0.085 | 1.1e-5 |
| rs2927439 | 19:44739483 | intergenic, near BCL3 (APOE region) | A | A: −0.085 | 8.9e-5 |
| rs28601761 | 8:125487789 | TRIB1AL, near TRIB1 (paper: RP11-136O12.2) | C | C: −0.074 | 1.4e-4 |

## Design decisions

- **Selection rule: the paper's own strict replication set.** Only the six lead SNPs whose
  extreme-longevity association passed the authors' Bonferroni threshold (0.05/263) were kept. The
  other 43 nominal (P < 0.05) hits were left out as too noisy for per-person reporting; the remaining
  214 mvARD SNPs make no longevity claim in this paper. The paper's MR genes (DCAF16, PHF13, MGA,
  GTF2B) and lifestyle MR results are not per-genotype claims and are not in this module.
- **Three genotype rows per variant, additive reading.** Two longevity-lowering alleles → `risk`;
  one of each → `neutral` (the middle of the distribution, not "no effect"); two longevity-raising
  alleles → `protective`. Both directions are reported.
- **No weights.** `weight` is empty everywhere and `weighting:` says so. The paper's per-allele
  longevity beta is carried in `effect_size` with `effect_allele` = the paper's effect allele, and
  `direction` describes that allele (it repeats across the variant's three rows on purpose).
- **Gene column** uses current symbols from Ensembl VEP (GRCh38): NECTIN2 (was PVRL2), LINC02513,
  TRIB1AL. Left blank where the SNP is intergenic.
- **Trait id** `OBA_VT0005372` (life span determination trait), the replacement EFO names for the
  obsolete EFO_0004300 "longevity".

## What this module is not

- **Not a lifespan prediction.** These are population-level associations with tiny per-allele
  effects (|beta| 0.07–0.12 on the longevity GWAS scale).
- **Mostly not purely "ageing" variants.** Five of the six have a significant Q_SNP heterogeneity
  test in the paper (P < 0.05/263, Supplementary Table S5), so they do not act on the five diseases
  only through the shared factor. The exception is rs10004996 (Q_SNP P = 0.95). Three sit in the
  APOE/NECTIN2 region of chromosome 19 and one at TRIB1. Both are well-known lipid regions, and the
  APOE region is also an Alzheimer's-risk region, so much of the longevity signal may reflect
  cholesterol and APOE biology rather than ageing as such.
  The three chromosome-19 SNPs are separate lead SNPs (r² < 0.1) but are in the same genomic locus
  (FUMA locus 174), so they are not independent evidence of three biological effects.
- **European ancestry only.** Both the disease GWAS and the longevity GWAS are European-ancestry;
  the paper says this limits generalizability.
- **Not independently replicated here.** The longevity look-up is the paper's own quasi-replication;
  no second cohort was checked for this module.

## How the rows were made, and what was not checked

- Paper metadata, full text (JATS) and supplementary files came from Europe PMC (PMC13601487). All
  numbers in `studies.csv` and `variants.csv` were extracted by script from
  `11357_2025_2044_MOESM2_ESM.xlsx`, sheet **ST9** (proxy-phenotype analysis); Q_SNP P from sheet
  **ST5**. The rsIDs do not appear in the article body.
- **`provenance_quote` is the ST9 workbook row for each variant**, cells as stored in the xlsx
  (full float precision, so e.g. `2.0380000000000001E-8`), joined by single spaces. It was located by
  `claude-opus-5-5` (the `curator` column). Because it comes from a supplementary file, a literature
  pass that searches only the article body will report `quotes_found: 0` for these rows. That is
  expected and does not mean the quote is missing from the paper.
- **`resolution.csv` was written by hand (`source=manual`)** because the enricher was not available
  in the authoring environment. GRCh38 position and alleles come from Ensembl REST `/variation`,
  checked against NCBI dbSNP (same GRCh38 position and ref). dbSNP's GRCh37 position matches the
  paper's own GRCh37 `BP` for all six. The reference base at each GRCh38 position was read back from
  Ensembl `/sequence/region` and matches. `alts` lists every alt allele Ensembl reports, so rs6859,
  rs4803763, rs11754167 and rs10004996 carry a third allele that no genotype row uses. VRS ids were
  minted offline with `just_dna_format.vrs.derive_vrs_allele_id`.
- **Not run:** `just-dna-enricher enrich` (its live ref/rsID-currency checks), the literature pass,
  `check-identifiers`, gnomAD frequencies. None of these is recorded as passed.
- Written by an AI agent (see `authorship`); not yet reviewed by a human geneticist.

## Changelog

- **0.1.0**: first version, six variants from Dinh et al. Supplementary Table S9.
