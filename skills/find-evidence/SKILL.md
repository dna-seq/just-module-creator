---
name: find-evidence
description: >-
  Find, verify and read the literature behind a just-dna row — search PubMed, Europe PMC,
  Semantic Scholar and the preprint index, confirm a PMID names the paper you meant, locate a
  legal open-access copy, and decide what may honestly be written into studies.csv from what
  you read. Use when looking for evidence for a variant, gene, trait or drug response, when you
  have a claim and need the citation, when a PMID needs checking against the paper it should
  name, when you need an article's full text, or when deciding whether a quoted passage may
  travel inside a published module. Triggers: "find papers", "literature search", "what is the
  evidence for", "PMID for", "is this variant supported", "find the study", "open access",
  "read the paper", "fulltext", "preprint", "bioRxiv", "medRxiv", "arXiv", "cite this",
  "provenance quote", "studies.csv", "is this citation real", "has this been replicated".
---

# Finding the evidence behind a row

This skill covers getting from a question — *what is known about this variant?* — to citations and
numbers you can defend. Authoring the module around them is
[create-module](../create-module/SKILL.md); this is the step in the middle of its **curate** phase,
where `state`, `weight`, `effect_size`, `conclusion` and every `studies.csv` row get decided.

Two things this never does. It does not judge whether a paper supports your claim — no tool here
returns that verdict, at any tier. And it does not write a cell. It finds and it fetches; the
reading and the deciding are the authoring work.

---

## Read this first: existence is not identity

**PMIDs are densely allocated across roughly 1–40,000,000.** So a plausible-looking 8-digit number
you recall is almost always a *real record for a different paper*, and `lookup_citation` answers
`pmid_exists: true` for it. Nothing upstream returns a title from that call, so it cannot tell you
whether the id names the paper you meant.

That makes the obvious-sounding rule — *"verify every PMID before writing it"* — unenforceable if
`lookup_citation` is all you use. The working rule is stronger:

> **Take every PMID you write from a search result in this session. Never from memory.**

To check ids you already have, read their titles back:

```
literature_search(pmids=["11788828", "10748118"])
```

The result carries titles. Compare each against the paper you meant. An id PubMed does not know
comes back as an `error` finding — do not write those.

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
paper_citations(...)                                          # replicated, or one paper?
enrich_literature_pass(spec_dir="spec")                       # after you have authored the rows
```

---

## Which source answers which question

| Source | Good for | Cannot say |
|---|---|---|
| **pubmed** | The clinical-genetics spine. It is where PMIDs come from, and `studies.csv` requires one. | Nothing about full text. |
| **europepmc** | Search plus abstracts plus open-access full text in one place. Also the preprint index (`SRC:PPR`). | **It cannot say "does not exist."** It omits ids it does not know with no error marker, so a miss is *not retrievable*, never *absent*. |
| **semanticscholar** | The citation graph — who cited this, what it cited. How you ask whether a finding was replicated. | Coverage is uneven for older clinical literature. |
| **preprints** | Europe PMC's preprint index plus arXiv. Real for PGS and methods work. | Not peer-reviewed, and **no PMID**. |
| **unpaywall** | DOI → legal open-access copies, **and the article's licence**. | Not a search engine — it takes a DOI you already have. |

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
| `provenance_quote` / `provenance_regex` | The passage **you** located. | Anything a tool handed you. |

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

---

## The quote tautology, in full

`fetch_fulltext` returns a document. It does not return the best-matching passage, a suggested
quote, or a search within the text — and it never will.

`enrich_literature_pass` checks `provenance_quote` against the *same* Europe PMC full text a tool
would have taken it from. So a quote lifted from the tool's output makes `quotes_found` confirm
itself. But the sharper problem is what `provenance_quote` means: it records that **a curator read
the paper and located the claim in it**. A passage a machine pulled out of a document the machine
fetched asserts a reading that never happened. That is a false claim of provenance, not merely a
vacuous check.

**And the honest cost, which you should weigh before using `fetch_fulltext` at all:** once you have
read the full text through this tool, `quotes_found` on that row is no longer independent evidence.
It has become a citation-pairing check. Still useful — it catches a quote written against the wrong
PMID — but it no longer tells anyone the claim is in the paper.

If you want `quotes_found` to mean the stronger thing, read the paper somewhere else and write the
quote from that reading.

### `quotes_unchecked` is not a failure

It means there was nothing retrievable to check against. And an abstract *miss* is not a verdict:
Europe PMC returns abstracts for paywalled records, so a claim absent from the abstract may well be
in the paper.

---

## Copyright: free to read is not free to reuse

This is the part nothing else in the toolchain covers, and it decides whether a module is publishable.

`lookup_open_access` returns each location's `license`. The values that matter:

- **`cc-by`** — reuse with attribution, including commercially. Quoting is fine.
- **`cc-by-nc`** — no commercial use. A quote from this article inside a module you intend to
  **sell** is a problem, and it is a problem in your module's *annotation* layer, where
  `commercial_use=false` actually bites.
- **`null` (bronze)** — free to read on the publisher's site, with **no reuse grant at all**. The
  most common trap: it looks open and is not.

A short located quote is a pointer to where a claim lives. A copied abstract pasted into
`conclusion` is a reproduction of someone's text. Write your own sentence.

These terms are **per article**, not per source. There is no licence you can state once for "PubMed"
that is right for every paper it indexes — which is exactly why `lookup_open_access` exists and why
no table on this side could replace it.

---

## `sources.csv` when you read by hand

`sources.csv` must cover every source your fact tables cite, and **a missing row is a warning, not
an error**, so a module ships without one unnoticed.

Every literature result carries a `licensing` block naming what you now owe. Nothing writes those
rows for you, on purpose: `declared_use` is a licence position only you can take, and a fabricated
licence string would be worse than the missing warning.

Two rows, not one, when you quote:

1. `source: pubmed`, `layer: literature` — the metadata you searched.
2. `layer: annotation` carrying the **article's** licence — if any of that article's text ended up
   in a cell.

Upstream's `TERMS_BY_SOURCE` has no entry for any literature service, so `stateable_upstream` comes
back `false` for all of them. That is a known gap, filed upstream as `S10`; until it is closed, the
row is yours to write and the terms are yours to read.

---

## Preprints

A preprint has **no PMID**, and `pmid` is required on every `studies.csv` row. So a preprint cannot
ground a study row on its own, full stop — that is a schema fact, not a policy preference.

It can still inform a hedged `conclusion`, and it is worth knowing about. If the preprint has since
been published, the published version has a PMID and that is the one to cite.

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
- **Semantic Scholar or preprints keep returning 429.** The anonymous pools are shared and small. Set
  `S2_API_KEY` for Semantic Scholar; for the rest, ask for fewer sources at a time.
- **A PMID resolves but the title is wrong.** That is the failure this skill opens with. Discard it
  and search for the paper properly.
