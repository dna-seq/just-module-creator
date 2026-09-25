# README.md — the module's prose, and the receipt that is not it

> **Audit banner — re-stamped 2026-09-13 against format 0.7.0 / compiler 0.7.0 / enricher 0.7.0 /
> registry 0.25.2** (`importlib.metadata`, read from this repo's venv). **The prose below was written
> against 0.6.1 and has not been re-argued sentence by sentence.** What was done is narrower and is
> the half that rots: every `file:line` citation was removed — the line numbers had drifted, the
> symbol names held, so anchor on the symbol — and the counted rosters were re-measured against the
> installed packages.
>
> **This file describes something that is not a table kind**, so it has no generated upstream page.
> Its facts come from the code named by symbol below; the per-table reference pages are at
> <https://just-dna.life/just-dna-compiler/tables/> and the live answer is `describe_table` /
> `describe_machine_table`.
>
> Two markers appear below — 🚧 **ROADWORKS** for a surface that is broken or unfinished, always with
> a guard saying what to do instead, and ⚠️ **CHECK** for a claim whose current state is not what the
> surrounding text would lead you to expect. **Both were raised in the 0.6.1 pass, so a marker is not
> evidence the surface is still broken at 0.7** — re-check before quoting one.

Not a table. No model, no columns, no parquet. It is the one file in a spec directory that is
*about* the module rather than part of it, and almost every rule here follows from that one
sentence. Covered together with its old name `MODULE.md` — which is what the real corpus actually
carries — and with `published.json`, the local receipt that sits beside it and is routinely
confused for it.

## What it is

A module's rows say what is true. The readme says what the module *is*, what it is **not**, and what
the author decided that no row records. On the catalog it is the module card's long prose (registry
`S5`); in the spec directory it is the only place a caveat like *"most of these are from a preprint
and one association was not significant"* can live, because `module.description` is the card's
one-sentence subtitle and has no room for it (`module_spec.md` owns that norm and what it is worth —
nothing enforces it, and most published descriptions overrun it).
It is optional, it is never parsed, and nothing downstream branches on its content. It is a claim.

## Identity card

| | |
|---|---|
| Model / module | **none.** A `FileEntry` (`just_dna_format.manifest.FileEntry`) records `{name, sha256, size}` in `manifest.readme`; the bytes are never modelled |
| Accepted names | `manifest.README_CANDIDATES` — six names, in discovery order (§ Gotchas) |
| Parquet | none, ever. Copied verbatim into the module dir beside the parquets |
| Natural key | the filename. One readme per module; two on disk resolve by the candidate ladder, never by luck |
| Authored or produced | **authored**, always. No pass writes it and no drafter stubs it |
| Who writes it | a human or an AI co-author. `just-dna-pipelines` writes `MODULE.md` (`agents/module_creator.py`) |
| Fact signature | none — it is not a fact table |
| In `content_signature`? | **no.** `specfiles.SIGNATURE_INPUTS` is `module_spec.yaml` + the twelve authored CSVs; `README.md` is absent (measured below) |
| In `artifact.digest`? | **no.** It is not in `artifact.files[]`; the digest is a Merkle root over the parquets only |
| In the attestation binding? | **no.** `compiler.authored_input_entries` returns `_INPUT_FILES` only — measured as `['module_spec.yaml','variants.csv','studies.csv']` on `hfe_hemochromatosis` |
| Registry card | yes — module-level, last-publish-wins, amendable without a version bump |

And its neighbour:

| | `published.json` |
|---|---|
| Written by | **this plugin**, nothing upstream. `tools/registry.py` `RECEIPTS_FILE`, appended by `_record_receipt` (`tools/registry.py`) |
| Contains | the registry-stamped identity: `target`, `canonical_id`, `namespace`, `name`, `version`, `owner`, `artifact_digest`, `content_signature`, `registry_url`, `published_at` |
| Known to the format? | no — tolerated as an unknown file (§ `published.json`) |
| Known to the registry? | **no.** `"published.json" in RECOGNIZED_SPEC_FILES` → `False` (measured) |

## Who populates what

