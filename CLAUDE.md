# Agent Guidelines — just-module-creator

A **Claude Code plugin** shipping two halves: an MCP server that wraps the
just-dna toolchain with agent-shaped tools, and a skill that teaches the
workflow those tools serve. It is an **application, not a published library** —
the contract is the MCP tool surface and the skill, not Python imports, so
internals are free to change and no `__all__` is curated.

It is **not** a format, a schema or an annotation engine. We own no schema:
every column list, vocabulary and requirement comes from the live pydantic
models in `just-dna-format`. It also never executes a VCF — nothing here reads a
sample or calls a genotype.

`AGENTS.md` is a symlink to this file. If the two ever differ, that is a bug —
`ln -sf CLAUDE.md AGENTS.md`.

---

## Read these first, in this order

Obligatory. Read them yourself. **Do not delegate a document you are about to
judge a design against** — a subagent returns a summary, and a summary of a rule
drops the qualifier the decision turned on. Delegation is for finding, never for
deciding.

1. **[docs/DOMAIN.md](docs/DOMAIN.md)** — what a just-dna module is, what the
   four upstream packages guarantee, and the traps that constrain what we may
   build. Every tool here is a promise about one of its rules.
2. **[docs/ROADMAP.md](docs/ROADMAP.md)** — active-only, forward-only. One
   `## RMn — name` section per *open* item.
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — what actually shipped, newest first.
4. **[docs/dogfooding.md](docs/dogfooding.md)** — open findings from using the
   shipped surface for real work. Read before touching the tool surface.

Everything below is self-contained: no rule here requires following a link to
know what you must not do. Links carry positive detail only.

### The agent assets this repo ships

| Path | What |
|---|---|
| `skills/create-module/SKILL.md` | **The canonical copy of the authoring procedure.** Do not restate it here or in `docs/` — restating a procedure beside its skill is how the two drift. |
| `skills/create-module/references/TABLES.md` | Which table kind a finding belongs in. |
| `skills/create-module/references/SYMPTOMS.md` | Upstream message text → cause → action. |
| `skills/create-module/references/CLI.md` | The full CLI surface, and what this server deliberately does **not** wrap. |
| `.claude-plugin/plugin.json` | Claude plugin manifest; declares the MCP server via `${CLAUDE_PLUGIN_ROOT}`. |
| `.claude-plugin/marketplace.json` | Lets `/plugin marketplace add ./` work. |
| `.codex-plugin/plugin.json` | Codex plugin manifest; same skills and server, via `${PLUGIN_ROOT}`. Carries the **second** hand-bumped version string. |

---

## 1. Adopting these guidelines: ask, never infer

**When two rules conflict — this file against a sibling repo's, this file
against the user's global preferences, a rule against what the code actually
does — stop and run a questionnaire.** Do not pick the one that looks better, do
not synthesize a compromise, and do not silently follow the more specific file. A
contradiction between two live rules is almost always a real difference in the
repos' natures, and inferring which nature applies here is exactly the guess that
produces a rule nobody agreed to.

1. **Survey first, ask second.** Read the conflicting rules in full and find out
   *why* each side adopted its version. A question that does not carry the reason
   is unanswerable.
2. **One question per contradiction, batched** — never drip-fed. Two to four
   concrete options each, never an open prompt.
3. **Each option states its cost**: what breaks, what it forces on other repos,
   which existing rule it contradicts.
4. **Recommend one and say so.** A questionnaire with no recommendation offloads
   work the survey already did.
5. **Record the answer where it will be read again** — the rule into its section
   below, the reasoning into §10 in the user's own words. An answered
   contradiction that is not written down gets re-asked, which is worse than a guess.

---

## 2. Non-negotiables

Read the whole list before the first edit. The reason follows each one, because a
rule without its reason gets rationalised away at 2 a.m.

### Environment and packaging

- **Never `uv pip install`.** Use `uv sync` / `uv add` / `uv add --dev`.
  `uv pip install` writes into the venv without touching `pyproject.toml` or the
  lockfile, so the next clean checkout silently lacks the dependency.
- **Never call bare `python` / `python3`.** Always `uv run python …`,
  `uv run pytest …`. A bare interpreter bypasses the workspace environment.
- **Never hardcode a version string.** It comes from `pyproject.toml` via
  `importlib.metadata.version("just-module-creator")`. Two sources of truth drift,
  and the one you read is the wrong one.

  **The unavoidable exceptions are the two plugin manifests** —
  `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`. Both are JSON and
  cannot read `importlib.metadata`, so both `version` fields **must be bumped by hand
  in the same commit as the `pyproject.toml` bump** — a version bump touches **three**
  files here, always. It was two until the Codex manifest landed; a rule that still
  says "two" will leave the Codex one behind. The drift is silent: loading is
  unaffected, so the only symptom is an installed plugin misreporting itself, and
  0.3.0 shipped with a manifest still saying 0.2.0 because of exactly that.
  `tests/test_plugin_manifest.py` fails on either mismatch, which is the guard — do
  not rely on remembering. Keep it at those two and no more:
  `.claude-plugin/marketplace.json` deliberately carries none, and a test pins that
  too.
- **Never rename a user-facing command to dodge a stale `uv run` wrapper.** Bump
  the version and re-run `uv sync` so uv rebuilds the entry points.
- **Never use a placeholder path or a fabricated example value** in committed
  code — `/my/custom/path/`, a dummy digest, `rs999999999`, `1e-328`. Fixtures use
  real identifiers (`rs4988235`, PMID `11788828`). A fabricated value proves
  nothing and outlives the session that invented it.
- **Never commit large data.** No VCF/parquet/gz/BAM/FASTA/`.db`. Anything over
  ~5 MB that must travel goes through Git LFS. A blob committed *before*
  `git lfs track` stays in every past commit even after the pointer replaces it at
  HEAD, so the pack still ships it — surface it, and hand the remediation to the user.
- **Never run tree operations.** No tags, releases, branch management or history
  rewriting except where §10 grants it. **Never `git stash drop` /
  `git stash clear`**, even on explicit request. **Never `git add -A` or
  `git add .`** — it sweeps in `.env` files and editor swap files; stage explicit
  paths.
