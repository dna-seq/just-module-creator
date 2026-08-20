# gene_validity.csv — does variation in this gene cause this disease, and how sure is anyone

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

> **Correction, 2026-08-20 (later than the banner above).** This file says `describe_table`
> refuses this table and quotes that refusal's wording. Both were true when written and are not
> now: **ask `describe_machine_table`**, which answers the live columns of all seven
> machine-produced tables and carries `hand_authored=False` in its own schema. Nothing about
> *you read this, you never hand-finish it* has changed — that signal is now carried by the tool
> split rather than by a refusal.

## What it is

`gene_validity.csv` records one **curated gene–disease assertion** per row: a named body says that
variation in one gene causes one disease under one mode of inheritance, at one strength. It answers
what the two gene-level tables next door cannot — "constraint says how intolerant of variation a gene
*looks*; dosage sensitivity says whether losing a copy causes disease. Neither says whether variation
in this gene causes **this** disease… and it is the claim a clinical module most often rests on
without recording" (`enricher/src/just_dna_enricher/gene_validity.py:3-6`).

Two submitters ship, and they are different kinds of thing. **ClinGen** publishes expert-panel
curations, one per (gene, disease, MOI), each from a named Gene Curation Expert Panel working to a
numbered SOP. **GenCC** publishes an *aggregate* of nineteen submitters — ClinGen among them, plus
Orphanet, PanelApp and several laboratories — where "the same gene–disease pair routinely carries
several submitters at different strengths, and that disagreement is the data"
(`gene_validity.py:10-15`). Its audience is a clinical reader asking "is this gene–disease link
actually established, or did somebody dispute it", and a catalog wanting to index modules by
condition. **No annotation table joins to it.** The compiler only cross-checks that its genes are
genes the module mentions (`compiler.py:5733 _cross_check_gene_validity`, warning-only).

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.gene_validity.GeneValidityRow` (`schema/src/just_dna_format/gene_validity.py:81`) |
| Parquet | `gene_validity.parquet` — in `ARTIFACT_PARQUETS` (`compiler.py:293`), so inside `artifact.digest`. The parquet carries a 16th column, `module`, that the model has not got (`compiler.py:457-462`) |
| Natural / dedup key | `(gene, disease, mode of inheritance, submitter)` (`gene_validity.py:82`). The **merge** key is narrower and different: `assertion_id` when the source published one, else `(gene, disease_id, moi, submitter, dataset)` (`_merge_key`, `enricher/…/gene_validity.py:546-556`). **Not enforced by the compiler** — see Gotcha 2 |
| Authored or machine-produced | **machine-produced, human-overridable.** Standalone `BaseModel`, not an `AuthoredModel`; `extra="forbid"` so a typo'd column is refused, not dropped |
| Who writes it | one pass, `enricher.gene_validity.enrich_gene_validity` — `just-dna-enricher gene-validity <dir> [--source clingen|gencc]` (`enricher/src/just_dna_enricher/cli.py:386-438`) |
| Fact signature | `integrity.gene_validity_signature` over `gene_validity.GENE_VALIDITY_FACT_FIELDS` — **10 of 15 fields**; `source`/`status`/`fetched_at` excluded as provenance, `report_url`/`disease_label` excluded as *descriptive* → `manifest.gene_validity.signature` (`integrity.py:316-328`) |
| In `content_signature`? | **No.** `content_signature` reads `variants.csv`, `studies.csv` and `_TABLE_KINDS` only (`compiler.py:3869-3873`); `_INPUT_FILES` (`compiler.py:267`) does not list it |
| In `artifact.digest`? | **Yes**, via its parquet. Also byte-hashed into `manifest.derived[]` — transport only (`compiler.py:337-347`) |
| Manifest block | `manifest.gene_validity` = `{signature, sources, datasets, row_count, genes, diseases, classifications, submitters}` (`manifest.py:384-433`, built at `compiler.py:4737`); absent when the module carries no such sidecar |
| Location | root or `derived/gene_validity.csv`. Both at once = `layout.SidecarCollision`, an error, never a merge. This pass has always routed through `licensing.sidecar_path` — it is the one three others were fixed *to match* in enricher 0.6.1 (RM99) |
| Source layer | `gene_validity` is a member of `vocab.VALID_SOURCE_LAYERS` (`vocab.py:553-559`) and is **not** `annotation`, so nothing recorded here can taint a module's commercial-use or redistribution verdict (`sources.py:241-260`) |

## Who populates what

- **enricher pass — everything.** `enrich_gene_validity` (`just-dna-enricher gene-validity <dir>
  [--source clingen|gencc]`) fills all fifteen columns. The gene set is the **`gene` column of
  `variants.csv`**, borrowed from `gene_metrics.module_genes` and re-raised as this pass's own error
  type (`gene_validity.py:530-543`). `dataset` is `clingen_gene_validity_<FILE CREATED date>` or
  `gencc_submissions_<latest submitted_run_date>`; `source` is `clingen` or `gencc`; `status` is
  always `"resolved"` on a written row (`gene_validity.py:481`); `fetched_at` is `now_utc_iso()`.
- **drafter — none.** `gene_validity.csv` is **not in `just_dna_compiler.draft.DRAFTABLE`** (verified
  against compiler 0.6.1: the set is the eleven authored kinds plus `sources.csv`/`licensing.csv`),
  so there is no `<<REPLACE>>` stub, no `get_template`, no `draft_from_*` route, and
  `describe_table("gene_validity.csv")` **refuses**. See *Ask the live schema*.
- **author** — no column is *expected* of a human, and every column *may* be written by one.
  `source` is an open vocabulary naming `clingen|gencc|manual|reversed` (`gene_validity.py:190-197`),
  so `manual` is the declared route for a curator override, and MODULE_LIFECYCLE §6.3 counts curator
  overrides as what deleting this file costs. Unlike `gene_metrics.csv`, the override here **works**
  — see Gotcha 5 — but it costs you a licence-ledger warning.
- **compiler-stamped** — nothing in the CSV. No column is `base.stamped_identity_field`,
  `COMPILER_MANAGED` or `reject_compiler_filled`. The compiler reads, warns, and builds the parquet;
  it never writes a cell of this file. It *does* stamp the parquet-only `module` column
  (`compiler.py:457-462`), which is why the parquet has 16 columns and the CSV 15.
- **registry-stamped** — nothing. No column is in `normalize.IDENTITY_AUTHORITY_KEYS`. The registry
  *does* carry the file (`specfiles.FACT_CSVS`, `just-dna-registry/src/just_dna_registry/specfiles.py:102`)
  and *does* re-parse it through `GeneValidityRow` on `revalidate`/`upgrade`
  (`services/upgrade.py:168`), which can **trim an unknown column lossily**
  (`trim_unknown_columns`: "**LOSSY** — the dropped cells are gone").
- **nobody, ever** — no permanently-unwritten column; all fifteen have a producer.

**Which cells no tool may fill even though it easily could:** *none here, and that is a fact about
this table's kind.* No column appears in `hints.REDUNDANCY_BEARING` (14 columns) or
`hints.ATTESTATION_BEARING` (`provenance_quote`, `provenance_regex`) — those name **authored** cells
a later check cross-examines, and this whole table is the *source side* of such a comparison. The
consequence is the one worth carrying: **nothing in this table is independently verified by
anything.** The only compiler check on it is a gene-symbol orphan warning.

The refusal that *is* live here is a **reserved verification-check name this pass must never emit**.
`vocab.VALID_VERIFICATION_CHECKS` carries `"gene_disease_validity"` marked RESERVED, and its comment
says what it is not for: "0.6's `enrich_gene_validity` **records** ClinGen/GenCC verdicts into a
derived table and compares nothing authored, so it does not emit this. The member is for a future
pass that checks an authored gene/phenotype pair" (`vocab.py:708-711`). Upstream re-affirmed it under
RM72: "wiring it to `gene-validity` would report a check where no question was put, which is the
confusion RM45 exists to end" (`docs/ROADMAP_0_7.md:713-718`). So a compiled module will never carry
a `gene_disease_validity` record, and `reference_examples/hboc_palb2/README.md:59` listing it among
twelve "never emitted" names is the *finding*, not a contract to fill in.

## What moving this table moves

Measured, not asserted: `reference_examples/hboc_palb2` (two PALB2 rows) copied into a scratch tree
and compiled ten times with `compile_module(spec, out)` under format/compiler **0.6.1**, comparing
`content_signature`, `manifest.gene_validity.signature`, `manifest.artifact.digest`, the
`manifest.derived[]` byte hash and `manifest.verification.module_hash`.

| An edit here | `content_signature` | `gene_validity.signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row (a GenCC `strong` assertion) | **same** `43ad8ac13609` | **moved** `e7e5d4…`→`b050ff…` | moved `6876cc…`→`21f5ab…` | unchanged, still closed |
| edit a fact cell (`classification` `definitive`→`strong`) | **same** | **moved** `90a21bdad6d9` | moved `8db1664d56ea` | unchanged, still closed |
| edit `dataset` (release label only) | **same** | **moved** `16e5c3713b2b` | moved `21b59498cfb7` | unchanged, still closed |
| edit `disease_label` (prefix it "obsolete ") | **same** | **same** `e7e5d436546b` | **moved** `d359c0ecfee2` | unchanged, still closed |
| edit `report_url` (change host) | **same** | **same** `e7e5d436546b` | **moved** `97fd8977c68d` | unchanged, still closed |
| edit provenance only (`fetched_at`) | **same** | **same** `e7e5d436546b` | **moved** `7e316b8b069c` | unchanged, still closed |
| reorder rows | **same** | **same** `e7e5d436546b` | **moved** `9e2c6a9fdc8f` | unchanged |
| delete the file | **same** | block **absent entirely** | moved `bf8d03aefb26` | unchanged, still closed |
| re-run the pass, same export | same | same | same (nothing rewritten — merge-not-clobber, `enricher/tests/test_gene_validity.py:247`) | unchanged |
| delete + re-derive, source unchanged | same | same | **moved** (fresh `fetched_at`) | unchanged |
| recompile under a newer toolchain | same | same | may move | unchanged |

