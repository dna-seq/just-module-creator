# pharm_variants.csv — one variant, one drug, one genotype: a drug-response annotation

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

Reference for an agent about to author, draft or read this table. Every claim below was read out of a
file or measured; measurements say so. Verified against **format / compiler 0.6.1, enricher 0.6.4,
registry 0.18.2** (`importlib.metadata.version`, 2026-08-19).

## What it is

The table answers *"this person carries this genotype at this variant — what does the literature say
about this drug for them?"* It is the single-variant half of pharmacogenomics: a row maps a variant →
a **drug** → a **response** at a PharmGKB/ClinPGx **evidence level** (1A…4). It exists as a distinct
rowtype rather than columns on `VariantRow` because a drug response is a different axis from a risk
weight (`pgx.py:318-323`), and because one CSV = one concern — a drug-response module carries
`pharm_variants.csv` and **no** `variants.csv`. Diplotype-keyed drug response is not this table: it
rides on `DiplotypeRow`'s optional `drug`/`response`/`recommendation_strength`/`clinical_context`
columns. Its readers are a report generator (grouping by drug, ranking by evidence level) and,
increasingly, a VCF annotator joining on position.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.pgx.PharmVariantRow` (subclass of `base.AuthoredModel`) |
| Parquet | `pharm_variants.parquet` — in `compiler._TABLE_KINDS` (`compiler.py:232`) and in `compiler.ARTIFACT_PARQUETS` |
| Dedup key | `(variant_key, drug, genotype, phenotype_category, annotation_id)` — `compiler._TABLE_DUPE_KEYS[PharmVariantRow]`, `compiler.py:262-264`. Also what `draft.natural_key` returns, so an append can never create a row the compiler then rejects |
| Authored or machine | **Authored.** A source provider (`clinpgx_draft`) can write real rows, but a human/AI owns them afterwards |
| Who writes it | the author; `just-dna-enricher draft-clinpgx` (MCP: `draft_from_clinpgx`); the compiler stamps three parquet-only columns |
| Fact signature | **none.** It is an authored table, not a derived sidecar — see *What moving this table moves* |
| In `content_signature`? | **Yes**, its authored cells. The three compiler-stamped columns are not |
| In `artifact.digest`? | **Yes**, as `pharm_variants.parquet` bytes |
| Positional? | **Yes** — one of the three tables in `compiler._POSITIONAL_TABLE_KINDS` (derived: a kind is positional exactly when its model declares both `chrom` and `start`), with `haplotypes.csv` and `heteroplasmy.csv` |

Run `describe_table("pharm_variants.csv")` for the live column list. Do not trust any list in prose.

## Who populates what

| Cell(s) | Who | Notes |
|---|---|---|
| `drug`, `conclusion` | **author** | the only two always-required columns (`draft.authoring_requirements`, measured: `always: ["drug","conclusion"]`) |
| `rsid` **or** `chrom`+`start` | **author** | `REQUIRED_ANY_OF` on the model; `_validate_identification` enforces it. `stub_template` puts `<<REPLACE>>` in `rsid`, `drug`, `conclusion` and leaves the other ten empty (measured) |
| `genotype` | **author**, or **drafter** | ClinPGx publishes per genotype; `clinpgx_draft._authored_genotype` re-spells `CC`→`C/C`, keeps `CTT/CTT` and a bare haploid `A`, and **declines** star alleles and symbolic ones |
| `gene` | **author**, or **drafter with a withhold rule** | `clinpgx_draft._authored_gene`: a `;`-joined ClinPGx cell (`PRSS53;VKORC1`, 396 of 16,087 snapshot rows) is written **only** when `--gene` selects exactly one member; otherwise the cell is left **empty and reported**. Never one row per gene — `gene` is outside the dedup key, so the copies would collide |
| `drug` (multi) | **drafter** | `drugs` is `;`-joined upstream and `drug` is singular, so one annotation becomes one row per drug. Legal because `drug` **is** in the key |
| `phenotype_category` | **author / drafter**, then **model-normalized on load** | vocabulary `vocab.VALID_PHENOTYPE_CATEGORIES`; `vocab.validate_phenotype_categories` accepts ClinPGx's own spellings case-insensitively and rewrites them (`Metabolism/PK` → `metabolism_pk`). Multi-valued via `[,;|]`, re-joined with `;` |
| `annotation_id` | **author / drafter** | ClinPGx's own accession; the tie-break of last resort in the key |
| `evidence_level` | **drafter writes it, and that is the acknowledged tautology** | see the refusals below |
| `response`, `trait_efo_id` | **author** | free-form / ontology CURIE; nothing fills either |
| `chrom`, `start`, `ref` | **author, else compiler-filled** at compile from injected `resolution.csv` (RM43) | `resolution.resolve_positional_rows` fills **only cells the author left empty**, from **exactly one locus or none**, and never expands |
| `alts` | **compiler-filled, and an authored value is REFUSED** | `stamped_identity_field` + `base.reject_compiler_filled`. Data, not identity — `variant_key` is derived without it |
| `variant_key`, `authored_ident` | **compiler-stamped at load**; an authored value is *accepted and overwritten* | `stamped_identity_field`. The distinction from `alts` is deliberate: `reject_compiler_filled` is scoped to `IDENTITY_FIELDS`, so a *stamped* value costs nothing to ignore while a *filled* one does (`base.py:325-341`) |
| registry-stamped | **none.** `normalize.IDENTITY_AUTHORITY_KEYS` (`namespace`, `owner`, `canonical_id`) are `module_spec.yaml` keys, not columns here |
| nobody, ever | none. Every column has at least one writer |

### Cells no tool may fill, and why

`hints.REDUNDANCY_BEARING` ∩ this model's authored fields = **`rsid`, `chrom`, `start`, `ref`,
`evidence_level`**. `hints.ATTESTATION_BEARING` (`provenance_quote`/`provenance_regex`) does **not**
intersect this table — those live on `studies.csv`.

- `chrom` / `start` / `ref` — a lookup could supply all three and deliberately does not. The compile-time
  check `resolution._authored_conflict` compares whatever the author wrote against `resolution.csv`;
  filling from that table would compare it with itself. Measured: `hints.inspect_rows` on the
  reference example emits exactly three `info` findings, on `chrom`, `start` and `ref`.
- `rsid` — checked by `compiler.resolution._verify` and `identifiers.check_rsids`. Not reported on the
  reference example because the author filled it — `_flag_advisory_columns` stays quiet on a column
  that is populated somewhere.
- `evidence_level` — **the one place where the drafter writes a checked cell on purpose**, and the
  package says so: `clinpgx_draft` copies it straight out of the snapshot that `enrich_clinpgx` then
  compares it against ("RM4's tautology, one source over (RM73)",
  `clinpgx_draft.py:427-433`). The mitigation is not a refusal but a **detector**:
  `provenance.stamp_draft_digest` hashes
  `(rsid, chrom, start, ref, drug, genotype, phenotype_category, annotation_id) → (evidence_level)`
  over the raw CSV cells (`provenance.DRAFT_PROJECTIONS["clinpgx"]`). If the release label matches
  *and* the digest is unmoved, the check reports `not_checked="tautology"` and says so in prose. Edit
  one `evidence_level` and the full check runs again. **A skipped check is not a passed check** — read
  `verification.json`'s `pgx_evidence_level` record, which distinguishes `ran` from `skipped` with a
  reason (`clinpgx._attest`).

The normalizations the model applies on load are surfaced but **not** refused, because they have
already happened: `hints._apply_normalizations` reports each as `kind="normalized", applied=True`.
Measured on the reference example: **9 alterations**, all `phenotype_category`.

## What moving this table moves

Measured by compiling `reference_examples/pgx_slco1b1_simvastatin` (copy in a scratch dir) with
compiler 0.6.1, then mutating one thing and recompiling. Baseline:
`content_signature sha256:8173dab7…`, `artifact.digest sha256:2088151e…`,
`positional_rows 9 / positional_rows_placed 9`, `resolution_signature sha256:271a0d3f…`,
`sources.signature sha256:b80c9079…`.

| An edit here | `content_signature` | this table's fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row | **moves** | n/a (authored table has none) | **moves** | **un-closed** — `pharm_variants.csv` is in `compiler._INPUT_FILES` and so in `authored_input_entries` |
| edit an authored cell (`conclusion`) | **moves** (`a910b428…`) | n/a | **moves** (`08966cab…`) | **un-closed** |
| rewrite `Metabolism/PK` as `metabolism_pk` | **unchanged** (`8173dab7…`) | n/a | **unchanged** (`2088151e…`) | **un-closed anyway** |
| clear an `annotation_id` | **moves** (`e91f324f…`) | n/a | **moves** (`1b6da84b…`) | **un-closed** |
| reorder rows | **unchanged** | n/a | **moves** (`0d432bff…`) | **un-closed** |
| a provenance-only edit (`fetched_at`, `source`, `status`) | not applicable — **this table has no provenance columns.** They live in `resolution.csv` / `licensing.csv` | — | those sidecars' bytes; `resolution.csv` gets **no parquet at all** | derived sidecars are outside the binding, so **stays closed** |
| re-run `draft-clinpgx` | moves only if rows were *added* (append-only, never rewrites an existing row) | n/a | same | un-closed iff rows changed |
| delete `resolution.csv` and re-enrich | **unchanged** | `resolution_signature` moves iff the coordinates changed; `fetched_at` moves regardless | **moves** — the fill writes `chrom`/`start`/`ref`/`alts` into this parquet | **stays closed** |
| recompile under a newer toolchain | unchanged | unchanged | **moves** (`compiler_version` is in the reproducibility triple) | stays closed |

Four answers in prose:

1. **Inside `content_signature`?** Yes. `integrity.content_signature` hashes
   `model_dump(mode="json", exclude_none=True)` per row, sorted, per file — so it is order-independent
   and absorbs CSV reformatting *and* the model's own canonicalization. That is why the
   `Metabolism/PK` → `metabolism_pk` rewrite is invisible to it. The three stamped columns are
   `Field(exclude=True)` (`base.stamped_identity_field`), so they reach parquet via direct attribute
   read in `_build_table` and never enter the signature. **`VariantRow.variant_key`/`authored_ident`
   ARE inside it** — a grandfathered asymmetry filed as a 1.0-cleanup candidate, explicitly "not a
   precedent" (`base.py:302-305`, RM43).
2. **Inside `artifact.digest`?** Yes, as `pharm_variants.parquet` in `ARTIFACT_PARQUETS`. The digest
   *preserves* authored row order where `content_signature` sorts, which is why reordering moves one
   and not the other. Anything that changes the bytes moves it, including a coordinate the fill wrote
   that no authored edit touched.
3. **Does an edit un-close the module?** Yes. `compiler.authored_input_entries` binds the bytes of
   `module_spec.yaml`, `variants.csv`, `studies.csv` and all nine table kinds, `\r\n` read as `\n`
   since RM82. Measured: every one of the four mutations above dropped the `verification` block and
   produced *"verification.json is stale: the attestation was computed over different module bytes"*
   plus the no-closure warning — **including the vocabulary rewrite that moved neither identity**.
   An `authorship:` append does the same for the same reason. Re-enrichment does not: derived
   sidecars are outside the binding.
4. **Part of the §5.1 canary?** Not as a producer — it has no fact signature, so it cannot itself
   show *content same + fact moved*. It participates as a **reader**: its coordinates come from
   `resolution.csv`, so an upstream coordinate change gives `content_signature` same,
   `compilation.resolution_signature` **moved**, `artifact.digest` moved — the canary reading, with
   this parquet as the thing that changed. Detecting it needs **delete-and-re-derive**: the enricher's
   resolution merge is authoritative-and-never-overwrite, so a plain re-run never re-asks.

## Required to exist

- A module must carry **at least one** recognized table kind; `pharm_variants.csv` alone satisfies
  that (`compiler.py:3603-3607`).
- **`studies.csv` is not required.** It is required iff `variants.csv` is present. The reason is not
  "PGx tables carry their own evidence" — that comment was corrected: only two of the nine do. The
  real reason is that `StudyRow` can only name a variant, so for a gene-keyed table the requirement
  would be *unsatisfiable* (`compiler.py:3609-3616`, S19/RM47). `studies.csv` **is** accepted in a
  module with no `variants.csv` and does ground a `pharm_variants.csv` row by rsid or coordinate
  (`SCHEMAS.md:53-60`) — so citing your literature is available and unenforced.
- What the table drags in is **licensing**. Every PGx upstream is CC BY-SA *plus* a contractual bar on
  sale, and these rows sit at the `annotation` layer — the one layer that taints
  (`sources.taints_commercial_use`: `commercial_use is False` **and** `layer == "annotation"`).
  Most-restrictive-wins module-wide: **one** tainting row with no `declared_use == "non_commercial"`
  refuses the whole compile (`compiler.py:4832-4849`). Measured on the reference example:
  `manifest.sources.commercial_use=False`, `redistribution=True`,
  `declared_uses=['non_commercial']`, and `license_sha256` pinned to the `LICENSE.txt` inside the
  snapshot archive. The `declared_use` cell is keyed on **data carried by the module**, never a CLI
  flag, so `compile → reverse → compile` stays a fixed point.
- `resolution.csv` is not required but is what makes the table positionally joinable.

## The columns that carry judgement

- **`genotype` is identity, not decoration.** ClinPGx publishes one annotation per genotype and the
  calls can be *opposed*: for rs4149056/simvastatin toxicity, `C/C` is higher myopathy risk and `T/T`
  is lower. Collapsing them loses the axis a consumer looks up. Canonical form is sorted and
  slash-separated (`C/C`); `CC` parses as one two-base allele. A pipe (`C|T`) records that the call
  was phased — with no phase-set column that is *phase recorded but unaddressable* (RM63), not a
  homolog assignment. Grammar is the shared `AuthoredModel._validate_genotype`, so a genotype means
  the same thing here as on a `VariantRow`.
- **`phenotype_category` is identity too.** One variant+drug carries separate efficacy, toxicity and
  metabolism annotations; without the category they collide. Vocabulary is closed
  (`vocab.VALID_PHENOTYPE_CATEGORIES` — as of format 0.6.1: `efficacy`, `toxicity`, `dosage`,
  `metabolism_pk`, `pd`, `other`; ask `describe_table` rather than trusting that).
- **`annotation_id` is the tie-break of last resort**, the same shape as `PgsRow.pgs_id`: a source
  accession is a legitimate identity for a curated record. Optional — and an empty cell participates
  in the provenance digest as the empty string rather than being dropped.
- **`evidence_level` vs `recommendation_strength`.** This table has only the first (PharmGKB/ClinPGx
  1A…4 — *how well established*). CPIC's grading of the prescribing action lives on `DiplotypeRow` as
  `recommendation_strength`. Different axes; a well-evidenced association can carry an `optional`
  action. Not interchangeable, deliberately not one column.
- **`conclusion` is what the module claims**, and it is the one column with no check on it. The
  drafter writes ClinPGx's `annotation_text` **verbatim** rather than a synthesized restatement — an
  earlier version emitted `"ClinPGx 655385012: C/C and warfarin — dosage"`, every word of which is
  already in the key, so the one column whose job is to say something said nothing and no gate
  noticed. Verbatim on purpose: the moment the drafter rewords it, the human who owns the claim can
  no longer see what the source said. **Editing it is the author's job.**
- **`gene` is singular and outside the key.** That combination is why the drafter withholds instead of
  splitting. It also means it cannot be used to disambiguate two rows.
- **`response` is free-form** and read straight into the report; `trait_efo_id` exists for a
  cross-module join.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **`chrom`/`start` are no longer null in the artifact — the advice you will read says they are.**
   Pre-0.6, resolution reached `variants.csv` only, so an rsid-authored PGx module compiled clean,
   validated, published, and carried a null coordinate on every row; the consumer who found out had a
   1,482-row module and read the parquet to discover it (`compiler.py:1253-1259`, S31). RM43 fixed it.
   Measured now on the reference example: `12 / 21178615 / T / A,C` on all nine rows,
   `positional_rows_placed == positional_rows == 9`. **Resolved 2026-08-20:** the skill that stated the old
   behaviour — "resolution is applied to `weights.parquet` only" — was corrected and then dismantled;
   [`module-enrich`](../../module-enrich/GUIDE.md) now names the three positional tables and the three reasons a row is left unplaced,
   and pins the grep fragment `have no chrom+start` rather than the sentence around it.
2. **`alts` reaches parquet as a comma-joined *string*, where `weights.parquet` uses `List(Utf8)`.**
   Measured: `pharm_variants.parquet.alts` is `String` with value `'A,C'`. This is the `genotype`
   asymmetry (S30 / RM81) repeated on a **new** column, and it is already breaking a consumer — see
   *Blanks* below. Do not author it; the compiler refuses an authored `alts` here outright.
3. **The bare `(variant, drug)` triple is a bug this ecosystem has already shipped once.** 1,199 of
   17,380 (variant, drug, genotype) triples in one ClinPGx release map to more than one annotation,
   839 differing by category and 283 by neither — hence all five key parts
   (`compiler.py:240-250`). Index anything by the triple and you either collide or compare the wrong
   annotation: keying the cross-check that way reported all three of the reference example's
   correctly-authored levels as stale (`clinpgx.py:270-278`).
4. **A vocabulary spelling rewrite un-closes the module while moving no identity.** Measured:
   `Metabolism/PK` → `metabolism_pk` left `content_signature` and `artifact.digest` byte-identical and
   still dropped the `verification` block, because `module_hash` binds bytes. Corollary: after a
   `reverse_module` the CSV comes back with the canonical spelling (measured), so a
   compile → reverse cycle re-closes nothing.
5. **`fully_resolved` is `True` and `resolution_subjects` is `0` on a fully-populated 9-row module.**
   Measured. Both fields are about `variants.csv` alone, so on a table-only module the flag is
   `all()` over an empty list. The registry documents having granted trust on exactly that quantifier
   (`db/facets.py:is_trusted`). Read `positional_rows` / `positional_rows_placed` instead, and treat
   `None` as *this compiler did not count* — never as `0`.
6. **The evidence-level cross-check is designed to skip itself, and the skip is the honest answer.**
   `not_checked="tautology"` fires when the licence row's `dataset` matches the snapshot **and** the
   draft digest is unmoved. It means *nothing was compared*, not *everything agreed*. Under `strict`
   a genuine conflict **raises**, because an evidence level is ClinPGx's own metadata about its own
   annotation — a difference means the module is stale, not that two experts disagree. That is why it
   escalates where `clin_sig` and `function_status` only warn.
7. **`del/del` and `C/del` are still skipped, and the reason moved.** RM5 widened the grammar to hold
   `<DEL:1500>`, so the block is no longer "the format cannot spell it" but "ClinPGx publishes no
   **length**, and a lengthless symbolic allele is a rule the compiler drops"
   (`clinpgx_draft._symbolic_types`). A provider must not hand you work the next command undoes. Add
   the length by hand if you know it.
8. **A symbolic-allele finding drops the row here, and refuses elsewhere.**
   `compiler._SYMBOLIC_DROPPABLE_TABLES` = `{variants.csv, pharm_variants.csv}` — one row is one
   self-contained rule, so dropping it removes a claim and nothing else. On `haplotypes.csv` /
   `heteroplasmy.csv` the same finding is fatal in both modes, because a row there is part of a
   composite. Under `strict` nothing is dropped anywhere; it reports.
9. **Multi-gene and multi-drug cells are not symmetric.** `drugs` fans out to N rows (in the key);
   `gene` does not (outside the key — the copies would collide and the compiler would refuse the
   module). If the drafter left `gene` empty on rows you care about, `--gene <SYMBOL>` selects the
   member; otherwise fill it by hand from the reported cells.
10. **Enricher 0.6.3's S44 fix recovered 158 rows, 36 at level 1A** — every MT-RNR1 annotation
    (aminoglycoside hearing loss, a CPIC guideline, 32 rows at 1A) and CFTR F508del, lost to a
    genotype gate narrower than the schema it wrote into. **A plain re-draft converges exactly** for
    S44 (measured upstream: 18,895 rows, 0 missing, 0 stale) because it only *skipped* rows. That is
    the opposite of the ClinVar-side S41, which wrote rows under an identity that has since moved and
    leaves stale rows behind. Do not generalise one remediation to the other.
11. **`ref` on this row is not checked against the genome.** `REDUNDANCY_BEARING` names
    `enricher.sequences.verify_reference_alleles`, but that function takes `list[ResolutionRow]` — it
    checks `resolution.csv`. What checks *your* `ref` is `resolution._authored_conflict` at compile,
    which reports the disagreement and **leaves the row exactly as authored**, filling nothing.
12. **A half-coordinate is the deceptive shape.** A `start` with no `chrom` reads as a position and
    joins to nothing; the fill will not complete it from a locus whose `start` disagrees, because
    that would build a coordinate no source ever stated. Counted separately in the joinability
    warning.
13. **`licensing.csv` is the preferred spelling** (`layout.preferred_spelling("sources.csv")` →
    `licensing.csv`, measured); `sources.csv` is deprecated-but-read, and both present is an error.
    The reference example's own README says `sources.csv` while the file on disk is `licensing.csv`.
    The parquet and `manifest.sources` keep the old names for the whole 0.x tail.

## What does not exist

- **No fact signature.** There is no `pharm_variants_signature`; it is authored, hashed inside
  `content_signature` by content and inside `artifact.digest` by bytes.
- **No `recommendation_strength`, no `clinical_context`.** Both are on `DiplotypeRow` only. A CPIC
  recommendation scoped to `CVI ACS PCI` vs `NVI` has no home on this row.
- **No `requires_callable`.** It is `VariantRow`-only, so no PGx table can record the assumption CPIC
  states in prose. Open as **RM70**, and the open question is which of the three PGx tables owns it.
- **No `chrom` vocabulary validation.** Unlike `VariantRow.chrom` / `StudyRow.chrom`, this model runs
  no chrom validator, and the schema deliberately attaches **no** vocabulary marker rather than claim
  a rejection that does not happen. Acknowledged in the code as a real inconsistency whose fix is a
  *tightening* (Principle 3), not a marker change (`pgx.py:345-350`).
- **No split `genotype` column, and the parallel-column repair is refused.** S30 asked for it;
  **RM81** records the refusal: splitting a published column is a retype (major-only), and adding a
  `genotype_alleles` list beside the string is refused as two spellings of one value in one table.
  The reader-side fix shipped instead: `just_dna_format.alleles.split_genotype`, the one public leaf
  every tier calls. **Call it; do not re-derive the split from prose** — three copies existed and one
  consumer got it wrong twice, in opposite directions, with nothing failing either time.
- **No `--no-ensembl` compiler flag.** Half of S14 was **refused with a reason**: the compiler has no
  network branch, so the flag would assert something false. Permanent, not interim.
- **No coordinate from the drafter.** `clinpgx_draft` deliberately never fills `chrom`/`start`/`ref`:
  the snapshot has none, and a coordinate authored there would be compared by `resolution._verify`
  against the table that supplied it.
- **No expansion of a one-to-many rsID.** `variants.csv` expands into N coord-keyed rows; doing that
  here would multiply the `(variant_key, drug, genotype, …)` key across loci the author never named.
  One locus or none.
- **No `resolution.parquet`.** `reverse_module` rebuilds `resolution.csv` from the positional
  parquets, which is why `alts` is carried here at all.
- **No live PharmGKB API.** `api.pharmgkb.org` was retired 2026-07-20; the snapshot is the only route
  and it is provisioned automatically. `draft-clinpgx` downloads nothing — build the snapshot first.

## Consumption today

**just-dna-lite / just-dna-pipelines** — the real consumer, and it treats this table as a *lead
table* peer of `weights.parquet`:

- `module_config.py:491-503` — `LEAD_TABLES` lists `pharm_variants` second after `weights`; a
  directory holding `pharm_variants.parquet` **is** a module. `LEAD_TABLE_CSVS` derives the authored
  name. `find_lead_table` / `has_lead_table` (`:517-537`) key discovery on schema, not on a name —
  the fix for a `pharm_variants`-led install that was annotatable but impossible to list or publish.
- `annotation/hf_modules.py:43`, `:495-503` — `ModuleInfo` carries `lead_table`/`lead_url`;
  `ModuleTable.LEAD` is what callers ask for.
- `annotation/hf_assets.py:170-176` — the lead table is appended to the asset group, or a
  `pharm_variants`-led module contributes no assets at all.
- `annotation/hf_logic.py:222-249` `_lead_join_strategy` — classifies by *schema plus data*:
  `position` if `chrom`/`start` exist **and** at least one is non-null, else `rsid` + `genotype`, else
  `unsupported`. This is the code RM43 silently upgrades: a 0.6-compiled pharm module now takes the
  **position** branch for the first time.
- `annotation/hf_logic.py:286-312` `_normalize_lead_genotype` — splits the authored `"C/C"` string to
  `List(Utf8)` before any join, mirroring `_split_genotype` and **not sorting**. Their workaround for
  S30.
- `annotation/hf_logic.py:342-399` — the two join paths. rsid: `(rsid, genotype)`. position:
  `(chrom, start, genotype)` plus a `ref` agreement filter that discards a coincidental ALT match.
- `annotation/report_logic.py:1024-1088` `build_pharmacogenomics_report_data` — the only bespoke
  report shape: groups by **drug**, ranks within a drug by `evidence_level` (`1A` strongest), reports
  `total_drugs` and a `guideline_count` of 1A/1B rows. A weight-ranked flat table is the wrong shape
  because every weight is 0.0.
- `annotation/report_logic.py:704-745` `_build_variant` — reads `drug`, `evidence_level`,
  `phenotype_category`, `response` explicitly, plus the generic `gene`, `genotype`, `ref`, `alts`,
  `conclusion`, `trait_efo_id` (via `_AUTHORED_AXES`), `locus_count`/`locus_index`.
- `annotation/report_logic.py:609-635` — those same fields go into the AI-assistant prompt
  (`Drug`, `Drug response`, `Evidence level`, `Module alternate alleles`).
- `annotation/report_logic.py:389-400` `_genotype_alleles` — documents the string-vs-list split and
  delegates to `alleles.split_genotype`.
- `module_registry.py:262`, `:305-315` — custom-module install and listing key on `has_lead_table`.
- `docs/MODULE_RELEASE_0_5.md:87`, `:402`, `:470`, `:503` — their real `pharmgkb` module: 1,482
  `pharm_variants` rows over 147 loci, three published files, no `weights.parquet`.

**just-dna-registry (0.18.2; `just-dna-marketplace` is the same tree under a stale directory name)**

- `specfiles.py:56-66` — `pharm_variants.csv` in `TABLE_KIND_CSVS`, so it is accepted, stored and
  round-tripped on publish.
- `services/enrich.py:349-353` — `ENRICHMENT_SUBJECT_TABLES` includes it, so `enrichment_subject_count`
  counts its rows as things an `enrich()` will ask about. `variant_count` would say 0.
- `services/enrich.py:1420-1440` — the publish-time `check` runs `enrich_clinpgx`; an unparseable
  `pharm_variants.csv` is a **skip with a reason**, never `unreachable`. Evidence-level conflicts are
  rendered into `FunctionConflictEntry(gene=rsid, allele=drug)` — an acknowledged mis-shaping.
- `services/upgrade.py:161` — `_ROW_MODELS["pharm_variants.csv"] = PharmVariantRow`, so the
  trim/block planner can see an offending column in a PGx module (through 0.10 it could not).
- `db/facets.py:44-96` — `positionally_joinable` reads `positional_rows_placed == positional_rows`;
  `joins_nothing_positionally` substring-matches `compiler.UNJOINABLE_PHRASE` for pre-0.6 artifacts;
  `is_trusted` returns `False` when either fires. `db/facets.py:114` names this table's reference
  example as the calibration case.
- `models/api.py:66`, `:503` — `positional_rows` and `table_rows` are published API fields.

**just-prs / just-prs-mcp** — nothing. Grepped for `pharm_variants` and `PharmVariant`: zero hits.

## Blanks for just-dna-lite

- **`alts` on `pharm_variants.parquet` is a comma-string and the report renders it wrong today.**
  `report_logic.py:709` does `"/".join(row.get("alts", []) or [])`. On `weights.parquet` `alts` is
  `List(Utf8)` and that works; on `pharm_variants.parquet` it is `String` — measured value `'A,C'` —
  and `"/".join("A,C")` returns **`'A/,/C'`** (verified in a REPL), which is what reaches the report
  as *"Module alternate alleles"* and goes into the AI prompt. **Newly reachable**: before format
  0.6 the column did not exist, so `row.get("alts", [])` returned `[]` and rendered empty. Ask:
  route the cell through `alleles`-style splitting the way `_genotype_alleles` already does for
  `genotype`, and file the type asymmetry upstream.

  > ⚠️ **CHECK — aligning `alts` to `List(Utf8)` is a retype, not a minor.**
  > **Current state.** The column being 0.6-additive does not make its *type* free. `alts` shipped
  > typed `String` in 0.6.0 and 0.6.1 (measured on the published parquets), so a consumer may already
  > read it as a string. The upstream charter lists *"retyping a field"* among the breaking changes
  > reserved for the next major, with **no** additive-column exemption.
  > **Expected state.** The fix belongs to the same 1.0 item as `genotype`'s (RM81), not to a minor
  > release. Until then the asymmetry is permanent for the 0.x line.
  > **Guard.** Consumer-side, split on `,` yourself and do **not** assume a list; the workaround is
  > the answer for the whole 0.x line, not a stopgap for one release.
- **The position join has never run on a 0.4-family lead table, and RM43 just enabled it.**
  `_lead_join_strategy` picks `position` as soon as `chrom` is non-null, which a 0.6-compiled pharm
  module now is. That path joins on `(chrom, start, genotype)` and compares `ref` — all types agree —
  but the code comments still assert the family "reaches us with chrom/start null on every row"
  (`hf_logic.py:229-232`, `:296-299`). Ask: recompile the `pharmgkb` module against 0.6, exercise the
  position branch on an rsID-less VCF (DeepVariant output), and update the two comments. Today a
  1,482-row module still annotates zero variants on such a VCF for no remaining reason.
- **`annotation_id` is published and read by nobody.** It is a live ClinPGx accession on every
  drafted row and part of the identity. Ask: link it (`clinpgx.org/clinicalAnnotation/{id}`) from the
  report row, so a reader can reach the curated annotation the module transcribed. Today the report
  shows a conclusion sentence with no route back to its source record.
- **`phenotype_category` is carried into the view model and never used to organise anything.** The
  report groups by drug and ranks by evidence level; efficacy, toxicity and metabolism rows for one
  drug are interleaved. Ask: sub-group or badge by category — it is the axis that makes three rows
  about one variant+drug three *different findings* rather than repetition, and the reference example
  exists precisely to demonstrate that.
- **`positional_rows` / `positional_rows_placed` are unread on the consumer side.** The registry
  facets on them; the pipelines do not. Ask: read them from `manifest.json` at install time and warn
  when a module will annotate a fraction of its rows, instead of discovering it as a small join
  result. `None` means *not counted*, never `0`.
- **`trait_efo_id` on a pharm row goes into `_AUTHORED_AXES` and is rendered as a bare string.** Ask:
  it is the cross-module join key the schema advertises — use it to link a drug-response row to the
  trait modules in the same report.

## Ask the live schema

```
list_tables()                                # every table kind, with its model and one-line purpose
describe_table("pharm_variants.csv")         # columns, types, vocabularies, redundancy_bearing /
                                             #   attestation_bearing (attestation is a SUBSET of redundancy)
table_requirements("pharm_variants.csv")     # always-required, any_of groups, defaulted, optional
get_template("pharm_variants.csv", stub=True)# header, and <<REPLACE>> in the cells you must decide
lint_rows("pharm_variants.csv", csv_text)    # findings + alterations; preserve `applied:false` and
                                             #   its `refusal` verbatim — that is upstream's answer, not ours to restate
authoring_reference(schemas=True)            # the whole surface in one call
```

Python, if you are outside the MCP surface:

```python
from just_dna_compiler.hints import describe_table, inspect_rows, REDUNDANCY_BEARING, ATTESTATION_BEARING
from just_dna_compiler.draft import authoring_requirements, natural_key, blank_template, stub_template
from just_dna_format.vocab import VALID_PHENOTYPE_CATEGORIES   # never hardcode the members
from just_dna_format.alleles import split_genotype              # the one public genotype splitter
```

Never restate a column list or a vocabulary from this file. It was true of format 0.6.1 and it drifts.
