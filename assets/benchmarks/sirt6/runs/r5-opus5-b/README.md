# longevity_sirt6 — SIRT6 rs117385980, frailty and longevity

One variant, three genotypes, two cohorts, and no significant result anywhere. This module exists to
say that carefully, because the alternative — silence — reads as "nothing is known", and something
*is* known: this variant has been looked at twice, in opposite corners of the world, and both times
the answer came back short of significance in the same direction.

Built from **Sheikholmolouki et al., *Sci Rep* 15:40251 (2025)**, doi
[10.1038/s41598-025-24018-3](https://doi.org/10.1038/s41598-025-24018-3), PMID 41249831, plus the
earlier study it rests on, **Hirvonen et al., *BMC Med Genet* 18:41 (2017)**, PMID 28399814.

## What the module claims

| Genotype | Direction | Significance | In one sentence |
|---|---|---|---|
| `C/C` | protective | **not significant** | The usual result (~95–96% of people); slightly over-represented among the oldest in both cohorts, neither significantly |
| `C/T` | risk | **not significant** | ~4% of people (3.6–4.5%); under-represented among the oldest in both cohorts, neither significantly |
| `T/T` | *no direction* | **unknown** | Never observed in either cohort. No evidence either way |

`state=alt` and `direction=unknown` on the `T/T` row are deliberate. That row is a genotype
descriptor carrying no claim, which is not the same as a claim of no effect.

**This module ships no weights.** Every published estimate for this variant has a confidence
interval spanning an order of magnitude on both sides of 1 — the widest is OR 1.42, 95% CI
0.18–11.67. A weight would assert a magnitude the evidence cannot support, and a weight of `0.0`
would assert a measured null, which is also not what happened. `weighting:` in `module_spec.yaml`
says this, so a consumer combining modules cannot mistake absence for zero.

## The correction this module makes

**The source paper describes rs117385980 as a stop-gained variant in exon 2 of SIRT6. That appears
to be wrong, and the module does not repeat it.**

> "The single nucleotide polymorphism (SNP) rs117385980 (C > T) is a stop gained variant within the
> exon 2 of SIRT6 gene" — Sheikholmolouki et al. 2025, Introduction

Four independent authorities place it in an intron instead:

| Authority | Says |
|---|---|
| Ensembl VEP, release 116 | `intron_variant` on **all 13** SIRT6 transcripts, including MANE Select `ENST00000337491`. Most severe consequence across the whole variant: `intron_variant` |
| gnomAD v4 | `c.194+194G>A`, `intron_variant`, no LoF flag — 194 bases into the intron |
| ClinGen Allele Registry | CAID `CA15948970`, canonical title `NM_016539.4(SIRT6):c.194+194G>A` — the MANE Select RefSeq transcript |
| **Hirvonen et al. 2017** — the paper the 2025 study cites for this variant | calls it `intron variant` in **both** of its results tables, and locates it "situated 23 bases downstream of the exon/intron border of exon 2" |

The fifth and strongest argument is a frequency: **gnomAD v4 records 183 individuals homozygous for
the T allele** (148 of 211,259 with exome calls; 35 of 76,133 with genome calls). A true homozygous
null for SIRT6 is not compatible with that. Homozygous inactivating *SIRT6* mutation causes human
perinatal lethality (Ferrer et al., PMID 29555651), and *Sirt6*-knockout mice die at about four
weeks (PMID 16439206). 183 living homozygous adults is not what loss of SIRT6 looks like.

Where the `stop_gained` label comes from: dbSNP reports a `stop_gained` consequence
(`p.Trp38Ter`) on `XM_024451539.2`, a *predicted* RefSeq model transcript with an alternative first
exon. It is a real annotation on a real transcript record, but it is not the MANE Select transcript
and it is not how any of the four authorities above read the variant. The 2025 paper's mechanistic
framing — a truncated SIRT6 protein — rests on that single predicted transcript.

**This does not invalidate the paper's genotyping or its statistics.** The PCR-RFLP assay cuts at
the right place and Sanger sequencing confirmed three samples. What changes is the mechanism: if the
variant is intronic, the plausible route to an effect is splicing (Hirvonen's own suggestion, given
proximity to the exon 2 boundary) or linkage to something else — not a truncated protein. The
module records the variant as intronic and says so on the `T/T` row and here.

A second, smaller discrepancy, unresolved: Hirvonen places the variant 23 bases from the exon/intron
border; gnomAD and ClinGen both say `c.194+194`, i.e. 194 bases in. The module carries the
coordinate (chr19:4,180,588, GRCh38), which all sources agree on, and takes no position on the
distance.

## What was dropped, and why

The source paper's Discussion cites four other SIRT6 longevity studies. **None of them became a row**,
because none of them genotyped rs117385980:

- **rs107251** (TenNapel et al., PMID 25541994) — a different variant. CC/CT vs TT, >5-year survival difference.
- **rs350846** (You et al., Bama County, China) — a different variant.
- **rs350852, rs350844, rs352493, rs4807546, rs3760905** (Lin et al., Hainan) — five different variants, all null.

They are relevant to *SIRT6 and longevity* as a subject and irrelevant to *this variant*. A module
keyed on rs117385980 that cited them would be borrowing credibility from studies that never looked
at it. If someone wants a SIRT6-wide longevity module, those are its starting rows, and this one is
not that module.

Worth noting for anyone who extends this: the T allele is **essentially absent in East Asians**
(gnomAD v4 exome AF 4.1 × 10⁻⁵; 1 of 24,636 alleles). The two Chinese studies above could not have
tested rs117385980 even if they had wanted to. The `frequencies.csv` table carries this.

## Why the frailty result is not in the headline

Frailty was the 2025 paper's *primary* hypothesis, and it is null:

> "This exploratory study did not find a statistically significant association between the SIRT6
> rs117385980 variant and frailty syndrome" — Conclusions

Unadjusted allelic OR 1.4, p = 0.36; fully adjusted OR 0.96, 95% CI 0.10–9.66, p = 0.98. The frail
group contributed 78 alleles and contained zero T alleles; at a MAF of ~2% you would expect about
1.6. Observing zero is unremarkable. The module therefore does **not** carry a "T allele protects
against frailty" claim, even though the raw direction (2.13% of non-frail alleles vs 0% of frail)
points that way — that direction is recorded in the `negatives` column of the `C/T` row as the
antagonistic-pleiotropy reading the authors themselves raise, flagged `ap:weak`.

The module's headline is longevity instead, because that is the one place two independent cohorts
agree in sign: Finnish men of mean age 83 (OR 3.58, 95% CI 0.96–13.4, p = 0.074) and Iranian adults
across three age bands (0% carriers at 80–90 vs 1.39% and 4.65% below, p = 0.073). Two p-values of
0.07 in the same direction, in populations with no shared ancestry, is the most this literature
supports. It is a trend worth recording and not a finding worth acting on.

## Honest limits

- **Total world evidence: 20 heterozygotes.** 8 in Iran (of 227 people), 12 in Finland (of 198).
- **No survival data.** Neither study followed participants to death. The Iranian study says
  date-of-death data for BLAS is unavailable; both infer longevity from cross-sectional age. An
  allele frequency that falls with age band is consistent with viability selection *and* with birth
  cohort effects, migration, or chance. `phenotype_class=VIABILITY_AF` on that row names the design
  rather than dressing it up as a survival analysis.
- **Neither cohort saw a `T/T` homozygote**, so the module's `T/T` row is evidence-free by
  construction.
- **One sex, in half the evidence.** Hirvonen is male-only; `stratum=sex`, `stratum_level=male`
  records it.
- **Underpowered by the original authors' own arithmetic.** Hirvonen state that 427 cases and 371
  controls would be needed for 80% power; they had 106 and 92.
- **Ancestry coding is incomplete.** The `ancestry` column is a 1000 Genomes superpopulation
  vocabulary (AFR/AMR/EAS/EUR/SAS) with no code for a Middle Eastern population, so the Iranian
  cohort's row leaves `ancestry` **empty** rather than forcing a wrong code. Its free-text
  `population` cell carries the real description. Empty here means "not codeable", not "unknown".
- **One row per paper.** `studies.csv` is keyed on (variant, PMID), so the 2025 paper's two distinct
  analyses — the age-band allelic trend and the adjusted frailty regression — share a single row.
  The structured `p_value_num`/`phenotype_class` fields carry the longevity analysis; the frailty
  numbers are in that row's prose. Nothing was discarded, but a machine reading only the numeric
  columns will see one of the two.
- **No verification records.** `verification.json` contains a closure and nothing else. Every
  cross-check in this toolchain (coordinate resolution, reference-allele verification, trait and
  gene identifier currency, ClinVar concordance, frequency provenance) lives in `just-dna-enricher`,
  which is not installed in the environment this module was built in. So the module asserts that
  authoring finished, and asserts nothing about having been machine-checked. The
  `placement_witness`, `placement_verdict`, `left_aligned` and `authored_event` columns of
  `resolution.csv` are deliberately empty for the same reason: no check ran, so no verdict is
  recorded. **`resolution.csv` and `frequencies.csv` were written by hand** from Ensembl REST
  (release 116) and the gnomAD v4 GraphQL API respectively, rather than by the passes that normally
  own them.
- **Four columns of the compiled artifact are empty when they should not be.** `weights.parquet`
  carries `outcome_lifespan`, `outcome_healthspan`, `outcome_exceptional` and `eur_only_evidence`,
  which the format declares (RM326, RM328) as derived from `studies.csv`'s `phenotype_class` and
  `ancestry`. This module has an `EXTREME_SURVIVAL_CC` study row, which `vocab.OUTCOME_STRIP_CELLS`
  maps to the `exceptional` cell, so `outcome_exceptional` should read `true`. It reads `null`. In
  compiler 0.8.9 nothing reads that mapping — the constant is defined once and never used — so all
  four columns are emitted unpopulated for every module. A consumer filtering on
  `outcome_exceptional` will treat this locus as never having been tested for exceptional survival.
  Read `studies.parquet:phenotype_class` directly instead. This is a toolchain gap, not a statement
  about the evidence.
- **Not in ClinVar.** A ClinVar query for rs117385980 returns zero records, so `clinvar=false` on
  every row and `clin_sig` is empty. SIRT6 is not on the ACMG secondary-findings list.

## Model organism rows

`model_organisms.csv` carries four rows, and they are about **SIRT6 the gene, not this variant**:
overexpression extends mouse lifespan (+15% male, PMID 22367546; +27% male / +15% female with
improved frailty measures, PMID 34050173), knockout is lethal at ~4 weeks (PMID 16439206), and
human homozygous inactivating D63H is perinatally lethal (PMID 29555651). All four are marked
`concordance=concordant`, meaning they agree in direction with "less SIRT6 function is worse for
ageing". They establish that *SIRT6 dose matters for lifespan in mammals*. They say nothing about
whether rs117385980 changes SIRT6 dose — and the intronic placement above is a reason to doubt that
it does. Do not read these rows as support for the variant claim.

## Licensing

The 2025 paper is **CC BY-NC-ND 4.0**, and the ND term is real: *"You do not have permission under
this licence to share adapted material derived from this article or parts of it."* The module
declares `CC-BY-NC-ND-4.0` as the most restrictive term in its mix (Hirvonen 2017 is CC BY 4.0;
Ensembl is unrestricted; gnomAD is CC0), which is why `validate` warns about a licence mismatch —
that warning is the expected mixed-licence case, not a defect.

What the module actually reproduces from the NC-ND paper: allele counts, odds ratios and p-values,
which are facts and not protected expression, plus **two short verbatim sentences** in
`provenance_quote` cells whose only job is to let a reader find the claim in the article. Anyone
redistributing this commercially, or uncomfortable with relying on short quotation, should strip the
`provenance_quote` column — it carries no claim and the rows stand without it. Coordinates come from
Ensembl 116; frequencies from gnomAD v4; the rsID identity and the `XM_024451539.2` predicted-
transcript annotation discussed above come from dbSNP, which is a US Government work in the public
domain and is credited here rather than in `licensing.csv` (no table in this module carries
`source=dbsnp`, and declaring an unused source raises a warning).

## Authorship

Drafted by `claude-opus-5` (an AI agent) on 2026-11-26: evidence located, both full texts read,
quotes verified verbatim against the fetched XML, rows and prose written. `authorship:` in
`module_spec.yaml` records this as `kind: [ai, agent]`, `role: created`.

**Not reviewed by a human, and not reviewed by a geneticist.** The central correction in this
README — that the source paper misdescribes its own variant's consequence — is the kind of claim
that deserves a second pair of eyes before anyone relies on it. The evidence for it is laid out
above so it can be checked rather than taken on trust.

## Reproducing the lookups

```
Ensembl VEP      https://rest.ensembl.org/vep/human/id/rs117385980
Ensembl variant  https://rest.ensembl.org/variation/human/rs117385980
ClinGen AR       https://reg.clinicalgenome.org/allele?hgvs=NC_000019.10:g.4180588C>T
gnomAD           POST https://gnomad.broadinstitute.org/api  (variant 19-4180588-C-T, gnomad_r4)
Europe PMC       https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12624115/fullTextXML
                 https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5387321/fullTextXML
```

The GA4GH VRS allele id on the resolution row,
`ga4gh:VA.YxCS1acZj0ufkzEEd26R-KF--4hLspHR`, was minted offline with
`just_dna_format.vrs.derive_vrs_allele_id('19', 4180588, 'C', 'T', build='GRCh38')` (VRS spec 2.0).
