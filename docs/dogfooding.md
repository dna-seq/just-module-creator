# Dogfooding — open findings

Open quirks, bugs and UX gaps found by **using the shipped surface for real
work**, not by testing it. Read before touching the tool surface.

Findings carry stable `F#` IDs and **move** between files rather than being
duplicated: resolved here → [previous_issues.md](previous_issues.md); blocked on
an upstream change → [just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).
One legitimately appears in two files when we have mitigated it and upstream
still owes the fix.

Layer 1 (the suite) proves the code does what it was told. This asks whether it
is usable, and what is missing.

---

## F68 — nothing on the surface reaches a supplementary table, and the skill taught the empty cell because of it

**Found:** 2026-08-30, reproducing a supplementary table retrieval from a PDF the owner supplied ·
**Severity:** medium · **Status:** the skill half is fixed in this change
(`skills/find-evidence/references/SUPPLEMENTARY.md`, plus the corrected passage in `SKILL.md`); the
tool half is open and deliberately not built.

For a GWAS paper the per-variant numbers a `studies.csv` row asserts are almost never in the article
body. The body says *"263 independent variants across 180 genomic loci"*; the rsIDs, positions,
alleles and p-values are in the supplementary workbook. `fetch_fulltext` returns the JATS body and
nothing else, and **no tool on the surface lists, fetches or reads a supplementary file.**

**The cost is not the missing tool. It is what the skill concluded from it.**
`skills/find-evidence/SKILL.md` said, of the exact case it names:

> `fetch_fulltext` returns the JATS body and no supplementary file, so for those rows there is
> nothing in reach to quote — and the honest cell is empty.

That is `F42`'s shape one layer up: a surface limit written up as a fact about the world, teaching an
author to record *nothing available* for something that is available. Measured against its own
example — PMID `29500382`, `10.1038/s41467-018-03242-8`, the 65 `aggression_anger` rows — the
supplementary is **two HTTP requests from the DOI**, on an open host, no authentication, CC-BY, and
its *Supplementary Data 2* carries 504 lead-SNP rsIDs of which **42 of the 65 are present**, with the
per-item association p-values those rows assert. The rows did not get the honest empty cell either:
all 65 shipped carrying the article title (`F42` / upstream `S54`).

**What was measured, on four real articles.** The ladder is DOI → Europe PMC record → `fullTextXML`
inventory → publisher pattern, and the negative results are the load-bearing half:

- `link.springer.com` is behind a JavaScript bot challenge — a `curl` of the resolved DOI returns
  3 KB titled *Client Challenge* under HTTP 200. Scraping the article page finds no links and looks
  like an article with no supplementary material.
- Europe PMC reported `hasSuppl: N`, `inEPMC: N`, `isOpenAccess: N` for `10.1007/s11357-025-02044-3`,
  which is CC-BY and has two openly downloadable ESM files. The flag describes their holdings, not the
  article. Crossref carries no `relation` for the ESM and Unpaywall points only at the article PDF, so
  **no metadata API in our stack exposes supplementary files.**
- Europe PMC's `supplementaryFiles` endpoint works and returns one zip of everything including every
  figure, unselectable: **224 MB** on `PMC12506250` to reach a 14 KB table.
- Extensions are not guessable — `MOESM1` was `.txt` on one article and `.pdf` on another, and
  `MOESM3` was a peer-review PDF rather than data. A 403 across the extensions tried means *unknown*,
  not *absent*, which is the three-valued rule at the corpus level.

**A second counter reads wrong, and this one is ours.** `enrich_literature_pass` searches the Europe
PMC body, so a quote lifted from a supplementary workbook scores `quotes_found: 0` — indistinguishable
from *read and not found*, which the skill teaches "says something". A correct supplementary quote
therefore reports as a suspect one. The skill now names the fifth state and tells the author to record
the source file, because nothing on the surface can.

**Surface it, do not build it yet — and why each candidate repair is wrong today.**

- **A `fetch_supplementary` tool.** The obvious shape, and the reason to wait is that rung 3 is
  publisher-specific: we measured the Springer Nature family only (`10.1007`, `10.1186`, `10.1038`).
  A tool that silently covers one family and returns nothing for Elsevier or Oxford reproduces exactly
  the defect above — a surface limit an author reads as an absence — unless it distinguishes *no
  pattern for this publisher* from *no supplementary material*, which is a three-valued return the
  design has not been through yet.
- **Wrapping Europe PMC's `supplementaryFiles`.** One call, no pattern table, and it is the 224 MB
  route. It also answers nothing for the article that prompted this, which is not in PMC at all — the
  common case for a paper published in the last few months, which is exactly when a module is being
  written about it.
- **Teaching the ladder in prose only, which is what shipped here.** Honest and immediately useful,
  and it costs a network call the `ServiceGate` never sees: §2 says every outbound request goes
  through `net.py` so pacing and the shared NCBI budget cannot drift, and a taught `curl` is outside
  it. The two hosts involved (`static-content.springer.com`, EBI) are not NCBI and are not metered
  against that budget, so the ceiling is not breached today — but this is the argument that makes the
  tool the right end state rather than an optional convenience.
- **Parsing the ESM into rows for the author.** Out of scope and the wrong layer — which sheet answers
  a row's claim is a judgement about that row, the same reason `fetch_fulltext` does not return a
  best-matching passage.

**Not filed upstream.** This is authoring workflow, which is ours to build (§11); the schema and the
checks are unchanged. The one thing owed upstream is a corroboration on `S54`, whose evidence was that
a rule against machine-located quotes produced 3668 titles: the 42-of-65 number says those rows had a
real passage in reach the whole time.

## F66 — `lint_rows` echoes its whole input back, and that is load-bearing

**Found:** 2026-08-21, run 2 · **Severity:** low · **Status:** open, deliberately not changed.

`lint_rows` returns the entire input as `normalized_csv`. On a twelve-row slice that is
fine; on a 1,039-row module it doubles a response that is already the largest thing the
tool returns, and the run's ask was to make it opt-in.

**Left as it is, and the reason is the `alterations` list beside it.** The tool reports
what it normalised — `-2.0` written back as `-2` — and a caller applying those needs the
normalized text to apply them *to*. Defaulting the echo off would leave `alterations`
describing edits against bytes the caller no longer has, which trades a size problem for a
correctness one.

The size complaint is still real. The shape that would resolve both is a flag that returns
the normalized rows **only where something was altered**, which is neither the whole file
nor nothing — recorded here rather than built, because it is a behaviour change and this
pass was scoped to surfaces.

## F65 — four of the runs' registry findings did not survive verification, and one was ours

**Found:** 2026-08-22, verifying before filing · **Severity:** n/a ·
**Status:** closed. Recorded so nobody re-investigates.

Checked against the live instances and the registry's own source before filing upstream.
Four claims from the two runs were **not filed**, because they are wrong:

