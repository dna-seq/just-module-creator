# Longevity and shared age-related disease risk (`longevity_ards`)

48 common variants where one study found both a shift in the shared genetic liability to five
age-related diseases **and** a shift, in the opposite direction, in the odds of extreme human
survival. 144 genotype rows, 96 study rows.

**Built from.** Dinh P-A, Han H, Kim S, Guo Q, Zhang ZD, Vijg J, Suh Y.
*Genetic links between multimorbidity and human aging.* GeroScience (2025).
[doi:10.1007/s11357-025-02044-3](https://doi.org/10.1007/s11357-025-02044-3) ·
PMID 41405793 · PMC13601487 · CC BY 4.0. Specifically its Supplementary Tables S5 and S9.

**Also cited.** Deelen J, Evans DS, Arking DE, et al. *A meta-analysis of genome-wide association
studies identifies multiple longevity genes.* Nat Commun 10, 3669 (2019).
[doi:10.1038/s41467-019-11558-2](https://doi.org/10.1038/s41467-019-11558-2) · PMID 31413261 ·
CC BY 4.0. Every longevity number in this module originates in Deelen's summary statistics, so the
longevity rows in `studies.csv` cite Deelen, not Dinh — see *Which paper each row cites* below.

---

## What the paper did

It combined GWAS summary statistics for five genetically correlated age-related diseases — heart
attack, high cholesterol, hypertension, stroke and type 2 diabetes — into one latent factor using
genomic structural equation modelling, and called that factor **mvARD**. A multivariate GWAS of
mvARD found 263 lead SNPs across 180 loci.

Because no cohort has been measured for "mvARD", the authors could not replicate it directly.
Instead they looked all 263 lead SNPs up in an independent extreme-longevity GWAS (Deelen et al.
2019, PMID 31413261: cases survived past the 90th percentile of their birth cohort, N = 36,745) and
asked whether the signs ran the other way, as the geroscience hypothesis predicts. They did:
*"76% of SNPs showed the expected direction of effect"*, and the set was enriched for longevity
signal on three separate tests.

**This module is built from that look-up table (Supplementary Table S9), not from the headline
GWAS.** The 263-SNP enrichment is a statement about the set. A row in a genome report is a statement
about one person at one position, and only the subset with its own longevity statistic can carry one.

## What got a row, and what did not

| | variants |
|---|---|
| mvARD lead SNPs in the paper | 263 |
| of those, longevity association nominally significant (P < 0.05) | 49 |
| of those, in the direction the hypothesis predicts (discordant) | **48 — every row in this module** |
| dropped: longevity P ≥ 0.05 | 214 |
| dropped: nominally significant but *concordant*, i.e. the wrong way round | 1 |

**214 of 263 variants were dropped because the paper shows no longevity effect for them
individually.** Their contribution to the paper is real and is statistical: they are part of the set
whose enrichment is the result. They are not evidence about a person's genome and they get no row.

The one concordant variant was dropped because a same-sign effect contradicts the model this module
is built on; reporting it under the same heading would misrepresent it.

### Two tiers, and why 42 of 48 rows are weak

| tier | rule | n | `stat_significance` |
|---|---|---|---|
| A | longevity P < 0.05/263 = 1.9 × 10⁻⁴ (survives correction for all variants looked up) | 6 | `significant` |
| B | longevity P < 0.05 only | 42 | `suggestive` |

At P < 0.05 across 263 look-ups, about 13 hits are expected by chance and 49 were seen — so most
of tier B is probably real signal, but **any individual tier-B row may be noise**. Every tier-B
conclusion says so in its own text, because a reader sees one row and not this table. Tier A is
rs6859, rs4803763, rs11754167, rs10004996, rs2927439 and rs28601761.

### A second axis: QSNP heterogeneity (`category`)

The paper tests, per SNP, whether its effect on the five diseases is explained by the common factor
or runs through disease-specific pathways, and *"conservatively excluded all SNPs with nominal QSNP
significance"* from its own downstream analyses.

- `shared_aging_factor` — QSNP P ≥ 0.05. **10 variants.** These are the ones whose disease effects
  really do look like one shared mechanism, which is the claim the module is named after.
- `disease_specific_pathway` — QSNP P < 0.05. **38 variants.**

**The 38 are kept, deliberately, and this is the one curation call most open to argument.** The
paper's filter is about the *mvARD* side. The longevity statistic in Supplementary Table S9 is a
separate measurement and is unaffected by it — and applying the filter would delete rs6859 (the
APOE-region variant, the strongest longevity signal in the entire table at P = 2 × 10⁻⁸), LPA, and
the 9p21 locus, i.e. exactly the loci with the deepest independent longevity literature. Dropping
APOE from a longevity module to satisfy a filter about multi-disease heterogeneity would be
obeying the letter of the source against its sense. The category column records the split so a
consumer can take the strict 10 if they want them.

## Which paper each row cites

Each variant gets two rows in `studies.csv`, and they cite different papers on purpose:

| row | `pmid` | `phenotype_class` | what it records |
|---|---|---|---|
| mvARD effect | 41405793 (Dinh 2025) | `MULTIVARIATE_AGEING` | beta on the latent five-disease factor. Dinh et al. measured this; it is their result. |
| longevity effect | 31413261 (Deelen 2019) | `EXTREME_SURVIVAL_CC` | log-odds of 90th-percentile survival. Deelen et al. *measured* this; Dinh et al. *read it out* for these 263 variants and published it in Supplementary Table S9, which is the copy this module used. |

The chain is spelled out in each longevity row's `population` field and in `licensing.csv`, so
nothing implies that Deelen's paper reports these variants — it does not. Deelen's discovery set is
11,262 cases and 25,483 controls, European ancestry; that is 36,745, the N Dinh quotes, which is
how the identity of the dataset was confirmed rather than assumed.

A single row citing Dinh for both measurements was the first attempt and was wrong twice over: it
misattributed the measurement, and `studies.csv` is keyed on (variant, pmid), so the two rows
collided. `just-dna-compiler validate` and `compile` both accepted the collision silently; only
`hint` reported it.

## What the numbers mean

- `effect_allele` is the paper's effect allele, which for all 48 variants is also the **GRCh38
  reference allele** (verified, not assumed — see below).
- `effect_size` / `effect_measure` on `variants.csv` is the longevity log-odds for that genotype
  (allele log-odds × copies). `studies.csv` carries both sides: one row per variant for the mvARD
  effect (`MULTIVARIATE_AGEING`, beta in factor SDs) and one for the longevity effect
  (`EXTREME_SURVIVAL_CC`, log-odds of survival past the 90th percentile).
- `weight` is the longevity log-odds × allele dosage, so positive = protective = better odds of
  extreme survival. The scale is declared in `module_spec.yaml`. Range −0.31 to +0.31.

### Do not sum these weights

Three reasons, all in `weighting.note` as well:

1. **12 of 48 variants share a genomic locus with another variant here** (FUMA loci 9, 97, 138, 139
   and 174; flagged `shared_locus_<n>`). Locus 174 alone contributes four rows — rs2927439,
   rs62117206, rs4803763 and rs6859 — all inside the APOE linkage block on chromosome 19. A sum
   counts that one signal four times.
2. 42 of 48 rows are nominally significant only.
3. These are selected on the longevity statistic, so the set is enriched for upward fluctuations in
   exactly the number being summed. A score built from them is biased by construction.

This module is a per-variant findings table. It is not a polygenic score and must not be used as one.

## Where each value came from

| value | source |
|---|---|
| rsID, effect/other allele, both betas, both SEs, p-values, MAF, QSNP | the paper's Supplementary Tables S5 and S9 |
| nearest / containing gene | **re-derived**, not taken from the paper — Ensembl `overlap/region` around each GRCh38 position |
| GRCh38 coordinate, ref, alts | Ensembl REST `/variation`, cross-checked against dbSNP SPDI |
| European allele frequency in the conclusions | Ensembl, 1000 Genomes phase 3 EUR |
| GA4GH VRS allele ids (all 91) | minted offline from the installed `just_dna_format.vrs` |

### Checks that were actually run

- **Build.** The paper reports GRCh37. For all 48 variants, dbSNP's `chrpos_prev_assm` matches the
  paper's position **exactly**, which is what confirms the build rather than assuming it.
- **Coordinates.** Ensembl's GRCh38 position agrees with dbSNP's for all 48. All 48 are SNVs on the
  forward strand with a single primary-assembly mapping; none has been merged into another rsID.
- **Alleles.** The paper's effect and other alleles are both present in the allele set at every
  position in both sources. Ensembl and dbSNP list slightly different *full* allele sets at
  rs2107595 and rs1169288 (dbSNP records extra rare alleles); `alts` follows dbSNP's SPDI, the
  superset. This affects no claim — the effect and other alleles agree.
- **Frequencies.** The 1000 Genomes EUR frequency of the minor allele matches the paper's MAF to
  three decimal places at **all 48** variants. This independently confirms the allele orientation.
- **Direction, against outside knowledge.** At four loci with a well-known literature direction, the
  module's risk allele is the one the literature names: rs964184-G (APOA5/ZPR1, triglycerides),
  rs11556924-C (ZC3HC1, coronary disease), rs1111875-C (HHEX, type 2 diabetes), rs10455872-G
  (LPA, lipoprotein(a)).
- **Quotes.** Both `provenance_quote` strings were checked to appear verbatim in the Europe PMC
  full text of the paper each row cites — Dinh (PMC13601487) for the mvARD rows, Deelen
  (PMC6694136) for the longevity rows.

### Checks that could **not** be run, and are therefore unknown

This module was built with the offline compiler only — no enricher, no registry client, no MCP
tooling. The following were not performed and nothing in the module pretends otherwise:

- `enrich` (the real resolution pass), `check-identifiers`, `gwas` (GWAS Catalog effect sizes),
  `frequencies` (gnomAD), `gene-metrics`, `literature` (PubMed verification of the PMID/DOI),
  `ld-pairs` (r² between the correlated loci above — which is exactly the number a reviewer would
  want for the APOE block), `alphagenome`, `check-acmg`.
- `resolution.csv` is **authored by hand** from live Ensembl and dbSNP queries rather than produced
  by `just-dna-enricher enrich`. Its `source` says `ensembl-rest` and its `authority` says `ensembl`,
  which is where the values came from; `placement_witness` is left empty because dbSNP — the second
  witness actually used — is not in that column's vocabulary. The cross-check is recorded here and
  in `licensing.csv` instead of being asserted in a field that would mean something else.
- `license_sha256` is empty for all three sources. The licence texts were read, not hashed.
- `dbsnp` appears in `licensing.csv` with no table referencing it, which raises a compiler warning.
  That is intentional: dbSNP really was used, as the second coordinate witness, and deleting the row
  to silence the warning would delete a true provenance fact.

## Known limits

- **One longevity cohort.** Every longevity number traces to a single meta-analysis, read out by a
  single later paper. Nothing here is independently replicated. A second longevity GWAS
  (parental lifespan, healthspan, a 99th-percentile set) would be the most valuable addition.
- **European ancestry only.** The input GWAS, the longevity cohort and the frequencies are all
  European. Effect sizes and frequencies should not be assumed to transfer.
- **Extreme survival is not lifespan.** The outcome is being in the longest-lived ~10% of one's
  birth cohort, in a case-control design — not years of life, not healthspan.
- **mvARD is cardiometabolic.** The five diseases that define the factor are weighted toward heart
  and metabolic disease; the paper says so itself. "Age-related" here is narrower than it sounds.
- **Gene labels are neighbourhood, not mechanism.** Over 90% of these variants are non-coding. The
  `gene` column names the gene the variant sits in, or the nearest protein-coding gene; it does not
  claim that gene is the one the variant acts through. Where the module could not name a credible
  gene (rs11754167, rs35443) the column is **empty rather than guessed**. Only two variants change a
  protein: rs11556924 (ZC3HC1) and rs1169288 (HNF1A).
- **The chromosome 19 rows are APOE.** rs6859, rs4803763, rs2927439 and rs62117206 all sit in the
  APOE linkage block. Their conclusions say this; treat them as one signal.
- **`trait_efo_id` is `OBA_VT0005372`** ("life span determination trait"). The obvious choice,
  `EFO_0004300` (longevity), is **obsolete** — EFO redirects it to this OBA term. There is no
  ontology term for mvARD, so the mvARD study rows carry no trait id rather than a wrong one.

## What is in the paper but not in this module

Deliberately out of scope, because none of it is a per-genotype claim:

- The four high-confidence genes from TWAS + colocalisation + Mendelian randomisation — **DCAF16,
  PHF13, MGA and GTF2B** — and the 22 genes with colocalisation PP4 > 0.8. These are gene-level
  findings with no genotype attached. None of the 48 variants here is the lead SNP for any of them.
- The Mendelian randomisation of lifestyle factors (BMI, coffee, tea, years of education, smoking
  initiation, insomnia, red meat). Those are claims about exposures, not about anyone's DNA.
- The GARFIELD regulatory enrichment and the genetic correlations with healthspan, parental lifespan
  and frailty index — module-level context, not row-level evidence.

## Authorship and review status

Written end to end by `claude-opus-5` (recorded in `module_spec.yaml` `authorship`, `kind: [ai, agent]`,
and in the `curator` column of every row). **No human has reviewed it.** The curation calls worth a
reviewer's attention first, in order:

1. Keeping the 38 `disease_specific_pathway` variants (see above).
2. The nominal-P tier-B cut at all — a stricter module would be the 6 tier-A rows.
3. The dosage weighting, which makes the homozygous-**alternate** genotype the zero point at every
   variant, since the effect allele is the reference allele throughout.

## Build state

Compiled with `just-dna-compiler 0.8.9` / format 0.8.9, `--strict`, fully resolved over all 144
variant rows. Closed (`verification.json`), and `verify --no-require-marketplace` passes.

**Not signed.** `close` recorded the authored bytes as change-evident but unattributed. Signing
needs an Ed25519 key its holder actually controls over time; minting a throwaway one that nobody
has pinned would look like attestation while guaranteeing nothing. A publisher should sign this
with their own key.

Outstanding compiler warning, by choice: `sources.csv declares 1 source(s) no table in this module
uses: ['dbsnp']` — see *Checks that could not be run* above.

## Licence

Module content: CC BY 4.0, following the source article. Attribution and per-source terms are in
`licensing.csv`.
