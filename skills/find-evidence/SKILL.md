---
name: find-evidence
description: >-
  Find, verify and read the papers behind a row — search PubMed, Europe PMC, Semantic Scholar and the preprint index, confirm a PMID names the paper you meant, find a legal open-access copy, reach the supplementary tables a GWAS paper's per-variant numbers actually live in, and decide what may honestly be quoted.
  Triggers: "find papers", "what is the evidence", "search the literature", "is this PMID real", "which paper is this", "get the full text", "can I quote this", "find a study for this variant", "provenance_quote", "open access", "preprint", "citations", "supplementary table", "supplementary data", "additional file", "the rsIDs are not in the text", "MOESM", "ESM", "the paper only gives a summary", "where are the effect sizes", "download the xlsx", "the source has no rsID", "only a variant name", "HGVS", "what allele is this", "c.448delA", "IVS2+1G>A", "allele registry", "CAID", "which transcript", "ref and alt look swapped".
---

# Finding the evidence behind a row

This skill covers getting from a question — *what is known about this variant?* — to citations and
numbers you can defend. Authoring the module around them is
[module-curate](../module-curate/GUIDE.md); this is the step in the middle of that stage,
where `state`, `weight`, `effect_size`, `conclusion` and every `studies.csv` row get decided.

Two things this never does. It does not judge whether a paper supports your claim — no tool here
returns that verdict. And it does not write a cell. It finds and it fetches; the
reading and the deciding are the authoring work.

**You are a legitimate reader.** `fetch_fulltext` hands you the article, so reading it is a reading
that happened, and a passage you located in it may be quoted. What is required is not abstention but
**attribution** — see [`references/QUOTING.md`](references/QUOTING.md), which is the part of this
skill most likely to be got wrong.

---

## Read this first: existence is not identity

**PMIDs are densely allocated across roughly 1–40,000,000.** So a plausible-looking 8-digit number
you recall is almost always a *real record for a different paper*, and `pmid_exists: true` comes back
for it. Fabrication is a failure of **identity**, and no existence answer can catch it.

Only a title settles identity. Both of these report one:

```
lookup_citation(pmid="11788828")                   # title, journal, year, first_author for one id
literature_search(pmids=["11788828", "10748118"])  # the same, in bulk, across services
```

Compare each title against the paper you meant. **A title that disagrees means the id is wrong,
however true `pmid_exists` is.** A `null` title means the question was not put — offline, or the
service did not answer — and an unasked question is never a passed check. An id PubMed does not know
comes back as an `error` finding; do not write those.

That still leaves one thing a title cannot do: tell you which paper you *should* be citing. So the
rule stays:

> **Take every PMID you write from a search result in this session. Never from memory.**

---

## The loop

```
search  ──▶  read  ──▶  decide  ──▶  author  ──▶  verify
```

**Verify is separate and comes last** because it checks a different thing. Searching finds
candidates; `enrich_literature_pass` checks that what you *wrote down* resolves — that the PMIDs
exist, that your authored DOI agrees with the registry's, that your quotes appear in the text. It
cannot tell you the evidence was any good.

```
literature_search(gene="MCM6", trait="lactase persistence")   # candidates, with titles
lookup_open_access(pmid="11788828")                           # where may I read it, on what terms
fetch_fulltext(pmid="11788828")                               # the document — never a passage
paper_citations(...)                                          # a corpus sizes it. replicated, or one paper?
enrich_literature_pass(spec_dir="spec")                       # a corpus sizes it. after you author the rows
```

**All five are always there.** The last two used to need `JMC_MODE=extended` and be absent without
it, so on a default install the verify step of this loop could not be run at all; the tier went in
0.21.0. What is still true is the **cost**: `paper_citations` follows a citation graph as large as
the paper is cited, and `enrich_literature_pass` spends at least one request per citation in the
module, so on a module with hundreds of studies it is a long run rather than a lookup. Weigh it,
then run it.

`refresh_sidecar` reaches the same pass through a different door — naming `literature.csv` re-derives
that table — and it warns rather than refuses. [`module-refresh`](../module-refresh/GUIDE.md) owns the tool.

---

## Which source answers which question

