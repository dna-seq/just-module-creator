# colocalisations.csv — where a GWAS credible set and a molecular-QTL signal look like one causal variant

> **Written 2026-11-28 against format 0.9.0 / compiler 0.9.0 / enricher 0.9.0, read from the installed
> code.** The table landed in format 0.8 (upstream `RM333`). Anchor on symbol names:
> `locus_genes.ColocalisationRow`, `locus_genes.COLOCALISATION_FACT_FIELDS`,
> `overrides.OVERRIDABLE_TABLES`. Never on `file:line`.
>
> **Columns, types and requiredness are generated upstream**, at
> <https://just-dna.life/just-dna-compiler/tables/colocalisations/>, and live in-session from
> `describe_machine_table("colocalisations.csv")`. **The pass that writes this table is described once,
> in [`locus_to_gene.md`](locus_to_gene.md)**: the snapshot it reads, the coordinates it needs, the
> licence row, how to run it and what a re-run moves. This page keeps what is particular to
> colocalisations.

## In one paragraph

One row pairs a GWAS study locus your variant is a member of (the **left** side, the same
`study_locus_id` that [`locus_to_gene.csv`](locus_to_gene.md) keys on) with one molecular-QTL study
locus (the **right** side): an eQTL, sQTL or pQTL study measuring one gene in one tissue or cell type.
The statistics say how likely it is that the two signals share a causal variant. It is a second table,
not columns on the L2G row, because one `(study locus, gene)` pair colocalises in many tissues and QTL
kinds, and folding them in would make the table pick a tissue on the module's behalf.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.locus_genes.ColocalisationRow`, `extra="forbid"` |
| One row is | one `(left study locus, right study locus)` pair, per module variant in the left set |
| Natural key | run `hints.key_fields("colocalisations.csv")` |
| Becomes | `colocalisations.parquet`, in `compiler.ARTIFACT_PARQUETS` |
| Machine-produced | yes; written by `just-dna-enricher opentargets enrich`, which no tool runs on this machine |
| Fact signature | `integrity.colocalisation_signature`; `source` and `fetched_at` are outside |
| Overlayable | yes: subject `study_locus_id`, member `right_study_locus_id` |
| Compiler cross-check | **none** (`_no_checks`) |
| Manifest | `manifest.colocalisations`, an `OpenTargetsTable` block |

## Who decides which cell

- **The pass fills every cell** from the Open Targets snapshot. `right_gene_id` and
  `right_biosample_id` are looked up from the right-hand study rather than read off the coloc record,
  and they sit **inside** the fact hash: a colocalisation in another tissue is another claim.
- **`h4` and `clpp` are kept side by side, and neither replaces the other.** Upstream measured them
  disagreeing often enough that choosing one is a judgement. That choice, and any threshold that turns
  a posterior into "colocalises", belongs to the author's rubric, never to this table.
- **A statistic without its `method` is refused by the model** (`ColocalisationRow` pairs `h4` and
  `clpp` with `method`). A method with no statistic is a pair the source reported without numbers, and
  it is kept.
- **`right_study_type` is open**: the source adds QTL kinds between releases. Ask
  `describe_machine_table` for the recommended members rather than treating any list as complete.
- **A null `right_gene_id` means the right-hand study names no gene.** It is not a failed lookup to
  fill from another source; a gene supplied from elsewhere would be another source's claim on this row.

## How it relates to the rest of the module

- **The join to the gene question** is `right_gene_id` against `locus_to_gene.csv`'s `gene_id`, under
  the same `study_locus_id`. How much weight a gene that scores on L2G and also colocalises in some
  tissue deserves is the author's rubric, not this table's. Saying anything about it on a `variants.csv`
  row is authored prose, logged with `record_override`.
- **The join back to your rows** is `variant_key`, the variant the pass asked about: any
  `resolution.csv` key, which includes study proxies and rows left behind by removed variants
  ([`locus_to_gene.md`](locus_to_gene.md) explains why).
  A member of a molecular-QTL set only gets rows here as the right half of a pair: the snapshot holds
  GWAS sets on the left.
- **Tissue is the right side's, not your module's.** `right_biosample_id` is an ontology id, verbatim.
  Whether that tissue is relevant to the module's trait is the author's reading.

## Corrections, and what a re-run moves

Never edit this file by hand. The next run replaces every row of each variant it answers, so the edit
disappears with no record. A correction is an `overrides.csv` row naming the left `study_locus_id` as
subject and `right_study_locus_id` as member (see [`overrides.md`](overrides.md)). An `update` there
reaches every member variant's row of that pair, because the pair is a fact of the two sets, whichever
member asked. A `suppress` likewise removes the pair for every member; it cannot withdraw one member's
row alone.

Re-run semantics, the partial-snapshot rule and how to re-derive are in
[`locus_to_gene.md`](locus_to_gene.md); `refresh_sidecar` refuses this table and names the CLI.

## The symptom when it lies

- **Silence.** No compile check reads this table. A row for a variant you have since removed compiles
  green; compare its distinct `variant_key`s with `resolution.csv`'s keys.
- **No rows for a variant that has L2G rows** means the release records no colocalisation for those
  credible sets. It is not evidence that the gene is not expressed there.
- **Rows from a partial snapshot**: an absent pair may sit in a part the build never read. The run
  warns; read the warning before reading an absence as an answer.

## Ask the live schema

```
describe_machine_table("colocalisations.csv")
describe_machine_table("locus_to_gene.csv")     # the left side's gene scores
```