- **author** — the whole file. There is no drafter, no enricher pass and no compiler stamp for
  prose. `scaffold_module` does not create one; `list_tables` does not list it.
- **compiler-stamped** — only the *hash*. `_collect_readme` (`compiler/…/compiler.py`)
  discovers the file, copies it into the output dir and fills `manifest.readme`. It never writes,
  edits or generates prose.
- **registry-stamped** — only the *projection*. `publish.py` reads the stored bytes
  (`readme_name = manifest.readme.name if manifest.readme is not None else README_FILE`) and hands
  them to `ingest_manifest(..., readme=...)`, which lands in the `modules.readme` TEXT column
  (`db/schema.py`).
- **nobody, ever** — there is no field in `module_spec.yaml` for prose and no plan to add one. The
  file is the field.

**Which cells no tool may fill.** None — a readme is prose an agent may write. What it must
not do is **assert a judgement nobody made**, and that is a rule about the content, not the typist.
Report-never-repair does not forbid the typing here, only the judgement.

- `hints.ATTESTATION_BEARING` (`provenance_quote`, `provenance_regex` on `studies.csv`) exists for
  **attribution** — who located the passage — not abstention: an agent that reads the article is a real
  reader, so it may locate and quote, recording who did. It is not a requirement that a *curator* read
  the paper. A readme is the same kind of object one
  level up: it records what somebody decided this module is *for*. So write one, and let `authorship`
  say who wrote it; the thing to avoid is a readme that invents a purpose nobody chose.
- **`enrich_literature` will happily check a readme's claims against nothing at all.** There is no
  lint for prose. `validate_spec` never opens the file — measured: rewriting `README.md` to
  `"# totally new prose\nclaims galore\n"` changed no finding, no signature and no digest.

## What moving this file moves

Measured on `reference_examples/hfe_hemochromatosis`, compiled five times with
`compile_module(resolve_with_ensembl=True, ensembl_cache=None)`:

| An edit here | `content_signature` | fact signatures | `artifact.digest` | `manifest.readme.sha256` | attestation + closure |
|---|---|---|---|---|---|
| add a `README.md` where there was none | unmoved | unmoved | unmoved | `null` → set | **survives** |
| rewrite the prose entirely | unmoved | unmoved | unmoved | moves | **survives** |
| delete it | unmoved | unmoved | unmoved | → `null` | survives |
| rename `README.md` → `MODULE.md` | unmoved | unmoved | unmoved | → **`null`, silently** | survives |
| pass `readme_file=MODULE.md` explicitly | unmoved | unmoved | unmoved | set, `name="MODULE.md"` | survives |
| recompile under a newer toolchain | unmoved | unmoved | may move | unmoved | survives |
| *(control)* append `\n` to `studies.csv` | moves | — | moves | unmoved | **closure dropped** |

All five compiles produced **one** distinct `artifact.digest` and **one** distinct
`content_signature`. The control row is what proves the check could run.

1. **Inside `content_signature`?** No. `SIGNATURE_INPUTS` names the authored *tables*; prose is not
   one. Measured directly: adding, rewriting and deleting both `README.md` and `MODULE.md` in a copy
   of `chd_depression_v1` left `sha256:903e6ce7…` unchanged through all four states.
2. **Inside `artifact.digest`?** No, and this is the one case where "it has no parquet" is not the
   reason — `resolution.csv` also has no parquet but still owns `compilation.resolution_signature`.
   A readme owns no signature of any kind. Its only identity is `manifest.readme.sha256`.
3. **Does an edit un-close the module?** No. `close_module` binds `authored_input_entries(spec_dir)`
   = `_INPUT_FILES`, newline-normalized since RM82. Measured: closed `hfe_hemochromatosis`, rewrote
   its `README.md`, recompiled — `manifest.verification.closure` still present, `digest` identical,
   only `manifest.readme.sha256` moved. Then touched `studies.csv` and the closure dropped. **You
   can fix a caveat in a closed module without re-closing it.**
4. **Part of the canary?** No. The canary (MODULE_LIFECYCLE § 5.1) is *content unmoved + fact
   signature moved*, and a readme has neither content membership nor a fact signature. It cannot
   produce or mask that reading.

