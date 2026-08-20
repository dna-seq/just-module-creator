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

## 3. What a correct remediation looks like, measured on two real ones

Both `aggression_anger` and `big_five_personality` were remediated end to end and published to the
polygon, as `test-sheep/test_aggression_anger_snps@1.0.0` and
`test-sheep/test_big_five_personality_snps@1.0.0`. The yields:

```
                        rows   quoted after   distinct strings   PMIDs
aggression_anger          69              1                  1       3
big_five_personality     859             21                 21      26
```

**Around 2–3% of rows can carry a variant-level quote.** That is the number to budget against, and it
is worth knowing before you start rather than after.

### The measurement that explains the number

Every one of `big_five`'s 26 cited PMIDs was retrieved with `fetch_fulltext`, and every `rsNNNN`
token in the retrieved text was intersected with the rsIDs the module cites to that paper. All 859
rows fall into four classes:

```
quotable   — the article's retrievable text names this row's variant           25 rows
read and not found — fulltext retrieved and read, variant not in it           300 rows
unchecked  — no open-access fulltext; abstract only                           527 rows
unchecked  — nothing retrievable at all (pmid 31972866)                         7 rows
```

**The relationship is inverse, and that is the useful part: the more rows a paper grounds, the less
likely its text names any of them.** The three biggest contributors yielded nothing — `30643256`
(298 rows), `29500382` (197) and `29255261` (69). `29500382`'s fulltext *was* retrieved in full and
names exactly two rsIDs, neither among the 197 it is cited for. A paper cited for hundreds of
variants is a large GWAS whose hits live in supplementary tables, which is why
`cognitive_intelligence` (2045 rows, 33 PMIDs) should be expected to behave like `big_five` rather
than better.

Two things that were *not* wrong: every module p-value checked against its paper's own table agreed
to one significant figure, on all 18 rows where both were available, and every PMID named the paper
the row meant. The citations and the numbers are right. Only the quotes were metadata.

### Three situations the current guidance does not cover, all met on `big_five`

1. **Named only in a table.** 15 of the 21 quotes are a row of a flattened JATS table, because that
   is the only place the article states the association for that variant. They are verbatim, they
   match, and each carries the variant, its alleles, its effect and its p-value — but the column is
   documented as "human-legible" and a table row is legible only to somebody holding the paper. It
   was written anyway: strictly better than empty, enormously better than a title. Your call whether
   you agree.
2. **Named, but for a different claim.** See decision 7 below. This is the one that matters.
3. **Quotable, but with no reuse licence.** `27089181` (Okbay A et al., Nat Genet 2016) is free to
   read and carries **no** reuse grant on any location — every one came back `other-oa`. The quote
   was kept and the `licensing.csv` row records its three rights as **unknown** rather than
   assuming them, which is what puts it in the card's `unknown_terms_sources`. Free to read is not
   free to reuse, and the annotation layer is where that bites.

### Per-PMID detail from the smaller module

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

1. **Whether to remediate at all, and in what order.** The measured yield is 1 of 69 and 21 of 859 —
   call it 2–3%, and expect `cognitive_intelligence` and `risk_impulsivity` to be at the low end,
   because they are dominated by papers cited for hundreds of variants each. An equally defensible
   answer is to **empty the column** on the next version and say in the README that these rows are
   grounded on GWAS Catalog association records rather than on located passages. That is honest, it
   is cheap, and it removes a green check that means nothing. The case *against* emptying is
   decision 7, which only surfaced because somebody went looking for the passages.

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

7. **Four rows in `big_five_personality` whose cited article reports a different trait. This is the
   one that needs a person, and it is why remediating beat emptying.**

   `rs34588274`, `rs3742021`, `rs4245154` and `rs527528` cite PMID `34054130` — Bralten J et al.,
   *Genetic underpinnings of sociability in the general population*, Neuropsychopharmacology 2021 —
   for trait `EFO_0009589`, *"Worry too long after an embarrassing experience"*, via GWAS Catalog
   accession `GCST012111`.

   The article names all four rsIDs. It names them in a table of genome-wide significant hits for
   **sociability**, with p-values `1.01E-13`, `7.43E-09`, `7.17E-09` and `4.02E-10`. The module
   authored `2e-17`, `1e-09`, `9e-09` and `4e-11` — different numbers — and the article contains no
   analysis of that neuroticism item at all; the word *worry* appears once, in an unrelated sentence.

   So a passage naming the variant exists and does **not** support the claim the row makes. The rows
   were left with an empty quote rather than given that passage, because attaching a real sentence to
   the wrong assertion is worse than an empty cell. Nothing else was touched: `trait_efo_id`,
   `p_value` and `conclusion` are authored values.

   **What has to be decided:** which of the three is wrong — the trait label, the accession, or the
   PMID. Checking it needs the GWAS Catalog record for `GCST012111`, which `enrich_gwas_effects`
   would fetch; that tool is extended-tier, so a default install cannot answer it.

   **Why this is the argument against simply emptying the column.** Under the old rule these four
   rows carried the article's title and looked exactly like the other 855. Nobody would ever have
   looked. Going after the passage is what found them, and there is no reason to think four is the
   total across 3668 rows — it is the total across the 25 that were checkable at all.

## 6. What was deliberately not done

The remediation touched **only** `provenance_quote`. No `conclusion`, `weight`, `effect_size`,
`direction`, `clin_sig`, `p_value` or `population` was altered, in the working copy or anywhere else,
because those are authored or checked values and changing one silently is the thing this whole
exercise exists to prevent. Nothing in the published modules was touched at all — they are immutable
and they are not ours.

The full run record is in [`RM15-remediation-log.md`](RM15-remediation-log.md), and the friction the
tooling produced along the way is `F44`–`F47`, `F50` and `F51` in
[`dogfooding.md`](dogfooding.md).
