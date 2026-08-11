# `fto_bmi` — a one-locus module, and the four things authoring it broke

A reference example from a dogfooding session on 2026-08-11, run as an assisted session: a
non-specialist user brought an LLM-written summary of two YouTube genetics lectures and asked for it to
be turned into a module. Published as a rehearsal to `test-sheep/fto_bmi@1.0.0` on the polygon.

It is deliberately small. The interesting part is not the module — it is the ratio, and what refused.

## What the source offered, and what survived

The PDF listed seven rsIDs across two topics. Checked against Ensembl and the literature:

| source claim | verdict |
|---|---|
| `rs1421085` in **FTO** | real — chr16, in FTO |
| `rs9939609` in **FTO** | real, and **dropped**: same signal as `rs1421085`, so two rows would double-count one effect |
| `rs6567160` in **MC4R** | real, and **dropped**: no located paper stated *which* allele carries the risk |
| `rs13010010` "CADM2" | CADM2 is chr3; the rsID is chr2 |
| `rs2252481` "NEGR1" | NEGR1 is chr1; the rsID is chr6 |
| `rs10180596` "EXOC3L2" | EXOC3L2 is chr19; the rsID is chr2 |
| `rs36071874` "FOXO3" | FOXO3 is chr6; the rsID is chr1 |

The four intelligence-section pairings are fabricated — real gene names with invented rs numbers, which
land on real positions only because dbSNP is dense enough that almost any 7-digit number hits
something. `literature_search` found **zero** papers for any of those gene+variant pairs.

So one row out of seven claims, and it needed a genuine curation decision to get there. That ratio is
the example.

## What is deliberately absent

- **`provenance_quote` / `provenance_regex` are empty.** No fulltext was fetched. Those columns record
  that a human read the paper and located the claim; filling them from an abstract a search tool
  returned would assert a reading nobody did. `sources.csv`'s `notice` says so in the published record.
- **No `effect_size`, no `p_value`.** The source PDF supplied numbers (`+1.2 kg`, `+3.0 kg`, `7x`) and
  one was demonstrably wrong — it reported the paper's *rescue* factor (7-fold, on repairing the
  variant) as the deficit (the paper says 5-fold). None was verified, so none is claimed.
- **No `license:` in the spec, and all three licence flags blank** in `sources.csv`. Unknown terms are
  undetermined, never permitted. The registry surfaces them correctly as
  `unknown_terms_sources: ["europepmc", "pubmed"]`.
- **No authored coordinates.** `variants.csv` carries the rsID only; `resolution.csv` is
  enricher-produced. That is what makes the coordinate cross-check meaningful — the independent second
  value exists. Confirmed to agree across two sources: the sidecar resolved from the **ClinVar**
  snapshot, and an earlier `lookup_variant` had reported the same `16:53767042 T>C` from **live
  Ensembl**.

## What it broke

Findings filed while authoring this, in order of severity:

| id | where | what |
|---|---|---|
| `S20` / `F17` | upstream + `pending-fixes.md` | **high.** A failed Ensembl request is reported as `loci: []` + *"live Ensembl has no GRCh38 locus for it either"* — a definite negative. `rs6567160` and `rs13010010` both reported no-locus on attempt 1 and resolved on attempt 2, unchanged call. `loci: []` is the fingerprint of a *fabricated* rsID, so flaky egress makes real variants look invented — it misfiled two genuine SNPs during exactly the triage above |
| `F18` | `dogfooding.md` | The skill claims "a green pre-flight should mean a green compile". Before `resolution.csv` existed: `validate_module(strict)` → valid, **zero** findings at any level; `compile_module(strict)` → refused |
| `F19` | `dogfooding.md` | Nine essentials tools were missing because the stdio server process was 3h older than HEAD, and **nothing on the surface reports the server's version**, so it took `ps` + `git log` + a grep to tell "stale process" from "tool does not exist" |
| `S21` / `F20` | upstream + `dogfooding.md` | `sources.csv` is the one sidecar a human must hand-write, and `list_tables` advertises it while `describe_table` and `get_template` reject the name. `authoring_reference()` omits `SourceRow` entirely, so its columns were read out of `model_fields` |
| `S23` / `F21` | upstream + `dogfooding.md` | The skill says a missing `sources.csv` row is a warning. Reality is inverted: the pubmed/europepmc rows draw *"declares 2 source(s) no table in this module uses"*, and **deleting the file entirely warns about nothing at all** |

`S22` (hg19→GRCh38 has no supported authoring path) was filed the same day as a longshot, from a
question this probe raised rather than from a failure in it.

## What held up, and should be said as loudly

- **The strict compile gate refused the unresolved module**, named the row count, and named the remedy.
  `F18` is medium rather than high entirely because of this.
- **Every refusal that was supposed to fire, fired.** `lookup_variant` withheld `chrom`/`start`/`ref`/
  `alts` with a reason; `literature_search` withheld every DOI; `check_identifiers` confirmed `FTO`
  against HGNC without touching the cell.
- **Reproducibility is real.** Recompiling the untouched spec reproduced `artifact_digest`
  `e52bd75…` exactly, and so did the **registry server's own** independent recompile.
- **Semantic Scholar 429'd throughout and was reported as `results: null`, not `0`** — unchecked, not
  empty (`F6`), which is the tri-state design earning its keep in the same session as `S20`, where the
  same distinction was fused.

## Reproducing

```
validate_module(spec_dir="assets/fto_bmi", strict=True)
enrich_module(spec_dir="assets/fto_bmi")        # delete resolution.csv first to re-resolve
compile_module(spec_dir="assets/fto_bmi", output_dir="out", strict=True)
```

Expect one warning on compile — the `sources.csv` orphan (`F21`). It is expected until `S23` lands, and
the rows are correct; do not delete them to silence it.
