# Longevity and shared age-related disease liability (Dinh 2025, mvARD)

This module records the **263 genome-wide significant lead SNPs** (180 loci) for the
*multivariate age-related disease factor* (mvARD) from
[Dinh et al., GeroScience (2025/2026), "Genetic links between multimorbidity and human aging"](https://doi.org/10.1007/s11357-025-02044-3),
PMID 41405793, PMC13601487. For each SNP it also records the paper's look-up of that SNP in an
independent **extreme-longevity GWAS** ([Deelen et al., Nat Commun 2019](https://doi.org/10.1038/s41467-019-11558-2),
PMID 31413261: 11,262 people who survived past the 90th age percentile of their birth cohort, compared with 25,483 controls).

mvARD is the genetic liability shared by five common age-related diseases: heart attack,
high cholesterol, hypertension, stroke and type 2 diabetes. It was estimated with genomic SEM
from European-ancestry GWAS, with an effective N of 475,203. The paper's central longevity result is a
property of the **set** of SNPs, not of any single one. At 199 of the 263 SNPs (76%, one-sided
P = 1.4E-17), the allele that raises mvARD has a lower-odds point estimate for extreme longevity.
49 SNPs reach nominal P<0.05 against 8.4% expected under a frequency-matched null. Only 6 survive
correction for 263 tests.

## What is in the module

| Table | Rows | Content |
|---|---|---|
| `weights.parquet` / `annotations.parquet` | 789 (263 × 3 genotypes) | genotype-level interpretation |
| `studies.parquet` | 526 (263 × 2) | one mvARD row (PMID 41405793) and one longevity row (PMID 31413261) per SNP |
| `literature.parquet` | 2 | both papers, PubMed-resolved, CC BY |
| `sources.parquet` | 6 | provenance and licences |
| `clin_sig_*` | 0 | no authority calls authored |

**Genotype labels.** `risk` means the genotype carries at least one copy of the allele that
*raises* mvARD. `protective` means it carries none, but only relative to allele dosage under the study's
additive model. It is never a claim of immunity. Heterozygotes are labelled `risk`, the same
convention as `adhd_gwas_loci`. `stat_significance` on genotype rows refers to the mvARD association,
which is genome-wide significant for every row. The longevity evidence for each SNP is spelled out in
its conclusion text and in its longevity `studies` row.

**No weights are authored.** mvARD is a latent construct with no conventional unit (the paper says
so explicitly). The paper did not build or validate a score, and 98 of the SNPs fit the
common-factor model poorly. **These rows must not be summed as a polygenic score.** `effect_size` in
`studies` is the per-allele beta on the mvARD factor or, in the longevity rows, the log(OR).

**`flags`** (on every genotype row, per SNP):

| Flag | SNPs | Meaning |
|---|---|---|
| `qsnp_heterogeneous` | 98 | Q_SNP P < 0.05/263. The SNP's effects on the 5 diseases are not well explained by the shared factor. These are the SNPs highlighted in the paper's ST5 (the highlighting was cross-checked). |
| `qsnp_nominal` | 78 | 0.05/263 ≤ Q_SNP P < 0.05. The paper also excluded these from its downstream analyses. |
| *(neither)* | 87 | consistent with a purely shared mechanism |
| `longevity_bonferroni` | 6 | longevity P < 0.05/263 (all 6 in the expected, opposite direction) |
| `longevity_nominal` | 43 | 0.05/263 ≤ longevity P < 0.05 |
| `longevity_not_significant` | 214 | |
| `longevity_expected_direction` / `longevity_unexpected_direction` | 199 / 64 | sign of the longevity estimate relative to the mvARD-raising allele |
| `novel_mvard_locus` | 6 | > 1 Mb from every locus of the five input GWAS |

**Outcome tags.** `outcome_exceptional = true`, because every row carries the 90th-percentile
longevity look-up. `outcome_healthspan = true`, because mvARD is liability to age-related cardiometabolic
multimorbidity, and the paper reports r_g = 0.65 with healthspan, −0.65 with parental lifespan and 0.60 with
the frailty index. `outcome_lifespan` is left null. `eur_only_evidence = true`.

**Trait identifiers.** The longevity study rows use `OBA_VT0005372` (life span determination trait),
which is the GWAS Catalog's mapping for GCST008598. No EFO/MONDO term exists for mvARD or
multimorbidity, so `trait_efo_id` is null on the mvARD study rows and on all genotype rows.

## Things a reader should know

* **The six Bonferroni-significant longevity SNPs.** Three are in the chr19q13.32 APOE/TOMM40/NECTIN2
  region: rs6859 and rs4803763 (FUMA nearest gene "PVRL2", now NECTIN2) and rs2927439 (BCL3).
  The other three are rs10004996 (chr4), rs11754167 (chr6) and rs28601761 (chr8, near TRIB1).
  Neither APOE-defining SNP (rs429358, rs7412) is an mvARD lead SNP, and this module does not call
  APOE genotype. Five of the six are Q_SNP-heterogeneous.
* **One nominal longevity hit goes the "wrong" way.** At rs34333163 (SLC39A8) the mvARD-raising
  allele has *higher* longevity odds (P = 7.0E-04).
* **Heterogeneous SNPs are not weaker longevity evidence here.** 86/98 Q-heterogeneous SNPs are in the
  expected direction, compared with 59/87 of the Q-clean SNPs. This is reported as an observation, not interpreted.
* **HFE C282Y (rs1800562)** is an mvARD lead SNP. Its genotype rows carry an explicit caveat that the
  hemochromatosis meaning is separate from the mvARD association, and the A/A row has `acmg_sf = true`.
  Seventeen other lead SNPs have ClinVar records, all benign, association, drug-response, conflicting or
  VUS (e.g. MTHFR rs1801133, APOB rs1367117, LPA rs10455872, KCNJ11 rs5215). No clinical significance
  is authored for them.
* **Nearest genes are FUMA positional annotations** with the paper's (2017-era) names, e.g.
  RP11-/CTD- clone IDs and PVRL2. They are mentioned in the text but `gene` is left empty, because nearest ≠ causal.
  The paper's four high-confidence genes from TWAS + colocalisation + MR (DCAF16, PHF13, MGA, GTF2B) are
  gene-level results with no single variant to annotate, so they are not represented as rows.
* 38 SNPs are strand-ambiguous (A/T or C/G). The paper's harmonised alleles, the Deelen file and
  Ensembl/dbSNP GRCh38 all agree on forward-strand alleles, but array-based consumer data for these
  SNPs should be checked for strand.
* All evidence comes from European-ancestry samples. The UK Biobank contributes to several input GWAS.

## Not covered

The paper's MR of lifestyle factors (BMI, coffee, tea, education, …), the gene-expression MR, TWAS,
GARFIELD enrichment, the genetic-correlation table and the 6 novel loci's GWAS Catalog trait lists are
not variant-genotype annotations and are left out. There is no PGS: the paper did not publish one.
The mvARD summary statistics are on Zenodo (record 15522815) for anyone who wants to build one.

## Curation and verification

AI-authored (Claude Opus 5.5) from the article text and ESM2 (Supplementary Tables S5 and S9).
The build is reproducible from `../build/` and `../authoring/`. Every check below is a hard assertion in
`build/stage_inputs.py` or `build/validate.py`:

* ST5 and ST9 agree on all 263 SNPs (alleles, GRCh37 positions, betas, P-values, discordance flags),
  and the 98 highlighted ST5 rows are exactly those with Q_SNP P < 0.05/263.
* **All 263 longevity beta/SE/P values in ST9 were reproduced exactly** from the original
  GCST008598 summary statistics (`Results_90th_percentile.txt.gz`), after aligning 146 allele flips.
* GRCh38 placements come from Ensembl REST release 116. They agree with NCBI dbSNP at every SNP, and
  dbSNP's GRCh37 position equals the paper's position at every SNP. Both paper alleles are present in
  the GRCh38 allele set for all 263 SNPs.
* VRS 2.0 allele IDs were computed locally. The implementation reproduces every VRS ID in the
  `adhd_gwas_loci` and `bodybuilding` modules, and the variation-normalizer service on 7 test
  alleles covering the remaining chromosomes.
* PMIDs, DOIs and PMCIDs were checked against PubMed. Both papers are CC BY 4.0 according to Europe PMC.
  No article passage is quoted (`quotes_authored = 0`), because all row values come from tables.
* The resolution layer uses dbSNP as its placement witness, not the ClinVar/ClinVar-GKM witness
  used by the published modules. Those layers were not available in this run.

Research and informational use only. These rows are not a diagnosis, a disease-risk estimate or a
lifespan prediction.
