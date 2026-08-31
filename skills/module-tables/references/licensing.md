# licensing.csv — what each source is, and on what terms this module used it

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

## What it is

`licensing.csv` answers one question per row: *this source, contributing to this layer of this
module, came under these terms, and the acquirer declared this use.* It is the module's attribution
and permissions ledger — the only place a compiled artifact records that ClinPGx asked to be cited,
that CPIC forbids sale, or that nobody could establish what the GWAS Catalog permits. Its audience is
three-deep: the **compiler**, which refuses to build a module carrying annotation-layer content that
forbids sale with no matching declaration; the **registry**, which projects the verdict onto a module
card; and the **report reader**, who is handed a licence footer naming what the report redistributes.

It is the fourth derived-fact sidecar and the one that inverts the family: everywhere else `source`
is *provenance* (which link answered) and is excluded from the fact hash, so a human-filled and a
machine-filled table hash equal. Here the source **is the subject** — "ClinPGx, at the annotation
layer, is CC BY-SA and forbids sale" is the fact — so `source` is inside the fact set and dropping it
loses the key (`sources.py:52-66`). A reader who has internalised `frequencies.csv` will read that
inclusion as a bug. It is not.

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.sources.SourceRow` (`schema/src/just_dna_format/sources.py:84`) |
| Filename | **`licensing.csv`** preferred; **`sources.csv`** deprecated-but-read, removal queued for 1.0 (`layout.py:37`, `layout.py:59`). Root or `derived/` — four legal paths, measured: `['sources.csv', 'licensing.csv', 'derived/sources.csv', 'derived/licensing.csv']` |
| Parquet | **`sources.parquet`** — the rename stops at the CSV. In `ARTIFACT_PARQUETS` (`compiler.py:299`), so in `artifact.digest` |
| Manifest key | **`manifest.sources`** → `manifest.Sources` (`manifest.py:640`). Also a published key that only a major may rename |
| Natural / dedup key | `(source, layer)` — `draft._CORE_DUPE_KEYS[SourceRow]` (`draft.py:92`) and `licensing.merge_sources_csv` (`licensing.py:497`). **Not enforced by the compiler** — see Gotchas |
| Authored or machine-produced | **both, genuinely.** A plain `BaseModel` with `extra="forbid"`, not an `AuthoredModel` — but the *only* fact sidecar in `draft.DRAFTABLE` and the only one with a template (S21) |
| Who writes it | eleven enricher passes via `licensing.merge_sources_file`; and a human, for a source read by hand |
| Fact signature | `integrity.source_signature` (`integrity.py:367`) over `sources.SOURCE_FACT_FIELDS` — **12 of 14** fields → `manifest.sources.signature` |
| In `content_signature`? | **No.** `_INPUT_FILES` (`compiler.py:267`) is `module_spec.yaml`, `variants.csv`, `studies.csv` and the table kinds. The filename enters no identity at all — measured below |
| In `artifact.digest`? | **Yes**, via `sources.parquet`. Also byte-hashed into `manifest.derived[]` (transport only) |
| Compile gate | `_check_license_gate` (`compiler.py:4815`), run **before `output_dir.mkdir()`** so a refusal leaves nothing written, and run by `validate_spec` too — measured |

## Who populates what

- **enricher pass — most rows, most of the time.** Eleven sites call `licensing.merge_sources_file` /
  `record_source_terms` (`licensing.py:386`, `licensing.py:536`), one per pass that consulted a
  source, each at its own layer. Measured call sites: `enrich.py:1262` (resolution),
  `frequencies.py:319` (frequency), `gene_metrics.py:344` (gene_metrics), `assertions.py:359`
  (clinical_assertion), `gene_validity.py:521` (gene_validity), `gwas.py:561` (gwas_effect),
  `clingen.py:263` (annotation), `clinvar_draft.py` / `pgx_draft.py:526` / `clinpgx_draft.py:415`
  (annotation), `clinpgx.py:352`. The terms themselves come from `TERMS_BY_SOURCE`
  (`licensing.py:365`) — nine constants as of enricher 0.6.4: `clinpgx`, `cpic`, `pharmvar`,
  `clingen`, `gencc`, `clinvar`, `ensembl`, `gnomad`, `gwas_catalog`. **A source with no constant is
  skipped rather than guessed at.**
- **author — the whole row, and this is the expected case for a hand-read source.** This is the one
  derived-family table a human is supposed to write, because a source read by hand leaves no `source`
  cell anywhere for the compiler's coverage check to find. It is in `draft.DRAFTABLE`
  (`draft.py:82`), under **both** spellings, and `get_template("licensing.csv")` /
  `blank_template` answers a real header. Before 0.5.4 it answered *"is not an authored table of this
  format"* — S21, and the surface that said it is the one an author reaches for.
- **drafter — one row each, at the `annotation` layer, plus two self-maintaining columns.**
  `clinvar_draft` writes `clinvar,annotation` and stamps `dataset` with the ClinVar release label;
  `pgx_draft` writes `cpic,annotation`; `clinpgx_draft` writes `clinpgx,annotation` with
  `license_sha256` taken from the `LICENSE.txt` inside the archive it downloaded. **None of them
  leaves a `<<REPLACE>>` here** — the stub template does (`stub_template("licensing.csv")` emits
  `<<REPLACE>>,<<REPLACE>>,,,,,,,,,,,,`, stubbing only `source` and `layer`), and since RM76 any
  `<<REPLACE>>` in this file is refused before type coercion. Measured: `licensing.csv line 2 []:
  Value error, unreplaced template placeholder '<<REPLACE>>' in sources.csv row: source.`
- **compiler-stamped — nothing in the CSV.** `SourceRow` is not an `AuthoredModel`, so it has no
  stamped-identity fields and nothing is refused as compiler-filled. The compiler adds `module` on
  the way to parquet and derives the whole `manifest.sources` block (`_sources_block`,
  `compiler.py:4953`); it never writes back into the CSV.
- **registry-stamped — nothing.** `normalize.IDENTITY_AUTHORITY_KEYS` lives on the manifest identity,
  not on any sidecar row. The registry only *reads* this table's manifest block.
- **machine-owned, self-maintaining — two columns, and they behave differently.**
  `dataset` is **blanked** by `withdraw_stale_dataset` (`licensing.py:560`) when a re-draft spans two
  releases: one column cannot name two releases, so the honest value is unknown and unknown is
  withheld. `draft_digest` is **re-stamped** by `stamp_draft_digest` (`provenance.py:141`), because a
  digest describes the table as it now stands whatever mixture produced it. Both override
  never-clobber deliberately; everything else in the row a curator wrote survives a re-run.
- **nobody, ever — the `literature` layer.** `VALID_SOURCE_LAYERS` contains `literature`, and there
  is deliberately **no `pubmed` entry in `TERMS_BY_SOURCE` and there will not be one** (RM46,
  `licensing.py:277-292`): a literature source's terms are per *article*, not per source. Article
  rights live on `LiteratureRow` via `article_terms` (`licensing.py:315`) instead. A `pubmed` row
  here would be "right for a module citing only ids and a false all-clear for one carrying a
  `provenance_quote` lifted from a CC-BY-NC article".
- **`acmg` records no row at all**, and that is the deliberate exception to "a pass that consults a
  source must write its `SourceRow`" (`acmg.py:26`): nothing from ACMG lands *in* the module, so
  there is nothing to account for. Same shape as `check_identifiers` (HGNC, OLS4 also unrecorded).

**Cells no tool may fill even though it could.** Measured against format 0.6.1:
`set(SourceRow.model_fields) & set(hints.REDUNDANCY_BEARING)` is **empty**, and the intersection with
`hints.ATTESTATION_BEARING` is **empty** too. This table carries no redundancy- or
attestation-bearing cell, so the usual refusal does not apply here. The refusal that *does* apply is
`check_declared_use` (`licensing.py:422`): the enricher will not fetch from a source whose terms it
could not establish, and will not fetch at all when `--use commercial` contradicts the terms —
`LicenseRefusal`, fatal in **both** modes, because "best_effort means *resolve what you can*, never
*take what you may not*". And the compiler's own refusal ends with the sentence that names the
limit: *"Declaring it is an assertion about how the module will be used — the compiler records that
assertion, it does not verify it."* Nothing can check a `declared_use`.

## What moving this table moves

Measured, not asserted. `reference_examples/hboc_palb2` (6 licence rows, 3 sources, 6 layers) copied
to a scratch tree and compiled with `compile_module(strict=False, resolve_with_ensembl=True,
ensembl_cache=None)`, one build per row, comparing `artifact.digest`, `content_signature`,
`manifest.sources.signature` and `manifest.verification.module_hash`. Baseline compiled twice:
**byte-identical** (digest `6876cc79…`, content `43ad8ac1…`, source signature `8ed72a5b…`,
module_hash `527abadc…`, closed).

| An edit here | `content_signature` | `sources.signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row (`pharmvar,annotation,…`) | unmoved `43ad8ac1…` | **moves** `→92e569c8…` | **moves** `→7e6d6d70…` | unmoved, still closed |
| edit a fact cell (`license` `CC0-1.0`→`CC0-1.0-edited`) | unmoved | **moves** `→dde188a1…` | **moves** `→1c0cb318…` | unmoved |
| edit a provenance-only cell (`fetched_at`) | unmoved | **unmoved** `8ed72a5b…` | **moves** `→3371f4f1…` | unmoved |
| fill `draft_digest` on every row | unmoved | **unmoved** | **moves** `→06a33f91…` | unmoved |
| reorder rows | unmoved | **unmoved** (order-independent) | **moves** `→6ccbeb7c…` | unmoved |
| **rename `licensing.csv` → `sources.csv`** | unmoved | **unmoved** | **unmoved** `6876cc79…` | unmoved |
| delete the file and re-derive | unmoved | **the whole `sources` block disappears** while deleted | **moves** `→f9b10391…` | unmoved |
| re-run a producing pass | unmoved | moves only if a *fact* changed (never-clobber means usually nothing) | moves if any byte changed | unmoved |
| recompile under a newer toolchain | unmoved | unmoved | may move (compiler/polars version) | unmoved |