| Source | Good for | Cannot say |
|---|---|---|
| **pubmed** | The clinical-genetics spine. It is where PMIDs come from, and `studies.csv` requires one. | Nothing about full text. |
| **europepmc** | Search plus abstracts plus open-access full text in one place. Also the preprint index (`SRC:PPR`). | **It cannot say "does not exist."** It omits ids it does not know with no error marker, so a miss is *not retrievable*, never *absent*. |
| **semanticscholar** | The citation graph — who cited this, what it cited. How you ask whether a finding was replicated. | Coverage is uneven for older clinical literature. |
| **preprints** | Europe PMC's preprint index plus arXiv. Real for PGS and methods work. | Not peer-reviewed, and **no PMID**. |
| **openalex** | The broadest index here, 250M+ works, and it returns a PMID, a DOI, open-access status and a citation count in one hit. Good when PubMed's clinical framing is too narrow — population genetics, methods, anything not indexed as clinical. | Its abstracts are reconstructed from an inverted index, so read them as a gist rather than quoting them. Never quote from one. |
| **crossref** | DOIs, and the registered metadata behind them. Worth asking precisely because it is DOI-first: a DOI is the handle that reaches Unpaywall, so a hit here can become a legal full text that a PMID-only search would never have found. | No full text and **no open-access verdict at all** — `is_open_access` comes back null, which is unknown and not "closed". |
| **unpaywall** | DOI → legal open-access copies, **and the article's licence**. | Not a search engine — it takes a DOI you already have. |
| **ClinGen Allele Registry** (`lookup_allele_identity`) | What allele an **HGVS expression** names, when a source published a name and no identifier. Also the direction test: it rejects the expression whose reference base is wrong. | Which reading a curator *meant*, when two spellings name different alleles. It answers about expressions you constructed; constructing them is [`IDENTITY_FROM_A_NAME.md`](references/IDENTITY_FROM_A_NAME.md). |

`sources` narrows which are asked. `JMC_LITERATURE_SOURCES` is the deployment ceiling and a per-call
`sources` can only narrow it further, never widen it.

### Read `sources` before you believe an empty result

Every search reports what each source did:

- `results: 5` — it answered, and found five.
- `results: 0` — it answered, and found nothing. **This is evidence.**
- `results: null` — it **could not answer**: timed out, rate-limited, blocked. This is *not*
  evidence, and `queried: false` means it was never asked at all.

An empty `papers` list with two sources at `null` means most of the literature was never consulted.
Do not report "no studies found" on the back of that.

**Do not re-run a search to get more results.** These are polite-pool guests on shared rate limits —
the same NCBI budget the enricher uses. Raise `limit` instead, or narrow the query.

---

## What you may write, and from where

| Column | Take it from | Never |
|---|---|---|
| `pmid` | A search result in this session. | Memory. |
| `doi` | **Leave it empty**, or read it off the paper itself. | The search result. It arrives in `withheld` with a refusal, because `enrich_literature_pass` compares your DOI against the registry's — filling it from the registry makes that check compare a source with itself. Leaving it empty costs nothing: the registry DOI is recorded in `literature.csv` regardless. |
| `population` | The paper's methods section, verbatim. | An assumption that it generalizes. See below. |
| `study_design`, `p_value`, `effect_size`, `effect_measure` | The paper's results, transcribed. | An abstract's summary when the number is in a table. |
| `conclusion` | Your own reading, hedged where the biology is. | The abstract's own wording, copied. |
| `provenance_quote` / `provenance_regex` | The passage **you** located, verbatim, for **this row's** claim. | The article's **title**. A passage a tool picked for you. |

### `effect_measure` and `p_value`

`effect_measure` is an **open recommended** vocabulary — `OR`, `HR`, `RR`, `beta`, `log(OR)`, `NR` —
so an unlisted measure is allowed, but say which one it is. An odds ratio and a beta are not
interchangeable, and a module that mixes them silently is unreadable downstream.

`p_value` is free text (`"3.2e-08"`, `"<0.001"`, `"NS"`). `p_value_num` is a real number bounded
`(0, 1]` and **redundancy-bearing** — the compiler cross-checks the two against each other, so
deriving one from the other makes the check vacuous. Transcribe both from the paper or fill neither.

### Population is where modules overreach

`studies.csv` has a `population` column because an effect estimated in one ancestry frequently does
not transfer. Lactase persistence is the standard example: `rs4988235` explains the trait in
Europeans and largely does not in East Africa, where different variants do the same job. A module
that carries a European odds ratio and a `conclusion` phrased as though it were universal is wrong
for most of the world's genomes, and nothing in the compile gate will catch it.

Write the population the study measured. Hedge the `conclusion` to match.

**If a GWAS pass has run, the answer is already in the module.** `gwas_effects.csv` carries the
Catalog's own `ancestry` per study, and `study_facts(spec_dir)` reports it joined by `pmid` — so
`population` rarely needs to be reconstructed from the paper by hand. It is surfaced and never
written for you, because the Catalog frequently answers with several cohorts at once
(*"African American or Afro-Caribbean, European, Hispanic or Latin American"*) and which of them
applies to a given row is yours to decide.

**What must not go in the column is a citation.** A published module carries
`"Nagel M et al. — GWAS Catalog GCST006941"` in every `population` cell — a provenance breadcrumb
written where an ancestry belongs, by an author who had the ancestry in the next file over. The
accession belongs in `studies.csv`'s own identifier columns; `population` is the cohort.

---

## What may honestly go in `provenance_quote`