- **Every git permission is bounded to THIS repository.** A commit, push or tag
  grant covers `/data/sources/just-module-creator` and nothing else — never a
  sibling, a parent or a downstream repo, whatever the state of its tree. Writing a
  file into `../just-dna-format` or `../just-dna-marketplace` is how an upstream
  note gets filed; committing it there is not ours to do, and the note is complete
  the moment it is written. Leaving their working tree dirty is the expected
  outcome, not an unfinished job.

### Code

- **Never write an inline import.** Every import at module top level, absolute.
  The sole exception is a guarded module-level `try/except ImportError` for an
  *optional* dependency — and this repo has none: all four just-dna packages are
  hard dependencies, so every tool works after a bare `uv sync`. See §5.
- **Never nest a `try`/`except` inside another.** It hides the real error. Let
  typed exceptions propagate; wrap only where a genuine recovery path exists.
- **Never `print` for diagnostics.** Stdlib `logging` to **stderr** — under stdio
  the JSON-RPC stream owns stdout, and a log line on stdout corrupts the protocol.
  `print`/`typer.echo` is only for CLI output the user asked to see.
- **Never curate `__all__` or add a re-export `__init__.py`.** This is an
  application; import from where the symbol actually lives.
- **Never open a socket outside `net.py`.** Every outbound request goes through a
  `ServiceGate` there, so pacing, User-Agent and the shared NCBI budget cannot
  drift between clients. This server was socket-free until literature discovery
  landed; that is a normal thing for an app surface to own, but only in one place.
- **Never reach into an upstream private API.** No `EutilsClient._get`, no
  `EuropePmcClient._get`, no reassigning another package's decorator state.
  Everything we need is public — `EutilsSettings.identity_params()`,
  `PacingGate`, `EuropePmcClient.lookup()/.fulltext()`, and the injectable
  `LookupClients`. If something genuinely is not, file it; do not tunnel to it.

### The domain rules this server exists to enforce

Each corresponds to a trap in [docs/DOMAIN.md](docs/DOMAIN.md). Breaking one does
not merely bend a convention — it deletes a class of validation the upstream
design depends on.

- **Never hardcode a schema fact** — no column list, no vocabulary, no
  requirement. Call `describe_table` / `table_requirements` /
  `authoring_reference` and pass through what they return. A hardcoded vocabulary
  is a bug waiting for the next upstream release. The single exception is
  `authoring._SUBJECTS`, which answers "which table?" — a question about *intent*
  that the schema cannot answer — and is commented as such.
- **Never fill a value from the same source that checks it.** A cross-check
  compares an independently authored value against a source; filling it *from*
  that source makes the check compare a convention against itself, and it agrees
  perfectly. Worse, the row moves from honestly unverified to apparently verified.
- **Never let a tool write a checked value from a lookup result.** Lookups report,
  the human decides, the linter checks. Preserve `applied: false` and its
  `refusal` verbatim across the MCP boundary — **the refusal is the feature.**
- **Never extract a passage from a document a tool fetched.** No "best-matching
  passage", no suggested quote, no search-within-text. `enrich_literature` checks
  `provenance_quote` / `provenance_regex` against the Europe PMC fulltext, so a
  quote lifted from that same fulltext makes `quotes_found` confirm itself. The
  sharper reason is that those columns exist to record *that a curator read the
  paper and located the claim* — a machine-located quote asserts a reading that
  never happened, which is a false claim of provenance, not merely a vacuous
  check. Filed as `S11`, and **released in 0.5.4**: `hints.ATTESTATION_BEARING`
  holds exactly these two columns, adopting the argument that a quote is an
  *attestation* rather than a spent comparison, and both are now in
  `REDUNDANCY_BEARING` too because they qualify under that map's own definition.
  `describe_table` reports `attestation_bearing` as a **subset** of
  `redundancy_bearing`, so the sharper reason reaches an agent rather than living
  only here. **A released constant does not make a machine-located quote honest**,
  so say the consequence out loud anyway: once a fulltext has been read through
  `fetch_fulltext`, `quotes_found` on that row is no longer independent evidence —
  it has degraded to a citation-pairing check, which still catches a quote written
  against the wrong PMID.
- **Never collapse "unknown" into a boolean.** Answers are three-valued: true /
  false / **unknown**, and `None` is never `False`. When unknown, withhold — never
  report, never negate. **A check that could not run is not a check that passed**,
  and tool output must keep that visible. Combine with Kleene semantics, not
  withhold-on-any-unknown: `unknown AND false` really is `false`.
- **Never treat a determinism gate as a correctness gate.** `--strict`, a digest
  match, a reproducible build mean *reproducible*, not *right*.
- **Never expose a path to `resolve_with_ensembl=False`.** Despite its name it is
  the master switch for *all* resolution, injected `resolution.csv` included; it
  compiles every row with `chrom=None` and **succeeds**. `compile_module` pins it
  `True` with `ensembl_cache=None`.
- **Never let a module carry two spellings of one sidecar.** `licensing.csv` and `sources.csv`
  are one table with one model; both read, only the preferred one is created, and both present is
  an **error** rather than a merge. Route every write through `layout.sidecar_write_path` (write to
  the file you read) and read `layout.preferred_spelling` / `is_deprecated_spelling` rather than
  restating which is which. The rename stops at the CSV: `sources.parquet` and `manifest.sources`
  keep their names for the whole 0.x tail, so never "finish" it into a published key.
- **Never read `fully_resolved` without `resolution_subjects`, and never coalesce a null counter
  to zero.** Over an empty list the flag is `all()` over nothing. All five RM44/S31/S33 counters
  are `int | None` where `0` is a real answer and `None` means nothing counted — which is what
  every pre-0.6 manifest honestly is.
- **Never place a `*Unavailable` except-arm after its parent.** Since enricher 0.6.2 each is a
  subclass of the type beside it, so parent-first catches every outage in the parent arm and the
  outage arm goes dead — silently, raising nothing. One tuple is safe; two arms must be
  narrow-first. `tests/test_passes.py` walks the AST for this.
