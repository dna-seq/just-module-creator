---
name: module-draft
description: >-
  Draft rows from a source that publishes them — ClinVar gene panels, CPIC star alleles, ClinPGx drug
  response — and read the report honestly. Covers appends-never-rewrites, what `differs` means and why
  the source may be the stale side, partial rows and the placeholder, review-star floors, the licence
  position a draft asserts, the alleles a provider silently drops, and what a re-draft cannot repair
  on a module drafted before a drafter fix.
  Triggers: "draft from ClinVar", "draft a panel", "draft from CPIC", "ClinPGx", "already_present",
  "differs", "REPLACE placeholder", "min_review_stars", "re-draft", "star alleles", "diplotypes",
  "added 0 rows", "function_status blank", "panel block".
---

# Stage 2 — draft from a source that publishes the table

**Lifecycle stage:** 2. Optional — plenty of good modules are authored from papers with no drafter
involved at all.

Letting a provider write what it can, and leaving **loudly incomplete** what only a pilot decides.
Drafting appends and never mutates a cell, which is what makes this the one stage designed for
repetition.

## The three drafters

```
draft_from_clinvar(spec_dir="spec", genes=["HFE"], use="non_commercial", dry_run=True)
draft_from_cpic(...)        # extended tier — a corpus sizes it
draft_from_clinpgx(...)     # extended tier, and inject-only: build the snapshot first
```

`draft_from_clinvar` is **essentials**; the two PGx drafters are **extended**, because a whole-source
draft is sized by how much has been published rather than by what you named.

**`use` is required on all three and has no default.** `unstated` silently skips licence-bearing
sources; anything else asserts a licence position you may not hold. If a draft returns
`skipped=true`, the terms were not satisfied and **nothing was fetched** — that is the gate working,
and **re-running with a different `use` to get past it is fabricating a licence position.**

The CLI equivalents, for driving it directly:

```bash
just-dna-enricher draft-panel spec/ --gene HFE --use non-commercial              # ClinVar → variants.csv + studies.csv
just-dna-enricher draft spec/ --gene CYP2C19 --drug clopidogrel --use non-commercial   # CPIC → the 3 PGx tables
just-dna-enricher draft-clinpgx spec/ --snapshot cp/ --drug simvastatin --use non-commercial
```

`draft-panel` downloads the published ClinVar snapshot when you have no local one; add
`--snapshot cv/ --offline` to use one you built. `--min-review-stars` defaults to **2** (multiple
submitters, no conflicts) and `--max-citations 3` drafts study rows from ClinVar's literature links —
which is what makes a panel compilable at all, since a variant row needs grounding evidence.

**Name your floor.** A panel mixing a 0-star submission with an expert panel *without saying so* is
worse than one that declares where it drew the line; put the floor in the README.

`draft-clinpgx` downloads nothing — build the snapshot first with
`just-dna-enricher clinpgx build --out cp/ --use non-commercial`.

## Reading the report

**Drafting appends and never rewrites a cell.** A row whose key already exists comes back as one of:

| | Means | What to do |
|---|---|---|
| `already_present` | nothing happened and nothing needed to | **inert.** Ignore it |
| `differs` | **the source disagrees with something you already authored** | a decision — see below |
| a **partial** row | matched on *identity* columns rather than the natural key | nothing; a re-draft after a human filled a stubbed `genotype` adds no duplicate |

**`differs` is the interesting one, and it is not a defect report.** The row is left unchanged
deliberately, because only a pilot knows which side is right — and **the source is not automatically
the newer or better one.** An archive lags the edge: a retraction, a refuting meta-analysis, a
reclassification ClinVar has not absorbed. Conforming your row to the source silently can *degrade* the
module, and the cross-check will then agree with itself and report green. If you do edit against it,
**the reason that outranks the source gets written down**, and the row keeps warning.

**The warnings are the interesting output** — skipped rows, aggregated counts, and the allele pairs you
need for stage 3. Two you will meet on a real ClinVar panel and should not chase:

- *"N row(s) on non-diploid contigs were written with a single-allele genotype"* — the provider filling
  a cell where nothing was open to decide. MT is haploid and chrY outside the PAR is hemizygous.
- *"N ClinVar citation(s) skipped: the id ClinVar filed under PubMed is not a PMID"* — a defect in the
  source. A few hundred of ClinVar's citation ids are nine digits where a PMID is eight. Counted, not
  listed, and nothing to fix by hand.

**A drafted panel does not need a zygosity decision on every row.** `draft-panel` writes the sole
expressible genotype where the contig leaves nothing open, decided **per locus**. If you expand
placeholders into both zygosities, expand *only* what is still a placeholder — do not key that off the
contig yourself.

