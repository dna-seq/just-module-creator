# module_spec.yaml — the one required file: who the module is, what build it is in, and what its weights mean

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

Every other file in a spec directory is optional in some combination. This one is not: *"module_spec.yaml
is the only always-present file, and at least one recognised table must exist"*
(`src/just_module_creator/tools/authoring.py:102`). It answers four questions no CSV can — **what is this
module called and how does it present**, **what assembly are the coordinates in**, **what values apply to a
row that states none**, and (since 0.6) **what does the `weight` column mean**. It is the *input* half's
header; `manifest.json` is what the compiler turns it into (`schema/src/just_dna_format/spec.py:1-11`).

It is not a table. It has no rows, no parquet, no dedup key and no fact signature. Almost all of it is
metadata that moves neither identity hash — and exactly two parts of it are not, which is the trap the
Gotchas open with.

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.spec.ModuleSpecConfig`, with `ModuleInfo(Display)` and `Defaults` in the same file. `Weighting`, `Contribution`, `GenePanelSpec` and `Display` live in `just_dna_format.manifest` and are imported (`spec.py:42-48`). |
| Parquet it becomes | **None.** It becomes `manifest.json` (`manifest.ModuleManifest`, built at `compiler.py:5180-5245`). Two of its values reach `weights.parquet` anyway — `module.name` as the `module` column, and `defaults:` folded into `curator`/`method`/`priority` per row. |
| Natural key | Not a row table. One file, one module. Every block is `extra="forbid"`: `ModuleSpecConfig`, `ModuleInfo`, `Defaults`, `Weighting`, `Contribution`. |
| Authored or machine-produced | **Authored, entirely.** No drafter and no enricher pass writes it. `just-dna-compiler scaffold` writes a skeleton (`scaffold.py:83-113`). |
| Who writes it | The author (human or AI co-author), start to finish. |
| Fact signature | **None.** It has no fact hash of its own, so it can never be the moved half of the §5.1 canary. |
| In `content_signature`? | **Two parts only** — `genome_build` when it is not `GRCh38` (`integrity.py:247-249`), and `defaults:` folded into each row by `_resolve_spec_defaults` (`compiler.py:3819-3845`, RM37). Everything else is excluded by design: *"the identity and display half of `module_spec.yaml` … is excluded"* (`integrity.py:215-218`). |
| In `artifact.digest`? | The file itself, no — it is not a parquet. **`module.name` and `defaults:` are**, through `weights.parquet`. Measured: renaming `module.name` moved the digest and left `content_signature` byte-identical. |
| In the attestation binding? | **Yes, all of it.** `module_spec.yaml` is the first member of `_INPUT_FILES` (`compiler.py:267-272`), which is what `authored_input_entries` hashes (`compiler.py:361-386`). Any byte change drops the attestation and the closure. |

## Who populates what

- **author** — `module.title`, `module.description`, `module.report_title`, `module.name`,
  `module.icon`, `module.icon_set`, `module.color`, `module.version`, `genome_build`, `defaults.*`,
  `license`, `weighting.*`, `authorship[]`. All of it. There is no other writer.
- **drafter** — **none.** No provider writes this file. `clinvar_draft` (`clinvar_draft.py:533`) and `pgx_draft` (`pgx_draft.py:291`)
  *read* it (for `genome_build`) and refuse when it will not parse.
- **enricher pass** — **none writes it.** `enrich` reads `genome_build` out of it and will not guess:
  *"the enricher cannot know the module's declared build, so it will not choose one for you — fix
  module_spec.yaml"* (`enricher/src/just_dna_enricher/enrich.py:356-363`). A spec with **no**
  `module_spec.yaml` at all gets the format default instead (`enrich.py:349`).
- **compiler-stamped** — nothing in this file. The compiler *copies* it into the manifest and
  *coerces* one field: `module.version` is rewritten to SemVer in place by `ModuleInfo._enforce_semver`
  (`spec.py:252-267`), with the original kept on the non-field property `version_coerced_from`. That
  coercion is the codebase's one documented exception to report-never-repair, and it is announced by a
  compiler warning in both `compile` and `validate`.
- **registry-stamped** — `namespace`, `owner`, `canonical_id` (`normalize.IDENTITY_AUTHORITY_KEYS`).
  Authoring one is **refused with a named diagnosis**, not silently dropped: `_diagnose_authority_keys`
  runs `mode="before"` so the message says which key and why, instead of pydantic's generic *extra
  inputs are not permitted* (`normalize.py:90-123`). Measured — `module: {namespace: acme}` raises
  *"registry-stamped identity key(s), not authored fields"*. `version` is **deliberately absent** from
  that set: it is a genuine advisory authored field.
  The registry side of that contract is not the injected stripper you would expect. It rewrites your
  `module:` block **on disk** (`just-dna-registry/src/just_dna_registry/services/publish.py:89-134`,
  `normalize_module_block`) before hashing, because *"`content_signature(spec_dir)` loads the YAML with
  no authority keys of its own. A stored spec still carrying `namespace:` fails that load, falls back
  to the default genome build, and quietly produces the wrong signature"* (`publish.py:93-100`). It
  then stamps all three back plus `published_at` and a signature (`publish.py:574-585`). The strip
  happens at publish, so **a download is already clean and is republishable as itself** —
  `tests/test_v04.py:122` asserts `set(module) & IDENTITY_AUTHORITY_KEYS == set()`.
- **nobody, ever** — `panel:`. Deprecated in 0.6, removed at 1.0, and **nothing reads it any more**:
  its last machine reader moved to the licence row's `dataset` column (`spec.py:340-350`, RM4). It is
  published into the manifest and permanently unconsumed.

**Cells no tool may fill even though it easily could.** `hints.REDUNDANCY_BEARING` and
`hints.ATTESTATION_BEARING` are column maps over the *row* models; neither names anything in this file,
because this file has no columns. The refusals that bite here are different in kind and there are two:

- **`weighting` is not derivable and no tool offers to derive it.** It is three free-text strings and
  the format says why a vocabulary was refused: *"A closed vocabulary would have to enumerate scales
  nobody has surveyed"* (`manifest.py:1216-1233`). Nothing can read a module's weights and report what
  scale they are on — that is the author's statement about their own method.
- **`authorship` may only be appended to.** A later pass adds an entry; it never edits an existing one.
  A joint human+AI contribution is **two entries**, each with its own `kind`, *"so the mix is always
  spelled out and there is no lossy `hybrid` tag"* (`manifest.py:1146-1160`).

## What moving this table moves

Measured on `reference_examples/hfe_hemochromatosis`, compiled with `just-dna-compiler compile --strict`
against format/compiler 0.6.1. Baseline: `artifact.digest sha256:6c6e103d14f9…`,
`content_signature sha256:44ad44497940…`, attestation present, closure present.

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| append an `authorship:` entry | unchanged | n/a — none | unchanged | **both DROPPED** |
| delete the whole `weighting:` block | unchanged | n/a | unchanged | **both DROPPED** |
| add `license: CC0-1.0` | unchanged | n/a | unchanged | **both DROPPED** |
| add `module.version: draft` | unchanged | n/a | unchanged | **both DROPPED** (and `identity.version` becomes `0.0.0`) |
| reword `module.report_title` | unchanged | n/a | unchanged | **both DROPPED** |
| add a deprecated `panel:` block | unchanged | n/a | unchanged | **both DROPPED** (+ a deprecation warning) |
| rewrite the file `\n` → `\r\n` | unchanged | n/a | unchanged | **kept** (RM82) — but `manifest.inputs[].sha256` moved, `1c66a76…` → `33d69e3…` |
| rename `module.name` | **unchanged** | n/a | **MOVED** `323dfe190bd8…` | both dropped |
| add `defaults.priority: high` | **MOVED** `38c6afc18258…` | n/a | **MOVED** `f1bfa68ca62d…` | both dropped |
| flip `genome_build` GRCh38 → GRCh37 | **MOVED** `5b46e7b1821c…` | resolution sig unchanged | **MOVED** `7707b883062d…` | both dropped — **and a strict compile now FAILS** |
| recompile, nothing touched | unchanged | unchanged | unchanged | kept |
| delete the file and re-derive it | n/a — `reverse` fabricates a *different* file; see Gotcha 6 | | | |

1. **Is this table inside `content_signature`?** Only in the two places above. `genome_build` feeds the
   hash **only when it is not the default**, so every GRCh38 module keeps its existing signature byte
   for byte and only the misidentified ones move (`integrity.py:210-214`). `defaults:` is folded into
   each row first, because *"a value written once under `defaults:` and the same value written on every
   row are the same content"* — and a value equal to the `Defaults` model's own default is written back
   as `None`, which is why the reference example's `curator: ai-module-creator` costs nothing
   (`compiler.py:3833-3838`). The whole identity/display half is excluded on purpose.
2. **Is it inside `artifact.digest`?** The file has no parquet, so not directly. `module.name` becomes
   the `module` column of `weights.parquet` and `defaults:` becomes `curator`/`method`/`priority`, so
   both move the digest. A `report_title` reword does not — measured, unchanged.
3. **Does an edit here un-close the module?** **Yes — every single one, including a pure display
   reword.** `module_spec.yaml` is inside `authored_input_entries` in its entirety, and the binding is
   over bytes with no field-level exceptions. This is the one file where an edit that moves *neither*
   identity still drops the closure, which the §6.2 lifecycle matrix records for the `authorship:` case
   and which the measurements above extend to `weighting`, `license`, `version`, `panel` and
   `report_title`. The exception is line endings: `authored_input_entries` normalizes `\r\n` to `\n`
   since RM82 while `manifest.inputs[]` deliberately does not, *"two different questions asked of one
   file set"* (`compiler.py:376-384`).
4. **Is this table part of the canary?** **No, and it cannot be.** The canary is *content unmoved + a
   fact signature moved*, and this file produces no fact signature. Nothing upstream can change it —
   it has no source. Every move of it is an authored act.

## Required to exist

Required unconditionally. `ModuleSpecConfig` requires exactly one thing: `module:`, and inside it
`title`, `description`, `report_title`, `name`. Everything else is defaulted or optional
(`authoring_reference()['models']['ModuleSpecConfig']`).

What it drags in: nothing directly, but it *decides* what the rest of the directory means.
`genome_build` decides the identity key of every variant row (see Gotcha 2) and gates whether the
enricher will run at all. `defaults:` silently supplies `curator`/`method`/`priority` to every row that
omits them. `license:` is only checked against `licensing.csv` when that file exists.

## The keys that carry judgement

- **`weighting.scale` / `.method` / `.note`** — the author's statement of what their `weight` numbers
  mean and whether they travel. Nothing can infer it; see the whole of Gotcha 1.
- **`genome_build`** — the only key in this file that is *content* rather than metadata. Getting it
  wrong relocates every coordinate in the module.
- **`module.description`** — the catalog card's subtitle, and **this dossier is where its length norm
  lives**. Aim at **one short sentence, roughly 5-15 words**. Nothing enforces it: the field is a bare
  `str` with no validator and, unlike `icon_set` and `color` beside it, carries no
  `Field(description=...)` either, so an author gets no guidance from the model (format-tree `S63`).
  Measured on production 2026-08-21, six of the seven published modules are 25-79 words — two to five
  sentences, rendered whole, and the 60-word one occupies fourteen rows of its card. Say what this
  module distinguishes from the ones beside it in a search result; **methodology is the thing to keep
  out**, because it has three homes that persist and are meant for it (`weighting:`, `authorship:`,
  `README.md`) and because it is the half that repeats. Four of the five reference specs end with the
  byte-identical *"Curated from the GWAS Catalog (GRCh38), allele/strand-validated against dbSNP with a
  gnomAD r4 second witness."* — fifteen words that make four cards look alike. The eight-word
  `eric-mods/lactose_tolerance` is the calibration case *for*.

  A long one is **not** a defect to repair: `description` sits inside the attestation binding, so
  editing it costs a version. On a module already published it is a line for the decision list, never a
  silent rewrite.
- **`module.version`** — advisory, and **there is no versioning contract**. `2.0.0` does not mean
  reviewed, `1.0.0` does not mean unreviewed, and *"any rule of the form 'version N means stage X' is
  invented"* (MODULE_LIFECYCLE § 6.0). Never withhold a publish waiting for a milestone.
- **`authorship[].kind`** — an **open** tag set where the trust signal actually lives. `role` is closed
  (`audited|created|edited|reviewed`, measured); `kind` accepts an uncoined tag (`kind: ["wizard"]` was
  accepted) but **refuses an empty list** — `Contribution`'s own validator raises *"kind must list at
  least one tag (recommended: ['agent', 'ai', 'human', 'human_certified', 'human_expert', 'swarm',
  'team'])"* (`schema/src/just_dna_format/manifest.py`).

  > ⚠️ **CHECK — the quoted rationale belongs to a different rule.**
  > **Current state.** *"An empty `authorship: []` would quietly claim the module has no authors"*
  > (`scaffold.py`) explains why `module_spec_template` **omits** the block, not why anything is
  > refused. `ModuleSpecConfig.authorship` is `Field(default_factory=list)`, and
  > `ModuleSpecConfig(..., authorship=[])` was measured **accepted**.
  > **Expected state.** An empty *list of contributions* is legal and means "not stated"; an empty
  > `kind` **inside** one contribution is what raises. The behavioural claim above is right; only the
  > quote was attached to the wrong symbol.
- **`license`** — an SPDX id **by convention only**. The field is a bare `str | None` with no validator:
  `license: "not an spdx id at all"` was accepted. What the compiler does check is *agreement* with
  `licensing.csv`, and it warns in both modes and never adjudicates — *"a compatible pair is
  legitimate, an incompatible one is a real problem, and only a human can tell which"*
  (`compiler.py:4924-4950`).
- **`defaults.priority`** — the one `Defaults` field with no model default (`None`), so writing it is
  the only way `defaults:` moves `content_signature`.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **`weighting:` is invisible unless you already know it exists — and two real authoring sessions
   concluded it did not.** The scaffold generator skips every field it classifies as *optional*, with
   no comment and no placeholder: *"Optional blocks (`panel`, `license`) are left out entirely"*
   (`scaffold.py:88-90`). Rendered, `module_spec_template(name="demo_module")` emits **thirteen lines**
   — `schema_version`, `module.*`, `defaults`, `genome_build` — and no `weighting`, `license`,
   `authorship`, `panel` or `version`. Worse, `describe_table("module_spec.yaml")` **cannot answer**:
   `known_kind` appends `.csv` and refuses with *"Unknown table kind"* (`_shared.py:142-151`), and the
   error names the CSV kinds without pointing at the one call that would have worked. Coverage in the
   reference corpus: **1 of 16** examples declares `weighting:` (`hfe_hemochromatosis`), 1 declares
   `license:`, 1 declares `authorship:`, 2 declare a `version:`, 0 declare `panel:`.
   **Read the one declaration verbatim — it is a *negative* one, and that is the point:**
   ```yaml
   weighting:
     scale: none — this module authors no weights; every `weight` cell is empty
     method: clinical zygosity call from ClinVar's 2★-and-above assertions, not a graded score
     note: >-
       Read gwas_effects.parquet instead of inventing a weight from these rows, and read it per trait:
       … Nothing in that set is poolable into a single score.
   ```
   **Absent means the module has not said, which is not the same as saying its weights are
   comparable** (`manifest.py:1290-1297`). A consumer must read absent as *do not aggregate across
   modules* (INTEGRATION_0_6 § 456-459). And **an empty block is silently the same as absent**: a
   `weighting:` whose fields are all null validates, reaches the manifest as
   `{"scale": null, "method": null, "note": null}`, produces **no compiler warning** (measured: zero
   mentions of "weighting" in the compile output), and the one consumer that reads it renders it as
   *Not stated*. Write all three fields or none.
2. **`genome_build` decides the identity key, and it is the one key here that moves content identity.**
   A GRCh37 module minted GRCh38 VRS allele ids until `_restamp_for_build` — HFE C282Y is 6:26,092,913
   on GRCh38 and 6:26,093,141 on GRCh37, and the GRCh37 module's key was *byte-identical* to the
   GRCh38 one for a locus 228 bp away (`compiler.py:901-922`). Two consequences you will meet:
   flipping the declaration on otherwise untouched CSVs moved both hashes (measured), and a
   `--strict` compile of the flipped module **failed** — the existing `resolution.csv` was skipped
   (*"compiler is GRCh38-bound, module genome_build is 'GRCh37' — positions are not re-resolved
   cross-build (RM15)"*) leaving 11 unresolved rows. `reverse_module` reads the build from
   `manifest.json` for exactly this reason: it lives in no parquet column
   (`compiler.py:6071-6078`). And a typo'd `genome_bild:` is a hard error precisely so it cannot
   silently leave the default in force (`spec.py:302-307`).
3. **A digitless `version:` becomes `0.0.0` — a legal SemVer nobody wrote.** Measured on 0.6.1:
   `abc`, `draft`, `unreleased` and `-` all coerce to `0.0.0`, and it **reaches the artifact** —
   compiling with `version: draft` wrote `identity.version: "0.0.0"` into `manifest.json`. This is
   S42, accepted as a real defect and filed as **RM103**, open; refusing it is a *new refusal* and
   therefore a minor, not a patch. The mitigation exists today: both `compile` and `validate` warn
   naming both values, and `ModuleInfo.version_coerced_from` holds the authored string. The
   digit-bearing coercions are working as intended and are not in question (`v2` → `2.0.0`,
   `3` → `3.0.0`, `v1.2.3-beta` → `1.2.3`). **A float is refused outright** and the message is the
   feature: YAML reads `1.10` as `1.1`, so *"a version is quoted or it is guessed"*
   (`spec.py:229-247`). Quote anything with a dot.
4. **Editing this file un-closes the module while moving no identity — including a display reword.**
   Every probe in the matrix above dropped both the attestation and the closure. That is correct and
   it is the design: *"a review that changes nothing is an attestation of zero changes, so un-closing is correct"* (MODULE_LIFECYCLE.md:700). So the
   reviewer appending their `authorship:` entry is the one who must re-close. Run
   `just-dna-compiler close <spec-dir>` after the append, never before. Closing is deliberate and is
   *"never stamped by a passing check"* (`compiler.py:4617-4621`).
5. **`panel:` is inert.** It warns, it reaches the manifest, and **nothing reads it**. Measured:
   adding a `panel:` block to the reference example moved neither hash. Its one machine reader — the
   enricher's ClinVar `clin_sig` cross-check — now reads the drafted-from release out of the licence
   row's `dataset` column. Delete it; *"the rows it describes are the authored variants.csv rows, and
   nothing else is lost"* (the compiler's own deprecation text).
6. **`reverse` does not give you this file back — it fabricates one.** Reversing the compiled baseline
   produced a `module_spec.yaml` that had lost `weighting:`, `license:`, `panel:`, `authorship:`,
   `defaults.priority` and `module.version`, and had **invented** `title: Hfe Hemochromatosis`,
   `description: 'Annotation module: hfe_hemochromatosis'`, `icon: database`, `color: '#6435c9'` from
   the module name and the flag defaults. `genome_build` is deliberately *not* in that fabricated
   class — it is read from the manifest, because *"a wrong title is cosmetic; a wrong build relocates
   every coordinate"*. Reverse is a fixed point, never a backup (FAQ).
7. **Because `weighting` is outside `content_signature`, two modules that differ only in it collide.**
   The registry deduplicates on `content_signature` and refuses a match under a *different*
   `(namespace, name)` with `409 duplicate_content` (`publish.py:637-676`). A weighting declaration
   moves no content, so **you cannot publish "the same panel, differently weighted-and-documented"
   under two names.** The registry found this by accident writing its own suite
   (`just-dna-registry/tests/test_format_06.py:118-121`) and then pinned it deliberately at `:237`.
   The same is true of `license`, `authorship`, `panel` and every display field.
8. **`defaults:` is content, not metadata.** Adding `priority: high` moved `content_signature` as well
   as the digest, because RM37 folds the block into every row before hashing. The corollary is the
   useful half: writing `curator: ai-module-creator` explicitly on every row and writing it once under
   `defaults:` are **one content**, so a `compile → reverse → compile` cycle no longer moves the
   signature over where the author happened to type it.

### The 0.1-era corpus, loaded on 0.6.1 — measured

All 27 submitted bundles in `/data/sources/just-dna-registry/data/input/*.zip` were extracted and their
`module_spec.yaml` loaded with the installed `ModuleSpecConfig` (format 0.6.1).

- **Genuine breaks: 0.** 27 of 27 validate. Nothing a 0.1-era spec legitimately contained is refused —
  CONSTITUTION P3 holds on this file.
- **Live deprecations hit: 0.** None carries `panel:`, so none trips the 0.6 deprecation.
- **Era gaps: 27 of 27**, in the same shape every time. Not one carries `weighting:`, `license:`,
  `authorship:` or `module.icon_set` — none of which existed when they were written. Absence is not a
  fault; a module of that vintage could not have had them.
- **One measurement worth carrying:** all 27 write `module.version` as an **unquoted YAML integer**
  (`version: 5`), and all 27 therefore coerce — `1`→`1.0.0` … `5`→`5.0.0`. That is the RM17 widening
  earning its keep on a corpus the format measured separately at 26 of 61. All 27 also carry
  `defaults.priority` (`medium`), which is the field `reverse_module` drops.
- Zero carry a registry authority key, so `strip_authority_keys` has nothing to do on this corpus.

## What does not exist

- **No `describe_table` for this file.** The tool surface covers CSV kinds only; `authoring_reference()`
  is the sole route (see the last section). Not a documented deferral — just a gap.
- **No SPDX validation on `license:`.** Any string is accepted. The compiler compares it to
  `licensing.csv` for *equality* and nothing more; an SPDX compatibility matrix was refused as
  *"world-knowledge that would go stale, and the compiler is not the tier that should hold it"*.
- **No registry override of `license:` either.** Three upstream strings used to say there was — two
  of them `Field(description=…)`, which reach an author through `describe_table` and
  `authoring_reference` — and all three were corrected in 0.6.6 (upstream **RM111**), so the
  descriptions you read from those tools now say what the compiler actually does: warn when the
  declaration contradicts the annotation-layer sources. The registry never assigns `manifest.license`:
  `_finalize` stamps six fields on publish and that is not one of them; the only other references are
  reads into a DB column and a facet. Verified by grep in both directions, and by upstream's own
  correction afterwards. **So whatever an author writes becomes a public exact-match facet
  unchallenged** — the guard is the compiler's soft warning against `licensing.csv`, nothing else.
  Write it as if nobody will correct it, because nobody will.
- **No precedence field inside `weighting:`.** A typed rule saying "use the GWAS effect where `weight`
  is null" was considered and **refused**: *"That would put two methodologies in one summable column,
  which is the defect the report is about"* (`manifest.py:1226-1231`). A consumer chooses a table
  wholesale, never blends row by row.
- **No sentinel version for an unreadable one.** Rejected under RM103: *"there is no such SemVer. Every
  three-number string is a legal version, so any sentinel is someone's real one."*
- **No versioning contract at all.** The registry enforces exactly two things — that a version parses
  as SemVer (`api/routers/publish.py:181-182`) and that `(namespace, name, version)` is new. **Ordering
  is client-side only**: `client_cli.py:363-365` refuses a version ≤ current latest, and any direct
  HTTP caller bypasses it; `recompute_latest` then just keeps the higher one as latest
  (`repository.py:673-680`). Confirms MODULE_LIFECYCLE § 6.0 — do not invent a milestone ladder.
- **No conflict check between authored `module.version` and the published version.** There is no code
  path anywhere in the registry that compares them; no warning, no error. The authored one is kept
  verbatim in the stored yaml and *"the registry stamps `Identity.version` from the request regardless,
  and that always wins"* (`publish.py:81-85`). Stripping it was the policy through 0.10 and was
  **reversed** — it *"discards author intent for no gain"*.
- **No `authorship` on a catalog card, and it will not be added.** Refused as policy, with the reason:
  *"the card's claims [are] ours, while `authorship` is the author's statement about who reviewed their
  own work"* (`just-dna-registry/docs/CONSUMER_SUGGESTIONS_HISTORY.md:1019-1021`, restated at
  `docs/CHANGELOG.md:720`). It reaches an API consumer only inside `ModuleDetail.latest_manifest`.
- **No `verification` facet either**, for the same class of reason: *"a registry that let you sort by
  someone else's unverifiable pass would be lending it our credibility"* (`models/api.py:201-203`).
- **No `weighting` reconstruction on reverse**, and it is pinned by a test rather than left to
  convention (ROADMAP_HISTORY: *"`weighting`'s reverse-drop is pinned"*).
- **No fact signature and no parquet.** Do not look for either.

## Consumption today

The full read map, from a sweep of `just-dna-lite` (incl. `just-dna-pipelines`, `webui`), `just-prs` and
`just-prs-mcp`. `just-prs` consumes no just-dna module metadata at all; `just-prs-mcp`'s `manifest.json`
is a Claude Desktop extension manifest, unrelated.

**From `manifest.json`:**

- `just-dna-pipelines/src/just_dna_pipelines/annotation/hf_modules.py:642-652` — `_weighting_summary`
  reads `weighting.scale/.method/.note` and joins the non-empty ones with `" · "`. Verbatim, never
  parsed; returns `None` when the block is absent **or** entirely empty.
- `.../hf_modules.py:695-697` — `read_module_provenance` returns `(identity.version, artifact.digest,
  weighting)`. The digest is *displayed*, never verified: nothing in that repo calls `verify_manifest`.
- `.../annotation/hf_logic.py:635,644` → `.../annotation/report_logic.py:1238` →
  `.../annotation/templates/longevity_report.html.j2:929` — the weighting string reaches one report table cell,
  rendered as *Not stated* when empty.
- `.../hf_modules.py:140,153` — the **remote** (HF/HTTP) path validates the whole `ModuleManifest` and
  takes only `artifact.files[].name`.
- `webui/src/webui/state.py:6162-6168` — `identity.version/.namespace/.name` and
  `display.title/.icon/.color` for the local-module scan.
- `just-dna-pipelines/src/just_dna_pipelines/module_registry.py:277-288` — reads `manifest.json` as a
  raw dict and copies only the `display` block into `modules.yaml`.

**From `module_spec.yaml` directly:**

- `.../module_config.py:548-562` — `spec_version()` reads `module.version` only, coercing legacy
  `2`/`v2`, because the compiler leaves `identity.version` null until publish.
- `.../module_registry.py:30,46-54,137` — parses the full `ModuleSpecConfig` and uses `module.name`.
- `.../agents/module_creator.py:339-362` and `webui/state.py:5530-5545` — the `module:` block only
  (name/version/title/description/report_title/icon/color).
- Upstream, `just_dna_enricher/enrich.py:356-363` reads `genome_build` and refuses to guess when the
  file will not parse.

**By the registry** (`/data/sources/just-dna-registry`; `just-dna-marketplace` is a symlink to it, one
checkout). Its relationship to this file is the strongest of any consumer, because it is the only one
that *requires* it:

- `src/just_dna_registry/specfiles.py:224` — `REQUIRED_SPEC_FILES = (SPEC_YAML,)`. `module_spec.yaml` is
  the **only** file a publish must carry; *"composition is the compiler's judgement, not the
  registry's"*.
- **An uploaded `manifest.json` is never read.** The publish contract is spec-only and the server
  recompiles: the client refuses to send one (`client.py:46-47`, `_SKIP_UPLOAD_NAMES`) and `_finalize`
  overwrites any that arrives (`publish.py:586`). So *everything* the registry knows about a module
  outside its CSV rows comes from this file, through the compile it runs itself.
- `publish.py:469` — `validate_spec(spec_dir, IDENTITY_AUTHORITY_KEYS)`, deliberately **modeless**,
  before enrichment; then `compile_module(..., strict=settings.compile_strict)` at `:522-547`.
- **`weighting` is stored, displayed verbatim and indexed.** `services/catalog.py:211-219` (`_weighting`
  — *"verbatim, or `None` if it has not said"*) reaches `ModuleDetail.weighting`; `db/facets.py:216`
  projects `weighting_declared = int(manifest.weighting is not None)` into a column
  (`db/schema.py:288`) that `?weighting_declared=` filters on. The card carries only the boolean. The
  facet's own note: *"this says the module **stated** what its weights mean, not that it has any …
  an absent declaration answers it with *no*"* (`facets.py:213-215`), and an absent block renders as
  `null`, never as an empty one (`tests/test_format_06.py:156-199`).
- `genome_build` → a column (`db/schema.py:45`), a card field (`catalog.py:268`), and a `?genome_build=`
  filter. `license` → a column and an exact-match facet. `stats.genes`/`stats.categories` → join tables
  behind `?gene=` / `?category=`.
- `authorship`, `panel`, `report_title`, `defaults.*`, `schema_version` → carried in `manifest_json` and
  visible only inside `ModuleDetail.latest_manifest`. No column, no card field, no facet.

**Verdict.** `weighting` **is** read — by the registry (stored, shown, faceted) and by exactly one path
in `just-dna-lite` (display only, local dirs only). **No code anywhere branches on `scale`, compares two
modules' scales, or gates arithmetic on it.** `genome_build` and `license` are read by the registry and
by nothing in the annotation path. `defaults`, `authorship`, `panel`, `report_title` and
`schema_version` are read by nothing at all beyond being carried.

## Blanks for just-dna-lite

- **Gate the "Net weight" headline on `weighting`, or annotate it.** `report_logic.py:943-951` and
  `:1014` sum `weight` per module and `.../templates/longevity_report.html.j2:813,859` render it as a "Net weight" stat box beside the weighting cell at `:929` —
  but the two are **not wired to each other**. Two modules' Net weight numbers appear side by side in
  one table with no scale caveat on either. The block was added (RM92 / S36) precisely to make that
  safe, and INTEGRATION_0_6 § 456 states the ask as *"if you aggregate `weight` across modules, stop,
  or gate it on `manifest.weighting`."* Today an absent block changes nothing about what is rendered.
- **Carry `weighting` down the remote path.** `hf_modules.py:140` has the whole validated
  `ModuleManifest` in hand and takes only `artifact.files`; `read_module_provenance` then returns
  `(None, None, None)` for any HF-discovered module because `local_module_dir` is `None`. So every
  remotely-discovered module renders *Not stated* regardless of what its manifest says — the data was
  fetched and dropped three lines earlier.
- **Read `genome_build` before joining positions.** No consumer dereferences it, in the manifest or the
  spec; `cli_annotate.py:264-268` falls back to the literal `"GRCh38"` from the *sample* and
  `agents/module_creator.py:277` hardcodes the same string into every scaffolded spec. A GRCh37 module
  joined against a GRCh38 VCF produces silently wrong rows, and the module has been declaring its build
  all along.
- **Surface `authorship` as the trust signal it was built to be.** `Contribution.kind` exists so *"a
  consumer routes its scrutiny by `kind`"* (`manifest.py:1146-1168`). Nothing reads it, so a report
  cannot distinguish an AI-only module from one two medical geneticists reviewed — which is the one
  signal the format offers about how much a module was worked on.
- **Read the module-wide `license`, or say why not.** The report reconstructs licensing from
  `sources.parquet` (`report_logic.py:1093-1133`) and never reads `manifest.license`, so the author's
  own declaration — and any *disagreement* the compiler already warned about — reaches no reader.

## Ask the live schema

Nothing in this file that is a *value* is stable across releases; everything quoted above is stamped
format 0.6.1. **`describe_table` / `table_requirements` / `get_template` do not accept
`module_spec.yaml`** — they take CSV kinds only and will answer *"Unknown table kind"*. Use:

```
authoring_reference()          # the whole DSL, generated from the live models. Carries
                               #   models: ModuleSpecConfig, ModuleInfo, Defaults, Display,
                               #           Weighting, Contribution, GenePanelSpec
                               #   registry_stamped_keys  — the three keys you must not author,
                               #                            each with the reason
                               #   genome_build_default   — what an omitted genome_build means
                               #   schema_version         — the only accepted value
                               #   vocabularies['author_role'], ['icon_set']  — closed
                               #   open_recommended['author_kind']            — open, seed only

authoring_reference(schemas=true)   # raw JSON Schema instead of the summary form

scaffold_module(...)           # writes the skeleton — and omits every optional block,
                               # so add weighting:/license:/authorship: by hand

module_signature(spec_dir)     # content signature; folds defaults: into every row first
validate_module(spec_dir, strict=true)   # reports the version-coercion warning, the panel
                                         # deprecation, and the license/licensing.csv disagreement
```
