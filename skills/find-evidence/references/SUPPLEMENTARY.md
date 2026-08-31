# Supplementary tables: finding them, fetching them, quoting them

> **Scope — measured 2026-08-30 against four real articles.** The retrieval ladder below is
> publisher-general at rungs 0–2 and **Springer Nature family only** at rung 3 (DOI prefixes
> `10.1007` Springer, `10.1186` BMC, `10.1038` Nature). That family covers most of the genetics
> literature a module cites, and it is not all of it. Meeting another publisher is not a failure of
> this file — it is the moment to add a row to the pattern table, with the probe that established it.

| Section | Answers |
|---|---|
| [Why this matters](#why-this-matters) | Why a GWAS row's numbers are almost never in the article body |
| [The ladder](#the-ladder) | Rung 0 DOI → 1 record → 2 inventory → 3 publisher pattern |
| [What the ladder refuses to do](#what-the-ladder-refuses-to-do) | The four routes that look right and are not |
| [Inside the file](#inside-the-file) | Workbook → sheet → the table you actually wanted |
| [Quoting from a supplementary table](#quoting-from-a-supplementary-table) | Why `quotes_found: 0` is expected here, not damning |
| [Licence](#licence) | The ESM is not automatically covered by the article's licence line |

---

## Why this matters

A GWAS paper's body says *"263 independent variants across 180 genomic loci"*. It does not list them.
The rsIDs, their chromosomes, positions, effect alleles, effect sizes and per-trait p-values — every
column `studies.csv` and `gwas_effects.csv` actually want — are in the supplementary workbook.

So for this kind of paper, `fetch_fulltext` returns the narrative and none of the data. That is a real
limit of that tool and not a limit on what is reachable: the supplementary file is normally two HTTP
requests from the DOI, on an open host, under the article's own licence.

**The measured case, and it is the one this skill used to teach the opposite of.** PMID `29500382`
(*Item-level analyses reveal genetic heterogeneity in neuroticism*, `10.1038/s41467-018-03242-8`)
backs 65 rows of the published `aggression_anger` module. Its JATS body names none of those rsIDs.
Its **Supplementary Data 2** — described in its own index file as *"Association P values for all
genome-wide significant lead SNPs for the 12 individual items and the sum-score"* — carries 504
distinct rsIDs, and **42 of the module's 65 are in it**, with the per-item p-values those rows assert.
All 65 rows currently carry the article's title as their `provenance_quote` (`F42` / upstream `S54`).
A real passage was available for two-thirds of them.

The remaining 23 are the honest residue: they are not in that file, and whether they are in another
supplementary file, in a different paper, or drawn from a catalog record is exactly the question
rule 3's *read and not found* versus *unchecked* distinction exists to keep separate. Do not guess.

---

## Four tools do this now

Since 0.25.0 the ladder is a tool surface, not a procedure you drive by hand, and since 0.29.0 it
reaches the cells:

| call | what it does |
|---|---|
| `list_supplementary(doi= / pmid= / pmcid=)` | inventory only, fetches nothing. Runs the rungs below and says which one answered |
| `fetch_supplementary(url=)` | one file, from a url the inventory gave you, into the cache |
| `describe_supplementary(path=)` | a workbook's sheet names and its in-cell `Supplementary Table …` titles. Offline, no spreadsheet library |
| `read_supplementary(path=, sheet=, offset=, limit=)` | the rows of one sheet you named. Offline |

**`read_supplementary` hands over cells and stops there.** It does not pick the sheet, find the header
row or select the rows that answer a claim — those are judgements about the row you are authoring, the
same reason `fetch_fulltext` returns no best-matching passage. What it does guarantee is the two things
a hand-written reader keeps getting wrong: every row padded to the sheet's width, so zipping against a
header cannot shift a column, and both counts taken by streaming rather than off the workbook's
optional dimension record.

**Page on `last_populated_row`, not `total_rows`.** They disagree by however many blank rows the
producer left: the ARDS paper's `ST9` spans 1000 and holds 266.

**Read `verdict` as three-valued and never as a boolean.** `found`; `none_published` — the paper has
none; `not_determinable` — no rung could answer, which for now usually means *no URL pattern is known
for this publisher*. The third is a gap in our coverage and is **never** evidence a paper has no
supplementary material. Two agents recorded exactly that inference as a fact about the world.

`notes` says what the answer is bounded by. The pattern rung stops enumerating on a guess, so its file
list is a floor rather than a count; the Europe PMC rung is authoritative because it carries each
file's real extension.

They go through `net.py`'s `ServiceGate`, so pacing, retries on 429/503 and the contact header are
handled — nothing below needs saying in a prompt.

**None of them parses a table into rows**, deliberately. Which sheet supports a row's claim is a
judgement about that row, the same reason `fetch_fulltext` returns no best-matching passage.

## The ladder those tools run

Worth reading even though you no longer type it: it is what `rung` and `why_not` are telling you, and
it is what to do by hand when the verdict is `not_determinable`. **Record which rung answered** — the
rung is part of what you know about the file.

**Identify yourself on every request.** These are polite-pool hosts and the address says whose budget
is being spent, so send the one the contact chain resolved — `JMC_USER_EMAIL`, then
`JUST_DNA_CONTACT_EMAIL`, then the project default — as `-A 'just-dna module author
(mailto:<that address>)'`. **Never invent an address**: a fabricated one misattributes the traffic to
a stranger. These calls are outside `net.py`'s `ServiceGate`, which is `F68`'s open half; neither host
is NCBI, so the shared budget is not touched, but pace yourself rather than looping a probe.

### Rung 0 — get the DOI

```bash
pdfinfo paper.pdf | sed -n 's/^Subject: *//p'      # Springer puts the DOI here
```

Two of the four PDFs measured carried no DOI in metadata, so this fails routinely. Fall back to the
text, where the Supplementary Information statement carries it:

```bash
pdftotext -layout paper.pdf - | grep -oE '10\.[0-9]{4,9}/[^ )]+' | head
```

Springer's typesetting inserts soft hyphens and zero-width joiners inside the printed DOI — strip
non-ASCII before matching, or you will extract a string that 404s and looks like a dead article.

If there is no PDF, a PMID reaches the DOI through `lookup_citation`.

### Rung 1 — the Europe PMC record

```bash
curl -sS "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%22<DOI>%22&format=json&resultType=core"
```

Read `pmcid`, `inEPMC`, `hasSuppl`. **`hasSuppl: N` does not mean there is no supplementary material**
— see the next section. It is a reason to go to rung 3, never a reason to stop.

### Rung 2 — the inventory, when the article is in PMC

```bash
curl -sS "https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML"
```

Every `<supplementary-material>` element carries an `xlink:href` with the **exact filename and
extension**, plus whatever caption the publisher supplied. This is the authoritative list and it is
cheap — 116–168 KB on the articles measured.

Two properties to code around: **each file is listed twice** (once in the body, once in the back
matter), so dedupe; and the caption is often useless (*"Additional file 3."*). Nature is the good case
— its captions read *"Supplementary Data 2"*, and its `MOESM1` is a *Description of Supplementary Data
Files* PDF that says what each one holds.

### Rung 3 — the publisher pattern, when the article is not in PMC

For the Springer Nature family every ESM sits on one open host, addressed by DOI:

```
https://static-content.springer.com/esm/art%3A<url-encoded DOI>/MediaObjects/<stem>_MOESM<n>_ESM.<ext>
```

The `<stem>` is `{journal}_{year}_{article}`, **leading zeros stripped from the article number**:

| DOI | stem |
|---|---|
| `10.1007/s11357-025-02044-3` | `11357_2025_2044` |
| `10.1186/s40246-025-00772-3` | `40246_2025_772` |
| `10.1038/s41467-018-03242-8` | `41467_2018_3242` |

Probe with a range request so a miss costs one byte, not a file:

```bash
curl -sS -L -r 0-0 -o /dev/null -w '%{http_code}\n' "<url>"
```

`206`/`200` = the key exists. `403` = **no such key** (the host answers absent objects with an S3
access-denied, not a 404). Iterate `n` from 1 upward; two consecutive absences across every extension
you try is a reasonable stop, and it is a *guess*, not a count.

---

## What the ladder refuses to do

Four routes look correct and are not. Each was measured.

- **Do not scrape `link.springer.com`.** The article page is behind a JavaScript bot challenge: a
  `curl` of the resolved DOI returns 3 KB titled *Client Challenge* with HTTP 200. An agent that
  parses that page for links finds none and concludes there is no supplementary material. The static
  host has no challenge.
- **Do not trust `hasSuppl: N`.** For `10.1007/s11357-025-02044-3` Europe PMC reports `inEPMC: N`,
  `isOpenAccess: N`, `hasSuppl: N`, while the article is CC-BY and its two supplementary files
  download without authentication. The flag describes *Europe PMC's holdings*, not the article's.
  This is the three-valued rule at the corpus level: the index not having it is not the paper not
  having it.
- **Do not default to Europe PMC's `supplementaryFiles` endpoint.** It works, and it returns
  **one zip of everything including every figure**, with no way to select. Measured on `PMC12506250`:
  **224 MB** transferred to reach a 14 KB table. Use it only when rung 3 has no pattern for the
  publisher and you have said out loud what it costs.
- **Do not guess extensions and read a miss as absence.** On `10.1038/s41467-018-03242-8`, `MOESM1` is
  `.txt` on one article and `.pdf` on another, and `MOESM3` is a *Peer Review File* rather than data.
  A 403 on the four extensions you tried means **unknown**, not *there is no file 3*. Rung 2 is what
  turns unknown into known; where rung 2 is unavailable, say the enumeration was partial.

---

## Inside the file

Finding the file is half of it. The table a row needs is usually one sheet of a workbook.

`describe_supplementary` gives the roster and `read_supplementary` gives the rows. The shell
equivalent of the first still works and is worth knowing when you are outside the plugin:

```bash
unzip -p suppl.xlsx xl/workbook.xml | grep -o '<sheet [^>]*name="[^"]*"'
unzip -p suppl.xlsx xl/sharedStrings.xml | grep -o 'Supplementary Table S[0-9]*:[^<]*'
```

There is **no shell equivalent of the second worth writing**, and that is why the tool exists. Four
authoring runs wrote one anyway — shared strings, cell references, absent dimension records, sparse
rows — and two produced a column-alignment bug that puts a BETA in the chromosome column: well-formed,
plausible and wrong. Call the tool.

**Read the first few rows before pulling the table.** A supplementary sheet usually opens with a title
line, sometimes a section line, then the header — `ST9` puts its real header on row 2, zero-based —
and a two-level header is common. `limit=5` at `offset=0` costs nothing and tells you where the data
starts.
Sheets are commonly named `ST1`…`ST14` while their in-cell titles read *"Supplementary Table S8: …"*,
and many workbooks carry a `Table of Contents` sheet that maps one to the other. The body text is the
other half of the map: it cites *(Supplementary Table S5-6)* at the sentence whose claim you are
trying to support, so grep the fulltext for the table number before opening anything.

**Worked example, end to end** — the file a reader may already have on disk as
`11357_2025_2044_MOESM2_ESM.csv` is not a Springer artifact at all. It is sheet `ST8` of
`11357_2025_2044_MOESM2_ESM.xlsx`, exported locally to CSV. Reproducing it: DOI from `pdfinfo` →
stem `11357_2025_2044` → rung 3 finds `MOESM1_ESM.pdf` and `MOESM2_ESM.xlsx` → sheet `ST8` →
263 rsIDs, the same 263 the abstract claims and the same 263 in the exported CSV.

---

## Quoting from a supplementary table

A row of a supplementary table is a legitimate `provenance_quote` for the same reasons a body-table row
is (rule 3c): verbatim, per-row, and it carries the variant with its effect and p-value. Extract it
with a regex against the file rather than retyping it.

**But it changes what one counter means, and this is the part to get right.**
`enrich_literature_pass` searches the **article body** Europe PMC holds. A passage lifted from a
supplementary workbook is not in that body, so:

> `quotes_found: 0` on a row whose quote came from supplementary material is **expected**, and it is
> not the *read and not found* state rule 3 describes.

Rule 3's four kinds of empty were written for body text. A supplementary-sourced quote adds a fifth
state, and collapsing it into *read and not found* reports a fabrication signal where none exists:

| state | `quotes_found` | what it means |
|---|---|---|
| body-sourced, matched | ≥ 1 | citation pairing holds |
| body-sourced, absent | `0` | says something — check the row |
| **supplementary-sourced** | **`0`** | **says nothing about the row; the checker never opened the file** |
| nothing retrievable | `null` | unchecked |

Nothing on the tool surface distinguishes rows three and two, so **you** have to. Write the file down:
the `curator` cell records who located the quote, and the source file and sheet go in
`logs/authoring.log` via `record_override` and in the module's README. A reviewer reading a `0` needs
to be able to find out which of the two it was, and the filename is the only thing that tells them.

Do not paper over it by also pasting a body sentence that does not name the variant — that is rule 3b's
failure with extra steps.

---

## Licence

The ESM is a separate file and its rights are not settled by the article's licence line, though they
usually follow it. `10.1007/s11357-025-02044-3` is CC-BY 4.0 per Crossref, which covers its two ESM
files; a paywalled article whose ESM happens to be openly served is the case to stop on.

Check with `lookup_open_access`, record the finding in `licensing.csv` the same way a body quote is
recorded, and where the rights are genuinely unclear the measured precedent is to keep the quote and
record the rights as unknown rather than to delete either.
