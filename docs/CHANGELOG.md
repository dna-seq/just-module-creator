# Changelog

What actually shipped, newest first. Includes cross-repo integration changes made
on our side, so agents in sibling repos are not surprised.

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