- **Never widen the write surface.** Tools write only where the upstream API
  already writes (scaffold, enrich, compile out-dir), always through
  `_shared.resolve_dir` so `JMC_WORKSPACE` containment holds, and never overwrite
  an authored file.
- **Never let a per-call argument loosen the offline ceiling.** `JMC_OFFLINE`
  combines with a per-call `offline` by **OR**, via `_shared.offline_for`. Never
  read the two separately.
- **Never silently fall back when primary data is missing.** Refuse explicitly or
  name the substitute. The caller cannot see that the source differed.
- **Never resolve a contradiction between two rules by inference.** Run §1.

---

## 3. Repository layout, data and assets

```
src/just_module_creator/   source (src layout)
tests/                     pytest suite — in-memory, offline
docs/                      all markdown except this file and README.md
skills/create-module/      the plugin's skill (canonical authoring procedure)
.claude-plugin/            plugin + marketplace manifests
assets/                    fixtures that MUST travel — committed
data/input|interim|output  git-ignored, never travels
scripts/                   operational one-offs, not importable code
```

- `data/` is git-ignored by ignore-all + allowlist. To commit a subtree, add
  explicit `!<dir>/` and `!<dir>/**`.
- Committed test data lives in `assets/`, not `data/`. Tests write to `tmp_path`
  or a resolved cache dir, **never** into the project tree.
- Sibling repos, **read-only** unless the task explicitly targets them:
  `../just-dna-format` (which also hosts the compiler, enricher and their docs),
  `../just-dna-lite`, `../just-dna-registry`.

---

## 4. Build, run, test

```bash
uv sync                                        # install
uv run pytest                                  # the suite; -vvv when diagnosing
uv run ruff check . && uv run pyright          # lint + types
uv run just-module-creator stdio               # run over stdio
uv run just-module-creator http --port 3011    # run over HTTP
uv run just-module-creator stdio --mode extended
uv run fastmcp dev fastmcp.json                # MCP Inspector
claude --plugin-dir .                          # load as a plugin for one session
```

`just <recipe>` wraps all of these. **Always run `uv run pytest` and
`uv run ruff check .` after changing code.** Python **≥ 3.13** — the just-dna
packages require it.

Every CLI that starts a network transport **prints its URL** in the first lines
of output, and every CLI **loads `.env` via `python-dotenv`** (`_load_env`,
`override=False`) before reading configuration — which is what lets one `.env`
serve both this server and the enricher it shells into. New configurable values
are read from env with sensible defaults, documented in `.env.template`, and
mentioned here.

**Timestamps: store ISO-8601 UTC, display local.** Never a naive
`YYYY-MM-DD HH:MM:SS` — it is misparsed as local time and breaks string
comparison against ISO values.

---

## 5. Coding standards

- **Type hints mandatory. `pathlib.Path` for every path** internally. Tool
  *signatures* take `str` because that is the MCP wire type, and convert
  immediately via `_shared.resolve_dir`.
- **Dependency tier: everything is a hard dependency.** All four just-dna
  packages (`format`, `compiler`, `enricher`, `registry`) plus `fastmcp[tasks]`,
  `pydantic`, `pydantic-settings`, `typer`, `anyio`, `python-dotenv`, `httpx`,
  `tenacity`. Chosen so every tool works after a bare `uv sync` and the plugin's
  one-command install stays true; the cost is a heavier install for someone who
  only wants offline linting. There are no extras and no optional imports.
  `httpx` and `tenacity` are **declared** rather than leaned on transitively,
  because `net.py` calls both directly and a transitive pin is not a contract.
- **Do not hand-roll what the enricher already uses.** Retries are `tenacity`
  with upstream's own `net.attempt_floor` stop, so one deployment variable tunes
  our persistence and theirs together. Pacing is upstream's `PacingGate` — not a
  rate-limiter library — because `ServiceGate` must share the *same instance*
  with `EutilsClient` for the NCBI budget to be one budget. `ServiceGate` adds a
  lock and nothing else.
- **We read the ecosystem's env vars; we never forward them.** `settings.py`
  passes nothing through to the enricher — it reads its own configuration from
  the process environment. But when *we* are the one making the call, reading a
  variable the enricher also reads is right, not a leak: `JUST_DNA_CONTACT_EMAIL`
  and `NCBI_API_KEY` reach our clients through `EutilsSettings`, so one `.env`
  configures both surfaces and upstream's precedence is inherited rather than
  copied.
- **The polite-pool contact is a three-step chain, and step 2 stays *inherited*.**
  `JMC_USER_EMAIL` → `JUST_DNA_CONTACT_EMAIL` → `settings.DEFAULT_CONTACT_EMAIL`.
  Ours goes first because the address says *whose* rate-limit budget is being
  spent — NCBI and Unpaywall both meter and contact per address. The middle step
  is not re-implemented: `build_services` passes `email=None` when ours is unset
  and lets `EutilsSettings.__post_init__` do that read, so a change to upstream's
  precedence is followed rather than copied. **Never build the chain by reading
  `JUST_DNA_CONTACT_EMAIL` yourself.**
- **Never fabricate a contact address** — an invented one misattributes the
  traffic to a stranger. `DEFAULT_CONTACT_EMAIL` is not an exception to that: it
  is the project's own address, supplied by its owner, who accepts the traffic.
  What it does cost is *attribution*, and the cost is real — an install that sets
  nothing pools its budget with every other unconfigured install and sends any
  abuse report to the project's inbox rather than the user's. So the default
  exists to stop a source sitting out a call for want of a contact, **not** to
  make configuring one optional: `.env.template` asks for `JMC_USER_EMAIL` in its
  own section, and `build_services` logs which of the three steps answered so
  "project default" is visible rather than silent. Since the default is always
  present, `contact_email()` returns `str`, and any `if not email:` branch is dead
  code — Unpaywall used to be the one source that reported itself unavailable on
  a fresh checkout, and that branch is gone rather than left to rot.
- **Typer for the CLI. Pydantic 2 at every boundary** — every tool returns a
  model from `models.py`, never a bare dict, because an agent reads the field
  descriptions.
