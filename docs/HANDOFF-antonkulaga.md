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

---

# Update, 2026-09-27

Written from just-dna-lite, against what is published now.

## Where the six items stand

Checked against the latest published versions (`aggression_anger_snps@2.0.1`,
`big_five_personality_snps@2.1.1`, `cognitive_intelligence@2.0.1`, `risk_impulsivity_snps@2.0.1`, all
2026-09-12):

| # | item | now |
|---|---|---|
| 1 | four `big_five` rows cite a sociability table for a neuroticism item | **half open.** `rs34588274` and `rs3742021` are gone. `rs4245154` and `rs527528` still cite PMID `34054130` under `EFO_0007660` (neuroticism), with the conclusion "Worry too long after an embarrassment". The `GCST012111` lookup that settles it has not been recorded. |
| 2 | three `aggression` rows behind a paywall (PMID `20585324`) | closed: no row cites it any more |
| 3 | `population` held a citation label | closed: it now states the cohort ("366,726 European ancestry individuals") |
| 4 | no `authorship` | closed: all four declare `ai-module-creator` (`ai`, `agent`) |
| 5 | `provenance_quote` held the article title | closed: quotes emptied, only located ones remain (aggression 2, cognitive 4, risk 0) |
| 6 | two modules never read against their papers | decided: emptied without the reading pass, which the list allowed |

## 7. `blood_groups@0.1.0`: two decisions about RHD

just-dna-lite now reads a deletion allele from the coverage inside its span on a whole-genome callset
(a small-variant VCF never lists a large deletion, so a missing `<DEL>` record says nothing). Calls
throughout the span mean at least one copy is present. An empty span with calls on both sides means
both copies are gone. Anything else is left unsettled, with the reason shown. It also no longer reads
any missing call as reference inside GIAB's low-mappability and segmental-duplication regions, and
all of RHD and RHCE is inside them. Two things in the module now matter because of that:

1. **The `RHD_deletion` span does not sit on RHD.** It is authored as `<DEL:68163>` at rs1132760
   (1:25,284,731), which by VCF convention covers 1:25,284,732-25,352,894: it starts about 12 kb inside
   RHD (1:25,272,393-25,330,445) and ends about 22 kb past it. On your genome all 15 calls in that span
   lie past the gene's end, with nothing inside RHD, so a reader that asked "is there any call in the
   span?" would have called you RhD-positive. The caller now refuses a span with a long call-free
   stretch inside it, so it reports you as not assessable, but the span is the module's claim. **Route:**
   re-anchor it on the common RhD-negative deletion (RHD plus its flanking Rhesus boxes). That costs a
   version, because the allele is part of the content signature.
2. **The weighting note is now stale.** It says RhD is "deliberately reported as not assessable from a
   variant-only VCF". That is still true on an exome, on a panel, and where coverage is ambiguous. On a
   whole genome with calls across the gene the report now says RhD-positive, labelled as read from
   coverage. **Route:** a prose-only change, so it rides along with item 1 or goes in a README amend.

**One question only you can answer:** your genome has no calls at all across RHD (a 72 kb hole), while
the three other genomes here have 45-56 calls inside it. That is what RhD-negative looks like, and also
what unplaceable reads look like. If you know your Rh type, it is the real-sample test for this code.
