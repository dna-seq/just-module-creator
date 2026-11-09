# `test_mthfr_folate`: MTHFR 677/1298 as a two-variant diplotype module, and what authoring it broke

A reference example from the tester seat's layman probe on 2026-11-09, plugin 0.48.3 on compiler 0.7.2 and
enricher 0.7.3. A layman arrives with a pasted AI chat about MTHFR, and the agent triages it through the
front door (`create-module` → `module-start`). The name is `test_`-prefixed so the registry's test-data sweep
collects a rehearsal of it. **It has not been rehearsed**: the test registry answered HTTP 502 for the whole
session. This is a probe, not a catalog candidate.

## The handed source, which is a planted test input

The "AI summary" below was **written by the tester seat to exercise triage**. Every identifier in it is real.
One claim is deliberately wrong: rs1801394 is MTRR's A66G, on chromosome 5, not an MTHFR variant. Nobody should
read it as a real claim.

> - C677T (rs1801133): TT reduces enzyme activity by about 70%; carriers should take methylfolate instead of
>   folic acid.
> - A1298C (rs1801131): has the same effect as C677T.
> - MTHFR A66G (rs1801394): a third MTHFR variant.
> - Two copies of any of these: "MTHFR positive", higher risk of heart disease, miscarriage and depression.

## Triage

| claim | verdict | evidence |
|---|---|---|
| C677T TT raises homocysteine | holds | Frosst 1995, PMID 7647779 |
| "about 70%" | left out | not in the text read |
| "take methylfolate" | dropped | medical advice, not a module claim |
| A1298C "same effect" | **contradicted** | van der Put 1998, PMID 9545395: neither genotype raises homocysteine |
| 677CT + 1298AC together resemble 677TT | found by reading, not handed | same paper |
| "MTHFR A66G (rs1801394)" | dropped | `check_identifiers`: chromosome 5, not MTHFR's 1 |
| heart disease, miscarriage, depression | dropped | nothing read supports it |

Three handed claims became two variants, and the module's central row came from the paper, not from the summary.

## The module

Four haplotypes over two variants (`wt`, `677T`, `1298C`, and `677T-1298C` in cis) and seven diplotypes. The
point is the pair: 677T on one chromosome and 1298C on the other (`1298C/677T`) is the at-risk combination. Both
on one chromosome with a common copy opposite (`677T-1298C/wt`) is not. They present the same unphased genotype,
so the compiler warns *"indistinguishable without phase"* and an unphased consumer must withhold. That warning
is the module's intended output, the pattern of `just-dna-format`'s `hfe_compound_het`. **No paper read
describes the cis arrangement**, and its conclusion says so.

Both `provenance_quote`s were located in the **abstracts** (`fetch_fulltext` returned `text_source: abstract`
for both PMIDs), by the tester seat, as `curator` records. `trait_efo_id` is empty: no ontology id was looked up.
Every authoring move is in `logs/authoring.log`.

## What it broke (findings in `docs/dogfooding.md`)

- **F135**: triage's gene-on-the-wrong-chromosome check, the catch for exactly this kind of generated claim,
  skipped on the rsid-only rows `module-start` teaches. It caught rs1801394 only after `enrich_module`.
- **F136**: `lookup_variant` prints every PubMind record twice (about 15 kB per answer). Three cold calls took
  2 min 43 s each; a warm one took 9 s.
- **F137**: after the triage table was removed, `resolution.csv` kept the dropped rsID. Validate, compile and
  audit were all quiet, and the manifest attested it (`resolution_signature`, `derived`); no parquet carried it.
  `refresh_sidecar` cleaned it, but read the author's removal as the source changing its answer. Upstream: S138.
- **F138**: `audit_module` read a stale `verification.json` as current, and never reads `diplotypes.csv`'s
  directions.
- **F139**: `enrich_module` re-signed `verification.json` over the current bytes while carrying
  `check_identifiers`' earlier record, so `gene_locus_agreement (1 of 3)` about rs1801394 is reported for a module
  that no longer names it. **This directory's `verification.json` is kept as that repro**: it still carries the
  record. F138's "stale" half now shows as F139 (hash current, record stale); the lead may treat them as one.
- **F132** (known): the closure warning names `just-dna-compiler close` where this surface has `close_module`.

What held: the router and `module-tables` sent the two-variant finding to `haplotypes.csv` + `diplotypes.csv`
with a worked example; `literature_search` found both primaries by title; `record_override` logged a row drop,
a file removal and a table edit as table-scope moves; strict validate and compile agreed.

## Reproduce

`validate_module(spec_dir="assets/mthfr_folate")` shows the phase warning and F139's carried finding.
`compile_module(spec_dir="assets/mthfr_folate", output_dir=<scratch>)` compiles strict.
