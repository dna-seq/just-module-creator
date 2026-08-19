# Roadmap

Active-only, forward-only. One `## RMn — name` per **open** item. Shipped and
deferred items move to [ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) with their
rationale; nothing is deleted, only relocated.

**An item belongs here only if the work is ours.** A gap whose fix lives in
`just-dna-format` / `-compiler` / `-enricher` / `-registry` is filed upstream as
an `S<n>` and tracked in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md) as an
`F<n>` — never as a roadmap item, because putting it here says we intend to build
something and invites a workaround where a note was owed. A probe belongs in
[dogfooding.md](dogfooding.md), not here.

---

## RM6 — two literature parsers have no fixture, so nothing tests them

**Severity:** medium · **Status:** open · **Owner:** unassigned

`parse_semantic_scholar` and `parse_arxiv` are exercised by nothing. Every other
parser has a real captured payload under `assets/literature/`; these two do not,
because both services answer HTTP 429 to this machine's IP regardless of
user-agent or pacing — arXiv on a first request with no prior traffic, confirmed
with plain `curl` outside the client.

The block itself is not a defect anywhere and not ours to fix. **The untested
parser is ours**, and a parser with no test breaks silently when the API shape
moves.

Two ways out, not exclusive: capture the fixtures from a host that is not
blocked, or set `S2_API_KEY` — Semantic Scholar's keyed pool is not the one being
throttled — and capture at least that half. Recorded as **F6** in
[dogfooding.md](dogfooding.md).

---

## RM9 — a module authored only through this server carries no check attestation

**Severity:** medium · **Status:** open · **Owner:** unassigned

Format 0.6 made `verification.json` a real surface: the registry projects a
`verification` block onto the module page, and a record says *the question was put*
rather than *the answer was clean*. The enricher writes those records from its
**CLI commands** — `check-identifiers` and `check-acmg` do it unconditionally, with
no flag, precisely so that "not run" and "ran and found nothing" stop reading alike.

The underlying functions do not, and the functions are what we call. So `close_module`
is the only thing on this surface that writes into `verification.json`, and a module
authored entirely through these tools shows nothing where a CLI-driven author's module
shows two records. That is the `F33` shape again — our own pin being what keeps an
author off a surface that exists.

It is not a missing upstream API: `identifiers.verification_records()` and
`verification.merge_records()` are both public, and `close_module` already proves the
write path works from here. What has to be decided first is a policy question, because
`tools/research.py` opens by promising that **no tool in it writes to a spec directory**
— a line that is currently true and load-bearing for how the read-only tier is
understood. Either the check tools move out of that module, or the promise is narrowed
to "writes no authored cell", which is upstream's own wording and is the narrower claim
that actually matters. Do not do this by quietly making the promise false.

---

## Idea book

Freeform, unscheduled, no commitment implied.

- A `module_diff` tool: two spec directories in, the authored rows that differ
  out. `module_signature` answers *whether* two specs differ but not *where*, and
  "diff the tables" is the standing advice whenever a digest moves without an
  intended content change.
- Surfacing `hints.REDUNDANCY_BEARING` as a resource rather than only as a field
  on `describe_table`, so an agent can read the whole list once instead of per table.

---

## RM10 — three tool answers restate a schema fact instead of generating it

**Severity:** medium · **Status:** open · **Owner:** unassigned

Each is a hardcoded schema fact, which §2 forbids for the reason all three show.

- `authoring._SUBJECTS["copynumbers.csv"]` emits `modifier_cn`; deprecated at 0.6.
- `list_tables().sidecars` is a literal four; omits licensing + the three 0.6 facts.
- `authoring.py:59` + `create-module/SKILL.md:708` describe studies.csv pre-RM47.

Derive all three from the models. `modifier_copy_number` replaces `modifier_cn`,
`specfiles.FACT_CSVS` is the sidecar roster, and RM47 moved studies.csv's columns.

## RM11 — no route answers a machine-produced table's columns

**Severity:** medium · **Status:** open · **Owner:** unassigned

`describe_table` refuses the six fact tables and `resolution.csv` — `DRAFTABLE`
covers authored kinds only. So "ask the tool, never memory" has a hole exactly
where an author reads a sidecar they must not hand-finish. The dossiers cover it
in prose; a tool answer would not drift.

## RM12 — `enrich_gwas` is wrapped by no MCP tool

**Severity:** low · **Status:** open · **Owner:** unassigned

The enricher publishes it; `gwas_effects.csv` is reachable only via the CLI.
Extended tier by the cost rule — a corpus sizes it.

## RM14 — `provenance.json` is recognised by the registry and by nothing here

**Severity:** low · **Status:** open · **Owner:** unassigned

In `specfiles.RECOGNIZED_SPEC_FILES`, survives a storage round-trip, and no tool
or dossier covers it. Named in `module-tables/references/LAYOUT.md` only.