## Required to exist

Nothing requires a readme. `validate_spec` does not mention it, `compile_module` compiles without
one, and `publish` accepts a module that has none. What it *drags in* is entirely on the catalog
side: **without one the module card's long prose is empty**, and an empty card reads as *this module
has nothing to say*, not as *nobody wrote one*.

The registry's precondition is `REQUIRED_SPEC_FILES = ("module_spec.yaml",)` — the readme is on
`RECOGNIZED_SPEC_FILES` (which is what makes it survive a storage round-trip) but not on the
required list.

## The claims that carry judgement

Not columns — the four things a real readme asserts, and which of them a reader may trust.

- **What the module is not.** The only place for it. `client.py`: *"the field where a module says
  what it is **not** — that its findings are candidates, that one association was not significant."*
  Unverifiable by construction, and the most valuable sentence in the file.
- **Design decisions / weight rationale.** Every one of the 26 corpus readmes has a
  `## Design Decisions` section explaining why a weight is `-1.0`. Nothing checks it against
  `variants.csv`. A weight edited without the prose edited leaves the rationale wrong and green.
- **Data sources.** Free-text PMIDs and DOIs. **These are not `studies.csv`** and nothing reconciles
  the two. Measured on the corpus: three bundles carry `studies.csv` rows referencing rsIDs absent
  from `variants.csv` (`['rs12116494','rs1801133','rs4305']`), and the readme claimed all of them.
  The declared *licence* belongs in `licensing.csv`, not here.
- **A changelog.** Hand-written, and the corpus shows it is the first thing to rot (§ Gotchas 3).

## Gotchas

Ordered by how likely a first-timer is to hit them. Counts are from **27 real submitted bundles** in
`/data/sources/just-dna-registry/data/input/`, extracted read-only into a scratch dir.