1. **Inside `content_signature`? No.** `content_signature` covers the authored rows only. This
   table's identity is `source_signature(rows)` over `SOURCE_FACT_FIELDS` (`sources.py:68`) — twelve
   fields: `source`, `layer`, `license`, `license_url`, `license_sha256`, `attribution`, `notice`,
   `share_alike`, `commercial_use`, `redistribution`, `declared_use`, `dataset`. Left out, measured:
   **`fetched_at`** (producer noise — when the terms were read is not a fact about the module) and
   **`draft_digest`** (a fact about how *this module's table* was built, which moves on every
   re-draft while the terms and the release stand still — RM73). `dataset` is deliberately **in**:
   which release the annotations came from is part of the claim the row makes.
2. **Inside `artifact.digest`? Yes** — `sources.parquet` is in `ARTIFACT_PARQUETS`. So a
   provenance-only column no signature sees still moves the digest, because the bytes differ.
   `just-dna-lite` hit this independently and wrote it down: *"Panel digests move on every rebuild…
   `licensing.csv` carries a `fetched_at` stamped when the row is drafted, and `sources.parquet` is
   one of the four files `artifact.digest` is a Merkle root over"*
   (`just-dna-lite/docs/MODULE_RELEASE_0_5.md:92`).
3. **Does an edit here un-close the module? No.** The attestation binds the *authored* bytes only
   (`compiler.authored_input_entries`, `compiler.py:361`, newline-normalised since RM82), and this
   sidecar is not in `_INPUT_FILES`. Measured: `module_hash` stayed `527abadc…` and `closed` stayed
   `True` across a fact edit, a `fetched_at` edit, a reorder, a spelling rename and outright
   deletion. A re-enrichment leaves a closed module closed. (An `authorship:` append, by contrast,
   un-closes a module while moving no identity at all — different file, different rule.)
