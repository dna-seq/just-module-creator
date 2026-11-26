# Longevity — coding variants shared by 21 centenarian/supercentenarian genomes (Sundar Raj 2025)

This module records the coding SNPs that
[Sundar Raj et al., Human Genomics 19:115 (2025)](https://doi.org/10.1186/s40246-025-00772-3)
(PMID 41057961, PMC12506250) reported as present in **all 21** whole genomes of
18 supercentenarians (110–117 years) and 3 centenarians (106–109 years), and that
SIFT predicted to be deleterious. The cohort was 13 women and 8 men: 17 Caucasian,
2 African, 1 Hispanic and 1 Ashkenazi Jewish, from the Betterhumans supercentenarian study.

**Read this first: these are not longevity-associated variants.** The study had
no control group and ran no association test. The supplementary tables do not
report zygosity, effect sizes or p-values. "Deleterious" is an in-silico SIFT
call, not observed harm. Every genotype row is therefore `state = neutral`,
`direction = unknown` and `weight = null`. The rows must never be summed or
scored. The module documents what the paper reported, together with
population-frequency context showing how little "shared by all 21" means for
most of these alleles.

## What is in it

**108 variants, 324 genotype rows, 77 genes.**

- 107 of the paper's 110 SIFT-deleterious variants (Supplementary Files 11
  and 13).
- rs412051 (BRD8). It is SIFT-tolerated, but the paper's text names it as
  previously linked to longevity. rs9885916 (PRIM2), the other variant named
  that way, is already in the deleterious set.

Each variant has three genotype rows: two copies, one copy or no copy of the
allele the paper reported. Alleles are on the GRCh38 forward strand.

Each row's `category` and `conclusion` place the variant in one of five
classes. The classes come from gnomAD genome (and 1000 Genomes) frequencies
of the reported allele, retrieved via Ensembl REST release 116. Each row also
gives the probability, under Hardy-Weinberg equilibrium, that 21 random people
would all carry the allele.

| Class | Variants | What it means |
|---|---|---|
| Majority allele, sharing expected | 61 | Allele frequency 0.6–1.0 worldwide. Most random 21-person groups would all carry it (e.g. AADAC rs1803155 0.76, ERCC5 rs9514066 0.998, BMP3 rs6831040 0.999). |
| Likely mapping artifact (flat ~50%) | 15 | gnomAD reports about 0.50 in *every* ancestry group. This is the signature of paralogous reads (MAP2K3, KCNJ12, MUC3A, MUC6, GPRIN2, ANKRD20A1, FRG1B, ZNF676, OR8U1, OR9G1, SLC9B1). For MUC6, OR9G1 and KCNJ12, 1000 Genomes reports ≤0.05 for the same allele. |
| Improbable sharing | 1 | KMT2C rs10454320 has frequency 0.41. Only about 1 in 10,000 random 21-person groups would all carry it. |
| Rare in reference panels | 13 | gnomAD frequency below 0.05, mostly below 0.0001 (OR4C3/OR4C5 cluster, PDE4DIP, TIMM23, PRIM2, TRBV7-3, MAP2K3, KCNJ12, PRSS3). |
| Absent from reference panels | 18 | No gnomAD or 1000 Genomes frequency, typically because the site fails filters in duplicated regions (OR4C3/OR4C5, PDE4DIP, ANKRD36C, MUC4, TIMM23, PRIM2, TRBV10-2, HNRNPCL1). |

For the last three classes: a truly rare allele carried by all 21 unrelated
people of four ancestries is statistically implausible. These calls more likely
reflect alignment in segmental duplications and gene families. The paper
reports neither read-level QC nor zygosity, so we could not test this further.

## Corrections to the paper's identifiers

- **"Novel" variants mostly are not novel.** Of the 16 variants the paper
  calls novel, 14 have dbSNP rsIDs at the same GRCh38 position with the same
  alleles (e.g. MAP2K3 "novel" = rs56216806, KCNJ12 = rs1714864, MUC3A =
  rs74460367). 43 variants had no rsID in the paper; all 43 were assigned
  one by allele-matched position.
