# model_organisms.csv: lifespan evidence from model organisms, about a human gene

> **Written 2026-11-28 against format, compiler and enricher 0.9.0** (`importlib.metadata`, this
> repo's venv). Every column, type, requirement and vocabulary is generated upstream at
> <https://just-dna.life/just-dna-compiler/tables/model_organisms/>, and live in a session from
> `describe_table("model_organisms.csv")` and `table_requirements("model_organisms.csv")`. This file
> keeps what a model cannot state: who decides which cell, what an edit moves, and the symptom when
> the table lies. Where the two disagree, the generated page and the tool are right and this file is
> the bug.

## What it is

One row is one experiment in an animal: which orthologue of a **human** gene was altered, in which
species, by which intervention, in which sex and on which diet, what happened to lifespan, and
whether that direction agrees with the human allele's. Upstream's own example is IGF1R in humans,
`Igf1r` in mouse, `daf-2` in worm.

It exists for evidence that has nowhere else to go. A `studies.csv` row naming the rsID would claim
the mouse study was about the human variant. A `studies.csv` row naming no variant attaches to the
whole module, because `StudyRow` has no `gene`. A `meta.csv` member names a variant, a genotype, a
diplotype or a named allele, never a bare gene, and a mouse genotype is not a human allele.

**Annotation only.** Nothing here reaches a weight, a tier or an effect column. A consumer reads the
rows beside the module's findings and never scores a genome from them. That is why the table is keyed
on the gene and carries no variant, genotype or allele column.

## When a module needs it

When the module's argument leans on animal lifespan work, typically an ageing or longevity module
whose human evidence is thin and whose mechanism was shown in mouse, fly or worm. It is never a lead
table and does not count toward the composition rule: a directory holding `module_spec.yaml` and
`model_organisms.csv` alone is refused with *"module has no recognized table"* (measured). Rows are
written at [`module-curate`](../../module-curate/GUIDE.md), from papers actually read through
[`find-evidence`](../../find-evidence/SKILL.md).

## Who decides which cell

- **Every cell is the author's**, person or agent co-author. No drafter writes this table: nothing in
  the enricher builds a `ModelOrganismRow`, neither upstream CLI has a command that does, and no
  `draft_from_*` tool here touches it. Its place in `draft.DRAFTABLE` means *authored*, which is why
  `get_template`, `scaffold_module`, `lint_rows` and `describe_table` answer for it. The scaffold's
  stub row puts the placeholder in `gene` alone, the one required cell.
- **`gene` is the human HGNC symbol, never the orthologue's.** The orthologue goes in its own column,
  verbatim in that organism's nomenclature. `check_identifiers` puts `gene` to HGNC with every other
  authored table's genes, but only in a module that has a `variants.csv`: without one, the tool here
  answers *not applicable* and asks nothing.
- **`concordance` is a judgement, and empty is an answer.** Empty means unstated: the curator could
  not tell. The vocabulary has no "unclear" member on purpose, so never fill the cell to make the
  column look complete. Comparing the model's direction with the human allele's needs both papers in
  hand. Treat it as a pilot cell when the human direction is itself contested.
- **`lifespan_effect`** is the paper's own words and number, prose that nothing reads as a size.
  **`sex`** here describes the animals measured. It is not `meta.csv`'s `sex`, which scopes a
  statement to a person.
- **`pmid` and `doi` are optional, and an uncited row draws no warning** (GenAge-style entries carry
  no paper). When a row does cite, the literature pass checks the PMID against PubMed, so take it from
  a `literature_search` result. Nothing compares `doi` against a source; `lint_rows` says so.

**Logging an agent's write.** `record_override` keys on a `variant_key`, and this table has none, so
use the table-scope form: `variant_key="model_organisms.csv"`, `field="rows"`, the row's gene,
species and model in `authored_value`, how you got there in `reason`. Measured on `meta.csv`, which
takes the same form: `provenance.json` keeps only the latest record for that pair, while
`logs/authoring.log` keeps every call and publishes with the module.

## How it relates to variants.csv and studies.csv

It joins neither. No member, key or check links a row here to a row there, and the compiler reads
nothing across. Its `gene` is **outside the module's gene scope** by design: `manifest.stats.genes`
leaves it out (measured: a module with HFE in `variants.csv` and IGF1R here published HFE alone), and
the gene-scoped enrichment passes exclude it (`gene_metrics._NOT_THE_MODULES_GENES`). A gene that
appears only here gets no gene facet in the registry, so name it in `README.md` if a reader should
find the module by it. `studies.csv` is still required whenever `variants.csv` is present; this table
neither satisfies nor needs it.

## What an edit moves

- `model_organisms.csv` is hashed raw into `manifest.inputs`, so **any edit moves
  `content_signature`** (measured by adding a row). `model_organisms.parquet` is written only when
  the table has rows, and it moves `artifact.digest`. Like any authored file, an edit drops a closure.
- No fact signature, no sidecar, nothing to re-derive. An edit elsewhere in the module moves nothing
  here, and nothing here moves another table.
- The key is every column except `lifespan_effect` and `concordance`. A male and a female cohort,
  or chow and high-fat, are two rows. Restating one experiment with a second effect is a duplicate
  key, and the compile refuses it.

## The symptom when it lies

Almost none, and that is the point to carry. `validate_module` checks this table for parse errors,
a present-but-empty file and a duplicate key, nothing more (`compiler.validate`, which says so).
No rule reads it.

- **An orthologue symbol in `gene`** is the likely mistake. `check_identifiers` reports a symbol
  HGNC does not approve, but whether a given mouse spelling is caught depends on how HGNC answers it.
  Read the cell; don't rely on the check.
- **A wrong `concordance`** or a misread `lifespan_effect` passes every check there is. Only a
  reviewer reading the paper beside the row finds it.
- **No consumer shows it yet.** Checked on just-dna-lite's trunk on 2026-11-28: nothing reads
  `model_organisms.parquet`. A row that lies costs nothing visible today and becomes wrong output on
  the day a reader is built.

## Ask the live schema

`describe_table("model_organisms.csv")` (the concordance vocabulary with a note per member),
`table_requirements("model_organisms.csv")`, `get_template("model_organisms.csv")`, `lint_rows`,
`list_tables` (its `keyed_on` is the key). Symbols worth naming rather than quoting:
`just_dna_format.model_organisms.ModelOrganismRow`, `VALID_MODEL_ORGANISM_CONCORDANCE`;
`just_dna_compiler.compiler.tables.AUTHORED_NON_KIND_TABLES`.
