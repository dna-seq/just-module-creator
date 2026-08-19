# gene_metrics.csv — what does a reference say about this whole gene

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

`gene_metrics.csv` answers one question per row: *what does one named authority say about this one
gene, at gene level, in this release.* Two authorities answer it and they answer different questions.
gnomAD says how intolerant of variation the gene **looks** in a population sample (pLI, LOEUF,
missense Z); ClinGen says whether an expert panel found evidence that **losing or gaining a copy
causes disease** (haploinsufficiency, triplosensitivity). They are separate rows sharing the gene,
each naming its own `dataset` — never one merged row, "which would put a statistical estimate and a
curated verdict under one provenance" (`enricher/src/just_dna_enricher/clingen.py:1-7`).

It exists because gene-level and variant-level facts get separate tables rather than gene metrics
repeated on every variant row: "a module with forty variants across six genes carries six rows here,
not forty duplicated ones, and the two axes stay independently updatable"
(`schema/src/just_dna_format/gene_metrics.py:8-11`). Its audience is a clinical reader asking "is
this gene the kind of gene where a truncating variant matters" and a consumer that wants that answer
without holding a 95.5 MB constraint TSV. **No annotation table joins to it.** The compiler only
cross-checks it (`compiler.py:5716 _cross_check_gene_metrics`, gene-symbol orphan warning) and checks
its internal arithmetic (`compiler.py:5449 _check_gene_metrics_arithmetic`).

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.gene_metrics.GeneMetricsRow` (`schema/src/just_dna_format/gene_metrics.py:57`) |
| Parquet | `gene_metrics.parquet` — in `ARTIFACT_PARQUETS` (`compiler.py:290`), so inside `artifact.digest` |
| Natural / dedup key | `(gene, dataset)` — both passes merge on it: `existing[(row.gene, row.dataset)]` (`gene_metrics.py:192`, `clingen.py:218`). **Not enforced by the compiler** — see Gotcha 3 |
| Authored or machine-produced | **machine-produced, human-overridable by design.** Standalone `BaseModel`, not an `AuthoredModel`; `extra="forbid"` so a typo'd column is refused, not dropped |
| Who writes it | two passes writing one file: `enricher.gene_metrics.enrich_gene_metrics` (`just-dna-enricher gene-metrics <dir>`) and `enricher.clingen.enrich_dosage_sensitivity` (`just-dna-enricher dosage <dir>`) |
| Fact signature | `integrity.gene_metrics_signature` over `gene_metrics.GENE_METRICS_FACT_FIELDS` — **18 of 21 fields**; `source`/`status`/`fetched_at` excluded → `manifest.gene_metrics.signature` |
| In `content_signature`? | **No.** `content_signature` reads `variants.csv`, `studies.csv` and `_TABLE_KINDS` only (`compiler.py:3868-3872`) |
| In `artifact.digest`? | **Yes**, via its parquet. Also byte-hashed into `manifest.derived[]` — transport only (`compiler.py:342-352`) |
| Manifest block | `manifest.gene_metrics` = `{signature, sources, datasets, row_count, genes}` (`compiler.py:4724 _gene_metrics_block`); absent when the module carries no such sidecar |
| Location | root or `derived/gene_metrics.csv`. Both at once = `layout.SidecarCollision`, an error, never a merge. Both passes route through `licensing.sidecar_path` since enricher 0.6.1 (RM99) |

## Who populates what

- **enricher pass — the gnomAD half.** `enrich_gene_metrics` (pass 3,
  `just-dna-enricher gene-metrics <dir>`, or our `enrich_facts(passes=["gene_metrics"])`) fills
  `gene`, `gene_id`, `transcript`, `mane_select`, `pli`, `loeuf`, `oe_lof`, `oe_lof_lower`, `lof_z`,
  `mis_z`, `syn_z`, `oe_mis`, `obs_lof`, `exp_lof`, `constraint_flags`, `dataset`, `source="gnomad"`,
  `status`, `fetched_at`. Gene set comes from the **`gene` column of `variants.csv`**, deduplicated in
  first-occurrence order (`gene_metrics.py:97 module_genes`) — "the module *saying which genes it is
  about*; querying anything else would be inventing scope the author did not ask for".
- **enricher pass — the ClinGen half.** `enrich_dosage_sensitivity`
  (`just-dna-enricher dosage <dir>`, or `enrich_facts(passes=["dosage"])`) fills only `gene`,
  `haploinsufficiency`, `triplosensitivity`, `dataset="clingen_dosage_<release>"`,
  `source="clingen"`, `status`, `fetched_at`. Same gene set, same file, its own rows.
- **author** — no column is *expected* of a human, and every column *may* be written by one.
  `source` names `gnomad|clingen|manual|reversed` as open vocabulary
  (`gene_metrics.py:155-163`), so `manual` is the declared route for a curator override, and
  MODULE_LIFECYCLE §6.3 lists "curator overrides, if any" as what deleting this file costs. **Read
  Gotcha 3 before writing one** — the merge does not behave the way the key suggests.
- **drafter** — none. `gene_metrics.csv` is **not in `just_dna_compiler.draft.DRAFTABLE`**, so there
  is no `<<REPLACE>>` stub, no `get_template`, and no `draft_from_*` route. This is also why
  `describe_table("gene_metrics.csv")` **refuses** — see *Ask the live schema*.
- **compiler-stamped** — nothing. No column here is `base.stamped_identity_field`, `COMPILER_MANAGED`
  or `reject_compiler_filled`. The compiler reads, warns, and builds the parquet; it never writes a
  cell of this CSV.
- **registry-stamped** — nothing. No column is in `normalize.IDENTITY_AUTHORITY_KEYS`. The registry
  *does* carry the file (`specfiles.FACT_CSVS`, `specfiles.py:99`) and *does* re-parse it through
  `GeneMetricsRow` on `revalidate`/`upgrade` (`services/upgrade.py:166`), which can **trim an unknown
  column lossily** (`trim_unknown_columns`, "**LOSSY** — the dropped cells are gone").
- **nobody, ever** — no permanently-unwritten column; all 21 have a producer.

**Which cells no tool may fill even though it easily could:** *none, and that is a fact about this
table's kind rather than an omission.* No column here appears in `hints.REDUNDANCY_BEARING` or
`hints.ATTESTATION_BEARING` (`compiler/src/just_dna_compiler/hints.py:72,81`) — those maps name
**authored** cells a Class-2 check later cross-examines, and this whole table is the *source side* of
such a comparison, not the authored side. The consequence is the one worth carrying: **nothing here
is independently verified by anything.** `_check_gene_metrics_arithmetic` checks the table against
*itself* (interval containment, `obs/exp == oe_lof`), which catches a column mismap and cannot catch
a wrong release or a wrong gene.

The refusal that *is* live here is a reserved verification check with no emitter:
`vocab.VALID_VERIFICATION_CHECKS` carries `"dosage_sensitivity"` marked **RESERVED**, because
"`enrich_dosage_sensitivity` … records ClinGen's haplo/triplo curation into `gene_metrics.csv` and no
model carries an authored dosage claim to compare it against. The member is for the pass that gains
one" (`vocab.py:712-715`). So a compiled module will never carry a `dosage_sensitivity` record in
`verification.json`, and `reference_examples/hboc_palb2/README.md:59` naming `dosage` as the command
that "answers `dosage_sensitivity`" is the *finding*, not the contract — the vocab comment is the
answer to it.

## What moving this table moves

Measured, not asserted: `reference_examples/hboc_palb2` (one PALB2 row) compiled seven times with
`compile_module(spec, out)`, comparing `content_signature`, `manifest.gene_metrics.signature`,
`manifest.artifact.digest`, the `manifest.derived[]` byte hash, and `manifest.verification.module_hash`.

| An edit here | `content_signature` | `gene_metrics.signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row (a ClinGen dosage row) | **same** `43ad8ac13609` | **moved** `480f01…`→`c1ae3c…` | moved | unchanged, still closed |
| edit a fact cell (`pli`, `loeuf`, a dosage term) | **same** | **moved** `90ddf093d757` | moved | unchanged, still closed |
| edit `constraint_flags` `[]`→blank | **same** | **moved** `96ae7c8f5500` | moved | unchanged, still closed |
| edit provenance only (`fetched_at`, `source`, `status`) | **same** | **same** `480f01260bd1` | **moved** `6876cc…`→`5f219d…` | unchanged, still closed |
| reorder rows | **same** | **same** `c1ae3c3d4877` | **moved** `f974d3…`→`5ed028…` | unchanged |
| delete the file | **same** | block **absent entirely** | moved `e15f5bd73ae1` | unchanged, still closed |
| re-run the producing pass, nothing new | same | same | same (nothing rewritten — merge-not-clobber) | unchanged |
| delete + re-derive, source unchanged | same | same | **moved** (fresh `fetched_at`) | unchanged |
| recompile under a newer toolchain | same | same | may move | unchanged |