4. **Part of the canary? Yes — and it is the one sidecar whose canary reading has a second,
   near-identical cause.** MODULE_LIFECYCLE.md § 5.1: content unmoved + fact signature **moved** =
   the upstream source said something different this time. `manifest.sources.signature` is one of the
   numbers to watch (its worked example is `hfe_hemochromatosis`, three numbers, not nine). The
   second cause is local and documented at `MODULE_LIFECYCLE.md:445`: *`dataset` blanked, because the
   module now spans two releases; or a source recorded for the first time* — both move
   `source_signature` without anything upstream having changed. Detecting the real thing requires
   **delete-and-re-derive**, because `merge_sources_csv` is never-clobber and a re-run never re-asks
   about a row already recorded. Row 2 of that decision tree (`fetched_at` moved, signature unmoved)
   is reachable here only by a delete-and-re-derive or a toolchain change — measured upstream over
   three states.

## Required to exist

Nothing *requires* `licensing.csv`. **Seven of sixteen reference examples carry no licence sidecar
at all** (measured: 9 of 16 do — `cyp2c19_star_alleles`, `cyp2c9_warfarin_grch37`,
`cyp2d6_structural`, `hboc_palb2`, `hfe_hemochromatosis`, `mt_common_deletion`, `par_boundary`,
`pgx_slco1b1_simvastatin`, `shox_par1`). A module without one gets no `manifest.sources` block, and
`_source_checks` suppresses its under-declaration warning entirely so such a module warns exactly as
it did before the table existed (Principle 3).

What it becomes **effectively required** by:

- **any PGx content.** ClinPGx, CPIC and PharmVar are each CC BY-SA 4.0 *plus* a contractual bar on
  sale. `taints_commercial_use` fires, and with no `declared_use="non_commercial"` on that row the
  compile refuses in **both** modes. So a CPIC- or ClinPGx-drafted module cannot compile without this
  file — the drafter writes it, but a hand-copied PGx row leaves it to you.
- **anything you copied by hand.** `vocab.MISPLACED_COLUMN_REASONS['source']` tells an author to
  declare a hand-read source by adding a row here; there is no other place for it.
- **a `license:` in `module_spec.yaml`.** Not required, but if present it is compared, string-equal
  only, against every annotation-layer `license` — a warning in both modes, never adjudicated.
  Measured verbatim: *"module declares license 'MIT' but annotation-layer sources report
  ['public-domain']. Not adjudicated here — a compatible pair is legitimate, an incompatible one is a
  real problem, and only a human can tell which."*

What it drags in: nothing. It requires no other table, and no other table requires it.

## The columns that carry judgement

Run `describe_table("licensing.csv")` for the live list; these are the ones a human decides or
routinely misreads.

