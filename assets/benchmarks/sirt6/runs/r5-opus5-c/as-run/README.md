# SIRT6 variants and human longevity

Human germline variants in *SIRT6* that have been reported in relation to
lifespan, longevity and frailty. The module is built around
[Sheikholmolouki et al., *Scientific Reports* 15:40251 (2025)](https://doi.org/10.1038/s41598-025-24018-3),
PMID 41249831, and extends to the primary studies that paper cites, each read
at source rather than through the paper's summary.

**Three variants carry genotype annotations; ten more appear as study-level
rows only. Nothing in this module is a score and nothing in it is significant
at conventional thresholds except one estimate resting on ten people.** Read
the two correction sections below before using any of it.

## What is in this module

### Genotype-annotated variants (9 genotype rows, 3 variants)

| Variant | MANE HGVS (NM_016539.4) | Trait | Direction | Evidence |
|---|---|---|---|---|
| **rs117385980** | `c.194+194G>A` (intronic) | longevity / lifespan | T allele suggestively adverse | Hirvonen 2017 (PMID 28399814), OR 3.58, 95% CI 0.96–13.4, p=0.074, n=198 Finnish men; Sheikholmolouki 2025, T absent above age 80, p=0.073, n=227 Iranian |
| **rs107251** | `c.438-151A>G` (intronic) | age at death | T/T adverse, −5.5 y | TenNapel 2014 (PMID 25541994), q=0.012, n=1,192 Iowa 65+, **10 T/T individuals** |
| **rs350846** | `c.*216G>C` (3′UTR) | longevity (survival to 90+) | **none asserted** | You/Li 2016 (PMID 28032059), n=503 Bama County, China — direction contradictory, see below |

### Study-level rows only (21 rows, 13 variants, 10 of them not annotated)

Hirvonen 2017 sequenced the *SIRT6* exons and their boundaries in 135 Finnish
men and tabulated eight variants; seven were null and are recorded here with
their published odds ratios. Lin 2016 (PMID 26802595) tested five variants in
1,462 people from Hainan Island, China and found nothing; that paper is closed
access and its five rows carry explicitly secondary provenance. These rows
exist so that a consumer can see that the *SIRT6*–longevity literature is
mostly null, and which specific markers have already been looked at.

### Not in this module

- **No score.** `weights.weight` is null in every row. These rows must not be
  summed, and there is no *SIRT6* polygenic score to point at.
- **No VRS identifiers.** `vrs_id` and `vrs_spec` are null throughout. Computing
  a `ga4gh:VA` digest needs the GA4GH VRS serialisation library, which was not
  available to this curator. ClinGen canonical allele identifiers (CAIDs) are
  supplied instead, in `resolution_loci.caid` and `source/resolution.csv`, and
  resolve the same alleles unambiguously.
- **No mouse or cell biology.** *SIRT6* overexpression extends mouse lifespan
  (Roichman 2021) and serum SIRT6 is lower in frail older adults (Zhu 2023,
  PMID 37754211). Neither is a germline genotype and neither is annotated here.
- **No clinical significance.** No allele in this module has a ClinVar record;
  absence was checked against the ClinGen Allele Registry for each one, which
  is why `clin_sig_authority_calls` and `clin_sig_concordance` are present but
  empty rather than omitted.
- **No pharmacogenomics, no interventions.** Annotation only.

## Correction 1: rs117385980 is not a stop-gained variant

The focal article states that rs117385980 is "a stop gained variant within the
exon 2 of SIRT6 gene". **It is not.** Four independent authorities agree:

| Authority | Verdict |
|---|---|
| ClinGen Allele Registry (CA15948970) | `NM_016539.4(SIRT6):c.194+194G>A` — 194 bp inside intron 2 |
| Ensembl VEP | `intron_variant` on **all 28** of the 30 *SIRT6* transcripts that overlap it (the other two place it outside their bounds); MANE Select ENST00000337491 included |
| Ensembl exon coordinates | exon 2 is chr19:4,180,782–4,180,909; the variant is at 4,180,588, i.e. 194 bp away |
| Ensembl repeat annotation | the variant lies inside an **AluSx4** element, chr19:4,180,385–4,180,624 |

The `stop_gained` label is traceable: dbSNP's `fxn_class` field for this rs id
reads `coding_sequence_variant,stop_gained,intron_variant`, pooled across every
transcript it knows. The only transcript supporting `stop_gained` is
**XM_024451539.2**, a Gnomon-*predicted* RefSeq model whose exon 2 extends past
4,180,588; on that model the change is `c.114G>A`, `p.Trp38Ter`. The nonsense
prediction is arithmetically correct for that model (SIRT6 is on the minus
strand, the reference codon reads TGG and the T allele makes it TGA — verified
against the GRCh38 sequence), but no curated `NM_` transcript contains that
exon.

The original report of this variant got it right. Hirvonen 2017 described it as
"situated 23 bases downstream of the exon/intron border of exon 2" and typed it
as `intron variant` in both its tables. The "23 bases" also checks out against
a real annotation: Ensembl transcript ENST00000594341 carries an extended
exon 2 ending at chr19:4,180,612, which puts the variant 23 intronic bases away.

**Consequence for a consumer:** rs117385980 must be treated as a non-coding
marker of a haplotype, not as a *SIRT6* loss-of-function allele. The four
checks above settle this on their own. As corroboration only: a 1.8 %
population frequency would be a surprising thing to find for a true nonsense
allele in a gene where a homozygous inactivating missense mutation causes human
perinatal lethality (Ferrer 2018, PMID 29555651) and knockout mice die within
four weeks. As an intronic Alu variant the frequency is unremarkable.

## Correction 2: the rs350846 direction in the literature is inverted

The focal article reports that "the C allele at rs350846 of the SIRT6 gene was
associated with longevity", following the conclusion of You/Li 2016. That
paper's own Table 4 says the opposite:

| Group | n | C allele | vs longevity |
|---|---|---|---|
| Longevity (90–110 y) | 169 | 28.7 % | — |
| Internal control (26–82 y, same region) | 158 | 27.8 % | p=0.796, OR 1.046 |
| External control (20–82 y, no longevity family history) | 176 | **38.6 %** | p=0.006, **OR 0.639** |

The C allele is *lower* in the long-lived than in the external controls, and
indistinguishable from the better-matched internal controls. The two control
groups differ from each other at p=0.003 — more than the long-lived differ from
either. This is a control-selection artefact, not a longevity signal. This
module therefore authors `direction = unknown` and `state = neutral` for all
three rs350846 genotypes and says why in each `conclusion`.

## Three markers, probably one signal

In 1000 Genomes phase 3 EUR, rs117385980, rs107251 and rs350846 all sit on a
single haplotype: **D′ = 1.00 pairwise**, with r² held to 0.30 only by the
frequency difference (0.018 against 0.116). The rare rs117385980 T allele exists
only on the haplotype background that carries the minor alleles of the other
two. Three published associations in three cohorts may therefore be one signal
seen through three markers — and once that is noticed, the directions line up:
rs117385980-T adverse (Hirvonen), rs107251-T/T adverse (TenNapel), and
rs350846-C lower in the long-lived (You/Li's table, not its conclusion).

Two further LD facts, both from the Ensembl LD endpoint:

- **rs117833511** (chr19:4,180,315, intronic) is a perfect proxy for
  rs117385980 in EUR (r²=1.00). It is recorded as `proxy_rsid` on the Hirvonen
  study rows for consumers whose array carries one but not the other.
- **rs192661013**, `c.1024C>G` / **p.His342Asp**, is the only coding *SIRT6*
  variant in appreciable LD with rs117385980 (r²=0.57, D′=1.00). Hirvonen
  speculated that rs117385980 "is a mere genetic marker for some currently
  unknown sequence variant, which affects the function of the protein"; this is
  a concrete candidate for that variant, and Hirvonen tested it (OR 2.37,
  95% CI 0.27–20.6, p=0.67, underpowered at MAF 0.008). It is **absent from
  gnomAD Middle Eastern samples**, so the LD cannot be assumed in the Iranian
  cohort.
- rs7260071, a common variant (AF 0.27) only 105 bp from rs117385980 in the
  same intron, is **not** in LD with it (r²<0.2) and was null in Hirvonen.
  That argues against a shared functional element at this position.

## Population

| Ancestry group (gnomAD v4.1 genomes) | rs117385980 T |
|---|---|
| Non-Finnish European | 0.0269 |
| Finnish | 0.0267 |
| Ashkenazi Jewish | 0.0349 |
| Admixed American | 0.0151 |
| **Middle Eastern** | **0.0137** |
| South Asian | 0.0068 |
| African/African-American | 0.0047 |
| **East Asian** | **0.0000** |
| Global | 0.0181 |

The Birjand cohort's observed allele frequency of 0.0176 (8 heterozygotes in
227 people) is unremarkable against the Middle Eastern reference, and the
genotype counts are in Hardy–Weinberg equilibrium (7.85 heterozygotes expected,
8 observed). Hirvonen cited a Finnish frequency of 0.056 from 1000 Genomes;
that came from 98 Finnish samples, and gnomAD's much larger Finnish sample puts
it at 0.027.

Two consequences worth stating plainly:

- **No T/T homozygote has ever been reported.** At this frequency about 1 person
  in 3,000 is T/T; across all three cohorts here (227 + 135 + 63 = 425 people)
  the expectation is 0.14. The `T/T` row carries `direction = unknown` because
  there is no evidence for it, not because the evidence is mixed.
- **rs117385980 is absent in East Asians.** The rs350846 result from Bama
  County cannot be the same haplotype signal as the Finnish and Iranian
  rs117385980 results, because the Chinese cohort is effectively monomorphic at
  rs117385980.

All longevity direction for rs117385980 and rs107251 comes from
European-ancestry cohorts (Finnish, Iowa). `eur_only_evidence` is set for
rs107251. For rs117385980 it is false because the Iranian cohort contributes,
but that cohort contributes only the age-band trend, not an effect size.

## Methodology

### What the focal article actually found

Nothing significant. It is labelled exploratory by its own authors and the
honest summary is:

- **Frailty: null.** T allele 8/376 alleles in non-frail, 0/78 in frail
  (p=0.36). Fully adjusted logistic model OR 0.96, 95% CI 0.10–9.66, p=0.98.
- **Age: suggestive.** T allele 1.39 % at 60–69 y, 4.65 % at 70–79 y, 0 % at
  80–90 y (p=0.073). Non-monotonic, peaking in the middle band.
- **Sex, diabetes, hypertension: null** (Fisher p=1.00, 0.72, 1.00).

The two findings point in opposite phenotypic directions: zero T carriers among
the frail reads as T being favourable, zero T carriers above 80 reads as T being
adverse. The module records both and resolves neither, because 8 carriers cannot
resolve it.

### Reported statistics this module declines to use

- **Table 3's OR of 1.4 and the 70–79-vs-80–90 OR of 3.9** are not estimable
  from the published counts. Both comparisons have a zero cell, which gives
  complete separation; an unpenalised logistic or unconditional odds ratio is
  infinite, and the paper does not state which group is the outcome or what
  correction, if any, was applied. Both are recorded in `studies.parquet` with
  that caveat in the `conclusion` and are not propagated to any genotype row.
- **Sex-difference p-value.** The Discussion gives p=0.87; Table 5 gives
  Fisher p=1.00 and χ² p=0.84/0.85 for the same comparison. Not used.
- **Counts attributed to Hirvonen.** The focal article says "1/42 long-lived men
  (aged 77+)"; Hirvonen reports **1/43**, and the "77+" appears to be a misread
  of Hirvonen's remark that male life expectancy in Finland is 77.5 years. The
  Hirvonen replication group had a mean age of 83. This module uses Hirvonen's
  own numbers throughout.

### The genotyping assay was verified in silico

The focal article's PCR-RFLP design was checked against the GRCh38 reference,
and it is sound:

- The published primers (`5'-CTCAGGCAAGACAGGGACAG-3'` forward, reused from
  Hirvonen 2017; `5'-ATGAGGTGAGTGGAATGCTGG-3'` reverse, new to this study) map
  uniquely in the locus and define an amplicon of chr19:4,180,347–4,181,007 —
  **exactly 661 bp**, the published size.
- Simulating BsuRI/HaeIII (`GG^CC`) digestion of that amplicon reproduces the
  published fragment sizes **exactly**: C allele → 241, 216, 161, 43 bp;
  T allele → 402, 216, 43 bp. The C>T change destroys the `GGCC` site at
  4,180,586–4,180,589.
- Exhaustively simulating every possible single substitution at all 661
  positions finds 51 that would change the fragment pattern. The only common
  variant sitting at any of them is rs117385980 itself. Both other common
  variants inside the amplicon — rs7260071 (AF 0.27) and rs352493 (AF 0.08) —
  leave the digest unchanged, so neither can produce a false genotype call.
  The 51 sensitive positions otherwise host only singleton-level dbSNP entries.
- Both primers fall in unique flanking sequence outside the AluSx4 element,
  though 240 bp of the amplicon — including the variant itself — lies within it.

The assay measures what it claims to measure. The disagreement with the paper
is about what the position *is*, not about whether it was genotyped correctly.

### Variant selection

Every variant here is one a cited human study actually tested. No candidate
variant was added from general *SIRT6* knowledge, no GWAS catalogue was mined,
and no proxy was substituted for an authored variant. Genotype annotations were
authored only where a primary study gave a per-genotype or per-allele direction
that this curator could read at source and reproduce from the published counts.
That excluded Lin 2016 (closed access, secondary provenance) and rs350846
(direction contradictory).

### Licensing of the authored text

The focal article is **CC BY-NC-ND 4.0**, and You/Li 2016 is CC BY-NC 3.0. No
passage from either is reproduced anywhere in this module: only
non-copyrightable facts were transcribed — rs ids, alleles, counts,
frequencies, p-values, odds ratios, confidence intervals, primer sequences and
fragment sizes. The NonCommercial and NoDerivatives terms therefore do not
attach to this module's own contents, and the module can be redistributed
freely. The three `provenance_quote` values in `studies.parquet` come only from
CC BY sources (Hirvonen 2017, TenNapel 2014), and the build fails if a quote is
ever authored from a source whose licence does not permit verbatim reuse.
`sources.parquet` records the reasoning per source.

## Curation

AI-authored (Claude Code, Opus 5), November 2026. Verification log in
`../NOTES.md`; the authoring layer is `../source/*.csv` and the compiler is
`../build/compile.py`, which asserts schema conformance against the published
reference modules and fails on drift. `../build/validate.py` re-checks genotype
completeness, cross-table agreement, p-value arithmetic, trait-id provenance,
the licence gate on quotations, verbatim recovery of every quote from the
retrieved full text, and reproduction of the focal paper's own allele-frequency
and Hardy–Weinberg arithmetic.

Externally verified: all nine PMIDs and eight DOIs against PubMed and Europe
PMC; every GRCh38 placement and reference allele against Ensembl; every
canonical HGVS and CAID against the ClinGen Allele Registry; every allele
frequency against gnomAD v4.1; all three trait ontology terms against EBI OLS
(note `EFO:0004300` "longevity" was obsoleted in EFO 3.74.0 — this module uses
its replacement, `OBA:VT0005372`).

Errors caught and corrected during curation, beyond the two corrections above:
Hirvonen's Table 1 types rs11554579 as *missense*; it is `c.228A>G`,
`p.Arg76=`, **synonymous**. Hirvonen types rs7260071 as a non-coding transcript
exon variant; it is intronic on all current transcripts. Two of Lin 2016's five
"*SIRT6*" SNPs are not in *SIRT6*: rs3760905 is in **ANKRD24** and rs350852 is
in **CREB3L3**, both outside the Ensembl *SIRT6* footprint
(chr19:4,174,104–4,182,604). Hirvonen's own abstract gives OR 3.53 where its
Results and Table 2 give 3.58; the tabulated value is used.

**Research and informational use only.** Nothing here is a clinical test, a
diagnosis, or a prediction of an individual's lifespan. The strongest single
estimate in the module rests on ten people, and the focal study found nothing.