`module_hash` was byte-identical (`527abadc2fe6`) across base, the `pli` edit, the `fetched_at` edit
and the delete.

1. **Is this table inside `content_signature`?** No. `content_signature` loads only
   `variants.csv`, `studies.csv` and `_TABLE_KINDS` (`compiler.py:3868`); `_INPUT_FILES`
   (`compiler.py:267`) does not list it. Its identity is instead
   `integrity.gene_metrics_signature(rows)` over `GENE_METRICS_FACT_FIELDS` — 18 fields, with
   `source`, `status` and `fetched_at` deliberately **out**, so "a human-filled and a machine-filled
   table with identical facts hash equal" (`integrity.py:265-272`). `dataset`, `transcript` and
   `mane_select` are deliberately **in**: "a v2.1.1 pLI and a v4.1 pLI are different facts" and "a
   constraint score is a property *of a transcript*" (`gene_metrics.py:30-34`).
2. **Is it inside `artifact.digest`?** Yes — `gene_metrics.parquet` is in `ARTIFACT_PARQUETS`, and the
   tuple's **order is the digest order**, so it must never be re-positioned. This is why a
   provenance-only change no signature sees still moves the digest: the parquet bytes differ. The CSV
   is *additionally* byte-hashed into `manifest.derived[]`, and that hash is **transport only** — "a
   consumer that reads this one as identity will see a reverse→recompile cycle as tampering"
   (`compiler.py:345-347`).
