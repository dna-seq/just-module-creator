# SIRT6 rs117385980 and human longevity

One variant, three genotypes, two studies. This module records what the published literature
actually says about a single SIRT6 polymorphism and human lifespan — which is less than the
gene's reputation suggests.

## What this module claims

`rs117385980` (chr19:4180588, C>T, GRCh38) is a low-frequency SIRT6 variant. Two independent
cohort studies have genotyped it against longevity or age:

| Study | Cohort | Result |
|---|---|---|
| Hirvonen 2017, PMID 28399814 | 43 long-lived + 92 earlier-deceased Finnish men (HBCS), replicated in 63 men aged ~83 (HBS) | T allele in 1/43 long-lived vs 9/92 controls; combined OR 3.58 (95% CI 0.96–13.4), p = 0.074 |
| Sheikholmolouki 2025, PMID 41249831 | 227 Iranian adults aged 60–90 (Birjand Longitudinal Aging Study) | Frailty: null (p = 0.36). Age gradient: T allele 1.39% at 60–69, 4.65% at 70–79, 0% at 80–90 (p = 0.073) |

Both point the same way — T carriers are thinner on the ground among the oldest — and **neither
reaches conventional statistical significance.** The Finnish study reports 28% statistical power
and estimates that 427 cases and 371 controls would be needed for 80%. Neither cohort has
mortality follow-up. The 2025 study is described by its own authors as exploratory.

**This module therefore encodes a direction, not an effect.** It should not be read as a lifespan
prediction for anybody.

## The weight scale

Declared in `module_spec.yaml` under `weighting:`, and repeated here because a consumer may see a
summed "net weight" without ever seeing the declaration:

- **−1 to +1, curator-set and ordinal. Positive is protective for lifespan.**
- `C/C` = `0.0` — a real claim that this genotype is the baseline, not a blank.
- `C/T` = `−0.15` — deliberately small. The magnitude encodes *strength of evidence*, not effect
  size, because both source findings are below significance.
- `T/T` = **empty**, which is not zero. See below.
- The Finnish odds ratio of 3.58 was **not** converted into a weight. It lives in `studies.csv`
  with its confidence interval and p-value attached, where a reader can weigh it properly.
- These weights are comparable with each other and with nothing else. Summing them alongside
  another module's weights combines incomparable scales.

## Why T/T carries no number

Neither study observed a single homozygote — 8 heterozygotes in 227 Iranian subjects, 12 in 198
Finnish men, no T/T anywhere. gnomAD does record the genotype (183 homozygotes in 574,784
alleles), so it exists in the population and a consumer will eventually meet one.

Both studies analysed *alleles*, not genotypes. Doubling their allele-level signal into a
homozygous effect is an inference the authors never make. So the row exists — a T/T carrier gets
an annotation rather than silence — but `weight` is empty and `direction`/`stat_significance` are
`unknown`. A weight of `0.0` was considered and rejected: `0.0` asserts *this changes nothing*,
which is a claim, and the honest answer here is that nobody has looked.

The reasoning is in `logs/authoring.log`.

## An unresolved disagreement between the two sources

The two papers describe the variant's molecular consequence differently, and this module asserts
neither:

- Sheikholmolouki 2025 calls it "a stop gained variant within the exon 2 of SIRT6 gene".
- Hirvonen 2017 places it "23 bases downstream of the exon/intron border of exon 2" and types it
  **intron variant** in both of its results tables.

These cannot both be right. A nonsense variant at ~2.7% frequency in non-Finnish Europeans, with
145 homozygotes recorded, would be a remarkable finding in its own right; a splice-region intronic
variant would not. No consequence annotation is recorded in this module, and no `clin_sig` is
authored — ClinVar returned no clinical significance for this variant, and an unchecked question
is not a benign answer. **Anyone extending this module should settle the consequence against a
current transcript annotation before adding one.**

## Provenance and its honest limit

Each `studies.csv` row carries a `provenance_quote` located in that paper's fulltext, verbatim,
supporting that row's own claim — not the article title. `curator` on each row names the agent
that located it. Both quotes verified as present (`quotes_found` 2 of 2, `titles_as_quotes` empty).

**The limit worth stating:** both fulltexts were retrieved through the same toolchain that then
checked the quotes against them. That check therefore confirms *citation pairing* — the quote
belongs to the PMID it is filed under — and is no longer independent evidence that the claim
appears in the literature. The reading is real; the check is narrower than it looks.

Responsibility for these rows rests with the human author of record, not with the agent named in
`curator`. `authorship:` currently lists only the agent; **a human contributor entry should be
added before this module is published anywhere.**

## Licensing — read this before redistributing

`licensing.csv` carries the binding constraint. The 2025 paper is **CC BY-NC-ND 4.0**, and one
clause of it is quoted verbatim in `studies.csv`, at the `annotation` layer. That makes this
module **non-commercial**: `declared_use` is recorded as `non_commercial`, and the compiler
requires that declaration rather than verifying it.

Two further notes:

- Hirvonen 2017 is CC BY 4.0 — the more permissive of the two. The NC-ND paper is what constrains
  the module.
- Unpaywall reports `cc-by-nc-nd` for the 2025 article at the publisher, while a DOAJ record for
  the same article reports `cc-by-sa`. The licence statement carried in the article's own text is
  CC BY-NC-ND 4.0, and that is what is recorded. The discrepancy is left visible rather than
  resolved.

## What this module is not

It does not interpret a genome, call a genotype, or offer medical advice. It supplies annotation
rows; a consumer supplies the measurement. Two small, underpowered, non-significant studies are
the entire evidence base — this is a starting point for someone extending the SIRT6 longevity
picture, not a finding to act on.