- **Not placed (3, excluded; see `source/excluded.csv`).**
  - PRAMEF22 chr1:13036247 T/A and PRAMEF13 chr1:13449723 G/C: these GRCh37
    positions have no GRCh38 mapping.
  - TIMM23B chr10:51381481 C/T: it lifts over, but the GRCh38 base is T and
    no dbSNP record matches.
- **Build discrepancies.** For TIMM23 (rs61849494, rs61849498), PRIM2
  (rs9885913, rs9885916) and ANKRD20A1 (rs62542472), the GRCh37 position
  either does not lift over or lifts to a different place than the rsID's
  GRCh38 position. These were placed via the paper's rsID. Seven variants are
  reverse-complemented between builds.
- **Reference base changed between builds.** At six variants the paper's
  "alternate" allele is the GRCh38 reference base (PDE4DIP ×3, OR52L1 ×2,
  MUC3A ×1).
- **Paper's frequency columns are not minor-allele frequencies.** The tables
  headed "Minor Allele" in Supplementary Files 9 and 12 report the ALT allele
  frequency, which is often above 0.9. So the table does not show which
  variants are actually rare.
- **ClinVar.** ClinVar classifies 17 of these alleles as Benign or
  Benign/Likely benign (`clin_sig_authority_calls.parquet`). ERCC5 rs9514066
  has one Likely-pathogenic ClinVar record, but it is for a *different*
  allele (G>T, p.Gly1053Ter). The allele in this module (G>C) is Benign.
- **Gene symbols.** Paper symbols are kept in the conclusion text, and the
  `gene` column uses current HGNC symbols. KIAA1551→RESF1, C5orf45→MRNIP,
  TTC30B→IFT70B, FRG1B→FRG1BP (a pseudogene), MDM1→SAXO6. MDM1/SAXO6 is a
  centriole protein; the paper's description of it as a p53-pathway regulator
  appears to confuse it with MDM2. The module adopts none of the paper's
  gene-function narratives.

## Not included

- The paper's 754,520 shared SNPs, its 4,980 non-synonymous SNPs and the
  Reactome pathway enrichment. None of these are genotype-level claims.
- Insertions/deletions and chrX/chrY/chrM variants. None are in the
  deleterious set.
- Any polygenic score. The paper proposes none.
- Supplementary File 13's "aging references". These are a mix of PubMed
  links, theses, patents and web pages attached to individual SNPs. They are
  recorded in `source/variants.csv` (`aging_reference`) but were not checked
  and are not used as evidence.

## Provenance and licence

- **Source data.** Alleles, positions, SIFT scores and amino-acid changes were
  transcribed from Supplementary Files 11–13. GRCh38 placements, alleles and
  frequencies come from Ensembl REST (release 116), and ClinVar classifications
  from NCBI E-utilities (accessed 2026-11-26).
- **VRS identifiers.** The GA4GH VRS 2.0 identifiers were computed locally.
  Refget digests were computed from the INSDC GRCh38 chromosome records
  (CM000663.2–CM000684.2, streamed from ENA). The method reproduces all 38 VRS
  IDs in the two reference modules, and for the other chromosomes the md5s
  match ENA's refget registry.
- **Licence.** The article and its supplements are **CC BY-NC-ND 4.0**. Only
  factual identifiers and numbers were transcribed, and no article text is
  quoted (`provenance_quote` is empty). Whether a curated annotation of these
  facts counts as an "adapted work" under ND has not been established, so the
  paper source is marked `commercial_use = false`. Treat the module as
  non-commercial until that is settled.

## Curation

AI-authored by Claude Opus 5.5. No official module compiler or validator was
available. The parquet files were written to the exact column schemas of the
reference modules and checked with `build/check_module.py`, not by the
production toolchain. `placement_witness`, `placement_verdict` and `caid` are
left empty because the ClinVar-GKM / ClinGen witness step was not run.

Research and informational use only. This module is not a predictor of
lifespan.
