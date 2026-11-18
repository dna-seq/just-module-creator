# SIRT6 and Longevity (`longevity_sirt6`)

One variant, three genotype rows, two papers. This module exists to record an
**exploratory and statistically non-significant** association between the SIRT6
variant `rs117385980` and human lifespan. It is not a predictive test.

## Origin

Built on request from a single seed paper, supplied as a DOI:

- **PMID 41249831** — Sheikholmolouki E *et al.*, *The association of the SIRT6
  rs117385980 variant with frailty and longevity: an exploratory study*,
  Scientific Reports, 2025. (`10.1038/s41598-025-24018-3`)

The seed paper's own longevity claim is inherited from the study it set out to
replicate, so that paper was traversed, retrieved and read as well:

- **PMID 28399814** — Hirvonen K *et al.*, *SIRT6 polymorphism rs117385980 is
  associated with longevity and healthy aging in Finnish men*, BMC Medical
  Genetics, 2017. (`10.1186/s12881-017-0401-z`)

Nothing else was used. No third source was consulted for the association claim,
and no rows were drafted from ClinVar — ClinVar holds no record for this variant.

## What the evidence actually says

Both studies point the same way and **neither reaches significance**:

| | Cohort | n | Result | p |
|---|---|---|---|---|
| Hirvonen 2017 | Finnish men (HBCS + HBS) | 198 | T allele over-represented among men who died earlier; OR 3.58 (95% CI 0.96–13.4) | 0.074 |
| Sheikholmolouki 2025 | Iranian elderly (BLAS) | 227 | No association with frailty (adjusted OR 0.96, p = 0.98); T allele absent above age 80 | 0.073 |

Hirvonen reports the study's own power as 28.4% and states that 427 cases plus
371 controls would be needed for 80%. The 2025 study had no dates-of-death data
at all, so its longevity reading is an age-stratification artefact rather than a
survival analysis. Twelve heterozygotes in one study and eight in the other are
the entire observational basis of this module.

**Treat the direction as a hypothesis, not a finding.**

## Two discrepancies found while authoring, and how they were resolved

1. **Variant consequence.** The seed paper describes `rs117385980` as *"a stop
   gained variant within the exon 2 of SIRT6"*. The paper it cites classifies the
   same variant, at the same coordinate, as an **intron variant** situated 23
   bases downstream of the exon 2 exon/intron border (Hirvonen Tables 1 and 2).
   gnomAD v4.1 records **183 homozygotes** for the T allele and shows SIRT6 is not
   loss-of-function constrained (pLI ≈ 0, LOEUF 1.06, 21 observed LoF variants) —
   both consistent with a tolerated intronic change and not with a segregating
   nonsense allele. This module follows the intronic reading and says so on the
   study row; the seed paper's "stop gained" wording was **not** propagated.
2. **Odds ratio.** Hirvonen's abstract reports OR 3.53; its Results text and
   Table 2 both report 3.58. The table value is recorded here.

## Genotype rows, and why there are three

- `C/T` — **risk**, direction risk, effect allele T. The only genotype either
  cohort observed carrying the minor allele.
- `C/C` — **neutral**. The common genotype (about 96% of gnomAD samples).
  Marked `requires_callable`, because a no-call is not a reference call and the
  reassurance must be withheld rather than asserted where callability is unknown.
- `T/T` — **alt**, direction `unknown`, significance `unknown`. Neither study
  observed a single homozygote, so this row deliberately asserts *nothing*. It
  exists because gnomAD shows such people are real, and a module that silently
  returns no annotation for them is less honest than one that says the evidence
  does not reach them.

## Replication status, checked 2026-08-31

**None.** A forward citation traversal of the seed paper (Semantic Scholar) returns
three citing works, and all three are narrative reviews of the sirtuin family or of
longevity genetics — no independent cohort has re-tested `rs117385980`. One of those
reviews places sirtuins among loci "variably supported at the variant level", against
FOXO3 and APOE as the consistent human associations.

Neither paper published supplementary material (Europe PMC lists no supplementary
file for the seed article), so the two in-text table sets are the whole dataset. The
seed cohort's individual-level data are stated as not publicly available.

So the evidence base is closed at two underpowered cohorts, 425 people, 20
heterozygotes, and no replication. Anyone revisiting this module should re-run that
citation check first.

## Weights

There are none, deliberately. `weighting.scale` declares `none`. Two underpowered
studies with confidence intervals crossing 1 do not support a weight, and this
module must not be folded into a polygenic score.

## Provenance and authorship

Both `provenance_quote` values are verbatim passages located by an agent
(`claude-opus-5`, recorded per-row in `curator`) in the retrieved fulltext, and
verified by the literature pass (2 of 2 found, no titles used as quotes). Neither
is the article title. The module was authored end to end by an agent — declared
in `authorship:` as `[ai, agent]` — and has had **no human expert review**. That
is the single most useful thing a reviewer can know about it.

## Licensing

The seed article is **CC BY-NC-ND 4.0**, read off the article itself. That is the
binding constraint on this module: non-commercial, and the NoDerivatives clause
is recorded in the `notice` column. Hirvonen 2017 is CC BY 4.0. Unpaywall also
reports a `cc-by-sa` DOAJ record for the seed article; the article text says
BY-NC-ND and the article text was preferred.

## What this module cannot do

It does not read a genome. It supplies annotation rows; a consumer such as
`just-dna-lite` supplies the measurement. Nothing here is medical advice, and a
single non-significant candidate-gene signal in two small cohorts is not a basis
for any decision about a person.
