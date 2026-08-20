# The four published modules: what is left to decide

For Anton Kulaga. Written 2026-08-20.

`aggression_anger_snps`, `big_five_personality_snps`, `cognitive_intelligence` and
`risk_impulsivity_snps` were read closely while the plugin's own attestation rules were being
audited. Two of the four were then remediated as rehearsals on the polygon; nothing in the four
published versions was touched, and nothing here proposes touching them. A published version is
immutable, so every item below is a decision about what a *next* version says, or about whether one
is worth cutting at all.

This is a decision list, not a report. If nothing has to be chosen, it is not here.

## What held up

On all **18** rows where both the module and the paper's own table gave a p-value, the two agreed to
one significant figure. That is every row where the comparison could be made at all. It is stated
nowhere else, and it is the strongest single thing measured about
these modules: the numbers that were transcribed were transcribed correctly.

---

## 1. Four rows in `big_five_personality_snps` cite a paper that does not support them

`rs34588274`, `rs3742021`, `rs4245154` and `rs527528` cite PMID `34054130` through GWAS Catalog
accession `GCST012111`, for `EFO_0009589` — a neuroticism item. The article does name all four
rsIDs. It names them in a table of hits for **sociability**.

So exactly one of three is wrong, and the other two are probably fine:

- the trait label, if the accession and the PMID belong together and the row was filed under the
  wrong EFO term;
- the accession, if `GCST012111` is a sociability study and a neuroticism accession was meant;
- the PMID, if `GCST012111` is a neuroticism study whose publication is a different paper.

**Route:** pull the `GCST012111` record from the GWAS Catalog. It carries both the reported trait and
the publication, so whichever two of the three it agrees with settle the third. Ten minutes, no
journal access needed.

This is also the finding that justified reversing our rule against machine-located quotes. Under the
old rule these four rows carried the article's title in `provenance_quote` and were indistinguishable
from the other 855. Only going after an actual passage surfaced them.

## 2. Three rows in `aggression_anger_snps` sit behind a paywall

`rs11838918`, `rs16891867` and `rs7950811` cite PMID `20585324`. Its abstract names `C1QTNF7` and no
rsID at all, so the abstract cannot confirm or deny any of the three. No open-access copy came back.

**Route:** somebody with journal access settles all three in about ten minutes. Failing that, the
ordered routes are in `skills/find-evidence/SKILL.md`, section *When there is no legal copy* —
preprint, corresponding author, Open Access Button, institutional access or interlibrary loan,
ranked by how fast they actually work rather than by how official they look. Each needs a person, and
that is precisely why the item is here rather than closed.

Until one of them lands, the honest state of those three rows is *unchecked*, which is not the same
claim as *checked and not found*.

## 3. `population` holds a citation label rather than a population

Every row of `aggression_anger_snps` carries `"Nagel M et al. — GWAS Catalog GCST006941"` in
`population`. That is a citation, and the citation is already elsewhere on the row.

**Decided reading:** the column wants the studied cohort's ancestry — the population the association
was measured in.

**Route:** if the module has been through a GWAS enrichment pass with study facts on, the answer is
already inside it. `gwas_effects.csv` carries an `ancestry` column, free text as the Catalog records
it ("European", "East Asian", "Hispanic or Latin American"), joinable back to `studies.csv` on `pmid`
or `study_accession`. Otherwise it is on the Catalog study record directly.

Two things make this a decision rather than a mechanical fill. A study often reports several
ancestries, so which of them a single cell should say is a judgement. And `population` is not one of
the redundancy-bearing columns, so filling it from the Catalog does not make any check vacuous, but
it does commit you to a reading of what the column is for.

The gap on our side is real and is on our list: the enricher fetches this and no tool of ours offers
it to an author writing `studies.csv`.

## 4. None of the four declares `authorship`

They were authored with AI assistance and say so nowhere. Of everything in this list, this is the one
thing a later reader cannot work out from the artifact — a wrong trait label can be caught by
reading the paper, an undeclared author cannot be caught at all.