## Curate before you enrich — the placeholder is deliberate

A drafted row leaves `<<REPLACE>>` in the cells only a pilot can decide, and that placeholder makes
**every** loader refuse the file, `enrich_module` included. That is deliberate: forward resolution is
allele-aware, and a placeholder genotype would silently skip the allele filter on exactly the
one-to-many rsIDs that need it. **So you cannot "enrich first to see the alleles" — and you do not need
to: the draft report prints the allele pair for each stubbed row**, and `lookup_variant` gives you the
same for a row you are writing by hand.

## Pin the release you drafted from

Add a `panel:` block naming the source, the release and its hash. Then `enrich` recognises that its
ClinVar `clin_sig` cross-check would be comparing your values against **the file they came out of**,
skips it, and says so — rather than reporting a zero it could not have avoided. A guaranteed zero looks
like evidence without being any.

**Leave the block out the moment a human has touched those calls**, and the check runs as usual. That is
the whole point of the pin: it is a statement about where the values came from, not a way to quieten a
check.

## What the PGx drafters drop, silently

🚧 **ROADWORKS — `pgx_draft` drops 763 of CPIC's 1,361 alleles**, 693 of them names the model would
accept. The drafter checks `STAR_ALLELE_PATTERN` while the table itself checks only non-empty and
no-whitespace. **Eleven genes lose every allele** — `ABCG2`, `CACNA1S`, `CFTR`, `DPYD`, `G6PD`,
`HLA-A`, `HLA-B`, `IFNL3`, `MT-RNR1`, `RYR1`, `VKORC1`. `draft --gene DPYD` emits 248 skips and adds
**0 rows**.

**And a zero-row draft writes no `SourceRow` either**, so the module can end up with **no
`licensing.csv` entry for CPIC at all** — and `licensing.csv` is the file the compile licence gate keys
on. **Guard:** for those genes, hand-author the table from CPIC's own, **write the source row
yourself**, and never read `added 0 row(s)` as a clean run.

🚧 **ROADWORKS — 408 of CPIC's 1,275 graded alleles (32%) map to a blank `function_status`, with no
warning.** `ivacaftor responsive` (103), `III/Deficient` (37), the MT-RNR1 aminoglycoside-risk phrases
(25 rows across four strings, including a `Normal risk…` / `normal risk…` case-variant pair), `IV/Normal`
(5) and others. **A blank is unknown**, so the later comparison skips the row — and a blank is
indistinguishable from *"CPIC has not graded this"*. **Guard:** count blank `function_status` cells after
every `draft --gene` and check each against CPIC's table.

**Two skip families are un-aggregated, not one.** Measured on a single `--gene DPYD` run: 84 lines from
the allele-function loop and 164 from `_haplotype_rows`. Expect volume; read the counts rather than the
lines.

## Star alleles

- **A large star-allele gene needs `draft --allele`.** *n* alleles is *n(n+1)/2* diplotypes; unfiltered
  CYP2D6 is **16,290 rows, 73% `Indeterminate`**. Your real bound is the allele set your caller emits —
  **six alleles turn those 16,290 into 21.** The filter covers all three PGx tables, `*1` is always kept,
  and it takes a single `--gene` because a star name is gene-scoped.
- **A star allele can be *used* without being *defined*.** If `haplotypes.csv` never defines an allele
  that `diplotypes.csv` or `allele_function.csv` names, a caller can never emit it and every row about it
  is dead. Warned, not blocked — leaning on an external caller's definitions is legitimate.
- **CPIC recommendations are keyed by (phenotype, drug, *population*)**, and the populations disagree:
  the same Poor Metabolizer diplotype is `strong` in one clinical context and `moderate` in another.
  **Every clinical context is drafted**, kept apart by `clinical_context`, and the **consumer** picks at
  query time — which is the right owner, since which indication a patient is being treated for is
  knowable then and not at authoring time. So `population` **filters, it does not decide**: leave it
  unset to get them all. An unrecognised value is an error listing what CPIC actually publishes, so a
  typo cannot quietly draft nothing.
- **`recommendation_strength` is CPIC's; `evidence_level` is PharmGKB/ClinPGx's.** Different axes — fill
  only the one your source states.
- **CPIC activity scores are inequality strings (`"≥3.0"`), not numbers**, so they do not drop into
  numeric bin bounds; and CPIC's `n/a` means *not scored* — an absence, so leave the cell blank.
- **A PGx module carries no `variants.csv`, and that is correct.** No `variants.csv` means no
  `studies.csv` requirement either.

