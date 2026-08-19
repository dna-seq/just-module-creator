---
name: module-tables
description: >-
  Router for the per-table dossiers, and the module's structure on disk. Which table kind a finding
  belongs in, keyed on grain; the three tables that all read as references and are three different
  levels; what a spec directory, a compiled artifact and a downloaded module each look like; the
  registry's `derived/` layout and what it refuses; and a pointer to the exhaustive dossier for every
  CSV, parquet and sidecar. Triggers: "which table", "where does this go", "table kinds", "what
  columns", "grain", "studies or literature or licensing", "dossier", "what tables exist", "module
  layout", "what does a module look like", "directory layout", "derived folder", "derived/",
  "WHERE-THIS-CAME-FROM", "published.json", "what does a download give me", "flat or split", "which
  files are mine to edit", "sources.csv or licensing.csv".
---

# Which table, what it holds, and where it sits

**Lifecycle stage:** read by every stage.

This skill answers three questions and nothing else: **which table** a finding belongs in, **what the
tree looks like** around it, and **which dossier** to open for the detail. It holds no procedure — that
is the stage skills — and no column lists or vocabularies. For a cell's type, its pick-list or whether
it is required, **ask `describe_table` / `table_requirements`** for an authored table and
**`describe_machine_table`** for a machine-produced one; those answers are generated from the live
pydantic models and cannot drift from what the compiler accepts.

## Reading the dossiers

Each dossier is exhaustive on one table: its model, its natural key, what it becomes in the artifact,
which signatures it moves, who may write each cell, and its symptoms. Two markers appear throughout:

| Marker | Means |
|---|---|
| 🚧 **ROADWORKS** | the surface is broken or unfinished. Always paired with a guard saying what to do instead |
| ⚠️ **CHECK** | the claim's current state is not what the surrounding text would lead you to expect |

Unmarked text either held on re-check or was not reached; coverage is thorough, not exhaustive.

**Audited 2026-08-20** against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, three ways — dossier
versus upstream `docs/` versus the code, **with the code as arbiter**. Roughly 250 `file:line`
citations were spot-checked and near-zero named the wrong symbol, so: **anchor on the symbol name,
never on the line number.** The reasoning held; the line numbers have drifted with the upstream tree.

**Before telling an author to rely on a tool, grep that table's dossier for 🚧.** If there is a guard,
the guard is what you owe them, not the happy path.

**Every count in this file was measured on 2026-08-20** against those versions — 19 parquets, 34
manifest keys, 11 authored table kinds, 8 machine-produced sidecars. A counted claim rots exactly like
a hand-kept list, so where a number matters, re-run the call rather than trusting this line.

## The dossiers

`references/`, non-invokable, read on demand. Twenty-four tables plus the tree they sit in.

**Authored — you write these.** A module carries only the ones it uses.

| Dossier | One row is | Notes |
|---|---|---|
| [`variants.md`](references/variants.md) | one (variant, genotype) pair, plus the prose conclusion | the only table joined directly against a VCF genotype; becomes **two** parquets |
| [`studies.md`](references/studies.md) | the receipt for a claim | required **iff** `variants.csv` is present |
| [`haplotypes.md`](references/haplotypes.md) | one variant belonging to one named allele | a junction table: a two-SNP haplotype is two rows |
| [`allele_function.md`](references/allele_function.md) | what a named star allele *does* | as one expert panel graded it |
| [`diplotypes.md`](references/diplotypes.md) | a **pair** of haplotypes → a phenotype | this is what *in trans* means |
| [`pharm_variants.md`](references/pharm_variants.md) | one variant + one drug + one genotype | the calls can be *opposed* across genotypes |
| [`activity_phenotype.md`](references/activity_phenotype.md) | an activity-score range → a metabolizer phenotype | binning family |
| [`copynumbers.md`](references/copynumbers.md) | a copy-number range → a phenotype | binning family |
| [`repeat_alleles.md`](references/repeat_alleles.md) | a repeat-count range → a phenotype | binning family; a locus with **no coordinate** |
| [`heteroplasmy.md`](references/heteroplasmy.md) | an mtDNA fraction range, in one tissue | binning family; `tissue` is in the key |
| [`pgs.md`](references/pgs.md) | a published polygenic score you point at | plus the envelope it is valid in |
| [`licensing.md`](references/licensing.md) | what one source is, and on what terms | **author or enricher** — see *three levels*, below |

**Machine-produced — you read these, and never hand-finish one.**

