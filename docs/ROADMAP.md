# Roadmap

Active-only, forward-only. One `## RMn — name` per **open** item. Shipped items
move to [ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) with their rationale; nothing is
deleted, only relocated.

---

## RM3 — signing is unwrapped, and the key handling is the reason to be careful

**Severity:** low · **Status:** open · **Owner:** unassigned

`keygen` / `sign` are CLI-only. `keygen` writes an unencrypted PKCS#8 key, which
is a bootstrap rather than a key-management system, so a tool that generates one
into a workspace on an agent's initiative is the wrong default. A `sign` wrapper
that takes an *existing* key path is the safer half and could land alone.

## RM4 — nothing verifies `enrich_module` or `registry_publish` end to end

**Severity:** medium · **Status:** open · **Owner:** unassigned

Every other tool is exercised against the real upstream packages by the suite,
and the read-only network tier was confirmed by hand against the live services.
These two are not: `enrich_module` needs a real enrichment run, and
`registry_publish` needs a token, a namespace and a module we are willing to
publish immutably.

The offline ceiling keeps the suite hermetic, so neither can be a normal test.
The shape that fits is a marked, opt-in integration run plus a dogfooding probe
that authors a small real module all the way through — which would also exercise
RM1's gap from the inside.

## RM6 — Semantic Scholar and arXiv are unreachable from this host, so two parsers are untested

**Severity:** medium · **Status:** open · **Owner:** unassigned

Both services return HTTP 429 to this machine's IP regardless of user-agent or
pacing — arXiv on a first request, with no prior traffic. So neither has a
captured payload under `assets/literature/`, and `parse_semantic_scholar` and
`parse_arxiv` are exercised only by the network-marked suite that does not yet
exist (RM4).

The tools behave correctly under the block — `results=null`, `rate_limited=true`,
and a warning that those sources are *unchecked* rather than empty — which is the
design working. But a parser with no test is a parser that will break silently
when the API shape moves.

Two ways out, and they are not exclusive: capture the fixtures from a host that
is not blocked, or set `S2_API_KEY` (Semantic Scholar's keyed pool is not the one
being throttled) and capture at least that half.

## RM7 — the literature sources have no `sources.csv` terms, upstream or here

**Severity:** medium · **Status:** open · **Owner:** unassigned · **Blocked upstream**

`enrich_literature` writes `source="pubmed"` into `literature.csv` and
`TERMS_BY_SOURCE` has no `pubmed`, so **every literature-enriched module already
warns** about a source the enricher itself introduced — and it is a warning, not
an error. Our tools add `europepmc`, `crossref`, `unpaywall`, `semanticscholar`
and `preprints` to the same gap.

We report it (`SourceLicenseNote` on every literature result) and refuse to fill
it, because `licensing.py` says the enricher is the only tier permitted to hold a
source convention, and because a fabricated licence string is worse than a
missing warning.

Filed upstream as `S10`, where the substantive point is that **a literature
source's terms are per-article, not per-source** — so a single `pubmed` row would
be wrong for any module quoting a CC-BY-NC article. Recorded here as **F8**.

## Idea book

Freeform, unscheduled, no commitment implied.

- A `module_diff` tool: two spec directories in, the authored rows that differ
  out. `module_signature` answers *whether* two specs differ but not *where*, and
  "diff the tables" is the standing advice whenever a digest moves without an
  intended content change.
- Surfacing `hints.REDUNDANCY_BEARING` as a resource rather than only as a field
  on `describe_table`, so an agent can read the whole list once instead of per table.
- A `check_publishable` tool that runs the local strict validate plus the
  identifier checks and returns one branchable verdict — the useful half of the
  upstream `would_publish` field, without the variant ceiling that makes the
  server-side version unusable on a large module.
