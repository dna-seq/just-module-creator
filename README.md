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
uv run pytest                                  # in-memory and offline; no test can reach the network
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
| `literature_search` | essentials | no | **the papers behind a row** — with titles, across several services |
| `lookup_citation` | essentials | no | does this PMID/DOI exist, and which paper does it name |
| `registry_search` | essentials | no | has someone already built this |
| `registry_namespace_available` | essentials | no | is the name legal, is it free — the pre-flight for an irreversible claim |
| `draft_from_clinvar` | essentials | no | ClinVar → `variants.csv` + `studies.csv`; `use` required |
| `enrich_module` | essentials | no | **background task**; the only thing that catches a shifted `start` |
| `check_identifiers`, `lookup_identifier` | essentials | no | HGNC / OLS4 currency — what makes `trait_efo_id` writable honestly |
| `lookup_open_access`, `fetch_fulltext` | essentials | no | where may I read it and on what terms; the document, never a passage |
| `authoring_reference` | essentials | no | the whole generated DSL |
| `module_signature`, `verify_artifact` | essentials | no | did the content change; is the artifact intact |
| `registry_get_module` | essentials | no | one module's full record — the best worked example there is |
| `registry_is_published` | essentials | no | is this data already published **under any name** — local signature, nothing uploaded |
| `registry_health` | essentials | no | is the instance up, and does it agree it is the one you named |
| `registry_register` | always | — | **mints** an account and token, so it cannot be gated by one |
| `authenticate` | always | — | stores a registry token you already hold, for *this session* |
| `paper_citations` | extended | no | has this finding been replicated — traverses a graph the corpus sizes |
| `draft_from_cpic`, `draft_from_clinpgx` | extended | no | the PGx tables |
| `enrich_facts`, `enrich_literature_pass` | extended | no | the sidecars the compile gate reads; rewrite many rows at once |
| `reverse_module`, `registry_download` | extended | no | read back somebody else's compiled artifact |
| `registry_validate`, `registry_check` | gated | **yes** | would this publish — server-side, spending no version number. `check` is the full dry run |
| `registry_whoami`, `registry_claim_namespace`, `registry_publish` | gated | **yes** | registry writes; publish records the stamped identity in `published.json` |
| `registry_amend_readme` | gated | **yes** | fix a published module's card — outside `artifact.digest`, so no version is spent |
| `registry_delete_version`, `registry_delete_module` | gated | **yes** | undo a rehearsal on the polygon; refused for production, which offers `yank` instead |

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
   ─▶ registry_check(target="test")     ─▶ ask whether it would publish, cost-free
   ─▶ registry_publish(target="test")   ─▶ registry_publish(target="prod")
