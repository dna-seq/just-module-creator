# `allele_function.csv` — what a named star allele *does*, as one expert panel graded it

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

Stamped against **format/compiler 0.6.1, enricher 0.6.4, registry 0.18.2** (`importlib.metadata`,
2026-08-19). Every column list and vocabulary below is illustrative; run the tool calls in the last
section for the current answer.

## What it is

One row per `(gene, named allele)` saying what that allele's product does: a function category from a
closed vocabulary, and optionally a numeric activity value. It is the *dictionary* half of the
star-allele model — `haplotypes.csv` says which variants make an allele, `diplotypes.csv` says what a
pair means, and this table says what one allele contributes. Its reader is a consumer's star-allele
caller, which sums per-allele activity across the two haplotypes to reach a phenotype; the module
never calls a genotype itself. Because copy number attaches to a *cis* allele-unit, `*2x2/*4` (AS 2)
and `*2/*4x2` (AS 1) are different answers, and the module docstring warns that a consumer
multiplying by *total* CN gets it wrong (`schema/src/just_dna_format/pgx.py:15-18`).

## Identity card

| | |
|---|---|
| Model | `just_dna_format.pgx.AlleleFunctionRow` (`schema/src/just_dna_format/pgx.py:168`), subclass of `base.AuthoredModel` |
| Parquet | `allele_function.parquet`, registered in `compiler._TABLE_KINDS` (`compiler/src/just_dna_compiler/compiler.py:229`) |
| Dedup key | `(gene, allele)` — `_TABLE_DUPE_KEYS` (`compiler.py:254`). Nothing else keys it: one function per allele, full stop |
| Authored or machine-produced | **Authored.** It is a table kind, not a fact sidecar — `AuthoredModel` semantics, reserved-namespace guard, raw-byte input hashing |
| Who writes it | a human/AI author, or `pgx_draft` from CPIC (which never rewrites an existing row) |
| Fact signature | **none.** Authored tables have no fact set and no manifest block. `describe_table` will not show you one because there isn't one |
| In `content_signature`? | **yes** — `_TABLE_KINDS` feeds `compiler.content_signature` (`compiler.py:3848`) |
| In `artifact.digest`? | **yes** — `allele_function.parquet` is in `ARTIFACT_PARQUETS` (`compiler.py:278`) and in `LEAD_PARQUETS` (`compiler.py:308`), so a module carrying only this table is still a module |
| Attestation | `verification.json` check name `allele_function`, written by `enrich_pgx._attest` (`enricher/src/just_dna_enricher/pgx.py:578`). It is one of the fifteen wired members of `vocab.VALID_VERIFICATION_CHECKS` |

## Who populates what

| Column(s) | Who writes it |
|---|---|
| `gene`, `allele` | **author**, or **drafter** (`pgx_draft`, `pgx_draft.py:387`). `scaffold --kinds allele_function.csv` stubs *both* as `<<REPLACE>>` and everything else blank — measured: `stub_template("allele_function.csv")` → `<<REPLACE>>,<<REPLACE>>,,,,,,` |
| `function_status` | **author**, or **drafter** — `pgx_draft` copies CPIC's `clinicalfunctionalstatus` through `cpic.map_function_status` (`cpic.py:237`). This is the one drafted column that a later check re-reads, and it is why `DRAFT_PROJECTIONS["cpic"]` exists (`provenance.py:96`) |
| `activity_value` | **author**, or **drafter** — `pgx_draft` copies CPIC's `activityvalue`. CPIC states it for only 215 of 1,361 alleles in the shipped snapshot (measured), so a drafted cell is usually blank |
| `suballele`, `copy_number`, `sv_type`, `hybrid_orientation` | **author only.** The drafter never writes any of them (`pgx_draft.py:387-393` sets four fields and no more). They are "optional parsed conveniences of the *cis* allele-unit — the star-string remains truth" |
| `module` (parquet only) | **compiler-stamped** at build, not a CSV column at all: `_build_table` prepends it (`compiler.py:457`) so `reverse_module` can recover the module name. Not authorable — `AuthoredModel`'s reserved-namespace guard rejects it in the CSV |
| registry-stamped | **none.** `normalize.IDENTITY_AUTHORITY_KEYS` touches `module_spec.yaml`, not this table |
| nobody, ever | **none.** Every column here is reachable by an author |

