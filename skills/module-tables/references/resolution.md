# `resolution.csv` — the injected rsID↔coordinate lookup the compiler resolves from, and never fetches

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

`resolution.csv` answers one question: **where is this variant, and what alleles are there** — for a
`variant_key` an author wrote as an rsID alone, or as a coordinate with no rsID. It exists so the
*compiler* can answer it without owning a source convention: the enricher (the only tier with egress)
writes the facts down, the compiler reads them and resolves offline. Its audience is the toolchain,
not a downstream reader: "the compiler *consumes* it, the enricher *produces* it, and a verify-only
client may *re-check* it" (`schema/src/just_dna_format/resolution.py:9-11`). It is the hinge between
the authoring tier and the artifact tier, and it is the only table in the format that is hashed,
attested, shipped — and **materialized into other tables rather than published as one of its own**.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.resolution.ResolutionRow` (`schema/src/just_dna_format/resolution.py:49`), a standalone `BaseModel` with `extra="forbid"` — **not** an `AuthoredModel` |
| Parquet | **none, deliberately.** `'resolution.parquet' in compiler.ARTIFACT_PARQUETS` is `False` (verified against installed compiler 0.6.1) |
| Natural / dedup key | `(variant_key, locus_index)`. Several rows share one `variant_key` with distinct `locus_index` for a one-to-many rsID |
| Authored or machine-produced | machine-produced, human-overridable |
| Who writes it | `just_dna_enricher.enrich.enrich()` (`enricher/.../enrich.py:1550`), and `compiler.reverse_module` (`compiler/.../compiler.py:6256`) |
| Fact signature | `integrity.resolution_signature` over `resolution.RESOLUTION_FACT_FIELDS` (`schema/.../integrity.py:378`), published as `manifest.compilation.resolution_signature` |
| In `content_signature`? | **no** — absent from `compiler._INPUT_FILES` (`compiler.py:267`) |
| In `artifact.digest`? | **no** — no parquet, so no bytes in the Merkle root |
| Elsewhere in the manifest | byte-hashed into `manifest.derived` via `compiler._DERIVED_FILES` (`compiler.py:355`). That hash is **transport only**; the identity is the fact signature beside it |
| Legal homes | spec root **or** `derived/` (`just_dna_format.layout.DERIVED_SUBDIR`). Exactly one spelling — no `licensing.csv`-style rename. Both copies present → `layout.SidecarCollision`, an error, never a merge |

## Who populates what

- **enricher pass — `just-dna-enricher enrich <dir>`** (jmc: `enrich_module`). Writes every column
  the chain can establish. Chain, first hit wins: existing rows → Ensembl snapshot (`source=cache`) →
  ClinVar snapshot (`clinvar`) → live Ensembl (`ensembl-rest` / `ensembl-graphql`) → live gnomAD
  (`gnomad`) (`enrich.py:509-515`; the same table in `docs/audit/ENRICHER_FROM_CODE.md:221-227`).
  Ordering is chosen so adding a link cannot move an already-compiled module's digest: whichever link
  answers first decides `alts`, and `alts` is a fact.
- **enricher pass — `vrs mint`, and `enrich --no-vrs` to skip.** `vrs_id` / `vrs_spec` come from
  `vrs.mint_resolution_rows`; substitutions mint offline, indels need sequence access.
- **enricher pass — the rsID currency check** (online only). Stamps `rsid_status` and `rsid_current`
  onto rows it got an answer for, and **withholds on every row when NCBI is unavailable** rather than
  stamping `absent` (`enrich.py:1068-1078`).
- **enricher, derived not fetched — `authority`.** Read off the row's own `source` through
  `licensing.RESOLUTION_AUTHORITY_BY_LINK` (`enricher/.../licensing.py:267`), and filled **only where
  empty**, so a hand-written authority survives (`enrich.py:1135-1137`).
- **author (hand) — `source=manual`.** The escape hatch, and the only way a non-GRCh38 module gets a
  resolution table at all: `reference_examples/cyp2c9_warfarin_grch37/resolution.csv` carries three,
  hand-recorded from `just-dna-enricher hint recover` output (its README §"Where the coordinates came
  from"). Everything on such a row is the author's.
- **compiler-stamped — `reverse_module`.** Rebuilds the whole file from `weights.parquet` plus the
  positional parquets, writing 11 columns only and forcing `source="reversed"`, `status="resolved"`,
  `fetched_at=""` (`compiler.py:6461-6486`). Authored provenance is not preserved; it is *discarded*.

  > 🚧 **ROADWORKS — a reverse costs you the VRS ids, and the round trip still calls itself lossless.**
  > **Current state.** The eleven columns `reverse_module` writes do **not** include `vrs_id`,
  > `vrs_spec` or `caid` — nor `authority`, `rsid_alternates`, `rsid_current`, `rsid_status`. Seven
  > columns are dropped. Because none of them is in `RESOLUTION_FACT_FIELDS`, `compile → reverse →
  > compile` still reproduces `content_signature`, `resolution_signature` and `artifact.digest`
  > exactly, so **every identity check says the round trip was lossless while a minted VRS id has
  > silently gone**.
  > **Expected state.** The fixed point is over *facts*, and that is deliberate. What is missing is
  > any statement, in the artifact or the output, that the reverse dropped a mint.
  > **Guard.** Keep the authored `resolution.csv` in version control; do not treat a reversed one as
  > a replacement. After a reverse, re-run `enrich … vrs mint` before publishing, or the module ships
  > with no VRS ids and nothing will mention it.
- **nobody, ever — `fetched_at`.** It is in `enrich._FIELDNAMES` and in the writer, and **no enricher
  code path ever assigns it**: grepping `fetched_at` across `enrich.py` and `identifiers.py` returns
  only the field list and the writer line. All eleven reference-example `resolution.csv` files carry
  it blank. Treat a populated `fetched_at` as hand-written.
- **drafter — none.** `resolution.csv` is not in `just_dna_compiler.draft.DRAFTABLE` (verified). No
  `<<REPLACE>>` template exists for it, and `get_template`/`describe_table` refuse it (see *Ask the
  live schema*).
- **registry-stamped — none.** The registry stores and re-serves the file; it stamps nothing in it.

**The cells no tool may fill are on the *other* side of this table.** `resolution.csv` is what makes
`chrom`, `start`, `rsid`, `ref` and `alts` redundancy-bearing *in `variants.csv`*:
`hints.REDUNDANCY_BEARING` names `compiler.resolution._verify (rsid vs coordinate)` as the check for
`chrom` and `start` (`compiler/.../hints.py:82-86`). So `lookup_variant` reports a resolved locus with
`applied: false` and this refusal, verbatim (`enricher/.../lookup.py:471-474`):

> "resolution fills this into resolution.csv, which is where it belongs: authoring it instead would
> make the compiler's rsid-vs-coordinate check compare a source with itself, and for an rsid-only row
> that check would not run at all"

Preserve it. Copying a coordinate out of a lookup into `variants.csv` does not merely make the check
tautological — for an rsid-only row `_verify` never runs at all, so the row moves from *honestly
unverified* to *apparently verified* (`hints.py:11-15`).

## What moving this table moves

Measured on `reference_examples/hfe_hemochromatosis` (12 resolution rows), compiled with
`compile_module(resolve_with_ensembl=True, ensembl_cache=None, strict=False)` under
format/compiler 0.6.1. Baseline: `digest 6c6e103d14`, `content 44ad444979`, `resolution_signature
9717cdda1b`, `manifest.derived[resolution.csv] 8823130982`. Two consecutive compiles were identical.

| An edit here | `content_signature` | `resolution_signature` | `artifact.digest` | `manifest.derived[]` | attestation + closure |
|---|---|---|---|---|---|
| add a row (a second locus under one key) | same | **moved** `4b3ba76bba` | **moved** `98be09861d` | moved | **kept** |
| edit a fact cell (`start` +1, `vrs_id` cleared) | same | **moved** `765b03376d` | **moved** `6901648b80` | moved | **kept** |
| edit a provenance cell (`source: clinvar→manual`) | same | same | **same** | moved `234919a0b8` | **kept** |
| fill `fetched_at` | same | same | **same** | moved `7efbdd10bf` | **kept** |
| set `status=ambiguous` | same | same | **same** | moved | **kept** |
| reorder every row | same | same | **same** | moved `c3397879bc` | **kept** |
| re-run the producing pass (`enrich` again) | same | same unless the chain adds a **new** key — merge-not-clobber never re-asks about a covered one | as the fact signature | moves only if bytes move | kept |
| delete the file and re-derive | same | moves iff a fact moved | moves iff a fact moved | moves | kept |
| delete the file and **not** re-derive | same | **`None`** | **moved** `4d22d0dd67` | entry gone | **kept** |
| recompile under a newer toolchain | same | same | may move (parquet is not byte-stable across polars versions; P4 scopes reproducibility to a fixed `compiler_version`) | same | kept |

1. **Inside `content_signature`? No.** It is a derived table and is hashed by its own facts —
   `RESOLUTION_FACT_FIELDS = (variant_key, rsid, chrom, start, ref, alts, genome_build, locus_index)`
   (`resolution.py:37-46`). Left out: `source`, `authority`, `status`, `rsid_alternates`,
   `rsid_current`, `rsid_status`, `fetched_at`, plus the cross-references `vrs_id`/`vrs_spec`/`caid`.
   The stated reason for the provenance block is producer-independence — "a human-filled and an
   Ensembl-filled table carrying identical facts hash equal". `rsid_current`/`rsid_status` carry a
   second, sharper reason: they "describe *time-varying external state*", so inside the fact set the
   signature would move the day dbSNP merged something, with no change to the module
   (`docs/SCHEMAS.md:1503-1508`). `vrs_id`/`caid` are out so adding them moved no existing signature.
2. **Inside `artifact.digest`? No — this is the one table with no parquet at all.** Every other fact
   sidecar has one, so a provenance-only edit there still moves the digest because bytes differ. Here
   it cannot: rows 3–6 of the table above move the digest by exactly nothing. The digest still moves
   on a *fact* edit, but indirectly — through the coordinates the fill materializes into
   `weights.parquet` and the positional parquets.
3. **Does an edit here un-close the module? No.** The binding is `compiler.authored_input_entries`,
   which is `newline_normalized_file_entries(spec_dir, _INPUT_FILES)` (`compiler.py:385`), and
   `resolution.csv` is not in `_INPUT_FILES`. Measured: `manifest.verification` **and**
   `verification.closure` survived all eight perturbations above, including deleting the file
   outright. (For contrast, appending one `authorship:` entry to `module_spec.yaml` moves no identity
   at all and *does* drop both — `docs/MODULE_LIFECYCLE.md:346`.)
4. **Part of the canary? Yes, and it is the primary instrument.** Content unmoved + fact signature
   moved = row 3 of `MODULE_LIFECYCLE.md:269` — *"nobody authored anything and a derived fact changed:
   the upstream source said something different this time"*. `resolution_signature` is one of the
   three numbers a `hfe_hemochromatosis` reader watches. But **merge-not-clobber means a plain re-run
   can never produce that reading**: the chain skips every `variant_key` an existing row covers
   (`enrich.py:788-792`), so a source that quietly revised an answer moves nothing. Detecting drift
   *is* the delete-and-re-derive — note the signature, delete, re-enrich, compare — and no command
   performs that sequence (`MODULE_LIFECYCLE.md:301`, filed as RM83).

## Required to exist

**Never required, and never authored into existence.** A module compiles with no `resolution.csv`
(rows keep `chrom=None` and the compile *succeeds* with a warning). It is required by consequence:

- `--strict` refuses when any `VariantRow` still lacks a coordinate, so an rsID-authored module needs
  it to compile strictly. The registry says so plainly: `resolution.csv` must ride along on an upgrade
  "without which the strict recompile then fails" (`just-dna-registry/.../services/upgrade.py:455`).
- **Two later enricher passes hard-require it and raise without it**: `frequencies`
  (`enricher/.../frequencies.py:171-178`) and `assertions` (`assertions.py:182`) read resolved
  coordinates, not `variants.csv`. So the pass order is `enrich` → everything else.
- It drags in `licensing.csv`/`sources.csv`: `enrich()` calls `record_source_terms(..., "resolution")`
  for every distinct `authority` (`enrich.py:1261-1266`), so an Ensembl- or ClinVar-answered module
  acquires a licence row it did not have.
- It does **not** drag in a parquet, a manifest block of its own, or a `studies.csv` obligation.

## The columns that carry judgement

Ask the live schema for the column list. These are the ones whose *meaning* is routinely misread.

- **`variant_key`** — the join key, and it is the **authored** identity, frozen by
  `base.derive_variant_key`. For a resolved substitution that is a `ga4gh:VA.…` digest, not a
  position; `_locus_label` exists in the compiler precisely because the old message called one a
  position (`compiler/resolution.py:415-427`). It is **build-dependent**: a GRCh37 module keyed with
  GRCh38 defaults produces a table that silently joins to nothing (`grch37_build/README.md:92`).
- **`locus_index`** — `0` for a 1:1 resolution, `0..N-1` across the rows of a one-to-many rsID. It is
  **inside** the fact set, so a duplicate under one key is a malformed signed fact rather than a
  cosmetic slip (`compiler.py:6396-6400`).
- **`alts`** — comma-separated, and the single most consequential cell: whichever link answers first
  decides it, and it is a fact, so it decides the compiled bytes.
- **`source`** — *which link answered*: `cache`, `clinvar`, `ensembl`, `ensembl-rest`,
  `ensembl-graphql`, `gnomad`, `authored`, `reversed`, `manual` (as of format 0.6.1; the field is
  documented as open). Not a licensed source.
- **`authority`** — *which licensed source that link speaks for*, and the column `sources.csv.source`
  joins on. Empty is a real answer: `authored`, `reversed` and `manual` have no external authority to
  declare (`licensing.py:264-274`). Before the split existed, the compiler string-compared `source`
  against `sources.csv` and every enriched module was told `ensembl-rest` has no terms recorded (RM33).
- **`status`** — `resolved` / `not_found` / `ambiguous` (`vocab.VALID_RESOLUTION_STATUS`).
  `not_found` means *a source was asked and does not have it*, never *unchecked*.
- **`rsid_alternates`** — the full sorted candidate list when a reverse back-fill hit several rsIDs for
  the **same exact allele** (a real dbSNP merge). `rsid` then carries the deterministic lowest pick.
- **`rsid_current` / `rsid_status`** — recorded, **never substituted**. Writing a merged-into label
  into the artifact would migrate `variant_key` by network lookup and break the round-trip fixed point
  (`resolution.py:156-164`).
- **`vrs_id`** — a comma-joined **parallel array of `alts`**, one member per ALT, an empty member
  meaning "no id could be minted for that allele". The codec is public
  (`just_dna_format.vrs.split_vrs_ids`, `vrs.py:507`) because a second implementation loses the
  alignment. A length mismatch is refused at load; a *reordered* pair of the right length is caught by
  the compiler's `_verify_vrs_ids` (`compiler.py:2577`).

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **A re-run does not refresh anything. Delete to re-derive — and deleting discards hand-authored
   rows.** Existing rows are authoritative and merged verbatim (`enrich.py:788-792`). The cost is
   named upstream: "hand-authored `source=manual` rows — real, and not reproducible by re-running
   (`reference_examples/cyp2c9_warfarin_grch37` carries three)" (`MODULE_LIFECYCLE.md:412`). Move the
   file aside rather than deleting it if you may need the manual rows back.
2. **`--no-resolve` / `resolve_with_ensembl=False` is the master switch for resolution of *every*
   kind, injected table included — and the compile still succeeds.** Measured: with the table present
   and `resolve_with_ensembl=False`, `resolution_signature` is `None` and the digest is `4d22d0dd67` —
   **byte-identical to compiling with `resolution.csv` deleted**. The compiler does warn, naming the
   row count. Upstream refused a `--no-ensembl` alias with a reason: the compiler has *no* network
   branch, so such a flag would assert something false (S14, `history/CONSUMER_SUGGESTIONS_HISTORY_PRE_0_6.md:804`).
   The pin is permanent, not interim.
3. **You cannot hand-edit a coordinate on a VRS-minted row.** Changing `start` from `26092916` to
   `26092917` and leaving `vrs_id` alone failed the compile outright: *"stored vrs_id … does not match
   the id recomputed from 6:26092917 A>C … this is corruption, not a difference of opinion."* Clear
   `vrs_id` and `vrs_spec` when you touch `chrom`/`start`/`ref`/`alts`, and re-mint.
4. **A missing row means *unchecked*; `not_found` means *asked and absent*.** Three distinct
   non-answers all write **no row at all**: an unreachable live request (S20, `enrich.py:858-865`), a
   run where no link was consulted at all — `--offline` on a machine with no cache (RM98,
   `enrich.py:866-884`) — and a non-GRCh38 module. Do not read absence as a negative. `strict` still
   refuses on the key either way.
5. **`rsid_status=withdrawn` is fatal in `best_effort` too.** Measured: `strict=False` still refused
   with *"dbSNP has WITHDRAWN … this refuses in best_effort too, unlike a merged or absent rsid."*
   Nothing emits it — the automated check reports `absent` because a retraction is byte-identical to a
   never-assigned id through every live endpoint (`resolution.py:166-176`). It exists for a curator who
   established the retraction by hand.
6. **`status=ambiguous` compiles under `best_effort` and refuses under `strict`.** Measured both ways.
   The strict message: *"The label is a deterministic pick among equals, not a fact."*
7. **One rsID can name several *different* variants, and the genotype decides which.** Forward
   resolution is allele-aware: a locus whose `{ref} ∪ alts` cannot host the authored genotype is left
   out of the table entirely (`hosting_verdict`, three-valued — `True`/`False`/**`None`**, and `None`
   keeps the locus and says it did not decide). `pathogenic_clinvar` resolved to **340** rows before
   that fix and **337** after, and only then did `compile → reverse → compile` become a fixed point on
   all three signatures (its README, finding 0).
8. **A one-to-many rsID silently multiplies `weights.parquet`.** 2 authored genotypes × 2 resolved
   loci = 4 rows, and the non-matching member can be a *well-formed reference homozygote asserting a
   pathogenic finding*. Measured downstream: it would have put 2,579 such rows into one real genome's
   pathogenic section (S33, `CONSUMER_SUGGESTIONS_HISTORY.md:726`). The row-level answer is
   `locus_count > 1` on `weights.parquet` (RM87), not anything in this file.
9. **On a non-GRCh38 module the fill never runs, so your injected rows do not survive a round trip.**
   Measured upstream on `cyp2c9_warfarin_grch37`: `artifact.digest` and `content_signature` are fixed
   points, `resolution_signature` goes `c6fd3238… → a0558501…`, and the three `manual` rows are simply
   gone — reverse has no parquet to rebuild them from (its README, *The round trip, measured*).
10. **A header-only `resolution.csv` is not an empty one.** Measured: `resolution_signature` is `None`
    (the stamp is gated on the table having *rows*, `compiler.py:4090`) while the file is still
    byte-hashed into `manifest.derived`. `resolution_signature is not None` means "this module was
    resolved"; do not create the file to look tidy.
11. **Both homes at once is an error, not a merge.** Root **and** `derived/` → `SidecarCollision`,
    naming both paths, "because two fact-hashed, human-overridable copies are two legitimate claims"
    (`layout.py:81-88`). Running `enrich` on a downloaded split tree used to create exactly this.
12. **An older table legitimately lacks columns.** Three of the eleven reference examples with a
    `resolution.csv` (`apoe_epsilon`, `hfe_compound_het`, `hfe_hemochromatosis`) have no `authority`
    column at all — written before RM33. It loads as `None` and contributes nothing to the licence
    coherence check, which is the accurate statement, not a gap.
13. **The shape is still marked provisional** (`SCHEMAS.md:1537`) — no 0.4 module carries one, so the
    digest-freeze obligations have not engaged. Do not build a consumer contract on its columns.

## What does not exist

- **`resolution.parquet`.** Refused, explicitly and repeatedly, and it is *"the first repair anyone
  proposes"* (`SCHEMAS.md:1471-1481`). Three reasons: its provenance columns are deliberately outside
  the fact set, `reverse_module` cannot reconstruct half of them, and a downstream reader keying on it
  "would be reading the *lookup* rather than the *answer*". The right repair was RM43 — materialize
  the coordinate into the positional tables — and that shipped in 0.6 (`COMPILER.md`, *The positional
  fill*). Do not re-propose it.
- **Recovery of provenance after a round trip.** `reverse_module` writes 11 columns and drops
  `authority`, `rsid_alternates`, `rsid_current`, `rsid_status`, `vrs_id`, `vrs_spec`, `caid`. Filed
  once as a bug about `rsid_alternates` specifically; **it is not one and is not fixable there** — the
  information is outside the fact set precisely so it stays out of `weights.parquet`, so it does not
  exist in the artifact reverse reads. Emitting the headers would produce permanently empty cells
  (`compiler.py:6289-6297`). Re-run the enricher.
- **An `unchecked` member of `VALID_RESOLUTION_STATUS`.** Considered and rejected: "inventing one to
  describe a row that carries no fact is worse than writing no row" (`enrich.py:885-895`).
- **A `--no-ensembl` flag on the compiler.** Refused with a reason (S14): there is no network branch to
  disable, so the flag would be a permanent no-op implying the compiler might otherwise fetch.
- **A `licence` column on `ResolutionRow`.** Refused: a licence column here "would be wiped on every
  `compile → reverse → compile` cycle and could never be recovered" — hence `sources.csv` as its own
  fact table (`schema/.../sources.py:23-29`).
- **A link→authority map in the compiler.** Refused: it would hand the compiler a source convention,
  which is exactly what P2's 0.5 tightening removed (`resolution.py:121-132`). The map lives in the
  enricher.
- **A deprecated second spelling.** Unlike `sources.csv`/`licensing.csv`, this file has one name.
- **A drafter or a template.** Not in `draft.DRAFTABLE`; `describe_table`/`get_template` refuse it.
- **A `fetched_at` value.** Present as a column, written by nothing (see *Who populates what*).
- **A `--refresh` that re-asks without discarding overrides.** Filed as RM83, open.

## Consumption today

**The annotation consumer never sees this file.** The HuggingFace publish allowlist is
`[*ARTIFACT_PARQUETS, "manifest.json", "logo.png", "logo.jpg"]`
(`just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/v1_port/publish.py:39`; the same shape in
`just-dna-format/enricher/src/just_dna_enricher/upload.py:58-64`, which adds README candidates). No
CSV is in it. So an installed module has parquets and a manifest, and nothing downstream can read
`status`, `authority`, `rsid_status` or `rsid_alternates` at annotation time.

| Site | What it does |
|---|---|
| `just-dna-pipelines/src/just_dna_pipelines/v1_port/runner.py:228-260` — `prune_unmatchable_rows` | **The only code that reads the file in the consumer tree.** Raw `csv.DictReader`, builds `rsid → {ref} ∪ alts`, drops `variants.csv` rows whose genotype is not a subset, and counts rsIDs the resolver could not place. An authoring/porting step, not annotation. |
| `.../v1_port/runner.py:110, 152` | Deletes `resolution.csv` before enriching, and again after pruning — correctly applying the delete-to-re-derive rule. |
| `.../v1_port/pharmgkb.py:200` | Deletes it as a stale artifact before a rebuild. |
| `.../annotation/restoration.py:270-330` | Reasons *about* the expansion this table records but reads **`weights.parquet`**: `locus_count > 1` (RM87), with a `ref`-spelling grouping kept as the pre-0.6 fallback. This is the substitute for reading `resolution.csv`. |
| `.../annotation/hf_logic.py:231, 298` | Comments only, and **stale**: both say "the compiler applies `resolution.csv` to `weights.parquet` alone", which RM43 retired in format 0.6. The rsid-join fallback they justify is still correct as a fallback. |
| `just-dna-registry/src/just_dna_registry/services/enrich.py:471` | The server produces the file before compiling, exactly as an author would. |
| `.../services/upgrade.py:502` | Carries it forward verbatim on a re-publish, "so carrying them makes the re-publish cheap and deterministic instead of re-resolving everything". |
| `.../specfiles.py:110, 202, 234` | Recognized (`RECOGNIZED_SPEC_FILES`), stored, and emitted into `derived/` by `download(layout="split")`. Excluded from `SIGNATURE_INPUTS` by construction. |
| `.../db/facets.py:130-175` | The catalog's `resolution.trusted` verdict reads `manifest.compilation` fields only — never the CSV. |
| `just-prs`, `just-prs-mcp` | **Nothing.** Zero hits for `resolution.csv`, `ResolutionRow` or `resolution_signature`. |

Verdict: **the registry round-trips it, one porting script in `just-dna-pipelines` parses it, and the
annotation path reads none of it** — by design, since it is not published with a module.

## Blanks for just-dna-lite

- **Two comments in `annotation/hf_logic.py` (lines 231 and 298) assert a 0.5 fact that RM43
  retired.** They say the compiler applies `resolution.csv` to `weights.parquet` alone, which is why
  a `pharm_variants`-led module downgrades to an rsid join. Since format 0.6 the compiler fills
  `pharm_variants`/`haplotypes`/`heteroplasmy` from the same table, and the manifest publishes
  `positional_rows` / `positional_rows_placed` to say whether it worked. **Ask:** gate the downgrade
  on those two counts (or keep the schema probe and fix the reason), so a 0.6-compiled PGx module
  gets the position join it now qualifies for instead of silently falling back to rsIDs — which is
  worthless on a DeepVariant VCF with an empty ID column, as that same function already notes.
- **`prune_unmatchable_rows` parses the table by hand.** `runner.py:251` uses `csv.DictReader` and
  keys on `rsid`, ignoring `variant_key`, `genome_build`, `locus_index` and `status`. On a mixed-build
  or coordinate-authored spec it unions alleles across builds and cannot see a coordinate-keyed row at
  all. **Ask:** switch to `load_csv_rows(path, ResolutionRow, ...)` and filter on
  `genome_build == module build and status != "not_found"` — the compiler's own `_usable_loci`
  predicate. `extra="forbid"` would also catch a typo'd column that the DictReader drops silently.
- **Nothing downstream can read `rsid_status`, `rsid_alternates` or `authority`, because the file is
  not published.** A consumer rendering a report has no way to say "this module's rsID has been merged
  away in dbSNP", "this label was a deterministic pick among equals", or "these coordinates came from
  ClinVar rather than Ensembl" — the first two exist nowhere else, and the third only survives via
  `sources.parquet` at the module level, not per row. **Ask:** decide whether any of the three is worth
  a manifest field or an entry in the publish allowlist; today the answer is "silently unavailable",
  which reads as "nothing to say".

## Ask the live schema

`describe_table("resolution.csv")` and `get_template("resolution.csv")` **do not work** — both go
through `draft.DRAFTABLE`, which holds authored tables only, and raise
`'resolution.csv' is not an authored table of this format`. That is **routing**, not a verdict that
the file is unreadable or that its rows are untouchable — `describe_machine_table("resolution.csv")`
answers it in full, at essentials tier. (Nor is a hand-written row here forbidden: `source` documents
`manual` for exactly that, and `refresh_sidecar` recognises and protects such rows. What is wrong is an
**unmarked** cell, which nothing downstream can tell from a fetched fact.) The other live-schema routes:

```
authoring_reference()                      # JSON; ["models"]["ResolutionRow"] has every column,
                                           # type, category (required/defaulted/optional) and description
authoring_reference(schemas=true)           # raw JSON Schema, incl. the vocabulary annotations
list_tables()                              # names resolution.csv under `sidecars`
```

In Python, against the installed packages:

```python
from just_dna_format.resolution import ResolutionRow, RESOLUTION_FACT_FIELDS
from just_dna_format.vocab import VALID_RESOLUTION_STATUS, VALID_RSID_STATUS
from just_dna_format.layout import sidecar_candidates, sidecar_write_path
from just_dna_compiler.compiler import ARTIFACT_PARQUETS   # resolution.parquet is not in it
from just_dna_enricher.licensing import RESOLUTION_AUTHORITY_BY_LINK
```

To produce or update it: `enrich_module(spec_dir)` (jmc) / `just-dna-enricher enrich <dir>`. To read
what a compile made of it: `manifest.compilation.resolution_signature`, `resolution_sources`,
`resolution_mode`, `fully_resolved`, `resolution_subjects`, `expanded_keys`, `expanded_rows` — and
**never read `fully_resolved` without `resolution_subjects`**, since over an empty list the flag is
`all()` over nothing.