**1. The corpus writes `MODULE.md`, and the compiler does not know that name.**
**26 of 27 bundles carry `MODULE.md`. Zero carry `README.md`. One (`longevity_2025_v2`) carries
neither.** This is not history: `just-dna-pipelines`' authoring agent still writes it today
(`agents/module_creator.py`, `write_module_md`, docstring *"Write or update the MODULE.md
documentation file"*). The name is not in `README_CANDIDATES`, so **`_collect_readme` returns
`None`** — measured on `chd_depression_v1`. A local `compile_module` on any of those 26 bundles
produces an artifact with `manifest.readme: null` and no prose copied out, and says nothing about it.
The prose does not reach the artifact and no warning is raised.

> 🚧 **ROADWORKS — `MODULE.md` is invisible to the compiler, and the corpus is full of it.**
> **Current state.** 26 of 27 submitted bundles carry `MODULE.md` and none carries `README.md`; the
> name is not in `README_CANDIDATES`, so `_collect_readme` returns `None` and the compile is silent.
> No near-miss warning can fire either — the fuzzy scan runs over root-level `.csv`/`.json`, not
> markdown. Only the registry repairs it, on upload, as an `info` note that lands nowhere durable.
> **Expected state.** Either the upstream authoring agent emits `README.md`, or discovery accepts
> both names. Neither has happened; the rename is the registry's, not the format's.
> **Guard.** **Name the file `README.md`.** If you have a `MODULE.md`, rename it *before* you compile
> and before you publish — a local compile silently drops the prose, and the registry's repair leaves
> no record you can read back. Do not pass `readme_file=MODULE.md` to work around it: that mints a
> manifest attesting a name the registry's recognised-file list does not contain.

**2. The registry repairs it, the compiler does not, and only the registry tells you.**
`specfiles.RENAMED_ON_UPLOAD` is exactly two entries: `{'MODULE.md': 'README.md',
'sources.csv': 'licensing.csv'}` (measured). `plan_layout` (`specfiles.py`) applies the rename
and appends a **note**, graded `info`, not a warning:

> renamed `MODULE.md` to `README.md` (the readme filename the registry reads; `MODULE.md` was this
> project's advice until 0.14 and nothing read it)

Ran `plan_layout` over all 27 bundles: **26 produce that exact rename**, one produces nothing (it has
no prose at all). The applier is `normalize_spec_layout` (`services/publish.py`), which does
`(spec_dir / source).replace(spec_dir / dest)` before validation, before signing, before the compile.

**Is the rename recorded anywhere durable? No.** It reaches the caller three ways and lands on disk
in none: `plan.notes` → the publish response's `info`; `action.log(message_type=...)` → the server's
own action log; and it rides on a *refusal* too (`publish.py` — *"a publisher whose `MODULE.md`
was renamed and whose spec then failed for an unrelated reason should not have to guess which of the
two happened"*). It is **not** in `manifest.compilation.warnings`, not in `verification.json`, and
not in the stored spec. Download the module later and it is simply a `README.md` that was always
called that. So: **rename before you publish, or the record of the rename lives only in a response
you did not keep.**

Two spellings of the readme is a *warning*, not a conflict — unlike two spellings of a sidecar, which
`plan_layout` **refuses** (`SidecarCollision`). The readme's loser is carried unchanged and ignored,
because "an extra markdown file makes the compiler do nothing at all" (`specfiles.py`, the
two-spellings branch). A near-miss name (`readme.txt`, bare `README`, `module.markdown`) is warned
about and **deliberately never renamed** — `S7`, refused with a reason: renaming `MODULE.md` repairs
this project's own advice, whereas guessing that `README.txt` meant the card would be inventing
intent.

**3. A version bump does not move the prose, and nothing notices.** The corpus is the only real
second-pass material anywhere in this workspace, and it is unambiguous:

- `latest_longevity` v1→v2→v3 — prose moved every time, each version appending a `## Changelog`
  bullet. The good case, and it is a *hand-written* good case.
- `longevity_2025` v2→v4→v5 — **`v4`'s `MODULE.md` is byte-identical to `v2`'s** (`cmp` clean, 2226
  bytes), while `variants.csv` grew from **32 rows to 71**. Its changelog's newest entry says
  **v3** — a version whose zip is not even in the corpus. Then `v5`'s changelog jumps v5 → v3 → v2 →
  v1: **v4 never appears at all**, so 39 added rows are recorded nowhere in the prose.
- `multimorbidity_aging` v2→v3 — `variants.csv` and `studies.csv` **byte-identical**;
  `module_spec.yaml` differs by exactly `version: 2` → `version: 3`; the changelog gained
  *"**v3** (2025-10-25): Maintenance update."* Measured: `content_signature` is **identical**
  (`sha256:fac0da6f…`) across both. That is the review-pass shape the registry's dedup carve-out
  exists for — and the prose is the only thing claiming anything happened.

**Nothing in the format records that a readme changed, or that it did not.** `manifest.readme.sha256`
moves, but nobody diffs it across versions, and the registry's `readme` column is *module-level and
last-publish-wins* (`db/repository.py`), so a v4 publish carrying stale prose overwrites v3's on
the card with no trace. The hand-written `## Changelog` section is the only mechanism, and the corpus
shows it fails.

**4. A readme overclaims, and nothing can catch it.** The canonical case is in this workspace:
`/data/sources/just-dna-format/data/output/corrected_modules/README.md` — *"The intelligence bundle's
own README claims allele/strand validation against dbSNP with a gnomAD second witness. That claim is
not supported — the coordinates it was asserted over were shifted."* Four modules passed `validate`,
passed `compile --strict`, reported `fully_resolved: true`, minted verified `ga4gh:VA.…` ids, and
were wrong by one base on **every** coordinate. The readme asserted the check that would have caught
it. The corpus repeats the shape: `multimorbidity_aging_v2(1)`'s readme claims *"**Validation**: Risk
alleles and phenotypes were cross-referenced with the GWAS Catalog and primary literature"* — an
assertion with no artifact anywhere in the bundle.

Contrast the reference examples (`reference_examples/*/README.md`, 16 of them, all named
`README.md`). They say what the module **demonstrates and what it broke** — `hfe_hemochromatosis`'s
opens *"Its point is not the biology: it is what a drafting provider will and will not decide for
you"*, then pastes the three verbatim warnings the draft emitted and shows the thirteenth row that
makes the argument. A submitted readme says what the author intends; a reference readme says what
the tooling did. **Write the second kind.**

**5. `check_readme` passes on an absent file.** `integrity.py` — *"an absent one is not a
failure"*. So `verify_manifest(check_readme=True)` on a manifest attesting a readme that never
arrived returns clean. This is a live gap in `just-dna-lite`: `v1_port/publish.py` sets
`_ALLOW_PATTERNS = [*ARTIFACT_PARQUETS, "manifest.json", "logo.png", "logo.jpg"]` — **no readme**.
The enricher's publisher fixed exactly this and says why (`enricher/…/upload.py`): *"A manifest
field whose bytes nobody uploads is a field that does not travel"*, and imports `README_CANDIDATES`
rather than spelling names. The pipelines copy has not.

**6. `reverse_module` does not re-emit it.** `reverse_module` (`compiler.py`) takes no `readme`
parameter and writes none — it rebuilds `module_spec.yaml`, the authored CSVs and the sidecars from
the parquets, and prose is in no parquet. **The round trip costs you the prose.** `compile → reverse
→ compile` reproduces the identical `artifact.digest` and the identical `content_signature` (which is
the point of the fixed point) while silently dropping the readme, so a module recovered from its
artifact has an empty card until somebody re-attaches the file or calls `amend_readme`. Keep the
readme in version control beside the spec; it is not recoverable from the artifact.

**7. Its extension is checked; its name, on the explicit path, is not.** `_collect_readme` validates
against `README_EXTENSIONS` = `{md, txt, rst}` and raises `ValueError` internally otherwise (which
`compile_module` catches, so it reaches you as a failed compile rather than an exception) — but only the
*discovery* path consults `README_CANDIDATES`. Passing `readme_file=` an explicit path accepts any
name with a legal extension: measured, `readme_file=MODULE.md` produced
`manifest.readme = FileEntry(name='MODULE.md', …)` and copied `MODULE.md` into the module dir. This
does not arise through the registry (it renames first, then compiles itself), and **our
`compile_module` does not expose `readme_file` at all** — so from this plugin the discovery ladder is
the only path. Named because a hand-rolled `just-dna-compiler compile --readme MODULE.md` mints a
manifest attesting a name `RECOGNIZED_SPEC_FILES` does not contain.

## `published.json` — the receipt

Written by **this plugin and nothing else** (`src/just_module_creator/tools/registry.py`). One
JSON array, appended to after each successful publish, never overwritten: a published version is
immutable, so a second receipt for a version already recorded keeps the original and reports the
difference (`registry.py`). Prior receipts match on **version AND target**, so a polygon
rehearsal of `1.0.0` is not a prior publish of production's `1.0.0`.

It exists because the registry owns four identity keys and `module_spec.yaml`'s `module:` block is
`extra="forbid"` — those keys are rejected there *precisely because* the registry owns them (upstream
`S1`). So the stamped identity had nowhere on disk to land — this file is where it lands.

**Its contract with the compiler is narrow and deliberate.** `compiler.py`:

> Neither `published.json` nor any other registry receipt is within one edit of a known name, which
> is the property that keeps the tolerance beside it intact (measured, not assumed).

That is `S16` — unknown files in a spec directory are tolerated — plus RM45, which made the
root-level near-miss scan read `.json` as well as `.csv` so a typo'd `verifcation.json` warns instead
of silently not being an attestation. `published.json` is far enough from every known name that the
fuzzy matcher (`difflib`, cutoff 0.8) does not reach it. **Do not rename it.** A receipt called
`publised.json` or `publish.json` would start drawing the near-miss warning.

**What actually happens to it on publish — and the brief's premise is wrong here, so state it
precisely.** `published.json` is **not** filtered out of a loose-files upload:
`client.gather_spec_files` (`client.py`) skips only `_SKIP_UPLOAD_SUFFIXES = {".parquet"}` and
`_SKIP_UPLOAD_NAMES = {"manifest.json", "WHERE-THIS-CAME-FROM.md"}` (measured). So on the ordinary
publish path it is uploaded, materialized into the server's spec dir (`routers/publish.py`), and
copied into storage by the carry-forward loop (`services/publish.py`, which skips only
`*.parquet`). It **is** filtered on the *archive* path, where `collect_archive` applies
`carries_spec_content` (`services/publish.py`).

It never comes back either way. `/files/{path}` serves only what the manifest attests
(`routers/modules.py`) and the tarball is built from manifest entries
(`routers/modules.py`); a receipt is in neither. And because
`"published.json" in RECOGNIZED_SPEC_FILES` is `False`, a `revalidate` or `upgrade` — both of which
rebuild a spec directory from that tuple — drops it from storage. **Treat it as local-only and commit
it to your own repo**; that is the only place it survives.

## What does not exist

- **A `readme:` key in `module_spec.yaml`.** Never proposed. The file is the field.
- **The prose inlined into `display`.** Proposed and **rejected** in `S25`, upheld by both sides: *"a
  readme is unbounded prose — the case that motivated this is an 11-row module whose README is longer
  than its data — and `display` is inlined into every card and listing we serve."*
- **`README.md` in `artifact.files[]`.** Proposed and **rejected**, and the reason generalises: on an
  immutable registry a fixed typo would mint a new `artifact.digest`, cost a version, and then the
  corrected module would collide with its own predecessor under the name-independent
  `409 duplicate_content` check. `S26` cites this rejection as precedent for a second case. The
  rejection only holds because prose is out of `content_signature` too, which is why `S25`'s tests
  compute **both** identities rather than the digest alone.
- **A rename for `README.txt` / `readme.md` / bare `README`.** Refused (`S7`) — warned about,
  carried unchanged, never guessed at. Note the asymmetry with `README_CANDIDATES`: the *compiler*
  discovers `readme.md` and `README.txt` happily; the *registry* card reads `README.md` exactly.
  A `readme.txt` therefore compiles into `manifest.readme` and still leaves the card blank.
- **Any validation of the prose.** No linter, no claim checker, no reconciliation against
  `studies.csv` or `licensing.csv`. There is no proposal for one and it is hard to see what it would
  check.
- **Per-version readmes on the card.** The DB column is module-level by design
  (`db/repository.py`): *"the readme answers 'what is this module and what is it not', which is
  not a question each version re-answers."* `manifest.readme` is per-version; the card is not.
- **A `MODULE.md` era-gap.** It is not a deprecation and not a break — it is a name this project
  advised for two releases and then changed, with a rename that repairs its own advice.

## Consumption today

- **`just_dna_compiler.compiler._collect_readme`** (`compiler.py`) — discovers, copies into the
  module dir, hashes into `manifest.readme`. The only producer.
- **`just_dna_format.integrity.verify_manifest(check_readme=True)`** (`integrity.py`) — re-hashes
  it if present; skips silently if absent. Exposed as `just-dna-compiler verify --check-readme`
  (`compiler/cli.py`), **default `False`**.
- **`just_dna_enricher.upload`** (`upload.py`) — `_ALLOW_PATTERNS` includes `*README_CANDIDATES`,
  so the HuggingFace publisher ships it.
- **registry `services/publish.py`** — projects the stored bytes onto `modules.readme`.
- **registry `db/repository.py, 625`** — `upsert_module(readme=None)` means *leave it alone*;
  `set_module_readme` replaces it module-wide.
- **registry `services/catalog.py`** — `ModuleDetail.readme = row["readme"]`. The card.
- **registry `api/routers/modules.py, 318`** — `manifest.readme.name` joins the `/files/{path}`
  allowlist and the tarball entry list.
- **registry `services/publish.py` / `api/routers/publish.py` / `client.py` /
  `client_cli.py`** — the `amend_readme` chain: replaces prose, sets `manifest.readme`, spends no
  version, moves no identity.
- **registry `client.py`** — `download` re-hashes it via
  `check_readme=manifest.readme is not None`.
- **this plugin, `tools/registry.py`** — `registry_amend_readme`, gated
  (`auth.py`), reads `spec_dir/README.md` by that exact name and refuses a path passed as
  `readme_text`.

**Nothing in `just-dna-lite` reads a module's readme.** The only hits are
`webui/pages/modules.py` `_module_manager_readme()`, which is the *page's own* help text, and
`just-prs/hf.py`, which writes a HuggingFace dataset card. The annotation half never opens it.

## Blanks for just-dna-lite

- **The v1 HF publisher drops the readme it attests.** `just-dna-pipelines`
  `v1_port/publish.py` omits `README_CANDIDATES` from `_ALLOW_PATTERNS` while the manifest carries
  `manifest.readme`. A consumer fetching that module gets a manifest attesting a file the repo does
  not have, and `verify_manifest(check_readme=True)` passes anyway because absent is not a failure.
  Fix is one line and already written next door: import `README_CANDIDATES`, as
  `just_dna_enricher.upload` does. **Ask: mirror the enricher's allowlist.**
- **The authoring agent still writes `MODULE.md`.** `agents/module_creator.py`. Every module it
  produces depends on the registry's rename to have a card at all, and gets `manifest.readme: null`
  if compiled locally. Registry `S8` addressed this to the wrong repo (it credited the tool to this
  plugin, which has never had it). **Ask: emit `README.md` at the source, or accept both and prefer
  `README.md`.**
- **No annotation-side reader renders module prose.** A report generated from a module can show a
  title, a gene list and a green `compile_success`, and has no place to show *"these are candidates,
  most from a preprint"*. That is the exact inversion the three-valued rule exists to prevent,
  arriving through presentation. **Ask: surface `manifest.readme` (or the downloaded `README.md`)
  wherever a module is presented to a person.**
- **Nothing diffs prose across versions.** `manifest.readme.sha256` is per-version and the card is
  module-level last-publish-wins, so a stale readme silently overwrites a current one — measured
  three times in the corpus. **Ask: when publishing version *n+1*, compare `manifest.readme.sha256`
  against version *n* and say "the prose did not change" out loud.**

## Ask the live schema

There is no `describe_table("README.md")` — it is not a table, and `list_tables` will not list it.
What to run instead:

```python
from just_dna_format.manifest import README_CANDIDATES, README_EXTENSIONS, README_STEMS
README_CANDIDATES   # discovery order, authoritative
```

As of format **0.6.1** that is
`('README.md', 'README.rst', 'README.txt', 'readme.md', 'readme.rst', 'readme.txt')` — stem is the
outer loop, so `README.txt` beats `readme.md`; extensions sort `md` first. Defined **once**
(`manifest.py`) because three parties must agree: the compiler discovers, the enricher's publisher
uploads, the registry serves.

For the registry's half, in a checkout of `just-dna-registry`:

```python
from just_dna_registry.specfiles import (
    README_FILE, LEGACY_README_FILE, RENAMED_ON_UPLOAD,
    RECOGNIZED_SPEC_FILES, SIGNATURE_INPUTS,
)
from just_dna_registry.specfiles import plan_layout
plan_layout([p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()])
```

`plan_layout` is the honest rehearsal: it tells you exactly what the server will rename, warn about
or refuse, from filenames alone, with no network and no upload. Run it before every publish.

And for the digest questions, measure rather than trust this file: compile twice into different
output dirs, rewrite the readme between them, and compare `manifest.artifact.digest`,
`manifest.content_signature` and `manifest.readme.sha256`. That is what produced the table above.

---

**A README is a claim, not a receipt.** Nothing in the format checks a sentence of it, no signature
covers it, no digest moves when it changes, and the corpus shows it going stale two versions deep
without a single warning. That is the correct design — prose about a module must not be able to mint
a new content identity — but it means the file's honesty rests entirely on whoever typed it. So put
anything that must be *verifiable* where verification lives: **`authorship:` in `module_spec.yaml`**
for who did the work (which is where the real trust signal is — a v25 module with two named
medical-geneticist curators says something a readme cannot), **`verification.json`** for which checks
ran and which did not, and **`licensing.csv`** for the terms and attribution a downstream report is
obliged to render. Leave the readme for what only a person can say: what this module is for, what it
is not, and what you decided not to claim.
