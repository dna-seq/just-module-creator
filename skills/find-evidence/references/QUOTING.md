# What may honestly go in `provenance_quote`

> **The part of finding evidence most likely to be got wrong, and the one with a measured cost.**
> The rule that used to forbid a machine-located quote did not produce human-read quotes — it produced
> **3668 published rows carrying the article's title**, which passes `quotes_found` every time because
> a title is always in its own fulltext. Full coverage, witnessing nothing. What replaces it is
> attribution, not abstention.

**Contents.** The four rules and their sub-cases, then the counters and what each can and cannot prove:

| | |
|---|---|
| [1. A passage, not a property of the article](#1-it-must-be-a-passage-not-a-property-of-the-article) | why a title is the failure case |
| [2. Choose a grain and hold it](#2-choose-a-grain-and-hold-it) | per-row versus per-paper |
| [3. An empty cell is a result](#3-an-empty-cell-is-a-result-and-there-are-four-kinds) | four kinds, and a fifth the counter cannot see |
| [3b. Named but for a different claim — STOP](#3b-if-the-article-names-the-variant-but-reports-a-different-trait-stop) | the most valuable thing a search produces |
| [3c. A name with no identifier](#3c-a-variant-name-and-no-identifier-is-not-an-unresolvable-record) | → [`IDENTITY_FROM_A_NAME.md`](IDENTITY_FROM_A_NAME.md) |
| [4. Record who located it](#4-record-who-located-it--and-know-where-that-record-does-and-does-not-go) | `curator`, and what nothing checks |
| [The cost of `fetch_fulltext`](#the-cost-of-using-fetch_fulltext-stated-rather-than-used-to-refuse) | when `quotes_found` stops being independent |

**This file is loaded from [`../SKILL.md`](../SKILL.md)**, which owns the search loop and the source
table. Licensing — whether a passage you may quote is one you may *redistribute* — is
[`LICENSING.md`](LICENSING.md).

---

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
associations live in its supplementary data and downloadable summary statistics.

**`fetch_fulltext` returns the JATS body and no supplementary file — a limit of the tool, not of what
is in reach. Corrected 2026-08-30; this passage used to end "there is nothing in reach to quote, and
the honest cell is empty".** That was wrong on its own example: PMID 29500382's workbook is two HTTP
requests from the DOI, openly CC-BY, and **42 of those 65 rsIDs are in it** with the p-values the rows
assert. All 65 shipped carrying the title instead. Go and get it: `list_supplementary`,
`fetch_supplementary`, `describe_supplementary`, `read_supplementary`, with the ladder and the routes
that look right and fail in [`SUPPLEMENTARY.md`](SUPPLEMENTARY.md). The honest
empty cell comes *after* you have called them, not instead of it.

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

**A fifth state exists and this counter cannot see it.** A quote located in a *supplementary* file
also scores `0`, because the checker searches the article body only — reporting "absent from the
paper" for a passage verbatim in that paper's own workbook. Nothing separates the two, so record the
source file yourself: [`SUPPLEMENTARY.md`](SUPPLEMENTARY.md).

### 3c. A variant NAME and no identifier is not an unresolvable record

`N150fs (c.448delA)`, `IVS2+1G>A`, `D1709N`. `lookup_variant` needs an rsID or a coordinate, which is
exactly what the record lacks — but a `c.` or protein fragment plus the gene's numbering frame **is**
an allele, and an allele registry holds it: 35 of 43 such records resolved in the survey behind this.
`lookup_allele_identity` asks that registry; constructing the expressions and choosing between two
that both register are yours. Do not start from the tool —
[`IDENTITY_FROM_A_NAME.md`](IDENTITY_FROM_A_NAME.md) has the procedure, and
sending a source's legacy name unmodified resolves 0 of 14.

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

**`studies.csv` has a `curator` column since format 0.6.5** — our `F43` / upstream `S55`, the field
`VariantRow` always had, put on the table where the attestation lives. Optional free text: a name, a
handle or a model id, resolvable against the module's `authorship`. **Fill it on every row whose quote
you located**, with whatever identifies you as the one who did the reading.

It is row-level because real work is mixed at row granularity — a human reads a review while an agent
traverses its citations, in one module, in one pass — and it records the distribution of labour so a
reviewer can route scrutiny. It does **not** move responsibility: the human author holds that
regardless of who typed the cell. It is deliberately not a `machine_located` boolean, so do not write
`true`, `ai` or `agent` into it as though it were one; write the identity, and let `authorship` say
what kind of contributor that identity is.

Nothing checks the value, and that is worth saying: `curator` is not redundancy-bearing, so an honest
entry and a careless one look the same to every check. It is legible to a **reviewer**, which is its
whole purpose.

The three other records still exist and still answer different questions:

| Where | Grain | Travels with the module? |
|---|---|---|
| `studies.csv: curator` | per **row** | yes — it is authored content, inside `content_signature` |
| `module_spec.yaml: authorship` (`Contribution`: `who`, `role`, `kind`) | per **version** | yes — `manifest.authorship` |
| `provenance.json` (`ProvenanceItem.rationale` + `outranks`, keyed by `variant_key`) | per **variant** | yes — stored, and summarised into `manifest.provenance`; **not** carried by a registry contract `upgrade` |
| `logs/*.log` | per **run**, free text | yes — `manifest.logs`; **not** carried by an `upgrade` |

Verified by publishing a remediated module and reading the manifest back: all three of the latter
survive a publish. Name the identity in `curator` and let `authorship` carry what kind of contributor
it is — that pairing is the whole record, and neither half means much alone.

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
authored after that run it stays at `0` — measured at `0` on all four published `antonkulaga/*`
modules beside 3668 authored quotes, with the manifest summing the nulls into a confident zero (`F49`
/ upstream `S56`). Format 0.6.5 warns when the counter disagrees with `studies.csv`, naming both
numbers, and publishes `quotes_unchecked` beside the other two so the zero is no longer confident —
but **it still does not rewrite the sidecar**, and a version published earlier keeps the counters its
own compile wrote. **`lint_rows` and `validate_module` detect the title case for you** (`RM17`), as
does the literature pass itself since 0.6.5 (`titles_as_quotes`, decided from the citation's metadata
rather than the string's shape): all report a
warning naming any PMID whose every quoted row carries the same passage, with the row count and the
first few words. It arrives in `validate_module`'s `authored_findings` rather than in `warnings`,
because that list transports upstream's own strings and this finding is ours; each carries
`source: just-module-creator` so you can always tell which layer spoke.

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