| Dossier | Answers | Written by |
|---|---|---|
| [`resolution.md`](references/resolution.md) | rsID ↔ coordinate | enricher. Compiler *input*; gets no parquet |
| [`frequencies.md`](references/frequencies.md) | how common, in whose samples | enricher (gnomAD) |
| [`gene_metrics.md`](references/gene_metrics.md) | what a reference says about the whole gene | enricher (gnomAD constraint, ClinGen dosage) |
| [`literature.md`](references/literature.md) | does each citation check out, on what terms | enricher (PubMed, Europe PMC, Crossref) |
| [`gene_validity.md`](references/gene_validity.md) | does variation in this gene cause this disease | enricher (ClinGen, GenCC) |
| [`clinical_assertions.md`](references/clinical_assertions.md) | the archive's call, **and the review behind it** | enricher (ClinVar) |
| [`gwas_effects.md`](references/gwas_effects.md) | what a study measured, **and on what scale** | enricher (GWAS Catalog) |
| [`verification.md`](references/verification.md) | whether anything was ever *checked*, and the closure | enricher + `close` |

**Ask `describe_machine_table` for these — a different tool, and the split is the point.**
`describe_table` covers the eleven authored kinds plus both spellings of `licensing.csv` and redirects
for the rest; `describe_machine_table` answers the live columns of all seven machine-produced tables.
The separation carries the signal that a shared tool could not: `hand_authored` is `Literal[False]`
here against `Literal[True]` there, so an agent sees which kind of table it is holding **in the schema,
before it calls** — and there is no template, no linter and no requirements answer for these, because
"what is required of you" is not a question about a table you do not write.

*(Until 2026-08-20 `describe_table` simply refused them and this box said so. Upstream shipped
`hints.DERIVED_TABLE_MODELS` the same day and declined to widen their own `describe_table` for the same
reason — the missing piece was the map, not the presentation.)*

**Four properties of that derived family**, each of which has cost somebody a day. `module-refresh`
owns the procedure; these are the properties that make it necessary.

- **Merge, never clobber.** A re-run *adds* to a sidecar and refreshes nothing already recorded, because
  these tables are human-overridable by design. To re-derive one you **delete it first**, and deleting
  discards every hand-curated row along with the stale ones.
- **Write to the file you read.** Two copies of one sidecar is a refusal naming both paths — never a
  merge, never newest-wins.
- **Each is hashed by its *facts*, not its bytes.** A human-filled and a machine-filled table with the
  same facts hash equal, and a provenance column moves no signature. Which is why a moved
  `artifact.digest` beside an unmoved `content_signature` is a meaningful reading rather than a puzzle —
  `module-diff` owns it.
- **They are the tables that may sit under `derived/`**, and the only ones. An authored table has exactly
  one legal name in one legal place.

**The rest of the tree.**

| Dossier | Holds |
|---|---|
| [`module_spec.md`](references/module_spec.md) | the one required file: identity, build, and what the weights mean |
| [`readme.md`](references/readme.md) | the module's prose — and the receipt that is not it |
| [`logo.md`](references/logo.md) | the picture, and the house style it is drawn in |
| [`logs.md`](references/logs.md) | the provenance subtree nobody fills |
| **[`LAYOUT.md`](references/LAYOUT.md)** | **the tree itself**: which names are recognised, what is hoisted, renamed or refused on upload, and what `derived/` actually is |

## Which table — decide on grain, not on subject

**The question is what the row's *subject* is**, not what data you happen to hold. One CSV = one
concern; a module leads with exactly one primary table.

`list_tables` returns this decision table generated from the live models, and it is the authority on
each table's natural key. Use it rather than the tuples any prose gives you.

- **The finding depends on *how much*** — repeat length, copy number, heteroplasmy fraction, activity
  score → a **binning** table. The subject is the measurement and the module supplies the bins. Inclusive
  `[measure_min, measure_max]`, `min == max` for a sharp value, a null bound for open-ended, and
  **always author the `unresolved` sentinel.**
- **Two alleles on one chromosome** → `haplotypes.csv` (same-strand co-location, which needs no
  predicate language). **One on each** → `diplotypes.csv`. Together they express compound heterozygosity
  and its cis counterpart as distinct rows.
- **Drug response splits by subject, not by source.** One variant + one drug → `pharm_variants.csv`. A
  diplotype + a drug → the optional drug columns on `diplotypes.csv`. A haplotype-keyed annotation
  (`*1`) belongs on a diplotype row **even if the source published it beside single-variant rows.**
