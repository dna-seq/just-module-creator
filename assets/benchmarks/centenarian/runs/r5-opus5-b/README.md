# longevity_centenarian

Eight coding variants that 21 people aged 106 to 117 all carried, and the reasons not to read much
into any of them.

Built from one paper: **Raj APMS, Selvakumar G, Clement J, Church GM, Sivasubramaniam S. "Genetic
signatures of exceptional longevity: a comprehensive analysis of coding region single nucleotide
polymorphisms (SNPs) in centenarians and supercentenarians." *Human Genomics* 2025.** PMID
`41057961`, DOI `10.1186/s40246-025-00772-3`, PMC `PMC12506250`, CC BY-NC-ND.

## What this module is not

**It is not a longevity test, and none of its rows carries a direction.** The source study sequenced
3 centenarians and 18 supercentenarians, kept the variants that were present with the same alternate
allele in all 21, and annotated them. It had **no control group, no comparison cohort, and ran no
association test** — no odds ratio, no hazard ratio, no p-value for any variant. So the strongest
honest claim per row is *this allele was present in all 21 sequenced genomes of that cohort*, and
nothing follows from it about anybody's lifespan. The paper says as much itself: its abstract's
closing sentence asks for "larger cohorts with appropriate controls".

Every `direction` cell therefore reads `unknown` — not `neutral`, which would be a claim — and every
`weight` cell is blank. `weighting:` in `module_spec.yaml` says the same in the author's own words:
**do not build a score out of these rows.**

**It is not a panel of the paper's 110 deleterious SNPs.** Eight of them are here. See *What was
dropped*.

## What a row says

| | |
|---|---|
| Rows | 24 — 8 variants x 3 genotypes (both copies of the cohort allele, one copy, neither) |
| Study rows | 9 — one per variant for the source paper, plus one for the article it miscites |
| Weights | none, deliberately |
| Coordinates | none authored. `rsid` only |
| State | `alt` on the two genotypes carrying the cohort allele, `ref` on the reference homozygote. Both are the vocabulary's direction-free members; `neutral` and `risk` would each assert something nobody measured |

## The eight, and why each is here

GRCh38 plus-strand alleles. SIFT scores and amino-acid changes are the paper's own (Additional
file 11); the "previously reported" flag is the paper's own text.

| Variant | Gene | ref>cohort allele | Paper's basis | SIFT |
|---|---|---|---|---|
| rs412051 | BRD8 | T>C | "previously associated with longevity" | 1 — **Tolerated** |
| rs9885916 | PRIM2 | A>G | "previously associated with longevity"; also deleterious | 0 |
| rs11228733 | OR9G1 | C>T | deleterious; MAF <1% in 1000 Genomes | 0.01 |
| rs75029097 | KCNJ12 | G>A | deleterious; MAF <1% in 1000 Genomes | 0.03 |
| rs575564328 | TRBV7-3 | G>T | deleterious; MAF <1% in 1000 Genomes **and** gnomAD | 0.04 |
| rs61849494 | TIMM23 | C>T | deleterious; MAF <1% in gnomAD | 0.04 |
| rs150316320 | PRSS3 | A>C | deleterious; MAF <1% in gnomAD | 0.028-0.042 |
| rs141207681 | HNRNPCL1 | C>A | deleterious; MAF <1% in gnomAD | 0.003 |

These are the eight variants the article names **in its own prose**. Every other variant it discusses
lives only in a supplementary table, as a position with no claim attached.

## Three findings the curation produced, which the paper does not state

These are this module's own, not the paper's. They are why the conclusions are hedged as hard as they
are, and a reviewer should check them before trusting them.

