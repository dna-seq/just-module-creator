# AGENTS.md

Guidance for coding agents (Claude Code, Cursor, Codex, Antigravity, …) working
in this repository. Humans: see `README.md`.

**Read [CLAUDE.md](./CLAUDE.md) first.** It is the domain briefing — what a
just-dna module is, what the four packages we wrap guarantee, and the traps that
constrain what we may build. Every tool here is a promise about one of those
rules. This file covers the code: commands, layout, conventions.

## What this is

A **Claude Code plugin** shipping two halves:

* an MCP server (`src/just_module_creator/`) that wraps the just-dna toolchain
  with structured, agent-shaped tools, and
* a skill (`skills/create-module/`) that teaches the workflow those tools serve.

We own no schema. Everything a tool reports about columns, vocabularies or
requirements is generated from the live pydantic models in `just-dna-format`.

## Commands (prefer these)

```bash
uv sync                                    # install deps (incl. dev)
uv run pytest                              # tests (fast, in-memory, offline)
uv run ruff check .                        # lint
uv run ruff format .                       # format
uv run pyright                             # type-check
uv run just-module-creator stdio           # run over stdio
uv run just-module-creator http --port 3011  # run over HTTP
uv run just-module-creator stdio --mode extended
uv run fastmcp dev fastmcp.json            # MCP Inspector (interactive)
claude --plugin-dir .                      # load as a plugin for one session
```

`just <recipe>` wraps all of the above if `just` is installed.

**Always run `uv run pytest` and `uv run ruff check .` after changing code.**

Python **≥ 3.13** — the just-dna packages require it.

## Architecture (read before editing)

- `server.py` — `build_server(mode, settings)` wires everything; module-level
  `mcp` is the instance `fastmcp` discovers. Typer CLI + graceful shutdown too.
- `settings.py` — `pydantic-settings`; all fields default, so the server **never**
  requires env at boot. `JMC_` prefix.
- `auth.py` — per-session, per-request registry-token resolution.
- `models.py` — trimmed Pydantic views of upstream results (see its docstring for
  why they are not the upstream models).
- `tools/_shared.py` — path containment, the offline ceiling, and the converters
  that carry `level` / `applied` / `refusal` across the MCP boundary intact.
- `tools/authoring.py` — essentials: the offline authoring loop.
- `tools/research.py` — essentials: read-only network lookups, no token.
- `tools/advanced.py` — extended-only: enrichment, integrity, round-trip.
- `tools/registry.py` — token-gated registry writes.
- `tests/` — in-memory `Client(transport=build_server(...))`, always offline.

## The three gating axes

1. **Mode (essentials vs extended)** — controls which tools *exist*.
   - Essentials (`authoring.py`, `research.py`) register in **every** mode.
   - Extended (`advanced.py`) registers only when `mode == "extended"`
     (`JMC_MODE` or `--mode`).
   - Why: a smaller default tool list = less context pollution for the agent.
2. **Auth (per session)** — controls whether registry writes *work*.
   - Gated tools (`registry.py`, tag `registry_write`) are always listed but
     enforce a token **per call** via `require_key`.
   - Precedence: `X-Registry-Token` header → per-session store (set by
     `authenticate`) → `JMC_API_KEY` → `REGISTRY_TOKEN`.
   - No token? A friendly `OpResult(success=False)`, never a raise.
   - **Never** store a token in server-global state, and **never** use
     `mcp.enable()`/`disable()` to gate per-user on multi-tenant HTTP — it is
     server-global and would leak tools across clients. (A documented
     single-tenant stdio-only variant lives in `auth.py`.)
3. **Offline (`JMC_OFFLINE`)** — a **ceiling**, not a default. It combines with a
   per-call `offline` argument by OR, so an argument can tighten it and never
   loosen it. Use `_shared.offline_for`; never read `settings.offline` and the
   argument separately.

`JMC_WORKSPACE` is the fourth safety property: write containment for the HTTP
transport. Every path argument goes through `_shared.resolve_dir`.

## How to add a tool

1. Pick the tier: essentials (always), extended (opt-in), or token-gated.
2. Add a function inside the matching `register_*` function with type hints, a
   docstring (it becomes the description) and `ToolAnnotations`
   (`readOnlyHint` / `idempotentHint` / `destructiveHint` / `openWorldHint`).
3. Return a Pydantic model from `models.py`. Add one rather than returning a
   bare dict — an agent reads the field descriptions.
4. Any path argument goes through `resolve_dir`. Any network call goes through
   `offline_for` and runs in `anyio.to_thread.run_sync`.
5. Token-gated tools take `ctx: Context`, call `require_key(...)`, and return
   `unauthenticated_result(settings)` on `None`. Tag them `registry_write` and
   keep `GATED_TOOLS` in `auth.py` in sync.
6. Add a test using the in-memory client.

## Conventions

- Keep the **essentials** surface small: it is the loop you cannot author a
  module without, and nothing else.
- **Never hardcode a schema fact** — no column list, no vocabulary, no
  requirement. Call `describe_table` / `table_requirements` /
  `authoring_reference` and pass through what they return. The one exception is
  `authoring._SUBJECTS`, which answers "which table?" — a question about intent
  that the schema cannot answer — and is commented as such.
- **Preserve upstream's distinctions.** `error` / `warning` / `info`,
  `applied` / `refusal`, and `None` meaning *unchecked* are all load-bearing.
  Never collapse them into a boolean.
- Tools return structured models on failure rather than raising, unless the
  input is malformed (then `ToolError` is fine).
- Server-side logs use stdlib `logging` and **must** go to stderr
  (`logging_setup.py`); client-facing messages use `ctx.info` /
  `ctx.report_progress`.
- Line length 100; ruff rules in `pyproject.toml`.

## Background tasks

`enrich_module` is a real MCP background task (`@mcp.tool(task=True)`): it fetches
per variant and a panel-sized module takes minutes, so the client gets a task id
immediately, polls, and gets the result when done. Powered by the `fastmcp[tasks]`
extra (a core dependency). The default backend is **in-memory** (`memory://`) —
zero config, no Redis, embedded worker. For distributed/persistent tasks set
`FASTMCP_DOCKET_URL=redis://...`. `await client.call_tool(...)` transparently
submits, polls and returns the final result.

## Tests

Every fixture forces `offline=True` and `_env_file=None`, so the suite is
hermetic and cannot reach the network — important because half the tool surface
is network-capable. Tests assert *our* contract, not upstream's schema; where one
names a column it is because a tool docstring mentions it.

Note `from conftest import ...` rather than `from tests.conftest import ...`: a
transitive dependency ships a `tests` package that shadows ours.

## The plugin

- `.claude-plugin/plugin.json` — manifest; declares the MCP server inline using
  `${CLAUDE_PLUGIN_ROOT}` so it launches from the plugin directory, not the
  user's cwd.
- `.claude-plugin/marketplace.json` — lets `/plugin marketplace add ./` work.
- `skills/create-module/` — `SKILL.md` plus `references/`.

Keep the skill and the tool docstrings in agreement. If a tool changes what it
refuses to do, the skill's claim about that refusal changes with it.