- **Constrained vocabularies:** `Mode` is a `Literal` because it is local config
  read from env and never appears in a wire artifact. Anything that *does* reach a
  persisted artifact would need `frozenset[str]` + a validator, so additions stay
  non-breaking — but nothing here does; upstream owns every wire vocabulary.
- **Polars only where upstream hands it to us.** We do not build dataframes; we
  read the parquet upstream wrote.
- **Deterministic ordering is load-bearing** wherever output is compared or
  hashed. Never emit from `set`/`dict` iteration without an explicit sort —
  `sorted(draft.DRAFTABLE)`, `sorted(...checked...)`.
- **Preserve upstream's distinctions.** `error` / `warning` / `info`,
  `applied` / `refusal`, and `None`-means-unchecked are all load-bearing.
  `_shared.to_findings` / `to_alterations` exist to carry them across the boundary
  field-for-field.
- **Aggregate repeated warnings** by *reason*, with a count — never one per row.
- **Heed terminal warnings, deprecations especially.** A deprecation in code you
  touched is a **blocker**: find the current API, fix it, and update this file.
- **Refactor internals aggressively** — no dead code, no API kept for nostalgia.
  The contract is the MCP tool surface, the skill and the CLI; breaking *that* is
  allowed but deliberate and versioned.

### How to add a tool

1. Pick the tier. The line is **cost, not usefulness**: **essentials** =
   everything whose work is bounded by what the caller named — one identifier,
   one paper, one spec directory; **extended** (`JMC_MODE=extended`) = only what
   a *corpus* sizes (a citation graph, a whole-source draft, a pass that rewrites
   every row) or that reads back somebody else's compiled artifact;
   **token-gated** = registry writes.

   **Read-vs-write was the previous rule and it was wrong twice over.** It never
   described the code — `scaffold_module` and `compile_module` both write and were
   always essentials — and it put `lookup_identifier` behind the flag, so the
   default tier could tell you `trait_efo_id` takes an ontology CURIE and then
   give you no way to check one, which is an invitation to write it from memory:
   the exact thing rule 1 of the server instructions forbids. Worst of all,
   `enrich_module` was extended-only while being step 6 of the order those same
   instructions teach. **A tier that teaches a step it cannot run is the failure
   mode to check for**, and
   `tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier`
   now parses the tool names straight out of `server.INSTRUCTIONS` and fails if
   any is missing from essentials. Widened in 0.4.0 (see `docs/ROADMAP_HISTORY.md`).

   **The one exception, and its test.** `registry_register` writes to the registry
   and is *not* gated, because it is what mints the token — gating it would be a
   cycle. So the rule is: a registry write is token-gated **unless the token is its
   output**, and that is a set of exactly one. It lives in `auth.py` beside
   `authenticate` rather than in `tools/registry.py`, and it is registered in every
   mode, not extended-only: hiding the only route to a credential behind a mode
   flag reproduces the dead end it exists to remove (`F12`). If a second such tool
   ever appears, that is the moment to ask whether "ungated onboarding" is a tier
   rather than an exception — do not grow the exception silently.

   There is no third mode, and tags are not the escape hatch: `mcp.enable()` is
   server-global (see 7 below) and FastMCP 3.4.7 deprecated `include_tags` /
   `exclude_tags` in its favour. Splitting extended would need a second `Mode`
   member and a second `register_*`, and should wait for evidence that it is needed.
2. Add it inside the matching `register_*` with type hints, a docstring (it
   becomes the description) and `ToolAnnotations`.
3. Return a model from `models.py`.
4. Paths through `resolve_dir`; network through `offline_for` and
   `anyio.to_thread.run_sync`.
5. Gated tools take `ctx: Context`, call `require_key`, return
   `unauthenticated_result(settings)` on `None`, are tagged `registry_write`, and
   are listed in `auth.GATED_TOOLS`.
6. Add a test using the in-memory client.
7. **Never** use `mcp.enable()`/`disable()` to gate per-user on multi-tenant
   HTTP — it is server-global and would leak tools across clients.

---

## 6. Testing — layer 1

- **Real data + ground truth.** Real rsIDs and PMIDs; compute expected values from
  the fixture rather than pasting a count read off a dump. Hardcoding a documented
  constant is fine; hardcoding a row count is not.
- **Meaningful assertions** — relationships and set equality over `len(df) > 0`.
- **Never mock the transformation under test.** We test our wrapper against the
  real upstream packages; only the *network* is excluded, by the offline ceiling.
- **The suite is hermetic by mechanism, not by discipline.** `conftest`'s autouse
  `_hermetic_configuration` points `env_file` at a path that cannot exist and clears
  the ecosystem's variables from `os.environ`, so **forgetting `_env_file=None` is
  harmless** rather than silently live. `offline_settings()` still forces
  `offline=True` and is what fixtures use. Do not undo this by removing
  `env_file=".env"` from `model_config` — the product needs it, and breaking the
  product to protect the suite is the wrong trade.

  It was a convention until 2026-08-12 and that failed exactly as predicted (`F24`):
  a bare `Settings()` returned the developer's real polygon token **and**
  `offline=False`, so a test could reach the network holding a live credential, while
  passing locally and in CI. **The clear-list is derived from `Settings.model_fields`,
  never written** — the hand-written first draft missed seven variables inside the same
  change, `JMC_API_KEY_HEADER` and `JMC_TRANSPORT` among them, and an exported one of
  those changes what a test asserts as effectively as a token does. Only the four
  upstream names are hand-maintained, because no field of ours can name them.
- **A test that means "no credential" must say so.** `api_key=None` is
  indistinguishable from "not passed" when the reader does
  `api_key or os.environ.get(...)`. Neutralize with `setenv(VAR, "")`, **not**
  `delenv` — `load_dotenv(override=False)` skips a key that is merely present. (The
  autouse fixture above uses `delenv`, which is not an exception: nothing in the suite
  calls `load_dotenv`, and with the dotenv source neutralized pydantic reads
  `os.environ` directly, where absent means unset. Inside a *test*, prefer
  `setenv(VAR, "")` — it runs after the fixture and wins.)
- **Suspect ordering whenever a test passes alone and fails in the suite.**
- **Never claim a test "would have caught" a bug** without running it against the
  buggy code and watching it fail.
