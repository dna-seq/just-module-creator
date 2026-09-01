# Licensing what you read: free to read is not free to reuse

> **This decides whether a module is publishable, and nothing else in the toolchain covers it.**
> Reuse terms are **per article**, never per source: there is no licence you can state once for
> "PubMed" that is right for every paper it indexes.

**Contents.**

| | |
|---|---|
| [What the licence values mean](#copyright-free-to-read-is-not-free-to-reuse) | `cc-by`, `cc-by-nc`, and the bronze trap |
| [`licensing.csv` when you read by hand](#licensingcsv-when-you-read-by-hand) | which row, and what blank means |
| [When there is no legal copy](#when-there-is-no-legal-copy) | the four routes, and why there is no fifth |

**Loaded from [`../SKILL.md`](../SKILL.md)**, which owns finding and reading the paper.
What may honestly be *quoted* is [`QUOTING.md`](QUOTING.md); the column-by-column dossier for the
file itself is [`module-tables`](../../module-tables/references/licensing.md).

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

## When there is no legal copy

`lookup_open_access` came back empty and the article is paywalled. **That is a routing problem, not
the end of the search** — and it ends in the decision list rather than in a defect report, because
every route below needs a person and none of them is instant.

Ordered by how fast they actually work:

1. **Check for a preprint first.** bioRxiv, medRxiv and arXiv often carry the same work, and the
   discovery surface already reaches all three. Read [Preprints](#preprints) below before authoring
   from one — the preprint and the published version can differ in exactly the numbers you came for.
2. **Ask the corresponding author.** The address is in the PubMed record. This is ordinary academic
   practice, it usually works, and for a recent paper it is often the *fastest* route — frequently
   same-day. Highest yield of anything here.
3. **Open Access Button** (openaccessbutton.org, run by OA.Works). Give it the DOI: it searches
   repositories Unpaywall may miss, and when it finds nothing it emails the corresponding author on
   your behalf and archives whatever comes back. Route 2 with the asking done for you.
4. **Institutional access or interlibrary loan.** Anyone with a university library account settles it
   in minutes; ILL document delivery is standard and normally free to the requester. This is the
   route that needs somebody specific, which is why it belongs in the decision list with the DOI and
   the citation attached rather than as a task an agent can close.

**What to record while a route is in flight.** Nothing changes in the row: `text_source` stays
`null`, `quotes_found` stays `null`, and the cell is *unchecked* — kind 2 of the four in rule 3
above. An unchecked row is honest. Do not downgrade it to "read and not found", which is a different
and much stronger claim, and do not reach for a quote from the abstract to fill the gap.

**There is no fifth route.** See [What is deliberately not here](../SKILL.md#what-is-deliberately-not-here) for
why a bypass is not one, and do not offer one — the reason is the licence gate this repo is built
around, not squeamishness.

---