3. **Does an edit here un-close the module?** **No.** The attestation binds
   `compiler.authored_input_entries(spec_dir)` = `newline_normalized_file_entries(_INPUT_FILES)`
   (`compiler.py:386`), and this file is not in that set — "the derived sidecars carry per-run noise
   (`fetched_at`) that would invalidate an attestation on a re-enrichment that changed nothing anyone
   claimed". Measured: `module_hash` unmoved across every edit above, including deleting the file.
   Note the asymmetry an author will trip on anyway — an `authorship:` append to `module_spec.yaml`
   *does* un-close a module while moving no identity at all, because `module_spec.yaml` **is** in
   `_INPUT_FILES`.
4. **Is this table part of the canary?** Yes — it is one of the six fact signatures MODULE_LIFECYCLE
   §5.1 names. Row 3 of that table (`content_signature` same, fact signature **moved**) reads "the
   upstream source said something different this time". This table can produce that reading, and it
   is the only table where it means two things: gnomAD revised a constraint number, **or** the
   ClinGen release rolled and the dosage rating changed. Detecting either **requires
   delete-and-re-derive**, because merge-not-clobber never re-asks about a `(gene, dataset)` already
   present — and deleting is also what discards curator overrides, which is why the refresh operation
   is still open as upstream **RM83**.

## Required to exist

- **Nothing requires this table.** It is optional at every tier. `manifest.gene_metrics` is `None`
  when absent (`_gene_metrics_block` returns `None` on empty), the parquet is skipped, and no
  compile check fails.
- **It requires `variants.csv` to be useful, and silently produces nothing without it.**
  `module_genes()` returns `[]` when `variants.csv` is absent (`gene_metrics.py:99-101`), so a PGx
  module keyed on `haplotypes.csv`/`diplotypes.csv` gets an **empty** gene set — the gene symbols in
  those tables are never read. If you want constraint on a PGx gene, you author the rows by hand.
- **It drags in `sources.csv` / `licensing.csv`.** Both passes call `record_source_terms` /
  `merge_sources_file` on write (`gene_metrics.py:343`, `clingen.py:263`), so a `gnomad` and/or
  `clingen` row appears in the licence ledger at layer `gene_metrics`. The compile licence gate reads
  that file and nothing else, so a hand-written `gene_metrics.csv` with `source=gnomad` and no
  matching ledger row draws a source-coverage warning (`_sources_checks`, `compiler.py:4441`).
  Licence-wise it costs nothing: `GNOMAD_TERMS` and `CLINGEN_TERMS` are both `CC0-1.0`,
  `commercial_use=True`, `redistribution=True`, `share_alike=False` (`licensing.py:161-168,241-253`),
  and `gene_metrics` is not the `annotation` layer, so neither can taint a module.
- **`variants.csv` gene symbols must be current HGNC names or you get nothing.** Both passes match on
  the literal string. Run `check_identifiers` (`gene_symbol_currency`) *before* these passes, not after.

## The columns that carry judgement

- **`dataset`** — the release label, and the only column that makes two rows about one gene readable.
  Inside the fact set on purpose. `gnomad_v4.1_constraint` (snapshot) /
  `gnomad_v2.1.1_constraint` (live API) / `clingen_dosage_<release line>`. Never edit it to
  "tidy up" — you are restating which release answered.
- **`source`** — names the **licensed source**, never the route. `gnomad`, not `gnomad-api`. The route
  distinction lives in `dataset`. Writing a route here made every gene-metrics module warn that a
  source with no recorded terms had contributed (RM33, fixed in 0.5).
- **`loeuf`** — is the source's `oe_lof_upper`, "stored under the name clinical readers actually ask
  for it by". So `loeuf` is the **upper bound**, `oe_lof` is the point estimate, `oe_lof_lower` the
  lower bound. A reader who thinks `loeuf` is the point estimate will read every gene as less
  constrained than gnomAD says. There is no `oe_mis` interval — see *What does not exist*.