- Note `from conftest import ...`, not `from tests.conftest import ...`: a
  transitive dependency ships a `tests` package that shadows ours.

---

## 7. Dogfooding — layer 2

Tests prove the code does what it was told. Dogfooding asks whether it is
**usable, and what is missing**. Both are required.

**Do not verify the tool's answers with a second implementation while
dogfooding** — that is a test and belongs in the suite. Use the tool, notice the
friction, write down what was not there.

- **A capability the tool LACKS is the result, not an obstacle to route around.**
  The moment you reach for an ad-hoc script or a raw HTTP call to get past
  something the product cannot do, the exercise has stopped producing signal.
  Record the gap; if it blocks the work, build it into the product.
- **Attack claims, not gaps.** A documented deferral is a decision. What counts is
  where a docstring or doc *promises* something the code does not do.
- **Use real data.** No `rs999999999`, no `1e-328`.
- **Pick the probe where the design generalized from one case** — if the example
  shows one of something, use a real case with two.
- **Dogfood a finding before you report it.** Build a real example against the
  actual code path and show it fails.
- **Finish each probe as a committed reference example whose README names what it
  broke**, demonstrating the failure on the *old* behaviour.
- **Separate "fix it" from "surface it" before writing code**, and say *why each
  candidate repair is wrong* for the surfaced ones.

Findings carry stable `F#` IDs and **move** between files, never duplicated —
except one mitigated here but still owed upstream, which legitimately appears in
two: `docs/dogfooding.md` (open) → `docs/previous_issues.md` (resolved here) /
`docs/just-dna-format-pending-fixes.md` (blocked upstream).

---

## 8. Docs and their lifecycle

- **All new markdown goes in `docs/`** — the only exceptions are this file and
  `README.md`. `docs/` is the single ground truth; this file duplicates only what
  is needed to *orient*, and every prohibition lives here in full because a
  `don't` behind a link does not get read.
- **`docs/ROADMAP.md` is active-only.** Shipped items move to
  `docs/ROADMAP_HISTORY.md` with their rationale. Nothing is deleted, only relocated.
- **`docs/CHANGELOG.md` records what shipped**, newest first, including cross-repo
  integration changes made on our side.
- **Update this file and the affected `docs/` in the same change as the
  refactor**, not after. Policy is written first; code complies.
- **Keep the skill and the tool docstrings in agreement.** If a tool changes what
  it refuses to do, the skill's claim about that refusal changes with it.
- **Run the commands yourself** rather than telling the user to run them — except
  where a command genuinely needs an interactive terminal, which is when you hand
  over a verbatim line.
- **Before a PR**, print `git diff <upstream>/main --stat HEAD` and
  `git log <upstream>/main..HEAD --oneline`, show the output, and wait for approval.

### Upstream findings go to the producer, never into a workaround

We consume `just-dna-format` / `-compiler` / `-enricher` / `-registry` and own
none of them. **There are two intakes, and a note belongs wherever the fix would
land:**

| The fix would land in | File the `S<n>` in |
|---|---|
| format, compiler, enricher (one repo) | `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md` |
| the registry service, its client, or a `just-dna-pipelines` command calling it | `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md` |

**`../just-dna-marketplace` is a stale *directory* name and nothing more.** The
project, the package and the service are all `just-dna-registry`; only the path on
disk kept the old word. Do not call it "the marketplace" in prose — say the
registry, and refer to the path only when a path is what you mean.

Its `S<n>` numbering is a separate series from the format tree's; both start at
`S1`. If a note is in the wrong file it may as well not be filed, so decide by
asking who would change code, not which surface you noticed it through.

#### The format tree's intake is split, and the inbox is the empty half

`../just-dna-format/docs/CONSUMER_SUGGESTIONS.md` holds **only what is still
unanswered**. The moment upstream writes a `**Status —**` reply, the whole entry
moves — prose byte-for-byte — to
**`../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md`**, whose index table
gives every `S<n>`, who reported it, the verdict and where it landed. So:

- **An empty inbox means nothing is owed, not that our notes were lost.** As of
  2026-08-11 every `S<n>` we have filed there is answered, `S1`–`S24`. A note of
  ours that is no longer in `CONSUMER_SUGGESTIONS.md` has been answered — read the
  history file's index before concluding anything else.
- **Never number a new `S<n>` from what the inbox shows.** An empty inbox says
  nothing about which ids are taken, and ids are never reused — not even for an
  item answered as a non-issue, because the reply is part of the record. Compute it:
  `.claude/triage-state.sh --next` in their repo scans the inbox *and* the history
  file. The inbox states the next id in its own heading too (**`S27`** in the format
  tree and **`S8`** in the registry's, as of 2026-08-12 — and those move within
  hours, so run the script: both moved by two on 2026-08-12 alone). Their `CONSUMER_TRIAGE_LOOP.md` is the producer-side
  runbook and not ours to drive.
- **"Answered" is not "fixed", and "fixed" is not "released".** Three distinct
  states, and only the third lets a guard come out:
  1. *accepted and filed* — a reply exists and the work is an upstream `RMn`, still
     open. Check `RM_TOC.md`, not the history file, for that half.
  2. *fixed in tree* — the symbol exists in `../just-dna-format` but the version we
     install does not have it. **This is the common case and the easy mistake.**
  3. *released* — on PyPI and in our lockfile.
- **Verify state 2 against the installed package, never the sibling checkout.**
  Import the symbol and check, e.g. `hasattr(hints, "ATTESTATION_BEARING")`. A
  mitigation of ours stays until the release that carries the fix is what
  `uv sync` gives us, and dropping one because the upstream tree looks fixed
  breaks the plugin for everyone who installs from PyPI.
- **A refusal is an answer too, and it is load-bearing.** Upstream refused half of
  `S14` with a reason: the compiler has **no** network branch, so a `--no-ensembl`
  flag would assert something false. That makes our pin permanent rather than
  interim, and "closes when upstream renames the flag" was never going to happen.
  Record a refusal as settled, not as pending.