- **"Every warning a local strict compile produced was discarded at publish."** Refuted
  three ways. Production manifests carry `compilation.warnings` — two to four each —
  **including the licence-conflict warning the finding said was dropped**. The server's
  compiler version is readable at `/api/v1/version`, and digest non-reproducibility across
  compiler versions is documented twice in their API reference (*"a recompile of the same
  spec need not produce the same digest"*). The remaining true part is a **deployment lag**,
  not a defect: their 0.20 roadmap already adopts 0.6.6.
- **"`module_spec.yaml` never matches its own published digest."** Refuted by sweep: every
  input of all eight production modules fetched through `/files/` and hashed — **29 of 29
  match on both `sha256` and `size`**. The "374 bytes recorded vs 1198 served" observation
  does not reproduce.
- **"The `/files/` endpoint is undocumented."** It is documented in their API reference, and
  the supported client route to authored source is `download(include_inputs=True)`, also
  documented. Our own tier is what made it unreachable, which is `F60`'s neighbour and is
  fixed.
- **"The registry truncates the gene list without saying so."** The truncation is real and
  documented, and `gene_count` sits beside the three genes in the live payload. **The bug
  was ours**: `_module_card` read `genes` and never read `gene_count`, so a module naming 22
  genes projected three and looked complete. Fixed; a caller filtering on `genes` now has
  the number that says the list is a sample.

**The pattern worth keeping.** Every one of these read as a confident measurement in a
careful report, and three of the four dissolved on contact with the source. One run said it
of itself — two of its three findings needed retracting, and the toolchain contributed to
neither retraction. **Verify before filing, and verify against the producer rather than
against the observation**; a note filed on a refuted claim costs upstream a triage cycle and
costs us the next note's credibility.

## F60 — the surface answers "will this build?" four ways and "is this any good?" not at all

**Found:** 2026-08-21, two independent unattended runs · **Severity:** high ·
**Status: closed 2026-08-24.** The tier and discovery half shipped 2026-08-22; the audit surface
shipped in 0.20.0 as `audit_module` (`RM26`).

Run 1 curated the eight modules then on the production registry; run 2 revised the ten
modules in `just-dna-lite`'s v1 port. Neither had prior context. Both ran in the default
tier. **Every module passed `validate_module(strict=true)` with zero errors**, and every
real defect either run found was found by writing arithmetic over the CSVs.

`registry_check`, `registry_validate`, `validate_module`, `compile_module` and `lint_rows`
all answer *"will this build?"*. The offline gate is **right** to pass those modules and
says so itself — *"strict means reproducible, not correct"* — so this is not a broken
check. It is that the entry point to a curation pass tells you nothing, and the caveat
that says so is prose while the green result is a tool call.

What run 1 measured in modules that passed every gate, all by hand:

| defect | how it was found | scale |
|---|---|---|
| `effect_measure` says `beta` on a Z-statistic | compare `effect_size` against `-Φ⁻¹(p/2)` | 242 variants, 4 modules |
| `effect_size` dosage-doubled on hom rows | hom value = 2 × het value | 10 of 13 variants, 1 module |
| `weighting:` never declared | read `module_spec.yaml` | every module in both runs |
| the reference-base check had never run | read `verification.json` | every module in run 1 |
| `gene: KIBRA` not HGNC-approved | `check_identifiers` — the one tool that found anything | 1 module |

A "beta" of 7.29 on an item-level irritability score is not a possible effect size; it is
the Z for that row's own p-value to three decimals, and in one module that column then
held Z-statistics beside genuine per-allele betas of order 0.02 under one unit label.

Run 2 found the same shape from the other side: a module with **190 rows and an empty
`weight` on every one**, no `weighting:` block, passing strict and compiling green with
`weights_rows: 190`. Nothing distinguishes "the author deliberately authors none" from
"the author forgot", which is the question `weighting:` exists to answer.

**Every signal in that table is computable offline from files the plugin already reads.**
That is what makes this a gap rather than a wish, and `audit_module` now computes them: it
reproduces `superhuman`'s 190 empty weights, the six curated modules' undeclared scale, the 52
`detail: null` findings split 20/32 across two modules, and `clinical_significance` recorded at
`subjects: 0` on all eight modules of the other corpus — measured against those directories rather
than against fixtures. **It also finds seven rows the hand-repair pass missed**, still labelled
`beta` while carrying the Z of their own p-value, which is the argument for the tool in one line.
The one row in that table it does **not** cover is `gene: KIBRA` — that is `check_identifiers`,
which needs HGNC and is therefore a check rather than an audit. See `RM26` in
[ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) for what was deliberately not built and why.

## F61 — `review_queue` reports nothing to review while holding the evidence

**Found:** 2026-08-21, run 1 · **Severity:** high · **Status:** **fixed 2026-08-24**, and the
cause was not the one this entry assumed.

`review_queue` is introduced as the priority list for a review pass — *"these are the rows
to start with … the highest-value judgements in the module and the easiest to forget."*
Run 1 recorded six overrides through `record_override`, including a ten-row correction to
a fabricated `effect_size`, and every one was written to `provenance.json` and
`logs/authoring.log`. The tool then returned `{"total": 0, "entries": []}` on both modules,
with the records shunted into an `other_provenance` bucket of flattened strings.

This entry read the symptom correctly and the cause wrongly, and both halves are worth
keeping. The reading it proposed — that the queue can only decide `clin_sig` offline, so
everything else should surface as `unknown` rather than as silence — describes behaviour the
tool **already had**: `review_queue` emits an entry per record whatever the field, and
`unknown` is one of its three documented states. `RM26` inherited the misreading and proposed
widening a thing that was not narrow.

**The actual defect was a codec that disagreed with itself.** `record_override` appends a
marker to `rationale`; the reader's pattern encoded `source=` as `[A-Za-z0-9_.-]+` and the
writer enforced nothing, so a source named `GWAS Catalog` — or `ClinVar 2024-06`, or
`gnomAD v4.1 (non-neuro)` — was written and then read back as **somebody else's provenance**.
Hence `total: 0` beside a bucket of flattened strings: not a question that could not be put,
but a record that could not be recognised as ours. Fixed 2026-08-24, and the recovery is **measured
on that run's own files** rather than asserted: the six records still sitting in
`modules_dogfooding/work/*/provenance.json` parse **0 of 6 under the old pattern and 6 of 6 under the
new one**. Every one of them names its source as something like *"module's own prior authored value
(big_five_personality_snps@2.1.0 as published)"* — which is a good source name and an impossible
`[A-Za-z0-9_.-]+`.

**What generalises: a round trip that is only ever tested against the values the test author
chose is not tested.** Every existing test used `source_name="clinvar"`, which the pattern
accepted. Ask of a green round-trip what §6 asks of a green fixture — could this have
failed? Four of the five source names in the new parametrization would have failed before
the fix, and every one of them is a string somebody would actually type.

## F62 — `compile_module` accepts an output directory that makes the spec unpublishable

**Found:** 2026-08-21, run 1 · **Severity:** medium · **Status:** open.

`out/` inside the spec directory is the obvious choice. `compile_module` accepts it and
copies `README.md` into it, and the **publish** then fails two steps later:

```
HTTP 422 ambiguous_spec_layout
  "`README.md` arrives from more than one path (`README.md`, `out/README.md`);
   send one copy, since only the author knows which is current"
```

The error is excellent — it names both paths and refuses to guess — but it lands at the
one operation with real consequences, and nothing upstream of it warns. Either
`compile_module` should refuse an `output_dir` inside `spec_dir`, or the copy should
exclude authored files.

## F63 — an aborted `enrich_module` keeps running and overwrites the spec directory afterwards

**Found:** 2026-08-21, run 1 · **Severity:** high, data integrity ·
**Status:** mitigated 2026-08-22; the upstream half is format-tree `S66`, tracked as `F63`
in [just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).

The mechanism, localized by reading both trees rather than by reproducing the timeout.
`enrich_module` dispatches through `anyio.to_thread.run_sync` with the default
`abandon_on_cancel=False`, and a worker thread cannot be interrupted at all — so a
client-side abort leaves the work running, unaware and still holding its write. The
enricher reads `resolution.csv` at the start of the run and rewrites it in one truncating,
non-atomic write at the very end, with no lock anywhere in either tree, so the
read-modify-write window is the whole run and two concurrent enrichments are
last-writer-wins.

What that produced: a run aborted client-side at 1800s; the published 330-row
`resolution.csv` restored by hand; a second `enrich_module` returning `resolved: 330,
sources: ["cache"]` correctly and instantly; and then the first call reaching its write and
leaving **162 distinct rsIDs**, plus a rewritten `verification.json`. Subjects that never
resolved contribute no row at all rather than an unresolved one, which is why the file
shrank rather than degrading visibly. The module validated, closed and compiled green.

**Partly fixed 2026-08-22.** A directory with an enrichment in flight is claimed, and a
second enrichment of it raises with what is running and when it began rather than
succeeding into a file about to be overwritten. The claim releases in `finally`, which
covers exactly the window the abandoned write can land in, because `run_sync` defaults to
`abandon_on_cancel=False`. The docstring also carries the reading guard — count
`resolution.csv` against the authored subject count after any timeout.

**What stays open.** The claim is in-process: it cannot see an enrichment started by a
different server process, and there is no lockfile in this tree or upstream's. And
`enrich_module` still destroys `resolution.csv` with no capture, while the sibling
`refresh_sidecar` has exactly the pattern it needs — copy out, read the copy back, hash it,
only then let anything destroy the original. The durable repairs are upstream's: a
tmp+rename write, incremental persistence so an interrupted run keeps what it resolved, and
an advisory lock over the read-modify-write window, which is the whole run.

## F64 — the plugin cannot see the channel a whole family of modules is published on

**Found:** 2026-08-21, run 2 · **Severity:** medium · **Status:** open, acknowledged.

`compare_to_published`, `registry_is_published` and `registry_search` all answer about the
module registry. Six of `just-dna-lite`'s modules have been published for months on
HuggingFace at `just-dna-seq/annotators`, where each carries a `manifest.json` today, and
that is where that repo's discovery tier actually reads modules from.
`registry_is_published` returns `free_to_publish: true` for them. That verdict is true
about the registry and **false about the world**, so for every module in that repo the
question a revision pass opens with cannot be asked at all.

The plugin is careful about precisely this class of mistake one level down — `target` is
required with no default on every catalog read, because a search that guessed would answer
confidently about the wrong instance. The same argument applies to which *kind* of
publication is being asked about, and there it is not applied. The minimum their run asked
for is the right shape: say what was not looked at.

## F6 — two of five literature sources refuse this host, and the tool is right to say so

**Found:** 2026-08-11, capturing fixtures · **Severity:** medium ·
**Status:** **RESOLVED 2026-08-20 — and the diagnosis below was wrong.** Both fixtures are
captured and both parsers are tested; `RM6` is closed in
[ROADMAP_HISTORY.md](ROADMAP_HISTORY.md). The tri-state finding this entry exists for **stands
unchanged** and is why it stays here.

> **Corrected 2026-08-20.** *"IP block"* was the wrong conclusion from a real observation.
> Re-probed through our own client: **arXiv answers HTTP 200** — six requests, no throttling —
> and Semantic Scholar's 429 is **intermittent and endpoint-specific**, `paper/search` shedding
> load while `paper/{id}` answers reliably. arXiv had a genuine rate-limit incident in late
> February 2026 that its maintainers acknowledged and fixed; we measured it during that window
> and then carried the conclusion for six months without re-probing. **The lesson is the
> re-probe, not the block:** an environmental verdict is a measurement with a date on it, and
> ours had no expiry. `assets/literature/` now holds `arxiv_query.xml` and
> `semanticscholar_search.json`, captured through `Discovery` itself so each is a real response
> to the exact request the client makes.

The original observation, which was accurate on the day: Semantic Scholar and arXiv both answered
HTTP 429 from this machine regardless of user-agent, arXiv on a *first* request with no prior
traffic. Confirmed with plain `curl` outside the client.

Reported here rather than routed around because it is the best available
evidence that the tri-state design earns its keep. A live `literature_search`
returns `results=null` and `rate_limited=true` for those two, plus a warning that
their part of the literature is **unchecked, not empty** — while PubMed and
Europe PMC answer normally. Had the model used `0`, the same call would have
read as "no preprints exist on this subject", which is a conclusion an author
would act on.

The cost was real while it lasted: `parse_semantic_scholar` and `parse_arxiv` had no committed
fixture and therefore no test, for six months. Both now have both — six tests, including the
`arxiv:doi` branch that only fires for a preprint that was later published, which is the branch a
fixture-less parser was most likely to have got wrong.

## F7 — a `limit` was spent entirely on whichever source was asked first

**Found:** 2026-08-11, first live search · **Severity:** medium ·
**Status:** resolved same day, kept here as the reason the ordering rule exists

The first working `literature_search` asked four sources with `limit=5` and
returned five PubMed papers. Europe PMC had answered with five of its own and
none of them appeared: the merge preserved first-appearance order, so source one
filled every slot.

Nothing was broken and every count in `sources` was accurate — which is what made
it easy to miss. It only showed up because the live run printed `found_in` per
paper and every row said `['pubmed']`.

Merge now interleaves by each source's own rank, so every source's top hit
outranks anyone's second. Ties break on first appearance, so the order stays
deterministic.

**Why it stays in this file rather than moving to previous_issues.md:** the
finding is not the bug, it is that asking several sources can silently degrade
into asking one, and nothing in the result said so. A future federated tool wants
the same guard.

## F8 — the literature sources have no recordable licence terms

**Status:** mitigated here, open upstream. Full entry in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md); filed as
`S10`.

