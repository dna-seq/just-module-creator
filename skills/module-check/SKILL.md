---
name: module-check
description: >-
  Compare what the module claims against what the sources say, and record that the question was put.
  Covers which checks exist and what each one reads, the two that deliberately never escalate, how to
  tell a check that was skipped from one that ran over nothing, the attestations that record a check
  nobody could have run, the three passes whose strict gate fires on the usual answer, and the
  mismatches that are decisions rather than defects.
  Triggers: "cross-check", "verify", "check identifiers", "clin_sig conflict", "ACMG SF", "gene
  locus", "validate strict", "why is this a warning", "verification.json", "unverifiable", "skipped",
  "subjects", "did the check run", "strict failed on correct data".
---

# Stage 5 — cross-check what you asserted

**Lifecycle stage:** 5. The second stage that fetches, and the one whose output is a **record** as much
as a verdict.

This stage turns an assertion into a **checked** assertion, and writes down which checks ran — so a
later reader can tell silence from a pass.

## What a finding is, and what it is not

**A mismatch against a source is not a defect report.** Archives lag the edge: a paper is retracted, a
meta-analysis refutes it, a bigger cohort moves the call. A row that disagrees with ClinVar may be
**the module being right and current while the archive is stale**. Conforming it to the source silently
*degrades* the module — and the check then agrees with itself and reports green.

So this stage produces **findings**, and where a human must choose, **decisions**. It does not conform
rows to sources. That is a statement about *evidence*, not a rule against writing: this layer writes,
and editing against a source is legitimate **when there is a reason that outranks the source and that
reason is written down.** An outranked row keeps warning — *somebody decided this* never means green,
because two releases on nobody remembers whether the retraction that motivated it was itself
superseded.

## Before the checks: what is decidable without a source

```
audit_module(spec_dir="spec")           # offline, writes nothing; decisions | clear | not_computed
```

Every gate below this line asks a source. `audit_module` asks the arithmetic instead — the questions
answerable from the authored files alone, which is why it is not a check and does not belong in
`verification.json`. Two unattended curation passes over eighteen real modules found **every** genuine
defect by hand-writing exactly this arithmetic while `validate_module`, `compile_module`, `lint_rows`,
`registry_check` and `registry_validate` all returned green. They were right to: those tools answer
*"will this build?"*, and the modules built.

What it asks: whether `weighting:` says what the `weight` column means (in both directions — an empty
weight column and a deliberately unweighted module are the same bytes); whether any recorded check ran
over zero subjects or was skipped; whether a check counted disagreements and kept none; whether an
`effect_size` is really the Z-statistic of its own p-value under a label saying otherwise; and whether
clinical claims have a paper behind them, over every table that can carry `clin_sig` rather than
`variants.csv` alone.

Its three lists are three different claims, and the third is the one to read carefully.
**`not_computed` is not a pass** — the file that signal reads is absent, so nothing about it is
established. A signal is not a verdict on the work either: a module that raises one is out of date or
undeclared, not broken.

## The checks, and what each one actually reads

```
check_identifiers(spec_dir="spec")      # trait CURIEs (OLS4), gene symbols (HGNC), gene <-> chromosome
```

```bash
just-dna-enricher check-acmg spec/ --sf-list acmg/   # acmg_sf vs the ACMG SF list
just-dna-enricher pgx spec/                          # function_status vs PharmVar and CPIC
just-dna-enricher clinpgx check spec/ --snapshot cp/ # pharm_variants.csv vs the ClinPGx snapshot
```

The reference-base, `clin_sig` and rsID-currency checks are folded into `enrich_module` rather than
living here — `module-enrich` owns them, because only that tier holds a reference sequence.

**Read `gene_locus_conflicts` even when `stale` is empty.** A fabricated row usually pairs a real gene
name with a real-but-unrelated rsID: both halves pass their own check, and only the *relationship* is
false. If `gene_locus_check_skipped` is non-null the comparison never ran, which is not a pass.

⚠️ **CHECK — a check is only as wide as the table it reads.** `check_identifiers` reads
`variants.csv`, so a binning row's `gene` or `trait_efo_id` is **never checked for currency**. The
shape recurs across the toolchain and two instances of it closed in 0.6.6 — `stats.genes` now reads
every gene-bearing table, and a redundancy advisory now says when its checker cannot see your table —
while `enrich-pgx` still never opens `diplotypes.csv`. **Naming a check without naming its scope is how
a reader over-trusts it**, and the fix for the reader is the same either way: ask what the checker
loads before reading a green run as agreement.

## Severity, and the two that never escalate

`--strict` escalates a finding to a refusal; `--best-effort` (the default) warns and carries on.