- **`mane_select`** — tri-state and load-bearing, not decoration: "the source is per-transcript and
  the row pick must be deterministic". `true` = MANE Select on an ENSG id; `false` = the builder fell
  back to `canonical` on an ENSG id (637 of 18,111 genes in the live v4.1 snapshot); **`None` = never
  established** — which is what the live API route writes whenever gnomAD returns no MANE transcript
  (`bool(mane.get("ensembl_id")) or None`, `gnomad.py:502`). `None` is not `false`.
- **`haploinsufficiency` / `triplosensitivity`** — **terms, never ClinGen's numeric codes**, and a
  deliberate departure from keep-the-source-value-verbatim. The codes look ordinal and are not: `30`
  = autosomal-recessive-phenotype, `40` = dosage-sensitivity-unlikely, so sorting on the raw number
  ranks `40` above `3` — "the exact inversion of the meaning" (`vocab.py:384-398`).
  `vocab.DOSAGE_SENSITIVITY_BY_CODE` is the lossless mapping in both directions. **A blank
  `triplosensitivity` is an absence, not a rating** — ClinGen writes a literal `"Not yet evaluated"`
  for 210 of 1,520 genes and it maps to `None`.
- **`status`** — `resolved | not_found | ambiguous` (`vocab.VALID_RESOLUTION_STATUS`, enforced since
  format 0.6.1 / RM96; before that `status="totally-made-up"` validated). `not_found` is a **fact** —
  the gene was looked up and gnomAD has no constraint, genuinely true for many small or non-coding
  genes. **A gene with no row at all is a different thing**: unchecked. Never read absence as absence.
- **`constraint_flags`** — the source's own caveat list. "A flagged gene's scores are not to be read
  at face value." Read Gotcha 2 before writing any code that tests it.
- **`fetched_at`** — when *this row was last written by a pass*, never when the source published
  anything. ISO-8601 UTC, second resolution, canonicalized on load.

## Gotchas

Ordered by how likely a first-timer is to hit it.

### 1 — Re-running the gene-metrics pass on an already-enriched module **crashes**

`enrich_gene_metrics` binds `reference` only inside `if wanted:` (`gene_metrics.py:206-207`) and then
reads it unconditionally at `gene_metrics.py:255`
(`constraint_routes_consulted = reference is not None or not offline`). `wanted` is empty whenever
**every gene already has a `source`-startswith-`gnomad` row** — i.e. the ordinary idempotent re-run —
or when the module has no `variants.csv`. Reproduced on `reference_examples/hboc_palb2` with enricher
**0.6.4**, both online and offline, through the library *and* through the CLI:

```
$ just-dna-enricher gene-metrics hboc_palb2/ --offline
:255 in enrich_gene_metrics
UnboundLocalError: cannot access local variable 'reference' where it is not associated with a value
```

