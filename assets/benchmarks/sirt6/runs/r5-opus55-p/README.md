# Longevity and the SIRT6 gene

One spot in the SIRT6 gene, rs117385980 (GRCh38 19:4180588 C>T), where two small studies saw the less
common T version less often among people who reached old age. Both results are
trends that did not reach statistical significance. This module reports that hint. It is not a lifespan
prediction.

## Where this module came from

Built on request from one paper:

- **Sheikholmolouki E et al. (2025).** *The association of the SIRT6 rs117385980 variant with frailty and
  longevity: an exploratory study.* Scientific Reports 15:40251. PMID 41249831, PMC12624115.
  CC BY-NC-ND 4.0.

A second paper was added because the first one's longevity claim rests on it and it gives the primary
numbers:

- **Hirvonen K et al. (2017).** *SIRT6 polymorphism rs117385980 is associated with longevity and healthy
  aging in Finnish men.* BMC Medical Genetics 18:41. PMID 28399814, PMC5387321. CC BY 4.0.

Origin: a paper-drafted module. No source publishes these rows as a table; every cell was authored from the
two papers' full texts. All authoring was done by an AI agent (`claude-opus-5-5`, see `authorship:`), and
every move is in `logs/authoring.log`. No human has reviewed it.

## What the evidence says

| | Finland (PMID 28399814) | Iran, Birjand (PMID 41249831) |
|---|---|---|
| Who | 198 men: 43 healthy long-lived plus 63 healthy men aged about 83, against 92 who died of natural causes at about 66 | 227 adults aged 60 to 90 from a community cohort, both sexes |
| Design | case-control, direct sequencing | allele frequency by age group, cross-sectional; frailty case-control |
| T carriers | 1/43 long-lived, 2/63 replication, 9/92 died early | 4/144 (60-69), 4/43 (70-79), 0/40 (80-90) |
| Test | Fisher's exact, combined groups: OR 3.58 (95% CI 0.96-13.4), p = 0.074 | Fisher's exact across age groups: p = 0.073 |
| Homozygotes (T/T) | none observed | none observed |

Both point the same way: T was seen more often in people who died earlier, or in younger rather than older
survivors. Neither reaches p < 0.05. The Finnish study states its own power was 28.4%. The Finnish main cohort
on its own gave p = 0.18 (its Table 1). The 0.074 pools it with the replication group, so there is no
independent Finnish replication. The Finnish study included men only.

**Module-level `stat_significance` is `not_significant`.** No test reached p < 0.05. Birjand's p = 0.073
tests across three age groups and does not test a decline, and the comparison that bears on direction
(60-69 against 80-90) gives p = 0.37. The `risk` direction is the sign of both studies' point estimates
for the oldest groups. The schema defines `direction` as a sign "whether or not it is established", so
the hint is carried by the direction plus a small weight, not by the significance grade.

**Limits worth knowing:**

- In Birjand, 8 carriers among 227 people means only about 1.4 carriers were expected among the 40 aged
  80-90, so finding none happens by chance about one time in four.
- The Birjand age pattern is not a steady decline. The T frequency rises from 1.39% (60-69) to 4.65%
  (70-79) and then falls to 0% (80-90); 60-69 against 80-90 gives p = 0.37. The study is cross-sectional
  and has no death dates.
- The Birjand study's main question was frailty (Fried phenotype), and it found **no association**
  (final adjusted OR 0.96, 95% CI 0.10-9.66, p = 0.98). Carriers were, if anything, slightly more common
  among non-frail people. This is recorded in the C/T row's `negatives` and in the study row's
  conclusion. `studies.csv` keys one row per variant and paper, so the frailty result has no row of its own.
- The odds ratios Birjand prints for its pairwise and frailty comparisons (3.9 and 1.4) come from tables
  with zero cells and no stated correction. They are not carried into `effect_size`.
- No one with two copies (T/T) was observed in either study. The T/T row says the two-copy effect is
  unknown and gets the same weight as C/T, not a larger one.
