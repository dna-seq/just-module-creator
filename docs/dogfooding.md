# Dogfooding — open findings

Open quirks, bugs and UX gaps found by **using the shipped surface for real
work**, not by testing it. Read before touching the tool surface.

Findings carry stable `F#` IDs and **move** between files rather than being
duplicated: resolved here → [previous_issues.md](previous_issues.md); blocked on
an upstream change → [just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).
One legitimately appears in two files when we have mitigated it and upstream
still owes the fix.

Layer 1 (the suite) proves the code does what it was told. This asks whether it
is usable, and what is missing.

---

## F6 — two of five literature sources refuse this host, and the tool is right to say so

**Found:** 2026-08-11, capturing fixtures · **Severity:** medium ·
**Status:** open · **Roadmap:** [RM6](ROADMAP.md#rm6--semantic-scholar-and-arxiv-are-unreachable-from-this-host-so-two-parsers-are-untested)

Semantic Scholar and arXiv both answer HTTP 429 from this machine regardless of
user-agent, arXiv on a *first* request with no prior traffic — so it is an IP
block, not our pacing. Confirmed with plain `curl` outside the client.

Reported here rather than routed around because it is the best available
evidence that the tri-state design earns its keep. A live `literature_search`
returns `results=null` and `rate_limited=true` for those two, plus a warning that
their part of the literature is **unchecked, not empty** — while PubMed and
Europe PMC answer normally. Had the model used `0`, the same call would have
read as "no preprints exist on this subject", which is a conclusion an author
would act on.

The cost is real: `parse_semantic_scholar` and `parse_arxiv` have no committed
fixture and therefore no test.

## F7 — a `limit` was spent entirely on whichever source was asked first

**Found:** 2026-08-11, first live search · **Severity:** medium ·
**Status:** resolved same day, kept here as the reason the ordering rule exists

The first working `literature_search` asked four sources with `limit=5` and
returned five PubMed papers. Europe PMC had answered with five of its own and
none of them appeared: the merge preserved first-appearance order, so source one
filled every slot.

Nothing was broken and every count in `sources` was accurate — which is what made
it easy to miss. It only showed up because the live run printed `found_in` per
paper and every row said `['pubmed']`.

Merge now interleaves by each source's own rank, so every source's top hit
outranks anyone's second. Ties break on first appearance, so the order stays
deterministic.

**Why it stays in this file rather than moving to previous_issues.md:** the
finding is not the bug, it is that asking several sources can silently degrade
into asking one, and nothing in the result said so. A future federated tool wants
the same guard.

## F8 — the literature sources have no recordable licence terms

**Status:** mitigated here, open upstream. Full entry in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md); filed as
`S10`.

Listed here too because the mitigation is reporting only: each literature result
carries a `SourceLicenseNote` naming the row the author owes, and a module still
compiles green with the terms unrecorded because it is a warning.

It briefly had a roadmap item (`RM7`), which was wrong — there is no work here for
us to do. Removed on 2026-08-11 during a sweep for upstream gaps this repo had
absorbed as its own.

## F9 — `lookup_citation` cannot detect a fabricated PMID, and our docs said it could

**Found:** 2026-08-11, designing the search tool · **Severity:** high ·
**Status:** mitigated here, open upstream (`S12`)

`CitationHint` carries `pmid_exists`, `doi`, `pmcid`, `open_access` — and no
title, journal or year. PMIDs are densely allocated across roughly 1–40,000,000,
so a recalled 8-digit number is almost always a real record for a **different**
paper, and `lookup_citation` answers `pmid_exists: true` for it.

Both our skill and the tool docstring said "never invent a PMID — verify each one
with `lookup_citation`", which is a rule the surface could not enforce.
Fabrication is a failure of *identity*; that call only answers existence.

This is the finding that put `literature_search` in the **essentials** tier
rather than extended: discovery is the missing half of an anti-fabrication
promise the default surface had already made. `literature_search(pmids=[...])`
reads titles back, and both docs now say to take every PMID from a search result
rather than from memory.

---

## Probes not yet run

Recorded so the gaps in *this* file are visible too, per the completeness rule.

- **Author a real module end to end and publish it.** Everything up to
  `compile_module` has been exercised on a real spec; `enrich_module` and
  `registry_publish` have not ([RM4](ROADMAP.md)). This probe would also hit F1
  from the inside rather than by inspection.
- **A binning module.** Every probe so far has been `variants.csv` or
  `pharm_variants.csv`. The bounds rules are the densest part of the domain — two
  kinds with opposite endpoint conventions — and nothing has tested whether the
  tools make them followable. Per "pick the probe where the design generalized
  from one case", the case to use is one with two bins sharing an endpoint.
- **`enrich_module` and `registry_publish`, end to end against the live services.**
  Was tracked as a roadmap item until 2026-08-11; it is a probe, not a
  deliverable. The offline ceiling keeps the suite hermetic, so neither can be a
  normal test — what fits is a marked, opt-in integration run alongside authoring
  a small real module all the way through. `registry_publish` needs a token, a
  namespace and a module we are willing to publish immutably; the new
  `published.json` receipt is what makes the result inspectable afterwards.
- **A module with two of something the examples show one of.** The worked example
  throughout is a single-gene, single-rsID module. A paralogous rsID mapping to
  several loci, or one gene carrying two variants with different thresholds, is
  where a key that works for one instance stops working.
