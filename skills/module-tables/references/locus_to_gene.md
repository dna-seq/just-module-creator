# locus_to_gene.csv — which genes a GWAS credible set points at, each scored, none chosen

> **Written 2026-11-28 against format 0.9.0 / compiler 0.9.0 / enricher 0.9.0 / registry client
> 0.35.0, read from the installed code.** The table landed in format 0.8 (upstream `RM333`). Anchor on
> symbol names: `locus_genes.LocusToGeneRow`, `opentargets.enrich_opentargets` in the enricher,
> `licensing.OPENTARGETS_TERMS`, `overrides.OVERRIDABLE_TABLES`. Never on `file:line`.
>
> **Columns, types and requiredness are generated upstream**, at
> <https://just-dna.life/just-dna-compiler/tables/locus_to_gene/>, and live in-session from
> `describe_machine_table("locus_to_gene.csv")`. This file keeps who decides which cell, what a re-run
> moves, and the symptom when the table is wrong. **It also owns the Open Targets pass**, which writes
> [`colocalisations.csv`](colocalisations.md) and [`consequences.csv`](consequences.md) in the same run;
> those two dossiers link here for it.

## In one paragraph

One row is one candidate gene for one **study locus** (Open Targets' credible set from one study),
for one module variant that is a **member** of that set, whether or not it leads it. The score is
Open Targets' locus-to-gene (L2G) model output. The table holds the **inputs** to an effector-gene
judgement and never the judgement: upstream deliberately computes no causal or effector label, and
neither does this plugin. Which gene a module names, and in what words, is an authored decision on
`variants.csv`, made by whoever is flying and logged with `record_override`.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.locus_genes.LocusToGeneRow`, `extra="forbid"` |
| One row is | one `(study locus, gene)` pair, per module variant in the set |
| Natural key | run `hints.key_fields("locus_to_gene.csv")`; `variant_key` is in it, so two module variants in one set each get the set's rows |
| Becomes | `locus_to_gene.parquet`, in `compiler.ARTIFACT_PARQUETS` |
| Machine-produced | yes. No drafter, no template; `describe_table` redirects to `describe_machine_table` |
| Written by | `just-dna-enricher opentargets enrich`. **No tool runs it on this machine** (see *Running it*) |
| Fact signature | `integrity.locus_to_gene_signature` over `LOCUS_TO_GENE_FACT_FIELDS`; `source` and `fetched_at` are outside |
| In `content_signature`? | no, it is not authored input |
| Overlayable | yes: subject `study_locus_id`, member `gene_id` (`overrides.OVERRIDABLE_TABLES`) |
| Compiler cross-check | **none**. The compiler routes it through `_no_checks`, a table with no check |
| Manifest | `manifest.locus_to_gene`, an `OpenTargetsTable` block: signature, sources, datasets, row and variant counts |

## Who decides which cell

- **The pass fills every cell**, from the provisioned Open Targets snapshot. `dataset` names the
  release, and it is inside the fact hash because L2G is retrained every release: the same pair scored
  by another release's model is another fact.
- **`variant_key` is the variant the pass asked about; `lead_variant_id` is the source's lead.** When
  the asked variant is a member and not the lead, the two name different variants. Never read
  `lead_variant_id` as "my variant leads this locus", and never parse it.
- **The pass asks about every `resolution.csv` key, not only your `variants.csv` rows.** That file also
  holds each study's LD proxy, resolved on purpose, and any row left behind by a variant you removed,
  since `enrich_module` never deletes one. Both get rows here under their own `variant_key`.
- **`l2g_score` is comparable only within one `dataset`.** It is a model output, not an effector call.
  What score makes a gene the effector is the module's rubric, stated by the author, never this table's.
- **The author decides three things, none of them a cell here**: whether to run the pass at all, the
  `declared_use` recorded on its licence row (`--use` on the CLI; a registry run under `remote_derive`
  records the deployment's own setting instead), and every gene claim a `variants.csv` row makes from it.
- **Several study loci per variant are kept and counted, never collapsed.** Picking the top score
  across studies is a ranking policy, and a ranking policy is a judgement for a pilot.

## The Open Targets pass (shared with colocalisations and consequences)

1. **It never fetches.** It reads the snapshot that `provision_caches(lanes=["opentargets"])` (CLI
   `opentargets build`) put on this machine. With none, it warns and writes nothing. That is *nobody
   asked*, not *Open Targets holds nothing*. Ask `provision_caches()` with `dry_run` for the price first:
   the lane is several gigabytes.
2. **Coordinates come from `resolution.csv`**, after `overrides.csv` is laid over it, so run
   `enrich_module` first. With no `resolution.csv` the pass refuses. The release is GRCh38-only; a row
   resolved on another build is skipped and counted.
3. **A resolution row with no ALT** gets the release's allele only when exactly one candidate carries
   the row's rsID; several candidates withhold the variant. A supplied ALT is **not** written back to
   `resolution.csv` and the run's warning names the keys. That allele is one the module did not author,
   so stating it is a decision to surface, not a gap to fill silently.
4. **A partial snapshot** (built from some parts of a dataset) warns and keeps every existing row under
   the default mode; `--strict` refuses before reading.
5. **It also fills a fine-mapping posterior on `gwas_effects.csv`** rows another pass wrote, so run
   `enrich_gwas_effects` before it. [`gwas_effects.md`](gwas_effects.md) predates that column.
6. **Licence.** One `licensing.csv` row per table it contributed rows to, source `opentargets`, terms
   from `licensing.OPENTARGETS_TERMS`: CC0-1.0, commercial use and redistribution permitted, with the
   Platform's notice that original data owners may still hold rights. No row lands for a table the run
   contributed nothing to. See [`licensing.md`](licensing.md).

## Running it

**No tool here runs this pass on the author's machine**; `cli_map` records it as a parity gap, not a
decision. Two routes:

```
uv run just-dna-enricher opentargets enrich <spec-dir> [--dry-run] [--strict] [--use non-commercial|commercial]
remote_derive(spec_dir, namespace, name, target="test", passes=["opentargets enrich"])   # dry_run=True first
```

`remote_derive` **uploads every authored CSV, `module_spec.yaml` and `logs/`** to the registry, so it is
the author's call with an explicit `target`. Run `registry_caches(target=…)` first: whether an instance
holds the `opentargets` lane is its operator's choice. Then `validate_module` and `compile_module`.

## What a re-run moves

**Answered replaces; could-not-ask keeps.** For every variant the run looked up, its rows are replaced
whole by the snapshot's answer, so a hand edit on such a row is gone after the next run and nothing
records it was there. That is why a correction goes in `overrides.csv`, never in this file (see
[`overrides.md`](overrides.md)). A variant the run could not ask about (off-build, unresolved, allele
withheld, snapshot not read whole) keeps its rows.

A variant you removed from `variants.csv` keeps its `resolution.csv` row, so **the pass keeps asking
about it and keeps writing its rows**. Nothing on this table warns. The nearest signal is the compiler's
`derived_row_orphan` warning on `resolution.csv` (see [`resolution.md`](resolution.md)); delete that
row first, then re-derive. `refresh_sidecar` refuses this table and names the CLI, because no tool here
could re-run the pass. To re-derive cleanly, copy the file out of the spec directory, delete it, and
re-run; [`module-refresh`](../../module-refresh/GUIDE.md) owns that procedure.

## The symptom when it lies

- **Silence.** No compile check reads this table, so a stale or orphaned row compiles green. Compare
  the distinct `variant_key`s here with `resolution.csv`'s keys, not with `variants.csv` (proxies are
  asked too), and read `manifest.locus_to_gene.datasets`: two releases in one table means some rows
  were kept from an older run.
- **A low `variant_count` is usually the release, not a defect.** Only variants in some GWAS credible
  set get rows.
- **No file after a run** (the pass writes none when it has no rows and none existed) means the run's
  warnings matter more than the file: no snapshot, every row off-build, or every allele withheld. Read
  them before concluding Open Targets holds nothing.

## Ask the live schema

```
describe_machine_table("locus_to_gene.csv")
describe_spec_file("overrides.csv")        # how a correction names subject and member
provision_caches()                         # is the opentargets lane here, and what it costs
```
