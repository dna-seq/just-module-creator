# `logs/` — the provenance subtree, and the one writer it finally has

> ⚠️ **CHECK — this file was titled *"the subtree nobody fills"* until 2026-08-20, and that is no
> longer true.** `record_override` appends to `logs/authoring.log` (`RM16`), which is the first
> writer this plugin has ever pointed at the surface. Everything below about *what happens to* a log
> — discovered, copied, hashed, never opened, published with no opt-out — is unchanged and now
> matters more, because a file this repo writes travels to the catalog verbatim.

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

`logs/` is not a table. It is the one place in a just-dna module where a **free-form, unparsed byte
blob** travels inside the compiled artifact directory and gets a hash in the manifest. It answers a
question no CSV can: *what did the run that produced this module actually do* — which model, which
prompt, which tool calls, which thresholds, which rows it dropped and why. The compiler discovers it,
copies it, hashes it, and never opens it. Its audience is a human auditor reading a module somebody
else built, and a catalog that wants to show "here is the transcript" beside the card.

Two things make it unlike every other file in a spec directory. It is **outside every identity a
module has** — digest, content signature, fact signatures, the attestation binding, and the Ed25519
signature — so editing one changes nothing that any check compares. And it is **the only thing in the
format designed to accumulate across versions**: `aggregate.aggregate_logs` defines full provenance as
the union of every version's logs (`aggregate_provenance` does the same for `provenance.json`; nothing
else in the format has a cross-version union at all).

Measured, and this is the headline: **nothing published uses it.** Zero of the 16 published versions
across the 5 modules on production carry a log entry; the polygon is empty; none of the 16 reference
examples ships a `.log`. Meanwhile 11 of the 27 submitted bundles in
`/data/sources/just-dna-registry/data/input/` carry 17.6 MB of real agent transcripts that never
reached the catalog.

## What must never go in one

**`logs/**.log` is swept into every compile with no opt-out and travels to the catalog verbatim**, so
a log is a **publishing surface**, not scratch space. Nothing redacts it, nothing reviews it, and a
published version is immutable — a secret written here cannot be taken back by deleting the file
afterwards.

So never write into one:

- **a credential** — a registry token, an API key, anything from `.env`;
- **an absolute path** — it names the machine, the operator's home directory and often their real
  name, and it is meaningless to every reader but you;
- **a transcript fragment** — a prompt, a system prompt, or a user's own words, none of which the
  author agreed to publish when they agreed to publish a module.