**The cell no tool may fill: `function_status`.** It is in `hints.REDUNDANCY_BEARING`
(`compiler/src/just_dna_compiler/hints.py:94`), mapped to
`enricher.pgx.enrich_pgx (authored function vs PharmVar and CPIC)`. `lint_rows` on a table whose
`function_status` column is empty throughout emits an `info` finding with `row=None` saying the
column *"is left to the author on purpose … filling it from that same source would make the check
vacuous"* (`hints.py:508-530`). Nothing here is in `hints.ATTESTATION_BEARING` — that set is
`{provenance_quote, provenance_regex}` only, and belongs to `studies.csv`.

**The refusal is weaker here than it looks, and you must know why.** `pgx_draft` *does* write
`function_status` out of CPIC. That is not a violation — a drafter transcribes a published table and
the human then owns the row — but it means the CPIC leg of the cross-check can compare a value
against its own source. See gotcha 1.

## What moving this table moves

Measured on `reference_examples/cyp2c19_star_alleles` (36 rows), compiled with
`just-dna-compiler compile … --strict` and the manifests diffed. **There is no fact signature
column**: authored tables have none, so that column is struck through for every row.

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row | **moves** | n/a | **moves** | **dropped** |
| edit an authored cell (`*9 decreased→uncertain`) | **moves** `13aec2…`→`c9bbdd…` | n/a | **moves** `5a831e…`→`4e6535…` | **dropped** |
| edit a provenance-only cell | *no such cell exists* — this table carries no `source`, `fetched_at` or `status` | | | |
| reorder rows (reverse the file) | **same** `13aec2…` | n/a | **moves** `5a831e…`→`5ffa07…` | **dropped** |
| add an all-blank optional column (`activity_value`) | **same** | n/a | **same** | **dropped** |
| normalize `\r\n`→`\n` | **same** | n/a | **same** | **kept** (RM82) — but `manifest.inputs[].sha256`/`size` move (1045→1008 bytes) |
| re-run `pgx_draft` appending nothing | same | n/a | same | kept — `merge_sources_csv` is `setdefault` and `stamp_draft_digest` no-ops |
| delete the file and re-derive | **moves** | n/a | **moves** | **dropped** |
| recompile under a newer toolchain | same | n/a | may move (parquet bytes / polars) | kept |

Four rows are worth staring at. **Reordering moves the digest and not the signature** —
`artifact.digest` preserves authored row order by design, `content_signature` sorts. **Adding a blank
column moves neither identity and still un-closes the module** — the binding hashes bytes. And
`\r\n`→`\n` is now free (the reference corpus ships CRLF, so this is not hypothetical).

1. **Inside `content_signature`?** Yes. It is a `_TABLE_KINDS` member, so `compiler.content_signature`
   loads and hashes it as `model_dump(mode="json", exclude_none=True)`, sorted, order-independent
   (`integrity.content_signature`). There is no fact-field constant for it and nothing is excluded —
   contrast `sources.csv`, which is hashed by `SOURCE_FACT_FIELDS` (`sources.py:68`) with `fetched_at`
   and `draft_digest` deliberately left out.
2. **Inside `artifact.digest`?** Yes, via `allele_function.parquet`. Note the parquet carries **all
   seven model fields plus `module`** whatever the CSV has, so a three-column CSV and an eight-column
   CSV with the same values produce byte-identical parquets — which is why "add a blank column" moved
   the digest not at all.
3. **Does an edit un-close the module?** Yes, always. `allele_function.csv` is in `_INPUT_FILES`
   (`compiler.py:267`), so it is inside `authored_input_entries` (`compiler.py:361`) and any changed
   byte other than a line ending drops both the attestation and the closure. Watched it happen live:
   editing one cell made `enrich_pgx` print *"verification.json carried a closure over different
   authored bytes; it is dropped rather than re-bound."* Note the converse trap from
   `MODULE_LIFECYCLE.md` §6.2 — appending an `authorship:` entry un-closes the module while moving
   **no** identity at all.
