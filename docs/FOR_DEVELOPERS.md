# For developers

The technical half of [README.md](../README.md): what the server is, how to run it standalone, the
full tool surface, and every switch. If you only want to *write a module*, the README is enough.

Agents start with [CLAUDE.md](../CLAUDE.md) — house rules and must-read order. The domain itself is
[DOMAIN.md](./DOMAIN.md).

## Why a server and not just a skill

Prose can ask an agent to behave; a tool can make it. Three rules are enforced here rather than
merely documented:

- **Ask the tool, never memory.** Every column list, vocabulary and requirement is generated from
  the live pydantic models in `just-dna-format`, so `describe_table` and `table_requirements`
  cannot drift from what the compiler accepts.
- **You may write; don't write a cell from the source that checks it.** This is the authoring
  layer, so revising and correcting is the job. What `lookup_variant` and `literature_search`
  withhold is narrower: those particular cells are redundancy-bearing, and a later check compares
  your independent value against the same source — so filling one from that source deletes a whole
  validation class and leaves the row *apparently* verified. The value is shown so you can compare
  it, not paste it, and the reason travels with it.
- **A mismatch against a source is not a defect report.** Archives lag: a paper is retracted, a
  bigger cohort moves the call. A row that disagrees may be right and current while the source is
  stale, so conforming it silently degrades the module — and the check then agrees with itself.
- **A check that could not run is not a check that passed.** `null` and `unknown` never collapse
  into a boolean pass. A literature source that timed out reports `results: null`, never `0`.

The one thing the toolchain has nowhere else is **literature discovery**. The enricher verifies
citations you already have; nothing upstream searches. So `literature_search` is the only way to
answer *"does this PMID name the paper I meant"* — existence alone cannot, because PMIDs are dense
enough that a recalled one is usually a real record for a different paper.

## Quickstart (standalone)

```bash
uv sync
uv run pytest                                  # in-memory and offline; no test can reach the network
uv run just-module-creator stdio               # run over stdio
uv run fastmcp dev fastmcp.json                # MCP Inspector
```

The server **boots with no environment configured** — authoring a module needs no registry account.

## The tools

**This table is the ones worth a note, not the roster.** It listed 32 of 48 while reading as complete,
which is the shape of claim this repo now warns about in `CLAUDE.md` §8 — a counted list in prose rots
exactly like a hardcoded one. **Ask the server instead**, which cannot drift:

```bash
uv run fastmcp dev fastmcp.json     # the Inspector lists every registered tool
```

Or from Python:

```python
from fastmcp import Client
from just_module_creator.server import build_server

async with Client(transport=build_server()) as client:
    names = sorted(tool.name for tool in await client.list_tools())
```

**There is one surface.** The `Cost` column below is a warning, not a gate: since 0.21.0 every tool
is registered on every start, and the expensive ones say so in their own descriptions.