`record_override` is the writer to route an authoring move through, and the same rule binds what you
hand it: a reason, not a paste. If a move genuinely needs a path recorded, record it **relative to
the spec directory**.

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.manifest.FileEntry`, in `ModuleManifest.logs: list[FileEntry]` (`schema/src/just_dna_format/manifest.py:1395`) |
| Parquet | **None, ever.** Logs are copied verbatim into the artifact dir; nothing materializes them |
| Natural / dedup key | `(name, sha256)` — the dedup key `aggregate_logs` uses (`schema/src/just_dna_format/aggregate.py:22`) |
| Authored or machine-produced | **machine-produced**, by whatever pipeline wrote the module. No human writes one by hand |
| Who writes it | `just-dna-lite`'s Module Manager (`v<N>.log`) and `just-dna-pipelines`' `v1_port` (`v1_port.log`, `clinvar_panel.log`, `pharmgkb.log`). **Not the enricher** — see Gotchas |
| Who collects it | `just_dna_compiler.compiler._collect_logs` (`compiler/src/just_dna_compiler/compiler.py:552`), called at `compiler.py:4522` |
| Fact signature | **None.** No signature of any kind covers a log's bytes |
| In `content_signature`? | **No.** `content_signature` hashes parsed CSV rows plus a non-default `genome_build` and nothing else (`integrity.py:189`) |
| In `artifact.digest`? | **No**, explicitly — `manifest.py:1401`: "Kept out of `artifact.digest` so identical compiled data stays dedup-equal regardless of logs" |
| In `manifest.inputs`? | **No.** `_INPUT_FILES` is `module_spec.yaml` + `variants.csv` + `studies.csv` + the table kinds (`compiler.py:267`) |
| In the Ed25519 signature? | **No.** `sign_digest` signs the `artifact.digest` string's UTF-8 bytes and nothing else (`schema/src/just_dna_format/signing.py:56-63`) |
| Location | `spec_dir/*.log` (top level) **and** `spec_dir/logs/**.log`, at any depth |

## Who populates what

There are no columns, so this section names **producers** instead.

- **author** — nobody. There is no path by which a human is expected to write a log, and no tool asks
  for one. A hand-written `notes.log` dropped in a spec directory would be picked up and hashed
  exactly like a machine one, silently.
- **drafter** — none. `clinvar_draft` / `pgx_draft` / `clinpgx_draft` write no logs.
- **enricher pass** — **none, and this is the correction worth carrying.** Grepping
  `enricher/src/` for a `.log` write returns nothing: the enricher writes `resolution.csv` and the
  fact sidecars and never a log file. Annotating `logs/` as "the enricher's" is wrong in both
  directions — the enricher does not write there, and what does write there is the *authoring*
  pipeline.
- **compiler-stamped** — the compiler collects and hashes, it does not author. `_collect_logs`
  auto-discovers `sorted(spec_dir.glob("*.log"))` plus `logs_dir.rglob("*.log")`, copies each to
  `output_dir / rel` with `shutil.copyfile` (creating parent directories), and returns
  `file_entries(output_dir, names)` (`compiler.py:571-587`).
- **registry-stamped** — nothing on the entry itself. But on a registry publish the **server** runs
  the compile, so `manifest.logs` on a published module is the registry's own hash of what you
  uploaded, not yours (`just-dna-registry/src/just_dna_registry/services/publish.py:543-547`).
- **nobody, ever** — in practice, everything. See the measured counts above.

**Cells no tool may fill even though it easily could.** `hints.REDUNDANCY_BEARING` and
`hints.ATTESTATION_BEARING` do not reach this file — they name *columns*, and a log has none. The
analogous refusal is sharper and unwritten: **a log is not evidence and must never be treated as
one.** Nothing parses it, nothing cross-checks it, and the one pipeline that tried to make its log
authoritative shipped a log that contradicted its own parquet (see Gotcha 4). If you want a machine to
believe a claim, it goes in `verification.json`, `provenance.json` or `authorship` — never in a log.

## What moving this subtree moves

Measured by compiling `/data/sources/just-dna-registry/data/input/latest_longevity_v2.zip` with the
installed format/compiler **0.6.1**, then touching a log and recompiling.

| An edit here | `content_signature` | fact signatures | `artifact.digest` | `manifest.logs[]` | attestation + closure |
|---|---|---|---|---|---|
| Add a new `*.log` or `logs/**.log` | unmoved | unmoved | **unmoved** | new entry | unmoved |
| Append one line to an existing log | unmoved | unmoved | **unmoved** (measured: identical) | that entry's `sha256` moves | unmoved |
| Delete a log before compiling | unmoved | unmoved | unmoved | entry disappears | unmoved |
| Delete a log **after** compiling | unmoved | unmoved | unmoved | entry stays, file absent — `check_logs=True` **skips it** | unmoved |
| Reorder the lines inside a log | unmoved | unmoved | unmoved | that entry moves (raw bytes) | unmoved |
| Re-run the producing pass | unmoved unless the CSVs changed | unmoved unless facts changed | moves only if a parquet byte moved | moves (timestamps, elapsed seconds) | unmoved |
| Recompile under a newer toolchain | unmoved | unmoved | **moves** (compiler version is inside it) | unmoved (same bytes) | unmoved |
| Move `run.log` → `logs/run.log` | unmoved | unmoved | unmoved | **`name` changes** — a different entry, and `aggregate_logs` will not collapse the two | unmoved |

The four questions, answered:

1. **Inside `content_signature`?** No. `content_signature` takes a mapping of CSV filename → parsed
   rows and hashes their normalized JSON, plus `genome_build` when non-default (`integrity.py:189-253`).
   A log is never parsed into rows, so it cannot enter. There is no fact-field constant to name here
   because there is no fact set — this is not a derived table with provenance columns excluded, it is
   a blob with nothing hashed *by facts* at all.
2. **Inside `artifact.digest`?** No, and this is the one exception-shaped fact worth memorizing:
   every other file the compiler *copies into the artifact directory* is either a parquet inside the
   digest, or a logo/readme deliberately outside it. Logs join the logo and readme on the outside, and
   the reason is stated in the field description: identical compiled data must stay dedup-equal
   regardless of what logs came with it (`manifest.py:1401`). **Measured:** appending to `v2.log` left
   `artifact.digest` byte-identical.
3. **Does an edit here un-close the module?** No. The attestation binds `authored_input_entries`
   (`compiler.py:361-386`), which is `_INPUT_FILES` newline-normalized — `module_spec.yaml`,
   `variants.csv`, `studies.csv` and the table-kind CSVs. Logs are not in that set, so writing,
   editing or deleting one leaves a closed module closed. Contrast: an `authorship:` append **does**
   un-close a module, because `authorship` lives inside `module_spec.yaml`, while moving no identity
   at all.
4. **Part of the canary?** No. The canary reading is *content unmoved + fact signature moved* = the
   upstream source said something different this time (MODULE_LIFECYCLE § 5.1). A log has no fact
   signature, so it can never produce that reading. What a changed log *can* tell you is strictly
   weaker: the producing run differed. That is not a signal any consumer currently reads.

## Required to exist

Nothing. `manifest.logs` defaults to `[]` and an empty list is a fully valid module —
`schema/tests/test_logs.py:38-41` pins exactly that (`verify_manifest(..., check_logs=True)` on a
module with no logs). A log drags in nothing: no companion file, no manifest block, no validation.

What it does drag in is **bytes**. Measured on `latest_longevity_v2`: `v2.log` 1,757,925 +
`v1.log` 200,121, against `weights.parquet` 13,983 + `studies.parquet` 7,078 +
`annotations.parquet` 5,555. The logs are **68× the size of the data they describe**.
`latest_longevity_v3.zip` carries a 4.0 MB `v3.log`; the 27 bundles hold 17.6 MB of log against a
few hundred KB of CSV.

## The files that carry judgement

- **A top-level `*.log`** is the *aggregate* run transcript by convention — one per module version.
  Both producers in the wild use this shape.
- **`logs/<role>.log`** is the per-role shape the format was designed for. `schema/tests/test_logs.py`
  names `logs/researcher.log` and `logs/reviewer.log` and comments the assertion `# per-role
  preserved` — the roles of an agent *team*, which is exactly the topology just-dna-lite's Module
  Manager runs. **Measured: nothing in the wild uses it.** 0 of 27 bundles, 0 of 16 reference
  examples, 0 of 16 published versions.
- **`logs/` is the one subtree the registry never flattens.** `plan_layout` hoists a recognized spec
  file to the root from any subdirectory, and explicitly skips `LOGS_DIR`
  (`just-dna-registry/src/just_dna_registry/specfiles.py:352-355`), because the manifest records that
  path verbatim and flattening would rename a file the manifest attests
  (`specfiles.py:196-200`). Arbitrary depth survives — **measured**: `logs/team/reviewer.log`
  compiled to `manifest.logs` under that exact name.
- **The name is the identity.** `aggregate_logs` dedups on `(name, sha256)`, so renaming a log across
  versions produces two entries where one was meant, while the same path with changed bytes is
  correctly kept as two.

## Gotchas

Ordered by how likely a first-timer is to hit them.

**1. You will ship a log without meaning to.** `_collect_logs` runs on every compile with no flag and
no opt-out. Any `*.log` in the spec directory — a stray debug dump, an editor artifact, a transcript
holding the user's upload paths and every model system prompt — is copied into the artifact directory,
hashed into the manifest, and uploaded on publish (`gather_spec_files` skips only `.parquet`,
`manifest.json` and `WHERE-THIS-CAME-FROM.md`; `just-dna-registry/src/just_dna_registry/client.py:92-106`).
The real transcripts in the submitted bundles contain the full Agno team system prompt, every member
model id, and paths like `data/agent_uploads/40246_2025_Article_772.pdf`. **Read a log before you
publish it** — no tool will read it for you.

**2. A log proves that these bytes were there. It proves nothing about what they say.** Not signed
(`sign_digest` covers `artifact.digest` alone), not parsed, not cross-checked against the artifact,
and absent-is-fine. **Measured** on a tampered `logs/researcher.log`:
`verify_manifest(..., check_logs=True)` raised `log hash mismatch for logs/researcher.log`;
`verify_manifest(...)` with defaults **passed**. Then, with the file deleted, `check_logs=True` passed
too — that is the `logs` rule, deliberately unlike the `inputs` rule, which raises `input file missing
on disk` (`integrity.py:495-511`). Consequence: **anyone can strip every log from a downloaded module
and it still verifies.**

**3. Nothing in this plugin turns `check_logs` on.** `verify_artifact` calls `verify_manifest` with
only `require_marketplace` and `public_key` (`src/just_module_creator/tools/authoring.py:610-615`).
So through our surface a tampered log is undetectable. `just-dna-compiler verify --check-logs` is the
only shipped route (`compiler/src/just_dna_compiler/cli.py:213`).

**4. A log can contradict the module it ships with, and one did.** `just-dna-pipelines`' v1_port
writes `v1_port.log` before resolution, then prunes unmatchable rows — so the log attested counts that
were never true of the files beside it: *"thrombophilia said `variant_rows: 25` / `study_rows: 29`
against a 24-row and 27-row artifact, lipidmetabolism `study_rows: 43` against 41"*
(`just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/v1_port/runner.py:133-149`). The repair was
`_restate_log_counts`, rewriting the header in place. Nothing in the format would have caught it:
there is no check that compares a log to an artifact, and there cannot be one, because the bytes are
opaque.

**5. Explicit `log_files` *overrides* discovery — it does not add to it.** `_collect_logs` takes the
explicit branch or the discovery branch, never both (`compiler.py:565-581`). The v1_port runners each
pass exactly one file (`runner.py:191`, `pharmgkb_runner.py:124`, `clinvar_runner.py:176`), so a
directory holding both `v1_port.log` and `clinvar_panel.log` ships only the one named. That pipeline
works around it by *deleting* the other on rebuild (`clinvar_panel.py:481-487`, so a rebuild does not
"ship a mixture of two builds"). A second trap in the same branch: an explicit path **outside**
`spec_dir` falls back to `path.name`, so `/tmp/run.log` is flattened to `run.log` in the module dir.

**6. `registry upgrade` drops every log, deliberately.** `prepare_version_upgrade` rebuilds the spec
from `RECOGNIZED_SPEC_FILES ∩ storage` (`services/upgrade.py:456`), and no log spelling is in
`RECOGNIZED_SPEC_FILES` (`specfiles.py:218`). The comment states the intent: *"Logs and provenance are
intentionally NOT carried: they describe how the predecessor was built, and this mechanical
re-publish has its own (absent) provenance"* (`upgrade.py:496-499`). So an upgraded successor has
`logs: []`. This is coherent **only** because each version's manifest keeps its own logs and
`aggregate_logs` unions them — which is precisely what nothing calls. The same shape is pinned
server-side: `tests/test_v05.py:567-574` publishes a second version with only `v2.log` and asserts
`logs == ["v2.log"]`. **Logs do not accumulate inside a version; they accumulate across manifests, or
not at all.**

**7. `aggregate_logs` is sorted, not first-occurrence.** `SCHEMAS.md:1814-1815` says both aggregate
helpers return "first-occurrence order". That is true of `aggregate_provenance` and **false of
`aggregate_logs`**, which returns `[seen[key] for key in sorted(seen)]` — sorted by `(name, sha256)`
(`aggregate.py:26-27`). "First occurrence wins" in its docstring is about *which FileEntry object* is
kept for a duplicate key, not about output order. A doc bug, not a code bug; the code's own docstring
is right. **Measured** across two manifests: `['v1.log', 'v2.log' (a), 'v2.log' (b)]` in sorted order.

**8. The dry-run archive filter drops a top-level `*.log`.** `carries_spec_content("v1.log")` is
`False` while `carries_spec_content("logs/researcher.log")` is `True` (measured against registry
0.18.2). That filter is on the *packed dry-run* path only (`services/publish.py:240`); the real
publish extracts unfiltered, and both shapes reach `manifest.logs` — `tests/test_v05.py:542-552`
publishes `v1.log` and `logs/reviewer.log` and asserts both. `logo.png` is filtered the same way, so
this is "the dry run keeps only what validation reads", not a log defect. Worth knowing before you
conclude a rehearsal lost your log.

**9. Naive local timestamps.** The lite `RunLog` header is
`f"Agent Run Log — {self._start.strftime('%Y-%m-%d %H:%M:%S')}"` over `datetime.now()` — local, naive,
no zone (`agents/module_creator.py:96-101`). Every real transcript starts that way
(`Agent Run Log — 2026-03-20 11:49:12`). Two logs from two machines are not comparable, and the string
does not sort against the ISO-8601 UTC every other timestamp in the ecosystem uses.

## What does not exist

- **No `describe_table("logs")`, no `table_requirements`, no template.** This is not a table; the
  table tools do not know about it, and `list_tables` will not mention it.
- **No `--log-file` flag on `just-dna-compiler compile`.** The parameter exists in the Python API
  (`compile_module(log_files=...)`, `compiler.py:3898`); the CLI exposes only discovery. Checked
  against the whole option list at `compiler/src/just_dna_compiler/cli.py:110-128`.
- **No log surface in this plugin at all.** `scaffold_module` creates no `logs/` directory,
  `compile_module` never passes `log_files`, `CompileReport` has no `logs` field
  (`src/just_module_creator/models.py:333-358`), and `verify_artifact` never sets `check_logs`. An
  author driven by this plugin has no way to know a log was shipped.
- **No schema, no version field, no declared format.** Grepping every repo for `v0.1` finds only
  manuscript filenames; there is no "v0.1 log schema" anywhere in `just-dna-lite`,
  `just-dna-format` or the registry. What exists are **two mutually unintelligible plain-text
  conventions**, neither versioned:
  - the Module Manager's transcript — header, `====` rule, then `[%7.1fs] message` lines with
    12-space-indented detail continuations, details truncated at 30 lines / 2000 chars
    (`module_creator.py:78-101`, `_fmt_detail:152-160`);
  - v1_port's `key: value` provenance card — `module:`, `source_sha256:`, `variant_rows:`,
    `min_review_stars:`, `warnings:` (`v1_port/writer.py:99-108`, `v1_port/clinvar_panel.py:560-589`).

  **The format tier can read neither.** `_collect_logs` does `shutil.copyfile` and `sha256`, full
  stop. A log is an opaque blob to every tier that handles it, by design.
- **No signature over a log.** Asked and answered by the code: `signing.py`'s module docstring says
  *"Ed25519 signing over `artifact.digest`"*, and `sign_digest` signs the digest string. A signed
  module's logs are unsigned.
- **No `check_logs` by default, and that is the decision.** `verify_manifest`'s step 5 spells out
  why: *"absent logs are skipped, since logs are optional and need not be downloaded"*
  (`integrity.py:439-440`). This is the `logs` rule; a repair making it strict would break every
  consumer that fetches parquets only.
- **No cross-check between a log and the artifact**, and none is possible without a parseable schema.
  Gotcha 4 is the cost, and it was paid.
- **`logs` was the precedent, not a candidate for change.** When we asked for `manifest.derived`
  (our S26), upstream's answer was to model it on `logs` rather than on `inputs`, in every respect —
  optional, hashed, out of `artifact.digest` and out of `content_signature`, *"like a run log, these
  files are evidence about a compile rather than the compile's inputs"*
  (`just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md:242-244`, shipped at `manifest.py:1408`).
  The optional-and-skippable semantics of `logs` are settled architecture; do not propose tightening
  them.

## Where an agentic run can leave a trace — four places, and which to use

An agent that authored a module has four candidate homes for "who did what". They are not
alternatives; they answer different questions, and three of them are checked while one is not.

| | grain | file | in `content_signature` | in `artifact.digest` | un-closes? | cross-version union |
|---|---|---|---|---|---|---|
| `authorship:` | one contributor, one version | inside `module_spec.yaml` → `manifest.authorship` | no | **no** (`manifest.py:1156`) | **yes** — it is inside `_INPUT_FILES` | no |
| `verification.json` | one *check*, with counts and the release checked against | beside the spec → `manifest.verification` + `manifest.derived` | no (`manifest.py:1378`) | no | no — but a stale binding **drops the block** | no |
| `provenance.json` | one *variant* — rationale, reviewer verdict, confidence, `human_reviewed` | beside the spec → `manifest.provenance` summary | no | no | no | **yes** — `aggregate_provenance` |
| `logs/` | one *run*, unstructured | copied into the artifact dir → `manifest.logs` | no | no | no | **yes** — `aggregate_logs` |

Use them like this:

- **Who contributed, and in what capacity → `authorship:`.** `Contribution` is three orthogonal axes
  (`manifest.py:1146-1210`): `who` (free text — a name, handle or model id), `role` (a **closed**
  vocabulary, `vocab.VALID_AUTHOR_ROLES`), and `kind` (an **open** multi-valued tag set,
  `vocab.RECOMMENDED_AUTHOR_KINDS` — a human ladder plus `ai` with a scale tag). A joint human+AI
  contribution is **two entries**, each with its own `kind`; there is deliberately no `hybrid` tag,
  and that was refused with a reason: *hybrid what — a human plus a small model, or a certified expert
  plus a SOTA swarm?* (`vocab.py:805-807`). Call `authoring_reference` for the live members; do not
  quote this paragraph's vocabulary in a module.
- **What was checked, and did it pass → `verification.json`.** Written by the enricher, bound to the
  authored bytes by `module_hash`, and **dropped wholesale by the compiler when the binding no longer
  matches** — the one derived artifact whose human-overridability was deliberately removed, because
  an edited attestation is not stale but false (`manifest.py:1003-1017`). Never hand-write one.
- **Why this row says what it says → `provenance.json`.** `ProvenanceItem` is per-variant:
  `variant_key`, `rationale`, `reviewer_verdict`, `confidence`, `human_reviewed`
  (`manifest.py:778-786`). This is where an AI co-author's *reasoning about a specific call* belongs,
  and it is the only one of the four with a per-row grain. It is currently as unused as `logs`.
- **What the run literally did → `logs/`.** Everything the other three cannot express: the prompt,
  the model roster, the tool calls, the thresholds, the rows dropped mid-run. Use it as a transcript a
  human may read, never as a claim a machine will believe.

**The rule that falls out:** if a fact about the module can be stated in one of the first three, put
it there and *also* leave the transcript. A claim that exists only in a log is a claim nothing
verifies, nothing indexes, and nothing currently reads.

## The just-dna-lite Module Manager, and where its logs go

This is the pipeline the format's `logs/researcher.log` / `logs/reviewer.log` example was written for.

**What it is.** An Agno-based agentic pipeline in the just-dna-lite web UI's "Module Manager" tab
(`docs/AI_MODULE_CREATION.md`, `docs/ARCHITECTURE.md:141`). A user uploads up to 5 files (PDF, CSV,
Markdown, text) and describes a module; the system runs either a solo agent or a **research team** — a
PI plus three researchers on different models plus a quality reviewer
(`agents/module_creator.py:401-460`, `create_module_team:618`) — with four PI tools:
`write_spec_files`, `validate_spec`, `write_module_md`, `generate_logo`
(`_build_pi_tools:521-616`). Output is a spec directory: `module_spec.yaml` with
`schema_version: "1.0"`, `defaults.curator: ai-module-creator`, plus `variants.csv` and optionally
`studies.csv` (`_write_spec_files:243-288`).

**What it writes as a log.** `RunLog` (`module_creator.py:68-101`) accumulates status messages,
structured tool-call events, and — via `_LogCapture` and `configure_agno_logging`
(`:105-148`) — **all Agno internal debug output**, which is why a real transcript contains the entire
team system prompt verbatim. `_write_run_log` (`webui/src/webui/state.py:5951-5968`) writes
`<module_dir>/v<N>.log` on success, or
`data/output/generated_modules/_logs/failed_<timestamp>.log` when no spec was produced.

**Plain text, no schema, no version.** See "What does not exist" above. The format tier ships it as an
opaque blob.

**Does it reach a module's `logs/`?** It reaches the module — at the **top level**, never in `logs/`.
The chain is wired end to end and each hop preserves `.log`:

1. agent run → `GENERATED_MODULES_DIR/<name>/v<N>/v<N>.log` (`state.py:5617-5624` persists, then
   `:5957` writes the log). Note `:5622` copies only `f.is_file()` from the temp spec dir, so a
   subdirectory would be dropped here.
2. `register_custom_module` copies `.log` into `CUSTOM_MODULES_DIR/<name>` — top level only, no
   recursion (`just-dna-pipelines/src/just_dna_pipelines/module_registry.py:158-161`).
3. `RegistryClient.publish(..., CUSTOM_MODULES_DIR / key)` (`state.py:7412`) →
   `gather_spec_files` uploads it (`client.py:92-106`).
4. Server compiles; `_collect_logs` discovers it; `manifest.logs` gets the entry
   (`publish.py:543-547`; proven by `tests/test_v05.py:542-552`).

So: **not dropped — but the whole chain is top-level-`*.log` only, and `logs/` never survives step 1
or 2.** The per-role subtree the format designed exists in the format's tests and in the registry's
never-flatten rule, and in no producer.

**The second producer.** `just-dna-pipelines`' `v1_port` writes `v1_port.log`, `clinvar_panel.log` and
`pharmgkb.log` and passes each **explicitly** to `compile_module(log_files=[...])`
(`v1_port/runner.py:191`, `pharmgkb_runner.py:124`, `clinvar_runner.py:176`). Its comments are the only
two places in any consumer repo that mention `manifest.logs` (`clinvar_panel.py:90`,
`runner.py:143`), and it treats the log as the module's provenance record — recording the *actual*
thresholds a build ran with rather than the module defaults, because a caller overriding either "got a
log that quietly disagreed with its own artifact".

### Era classification — measured, not assumed

All 27 submitted bundles loaded with the installed **format/compiler 0.6.1** via
`just_dna_compiler.compiler.validate_spec`:

| bucket | count | what |
|---|---|---|
| **genuine break** (0.6.1 refuses something a 0.1 module legitimately had) | **0 / 27** | none found. Additive-within-a-major holds |
| **live deprecation** (read, warn-only) | **27 / 27** | `module.version: 2` as a bare YAML int → *"module.version '2' was read as SemVer '2.0.0'. It is advisory either way"*. Coerced, never refused |
| **era gap** (absent because it did not exist yet) | **27 / 27** | no closure (*"This module records no closure"* on every one), no `verification.json`, no `authorship:`, no `provenance.json`, no `licensing.csv`/`sources.csv`, no `weighting:`, no fact sidecars |
| **author defect** (wrong in any era) | **3 / 27** | `longevity_rare_v1`, `longevity_rare_v1(1)`, `putter_v1` — *"studies.csv is missing. Grounding evidence is mandatory"*. Three others warn that studies cite rsIDs absent from `variants.csv` |

Net: **24 of 27 still validate on 0.6.1, and the 3 that do not are the submitter's fault, not the
format's.** The bare-int `version:` is worth a note — the lite pipeline's own comment
(`module_creator.py:260-263`) records that it *was* refused once (`Input should be a valid string`)
and the producer now quotes it and widens `1` → `1.0.0`. Today's compiler coerces with a warning, so
the break was repaired into a deprecation on both sides.

**The question underneath.** These logs predate `verification.json`, the closure and `authorship`, so
when they were written the log genuinely was the only place an agentic run could leave a trace. That is
no longer true: who ran it → `authorship` with `kind: [ai, team]`; what was checked →
`verification.json`; why a variant was called → `provenance.json`. What keeps no better home is the
**verbatim transcript** — prompt, model roster, delegation trail — still worth shipping as reading
material, never as a claim.

## Consumption today

**Nothing reads `manifest.logs`.** This is the finding, and it holds across every consumer repo.

| where | path | what it does |
|---|---|---|
| registry server | `just-dna-registry/src/just_dna_registry/api/routers/modules.py:223-235` | `GET .../versions/{v}/logs` lists name, sha256, size and a fetch URL |
| registry server | `modules.py:238-286` | `GET .../files/{path}` serves any manifest-listed file; a log fetch is explicitly **not** counted as a download |
| registry server | `modules.py:290-320` | the version tarball includes `manifest.logs` entries |
| registry server | `services/publish.py:630` | records `logs=[e.name for e in manifest.logs]` in the structured publish action |
| registry client | `client.py:379` | `RegistryClient.logs(namespace, name, version)` |
| registry CLI | `client_cli.py:144-145` | prints `logs: <names>` after a download |
| just-dna-lite | `webui/src/webui/app.py:280-295` | `/api/agent-log/{name}/{vdir}/{file}` serves a **local generated** log by filesystem path — never from a manifest |
| just-dna-lite | `webui/src/webui/state.py:5502-5521` | `slot_archive_logs` lists local `v*.log` across version dirs for the editing slot |
| just-dna-pipelines | `v1_port/clinvar_panel.py:90`, `v1_port/runner.py:143` | comments only — they *write* logs knowing they will be hashed |
| just-prs / just-prs-mcp | — | nothing |
| just-module-creator | — | nothing. No tool mentions logs |

`aggregate_logs` has **zero callers anywhere** outside `schema/tests/test_aggregate.py` — tested,
documented in `SCHEMAS.md`, never called by product code in any repo. `aggregate_provenance` is in the
same position; `ROADMAP.md:359` still names the module-detail view as its intended consumer.

**Live measurement, production registry `0.18.2` / format `0.6.1`, 2026-08-19:**

```
antonkulaga/aggression_anger_snps      1.0.0 1.0.1 1.1.0 2.0.0   logs=0
antonkulaga/big_five_personality_snps  1.0.0 1.0.1 2.0.0 2.1.0   logs=0
antonkulaga/cognitive_intelligence     1.0.0 1.0.1 2.0.0         logs=0
antonkulaga/risk_impulsivity_snps      1.0.0 1.0.1 2.0.0         logs=0
eric-mods/lactose_tolerance            1.0.0 1.0.1               logs=0
```

16 versions, 5 modules, **not one log entry**. The polygon holds 0 modules. The 16 reference examples
in `just-dna-format/reference_examples/` contain no `.log` file and no `logs/` directory. The feature
is fully built on all three tiers and used by nothing that shipped.

## Blanks for just-dna-lite

- **The Module Manager writes `v<N>.log` and never `logs/<role>.log`, though it runs a named team.**
  Ask: have `RunLog` fan out per member — the PI transcript at `logs/pi.log`, each researcher at
  `logs/researcher-<n>.log`, the reviewer at `logs/reviewer.log` — which is the exact shape
  `schema/tests/test_logs.py` was written against and the registry's never-flatten rule exists to
  protect. Today the reviewer's verdict is buried in a 1.7 MB aggregate nobody will open, and no
  consumer can fetch just the review. **Blocked at two hops**: `state.py:5622` and
  `module_registry.py:158-161` both iterate `iterdir()` with `is_file()`, so a `logs/` subtree is
  silently dropped before publish. Both need `rglob`.
- **Nothing reads a published module's logs back.** Ask: have the lite registry page call
  `RegistryClient.logs(...)` and offer the transcript beside the module card — the endpoint, the
  client method and the fetch URL all exist and are exercised only by the registry's own tests. Today
  a module's provenance is fetchable and invisible.
- **Nobody calls `aggregate_logs`, so cross-version provenance is asserted and never assembled.**
  Ask: on the module-detail view, union the logs across every version's manifest (upstream's
  `ROADMAP.md:359` names this view as the intended consumer). This matters more than it looks:
  `registry upgrade` deliberately does not carry logs forward (`upgrade.py:496-499`), so the union
  across manifests is the *only* thing that makes a v3 module's provenance include v1's. Without a
  caller, the design's "v3 provenance = v1+v2+v3" is a claim no code makes true.
- **A published transcript is unreviewed and can carry anything.** Ask for a pre-publish log review
  step in the Module Manager — the real transcripts contain the full team system prompt, every model
  id, and the user's local upload paths, at up to 4 MB per version. Today a user clicks Register and
  ships it.
- **The log's counts can contradict the module and nothing notices.** v1_port hit this and patched it
  with `_restate_log_counts`. Ask: emit the machine-checkable half of a run as `provenance.json`
  (which has a schema and a per-variant grain) and keep the log for prose. That converts an unverified
  assertion into a manifest block a consumer can read.
- **`RunLog` stamps naive local time.** Ask for ISO-8601 UTC in the header
  (`module_creator.py:96-101`), so two logs from two machines are comparable and sort against every
  other timestamp in the ecosystem.

## Ask the live schema

There is no `describe_table` for this — it is not a table, and `list_tables` will not name it. Ask the
installed package directly:

```python
# the manifest field and its current description
from just_dna_format.manifest import ModuleManifest, FileEntry
ModuleManifest.model_fields["logs"].description
FileEntry.model_fields.keys()                       # name / sha256 / size

# discovery and copy semantics, verbatim from the installed compiler
import inspect
from just_dna_compiler import compiler
print(inspect.getsource(compiler._collect_logs))
print(inspect.signature(compiler.compile_module))   # log_files=...

# what verification does and does not check
from just_dna_format.integrity import verify_manifest
print(verify_manifest.__doc__)                      # steps 4 (inputs) vs 5 (logs)

# the cross-version union, and its real ordering
from just_dna_format.aggregate import aggregate_logs
print(aggregate_logs.__doc__)                       # trust this over SCHEMAS.md
```

For the three *structured* homes a claim about who-did-what belongs in, use the tools rather than this
file: `authoring_reference()` for the `authorship:` block's live roles and kinds, and

```python
from just_dna_format.vocab import VALID_AUTHOR_ROLES, RECOMMENDED_AUTHOR_KINDS
from just_dna_format.manifest import Contribution, ProvenanceItem, ProvenanceDoc, VerificationDoc
```

Verify the version everything above was measured against, and re-measure if it differs:

```python
from importlib.metadata import version
version("just-dna-format"), version("just-dna-compiler"), version("just-dna-registry")
```

Everything in this file was measured against **format 0.6.1 / compiler 0.6.1 / registry 0.18.2** on
2026-08-19.