- **`source`** — free text by design, joining to the open `source` column on the other fact tables. A
  closed vocabulary would need revising every time a link is added. Consequence: a typo here is not
  caught by validation, only by the orphan warning — and see Gotchas for how weak that is.
- **`layer`** — closed vocabulary (`vocab.VALID_SOURCE_LAYERS`). **This is the column that decides
  what taints.** Only `annotation` carries a derivative-work obligation; a source consulted for a
  coordinate contributed a fact Ensembl reports identically. Get it wrong upward and the module stops
  compiling; wrong downward and a real obligation is silently dropped.
- **`share_alike` / `commercial_use` / `redistribution`** — three **orthogonal tri-states**, not a
  ladder. CC BY-SA, CC BY-NC and CC BY-NC-SA are three different combinations. `redistribution` is a
  genuine third axis: CC BY-NC forbids sale and *expressly allows* sharing, while an academic-use-only
  source (OMIM, dbNSFP) permits neither — recording the second as merely non-commercial understates
  it, and a module embedding it cannot be published at all, free or not. **`None` means the terms
  could not be established and must never render as "does not forbid".**
- **`declared_use`** — closed vocabulary (`unstated | non_commercial | commercial`). A claim about
  *the acquirer*, not about the licence, which is why it is a separate axis from the three flags.
  `unstated` is **not** a loophole: it is the absence of a declaration, which is exactly what the
  gate refuses on. Nothing verifies it, ever.