| Tool | Cost | Token? | Notes |
|---|---|---|---|
| `list_tables` | bounded | no | which table kind a finding belongs in |
| `describe_table` | bounded | no | columns, vocabularies, pick-lists, redundancy-bearing cells |
| `table_requirements` | bounded | no | required / **defaulted** / optional + the one-of rules |
| `get_template` | bounded | no | header-only or stubbed CSV |
| `scaffold_module` | bounded | no | never overwrites; re-run to add a table |
| `lint_rows` | bounded | no | lints CSV *text*; writes nothing, anywhere |
| `validate_module` | bounded | no | pre-flight; pass the mode you will compile with |
| `compile_module` | bounded | no | parquet + `manifest.json` |
| `lookup_variant` | bounded | no | loci, alleles, ClinVar, rsID currency — and what it withholds |
| `literature_search` | bounded | no | **the papers behind a row** — with titles, across several services |
| `lookup_citation` | bounded | no | does this PMID/DOI exist, and which paper does it name |
| `registry_search` | bounded | no | has someone already built this |
| `registry_namespace_available` | bounded | no | is the name legal, is it free — the pre-flight for an irreversible claim |
| `draft_from_clinvar` | bounded | no | ClinVar → `variants.csv` + `studies.csv`; `use` required |
| `enrich_module` | bounded | no | **blocks; no task id despite `task=True`**; the only thing that catches a shifted `start` |
| `check_identifiers`, `lookup_identifier` | bounded | no | HGNC / OLS4 currency — what makes `trait_efo_id` writable honestly |
| `lookup_open_access`, `fetch_fulltext` | bounded | no | where may I read it and on what terms; the document, never a passage |
| `authoring_reference` | bounded | no | the whole generated DSL |
| `module_signature`, `verify_artifact` | bounded | no | did the content change; is the artifact intact |
| `registry_get_module` | bounded | no | one module's full record — the best worked example there is |
| `registry_is_published` | bounded | no | is this data already published **under any name** — local signature, nothing uploaded |
| `registry_health` | bounded | no | is the instance up, and does it agree it is the one you named |
| `registry_register` | always | — | **mints** an account and token, so it cannot be gated by one |
| `authenticate` | always | — | stores a registry token you already hold, for *this session* |
| `paper_citations` | corpus-sized | no | has this finding been replicated — traverses a graph the corpus sizes |
| `draft_from_cpic`, `draft_from_clinpgx` | corpus-sized | no | the PGx tables |
| `enrich_facts`, `enrich_literature_pass` | corpus-sized | no | the sidecars the compile gate reads; rewrite many rows at once |
| `record_override` | bounded | no | why an authored value outranks a source. **In response to a reported mismatch, never ahead of one** — a row markable as outranked before the check runs destroys the signal that catches a hallucination. Writes `provenance.json` and `logs/authoring.log` |
| `review_queue` | bounded | no | those records, ranked worst-first. `still_bound` is three-valued; `resolved` means the archive caught up and the override was vindicated |
| `compare_modules` | bounded | no | two spec directories, three grains, rows grouped by the set of columns that changed. No write path, no verdict on which side is right, and it never pairs rows whose key changed |
| `refresh_sidecar` | bounded, except `literature.csv` / `gwas_effects.csv` | no | capture, verify, delete, re-derive, reapply what is provably authored, report the rest. Refuses offline and refuses `licensing.csv` |
| `describe_machine_table` | bounded | no | the live columns of the machine-written tables, and what a hand-written cell there costs |
| `enrich_gwas_effects` | corpus-sized | no | the GWAS Catalog's published effect sizes, **beside** `weight` and never into it. `1 + 2N` requests per variant — the corpus of published associations sizes it |
| `reverse_module`, `registry_download` | bounded | no | get somebody else's published module onto disk — bounded by the one version you named |
| `registry_validate`, `registry_check` | gated | **yes** | would this publish — server-side, spending no version number. `check` is the full dry run |
| `registry_whoami`, `registry_claim_namespace`, `registry_publish` | gated | **yes** | registry writes; publish records the stamped identity in `published.json` |
| `registry_amend_readme` | gated | **yes** | fix a published module's card — outside `artifact.digest`, so no version is spent |
| `registry_delete_version`, `registry_delete_module` | gated | **yes** | undo a rehearsal on the polygon; refused for production, which offers `yank` instead |

Plus a resource (`resource://just-dna/tables`) and a prompt (`create_module`).

Not wrapped, and deliberately so — use the CLIs (`skills/module-101/references/CLI.md` has the
full surface): the PGx cross-checks, snapshot building, and signing. Signing stays out because
**module identity belongs to the registry**, which stamps `namespace`, `owner`, `version` and
`canonical_id` on publish; author-held Ed25519 signing sits beside that as a prototype, and wrapping
a prototype would lend it a durability its design has not earned.

`registry_publish` writes the identity it receives into a `published.json` receipt beside the spec —
canonical id, owner, digest, content signature, ISO-8601 UTC timestamp — because those keys are the
registry's answer and cannot live in `module_spec.yaml`, where they are rejected as registry-owned.
Commit it with the spec. A version already recorded is never overwritten: a published version is
immutable, so a changed digest is reported rather than applied.