- Two candidate-gene studies with about 425 people between them are early evidence. A GWAS-scale
  replication does not exist yet in either paper's literature.

## Discrepancies found in the handed paper

1. **Consequence.** PMID 41249831 calls rs117385980 "a stop gained variant within the exon 2 of SIRT6 gene".
   Its cited source (PMID 28399814, which sequenced the region) calls it an intron variant 23 bases
   downstream of the exon 2/intron border. The ClinGen Allele Registry names the allele CA15948970,
   `NM_016539.4(SIRT6):c.194+194G>A`, which is also intronic. gnomAD v4 lists 183 T/T homozygotes, which
   also argues against a truncating change. This module treats the variant as intronic. The exact distance
   to the exon (23 bases per Hirvonen against +194 on NM_016539.4) is unresolved; the two may be using
   different exon or transcript numbering.
2. **Count.** PMID 41249831 quotes the Finnish result as "1/42 long-lived men". The source says 1/43.
3. **Odds ratio.** PMID 28399814's abstract prints OR 3.53; its Table 2 and results text print 3.58. This
   module uses 3.58.

## Weights

`weighting:` in `module_spec.yaml` declares the scale. Values run from -1 to 1, are set by the curator,
and are ordinal within this module only. Negative means the genotype was seen more often in people who
died earlier. C/C = 0 (common). C/T = -0.2. T/T = -0.2. The value is deliberately small because the
evidence is two non-significant trends. It is not an odds ratio and is not comparable with any other
module's weights.

## Frequencies

These come from gnomAD v4, read through `lookup_variant`. The T allele frequency is 2.7% in non-Finnish
Europeans, 2.4% in Finns, 2.5% in the Middle East, 0.9% in South Asians, 0.5% in Africans, and 0.003%
in East Asians (1 allele in about 30,000). The carrier figure in the conclusions ("about 5 in 100") is
2pq for European and Middle Eastern allele frequencies. The homozygote figure ("about 8 in 10,000")
counts gnomAD non-Finnish European homozygotes.

## Other SIRT6 variants named in the paper, and not included

PMID 41249831's discussion cites further SIRT6 SNPs from other studies:

- rs107251: TenNapel 2014, survival in an Iowa cohort.
- rs350846: You 2016, Bama longevity cohort.
- rs350852, rs350844, rs352493, rs4807546 and rs3760905: Lin 2016, Hainan, no association.

They are second-hand claims in this paper. No rows were authored for them. Adding them means reading
those primary papers, which is a decision for the module's owner. rs107251 is already carried by
`just-dna-seq/longevitymap` in the catalog.

## Review

On 2026-11-26 two independent AI reviews were run on the conclusion texts. They used separate
`claude-opus-5-5` subagents, and their outputs are not part of the module.

- **Lay reader:** no sources, plain text only. Flagged undefined terms ("protein-coding sections"), a
  missing statement of direction, and the alarming, unsized "nobody aged 80 or over".
- **Scientific reviewer:** re-read both papers in full. It confirmed every number and the intronic call.
  It flagged:
  - the Birjand result was presented selectively;
  - "slightly" mislabelled weak evidence as a small effect (the Finnish point estimate is about 3.6);
  - the T/T text did not say it was scored like C/T;
  - `suggestive` was generous;
  - the unsourced mouse-lifespan sentence;
  - the missing men-only caveat.

All of these were applied. The mouse sentence was removed rather than sourced. No human has reviewed
the module.

## Provenance quotes

Each `studies.csv` row carries a passage located verbatim in that paper's Europe PMC full text by
`claude-opus-5-5` (the `curator` column). `enrich_literature_pass` found both. Because the passages were
read from the same full text that the check searches, `quotes_found` here confirms the pairing between
citation and paper. It is not independent evidence that the claim is in the literature.

## Licence

Module licence: CC-BY-NC-4.0, declared by the agent and not yet confirmed by the owner. One quote comes
from a CC BY-NC-ND article (PMID 41249831), so commercial use is not permitted for that article's text.
`literature.csv` records each article's own terms.
