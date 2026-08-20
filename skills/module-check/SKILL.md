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
`variants.csv`, so a binning row's `gene` or `trait_efo_id` is **never checked for currency**. The same
shape recurs across the toolchain — `enrich-pgx` never opening `diplotypes.csv`, `stats.genes` computed
from `variants.csv` alone, a redundancy advisory keyed on a bare column name. **Naming a check without
naming its scope is how a reader over-trusts it.**

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

🚧 **ROADWORKS — nothing on the authored side can see a quote repeated across every row citing a
paper.** Two spec directories differing *only* in `provenance_quote` — one honestly located, one all
article titles — come back **byte-identical** from `registry_check(literature=true, strict=true)`:
`verdict: true`, every finding list empty. `lint_rows`, `validate_module` and `compile_module` say
nothing either. Four published modules reached production this way carrying **3668** title-quotes.
**Guard until this lands (`RM17`):** group `studies.csv` by `pmid` yourself and count the **distinct**
non-empty quotes. One distinct value across many rows is the signature — and it is the *shape* that
matters, not the string, because the next variant of it is one real sentence pasted onto 2,000 rows.

## Counting findings honestly

⚠️ **CHECK — deduplicate before you count.** The `faf95` arithmetic warning reaches
`manifest.compilation.warnings` **twice**, because the check runs in `validate_spec` and again in the
compile-side `_frequency_checks` with no filter. Measured: 15 warnings, 14 distinct. Upstream **RM106**.

⚠️ **CHECK — a duplicate `(source, layer)` row in `licensing.csv` compiles green under `--strict`**,
even one carrying the opposite `commercial_use`. `SourceRow` is in the drafter's dupe map and absent
from the compiler's. **Guard:** sort on `(source, layer)` after any hand edit. Upstream **RM107**.

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
- **The reason that outranks a source**, whenever you do edit against one.

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
