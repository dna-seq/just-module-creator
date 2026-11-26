# Longevity markers shared with age-related disease (`longevity_ards`)

49 common variants whose alleles were associated with the odds of reaching extreme old age, taken
from the lead variants of a multivariate GWAS of five age-related diseases.

## Where it comes from

One paper: Dinh PA, Han H, Kim S, Guo Q, Zhang ZD, Vijg J, Suh Y. *Genetic links between
multimorbidity and human aging.* GeroScience (2025), doi:10.1007/s11357-025-02044-3, PMID 41405793,
CC BY 4.0.

The authors combined GWAS of heart attack, high cholesterol, hypertension, stroke and type 2
diabetes into one shared genetic factor (mvARD) and found 263 independent lead SNPs. They then looked
each of the 263 up in an independent extreme-longevity GWAS (Deelen et al. 2019, survival beyond the
90th percentile of the birth cohort, N = 36,745, European ancestry) as a proxy phenotype. Those
per-SNP longevity statistics are published in **Supplementary Table S9** (sheet `ST9` of
`11357_2025_2044_MOESM2_ESM.xlsx`), and that sheet is the only source of every number in this module.

Origin: a paper the author handed over; no source-drafted rows. A later pass should follow the
literature, for example a replication of these SNPs in a newer longevity GWAS.

## What is in it

- **Selection.** The 49 of 263 lead SNPs whose longevity P is below 0.05 in ST9. Six of them also pass
  P < 0.05/263 (rs4803763, rs6859, rs10004996, rs11754167, rs2927439, rs28601761); those are tagged
  `stat_significance=significant`, the rest `suggestive`.
- **Direction is the longevity direction.** `direction`, `state` and `weight` come from the longevity
  BETA in ST9, never from the mvARD beta. 48 of the 49 have the allele that raises disease liability
  also lowering longevity odds, as the paper predicts. One (rs34333163, SLC39A8) runs the other way and
  its conclusion says so.
- **Genotypes.** Three rows per SNP: the common homozygote (`neutral`, weight 0.0) as the comparison
  point, the heterozygote and the rare homozygote. "Common" is the more frequent allele in gnomAD v4.1
  non-Finnish Europeans (the module's `frequencies.csv`), and `effect_allele` is the less common one.
  Where that differs from ST9's effect allele, the sign of the BETA was flipped to match.
- **Identity.** rsID only. ST9's CHR/BP are GRCh37 (the paper harmonised to GRCh37), so no coordinate
  was copied; `resolution.csv` supplies GRCh38 positions from Ensembl. Every genotype allele was
  confirmed to be among the resolved ref/alts.
- **`gene`.** FUMA's `nearestGene` from Supplementary Table S5, renamed to the current HGNC symbol
  where it was retired (PPAP2B → PLPP3, PVRL2 → NECTIN2, ZNF259 → ZPR1). For a "lncRNA:gene" pair the
  protein-coding gene was kept. Clone-based lncRNA names, pseudogenes and Y_RNA were left blank (13
  SNPs). The nearest gene is not a causal gene, and every conclusion says so.

## Weighting

Curator-set and ordinal, declared in `module_spec.yaml` under `weighting:`. The per-copy value is
0.5 for the six Bonferroni-tier SNPs and 0.2 for the nominal ones, so a heterozygote carries 1x and a
homozygote 2x. Positive means higher odds of extreme longevity. These are not log-odds and not
comparable with another module's weights.

**Seven SNPs carry no weight on purpose.** Lead SNPs were made independent for mvARD (r² < 0.1), and
that says nothing about whether they are independent signals for longevity. Where two or more kept
SNPs lie within 500 kb, only the one with the smallest longevity P is weighted:

| Region | Weighted | Unweighted |
|---|---|---|
| 1p13 (WNT2B / MOV10) | rs351365 | rs12129649 |
| 8q24 | rs28601761 | rs7012891 |
| 12q21 (ATP2B1) | rs73437382 | rs7975788 |
| 12q24 (HNF1A / KDM2B) | rs1169288 | rs10774597 |
| 19q13 (APOE region) | rs6859 | rs2927439, rs62117206, rs4803763 |

Their rows still carry `state`, `direction` and a conclusion; only the score contribution is withheld.

## What this module is not

- **Not a longevity predictor.** Each marker shifts the odds of reaching extreme old age by a few
  percent. The paper's own claim is about the 263 SNPs **in aggregate** (76% sign discordance, P =
  1.4e-17), not about any single one.