```

`registry_check` is worth the extra step because a publish is not: it runs the server's own
gates — including the two your machine cannot know, whether `module.name` matches the path and
whether identical data is already published under someone else's name — and spends no version
number doing it. Read `verdict` as three-valued: `null` means the dry run never reached one,
which is not a pass.

Publishing for the first time needs an account, and that is self-service from here — no admin, no
email, no approval:

```
registry_register(account="my-name")            ─▶ mints the token, stores it for this session
registry_namespace_available("my-ns")           ─▶ legal? free?
registry_claim_namespace("my-ns")               ─▶ irreversible on production
```

`registry_register` returns two secrets and neither is recoverable elsewhere: put the token in `.env`
as `JMC_API_KEY` (or `JMC_TEST_API_KEY` for the polygon) and **the install-id as `JMC_INSTALL_ID`**.
The install-id is the account's only recovery path — re-registering it reissues a key for the same
account, while registering without it creates a different one and strands the first. Account and
namespace names are lowercase with hyphens and reject underscores; module names are the opposite and
take them.

### Two registries: rehearse, then publish

The registry runs a production catalog and a **polygon** — a second instance where a publish is a
rehearsal you can delete again. Every registry tool takes `target="test" | "prod"`; the write tools
default to the polygon and the catalog reads default to production. The instances share no database,
so an account, a token and a namespace exist on one of them only, and promoting means publishing
again with `target="prod"`.

Rehearsing is worth the extra step because a production publish cannot be taken back: the version is
immutable and the authored rows are claimed by a content hash that outlives a `yank`.

Curate before you enrich: a `<<REPLACE>>` placeholder makes every loader refuse the file, `enrich`
included, because forward resolution is allele-aware and a placeholder genotype would skip the
allele filter on exactly the rsIDs that need it.

## Modes

`JMC_MODE` (env) or `--mode` (CLI), default `essentials`. The line is **cost, not usefulness**:

- `essentials` — everything whose work is bounded by what you named: one identifier, one paper, one
  spec directory. That is the whole taught workflow plus the checks around it, so this tier takes a
  variants or SNP module from nothing to compiled, verified and published.
- `extended` — only what a corpus sizes: `paper_citations`, the PGx drafters, the bulk fact passes,
  and reading back somebody else's compiled artifact (`reverse_module`, `registry_download`).

It used to be read-vs-write, which never described the code — `scaffold_module` and `compile_module`
both write and were always essentials, while `lookup_identifier` only reads and was not. Worse, the
server taught `… → enrich_module → compile_module` as the canonical order while `enrich_module` was
extended-only, so an agent following the default tier's own instructions hit a tool that was not
there. `tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier` now parses
the tool names out of that instruction text and fails if any of them is missing from essentials.

### Switching mode

Where you set it depends on how the server was started, and **the three ways do not fall back to
each other**:

| Started as | Switch by |
|---|---|
| plugin (`/plugin install`, `--plugin-dir`) | edit `JMC_MODE` in `.claude-plugin/plugin.json` → reconnect |
| project MCP server (`.mcp.json` in a checkout) | edit `JMC_MODE` in that file → reconnect |
| standalone CLI | `uv run just-module-creator stdio --mode extended`, or `JMC_MODE` in the shell or `.env` |

**Editing `.env` cannot switch a plugin-launched server.** `plugin.json` sets `JMC_MODE` in the
server's `env` block, so it is already exported in the subprocess before any code runs, and `.env` is
loaded with `override=False` — an exported variable wins deliberately, so the file is read and then
ignored for that key. Nothing warns you; the tool list simply does not change. Same for `.mcp.json`.
`JMC_MODE` is the only setting this bites, because it is the only one those files pin.

To confirm which tier is actually live rather than which one you configured, ask for a tool that
exists in one and not the other — `enrich_module` is present only in extended.

## Reloading after a change

The plugin runs the server from the checkout (`uv run --project ${CLAUDE_PLUGIN_ROOT}`), so a Python
edit needs the **subprocess restarted, not a reinstall**. What restarts it is the part that surprises
people:

| Action | Restarts the MCP server? |
|---|---|
| `/reload-plugins` | **No.** Skills and manifests reload; a running stdio server keeps serving its old tool list. |
| `/mcp` → reconnect the server | **Yes.** This is the one to use after editing Python. |
| Restarting Claude Code | Yes. |

`/reload-plugins` was verified not to re-exec the server by comparing process start times against the
commit time: no new process appeared and the old tool list survived. Stale servers **accumulate**
rather than being replaced, so if tool behaviour looks like a version you no longer have on disk,
check for leftover processes:

```bash
pgrep -af just-module-creator
```

Editing `SKILL.md`, `references/*.md` or `plugin.json` is a *plugin* change, so `/reload-plugins` is
the right lever there — but a `plugin.json` change to `JMC_MODE` also needs the reconnect, because
that value is only read when the server process starts.

## Auth

The server **never** raises at startup for a missing token. Gated tools resolve one **per request**:

1. `X-Registry-Token` / `X-Registry-Test-Token` HTTP header (multi-user safe)
2. per-session token set via `authenticate` — or by `registry_register`, which stores the token it
   mints into the same slot
3. `JMC_API_KEY`, else `REGISTRY_TOKEN` (what `registry-client` already reads) — and
   `JMC_TEST_API_KEY`, else `REGISTRY_TEST_TOKEN`, for the polygon

Each step resolves **per instance**. A production token is never offered to the polygon or the other
way round: the two keep separate databases, so the other instance's key is an unknown key there
rather than a weaker one, and falling back would report the wrong problem.

If none resolve, gated tools return a friendly message rather than raising. A token set via
`authenticate` is scoped to the caller's own session and never leaks between HTTP clients. See
[CLAUDE.md](./CLAUDE.md) for the multi-tenant caveat about `mcp.enable()`.

`registry_register` is the one registry write that is never gated, because it is what produces the
token. It lives beside `authenticate` for that reason rather than with the other registry writes.

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
    authoring.py       essentials — the offline loop, schema dump, integrity
    research.py        essentials — read-only lookups: variants, papers, identifiers
    passes.py          fetch-then-write: draft_from_clinvar + enrich_module (both
                       essentials), then the extended PGx drafters and fact passes
    advanced.py        extended — citation graph, reverse, registry download
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