## The workflow, as tool calls

```
list_tables ─▶ scaffold_module ─▶ draft_from_clinvar ─▶ literature_search ─▶ author rows
   ─▶ lint_rows ─▶ validate_module(strict) ─▶ enrich_module ─▶ compile_module(strict)
   ─▶ registry_check(target="test")     ─▶ ask whether it would publish, cost-free
   ─▶ registry_publish(target="test")   ─▶ registry_publish(target="prod")
```

`registry_check` is worth the extra step because a publish is not: it runs the server's own gates —
including the two your machine cannot know, whether `module.name` matches the path and whether
identical data is already published under someone else's name — and spends no version number doing
it. Read `verdict` as three-valued: `null` means the dry run never reached one, which is not a pass.

Curate before you enrich: a `<<REPLACE>>` placeholder makes every loader refuse the file, `enrich`
included, because forward resolution is allele-aware and a placeholder genotype would skip the
allele filter on exactly the rsIDs that need it.

## Accounts, namespaces and the two instances

Publishing for the first time needs an account, and that is self-service — no admin, no email, no
approval:

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

The registry runs a production catalog and a **polygon** — a second instance where a publish is a
rehearsal you can delete again. Every registry tool takes `target="test" | "prod"`; the write tools
default to the polygon and the catalog reads have **no default at all** — they refuse to guess which
instance a question is about, because reading the world you did not just write to is what makes a
fresh publish look like a broken catalog. The instances share no database,
so an account, a token and a namespace exist on one of them only, and promoting means publishing
again with `target="prod"`.

## One surface (the mode axis is gone)

`JMC_MODE`, `--mode` and the `extended` tier were removed in **0.21.0**. Every tool is registered on
every start; nothing has to be switched on, and nothing is missing because of how the server was
launched.

**The cost the tier was protecting is real and is now prose.** A handful of tools are sized by a
*corpus* rather than by what the caller named — `paper_citations`, the PGx drafters, the bulk fact
passes, and `enrich_gwas_effects` at `1 + 2N` requests per variant, measured at 382 for one real
module. Each says so in its own description, and
`tests/test_surface_and_auth.py::test_the_corpus_sized_tools_say_what_they_cost` fails if one stops
saying it. A caller can weigh that against what they are doing; a flag read at server start cannot.

**Why it went rather than being narrowed again.** The line was drawn four times and moved three:
read-vs-write never described the code, `enrich_module` was extended-only while being step 6 of the
taught order (0.4.0), `compare_to_published`'s own docstring named `registry_download` from a tier
that did not have it, and `refresh_sidecar` was invisible to both 2026-08-21 unattended runs, which
each concluded that `rm resolution.csv` is how a stale sidecar is re-derived. Every one is the same
defect — the surface taught a step it could not run — and hiding a tool never made its pass cheaper.
What survives is narrower and still fails loudly: `test_every_tool_the_taught_workflow_names_exists`
parses the taught order out of `server.INSTRUCTIONS`, and `test_docstrings_only_name_tools_that_exist`
asserts the same over every description.

Two axes remain, and neither is a tier. **Auth** decides whether the registry tools work — and,
with `JMC_HIDE_GATED_UNTIL_AUTH`, whether they are listed to a session that has not authenticated.
**Discovery** decides how the surface is presented: `JMC_TOOL_SEARCH` replaces the listing with
`search_tools` + `call_tool`.

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
the right lever there — but a `plugin.json` change to the server's `env` block also needs the
reconnect, because those values are only read when the server process starts.

## Auth

The server **never** raises at startup for a missing token. Gated tools resolve one **per request**:

1. `X-Registry-Token` / `X-Registry-Test-Token` HTTP header (multi-user safe)
2. per-session token set via `authenticate` — or by `registry_register`, which stores the token it
   mints into the same slot. The slot is FastMCP session state
   (`ctx.set_state("registry_token:<target>", …)`), namespaced by session id for us
