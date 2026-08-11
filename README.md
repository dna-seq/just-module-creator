# just-module-creator

A **Claude Code plugin** for authoring [just-dna](https://module-registry.just-dna.life)
annotation modules. It ships two halves that work together:

- an **MCP server** wrapping the just-dna toolchain with structured, agent-shaped tools, and
- two **skills** — one teaching the authoring workflow, one teaching how to find and read the
  evidence behind a row.

A module is a directory of authored CSVs plus `module_spec.yaml`, compiled into a parquet artifact
with a content-addressed `manifest.json`. It carries annotation only — lookup tables mapping a
genotype or a measured quantity to a phenotype.

> Agents: start with [CLAUDE.md](./CLAUDE.md) — the house rules and the must-read order.
> (`AGENTS.md` is a symlink to it.) The domain itself is [docs/DOMAIN.md](./docs/DOMAIN.md).

## Why a server and not just a skill

Prose can ask an agent to behave; a tool can make it. Three rules are enforced here rather than
merely documented:

- **Ask the tool, never memory.** Every column list, vocabulary and requirement is generated from
  the live pydantic models in `just-dna-format`, so `describe_table` and `table_requirements`
  cannot drift from what the compiler accepts.
- **Report, never repair.** `lookup_variant` and `literature_search` show you a value and *refuse* to
  write it into an authored cell, with the reason attached. Those cells are redundancy-bearing: a
  later check compares your independent value against the same source, so filling it from that source
  deletes a whole validation class.
- **A check that could not run is not a check that passed.** `null` and `unknown` never collapse into
  a boolean pass. A literature source that timed out reports `results: null`, never `0`.

The one thing the toolchain has nowhere else is **literature discovery**. The enricher verifies
citations you already have; nothing upstream searches. So `literature_search` is the only way to
answer *"does this PMID name the paper I meant"* — existence alone cannot, because PMIDs are dense
enough that a recalled one is usually a real record for a different paper.

## Install as a plugin

```bash
# One session, straight from a checkout
claude --plugin-dir /path/to/just-module-creator

# Or via the bundled marketplace
/plugin marketplace add /path/to/just-module-creator
/plugin install just-module-creator@just-dna
```

Requires [`uv`](https://docs.astral.sh/uv/) on PATH and Python ≥ 3.13. The plugin launches the
server with `uv run --project ${CLAUDE_PLUGIN_ROOT}`, so dependencies install on first use.

## Quickstart (standalone)

```bash
uv sync
uv run pytest                                  # 81 tests, in-memory and offline
uv run just-module-creator stdio               # run over stdio
uv run just-module-creator stdio --mode extended
uv run fastmcp dev fastmcp.json                # MCP Inspector
```

The server **boots with no environment configured** — authoring a module needs no registry account.

## The tools

| Tool | Tier | Token? | Notes |
|---|---|---|---|
| `list_tables` | essentials | no | which table kind a finding belongs in |
| `describe_table` | essentials | no | columns, vocabularies, pick-lists, redundancy-bearing cells |
| `table_requirements` | essentials | no | required / **defaulted** / optional + the one-of rules |
| `get_template` | essentials | no | header-only or stubbed CSV |
| `scaffold_module` | essentials | no | never overwrites; re-run to add a table |
| `lint_rows` | essentials | no | lints CSV *text*; writes nothing, anywhere |
| `validate_module` | essentials | no | pre-flight; pass the mode you will compile with |
| `compile_module` | essentials | no | parquet + `manifest.json` |
| `lookup_variant` | essentials | no | loci, alleles, ClinVar, rsID currency — and what it withholds |
| `literature_search` | essentials | no | **the papers behind a row** — and the only way to check a PMID's *identity* |
| `lookup_citation` | essentials | no | does this PMID/DOI *exist* (not: is it the right paper) |
| `registry_search` | essentials | no | has someone already built this |
| `draft_from_clinvar` | essentials | no | ClinVar → `variants.csv` + `studies.csv`; `use` required |
| `authenticate` | always | — | stores a registry token for *this session* |
| `lookup_open_access`, `fetch_fulltext` | extended | no | where may I read it and on what terms; the document, never a passage |
| `paper_citations` | extended | no | has this finding been replicated |
| `draft_from_cpic`, `draft_from_clinpgx` | extended | no | the PGx tables |
| `enrich_facts`, `enrich_literature_pass` | extended | no | the sidecars the compile gate reads |
| `enrich_module` | extended | no | **background task**; the only thing that catches a shifted `start` |
| `check_identifiers`, `lookup_identifier` | extended | no | HGNC / OLS4 currency |
| `authoring_reference` | extended | no | the whole generated DSL |
| `module_signature`, `verify_artifact`, `reverse_module` | extended | no | integrity and round-trip |
| `registry_get_module`, `registry_download` | extended | no | read the catalog |
| `registry_whoami`, `registry_claim_namespace`, `registry_publish` | gated | **yes** | registry writes; publish records the stamped identity in `published.json` |

Plus a resource (`resource://just-dna/tables`) and a prompt (`create_module`).

Not wrapped, and deliberately so — use the CLIs (`references/CLI.md` has the full surface): the PGx
cross-checks, snapshot building, and signing. Signing stays out because **module identity belongs to
the registry**, which stamps `namespace`, `owner`, `version` and `canonical_id` on publish; author-held
Ed25519 signing sits beside that as a prototype, and wrapping a prototype would lend it a durability
its design has not earned.

`registry_publish` writes the identity it receives into a `published.json` receipt beside the spec —
canonical id, owner, digest, content signature, ISO-8601 UTC timestamp — because those keys are the
registry's answer and cannot live in `module_spec.yaml`, where they are rejected as registry-owned.
Commit it with the spec. A version already recorded is never overwritten: a published version is
immutable, so a changed digest is reported rather than applied.

## The workflow

```
list_tables ─▶ scaffold_module ─▶ draft_from_clinvar ─▶ literature_search ─▶ author rows
   ─▶ lint_rows ─▶ validate_module(strict) ─▶ enrich_module ─▶ compile_module(strict)
   ─▶ registry_publish
```

Curate before you enrich: a `<<REPLACE>>` placeholder makes every loader refuse the file, `enrich`
included, because forward resolution is allele-aware and a placeholder genotype would skip the
allele filter on exactly the rsIDs that need it.

## Modes

`JMC_MODE` (env) or `--mode` (CLI), default `essentials`. The line is **what a tool does, not how
useful it is**:

- `essentials` — everything that only *reads*, plus the ClinVar draft. Small on purpose: fewer tools
  is less context pollution, and this tier can still take a variants module from nothing to compiled.
- `extended` — everything that writes into a spec directory or fetches at scale: the PGx drafters,
  enrichment, the fact passes, integrity, round-trip and registry reads.

## Auth

The server **never** raises at startup for a missing token. Gated tools resolve one **per request**:

1. `X-Registry-Token` HTTP header (multi-user safe)
2. per-session token set via the `authenticate` tool
3. `JMC_API_KEY`, else `REGISTRY_TOKEN` (what `registry-client` already reads)

If none resolve, gated tools return a friendly message rather than raising. A token set via
`authenticate` is scoped to the caller's own session and never leaks between HTTP clients. See
[CLAUDE.md](./CLAUDE.md) for the multi-tenant caveat about `mcp.enable()`.

## Safety switches

| Variable | Effect |
|---|---|
| `JMC_OFFLINE=true` | Hard network ceiling. Every tool that could fetch runs cache-only, and a per-call `offline=false` cannot override it. |
| `JMC_WORKSPACE=/path` | Refuse to read or write outside this directory. Unset = no restriction (right for stdio; set it for HTTP). |
| `JMC_LITERATURE_SOURCES=a,b` | Which literature services this deployment may talk to. A per-call `sources` narrows it and can never widen it. Unset = all; `""` = none. |

## Configuration

All `JMC_*` variables are optional — see `.env.template` and `settings.py`. The just-dna toolchain's
own variables (`JUST_DNA_*_CACHE`, `NCBI_API_KEY`, `PHARMVAR_API_KEY`, `REGISTRY_TOKEN`) are read by
the enricher straight from the process environment; `.env.template` documents them so everything is
configured in one place.

`PHARMVAR_API_KEY` is personal under PharmVar's ToS §2 — never bake it into a module or a snapshot.

## Deployment

- **Docker**: `docker build -t just-module-creator . && docker run -p 3011:3011 just-module-creator`
  (defaults to HTTP). Set `JMC_WORKSPACE` for multi-user deployments.
- **Declarative**: `fastmcp.json` drives `fastmcp run` / `fastmcp dev`.

## Project layout

```
CLAUDE.md              house rules; AGENTS.md is a symlink to it
docs/
  DOMAIN.md            what a module is and the traps that constrain the tools
  CHANGELOG.md         what shipped, newest first
  ROADMAP.md           open items only; ROADMAP_HISTORY.md holds the rest
  dogfooding.md        open findings from real use (F# ids)
.claude-plugin/
  plugin.json          manifest; declares the MCP server via ${CLAUDE_PLUGIN_ROOT}
  marketplace.json     so `/plugin marketplace add ./` works
skills/create-module/
  SKILL.md             the workflow, MCP-first
  references/
    TABLES.md          which table kind a finding belongs in
    SYMPTOMS.md        message text -> cause -> action
    CLI.md             the full CLI surface, and what is not wrapped
skills/find-evidence/
  SKILL.md             search, appraise, and what a paper's licence lets you reuse
src/just_module_creator/
  server.py            build_server(), CLI, graceful shutdown
  settings.py          pydantic-settings (JMC_*), safe defaults
  auth.py              per-session/per-request token resolution
  models.py            trimmed Pydantic tool I/O
  logging_setup.py     stdlib logging -> stderr
  net.py               the ONLY module that opens a socket: pacing, retries
  discovery.py         literature sources, parsers, and the refusals
  tools/
    authoring.py       essentials — the offline authoring loop
    research.py        essentials — read-only network lookups + literature search
    passes.py          drafting from a source; the sidecar fact passes
    advanced.py        extended — enrichment, integrity, round-trip
    registry.py        token-gated registry writes
    _shared.py         path containment, offline ceiling, converters
tests/                 in-memory, offline
assets/                fixtures that must travel; data/ is git-ignored
```

## Upstream

`just-dna-format` (schema) ← `just-dna-compiler` (spec → parquet) ← `just-dna-enricher` (the only
tier that fetches), plus `just-dna-registry` (catalog client). The dependency arrow points inward;
only the enricher touches the network.

## License

MIT — see [LICENSE](./LICENSE).
