# Your four published modules: one question on two rows

**For:** Anton, owner of the `antonkulaga/*` modules on the production catalog.
**From:** the just-module-creator lead seat, drafted 2026-11-16; the repository owner decides whether and how it is sent.
**Read:** the versions published now, downloaded with their authored CSVs on 2026-11-16:
`big_five_personality_snps@2.1.2`, `aggression_anger_snps@2.0.2`, `cognitive_intelligence@2.0.2`,
`risk_impulsivity_snps@2.0.2`.

Published versions cannot change, so the question below is about a next version, or about leaving it.

## What the four hold, in brief

- Each declares `authorship`, naming an AI agent as creator.
- `provenance_quote` is sparse and every quote is its own passage: 2 of 28 study rows in aggression,
  4 of 89 in cognitive, none in risk. Big-five has no quote column; its README says so. No PMID
  repeats one quote across its rows, the pattern an article title leaves.
- Aggression's `population` names each cohort's size and ancestry.

Nothing in that list asks anything of you.

## The one question: two big-five rows and the sociability paper

In `big_five_personality_snps@2.1.2`, two `studies.csv` rows cite PMID 34054130 (Bralten et al. 2021,
GWAS Catalog `GCST012111`) under trait `EFO_0009589`, labelled "Worry too long after an embarrassing
experience":

| rsid | p in the row | p in the paper's Table 1 |
|---|---|---|
| rs4245154 | 9e-09 | 7.17e-09 |
| rs527528 | 4e-11 | 4.02e-10 |

The paper is titled "Genetic underpinnings of sociability in the general population". Its Table 1 lists
both variants as "lead-SNPs ... in the GWAS of the sociability score in the UK Biobank sample". That
score adds up four questions, and worry after social embarrassment is one of them. So the trait label and
the p-values in these rows do not match the paper's main result.

Both rows may still be right. The paper reports each question separately in its Supplementary
Table 4, and `GCST012111` may be the catalog's record of the worry question alone. The catalog
record decides it:

1. **If `GCST012111` is the worry question**, the rows stand. A `provenance_quote` from Supplementary
   Table 4 would show it.
2. **If it is the combined score**, the trait becomes sociability, and the p-values become the
   Table 1 values above.

Each row also cites a second paper for neuroticism (PMIDs 29500382 and 31972866), so neither answer
removes a variant from the module.

## How this was checked

The four versions were downloaded from the catalog and their rows counted directly. The paper was
read in full from PubMed Central (PMC8280100), and the passages and p-values above are quoted from
that text.