**Two deliberately never escalate — the ClinVar `clin_sig` and the allele-function comparisons.**
Failing would make the format arbitrate between expert panels. Two opinions differing is not a factual
error, and ClinVar is not truth: a curator who has read the primary literature may correctly disagree
with a one-star submission. The finding carries ClinVar's **review-star count** so you can weigh it.

🚧 **ROADWORKS — three passes fire their strict gate on the *usual* answer**, so `--strict` there is a
run that fails on correct data:

| Pass | The gate fires when | Reality |
|---|---|---|
| clinical assertions | a resolved allele has no ClinVar record | true of most alleles — the error says so itself |
| GWAS effects | `unusable` or `p_value_underflows` | `hfe_hemochromatosis`, a shipped flagship, fails today on **six** Catalog underflows |
| gene metrics | gnomAD has no constraint row for a gene | ordinary |

**Guard:** run these three at their default; if a pipeline sets `--strict` globally, exempt them **by
name**, and never read the failure as *"the module is wrong"*. The GWAS ladder has no test coverage in
either direction.

🚧 **ROADWORKS — `enrich_pgx(mode="strict")` does not raise.** `mode` is stored and never read, while
`PgxEnrichmentError`'s docstring and the CLI's `--strict/--best-effort` help both advertise a failure.
**Guard:** never gate a pipeline on it; read `PgxResult`'s conflicts yourself.

## `check-acmg` needs its list, or it answers nothing

NCBI's page serves SF **v3.2** while ACMG has published **v3.3** — it lacks `ABCD1`, `CYP27A1` and
`PLN`. Without `--sf-list` every disagreement comes back `unverifiable` rather than as a finding, and
`--strict` will not fail on one. Build the snapshot once:

```bash
just-dna-enricher acmg build <workbook.xlsx> --out acmg/
```

and the check also stops needing the network. **`acmg_sf` is gene-level list membership**: if the row is
about a variant in a listed gene that is not itself a reportable finding, leave the cell **blank** —
blank means *not stated*, and ACMG scopes some entries more narrowly than the gene.

## Telling a skipped check from a check that found nothing

**A check that could not run is not a check that passed.** The record distinguishes them and you must
read it that way:

| In the record | Means |
|---|---|
| `subjects: 0`, **no** `skipped` key | it **ran**, over nothing |
| a `skipped` key | it **did not run**, and the key says why |
| `unchecked` / `null` in a report | the question was never put |

Two `clin_sig` skip reasons that read alike and are not:

- *"this module declares it was drafted from the very snapshot the check reads"* — your `panel:` block
  pins the release the rows came from, so every value would be matched against its own source and the
  answer would be zero whatever the data said. **A guaranteed zero looks like evidence without being
  any.** Drop the pin the moment a human edits those calls.
- *"no ClinVar snapshot this run"* — nothing was compared because there was nothing to compare against.

**15 of 17 check members have live emitters** (RM72, enricher 0.6.4). The widely-cited *"five of
seventeen"* is stale.

## Attestations that record a check nobody could have run

The record is only worth what its narrowest claim is worth, and three known cases inflate it:

1. **`enrich_pgx` grading CPIC's own table** — a draft pinned to a source, compared against that source.
2. **`hints._flag_advisory_columns` naming checkers that cannot see the table quoted** — the advisory is
   keyed on a bare column name, so it prints on tables its named checkers never open.
3. **`enrich_facts` collapsing "no constraint published" into "not asked"** — two different states in
   one cell.

**Guard:** when you read a green attestation, ask **could this check have failed?** If not, it measured
nothing, and that is worth saying in the README rather than leaving for a reviewer to discover.

### The one check the compiler cannot make, and this layer does

**Nothing upstream can see a quote repeated across every row citing a paper.** Two spec directories
differing *only* in `provenance_quote` — one honestly located, one all article titles — come back
**byte-identical** from `registry_check(literature=true, strict=true)`, and `compile_module` says
nothing either. Four published modules reached production that way carrying **3668** title-quotes.

**So this layer computes it** (`RM17`). `lint_rows` and `validate_module` both report a **warning**
naming any PMID whose every quoted row carries the same passage, with the row count and the first few
words so you can recognise the paper. It reads `studies.csv` alone, offline, and deliberately not
`literature.csv`, whose counters are stale on every module that has the problem.

**It is keyed on the shape, not the string** — the next variant of this is one real sentence pasted
onto 2,000 rows, and a rule that only caught the title would miss it. Confirming that the repeated
string *is* the title needs `lookup_citation`, a network call, so it belongs where a round trip is
already being paid for rather than in the offline linter.

**Read it from `authored_findings`, not from `warnings`.** `validate_module`'s `warnings` transport
upstream's own strings field-for-field, and mixing a finding *we* computed into that list would make
it impossible to tell which layer spoke. Every finding carries `source`: `upstream` or
`just-module-creator`. An authored finding does **not** move `valid` — the compiler would still build
the module, which is the whole point of it being visible here.

