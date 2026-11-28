# meta.csv: statements about other rows, alone or in combination

> **Written 2026-11-28 against format, compiler and enricher 0.9.0** (`importlib.metadata`, this
> repo's venv). Every column, type, requirement and vocabulary is generated upstream at
> <https://just-dna.life/just-dna-compiler/tables/meta/>, and live in a session from
> `describe_table("meta.csv")` and `table_requirements("meta.csv")`. This file keeps what a model
> cannot state: who decides which cell, what an edit moves, and the symptom when the table lies.
> Where the two disagree, the generated page and the tool are right and this file is the bug.

## What it is

Every other authored table makes single statements: one variant and genotype, one diplotype, one
drug. `meta.csv` makes statements **about rows of those tables**. A row names its *members* in a
small selector grammar (upstream's own example is `variants[variant_key=rs429358, genotype=C/C]`;
the grammar is in the `members` column's description) and attaches one or more of:

- **a finding about the combination.** On a row with two or more members, `conclusion` replaces
  the findings of the rows the members match. This is the home for "these two together mean
  something neither means alone".
- **a judgement on one trait** (`trait_efo_id` with `direction`), so one locus can be protective
  for one trait and a risk for another. The compiler marks that as a `tradeoff`.
- **per-locus facts** no single-statement table has a column for: an evidence `tier`, when in life
  the effect acts, tags.

Any row may be scoped to a `sex` or a `drug`, and the scope is part of the key. Which tables a member
may name is `just_dna_format.meta.META_MEMBER_TABLES`. `studies.csv` is refused by design, because a
study is evidence for a statement and not a statement. Cite it with the row's `pmid` instead.

## When a module needs it

Only when the module states a combination, a per-trait judgement, a tier or an age of action, or a
sex- or drug-scoped fact. It is never a lead table: a directory holding `module_spec.yaml` and
`meta.csv` alone is refused with *"module has no recognized table"* (measured). It belongs to
[`module-curate`](../../module-curate/GUIDE.md) and to a later pass, once the rows it names exist.

## Who decides which cell

- **Every authored cell is the author's**, whether the author is a person or the agent co-authoring.
  No drafter writes this table: no `*_draft` module upstream imports `MetaRow`, the enricher reads
  the file only to collect the rsIDs its members name, and no `draft_from_*` tool here touches it.
  Its place in `draft.DRAFTABLE` means *authored*, which is why `get_template`, `scaffold_module`,
  `lint_rows` and `describe_table` all answer for it. The scaffold's stub row puts the placeholder
  in `members` and `conclusion`.
- **Pilot cells.** `direction` and `conclusion` are the two the server withholds for a pilot, and
  `negatives` reads the same way. A `sex` or `drug` scope is a claim about what the evidence
  measured, so it comes from the paper and never from tidiness.
- **`tier`** grades on a scale the module names once as `tier_scale` in `module_spec.yaml`
  (`describe_spec_file` answers it). Values are not checked against the scale. The scale is the
  module's, so the README should define it.
- **`pmid`** is redundancy-bearing: the literature pass checks it against PubMed
  (`LiteratureRow.exists`), so take it from a `literature_search` result. Nothing compares `doi`
  against a source; `lint_rows` says so in an `info` line.
- **`trait_efo_id`** is put to OLS4 by `check_identifiers`, together with every other authored
  table's traits; `meta.csv` in its `tables_read` says it was. Find a term with
  `search_trait_terms`.
- **The compiler** stamps `members_key` (the member set, normalized) and writes everything in
  `meta.parquet` and `meta_resolved.parquet` beyond the authored cells: the matches, `replaces`,
  `withheld`, the resolved facts and `tradeoff`. None of it is authored.

**Logging an agent's write.** `record_override` keys on a `variant_key`, and a meta row has none, so
use the table-scope form: `variant_key="meta.csv"`, `field="rows"`, the row's `members` cell and what
changed in `authored_value`, and how you got there in `reason`. Each call is its own record in
`provenance.json`, with that `authored_value` kept, and `review_queue` lists them all;
`logs/authoring.log` keeps every call too and publishes with the module.

## How it relates to variants.csv and studies.csv

- Members are matched against the authored rows **as the table stores them**, after the
  symbolic-allele drop and before resolution. A genotype's alleles are sorted and a diplotype pair is
  stored `haplotype_a <= haplotype_b`, so write members in that spelling.
- **Precedence** (`meta.member_rank`): a member naming a row's full key outranks a bare locus, a locus
  outranks any other selector, and more conditions outrank fewer. A sex- or drug-scoped row outranks
  the unscoped row with the same key, for that scope. Equal ranks are never ordered by anything else.
  When they disagree, the compile **withholds** the column and lists it in `withheld`.
- A combination's facts stay on its own `meta.parquet` row. They never reach a member row by
  themselves; only one-member rows feed `meta_resolved.parquet`.
- A row with a `direction` needs every member to fix an allele (`meta.allele_bearing`). A bare
  `variants[variant_key=…]` locus qualifies only when every row of that locus states the same
  `effect_allele`, which the compile decides from the data.
- `studies.csv` stays required whenever `variants.csv` is present. A meta row's `pmid` is for a claim
  finer than a study row's key; it does not replace the study row.

## What an edit moves

- `meta.csv` is hashed raw into `manifest.inputs`, so **any edit moves `content_signature`**
  (measured by adding a row). It compiles to `meta.parquet` and `meta_resolved.parquet`, which move
  `artifact.digest`, and like any authored file an edit drops a closure.
- **An edit elsewhere can move it without touching it.** Re-spell a genotype or drop a row in a member
  table and a member silently stops matching, so the row's facts leave `meta_resolved.parquet`. After
  any change to a member table, run `validate_module` again.
- `enrich_module` reads `meta.csv` before any network pass and refuses an invalid one there. Its rsID
  currency check also asks dbSNP about every rsID a member names (`enrich.subjects.meta_member_rsids`).
  That catches one variant written under a merged id. It reports and never rewrites.
- There is no fact signature and no sidecar to re-derive. Nothing upstream can drift under this table.

## The symptom when it lies

- **Check width.** `lint_rows` sees one table: the grammar, a row stating nothing, a `direction` on a
  member that fixes no allele, and the closed vocabularies. It returned zero findings for a member
  matching nothing and for a `tier` with no scale (measured). Only `validate_module` and
  `compile_module` see the module.
- **`tier` with no `tier_scale`** is an error in both modes (`compiler.meta.meta_scale_errors` takes
  no strictness). Add `tier_scale:` to `module_spec.yaml`. Do not drop the tiers.
- **`meta_selector_matches_nothing`, `meta_member_drug_disagrees`, `meta_member_allele_ambiguous`**
  are warnings on a green run. Read them in [`SYMPTOMS.md`](../../module-101/references/SYMPTOMS.md).
- **A combination that can never fire still says `replaces`.** The flag is set by member count, so a
  two-member row whose second member matches nothing compiles with `replaces` true (measured). The
  zero shows only in the warning and in `manifest.meta_selectors`, which lists each member with its
  match count. Read that list after every compile of a module carrying this table.
- **A selector broader than you meant** (a `flags` tag, a gene) compiles clean and lands its facts on
  every row it matches. The same `meta_selectors` count is the only place that shows it.
- **Consumers read part of it.** Checked on just-dna-lite's trunk on 2026-11-28: its report joins only
  the unscoped rows, so a sex- or drug-scoped fact does not appear there.

## Ask the live schema

`describe_table("meta.csv")`, `table_requirements("meta.csv")` (read `any_of`: a row must state at
least one finding or fact), `get_template("meta.csv")`, `lint_rows`, `list_tables` (its `keyed_on`
is the key), `describe_spec_file` (`tier_scale`). Symbols worth naming rather than quoting:
`just_dna_format.meta.MetaRow`, `META_MEMBER_TABLES`, `parse_members`, `member_rank`,
`allele_bearing`; `just_dna_compiler.compiler.meta.build_meta`, `meta_scale_errors`.