**1. rs412051's prior longevity association is a miscitation.** The paper cites PMID `29788292`
(Muntané et al. 2018, *Mol Biol Evol*) for it. That article is a comparative study of primates, not of
human longevity: it reports BRD8 p.Q1198R as one of 25 parallel amino-acid changes in three long-lived
primate species, states the human alternate allele is at **0.97** in the 1000 Genomes Project, and
calls the change **tolerated by SIFT and benign by PolyPhen2**. It also concludes the 25 parallel
changes "was not extreme in absolute terms" against its own resampling null. So the allele that all 21
very long-lived people shared at this site is the allele roughly 98 in 100 people carry, and the
article offered as its longevity credential does not claim a human longevity association. The article
has its own row in `studies.csv` saying this. The row stays in the module because a reader meeting
this variant elsewhere deserves to find that out; it does not stay as support.

**2. rs9885916's prior association rests on an unindexed doctoral thesis.** The paper's reference
`[30]` for it is a 2014 PhD thesis from Kiel (`macau.uni-kiel.de`, file
`Diss_nbadarinarayan_Oct2014_PhDthesis.pdf`, also reachable only via a `wps.com` share link in the
reference list). It has no PubMed id and no DOI, so it could not be checked and it has no row in
`studies.csv`. A Europe PMC search for `rs9885916` returns exactly one record: the source paper
itself.

**3. The rarity claim does not survive a second look, for seven of the eight.** Read against dbSNP's
per-study frequency table (NCBI E-utilities, 2026-11-26), the alternate-allele frequencies for these
sites disagree between callsets by two to five orders of magnitude:

| Variant | The paper's basis | What dbSNP's other studies say |
|---|---|---|
| rs11228733 | 1000 Genomes T = 0.0008 | 1000 Genomes 30X T = **0.49**, ExAC T = 0.49 |
| rs75029097 | 1000 Genomes A = 0.0002 | ExAC A = **0.49**, ALFA A = 0.50 |
| rs575564328 | 1000 Genomes A = 0.0002, gnomAD T = 0.000038 | ExAC A = 0.013, ALFA T = **0.12**, KOREAN A = 0.50 |
| rs61849494 | gnomAD exomes T = 0.0000021 | GENOME_DK T = **0.33**, KOREAN T = 0.53 (both reported on the opposite strand, as A and C) |
| rs141207681 | gnomAD exomes A = 0.000002 | ExAC A = 0.062, ALFA A = **0.21**, KOREAN A = 0.46 |
| rs9885916 | (not claimed rare) | ExAC G = 0.50 vs ALFA G = 0.040 vs PAGE G = 0 |
| rs150316320 | gnomAD exomes **T** = 0.0000007 | the cohort carried **C**: 1000 Genomes 30X C = **0.12**, ALFA C = 0.058 |

Two separate problems sit in that table. For rs150316320 the sub-1% figure is for a **different
alternate allele** from the one the cohort carried, so the rarity claim and the cohort observation are
about two different variants at one position. For the rest, the discordance itself is the finding: all
seven sit in olfactory-receptor clusters, a paralogue pair (KCNJ12/KCNJ18), the PRAMEF/HNRNPCL
duplication at 1p36.33, the somatically rearranged T-cell receptor beta locus, the duplicated
trypsinogen genes, or PRIM2 — where the paper's own table reports a second "deleterious" variant
(rs9885913) nine bases away, which is itself what paralogous mismapping looks like. These are the
places where short reads are hardest to place. A variant called in all 21 members
of a small cohort, in a region like that, is as consistent with a shared mapping artefact as with
shared biology. **rs412051 is the only one of the eight whose frequency estimates agree across
callsets**, and it is the one whose allele is near-universal.

## What was dropped, and why

A source that lists many variants usually supports few.

- **The other 103 of the paper's 110 predicted-deleterious SNPs** (Additional file 13; 64 of the 110
  carry an rsID, and 7 of this module's 8 variants come from that list). Dropped. The paper attaches no per-variant claim to them in its prose: they are positions in
  a list. Authoring them would turn one unmeasured observation into 300-plus annotation rows and make
  the module look like a polygenic score that nobody computed.
- **The 4,980 non-synonymous and 11,348 coding SNPs.** Dropped for the same reason, more so.
- **The 148 enriched Reactome pathways.** No table kind in this format holds a pathway enrichment, and
  a pathway is not a genotype.
