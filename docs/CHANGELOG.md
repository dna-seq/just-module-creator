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

### `registry_publish` now keeps the identity it is given

The registry is the authority on module identity — it stamps `namespace`, `owner`, `version` and
`canonical_id` on publish and overrides anything authored. We were returning that in a message and
dropping it, so nothing on disk recorded that a spec had ever been published, under what identity, or
against which digest. It now lands in a `published.json` receipt beside the spec, with the artifact
digest, the content signature and an ISO-8601 UTC timestamp. Not a cache and not a temp dir: a receipt
that does not survive the session is not a record. It cannot go into `module_spec.yaml` either —
`module:` is `extra="forbid"` and those exact keys are rejected there because the registry owns them
(upstream S1). An already-recorded version is never overwritten; a published version is immutable, so
a changed digest is reported for investigation rather than applied.

### Three documentation gaps filed upstream

Facts we had to establish by **experiment** rather than read, filed as `S15`–`S17`
in the format tree under their own "Documentation gaps" heading — nothing is
misbehaving, so they read as a separate category:

- **`PacingGate`'s concurrency contract is unstated, and it is not thread-safe.** We
  found this by demonstration (four threads overlap inside `wait()` on a frozen
  clock) and shipped a locked `ServiceGate` subclass. `ENRICHER.md` documents the
  class in nine places without a concurrency caveat, which matters because
  `LookupClients`' own docstring tells callers to hold and reuse one — exactly the
  arrangement that needs the answer.
- **Whether a spec directory may hold files the compiler does not know is
  unspecified.** It tolerates them; we tested, and `published.json` now relies on it.
- **`source` exists on only 4 of 16 row models, and all four are enricher-produced.**
  No authored table has one, so the `sources.csv` coverage check can only see sources
  a *pass* introduced — a hand-read source is structurally invisible, not merely easy
  to forget. Found by putting a `source` column on a `pharm_variants.csv` and getting
  `Extra inputs are not permitted`.

The rule behind them is now in `CLAUDE.md` §8: a fact you had to probe is a doc bug,
and the experiment is the argument for fixing it.

### Two upstream intakes, not one

The registry keeps its own `docs/CONSUMER_SUGGESTIONS.md` (created 2026-08-11, its own
`S<n>` series) at `../just-dna-marketplace/` — a stale directory name; the project and
package are `just-dna-registry`. Our
intake rule said one file served all four packages, which had stopped being true. The
`would_publish` note was written into the format tree by mistake and moved; a note in
the wrong file may as well not be filed.

### Docs swept for upstream gaps we had absorbed as our own

Three items were sitting in our roadmap or our skill as though the work were ours:

- **`would_publish`'s variant ceiling** (`422 too_many_variants` on a large module) had never been
  filed, and the idea book proposed building our own `check_publishable` to route around it. Filed as
  **S15**, tracked as **F11**, idea-book entry withdrawn — a parallel publishability check in a
  consumer is how two answers to one question start drifting.
- **RM7** (no `sources.csv` terms for any literature source) is upstream's granularity question. There
  was never work here for us: we report it and refuse to fill it. Removed from the roadmap, now **F8**
  in `just-dna-format-pending-fixes.md`.
- **F9** (`lookup_citation` cannot check identity) gained its upstream-blocked entry alongside the
  dogfooding one, since the mitigation is ours and the fix is not.

`docs/ROADMAP.md` now states the rule at the top: an item belongs there only if the work is ours.
**RM3** (signing) is deferred with its reason, and **RM4** was reclassified — it is a dogfooding probe,
not a deliverable, and now lives in `dogfooding.md`.

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