- **`notice`** — free text, and the only home for a restriction the three flags cannot express
  (PharmVar's *"not intended for direct diagnostic use or medical decision-making"*). It travels into
  `manifest.sources.notices` and into the consumer's report footer. Dropping it loses the only
  machine-carried statement of a non-permission restriction.
- **`attribution`** — the credit line the licence *requires*, "one lookup, not a reconstruction". It
  is what a redistributor must reproduce, and `just-dna-lite` renders it verbatim.
- **`license_sha256`** — pins the terms to the bytes they were read from, so an upstream policy
  change becomes a finding rather than a silent pass. Only a pass that read a `LICENSE.txt` out of
  the payload can set it honestly.
- **`dataset`** — inside the fact set, and load-bearing for the ClinVar tautology skip. Do not
  hand-edit it to "tidy up" a blank; a blank is `withdraw_stale_dataset` saying the module spans two
  releases, and it makes a real check run.
- **`draft_digest`** — machine-owned; leave it alone. Recomputed and compared, never trusted as a
  claim.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **The file is `licensing.csv`, the parquet is `sources.parquet`, and the manifest key is
   `manifest.sources` — and that is finished, not half-done.** `layout.py:20-36` states the trade
   explicitly: renaming the parquet or the manifest key breaks a reader, so both wait for 1.0. **Do
   not "finish" the rename.** Measured: renaming `licensing.csv` to `sources.csv` produced a
   **byte-identical `artifact.digest`** and an unmoved `source_signature` — the filename enters no
   identity at all, which is exactly why the rename was minor-legal.
2. **`sources.csv` is a live deprecation, not an error.** Warn-only, in both modes, removal at 1.0.
   Measured verbatim: *"sources.csv is the deprecated spelling of this table and will be removed at
   1.0 — rename it to 'licensing.csv'. It is read exactly as before until then; the compiled parquet
   and the manifest key keep their current names, which only a major may change."*
   `reference_examples/hfe_hemochromatosis` deliberately keeps the old spelling to hold the path open
   (its README says so at line 95) — and its own README table still calls the file `sources.csv`
   while eight sibling examples were renamed.
3. **Both spellings present is an error, and it is reachable by following the documented workflow.**
   Measured: a spec carrying `licensing.csv` and `sources.csv` refuses with `SidecarCollision`
   naming both paths. Not a merge and not newest-wins — these tables are fact-hashed and
   human-overridable, so two copies are two legitimate claims. The realistic route in is a
   `derived/`-split downloaded module plus a pass that wrote the flat preferred spelling; **always go
   through `layout.sidecar_write_path`** (`layout.py:154`), never `spec_dir / "licensing.csv"`.
4. **A duplicate `(source, layer)` row is an ERROR as of compiler 0.6.6**, in `validate` and
   `compile`, in both modes: `licensing.csv: duplicate row for key ('clinvar', 'annotation')`,
   re-measured against the installed release on `hfe_hemochromatosis`. Until 0.6.1 it compiled green
   under `--strict` — measured on `hboc_palb2`, appending an exact copy of row 2 gave
   `strict compile ok: True`, **no duplicate warning of any kind**, `manifest.sources.row_count`
   **7**, and a **moved** `source_signature` (`8ed72a5b…` → `b260669e…`), so two byte-identical
   claims never did hash the same as one; a duplicate carrying the *opposite* `commercial_use`
   compiled green too. `SourceRow` was in the drafter's dupe map and absent from the compiler's,
   which is the one file the compile licence gate reads (upstream **RM107**).

   **What this means for a module you inherit.** It may carry a pair, and it will stop compiling on
   the first run under this toolchain. That is the pair being noticed, not the module breaking — and
   the repair is a decision rather than a merge. `licensing.merge_sources_csv` does merge on
   `(source, layer)` and keeps the **last** row under the key, so where the two rows disagree — the
   case worth catching — it discards a claim without asking. Read both and choose. One source at two
   layers is unaffected, which is why the key is a pair.
5. **`None` is not `False`, and the module-wide verdict is most-restrictive-first.** Measured on
   `hfe_hemochromatosis`: two rows, `clinvar/annotation` (public domain, `commercial_use=true`) and
   `gwas_catalog/gwas_effect` (terms not established, `commercial_use` blank). Result:
   `commercial_use: None`, `unknown_terms_sources: ['gwas_catalog']`, `redistribution: True`. One
   unknown makes the whole module undetermined — never permitted. Do not "tidy" a blank
   `commercial_use` to `true` because the licence page reads permissive; `GWAS_CATALOG_TERMS`
   (`licensing.py:350`) carries a long comment explaining exactly why that one stays null.
6. **The gate fires on `layer == "annotation"` only, and `unstated` is not a loophole.** Measured
   three ways on `hboc_palb2`: `commercial_use=false` + `declared_use=unstated` at the `annotation`
   layer → **compile refused**, in the default (non-strict) mode; the same row with
   `declared_use=non_commercial` → **compiles**; the same restriction at the `resolution` layer →
   **compiles**. `validate_spec(strict=True)` returns the identical refusal, so the pre-flight and
   the compile agree.
7. **The orphan check is per *source name*, not per `(source, layer)` — and its own docstring's
   example does not actually work.** `_source_checks` claims *"a frequency declaration in a module
   with no frequencies really is stale"*. Measured: deleting `frequencies.csv` while keeping the
   `gnomad,frequency` row produced **no warning at all**, because `gene_metrics.csv` still cites
   `gnomad`. Only after deleting *both* gnomad-citing tables did it fire — and then it named the
   source, not the layer: `sources.csv declares 1 source(s) no table in this module uses:
   ['gnomad']`. The under-declaration half does work and is the more useful one: `sources.csv has no
   row for 1 source(s) the module's fact tables cite: ['gnomad'] — their terms are unrecorded.`
   Both are warnings that never escalate under `--strict`.
8. **`annotation` and `literature` rows can never be corroborated, and are exempt from the orphan
   half by design.** The annotation layer *is* `variants.csv` / `diplotypes.csv` / …, which carry no
   `source` column, so before the exemption every drafted module was told its one load-bearing
   licence row looked unused. `literature` joined unconditionally in 0.6 (S23, then RM46). The
   consequence for you: **nothing will ever tell you an `annotation`-layer row is wrong.**
9. **`draft_digest` and `dataset` interact, and the interaction decides whether a real check runs.**
   `clinical.tautology_reason` (`clinical.py:121`) skips the ClinVar `clin_sig` cross-check only on a
   **conjunction**: the `clinvar`/`annotation` row's `dataset` equals the label recomputed from the
   snapshot in hand, **and** `drafted_unchanged` says every `clin_sig` still hashes to what the
   drafter wrote. Either half failing runs the check in full, and `None` — no digest recorded, a
   module drafted before RM73 — counts as failing. That is deliberate: *"a module drafted before the
   digest existed has established nothing about its cells."* So the two self-maintaining columns are
   the safety valve. Blanking `dataset` (what `withdraw_stale_dataset` does when a module spans two
   releases) turns the skip off; re-stamping `draft_digest` after a second draft keeps it honest
   rather than silently dead. **Never hand-write either one.**

   > 🚧 **ROADWORKS — the RM73 guard is defeated in the example most people copy.**
   > **Current state.** Measured on the shipped `reference_examples/cyp2c19_star_alleles`: its
   > `licensing.csv` carries an **empty `dataset`** and **no `draft_digest`**. Both halves of the
   > conjunction above therefore fail, which is the *safe* direction — the cross-check runs in full
   > — but it means the module in the corpus that authors copy from carries the defect shape RM73
   > was written to close, and copying its licence table forward carries it along.
   > **Expected state.** A drafted licence row should arrive with both columns stamped. This one
   > predates the stamping and nobody backfilled it.
   > **Guard.** Do not copy a `licensing.csv` between modules. Let the drafter write it, and if you
   > must start from an example, blank the whole row rather than inheriting an empty `dataset` — a
   > blank you did not choose looks exactly like a blank the drafter chose.
10. **`--use non-commercial` (hyphen) and `non_commercial` (underscore) both work, and that was a
   real bug once.** `check_declared_use` runs the string through `check_vocab`, which canonicalises
   `-` to `_`, so the CLI spelling and the cell spelling cannot disagree. Measured: a
   `licensing.csv` cell reading `non-commercial` loads and compiles.
11. **A stub row that names only `source` and `layer` compiles green and records nothing.**
   `stub_template("licensing.csv")` stubs exactly those two cells; fill them and leave the rest
   blank and you have a legal row whose every permission is unknown. It will not refuse, it will not
   warn — it will show up in `unknown_terms_sources` and drag the module-wide verdict to `None`.
   That is honest, but it is not a licence record.
12. **A `<<REPLACE>>` here used to compile green under `--strict` and reach the published manifest.**
   RM76: `SourceRow` is not an `AuthoredModel`, so it inherited no placeholder guard, and
   `manifest.sources` published `"sources": ["<<REPLACE>>"]` **inside the block its own signature
   covers**. Fixed on the model (`sources.py:96`, `reject_template_placeholders`). Verified fixed in
   format 0.6.1 by measurement, not by changelog.
13. **0.1-era material carries none of this, and that is an era gap rather than a defect.** Measured
   over the 27 submitted bundles in `/data/sources/just-dna-registry/data/input/`: **0 of 27 carry
   `sources.csv` or `licensing.csv` under either spelling, and 0 of 27 declare `license:` in
   `module_spec.yaml`.** A typical bundle is `MODULE.md` + `module_spec.yaml` + `studies.csv` +
   `variants.csv` + a log. The table did not exist in 0.1, so its absence is not a fault; such a
   module compiles with no `manifest.sources` block and the registry projects the licensing facets
   as `None` — undetermined, honestly. No genuine break was found: nothing a 0.1 module legitimately
   contained is refused by today's `SourceRow`.
14. **`license` is an open string, and `manifest.sources.licenses` drops the nulls.** Several sources
   are an SPDX licence *plus* a bespoke clause, which no single identifier expresses — do not read a
   bare "CC BY-SA 4.0" as permission to sell; the CC grant covers the content while the surrounding
   terms restrict the use, and PharmVar states the two in adjacent sentences (`licensing.py:100`).
   The manifest facet is a sorted set of non-null values, so a source with no named licence vanishes
   from it: measured on `hfe_hemochromatosis`, `licenses: ['public-domain']` over two rows, because
   `gwas_catalog` has `license=None`. `unknown_terms_sources` is the field that says so — and it
   keys on `commercial_use is None`, not on `license is None`.
15. **`license_sha256` is almost never set.** Measured across the whole reference corpus: **1 of 18
   rows in 9 sidecars** carries one — `pgx_slco1b1_simvastatin`, whose ClinPGx row is
   `sha256:dd1f90ff…`, because `clinpgx_build` extracts `LICENSE.txt` out of the archive it
   downloaded. Every other row records terms read from a web page at some past moment with nothing
   pinning them. Treat an absent hash as "the terms were a lookup, not a capture".

## What does not exist

- **No enforcement of `redistribution`, anywhere in the four packages — and that is settled, not
  pending.** `taints_redistribution` (`sources.py:255`) is computed and summarised, and the docstring
  is explicit: *"a distribution right is not a use, so the three-state
  `unstated|non_commercial|commercial` axis has nothing to say about it. Gating on the act is right,
  and the act is a publish."* What is **rejected and stays rejected** is a second author declaration
  beside `declared_use`: symmetric, tempting, and it asks an author at build time about something
  they may not know until later. Do not propose it again. (Whether the *downstream* enforcement
  happened is a separate question — see Consumption.)
- **No `--no-licence-check` and no strict/non-strict split on the gate.** The refusal fires in both
  modes on purpose: `strict`'s single meaning is "produce a reproducible artifact", and whether the
  terms were accepted is unrelated to reproducibility.
- **No CLI-flag route to a declaration.** The gate is keyed on data carried by the module, never on a
  flag, so `compile → reverse → compile` stays a fixed point: `reverse_module` could never re-emit a
  flag, and a flag-gated compile would refuse on the third step. (Measured: reversing a module that
  carried `sources.csv` writes `licensing.csv` — the round-trip does not pick up a deprecation.)
- **No SPDX compatibility matrix**, and **no source→licence map in the compiler**.
  `_check_declared_license_agrees` (`compiler.py:4925`) does string equality only and warns rather
  than failing, because "failing the compile would make the format arbitrate a licensing dispute". A
  hardcoded map would be an un-injected reference (Principle 2) and would go stale — both halves of
  one did inside a single release (`api.pharmgkb.org` retired 2026-07-20; CPIC's licence page moved
  to the ClinPGx policy). The licence travels as data.
- **No `pubmed` row, ever** (RM46). See *Who populates what*.
- **No duplicate-key check.** `(source, layer)` is the key by every other writer's reckoning and the
  compiler does not enforce it — measured in Gotcha 4. This one is **not** a documented deferral: it
  is a gap the docs do not mention, and it looks like a genuine upstream defect worth filing.
- **No column recording *why* a source was consulted**, and no column recording that a source was
  read by a human rather than fetched. `source` is free text, so the honest way to record a hand-read
  source is to write the row yourself — nothing marks it as hand-written. **Except a literature
  service, which has no row at any layer**: Crossref, Europe PMC, OpenAlex, PubMed and Unpaywall read
  by hand still record nothing here, because their terms are per *article* and live on
  `literature.csv`. See *Who populates what*. The two rules meet here and it used to read as a
  contradiction — write the row yourself, at the one layer that is forbidden — which is exactly what
  the benchmark reference did before this was scoped.

  **The principle that settles it is upstream's own, from `S77`/`RM142`:** a pass that put no row in a
  table records no source. Consultation is not consumption, and reading a service that yielded nothing
  creates no obligation to record.

  **The residue is real and is stated rather than designed around.** A literature service you read by
  hand which yields no `literature.csv` row leaves *no trace anywhere* — not the licence table, not
  the manifest, not the log. `logs/authoring.log` is the natural home and nothing writes a "consulted
  X, took nothing" line into it; `record_override` only writes about cells. That is authoring work
  with nowhere to go, and it is put to upstream as `S82` rather than invented here — asking how they see a consultation being recorded, with *"it should not be"* named as a complete answer.
- **No re-check that a recorded `dataset` is still the source's current release.** Named as an open
  item (`ROADMAP_0_7.md:1083`, RM85): *"`SourceRow.dataset` records the release, so the fact is
  nearly there. What is missing is anything that acts on it."*

## Consumption today

**This is the most-read derived sidecar in the ecosystem.** Three consumers read it, at three levels.

- `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/annotation/report_logic.py:1093`
  `load_module_credits` — scans `sources.parquet` via `ModuleTable.SOURCES`, **filters to
  `layer == "annotation"`**, and projects `source`, `license`, `license_url`, `attribution`,
  `notice`, `dataset` and the three tri-states. The docstring cites SCHEMAS.md § SourceRow for the
  layer restriction and keeps the tri-states tri-state.
- `…/report_logic.py:1136` `build_report_credits` — deduplicates across every module in the report,
  keyed on `(source, license, attribution, notice)` rather than on the module, and records which
  modules pulled each one. Called at `report_logic.py:1315`.
- `…/annotation/templates/longevity_report.html.j2:942-976` — renders the **"Data sources and
  licences"** footer section: source + dataset, which modules used it, a linked licence, the
  attribution with the notice under it, and a Terms cell reading *Share-alike required* /
  *Non-commercial use only* / *Redistribution restricted*, each fired by `is sameas true|false` so a
  `None` never renders as a permission. All-`None` renders `<em>Not stated</em>`. Tested at
  `just-dna-pipelines/tests/test_report_logic.py:679, 706, 722`.
- `…/annotation/hf_modules.py:241` — discovery sets `ModuleInfo.sources_url` when
  `sources.parquet` is in the set `manifest.artifact.files` attests, probing only where there is no
  manifest. Comment: *"Every module the compiler emits carries one, and a report that embeds a
  module's curated prose owes its attribution."*
- `…/v1_port/publish.py:38` — the publisher's allow-list is now `[*ARTIFACT_PARQUETS,
  "manifest.json", "logo.png", "logo.jpg"]`, imported rather than restated, with a comment naming
  the S35 measurement: fifteen of sixteen reference modules published a manifest attesting files
  never uploaded, *"with `sources.parquet` in the dropped set every time it existed (so the module
  arrived carrying no licence terms at all)"*.
- **Registry** — `services/catalog.py:133` `_licensing` projects `manifest.sources` onto
  `LicensingInfo` (`models/api.py:90`): `commercial_use`, `redistribution`, `share_alike_layers`,
  `noncommercial_layers`, `nonredistributable_layers`, `unknown_terms_sources`, `licenses`,
  `attributions`, `declared_uses` — tri-state throughout. `db/facets.py:183` `version_facets`
  projects `commercial_use` / `redistribution` / `share_alike` into per-version SQL columns
  (`db/schema.py:255`, since registry 0.11).
- **`just-prs` / `just-prs-mcp` — nothing.** Grepped for `sources.parquet`, `licensing.csv` and
  `SourceRow`: no hits in either repo.

**Two verdicts on the S35 question, and they differ.**

*Fixed on both ends.* The enricher's publisher derives its allow-list from
`compiler.ARTIFACT_PARQUETS` (verified against the installed enricher 0.6.4:
`'sources.parquet' in upload._ALLOW_PATTERNS` is `True`), and `just-dna-lite`'s own publisher does
the same since commit `8f13142` (2026-08-18). On the read side, `sources_url` discovery and the
report footer are both live and tested. The "Not stated" *the brief remembers* is not the licence
footer's — that footer disappears entirely under `{% if credits %}` when there is no
`sources.parquet`, rather than saying "Not stated". The *Not stated* strings a reader would actually
have seen come from the "Modules in this report" table (`version`/`digest`/`weighting`/`source_url`,
template lines 925-930), which is a different gap (`just-dna-lite/CLAUDE.md:526-535`).

*Not fixed anywhere.* **The RM27 ask to the registry is unmet.** `SCHEMAS.md:1344` addresses it by
name: *"To the registry, concretely: enforce `manifest.sources.redistribution` at publish, at 0.6
integration. A module whose verdict is `false` must not be served to third parties, and one whose
verdict is `null` must not be treated as clear."* Grepped the whole registry at 0.18.2:
`redistribution` appears in exactly five places — a DDL column, the facet writer, the card projection,
the API model and a changelog line. **No publish path reads it**, and `Repository.search_modules`
(`db/repository.py:933`) exposes no licensing filter at all: its keyword arguments are `q`,
`category`, `gene`, `genome_build`, `owner`, `license`, `namespace`, `featured`, the two namespace
scopes, `curated_only`, and the five 0.17 fact-table flags. So `commercial_use`, `redistribution` and
`share_alike` are **write-only columns** — populated by `version_facets`, never selected, never
filtered on — which contradicts their own schema comment that *"a column is for something you filter
or sort by; the rest is payload."* The card path reads the manifest directly, not these columns.

## Blanks for just-dna-lite

- **Nothing reads `license_sha256`, so an upstream terms change is invisible to a consumer.** The
  column exists so re-enriching turns a policy change into a finding, but no consumer compares an
  old hash to a new one. *Ask:* on install or refresh, compare the incoming `license_sha256` against
  the one recorded for the same `(source, layer)` and surface a diff — it is the only mechanism in
  the format that can detect a source silently rewriting its terms, and it costs one string compare.
  Today a module whose ClinPGx terms changed under it re-publishes with a new hash and nobody looks.
- **Nothing reads `unknown_terms_sources`, so "we could not establish the terms" reads to a report
  reader exactly like "no obligations".** The footer renders *Not stated* per row, but a module with
  **no** `sources.parquet` at all renders no credits section whatsoever — `{% if credits %}`,
  template line 942. *Ask:* render an explicit "no licence terms recorded for this module" row rather
  than omitting the section, and surface `manifest.sources.unknown_terms_sources` beside it. Today a
  reader cannot distinguish a module with clean terms from one that never recorded any, and the
  second is the common case for the Gen-I ports.
- **Nothing enforces or filters on `redistribution`, at either end.** The registry stores it in a
  column nothing queries, and the report only shows it per credit row. *Ask (registry):* implement
  the RM27 enforcement verbatim — refuse or flag a publish whose `manifest.sources.redistribution` is
  `false`, treat `null` as not-clear, and expose `commercial_use` / `redistribution` /
  `share_alike` as search filters so the three columns stop being write-only. *Ask (lite):* refuse to
  include a module whose verdict is `false` in a report that will be shared, or say so at the top.
  Today a module carrying an academic-use-only source is served and rendered like any other, and the
  verdict that would have stopped it is sitting in the manifest, computed and ignored.
- **Nothing reads `dataset` to tell an author their source has moved on.** RM85 names this as open
  upstream. *Ask:* on refresh, compare each row's `dataset` against the source's current release
  label and report the drift — this is the one column that already knows which snapshot the module
  was built from.
- **Nothing reads `notice`, structurally.** It is rendered as free prose under the attribution, which
  is right for a human but means a restriction like PharmVar's *"not intended for direct diagnostic
  use"* cannot gate anything. *Ask:* at minimum, hoist any `notice` from a module in the report into
  the report's own disclaimer block, so a restriction the source stated survives into the artifact a
  reader actually keeps.

## Ask the live schema

Never write a column list or a vocabulary from this file — it is stamped **as of format 0.6.1 /
compiler 0.6.1 / enricher 0.6.4 / registry 0.18.2** and the models move.

```
list_tables()                              # confirm the current spelling and the family
describe_table("licensing.csv")            # live columns, types, descriptions, vocabularies
table_requirements("licensing.csv")        # what is required, what each column means
authoring_reference()                      # the cross-table view, including which layers exist
get_template("licensing.csv")              # header only
get_template("licensing.csv", stub=True)   # header + a <<REPLACE>> row (source and layer only)
lint_rows("licensing.csv", rows=[...])     # validate before writing
validate_module(spec_dir, strict=True)     # runs the licence gate as an ERROR, pre-flight
compile_module(spec_dir, strict=True)      # the gate again, before anything is written
```

Python, for the two facts a tool call will not give you:

```python
from just_dna_format.layout import preferred_spelling, is_deprecated_spelling, sidecar_relative_names
preferred_spelling("sources.csv")      # -> 'licensing.csv'
is_deprecated_spelling("sources.csv")  # -> True
sidecar_relative_names("sources.csv")  # -> the four legal paths

from just_dna_format.vocab import VALID_SOURCE_LAYERS, VALID_DECLARED_USE
from just_dna_format.sources import SOURCE_FACT_FIELDS   # what moves source_signature
from just_dna_enricher.licensing import TERMS_BY_SOURCE  # which sources the enricher can state
```