- **Everything with no rsID.** The source is on **GRCh37** and nothing in this seat lifts coordinates
  between builds, so a variant the paper gives only as a GRCh37 position cannot come forward at all.
  That is most of the 110: 46 of them carry no dbSNP identifier in the supplementary table.
- **Additional file 13's "Reference" column.** It promises "literature references that support their
  association with aging-related processes" and is filled on 35 of the 110 rows; where it is filled, the
  targets include patent applications, a mutation-browser query URL and PDF-aggregator links. Nothing from it
  was carried into `studies.csv`.
- **`model_organisms.csv`.** This format has a table built for exactly the kind of evidence a
  longevity module wants, and this paper cannot fill it: its model-organism references are about
  protein function, not about measured lifespan in an organism carrying an orthologue of one of these
  eight genes. Left empty rather than padded.

## Design decisions

**Why `rsid` only, and no coordinate anywhere.** The source publishes **GRCh37** positions; this
module is GRCh38. Two of the eight (rs61849494, rs575564328) are **strand-flipped** between the
builds — the paper writes `G/A` and `C/A` where GRCh38 reads `C>T` and `G>T` at the same sites — so
pasting the paper's alleles would have been wrong in both the position and the letters. An rsid-only
row cannot carry a coordinate mistake, and it leaves the rsid-vs-coordinate cross-check something
independent to compare whenever this module is next enriched.

**Why there is no `resolution.csv`, and why one was not hand-written.** Coordinate resolution belongs
to `just-dna-enricher`, which is not installed in the seat this module was built in. A hand-built
`resolution.csv` would have been the module's *only* source of coordinates, and the compiler would then
have minted content-addressed `ga4gh:VA.` identifiers over numbers nothing had checked and reported
them verified. That is a documented way to ship a module about the wrong bases with every offline gate
green, so it was not done. The consequence is honest and visible: `fully_resolved` is false, the
compile is `best_effort` rather than `--strict`, and a consumer joins these rows by `rsid` and
`genotype`. **Running `just-dna-enricher enrich` is the first thing a second pass should do**, and it
is the only step that can catch a coordinate error in what is written here.

**Where the genotype letters came from.** The `genotype` column needs alleles, and the paper states
them only on GRCh37 (and, for two variants, on the other strand). The GRCh38 plus-strand reference and
alternate alleles were read from dbSNP, which is recorded as an annotation-layer row in
`licensing.csv`. `ref` and `alts` were **not** filled from the same read: they are redundancy-bearing,
and filling them there would have made the later reference-allele check agree with itself.

**Where `effect_allele` came from, and what it does not mean.** It names the allele the cohort shared.
It is the only machine-readable place in `variants.csv` that records which of the two alleles each row
is about, since `direction`, `weight` and `effect_size` are all absent. It is not an effect: there is
no effect to orient.

**Why the reference homozygote rows set `requires_callable`.** Those rows tell a reader they do *not*
carry the cohort allele. These sites sit in regions where a sequencer may simply fail to make a call, and a no-call is not a reference call — so a consumer without callability evidence should
withhold that sentence rather than assert it. `callable_from` points at `FORMAT/DP|FORMAT/GQ`. Nothing
reads these columns today; they are the only place the module can state where it stops applying.

**Why `phenotype_class` says `EXTREME_SURVIVAL_CC` on a study with no controls.** That token is the
only member of the recommended set that means *exceptional survival*, and the compiler uses it:
`studies.phenotype_class` is what fills `weights.parquet`'s `outcome_healthspan` /
`outcome_lifespan` / `outcome_exceptional` flags, which are the columns a longevity consumer facets
on and which an author cannot set directly. Measured here: `EXTREME_SURVIVAL_CC` and `FAMILIAL` set
`outcome_exceptional`, `OWN_SURVIVAL` and `PARENTAL_LIFESPAN` set `outcome_lifespan`, `HEALTHSPAN`
sets `outcome_healthspan`, and any token outside the recommended set both warns and leaves all three
null. The `_CC` suffix is a misfit — this is an uncontrolled extreme-phenotype cohort, not a
case-control study — and the set offers no uncontrolled variant. The design is stated unambiguously
beside it on the same row instead: `study_design` names the absence of a control group, and
`n_cases` equals `sample_size` equals 21. The Muntané row carries `EVOLUTIONARY`, which fits it
exactly.