Cost: the pass documented as "existing rows are authoritative and merged, never clobbered" raises an
undocumented `UnboundLocalError` in exactly the merge case, so a caller's `except
GeneMetricsEnrichmentError` — the type RM101 was built to make reliable — does not catch it. **Genuine
upstream defect, unfiled as far as this dossier's search reached.**

> 🚧 **ROADWORKS — `enrich_gene_metrics` cannot be re-run. Do not put it in a loop.**
> **Current state.** Independently reproduced on a scratch module against enricher 0.6.4, offline:
> `reference` is bound only inside the `if wanted:` branch, so the ordinary idempotent re-run — and
> any module with no `variants.csv` — raises `UnboundLocalError` out of the pass. It is not a
> subclass of `GeneMetricsEnrichmentError`, so the RM101 `except …EnrichmentError` contract does not
> hold for it.
> **Expected state.** A one-line fix (`reference = None` before the branch) plus a test that re-runs
> the pass. Neither has landed, and no `RMn` owned it at the time of this audit.
> **Guard.** Run this pass **once**, on a module that has a `variants.csv`. If you must re-run,
> delete `gene_metrics.csv` first — which costs you every hand-written override in it (see §3, where
> those overrides are broken anyway). Do not wrap the call in `except GeneMetricsEnrichmentError` and
> assume you have covered it; catch `Exception` at that call site until this is fixed.

### 2 — `constraint_flags` has three incompatible encodings, and the snapshot's "empty" is a non-empty string

The field description says the list is "kept verbatim and pipe-joined". Only the **live API** route
does that (`"|".join(sorted(flags)) if flags else None`, `gnomad.py:513`). The **snapshot** route
copies the TSV cell verbatim, and gnomAD writes a JSON array literal there; `[]` is not in
`constraint_build._NULLS` (`constraint_build.py:85`), so it survives as the two-character string
`"[]"`. Measured over the real published v4.1 snapshot (18,111 genes):

> 🚧 **ROADWORKS — two producers, two encodings, and the column is inside the fact signature.**
> **Current state.** Re-confirmed: 17,403 of 18,111 snapshot rows carry the literal string `"[]"`,
> which is truthy, while the live-API route writes a pipe-joined list or `None`. So
> `if row.constraint_flags:` reads ~96% of snapshot rows as *flagged*, and the same gene fetched two
> ways gives two different cells.
> **Expected state.** One encoding, with `[]` normalized to null on the snapshot leg. The obstacle is
> that `constraint_flags` is inside `GENE_METRICS_FACT_FIELDS`, so normalizing it **moves
> `gene_metrics.signature`** for every module already carrying snapshot rows — which is why nobody
> has done it, and why it needs an owner rather than a quick patch.
> **Guard.** Never write `if row.constraint_flags:`. Compare against the two literals — treat `"[]"`,
> `""` and `None` alike as *no flags* — and record which route wrote the row (`source`) before
> drawing any conclusion from the cell.

| value | rows |
|---|---|
| `[]` | 17,403 |
| `["no_exp_lof"]` | 225 |
| `["outlier_mis"]` | 185 |
| `["outlier_mis","outlier_syn"]` | 156 |
| `["outlier_syn"]` | 103 |
| `["no_variants"]` | 9 |
| `NULL` | **0** |

`reference_examples/hboc_palb2/gene_metrics.csv:2` ships `[]` for PALB2, so this is what a real module
carries. Cost: **any consumer writing `if row.constraint_flags:` treats 96.1% of snapshot rows as
flagged**, and a consumer splitting on `|` gets one token containing brackets and quotes. The column
is inside the fact signature, so the two routes hash differently even when the flag content agrees —
measured: blanking `[]` moved `gene_metrics.signature`. **Genuine upstream defect: two producers, one
column, three encodings, and the docstring describes only one of them.**

### 3 — A curator override does not override; it duplicates, silently

The merge key is `(gene, dataset)`, but the *fetch-suppression* key is different:
`done = {row.gene for row in existing.values() if (row.source or "").startswith("gnomad")}`
(`gene_metrics.py:197`). So a hand-written correction with `source="manual"` does not mark the gene
done. Measured on `hboc_palb2` — set `source=manual` and `loeuf=0.95`, re-run the pass, and the file
comes back with **two rows sharing `(PALB2, gnomad_v4.1_constraint)` and contradicting `loeuf`**:

```
PALB2 gnomad_v4.1_constraint manual 0.95
PALB2 gnomad_v4.1_constraint gnomad 0.9
```

`compile_module` on that spec emitted **zero** gene-metrics warnings — fact tables are outside
`_TABLE_DUPE_KEYS`, so nothing checks for a duplicate key here. (Being outside `_TABLE_KINDS` is the
mechanism, not the dividing line: `_TABLE_DUPE_KEYS` covers only five of the nine *authored* table
kinds too — `HaplotypeRow`, `AlleleFunctionRow`, `DiplotypeRow`, `PgsRow`, `PharmVariantRow` — so
"keyed kind ⇒ dupe-checked" does not hold either. `SourceRow` is another one it misses; see
`licensing.md`.)

> 🚧 **ROADWORKS — an honest override duplicates the key, in silence.**
> **Current state.** The fetch-suppression key is a `gnomad`-prefix scan over `source`, while the
> merge key is `(gene, dataset)`. Any override that changes `source` therefore fails to suppress the
> fetch and lands beside the fetched row. `clingen.py`, in a sibling pass, derives its suppression
> set from its merge key and gets this right — so the shape is understood, just not applied here.
> **Expected state.** Suppression derived from the merge key, as the sibling pass does.
> **Guard.** Do not hand-edit `source` on a row you want to keep. To override a value, edit the cell
> and **leave `source` as the fetched one**; to override the provenance too, delete the fetched row
> in the same edit. Then check for duplicate `(gene, dataset)` pairs yourself — nothing else does. The
manifest reports it as ordinary: `{"row_count": 2, "genes": ["PALB2"], "datasets":
["gnomad_v4.1_constraint"], "sources": ["gnomad", "manual"]}`. Cost: a consumer joining on gene gets
two different LOEUFs with no signal which is authoritative, and the curator's intent is unrecorded —
which is precisely the "**nothing records that a row was overridden**" sub-question upstream calls
blocking on **RM83**. **Genuine upstream defect**, and the only safe override today is to edit the
row *in place*, keep `source="gnomad"`, and note the change outside the table.

### 4 — One module can hold two gnomAD releases at once, per gene

The fallback is **per gene**, not per run: `still_missing = [g for g in wanted if g not in
from_snapshot]` (`gene_metrics.py:233`). So a six-gene module where one gene is outside the
18,111-gene snapshot gets five `gnomad_v4.1_constraint` rows and one `gnomad_v2.1.1_constraint` row.
The numbers are not comparable — verified upstream against both routes, BRCA1 is pLI 1.55e-34 /
LOEUF 0.885 / mis_z 2.338 from the bulk v4.1 file versus 5.52e-38 / 0.928 / 1.734 from the live API,
same gene, same MANE transcript (ENRICHER.md:1029-1037; re-measured from the local snapshot:
`1.5474e-34 / 0.885 / 2.3379`). A warning fires naming the count and the label
(`gene_metrics.py:295-301`). **Read `dataset` per row before comparing any two genes in one table.**

**Which route a plain run takes today (2026-08-19, enricher 0.6.4):** the **v4.1 snapshot**.
`resolve_constraint_reference(None)` finds `~/.cache/just-dna-pipelines/gnomad_constraint`, and on a
fresh cache `download.ensure_constraint_snapshot` pulls `just-dna-seq/gnomad_constraint` from
HuggingFace — probed live, HTTP 200, one 866 KB parquet plus `release.json`. The v2.1.1 path is
reached only when HF is unreachable (best-effort, logs *"snapshot provisioning failed … continuing
with the live API, which serves v2.1.1 rather than v4.1"*) or per-gene as above. Note the local
snapshot's `release.json` reports `builder_version: 0.5.0`, `built_at: 2026-08-03`,
`unresolved_count: 93` — the published snapshot is a **build artifact with its own age**, and nothing
in the module records which build answered.

### 5 — `missing` is three states collapsed into one, and our tool surface loses the third

`GeneMetricsResult` distinguishes `missing` (gnomAD was asked and has no constraint — a real fact) from
`unconsulted` (RM98: no snapshot present *and* the API gated off, so **no route was consulted and no
row is written**). `unconsulted ⊆ missing` by construction, because `strict` must still refuse a run
that established nothing. **Our `enrich_facts` reports `covered` and `missing` and never
`unconsulted`** — `grep -rn unconsulted src/just_module_creator/` returns nothing. So an agent reading
our report cannot tell "gnomAD has no constraint for this gene" from "nothing was asked". The pass
itself warns in both modes: *"their absence from gene_metrics.csv means unchecked, never 'gnomAD has
no constraint for this gene'"* — that text arrives only in `warnings`. **A gap in this plugin, not
upstream.**

### 6 — Strict mode refuses on a fact that is usually correct

`mode="strict"` raises `GeneMetricsEnrichmentError` if any module gene has no gnomAD constraint, and
`enrich_dosage_sensitivity` raises `ClinGenError` if any gene is absent from the curation list —
which curates **1,520 genes by design** against ~19,000 protein-coding genes. Both error messages say
so and recommend `best_effort`. Do not reach for `strict` on this pass by analogy with the others.

### 7 — `dosage` is live-only and a no-op offline, and ClinGen's file shape breaks a naive reader

There is no ClinGen snapshot and deliberately none (upstream's RM38 family). `--offline` makes
`enrich_dosage_sensitivity` a **no-op with a warning**, reported as `ClinGenResult.skipped_offline=True`
— not a failure and not "no curation found"; an injected `curation_text=` still wins, because that is
not egress. Consequence: an offline module gets its gnomAD rows and **no dosage rows at all**, which is
exactly what `reference_examples/hboc_palb2/gene_metrics.csv` shows — one gnomAD row, both dosage
columns blank, no ClinGen row, on a module whose README documents running the full chain.

If you ever parse that TSV yourself instead, `clingen.py:12-28` lists the three shapes that will break
you: six `#` comment lines the last of which *is* the header (`#Gene Symbol…`), a literal
`"Not yet evaluated"` making `int(cell)` crash on one file in seven, and the non-ordinal codes.
`decode_rating` **logs and leaves unset** any code the mapping does not know, "because guessing at it
would be worse than recording nothing".

