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
itself — it passes by construction and proves nothing.

**The axis is where the text came from relative to the checker — not who did the reading.** You are
an author here, and an agent reading a paper is a reading that happened. What must not happen is
sourcing the quote and its answer key from the same retrieval.

| you read | quote it? | what `quotes_found` then proves |
|---|---|---|
| a PDF or copy the author supplied | **yes** | the passage is in the paper that PMID names |
| a copy you obtained outside this session's `fetch_fulltext` | **yes** | same |
| `fetch_fulltext` output for that same PMID | **no** | nothing |

**The honest cost, worth weighing before calling `fetch_fulltext` at all:** once you have read the
full text through this tool, `quotes_found` on that row is no longer independent evidence. It has
degraded to a citation-pairing check — still useful, since it catches a quote written against the
wrong PMID, but it no longer tells anyone the claim is in the paper. If you want the stronger thing,
read the paper somewhere else and write the quote from that reading.

**Then read the counters as three-valued.** `quotes_found` is `null` when no full text could be
retrieved and `0` when one was read and the passage was not in it. A preprint with no OA full text
returns `null` for every quote on it: **unchecked, not refuted**, and not a reason to delete them.
`quote_source` says how far the search reached — a phrase found in an abstract is in the paper, while
a phrase absent from a 200-word abstract says nothing about the body.

> **Upstream calls these columns `ATTESTATION_BEARING` and glosses them "the cell asserts that a
> HUMAN read something".** That is correct as a *provider* rule — no lookup tool may write these
> cells, and none does — and it is not the authorship rule, in a product whose `Contribution` model
> ships an `ai` author kind and whose `curator` field routinely holds an agent id. Filed upstream.
> Until it is answered: never fill these from a lookup, and do write what you read.

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

## `licensing.csv` when you read by hand

`licensing.csv` must cover every source your fact tables cite, and **a missing row is a warning, not
an error**, so a module ships without one unnoticed. The file was called `sources.csv` before format
0.6; both spellings still read, only the new one is created, and a module carrying **both** is
refused rather than merged.

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

**Some preprints have a PMID, and the tooling currently says otherwise.** bioRxiv and medRxiv
postings are indexed in PubMed under the NIH preprint pilot, so they get a real PMID and often a
PMCID: `41427385` is a bioRxiv posting with both. A preprint from the arXiv index typically has
neither, and that is where the old rule came from.

So the honest statement is: **check the record, do not assume the class.** A preprint result carrying
a PMID *can* ground a `studies.csv` row — the schema requires a PubMed token and it has one.

> `literature_search` emits a warning reading *"Some results are preprints: not peer-reviewed, and
> they carry no PMID, so they cannot ground a studies.csv row"* — and it fires on results that do
> carry one. Read the `pmid` field, not the warning. Filed as `F28`.

What remains true, and is the part that matters: **a preprint is not peer reviewed.** Grounding a row
on one is legitimate and must be said out loud in the `conclusion`, because a reader cannot tell from
a PMID alone. And two further consequences worth planning for:

- **Check for a published version before you author from it** — see the create-module skill's "is the
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
- **Semantic Scholar or preprints keep returning 429.** The anonymous pools are shared and small. Set
  `S2_API_KEY` for Semantic Scholar; for the rest, ask for fewer sources at a time.
- **A PMID resolves but the title is wrong.** That is the failure this skill opens with. Discard it
  and search for the paper properly.