- **A per-genotype or per-context axis belongs in the key, or the rows collide.** Every one of these was
  learned from a real corpus rejecting itself: `PharmVariantRow.genotype` (ClinPGx publishes per
  genotype and the calls oppose each other — rs4149056/simvastatin is "decreased" for CC/CT and
  "increased" for TT); `phenotype_category` + `annotation_id` (1,199 of 17,380 triples collide without
  them); `DiplotypeRow.clinical_context` (CPIC scopes a recommendation to a setting and the settings
  disagree — draft all of them and let the consumer select); `HeteroplasmyRow.tissue` **and**
  `variant_key` (the same fraction means different things in blood and muscle, and keying on the gene
  alone makes a second real variant in that gene uncompilable).

⚠️ **CHECK — `list_tables` reports a deprecated key for `copynumbers.csv`.** It gives
`(gene, modifier_gene, modifier_cn)`. `modifier_cn` has been **deprecated since format 0.6** in favour of
`modifier_copy_number`, which holds the fractional dosages VCF 4.4 §7.2 allows; both are read, setting
both is an **error**, and the old one is removed at 1.0. Author `modifier_copy_number`.

### Axes that look interchangeable and are not

Never fold these together — each pair is two independent facts.

- `evidence_level` (ClinPGx 1A–4: how well established) vs `recommendation_strength` (CPIC: how firmly
  to act). A provider fills only its own.
- `requires_callable` (a negative must be *proven*) vs `callable_from` (where the proof lives) vs
  `quality_from` / `min_quality` (whether what was seen is good enough to act on). The first two ask
  whether the position was seen; the third asks whether the call is trustworthy.
- `FrequencyRow.population` (an **ancestry** group) vs `DiplotypeRow.clinical_context` (an indication,
  age band, prior treatment or dose). Two unrelated axes; do not reuse the name.
- `acmg_sf` (gene-list membership) vs `actionability` (the gene–condition–intervention category).

## The three that all read as "references", and are three different levels

They stack rather than overlap, and mixing them puts a fact where no check will find it.

| Table | Asks | Grain |
|---|---|---|
| `studies.csv` | *why do I, the curator, believe this row?* | per claim — a variant and a PMID |
| `literature.csv` | *does that citation actually check out, and on what terms?* | per citation, machine-verified |
| `licensing.csv` | *where did the bytes come from, and what may I do with them?* | per `(source, layer)` |

**A paper is not a data source.** And `licensing.csv` is the one fact sidecar a human is *expected* to
write: a source read by hand leaves no `source` cell anywhere for the coverage check to find, no pass
ran, so no pass will write the row — and the compile licence gate reads that file and nothing else.

## Composition — a module is only the tables it uses

`module_spec.yaml` is the only always-present file. At least one recognised table must exist.
`studies.csv` is required **iff** `variants.csv` is present.

| Shape that works | Tables |
|---|---|
| a ClinVar-drafted gene panel, zygosity curated by hand | `variants.csv` + `studies.csv` |
| a two-SNP haplotype needing no predicate language (APOE ε) | `variants.csv` + `studies.csv` |
| cis vs trans as two rows (HFE compound het) | `haplotypes.csv` + `diplotypes.csv` |
| CPIC star alleles, curated by removal | `haplotypes.csv` + `allele_function.csv` + `diplotypes.csv` |
| single-variant drug response (SLCO1B1 / simvastatin) | `pharm_variants.csv` |
| repeat-count bins (HTT) | `repeat_alleles.csv` |
| tissue- and variant-conditional bins with `unresolved` sentinels | `heteroplasmy.csv` |
| a pseudoautosomal panel | `variants.csv` + `studies.csv`, X spelling only |

**Each of those is a whole module.** Seven of the sixteen reference examples carry no `variants.csv` at
all, and six of those carry no `studies.csv` either. Adding an empty `variants.csv` to a PGx module to
make it look complete is the mistake this rule exists to prevent.

🚧 **ROADWORKS — a module with no `variants.csv` cannot be found by gene.** `manifest.stats` is computed
from `variants.csv` **alone**, and the registry's gene index is fed from `stats.genes`. So a star-allele,
copy-number or activity-bin module publishes `gene_count: 0, genes: []` and `registry_search(gene=…)`
misses it — even when every row carries a `gene` cell. Three dossiers reached this independently
(`copynumbers.md`, `diplotypes.md`, `allele_function.md`). **Guard:** do **not** add an empty or
invented `variants.csv` to fix it — that trades a discoverability gap for a dishonest module. Name the
genes in `README.md` and in the module's `display` prose, where a text search will find them, and say
in the readme which genes the module covers.

## What it looks like on disk

Three shapes, and the differences are load-bearing. `LAYOUT.md` carries the full contract.

**1. A spec directory, mid-authoring — what you edit.** Flat. The compiler reads authored and
machine-written tables from **one directory**.