Listed here too because the mitigation is reporting only: each literature result
carries a `SourceLicenseNote` naming the row the author owes, and a module still
compiles green with the terms unrecorded because it is a warning.

It briefly had a roadmap item (`RM7`), which was wrong — there is no work here for
us to do. Removed on 2026-08-11 during a sweep for upstream gaps this repo had
absorbed as its own.

---

## Probes not yet run

Recorded so the gaps in *this* file are visible too, per the completeness rule.

- **Author a real module end to end and publish it.** Everything up to
  `compile_module` has been exercised on a real spec; `enrich_module` and
  `registry_publish` have not ([RM4](ROADMAP.md)). This probe would also hit F1
  from the inside rather than by inspection.
- **A binning module — partly run, 2026-08-11.** Probed at the `lint_rows` level
  with real HTT CAG repeat bins (≤26 normal / 27–35 intermediate / 36–39 reduced
  penetrance / ≥40 full penetrance, plus the `unresolved` sentinel). The bounds
  handling held up better than expected: the coverage check reports a genuine hole
  (`no bin covers (26.0, 36.0)` when a bin is missing) and correctly does **not**
  invent one between adjacent integer bins 26 and 27, and the missing-sentinel
  warning states the contract outright — a consumer with no measurement selects the
  sentinel, never the lowest bin. What it did find is [F14](just-dna-format-pending-fixes.md)
  (`S18` upstream): a ragged row is silently shifted and misdiagnosed. **Still not
  run:** scaffold → validate → compile on a binning module, and `heteroplasmy.csv`,
  the other endpoint convention, where bins genuinely do share a bound on a
  continuous measure.