### 8 — The arithmetic checks are warnings, and they check the table against itself

`_check_gene_metrics_arithmetic` verifies `oe_lof_lower ≤ oe_lof ≤ loeuf` and
`obs_lof / exp_lof == oe_lof` (tolerance `1e-4`). Warnings, never errors, "because every value here is
a float that has been through a CSV, and a constraint score is advisory to begin with". They catch a
column mismap or a point estimate and bounds taken from different releases. They cannot catch a wrong
gene, a wrong release, or a stale snapshot — nothing can, since no independent authority is consulted.

### 9 — `_cross_check_gene_metrics` is a one-way orphan check

It warns when a gene-metrics row names a gene `variants.csv` never mentions. **There is no check in
the other direction** — a module gene with no gene-metrics row draws nothing. Silence here means
nothing was measured.

## What does not exist

- **No `describe_table` / `table_requirements` / `get_template` / draft route.** `gene_metrics.csv` is
  absent from `draft.DRAFTABLE` and `hints.describe_table` raises `DraftError`. Verified against the
  live plugin: `describe_table("gene_metrics.csv")` → *"Unknown table kind 'gene_metrics.csv'.
  Authorable kinds: …"*, and the **thirteen** names it lists do not include it. (That wording is this
  plugin's MCP wrapper. The library call underneath raises a `DraftError` with different wording —
  *"'gene_metrics.csv' is not an authored table of this format. Known: [...]"* — over the same
  thirteen kinds. `frequencies.md` quotes the library form; both are right for the surface each
  names.) It appears in `list_tables()` only under `sidecars`. Use
  `authoring_reference` instead — see below.
