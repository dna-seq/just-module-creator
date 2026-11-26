# Variants shared by centenarians and supercentenarians

A small annotation module built from one paper:

> Raj APMS, Selvakumar G, Clement J, Church GM, Sivasubramaniam S. *Genetic signatures of exceptional
> longevity: a comprehensive analysis of coding region single nucleotide polymorphisms (SNPs) in
> centenarians and supercentenarians.* Hum Genomics. 2025;19:115.
> doi:[10.1186/s40246-025-00772-3](https://doi.org/10.1186/s40246-025-00772-3) · PMID 41057961 ·
> PMC12506250 · CC BY-NC-ND 4.0

## What this module is not

**It is not a longevity predictor, and nothing in it raises or lowers anyone's expected lifespan.**
The source study took whole genomes from 21 people aged 106–117 (18 supercentenarians, 3
centenarians) and listed the variants that **all 21** carried. It had **no comparison group** of
people with ordinary lifespans and ran **no association test**. A variant that every one of 21
long-lived people carries may just be a variant that nearly everybody carries. So no row has a known
direction of effect: every row is `direction=unknown` and has an empty `weight`.

The module records what the paper reported, so a reader can see whether they share those variants.
It records nothing beyond that.

## What is in it

Eight variants. These are every rsID the paper's **body text** names as a finding, in two groups.

| rsID | Gene (GRCh38) | Allele carried by all 21 (GRCh38 + strand) | Why it is here | Population frequency of that allele |
|---|---|---|---|---|
| rs412051 | BRD8 | C | paper: "previously associated with longevity" | ~98% (1000 Genomes, TOPMed) — the reference allele T is the rare one |
| rs9885916 | PRIM2BP (paper: PRIM2) | G | paper: "previously associated with longevity" | not recorded in dbSNP |
| rs575564328 | TRBV7-3 | T (paper, GRCh37: A) | rare + SIFT-deleterious | 4×10⁻⁵ (gnomAD exomes) |
| rs75029097 | KCNJ12 | A | rare + SIFT-deleterious | 2×10⁻⁴ (1000 Genomes) |
| rs11228733 | OR9G1 | T | rare + SIFT-deleterious | 8×10⁻⁴ (1000 Genomes) |
| rs61849494 | TIMM23 | T (paper, GRCh37: A) | rare + SIFT-deleterious | ~0 (gnomAD exomes, TOPMed) |
| rs150316320 | PRSS3 | C | rare + SIFT-deleterious | ~0 (paper's gnomAD lookup) |
| rs141207681 | HNRNPCL1 | A | rare + SIFT-deleterious | ~0 (gnomAD exomes) |

Frequencies were read from dbSNP (NCBI Variation API) on 2026-11-26 to write the conclusions. They
are **not** stored as a frequency table, because the enricher that writes `frequencies.csv` was not
available.

**Genotype rows.** For the two "previously associated" variants there are rows for all three
genotypes. For the six rare variants there are rows for carriers only (heterozygous and
homozygous). The reference homozygote is what almost everybody has, so a row for it would say
nothing. The compiler warns that `6 genotype(s) at 6 site(s) have no row`. That warning is expected.

**Zygosity is not known.** The paper reports that the alternate allele was called in all 21
genomes. It does not say whether each person had one copy or two. So the het and hom rows for a
variant make the same claim.

## Curation decisions worth a reviewer's eye

1. **Strand and build.** The paper's coordinates are GRCh37 (the methods say "Genome assembly
   GRCh37/hg19 was selected"). For two variants the GRCh37 and GRCh38 forward-strand alleles are
   complements:
   - rs575564328 is C/A on GRCh37 and G/T on GRCh38.
   - rs61849494 is G/A on GRCh37 and C/T on GRCh38.

   The genotypes here use the GRCh38 spelling. No coordinate was authored. Rows are rsID-only, as
   the authoring guide asks for an old-build source.
2. **rs9885916 is not in PRIM2 on GRCh38.** The paper (and its Supplementary File 11) calls it a
   PRIM2 missense change (Y→C), using a GRCh37 transcript. On GRCh38, Ensembl places it in the
   pseudogene PRIM2BP and a lncRNA, as a non-coding change. The `gene` cell says `PRIM2BP`.
3. **rs141207681** is named in the paper's text. The paper's own Supplementary File 13 lists the same
   site (GRCh37 chr1:12907380 C/A, HNRNPCL1) with dbSNP "None". dbSNP places rs141207681 at exactly
   that GRCh37 site.
4. **The rare variants are probably artefacts. This is the curator's reading, not the paper's.**
   An allele seen in essentially nobody in gnomAD should not turn up in all 21 of 21 people. The
   genes involved sit in paralogous or segmentally duplicated regions: TIMM23/TIMM23B, the TRBV
   cluster, PRSS3/PRSS1, the HNRNPCL/PRAMEF cluster, the olfactory-receptor clusters, and
   KCNJ12/KCNJ18. In regions like these, short-read mapping errors are common. The conclusions say
   so as their final caveat.
5. **The "previously associated" claims are the paper's, and were not followed up.** The paper cites
   two sources for them. For rs412051 it cites Muntané et al. 2018, a cross-primate phylogenetic
   study. For rs9885916 it cites a 2014 Kiel PhD thesis. Neither was read for this module.

## What was left out, and why

- **The remaining ~100 deleterious SNPs** (Supplementary Files 11–13), the 389 novel non-synonymous
  SNPs and the 754,520 shared SNPs. The body text does not single them out. Many have no rsID, and
  this toolchain cannot lift GRCh37 coordinates without an rsID to GRCh38. The paper's evidence for
  each one is the same "present in all 21" observation.
- **Gene-level highlights** (MDM1, KMT2C, NEMF, MAP2K3, TNK1, ZNF214, ZNF534, ESPL1, CDK11, ERCC5).
  The paper discusses these genes from the literature. It makes no variant-level claim beyond
  "present in all 21". The novel variants it names in TIMM23, NEMF, KMT2C, MAP2K3 and ZNF214 have no
  rsID.
- **Pathway enrichment** (ECM organisation etc.). There is no per-variant claim to annotate.
- **Trait ontology id.** `EFO_0004300` ("longevity") is obsolete in EFO, and no current EFO term
  for an individual's own exceptional longevity was found. `trait_efo_id` is left blank.

## Provenance and quotes

`studies.csv` has one row per variant, each citing PMID 41057961. Each row carries a verbatim
passage from the article body that names that row's rsID (per-(pmid, rsid) grain). The full text
was retrieved from Europe PMC (PMC12506250, JATS XML). The supplementary archive came from Europe
PMC's supplementaryFiles endpoint. Quotes were located by `claude-opus-5-5`, recorded in `curator`.

## Licensing

The article is **CC BY-NC-ND 4.0**. The module carries short verbatim passages in
`provenance_quote`, so `licensing.csv` records the article at the annotation layer with
`commercial_use=false`. **`declared_use=non_commercial` was entered by the agent so the compile gate
would pass. The module's author must confirm it before publishing.** To use the module
commercially, the alternative is to delete the `provenance_quote` cells and the licensing row. The
conclusions are the curator's own wording.

## Origin

- Drafted from a single paper by an AI agent (`claude-opus-5-5`) on 2026-11-26.
- No human review yet.
- Not run against any genome.
- Coordinates are **not resolved**: no `resolution.csv`. The coordinate enricher was not available
  in the build environment. Consumers that match on rsID will work. Consumers that need `chrom`/`start`
  will not, until `just-dna-enricher enrich` is run on this directory.