The format models this properly at module level: `authorship` entries carry `who` (a name, handle or
model id) and `kind`, which ladders `{human, human_expert, human_certified}` against `{ai}` plus
`{agent, team, swarm}`. Declaring an AI co-author is not a demerit; it is what lets a reader route
their scrutiny, and a module that declares a human curator alongside is a stronger signal than one
that declares nothing.

**Route:** `authorship` lives inside `module_spec.yaml`, so a prose-only amend to the catalog card
cannot carry it. It costs a version. That is the decision: whether declaring it is worth a version on
its own, or whether it rides along with whatever else gets fixed.

## 5. `provenance_quote` holds the article's own title, on all 3668 rows

Measured across all four: **3668 of 3668** `studies.csv` rows carry a `provenance_quote`, and there
is exactly **one distinct quote per PMID** across 81 PMIDs, 7 to 17 words each. The quote is the
article's title, verbatim, punctuation included. It is the same string `lookup_citation` returns as
`title`.

A title always occurs in its own full text, so the quote check can never fail on one. Full coverage
of that column, on these modules, witnesses nothing about whether the claim is in the paper.

Two related measurements, so you have the whole picture:

- The check **never ran** on any of those rows. All four ship `literature.csv` with
  `quotes_authored: 0`, because the literature pass ran while the column was still empty and that
  sidecar is merge-not-clobber. So nothing is being lost by changing the column; there was no green
  check resting on it.
- Locating real passages for these rows yields roughly **2–3%**. That is the measured rate from the
  two remediated modules, and it is low because most of these rows are grounded in papers that report
  hundreds of variants in a supplementary table and discuss almost none of them in prose.

**The decision taken, and it is reversible:** empty the column and keep only the real quotes. A sparse
column that means something beats a full one that witnesses nothing. The cost is visible and is
accepted — quote coverage goes from apparently complete to nearly empty, and anyone reading the
catalog card sees that drop.

The second half of the decision is whether a quote change is a version at all. Both answers are
defensible. If item 4 is being done anyway, this rides along.

## 6. Two modules have not been examined

`cognitive_intelligence` (2045 study rows, 33 PMIDs) and `risk_impulsivity_snps` (695 study rows, 19
PMIDs) were counted and nothing more. Neither has had a row read against its paper.

Expect the **low** end of the 2–3% yield on both, and the reason is structural rather than a guess:
both are dominated by papers cited for hundreds of variants at once, and in the pair that was
examined, the three papers grounding the most rows named none of their variants in prose. A paper
cited for 300 rows will, at best, discuss a handful of them by name.

**The decision:** whether that yield is worth the pass. Reading 33 papers to recover perhaps 20 usable
passages out of 2045 rows is a real cost, and declining it is a legitimate answer. Emptying the
column without doing the reading is also available and is cheap — the two are separable.

---

## Your call and nobody else's

**Whether to yank the published versions.** A published version is immutable; yank drops it from
default listings and from `latest` while keeping it fetchable, so anyone who already installed it
keeps verifying against exactly what they installed. It is not a repair and it undoes nothing.
Publishing a corrected version is a separate act, and doing one does not require the other. The
plugin does not expose yank yet: the registry client has it and we wrap neither it nor its reverse.
That is tracked as a gap on our side.

Nothing in this list is an argument for yanking. The four mis-cited rows in item 1 are the only thing
here that is wrong on the module's own terms, and four rows out of 859 is the kind of thing a next
version fixes.

## If a later pass redoes the quote work

Locate the quote per `(pmid, rsid)`, not per `(pmid, trait)`. The second grain degenerates on a
single-trait module: every row shares the trait, so one quote covers the whole file and the defect
has been rebuilt under a better name. Per `(pmid, rsid)` is the grain that actually asks the question
the column exists to answer.

Note that the schema cannot yet record *who* located a passage on a per-row basis. `VariantRow` has a
`curator` column and `StudyRow` does not, which is the wrong way round given that only one of the two
is an attestation. That has been asked of upstream and accepted. Until it ships, module-level
`authorship` is where the mixed human-and-agent reality gets stated, which is another reason item 4
is worth doing first.