4. **Part of the §5.1 canary?** **No.** The canary is *content unmoved + a fact signature moved*, and
   this table has no fact signature to move. The nearest thing is the licence row: a re-draft restamps
   `SourceRow.draft_digest`, which sits outside `SOURCE_FACT_FIELDS` and so lands in row 2 of the
   canary table (a thing *you* did), not row 3. Detecting that CPIC changed its mind about an allele
   requires deleting `allele_function.csv` and re-drafting — and `append_rows` is merge-not-clobber, so
   a plain re-run reports the difference as `differs` and writes nothing.

## Required to exist

**Nothing requires this table, and it requires nothing.** Measured: a directory holding only
`module_spec.yaml` and a two-line `allele_function.csv` compiles green under `--strict` (digest
`c7afba6c…`), with no error and no warning beyond the standard "records no closure". Specifically it
drags in **no** `haplotypes.csv`, **no** `studies.csv`, and **no** `licensing.csv`.

That asymmetry is deliberate but sharp-edged. `variants.csv` ⇄ `studies.csv` is a symmetric hard pair
(`scaffold.COMPANION_KINDS`); the PGx family has no such rule, because a module may legitimately lean
on an external caller's allele definitions. The consequence is that a module can assert *"CYP2C19 \*2
has no function"* with nothing defining `*2`, no citation, and no licence row, and pass strict compile.
The only backstop is a **warning** — `_cross_validate_haplotype_definitions` (`compiler.py:2932`) —
and it fires *only when `haplotypes.csv` is present*. Author a module with `allele_function.csv` alone
and the check does not run at all.

## The columns that carry judgement

- **`allele` — the identity, verbatim, and it is not a star grammar.** Since the APOE fix all three
  PGx tables share `validate_haplotype_name` (`pgx.py:58`): non-empty, no whitespace, nothing else.
  `e4`, `ε4`, `Tondela` and `c.1003G>T` are all legal names. `STAR_ALLELE_PATTERN` (`pgx.py:39`) still
  exists but is the **drafter's** rule, not the table's — see gotcha 4.
- **`function_status` — the redundancy-bearing cell, and the only one anything checks.** Vocabulary
  `pgx.VALID_FUNCTION_STATUS` (`pgx.py:69`), closed, six members. **Blank means unknown, not
  `unknown_function`**: `unknown_function` is a positive claim CPIC makes ("we looked and cannot say"),
  a blank is the module declining to claim anything, and `_compare` skips a blank row entirely
  (`pgx.py:215`). Three states, and they are not interchangeable.
- **`activity_value` — a float, and the format has nowhere to put a bound.** `float | None`, validated
  finite (`validate_finite`). CPIC's *allele* activity values really are numeric, but its *diplotype*
  activity scores are strings like `≥3.0` — measured 96 `≥3.0`, 32 `≥4.0`, 26 `≥3.5` and 103,757 `n/a`
  across the snapshot's 112,754 diplotypes. Those live on the diplotype grain, which the format does
  not carry at all (see *What does not exist*). At allele grain the loss is quieter: `cpic._float_or_none`
  (`cpic.py:261`) returns `None` for anything unparsable, so a non-numeric value would vanish without a
  warning. **Do not read `0` as unknown** — `0.0` is `*4`'s real activity and 82 alleles carry it.
- **`copy_number` — a *cis* count, not the sample's total.** `*1x2` → 2. It describes the allele-unit
  the row names, and the whole reason the model exists at this grain is that a consumer summing total
  CN gets a different phenotype.
- **`suballele`** — Aldy's `Minor` (`1.001`). Extra, never identity: `_TABLE_DUPE_KEYS` keys on the core
  star only, so two rows differing solely by `suballele` are **duplicates the compiler rejects**.

## Gotchas

Ordered by how likely a first-timer is to hit them.

### 1. The CPIC leg can grade a table CPIC itself wrote, and whether it does depends on two cells you never see

`pgx_draft` writes `function_status` from CPIC; `enrich_pgx` then compares `function_status` against
CPIC. RM73's fix is `_tautology_note` (`pgx.py:85`): the leg skips **only** when the licence row's
`dataset` names the release this leg is about to read **and** `SourceRow.draft_digest` still matches
the table's `(gene, allele, function_status)` projection (`provenance.py:88-138`). Either half missing
and the leg runs in full — the conservative direction, and the direction that produces a false clean bill.