3. `JMC_API_KEY`, else `REGISTRY_TOKEN` (what `registry-client` already reads) — and
   `JMC_TEST_API_KEY`, else `REGISTRY_TEST_TOKEN`, for the polygon

Each step resolves **per instance**. A production token is never offered to the polygon or the other
way round: the two keep separate databases, so the other instance's key is an unknown key there
rather than a weaker one, and falling back would report the wrong problem.

If none resolve, gated tools return a friendly message rather than raising. A token set via
`authenticate` is scoped to the caller's own session and never leaks between HTTP clients. Two
properties of that store are worth planning around: an entry **expires after 24h**, after which the
session is asked for its token again, and the default backend is an in-process `MemoryStore`, so a
multi-process HTTP deployment has to pass a shared one — `FastMCP(session_state_store=…)` — or a
worker will not see a token another worker stored.

`registry_register` is the one registry write that is never gated, because it is what produces the
token. It lives beside `authenticate` for that reason rather than with the other registry writes.

## Safety switches

| Variable | Effect |
|---|---|
| `JMC_OFFLINE=true` | Hard network ceiling. Every tool that could fetch runs cache-only, and a per-call `offline=false` cannot override it. |
| `JMC_WORKSPACE=/path` | Refuse to read or write outside this directory. Unset = no restriction (right for stdio; set it for HTTP). |
| `JMC_LITERATURE_SOURCES=a,b` | Which literature services this deployment may talk to. A per-call `sources` narrows it and can never widen it. Unset = all; `""` = none. |
| `JMC_HIDE_GATED_UNTIL_AUTH=true` | Hide the token-gated registry tools from a session until it authenticates. Off by default. |
| `JMC_TOOLBOX=layered` | List the core authoring loop only; hold nine named groups behind `toolbox`, which reveals one per session. Off by default. |

## Discovery: what a session is shown