- **A gap in the docs is a finding too.** If you had to *probe* to learn something —
  run an experiment, read their source, test a guess — that is a doc bug, and it
  gets filed with the same urgency as a behavioural one. The next consumer will
  otherwise run the same experiment. Say how you found it: "we put a `source`
  column on `pharm_variants.csv` and got `Extra inputs are not permitted`" argues
  for a fix better than "this is undocumented" does.
- **File it the moment you find it. Do not batch.** Found it → write the `S<n>`
  entry → carry on with what you were doing. Not after the guard is built, not
  after the task closes, not as a tidy set of "field notes" at the end of a work
  item. Upstream ships fast, and a note that arrives after the release window has
  closed buys nothing: `S14` (the `resolve_with_ensembl=False` footgun) was found
  while building the wrapper, guarded against, written up in our README as a
  *feature*, and filed days later — **0.5.3 shipped in between, and the fix could
  have been in it.** The delay is the whole cost. A rough note filed today beats a
  polished one filed next week.
- **A guard is not a substitute for the note, and never a selling point.** Pinning
  a flag protects our callers and nobody else's; the defect is still there for the
  next consumer. If you catch yourself describing a workaround in `README.md` as
  something this plugin does *for* you, the note was skipped. See §8's prose rule.
- **Check whether it is already filed first.** Entries are `S<n>`; a second
  consumer hitting a known one appends a corroboration to that entry rather than
  opening a new number. Two independent reproductions is itself the signal that
  raises its priority.
- **Write the note, and stop there.** **Never commit in that repo**, and never
  open a PR against it. Writing the note is the whole job.
- **Track our side too**: `docs/just-dna-format-pending-fixes.md` as an `F<n>` while
  it is open upstream, and `docs/CHANGELOG.md` if we shipped a mitigation, so
  nobody re-investigates a finding that looks fixed.
- **Re-read the upstream verdicts before trusting our own `Status:` lines.** Ours
  go stale silently — upstream answers in its own tree and nothing notifies us. On
  2026-08-11 every entry in `docs/just-dna-format-pending-fixes.md` said "open
  upstream" while all eight had in fact been answered, six of them fixed in tree.
  The status line has to name the upstream state *and* whether the fix is in the
  version we install; "open upstream" says neither.
- **Never work around it silently in the data.** A workaround that leaves a module
  dishonest is worse than the gap. Say what the limitation is, leave the data
  truthful, file the note.

### Prose style

Natural, human prose. Avoid AI tells — em-dash pile-ups, filler transitions,
marketing voice. Never hallucinate documentation or overpromise an unimplemented
feature. **`README.md` says what this plugin does, and never doubles as a
catalogue of upstream defects we guard against** — that belongs in the upstream
note, in §2's prohibitions, and in `docs/just-dna-format-pending-fixes.md`.
Telling an *author* "never pass this flag" in the skill or `references/CLI.md` is
different and correct: they may drive the CLI directly and need to know. **This project must never be described as interpreting a genome, calling
a genotype, or giving medical advice**: it helps author annotation tables, and the
consumer supplies the measurement.

---

## 9. Self-correction

When outdated API knowledge causes a real crash or logic failure, fix the code
**and** update this file (and the affected `docs/`) with the correct pattern, so
the next agent does not repeat it. The same applies when the user corrects a
preference: it goes into §10, in their words, with the reason.

## 10. Learned user preferences

*Append-only. One line each, in the user's terms, with the why where it is not obvious.*

- **"auto-commit grant lingers... you commit and tag as you go."** Granted
  2026-08-11 and it does **not** expire at the end of a feature: commit and tag
  without asking. Meaningfully sized commits rather than atomized ones, explicit
  paths — never `git add -A` — and tags at a version bump, matching the
  `pyproject.toml` version.
- **"Your commit permit is bounded by this repo only, no commits to
  siblings/parents/downstream."** Granted 2026-08-11. Writing an upstream note is
  the whole job; committing it there never is.
- **Pushing is never persistent.** "push — in this session only." A push grant
  covers the session it was given in and nothing after it, so a later session
  starts from *ask first* again no matter what the tree looks like. Releases and
  branch management stay the user's throughout.
- **"I need to have mvp, then pace declines."** Get a working end-to-end thing
  first and refine after; do not gold-plate the early steps of a long build.
- **"the fix could have been in 0.5.3 already if it were in the right place.
  Update your memory to fill in these immediately upon finding, without delaying
  and writing field notes like this."** Upstream notes are filed at the moment of
  discovery, never batched. See §8.
- **"Why is this in our readme instead of upstream's consumer_suggestions? Cleanout
  readme from parent lib issues, wtf really."** The README describes what this
  plugin does; a guard against an upstream defect is not a feature to sell.
- **Never destroy stashes**, even on explicit request. Data loss is the user's to
  enact.
- **Never blind-stage** (`git add -A` / `git add .`) — it once committed a `.env`
  swap file with live tokens.
- **Do not restate schema lists in prose; ask the tool.** Confirmed when the two
  authoring takes disagreed: "create-module preference on lists is proper; they
  may drift."
- **This is a *new*-module creator — do not carry historical baggage.** 0.4-era
  quirks never went to production, so a module author has no use for them.
- **The two authoring write-ups were independent takes made to reveal different
  surfaces**, not drafts of one another — so they were unified rather than one
  chosen over the other.
- **"For non-skilled users, publish to polygon explicitly, unless they explicitly
  ask for 'official catalog' or alike. This confuses the crowd and we don't want
  half-baked test modules on prod, given its immutable registry."** Decided
  2026-08-11 after an assisted session where a novice's "send it to your site"
  plainly meant *somewhere my friends can see it* and not *the immutable catalog*.
  The rule is a rule about the **conversation**, not the argument — `target`
  already defaults to `test`, so the exposure is an agent volunteering
  `target="prod"` to be helpful. It lives in `skills/create-module/SKILL.md` §7 and
  in `server.INSTRUCTIONS`, and it carries a corollary: prefix the **module** name
  as well as the namespace on a first rehearsal, because `purge-test-data` matches
  both halves and a first-timer will not come back to delete litter.
