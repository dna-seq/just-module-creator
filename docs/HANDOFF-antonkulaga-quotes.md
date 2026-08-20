# Handoff — the `provenance_quote` decision for the four `antonkulaga/*` modules

**Written 2026-08-20 by a `just-module-creator` dogfooding run, for whoever maintains those modules
next.** You need none of tonight's context to read this. Nothing here is urgent and nothing here is
a defect report about your work.

**This is a decision list, not a diff.** Every published version is immutable, so nothing described
here can be changed in place — all of it is a question about the *next* version, and several of the
answers are legitimately "leave it".

---

## 1. What was measured, so you can check it yourself in a minute

Four modules on production carry a `provenance_quote` on every `studies.csv` row:

```
aggression_anger_snps        69 rows      3 PMIDs
big_five_personality_snps   859 rows     26 PMIDs
cognitive_intelligence     2045 rows     33 PMIDs
risk_impulsivity_snps       695 rows     19 PMIDs
                          -----        -----
                           3668 rows     81 PMIDs
```

In all four there is **exactly one distinct quote per PMID**, and that string is the article's
**title**, verbatim — trailing period included.

The measurement, on any spec directory:

```python
import csv, collections
by = collections.defaultdict(set)
for r in csv.DictReader(open("studies.csv")):
    if r.get("provenance_quote"):
        by[r["pmid"]].add(r["provenance_quote"])
for pmid, quotes in sorted(by.items()):
    print(pmid, len(quotes), next(iter(quotes))[:70])
```

Any PMID showing `1` across many rows is the signal. Confirm the identity with one call:

```
lookup_citation(pmid="24489884").title
  -> "Genome-wide association study of proneness to anger."
studies.csv, pmid 24489884, provenance_quote
  -> "Genome-wide association study of proneness to anger."
```

**Why it matters, in one sentence.** A title occurs in its own fulltext, so the quote check can
never fail on one, and it can be obtained from PubMed `esummary` without retrieving a word of the
article — which is the one thing the column exists to witness.

**The shape is the detector, not the string.** One identical quote across many rows citing a paper
is not a located passage whatever it says, because different rows cite the same paper for different
findings. If you fix these four by hand and a future pass reintroduces a repeated string, this
group-by catches it and nothing else will.

## 2. Two things that are not what they look like

**The check never ran.** All four modules' `literature.csv` carry `quotes_authored: 0`, an empty
`quotes_found` and an empty `quote_source` on **every** row. The literature pass ran before the
quotes were authored, and `literature.csv` is merge-not-clobber, so no later run revisited it. The
published manifest then reports `quotes_authored: 0, quotes_found: 0` beside 3668 authored quotes,
because summing null counters gives a confident zero.

Two consequences: the counters are **not** a way to find this problem, and the modules were never
claiming coverage they did not have — they were claiming *nothing*, which is a different and more
honest failure than it first appears. Filed upstream as `S56`.

**These modules met the rules that existed.** Until 2026-08-20 this plugin's own guidance forbade an
agent to locate a passage in a fetched article at all. The rule did not produce human-read quotes;
with the column present and an agent forbidden to fill it honestly, it produced titles. That
prohibition is reversed. If you are the agent that wrote them, the rule you followed is the thing
that changed, not your judgement.

## 3. What a correct remediation looks like, measured on a real one

`aggression_anger` was remediated end to end and published to the polygon as
`test-sheep/test_aggression_anger_snps@1.0.0`. Result: **1 quote of 69**, and 68 deliberately empty.
That is the honest yield, and it is worth knowing before you budget the work.

Per PMID:

| PMID | rows | fulltext | outcome |
|---|---:|---|---|
| 24489884 (Mick, PLoS ONE, cc-by) | 1 | retrieved in full | quote written — a Discussion sentence naming that row's variant and its trait |
| 29500382 (Nagel, Nat Commun, cc-by) | 65 | retrieved in full, 58 257 chars, not truncated | **empty** — the article names exactly two rsIDs and neither is one of these 65 |
| 20585324 (Dick, Mol Psychiatry) | 3 | not open access, abstract only | **empty** — the abstract names the gene `C1QTNF7` and no rsID |

**The 65 are the important number.** Those rows come from a GWAS Catalog association record
(`GCST006941`), and the association lives in the study's supplementary data and downloadable summary
statistics, not in its prose. `fetch_fulltext` returns the JATS body and no supplementary file, so
there is nothing in reach to quote. This is not a flaw in those rows — the association is real and
the citation is right. It is that `provenance_quote` asks a question a catalog-derived row cannot
answer from the article text.

**Decide the grain before you start, and write the decision down.** Two defensible units:

- **per `(pmid, rsid)`** — the passage must identify the row's own variant. Strictest, and the only
  one that makes the quote evidence *for that row*. This is what the remediation used.
- **per `(pmid, trait)`** — a passage supporting the trait-level finding, repeated over the rows
  that share it.

The second one is a trap on a module where a paper contributes rows for one trait only: it produces
one string per PMID again, which is indistinguishable in shape from what you are repairing, and it
would defeat the detector upstream is being asked to build. If you use it, say so in the README.

**An empty cell is a result, and there are two kinds.** *Read and not found* (a fulltext was
retrieved and the claim is not in it) says something. *Unchecked* (no fulltext retrievable) says
nothing — an abstract miss is not a verdict. Keep them distinct wherever you record them.

## 4. What is genuinely blocked upstream, and what it costs meanwhile

- **`S54`** — the quote check cannot fail on a title. Asks the compiler to reject or flag a quote
  equal to `CitationHint.title`, and to report one identical quote repeated across every row citing
  a PMID. Open.
- **`S55`** — `StudyRow` has no per-row attributor. `VariantRow` has `curator`; the table that
  actually carries an attestation does not. Open.
- **`S56`** — nothing compares `literature.quotes_authored` with the quotes in `studies.csv`, and
  the manifest publishes a confident `0` where the counters are null. Open.

**What `S55` costs you today, precisely.** There is no column that says who located a quote, so it
goes beside the rows rather than on them. Three places, all verified to survive a publish:

| Where | Grain | Survives a contract `upgrade`? |
|---|---|---|
| `module_spec.yaml: authorship` (`Contribution`: `who`, `role`, `kind`, `at`) | per version | yes |
| `provenance.json` — `ProvenanceItem.rationale`, keyed by `variant_key` | per variant | **no** — explicitly not carried |
| `logs/*.log` | per run, free text | **no** — explicitly not carried |

None is per `(row, quote)`. A variant cited by two papers collapses to one `provenance.json` item.
State that limit in the module's README rather than designing around it.

## 5. The decisions — what a human has to choose

Nothing below is mechanical. Each needs somebody to pick.

1. **Whether to remediate at all, and in what order.** The yield measured on the smallest module was
   1 real quote from 69 rows. On `cognitive_intelligence` (2045 rows, 33 PMIDs) the ratio will be
   worse, because the larger a GWAS module is the more of it comes from catalog extraction. An
   equally defensible answer is to **empty the column** on the next version and say in the README
   that these rows are grounded on GWAS Catalog association records rather than on located passages.
   That is honest, it is cheap, and it removes a green check that means nothing.

2. **Whether an emptied column or a title is worse for a consumer.** A title reads as evidence and
   is not. An empty column reads as work not done, on modules where the work genuinely cannot be
   done from the article text. There is no rule that settles this; it is a judgement about what your
   readers will infer.

3. **What version a quote change is.** How the rows are *grounded* changes, which reads as a major
   under the publish tool's own guidance — but versions carry no implicit contract here, and no
   milestone is owed. Pick deliberately and write the changelog as a continuation of the previous
   one.

4. **The three `20585324` rows in `aggression_anger`, and every paywalled paper like them.** The
   abstract states that four markers reached genome-wide significance and names `C1QTNF7`; it does
   not name `rs11838918`, `rs16891867` or `rs7950811`. Somebody with journal access could settle all
   three in ten minutes. Worth doing, or leave them unwitnessed and say so?

5. **Whether to declare `authorship`.** None of the four declares one. The signal a reader routes
   scrutiny by lives there — `Contribution.kind` ladders `{human, human_expert, human_certified}`
   against `{ai}` + `{agent, team, swarm}` — and a module with no entry says nothing at all about
   who wrote it. An agent-only declaration is not a downgrade; it is the honest version of what is
   already true.

6. **Whether `population` should hold what it currently holds.** In `aggression_anger` every row's
   `population` is a citation label — `"Nagel M et al. — GWAS Catalog GCST006941"` — where the column
   is documented as the study population. Nothing checks it and nothing is wrong on its own terms.
   But an effect estimated in one ancestry frequently does not transfer, and this is the column a
   reader would look at to find out. **Flagged, not touched** — it is an authored value.

## 6. What was deliberately not done

The remediation touched **only** `provenance_quote`. No `conclusion`, `weight`, `effect_size`,
`direction`, `clin_sig`, `p_value` or `population` was altered, in the working copy or anywhere else,
because those are authored or checked values and changing one silently is the thing this whole
exercise exists to prevent. Nothing in the published modules was touched at all — they are immutable
and they are not ours.

The full run record is in [`RM15-remediation-log.md`](RM15-remediation-log.md), and the friction the
tooling produced along the way is `F44`–`F47` in [`dogfooding.md`](dogfooding.md).
