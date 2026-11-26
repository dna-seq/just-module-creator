# SIRT6 rs117385980 and longevity

One variant, one paper. This module reads **rs117385980** (C>T, an intronic variant in *SIRT6* on
chromosome 19) and reports what a single exploratory study says about it and reaching old age.

## What this module is not

- **Not an established association.** The study behind every row found **no statistically
  significant** result. The longevity signal is a trend (p = 0.073) driven by **8 carriers** out of
  227 people, and the authors call their own work "exploratory".
- **Not a frailty predictor.** The paper's main question was frailty, and the T allele showed no
  association with it (final adjusted OR 0.96, 95% CI 0.10–9.66, p = 0.98). If anything, the raw counts put
  the T allele in non-frail people only, the opposite tilt to the longevity trend.
- **Not tested on T/T.** No homozygous T/T person was seen. The T/T row is extrapolated from
  heterozygotes and says so.
- **Not a lifespan study.** Nobody was followed to death. "Longevity" here means the T allele was absent
  in the 80–90 age group of a cross-sectional cohort. That design cannot tell survival effects apart
  from differences between birth cohorts.

## The finding

Sheikholmolouki E, Sharifi F, Nickhah Z, et al. *The association of the SIRT6 rs117385980 variant with
frailty and longevity: an exploratory study.* Sci Rep 15, 40251 (2025).
PMID [41249831](https://pubmed.ncbi.nlm.nih.gov/41249831/), doi:10.1038/s41598-025-24018-3, PMC12624115.

- 227 adults aged 60–90 from the Birjand Longitudinal Aging Study, eastern Iran. Genotyped by PCR-RFLP,
  with Sanger confirmation on 3 samples.
- T allele frequency by age band: 60–69 y 1.39% (4/288 alleles), 70–79 y 4.65% (4/86), 80–90 y 0% (0/80).
  Fisher's exact p = 0.073. Pairwise 70–79 vs 80–90: p = 0.06.
- The authors read this as a possible inverse link between the T allele and reaching advanced age. They
  point to an earlier Finnish men's cohort (Hirvonen et al., BMC Med Genet 2017) that reported the same
  direction. **That Finnish study is not a source for any row here.** It is a candidate for a second
  pass.

## Design decisions

| Genotype | state / direction | weight | Why |
|---|---|---|---|
| C/C | neutral | 0.0 | the reference genotype, carried by everyone aged 80–90 in the study |
| C/T | risk | -0.1 | the observed carrier genotype. Direction follows the authors' reading; small because not significant |
| T/T | risk | -0.2 | never observed. Additive extrapolation, stated in the conclusion |

- `stat_significance` is `not_significant` on every row. `direction` is still `risk` for T carriers,
  because the format records the sign of a non-significant trend and lets significance say how far to
  lean on it.
- **Weights:** curator-set on a [-1, 1] scale, positive = favourable. They are kept deliberately tiny and
  are not derived from any published effect size, because the paper reports none for the age analysis.
  Do not sum them with other modules. The same statement is in `weighting:` in `module_spec.yaml`.
- No effect size is recorded. The paper's only odds ratios belong to the frailty analysis (non-significant,
  and inconsistent with a zero count in the frail group) and to the 70–79 vs 80–90 comparison (OR 3.9 with
  no confidence interval and no stated reference allele). Neither is a usable longevity estimate.
- Only one `studies.csv` row is possible per (variant, paper). The row carries the age-band (longevity)
  analysis. The frailty result appears in that row's `conclusion`.

## Where the coordinates came from

`resolution.csv` was **written by hand** (`source=manual`) because the enricher was not available in this
authoring environment. Values: GRCh38 19:4180588 C>T, taken from Ensembl REST
(`/variation/human/rs117385980`) and cross-checked against NCBI dbSNP esummary
(`NC_000019.10:g.4180588C>T`, gene SIRT6). Both agree. The variant falls inside SIRT6
(ENSG00000077463, minus strand). The paper's "C > T" matches the plus-strand alleles. The VRS id was
minted offline with `just_dna_format.vrs.derive_vrs_allele_id`. Re-run `just-dna-enricher enrich`
before a production publish so an independent source fills this table.

## Evidence and quoting

- The `provenance_quote` in `studies.csv` is one sentence copied verbatim (by script, not retyped) from
  the Europe PMC full text of PMC12624115, located by the agent named in `curator`. Any later
  `quotes_found` check against Europe PMC is therefore a citation-pairing check, not independent evidence.
- The article is **CC BY-NC-ND 4.0**. One short verbatim sentence is quoted. No adapted text is
  reproduced, and every `conclusion` is written in the curator's own words. `licensing.csv` records the
  article as non-commercial, so the module is not suitable for commercial redistribution.
- `literature.csv` was not produced (it needs the enricher's literature pass).

## Origin

Built from a single paper named by the author (DOI 10.1038/s41598-025-24018-3). There was no drafting
source. Written entirely by an AI agent (claude-opus-5-5) on 2026-11-26. No human has reviewed it yet.

## Changelog

- 0.1.0 (2026-11-26) — first draft.
