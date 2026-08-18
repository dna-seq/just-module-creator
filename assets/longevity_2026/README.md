# `longevity_2026` — thirteen longevity variants, grounded only in 2025–2026 work

Authored end to end by an agent on 2026-08-12 through the `just-module-creator` MCP surface, with no
human curation step. `authorship` says so: `kind: [ai, agent]`, `role: created`. That is the honest
label, not a disclaimer — a later human reviewer appends their own entry, they do not edit this one.

The constraint that shaped it: **every citation must be a 2025 or 2026 paper**, and preprints count.
Five papers ground 19 authored rows across 13 rsIDs.

| PMID | year | kind | what it grounds |
|---|---|---|---|
| 41427385 | 2025 | **bioRxiv preprint** | the ten rare familial-longevity candidates |
| 40594060 | 2025 | article, *Sci Rep* | `rs7412` — the C allele as the variant limiting extreme longevity |
| 40284181 | 2025 | article, *Nutrients* | `rs2802292` — the FOXO3 G allele's protective direction |
| 41588686 | 2026 | article, *J Cachexia Sarcopenia Muscle* | `rs429358` and `rs7412` directions; APOE-cluster colocalization |
| 41964836 | 2026 | article, *GeroScience* | `rs429358` and `rs2802292` in disease-free Super Seniors |

A preprint can ground a `studies.csv` row only because PubMed indexes it under a real PMID (the NIH
Preprint Pilot). `41427385` is a bioRxiv posting with a PMID; a bioRxiv posting without one could not
have been cited here at all, since `pmid` is required.

## The two halves, and why they are labelled differently

**Common variants (9 rows, 3 rsIDs).** `rs429358` and `rs7412` at APOE, `rs2802292` at FOXO3 — three
genotypes each, with `state`, `direction`, `weight` and `stat_significance: significant`. A 2025 or
2026 paper states the effect allele for each, which is the bar for writing a direction at all.

**Rare familial candidates (10 rows, 10 rsIDs).** One heterozygous carrier row each, from Table 3 of
the Leiden Longevity preprint. Nine carry `state: alt`, `direction: unknown`,
`stat_significance: suggestive` and **no weight** — the preprint prioritises them as candidates and
does not state a direction, so neither does the module. The tenth, `rs200818241` in *CGAS*, is the
only one written `protective`: it appeared in two independent sibships, was enriched in long-lived
individuals over controls, and was shown in cell models to reduce cGAS-STING signalling and delay
senescence. Its weight is `0.2` — deliberately small, because the source is still a preprint.

Only het genotypes were authored for the rare set. That is not caution about the biology, it is a
correctness property: a heterozygous genotype is an unordered pair, so it survives getting `ref` and
`alt` the wrong way round, and the preprint's effect/alternative allele columns are the only allele
information available for variants this rare. Enrichment later confirmed every pair against the
genome anyway — all 13 rsIDs resolved and no allele fell outside its locus.

## What was checked, and what came back

- `enrich_module` online: **15 loci resolved, 0 unresolved, 16 VRS ids minted**, no ref mismatches, no
  `clin_sig` conflicts, no stale rsIDs, no warnings.
- `check_identifiers`: 9 gene symbols approved, trait CURIE current, `stale: []`,
  `gene_locus_conflicts: []` **with `gene_locus_check_skipped: null`** — the comparison ran, so the
  empty list is a pass rather than a silence.
- `validate_module(strict=True)` and `compile_module(strict=True)`: both pass, `fully_resolved: true`,
  all 21 compiled weight rows carry a coordinate.
- Recompiled from the untouched spec: identical `artifact_digest`. That was `sha256:809facbf…` under
  format 0.5.4 and is `sha256:2df1276ace2d13…` under 0.6.1 — a compiler upgrade moves the
  byte identity and leaves `content_signature` alone, which is exactly what happened here.
  `verify_artifact`: digests verified (signature **not** checked — no key).

### The trait CURIE was found by being told, not by guessing

`trait_efo_id` is `OBA_VT0005372` ("life span determination trait"). It was reached by putting the
obsolete `EFO_0004300` to `lookup_identifier`, which answered `obsolete` and named the replacement.
Worth recording because the tool surface can *verify* a CURIE but cannot *search* for one by label —
so the only honest routes are being handed the id or walking an obsolescence pointer like this.

## What is deliberately absent

- **`provenance_quote` / `provenance_regex` are empty on all 16 study rows.** Three of the five papers
  were read through `fetch_fulltext`, and a passage lifted from the text that `quotes_found` later
  checks against would confirm itself. Empty by design, not pending.
- **`clin_sig` is empty everywhere**, including on `rs143389605`, where ClinVar has a call. It is
  redundancy-bearing; filling it from ClinVar would make the enricher's cross-check compare ClinVar
  with ClinVar.
- **No coordinates are authored.** Every `chrom`/`start`/`ref`/`alts` in the artifact was produced by
  `enrich_module` into `resolution.csv`. Authoring both sides is how a coordinate cross-check ends up
  agreeing with itself.
- **No effect sizes.** No 2025–2026 source read here stated one for these variants in a longevity
  model, and a number carried over from a different endpoint would look exactly as authoritative as a
  real one.

## Five variants were dropped, and that is part of the result

Named in the same 2025–2026 papers, and cut because no paper located here says **which allele** carries
the effect:

| dropped | named in | why |
|---|---|---|
| `rs13217795` (FOXO3) | 41964836 | listed among FOXO3 hits; effect allele not stated |
| `rs10457180` (FOXO3) | 41964836 | same |
| `rs7676745` (GPR78) | 41588686 | "associated with a lower likelihood of longevity" — variant, not allele |
| `rs2149954` (5q33.3) | 41588686 | named as a longevity locus, no direction |
| `rs6475609` (CDKN2B-AS1) | 41588686 | same |

Each would have compiled. A guessed `direction` is a coin flip that renders identically to a real one,
so 13 rsIDs with a stated allele beat 18 with five invented directions.

## Known warnings, not defects

- **VRS covers 16 of 19 alleles (84%).** `rs372893802` and `rs61745123` each map to a second locus on
  `HG2072_PATCH`, which has no refget accession, so no `ga4gh:VA.` id can be minted there. The rows are
  kept — deleting a locus to make a coverage number look better would be falsifying the resolution.
- **`license: CC0-1.0` against an annotation-layer source reporting `public-domain`.** The compiler
  flags the pair and declines to adjudicate. Adjudicated here: ClinVar is a US-government work with no
  copyright asserted and imposes no downstream obligation, so CC0-1.0 on the authored prose is
  compatible. The only ClinVar content in the annotation layer is two `negatives` notes.

## What this module is not

It is a lookup table of published associations. It does not read a genome, call a genotype, estimate
anyone's lifespan, or give medical advice — the consumer brings the measurement. Every effect here is
a population-level association small enough to be swamped by everything that is not genetic.