`module_hash` was byte-identical (`527abadc2fe6`) across every row above, deletion included. The two
rows in bold above are the load-bearing pair: **`disease_label` and `report_url` move the digest and
not the fact hash** — exactly what `GENE_VALIDITY_FACT_FIELDS`' comment promises.

**The round trip is a fixed point, measured.** `compile → reverse_module → compile` on `hboc_palb2`
reproduced `gene_validity.csv` **byte for byte** (`reverse_module` rebuilds it from the parquet via
`_FACT_TABLES` and `layout.sidecar_write_path`, `compiler.py:6106-6110`) and left
`content_signature`, `gene_validity.signature` and `artifact.digest` all identical. That holds
because the enricher's cell writer is deliberately "matching the compiler's reverse writer exactly"
(`enricher/…/gene_validity.py:586-592`). What does **not** survive is the attestation: reverse warns
that the closure cannot be carried and the recompiled manifest has no `verification` block.

1. **Is this table inside `content_signature`?** No. `content_signature` loads only `variants.csv`,
   `studies.csv` and `_TABLE_KINDS`. Its identity is `integrity.gene_validity_signature(rows)` over
   `GENE_VALIDITY_FACT_FIELDS` — ten fields, with `source`/`status`/`fetched_at` out as provenance
   "so a hand-curated and a ClinGen-filled table carrying the same verdicts hash equal", and
   `report_url`/`disease_label` out on a second and different rule: "a column that *locates or
   describes* the assertion is not the assertion" (`gene_validity.py:48-66`). `dataset` and
   `submitter` are deliberately **in** — "a 2024 curation and its 2026 revision are different facts",
   and "'Ambry says Limited' and 'ClinGen says Definitive' are two claims, not one recorded twice".
