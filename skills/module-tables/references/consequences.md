# consequences.csv — what a variant is predicted to do to each nearby transcript

> **Written 2026-11-28 against format 0.9.0 / compiler 0.9.0 / enricher 0.9.0, read from the installed
> code.** The table landed in format 0.8 (upstream `RM236`). Anchor on symbol names:
> `consequences.ConsequenceRow`, `consequences.CONSEQUENCE_FACT_FIELDS`, `vocab.VALID_IMPACTS`. Never on
> `file:line`.
>
> **Columns, types, requiredness and the `impact` vocabulary are generated upstream**, at
> <https://just-dna.life/just-dna-compiler/tables/consequences/>, and live in-session from
> `describe_machine_table("consequences.csv")`. **The pass that writes it is described once, in
> [`locus_to_gene.md`](locus_to_gene.md)**: the snapshot, the coordinates from `resolution.csv`, the
> licence row, how to run it and what a re-run moves.

## In one paragraph

One row is one `(variant, transcript)` pair: the Sequence Ontology consequence Open Targets' VEP
annotation gives your variant on that transcript, and VEP's impact class. The grain is per transcript
on purpose. One MANE value per variant would throw away the rest, and "the most severe consequence
across transcripts" is a ranking policy, which upstream leaves to the consumer and this plugin leaves to
the author. Unlike the two study-locus tables, every `resolution.csv` key the release knows gets rows
here, GWAS signal or not; that includes study proxies, which are resolved on purpose.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.consequences.ConsequenceRow`, `extra="forbid"` |
| One row is | one `(variant_key, transcript)` pair |
| Natural key | run `hints.key_fields("consequences.csv")` |
| Becomes | `consequences.parquet`, in `compiler.ARTIFACT_PARQUETS` |
| Machine-produced | yes; written by `just-dna-enricher opentargets enrich`, which no tool runs on this machine |
| Fact signature | `integrity.consequence_signature`; outside it are `source`, `fetched_at`, the `gene` symbol and `rsid` |
| Overlayable | yes: subject `variant_key`, member `transcript` |
| Compiler cross-check | **none** (`_no_checks`) |
| Manifest | `manifest.consequences`, an `OpenTargetsTable` block |

## Who decides which cell

- **The pass fills every cell** from the snapshot's VEP annotation, verbatim. `dataset` names the
  release whose annotation it is.
- **Which transcripts appear is the source's choice.** The release upstream measured lists one
  transcript per nearby gene, each flagged Ensembl-canonical, not every transcript of every gene.
  `canonical` records that flag rather than the table implying it. A transcript you expected and do not
  see is a fact about the source's selection, not a failed lookup.
- **`consequence_so_ids` holds accessions, not labels** (`SO_0001583`, not `missense_variant`). Several
  are comma-joined in the source's order when one transcript carries several. Mapping them to words is
  a mapping someone would have to own; when a conclusion needs the word, look the accession up and say
  where it came from.
- **`impact` is the class on this transcript only.** It is never the worst class across the variant's
  transcripts, and reading it that way is the ranking policy the grain exists to refuse.
- **`mane_select` is how to pick one row per gene without a ranking policy**: it carries the RefSeq
  accession when the transcript is that gene's MANE Select, and is null otherwise.
- **`gene_id` is the fact; `gene` is a label** the source renames between releases, so the symbol sits
  outside the fact hash. **`rsid` is yours**, the module's rsID for the variant, and is outside too, so
  two modules holding the same consequences hash equal whether or not their resolver attached one.

## How it relates to `variants.csv` and resolution

- **The join is `variant_key`.** The pass asks by allele, from `resolution.csv`'s coordinates, so a
  variant with no resolved ALT gets rows only when the release names exactly one candidate allele for
  its rsID ([`locus_to_gene.md`](locus_to_gene.md), the pass, item 3). A variant that resolves to several
  release alleles has its consequences **withheld** and named in the run's warning, because its
  per-transcript rows would collide on one key.
- **A `variants.csv` row's own `gene` is authored.** If it names none of the genes this table lists
  for the variant, that is a decision to put in front of the pilot: the row may name the gene the
  evidence is about rather than a nearby one. Neither side wins by default.
- **A predicted consequence is not a measured effect.** A HIGH impact on a transcript is VEP's class,
  not evidence about a phenotype. A conclusion grounded only on this table should say so.

## Corrections, and what a re-run moves

Never edit this file by hand. The next run replaces every row of each variant it answers, and nothing
records the edit. A correction is an `overrides.csv` row with subject `variant_key` and member
`transcript` (see [`overrides.md`](overrides.md)). Re-run semantics, the partial-snapshot rule and the
re-derive procedure are in [`locus_to_gene.md`](locus_to_gene.md); `refresh_sidecar` refuses this
table and names the CLI.

## The symptom when it lies

- **Silence.** No compile check compares this table with `variants.csv`. A removed variant keeps its
  `resolution.csv` row, so the pass keeps answering for it; compare this table's distinct `variant_key`s
  with `resolution.csv`'s keys, and heed `derived_row_orphan` on `resolution.csv`.
- **A variant with no rows** after a run is one of: off-build, unresolved, allele withheld, ambiguous,
  or absent from the release. The run's warnings say which; an absent row is not "no consequence".
- **`datasets` naming two releases** means some variants kept rows from an older run.

## Ask the live schema

```
describe_machine_table("consequences.csv")   # columns and the impact vocabulary
lookup_variant("rs4988235")                  # a second view of one variant's coordinates and alleles
```