- **"If you find the module is genuinely good and is underrepresented in official
  catalog — suggest yourself."** Added 2026-08-11, immediately after the rule above
  and as its deliberate counterweight: the polygon default is against *assuming*,
  not against advocating, and a good module nobody publishes helps nobody. Written
  against **checks rather than impressions**, because an agent asked whether its own
  work is good will say yes — a prod `registry_search` showing the gap, plus strict
  validate and compile, produced-not-authored resolution, every PMID from a search
  result whose title was read, a declared licence, nothing guessed, and a rehearsal
  read back. `assets/fto_bmi` is the calibration case *against*: it cleared all of
  that and `registry_search(gene="FTO")` returned `total: 0`, and one locus with no
  licence and no readme was still not worth an immutable `1.0.0`. **Underrepresented
  is necessary and nowhere near sufficient** — a stub occupies the search result a
  real module would have had.

## 11. Learned workspace facts

*Append-only. Environment, ports, credential layout, host quirks, sibling paths.*

- Sibling repos live beside this one under `/data/sources/`:
  `../just-dna-format` (hosts format, compiler and enricher, their
  `CONSUMER_SUGGESTIONS.md` intake and its answered half,
  `docs/CONSUMER_SUGGESTIONS_HISTORY.md`), `../just-dna-lite`, and the registry at
  **`../just-dna-marketplace`** — a **stale directory name only**. The project,
  package and service are `just-dna-registry`; "marketplace" is the old word,
  retained on the path and nowhere else. There is no `../just-dna-registry`
  directory, which is a path quirk and not a rename.
- The registry keeps its own intake at
  `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md`, created 2026-08-11.
- **`just-dna-registry` moves fast: 0.9.1 → 0.12.0 → 0.13.0 → 0.14.0 in two days.**
  0.14.0 is on PyPI, is what `uv sync` installs, and is our floor. **That floor is
  load-bearing rather than hygiene**: 0.14.0 is the release that projects a
  spec-directory `README.md` onto the module card, so below it every module we publish
  has a blank catalog card (`F33`). **Re-check with
  `importlib.metadata.version("just-dna-registry")` rather than trusting this
  line** — it has gone stale within hours three times.
- **Their release notes carry a `Client surface:` line, and it is trustworthy.** Their
  answer to our `S2`. Read that one line instead of the whole release to establish that
  the client methods we call did not move — 0.13.0 and 0.14.0 both say *unchanged*, and
  0.14.0's was verified upstream with `git log -S` over our eight. The **additions**
  still have to be read: 0.14.0's four all mattered to us.
- **Reading a registry upgrade got cheaper in 0.13.0** (their `S2` = our `F15`).
  Every release entry now opens with a `Client surface:` line — 0.13.0's says
  *unchanged*, checked with `git log -S` over the eight `RegistryClient` methods we
  call — and both reference docs are stamped with the versions they are normative
  for. **What is still missing is the enumeration itself**, which needs a contract
  version of its own; it exists machine-checked as `_WRAPPED_ROUTES` in their
  `tests/test_client_sdk.py` but is not published. Upstream says
  `research.py::_module_card`'s defensive projection is safe to delete against a
  0.13 server; **we keep it anyway**, for the narrower reason recorded in `F15` —
  `get_module` is not one of the six methods `assert_compatible` guards, so an
  older *server* answers it unchecked.
- **The registry is TWO instances and they share no database.** Production is the
  catalog everyone installs from; the polygon (`REGISTRY_MODE=test`) is where a
  publish is a rehearsal. An account, a token and a namespace exist on one of them
  only, so registering on one gives you nothing on the other. **Both are serving
  0.13.0 and both report their mode**, so a target is now *verified* rather than
  merely declared: `targets.client_for` passes `expect_mode=target` on every client,
  and a publish aimed at the polygon that would land on production refuses. The
  polygon is up — it was DNS'd but answering a bare Caddy 404 earlier the same day.
  See `targets.py`; the write tools default to the polygon and the catalog reads to
  production, because a forgotten `target` costs nothing on one and is
  irreversible on the other.
- **We hold a POLYGON credential and no production one, as of 2026-08-12.**
  `JMC_TEST_API_KEY` is set in `.env` and `registry_whoami(target="test")` answers
  **account `sheep`, namespace `test-sheep`** — so a polygon rehearsal needs no
  `registry_register` and no namespace claim. Production is still empty: the
  `test-creator` account and its `test-modules` namespace are **gone from
  production**, which now refuses `test-`prefixed data outright, and `JMC_API_KEY`
  was cleared from `.env` rather than left stale — a dead token makes every registry
  tool report *"the registry rejected your token"*, which sends an author to debug
  auth instead of to register. `JMC_INSTALL_ID` is still there deliberately: it is a
  proof-of-work string rather than an instance credential, it exists nowhere else,
  and destroying it is the user's call, not ours.
- As of 2026-08-11 production holds one module, `eric-mods/lactose_tolerance@1.0.0`
  — still the best available worked example of a real spec, and now the only thing
  a catalog read will find.
- The enricher's Ensembl cache lands in
  `~/.cache/just-dna-pipelines/ensembl_variations`. The live V2 GraphQL endpoint
  currently 404s and the client falls back to REST — expected, not a defect.
- A transitive dependency ships a top-level `tests` package that shadows this
  repo's, so test helpers import as `from conftest import ...`.
- **Format 0.6.1 / compiler 0.6.1 / enricher 0.6.3 / registry 0.18.1 — adopted 2026-08-19 (our
  0.10.1).** 0.6 is the line where the format-tier three stop moving in lockstep: format and compiler
  sit at 0.6.1 while the enricher takes patches alone (0.6.2 for RM101's exception contract, 0.6.3 for
  the ClinVar and ClinPGx drafter fixes). Verify by symbol, never by this line:
  `just_dna_format.layout`, `compiler.ARTIFACT_PARQUETS`, `compiler.close_module`,
  `frequencies.FrequencyUnavailable`, and for 0.6.3 the `(chrom, start, ref, alt)` event key inside
  `clinvar_draft.multi_allelic_rsids`.