🚧 **ROADWORKS — `enrich-pgx` never opens `diplotypes.csv`.** Both PGx cross-checks are driven from
`haplotypes.csv`; without that file they early-return. **A diplotype-only module therefore passes every
gate with no cell of it compared to anything, and looks identical to a checked one.** **Guard:** ship
`haplotypes.csv` and `allele_function.csv` beside the diplotypes, or say in the README that the rows are
unverified.

🚧 **ROADWORKS — `enrich_pgx(mode="strict")` does not raise.** `mode` is stored and never read, while
the `PgxEnrichmentError` docstring and the CLI's `--strict/--best-effort` help both advertise a failure.
The *reporting* behaviour is deliberate — the format will not arbitrate a PharmVar/CPIC disagreement —
but the ladder does not exist. **Guard:** never gate a pipeline on it; read `PgxResult`'s conflicts and
decide in your own code.

## Re-drafting a module that was drafted before a fix

**A drafter fix does not reach a module already drafted**, and the two shapes need opposite
remediations:

| The old bug | A plain re-run | What you must do |
|---|---|---|
| **skipped** rows | converges exactly | re-run, and you are done |
| **wrote** rows under an identity that has since **moved** | restores the lost records and **leaves the collapsed ones beside them** | re-run, then delete the stale rows by hand |

Measured on MLH1 after enricher 0.6.3: the ClinVar identity fix left **0 missing, 31 stale**; the
ClinPGx fix only skipped, so it converged at **0 stale, 0 missing**. *Skipped converges; moved does
not.*

Since enricher **0.6.4** the ClinVar drafter **names** the superseded rows — *"N row(s) already in
variants.csv identify by rsID alone…"* — with counts and examples, and **deletes nothing**, because by
re-draft time that row is authored material you may have curated. **The deletion is yours**, once the
coordinate rows cover the same records. Drafting into an empty directory and reconciling against that is
still the cleaner route.

🚧 **ROADWORKS — that supersession sweep does not reach `studies.csv`.** `_superseded_rsid_rows` has one
call site and is handed the **`variants.csv`** append report, so a ClinVar re-draft leaves both the stale
rsid-only study row and its coordinate-keyed replacement — surfacing only as a *"Studies reference
variants not in variants.csv"* orphan warning, which **blames the citation**. **Guard:** after any
re-draft, diff `studies.csv`'s rsIDs against `variants.csv`'s and delete the stale rows before compiling.

`module-refresh` owns re-running in general — including the fact that a re-draft appending nothing is
completely inert and does not even move the digest.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** re-running a drafter per gene as the module grows; expanding a
still-placeholder row into both zygosities where the contig leaves it open; writing the CPIC
`licensing.csv` row a zero-row draft failed to write; deleting a superseded rsid-only row **once the
coordinate rows demonstrably cover its records**.

**Surface it, and let a pilot settle it:**

- **Every `differs`.** Which side is right, and if it is the source, the reason that outranks your row.
- **The `use` position.** It asserts a licence claim; it is not a knob to turn until the draft runs.
- **The review-star floor**, and whether a mixed-provenance panel is honest without saying so.
- **Every `<<REPLACE>>`** — that is the drafter naming what it refused to decide.
- **Whether an undefined star allele should be defined or its rows dropped.**

## What this stage cannot do

**It cannot rewrite a cell**, ever. Appending is the whole mechanism, which is why a re-draft is safe
and why it cannot repair.

**It cannot decide a genotype, a `state` or a conclusion.** It prints the allele pair and stops.

**It cannot tell you a source is stale.** Nothing watches ClinVar, CPIC or ClinPGx for a release.

**It cannot draft what its own pattern rejects** — see the eleven genes above — and it does not say it
refused.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action:

- *"unreplaced template placeholder `<<REPLACE>>`"* — the drafter naming what only a pilot decides. It
  blocks every loader on purpose.
- *"must be a non-empty haplotype name without whitespace"* — an identity, not a grammar: `*4`, `e4`,
  `ε4` are all fine. CPIC's `x≥3` copy-number notation is not (RM5).
- *"`draft --gene CYP2D6` produced thousands of diplotype rows"* — expected without `--allele`.
- *"Star allele(s) used but not defined in haplotypes.csv"* — define it or drop the rows; `*1` is exempt.
- *"N row(s) already in variants.csv identify by rsID alone"* — the supersession report. Act on it; do
  not filter it.

## Where to go next

| You need | Load |
|---|---|
| to decide the cells it left | `module-curate` |
| to re-run anything that already ran | `module-refresh` |
| which PGx table a finding belongs in | `module-tables` |
| the PGx tables in full | `module-tables` → `references/{haplotypes,allele_function,diplotypes,pharm_variants}.md` |
| the licence row a draft should have written | `module-tables` → `references/licensing.md` |
| the drafter flags in full | `../module-101/references/CLI.md` |
