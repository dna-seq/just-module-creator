# Changelog

What actually shipped, newest first. Includes cross-repo integration changes made
on our side, so agents in sibling repos are not surprised.

## 0.4.0 — the essentials tier now runs the whole workflow (2026-08-11)

### The tier rule was wrong, not just one tool short of right

Dogfooding reported a narrow gap: the default tier could not verify a trait CURIE, because
`lookup_identifier` and `check_identifiers` were extended-only. `describe_table` would tell an
author that `trait_efo_id` takes an ontology CURIE and then offer nothing that checks one, so the
honest move was to leave the column blank and the tempting one was to write an id from memory —
which is precisely what rule 1 of the server instructions forbids.

Surveying before fixing turned up that the gap was a symptom. The stated rule — *essentials is
everything that only reads, plus the ClinVar draft* — did not describe the code **in either
direction**. `scaffold_module` and `compile_module` both write and were always essentials, while six
read-only tools sat behind the mode flag. And the worst case was not on anyone's list:
**`enrich_module` was extended-only while being step 6 of the order the server's own INSTRUCTIONS
teach**, so an agent following the default tier's instructions reached for a tool that was not there.

So the rule changed rather than the membership. **The tiers now split on cost, not usefulness:**

- **essentials** — everything whose work is bounded by what the caller named: one identifier, one
  paper, one spec directory. That is the whole taught workflow, scaffold through publish.
- **extended** — only what a *corpus* sizes (`paper_citations`, the PGx drafters, the bulk fact
  passes) or that reads back somebody else's compiled artifact (`reverse_module`,
  `registry_download`). Seven tools, down from sixteen.

Nine tools moved into essentials: `enrich_module`, `check_identifiers`, `lookup_identifier`,
`fetch_fulltext`, `lookup_open_access`, `authoring_reference`, `module_signature`, `verify_artifact`,
`registry_get_module`. Nothing left essentials, so this is additive for every existing caller —
`extended` still lists a strict superset.

Each landed beside its siblings rather than in a second closure: the schema dump and the integrity
pair in `authoring.py` (still network-free), the identifier and paper reads in `research.py` (still
writes nothing to a spec), and `enrich_module` in `passes.py` next to `draft_from_clinvar` — they are
the only two tools that fetch and then write into a spec directory, which is now what that module
means. `advanced.py` keeps the three that stayed.

### The guard is derived, not restated

`tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier` parses tool names
straight out of `server.INSTRUCTIONS` and asserts every one exists in essentials. It is written
against the text rather than a copy of it, so editing the taught order re-checks the tier for free.
Verified to bite: the parse yields `enrich_module`, which the pre-0.4.0 essentials tier did not have.
`test_extended_mode_is_a_superset` additionally pins `extended - essentials` to an exact set, so a
tool cannot drift between tiers unnoticed.

### Also

- **`authoring_reference` was unreachable from the tier that is told to call it.** `CLAUDE.md` §2 and
  the skill both instruct an agent to ask `describe_table` / `table_requirements` /
  `authoring_reference` rather than recall a schema fact — and the third was behind a mode flag. A
  rule pointing at a tool the default tier lacks is a rule that gets ignored.
- **README gained "Reloading after a change" and "Switching mode."** `/reload-plugins` does not
  re-exec a stdio MCP server — `/mcp` reconnect does — and stale servers accumulate. Mode has three
  launch paths that do not fall back to each other, and **editing `.env` cannot switch a
  plugin-launched server**: `plugin.json` exports `JMC_MODE` into the subprocess and `.env` loads with
  `override=False`, so the file is read and then ignored for that key, silently. Probed, not assumed.
- **The credential how-to moved into the skill.** It had been living in `docs/UX_TESTER.md`, where an
  author would never see it. `SKILL.md` §7 now also answers the account-*name* half: there is nothing
  to save, because `registry_whoami` reports it and re-registering with the same install-id returns
  the account that id owns while ignoring the `account` argument.

## 0.3.0 — registry onboarding (2026-08-11)

### A version bump touches two files, and the suite now knows it

`.claude-plugin/plugin.json` is JSON and cannot read `importlib.metadata`, so it is the one place
`CLAUDE.md` §2's "never hardcode a version string" cannot be obeyed — and it shipped this release
still declaring 0.2.0, caught in review rather than by anything automated. The drift is silent:
plugin loading is unaffected, so the only symptom is an installed plugin misreporting itself.

Fixed, and `tests/test_plugin_manifest.py` now fails on the mismatch, verified by reverting the
manifest and watching it fail rather than assuming it would. The same file pins the other
hand-maintained claims in the manifest: that its `mcpServers` command is still the console script
`[project.scripts]` installs and stays `${CLAUDE_PLUGIN_ROOT}`-relative, that the declared skills
directory holds the two skills the description promises, and that `marketplace.json` carries no
version of its own — one hand-maintained version string is the ceiling.