**A blank quote is not the defect.** The remediation that found this located passages for 21 of 859
rows — a 2–3% yield, *inverse* to row count — so mostly empty cells is the honest result, and the
check counts only rows that carry a quote.

## Counting findings honestly

**The `faf95` arithmetic warning used to reach `manifest.compilation.warnings` twice** — the check
runs in `validate_spec` and again on the compile side, and the compile side had no filter. Fixed in
compiler 0.6.6 (upstream **RM106**), so a module recompiled under it publishes one fewer warning with
no text changed. If you pinned a warning count against an older artifact, that is why it moved.

**A duplicate `(source, layer)` row in `licensing.csv` is an ERROR** since compiler 0.6.6 (upstream
**RM107**), in `validate` and in `compile` alike, in both modes:
`licensing.csv: duplicate row for key ('clinvar', 'annotation')`. It used to pass silently, even
carrying the opposite `commercial_use`, so an inherited module may carry one and stop compiling on the
first run under this toolchain — that is the pair being noticed, not the module breaking. Which of the
two rows is right is a decision, not a merge: `licensing.merge_sources_csv` keeps the LAST row under
the key, which is exactly the wrong tool where the two disagree. One source at two layers is
untouched, which is why the key is a pair.

**Findings aggregate by reason with a count**, never one per row. A wall of near-identical warnings is a
bug worth reporting upstream rather than filtering.

## Run the checks after you close, not before

`close_module` **drops** any check record attested over bytes that no longer match — correct, because
carrying it across would re-bind a claim to different bytes — and it reports the loss only in
`CloseResult.dropped_checks`, which is not a compile warning and never reaches `manifest.verification`.
**15 of 16 reference examples record zero checks.**

So the order is: close, then check, then read `dropped_checks`. `module-close` owns the closure itself.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** building the ACMG snapshot so the check can answer at all; exempting the
three passes above from a global `--strict`; re-running a check that reported `skipped` for a reachable
reason; deduplicating a doubled warning before reporting a count; dropping a `panel:` pin once a human
has edited the calls it covers.

**Surface it, and let a pilot settle it:**

- **Every `clin_sig` and allele-function disagreement.** These are two authorities differing, and the
  module may be the current one.
- **Every `gene_locus_conflict`** — a lookup cannot know *which half* is wrong, and fixing the gene and
  fixing the rsID give different modules.
- **A stale identifier.** A rename is what an author needs to *see*; rewriting it destroys the evidence
  that it moved.
- **Whether an attestation that could not have failed should be published as one.**
- **The reason that outranks a source**, whenever you do edit against one — and once you have
  decided, **record it**: `record_override(spec_dir, variant_key, field, authored_value, source_name,
  reason, recorded_by)` writes it into `provenance.json` and logs the move into
  `logs/authoring.log`. Call it **in response to a reported mismatch, never ahead of one**: a row
  markable as outranked before the check runs would destroy the only signal that catches the other
  pathway, which is an ordinary hallucination or a stale recollection. It records; it does not
  silence. `review_queue` reads the records back, and `module-revise` consumes that queue.

## What this stage cannot do

**It cannot tell you the module is true.** It compares cells against archives; both can be wrong, and
the archive can be behind.

**It cannot check what it does not read.** Bin rows, diplotype-only modules and any table outside a
check's scope are simply unexamined — and look identical to examined ones.

**It cannot see a vacuous cell.** A quote that is a title, a coordinate copied from the source that
verifies it, a `false` written where the terms were unknown: every one passes.

**It cannot repair, and neither should it.** The authored value survives so the evidence of the
disagreement does.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action:

- *"`unverifiable:` …"* and *"the list read is ACMG SF v3.2 but v3.3 is published"* — **not a finding
  about your module.** Build the snapshot.
- *"clin_sig cross-check not run: this module declares it was drafted from the very snapshot the check
  reads"* — working as intended, and more honest than a guaranteed zero.
- *"clin_sig cross-check not run: no ClinVar snapshot this run"* — a different sentence with a different
  meaning.
- *"`clin_sig` differs from ClinVar's"* and `--strict` did not fail — deliberate.
- *"N ClinVar citation(s) skipped: the id ClinVar filed under PubMed is not a PMID"* — a source defect,
  counted rather than listed.

## Where to go next

| You need | Load |
|---|---|
| the reference-base and rsID-currency checks | `module-enrich` |
| the closure these records bind to | `module-close` |
| what a record means, field by field | `module-tables` → `references/verification.md` |
| the tables that record rather than adjudicate | `module-tables` → `references/{clinical_assertions,gene_validity}.md` |
| what may honestly go in a quote | `find-evidence` |
| a module that already exists, and where a reviewer starts | `module-revise` |
