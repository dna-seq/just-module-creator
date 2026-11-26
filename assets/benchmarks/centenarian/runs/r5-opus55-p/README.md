# Centenarian coding variants (Raj et al. 2025)

This module annotates eleven protein-changing DNA variants that one study found in all 21 of the
very long-lived people it sequenced. It does **not** say that any of them lengthens or shortens life.
The study had no comparison group, and population data show that none of the eleven separates
long-lived people from anybody else. Each result says what the reader carries, how common it is,
and why the study's observation does not translate into a prediction.

## Where it comes from

- **Source:** Raj APMS, Selvakumar G, Clement J, Church GM, Sivasubramaniam S. *Genetic signatures of
  exceptional longevity: a comprehensive analysis of coding region single nucleotide polymorphisms
  (SNPs) in centenarians and supercentenarians.* Human Genomics 2025;19:115.
  PMID 41057961, doi:10.1186/s40246-025-00772-3. Licence CC BY-NC-ND 4.0.
- **What the study did:** it took whole genomes from 21 people aged 106 to 117 (18 supercentenarians,
  3 centenarians), kept the variants present in all 21 and annotated them on GRCh37. It ran SIFT on
  the protein-changing ones and listed 110 as "deleterious" (Supplementary File 11). There was no
  control group and no per-variant statistical test.
- **Second source, one row:** Muntané et al. 2018, *Mol Biol Evol*, PMID 29788292 (CC BY-NC). The paper
  cites it for rs412051. It is a primate comparison: the BRD8 Q1198R change arose in parallel in
  longer-lived primate species. It is not a human association study.
- **Origin type:** a paper-drafted module. A later pass is owed when a study with a comparison group
  examines these variants, or if the paper is corrected.

## Which variants are here, and why these

Kept, by one rule: **the variants the paper's own text makes a claim about.**

| rsID | Gene | Why kept | What gnomAD v4.1 shows for the allele all 21 carried |
|---|---|---|---|
| rs412051 | BRD8 | named in Results as "previously associated with longevity" | 99.7% of chromosomes: the version nearly everyone has |
| rs9885916 | PRIM2 | named in Results as "previously associated with longevity" (the paper cites a 2014 PhD thesis, not retrieved) | gnomAD: not found; its neighbour rs9885913, also in all 21, is 7 of 1,608,770 |
| rs575564328 | TRBV7-3 | named in Results as rare (<1%) | 27 of 766,224 chromosomes |
| rs75029097 | KCNJ12 | named in Results as rare (<1%) | 50.0%, 0 homozygotes |
| rs11228733 | OR9G1 | named in Results as rare (<1%) | 49.5%, 4 homozygotes |
| rs61849494 | TIMM23 | named in Results as rare (<1%) | 4 of 1,613,722 |
| rs61849498 | TIMM23 | Conclusion's notable gene | 3 of 1,613,760 |
| rs3100906 | NEMF | Conclusion's notable gene | 98.7% |
| rs10454320 | KMT2C | Conclusion's notable gene | 48.5%, 0 homozygotes |
| rs2363198 | MAP2K3 | Conclusion's notable gene | 86 of 1,613,868 |
| rs2857919 | ZNF214 | Conclusion's notable gene | 96.0% |

Frequencies are from this module's `frequencies.csv` (gnomAD v4.1 joint, fetched 2026-11-26).

**How to read that column.** A variant that all 21 people share tells you something only if it is
uncommon in everyone else. These fall into three groups:

- **Common:** 3 variants, nearly everyone carries the allele.
- **Paralog pattern:** 3 variants at about 50% with almost no homozygotes. An ordinary two-allele
  variant at 50% would leave about a quarter of people with two copies. The usual cause of this
  pattern is a near-identical stretch of DNA elsewhere being read as this one; that cause is
  inferred here, not tested.
- **Near-absent in gnomAD:** 4 variants seen in 3 to 86 of up to 1.6 million chromosomes, yet called
  in all 21 genomes. Three of them (rs61849494, rs61849498, rs575564328) sit where GRCh38 has the
  sequence in the opposite orientation to GRCh37, the build the study used. A technical artefact
  is likely; its cause is not established.

The same pattern holds for the wider list. Of the 64 rsID-bearing "deleterious" variants in
Supplementary File 11, 59 resolved on GRCh38 and 55 of those have a gnomAD frequency (measured
2026-11-26 in a throwaway triage copy, not shipped):

- **40** have the cohort allele at 70% or more, because the GRCh37 reference carries the minority
  allele there.
- **9** sit between 40% and 55%.
- **5** are below 1%.
- **1** is in between (FRG1B, 22%).

**Left out, and why:**

- **46 deleterious variants with no rsID.** The supplement gives only GRCh37 coordinates, and nothing
  here converts coordinates between builds.
- **rs150316320 and rs141207681.** The text names them as rare, but the supplement lists them under no
  rsID. Pairing them with their supplement rows needs a GRCh37 dbSNP lookup, and that service
  (Ensembl GRCh37 REST) returned HTTP 500 on 2026-11-26.
- **The other 54 rsID-bearing deleterious variants.** They appear only in the supplement, and the text
  makes no claim about them.
- **MDM1 and the other genes the Discussion mentions.** The text describes what the gene does, not
  this variant.

## How the rows are written

- One row per genotype: zero, one or two copies of the allele the study reports.
- `state=alt` on rows carrying the allele the study reports, `state=ref` on the rows carrying
  neither copy. Every row has `direction=unknown` and `stat_significance=unknown`. No current
  `state` member means "observed, direction not known"; `alt`/`ref` are the descriptive ones.
- The trait is `OBA_VT0005372` (life span determination trait). `EFO_0007796` was considered and
  rejected: it is *parental* longevity.
- Genotypes are on GRCh38's plus strand. The paper's GRCh37 alleles were complemented at three loci
  that are inverted between the builds (rs61849494, rs61849498, rs575564328); `resolution.csv`
  confirms the result.
- Passages in `studies.csv` were located and quoted verbatim by an AI agent from the PMC fulltexts.
  The `curator` column records this.

## Weights

None. See `weighting:` in `module_spec.yaml`. With no comparison group there is no direction to
weight, so a blank weight means "not known", not "no effect".

## Licence

Both cited articles are licensed **non-commercially** (CC BY-NC-ND 4.0 and CC BY-NC 4.0); see
`literature.csv`. This module quotes short verbatim passages from them, so treat the module as
**non-commercial**. The ND (no-derivatives) clause of the main paper bars sharing adapted versions of
the article. The variant list and frequencies are facts, and the conclusions are new text, but
whether a module built on its supplementary table counts as "adapted material" is a judgement for
the publishing author.

## Authorship

Created by an AI agent (claude-opus-5-5) on 2026-11-26 from a request naming the paper. No human
has reviewed the rows yet.
