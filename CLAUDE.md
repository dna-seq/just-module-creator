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
| `.claude-plugin/plugin.json` | Plugin manifest; declares the MCP server via `${CLAUDE_PLUGIN_ROOT}`. |
| `.claude-plugin/marketplace.json` | Lets `/plugin marketplace add ./` work. |

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
  check. The installed `hints.REDUNDANCY_BEARING` omits both columns. That was
  filed as `S11` and is **accepted and fixed in tree** — upstream added
  `hints.ATTESTATION_BEARING` for exactly these two, adopting the argument that a
  quote is an *attestation* rather than a spent comparison — but the fix is in the
  unreleased 0.5.4, so it is absent from what `uv sync` installs and the refusal
  stays ours to keep until then. Say the consequence out loud:
  once a fulltext has been read through `fetch_fulltext`, `quotes_found` on that
  row is no longer independent evidence — it has degraded to a citation-pairing
  check, which still catches a quote written against the wrong PMID.
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
  copied. Never fabricate a contact address — an invented one misattributes the
  traffic to someone.
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

1. Pick the tier. The line is **what the tool does, not how useful it is**:
   **essentials** = everything that only *reads*, plus the ClinVar draft;
   **extended** (`JMC_MODE=extended`) = everything that writes into a spec
   directory or fetches at scale; **token-gated** = registry writes. Stated this
   way because "the loop you need on every module" stopped discriminating once
   drafting — step 2 of the taught workflow — became a tool.

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
- **The suite is hermetic**: every fixture forces `offline=True` and
  `_env_file=None`, so no test can reach the network or read a developer's `.env`.
- **A test that means "no credential" must say so.** `api_key=None` is
  indistinguishable from "not passed" when the reader does
  `api_key or os.environ.get(...)`. Neutralize with `setenv(VAR, "")`, **not**
  `delenv` — `load_dotenv(override=False)` skips a key that is merely present.
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
  2026-08-11 it reads "Nothing open: S1–S18 are all answered". A note of ours that
  is no longer in `CONSUMER_SUGGESTIONS.md` has been answered — read the history
  file's index before concluding anything else.
- **Never number a new `S<n>` from what the inbox shows.** An empty inbox says
  nothing about which ids are taken, and ids are never reused — not even for an
  item answered as a non-issue, because the reply is part of the record. Compute it:
  `.claude/triage-state.sh --next` in their repo scans the inbox *and* the history
  file. The inbox states the next id in its own heading too ("The next item is
  S19", as of 2026-08-11). Their `CONSUMER_TRIAGE_LOOP.md` is the producer-side
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
- As of 2026-08-11 that repo declares `just-dna-registry` **0.11.3**, which is
  **not on PyPI** (published: 0.9.1). Adopting it would need a local path
  dependency, which breaks the plugin's one-command install for anyone else, so we
  stay on the published version until it ships.
- The published registry is `https://module-registry.just-dna.life`; as of
  2026-08-11 it holds exactly one module, `eric-mods/lactose_tolerance@1.0.0`,
  which is the best available worked example of a real spec.
- The enricher's Ensembl cache lands in
  `~/.cache/just-dna-pipelines/ensembl_variations`. The live V2 GraphQL endpoint
  currently 404s and the client falls back to REST — expected, not a defect.
- A transitive dependency ships a top-level `tests` package that shadows this
  repo's, so test helpers import as `from conftest import ...`.
- **Upstream's 0.5.4 is written but unreleased, and six of our findings are fixed
  only in it.** Checked 2026-08-11: PyPI's newest is compiler/enricher **0.5.3**
  and `just-dna-format` **0.5.0**, which is what we install, while the
  `../just-dna-format` working tree still declares 0.5.3 and carries the 0.5.4
  work. Verified by symbol rather than by changelog — `hints.ATTESTATION_BEARING`,
  `hints._report_ragged` and `Finding.line` are all present in
  `../just-dna-format/compiler/src/just_dna_compiler/hints.py` and all absent from
  the installed `just_dna_compiler.hints`. So every mitigation for `S11`, `S12`,
  `S15`, `S16`, `S17`, `S18` stays until 0.5.4 is on PyPI. `hints.py` lives in the
  **compiler**, not the enricher, which is easy to get wrong when grepping.
- The registry's own intake has **no history file** and, as of 2026-08-11, one
  unanswered entry (`S1`, the `would_publish` variant ceiling = our `F11`). The two
  intakes therefore behave differently: absence from the format tree's inbox means
  answered, absence there would mean nothing of the sort.
