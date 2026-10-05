# Agent Guidelines — just-module-creator

A plugin for **Claude Code and Codex**: two manifests, one MCP server, one skill set. The server
wraps the just-dna toolchain in agent-shaped tools; the skills teach the workflow those tools
serve. It is an **application, not a library** — the contract is the MCP tool surface, the skills
and the CLI, so internals are free to change and no `__all__` is curated. **Neither host is
primary**: a change to the tool surface or the skills owes the same to both.

It is **not** a format, a schema or an annotation engine. We own no schema: every column list,
vocabulary and requirement comes from the live pydantic models in `just-dna-format`. Nothing here
reads a sample or calls a genotype. Running a module over real genomes is `just-dna-lite`'s MCP
server, which the host runs **beside** this one; the agent drives it directly via
`module-install-local`, and no code here talks to it.

**just-dna-lite is opt-in.** Engage it only when the author asks to run the module on real
genomes/VCFs or names just-dna-lite. Otherwise the job is done with our own surface (`lint_rows`,
`validate_module`, `enrich_module`, the cross-checks, `compile_module`, `verify_artifact`). Do not
check whether -lite is connected, do not offer to install it, and do not treat its absence as a
gap. A green compile is a finished step. Both servers ship `validate_module`; unless a genome run
was asked for, it means **ours**.

`AGENTS.md` is a symlink to this file. If they differ, that is a bug: `ln -sf CLAUDE.md AGENTS.md`.

---

## Read these first, in this order

Read them yourself. **Do not delegate a document you are about to judge a design against** — a
summary of a rule drops the qualifier the decision turned on. Delegate finding, never deciding.

1. **[docs/DOMAIN.md](docs/DOMAIN.md)** — what a module is, what the four upstream packages
   guarantee, and the traps that constrain what we may build.
2. **[docs/ROADMAP.md](docs/ROADMAP.md)** — active-only; one `## RMn — name` per open item.
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — what shipped, newest first.
4. **[docs/dogfooding.md](docs/dogfooding.md)** — open findings from real use. Read before touching
   the tool surface.

No rule below requires following a link to know what you must not do; links carry positive detail.

### The agent assets this repo ships

**Two kinds of document, split by who invokes them.** A `SKILL.md` is a **command**:
`/`-invocable, listed in every session's prompt, written for a person deciding what they want.
The set is pinned by name in
`tests/test_skills.py::test_the_command_menu_is_what_a_person_would_ask_for` — `create-module`,
`module-status`, `module-revise`, `find-evidence`, `module-publish`, `module-symptom`,
`module-install-local`. A `GUIDE.md` is the same kind of content loaded **by path** by a router
when an agent reaches that step; guides are in nobody's menu. Don't count them in prose — the
roster is `ls skills/`.

The split exists because a twenty-entry menu cost ~14.7k characters of every prompt and asked a
layman to choose between `module-curate` and `module-enrich`. What it costs is auto-loading: a
guide cannot be matched from its description, so a router must name it.
`test_every_guide_is_reachable_from_a_command` walks the link graph from the commands. **When you
add a guide, link it from a router in the same change.**