**A `provenance_quote` is a passage you located, verbatim, for this row's claim — never the article's
title.** That distinction has a measured cost: the old rule against machine-located quotes did not
produce human-read quotes, it produced **3668 published rows carrying the title**, which passes
`quotes_found` every time because a title is always in its own fulltext. Full coverage, witnessing
nothing.

**You are a legitimate reader.** `fetch_fulltext` hands you the article, so the reading happened. What
is required is attribution, not abstention: locate it, quote it verbatim, and record who located it in
`curator`. Never write a passage that is not verbatim in the retrieved text.

**Read [`references/QUOTING.md`](references/QUOTING.md) before filling one.** It carries the four
rules and the sub-cases that decide real rows: the four kinds of honest empty cell and the fifth the
counter cannot see, what to do when an article names your variant but reports a different trait (the
most valuable thing a search can produce), what `curator` does and does not record, and when
`quotes_found` stops being independent evidence at all.

---

## Copyright: free to read is not free to reuse

**Free to read is not free to reuse, and the terms are per ARTICLE, not per source.** There is no
licence you can state once for "PubMed" that is right for every paper it indexes — which is why
`lookup_open_access` exists and why no table here could replace it.

The trap worth knowing before you quote anything: a `null` licence (bronze) is free to read on the
publisher's site with **no reuse grant at all**, and `other-oa` on every location is the same thing
wearing a label. One article with unclear terms drops the whole module's `commercial_use` and
`redistribution` to `null` on its published card.

**[`references/LICENSING.md`](references/LICENSING.md)** has the licence values and what each permits,
which `licensing.csv` row to write when you read by hand and why blank means *unknown* and never
*false*, and the four routes when there is no legal copy — plus why there is no fifth.

---

## Preprints

**Some preprints have a PMID, so check the record and do not assume the class.** bioRxiv and medRxiv
postings are indexed in PubMed under the NIH preprint pilot and get a real PMID, often a PMCID
(`41427385` has both); an arXiv posting typically has neither, which is where the old rule came from.
A preprint carrying a PMID *can* ground a `studies.csv` row — the schema requires a PubMed token and
it has one. `literature_search`'s warning that preprints *"carry no PMID"* fires on results that do:
read the `pmid` field, not the warning (`F28`).

What remains true, and is the part that matters: **a preprint is not peer reviewed.** Grounding a row
on one is legitimate and must be said out loud in the `conclusion`, because a reader cannot tell from
a PMID alone. And two further consequences worth planning for:

- **Check for a published version before you author from it** — see [`module-start`](../module-start/GUIDE.md)'s "is the
  copy you were handed still the current one?". Review changes numbers and sometimes conclusions.
- **Expect `quotes_found: null`.** A preprint frequently has no retrievable OA full text even when it
  has a PMCID, so quotes on it come back unchecked rather than confirmed. That is not a failure and
  not a reason to drop the quote — it is the check honestly reporting it could not run.

---

## What is deliberately not here

- **No Sci-Hub or paywall bypass.** This repo's compile gate exists to record what a source's licence
  permits. A bypass has no term to record, so it would manufacture exactly the dishonest provenance
  the gate refuses — and this ships to other people as a plugin.
- **No Google Scholar.** No API, scraping violates its terms, and it IP-blocks. Upstream evaluated
  and rejected it.
- **No PDF parsing.** Open-access full text comes as JATS XML from Europe PMC, which is better
  structured than a PDF anyway. For a paper available only as a PDF, `lookup_open_access` gives you
  the link and you read it yourself.
- **No combined relevance score.** Each source's own rank is reported under its own name. A merged
  score would be a convention with no source behind it, and it invites citing the top hit without
  reading it.

---

## When something looks wrong

- **Everything returns nothing.** Check `sources` for `results: null` before concluding anything.
- **`literature_search` refuses outright.** `JMC_OFFLINE` is set. There is no offline literature
  snapshot and there will not be one — once `literature.csv` is written it *is* the pin.
- **Unpaywall reports `queried: false`.** No contact address. Set `JUST_DNA_CONTACT_EMAIL`. It is not
  invented for you, because an invented address misattributes the traffic to a real person.
- **Semantic Scholar returns 429.** Measured 2026-08-20: its unauthenticated pool is one pool shared
  by every anonymous caller worldwide, so the throttle is **other people's traffic, not your pacing**
  — and it is endpoint-specific, `paper/search` shedding load while a lookup by id answers normally.
  The response carries **no `Retry-After` and no `X-RateLimit-*`**, so nothing can pace against it;
  just retry, spaced. `S2_API_KEY` gets you a dedicated 1 req/s and is the real fix.
- **arXiv returns 429.** Rare now. It had a genuine incident in early 2026 that its maintainers
  fixed, and this host reads clean since. Honour the 3-second spacing the client already enforces and
  retry; do not conclude the host is blocked without re-probing, which is the mistake `F6` records.
- **A PMID resolves but the title is wrong.** That is the failure this skill opens with. Discard it
  and search for the paper properly.
