# `haplotypes.csv` — which variants make up a named allele

> **Audit banner — re-stamped 2026-09-13 against format 0.7.0 / compiler 0.7.0 / enricher 0.7.0 /
> registry 0.25.2** (`importlib.metadata`, read from this repo's venv). **The prose below was written
> against 0.6.1 and has not been re-argued sentence by sentence.** What was done is narrower and is
> the half that rots: every `file:line` citation was removed — the line numbers had drifted, the
> symbol names held, so anchor on the symbol — and the counted rosters were re-measured against the
> installed packages.
>
> **Upstream generates the schema half now, so do not read it here.** Every column, type,
> requiredness, vocabulary and identity-card fact for this table is generated from the row model on
> each docs build, at <https://just-dna.life/just-dna-compiler/tables/haplotypes/>, with the authoring
> prose upstream keeps in `docs/TABLES.md` spliced above it. In-session the same answer is live from
> `describe_table("haplotypes.csv")` and `table_requirements("haplotypes.csv")`. **This file keeps the half a model
> cannot state**: who decides which cell, what an edit moves, and the symptom when the table lies.
> Where the two disagree, the generated page and the tool are right and this file is the bug.
>
> Two markers appear below — 🚧 **ROADWORKS** for a surface that is broken or unfinished, always with
> a guard saying what to do instead, and ⚠️ **CHECK** for a claim whose current state is not what the
> surrounding text would lead you to expect. **Both were raised in the 0.6.1 pass, so a marker is not
> evidence the surface is still broken at 0.7** — re-check before quoting one.

Measured against **format 0.6.1 / compiler 0.6.1 / enricher 0.6.4** (`importlib.metadata`, 2026-08-19).
Every column list, vocabulary and requirement below is illustrative; ask the tools in *Ask the live
schema* for the current answer.

## What it is

A **junction table**: one row per *(haplotype × one of its defining variants)*. It answers "what has
to be on one chromosome for this allele to be that allele" — for a star-allele caller, for
`diplotypes.csv` (which pairs the names this file defines), and for the compiler's own cross-table
checks. A haplotype defined by two SNPs is two rows; a variant recurring across twenty alleles is
twenty rows. That junction shape is the whole reason APOE ε needs no predicate language:
`HaplotypeRow` *is* same-strand conjunction (`reference_examples/apoe_epsilon/README.md`, "Why it
works without a predicate"), and a `diplotypes.csv` row pairing two of them *is* "in trans"
(`reference_examples/hfe_compound_het/README.md`).

It never says what an allele *does* (`allele_function.csv`) and never says what a pair *means*
(`diplotypes.csv`). It also never calls anything: the phased diplotype and the CN/SV calls come from
a consumer's star-allele caller (`schema/src/just_dna_format/pgx.py`).

## Identity card

| | |
|---|---|
| model | `just_dna_format.pgx.HaplotypeRow` (`schema/src/just_dna_format/pgx.py`) |
| parquet | `haplotypes.parquet` — registered at `compiler/src/just_dna_compiler/compiler.py`, in `compiler.ARTIFACT_PARQUETS` |
| dedup key | `(haplotype_name, variant_key, allele)` — `compiler.py`. **Not** `(haplotype, variant)`: one haplotype may state two alleles at one locus without colliding |
| `variant_key` | `derive_variant_key(rsid, chrom, start, ref)`, **without `alts`** (`_KEY_INCLUDES_ALTS = False`, `pgx.py`) — a haplotype junction matches a variant at `chrom:start:ref` regardless of allele |
| authored or derived | **authored.** It is in `compiler._INPUT_FILES` (`compiler.py`), not in `_DERIVED_FILES` (`compiler.py`) |
| who writes it | a human/AI author, or `just-dna-enricher draft --gene <G>` (CPIC) via `pgx_draft._haplotype_rows` |
| fact signature | **none.** It has no fact signature because it is not a derived sidecar — it is hashed by `content_signature` and by raw bytes |
| in `content_signature`? | **yes**, except the three stamped columns (see below) |
| in `artifact.digest`? | **yes**, as `haplotypes.parquet` |

## Who populates what

| column | who writes it |
|---|---|
| `haplotype_name` | **author** (or **drafter**: `pgx_draft` writes CPIC's allele label). `stub_template` marks it `<<REPLACE>>` |
| `rsid` | **author** or **drafter** (CPIC `sequence_location.dbsnpid`). Stub: `<<REPLACE>>`. Redundancy-bearing |
| `chrom` | **author**, or **drafter** since the `gene.chr` join (`enricher/src/just_dna_enricher/cpic.py,533`), or **compiler-stamped by fill** when left empty (RM43). Stub: blank |
| `start` | same three routes. **1-based VCF POS, stored as-is — never subtract one** (`pgx.py`) |
| `ref` | **author**, or **compiler filled by RM43**. `pgx_draft` never writes it |
| `alts` | **compiler-filled only**, from the injected `resolution.csv`. Declared via `base.stamped_identity_field` (`pgx.py`). An authored value is **refused**, not overwritten — `base.reject_compiler_filled` (`base.py`) |
| `allele` | **author** or **drafter**. The defining allele on this haplotype; bases, or a symbolic allele carrying its length (`<DEL:1500>`). Stub: `<<REPLACE>>` |
| `gene` | **author** or **drafter**. Optional to the model, but it is what `enrich-pgx` takes its scope from |
| `variant_key` | **compiler-stamped** at load from the authored cells, never re-derived (`pgx.py`). Tolerates nothing — it is not in the authored field set at all |
| `authored_ident` | **compiler-stamped**: which of `{rsid, chrom, start, ref}` the author actually supplied. This is what lets `reverse_module` re-emit the authored shape |
| `module` | **compiler-stamped** into the parquet only; no CSV carries it |
| *registry-stamped* | **none.** `normalize.IDENTITY_AUTHORITY_KEYS` touches `module_spec.yaml` identity, not this table |
| *nobody, ever* | **none on this model.** Every column has at least one writer |

**Cells no tool may fill.** Of `hints.REDUNDANCY_BEARING` (`compiler/src/just_dna_compiler/hints.py`),
five appear on this model: `rsid`, `chrom`, `start`, `ref`, `alts`. A lookup reports them with
`applied: false` and `refusal="redundancy_bearing"` — `compiler.resolution._verify` later compares
the authored rsID against the authored coordinate, and `enricher.sequences.verify_reference_alleles`
compares an authored `ref` against the genome, so filling either from the source it will be checked
against makes the check compare a convention with itself. `hints.ATTESTATION_BEARING` names
`provenance_quote`/`provenance_regex`, which live on `StudyRow` — **this table has none**, so the
attestation rule does not reach it at all.

`allele` is *not* in `REDUNDANCY_BEARING` and is not cross-checked against any source. `enrich-pgx`
verifies `allele_function.function_status` and nothing on this table
(`enricher/src/just_dna_enricher/pgx.py, 203-228`) — see gotcha 4.

## What moving this table moves

Measured on `reference_examples/cyp2c19_star_alleles` and `apoe_epsilon`, compiled with 0.6.1.

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row | **moves** | n/a (none) | **moves** | **dropped** — bytes changed |
| edit an authored cell | **moves** | n/a | **moves** | **dropped** |
| edit a provenance-only cell | *no such column on this table* | — | — | — |
| **reorder rows** | *unchanged* | n/a | **moves** | **dropped** |
| re-run the producing pass (`draft`) | moves only if rows were added (append-never-clobber) | n/a | same | dropped iff rows added |
| delete the file and re-derive it | moves unless byte-identical | n/a | moves | dropped |
| recompile under a newer toolchain | unchanged | n/a | may move (parquet bytes) | intact |
| edit `resolution.csv` **provenance** (`source: cache→manual`) | unchanged | `resolution_signature` unchanged | **unchanged** | intact |
| edit `resolution.csv` **facts** (`alts: "A,T"→"T,A"`) | unchanged | `resolution_signature` **moves** | **moves** | intact |

Measured numbers, `cyp2c19_star_alleles`: baseline `digest 5a831e40… / content 13aec230… /
resolution 3c42c100…`. The provenance edit reproduced all three exactly. The fact edit gave
`digest 155f1bcc… / content 13aec230… / resolution 2dd1193f…`, and diffing `manifest.artifact.files`
showed **exactly one** parquet changed: `haplotypes.parquet`.

The reorder measurement, `apoe_epsilon`: `content_signature` stayed `343333b6…` while `digest` went
`11f69653… → 5e5f0e00…` and the compile printed *"verification.json is stale … Re-run the checks to
attest these bytes, and close the module again."*

1. **Inside `content_signature`?** Yes — it is an authored table, hashed as parsed rows
   (`integrity.content_signature`, `schema/src/just_dna_format/integrity.py`). The three stamped
   columns (`alts`, `variant_key`, `authored_ident`) are `exclude=True` and therefore **outside** it,
   while still reaching parquet. `VariantRow.variant_key`/`authored_ident` *are* inside it — a
   grandfathered asymmetry carried until a major, documented at `base.py`, **not a
   precedent**.
2. **Inside `artifact.digest`?** Yes. And because the RM43 fill writes `chrom`/`start`/`ref`/`alts`
   into the parquet, a change to `resolution.csv` that no authored byte reflects still moves the
   digest — the table is the *amplifier* that turns a resolution fact into artifact bytes.
3. **Does an edit un-close the module?** Yes. `haplotypes.csv` is in `_INPUT_FILES`, so it is inside
   `compiler.authored_input_entries` (`compiler.py`) and inside the attestation binding. Since
   RM82 the binding reads `\r\n` as `\n`, so a line-ending rewrite alone does not un-close; anything
   else does — including a pure reorder, measured above. `resolution.csv` and `verification.json` are
   in `_DERIVED_FILES` and outside the binding, so a re-enrichment leaves a closed module closed
   (measured: both `resolution.csv` edits kept the closure). An `authorship:` append un-closes a
   module while moving no identity at all.
4. **Part of the §5.1 canary?** Not as a producer — it has no fact signature of its own, so it cannot
   itself produce "content same, fact moved". It is the **carrier**: the fact-edit row above *is* the
   canary reading (`docs/MODULE_LIFECYCLE.md:260-301`), with `resolution_signature` as the fact and
   `haplotypes.parquet` as the only byte that moved. Detecting real upstream drift still requires
   delete-and-re-derive — merge-not-clobber means a re-run never re-asks.

## Required to exist

- No table requires `haplotypes.csv`, and it requires none. `studies.csv` is required **iff**
  `variants.csv` is present; a PGx module carries neither.
- A module needs at least one recognised table kind; `haplotypes.csv` alone satisfies that.
- The presence of `haplotypes.csv` is what **switches on** two compiler checks
  (`_cross_validate_haplotype_definitions`, `_cross_validate_phase_ambiguity`) and what gives
  `enrich-pgx` its gene scope. A module carrying `diplotypes.csv` alone is legal and leans on the
  caller's own definitions — that is why "used but not defined" is a warning and only runs when this
  file exists (`compiler.py`).
- Drafting from CPIC drags in the **licence gate**: CPIC is CC BY-SA *plus* a bar on sale, so the
  draft is skipped when `declared_use` is unstated and refused when it is `commercial`, and the
  module must carry a `licensing.csv` row with `declared_use` set or the compile fails.

## The columns that carry judgement

- **`haplotype_name`** — an *identity, not a grammar* (`pgx.py`). The only rule is non-empty and
  no whitespace (`validate_haplotype_name`, shared by all three PGx tables since RM30). `*4`, `e4`,
  `ε4`, `wt`, `C282Y-H63D` are all legal. Spell it the same way in `allele_function.csv` and
  `diplotypes.csv` or the cross-check reports "used but not defined".
- **`allele`** — the defining allele *on this haplotype*, not the locus's ALT list. `validate_allele`
  takes ACGT or a symbolic allele carrying its length; it refuses `*` (which names the sample's
  non-observation, not a variant) and refuses IUPAC codes.
- **`ref`** — authored, it is the locus's reference base and it does two jobs: it disambiguates a
  half-coordinate, and `allele == ref` is how the phase-ambiguity check recognises "this haplotype
  carries reference here" (`compiler.py`). Omit it and that normalisation is dead.
- **`chrom` + `start`** — either alone is worthless. `REQUIRED_ANY_OF` is `{rsid}` **or**
  `{chrom, start}` (`pgx.py`), so a bare `start` is legal only because an rsID is present, and it
  reads like a coordinate while joining to nothing.
- **`gene`** — optional to the model, load-bearing in practice: `enrich_pgx._module_genes` derives the
  module's scope from this column and `allele_function.gene`, and answers *"the module names no
  genes … so there is nothing to check against"* when both are blank.

### `requires_callable` arrived in 0.7, and it is per locus for a reason

**RM70.** True says a consumer must prove this position was **callable** before reading the *absence*
of the defining allele as reference — that is, before assigning the reference haplotype at this
locus. False records the opposite claim, **which is the one CPIC's star-allele system makes**: an
uncalled position is taken as reference. Empty says nothing either way, and **is not False** — the
three-valued rule, on the column where getting it wrong assigns somebody the wrong star allele.

**Why it sits on the locus rather than on the module.** One gene can hold a common allele defined by
a single SNP beside one defined partly by a structural event, and the two do not have the same
callability requirement. A module-level flag would have to be the stricter of the two, which would
make every ordinary SNP row demand a proof nobody needs.

**`callable_from` did not travel with it, anywhere.** *"A proof is required"* and *"here is where the
proof lives"* are different axes, and only the first one exists. So the column tells a consumer that
it owes a check; it does not tell them where to look.

It is **not** on `DiplotypeRow`, deliberately: a diplotype names a star-allele pair, not a locus.
The same column arrived on `pharm_variants.csv` in the same item — see
[`pharm_variants.md`](pharm_variants.md), where the case it answers is the reference-homozygote row.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **`alts` is refused here and required on `variants.csv`.** Writing it by analogy is the single most
   plausible mistake, and it is an error per row:
   *"'alts' is filled by the compiler on this table, from the injected resolution.csv, and is not an
   authored column here — remove it."* (measured on a modified `apoe_epsilon`). Before 0.6 it was
   silently *accepted* and then dropped by reverse, so `compile → reverse → compile` was not a fixed
   point (`base.py`).

2. **A CPIC draft gives you `start` with no `chrom`, and that is a coordinate that joins to nothing.**
   `reference_examples/cyp2c19_star_alleles/haplotypes.csv` has the header
   `haplotype_name,rsid,start,allele,gene` — 106 rows, no `chrom` column at all. The compiler counts
   these apart as the *"more deceptive shape"* (`compiler.py`) and says so:
   *"106 carry one half of a coordinate (a start with no chrom, or the reverse), which reads as a
   position and is not one."* RM43's fill completes it from `resolution.csv` **only when the locus
   agrees**; a locus whose `start` disagrees leaves the row alone and reports, because completing it
   would build a coordinate no source ever stated (`resolution.py`). Measured after
   `enrich`: 106 of 106 placed, `chrom`/`start`/`ref`/`alts` all non-null in the parquet.
   **The reference example's README is now stale on the reason** — it says CPIC "never publishes a
   chromosome", and `cpic.py` corrects exactly that probe: `gene.chr` carries `chr10` for
   CYP2C9. A fresh draft today writes `chrom`.

3. **A pure row reorder moves `artifact.digest` and un-closes the module while `content_signature`
   stays put.** Measured above. `content_signature` sorts rows; the attestation binding and
   `manifest.inputs[]` hash bytes. Nothing warns that a cosmetic tidy-up cost you the closure.

4. **Nothing ever checks a defining-variant set against CPIC or PharmVar.** `enrich-pgx` reads this
   table *only* to learn which genes the module is about (`_GENE_TABLES`,
   `enricher/pgx.py`); the comparison it runs is `allele_function.function_status` against
   the two authorities. `DRAFT_PROJECTIONS["cpic"]` also points at `allele_function.csv`, not here
   (`enricher/provenance.py`), so the drafted-unchanged digest does not track this file
   either. If you mistype an `allele`, no pass will disagree with you.

5. **CPIC's IUPAC codes are skipped, permanently.** `*2`, `*4` and `*35` each have one defining
   variant CPIC records as `R`/`Y`/`M` — a *set* of nucleotides. `cpic.unusable_allele_reason`
   classifies it `"ambiguity"` and the drafter reports and drops the row, because expanding `R` to two
   rows *"would invent two defining variants where CPIC recorded one uncertainty"*
   (`cpic.py, 105-108`). The alleles survive with fewer defining positions. This is separate
   from `"symbolic"` (`DELTCT`, `AAAGGGGCG(2)`), which is a grammar gap RM5 partly closed — the two
   were once reported as one thing and that was wrong.

6. **A dropped row silently redefines the haplotype, so the symbolic-allele finding is fatal here in
   both modes.** `_SYMBOLIC_DROPPABLE_TABLES` is `{variants.csv, pharm_variants.csv}` only
   (`compiler.py`); a `haplotypes.csv` row is *part of a composite*, so
   *"dropping it would not make a smaller module but a quietly different one"*. Clearable by stating
   the length: `<DEL:1500>`.

7. **"Used but not defined" is checked; "defined but never paired" is not.** The exemption list is one
   name — `_REFERENCE_HAPLOTYPE = "*1"` (`compiler.py`), the star allele defined by carrying
   *none* of a gene's variants. Two consequences. (a) That hardcode is gene-agnostic, and CPIC's own
   reference allele for CYP2C19 is `*38`, not `*1` — measured: `*38` has **35 rows, every one with
   `allele == ref`** after the fill, i.e. the reference haplotype written out longhand. (b) The
   reverse direction is unchecked: in `cyp2c19_star_alleles`, `*40` and `*41` are defined in
   `haplotypes.csv` (`*40` 3 rows, `*41` **2** — measured) and graded in `allele_function.csv`, and appear in **none** of the
   1,190 diplotype rows. A caller can emit `*40/*1` and the module has no conclusion for it. Nothing
   says so.

8. **The reference haplotype is written out on all three examples, and `*1` is the exception, not the
   rule.** APOE ε3 carries the reference allele at both positions, HFE `wt` carries it at both, and
   CPIC's `*38` carries it at all 35. *"Unlike a star-allele `*1`, which is defined by the absence of
   variants, ε3 is a real named haplotype whose defining alleles happen to be the reference ones — so
   it is written out rather than left implicit"* (`apoe_epsilon/README.md`). Write it out unless your
   source's convention is genuinely `*1`-style.

9. **The `_IMPLIED_REFERENCE` normalisation is dead on a CPIC draft, and the fill does not revive it.**
   `_cross_validate_phase_ambiguity` folds `row.ref is not None and row.allele == row.ref` onto the
   same sentinel as "unmentioned" (`compiler.py`). Both cross-checks run at
   `compiler.py`, **before** `_apply_positional_resolution` at `compiler.py` — so they
   see the authored rows. Measured on `cyp2c19_star_alleles`: **0** authored rows normalise (no `ref`
   column exists), **35 of 106** would after the fill. So `*38`'s 35 explicit reference bases compare
   as 35 distinct alleles against a sparse allele that simply omits those positions, and the check
   under-reports. On a table that *does* author `ref` (APOE, HFE) it works as documented.

10. **The phase-ambiguity check is closed-world, and a clean run is not a clean bill.** It compares the
    rows the module states, never the rows it omits — APOE ε2/ε4 vs ε1/ε3 is the textbook unphased
    collision and nothing fires, because that module carries no ε1
    (`compiler.py`). It also distinguishes *two* failures: haplotypes this module defines
    **identically** (phase cannot help — a real CYP2D6 draft has 378 such groups) from ones phase
    would resolve (20). Do not report the first as "get phased data".

11. **A whitespace-free name is the *only* naming rule, and it was not always.** Before RM30,
    `AlleleFunctionRow.allele` demanded a leading `*` while the two haplotype columns had no rule at
    all, so `e4` was legal in two tables and illegal in the third — and the 0.5.1 cross-check turned
    the obvious workaround (`*4` here, `e4` there) into "used but not defined" with no legal spelling
    satisfying both (`pgx.py`). `STAR_ALLELE_PATTERN` still exists and is what the CPIC drafter
    checks, at four sites; it is **not** the rule for authoring.

12. **The manifest publishes no per-table row count for this file.** Measured `manifest.stats` on
    `cyp2c19_star_alleles`: `variant_count 0, gene_count 0, genes []`. `positional_rows: 106` /
    `positional_rows_placed: 106` is the only count, and it is the sum across
    `pharm_variants`/`haplotypes`/`heteroplasmy` (`manifest.py`). `table_rows` exists in
    `ValidationResult.stats` (`compiler.py`) and does **not** reach `Stats`.

13. **`gene` on this table reaches the catalog as of compiler 0.6.6.** `manifest.stats.genes` used to
    be `variant_stats(variants)`, running only `if variants:`, so a module whose 106 haplotype rows
    all say `gene=CYP2C19` published `genes: []` and `gene_count: 0` — invisible to a gene search,
    since the registry indexes that field into `version_genes`
    (`just-dna-registry/src/just_dna_registry/db/repository.py`).
    **Fixed in compiler 0.6.6** (upstream **RM121**): `module_stats` takes the gene facets over every authored table, `variant_stats` keeps its `variants.csv` promise, and a module already published carries the stats its compile wrote — recompile and re-publish to be findable by gene. Re-measured on `cyp2c19_star_alleles`: `gene_count: 1, genes: ['CYP2C19']`.

## What does not exist

- **No `requires_callable` / `callable_from`.** These are `VariantRow`-only, so a star-allele module
  cannot record CPIC's core assumption — *a position not called is reference*, which is literally
  `requires_callable=false`. Filed as **RM70** (`docs/ROADMAP_0_7.md:464-489`), deferred rather than
  refused: an authored column is full cost under the 0.6 charter amendment, and which of the three
  PGx tables owns the claim is undecided.
- **No expansion of IUPAC codes**, ever. Refused with a reason (gotcha 5).
- **No `resolve_with_ensembl=False` escape.** Despite the name it is the master switch for *all*
  resolution, injected `resolution.csv` included, and it compiles every row with `chrom=None` and
  **succeeds**. Upstream refused a `--no-ensembl` rename with a reason (the compiler has no network
  branch, so the flag would assert something false), which makes the pin permanent.
- **No fact signature and no `haplotypes` block in the manifest.** Fact signatures are for derived
  sidecars; this is authored.
- **No expansion of a one-to-many rsID.** `resolve_positional_rows` fills *"from exactly one locus, or
  from none"* (`resolution.py`) — expanding would multiply a junction row across loci the
  author never named. Several usable loci means the row stays unplaced and is counted.
- **No `requires_phase` column.** Deliberately a check rather than a column, because it is derivable
  from two tables the compiler already holds and *"would go stale the moment a haplotype is edited"*
  (`compiler.py`).
- **No predicate language.** RM28's cis/trans motivation dissolved into this junction table plus
  `diplotypes.csv`; what remains open is *economy* (300 pathogenic variants → ~45,000 pairs) and
  *pairing across subjects*, not expressiveness.
- **No `genotype` column** — and no consumer-side equivalent. See below; this is the sharp one.

## Consumption today

**just-dna-lite / just-dna-pipelines** — the table is *discovered* and never *read for content*.

- `just-dna-pipelines/src/just_dna_pipelines/module_config.py` — `haplotypes` is 4th in
  `LEAD_TABLES`, so a directory holding `haplotypes.parquet` counts as a module and is publishable.
- `module_config.py` (`LEAD_TABLE_CSVS`) and `webui/src/webui/state.py,6043-6050` —
  `haplotypes.csv`'s line count is what the registry's enrichment ceiling is applied against.
- `annotation/hf_logic.py` (`_lead_join_strategy`) — the only place the schema is inspected.
  It reads five columns (`rsid, chrom, start, ref, genotype`) and left-joins the rest opaquely.
- `annotation/hf_logic.py` — the position join, `on=["chrom","start","genotype"]`.
- **Nothing reads `haplotype_name`, `allele`, or `gene`. Nothing pairs haplotypes into diplotypes.
  There is no star-allele caller in the consumer at all** — `ModuleTable` (`hf_modules.py`)
  has members for `annotations`/`studies`/`weights`/`sources`/`lead` and nothing else.

**Measured, and it is worse than "unread":**

- `diplotypes.parquet` classifies as **`unsupported`** (`missing: genotype, rsid`) and
  `annotate_vcf_with_module_weights` raises `UnsupportedLeadTable`. `diplotypes` outranks
  `haplotypes` in `LEAD_TABLES`, so **every well-formed PGx module — including `apoe_epsilon`, the
  exact module `docs/V1_PARITY.md:110-115` says the `lnewco` port needs — is skipped whole.**
- A `haplotypes`-led module (no `diplotypes.csv`) with filled coordinates classifies as
  **`position`**, and the position join then asks for a column the table does not have. Reproduced
  against the real `apoe_epsilon` parquet:
  `ColumnNotFoundError: unable to find column "genotype"; valid columns: ["module","haplotype_name","rsid","chrom","start","ref","alts","allele","gene","variant_key","authored_ident"]`.
  With coordinates **null** it degrades gracefully to `unsupported`. So the module crashes the engine
  precisely when it is *better* resolved — and RM43 made filled coordinates the normal case. No test
  covers a `haplotypes`-led module (`just-dna-pipelines/tests/test_hf_modules.py`).

**just-dna-registry** — reads it as a *file*, never as rows.

- `src/just_dna_registry/specfiles.py` — in `TABLE_KIND_CSVS`; `has_spec_data` (`:305`) names it as
  the case for "a PGx-only module holding `haplotypes.csv` and no `variants.csv` has plenty".
- `src/just_dna_registry/services/upgrade.py` — `HaplotypeRow` is in the model map so a
  recompile-on-upgrade can parse it.
- `src/just_dna_registry/services/enrich.py` — in `ENRICHMENT_SUBJECT_TABLES`, so its rows count
  toward the `enrich_max_variants` bound (an upper bound: the enricher dedups by `variant_key`).
- `src/just_dna_registry/db/facets.py` — `positionally_joinable` reads
  `positional_rows`/`positional_rows_placed`, which include this table's rows;
  `joins_nothing_positionally` (`:63`) substring-matches `compiler.UNJOINABLE_PHRASE`. Both feed
  `is_trusted`. `cyp2c19_star_alleles` is the named case in the historic `S13`
  (`docs/history/CONSUMER_SUGGESTIONS_HISTORY_PRE_0_6.md:728`): 106 of 106 unjoinable rows,
  `trusted: true`, fixed downstream.
- `src/just_dna_registry/models/api.py` — `SpecStats.table_rows` carries per-CSV counts from the
  server's own validate. The **manifest** carries none.

**just-prs / just-prs-mcp** — nothing. `is_haplotype` in `just-prs/src/just_prs/scoring.py` is a
PGS Catalog scorefile column, unrelated.

## Blanks for just-dna-lite

- **Ask: teach the engine to call a diplotype.** `haplotypes.parquet` + `diplotypes.parquet` is a
  complete instruction set — junction rows give the per-variant genotype pattern, the diplotype table
  gives the conclusion — and the engine reads neither. Today `_lead_join_strategy` returns
  `unsupported` for `diplotypes` and every APOE/HFE/CYP2C19-shaped module is skipped entirely, which
  is why `V1_PARITY.md` §5 (`lnewco`) is still unbuilt with "no schema decision outstanding".
- **Ask: make `_lead_join_strategy` check that the columns the chosen join needs actually exist.**
  Returning `position` on a table with no `genotype` column produces a `ColumnNotFoundError` at
  collect time rather than a recorded skip — reproduced above on a real compiled `apoe_epsilon`.
  Cheapest correct fix: require `{"chrom","start","genotype"}` for `position`, so a `haplotypes`-led
  module degrades to the same recorded `unsupported` it already gets when its coordinates are null.
- **Ask: a haplotype-aware join key.** `haplotypes.parquet` states one `allele` per row, not a
  diploid `genotype`; the natural predicate is *"does the sample's call at this locus contain this
  allele"*, which `compiler.resolution.hosting_verdict` already implements three-valued and which the
  enricher and compiler both use for exactly this table. Reusing it would keep `unknown` from
  collapsing into "no match".
- **Ask: report which defined haplotypes no diplotype pairs.** The compiler checks "used but not
  defined" and not the reverse; a consumer that can emit `*40` from `haplotypes.parquet` and finds no
  conclusion row has no way to say so. Measured: `*40`, `*41` in `cyp2c19_star_alleles`.

## Ask the live schema

```
list_tables()                                  # every kind, with its subject and key
describe_table("haplotypes.csv")               # columns, types, requirements, vocabularies,
                                               #   redundancy_bearing, attestation_bearing
table_requirements("haplotypes.csv")           # required / required-any-of / conditional
authoring_reference()                          # the cross-table rules, generated from the models
get_template("haplotypes.csv", stub=True)      # header + a <<REPLACE>> row
lint_rows("haplotypes.csv", rows=[...])        # per-cell findings and refusals before you write
```

CLI equivalents live in the format tree: `just-dna-compiler validate <spec>` (runs both cross-table
PGx checks), `just-dna-compiler compile <spec> <out> --strict`, and
`just-dna-enricher draft <spec> --gene <G> --use non-commercial` for a CPIC draft.

Never restate a column list or a vocabulary from this file — it is a map of the traps, not the schema.