- **`enrich_module` and `registry_publish`, end to end against the live services.**
  Was tracked as a roadmap item until 2026-08-11; it is a probe, not a
  deliverable. The offline ceiling keeps the suite hermetic, so neither can be a
  normal test — what fits is a marked, opt-in integration run alongside authoring
  a small real module all the way through. `registry_publish` needs a token, a
  namespace and a module we are willing to publish immutably; the new
  `published.json` receipt is what makes the result inspectable afterwards.
  **Unblocked 2026-08-11** — `registry_register` now mints the token from inside the
  surface ([F12](previous_issues.md)), and `registry_namespace_available` answers the
  namespace question without spending the irreversible claim to ask it
  ([F13](previous_issues.md)). Both are wrapped and covered offline; **neither has
  been driven against the live service to the point of creating anything**, which is
  precisely what this probe is for.

  **Unblocked differently on 2026-08-11, and this is the bigger change:** the registry
  now runs a *polygon* (`REGISTRY_MODE=test`), where a publish is a rehearsal that
  `registry_delete_version` frees again — version number and content claim both. The
  reason this probe kept being deferred was that it demanded "a module we are willing to
  publish immutably"; on the polygon it demands nothing of the sort. Run it there, with
  `target="test"`, as many times as it takes. Two caveats to carry into it: the polygon
  scopes `duplicate_content` to the publishing account, so a rehearsal cannot prove a
  cross-account duplicate would be refused; and as of filing the polygon host answers a
  bare 404 (DNS'd, app not deployed), so the probe waits on that deployment rather than
  on us.
- **A module with two of something the examples show one of.** The worked example
  throughout is a single-gene, single-rsID module. A paralogous rsID mapping to
  several loci, or one gene carrying two variants with different thresholds, is
  where a key that works for one instance stops working.

## F18 — "a green pre-flight should mean a green compile" is false before `resolution.csv` exists

**Found:** 2026-08-11, authoring `assets/fto_bmi` · **Severity:** medium · **Status:** open

`skills/create-module/SKILL.md` §6 says:

> `validate_module` refuses everything `compile_module` refuses that does not need resolved rows, so
> **a green pre-flight should mean a green compile**.

The qualifier is correct and the conclusion drawn from it is not. On a freshly authored spec with no
`resolution.csv`:

```
validate_module(strict=True)  →  valid: true,  errors: [],  warnings: [],  info: []
compile_module(strict=True)   →  success: false
    "strict compile: 3 variant(s) have unresolved genomic positions after resolution"
```

Green pre-flight, refused compile — the exact implication the sentence licenses. Not one of the three
finding levels carried anything, so there is no hint in the payload that the most consequential step
has not run.

**The compile gate itself is fine** and is the reason this is medium and not high: it refuses, it names
the count, and its warning names the remedy (*"No resolution.csv and no ensembl_cache injected …
Produce a resolution.csv with just-dna-enricher"*). The defect is that the pre-flight advertises
itself as predictive of that outcome when it cannot be.

**Why it matters more than the wording suggests.** `valid: true, strict: true` with three empty
finding lists is the most reassuring output this surface produces, and the state it is reassuring
about is *a module that cannot match any genome*. The skill's own done-checklist carries "every weight
row has a coordinate" as a **manual** checkbox, which concedes that nothing checks it — so the one
condition the author must remember is the one the tool is silent on. It compounds with `F19`: an author
who cannot reach `enrich_module` sees a green strict validate and no reason to doubt it.

**Candidate fix**, cheapest first: have `validate_module` emit an `info` (or `warning` under strict)
when the spec has variant rows and no `resolution.csv` — "resolution has not run; a strict compile will
refuse N row(s)". It needs no network and no resolution, only a file-existence test plus the row count
it already has in `stats`. Then correct the skill sentence to say a green pre-flight predicts a green
compile *once resolution exists*.

**A candidate that is wrong:** having `validate_module` resolve anything itself. It is documented as
writing nothing and touching no network, both worth keeping, and authoring a second resolution path
is how the two sides of a redundancy check end up produced by one process.

## F19 — nothing on the tool surface reports the running server's version, and a stale process is invisible

**Found:** 2026-08-11, blocked mid-probe · **Severity:** medium · **Status:** open, partially
mitigated 2026-08-20

**Partial mitigation (RM13).** Every generated schema answer now carries
`produced_by.format_version` / `produced_by.compiler_version`, and `server.INSTRUCTIONS` names the
same pair instead of a hardcoded `(format 0.5)`. That makes a stale *toolchain* visible without
being asked, which is a strong proxy — a cached plugin build pins its own resolved dependencies. It
is not the whole finding: what is reported is the toolchain, not our own package version, and a
missing tool still reports nothing at all, because a tool that is not registered cannot stamp
anything.

The connected stdio server was missing nine tools the skill lists as **essentials** — `enrich_module`,
`check_identifiers`, `lookup_identifier`, `lookup_open_access`, `fetch_fulltext`,
`authoring_reference`, `module_signature`, `verify_artifact`, `registry_get_module` — which is exactly
the set 0.4.0 moved *into* essentials. The tree registers `enrich_module` in `register_passes`
(`tools/passes.py:297`), the essentials tier, so the code is right and the **process** was old:

```
2669780  Tue Aug 11 17:01:58   uv run --project … just-module-creator stdio
2726281  Tue Aug 11 18:03:54   uv run --project … just-module-creator stdio
HEAD     3a6d20d              2026-08-11 20:30:30 +0300
```

Two of them, both hours older than HEAD, consistent with the known behaviour that `/reload-plugins`
does not re-exec a stdio server and stale ones accumulate.

**The finding is not the staleness — it is that the staleness is undiagnosable from inside the
surface.** No tool reports the server's version, so the symptom presented as *"the plugin does not
have `enrich_module`"*, indistinguishable from *"this tier does not include it"* and from *"the skill
documents a tool that does not exist"*. Diagnosing it took `ps`, `git log` and a grep through
`tools/passes.py` — three moves outside the product, to answer a question the product is the only
authority on.

It is worse for the taught workflow than for an arbitrary missing tool, because `enrich_module` is
step 4 and unreachable means no `resolution.csv`, which `F18` shows a green strict validate will not
mention. The failure chain is: stale process → missing step → silent pre-flight → an author with a
module that compiles under best-effort and matches nothing.

**Candidate fix:** report the version where an agent will see it without asking — appended to
`server.INSTRUCTIONS` at build time from `importlib.metadata.version("just-module-creator")`, which is
already the single source of truth and already read by `tests/test_plugin_manifest.py`. That is
cheaper than a tool and cannot be forgotten, since the instructions are always in context. A
`server_info` tool would also work but has to be *called* to help, and nothing prompts an agent to
call it before the thing it is diagnosing.

**Not a candidate:** having the server detect its own staleness against the working tree. It would
make the server read git state it has no business reading, and it is wrong for anyone who installed
from PyPI, where there is no tree to compare against.

## F22 — `published.json`, the receipt we tell the author to commit, records `owner: null`

**Found:** 2026-08-11, rehearsing `test-sheep/fto_bmi@1.0.0` · **Severity:** low · **Status:** open

`registry_publish` says *"Identity recorded in published.json; commit it with the spec"*, and the file
it writes carries:

```json
{ "target": "test", "canonical_id": "test-sheep/fto_bmi@1.0.0", "owner": null, … }
```

`owner` is null in both the tool result and the committed receipt. The registry does know it — a
`registry_get_module` on the same module one call later reports `"owner": "sheep"`, and
`registry_claim_namespace` had already returned `{"namespace": "test-sheep", "owner": "sheep"}`. So the
value was available on the claim and is absent from the publish payload we persist.

Low severity because nothing depends on it and `canonical_id` carries the namespace, from which the
owner is recoverable via the registry. Worth fixing because the receipt's whole job is to be the local
record of what was published where, and "who published it" is a field it declares and then leaves
empty — a reader cannot tell an unowned module from a dropped field.

Probably the same root as `F15` (no enumerated client-surface contract for the registry client): the
publish response shape is read defensively and `owner` may simply not be on it. If so the fix is to fill
the receipt from the claim/whoami we already hold rather than from the publish response — but confirm
where the null originates before choosing, because `research.py::_module_card`'s defensive projection is
deliberate and must not be tightened on the strength of undated client docs.

**Related payload inconsistency, same call, not filed separately:** the top-level `resolution` block
reports `sources: ["clinvar"]` with a signature, while `versions[0].resolution` reports `sources: []`
and `signature: null` for the same version. Ours is the read side only; noting it here so the next
reader of that payload does not treat the nested copy as authoritative.

## F25 — nothing reports the resolved contact address or which step supplied it

**Found:** 2026-08-11 · **Severity:** low · **Status:** open

The polite-pool contact resolves `JMC_USER_EMAIL` → `JUST_DNA_CONTACT_EMAIL` →
`settings.DEFAULT_CONTACT_EMAIL`, and no tool answers which one won — or whether the author is on the
shared project default at all. `build_services` logs the origin at `debug`, which no MCP client sees.

That matters because `skills/create-module/SKILL.md` now instructs an agent to ask the author for an email
**only when nothing is configured**, and the only way to establish that is to read `.env` off disk — a step
outside the tool surface, in a file that also holds tokens. It is the shape `F23` had before 0.5.4
closed it (see [previous_issues.md](previous_issues.md)): a documented procedure whose precondition the
product cannot report. That one was closed by upstream giving us the check; this one has no upstream half
— the address is ours to report.

**Candidate fix:** surface it read-only on an existing result rather than adding a tool — the origin string
`build_services` already computes (`"JMC_USER_EMAIL"` / `"JUST_DNA_CONTACT_EMAIL"` / `"project default"`)
on `literature_search`'s `sources` block or alongside `lookup_open_access`'s findings, where an agent is
already looking when it matters. **Never the address itself** on a tool result: the origin answers the
question, and echoing a configured address writes personal data into a transcript for no gain — the same
argument as the `registry_register` install-id echo already noted in `UX_TESTER.md`.

## F26 — a stale plugin build serves an old tool surface, and no result says which build answered

**Found:** 2026-08-12, authoring a longevity module · **Severity:** high · **Status:** open,
partially mitigated 2026-08-20

**Partial mitigation (RM13).** The stronger candidate below shipped: `server.INSTRUCTIONS` now names
the running `just-dna-format` and `just-dna-compiler`, and the weaker one shipped too — every
generated schema answer carries the same pair, `authoring_reference` included. The first symptom in
the table below would now be visible in the answer itself. **The second and third would not**: a
tool that is absent stamps nothing, and a warning that fires from old code carries no version. So
the "stale build looks like a regression" trap is narrowed to the tool *roster*, not closed.

**Confirmed 2026-08-12 by `/reload-plugins`.** All three symptoms below cleared at once on 0.7.0:
`sources.csv` moved from `sidecars` into `tables` with `SourceRow` and `(source, layer)`,
`check_identifiers` returned `gene_locus_conflicts: []` **and** `gene_locus_check_skipped: null`
explicitly, and the `S23` orphan warning stopped firing. The `artifact_digest` was identical before
and after, so nothing built on the stale surface was wrong — only everything concluded *about* the
surface was.

`/plugin` reported *"Updated just-dna Module Creator. Run `/reload-plugins` to apply."* The reload
did not happen, so **every tool call in that session was answered by the 0.2.0 build** while the
repo, the skill and `docs/` were all 0.7.0. Nothing in any tool result said so, and the mismatch is
invisible: the tools are all still there, they all still answer, and the answers are internally
consistent — with a surface that shipped months ago.

**Four conclusions were drawn and had to be retracted.** Each looked like a defect in 0.7.0:

| Observed | Actually |
|---|---|
| `describe_table("sources.csv")` / `get_template(…)` reject it, `list_tables` files it under `sidecars` | exactly `F20`, closed in 0.5.4. 0.2.0's sidecar literal still contains `sources.csv` and its `_SUBJECTS` does not |
| `check_identifiers` omits `gene_locus_conflicts` / `gene_locus_check_skipped` | 0.2.0's `models.py` contains **zero** `gene_locus` references — the fields do not exist there. Read as "empty, therefore clean", which is the exact inversion the fields exist to prevent |
| the `S23` literature exemption never fires | 0.2.0 pins `just-dna-compiler>=0.5.3`; its resolved compiler predates the exemption |
| the skill's advice was wrong on all three | the skill was right; the server was old |

**Third instance, 2026-08-20, and the window was twenty minutes.** A dogfooding session loaded
`fetch_fulltext`'s schema and got the docstring from *before* `211dac5`, which had reversed it
twenty minutes earlier in the same tree. Nothing said so; the description simply read as the current
contract, and it said the opposite of the policy the session was working under. The narrower
symptom this time is that the surface goes stale **against a commit made in the same session by
another agent**, so "reload after installing" is not the whole discipline — a long-running server is
stale against every edit made while it runs, and only the two version strings `RM13` added would
show it, neither of which moves on a docstring change.

**Second instance, 2026-08-12, and it is not the same one.** A later session authoring
`assets/longevity_2026` found `registry_check`, `registry_validate`, `registry_health` and
`registry_is_published` **absent from the tool surface** while `pyproject.toml`, the manifest and
`skills/create-module/SKILL.md` were all 0.8.0 — and `git log -S "async def registry_check"` puts all
four in `2e77c4e`, the 0.8.0 commit itself. The stale surface also still emitted the pre-`F28` preprint
warning. So this is not "the reload never happened once": a build that had already been reloaded went
stale again at the next version bump, and the symptom moved from *wrong answers about tables* to
*four tools the skill teaches simply not being there*. That is the failure mode §5 of `CLAUDE.md`
names — a surface that teaches a step it cannot run — arriving by staleness rather than by tiering,
where no test can catch it. **The tell that cost the least time was reading `git log -S` for the
missing symbol**, which separates "not built yet" from "built, not running" in one command; nothing in
any tool result does.

Three of those were written into `SKILL.md` as corrections before the cause was found, which would
have enshrined 0.2.0's bugs as 0.7.0's documented behaviour — including restating `SourceRow`'s
columns in the skill, **the exact fix `F20` explicitly rejected**. Reverted.

**The trap is that a stale build is indistinguishable from a regression**, and the natural response
to an apparent regression is to document it. A version skew that presents as a defect will therefore
tend to get written down as one. The give-away was cheap and was found late: our own source already
had the fix, so the code and the running behaviour disagreed — but that check only happens if you
think to make it.

**Candidate fix:** report the build on something every session already reads. `server.INSTRUCTIONS`
is the natural home — it is in front of an agent before the first call, costs nothing, and a version
line there would have ended this in seconds. A `version` field on `authoring_reference()` is the
weaker second choice, since nothing forces an agent to call it.

**A candidate that is wrong:** having tools detect their own staleness by comparing against the
checkout. There is no reliable link from a running server back to "the" repo — the cached copy *is*
a legitimate install — and a wrong answer here is worse than none. Report the build, and let the
reader compare.

**Not an upstream note.** Every symptom is our build being old; the format tree is not involved.

## F28 — `literature_search` tells you a preprint has no PMID while handing you one that does

**Found:** 2026-08-12, authoring a module from three PDFs · **Severity:** medium ·
**Status:** fixed in this change

`discovery.py` fired this on `any(p.preprint for p in papers)`:

> *"Some results are preprints: not peer-reviewed, and they carry no PMID, so they cannot ground a
> studies.csv row (pmid is required)."*

It fired on a result whose `pmid` was **`41427385`** — a bioRxiv posting with a PMID *and* a PMCID
(`PMC12713140`), because bioRxiv and medRxiv are indexed in PubMed under the NIH preprint pilot. The
warning contradicted the payload in the same response.

**The cost is a citation not made.** An agent reading the warning rather than the field concludes the
paper cannot ground a row, and either drops the finding or hunts for a journal version that may not
exist yet. Here it was the *centrepiece* — the cGAS variant with the functional work — and only
re-reading the raw `pmid` recovered it.

**Fixed by counting instead of assuming**: the finding now reports how many preprints carry a PMID and
how many do not, and leads with the part that is always true and got buried — none of them is peer
reviewed, so a row grounded on one must say so in its `conclusion`. `skills/find-evidence/SKILL.md`
carried the same false claim ("A preprint has **no PMID** … full stop") and is corrected.

**The generalisable bug is a class claim standing in for a field read.** "Preprints have no PMID" was
true of the arXiv index and got written as a property of the category; the fix is that the record
answers, never the class.

---

## F29 — `lookup_identifier` can verify a trait CURIE but nothing can find one, so the honest routes are luck

**Found:** 2026-08-12, authoring `assets/longevity_2026` · **Severity:** medium · **Status:** open

`describe_table` says `trait_efo_id` takes an "EFO/MONDO/OBA/HP trait ontology id", and
`lookup_identifier` exists precisely so the id is checked rather than recalled — its own docstring says
"writing an ontology id from memory is the failure this exists to prevent."

**But it only answers a closed question.** Given an id it returns current / obsolete / absent with a
label. There is no call that goes the other way, from "human longevity" to a CURIE. So an author who
does not already hold the id has three options, and two of them are the thing the tool exists to stop:

1. recall one and check it — the check passes or fails, but the *recall* is the forbidden step, and a
   plausible wrong id that happens to be `current` passes;
2. leave the column blank — legitimate, and it loses the one machine-readable trait key the row has;
3. go outside the surface to OLS4, which is what "a capability the tool lacks" means.

**What actually happened here was luck, and it is worth writing down because it will not repeat.**
Guessing `EFO_0007796` returned `current` with label `parental longevity` — a real, current term for a
*different* trait, which is exactly failure mode 1 rendering as a pass. Guessing `EFO_0004300` returned:

```json
{"state": "obsolete", "current": "OBA_VT0005372", "label": "obsolete_longevity"}
```

The obsolescence pointer named the replacement, `OBA_VT0005372` ("life span determination trait"), and a
second call confirmed it `current`. **The module got a correct CURIE because a guess happened to land on
a deprecated term.** Had `EFO_0004300` been merely absent, the honest outcome was an empty column.

**The `label` field is the thing to lean on, and half a search already lives in it.** It is what turned
`parental longevity` from a pass into a rejection. A `lookup_identifier(kind="trait", label="longevity")`
returning candidate ids with their labels — reporting, never writing, like every other lookup here —
would close this without touching the refusal model: the author still reads the labels and chooses, and
`trait_efo_id` is not redundancy-bearing, so nothing downstream is made vacuous by it.

**Why not just leave it blank.** Blank is honest and we say so everywhere. But `check_identifiers`
reports traits alongside genes, `registry_get_module` surfaces them, and a trait key is how two modules
about the same phenotype are ever going to find each other. A column that is empty because the surface
cannot help you fill it is a different thing from one that is empty because nothing was stated.

---

## F30 — we read PubMed's `pmcid` display string instead of its `pmc` identifier

**Found:** 2026-08-12, authoring `assets/longevity_2026` · **Severity:** high · **Status:** open

`literature_search` returns PMCIDs that are not PMCIDs:

```json
{"pmid": "41427385", "pmcid": "pmc-id: PMC12713140;"}
```

`esummary` publishes the same id twice under two `idtype`s, and only one of them is an identifier:

```
'pmc'   -> 'PMC12713140'
'pmcid' -> 'pmc-id: PMC12713140;'
```

`discovery.parse_pubmed_summaries` does `pmcid=ids.get("pmcid")`, so it takes the display string. Every
PubMed-sourced result in a mixed search carries the mangled form while every Europe PMC-sourced result
in the *same response* carries a clean `PMC12155586`, so the field's shape depends on which service
answered — and an agent reading down a result list has no reason to expect that.

**The cost is that the value cannot be passed on.** `fetch_fulltext(pmcid=…)` wants a real PMCID.
Getting one out of our own search result means noticing the prefix and stripping it by eye, which is
what happened here — and only because the paper mattered enough to chase. The fix is `ids.get("pmc")`,
with the `pmcid` key kept as a fallback that strips `pmc-id:` and `;` rather than trusted.

**The generalisable point: two keys differing by four characters, one of which is a label.** Nothing
downstream type-checks a PMCID, so a display string travels as far as the first thing that dereferences
it, and that thing is usually a network call that comes back empty rather than an error.

## F31 — `fetch_fulltext(pmid=…)` reports "nothing retrieved" for papers whose fulltext it will return by PMCID

**Found:** 2026-08-12, authoring `assets/longevity_2026` · **Severity:** high · **Status:** open

The centrepiece paper of that module — the bioRxiv preprint with the *CGAS* functional work, PMID
`41427385` — came back empty:

```json
{"retrieved": false, "text": null, "text_source": null, "locations": []}
```

with the finding *"Nothing was retrieved. `text_source` is null, which means UNCHECKED … Try the
locations below"* — pointing at an empty list. The same call keyed by PMCID returned **82 KB of
fulltext** immediately:

```
fetch_fulltext(pmcid="PMC12713140")   ->  text_source: "fulltext"
```

**Why.** `discovery.fulltext` resolves the PMID→PMCID hop through Europe PMC alone:

```python
record = client.lookup([pmid]).get(pmid)
pmcid  = pmcid or (record or {}).get("pmcid")
```

Europe PMC does not index preprint-pilot records under their PubMed PMID — `EXT_ID:41427385` returns
**0 hits** — so `record` is None, and with it go the PMCID, the DOI *and* the abstract fallback. Europe
PMC holds the fulltext perfectly well; it just will not answer to that key.

**This is the retrieval half of `F28`.** That one fixed a warning that said preprints have no PMID while
handing you one that does. This is the same class of record failing at the next step: it has a PMID, it
has a PMCID, it has fulltext in Europe PMC, and the one route we offer joins them through the single
service that cannot make the join.

**It compounds with `F30`.** PubMed *did* give us the PMCID in the search result a moment earlier — we
mangled it, and then did not consult it. Either fix alone recovers the paper: read `pmc` in the parser,
or fall back to PubMed's `articleids` when Europe PMC's lookup misses.

**And `locations: []` beside "try the locations below" is its own small defect.** The open-access probe
is keyed on a DOI that the same failed lookup was supposed to supply, so when the hop fails the advice
fails with it. Guidance that names a field should not survive that field being empty.

## F32 — `validate_module`'s warnings are a silent subset of the compile's, including one that needs no resolution

**Found:** 2026-08-12, authoring `assets/longevity_2026` · **Severity:** medium · **Status:** open

Same spec, same `strict=True`, `resolution.csv` present for both:

| | warnings |
|---|---|
| `validate_module` | 2 — both the VRS coverage pair |
| `compile_module` | 5 — those two, two locus expansions, **and the licence pair** |

The licence one is the problem:

> *module declares license 'CC0-1.0' but annotation-layer sources report ['public-domain']. Not
> adjudicated here — a compatible pair is legitimate, an incompatible one is a real problem, and only a
> human can tell which.*

It compares `module_spec.yaml` against `sources.csv`. It reads no resolved row and could run on a spec
with no `resolution.csv` at all, yet it is reachable only by compiling.

**`F18` is not this.** That one is about a pre-flight run *before* resolution exists. Here resolution
existed and the pre-flight still withheld a check that does not depend on it.

**Why it matters more than the count suggests.** The message says only a human can adjudicate — it is
addressed to the author, and it is the one warning in the set that asks for a *decision* rather than
reporting a fact about coverage. The documented contract is about refusals, so nothing is technically
broken; but the skill also says to read the warnings on a green run, and an author who pre-flights,
sees two warnings about VRS coverage and stops has not been asked the question.

**Candidate fix:** move the licence-pair check into the shared pre-flight both entry points call, and
say in the docstring that `validate_module`'s warnings are the resolution-independent subset — because
if they are going to be a subset, that should be a stated property rather than something discovered by
diffing two outputs.

## F34 — every publish uploads the previous version's `published.json`

**Found:** 2026-08-12, upstream's review of a publish (theirs to notice, ours to own) ·
**Severity:** low · **Status:** open

**One thing upstream noticed that we did not.** `gather_spec_files` uploads our own `published.json` on
every publish, so each version's storage carries the previous version's receipt. We are the ones who
tell authors to commit that file beside the spec, so the loop is ours to have spotted. Harmless, and
still something shipping that nobody chose.

**The process lesson is the expensive one.** `F27` was already in this repo, filed hours earlier by
another session, with the upstream number on it. This session found the same defect, wrote a fresh
`S7` against the registry, and got it closed as a duplicate of `S5`. The rule that would have caught it
— *"check whether it is already filed first"* — is in `CLAUDE.md` §8 and neither session ran it. Filing
fast is right; filing without reading `docs/` first is how the same note gets written twice.

## F44 — the full network pre-flight cannot tell a module whose every quote is the article's title from one where the quotes are honest

**Found:** 2026-08-20, remediating `aggression_anger`'s quotes on the polygon · **Severity:** high ·
**Status:** open, and narrowed 2026-08-21 · **Upstream:** `S54` and `S56` both **released in 0.6.5**
— the pass reports `titles_as_quotes` (which we surface on `LiteratureReport` as a warning naming the
PMIDs) and warns when a stale quote counter disagrees with `studies.csv`.

**What is still open is this entry's own subject: the pre-flight.** `registry_check` runs the
literature pass on the *server*, and what comes back is a verdict, not the pass's warnings — so the
new signal reaches an author who runs `enrich_literature_pass` locally and not one who runs the most
expensive check on the surface — twice over, since both live instances were still serving
`format: 0.6.1` on 2026-08-21 and the server runs its own pass, not ours. `RM17`'s local check is what covers the second author today, from the
authored file and with no network. The measurement below is the pre-0.6.5 behaviour and is kept as
the record of it.

**The probe.** Two spec directories, identical except for `studies.csv:provenance_quote`:

- `baseline_original` — the module as published: 69 of 69 rows quoted, 3 distinct strings, one per
  PMID, each the article's own title.
- `aggression_anger` — remediated: 1 row carries a passage located in the article's Discussion that
  names that row's variant, 68 are empty on purpose.

Both were put through `registry_check(target="test", literature=true, strict=true)` — the most
expensive check on the surface, the one that runs the literature pass over the network, ~20 s each.

**What came back, both times:**

```
verdict: true      blocking: []      non_blocking: []      unchecked: []
```

Byte-for-byte the same answer. The literature pass ran (the elapsed time says so) and produced no
finding, no counter and no mention of quotes in either direction. `validate_module(strict=true)` and
`compile_module(strict=true)` are equally silent — their warnings on the remediated module were the
deprecated `sources.csv` spelling and the missing closure, and nothing else.

So an author who does the most careful thing the tool offers, and reads the result honestly, learns
nothing about the one column that carries the module's evidence. That is how 3668 title-quotes
reached production through this workflow without anybody being careless.

**`lint_rows` is silent too, and its silence has a shape.** Three rows carrying the *same* title
string, pasted straight in:

```
errors: 0   warnings: 0
findings: 6 × info — chrom, start, ref, doi, p_value_num, provenance_regex
              "left to the author on purpose: … comparing it against a source"
```

`provenance_quote` is absent from that list only because those `info` findings name the
redundancy-bearing columns you left **empty**. Fill it with anything at all — the article's title
included — and the linter stops mentioning it. The one thing it will never say is that the same
string is in every row.

**Why upstream's two notes do not close this one.** `S54` asks the compiler to reject a quote equal
to `CitationHint.title`; `S56` asks it to notice that `literature.csv` disagrees with `studies.csv`.
Both are right and neither is ours. But `registry_check` is *our* projection of the registry's dry
run, it is what the skill tells an author to run before publishing, and its docstring says it
"checks what nothing offline can". A pre-flight that says `verdict: true` and nothing else, on a
module whose entire evidence layer is metadata, is a green light we issued.

**The cheap detector needs no pass at all**, which is the part that makes this ours to build: group
`studies.csv` by `pmid`, count *distinct* non-empty `provenance_quote` values, and report any PMID
with exactly one across many rows. That is offline arithmetic over an authored file. It belongs in
`lint_rows` and in `validate_module`, beside the other authored-table findings, at `warning` — a
repeated quote is a signal, not a malformed module.

**Two candidate repairs that are wrong.**

- *Wait for upstream.* `S54`'s fix lands inside `_study_quote_found`, which — per `S56` — never runs
  on the modules that have the problem. Our check reads the authored file directly and does not
  care whether any pass ran.
- *Refuse the publish.* One quote per PMID is legitimate when a module cites a paper for one row.
  The signal is one quote across *many* rows citing it, and even then a warning is the honest level:
  the author may have chosen a trait-level grain deliberately and said so.

**What was done meanwhile.** Nothing in code — this is the finding, not the fix. The skill half
shipped: `find-evidence` now carries "what may honestly go in `provenance_quote`" with the shape
detector in it, and `studies.md` carries the measurement as its first gotcha.

## F45 — no tool writes an authored cell, so no authoring move can go through the log that policy requires

**Found:** 2026-08-20, editing 69 `provenance_quote` cells · **Severity:** high · **Status:** open

`CLAUDE.md` §2's counterstance has three parts, and the second is *"every authoring move goes
through the log… there's a whole `logs/` surface for this and I would want to have every authoring
move going through any tool logged"*, with the corollary *"a move the agent makes by hand is harder
to capture, so make it go through a skill that logs"*.

**There is no such tool and no such skill.** The write surface is `scaffold_module`, the drafters,
the enrich passes, `compile_module` and `close_module`. Not one of them writes a cell an author
chose. So the central authoring act — deciding what goes in a cell and putting it there — happens
entirely outside the product, and therefore outside anything that could log it.

**Measured by doing it.** Replacing the quotes meant `uv run python` with a `csv.DictWriter`, driven
by hand. Per §7 that is the exercise stopping: I stepped outside the product, and I am recording it
rather than presenting the script as a method. The log entry the policy asks for
(`logs/quote-remediation.log`) I then *typed*, which is exactly the "harder to capture" case the
corollary predicts — nothing verified it against what actually changed, and nothing would have
noticed if I had written a different number.

**What a fix looks like, and the ordering matters.** The smallest honest thing is not a general cell
writer. It is a tool per *decided* authoring move, each of which appends its own log line: for this
case, something like `write_provenance_quote(spec_dir, rsid, pmid, quote|null, located_by, reason)`
that verifies the quote is verbatim in the retrieved text before writing, refuses a string equal to
the article's title, and appends to `logs/`. That is small, it is auditable, and the log becomes a
record of what happened rather than a note about it.

**Why the general version is wrong.** A `write_cell(table, row, column, value)` tool would put the
same tooling behind a `weight`, a `clin_sig` and a `conclusion` — the values §10 says an agent must
put in the decision list rather than write. The write surface should widen one *decision* at a
time, not one *column* at a time.

## F46 — the licensing obligation is announced only by the one tool in the chain you need not call

**Found:** 2026-08-20, adding the article licence row after quoting a paper · **Severity:** medium ·
**Status:** open

Quoting an article's text into `studies.csv` puts publisher text in the module's **annotation**
layer, which is the layer where `commercial_use=false` actually bites. `licensing.csv` needs a row
carrying **that article's** terms — not the service's, because the terms are per article.

The product says so, once, in the right words: `discovery._licensing_notes` builds a
`SourceLicenseNote` whose text ends *"If you copy a passage from an article into studies.csv, that
is a SECOND row at layer='annotation' carrying the ARTICLE's licence, not this service's — use
lookup_open_access to read it, because those terms are per-article."*

**It rides on `LiteratureSearchResult` and nothing else.** `lookup_citation`, `lookup_open_access`
and `fetch_fulltext` carry no `licensing` field at all. So:

- the tool that *knows* the article's licence (`lookup_open_access`) says nothing about owing a row;
- the tool that hands you the text you are about to quote (`fetch_fulltext`) says nothing either;
- the only tool that mentions it is `literature_search`, and an author working from a PMID they
  already hold — a remediation, a hand-off, a module somebody else started — never calls it.

**Measured by being that author.** This whole session ran `lookup_citation` → `lookup_open_access` →
`fetch_fulltext`, three tools, six calls, and received not one licensing note. The `sources.csv` row
for the quoted CC-BY article got written because I re-read the skill, not because anything asked.

And a missing `licensing.csv` row is a **warning, not an error**, so the module publishes green.

**The fix is small and the right shape is a question.** Attaching `licensing` to
`OpenAccessResult` is one line of model plus one call to the existing builder — but the note it
would carry is per *service*, and what is owed here is per *article*. `lookup_open_access` is the
one tool that holds the article's own `license` string, so it can say the true thing:
*"you now owe a `licensing.csv` row at `layer=annotation` for `pmid:24489884` carrying `cc-by`"*.
That is more useful than the generic note and it is only available there.

**A candidate that is wrong: writing the row.** `declared_use` is a licence position only the author
can take, and a fabricated licence string is worse than the missing warning. Name the obligation,
name the licence you read, and stop.

## F50 — "Try the locations below" when there are none, because the fallback needs a DOI the caller did not pass

**Found:** 2026-08-20, chasing an author manuscript by PMCID · **Severity:** low · **Status:** open

`fetch_fulltext(pmcid="PMC10508260")` on an embargoed author manuscript returns, correctly,
`retrieved: false` and `text_source: null` — and this warning:

> Nothing was retrieved. `text_source` is null, which means UNCHECKED — not that the paper has no
> text. Try the locations below.

`locations` is `[]`. The reason is one line above the return: `if doi: locations =
open_access(...).locations`. Called with a `pmcid` and no `doi`, the branch never runs, so the advice
points at a list the same call declined to populate.

The three-valued half of that message is exactly right and is the reason the message exists —
`null` is unchecked, not "no text". It is the last sentence that spends the caller's trust: an
instruction that cannot be followed reads as a defect in the caller's own request.

**Candidate fix.** Either resolve the DOI first when only a `pmcid` was given — `lookup_citation`
already gets one from the same `esummary` response — or say the true thing when the list is empty:
*"no open-access locations were looked up, because that needs a DOI; call `lookup_open_access` with
the DOI or PMID."* The second costs nothing and never issues a request the caller did not ask for,
which fits the tier rule better.

## F51 — `uv run` answers about whichever repo you are standing in, and both report `just-dna-format 0.6.1`

**Found:** 2026-08-20, checking whether an upstream fix had reached us · **Severity:** high ·
**Status:** open

`CLAUDE.md` §8's rule for an upstream fix is *"verify state 2 against the installed package, never
the sibling checkout"*, and it names the exact move: import the symbol and check. That check was run
and it lied, because `uv run` resolves against the project of the **current working directory** and
the command happened to be chained after a `cd` into `../just-dna-format`.

```
cd /data/sources/just-dna-format     && uv run python -c "…'curator' in StudyRow.model_fields"  -> True
uv run python -c "…'curator' in StudyRow.model_fields"  -> False
```

Both print `just-dna-format 0.6.1` from `importlib.metadata`. Both resolve `just_dna_format.__file__`
to a `site-packages` path — a *different* venv, but the path shape is identical and nothing in the
output says which project answered. So the one discriminator the rule relies on is silently
working-directory-scoped, and the version string cannot break the tie because upstream develops in
tree without bumping it.

**It nearly shipped a false status line.** `F43` was seconds from recording `StudyRow.curator` as
available; it is not, and every mitigation resting on its absence would have come out early. The
sibling tree is where a fix appears *first*, so this failure mode is most likely at exactly the moment
it matters most — the hour after upstream answers.

**What actually protects against it, in order of strength.**

1. **Print `__file__` in the same command as the symbol check** and read the venv path, not just the
   symbol. Two lines, no ambiguity, and it is what caught this.
2. **Never chain a symbol check after a `cd`.** Run it as its own command from this repository, or
   use `uv run --project /data/sources/just-module-creator`, which pins the environment regardless of
   cwd. The agent guidelines already say to use absolute paths in git commands for the same reason;
   this is the same trap on a different tool.
3. Do not lean on `importlib.metadata.version` to tell two code states apart. It is right about the
   release and says nothing about an in-tree change, which is the whole of state 2.

**Why this is ours and not a note upstream.** Nothing is wrong with `uv`; the defect is in a
verification recipe of ours that assumes a command means the same thing from any directory. The fix
is the recipe.

## F58 — nothing tells an author how long a `description` should be, and six of seven published cards are paragraphs

**Found:** 2026-08-21, from the owner reading `antonkulaga/cognitive_intelligence`'s catalog card ·
**Severity:** medium · **Status:** mitigated here in `8fb2825` — the norm is homed in
`skills/module-tables/references/module_spec.md` and repeated at `scaffold_module`'s `next_step`. The
upstream half is open as format-tree `S63` and is tracked in `docs/just-dna-format-pending-fixes.md`;
the tool-surface prose change rides into the CHANGELOG at the next bump.

The card's description ran to fourteen rows. The owner's read: *"Although there is no restriction I'd
say 5-15 words length is optimum otherwise it looks bloated."*

There is indeed no restriction, and that is the finding — not that one module overran, but that **no
surface an author touches states a target at all**, so every module that came out long came out long
for the same reason.

**What the published catalog actually looks like.** `registry_search()` against production, all seven
modules, word count of `description`:

```
 79 words  antonkulaga/aggression_anger_snps@2.0.0
 60 words  antonkulaga/cognitive_intelligence@2.0.0     <- the fourteen-row card
 45 words  antonkulaga/bodybuilding@1.0.0
 38 words  antonkulaga/big_five_personality_snps@2.1.0
 36 words  ksuha-dna/placebo_response_claude@1.0.0
 25 words  antonkulaga/risk_impulsivity_snps@2.0.0
  8 words  eric-mods/lactose_tolerance@1.0.1
```

One of seven is inside the band, and it is the outside author's two-variant module. **Measure the
published record, not the sibling checkout** — `../just-dna-format`'s spec for
`cognitive_intelligence` says 33 words where the published version says 60, and the immutable one is
the one a consumer sees.

**The length is the symptom; the repetition is the defect.** Four of the five specs under
`data/output/corrected_modules/` end with the byte-identical sentence *"Curated from the GWAS Catalog
(GRCh38), allele/strand-validated against dbSNP with a gnomAD r4 second witness."* Fifteen words, four
cards, and on a search-results page the description's only job is to tell this module apart from the
ones beside it. A sentence four modules share does the exact opposite of that while spending most of
each card to do it. Methodology already has three homes that persist and are meant for it —
`weighting:`, `authorship:` and `README.md` — and none of them is the card subtitle.

**We had already asserted the norm twice and stated it nowhere.** `tools/registry.py`'s
`registry_amend_readme` docstring says *"`description` is one sentence and cannot carry that"*, and
`skills/module-tables/references/readme.md` says *"because `display.description` is one sentence"*.
Both use the claim as a premise for something else; neither is anywhere an author looks while writing
the line, and the corpus above is what the unenforced claim was worth. This is §8's third prose-rot
shape exactly — an enforcement claim with no surface named. Two restatements, and the field's own
model carries no `Field(description=…)` at all, which is `S63`.

**Fix it.** The norm gets **one home** (`skills/module-tables/references/module_spec.md`, which owns
the field), and it is repeated at the one point an author actually meets the field: `scaffold_module`'s
`next_step`, which is the string an agent reads immediately before replacing the `<<REPLACE>>`. The two
existing assertions are sharpened to agree with it rather than left as independent claims.

**Surface it, do not fix it — and why each candidate repair is wrong.**

- **A `max_length` or a validator on the field.** Refuses a spec that is merely verbose, and refuses it
  at validate time, long after the prose was written and for a property that is taste rather than
  correctness. It would also make six published modules retroactively invalid, which is a false claim
  about finished work — they met every requirement that existed. Argued in `S63` and declined there.
- **A `lint_rows`-style length warning of ours.** Cheaper, but it fires at the wrong end of the stage:
  by the time a module lints, the description has been written, reviewed and forgotten. A warning that
  arrives after the decision is a warning that gets waved through.
- **The registry clamping or folding the card.** Rendering is theirs, and clamping hides content the
  author chose to write — the description would still be a paragraph, just an invisible one. Not filed
  in their intake for that reason.
- **Amending the four long ones.** `description` lives in `module_spec.yaml`, inside the attestation
  binding, so unlike the README it is not amendable — it costs a new version. That is the module
  author's call and not ours, and it is a decision for their list rather than a repair for ours.

**Sharpened the next day, and the correction matters.** Measuring it rather than reasoning about it
showed the cost is *worse* than a version: editing only `module.description` leaves `content_signature`,
`artifact.digest` and `resolution_signature` byte-identical and **wipes `manifest.verification` to
`null`** — a closed module becomes one that "records no closure". So the sentence to quote is *costs a
version and the closure record, in exchange for changing nothing measurable*. That is `F59`, filed as
format `S64` and registry `S16`; the decision-list framing above is unchanged, only its price tag.