2. **Is it inside `artifact.digest`?** Yes — `gene_validity.parquet` is in `ARTIFACT_PARQUETS`, and
   that tuple's **order is the digest order**, so it must never be re-positioned. This is why an edit
   to `disease_label`, `report_url` or `fetched_at` — which no signature sees — still moves the
   digest: the parquet bytes differ. The CSV is *additionally* byte-hashed into `manifest.derived[]`,
   and that hash is **transport only** — "a consumer that reads this one as identity will see a
   reverse→recompile cycle as tampering".
3. **Does an edit here un-close the module?** **No.** The attestation binds
   `compiler.authored_input_entries(spec_dir)` = `newline_normalized_file_entries(_INPUT_FILES)`
   (`compiler.py:386`), and this file is not in that set — "the derived sidecars carry per-run noise
   (`fetched_at`) that would invalidate an attestation on a re-enrichment that changed nothing anyone
   claimed". Measured: `module_hash` unmoved across every edit, deletion included. Note the asymmetry
   you will still trip on — an `authorship:` append to `module_spec.yaml` *does* un-close a module
   while moving no identity at all, because `module_spec.yaml` **is** in `_INPUT_FILES`.
4. **Is this table part of the canary?** Yes — `gene_validity` is one of the six fact signatures
   MODULE_LIFECYCLE §5.1 names (`docs/MODULE_LIFECYCLE.md:230,274`). Row 3 of that table
   (`content_signature` same, fact signature **moved**) reads "the upstream source said something
   different this time", and this table can produce it. **But read Gotcha 4 before acting on it: on
   this table row 3 fires on a release refresh even when no verdict changed**, because `dataset`
   carries the release date and is inside the fact set. Detecting drift at all still **requires
   delete-and-re-derive** — merge-not-clobber never re-asks about an `assertion_id` already present —
   and deleting is also what discards curator overrides, which is upstream **RM83**, still open.

## Required to exist

- **Nothing requires this table.** Optional at every tier. `_gene_validity_block` returns `None` on
  empty (`compiler.py:4745`), the parquet is skipped, and no compile check fails. Deleting it from
  `hboc_palb2` produced zero errors and zero warnings.
- **It requires `variants.csv`, and silently produces nothing without it.** The gene set is
  `gene_metrics.module_genes(spec_dir)`, which reads `variants.csv` and returns `[]` when absent. A
  PGx module keyed on `haplotypes.csv`/`diplotypes.csv` gets an **empty** gene set — the gene symbols
  in those tables are never read. Author by hand if you want validity on a PGx gene.
- **It drags in `licensing.csv` / `sources.csv`.** The pass calls `record_source_terms({…},
  "gene_validity", spec_dir)` on every write (`gene_validity.py:521-526`), so a `clingen`/`gencc` row
  appears in the ledger at layer `gene_validity`. Licence-wise it costs nothing: both are `CC0-1.0`,
  `commercial_use=True`, `redistribution=True`, `share_alike=False` (`enricher/…/licensing.py:183-195`),
  and `gene_validity` is not the `annotation` layer, so neither can taint. **GenCC's attribution
  deliberately names the contributing sources as well as the aggregator** — "crediting only the
  aggregator credits nobody who did the work" (`docs/ENRICHER.md:1583-1586`).
- **A hand-written row with an unrecorded `source` draws a compile warning.** Measured: `source=manual`
  on both `hboc_palb2` rows with the `clingen` ledger row dropped gives `"sources.csv has no row for
  1 source(s) the module's fact tables cite: ['manual'] — their terms are unrecorded."` — warning,
  not error.
- **`variants.csv` gene symbols must be current HGNC names or you get nothing.** Both submitters are
  matched on the literal string (`by_gene.get(gene, [])`, `gene_validity.py:461`). Run
  `check_identifiers` (`gene_symbol_currency`) *before* this pass, not after.

