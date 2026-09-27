---
name: module-voice
description: >-
  How a module talks to the people who read its report: two audiences with equal weight (readers with
  no science background, and professionals), three layers of detail and which field each lives in,
  how to write a phenotype label and a conclusion, the plain-word list, what practical notes are
  allowed, when to ask the module author a question, and a before/after from a real report that
  nobody could read. Read before writing or rewriting any `conclusion`, `phenotype`, `title` or
  `description`.
  Triggers: "write conclusions", "conclusion text", "plain language", "readable", "tone", "voice",
  "the report is unreadable", "too technical", "jargon", "layperson", "phenotype label",
  "description", "what should the conclusion say", "explain to users".
---

# Module voice: writing for two audiences at once

**Read by:** stage 3 (curate), whenever a `conclusion`, `phenotype`, `title` or `description` is
written, and by any revision pass that touches text. [`module-curate`](../module-curate/GUIDE.md)
decides *what* a row claims; this guide decides *how it says it*.

The authoritative version, including the report-template side, is
[`docs/REPORT_VOICE.md` in just-dna-lite](https://github.com/dna-seq/just-dna-lite/blob/main/docs/REPORT_VOICE.md).
This file is the part a module author needs, and it must not contradict that one.

## Who reads a module

Two audiences, **with equal weight**:

1. **People without a science background**, reading their own report. They do not know what an
   allele, a diplotype or a VCF is and should never need to.
2. **Professionals** (clinicians, geneticists, bioinformaticians, reviewers) checking the result.

Writing for either one alone fails the other. The answer is layers, each in its own field.

## Three kinds of module, three report shapes

Modules answer different kinds of question, and one layout cannot serve them all. Decide the kind
first; it fixes what layer 1 looks like and what must never appear.

| Kind | Example | What the reader gets first | Must not appear | Module tables | Report partial |
|---|---|---|---|---|---|
| **Per-variant findings** | longevity, coronary, thrombophilia | a table, one plain answer per row, detail and evidence on unfold | unexplained numbers in the first view | `variants.csv` (+ `studies.csv`) | per-variant tables in `longevity_report.html.j2` |
| **Combination (a "formula")** | ABO and Rh, APOE, HFE compound carriers | one named result per gene, the rule in plain words, the possibilities when the file cannot decide | weights, scores, net weight, good/bad colours: a combined result is not a sum of parts, and group O is not "worse" than A | `haplotypes.csv` + `diplotypes.csv` | `phenotype_section.html.j2` |
| **Drug response** | ClinPGx drug annotations, CPIC diplotypes | per drug: what the result means and what to tell a doctor or pharmacist | "avoid X", dose numbers, a score | `pharm_variants.csv`, or `diplotypes.csv` with drug columns, or a metaboliser class | the drug section, grouped by drug, in `longevity_report.html.j2` |

Two further kinds exist in the format without a shape of their own yet: **"how much" results**
(repeat length, copy number, mitochondrial fraction: a measurement falling into a bin) and
**polygenic scores**, which the PRS tab handles. When one of these gets a report section, it gets its
own partial, not a branch in an existing one.

**Weights are a per-variant idea.** A phenotype module authors none (`weighting: scale: none`), and
`direction` on a combined result is used only when the whole result carries a meaning (HFE
C282Y/C282Y is a risk genotype). Where it is used, the report shows it as words, never as a score or
a colour.

**A combination module needs its rule in words.** Write a `## How this works` section in
`README.md`: how the versions of each gene combine into the result, in the same plain voice as the
conclusions. The report shows it before the results. The exact version of the rule (which bases
define each allele, and the full allele-pair table or activity values and bins) is generated from the
module's tables into each result's **More details** fold, so it never needs to be written twice.

**The module's own title and description are headings a lay reader sees.** just-dna-lite renders every
module as its own report section, headed by `module.title` (or `report_title`) with `module.description`
under it. Write them plainly (*"APOE type (ε2, ε3, ε4)"*, *"Which versions of the APOE gene you carry"*),
never as a build note (*"The APOE epsilon haplotypes, defined by rs429358 and rs7412"*).

## Three layers, three homes

| Layer | Answers | Lives in | Report shows it |
|---|---|---|---|
| **1. Result** | what does my DNA show? | `diplotypes.phenotype`; first sentence of `conclusion` | the result headline, start of a row |
| **2. What it means** | so what, how common, how sure, anything practical? | rest of `conclusion` | paragraph under the result |
| **3. More details** | how was it determined, how do I check it? | `haplotypes.csv`, `studies.csv`, `README.md`, `weighting:` | the *More details* fold, study tables |

**Layers 1 and 2 carry no layer-3 material**: no rsID, HGVS name (`c.261delG`), subtype code (`O1`,
`*2`, `PAV`), coordinate, p-value, odds ratio or tool name.

**Every term is explained where it first appears, in that conclusion.** A reader sees their own
result and nothing else, so a term explained in another result or in `## How this works` is
unexplained for them. A name the reader will meet elsewhere (APOE's ε4 version, C282Y on an HFE lab
report, the FUT2 gene) may appear, and the same conclusion says what it is when it first comes up:
*"The APOE gene comes in three common versions, called ε2, ε3 and ε4. They differ from each other at
two places in the gene."* Most readers do not know that ε4 is a combination of two DNA changes, or
that C282Y is a one-letter change. A term nobody outside a lab uses does not belong in a conclusion. **Layer 3 is complete and exact**, because for a professional it *is* the result; it is
folded, not trimmed.

## The failure this prevents

A real report, before:

> **RHCE** · *Ambiguous* · Ce / ce — C+ c+ E- e+ · Ce / cE — C+ c+ E+ e+ · Compiler notes:
> module_not_closed · positional_identity_contradicted
>
> *Conclusion:* GA variant is associated with increased risk of hyperhomocysteinemia and thrombophilia.

Every word was true and almost nobody could read it. After:

> You carry one copy of a common MTHFR variant, which slightly lowers how well your body processes
> folate. On its own it has little effect: about 4 in 10 people in Europe carry one copy, and most
> never have a problem. Studies link it to a small rise in homocysteine (an amino acid in the blood)
> and, weakly, to blood clots. It is not a reason to take supplements unless a doctor has measured
> your homocysteine and found it high.

## A conclusion, in order

Full sentences, as many as the idea needs: usually three to seven, roughly 50 to 160 words. **Simple
is not short.** *"Two ε3 alleles: the reference genotype most risk estimates are expressed relative
to."* is short and nobody without a genetics degree can read it. Say what the reader has, what the
gene does, how common it is, what it means in practice, and the main limit. **Make both audiences happy**: the lay reader understands the result and
learns something, the professional finds nothing wrong. And **always look for two things**: the
practical implication, and an interesting fact the reader probably never knew.

1. **The result, about the reader, in plain words.** *"You have blood group AB."*
2. **What it means**, in everyday terms.
3. **How common**, as a natural frequency for a named group (*"about 4 in 100 people in Europe"*), or
   a range across populations. With no sourced figure, *common* / *uncommon* / *rare*; never an
   invented number.
4. **The practical implication, when it is clear.** State it: blood group O is the universal
   red-cell donor, AB the universal recipient. Don't drop a useful sentence for sounding too
   practical (bounds below).
5. **An interesting, sourced *why***: blood groups are really about the immune system (you carry
   antibodies against the markers you lack, which is why mismatched blood is attacked). One accurate
   sentence, not trivia.
6. **How to check it yourself**, when there is a way (a donor card, a routine test, an observable
   trait). Teaching modules especially.
7. **How sure, and the one limit that matters most.**

Rules: full sentences, second person, a necessary term explained in the same sentence and an
unnecessary one dropped, one idea per sentence, direction named plainly (*raises*, *lowers*, *no
known effect*, never a bare *"associated with"*), size before the disease name, and *not destiny*
said whenever most carriers are unaffected. No fear or hype words.

**Certainty ladder**, the same words in every module: *well established* (replicated or guideline),
*likely* (consistent, not definitive), *early evidence* (few or small studies), *not known* (say so,
do not guess a direction).

## Practical notes: allowed, bounded

- **Allowed** when the evidence is solid: everyday context and when to act. *"If you donate blood, the
  blood service tests your group anyway."* *"People with this result often find coffee late in the
  day keeps them awake."*
- **Name who decides** anything medical: doctor, pharmacist, midwife, blood service.
- **Never** tell a reader to start, stop or change a medicine, supplement, diet or treatment, or imply
  DNA replaces a lab test. Drug response: *"tell your doctor or pharmacist about this result before
  starting X"*, not *"avoid X"*.
- A weak tip is worse than none. Leave it out.

## Key content first; caveats last

The reader came for their result, and a report that leads with disclaimers teaches them to skip text.
The report template puts general disclaimers, privacy notes and page help at the bottom; a module's
job is the same inside each text: **the result first, what it means next, its limits last.** Never
open a conclusion with a caveat, a disclaimer or "this is not medical advice" (the report says that
once, at the bottom). A caveat that changes what *this* result means (*"a lab test should confirm
the C marker"*) is part of the result and is its final sentence.

## Phenotype labels

A label is layer 1 on its own: something a person would say, up to about six words. *Blood group O*,
*RhD negative*, *Fast caffeine metabolism*, *Non-secretor*. Standard notation only after a plain
anchor (*Rh markers C+ c+ E− e+*). Never a code (`B/O1`, `*1/*2`, `PAV/AVI`).

**Give every common name.** When a result is known by different names in different regions or
traditions, the label carries both and the conclusion says so once: *Blood group B (III)*, "called
group III in some countries". Our readers are international; a result they cannot recognise in their
own nomenclature reads as a wrong result.

**Allele pairs that give the same result share an identical label and an identical conclusion.**
The report groups candidates by label and shows each result once; two different conclusions under
one label read as a contradiction. Anything that differs between the pairs (carrier status, which
allele) is layer 3, and the conclusion can say where to find it (*"which you have is listed under For
professionals"*).

**Write every possible result for someone who might have it.** When a file cannot settle a result,
the report lists all possible results with their conclusions, so a conclusion is also read by people
who do *not* have that result.

## Phenotype modules: patterns that recur

A phenotype module (haplotypes + diplotypes) lists **several possible results** whenever a file cannot
settle one, so its text is read in ways a single-variant row never is. The template handles the
mechanics (it groups allele pairs by label, sorts firm results first, prints sentences that every
listed result shares only once, and drops the per-result "cannot confirm" tag on a card that already
says the file cannot read it). The author's side:

- **Put the distinct sentence first, the shared background after, and word the shared part
  identically** across sibling results. The report factors out only sentences that match exactly;
  "Rh markers are proteins…" in one row and "The Rh markers are proteins…" in another prints twice.
- **Every result must read correctly as a possibility.** When the file cannot decide, a reader sees
  all of them, most of which are not theirs. Avoid sentences that are only true if this is the
  reader's result *and* would alarm someone for whom it is not.
- **Make the label carry the topic when the gene symbol does not.** A card is headed by the result
  and tagged with the gene symbol; *RhD negative* explains itself, *C+ c+ E- e+* does not, so it
  becomes *Rh markers C+ c+ E- e+*.
- **A gene the file cannot read still earns its card**: the possible results are shown under *What
  the possible results mean*, so each one should tell the reader what it would mean and what to ask a
  lab about.

## Independent review before publishing

The writer is the worst judge of both readability and accuracy, because they know what they meant.
Before a module is published, and again whenever its conclusions change substantially, run **two
reviewers as separate agents, with deliberately different inputs**. Review the **rendered report**
from a trial install on real genomes where you can (repetition, ordering and missing context only
show up rendered), plus the full list of result texts, since three genomes never show every result.

**1. The lay reader.** Input: only the plain part of the rendered reports (More details folds
hidden) and every result text. No sources, no web, no expertise. Brief: play an adult with no
science training who remembers school biology vaguely. Output:

- each person's result restated in their own words (**the pass test**: if a restatement is wrong,
  the text is wrong, however accurate it is);
- every word or sentence they would not understand or would misread, quoted, with a plainer wording;
- anything repetitive, contradictory, alarming or machine-sounding, quoted;
- what they would want to know next;
- a verdict and the single most important fix.

**2. The scientific reviewer.** Input: the rendered reports including the folds, the spec tables,
`README.md`, and literature access (PMIDs only from a search result whose title was read). Brief: a
specialist in the module's field checking whether any simplification became **wrong or misleading**,
not whether it is simple. Output:

- errors, with a corrected sentence just as plain;
- misleading or overstated claims, corrected;
- missing caveats that matter for safety or correct understanding (not expert-only caveats);
- mapping errors in the tables (an allele pair given the wrong result);
- practical notes that cross into medical advice;
- claims that could not be verified;
- a verdict.

**3. A family check, when related genomes are available.** Inheritance is ground truth that needs no
outside source: a child carries one allele from each parent, so the calls on a family must fit
together at every site and for every combined result. just-dna-lite's `scripts/family_check.py <module> --mother …
--father … --child …` checks both levels and reports a site or gene that was not readable in
everyone as *unchecked*, never as a pass. A violation means a wrong call, a sample swap or
non-paternity. It is the only one of the three checks that can catch a wrong **call** rather than
wrong **text**, but note what it cannot catch: an allele definition that is wrong in the same way for
everyone (the rs609320 E/e swap this module first shipped with) is still perfectly Mendelian.

**Reconcile as the author.** Fix every error. Take readability fixes that lose no accuracy. When the
two reviewers pull in opposite directions, keep the accurate claim and find a plainer way to say it;
if that fails, that is one of the one or two questions worth asking the module author. Then record
the review: a line in `README.md` (date, what was checked, what changed) and an `authorship:` entry
with `role: reviewed` and `kind: [ai, agent]`. An AI review is recorded as exactly that, never as a
human one.

## Plain words

| Instead of | Write |
|---|---|
| genotype | your DNA letters at this position; your version |
| allele | version of a gene; DNA letter |
| heterozygous / homozygous | one copy (from one parent) / two copies (one from each parent) |
| variant, SNP | a spot where people's DNA commonly differs |
| haplotype / diplotype | a version of a gene / the pair of versions you carry |
| phenotype | trait, result |
| VCF, callset | your DNA file |
| phase | which letters you inherited together from the same parent |
| odds ratio | a natural frequency: "about 3 in 100 instead of 2 in 100" |
| penetrance | not everyone with this version develops the condition |
| pathogenic / VUS | known to cause disease / effect not yet known |

## Asking the module author, sparingly

The person you build a module with usually knows what they want it to focus on. **Ask only when it
is genuinely unclear and the answer changes the text**: at most one or two questions, once, when you
start writing conclusions, each with a sensible default so a one-word answer works.

- Worth asking: two possible angles (*"lead the caffeine results with sleep, or with sport?"*), a
  borderline practical note that depends on the audience (*"is this for people planning a pregnancy,
  or general curiosity?"*), a term with no clean plain equivalent.
- Not worth asking: anything the sources settle, wording you can simply get right, or approval of
  each conclusion. An author who cannot read a genetics paper cannot referee your biology either;
  [`module-start`](../module-start/GUIDE.md) says the same about scientific cells.

## Before you compile

- [ ] Every label is something a person would say; no codes; every common regional name is given (blood group B (III)).
- [ ] Every conclusion opens with the result, about the reader.
- [ ] Clear practical implications are stated; an interesting, sourced *why* is there where one exists; a way to check it yourself is named where one exists.
- [ ] No rsID, HGVS, subtype code, coordinate, p-value or odds ratio in labels or conclusions.
- [ ] Every term a lay reader may not know (ε4, C282Y, FUT2, *secretor*) is explained in the same conclusion, at its first mention.
- [ ] `module.title` and `module.description` read as plain headings, not build notes.
- [ ] Every risk has a size and a frequency, and says *not destiny* where true.
- [ ] Every practical note is solid and names who decides anything medical; nothing tells the reader
      to change a medicine, supplement, diet or treatment.
- [ ] Same result, same label, same conclusion.
- [ ] `README.md` carries the full More details layer: sites, alleles, sources, limits, origin.
- [ ] A combination module has a plain `## How this works` section in `README.md`, and authors no weights.
- [ ] No conclusion opens with a caveat or disclaimer; a result's own caveat is its last sentence.
- [ ] Read three conclusions aloud. If one sounds like a database row, rewrite it.
- [ ] The two independent reviews (lay reader, scientific reviewer) ran on the rendered report, their findings are reconciled, and the review is recorded in `README.md` and `authorship:`.

**Nothing checks any of this.** `lint_rows` and the compiler test a conclusion's genotype tokens, not
its readability. This checklist and the two independent reviews above are the only gates, so run them. Every rewrite of an authored conclusion
is an edit, so log it with `record_override` (one table-scope record for a whole-table rewrite).