**Why the licence declaration warns, and why it was left alone.** `license: CC-BY-4.0` covers this
module's own prose and curation. The one annotation-layer source row says `public-domain` (dbSNP), and
the compiler warns that the two spellings differ without adjudicating. They are compatible; the warning
is left standing rather than silenced by restating the module as public domain, which would be false
about the prose. Separately, the **source article is CC BY-NC-ND** — the verbatim passages in
`provenance_quote` are quotations from it, and anyone redistributing this module commercially should
read those terms. That per-article record belongs in `literature.csv`, which only an enricher pass can
write, so it is stated here instead.

**Why one quote is shared by three rows.** `provenance_quote` holds a verbatim passage that locates
*this row's* claim, never the article's title. One sentence of the paper names three of the variants
at once and another names four; those rows share the sentence that actually grounds them, rather than
each being given a different slice of it to look distinct. Five distinct quotes across nine study
rows, two articles, and `curator` on every one.

## Data sources

- **PMID 41057961** — the source paper. Full text read from Europe PMC (`PMC12506250`); all 13
  supplementary files fetched (225 MB). Two were read in detail and are the only ones that supplied
  facts used here: Additional file 11 (SIFT predictions) and Additional file 13 (the 110 deleterious
  SNPs). The three largest — files 7, 9 and 12, 238 MB, 86 MB and 50 MB — were not opened.
- **PMID 29788292** — Muntané et al. 2018, read in full from Europe PMC (`PMC6063263`), because the
  source paper cites it for rs412051.
- **dbSNP** — GRCh38 plus-strand alleles and per-study frequencies, via NCBI E-utilities, 2026-11-26.
  Recorded in `licensing.csv`.
- **EFO / OBA** — `trait_efo_id` is `OBA_VT0005372` ("life span determination trait"). `EFO_0004300`
  ("longevity") was the obvious choice and is **obsolete** as of EFO 3.74.0; OLS4 names
  `OBA:VT0005372` as its replacement.

## What has not been checked

A closure says that whoever closed it declared these bytes final — here an AI agent, which is what
`closed_by` records. It does not say anything was verified. On this module:

- **No coordinate has been resolved or checked.** No `resolution.csv`, no reference-allele check, no
  VRS identifier, no rsID currency check. Nothing here has been compared against the genome.
- **No gene-to-chromosome agreement check has run.** The gene symbols are the paper's; `check_identifiers`
  was not available.
- **`trait_efo_id` was checked by hand against OLS4, not by a tool.**
- **The quotes were located by reading the two articles' full text** and verified to occur verbatim in
  it by string match; no tool confirmed that independently.
- **No allele frequency, constraint, ClinVar or GWAS Catalog sidecar exists.** `clin_sig` is blank on
  every row: dbSNP reports rs75029097 as benign, and pasting that would have made the ClinVar
  cross-check agree with itself.
- **No independent review.** One AI agent wrote the rows, the conclusions and this file. Neither the
  lay-reader review nor the scientific review that `module-voice` asks for has been run, and no human
  has read the biology. `authorship:` records exactly that.
- **The module has never been run against a genome.**

## Origin

Authored in one session on 2026-11-26 by an AI agent (`claude-opus-5`) from a single DOI supplied by
the module's requester, in a seat holding `just-dna-compiler` 0.8.9 and `just-dna-format` 0.8.9 and
nothing else — no enricher, no registry client, no MCP tooling. Compiled `best_effort`; closed by
hand. Nothing published.

## Changelog

- **1.0.0 (2026-11-26)** — first version. 8 variants, 24 genotype rows, 9 study rows from 2 articles.