```
my_module/
├── module_spec.yaml         author    ← the one required file
├── variants.csv             author    ┐ the SNP core; studies is required whenever variants exist
├── studies.csv              author    ┘
├── pgs.csv  …               author    ← one file per further table kind you use (nine more)
│
│                                        machine-written sidecars — at the root, or under
├── resolution.csv           enricher    derived/, NEVER BOTH (two copies is a refusal naming both)
├── frequencies.csv  …       enricher  ← and the rest of the derived family: see the dossier table
├── licensing.csv            enricher or author   ← was sources.csv; that spelling reads until 1.0
├── verification.json        enricher + close     ← which checks ran, and the closure
│
├── README.md                author    ← optional, and it becomes the catalog card
├── logo.png                 author    ← optional; often agent-drawn, to a house style
├── provenance.json          author    ← optional, recognised, and nothing here writes or reads it
├── published.json           this plugin ← a LOCAL receipt of a publish. Never uploaded
└── logs/*.log               the pipeline that authored it ← NOT the enricher, which writes none.
                                        Swept up by every compile and published with no opt-out, so
                                        never leave a stray log here: real ones carry system prompts
                                        and local paths. The one subtree whose paths are kept verbatim
```

**2. A compiled artifact — what `compile_module` writes into `out/`.** Never edit it; never hand-write
parquet.

```
out/
├── manifest.json            compiler  ← the content-addressed record; 34 top-level keys
├── weights.parquet          compiler  ┐
├── annotations.parquet      compiler  │ only the parquets with rows are written,
├── studies.parquet          compiler  │ from a fixed set of nineteen names
├── …one per table kind and per sidecar│
├── sources.parquet          compiler  ┘ ← note: `licensing.csv` compiles to `sources.parquet`
├── README.md                compiler  ← COPIED from the spec, and outside artifact.digest
├── logo.png                 compiler  ← COPIED from the spec, and outside artifact.digest
└── logs/*.log               compiler  ← copied if present
```

No CSVs and no `module_spec.yaml` land here: they are hashed **by name** into `manifest.inputs[]` and
`manifest.derived[]` and left where they are. **Because the README and the logo sit outside the digest,
fixing a caveat or swapping an image is a patch rather than a new version** — the registry has amend
endpoints for exactly that.

**3. A downloaded module.** `derived/` is the only place a subdirectory appears in the wild, and it
appears only under `--with-inputs --layout split`:

```
dest/
├── manifest.json                 registry client — written locally after verification
├── weights.parquet …             registry — every file artifact.files[] attests
├── module_spec.yaml              the author's, hash-checked  ┐ these stay at the root:
├── variants.csv                  the author's, hash-checked  │ an authored table has exactly
├── studies.csv                   the author's, hash-checked  │ one legal name in one legal place
├── README.md                     the author's, hash-checked  ┘
└── derived/                      registry client — created only if something lands in it
    ├── resolution.csv            ┐ DERIVED_FILES: the seven fact CSVs under their preferred
    ├── frequencies.csv           │ spelling, plus resolution.csv, plus verification.json
    ├── licensing.csv             │ (that last one joined at registry 0.17)
    ├── verification.json         ┘
    └── WHERE-THIS-CAME-FROM.md   the client's own note — deliberately NOT called README.md, and
                                  never re-uploaded: it would publish our explanation as the author's
```

**`derived/` is a presentation, never a location.** Five consequences, all of which somebody has got
wrong:

- **`manifest.derived[]` names bare filenames** — `resolution.csv`, never `derived/resolution.csv`.
- **The split runs *after* verification.** A tree split before it is a tree that fails to verify.
- **Re-uploading either layout publishes the same module** — the server flattens it back, and hoists a
  recognised file out of *any* subdirectory, not just this one. `logs/` is the sole exception and is
  never touched.
- **Nothing in `derived/` can move `content_signature`**, because the signature's inputs are entirely
  root-level. True by construction, which is why a folder was chosen over an in-file marker.
- **Two paths claiming one root name is a refusal, not a guess**, and so is one sidecar under both of
  its spellings.

## What this skill cannot do

It cannot tell you a column's type, its vocabulary or whether it is required — **ask the tool.** It
cannot tell you what value to *write*: a weight is `module-weights`, a conclusion and a genotype are
`module-curate`, a coordinate is `module-enrich`. It does not hold the procedure for any stage, and it
does not decode a message you got back — that is `create-module` → `references/SYMPTOMS.md`.

And no table here reads a sample. A module never contains a genotype under test or a measured value;
the consumer brings the measurement at query time, and `module-consumer` owns that seam.
