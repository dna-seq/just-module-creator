# Changelog

What actually shipped, newest first. Includes cross-repo integration changes made
on our side, so agents in sibling repos are not surprised.

## 0.2.0 — literature discovery, drafting, and the fact passes (2026-08-11)

### Adopted just-dna-compiler / -enricher 0.5.3

- Upstream shipped `_check_positional_joinability`, which **partly closes S9/F5**: `validate` and
  `compile` now warn per positional table how many rows have no `chrom`+`start` **and how many of
  those the injected `resolution.csv` could place**. Verified reaching our surface unchanged on the
  one-row `pharm_variants` reproduction. That second count is the actionable half — it separates
  "never enriched" from "the coordinates exist and this tier does not apply them". The coordinates
  themselves are still not materialized; upstream defers that to RM43 because filling them breaks
  Principle 7 (`reverse_module` would return a derived coordinate as an authored one).
- `heteroplasmy.csv` joined the enricher's subject list upstream, so an rsid-authored heteroplasmy
  module now resolves at all.
- `just-dna-registry` 0.11.3 is **not adopted**: it is unpublished (PyPI has 0.9.1) and lives in the
  renamed `just-dna-marketplace` repo, so taking it would mean a local path dependency and the
  plugin's one-command install would stop working for anyone else.

### New tools

- **`literature_search`** (essentials) — PubMed, Europe PMC, Semantic Scholar and the preprint
  index, merged. `pmids=[...]` reads titles back for ids you already have.
- **`lookup_open_access`**, **`fetch_fulltext`**, **`paper_citations`** (extended).
- **`draft_from_clinvar`** (essentials), **`draft_from_cpic`**, **`draft_from_clinpgx`** (extended)
  — closes F1/RM1, the hole in the middle of the taught workflow.
- **`enrich_facts`**, **`enrich_literature_pass`** (extended) — closes RM2.

### New skill

- `skills/find-evidence/` — search strategy, evidence appraisal, and the copyright rules that decide
  whether a module is publishable. `create-module` points at it from step 3 and stays the canonical
  authoring procedure.

### Why search is in the *essentials* tier

`CitationHint` carries no title, so `lookup_citation` can only prove a PMID **exists** — and PMIDs
are dense enough that a recalled one is usually a real record for a different paper. Both our skill
and the docstring told authors to "verify every PMID with `lookup_citation`", a rule the surface
could not enforce. Discovery is the missing half of an anti-fabrication promise the default tier had
already made. Filed upstream as `S12`; recorded as **F9**.

### Fixed

- `CitationLookup` was dropping `CitationHint.alterations` entirely, so the essentials tier was
  deleting the one refusal upstream hands it (the redundancy-bearing `doi`). Now carried, with
  `abstract_available`.
- `PacingGate` is not thread-safe and every tool here runs through `anyio.to_thread.run_sync`;
  `ServiceGate` adds the lock. One shared `LookupClients` per server replaces the per-call clients
  that were discarding rate-limit state.
- `lint_rows` documented refusals it never returns (F2/RM5) — narrowed to what it does return.
- `SKILL.md` and `DOMAIN.md` both claimed `draft --drug` refuses on multi-population pairs; upstream
  removed that in 0.5.1. RM1's rationale rested on the same removed behaviour.

### Owning sockets

`net.py` is now the only module permitted to open one, with retries on `tenacity` and upstream's own
`attempt_floor` stop so one deployment variable tunes our persistence and theirs together.
`JMC_LITERATURE_SOURCES` is a policy ceiling shaped like the offline one — a per-call `sources`
narrows it and can never widen it.

## Unreleased

### Adopted the house ruleset (2026-08-11)

- `AGENTS.md` is now a symlink to `CLAUDE.md`. They had been two different
  documents — a domain briefing and a code guide — so an agent's behaviour
  depended on which it happened to read.
- `CLAUDE.md` rewritten to the house template: must-reads in order, every
  prohibition inline, the `.claude`/`skills` assets named, and the authoring
  procedure left solely in the skill rather than restated beside it.
- Domain briefing moved to `docs/DOMAIN.md`.
- Adoption questionnaire answered and recorded: all four just-dna packages stay
  **hard dependencies** (no extras, no optional imports); this repo is an
  **application, not a published library** (no `__all__`, no re-export
  `__init__.py`); **no charter** — `just-dna-format`'s `CONSTITUTION.md` governs
  the format and ours would be a second charter about someone else's invariants.
- All inline imports hoisted to module top level.
- CLI now loads `.env` via `python-dotenv` (`override=False`) before reading
  configuration, so one `.env` serves both this server and the enricher it calls.
- Network transports print their URL before binding.
- `.env.example` → `.env.template`; removed the two placeholder values
  (`authors = "Your Name"`, `JMC_WORKSPACE=/path/to/your/modules`).
- Added the `assets/`, `data/{input,interim,output}` and `scripts/` layout with
  the ignore-all + allowlist rule on `data/`.

### The plugin (2026-08-11)

- Repo became a Claude Code plugin: `.claude-plugin/plugin.json` declares the MCP
  server inline using `${CLAUDE_PLUGIN_ROOT}` so it launches from the plugin
  directory rather than the user's cwd; `.claude-plugin/marketplace.json` makes
  `/plugin marketplace add ./` work.
- `skills/create-module/` — two independent authoring write-ups unified into one
  MCP-first skill, plus `references/{TABLES,SYMPTOMS,CLI}.md`. Removed the
  `.claude/skills/` copies they came from, which would otherwise have shadowed it
  with two same-named duplicates.
- Dropped 0.4-era history from the skill: this is a *new*-module creator, and that
  format version never reached production.

### The server (2026-08-11)

- Replaced the cake-demo FastMCP template with the just-dna authoring server.
  Package renamed `mcp_template` → `just_module_creator`; env prefix `CAKE_` →
  `JMC_`; Smithery removed (not applicable).
- `requires-python` raised to **≥3.13** — `just-dna-compiler` requires it. Ruff
  target, pyright version and the Docker base image moved with it.
- Added `just-dna-compiler`, `-format`, `-enricher`, `-registry`; bumped
  `fastmcp[tasks]` to ≥3.4.7.
- Tool tiers: **essentials** (the offline authoring loop plus the read-only
  lookups curation depends on), **extended** (enrichment as a background task,
  integrity, round-trip, registry reads), **gated** (registry writes, per-session
  token, never server-global).
- `JMC_OFFLINE` added as a hard network ceiling a per-call argument cannot
  override; `JMC_WORKSPACE` added as write containment for the HTTP transport.
- `compile_module` pins `resolve_with_ensembl=True`, so the wrapper cannot reach
  the branch that silently compiles every row with `chrom=None` and succeeds.

## Cross-repo

- **2026-08-11 — `just-dna-format`**: appended an independent corroboration to
  `docs/CONSUMER_SUGGESTIONS.md` **S9** (the non-SNP table families are
  materialized verbatim, so `resolution.csv` never reaches them). Reproduced here
  from the authoring surface with a `pharm_variants`-only module, twice — with and
  without a covering `resolution.csv` — which isolates the mechanism. Note left,
  not committed. No mitigation shipped on our side; the skill now tells authors to
  supply the rsID for those tables.