| Path | What |
|---|---|
| `skills/create-module/SKILL.md` | **The door.** Entry points (nothing yet, a theme plus sources, a handed bundle, a source that publishes rows, an existing module), the stage diagram and order, and the two to four tools each stage calls. Owns **no procedure**. Ceiling 200 lines, pinned by `test_the_router_routes_and_does_not_regrow_into_the_procedure`. |
| `skills/module-101/GUIDE.md` | **The map, high level only** — what a module is, what the plugin can and cannot do, the four packages, the lifecycle including later passes, and the minimal authored surface (`module_spec.yaml` + `variants.csv` + `studies.csv` + `README.md`). No column list, no procedure, no symptom lookup. Written for an LLM to explain modules to a human. |
| **The stage spine** | `module-start` (0–1: triage, licence, spec), `module-draft` (2), `module-curate` (3), `module-enrich` (4), `module-check` (5), `module-compile` (6), `module-close` (6b), `module-publish` (7–8). Each owns its stage's procedure outright, and ends with the discriminator: what to apply silently, what to put in front of a pilot. |
| **The second-pass three** | `module-revise` (which kind of pass, what it invalidates), `module-refresh` (re-running what already ran), `module-diff` (what moved, and the reading that means a source changed its answer). A second pass is the normal case. |
| **References the stages load** | `module-weights` (the column everyone fills and nobody declares), `module-voice` (how labels, conclusions and descriptions read to a lay reader and a professional; twin of just-dna-lite's `docs/REPORT_VOICE.md`), `module-consumer` (the far side of the seam), `find-evidence` (search, verify a PMID, read a paper, what may be quoted; `references/SUPPLEMENTARY.md` is the retrieval ladder for supplementary tables). |
| **Sideways doors** | `module-status` (read a spec directory, work out its stage, list the decisions due) and `module-symptom` (decode a message via `SYMPTOMS.md`, and which layer emitted it). Not stages; they route to the stage that owns the work. |
| `skills/module-install-local/SKILL.md` | Running a compiled module over this machine's genomes via just-dna-lite's MCP server, **only on the author's ask**: `status`, ask which genomes, `install_module` → `start_annotation` → `wait_for_job` → `validate_module`, route each finding back to the stage that owns the cell, re-run. Not a stage, not a publish rehearsal. Manual routes in `references/MANUAL_INSTALL.md`. |
| `skills/module-tables/GUIDE.md` | Which table and where every file sits: table choice by grain, key axes, composition, the three on-disk shapes, the registry's `derived/` layout. No column list. |
| `skills/module-tables/references/*.md` | One dossier per table kind (must cover `hints.DERIVED_TABLE_MODELS ∪ draft.DRAFTABLE`), five for the non-table spec files, and `LAYOUT.md`. The schema half lives upstream at `https://just-dna.life/just-dna-compiler/tables/<name>/`; these keep what a model cannot state — who decides which cell, what an edit moves, the symptom when the table lies. **Anchor on symbol names, never `file:line`.** |
| `skills/module-101/references/SYMPTOMS.md` | Upstream message → cause → action. Read from every stage. |
| `skills/module-101/references/CLI.md` | The CLI surface, and what this server deliberately does not wrap. |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Claude manifest (MCP server via `${CLAUDE_PLUGIN_ROOT}`) and the marketplace file for `/plugin marketplace add ./`. |
| `.codex-plugin/plugin.json` | Codex manifest; launched with `"cwd": "."` because Codex substitutes `${PLUGIN_ROOT}` only in hook commands. Carries the second hand-bumped version. |

**One fact, one home.** The old 1431-line `create-module` monolith was dismantled on the owner's
instruction; the name came back as a router only. If two skills need the same rule, one owns it
and the other links. The moment the router or a stage skill holds a column value, a warning phrase
or another stage's judgement call, the monolith is being rebuilt. Skill ceiling: 500 lines.

---

## 1. Adopting these guidelines: ask, never infer

**When two rules conflict** — this file against a sibling repo's, against the user's global
preferences, or against what the code does — **stop and run a questionnaire.** Don't pick, don't
synthesize a compromise, don't silently follow the more specific file.

1. **Survey first**: read both rules in full and find *why* each exists.
2. **One question per contradiction, batched**, two to four concrete options each.
3. **Each option states its cost**: what breaks, what it forces elsewhere, which rule it contradicts.
4. **Recommend one.**
5. **Record the answer**: the rule into its section, the reasoning into §10 in the user's words.

---

## 2. Non-negotiables

Read the whole list before the first edit. Each carries its reason, because a rule without one
gets rationalised away.

### Environment and packaging

- **Never `uv pip install`.** Use `uv sync` / `uv add` / `uv add --dev`; `uv pip install` bypasses
  `pyproject.toml` and the lockfile.
- **Never call bare `python` / `python3`.** Always `uv run python …`, `uv run pytest …`.
- **Never hardcode a version string.** It comes from `importlib.metadata.version("just-module-creator")`.
  **Exception: the two plugin manifests** (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`)
  are JSON and must be bumped by hand **in the same commit as `pyproject.toml`** — a version bump
  touches **three files**. `tests/test_plugin_manifest.py` fails on a mismatch.
  `.claude-plugin/marketplace.json` deliberately carries no version, and a test pins that too.
- **Never rename a user-facing command to dodge a stale `uv run` wrapper.** Bump the version and
  `uv sync`.
- **Never use a placeholder path or a fabricated example value** in committed code
  (`/my/custom/path/`, `rs999999999`, `1e-328`). Use real identifiers (`rs4988235`, PMID `11788828`).
- **Never commit large data.** No VCF/parquet/gz/BAM/FASTA/`.db`. Over ~5 MB goes through Git LFS;
  a blob committed before `git lfs track` stays in history — surface it and hand the fix to the user.
- **Never run tree operations** beyond what §10 grants. **Never `git stash drop` / `git stash clear`**,
  even on request. **Never `git add -A` / `git add .`** — stage explicit paths.
- **Every git permission is bounded to THIS repository.** Writing a note into `../just-dna-format`
  or `../just-dna-marketplace` is how an upstream finding is filed; committing there is never ours.
  Leaving their tree dirty is the expected outcome.

### Code

- **Never write an inline import.** Top-level, absolute imports. The only exception would be a
  guarded optional dependency, and this repo has none (§5).
- **Never nest a `try`/`except` inside another.** Let typed exceptions propagate; wrap only where a
  real recovery path exists.
- **Never `print` for diagnostics.** `logging` to **stderr** — under stdio the JSON-RPC stream owns
  stdout. `print`/`typer.echo` only for CLI output the user asked for.
- **Never curate `__all__` or add a re-export `__init__.py`.**
- **Never open a socket outside `net.py`.** Every outbound request goes through a `ServiceGate` so
  pacing, User-Agent and the shared NCBI budget cannot drift. `RegistryClient` is upstream's client
  with upstream's pacing and is not an exception; routing through it spends the deployment's budget,
  so the cost is **attribution** (`RouteInfo.answered_by`).
- **Never let a routed answer hide who answered it.** A snapshot-backed answer may come from a local
  lane, from a registry caching proxy, or from a live service after the proxy missed — the values can
  match while egress and provenance differ. `routing.route_for` decides, `routing.missed_at_registry`
  re-labels; a new routed tool owes both. **`offline` outranks every route.**
- **Never make anything that uploads the author's spec automatic.** `POST /drafts` and
  `POST .../derived` send every authored CSV, `module_spec.yaml` and `logs/` to a third party. Reads
  may route themselves; a send is a tool the author calls with an explicit `target`. Reversal recipe
  in `routing.py`'s docstring.
- **Never reach into an upstream private API** (`EutilsClient._get`, reassigning another package's
  decorator state). Use the public surface — `EutilsSettings.identity_params()`, `PacingGate`,
  `EuropePmcClient.lookup()/.fulltext()`, injectable `LookupClients`. If something isn't public, file it.

### The domain rules this server exists to enforce

Each maps to a trap in [docs/DOMAIN.md](docs/DOMAIN.md). These were audited under `RM15` against
this layer's purpose. **Keep applying the test to anything new:** is it physics, is it format's
policy that is also correctly ours, or is it format's policy we should not hold? "Upstream does it
that way" is not an argument. And a refusal that produces a *convincing-looking* artifact instead of
an honest gap is worse than what it refused (title-as-quote, §11).

- **Never hardcode a schema fact** — no column list, vocabulary or requirement. Call `describe_table`
  / `table_requirements` / `authoring_reference` and pass through what they return. The one
  exception is the **subject half** of `authoring._SUBJECTS` ("which table?" is about intent, not
  schema), commented as such. Everything structural is generated: `hints.key_fields(csv)`,
  `hints.DERIVED_TABLE_MODELS`, `scaffold.companions_for`, `compiler.spec_tables`. **A fact you
  cannot generate is guarded by a test, never a comment**, and when it becomes generated the test's
  subject moves rather than the test being deleted. Prefer guards that compare two **independent**
  producers over a derivation compared with itself.
- **Never fill a value from the same source that checks it.** The check then compares a convention
  against itself and agrees, and the row moves from honestly unverified to **apparently verified** —
  which nothing downstream can tell apart. This is one cell/source pair, not a licence to read it as
  "do not write". **The same defect arrives vacuously too**: a `provenance_quote` set to the article
  title always passes `quotes_found`. Ask of any green check: **could this have failed?**
- **Report-never-repair is the FORMAT's stance; we hold a counterstance.** Three parts, all required:
  1. **We may write.** Business decisions are delegated to this layer; filling or correcting a cell
     is legitimate here.
  2. **Every authoring move goes through the log.** `record_override` appends to
     `logs/authoring.log`, which every compile sweeps up and **publishes with no opt-out** — so never
     write an absolute path, credential or transcript fragment there. A hand edit must go through a
     tool or skill that logs. Every new write surface owes the same.
  3. **The agent needs a discriminator.** The real risk is that **the source lags the edge**: ClinVar
     may be stale, an article retracted, a conclusion refuted. "Your row disagrees with ClinVar" is not
     a defect report; silently conforming the row can degrade a module and make the check agree with
     itself. Editing *against* a source needs a reason that outranks the source.

  When we pass upstream's own answer across the boundary, `applied: false` and its `refusal` are
  preserved verbatim — that is upstream reporting its act. Our writes are logged as ours, never
  laundered as upstream's. **Who is flying is unknown**: the agent may serve a layman expecting it
  driven or a geneticist expecting fine control, so a tool writes, logs, and surfaces the decisions
  that need a pilot.
- **An agent MAY locate and write a `provenance_quote`.** The agent reads the article
  (`fetch_fulltext` hands it over whole), so the reading is real; the old prohibition protected a
  fiction about *who* read it and produced empty columns or unmarked title-quotes. The rule is
  **attribution, not abstention**:
  1. Quote **verbatim** and record who located it in `StudyRow.curator` (free text: name, handle or
     model id, row-level because work is mixed — "scientist reads review, agent traverses
     citations"). Nothing checks `curator`; it is for reviewers, paired with `authorship` and the
     `logs/` entry.
  2. **The human author holds full responsibility regardless.** Attribution is about the real
     distribution of roles, never about moving liability.
  3. Honest attribution beats an empty column.

  **Physics that survives:** once a quote is lifted from a fulltext, `quotes_found` on that row is a
  citation-pairing check (catches a wrong PMID), not evidence the claim is in the literature. State
  that; never use it to refuse. Never write a passage that isn't verbatim in the retrieved text.
  Upstream's `hints.ATTESTATION_BEARING` was built on our old reasoning; `S55` withdraws it.
- **Never collapse "unknown" into a boolean.** True / false / **unknown**; `None` is never `False`. A
  check that could not run is not a check that passed. Combine with Kleene semantics:
  `unknown AND false` is `false`.
- **Never treat a determinism gate as a correctness gate.** `--strict`, a digest match, a
  reproducible build mean *reproducible*, not *right*.
- **Never expose a path to `resolve_with_ensembl=False`.** It is the master switch for *all*
  resolution, injected `resolution.csv` included, and compiles every row with `chrom=None`
  **successfully**. `compile_module` pins it `True` with `ensembl_cache=None`; upstream refused the
  rename (`S14`), so the pin is permanent.
- **Never let a module carry two spellings of one sidecar.** `licensing.csv` and `sources.csv` are
  one table; both read, only the preferred one is created, both present is an **error**. Route writes
  through `layout.sidecar_write_path` and read `layout.preferred_spelling` /
  `is_deprecated_spelling`. The rename stops at the CSV: `sources.parquet` and `manifest.sources`
  keep their names.
- **Never read `fully_resolved` without `resolution_subjects`, and never coalesce a null counter to
  zero.** Over an empty list the flag is `all([])`. The RM44/S31/S33 counters are `int | None`: `0`
  is an answer, `None` means nothing counted.
- **Never place a `*Unavailable` except-arm after its parent.** Each is a subclass of the type beside
  it, so parent-first makes the outage arm dead code. One tuple is safe; separate arms go
  narrow-first. `tests/test_passes.py` walks the AST for this.
- **Containment never moves; the write surface does.**
  1. **Containment is absolute.** Every path resolves through `_shared.resolve_dir` so
     `JMC_WORKSPACE` holds. Nor may we invent a file **inside** a spec directory: a name absent from
     `specfiles.RECOGNIZED_SPEC_FILES` is dropped by the next server-side rebuild, so our bookkeeping
     goes to a resolved cache/workspace path.
  2. **What we may write is decided by the counterstance, not by upstream's surface.** Revising an
     authored cell is legitimate if it is logged, respects the discriminator (evident and mechanical
     → apply silently; judged or checked → surface), and any write that destroys content captures
     first and **verifies the capture**.

  Not licensed: overwriting an authored value silently, writing one from the source that checks it,
  or conforming a row to an archive that disagrees with it.
- **Never delete a derived sidecar without a verified capture, and never put the capture in the spec
  directory.** Sidecars are merge-not-clobber, so re-deriving means deleting, which discards
  hand-curated rows (`resolution.csv`'s `source="manual"` above all). `refresh_sidecar` copies out,
  reads back and hashes, and only then unlinks. **Never classify against a partial re-derivation**:
  an unreachable source, a no-op pass or an empty fresh table restores the captured bytes, because an
  unfilled table reports every real row as withdrawn.
- **Never let a per-call argument loosen the offline ceiling.** `JMC_OFFLINE` ORs with a per-call
  `offline` via `_shared.offline_for`; never read them separately.
- **Never silently fall back when primary data is missing.** Refuse, or name the substitute.
- **Never resolve a contradiction between two rules by inference.** Run §1.

---

## 3. Repository layout, data and assets

```
src/just_module_creator/   source (src layout). routing.py = thick/thin decision;
                           tools/proxy.py = registry caching-proxy tools;
                           provisioning.py = snapshot-lane pricing and offers
tests/                     pytest suite — in-memory, offline
docs/                      all markdown except this file and README.md
skills/<name>/             one directory per skill or guide (roster: the table above)
.claude-plugin/ .codex-plugin/   manifests
assets/                    fixtures that MUST travel — committed
data/input|interim|output  git-ignored, never travels
scripts/                   operational one-offs, not importable
```

- `data/` is ignore-all + allowlist; to commit a subtree add `!<dir>/` and `!<dir>/**`.
- Test data lives in `assets/`. Tests write to `tmp_path` or a resolved cache dir, never the tree.
- Sibling repos are **read-only** unless the task targets them (§11 for paths).

---

## 4. Build, run, test

```bash
uv sync
uv run pytest                                  # -vvv when diagnosing
uv run ruff check . && uv run pyright
uv run just-module-creator stdio
uv run just-module-creator http --port 3011
uv run fastmcp dev fastmcp.json                # MCP Inspector
claude --plugin-dir .
uv run manuscript manuscript                   # paper → .md + .pdf (§8)
```

`just` is not installed on this box; read the `justfile` for recipes, don't invoke it (re-check with
`just --version`). **Always run `uv run pytest` and `uv run ruff check .` after changing code.**
Python ≥ 3.13.

Every network CLI **prints its URL** in its first lines. Every CLI loads `.env` via `python-dotenv`
(`override=False`) before reading config. New configurable values are read from env with defaults,
documented in `.env.template`, and mentioned here.

**Configuration: three layers read, one written, never a project `.env`.** `userconfig.load_env`
reads process env, then a `.env` walked up from the **working directory** (never bare
`load_dotenv()`, which walks from the package file — the plugin copy), then the user config file
(`platformdirs.user_config_dir("just-module-creator")/.env` or `JMC_CONFIG_FILE`).
`remember_setting` writes the last, owner-only, for names on `userconfig.SAVABLE`. Reason: Claude
Code starts the server in the author's project, Codex in the plugin's per-version copy. **A skill or
tool message asking to persist anything names `remember_setting`, never a file.**

**Lists live in `state.json` (`localstore`): registry accounts and the todo list.** Many tokens per
instance, each with namespaces and install-id. `auth.resolve_api_key` picks by the namespace a call
names, falls back to the instance's default account, otherwise refuses listing the saved accounts
(*pick by namespace, or ask*). `accountcheck` re-checks saved tokens on a daemon thread at a real
start (never in `build_server`), recording `valid` / `invalid` / `unreachable` / `timeout`; only
`invalid` removes a token from selection. **Every write to either file takes a verified backup
first** (`userconfig.backup`, newest 50 kept) under a `filelock`.

**An env-backed preference is three-valued** (`bool | None`: null = not asked, `False` = declined),
e.g. `JMC_CACHE_PREWARM` / `JMC_CACHE_FULL`, documented in `.env.template`. **How an author is asked
lives in the skill that ships** (`skills/module-start/GUIDE.md` here), because this file reaches
nobody's install. Design constraint here, conduct in the skill; never split one rule across both.

**A first-run question may not require configuration the author has no reason to have done.** A tool
may withhold on a condition it can **name and repair** (an unwritable path), never on an unset
variable — unset is the default location. Cost ceilings are per item.

**Timestamps: store ISO-8601 UTC, display local.** Never naive `YYYY-MM-DD HH:MM:SS`.

---

## 5. Coding standards

- **Type hints mandatory; `pathlib.Path` internally.** Tool signatures take `str` (the MCP wire
  type) and convert immediately via `_shared.resolve_dir`.
- **Everything is a hard dependency**: the four just-dna packages plus `fastmcp[tasks]`, `pydantic`,
  `pydantic-settings`, `typer`, `anyio`, `python-dotenv`, `httpx`, `tenacity`. No extras, no optional
  imports. `httpx`/`tenacity` are declared because `net.py` uses them directly.
- **Don't hand-roll what the enricher already uses.** Retries: `tenacity` with upstream's
  `net.attempt_floor`. Pacing: upstream's `PacingGate`, shared as the **same instance** with
  `EutilsClient` so the NCBI budget is one budget. `ServiceGate` adds a lock and nothing else.
- **We read the ecosystem's env vars; we never forward them.** When we make the call, reading
  `JUST_DNA_CONTACT_EMAIL` / `NCBI_API_KEY` through `EutilsSettings` is right.
- **Contact chain**: `JMC_USER_EMAIL` → `JUST_DNA_CONTACT_EMAIL` → `settings.DEFAULT_CONTACT_EMAIL`.
  The middle step stays inherited: `build_services` passes `email=None` and lets
  `EutilsSettings.__post_init__` read it. **Never read `JUST_DNA_CONTACT_EMAIL` yourself.** Never
  fabricate an address; the default is the project's own, and `build_services` logs which step
  answered. `contact_email()` returns `str`, so `if not email:` branches are dead code.
- **A long tool talks to its caller through `_shared.narrate`, never `ctx.info`.** It uses
  `report_progress` plus stderr, which works on every wire; `ctx.info` raises in a fastmcp-4
  background task.
- **Typer for the CLI. Pydantic 2 at every boundary** — every tool returns a model from `models.py`.
- **Constrained vocabularies**: local config may be a `Literal`; anything persisted to a wire artifact
  would need `frozenset[str]` + validator. Upstream owns every wire vocabulary.
- **Polars only where upstream hands it to us.**
- **Two kinds of our own finding, split by unit.** `authored_checks.py`: per-table lint findings via
  `lint_rows` / `validate_module`, `source="just-module-creator"`. `audit.py`: the whole-directory
  decision list behind `audit_module`. Both offline, neither blocks a compile. **Anything that asks a
  source is a check** and belongs beside `check_identifiers`, where it writes an attestation; an audit
  writes nothing.
- **An audit signal is three-valued**: `decide` / `clear` / `not_computed` (with `why_not`). Never fold
  "the file is missing" into "nothing to decide".
- **Deterministic ordering is load-bearing** wherever output is compared or hashed — sort explicitly.
- **Preserve upstream's distinctions** (`error`/`warning`/`info`, `applied`/`refusal`,
  `None`-means-unchecked) via `_shared.to_findings` / `to_alterations`.
- **Aggregate repeated warnings** by reason, with a count.
- **A deprecation in code you touched is a blocker**: fix it and update this file.
- **Refactor internals aggressively.** Breaking the tool surface, skills or CLI is allowed but
  deliberate and versioned.

### Parity with upstream is the default, and a gap is a bug

This plugin is the **only** user-side exposure of the just-dna toolchain. When upstream adds a
drafting source, pass or check, **wrapping it is the default**; not wrapping it needs a written reason
in `docs/just-dna-format-pending-fixes.md`. The signature of the defect: **the surface names a thing
it cannot do** (e.g. `list_tables` naming a sidecar no tool could fill) — invisible from inside the
code.

Measure the gap; both sides move:

```bash
ls ../just-dna-format/enricher/src/just_dna_enricher/*_draft.py
uv run just-dna-enricher --help
uv run python -c "from just_dna_compiler import hints; print(sorted(hints.DERIVED_TABLE_MODELS))"
```

**Not grounds** for leaving one out: that it makes a module non-commercial (licence is per-module, in
`licensing.csv`), or that nobody has exercised it (argues for a test). **Grounds**: it is an
operator's sweep, a build hook, or only a deployment calls it. Say which.

### How to add a tool

1. **There is no tier** (removed in 0.21.0 — it repeatedly hid steps the taught workflow named).
   Pick the `register_*` group by subject matter. If it writes to the registry, it is token-gated.
   **If its cost scales with a corpus, say so in the docstring** (e.g. `enrich_gwas_effects` spends
   `1 + 2N` requests); `test_the_corpus_sized_tools_say_what_they_cost` pins that.
   `test_every_tool_the_taught_workflow_names_exists` and
   `test_docstrings_only_name_tools_that_exist` guard the surface against naming tools that aren't
   registered.

   **The one ungated registry write is `registry_register`**, because it mints the token. It lives in
   `auth.py` and stays visible however the listing is narrowed. If a second such tool appears, ask
   whether "ungated onboarding" is a category — don't grow the exception silently.
2. Add it inside its `register_*` with type hints, a docstring and `ToolAnnotations`. **Descriptions
   are context someone pays for.** In `toolbox.CORE`: one paragraph, two at most. Elsewhere: up to
   five, ceiling six. Tests pin both. Say what it does, what arguments mean, what it refuses; **the
   reasoning goes in a comment above it**, not in the description. Move reasons, never delete them.
   Re-measure listing size rather than trusting old numbers.
3. Return a model from `models.py`.
4. Paths through `resolve_dir`; network through `offline_for` and `anyio.to_thread.run_sync`.
5. Gated tools are `async def`, take `ctx: Context`, `await resolve_api_key(ctx, settings, target)`,
   return `unauthenticated_result(settings, target)` on `None`, are tagged `registry_write`, and are
   listed in `auth.GATED_TOOLS`. **Session state is FastMCP's own** (`ctx.set_state` / `get_state`
   under `auth.state_key(target)`; the target stays in the key). Call `auth.session_state_persists`
   before storing and refuse naming the env var — **never report a success the next call cannot
   find**. Under the fastmcp `<4` pin that guard is dormant (handshake sessions persist); on a 4.x
   re-upgrade, see §11.
6. Add a test using the in-memory client.
7. **Visibility is not authorization.** `mcp.enable()` / `disable()` are server-global — startup only.
   `ctx.enable_components()` is session-scoped — the only one a request may drive.
   `JMC_HIDE_GATED_UNTIL_AUTH` (off by default) combines them; a hidden tool answers "Unknown tool"
   instead of the refusal that explains how to get a token.
8. **Narrowing the listing is allowed; narrowing what a session can reach is not.** `JMC_TOOL_SEARCH`
   swaps the catalog for `search_tools` + `call_tool`; `JMC_TOOLBOX=layered` lists `core` + `toolbox`
   and reveals groups on request. **Every new tool joins a group in `toolbox.GROUPS`**
   (`test_every_registered_tool_is_in_exactly_one_group`); `CORE` only if the taught order needs it.
   `tool_search.ALWAYS_VISIBLE` holds what a client must see to get in at all.

---

## 6. Testing — layer 1

- **Real data, ground truth.** Real rsIDs and PMIDs; compute expected values from the fixture.
  Hardcoding a documented constant is fine; a row count read off a dump is not.
- **Meaningful assertions** — relationships and set equality over `len(df) > 0`.
- **Never mock the transformation under test.** Only the network is excluded, by the offline ceiling.
- **The suite is hermetic by mechanism.** `conftest`'s autouse `_hermetic_configuration` points
  `env_file` at a nonexistent path and clears every variable derived from `Settings.model_fields`
  (plus four hand-listed upstream names), so a bare `Settings()` can't pick up a live token.
  `offline_settings()` forces `offline=True`. Don't remove `env_file=".env"` from `model_config` —
  the product needs it. An upstream library (`just_dna_enricher.locations`) calls `load_dotenv`
  itself; the fixture neutralizes it.
- **A test meaning "no credential" must say so**: `setenv(VAR, "")`, not `delenv` —
  `load_dotenv(override=False)` skips a key that is merely present.
- **Suspect ordering** when a test passes alone and fails in the suite.
- **Never let a fixture compute its expected value with the code under test.** Build it the way the
  *producer* builds it (e.g. a real publish uses `file_entries`, not the newline-normalizing hasher).
  Ask of a green fixture: could this have failed?
- **A subset/difference assertion needs a denominator.** `A <= B` and `not (A - B)` pass when `A` is
  empty, and a foreign enumeration goes empty when an import moves. Give it one of: an explicit count
  floor (well under today's number), an adjacent exact assertion on a known member, or put the
  foreign set on the **right** of `<=`. Floor the inputs, never the answer (an empty result can be the
  good state).
  - **A split on text** needs the split checked: marker present, block neither empty nor the whole file.
  - **A negative assertion** (`X not in body`) needs the haystack established by a positive assertion
    first.
  - **A search can't be floored, so anchor it**: check the name you're most sure of first; if it's
    missing, the instrument is wrong, not the subject.
- **Never claim a test "would have caught" a bug** without running it against the buggy code.
- `from conftest import ...`, not `from tests.conftest import ...` — a dependency ships a `tests`
  package that shadows ours.

---

## 7. Dogfooding — layer 2

Tests prove the code does what it was told; dogfooding asks whether it is **usable, and what is
missing**. Both are required. Don't verify the tool's answers with a second implementation while
dogfooding — that is a test.

- **A missing capability is the result, not an obstacle.** Reaching for an ad-hoc script or raw HTTP
  call ends the signal. Record the gap; if it blocks the work, build it into the product.
- **Attack claims, not gaps** — where a docstring promises what the code doesn't do.
- **Use real data.** Pick probes where the design generalized from one case (if the example shows one,
  use a real case with two).
- **Dogfood a finding before reporting it**, and finish each probe as a committed reference example
  whose README names what it broke on the old behaviour.
- **Separate "fix it" from "surface it"** before writing code, and say why each repair is wrong for
  the surfaced ones.

Findings carry stable `F#` IDs and **move**, never duplicate: `docs/dogfooding.md` (open) →
`docs/previous_issues.md` (resolved here) or `docs/just-dna-format-pending-fixes.md` (blocked
upstream). One mitigated here but still owed upstream may appear in two.

---

## 8. Docs and their lifecycle

- **All new markdown goes in `docs/`** (except this file and `README.md`). Every prohibition lives
  here in full, because a `don't` behind a link doesn't get read.
- **`docs/ROADMAP.md` is active-only**; shipped items move to `docs/ROADMAP_HISTORY.md`.
- **`docs/CHANGELOG.md`** records what shipped, newest first, including cross-repo changes on our side.
- **Update this file and the affected docs in the same change as the refactor.** Policy first.
- **Keep skills and tool docstrings in agreement**, especially about what a tool refuses.
- **Run commands yourself**, except ones needing an interactive terminal.
- **Before a PR**, show `git diff <upstream>/main --stat HEAD` and
  `git log <upstream>/main..HEAD --oneline` and wait for approval.

### Manuscript writing

Draft in `docs/manuscript/` (EASRP 2026 `template.tex` + `easrp2026.sty`). Edit `manuscript.tex`,
then `uv run manuscript manuscript` to rebuild `.md` + `.pdf` (`--nopdf` for Markdown only). Section
order follows the empty template (Introduction, Related work, Method, Results, Discussion,
Conclusion). Related-work papers go in `data/cache/for_manuscript/` (gitignored). Process notes in
`docs/manuscript/README.md`. Tectonic setup: §11.

### Upstream findings go to the producer, never into a workaround

We own none of format / compiler / enricher / registry. **File where the fix would land:**

| The fix would land in | File it in |
|---|---|
| format, compiler, enricher | `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md` (`S<n>`) |
| the registry service, its client, or a `just-dna-pipelines` command calling it | `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md` (separate `S<n>` series) |
| `just-dna-lite` / `just-dna-pipelines` itself | `../just-dna-lite/docs/CONSUMER_HANDOFF_from_just-module-creator.md`, appended as a dated section with inline evidence |

"Marketplace" is a stale directory name; in prose say **the registry**. The -lite channel is
unnumbered and has no triage loop: silence or a refusal is a complete answer to record. Its file is
untracked in their tree; that is fine.

**The format and registry intakes are split**: the inbox holds only unanswered entries; once a
`**Status —**` reply exists, the entry moves verbatim to `CONSUMER_SUGGESTIONS_HISTORY.md` with an
index. So:

- **An empty inbox means nothing is owed**, not that notes were lost — check the history index.
- **Never number a new `S<n>` from what you see.** Run `.claude/triage-state.py --next` in the repo
  you're filing into. Ids are never reused.
- **Check for duplicates first**, in the inbox, the history file *and our own `docs/`*. A second
  reproduction is a corroboration appended to the existing entry.
- **Three states: answered ≠ fixed in tree ≠ released.** Only "released and in our lockfile" lets a
  mitigation come out. Check `RM_TOC.md` for accepted-but-open work.
- **Verify against the installed package, never the sibling checkout.** `uv run` resolves against the
  project you're standing in, and the version string can match while the symbol differs:

  ```bash
  uv run --project /data/sources/just-module-creator python -c "
  import just_dna_format; from just_dna_format.spec import StudyRow
  print(just_dna_format.__file__)                     # MUST contain .venv/site-packages
  print('curator' in StudyRow.model_fields)"
  ```
- **A refusal is an answer**, and load-bearing — record it as settled (e.g. `S14` made our
  `resolve_with_ensembl` pin permanent).
- **A gap in the docs is a finding.** If you had to probe to learn it, file it with the experiment.
- **File it the moment you find it. Do not batch.** Upstream ships within hours; a note filed after
  the release window buys nothing.
- **A guard is not a substitute for the note**, and never a README selling point.
- **Write the note and stop.** Never commit there, never open a PR there.
- **Track our side**: an `F<n>` in `docs/just-dna-format-pending-fixes.md` while open, and the
  changelog if we shipped a mitigation.
- **Re-read upstream verdicts before trusting our own `Status:` lines** — they go stale silently. A
  status names the upstream state *and* whether the fix is in what we install.
- **Never work around it silently in the data.** Leave the data truthful, state the limit, file it.

### Prose style

**Three claim-shapes rot silently. Check anything you write against them:**

1. **A check is only as wide as the table it reads.** Name its scope, or readers over-trust it (e.g.
   `check_identifiers` reads `variants.csv` only).
2. **A counted claim in prose rots like a hand-kept list.** State the rule and let the reader run the
   call; if a number must appear, say what was counted and when.
3. **An enforcement claim needs its surface named.** *Mandatory*, *refused*, *checked* and *warned*
   are different strengths; a hint never fails a build.

Natural human prose; no em-dash pile-ups, filler transitions or marketing voice. Never overpromise.
**`README.md` says what this plugin does and is never a catalogue of upstream defects.** Telling an
author "never pass this flag" in a skill or `references/CLI.md` is different and correct. **Never
describe this project as interpreting a genome, calling a genotype, or giving medical advice.**

---

## 9. Self-correction

When outdated API knowledge causes a real failure, fix the code **and** update this file and affected
docs. When the user corrects a preference, it goes into §10 in their words, with the reason.

### Running two agents across one night: the relay protocol

Create `docs/NIGHT-RELAY.md` with a `STATE:` line, the legal transitions, one append-only section per role.

1. **Read `STATE:` first.** Not your starting state → stop, write nothing, report what you found.
2. **Claim by writing your transition first** (UTC timestamp) and commit immediately.
3. **A `*-RUNNING` state older than four hours** (measured from the newest history entry, not `SINCE:`)
   is a dead agent: append a note, move the state back one step, stop. Live agents append proof-of-life.
4. **Never edit another role's section.**
5. **On finish, write what the next role needs decided**, including cheaply reversible calls you made.
   Commit.

The waiting agent arms a file monitor on `STATE:` (tested on a dummy file first) rather than polling.

---

## 10. Learned user preferences

*Append-only (grouped by theme in the 2026-10-05 rewrite). One entry each, in the user's terms, with the why.*

**Git**
- **"auto-commit grant lingers... you commit and tag as you go."** Standing grant: commit and tag
  without asking. Meaningfully sized commits, explicit paths, tags at a version bump matching
  `pyproject.toml`.
- **"Your commit permit is bounded by this repo only."** Writing an upstream note is the whole job.
- **Pushing is never persistent.** "push — in this session only." Releases and branch management stay
  the user's.
- **"When we are in plugin development mode we should remove and reinstall it on changes."** An
  install is a copy in `~/.claude/plugins/cache/`. Reinstall **once per batch**, before a new-session
  test, never per edit — it doesn't reach the running session, and uninstall deletes the running
  server's cache:
  ```bash
  claude plugin uninstall just-module-creator@just-dna
  claude plugin marketplace update just-dna
  claude plugin install just-module-creator@just-dna
  ```
  Then tell the user to start a new session; check `~/.claude/plugins/installed_plugins.json` matches
  `pyproject.toml`.

**Pace and scope**
- **"I need to have mvp, then pace declines."** End-to-end first, refine after.
- **"Push to the maximum; defer only items that honestly depend on architectural decisions and
  questions that came to be after now."** In unattended runs, a question with a written spec is
  decided, with reasoning **and a reversal recipe** recorded.
- **"Tools are automation. Minimizing excessive calls from model is favorable."** Checks the server
  can run itself (token validation, env-token import, install-id) run at start and are recorded —
  without multiplying requests, and never making a decision a person owns.

**Upstream and docs**
- **"Update your memory to fill in these immediately upon finding."** File upstream notes at
  discovery, never batched (§8).
- **"Cleanout readme from parent lib issues, wtf really."** README describes this plugin only.
- **"create-module preference on lists is proper; they may drift."** Don't restate schema lists; ask
  the tool.
- **"Asking them is no big deal; but don't come empty handed — show them the tool."** An
  authoring-workflow gap is ours to build first, then offer upstream. A schema, hash, check-scope or
  wire gap is theirs and filed immediately.
- **"I think it makes sense to upkeep tools/drafting surfaces parity in the plugin."** Parity is the
  default; abstention needs an argument (§5).
- **"Do not let a third-party evaluation turn into NIH."** Copying code ("leeching the code is
  yikes") is out; a dependency with attribution or a fork is fine. Our gate (one `ServiceGate`, one
  budget) is not a bicycle; our source list is.

**What the product is**
- **"The goal of this plugin is to be ai-coauthor. And it can be driven by a lyman."** The owner
  brings a theme and sources; triage, rows, conclusions and located passages are the agent's. Asking
  the layman for a `provenance_quote` or a publish-quality verdict is "v2 work from a wrong person".
  **"AI totaly can read articles."**
- **"Offline makes sense annotation-time, not author-time."** Authoring is networked by nature;
  `JMC_OFFLINE` stays (off by default, the suite's ceiling depends on it) but may not veto a broad
  improvement for a niche one.
- **"Versions and curation carry NO implicit contract."** "1.0.0 2.0.0 arent strict milestones." Trust
  is a signal read off the module ("v52 and 2+ curator med_geneticists? That's platinum"), so never
  withhold a publish or bump waiting for a milestone. The signal lives in `authorship`.
- **This is a *new*-module creator: "Idempotent `to_current_state`, so to say."** Recipes target the
  current release only — no per-era branches, no "under 0.5 this differed". Uplift mechanics are
  upstream's. Detecting an input's era is fine; preserving it is not. The upgrade path gets built from
  real authoring transcripts, not invented.
- **"Don't say 'broken' to user — say: needs this this and this decision to work in latest."** An old
  module is out of date, not defective. A revisit outputs a **decision list**: evident and mechanical
  changes are applied silently; checked or authored values (genotype, `weight`, `clin_sig`,
  conclusion, `provenance_quote`) go in the list. The rulebook for the boundary doesn't exist yet;
  when unsure, surface.
- **"Making decision != executing it."** A tool may execute any authored decision it is handed
  explicitly (e.g. `prune_rows` with a keep-list); it may not infer one.
- **"Can we get gene if derived sidecars or not? If yes — ours, if none provides it — theirs."** If a
  sidecar already carries a derived value, joining it is ours; producing it is upstream's pass. A
  cross-sidecar dependency is itself worth reporting upstream.
- **A machine-located `provenance_quote` is legitimate** — "demolish full force". Required instead:
  per-row "whoddunit" attribution. "AI is not a subject of right, so the human author holds the full
  responsibility, but at least honest highlights of real distribution of roles is 100% better than
  fake 'I read it all' fingerscrossed confirmation." (§2.)

**Publishing**
- **"For non-skilled users, publish to polygon explicitly, unless they explicitly ask for 'official
  catalog' or alike."** Production is immutable. The risk is an agent volunteering `target="prod"`.
  Prefix the **module** name as well as the namespace on a first rehearsal so `purge-test-data`
  collects it. Lives in `skills/module-publish/SKILL.md` and `server.INSTRUCTIONS`.
- **"If you find the module is genuinely good and is underrepresented in official catalog — suggest
  yourself."** Judged on checks, not impressions: a prod `registry_search` showing the gap, strict
  validate and compile, produced resolution, every PMID from a read search result, a declared
  licence, nothing guessed, a rehearsal read back. Underrepresented is necessary, not sufficient
  (`assets/fto_bmi` is the counter-example: one locus, no licence, no readme).

**Skills and voice**
- **"Eliminate it entirely; drag away every quote until that doc is empty."** The unit of a skill is
  the step an agent is on. One fact, one home; 500-line ceiling.
- **"People want /create-module back... make it a small helper/wrapper skill."** A split that is right
  internally can delete the users' entry point; the repair is a router at the old name, never the old
  file. Reversal recipe: move the diagram and entrypoint table back into `module-101`, delete
  `skills/create-module/`, drop the shape test, restore counts in `tests/test_skills.py`,
  `tests/test_plugin_manifest.py` and the Claude manifest description.
- **"Triage comands available to user, it is too puzzling for them to have a dozen."** The menu holds
  what a person arrives wanting; never which step the agent is on. Seven chosen, `module-tables`
  dropped deliberately. **Don't re-promote a guide.**
- **"User who needs [101] doesn't know it needs 101. And one who knows no longer needs it."** A command
  earns its place only if the person who wants it can recognise the want. Otherwise an agent notices:
  `create-module` step 0 routes a question or a wish in lay vocabulary to `module-101` first. "101 is
  for llm and for LLM to be able to 101 human."
- **"5-15 words length is optimum otherwise it looks bloated."** For `module.description`. Prose norm
  at the point of writing (`module_spec.md`, `scaffold_module`'s `next_step`), not a validator.
- **"It should focus on explainable potential phenotype changes ... in comparison to wildtype humans."**
  Every conclusion says what the reader would notice compared with carriers of the most common
  version, how big, and how sure — or that no noticeable difference is known. Owned by `module-voice`.

**just-dna-lite**
- **"I want to be able to apply it on a set of genomes I selected, see which results I get, and
  iteratively improve the module."** Settled: two servers, the skill orchestrates; per-sample rows
  may flow to the agent; validation is coverage, score shape and join health computed on the -lite
  side. No sample id or genotype is ever written into a module (`logs/` publishes).
- **"just-dna-lite as MCP is optional."** Route there only on the author's ask, never as the step
  after a compile.

---

## 11. Learned workspace facts

*Append-only. Environment, credentials layout, host quirks, sibling paths. Prefer the call that
answers a question over a number written here.*

**Paths**
- Siblings under `/data/sources/`: `just-dna-format` (format, compiler, enricher and their docs),
  `just-dna-lite`, and `just-dna-registry` — `just-dna-marketplace` is a **symlink** to it, so a
  resolved `just-dna-registry` path is not a second checkout.
- **`just-dna-pipelines` is a subdirectory of the -lite checkout**
  (`just-dna-lite/just-dna-pipelines/src/`), not under its `src/`. A grep rooted wrong reports real
  names as missing.
- **`scaffold` and `hints` live in the compiler**, not in format; `SourceRow` is in
  `just_dna_format.sources`, not `.spec`.
- Triage scripts are `.claude/triage-state.py` in both upstream repos.

**Versions and dependencies**
- **Upstream floors live in `pyproject.toml`**, with the reasoning in its comments; the format pin is
  `>=0.7.x,<0.8` deliberately (one minor, both ends). Verify capabilities by symbol with the
  `--project` recipe in §8, never from a line here. A floor bump is not adoption: sweep new authored
  fields into the skills.
- **fastmcp is pinned `>=3.4.6,<4`.** fastmcp 4 negotiates the sessionless 2026-07-28 wire, so
  session reveals and stored tokens evaporate (fastmcp#4920), and some clients can't connect.
  **Gate**: `tests/test_toolbox.py::test_a_reveal_reaches_a_default_mode_client`; lift when it passes on
  a 4.x. `ToolAnnotations` kwargs are **camelCase** on purpose (SDK 1.x silently drops snake_case) —
  don't revert. Owed on re-upgrade: restore the `MODERN_PROTOCOL_VERSIONS` branch in
  `session_state_persists`, re-add `mode="legacy"` in `make_client`, fix `toolbox` reporting a reveal
  the next call can't find, and add the persistence guard to `registry_register`. Full recipe: memory
  `fastmcp-pinned-below-4.md`.
- **Three mitigations are kept on purpose**: `ServiceGate`'s lock, `compile_module`'s
  `resolve_with_ensembl=True` pin, and `research._module_card`'s defensive projection (`get_module` is
  not version-guarded, so an older server answers unchecked).
- **Upstream answers within hours.** After filing, re-check the tree before quoting our mitigation as
  current; prefer wording that survives the fix landing.
- **A drafter fix doesn't reach a module already drafted.** Re-run and diff; whether that converges
  depends on whether the fix skipped rows or moved identities.
- **After `uv sync`, `/reload-plugins`** — the session's server imports lazily and otherwise answers
  every tool with a `ModuleNotFoundError`.

**Registry**
- **Two instances, no shared database**: production (immutable catalog) and the polygon
  (`target="test"`, rehearsals). Accounts, tokens and namespaces exist on one only. Clients pass
  `expect_mode=target`, so a polygon publish that would land on prod refuses. Writes default to the
  polygon; **catalog reads require `target`** (`registry_search`, `registry_get_module`,
  `registry_download`, `registry_is_published`, `compare_to_published`). Production refuses
  `test-`prefixed data.
- **Credentials**: saved accounts are in `state.json`; ask `registry_accounts` / `registry_whoami`
  rather than trusting a note. `JMC_INSTALL_ID` is a proof-of-work string; destroying it is the
  user's call. A dead token makes every registry tool say "rejected your token" — clear it rather than
  leave it stale.
- **The handshake is not validation.** `assert_compatible()` checks major.minor only; a field added in
  a patch release is refused by an older server's `extra="forbid"` model while every local gate passes.
  Only a real `registry_check` against the target instance proves a publish. `registry_health`'s
  `contract_compatible` is the field to read, not `status: "ok"`. **Never drop a field to get green.**
- **What a registry holds**: `registry_health(target=…)`'s `catalog` block, in one call. Instance
  versions: `curl -s https://module-registry.just-dna.life/api/v1/version` (polygon:
  `module-polygon.just-dna.life`).
- **Release notes carry a `Client surface:` line**, and it is trustworthy for "did our methods move";
  additions still need reading.
- **Online `registry_check` caps at 500 subjects** (`HTTP 422` above); dry-run larger modules with
  `offline=true`. When the server's compiler differs from ours, `artifact_digest` differs while
  `content_signature` matches — read the second. Polygon rate limits: dry runs serialised, publishes
  10/h; run registry calls one at a time (memory `polygon-rate-limits.md`).
- **The polygon carries `test-sheep/*` rehearsals** from dogfooding and ports (clawbio PGx genes,
  longevitymap, kunkle2019, two quote-remediation rehearsals). All are `test-`prefixed on both halves
  so `purge-test-data` collects them; records in the memory files and `data/interim/`.

**Hashing and spec files**
- **`manifest.inputs[]` is hashed over RAW bytes** (`compiler.file_entries`, locally and server-side).
  `newline_normalized_file_entries` is for the closure attestation only; using it for a published
  comparison flags every CRLF file (and Python's `csv` writes CRLF).
- **An invented file in a spec directory is silently dropped** by a server-side rebuild
  (`RECOGNIZED_SPEC_FILES`). Our state goes to a resolved cache/workspace path; the cost is that it
  doesn't travel, which is the honest limit.
- **`logs/authoring.log` publishes** with every compile, no opt-out.

**Host**
- **`JUST_DNA_PIPELINES_CACHE_DIR=/data/just-dna-cache`** (set in `.env`). Unset falls back silently
  to `~/.cache/just-dna-pipelines`, and the Ensembl snapshot alone is ~14 GB — it once filled `/`.
  `~/.cache/just-dna-pipelines` is a deliberate read-only *file* so `mkdir` fails loudly; if a tool
  raises `NotADirectoryError`, set the variable, never delete the guard. The V2 GraphQL endpoint 404ing
  and falling back to REST is expected.
- **Tectonic**: the wheel's build needs a newer glibc than this box; the static musl build at
  `~/.local/bin/tectonic-musl` is named by `MANUSCRIPT_TECTONIC` in `.env`. Set `TECTONIC_CACHE_DIR`
  too. Without it the command writes Markdown, fails, and leaves a stale `manuscript.pdf` — don't read
  a page count off it. `scripts/page_budget.py` estimates length when a render is impossible.
- **Plugin commands shadow skills**: a `commands/<name>.md` hides `skills/<name>/SKILL.md` entirely.
  A skill needs no command file to be `/`-invocable; `tests/test_plugin_manifest.py` fails on a name
  collision. Lesson: test what the user does (invoke the name), not what you built.

**Git hygiene lessons**
- **`git add -u <dir>` swept a concurrent session's edits into my commits.** A directory is not an
  explicit path; run `git status --short` before every commit.
- **`cd` leaks between Bash calls** and once put git commands into an upstream repo. Use absolute paths.

**Corpora and benchmarks**
- **Outside-driver corpora**: Anton's four authoring transcripts (memory
  `anton-authoring-transcripts.md`; published as the `antonkulaga/*` modules), and the two 2026-08-21
  dogfooding runs — `/data/sources/modules_dogfooding/observations/` and
  `/data/sources/just-dna-lite/docs/MODULE_DOGFOODING.md`. Both runs used the since-removed default
  tier, so re-test their "missing capability" conclusions against today's surface. Their F/D numbers
  are their own series. `modules_dogfooding` is not our repo.
- **Validate a new offline signal against those real corpora**, and say what it reproduced. A signal
  measured only against your own fixture is measured against yourself.
- **The old no-machine-quote rule produced title-as-quote on 3668 of 3668 published rows** in the four
  `antonkulaga/*` modules — one title per PMID, so `quotes_found` reported full coverage while
  witnessing nothing (`S54`). The calibration case for any rule that refuses instead of attributing.
- **Benchmark isolation**: `CLAUDE.md`, the memory index and skills reach a subagent unasked — check an
  isolation clause against all of them, ban **listing** as well as reading, and verify from the
  transcript's `tool_use` blocks, not the self-report. Runbook: `docs/BENCHMARKING.md`.
- **Runs converging on our reference partly measure how prescriptive our skills are.** Find the tool
  output or skill line that produced a good score before crediting the run.
