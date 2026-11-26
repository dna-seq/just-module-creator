# Coding variants shared by 21 centenarians and supercentenarians (Raj 2025)

This module records the 110 non-synonymous coding variants that
[Raj et al., *Human Genomics* 19:115 (2025)](https://doi.org/10.1186/s40246-025-00772-3),
PMID 41057961, found in **all 21** participants of a centenarian / supercentenarian
cohort and that SIFT scored deleterious. 108 of the 110 are carried here; three were
dropped and one extra variant was added (see *What is in, what is out*).

**Read this first.** The study is **case-only**. It has no control group, runs no
association test and reports no effect estimate. "Shared by all 21 participants" is not
evidence of a longevity effect — a variant carried by every human alive is also shared by
all 21. Nothing in this module is a risk estimate, a protective call or a longevity
prediction, and **no row carries a weight**: these rows must never be summed into a score.
Every row is flagged `no_control_group`.

The module exists because the variant list is a real, specific, checkable finding worth
recording — and because the checks that make it interpretable are not in the paper. They
are here.

## What is in this module

| | count |
|---|---|
| Variants | 108 (324 genotype rows: homozygous-cohort, heterozygous, homozygous-other) |
| Genes | 77 |
| rs-numbers the article supplied | 65 |
| rs-numbers recovered during curation | 43 |
| Variants with a weight | **0** |
| Studies rows | 108, all citing PMID 41057961 |

`state` is `alt` or `ref` and `direction` is `unknown` on every row. These are the
schema's *genotype descriptors* — they say which allele a genotype carries and assert no
direction at all. `neutral` was deliberately **not** used: `neutral` is a claim that the
variant has no effect, and a case-only study can no more establish absence of effect than
presence of one. This is a judgement call a reviewer may want to revisit, since `alt`/`ref`
are described in the format as retired descriptors.

The outcome strip (`outcome_healthspan` / `outcome_lifespan` / `outcome_exceptional`) is
null throughout — "untested", not "no effect". `phenotype_class` is left empty on the
study rows for the same reason: no outcome was tested.

## Resolution — what curation had to establish

The article reports **GRCh37** coordinates and alleles on the gene's strand. Nothing in
this format is GRCh37. Every variant was re-identified on GRCh38 through the Ensembl 116
REST API before a row was written.

- **43 of the 46 positions the article left without a dbSNP id now have one.** Each was
  lifted GRCh37→GRCh38, the GRCh38 reference base was read back, and an rs-number was
  accepted only when position **and both alleles** matched an Ensembl variation record.
  Those rows carry `rsid_recovered`.
- **14 of the 16 variants the article calls novel are catalogued in current dbSNP.** They
  carry `paper_called_novel`. The novelty claim rests on SNPnexus running against Ensembl
  95 (2019); it does not hold against Ensembl 116. (Two more "novel" variants were dropped
  entirely — below.)
- **7 variants' alleles are on the reverse strand** relative to GRCh38 forward. They are
  reported here on the forward strand and flagged `paper_alleles_reverse_strand`.
- **6 variants' "reference" base is an alternate allele on GRCh38**, i.e. the allele the
  article calls the variant is the current reference base. Flagged
  `paper_ref_is_not_grch38_ref`.
- **5 gene symbols are superseded**: C5orf45→MRNIP, FRG1B→FRG1BP, KIAA1551→RESF1,
  MDM1→SAXO6, TTC30B→IFT70B. All 80 symbols were checked against the HGNC REST API.

## Honest framing: the frequency evidence is in the paper's own supplement

The strongest reason for caution is not an outside opinion — it is Supplementary File 12,
the article's own gnomAD table, read column by column.

**58 of 108 alleles are the globally *commoner* allele.** The "minor allele frequency" the
article reports exceeds 0.55 for 58 variants and reaches 0.999 (rs6831040, BMP3). At these
sites the reference genome carries the rarer base, so essentially every human "has the
variant". Finding it in all 21 participants is arithmetically guaranteed. Flagged
`alt_is_global_major`.

**22 of 108 sit at exactly 0.50 in every population.** For 22 variants the article's
per-population gnomAD frequencies are all inside [0.495, 0.505] — AFR, AMR, ASJ, EAS, FIN,
NFE, OTH and SAS alike. A real biallelic polymorphism does not have identical frequency in
eight populations; a position where reads from two near-identical paralogous copies pile up
does, because every sample looks heterozygous. 14 further variants sit near 0.50 in the
gnomAD release Ensembl serves today. Flagged `frequency_pinned_half` and
`frequency_near_half_current`.

Current gnomAD contradicts or withholds most of these sites. Of the 31 variants the
article's gnomAD column puts between 0.45 and 0.55, the release Ensembl 116 serves reports
**9 at below 1%** — several at ~1 in a million, e.g. rs74589050 (OR4C3) at 6.8e-07 and
rs61849498 (TIMM23) at 2.1e-06 against a reported 0.50 — and serves **no frequency at all**
for 9 more. A frequency that moves from 0.50 to 1e-06 between releases is a call that was
wrong, not an allele that became rare.

**Only 4 of 108 alleles are genuinely rare** (<1% in the article's own gnomAD column):
rs141207681 (HNRNPCL1), rs575564328 (TRBV7-3), rs150316320 (PRSS3), rs75065468 (OR4C5).

**The gene list is a multi-copy gene list.** 28 of the 108 variants are in 13 olfactory
receptor genes; OR4C3 alone carries 9 and OR4C5 5. The rest cluster in PDE4DIP (5),
KCNJ12 (4), MAP2K3 (3), and in MUC3A/MUC4/MUC6, ANKRD36C, ANKRD20A1, PRAMEF, TRBV, TIMM23
/ TIMM23B, FRG1BP and HNRNPCL1. These are duplicated, repeat-rich or fast-evolving
families where short-read alignment is hardest and where loss-of-function alleles are
common in healthy people. OR rows are flagged `olfactory_receptor`.

**12 variants are not missense in current Ensembl.** For 7, the most severe consequence
across all transcripts is *less* severe than missense — synonymous (rs2905608, KLHL3),
intronic (rs2762745, PDE4DIP), 3'UTR (rs335689, UBE2Q2) or non-coding-transcript exonic
(rs9885913 and rs9885916 in PRIM2, rs2139440 in CRABP1, rs74765991 in FRG1BP). A SIFT
missense score cannot be interpreted at a position Ensembl no longer calls missense in any
transcript. Flagged `consequence_below_missense`. For 5 the most severe consequence is
*more* severe (stop_gained, start_lost): `consequence_above_missense`.

**After every flag, 19 variants are left** — and 9 of those are still in OR4C3/OR4C5, 2 in
ANKRD36C, 2 in TIMM23 and 2 in the TRBV T-cell-receptor segment. A consumer who wants the
defensible subset can filter on `flags`; what remains is small and still concentrated in
multi-copy families.

### Two claims in the paper that curation could not confirm

- The article names **rs412051** (BRD8) and **rs9885916** (PRIM2) as previously associated
  with longevity, citing a primate comparative-genomics paper (Muntané 2018,
  PMID 29788292) and a 2014 Kiel dissertation. A PubMed search returns **no record** for
  either rs-number, and Muntané 2018 is a phylogenetic genome–phenome analysis across
  primates rather than a human variant-association study. The attribution is not confirmed
  here. rs412051 is carried in the module under `category = prior_longevity_claim` with a
  conclusion that says so; it is the module's one SIFT-*tolerated* row. Muntané 2018 is in
  `literature.parquet` as read-but-uncited.
- The article's discussion describes **MDM1** as "a regulator of the p53 pathway". MDM1
  (now SAXO6) is a ciliary microtubule-binding protein; the p53 regulator is MDM2. The
  module carries the variant and the current symbol, not the interpretation.

Supplementary File 13's "References Related to Aging" column was **not** imported. Of its
35 entries, the majority point at somatic cancer mutation catalogues, a Google patent, lab
web tools and thesis PDFs rather than at aging or longevity literature. Treating them as
evidence would have misrepresented them.

## What is in, what is out

**Dropped (3 of the article's 110):**

| Variant | Gene | Why |
|---|---|---|
| chr1:13036247 T/A (GRCh37) | PRAMEF22 | Ensembl could not map the position to GRCh38 |
| chr1:13449723 G/C (GRCh37) | PRAMEF13 | Ensembl could not map the position to GRCh38 |
| chr10:51381481 C/T (GRCh37) | TIMM23B | lifted position does not carry the article's reference base on GRCh38 |

Both PRAMEF loci and TIMM23B sit in regions the GRCh37→GRCh38 transition rebuilt. Giving
them a GRCh38 identity would have meant guessing, so they are named here instead of shipped.

**Added (1):** rs412051 (BRD8), the SIFT-tolerated variant the article names as a prior
longevity association. See above.

**Not covered:**

- No polygenic score, no `pgs.csv`. There is none to point at and none can be derived from
  a case-only cohort.
- No clinical significance. `clin_sig_authority_calls` and `clin_sig_concordance` are
  present and empty: no ClinVar cross-check was run, and an empty table says "not asked",
  not "nothing found".
- No VRS identifiers. Minting them requires the enricher's reference-sequence digests.
  `resolution.csv` carries GRCh38 placements with `placement_verdict = undecided` — one
  authority answered, no second authority corroborated it.
- No model-organism evidence (`model_organisms.csv`). The paper has none, and importing
  lifespan experiments for 77 genes would be a different module.
- No pathway table. The article's Reactome enrichment (148 significant pathways) is run
  over variants that are largely the global major allele, so the enrichment inherits the
  same problem and is not represented here.

## Population

21 individuals: 13 female, 8 male; 3 centenarians aged 106–109 and 18 supercentenarians
aged 110–117; self-reported Caucasian 17, African 2, Hispanic 1, Ashkenazi Jewish 1.
`ancestry` on the study rows is recorded as `AFR|AMR|EUR`, mapping those self-reported
labels onto 1000 Genomes superpopulation codes; the free-text `population` column keeps
the cohort's own description. `eur_only_evidence` is `false`.

Allele frequencies quoted in row conclusions come from gnomAD and 1000 Genomes — the
article's v2.1 / Ensembl-95 values, and the current values Ensembl 116 serves, labelled as
such in each conclusion.

## Licensing — unresolved, and deliberately so

The article is **CC BY-NC-ND 4.0**. Non-commercial is recorded directly:
`commercial_use = false`, `declared_use = non_commercial` on the `raj_2025` source row at
the `annotation` layer, which is the layer that taints.

`redistribution` is left **null**, which in this format means *terms could not be
established* and is never a permission. The NoDerivatives term bars sharing adapted
material. Whether a reschematised extract of supplementary data tables is "adapted
material", or a set of facts that copyright does not reach, was not adjudicated during
curation. **A human licence decision is required before this module is published or
served.** If a registry enforces `manifest.sources.redistribution`, this module will be
withheld until that decision is made — which is the correct outcome, not a defect.

No sentence, table or figure of the article is reproduced. `provenance_quote` is null on
every study row, for the same reason the ADHD module leaves it null: a reuse right for the
article's expression was not established.

gnomAD's own terms are stated inconsistently across third-party listings (MIT, ODbL and
"no restrictions" all appear), so no licence is asserted for it; the frequencies are
carried as facts with attribution. HGNC (CC0), EFO (Apache-2.0), Ensembl and dbSNP are
recorded with their terms.

## Curation

AI-authored (`ai-module-creator`, Claude Opus 5), November 2026.

Checked during curation: PMID 41057961 and its DOI/PMCID against PubMed esummary; all 80
gene symbols against the HGNC REST API; every variant's GRCh38 placement, allele set and
most-severe consequence against Ensembl 116; all 46 coordinate-only positions lifted
GRCh37→GRCh38 with the reference base read back; EFO_0004300 confirmed through OLS4; both
"prior longevity association" rs-numbers searched in PubMed. The article's own counts were
reproduced from its supplementary files before anything was authored: 208 deleterious
transcript rows → 110 variants → 79 genes, and 39 novel transcript rows → 16 variants →
9 genes, all matching the paper exactly.

Not checked: ClinVar clinical significance; segmental-duplication or ENCODE-blacklist
overlap (the multi-copy reading above rests on gene family, frequency behaviour and
Ensembl consequences, not on a segdup track); LD; the article's Reactome enrichment; the
sample-level VCFs, which were not available.

Research and informational use only. This is annotation, not a health, diagnostic or
lifespan assessment.
