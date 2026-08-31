# Age-Related Disease Factor and Longevity (`longevity_ards`)

263 lead variants of the **multivariate age-related disease factor (mvARD)** — a shared genetic
component of heart attack, high cholesterol, hypertension, stroke and type 2 diabetes — together
with the direction each variant's effect allele takes in the same study's extreme-longevity GWAS.

## Source

One paper, open access under CC BY 4.0:

> Dinh P-A, Han H, Kim S, Guo Q, Zhang ZD, Vijg J, Suh Y.
> *Genetic links between multimorbidity and human aging.* GeroScience (2025).
> PMID **41405793**, doi **10.1007/s11357-025-02044-3**.

Every row is transcribed from that article's supplementary workbook,
`11357_2025_2044_MOESM2_ESM.xlsx`:

| Sheet | Supplies |
|---|---|
| **ST5** — Functional annotation of lead SNPs in mvARD | nearest gene, SNP function, MAF, CADD, effect / non-effect allele |
| **ST9** — Proxy-phenotype analyses of 263 SNPs in GWAS on extreme longevity | mvARD beta / SE / Z / P, longevity beta / SE / P, discordance flag |

ST5 and ST9 were cross-checked against each other for all 263 variants: **effect alleles, betas and
p-values agree in every row**, and the mvARD and longevity blocks of ST9 use the same effect-allele
orientation throughout (263/263), so no allele flipping was applied.

## What this module claims, and what it does not

**Each variant row claims a mvARD association, not a longevity association.** This distinction is the
central authoring decision and it is deliberate:

- All 263 variants are genome-wide significant for **mvARD** (max P = 4.99e-08).
- For **extreme longevity**, only **1** of 263 reaches genome-wide significance, **6** pass a
  Bonferroni threshold of 0.05/263, and **49** reach nominal P < 0.05.

The paper's longevity result is therefore a **set-level enrichment** across all 263 variants
(omnibus P = 9.73e-12), not a per-variant finding. Writing 263 rows that each asserted "associated
with extreme longevity" would have produced a module that compiles clean and asserts something the
source does not say. Instead the longevity direction rides on each row as **context**, with its own
beta and p-value quoted in the prose, and the set-level claim is stated here.

`category` records which side of that comparison a variant falls on, using the source's own flag:

| `category` | Variant rows | Meaning |
|---|---|---|
| `discordant_with_longevity` | 398 (199 variants) | mvARD and longevity betas have **opposite** signs — the disease-raising allele trends toward shorter life, the antagonism the geroscience hypothesis predicts |
| `concordant_with_longevity` | 128 (64 variants) | same sign |

199/263 = 75.7% fall in the antagonistic direction, symmetrically across both beta signs
(103/138 and 96/125).

**This module does not predict lifespan, diagnose anything, or compute a polygenic score.** It is
research-use annotation.

## Weights

Declared in full in `module_spec.yaml: weighting`. In short: positive is protective (this format's
convention, which is the **opposite** sign to a GWAS beta), each weight is a deterministic rescaling
of the published per-allele mvARD beta, and homozygotes carry twice the heterozygote value under an
additive model. No per-variant judgement was applied. Observed range **-0.5510 to +1.0000**.

The weights are **ordinal within this module only** and are not comparable with any other module's.

## Genotypes and coordinates

Two rows per variant — one heterozygote, one homozygote for the effect allele. The
homozygous-reference genotype carries no row, so absence of a match is not an assertion about a
non-carrier.

**No `chrom`/`start` is authored.** The source workbook gives positions, but the article's methods
(which would state the genome build) are not in the retrievable text — the supplementary PDF is
figures only, and the CC-BY full text was not reachable through the toolchain. Rather than assert a
build that could not be verified, the rows carry rsIDs only and coordinates are minted by resolution
against Ensembl on GRCh38. The published positions were **not** copied in.

## Provenance quotes — read `quotes_found: 0` correctly

Every `provenance_quote` is a **verbatim row of Supplementary Table S9**, rendered as its non-empty
cells joined by single spaces, in sheet column order:

```
rsID CHR BP EA OA BETA SE Z P  EA OA BETA SE P  Discordance
```

All 263 quotes are distinct — no repeated string stands in for a located passage.

**`enrich_literature_pass` searches the article body, not its supplementary files, so
`quotes_found: 0` is expected for every row here and does not mean the passage is absent from the
paper.** It means the checker never opened the workbook. This is the supplementary-sourced state, not
the "read and not found" state; the two are indistinguishable on the tool surface, which is why the
source file and sheet are named here and in `logs/authoring.log`.

The article body itself was retrieved only as an **abstract** (`text_source: abstract`), so no
body-text claim in this module was verified against full text.

## Attribution of the work

Located, transcribed and written by an agent (`claude-opus-5 (agent)`, recorded per row in `curator`
and per version in `authorship`). Responsibility for the module rests with its human author
regardless. Nothing in this module was read by a human reviewer at the time of writing.

## Known limits

- **Ancestry is not stated.** `population` names the contributing cohorts from source Table S1 (UK
  Biobank plus CHARGE, METASTROKE, SIGN, deCODE, EPIC-CVD, DIAGRAM, GERA) and says so explicitly.
  The ancestry composition could not be established from the retrievable material, and effects
  estimated in these cohorts may not transfer.
- **`gene` is the *nearest* gene** from ST5, which is not a causal-gene assignment. The paper's four
  high-confidence causal genes (DCAF16, PHF13, MGA, GTF2B) come from a separate TWAS/colocalisation/MR
  analysis and are not encoded per row.
- **`trait_efo_id` is empty.** mvARD is a latent factor over five diseases; no single ontology term
  names it, and attaching one of the five, or a longevity term, would misstate the row.
- **`p_value_num` is transcribed from the same workbook cell as `p_value`**, so their agreement check
  cannot fail independently.