### You can get a registry account from inside the tool surface

Dogfooding hit the wall at step zero: every registry tool needed a token, and the only route to one
the surface named was `registry-client register`, a shell command in another package. The plugin
gated every registry action behind a credential nothing in it could mint, which made a one-command
install quietly cost a second toolchain. Recorded as `F12`/`F13`, both now in
[previous_issues.md](previous_issues.md).

Nothing upstream was owed. `RegistryClient.register` and `.namespace_available` are public in the
**published** 0.9.1; `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email, self-service by design), and
`generate_install_id()` grinds the proof-of-work locally in about a second. Two public APIs we had
never wrapped.

- **`registry_register(account, install_id=None, difficulty=None)`** — always on, in `auth.py`
  beside `authenticate`. The one registry write that cannot be token-gated, because it is what
  produces the token; `CLAUDE.md` §5 now names that exception and bounds it to a set of one. Not
  extended-only either — hiding the only route to a credential behind a mode flag is the same dead
  end in a different place. The minted token goes into the caller's own session slot, so registering
  leaves the session usable and no secret travels back through the transcript by hand.
- **Both secrets are returned, and the install-id carries its warning in the field description.** It
  is the account's only recovery path: re-registering it reissues a key for the *same* account,
  while registering again without it creates a different one and strands the first. `JMC_INSTALL_ID`
  was added so a later session can reuse it — a value we read and never write, because persisting a
  secret ourselves would widen the write surface. `account_taken` now says outright that retrying
  cannot help, since a key is only ever reissued to the install-id that created the account.
- **`registry_namespace_available(namespace)`** — essentials, read-only, no token. The pre-flight
  `registry_claim_namespace` demanded and did not offer. `valid` and `available` stay separate
  answers, which the live registry justifies immediately: it reports `test_modules` as
  `valid: false, available: true`. One boolean would have called an illegal name claimable.
- **The name rules are stated wherever they bite.** Accounts obey the *namespace* rule
  (`^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` was rejected before anything else could happen,
  while module names are the opposite (`^[a-z][a-z0-9_]*$`) — hence `my-ns/lactose_tolerance`. An
  illegal account name is refused locally, with the pattern quoted, before a round trip is spent.
  "Lowercase, hyphen-separated" was replaced everywhere it appeared: it read as a style preference
  rather than a hard reject.

Verified hermetically (name refused before any socket opens, offline ceiling holds for both tools,
install-id precedence and origin) and against the live registry read-only, including one real
failure path. Minting an account and claiming a namespace are left to the dogfooding side: a builder
who runs the irreversible probe has graded their own work.

### Upstream had answered every one of our findings, and our docs did not know

Checked `../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md` for the first time. The format
tree's inbox holds only *open* items — an answered `S<n>` moves out, prose byte-for-byte — so it has
been empty since 2026-08-11 with `S1`–`S18` all answered. Meanwhile every entry in our
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md) still said "open upstream". All
eight were answered; six are fixed **in tree for the unreleased 0.5.4**.

That distinction is now written down as three states rather than two — *accepted and filed* →
*fixed in tree* → *released* — because only the third lets a mitigation come out, and the middle one
is the easy mistake. PyPI's newest is compiler/enricher 0.5.3 and format 0.5.0, which is what we
install; confirmed by symbol rather than changelog (`hints.ATTESTATION_BEARING`,
`hints._report_ragged`, `Finding.line` are in the sibling checkout and absent from the installed
package — and `hints.py` lives in the **compiler**, not the enricher).

- `S11`, `S12`, `S15`, `S16`, `S17`, `S18` — accepted and fixed in tree. Every mitigation stays until
  0.5.4 ships. `S18` (our `F14`, filed the same day it was found) had both defects fixed the same
  day, which is the counter-example to `S14`'s lateness.
- `S10` — accepted, filed as upstream `RM46`; the granularity question is design work, not an
  unanswered report.
- `S14` — **settled, and half of it refused with a reason.** A `--no-ensembl` flag would assert
  something false, because the compiler has no branch that reaches the network at all; renaming a
  published parameter is major-only regardless. Our pin is therefore permanent rather than interim,
  and `F10` is closed. A refusal is an answer, and wording a guard as "until upstream fixes it" when
  upstream has declined is its own kind of stale.
- The registry's intake behaves the opposite way: no history file, and `S1` (our `F11`) genuinely
  still open. Absence of movement there means nothing has been answered.

`CLAUDE.md` §8 gained the history path, the id rule (`.claude/triage-state.sh --next` — ids are never
reused and the inbox being empty says nothing about what is taken; the next is `S19`), and the
instruction to re-read upstream's verdicts rather than trusting our own `Status:` lines, which go
stale silently because upstream answers in its own tree and nothing notifies us.

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