- **No missense confidence interval.** `oe_lof`/`oe_lof_lower`/`loeuf` carry the LoF interval;
  `oe_mis` has neither bound. Deliberate scope, not an oversight.
- **No `lof_hc_lc.*` or `mis_pphen.*` columns.** "refinements of the same two axes, and carrying all
  55 columns would trade the small-snapshot property for data nobody asked for"
  (`constraint_build.py:62-64`).
- **No numeric dosage-code column.** Refused with a reason: the codes lie about their own order, and
  the mapping is lossless in both directions, so nothing is destroyed by carrying the term. Do not
  propose adding one; `vocab.DOSAGE_SENSITIVITY_BY_CODE` is the reverse route.
- **No ClinGen region-level or recurrent-CNV data.** ClinGen's FTP publishes gene-curation,
  region-curation, dosage and recurrent-CNV lists (probed 2026-08-03, ENRICHER.md:1915); this pass
  reads the **gene**-curation list only, because the table's grain is a gene.
- **No `dosage_sensitivity` verification record, ever.** RESERVED with no emitter, by decision, until
  some model carries an authored dosage claim to compare against.
- **No `has_gene_metrics` registry facet** — see below. Four of the six fact tables got one; this is
  not one of them.
- **No refresh operation.** RM83, open: "merge-not-clobber means the only refresh is `rm`", and the
  blocking sub-question is that nothing records that a row was overridden.
- **No duplicate-key enforcement.** `(gene, dataset)` is the merge key of two passes and nothing else.
- **No gene set from anything but `variants.csv`.**

## Consumption today

**Nobody reads a single column of this table. Not one consumer, anywhere.** That is the finding.

- `just-dna-lite/webui/src/webui/state.py:6007` — `_ARTIFACT_FILES = tuple(ARTIFACT_PARQUETS)`, so
  `gene_metrics.parquet` is one of sixteen names in a digest computation. Opaque; never opened.
- `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/v1_port/publish.py:39` —
  `_ALLOW_PATTERNS = [*ARTIFACT_PARQUETS, …]`, so the parquet is *uploaded*. Opaque.
- `just-dna-lite/.../annotation/hf_modules.py:206-243` — module discovery builds URLs for the lead
  table, `annotations.parquet`, `studies.parquet`, `sources.parquet`, logo and metadata. **`gene_metrics.parquet`
  is not even fetched.** The annotation report path (`annotation/report_logic.py:419,487`) reads
  `annotations.parquet` only.
- `just-dna-registry/src/just_dna_registry/specfiles.py:99` — `gene_metrics.csv` is in `FACT_CSVS`, so
  `revalidate`/`upgrade` carry it forward instead of dropping it. Structural, not interpretive.
- `just-dna-registry/src/just_dna_registry/services/upgrade.py:166` — parsed through `GeneMetricsRow`
  to find columns a newer model would reject, and to `trim_unknown_columns` (lossy) if asked.
- `just-dna-registry/src/just_dna_registry/services/enrich.py:1463 _pgx_leg_clingen` — the registry
  **runs the dosage pass** server-side under `?pgx=true`, with `write=False`, and keeps only
  `missing` / `unreachable` / `skipped` / the source row. **It discards every rating it computed.**
- `just-dna-registry/src/just_dna_registry/services/enrich.py:62-72` — explicit: `constraint` was in
  `RESOLUTION_REFERENCES` until "it was noticed that **no registry pass reads it**"; it now sits alone
  in `METRICS_REFERENCES`, pullable by `warm-caches`, gating nothing.
- `just-dna-registry/src/just_dna_registry/db/facets.py:209-212` — the 0.6 fact-table facets are
  `has_gene_validity`, `has_clinical_assertions`, `has_gwas_effects`, `has_frequencies`. **No
  `has_gene_metrics`** (`grep` across `src/` and `docs/` returns nothing), so no `?has_gene_metrics=`
  query exists on `/modules`, in `RegistryClient.search`, or in our `registry_search`.
- `just-dna-registry/src/just_dna_registry/db/repository.py:663` — `version_genes` is populated from
  `manifest.stats.genes`, **not** from `manifest.gene_metrics.genes`, so the gene facet gains nothing
  from this table.
- `just-prs`, `just-prs-mcp` — zero hits for `gene_metrics`, `loeuf`, `haploinsufficien`,
  `triplosensitiv`.