**The listing is the biggest single thing this server puts in a context window.** Measured
2026-08-27 over the serialized `tools/list` payload (o200k tokenizer, so a few percent off Claude's):

| Surface | Tools | Tokens | % of a 200k window | Saving |
|---|---:|---:|---:|---:|
| flat (default) | 57 | 58,586 | 29.3% | — |
| `JMC_TOOLBOX=layered` | 18 | 17,759 | 8.9% | 69.7% |
| layered + `JMC_TOOL_SEARCH=regex` | 5 | 2,507 | 1.3% | 95.7% |
| *(the removed `extended` tier, for scale)* | 50 | 53,844 | 26.9% | 12.4% |

The last row is measured against the pre-0.23.0 payload it belonged to — 61,458 tokens, before the
docstring pass — so read it as *the tier saved an eighth* rather than against the baseline above it.

Descriptions are the third lever and the only one that costs nothing to pull: they were 70,528
characters of that payload before the 0.23.0 pass and are 59,751 after, which took the flat listing
down 4.7% and the layered one — where the trimming was concentrated, because `core` is what nobody
can decline — down 11.7%. The ceiling is in `CLAUDE.md` §5 and two tests hold it: `core` stops at
two paragraphs, everything else at six.

Three switches narrow what is **listed**, and none of them narrows what exists. That distinction is
the whole lesson of the removed tier, so keep it straight before reaching for any of them.

**`JMC_TOOLBOX=layered`** lists the 17 core tools plus `toolbox`, and holds the other nine groups —
`evidence`, `identifiers`, `pgx`, `passes`, `review`, `integrity`, `catalog`, `publish`, `closing` —
until a session asks. `toolbox()` with no arguments returns the roster: every group, what it is for,
the tools in it, and roughly what listing it would cost. `toolbox(groups=["evidence"])` reveals that
group **to the calling session** via `ctx.enable_components`. Everything `server.INSTRUCTIONS`
teaches is in `core`, derived from the instruction text by a test, so the taught order runs without
a single `toolbox` call. The default is `flat` because a mid-session reveal depends on the client
honouring `notifications/tools/list_changed`; where it does not, a revealed group shows up after a
reconnect.

**`JMC_HIDE_GATED_UNTIL_AUTH=true`** disables the `registry_write`-tagged tools at startup and
reveals them to a session when that session's own `authenticate` (or `registry_register`) succeeds.
The reveal is `ctx.enable_components`, which is **session-scoped**; `mcp.enable`/`disable` are
**server-global** and are used only for the startup half. The cost, and why it is off by default: a
session that has not authenticated cannot discover those tools at all, and calling one by name gets
"Unknown tool" instead of the message saying how to get a token. `registry_register` is never
hidden — it is what mints the token.

**`JMC_TOOL_SEARCH=regex|bm25`** (or `--tool-search`) replaces the tool listing with two synthetic
tools, `search_tools` and `call_tool`, so a client discovers by querying instead of receiving a
catalog of dozens. `JMC_TOOL_SEARCH_MAX_RESULTS` caps the hits. Things to know: an unlisted tool is
still callable by name, but the client never received its schema, so FastMCP's own client degrades
`result.data` to a plain dict — go through `call_tool` if you want the typed model. `regex` does not
rank, so a broad pattern plus a small `max_results` can cut the tool you meant; `bm25` ranks.
Resources and prompts are unaffected. It composes with the switch above: search sees what the
session may see.

## Configuration

All `JMC_*` variables are optional — see `.env.template` and `settings.py`, including
`JMC_TOOLBOX`, `JMC_HIDE_GATED_UNTIL_AUTH`, `JMC_TOOL_SEARCH` and `JMC_TOOL_SEARCH_MAX_RESULTS`. The just-dna toolchain's
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
  FOR_DEVELOPERS.md    this file
  BEYOND_BASICS.md     what more a module can carry once the simple one works
  CHANGELOG.md         what shipped, newest first
  ROADMAP.md           open items only; ROADMAP_HISTORY.md holds the rest
  dogfooding.md        open findings from real use (F# ids)
.claude-plugin/
  plugin.json          manifest; declares the MCP server via ${CLAUDE_PLUGIN_ROOT}
  marketplace.json     so `/plugin marketplace add ./` works
skills/module-101/
  SKILL.md             the map: what a module is, the tool roster, which stage owns your step
  references/
    SYMPTOMS.md        message text -> cause -> action
    CLI.md             the full CLI surface, and what is not wrapped
skills/module-{start,draft,curate,enrich,check,compile,close,publish}/
  SKILL.md             one lifecycle stage each; no skill restates another's procedure
skills/module-{revise,refresh,diff}/
  SKILL.md             the second-pass half: which kind of pass, re-running, what moved
skills/module-{tables,weights,consumer}/
  SKILL.md             the references the stages load
skills/find-evidence/
  SKILL.md             search, appraise, and what a paper's licence lets you reuse
src/just_module_creator/
  server.py            build_server(), CLI, graceful shutdown
  settings.py          pydantic-settings (JMC_*), safe defaults
  tool_search.py       optional: collapse the listing into search_tools + call_tool
  toolbox.py           optional: the core group, the other nine, and the reveal
  auth.py              per-request token resolution (FastMCP session state)
  models.py            trimmed Pydantic tool I/O
  logging_setup.py     stdlib logging -> stderr
  net.py               the ONLY module that opens a socket: pacing, retries
  discovery.py         literature sources, parsers, and the refusals
  tools/
    authoring.py       the offline loop, schema dump, integrity
    research.py        read-only lookups: variants, papers, identifiers
    passes.py          fetch-then-write: draft_from_clinvar + enrich_module, then
                       the PGx drafters and the fact passes
    advanced.py        citation graph, reverse, registry download
    registry.py        token-gated registry writes
    _shared.py         path containment, offline ceiling, converters
tests/                 in-memory, offline
assets/                fixtures that must travel; data/ is git-ignored
```

## Upstream

`just-dna-format` (schema) ← `just-dna-compiler` (spec → parquet) ← `just-dna-enricher` (the only
tier that fetches), plus `just-dna-registry` (catalog client). The dependency arrow points inward;
only the enricher touches the network.