- **Both live registry instances now serve `format: 0.6.1` / `registry: 0.18.1`, verified 2026-08-19,
  and the 0.5.4 contract block is over.** Every version-guarded call works again — a `download` of
  `eric-mods/lactose_tolerance@1.0.0` returns its manifest where it 409'd a day earlier, and
  `assert_compatible()` passes on prod and polygon alike. `targets.instance_note` stays: it is a
  suffix on an existing `except RegistryError` arm, costs nothing while the contract agrees, and is
  there if an instance is rolled back. **Re-probe with `curl -s <url>/api/v1/version`, never assume** —
  this line has now been wrong in both directions within two days. Note the catalog's one module is
  still stamped `just-dna-compiler 0.5.1`; that is the contract gap registry 0.18.0's `upgrade`
  detects, and an operator's sweep rather than an author's problem.
- **A drafter fix does not reach a module already drafted, and the two drafters need opposite
  repairs.** Enricher 0.6.3's ClinVar fix (S41) moved identities, so re-drafting over an existing
  spec restores the lost records and leaves the collapsed ones — measured 0 missing, 31 stale on
  MLH1, and nothing in the file tells them apart. Draft into a fresh directory and reconcile. Its
  ClinPGx fix (S44) only *skipped* rows, so a plain re-run converges exactly (0 stale, 0 missing).
  Ours is `F36`, filed upstream as `S45`.
- **The format tree's triage script is `.claude/triage-state.py`**, not the `.sh` older notes name.
- **An upstream *library* call loads your `.env`.** `just_dna_enricher.locations` calls `load_dotenv`
  while resolving a cache path, so `build_server` repopulates `os.environ` from whatever `.env` is
  above the cwd. `load_dotenv(override=False)` skips a key that is *present*, so clearing a variable
  with `delenv` is what lets the file win — which is how the suite quietly stopped being hermetic.
  `F35` / format-tree `S39`; the fixture neutralizes the loader by walking `sys.modules`.
- **0.5.4 and registry 0.13.0 both released 2026-08-11, and we installed both** (superseded above).
  `uv sync` gives format/compiler/enricher **0.5.4** and `just-dna-registry`
  **0.13.0**; the floors in `pyproject.toml` say so. Adopted in our 0.7.0, which
  retired six mitigations at once — `S11`, `S12`, `S15`, `S16`, `S17`, `S18`, plus
  `S20`/`S21`/`S23`/`S24` and the registry's `S1`/`S3`. **Re-verify by symbol, never
  by this line or a changelog**: `hints.ATTESTATION_BEARING`, `hints._report_ragged`,
  `Finding.line`, `CitationHint.title`, `IdentifierReport.gene_loci`,
  `RegistryClient(expect_mode=…)`. `hints.py` lives in the **compiler**, not the
  enricher, which is easy to get wrong when grepping; `SourceRow` lives in
  `just_dna_format.sources`, not `.spec`.
- **Three mitigations are kept on purpose and are not oversights**: `ServiceGate`'s
  lock (upstream fixed `PacingGate` *because* callers share one), `compile_module`'s
  `resolve_with_ensembl=True` pin (`S14`'s rename was **refused** with a reason, so
  the pin is permanent), and `_module_card`'s defensive projection (`get_module` is
  not one of the six methods `assert_compatible` guards, so an older *server* can
  still answer it unchecked — our floor pins the client, not the host).
- **The registry's intake adopted the same split as the format tree on 2026-08-11**:
  it now has `CONSUMER_SUGGESTIONS_HISTORY.md`, a `CONSUMER_TRIAGE_LOOP.md` runbook
  and a `.claude/triage-state.sh --next`. Read both intakes the same way — and its
  history file is now populated, so the earlier advice to read `**Status —**`
  paragraphs in its inbox no longer applies.
- Ours there: `S1` (the `would_publish` ceiling = `F11`), `S2` (no enumerated
  client-surface contract = `F15`) and `S3` (no endpoint reports an instance's mode
  = `F16`) — **all three answered and released in 0.13.0**, except `S2`'s enumerated
  contract, which is open on their roadmap because it needs a contract version of
  its own. `S5`–`S7` (the readme) — **released in 0.14.0**. `S8` (they attribute
  `write_module_md` to us) and `S9` (`amend_readme` is on their client but not their
  CLI) — filed 2026-08-12, open.
- **Never read a next-`S<n>` off a line like this one; run
  `.claude/triage-state.sh --next` in the repo you are filing into.** The proof is in
  this file's own history: it said `S25`/`S5` on 2026-08-11, `S27`/`S8` hours later,
  and both were wrong again by the next session (`S29`/`S10`). A number written down
  here is stale by construction, because either seat may file between sessions.
- **Read `docs/` before filing, not just the inbox.** On 2026-08-12 two of our own
  sessions filed the same readme defect hours apart (`F27` = registry `S5`, then
  `S7`), and the second was closed as a duplicate. The duplicate check is cheap and
  neither session ran it.
- **"The goal of this plugin is to be ai-coauthor. And it can be driven by a lyman."** Stated
  2026-08-12. The module owner brings the *theme* and the *sources* — a trait, some PDFs, a video.
  Everything after that is the agent's: triage, rows, conclusions, located passages. **"Here you
  kinda ask v2 work from a wrong person"** — the worked case was asking a gardener, who cannot read
  a genetics paper, to supply `provenance_quote` and to judge whether the module was good enough to
  publish. Both are a reviewer's job and a different person's. **"AI totaly can read articles."**
- **Versions and curation carry NO implicit contract.** Corrected 2026-08-12 after the skill turned
  an illustration into a ladder: *"1.0.0 2.0.0 arent strict milestones, it was an example, we don't
  have any implicit contracts on versioning or order of curation."* The real rule is a signal read
  off the module, never a schedule: *"if module is v25 - likely it's worked on iteratively, slightly
  more trust; module has non-ai curators - that's a silver one already, human labor costs. v52 and
  2+ curator med_geneticists? That's platinum."* So `2.0.0` does not mean reviewed, a human may
  curate from the first version or never, and **no agent may withhold a publish or a bump waiting
  for a milestone that does not exist**. Curated work is then cherry-picked into a featured catalog
  section by the operator. `authorship` is where the signal actually lives, which is why it is now
  documented in `skills/create-module/SKILL.md` rather than left to the schema.