- `just-dna-marketplace` is a byte-identical copy of `just-dna-registry` for these files
  (`diff -q db/facets.py` → identical), so every registry citation above applies once, not twice.

Net: this table is written, hashed, digested, published, mirrored, re-validated and carried across
upgrades — and read by nothing. A pLI of 1e-19 has never reached a human reading a report.

## Blanks for just-dna-lite

- **Surface pLI / LOEUF / `constraint_flags` on the annotated variant, gene-level.** Nothing fetches
  `gene_metrics.parquet` today (`hf_modules.py:206-243` builds four URLs and this is not one), so a
  report cannot say "this truncating variant sits in a gene with LOEUF 0.64 and pLI ≈ 0" even when the
  module ships exactly that. **Ask:** add `gene_metrics.parquet` to the discovered set, join on `gene`,
  and render the LoF interval as an interval (`oe_lof_lower ≤ oe_lof ≤ loeuf`) rather than one number.
  What breaks today: a consumer has to infer gene-level constraint from nothing, or hold the 95.5 MB
  TSV itself.
- **Render the ClinGen dosage rating as a term, and never sort it.** `haploinsufficiency` /
  `triplosensitivity` are the module's only curated gene-level verdict, and the codes behind them are
  non-ordinal by measurement (`40` > `3` numerically, the reverse in meaning). **Ask:** display the
  six `vocab.VALID_DOSAGE_SENSITIVITY` terms with a blank rendered as *"not evaluated"*, never as
  "no evidence". What breaks today: the registry *computes* these ratings server-side under
  `?pgx=true` (`services/enrich.py:1470`, `write=False`) and throws them away, so the one place they
  are already derived is also where they are discarded.
- **Read `dataset` per row before comparing two genes, and show it.** One table legitimately holds
  `gnomad_v4.1_constraint` and `gnomad_v2.1.1_constraint` rows for different genes, whose pLI differ
  by orders of magnitude for the same gene (BRCA1: 1.55e-34 vs 5.52e-38). **Ask:** key any UI on
  `(gene, dataset)` and label the release; refuse to rank genes across differing `dataset` values.
  What breaks today: nothing reads it, so the mixed-release trap is unexercised rather than solved —
  the first consumer to join on `gene` alone will hit it.

Two more asks aimed elsewhere, kept separate because they are not lite's:

- **Registry:** add `has_gene_metrics` beside its four siblings in `_V017_COLUMNS` / `version_facets`,
  so "which modules carry gene constraint or a dosage rating" is answerable. Today four of six fact
  tables are searchable and this is not.
- **Upstream enricher:** Gotchas 1, 2 and 3 above are defects with reproductions attached.

## Ask the live schema

`describe_table` and `table_requirements` **refuse this table** — it is not in `draft.DRAFTABLE`.
Use these instead:

```
# The generated description, including GeneMetricsRow and the dosage vocabulary:
authoring_reference()                    # → models["GeneMetricsRow"], vocabularies["dosage_sensitivity"]
authoring_reference(schemas=true)        # → raw JSON Schema

# Verified: reference._ALL_MODELS contains GeneMetricsRow (since format 0.6.1 / RM96),
# which is what makes the above true and what makes `status` enforced.
```

```python
from just_dna_format.gene_metrics import GeneMetricsRow, GENE_METRICS_FACT_FIELDS
from just_dna_format.vocab import (
    VALID_DOSAGE_SENSITIVITY,       # the six dosage terms
    DOSAGE_SENSITIVITY_BY_CODE,     # ClinGen code → term, lossless both ways
    VALID_RESOLUTION_STATUS,        # resolved | not_found | ambiguous
)
from just_dna_format.integrity import gene_metrics_signature
from just_dna_compiler.compiler import ARTIFACT_PARQUETS, authored_input_entries

GeneMetricsRow.model_fields                     # the current columns — 21 as of format 0.6.1
set(GeneMetricsRow.model_fields) - set(GENE_METRICS_FACT_FIELDS)
# → {'source', 'status', 'fetched_at'} — the provenance columns outside the fact hash
```

For the enricher side: `just_dna_enricher.gnomad.CONSTRAINT_DATASET_LABEL` and
`API_CONSTRAINT_DATASET_LABEL` are the two gnomAD `dataset` labels; the ClinGen label is built at
runtime from the release line in the curation TSV (`clingen.py:221`), so it is not a constant to look
up. Confirm the installed toolchain by symbol, never by a version line:
`hasattr(just_dna_enricher.gene_metrics, "GeneMetricsUnavailable")` (0.6.2+) and
`"unconsulted" in GeneMetricsResult.__dataclass_fields__` (0.6.1+/RM98).

Every value quoted verbatim above is stamped **as of format 0.6.1 / compiler 0.6.1 / enricher 0.6.4 /
registry 0.18.2**, installed and measured 2026-08-19. Ask the tool for the current answer.
