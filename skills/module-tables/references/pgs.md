# pgs.csv — the polygenic scores a module points at, and the envelope they are valid in

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

*Verified against format/compiler **0.6.1**, enricher **0.6.4**, registry **0.18.2** (installed, checked
with `importlib.metadata`). Every column list and vocabulary below is quoted to explain a trap, never as
the source of truth — ask the live schema (last section).*

## What it is

`pgs.csv` answers **"which published polygenic scores does this module curate, and under what
conditions may they be applied?"** It is a *manifest of PGS Catalog accessions*, not a scoring file:
`just-prs` resolves a `PGSxxxxxx` id to a harmonized scoring file itself and scores each id
independently, so per-variant weights in the module would be dead data
(`schema/src/just_dna_format/pgs.py:1-20`). The audience is a scoring consumer, not a genotype
annotator — nothing in this table has a locus, and no VCF row will ever join to it. What the module
adds over a bare list of ids is the **validity envelope**: which superpopulation the score was
validated in, what variant-match floor invalidates a result, and whether the score may be read as an
absolute risk at all.

The three envelope columns are called *one-way-door fields* upstream and were pinned from day one "so
a consumer can refuse or caveat an out-of-ancestry application instead of silently miscalibrating"
(`pgs.py:9-11`). As of today no consumer reads any of them.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.pgs.PgsRow` (`schema/src/just_dna_format/pgs.py:39`), an `AuthoredModel` → `extra="forbid"` |
| Parquet | `pgs.parquet` — registered in `compiler._TABLE_KINDS` (`compiler/src/just_dna_compiler/compiler.py:231`), `ARTIFACT_PARQUETS` (`:278`) and `LEAD_PARQUETS` (`:307`) |
| Natural / dedup key | `(pgs_id, trait_efo_id)` — `_TABLE_DUPE_KEYS[PgsRow]` (`compiler.py:261`). The trait is in the key so a pleiotropic score is not a false duplicate |
| Authored or machine-produced | **Authored.** No drafter, no enricher pass — `grep -ri pgs` over `just-dna-format/enricher/` returns **nothing at all** |
| Who writes it | A human or AI co-author. `scaffold_module`/`stub_template` can emit the header + one `<<REPLACE>>` row and that is the whole machine contribution |
| Fact signature | **None.** `pgs.csv` is not in `compiler._FACT_TABLES` (`compiler.py:322-330`); there is no `PGS_FACT_FIELDS` and no `pgs_signature` in the manifest |
| In `content_signature`? | **Yes** — it is in `_INPUT_FILES` (`compiler.py:270-275`) and `compiler.content_signature` iterates `_TABLE_KINDS` (`compiler.py:3868-3886`) |
| In `artifact.digest`? | **Yes**, via `pgs.parquet` in `ARTIFACT_PARQUETS` |
| Lead table? | Yes — a module may consist of `module_spec.yaml` + `pgs.csv` and nothing else (measured) |

## Who populates what

| Column(s) | Who |
|---|---|
| `pgs_id` | **author.** The only required cell; `stub_template("pgs.csv")` stubs exactly this one (measured). No provider drafts it — `draft.DRAFTABLE` accepts `pgs.csv` (`draft.py:82-87`) but only to produce a blank stub |
| `trait_efo_id` | **author.** Shape-checked as an ontology CURIE by `vocab.validate_trait_ids` (`vocab.py:1065-1076`); existence is never checked |
| `note`, `group` | **author.** Free text. `group` is a module-local grouping label with no vocabulary |
| `training_ancestry`, `training_cohort` | **author.** The validity envelope. The PGS Catalog publishes its own development ancestry (`just-prs` reads it as `score_development_ancestry.parquet`, `prs_catalog.py:67,691`), so this is a *human narrowing* of it, not a copy |
| `match_rate_floor` | **author.** The floor only. The observed per-sample match rate is a measurement and is consumer-side by design (`pgs.py:14-17`) |
| `research_tier` | **author.** `research_only` / `calibrated` |
| `module` (parquet only) | **compiler-stamped.** Not a CSV column; measured as the first column of `pgs.parquet`. Authoring it in the CSV is rejected by `extra="forbid"` |
| `_genome_build` | **loader-injected private attr**, never a column, absent from `model_dump()` so it moves no signature (`base.py:554-574`) |
| registry-stamped | none. `normalize.IDENTITY_AUTHORITY_KEYS` touches `module_spec.yaml` identity, not this table |
| nobody, ever | none — every column is authorable |

**Cells no tool may fill: none.** `describe_table("pgs.csv")` returns `redundancy_bearing: {}` and
`attestation_bearing: []` (run, verbatim). No cell of this table is protected by `hints.REDUNDANCY_BEARING`
or `hints.ATTESTATION_BEARING`, no lookup returns an `applied: false` + `refusal` for it, and **no tool in
this server can resolve a PGS accession at all** — there is no PGS branch in `lookup_identifier` /
`check_identifiers`. So the discipline here is unenforced: nothing stops an agent filling `pgs_id`,
`trait_efo_id` and `training_ancestry` straight out of the Catalog, and nothing later compares them
against it. Write them from the Catalog page you actually read, and say so in `note`.

## What moving this table moves

Measured on a two-row `pgs.csv` compiled repeatedly with `compile_module(..., strict=True)`; hashes
truncated to 12 hex chars.

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row | moves | — (none exists) | moves | un-closes |
| edit an authored cell (`match_rate_floor` blank → `0.8`) | `1e99fe2c2fc4` → `4272a9aa96c0` | — | `0756038d0480` → `c4a290f03e3b` | un-closes (`9de6832d0932…`) |
| edit a provenance-only cell | **n/a — this table has none.** No `fetched_at`, no `source`, no `status` | — | — | — |
| **reorder rows** | `1e99fe2c2fc4` → **`1e99fe2c2fc4`** (unchanged) | — | `0756038d0480` → **`672a5223517a`** (moves) | **un-closes** — measured: `closure=ABSENT` + *"verification.json is stale"* |
| re-run the producing pass | **n/a** — nothing produces it |  |  |  |
| delete the file and re-derive | **impossible** — no derivation exists; deleting it deletes the rows |  |  |  |
| recompile under a newer toolchain | unchanged (reference- and toolchain-independent) | — | may move (parquet bytes) | unchanged (binding is over authored bytes) |

1. **Inside `content_signature`? Yes.** `pgs.csv` is an authored table: it is listed in `_INPUT_FILES`
   and hashed row-by-row as `model_dump(mode="json", exclude_none=True)`, sorted, order-independent.
   There is no fact-field constant for it and nothing is deliberately left out, because there are no
   provenance columns to leave out. Consequence for a published module: **a `pgs_id` edit is a content
   change**, so a registry keyed on `content_signature` treats the corrected module as different
   content — it will not dedup against the version carrying the typo, and the typo'd version stays in
   an immutable catalog.
2. **Inside `artifact.digest`? Yes**, through `pgs.parquet`. Since the parquet is materialized verbatim
   in authored row order, a pure reorder moves the digest while leaving `content_signature` alone —
   that asymmetry is deliberate (`integrity.content_signature`, "deliberately unlike `artifact.digest`,
   which *preserves* authored row order").
3. **Does an edit un-close the module? Yes, always.** `pgs.csv` is inside
   `compiler.authored_input_entries`, so the closure binding follows its bytes — including a reorder
   that changes no value. Newlines are the one exemption: the binding is newline-normalized since RM82,
   so a `\r\n` → `\n` rewrite alone does not un-close. (An `authorship:` append un-closes too, while
   moving no identity at all.)
4. **Part of the §5.1 canary? No.** The canary is *content unmoved + a **fact** signature moved*
   (`docs/MODULE_LIFECYCLE.md:260-300`), and this table publishes no fact signature. Every change to
   `pgs.csv` lands in row 4 of that table — "somebody edited the module". It follows that **upstream
   drift in a PGS score is undetectable from the module**: the Catalog can revise, retract or
   re-harmonize `PGS000135` and nothing in the artifact moves, because there is no sidecar to
   delete-and-re-derive.

## Required to exist

- **Nothing.** `pgs.csv` is optional, and it also satisfies the composition rule on its own: a module
  must carry at least one recognized table, and `pgs.csv` counts (`compiler.py:3604-3607`).
- **It drags in nothing.** No `variants.csv`, no `studies.csv`. The `studies.csv` requirement is scoped
  to `variants.csv` only, and the compiler is explicit about why `pgs.csv` is exempt: *"`PgsRow` carries
  a catalog accession, which is a provenance and not a citation"* (`compiler.py:3609-3617`). There is no
  `_check_binning_grounding` analogue for it, so no warning either.
- **Measured:** a `module_spec.yaml` + `pgs.csv` module passes `validate_spec(strict=True)` and
  `compile_module(strict=True)` with **one** warning, the generic "records no closure" one. No licensing
  ledger, no citation, no source row is asked for.

## The columns that carry judgement

- **`pgs_id`** — the only required cell, and the only one with any structural check: `^PGS\d+$`
  (`pgs.py:33`). It is an *accession*, so it is both the identity and the entire provenance of the row.
- **`training_ancestry`** — closed vocabulary of **1000G superpopulation** codes plus `multi`. This is
  the author's claim about where the score was validated; it is the cell a consumer would refuse an
  out-of-envelope application on.
- **`training_cohort`** — free text, and the only place sub-superpopulation precision can live: a
  Northwest-European-trained score applied to a Finnish or Ashkenazi sample is out of envelope in a way
  `EUR` cannot express (`pgs.py:12-13`). Routinely misread as decoration; it is the honest half.
- **`match_rate_floor`** — `[0,1]`, *the author's floor*, never a measurement. Its meaning is "below
  this, the computed score is invalid". See gotcha 2 for why the metric it names is the weaker of the
  two the consumer actually computes.
- **`research_tier`** — pins **as data** that a PRS is a within-reference Z/percentile and never an
  ancestry-calibrated absolute risk; upstream adds that `|Z| >= 2.5` in a healthy proband is a
  population-stratification signal, not a disease prediction (`pgs.py:18-20`). Nothing enforces it.
- **`trait_efo_id`** — the join to variant modules and to `just-prs`'s trait metadata. Shape-checked
  only.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **A fabricated `pgs_id` validates, lints clean, and compiles strict.** Measured: `PgsRow(pgs_id=…)`
   accepts `PGS999999999` **and `PGS0`**; `lint_rows("pgs.csv", …)` on a row carrying `PGS999999999`
   returns `errors 0, warnings 0, findings []`; `compile_module(strict=True)` succeeds. Nothing in the
   ecosystem resolves a PGS accession — not the enricher (zero references), not this server. **Cost:**
   the error surfaces on the consumer's machine, per sample, as a failed scoring-file resolution inside
   `just-prs`, after the module is in an immutable registry.

   > 🚧 **ROADWORKS — nothing in any tier resolves a `pgs_id`.** 
   > **Current state.** Re-confirmed across all three packages: the only check on the column is the
   > `^PGS\d+$` shape. No enricher pass fetches the PGS Catalog, `check_identifiers` does not look at
   > this table, and `fully_resolved: true` on a `pgs`-only module is structural — `PgsRow` is not a
   > positional kind, so resolution has nothing to resolve and reports success over an empty set.
   > **Expected state.** An existence check would be an enricher pass against the PGS Catalog. None
   > is designed, and the column is not even documented as author-sourced in the maintained schema
   > reference.
   > **Guard.** Take every `pgs_id` from a Catalog page you actually opened, and put the score's name
   > in `note` so a reviewer can tell that you did. Do not read `fully_resolved: true` on such a
   > module as evidence of anything — nothing was checked.
2. **`match_rate_floor` names the metric the reference consumer has concluded is the wrong gate.**
   `just-prs` gates coverage on **weight-mass coverage (C_wt)**, not the count match rate, and says why:
   *"WGS reference-restoration fills absent loci as hom-ref, inflating count match_rate to ~100% for
   every model (destroying its discriminative power) while leaving C_wt honest"*
   (`just-prs/just-prs/src/just_prs/quality.py:121-133`; the same argument at
   `enrich.py:41-56`, "Gating on the count `match_rate` inverts this (F9/F20)"). **Cost:** on a WGS
   sample — which is what just-dna-lite feeds it — a filled `match_rate_floor` passes vacuously, so the
   column protects a chip sample and not a genome. The format has **no** C_wt floor column. Fill
   `match_rate_floor` anyway (it is the only floor that exists), and record the C_wt expectation in
   `note` until a column exists.
3. **Real modules ship it blank on every row, and blank means unknown.** `match_rate_floor` is
   `float | None`; a blank cell is *no floor declared*, never `0.0` and never "any match rate is fine".
   **Cost today is zero and that is the trap** — nothing reads the column, so a blank costs nothing
   until the first consumer honours it, at which point a blank row is indistinguishable from a row whose
   author decided no floor applies. Same three-valued reading for `research_tier`: blank is *not*
   `calibrated` and *not* `research_only`; a consumer must withhold, and the safe withholding is to
   refuse the absolute-risk reading.
4. **Two ancestry vocabularies that share three letters, and merging them is forbidden.**
   `pgs.VALID_TRAINING_ANCESTRY` is 1000G superpopulations (`EUR EAS AFR AMR SAS multi`, uppercase);
   `vocab.RECOMMENDED_ANCESTRY_GROUPS` is gnomAD's population list (`nfe fin asj ami mid remaining …`,
   lowercase) and is used by `frequencies.csv`. `vocab.py:774-778`: *"This is NOT
   `pgs.VALID_TRAINING_ANCESTRY` and must never be merged with it … Two different axes that happen to
   share three letters."* The reference generator keys vocabularies by **name, not field name**, so the
   two cannot silently collapse (`reference.py:166-173`). **Cost:** `EUR` is right here and rejected in
   `frequencies.csv`; `nfe` is right there and rejected here. Multi-valued: `EUR|EAS` splits on
   `vocab.MULTI_SEP`.
5. **A pure row reorder un-closes the module.** Measured: `content_signature` identical, `artifact.digest`
   moved, closure gone, and the compile prints *"verification.json is stale: the attestation was computed
   over different module bytes"*. Sorting `pgs.csv` for tidiness after closing costs the closure and buys
   nothing, since the content identity was already order-independent.
6. **A `pgs`-led module gets an all-zero registry card.** Measured `manifest.stats` on a pgs-only module:
   `variant_count 0, weights_rows 0, study_count 0, gene_count 0, genes [], categories []`. That is not a
   bug in the compile — `variant_stats` reads `variants.csv` and only `variants.csv`
   (`compiler.py:3792-3812`), and `PgsRow` has no gene column to contribute. **Cost:** the registry
   projects `version_genes` / `version_categories` from those lists (`repository.py:663-668`), and
   `search_modules` accepts `gene=` and `category=` but nothing PGS-shaped (`repository.py:933-955`), so
   the module is findable by name, `q` and namespace only. Put the trait and the score names in the
   title, description and `README.md` — that is the only text a catalog search will see.
7. **`fully_resolved: true` over nothing, permanently.** Measured: `fully_resolved: true`,
   `resolution_subjects: 0`, `positional_rows: 0`, `resolution_signature: null`. `PgsRow` declares no
   `chrom`/`start`, so it is not in `_POSITIONAL_TABLE_KINDS` (derived from the models,
   `compiler.py:1147-1151`) and never will resolve anything. The registry projects `fully_resolved` as a
   filterable facet (`db/facets.py:196`). **Cost:** a pgs-only module reads as maximally resolved in
   catalog filters while having resolved nothing — the `int | None` counter rule (`0` is a real answer,
   `None` means nothing counted) is what keeps it honest, and only `resolution_subjects: 0` says so.
8. **`training_ancestry` reads as required in the docs and is optional in the code.** `pgs.py:11-13`
   calls it "the superpopulation(s) the score was validated in (**required floor**)", contrasted with
   "an *optional* free-form `training_cohort`" — but the field is `list[str] | None = Field(default=None)`,
   `table_requirements("pgs.csv")` returns `always: ["pgs_id"]` and nothing else, the scaffold leaves the
   cell blank, and no compiler check mentions the column. Treat it as *required by intent*: a row without
   it declares no envelope at all. (Flagged as a probable upstream doc/code disagreement.)
9. **A comma inside `note` shifts the row, and only two cells will notice.** Measured by accident: writing
   `fabricated, on purpose` unquoted pushed the `group` value into `training_ancestry` and produced
   `pgs.csv line 3 [training_ancestry]: Value error, training_ancestry must be one of ['AFR', 'AMR',
   'EAS', 'EUR', 'SAS', 'multi'], got: 'cad'`. The only structural guards on this row are the two closed
   vocabularies and the `float`; `note`, `group`, `training_cohort` and `trait_efo_id` are free enough
   that a shift landing in them compiles silently. Quote any cell containing a comma.
10. **`research_tier` is a declaration with no enforcement anywhere.** It exists to say "never an
    absolute risk", while `just-prs` ships `absolute_risk.py` and `just-prs-mcp` exposes absolute-risk
    tools, and neither has ever seen a module. **Cost:** an author can set `research_only` and believe a
    guard exists. It is a note to a future consumer, not a switch.
11. **This repo's own skill misdescribes the table.** `skills/create-module/SKILL.md:756-758` lists a
    "`pharm_variants` / `diplotypes` / `pgs` row's `chrom` and `start`" as arriving null. `PgsRow` has no
    `chrom` and no `start`, so there is nothing to arrive null and no rsID to author instead. Ignore that
    sentence for this table.

## What does not exist

- **Authored per-variant weights — RM16, deferred and *held*.** Status line, verbatim: *"deferred —
  **considered for 0.6 on 2026-08-13 and held**"* (`docs/ROADMAP_0_7.md:61-82`). What is deferred is a
  distinct digest-bearing `effect_allele` + `effect_weight` table for scores published only in a paper's
  supplementary material. Two reasons it stays parked: it is **not derivable** (nobody can fetch weights
  that exist only in an appendix), so it is a full-cost authored table; and *"the one thing that would
  validate its shape, a real consumer combining authored weights into a score, does not exist"* —
  fixing the shape now "spends a one-way door on a guess". **What would unpark it: a real consumer.**
  Do not propose inlining weights into `pgs.csv`; that is the shape already rejected.
- **Bins.** A PRS yields a Z/percentile *within a matched reference distribution*, "a shape the format
  does not bin" (`pgs.py:5-8`, RM16). `pgs.csv` is a *declared interface* like `GenePanelSpec`, not a
  `measure → phenotype` binning table, so do not reach for `MeasureBinRow`'s `unresolved` sentinel here.
- **A C_wt / weight-mass-coverage floor.** Only the count-based `match_rate_floor` exists. See gotcha 2.
- **Any existence check on `pgs_id`.** No enricher pass, no lookup tool, no compiler check, and the
  column is not in `REDUNDANCY_BEARING` — so it is not even *documented* as a cell an author must
  source independently.
- **A fact signature, a derived counterpart, or a `fetched_at`.** Nothing about this table is machine
  produced, so the canary cannot fire for it and there is nothing to delete-and-re-derive.
- **A gene, a locus, a genotype, a citation column.** Hence no positional join, no `studies.csv`
  requirement, no gene facet.
- **A worked reference example.** **Zero of the 16 modules in
  `/data/sources/just-dna-format/reference_examples/` carry a `pgs.csv`** — `find … -name pgs.csv`
  returns nothing and no README mentions PGS at all (both run). There is no example to copy and no
  example that records what this table broke. A first one would need: two or more real Catalog
  accessions from a page that was actually read (the design generalized from one score), at least one
  row with a `training_cohort` narrower than its `training_ancestry` so the sub-superpopulation case is
  exercised, `match_rate_floor` filled on every row with the reason in `note`, `research_tier` filled on
  every row, a `licensing.csv` naming the PGS Catalog's terms, a `README.md` (the registry projects it
  onto the card), and a README section stating the measured facts above — all-zero card, vacuous
  `fully_resolved`, and skipped by the lite annotator.

## Consumption today

**Verdict: no consumer reads `pgs.parquet` for its content. Not one.**

- **`just-prs` — nothing.** Grepping the whole repo for `pgs.csv`, `pgs.parquet`, `PgsRow`, `just_dna`,
  `match_rate_floor`, `research_tier`, `training_ancestry` yields only the HuggingFace dataset paths
  `just-dna-seq/pgs-catalog` and `just-dna-seq/prs-percentiles` (e.g. `just-prs/AGENTS.md:73`,
  `docs/DAGSTER.md:60`) — an org name that looks like a hit and is not one. There is no module reader,
  no manifest reader, no just-dna dependency.
- **`just-prs-mcp` — nothing.** Same grep; the only `match_rate` hits are its own computed results.
- **`just-dna-lite` / `just-dna-pipelines` — recognizes the module, then refuses it:**
  - `just-dna-pipelines/src/just_dna_pipelines/module_config.py:491-501` — `LEAD_TABLES` includes
    `"pgs"`, so a directory holding `pgs.parquet` **is** a module for discovery and publishing.
  - `webui/src/webui/state.py:6017,6043-6050` — `_authored_row_count` counts `pgs.csv`'s rows as the
    module's authored height, which is what the registry's enrichment limit is applied against.
  - `webui/src/webui/state.py:6005` — `_ARTIFACT_FILES = tuple(ARTIFACT_PARQUETS)` includes
    `pgs.parquet`, so it is hashed for digest verification. Hashed, never opened.
  - `annotation/hf_logic.py:222-249` — `_lead_join_strategy` classifies by schema and names this table
    in its docstring: *"`diplotypes`, `pgs`, `allele_function` and the binning families carry no
    per-variant key at all"* → `"unsupported"`, reason *"lead table has no populated coordinates and no
    rsid + genotype to fall back on (missing: genotype, rsid)"*. Confirmed against the measured parquet
    schema, which is `module, pgs_id, trait_efo_id, note, group, training_ancestry, training_cohort,
    match_rate_floor, research_tier` — no `rsid`, no `genotype`, no `chrom`.
  - `annotation/hf_logic.py:302-304, 602-605` — `UnsupportedLeadTable` is raised and the module is put
    in `skipped` with its reason; the run continues.
  - `annotation/report_logic.py:1284` — the report globs `*_weights.parquet`, which is never written for
    a skipped module, so a pgs-led module contributes **no report section**.
  - `webui/src/webui/state.py:4115,4653` — `selected_pgs_ids`, the PRS workbench's score selection, is
    populated from the PGS Catalog grid and trait search. Never from a module. The two halves of the app
    that would meet here do not.
- **The registry — stores and column-checks it, projects nothing from it:**
  - `specfiles.py:57-67` — `pgs.csv` is in `TABLE_KIND_CSVS`, so it round-trips through storage and is
    split back beside the spec on download.
  - `services/upgrade.py:160` — `_ROW_MODELS["pgs.csv"] = PgsRow`, so an unknown column is reported
    (or `--trim`med) rather than crashing a re-compile.
  - `db/facets.py:183-221` — `version_facets` projects nothing from this table; there is no
    `has_pgs`, no score count, no trait facet.
  - `db/repository.py:933-955` — `search_modules` has no PGS-shaped filter.
- **This server** — `tools/authoring.py:80` routes the intent ("a published polygenic score") and the
  generic tools (`describe_table`, `table_requirements`, `lint_rows`, `scaffold_module`,
  `validate_module`, `compile_module`) all handle it. No PGS-specific tool exists.

### Can `just-prs` compute a score from a module carrying `pgs.csv` today?

**The score: yes. From the module: no.** `just-prs` computes a PRS from a `pgs_id` plus a normalized
VCF — `just_prs.prs.compute_prs` (`prs.py:571`), `compute_prs_batch` (`prs.py:1272`), and over MCP
`compute_prs` / `compute_prs_batch(pgs_ids=[…])` / `compute_prs_by_trait`
(`just-prs-mcp/src/just_prs_mcp/tools/compute.py:1231,1305,1355`). So every id in a `pgs.csv` is
computable *the moment a human or an agent copies it across*. What does not exist is any code path
from a module to that call. Missing, concretely:

1. **A reader.** Nothing turns `pgs.parquet` into a list of ids. One `pl.read_parquet(...).get_column("pgs_id")`
   is the whole gap, and its absence is why the two halves of just-dna-lite never meet.
2. **The floor wiring, with a units trap in it.** `match_rate_floor ∈ [0,1]` lines up exactly with
   `TraitScoreRow.match_rate` ("Matched / total scoring variants", `just-prs-mcp/src/just_prs_mcp/models.py:244`)
   and with the `min_match_rate` filter that compares against it (`tools/compute.py:601-604`) — but
   **`EnrichedPRSResult.match_rate` is a percentage 0-100** (`just-prs/…/models.py:350`, set from
   `result.match_rate * 100` at `enrich.py:88`) while `PRSResult.match_rate` is a fraction
   (`models.py:234`). A bridge wired to the enriched result compares `0.8` against `80.0` and never
   trips.
3. **The ancestry leg.** `PRSCatalog.assess_ancestry_coherence` (`prs_catalog.py:985-1050`) already asks
   exactly the envelope question — score development ancestry × sample super-population × reference
   panel — and is "advisory only". It reads the Catalog's own development ancestry; the module's
   authored `training_ancestry` / `training_cohort` is not one of its legs.
4. **The tier gate.** Nothing maps `research_tier == "research_only"` onto suppressing the
   absolute-risk block (`just_prs.absolute_risk`).

## Blanks for just-dna-lite

- **Read `pgs.parquet` as a score selection.** A pgs-led module is discovered as a module and then
  skipped as `UnsupportedLeadTable`, so today installing one accomplishes nothing. Ask: feed its
  `pgs_id` column into `selected_pgs_ids` in the PRS workbench instead of routing it through the
  genotype annotator at all. What breaks today: an author can publish a curated score panel and no user
  can act on it — the app can compute every one of those scores and will not, because the ids arrive in
  the wrong half of the process.
- **Honour `match_rate_floor` as a per-score gate — and say which metric you gated on.** Ask: pass the
  module's floor into `min_match_rate`, and where `weight_mass_coverage` is known, gate on C_wt and
  report that the module's declared floor was the count metric. What breaks today: the only
  machine-readable "this result is invalid" statement a module can make is silently discarded, and a
  score computed at 12% coverage is presented beside one at 98%. (The upstream half of this ask is a
  C_wt floor column in the format; do not fabricate one in `note` and call it structured.)
- **Give the envelope a fourth leg and a refusal.** Ask: pass `training_ancestry` + `training_cohort`
  into `assess_ancestry_coherence` as the module's declared envelope, and let
  `research_tier == "research_only"` suppress the absolute-risk estimate rather than caveat it. What
  breaks today: the three columns that exist specifically so a consumer can *refuse* an out-of-ancestry
  application are read by nobody, so the refusal upstream designed cannot happen.
- **Report a pgs-led module instead of dropping it.** Ask: a "scores this module declares" section keyed
  on `group` / `trait_efo_id`, carrying `note`, the envelope and the tier — no genotype join required.
  What breaks today: `generate_longevity_report` globs `*_weights.parquet`, so a skipped module leaves
  no trace in the report, not even a line saying it was skipped and why.
- **Surface the score count somewhere a catalog can see.** Ask (registry-side): a `has_pgs` / score-count
  facet, or `manifest.stats` row counts per table kind. What breaks today: a pgs-only module publishes
  `genes: []`, `categories: []` and every count `0`, so `registry_search` can only find it by name.

## Ask the live schema

```
describe_table("pgs.csv")        # columns, types, both closed vocabularies with their members,
                                 # and redundancy_bearing / attestation_bearing (both empty here)
table_requirements("pgs.csv")    # always / any_of / defaulted / optional — read all four:
                                 # `always` is ["pgs_id"] alone, and `any_of` is []
authoring_reference()            # every model and every vocabulary in one call, keyed by
                                 # VOCABULARY name — which is what keeps training_ancestry
                                 # and the gnomAD population list from collapsing
get_template("pgs.csv")          # the header + one <<REPLACE>> row; only pgs_id is stubbed
lint_rows("pgs.csv", csv_text)   # before writing anything to disk. Read all three levels;
                                 # note that a fabricated PGS id produces zero findings
```

Constants to name rather than quote, when you must point at one:
`just_dna_format.pgs.PGS_ID_PATTERN`, `pgs.VALID_TRAINING_ANCESTRY`, `pgs.VALID_RESEARCH_TIERS`,
`vocab.RECOMMENDED_ANCESTRY_GROUPS` (the one that must **not** be merged with the first),
`vocab.MULTI_SEP`, `compiler._TABLE_KINDS`, `compiler.ARTIFACT_PARQUETS`, `compiler.LEAD_PARQUETS`,
`compiler.authored_input_entries`.
