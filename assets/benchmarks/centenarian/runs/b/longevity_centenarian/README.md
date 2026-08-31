# Centenarian Shared Coding Variants

Coding variants observed in a cohort of 21 exceptionally long-lived people, taken from a single
2025 study. **This module is descriptive. It does not predict longevity and must not be read as
saying any listed variant causes, protects against, or is associated with a long life.**

## The one source

Raj APMS, Selvakumar G, Clement J, Church GM, Sivasubramaniam S.
*Genetic signatures of exceptional longevity: a comprehensive analysis of coding region single
nucleotide polymorphisms (SNPs) in centenarians and supercentenarians.*
Human Genomics. 2025;19:115. PMID **41057961**, PMC12506250, doi 10.1186/s40246-025-00772-3.
Licence **CC BY-NC-ND 4.0** — non-commercial, and no distribution of adapted material.

## What the study did, and what it did not do

It sequenced 21 individuals aged 106–117 (3 centenarians, 18 supercentenarians; 13 female, 8 male;
African, Caucasian and Asian ancestry), took the variants they all share, annotated the coding ones
with SNPnexus, and scored them with SIFT. From 1.6 M annotated variants it reports 11,348 coding,
4,980 non-synonymous, and **110 predicted deleterious across 79 genes**.

It has **no control group**. It performs **no association test** — there is not a single p-value,
odds ratio, effect size or effect allele for any variant in the paper. The authors say so
themselves, calling the findings "preliminary" and asking for "larger cohorts with appropriate
controls".

Consequently every row here means only: *this coding variant was among those shared by all 21
members of that cohort, and SIFT predicted it deleterious.* Nothing more is claimed, and
`direction` is `unknown` on every row because nothing in the source states one.

## Why there are no weights

`weight` is empty on every row and `weighting:` in the spec says why: with no effect size, no
effect allele and no association statistic in the source, there is nothing to derive a weight from.
**Do not sum these rows.** They are presence annotations, not score contributions.

## The genome-build problem, and why rows are rsID-only

The paper is **GRCh37/hg19** throughout — it says so in its methods, and its supplementary
coordinates are GRCh37. This module is GRCh38. The two disagree by megabases in places
(rs1778159 is chr1:144,871,755 in the paper and chr1:149,012,717 on GRCh38), and the paper's
allele column is written against a strand column that is sometimes the opposite strand
(rs61849494 is `G/A` in the paper and `C>T` on GRCh38 — the reverse complement).

So **no coordinate, ref or alt from the paper was copied into this module.** Rows carry the rsID
only, and GRCh38 coordinates and alleles come from resolution, independently. That is also what
makes the compiler's rsID-versus-coordinate check meaningful rather than self-confirming.

## What is in, and what was left out

Rows were built from **Additional file 13**, the authors' table of the 110 deleterious SNPs
(titled inside the workbook "Supplementary File 14 – Deleterious SNPs and Their References
Related to Aging"; the file numbering is off by one in the published article).

- **Carried:** the entries in that table that bear a dbSNP rsID, plus `rs412051`, which the body
  names but the table does not. Each contributes two rows — heterozygous and homozygous for the
  non-reference allele — so the module annotates a carrier either way.
- **Left out:** the entries with no rsID, which are coordinate-only on GRCh37. **This includes the
  16 novel variants in 9 genes that the abstract leads with.** Carrying them would mean lifting
  GRCh37 coordinates into a GRCh38 module, which is exactly the mistake the section above avoids.
  Reaching them properly needs a GRCh37→GRCh38 liftover, which is not part of this toolchain.
- **Not used as citations:** the third-party links in that table's "Reference" column. They are the
  authors' own loose aging attributions and include a Google patent, several leukemia and cancer
  papers, lab web pages and an unpublished thesis. Every study row here cites the paper itself.

## Two variants the paper links to longevity, and how weak that link is

The body says `rs412051` and `rs9885916` "have been previously associated with longevity in earlier
studies". Those two claims rest on the paper's references 29 and 30, and both are weak:

- ref 29 is a **cross-primate comparative genomics** study, not a human longevity association study;
- ref 30 is an **unpublished 2014 PhD thesis** behind a file-sharing link.

They are carried under `category=prior_longevity_association` because that is what the paper says
about them, and this note is here so nobody mistakes it for replicated human evidence.

## Provenance of the quotes

Every `provenance_quote` is a verbatim passage from the article's fulltext, located by
`claude-opus-5`, which is recorded in `curator` on each study row and in `authorship:` in the spec.
There are three distinct quotes, chosen to match what each row actually claims — the set-level
deleterious finding, the population-rarity finding, and the prior-association sentence — rather
than one string repeated across every row.

Because the fulltext was retrieved and read through this toolchain, the enricher's `quotes_found`
check on these rows is a **citation-pairing** check: it confirms the passage belongs to the cited
PMID, and is no longer independent evidence that the claim appears in the literature.

## Counts in the source do not reconcile

Reported for transparency, not as a defect: the abstract says 110 deleterious variants while
Additional file 13 lists 111 data rows; the results text says "208 SNPs (223 with duplicates)"
deleterious; and the annotated-variant total is 1,607,122 in the abstract and 1,607,112 in the
conclusion. Counts here were taken from the table actually carried, not from the prose.

## Status

Research use. Authored by an AI agent from one paper, and **not reviewed by a human geneticist**.
The `authorship:` block records that. Treat it as a starting point for curation, not as a
finished clinical resource.