## The columns that carry judgement

- **`classification`** — the whole point of the table, and **a fact, never this workspace's
  opinion**. Nine members (`vocab.VALID_GENE_VALIDITY`, `vocab.py:442`), normalized from the
  submitter's own wording at the enricher boundary. **Only four of them are on a ladder**:
  `vocab.ORDERED_GENE_VALIDITY` is `("limited", "moderate", "strong", "definitive")` and deliberately
  holds nothing else (`vocab.py:463`). `disputed` / `refuted` / `no_known_disease_relationship` are
  **the opposite claim, not low rungs** — "putting `refuted` at position zero would read as 'the
  weakest evidence for', which inverts it". `supportive` is an assertion made *off* the ladder
  (GenCC-only, 5,274 of 30,410 submissions on 2026-08-13, mostly Orphanet's).
  `animal_model_only` is ClinGen-only and appeared in **no row** of that release — kept because it is
  a classification ClinGen's own SOP defines and P3 makes its later absence a one-way door.
- **An empty `classification` is an ungraded assertion, not a negative verdict.** "A submitter can
  assert an association without grading it; the cell is then empty… It is not the same as
  `no_known_disease_relationship`, which is a graded verdict *against*" (`gene_validity.py:31-33`).
  Three-valued, and the two "no" states are different: blank = nobody graded it; `refuted` /
  `no_known_disease_relationship` = somebody graded it and said no. Measured: blanking the cell
  passes validate and compile silently.
- **`moi`** — **part of the key, not decoration.** 59 (gene, disease) pairs in the 2026-08-13 ClinGen
  release carry two rows differing only here; `(gene, disease, moi)` has zero collisions
  (`gene_validity.py:19-21`). `undetermined` is a **stated** finding — ClinGen's `UD`, GenCC's
  `Unknown`, an expert panel having looked and not settled it — while an empty cell means the source
  has no such concept (`vocab.py:478-480`).
- **`classification_raw`** — the submitter's verbatim wording, "kept so the mapping stays auditable
  and a term this release does not model is still visible". Same role `clin_sig_raw` plays. **Blank
  `classification` + non-blank `classification_raw` means the release could not interpret the
  wording** — read the pair together, never `classification` alone.
- **`submitter`** — on ClinGen this is the **GCEP**, not the word "ClinGen": "a module reading this
  column wants to know which expert panel ruled, and every row here would otherwise say the same
  word" (`gene_validity.py:293-295`). On GenCC it is the contributing laboratory, and half the row's
  identity.
- **`dataset`** — which release the assertion is from, **inside the fact set** for that reason.
  `clingen_gene_validity_2026-08-13` comes from ClinGen's own `FILE CREATED:` line, the only version
  that file carries; GenCC publishes no release identifier at all, so the label is the latest
  `submitted_run_date` in the export, or `unknown` (`gene_validity.py:319-324`). Never "tidy" it.
- **`disease_id` vs `disease_label`** — the CURIE is the identity, stored **verbatim** ("rewriting one
  across ontologies is a claim this tier cannot make"); the label is descriptive, never a join key,
  and outside the fact hash because "one real export carries **MONDO:0017146** under two labels at
  once", one of them prefixed `obsolete` (`gene_validity.py:58-66`). **Never key or dedup on it.**
- **`assertion_id`** — the source's own stable id, and the *only* thing the merge keys on when
  present. ClinGen publishes it only inside the report URL and it is read from there, never
  synthesised (`_clingen_assertion_id`, `gene_validity.py:303-313`); GenCC's is a uuid.
- **`classification_date` vs `fetched_at`** — when the panel ruled, versus when a pass last wrote the
  row. Both go through `normalize_utc_timestamp` because ClinGen writes `2024-03-14T16:00:00.000Z`
  and GenCC writes `2018-03-30 13:31:56`, and "two spellings of one instant in one column would hash
  as two facts". Only the first is in the fact set.
- **`status`** — `resolved | not_found | ambiguous`. In practice the pass only ever writes `resolved`,
  because **an uncurated gene gets no row at all** — see Gotcha 3.

## Gotchas

Ordered by how likely a first-timer is to hit it.

### 1 — There is no route to this table from the authoring plugin. It is CLI-only

`just_module_creator.tools.passes._FACT_PASSES` is `("frequencies", "gene_metrics", "dosage")`
(`src/just_module_creator/tools/passes.py:93`), so `enrich_facts` cannot run this pass, and
`describe_table` / `table_requirements` / `get_template` / `lint_rows` all refuse the table because
they gate on `draft.DRAFTABLE`. `skills/create-module/references/CLI.md:34` already states the
consequence — `gene-validity` is listed under "**fact tables from ClinGen / ClinVar / GWAS
Catalog**" with an em-dash in the MCP column. Cost: an agent following the taught order has no tool
that produces this table and must shell out to `just-dna-enricher gene-validity <dir>`. Do that;
do not hand-write rows to work around it.

### 2 — An exact duplicate row passes validate and compile with **zero** warnings

Measured on `hboc_palb2`: appending a byte-identical copy of line 2 gave `validate_spec` no errors
and no warnings, `compile_module` no errors and no warnings, `gene_validity.parquet` **three** rows
with two sharing an `assertion_id`, and `manifest.gene_validity` reporting it as ordinary
(`row_count: 3`, `classifications: ["definitive"]`). Fact tables are outside `_TABLE_DUPE_KEYS` —
they are not `_TABLE_KINDS` — so nothing checks for a duplicate key here. Cost: a consumer counting
"how many definitive assertions does this module carry" gets the wrong number, and a hand-edit that
was meant to *correct* a row silently becomes a second contradicting row if you change the
`assertion_id` while doing it.

### 3 — A gene with no row is **unchecked**, not "no association", and `strict` will refuse over it

"A gene the submitter has not curated gets no row", reported in `result.missing`
(`gene_validity.py:406-410`): "a curating body's silence means nobody has assessed the gene yet,
which is not a fact about the gene, and writing a `not_found` row would state one." This is the
opposite of the ClinVar assertions pass, which *does* write an absence, "because ClinVar covers the
genome" (`docs/ENRICHER.md:1574-1577`). Two consequences a first-timer gets backwards: **never read
an absent gene as an absent association**, and **do not reach for `--strict`** — both submitters
curate a subset by design, so the strict refusal names a condition that is usually correct
(`gene_validity.py:509-514`). Also note `covered`/`missing` are counted **per gene**, while the
table's grain is per assertion; a gene with one `refuted` row counts as covered.

### 4 — The canary fires on every release refresh, because `dataset` is inside the fact set

`dataset` carries the release date, and ClinGen mints a new `FILE CREATED:` on every publication
whether or not any verdict moved. Measured: changing only `clingen_gene_validity_2026-08-13` →
`…_2026-09-01` moved `gene_validity.signature` from `e7e5d436546b` to `16e5c3713b2b` with
`content_signature` unchanged — MODULE_LIFECYCLE §5.1 row 3, "the upstream source said something
different this time", on a table where nothing about the world changed. That placement is deliberate
and correct as a *has-this-been-refreshed* signal; it is just not the signal §5.1's prose describes.
**Before concluding a verdict moved, diff `classification` per `assertion_id`, not the signature.**

### 5 — A curator override *works here*, unlike on `gene_metrics.csv` — and costs a licence warning

Measured: write a row, hand-edit `source` to `manual`, re-run the pass with the same export. The file
comes back with **one** row still saying `manual` — the merge keys on `assertion_id`
(`_merge_key`, `gene_validity.py:546-556`), so the ClinGen row is recognised as already present and
is not re-added. This is the opposite of `gene_metrics.csv`, whose fetch-suppression key is
`source`-dependent and duplicates the row. What it costs is the ledger: `record_source_terms` is
called with `{"manual"}`, `licensing.csv` gains nothing, and the compile emits
`"sources.csv has no row for 1 source(s) the module's fact tables cite: ['manual']"`. Add a
`manual` licence row, or accept the warning knowingly.

### 6 — A ClinGen re-curation **adds** a row; nothing marks the superseded one

ClinGen's assertion id embeds the curation timestamp — the two real `hboc_palb2` rows are
`CGGV:assertion_3ebabbf1-…-2019-08-18T160312.829Z` and `CGGV:assertion_b067d463-…-2024-08-29T170000.000Z`
— so an assertion re-curated at a later date carries a *different* id, misses the merge key, and is
appended beside the old one. Measured with two injected exports differing only in the curation date
and the grade (`Definitive` 2019 → `Moderate` 2026, same gene/disease/MOI/submitter/uuid stem): the
file came back with **both**, and `manifest.gene_validity.classifications` would then read
`["definitive", "moderate"]` with nothing saying which is current. `classification_date` and
`dataset` are the only discriminators, and no consumer reads either. **Genuine upstream defect
candidate**, and it is the same shape as the ClinVar drafter's `S45`, which upstream fixed in
enricher 0.6.4 by naming the superseded rows and deleting nothing (`clinvar_draft._superseded_rsid_rows`);
this pass has no equivalent. The enricher's own merge test only re-runs the *identical* export
(`enricher/tests/test_gene_validity.py:247-257`), so it cannot see this.

> 🚧 **ROADWORKS — re-curation duplicates, and the manifest can publish two contradictory grades.**
> **Current state.** Independently reproduced against enricher 0.6.4: a second export of the same
> gene/disease with a later curation date lands as a second row, and
> `manifest.gene_validity.classifications` can carry a pair as far apart as `["definitive",
> "refuted"]` with no currency notion anywhere in the artifact. No warning, in either mode. No `RMn`
> owns this yet.
> **Expected state.** The S45 shape — the newer row wins and the older one is *named* as superseded,
> nothing deleted — applied to this pass. It does not exist.
> **Guard.** Treat `classifications` as a **set of everything ever curated**, not as the module's
> current call. Before publishing, sort this table by `classification_date` per
> `(gene, disease, moi, submitter)` and delete the stale rows by hand; nothing else will. If you keep
> both, say so in the README — no artifact field can.

### 7 — Hand-writing a cell in the source's own spelling is refused

The vocabularies are mapped at the enricher boundary and never stored verbatim, so the file holds
`autosomal_recessive`, not ClinGen's `AR`, and `disputed`, not GenCC's `Disputed Evidence`
(`CLASSIFICATION_BY_WORDING` / `INHERITANCE_BY_WORDING`, `gene_validity.py:79-128`). Measured: `AR`
in `moi` is a **hard error** at both validate and compile, naming the nine legal members; so is
`very-definitive` in `classification`; so is any extra column (`Extra inputs are not permitted`).
A blank `dataset` is also an error, reported as `"Input should be a valid string"` rather than by
the model's own nicer message — the custom validator only fires on a whitespace-only cell, because a
blank CSV cell arrives as `None` against a required `str`.

### 8 — `--offline` is a **no-op with a warning**, never a failure

Neither submitter publishes a snapshot ("ClinGen's file is ~1 MB, GenCC's ~28 MB — small enough to
fetch whole and too incidental to publish a snapshot for", `gene_validity.py:24-26`), so an offline
run returns `GeneValidityResult(rows=[], skipped_offline=True)` and the CLI prints
`skipped: --offline`. An injected `export_text=` still wins, "because handing over bytes you already
hold is not egress". Cost: a pipeline that treats exit 0 as "the table was produced" ships a module
with no `gene_validity.csv` and no error anywhere. Branch on `skipped_offline`.

### 9 — An unmodelled wording costs a **cell**, reported once per run on stderr

A classification or MOI wording the maps do not know, or a curation date that will not parse, leaves
that cell empty and keeps the assertion (`gene_validity.py:176-186`). The report is one aggregated
`logger.warning` naming the distinct values with a count — "not one per row: at 30,410 GenCC
submissions one unknown wording would otherwise print thousands of lines saying one thing"
(`gene_validity.py:491-500`). Cost: on a GenCC run the most important diagnostic is one stderr line
you will scroll past, and nothing in the CSV, manifest or parquet records that it happened;
`classification_raw` is the only surviving trace, and only for classifications.

### 10 — The orphan check is one-way and warning-only

`_cross_check_gene_validity` warns when a row names a gene `variants.csv` never mentions
(`compiler.py:5733-5753`). Measured on `hboc_palb2` with a BRCA1 row added:
`"gene_validity.csv names 1 gene(s) this module never mentions: ['BRCA1']"` — warning, compile
succeeds. **There is no check in the other direction**, and the check is skipped entirely when
`variants.csv` has no rows or no gene cells.

### 11 — Era check: nothing pre-0.6 can carry this table, and nothing does

Verified against the 27 submitted bundles in `/data/sources/just-dna-registry/data/input/*.zip`,
unpacked and inventoried: **27/27** carry `module_spec.yaml` + `variants.csv`, 24 carry
`studies.csv`, and **0** carry `gene_validity.csv` or any validity-shaped column (the three distinct
`variants.csv` headers across all 27 are `rsid,chrom,start,ref,alts,genotype,weight,state,conclusion,[priority,]gene,phenotype,category`
and an rsID-only variant of it). Bucket counts against the ERA NOTE: **era gap 27, live deprecation
0, genuine break 0.** The table landed in format 0.6 (RM24), so a module of that vintage could not
have had it; `just-dna-lite/data/interim/v1_port/*/manifest.json` honestly records
`"gene_validity": null`, and the registry projects that as `has_gene_validity = 0` rather than
"unknown" — deliberately, because "the table did not exist to be omitted"
(`just-dna-registry/src/just_dna_registry/db/facets.py:206-209`).

## What does not exist

- **No `gene_disease_validity` verification record, ever, from this pass.** The vocabulary member
  exists and is RESERVED; wiring it here was proposed and **refused** with a reason (`vocab.py:708-711`,
  `docs/ROADMAP_0_7.md:713-718`). Do not read its absence in `verification.json` as a gap.
- **No HPO route.** `VALID_VALIDITY_SOURCES` is `{clingen, gencc}` and an unknown `--source` refuses
  by name (`gene_validity.py:417-422`). Two reasons, both established by probe: HPO's declared licence
  URL `https://hpo.jax.org/app/license` **answers HTTP 404** with a JavaScript shell and OBO Foundry
  records the licence as a bare label with no SPDX id, so "an unestablished permission is not a
  permission"; and separately `genes_to_phenotype.txt` is a different grain, while
  `genes_to_disease.txt`'s `association_type` (MENDELIAN/POLYGENIC/UNKNOWN, 8,288 of 15,944 rows
  UNKNOWN) is "a **mechanism class, not an evidence grade**" that would overload the axis
  (`gene_validity.py:28-36`, `docs/ENRICHER.md:1588-1599`). **The row shape fits; the link does not.**
- **No integer `classification` and no numeric strength column.** `ORDERED_GENE_VALIDITY` is a
  published tuple instead, on "the ClinGen-dosage reason inverted: those codes look ordered and are
  not, so they had to be decoded; these are ordered, so the order is published rather than left for
  each consumer to hardcode" (`vocab.py:456-462`). Read the tuple; never hardcode a rank. The
  manifest's `classifications` is likewise a sorted **set**, "so this block does not encode a second
  copy of [the ladder] that could drift" (`compiler.py:4740-4743`).
- **No superseded / current flag, and no per-assertion currency.** See Gotcha 6.
- **No duplicate-key check, no per-column check, no arithmetic check.** The compiler's only test of
  this table is the gene-symbol orphan warning.
- **No draft, template, lint or describe route.** Not in `draft.DRAFTABLE`; `hints.describe_table`
  raises `DraftError: 'gene_validity.csv' is not an authored table of this format`.
- **No `--offline` snapshot** and none planned; see Gotcha 8.
- **No deprecated spelling.** `layout.SIDECAR_SPELLINGS` carries only `sources.csv`/`licensing.csv`;
  `sidecar_spellings("gene_validity.csv")` answers `("gene_validity.csv",)`. Root or `derived/`,
  never both.

## Consumption today

**No consumer reads a single cell of this table.** That is the finding.

| Where | What it does |
|---|---|
| `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/v1_port/publish.py:36-39` | derives the upload allowlist from `ARTIFACT_PARQUETS`, so `gene_validity.parquet` is *sent*. A comment, not a read: "0.6 added three (`gene_validity`, `clinical_assertions`, `gwas_effects`) and this list named none of them" |
| `just-dna-lite/just-dna-pipelines/tests/test_format_0_6.py:85-90` | asserts the allowlist covers `gene_validity.parquet` by name. A publish-completeness test; reads no column |
| `just-dna-lite/webui/src/webui/state.py:5997-6007` | imports `ARTIFACT_PARQUETS` so the client-side digest covers `gene_validity.parquet` **as bytes**. Identity only |
| `just-dna-lite/…/annotation/hf_modules.py:36,39-64,206-241` | discovery/download builds URLs for the lead table + `annotations`/`studies`/`sources` only. `MODULE_TABLES` is a four-item list and `ModuleInfo` has **no `gene_validity_url`** — a module installed from HuggingFace may not carry the file locally at all |
| `just-dna-lite/data/interim/v1_port/*/manifest.json:530` | `"gene_validity": null` on the ported v1 modules. An era gap, not a read |
| `just-dna-registry/src/just_dna_registry/specfiles.py:97-105` | `FACT_CSVS` — what `revalidate`/`upgrade` rebuild a spec directory from. Missing here would mean silently dropped on re-publish, "precisely how `licensing.csv` was lost" |
| `…/services/upgrade.py:168` | maps `gene_validity.csv` → `GeneValidityRow` to find and **lossily trim** columns a newer model rejects |
| `…/db/facets.py:209`, `db/schema.py:284`, `db/repository.py:948,1017-1030`, `api/routers/modules.py:87-89`, `client.py:313,340` | one boolean, `has_gene_validity = int(manifest.gene_validity is not None)`, filterable in catalog search and scoped to the module's **current** version. Tri-state as a parameter: omitted ≠ `false` |
| `…/services/catalog.py:170`, `models/api.py:231` | the module card's `FactTablesInfo.gene_validity` — the same boolean, read from the manifest rather than the projected column "so card and filter cannot disagree" |
| `…/services/catalog.py:341-362` | `ModuleDetail` inlines the whole `latest_manifest`, so a client *can* reach `gene_validity.diseases`/`.classifications`/`.submitters` — but there is **no projection for it**, unlike `verification`, `weighting` and `gwas_effects`, which each get one |
| `…/services/enrich.py`, `api/routers/publish.py:440-446` | the `/check` preflight has legs for frequencies, literature, identifiers, ACMG and PGx. **No gene-validity leg**, and publish never runs the pass |
| `just-prs`, `just-prs-mcp` | **nothing.** No match for `gene_validity`, `GeneValidity` or `gene-validity` anywhere in either repo |

So: the registry knows *whether* a module has validity assertions and ships the parquet intact;
nobody reads a `classification`, a `disease_id` or a `submitter` downstream of publication, and the
annotation half of `just-dna-lite` cannot even locate the file.

## Blanks for just-dna-lite

- **Nothing reads `classification`, so a report cannot distinguish a `definitive` gene–disease link
  from a `disputed` one.** This is the sharpest gap in the table, because the two are not points on a
  scale: `ORDERED_GENE_VALIDITY` covers only `limited → definitive`, and `disputed`/`refuted`/
  `no_known_disease_relationship` are the *opposite* claim. What breaks today: a module can carry a
  pathogenic PALB2 call whose gene–disease relationship a GCEP graded `definitive`, and one whose
  relationship somebody `refuted`, and the annotated output renders both identically. **Ask:** join
  the annotation output to `gene_validity.parquet` on `gene` and surface the strongest assertion per
  (gene, disease) plus its submitter and date; sort with `vocab.ORDERED_GENE_VALIDITY` and render the
  three negative members as a *caveat*, never as a low rank.
- **`ModuleInfo` has no `gene_validity_url`, so a consumer cannot read the table even if it wanted
  to.** `MODULE_TABLES = ["annotations", "studies", "weights", "sources"]` (`hf_modules.py:36`) and
  `ModuleInfo` carries five URLs, none a fact sidecar; `get_module_table_url` falls through to a bare
  `f"{info.path}/{table_name}.parquet"` guess. **Ask:** add `gene_validity_url` (with the other five
  fact sidecars) to `ModuleInfo`, gated on `manifest.artifact.files` rather than probed.
- **The registry indexes genes and categories but not diseases, while `manifest.gene_validity.diseases`
  exists precisely to be indexed.** Its own field description says so: "Sorted disease CURIEs asserted
  against, so a catalog can index a module by condition without opening the parquet"
  (`manifest.py:412-418`). There is a `version_genes` table and a `version_categories` table
  (`db/repository.py:1003-1016`) and no `version_diseases`. What breaks today: "find me modules about
  MONDO:0012565" is unanswerable, and `has_gene_validity=true` is the only validity-aware query in the
  API. **Ask:** project `manifest.gene_validity.diseases` into a `version_diseases` index and add a
  `disease=` filter beside `gene=`.
- **`ModuleDetail` projects `verification`, `weighting` and `gwas_effects` and not `gene_validity`,
  so the card surface reduces the richest fact block to one boolean.** `classifications`,
  `submitters` and `diseases` all reach `latest_manifest` and none reaches a typed projection
  (`services/catalog.py:354-362`). **Ask:** add a `GeneValidityInfo` projection carrying
  `classifications`, `submitters`, `diseases` and `datasets`, with the same "read it as a set, not a
  verdict" note the manifest field already carries.
- **Nobody reads `dataset` or `classification_date`, so no consumer can say how old a verdict is —
  and Gotcha 6 means a module may be carrying two verdicts for one assertion.** **Ask:** whatever
  reads a classification must render the curation date beside it and, when two rows share
  `(gene, disease_id, moi, submitter)`, prefer the later `classification_date` and say that it did.
- **`submitter` disagreement is the reason GenCC exists and no reader models it.** A GenCC-sourced
  table legitimately holds `Definitive` from ClinGen and `Limited` from a laboratory for one pair.
  **Ask:** never collapse to one row at read time; show the spread, or show the strongest with a
  count of dissenters. Collapsing is the bare-triple mistake `PharmVariantRow` already paid for.

## Ask the live schema

`describe_machine_table("gene_validity.csv")` answers this file in full, at essentials tier. The
authored-table routes — `describe_table` / `table_requirements` / `get_template` / `lint_rows` —
**decline it**, which is routing rather than an absence —
they gate on `draft.DRAFTABLE`, which holds the authored kinds plus `licensing.csv`/`sources.csv`
only. Verified against format 0.6.1 / compiler 0.6.1:
`hints.describe_table("gene_validity.csv")` raises
`DraftError: 'gene_validity.csv' is not an authored table of this format`. Until that changes, read
the live model directly:

```bash
uv run python -c "
from just_dna_format.gene_validity import GeneValidityRow, GENE_VALIDITY_FACT_FIELDS
from just_dna_format.vocab import (
    VALID_GENE_VALIDITY, ORDERED_GENE_VALIDITY, VALID_INHERITANCE_MODE,
    VALID_RESOLUTION_STATUS, VALID_SOURCE_LAYERS, VALID_VERIFICATION_CHECKS,
)
for n, f in GeneValidityRow.model_fields.items():
    print(f'{n:20} {f.annotation!s:16} required={f.is_required()}  {f.description}')
print('fact fields  :', GENE_VALIDITY_FACT_FIELDS)
print('grades       :', sorted(VALID_GENE_VALIDITY))
print('LADDER only  :', ORDERED_GENE_VALIDITY)
print('off-ladder   :', sorted(set(VALID_GENE_VALIDITY) - set(ORDERED_GENE_VALIDITY)))
print('inheritance  :', sorted(VALID_INHERITANCE_MODE))
print('status       :', sorted(VALID_RESOLUTION_STATUS))
print('source layers:', sorted(VALID_SOURCE_LAYERS))
print('gene_disease_validity is a member (RESERVED):',
      'gene_disease_validity' in VALID_VERIFICATION_CHECKS)
"
```

Related live sources of truth, none of which should be restated from memory:

- `just_dna_enricher.gene_validity.VALID_VALIDITY_SOURCES` — which submitters this tier may read.
- `just_dna_enricher.gene_validity.CLASSIFICATION_BY_WORDING` / `INHERITANCE_BY_WORDING` — the exact
  submitter wordings this release can interpret. A wording absent from these is what leaves a cell
  blank with an aggregated warning.
- `just_dna_enricher.gene_validity.GeneValidityUnavailable` — the RM101 outage subclass. It is a
  **subclass** of `GeneValidityError`, so a narrow-first `except` order is mandatory; parent-first
  makes the outage arm dead code.
- `just_dna_compiler.compiler.ARTIFACT_PARQUETS` — whether `gene_validity.parquet` is still in
  `artifact.digest`, and in what position (position is load-bearing).
- `just_dna_format.integrity.gene_validity_signature(rows)` — recompute the fact hash yourself and
  compare against `manifest.gene_validity.signature` to read the canary (and see Gotcha 4 first).
- `just_dna_format.layout.sidecar_write_path(spec_dir, "gene_validity.csv")` — write to the file you
  read; never join the name onto `spec_dir` by hand.

Verified with: format 0.6.1, compiler 0.6.1, enricher 0.6.4, registry 0.18.2
(`importlib.metadata.version`, 2026-08-19). Every measurement in this file was taken against
`reference_examples/hboc_palb2` and injected ClinGen/GenCC exports compiled in a scratch tree;
nothing was inferred from a changelog.