- **Not replicated per SNP, and about half the nominal rows may be chance.** ST9's own omnibus
  table counts 49 of the 263 at P < 0.05 against about 22 expected under its matched null (P =
  1.2e-7), and 6 at P < 0.05/263 against an expected 0. So the set as a whole is enriched, but
  roughly 22 of the 43 nominal-only rows could be noise and nothing here says which. The six
  Bonferroni-tier rows are the ones to lean on.
- **Not ancestry-general.** Every source cohort is European.
- **Not about the four candidate genes** (DCAF16, PHF13, MGA, GTF2B) the paper prioritised for mvARD.
  Those are gene-level results from TWAS, colocalisation and MR, with no variant-level longevity claim,
  so they contribute no rows. Neither do the lifestyle MR results or the genetic correlations.
- **Not about the 214 lead SNPs with longevity P ≥ 0.05.** Including them would assert a longevity
  direction for SNPs the longevity data did not support individually.

## Known limits a reviewer should check

- **Palindromic SNPs.** 12 of the 49 are A/T or C/G (rs3924092, rs3732837, rs11771259, rs6961048,
  rs28601761, rs964184, rs73437382, rs7310615, rs35443, rs35317317, rs62117206, rs4803763). Their
  strand cannot be confirmed by allele membership. The paper used the EBI gwas-sumstats-harmoniser,
  which orients alleles to the forward strand, and that is what this module relies on.
- **`provenance_quote` comes from the supplementary sheet, not the article body.** Each quote is the
  rsID followed by that row's longevity cells from ST9 (EA, OA, BETA, SE, P, Discordance?), exactly as
  the workbook stores them. `enrich_literature_pass` searches the article body only, so
  `quotes_found: 0` on all 49 rows is expected and says nothing about the rows. Quotes were located by
  `claude-opus-5-5` (the `curator` column).
- **Effect sizes.** `effect_size` on `variants.csv` is the ST9 longevity BETA, re-signed to the
  module's `effect_allele`. `studies.csv` keeps ST9's own effect allele and sign. The "roughly N%
  higher/lower odds" in each conclusion assumes that BETA is a per-allele log-odds from a
  case-control logistic model. ST9's header only says BETA, but the paper's text describes the test
  as "lower odds of extreme longevity".
- **Disease-specific pathways.** 26 of the 49 SNPs have a significant Q_SNP heterogeneity test in
  Supplementary Table S5 (P < 0.05/263), which the paper reads as acting through some of the five
  diseases more than through the shared factor. Their conclusions say so.
- **APOE region.** Four of the SNPs (rs2927439, rs62117206, rs4803763, rs6859) lie on chromosome 19
  around APOE. Their conclusions note that the region has been linked to longevity before. That note
  rests on the source paper's own reference 20, Broer et al. 2015, *GWAS of longevity in CHARGE
  consortium confirms APOE and FOXO3 candidacy* (PMID 25199915), and not on ST9. The longevity
  statistics themselves come from Deelen et al. 2019, *A meta-analysis of genome-wide association
  studies identifies multiple longevity genes* (PMID 31413261), as re-analysed in ST9.
- **Frequencies** are gnomAD v4.1 joint, non-Finnish European, as the frequencies pass wrote them.

## Authorship

Written entirely by an AI agent (`claude-opus-5-5`, see `authorship:`), from the paper and its
supplementary workbook. No human has reviewed the rows yet.
