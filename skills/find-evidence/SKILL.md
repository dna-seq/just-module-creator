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
[module-curate](../module-curate/SKILL.md); this is the step in the middle of that stage,
where `state`, `weight`, `effect_size`, `conclusion` and every `studies.csv` row get decided.

Two things this never does. It does not judge whether a paper supports your claim — no tool here
returns that verdict, at any tier. And it does not write a cell. It finds and it fetches; the
reading and the deciding are the authoring work.

**You are a legitimate reader.** `fetch_fulltext` hands you the article, so reading it is a reading
that happened, and a passage you located in it may be quoted. What is required is not abstention but
**attribution** — see [what may honestly go in `provenance_quote`](#what-may-honestly-go-in-provenance_quote),
which is the part of this skill most likely to be got wrong.

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
paper_citations(...)                                          # EXTENDED. replicated, or one paper?
enrich_literature_pass(spec_dir="spec")                       # EXTENDED. after you author the rows
```

**Two of those five are extended-tier** (`JMC_MODE=extended`) and are simply absent from a default
install: `paper_citations` and `enrich_literature_pass`. So on a default server the verify step of
this loop **cannot be run at all**, and `literature.csv` stays at whatever the last run wrote —
which for a module you did not author yourself may be nothing. The CLI equivalent is
`just-dna-enricher literature <dir>`; reaching for it is stepping outside the MCP surface, so say so
when you do. The same applies to `refresh_sidecar`, the tool for re-deriving a sidecar without
losing curation: extended.

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

---

## What may honestly go in `provenance_quote`

`fetch_fulltext` returns a document. It does not return the best-matching passage, a suggested
quote, or a search within the text — and it never will, because *which* sentence supports a row is a
judgement about that row's claim and only you have read the row.

Everything after that is yours to write, and there are four rules.

### 1. It must be a passage, not a property of the article

**Never the title.** A title occurs in its own fulltext, always, so `quotes_found` matches it every
time and the module reports quote coverage while establishing nothing. It is also obtainable from
`esummary` without retrieving a word of the article, which is the one thing the column exists to
witness.

The general signature, and it is worth checking your own work against: **one identical string
across every row citing a PMID is not a located passage.** A real passage varies with the claim,
because different rows cite the same paper for different findings. Measured on the four published
`antonkulaga/*` modules — 3668 rows, 81 PMIDs, exactly one distinct quote per PMID, and every one of
them the article's title verbatim (`F42` / upstream `S54`). That is what a rule against
machine-located quotes produced when it met an author who needed the column filled.

### 2. Choose a grain and hold it

`studies.csv` rows are one per `(rsid, pmid)` at their finest. Before quoting, decide what a quote
is *for* on this module and write the choice down:

- **per `(pmid, rsid)`** — the passage must identify this row's own variant. Strictest, and the only
  one that makes the quote evidence *for this row*. Choose it by default.
- **per `(pmid, trait)`** — a passage supporting the trait-level finding, repeated over the rows
  sharing it. Weaker, and if a paper contributes rows for one trait only it collapses into rule 1's
  failure shape. Say so if you use it.

The choice matters most on GWAS. A catalog-derived module cites a paper for a per-variant
association the paper's *prose* may never state: measured on `aggression_anger`, none of the 65
rsIDs drawn from PMID 29500382 appears anywhere in that article's retrievable text, because the
associations live in its supplementary data and downloadable summary statistics. `fetch_fulltext`
returns the JATS body and no supplementary file, so for those rows there is nothing in reach to
quote — and the honest cell is empty.

### 3. An empty cell is a result, and there are four kinds

Do not stretch a passage to fill a row, and do not invent one. Record which kind of empty it is,
because they are not the same claim:

- **read and not found** — the fulltext was retrieved and the variant is not in it. Says something.
- **unchecked** — no fulltext was retrievable (`text_source: abstract`, or `null`). Says nothing.
  An abstract miss is not a verdict.
- **named, but for a different claim** — see rule 3b. Says a great deal, and it is not about quoting.
- **quotable, but the licence is unclear** — a judgement call; see the licensing section below. The
  measured case kept the quote and recorded the rights as unknown.

`quotes_found` mirrors the first two: `null` when nothing could be checked against, `0` when a text
was read and the passage was not in it. Neither is a failure and neither is a reason to delete a
quote.

### 3b. If the article names the variant but reports a different trait, STOP

This is the most valuable thing looking for a passage can produce, and it is worth going slowly when
it happens. The article names your row's variant — so the row looks well-cited — but the passage is
about a different phenotype, and the numbers in it do not match the numbers in your row.

The measured case: four rows citing PMID `34054130` for *"Worry too long after an embarrassing
experience"*. The article names all four rsIDs, in a table of hits for **sociability**, at p-values
that differ from the module's by orders of magnitude, and contains no analysis of that item at all.

**Do not quote it.** Attaching a real sentence to an assertion the article does not make is worse
than an empty cell: it converts an unverified row into an apparently-witnessed wrong one. Leave the
quote empty, record what you found, and put the row in the decision list — `trait_efo_id`, `p_value`
and `conclusion` are authored values and none of them is yours to change on this evidence.

Then read the cheap tell: **compare your row's `p_value` against the paper's own number.** Agreement
to one significant figure is a good sign the row and the passage are about the same result; an order
of magnitude apart usually means the row came from a different analysis, a different accession, or a
different paper.

### 3c. When the variant is named only inside a table

Common on GWAS papers, and the flattened JATS text keeps tables as runs of whitespace-separated
cells. A single table row is a legitimate `provenance_quote`: it is verbatim, it matches, it varies
per row so it cannot recreate the repeated-string shape, and it carries the variant, its alleles, its
effect and its p-value — which is more than most prose sentences do.

The honest cost is that the column is documented as *human-legible*, and a table row is legible only
to somebody holding the paper. Say so in the module's README or log. It is still far better than an
empty cell and incomparably better than a title. **Extract it with a regex against the retrieved
text rather than retyping it** — these tables are full of non-breaking spaces and en-dashes, and a
retyped span is a fabricated one.

### 4. Record who located it — and know where that record does and does not go

There is **no per-row attributor**: `VariantRow` has `curator`, `StudyRow` has nothing (`F43` /
upstream `S55`). So the whodunit has to go somewhere else, and the three places differ in what they
survive:

| Where | Grain | Travels with the module? |
|---|---|---|
| `module_spec.yaml: authorship` (`Contribution`: `who`, `role`, `kind`) | per **version** | yes — `manifest.authorship` |
| `provenance.json` (`ProvenanceItem.rationale`, keyed by `variant_key`) | per **variant** | yes — stored, and summarised into `manifest.provenance`; **not** carried by a registry contract `upgrade` |
| `logs/*.log` | per **run**, free text | yes — `manifest.logs`; **not** carried by an `upgrade` |

Verified by publishing a remediated module and reading the manifest back: all three survive a
publish. None of them is per `(row, quote)`, which is the grain the work actually has. State that
limit to the author rather than designing around it.

### The cost of using `fetch_fulltext`, stated rather than used to refuse

`enrich_literature_pass` checks `provenance_quote` against the *same* Europe PMC fulltext this tool
returns. So once you have read a PMID here, `quotes_found` on that row is no longer independent
evidence that the claim is in the literature. It has become a **citation-pairing check** — still
useful, because it catches a quote filed against the wrong PMID.

| you read | quote it? | what `quotes_found` then proves |
|---|---|---|
| a PDF or copy the author supplied | **yes** | the passage is in the paper that PMID names |
| a copy you obtained outside this session's `fetch_fulltext` | **yes** | same |
| `fetch_fulltext` output for that same PMID | **yes** | citation pairing only — say so |

Say the consequence out loud in the module's log or README. Never use it as a reason not to quote:
the alternative that rule actually produced was 3668 titles.

**And never write a passage that is not verbatim in the retrieved text.** A fabricated quote is a
fabricated quote whoever typed it. `quote_matches` is whitespace- and case-insensitive literal
containment, so ordinary reflowing is fine and a paraphrase is not.

**One more counter to read three-valued**, beyond `quotes_found` in rule 3 above. `quote_source` says
how far the search reached — a phrase found in an abstract is in the paper, while a phrase absent from
a 200-word abstract says nothing about the body. A preprint with no OA full text returns `null` for
every quote on it: **unchecked, not refuted**, and not a reason to delete them.

**And do not read `quotes_authored` as a check on any of this.** It records what the literature pass
saw *when it last ran*, and the sidecar is merge-not-clobber, so on a module whose quotes were
authored after that run it stays at `0` forever — measured at `0` on all four published
`antonkulaga/*` modules beside 3668 authored quotes, with the manifest summing the nulls into a
confident zero (`F49` / upstream `S56`). To check your own quotes, group `studies.csv` by `pmid`
yourself.

> **Upstream calls these columns `ATTESTATION_BEARING` and glosses them "the cell asserts that a
> HUMAN read something".** That is correct as a *provider* rule — no lookup tool may write these
> cells, and none does — and it is not the authorship rule, in a product whose `Contribution` model
> ships an `ai` author kind and whose `curator` field routinely holds an agent id. The reasoning we
> originally handed upstream for that constant is withdrawn (`S55`); the constant may still be right
> for their layer. Here: never fill these from a lookup, do write what you located, and record who
> located it.

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
  most common trap: it looks open and is not. `other-oa` on *every* location is the same thing
  wearing a label — measured on `27089181` (Okbay A et al., Nat Genet 2016), where all five
  locations came back `other-oa` and none carried a licence.

**What to do when it happens, measured rather than theorised.** The quote was kept and the
`licensing.csv` row recorded `license` empty with `share_alike`, `commercial_use` and
`redistribution` all **left blank — UNKNOWN, never false**. The consequence is visible on the
published card, which is the point of doing it that way: `unknown_terms_sources` lists that article,
and **the module's own `licensing.commercial_use` and `redistribution` drop to `null`**. One article
with unclear terms makes the whole module's commercial-use answer unknown. Weigh that before quoting
from a bronze article into a module you intend to sell; the alternative is to leave the cell empty
and say why.

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

**Only `literature_search` carries a `licensing` block** naming what you now owe — and it is the one
tool in the chain you may never call. `lookup_citation`, `lookup_open_access` and `fetch_fulltext`
return no such block, so an author who starts from a PMID they already hold gets **no reminder at
any point**, including at the moment they copy a passage out of a fetched article. Watch for that
yourself; it is the shape of the miss (`F46`).

Nothing writes those rows for you, on purpose: `declared_use` is a licence position only you can
take, and a fabricated licence string would be worse than the missing warning.

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

- **Check for a published version before you author from it** — see `module-start`'s "is the
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