**Measured on the shipped reference example**, whose `licensing.csv` carries an empty `dataset` and no
`draft_digest` at all:

```
subjects 34  findings 0  skipped null  source cpic  detail "compared 34 authored allele function(s) against cpic (snapshot, cpic_snapshot_3d2123598711)"
```

Thirty-four alleles pronounced clean by the panel that supplied all thirty-four values. Stamping the two
cells and re-running turns the same module into the honest record:

```
subjects 0  findings 0  skipped "offline"  detail "pharmvar: skipped — --offline and no built snapshot. … cpic: this module's licence row records that these rows were drafted from cpic_snapshot_3d2123598711 … so each is a copy of the value it would be compared against."
```

So: **if you drafted from CPIC, check that `licensing.csv` has a `dataset` and a `draft_digest` before
you believe a clean `allele_function` record.** Editing any `function_status` breaks the digest and the
leg genuinely runs again — verified: the same module with one cell changed reports `compared 34`.

### 2. This check warns under `--strict`, and `mode` is dead code

The pass warns in both modes on purpose: *"PharmVar and CPIC genuinely disagree about some alleles …
Failing a compile over that would make the format arbitrate a scientific disagreement between the two
authorities it depends on"* (`pgx.py:19-24`). It joins the ClinVar `clin_sig` exception. Verified by
running `enrich_pgx(mode="strict")` over a deliberately wrong `*2` → returned the conflict, raised
nothing. The registry does the same: `PgxCheck` conflicts never enter `_would_publish`
(`just-dna-registry/src/just_dna_registry/services/enrich.py:830`).

**Two shipped claims contradict this and are wrong** — flag them, do not act on them:
`PgxEnrichmentError`'s own docstring says *"Raised in strict mode when the PGx cross-check finds a
discrepancy it will not carry"* (`pgx.py:114`; it is only ever raised for an unparsable CSV), and the
CLI advertises `--strict/--best-effort` as *"Fail on an allele-function discrepancy"*
(`enricher/src/just_dna_enricher/cli.py:631`). `mode` is stored on `PgxResult.mode` and read nowhere.

> 🚧 **ROADWORKS — `enrich_pgx(mode=…)` is accepted and does nothing.**
> **Current state.** Re-confirmed: the parameter is stored on the result and read by no branch. The
> pass reports a PharmVar/CPIC disagreement identically under `best_effort` and `strict`. Two shipped
> user-facing strings — the `PgxEnrichmentError` docstring and the CLI's `--strict/--best-effort`
> help — promise a ladder that does not exist.
> **Expected state.** Either the flag gets a meaning or the strings get corrected; neither has
> happened, and the *reporting* behaviour is deliberate (the format will not arbitrate between two
> authorities), so the flag is the part that is wrong, not the silence.
> **Guard.** Do not gate a pipeline on `enrich_pgx(mode="strict")` — it cannot fail on a
> discrepancy, so a green run is not evidence of agreement. Read `PgxResult`'s conflicts yourself and
> decide in your own code.

### 3. Per-leg accounting: `subjects` counts what an authority named *back*

Three counting rules, each protecting against a record that reads clean when nothing was put
(`_function_check_record`, `pgx.py:488`, and `docs/ENRICHER.md:90-103`):

- **`subjects` = alleles an authority actually named back**, never authored rows. A claim about an allele
  neither panel lists was compared against nothing; the shortfall goes in `detail`, not the denominator.
- **`findings` = alleles in dispute, not conflicts.** One status contradicted by both panels is one
  allele reported twice, and `VerificationRecord` refuses `findings > subjects`.
- **`source` is filled only when exactly one authority is implicated.** It is a single join key into the
  licensing table; naming one of two would hide the other. So `source: cpic` on a two-authority check
  silently means *PharmVar did not answer*.

A module stating no `function_status` anywhere records `nothing_to_check`, not `0 of 0` — zero out of
zero would read as agreement.

### 4. The drafter drops 56% of CPIC's alleles, and eleven whole genes, on a rule the table does not enforce

`AlleleFunctionRow.allele` accepts any whitespace-free name. `pgx_draft` checks
`STAR_ALLELE_PATTERN` instead (`pgx_draft.py:384`) and skips anything failing it. Measured over the
shipped CPIC snapshot's 1,361 alleles:

| | count |
|---|---|
| pass `STAR_ALLELE_PATTERN` (drafted) | 598 |
| fail it but **legal** as a haplotype name (silently dropped) | 693 |
| fail both (a name with a space or comma) | 70 |

Eleven CPIC genes lose **every** allele: `ABCG2, CACNA1S, CFTR, DPYD, G6PD, HLA-A, HLA-B, IFNL3,
MT-RNR1, RYR1, VKORC1`. Run `just-dna-enricher draft <dir> --gene DPYD --use non-commercial` and you get
248 individual skip warnings and `added 0 row(s)`. (Two skips in `pgx_draft` are un-aggregated, not
one: measured on that same `--gene DPYD` run, 84 lines of *"… is not a star-allele string —
skipped."* from this table's loop **and** 164 lines of *"… is not a star-allele string this format
can hold — skipped."* from `_haplotype_rows`.) Same for G6PD, whose alleles CPIC names `Tondela`, `Wayne`, `Wisconsin`. **These
alleles are perfectly authorable by hand** — the block is the provider, not the schema.
`reference_examples/apoe_epsilon/README.md:56-59` records the model half of this fix and states the
provider stays strict; nobody measured what that costs.

> 🚧 **ROADWORKS — `draft --gene` is unusable for eleven CPIC genes, and says so only in the row count.**
> **Current state.** Re-confirmed against the shipped snapshot. For `ABCG2, CACNA1S, CFTR, DPYD,
> G6PD, HLA-A, HLA-B, IFNL3, MT-RNR1, RYR1, VKORC1` the drafter emits a wall of per-allele skip
> lines and then `added 0 row(s)`. There is **no** warning saying "this gene is not draftable"; the
> zero is the whole diagnosis, and it looks like "nothing to do" rather than "everything was
> refused".
> **Expected state.** The model accepts these names, so the right end state is either a provider
> that drafts them or an explicit refusal naming the gene. Neither exists.
> **Guard.** For those eleven genes, **hand-author `allele_function.csv`** from CPIC's table and do
> not treat `added 0 row(s)` as a clean run. And note the second failure that rides along: a draft
> that adds zero rows also writes **no `SourceRow`**, so the module can end up with no
> `licensing.csv` entry for CPIC at all — see `licensing.md`. Write that row yourself.

### 5. 408 CPIC statuses map to a blank cell, without a warning

`cpic._FUNCTION_MAP` (`cpic.py:225`) maps six CPIC phrases plus two `possible …` variants; anything
else returns `None` and the drafter writes an empty `function_status`. Measured: of the 1,275 snapshot
alleles CPIC *does* grade, **408 (32%) map to nothing** — `ivacaftor responsive` (103),
`Malignant Hyperthermia associated` (98), `I/Deficient with CNSHA` (86), `II/Deficient` (53),
`III/Deficient` (37), the MT-RNR1 aminoglycoside-risk phrases (25 rows across **four distinct
strings** — 20 + 3 + 1 + 1, including a `Normal risk…`/`normal risk…` case-variant pair), `IV/Normal`
(5). Nothing warns.

> 🚧 **ROADWORKS — a status CPIC states arrives as an empty cell.**
> **Current state.** 408 of the 1,275 graded alleles (32%) map to `None` and are written out blank.
> No warning, in either mode, and the blank is indistinguishable from "CPIC has not graded this".
> **Expected state.** An unmappable-but-stated grade should be reported — it is the *source said
> something we cannot hold* case, not an absence — and aggregated by reason. It is not.
> **Guard.** After any `draft --gene`, count blank `function_status` cells and check each against
> CPIC's own table before compiling. Do not read a blank as "not graded".
A blank then means *unknown*, `_compare` skips it, and a module of all-blank statuses attests
`nothing_to_check`. Two of those phrase families (`I/Deficient`, `ivacaftor responsive`) are not
metabolizer function at all — they are a different axis this vocabulary cannot hold. Live example in
the corpus: `cyp2c19_star_alleles/allele_function.csv` ships `*40` and `*41` with blank status, because
CPIC states none for them.

### 6. The comparison is an exact `(gene, allele)` string match, and a spelling difference reads as silence

`_read_cpic` keys on CPIC's own spelling (`*2`); `_read_pharmvar` strips the gene prefix first
(`_normalize_allele`, `pgx.py:197`) because PharmVar publishes `CYP2C19*2`. Your authored cell is used
raw. Measured: rewriting one row as `CYP2C19*2` dropped it out of the comparison — `compared` fell
34→33, `findings` stayed 0, and the only trace was a clause in `detail`: *"1 authored claim(s) name an
allele no consulted authority states a function for, so they were not checked."* Read that clause.

### 7. An allele used and never defined is dead weight — warned, never blocked

`_cross_validate_haplotype_definitions` (`compiler.py:2932`) warns when `allele_function.csv` or
`diplotypes.csv` names an allele `haplotypes.csv` does not define, because a caller can never emit it.
`*1` is exempt (it is defined by carrying no variants). This is exactly the curation
`cyp2c19_star_alleles` performed: `*36`, `*37`, `*42` were drafted, used across 71 diplotype rows, two
declared `no_function`, defined by nothing — and removed. **The check does not run when
`haplotypes.csv` is absent**, so a table alone is never audited.

### 8. A table you may legitimately omit

`reference_examples/apoe_epsilon` carries `haplotypes.csv` and `diplotypes.csv` and deliberately no
`allele_function.csv`: *"an ε allele has no CPIC activity value or function category, and inventing one
to fill a table would be worse than leaving it out"* (`apoe_epsilon/README.md:61-63`).
`cyp2d6_structural` also omits it. If your named alleles are not graded by a panel, the honest module
has two PGx tables, not three.

## What does not exist

- **No `activity_score` on a diplotype, anywhere.** `DiplotypeRow` has no such column, so CPIC's
  `≥3.0` bounds and its 103,757 `n/a`s are reported by `pgx_draft` and dropped. Deliberate: the value
  is a bound, not a number, and *"add a bin by hand if you need one"* — `activity_phenotype.csv` is
  where a per-gene score→phenotype ladder lives.
- **No column for the raw source string.** When `map_function_status` cannot map CPIC's phrase, the
  phrase is gone — there is nowhere to keep it. Same for an unparsable `activity_value`.
- **No `source`, `dataset`, `fetched_at` or `status` column.** This is an authored table, not a fact
  sidecar; provenance for it lives in `licensing.csv`'s CPIC row, and the *only* machine-readable link
  between the two is `SourceRow.draft_digest`.
- **No coordinates, no rsID, no `variant_key`.** `_POSITIONAL_TABLE_KINDS` derives itself from models
  declaring both `chrom` and `start`, and this one declares neither. The compiler's own comment says
  that is *"a property of what they describe rather than a gap"* for this table specifically
  (`compiler.py:1135`) — unlike `repeat_alleles.csv`/`copynumbers.csv`, where 0.6 corrected the same
  sentence to call it a real schema gap.
- **No `--no-ensembl`-style escape and no per-row severity.** RM4's strict per-row tautology audit was
  **deleted** in RM73 and replaced by the per-leg skip; do not look for it.
- **No third authority in `enrich_pgx`.** ClinPGx and ClinGen dosage checks exist, but they answer
  `pgx_evidence_level` and `dosage_sensitivity` on other tables. Only the registry's `/check?pgx=`
  bundles all four into one report.

## Consumption today

Nothing anywhere reads a value out of `allele_function.parquet`. That is the finding.

**just-dna-lite / just-dna-pipelines**

- `just-dna-pipelines/src/just_dna_pipelines/module_config.py:501` — `allele_function` is the last
  entry in `LEAD_TABLES`, so a directory holding `allele_function.parquet` counts as a module for
  discovery and for the HuggingFace publisher. Discovery only; no column is read.
- `just-dna-pipelines/src/just_dna_pipelines/annotation/hf_logic.py:222-250` — `_lead_join_strategy`
  classifies it **`unsupported`**: no populated `chrom`/`start`, no `rsid`+`genotype`. The annotator
  raises `UnsupportedLeadTable` (`hf_logic.py:304`) and the per-module loop skips it
  (`hf_logic.py:602`). **An `allele_function`-led module cannot be annotated against a VCF at all.**
- `webui/src/webui/state.py:6017,6043` — `_authored_row_count` counts `allele_function.csv`'s rows to
  decide whether a spec goes to the registry's `/check` enrichment half or to `/validate`. A row count,
  not a value.
- No star-allele caller exists anywhere in the repo. The format's design assumes the consumer brings
  one (`pgx.py:15-18`), and this consumer does not.

**just-dna-registry (0.18.2)**

- `src/just_dna_registry/specfiles.py:63` — on the accepted-spec-file allowlist, so it uploads.
- `src/just_dna_registry/services/upgrade.py:158` — mapped to `AlleleFunctionRow` so the `--trim`/block
  planner can find columns a 0.4 compile would reject in a stored version.
- `src/just_dna_registry/api/routers/publish.py:446` + `services/enrich.py:1336-1400` — the opt-in
  `POST /{ns}/{name}/check?pgx=true` runs `enrich_pgx(write=False)` and surfaces conflicts as
  `PgxCheck.conflicts`. Gated on `declared_use`: `unstated` (the server default) skips every PGx source
  without asking, `commercial` is `422 license_refused`. Never moves `would_publish`.
- **Read by `manifest.stats.genes` as of compiler 0.6.6**, which is what populates the catalog's
  `version_genes` index (`db/repository.py:663`) and the card's gene chips
  (`services/catalog.py:247`). It came from `variant_stats` over `variants.csv` before that, measured
  `"gene_count": 0, "genes": []` on `cyp2c19_star_alleles`, whose 36 rows all say `CYP2C19`.
  **Fixed in compiler 0.6.6** (upstream **RM121**): `module_stats` takes the gene facets over every authored table, `variant_stats` keeps its `variants.csv` promise, and a module already published carries the stats its compile wrote — recompile and re-publish to be findable by gene. Re-measured on `cyp2c19_star_alleles`: `gene_count: 1, genes: ['CYP2C19']`.

**just-prs / just-prs-mcp** — zero references. Expected.

## Blanks for just-dna-lite

- **A gene stated only in a PGx table was invisible to catalog search, and is not any more**
  (compiler 0.6.6). `manifest.stats.genes` was `variants.csv`-only, so `registry_search(gene="CYP2C19")`
  missed every star-allele module — measured `genes: []` on the corpus's own CYP2C19 example. The
  compiler now unions `gene` over every gene-bearing authored table. **A module published before that
  release still carries the old stats.** Under the old behaviour a
  pharmacogenomics module is unfindable by the one facet anyone would search it with.
- **Nothing turns a diplotype call into an activity sum.** `hf_logic` classifies this family
  `unsupported` and skips it; there is no star-allele caller and no consumer of `activity_value`.
  *Ask:* accept a diplotype call (from PharmCAT/Aldy/Cyrius, or from a `haplotypes.csv`-driven join)
  and use `allele_function.activity_value` + `copy_number` to compute a per-sample activity score,
  respecting the *cis* rule. What breaks today: a module can state everything a phenotype call needs
  and the annotator still emits nothing for it.
- **`function_status` never reaches a report even when the sample's alleles are known.** The engine
  projects nothing from a lead table it cannot join, so a user whose VCF plainly carries `rs4244285`
  never sees "your `*2` allele has no function" — the fact sits in the parquet, unread. *Ask:* join
  `haplotypes.parquet` (which **is** positionally joinable) to `allele_function.parquet` on
  `(gene, haplotype_name) → (gene, allele)` and surface the function category alongside the variant.
  That needs no caller and no new schema.

## Ask the live schema

```
list_tables()                                   # is this the right table for my finding?
describe_table("allele_function.csv")           # every column, type, vocabulary, redundancy_bearing
table_requirements("allele_function.csv")       # required / any_of / defaulted / optional — read all four
get_template("allele_function.csv", stub=true)  # the <<REPLACE>> shape scaffold writes
lint_rows("allele_function.csv", "<csv text>")  # before writing anything to disk
authoring_reference()                           # everything at once, if you need the whole DSL
```

`describe_table` is the only correct source for the `function_status` pick-list and for the
`redundancy_bearing` map; both are generated from the live pydantic models. As of format 0.6.1 the
vocabulary is `pgx.VALID_FUNCTION_STATUS`, closed, and `authoring_requirements` reports `gene` and
`allele` as the only required columns with an empty `any_of` — but ask the tool, because that is what
the compiler will actually enforce on the day you run it.
