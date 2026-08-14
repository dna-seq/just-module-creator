# What more can be done

The [README](../README.md) walks one shape of module: a few SNPs, a genotype per row, a paper behind
each claim. That is the common case and not the only one. This page is a map of what else a module
can carry — read it when the simple one already works.

**Ask the tools for the details.** `list_tables` names the table kinds that exist right now,
`describe_table` gives one kind's columns and vocabularies, `table_requirements` says what is
required. Those answers come from the live schema; anything written down in prose here would drift.
The [create-module skill](../skills/create-module/SKILL.md) is the procedure, and
`references/TABLES.md` beside it is the "which table?" decision.

## Rows that are not about a genotype

A `variants.csv` row is *one variant + one genotype*. Other row subjects need other tables, and a
module carries **only** the kinds it uses — never an empty table to keep another company.

**A measured quantity with thresholds is a binning table, not a variant row.** Repeat counts, copy
number, mitochondrial heteroplasmy fraction, metabolizer activity scores: each is a number the
consumer measures, and the module says which range means what. `assets/htt_cag_repeats` is a worked
example — one gene, one repeat unit, ranges.

One rule that catches everyone: **on a dial, a shared endpoint is a boundary; on a counter, it is two
bins claiming the same number.** Continuous ranges (a fraction, a score) must touch. Integer ranges
(a repeat count) must not.

## Pharmacogenomics

How a person's genotype changes a drug response. It is the deepest area of the schema, and it has
its own vocabulary: named alleles (the `*2`, `*17` "star alleles"), the pair a person carries
(a diplotype), what each allele does, and which variants make an allele up.

Two drafters exist for it, both in **extended** mode: `draft_from_cpic` and `draft_from_clinpgx`.
They copy rows out of a curated source, so they take a `use` argument, and that is not a formality:

**Every PGx upstream — ClinPGx, CPIC, PharmVar — is CC BY-SA *plus a no-sale clause*.** None of them
is sellable. Do not read a bare "CC BY-SA" as permission. Pass
`use = unstated | non-commercial | commercial` to every command that copies rows, and the terms land
in `sources.csv`, which is the only file the compile gate reads. A source you copied from by hand is
invisible to that gate, so you add its row yourself.

`PHARMVAR_API_KEY` is personal under PharmVar's terms — never bake it into a module or a snapshot.

The PGx **cross-checks** are not wrapped as tools; drive them from the CLI
(`skills/create-module/references/CLI.md`).

## Polygenic scores

A `pgs.csv` row names a *published* score and the trait it was built for. The module carries the
score's identity and provenance; the consumer computes the number from their own genotypes. Same
division as everywhere else — the module is the knowledge, the reader brings the measurement.

## Evidence you can go deeper on

- **Has this been replicated?** `paper_citations` (extended) walks the citation graph around a paper.
  It is extended because a citation graph is sized by a corpus, not by what you named.
- **Reading the paper.** `lookup_open_access` says where a legal copy is and on what terms;
  `fetch_fulltext` returns the document. Neither will hand you a passage — see the README's note on
  the two quote columns, and the [find-evidence skill](../skills/find-evidence/SKILL.md).
- **Bulk passes.** `enrich_facts` and `enrich_literature_pass` (extended) rewrite the sidecars the
  compile gate reads, across every row at once.

## Learning from modules other people published

- `registry_search` — has someone already built this?
- `registry_get_module` — one module's full record.
- `registry_download` (extended) — the compiled artifact **and** the authored CSVs. A published spec
  is the most instructive thing the catalog holds, which is why the inputs come down by default here
  even though the client's own default omits them.
- `reverse_module` (extended) — reconstruct a spec from a compiled artifact, for the modules that
  predate published inputs.

## After you have published

- **Fix a bad card without spending a version.** `registry_amend_readme` replaces a published
  module's readme. The readme sits outside the content digest, deliberately, so prose cannot change
  what a module *is* — which makes it the one repairable thing about a published version.
- **A rehearsal can be deleted.** On the polygon, `registry_delete_version` /
  `registry_delete_module` clean up. Production refuses both and offers `yank` instead: a production
  version is immutable and its content claim outlives the yank.
- **Trust accumulates; it is not scheduled.** A high version number suggests somebody kept coming
  back. A named human curator costs human labour, and that cost is the signal. There is **no**
  contract that says `2.0.0` means reviewed or `1.0.0` means unreviewed — record what is true in
  `authorship:` and let a reader weigh it. Never hold a publish back waiting for a milestone that
  does not exist.

## What this will never do

It authors annotation tables. It does not read a genome, call a genotype, or give medical advice —
the consumer supplies the measurement, and a module row is a claim with a citation, not a diagnosis.

Module **signing** is also deliberately unwrapped: module identity belongs to the registry, which
stamps namespace, owner, version and canonical id on publish. Author-held signing sits beside that as
a prototype, and wrapping a prototype would lend it a durability its design has not earned.
