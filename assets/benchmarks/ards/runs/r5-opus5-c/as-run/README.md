# Human longevity and the shared genetics of age-related disease (Dinh 2025)

This module records the 263 independent lead variants across 180 genomic loci
associated with **mvARD** — a latent genetic factor shared by heart attack, high
cholesterol, hypertension, stroke and type 2 diabetes — together with each
variant's effect in an independent **extreme-longevity** GWAS and in each of the
five contributing disease GWAS.

Source: Dinh P-A, Han H, Kim S, Guo Q, Zhang ZD, Vijg J, Suh Y.
*Genetic links between multimorbidity and human aging.* GeroScience 48:7277–7292
(2026), [doi:10.1007/s11357-025-02044-3](https://doi.org/10.1007/s11357-025-02044-3),
PMID 41405793, PMC13601487. The article is Open Access under CC BY 4.0, so its
tabular values and two quoted sentences are reproduced here with attribution.

The authors built mvARD with genomic structural equation modelling over five
European-ancestry ARD GWAS (effective N = 475,203, SNP h² = 9.17%, LDSC
intercept 0.99) and then asked whether its variants also move human lifespan.
They do: 199 of 263 lead SNPs (76%) push mvARD and extreme longevity in opposite
directions, and 49 (18.6%) reach nominal significance in the longevity GWAS
against 8.4% expected. That set-level enrichment is the reason this is a
longevity module rather than a cardiometabolic one.

## What is in this module

| Table | Rows | Contents |
|---|---|---|
| `weights.parquet` | 789 | 263 variants × 3 genotypes, weighted by mvARD dosage |
| `annotations.parquet` | 789 | per-genotype prose, nearest gene, category |
| `studies.parquet` | 1,841 | 7 association rows per variant (see below) |
| `sources.parquet` | 6 | licensing for every upstream source |
| `literature.parquet` | 6 | every PMID cited by `studies`, verified via Europe PMC |
| `clin_sig_authority_calls.parquet` | 0 | no clinical-significance claims are authored |
| `clin_sig_concordance.parquet` | 0 | — |

`studies.parquet` carries seven rows per variant, all oriented to one effect
allele:

| `pmid` | `phenotype_class` / `stratum_level` | What it is |
|---|---|---|
| 41405793 | `age-related disease multimorbidity` | the mvARD association (Supplementary Table S5) |
| 31413261 | `extreme longevity` | lookup in Deelen 2019 (Supplementary Table S9) |
| 33959723 | `high_cholesterol`, `hypertension` | Dönertaş 2021 UK Biobank GWAS (Table S6) |
| 30054458 | `type_2_diabetes` | Xue 2018, GCST006867 (Table S6) |
| 29531354 | `stroke` | Malik 2018 / MEGASTROKE, GCST006906 (Table S6) |
| 33532862 | `heart_attack` | Hartiala 2021, GCST011364 (Table S6) |

The per-disease rows are what let a consumer see *why* a variant is in a
"multimorbidity" set. The 263 loci are not evenly shared: at genome-wide
significance they are driven by hypertension (177/263), then high cholesterol
(45), type 2 diabetes (42), heart attack (9) and stroke (3).

## How the weights work

`weight = dosage(effect allele) × published per-allele mvARD beta`, so the three
genotype rows carry `2β`, `1β` and `0`. `effect_size` on a `weights` row is the
genotype-scaled value; the per-allele beta lives in `studies.effect_size`.

Two orientation facts matter more than usual here.

**The effect allele is the GRCh38 reference allele at all 263 loci.** This was
checked variant by variant against Ensembl, and three positions were confirmed
against the GRCh38 sequence itself. The zero-weight genotype in this module is
therefore the homozygous *alternate* genotype, not the homozygous reference, and
a consumer that assumes "ref/ref = 0" will invert every score. Use
`effect_allele`, never ref/alt, to compute dosage.

**Supplementary Table S6 is oriented the other way round.** The published
per-disease columns report the effect of the mvARD *non*-effect allele. Every
contributing-ARD beta in this module has had its sign flipped so the whole module
speaks about one allele; each such row says so in its `conclusion`. The
orientation was not taken on trust: across the 1,315 variant × disease cells,
the published betas agree in sign with mvARD for 103 (7.8%) as printed and for
1,212 (92.2%) after flipping, which is the expected behaviour for a factor whose
five loadings are all positive.

`state` is `risk` when the effect allele raises mvARD, `protective` when it
lowers it (138 and 125 variants respectively) and `neutral` on the zero-dose row.
These labels describe the sign of a population association with a latent disease
factor. They are not a diagnosis, a probability, or a prediction about how long
anyone will live.

### Scale, and why these weights should not be summed naively

mvARD is a latent factor. The paper is explicit that it "lacks the conventional
units", which is why `effect_unit` says so on every row and `trait_efo_id` is
left empty for the mvARD rows (no ontology term exists for a multivariate
disease factor; see *Known gaps*). Per-allele betas run from 0.0118 to 0.0825 in
absolute value, median 0.0164.

A raw sum over the 263 loci is a relative index at best, and it has a specific
defect: 98 of the 263 lead SNPs (37%) have Q_SNP heterogeneity below the paper's
0.05/263 threshold, and 176 below nominal 0.05, meaning their effect on the five
diseases is *not* mediated by the shared factor. The authors dropped every
nominally heterogeneous SNP before their own downstream analysis. A consumer
building a shared-liability score should do the same: filter on the
`qsnp_heterogeneous` / `qsnp_heterogeneous_nominal` flags, which leaves 87
variants. All 263 are kept here so the filter is the consumer's choice, not an
undocumented one baked into the data.

## The longevity evidence, stated carefully

`outcome_exceptional = true` means one thing only: this variant reached nominal
significance (P < 0.05) in the Deelen 2019 extreme-longevity GWAS, in the lookup
reported in Supplementary Table S9. It is `true` for 49 variants and `false` for
the other 214 — `false` here means *tested and not significant*, not *untested*.

`outcome_lifespan` and `outcome_healthspan` are left null throughout. mvARD is
strongly genetically correlated with parental lifespan (rg −0.65) and healthspan
(rg +0.65), but those are trait-level correlations from LDSC, not variant-level
evidence, and this module does not have per-variant results for those two
phenotypes. Setting the flags from a genome-wide rg would be an overclaim.

Only 6 variants survive Bonferroni correction (P < 0.05/263) in the longevity
GWAS, and **three of the six sit in the APOE region on chromosome 19**:

| rsID | GRCh38 | Nearest gene | mvARD β | Longevity β | Longevity P | Q_SNP P |
|---|---|---|---|---|---|---|
| rs6859 | 19:44878777 | NECTIN2 | +0.0146 | −0.112 | 2.0e−8 | 2.2e−37 |
| rs4803763 | 19:44854034 | NECTIN2 | −0.0145 | +0.118 | 8.4e−7 | 3.6e−31 |
| rs11754167 | 6:126856330 | RPS4XP9 | −0.0181 | +0.090 | 6.0e−6 | 5.7e−19 |
| rs10004996 | 4:38382012 | RP11-83C7.1 | +0.0153 | −0.085 | 1.1e−5 | 0.95 |
| rs2927439 | 19:44739483 | BCL3 | +0.0150 | −0.085 | 8.9e−5 | 2.6e−26 |
| rs28601761 | 8:125487789 | RP11-136O12.2 | +0.0312 | −0.074 | 1.4e−4 | 2.0e−51 |

Five of these six are strongly heterogeneous across the five diseases, so the
per-variant longevity signal is concentrated in exactly the SNPs that the paper
excluded from its shared-mechanism analyses. Variants within 1 Mb of APOE carry
an `apoe_region` flag and say so in their `conclusion`. The honest summary is
that the longevity link is a robust property of the 263-SNP *set* (three
independent set-level tests, P = 1.4e−17, 1.2e−7 and 9.7e−12) and is weak or
APOE-driven at the level of any individual variant.

### Field conventions worth knowing

* `confidence` holds the published standard error of `effect_size`, with
  `confidence_unit = "standard_error"`. It is not a confidence interval.
* `flags` on `weights` rows uses this vocabulary, authored by this module:
  `novel_locus` (6), `qsnp_heterogeneous` (98, P < 0.05/263),
  `qsnp_heterogeneous_nominal` (78, P < 0.05), `longevity_replicated_bonferroni`
  (6), `longevity_replicated_nominal` (43), `longevity_sign_discordant` (199),
  `longevity_sign_concordant` (64), `strand_ambiguous` (38, A/T or C/G sites
  that cannot be strand-resolved from alleles alone), `coding_or_exonic` (13),
  `apoe_region` (5, within 1 Mb of APOE), `multiallelic_site` (152, Ensembl
  lists more than one alternate allele). No registry vocabulary for this field
  was available while building, so these terms may need remapping before
  publication; everything they encode is also stated in `conclusion` prose and
  in `annotations.category`, so nothing is lost if the column is dropped.
* `trait_efo_id` is `OBA_VT0005372` (life span determination trait, the term the
  GWAS Catalog assigns to GCST008598) on longevity rows, MONDO/HPO terms on the
  five disease rows, and null on mvARD rows.

## Coordinates and gene symbols

The paper publishes GRCh37 positions only. All 263 rsIDs were resolved
independently against the Ensembl REST API (release 116) to GRCh38: every one
returned exactly one primary-assembly placement, the chromosome agreed with the
paper, and both the effect and non-effect allele appeared in Ensembl's allele
string. GRCh37 positions are kept in `build/variants.csv` for traceability but
are not authored into the module.

`vrs_id`, `vrs_spec`, `caid` and the placement-witness fields of
`resolution_loci` are null. Those identifiers are produced by the publishing
pipeline's enrichment layer; computing them by hand here would risk fabricating
identifiers that look authoritative. `resolution_loci` records what was actually
established: an Ensembl GRCh38 placement with its release.

Eighteen distinct `nearestGene` labels from FUMA were repaired against HGNC:

* **Spreadsheet damage in the published supplement** — `NPR 3.00` → `NPR3`
  (rs62369525) and `ARL 15.00` → `ARL15` (rs702634). Both were confirmed by
  locus coordinates. `ALG9:ALG9` → `ALG9`.
* **Withdrawn symbols updated** — PVRL2→NECTIN2, GUCY1A3→GUCY1A1, ZNF259→ZPR1,
  HIST1H3G→H3C8, PPAP2B→PLPP3, PHB→PHB1, C10orf107→CABCOCO1, C1orf172→KDF1,
  C1orf145→OBSCN-AS1, FAM101A→RFLNA, LRRC48→DRC3, LSMD1→NAA38,
  LINC00936→ATP2B1-AS1, PALM2-AKAP2→PALM2AKAP2, RP11-354A14.1→LINC02235.

Fifty-seven label components remain outside HGNC. These are clone-based GENCODE
identifiers (`RP11-…`, `CTD-…`, `AC######.#`) and RNA family labels (`Y_RNA`,
`Metazoa_SRP`) from the GENCODE build FUMA used; they are kept verbatim rather
than guessed at. In every case the nearest gene is a positional annotation, not
a claim about the causal gene.

## Pleiotropy: these are cardiometabolic loci

Supplementary Table S8 counts GWAS Catalog associations per lead SNP. The median
lead SNP already has 11 published trait associations and the most connected have
hundreds: rs6547692 (GCKR) and rs964184 (ZPR1) at 557 each, rs12740374 (CELSR2)
323, rs7310615 (SH2B3) 288. Fourteen have none. These counts are reproduced in
the `conclusion` of each mvARD study row.

A consumer should present this module as *shared cardiometabolic disease
liability that happens to track survival*, not as "longevity genes". The paper
says the same thing about itself: the five diseases that survived its genetic
correlation filter are all cardiometabolic, which it names as a limitation of
the gSEM framework rather than a biological result.

## What the paper found that is not in these tables

The just-dna table set is variant-centric, so three substantial results of the
paper have nowhere to live and are recorded here only:

* **Gene prioritisation.** TWAS in whole blood (Young Finns models) gave 42
  significant genes, 22 with colocalisation PP4 > 0.8. Four — **DCAF16, PHF13,
  MGA, GTF2B** — were also supported by eQTLGen Mendelian randomisation. These
  are gene-level, eQTL-mediated inferences, not variant annotations.
* **Genetic correlations.** mvARD vs parental lifespan rg = −0.65 (P = 6e−122),
  healthspan +0.65 (P = 9e−79), frailty index +0.60 (P = 9e−116), extreme
  longevity −0.44 (P = 1.4e−11); 19 of 33 tested traits pass Bonferroni.
* **Lifestyle Mendelian randomisation.** Of 21 exposures, BMI (b = +0.125 IVW,
  P = 6e−21), coffee intake and tea intake raised mvARD and years of education
  lowered it (b = −0.030, P = 3e−10) at the 0.05/21 threshold; smoking
  initiation, insomnia and red meat were nominal only. Several rest on few
  instruments and on UK Biobank samples that overlap the mvARD input GWAS.

Also not carried: GARFIELD regulatory enrichment (Table S11), CADD and
RegulomeDB scores and chromatin states (Table S5, except CADD which appears in
the mvARD `conclusion` text), and the full GWAS Catalog trait lists (Table S7).

## Population

Everything here is European-ancestry. `eur_only_evidence` is `true` on every
weights row. The one wrinkle: the catalogued T2D study GCST006867 also contains
1,178 Pakistani-ancestry cases and 2,472 controls alongside 61,714 European
cases, so the "European only" description of the inputs is approximate for that
one contributing GWAS. Allele frequencies, LD and effect sizes do not transfer
to other ancestries without re-estimation.

## What this module does not cover

* **No polygenic scores.** `pgs.parquet` is absent because the PGS Catalog has
  no published score for longevity, healthspan or parental lifespan (checked
  November 2026), and mvARD itself has no catalogued score. The mvARD summary
  statistics are public at <https://zenodo.org/records/15522815> if a consumer
  wants to build one.
* **No clinical significance.** No ClinVar assertion, pathogenicity call or
  actionability claim is authored; `actionability` is `descriptive` throughout
  and the two `clin_sig_*` tables are empty.
* **No pharmacogenomics, no lifestyle advice.** The lifestyle MR results above
  are summarised, not operationalised.
* **No rare variants.** Lead-SNP MAF ranges from 0.025 to 0.497.

## Curation

AI-authored (`ai-module-creator`), from the published supplementary workbook
rather than the article prose. The XLSX was parsed with a purpose-written
stdlib reader; `build/` contains the build script, the authored
`variants.csv` and `resolution.csv`, and a 572-assertion validator
(`build/validate.py`) that is run on every build. It re-derives the paper's own
headline counts from the compiled tables — 263 lead SNPs, 180 loci, 199
sign-discordant, 49 nominal, 6 Bonferroni, 98 heterogeneous — and fails the
build if any of them drifts.

Checks performed:

* Supplementary Tables S5, S6, S8 and S9 agree on all 263 rsIDs, alleles and
  mvARD betas; this was verified, not assumed.
* Every PMID, DOI and PMCID was resolved through Europe PMC; the four
  catalogued input GWAS were cross-checked against the GWAS Catalog v2 API,
  which confirmed accession, PubMed ID, trait ontology term and sample counts.
  Sample sizes in Supplementary Table S1 sum exactly to the Ns quoted in the
  article text for all five diseases.
* Both quoted sentences were regex-matched against the article full text.
* Gene symbols were checked against the HGNC complete set.

Two discrepancies were found and are not adjudicated here:

1. **`rs6505080` does not exist in this paper's data.** The Results text names
   `rs1788785, rs10931284, rs6505080, rs72887634` as the novel variants with
   known GWAS Catalog associations. `rs6505080` appears in no supplementary
   table. Supplementary Tables S5, S6 and S8 instead list `rs650508`
   (chr2:45,880,122 GRCh37, nearest gene PRKCE, 10 known trait associations),
   which fits the sentence. This module follows the supplement and carries
   `rs650508`. The article text looks like a typographical error, but that was
   not confirmed with the authors.
2. **`NPR 3.00` / `ARL 15.00`** in Supplementary Table S5 are spreadsheet
   number-formatting damage, repaired as described above.

Research and informational use only. Not a clinical test, not a diagnosis, and
not a prediction of anyone's lifespan.
