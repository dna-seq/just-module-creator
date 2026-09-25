# Previously resolved findings

Dogfooding findings (`F#`) resolved **here**, each with its resolution and a code
pointer. Findings move into this file from [dogfooding.md](dogfooding.md); they
are not copied.

**Check here before re-investigating a finding that looks fixed.**

---

## F83 — two runs picked the identical 49 variants and split on all 49 reference-homozygote rows

**Measured 2026-09-01, one paper, two independent runs** (`10.1007/s11357-025-02044-3`). The agreement
is the striking half and the disagreement is the useful one:

| | `run-ards-c` | `run-ards-d` |
|---|---|---|
| rsIDs selected | 49 of the paper's 263 | the same 49 |
| `(rsid, genotype)` pairs | 147 | the same 147, `key_jaccard` **1.00** |
| `stat_significance` | — | agrees on **147/147** |
| `direction` | — | agrees on **98/147** |

**Every one of the 49 disagreements is the same cell**: the reference homozygote. `run-ards-c` wrote
`direction: neutral` there; `run-ards-d` wrote the variant's own direction. Both wrote
`state: neutral`, `weight: 0.0` and `effect_allele: A` on that row, so the two runs agree on
everything except what `direction` is *about*.

**The schema settles it and no skill of ours said so.** `describe_table` returns `direction` as
*"orthogonal to `state`"* and `effect_allele` as *"the allele that `direction`/`weight`/`effect_size`
refer to"* — a property of the allele, which repeats across the variant's genotype rows. `run-ards-d`
is right. `run-ards-c` read `direction` as per-genotype, which is `state`'s job, and produced a row
whose `direction: neutral` silently answers a different question from the two rows above it.
`skills/module-tables/references/variants.md` carried the orthogonality bullet and never named the
subject; it does now, with the ref-hom row called out as the case that tempts.

**Why this is worth an F rather than a note.** It is a 100% systematic split, not noise: same paper,
same tool surface, opposite readings on every instance, and both compiled green under `--strict`. A
consumer reading `effective_direction` gets a different answer per run for the same genotype at the
same locus. **A vocabulary being closed and validated does not make its subject unambiguous**, and
nothing in the gates can catch a column that is filled consistently with the wrong question in mind.

*(A cosmetic tail: `run-ards-d`'s ref-hom weights are `-0.0000` — negative zero, from dosage-scaling a
negative beta by zero copies. Harmless to the compiler and ugly in a published CSV.)*

**Status (2026-09-25): resolved —** the skill half this entry reports as done is in place: `skills/module-tables/references/variants.md` (the `direction` / `state` bullet) now names the subject of `direction` as the allele, across every genotype row including the reference homozygote, and calls the ref-hom out as the tempting case. The `-0.0000` weight tail was cosmetic and was not acted on.

## F84 — `trait_tally: {checked: 0}` reads as a clean run, and a corrected diagnosis is why it is here

**Found 2026-09-01, and the version that survived verification is narrower than the version reported.**
A run said `check_identifiers`' trait check *never runs*, because it does not read
`studies.csv:trait_efo_id` — and reported that its own wrong CURIE (`EFO_0007796`, which is *parental*
longevity) had therefore passed every gate.

**Half of that is wrong and the transcript says so.** The check ran three times: `checked: 0` on the
first call, then `checked: 1, clean: 1` on the two after it. The `0` was honest for what it read — at
that moment `variants.csv` had no `trait_efo_id` column at all; the run added it later. And the wrong
CURIE never reached a gate: the run's own `lookup_identifier` call caught it before the column existed.
**Recorded because the correction is the lesson** — a run's self-report is evidence, not a finding, and
this one would have gone into the queue as a dead check if the tool calls had not been read back. Same
rule as `F65`.

**What survives is real, and it is two things.** The roster is `module_trait_ids(variants)`, so trait
ids living only in `studies.csv` — which has carried `trait_efo_id` since 0.3 — are never checked. And
`checked: 0, clean: 0, flagged: 0` is **indistinguishable from a module that declares no trait at all**,
which is the three-valued rule at a finer grain: a check that read an empty roster is not a check that
passed. The gene half is the same defect (a `gene` on a binning row is never checked), noted in our own
prose audit on 2026-08-20 and never filed, which was our mistake. Both filed together as format-tree
`S86`.

**Ours to improve too, and cheap**: our wrapper sees both tables, so it can say *"`studies.csv` carries
N trait ids this check does not read"* beside the tally. That is a plaster over a scope question that is
upstream's, and it is worth having anyway, because the `0` is what a reader acts on.

**Status (2026-09-25): resolved —** upstream `S86` shipped as `RM155` and is installed (enricher 0.7.2, `just_dna_enricher/identifiers.py::authored_identifiers`, `__file__` under `.venv/site-packages`): `check_identifiers(spec_dir=…)` builds the trait and gene rosters from every authored table carrying the column, and records the rest in `tables_not_read`. Our wrapper passes `spec_dir` (`tools/checks.py`, `_check_identifiers(spec_dir=target, …)`) and surfaces `tables_read` / `tables_not_read` on the result, so a `checked: 0` now says which tables it read.

## F78 — one PMC accession, two spellings, one session

**Found:** 2026-08-31 · **Severity:** low · **Status:** fixed here, 0.26.0.

`literature_search` returned `pmcid` as `"pmc-id: PMC12624115;"` while `fetch_fulltext` returned
`PMC12624115` for the same article, in the same session. Not a service disagreeing with itself:
PubMed's esummary spells the `pmcid` idtype with its label and a trailing semicolon, Europe PMC and
the OA service return the bare accession, and all three reached the caller verbatim because only
`doi` had a normalizer.

`pmcid_token` now mirrors `doi_token` at all three parse sites. It returns **`None`** for a string
with no accession rather than handing the wrapper back — a value that is not an id but looks like one
is worse than nothing, which is the same reason the DOI helper does it.

**Status (2026-09-25): resolved —** `discovery.pmcid_token` is applied at all three parse sites (PubMed esummary, Europe PMC, Semantic Scholar's `PubMedCentral`) and at the BioC rung. Same defect as `F30`, which retires with it.

## F81 — runs converging on our reference partly measure our own guidance

**Found:** 2026-08-31 · **Severity:** medium, and it is an interpretation defect rather than a code
one · **Status:** stated in the manuscript, `docs/BENCHMARKING.md` and `CLAUDE.md` §11.

Two of three runs matched the adjudicated SIRT6 reference **cell-for-cell on all three genotype
rows**, including the homozygous row that asserts nothing because neither cohort observed a carrier.
The obvious reading is that two independent judgements agreed and the reference is therefore sound.

**One of the runs volunteered the deflation, and it verifies.** `validate_module` names the missing
row explicitly — *"1 genotype(s) at 1 site(s) have no row… a gap in a set the author started rather
than a rule that fires once — e.g. rs117385980 T/T"* — and `skills/module-weights/GUIDE.md:122`
states *"A zero is a claim too — it says this genotype changes nothing, which is different from a
blank."* Its own summary: *"an expert following the same rulebook and receiving the same warning has
a fairly narrow path to anywhere else."*

So the supportable claim is narrower: **the workflow is prescriptive enough to produce consistent
output from independent runs.** That is worth having and it is not confirmation the output is
correct — it is the self-agreement shape the title-as-quote finding already taught us to distrust,
and upstream states the same about a module drafted from PubMind and checked against PubMind.

**The rule this leaves:** when a benchmark scores well, go find the tool output or skill line that
produced the score before crediting the run. The residual variance in this round was a single cell
(`suggestive` vs `not_significant` at p ≈ 0.07, upstream `S83`) that an aggregate score would have
hidden entirely.

**Status (2026-09-25): resolved —** the narrower claim is stated where it will be read — `docs/BENCHMARKING.md` ("the workflow is prescriptive enough to…"), `CLAUDE.md` §11 ("When benchmark runs converge on our reference…") and the manuscript. Nothing in code was owed.

## F76 — `output_dir` inside the spec directory poisons a registry call two steps later

**Found:** 2026-08-31 · **Severity:** medium · **Status:** fixed here, 0.26.0.

`compile_module(spec_dir=X, output_dir=X/build)` is the obvious call and nothing warned. The compile
copies `README.md` into `output_dir`; the registry uploader walks the spec tree recursively; and
`registry_check` then answers `ambiguous_spec_layout — README.md arrives from more than one path` with
a 422. The cost lands nowhere near the argument that caused it — the run that hit it lost a confusing
detour and a full restructure, with nothing pointing back at the compile.

**A warning, not a refusal, and that is the interesting half.** `reference-sirt6/` itself uses
`build/` inside the spec, and its artifact is fine. The layout is legal; what it costs is a later
call. Refusing would condemn working modules to catch a mistake that only matters if you publish.

**Status (2026-09-25): resolved —** `compile_module` appends a `layout_note` when `output_dir` is the spec directory or inside it (`tools/authoring.py`, the `out == source or source in out.parents` branch), naming the `ambiguous_spec_layout` refusal it leads to and telling the author to move the output beside the spec. A warning by design, as argued above. `F62` is the same mechanism and retires with it.

## F75 — one refusal, one reason, ten copies

**Found:** 2026-08-31 · **Severity:** low · **Status:** fixed here, 0.26.0.

A single `literature_search` emitted the same ninety-word DOI-refusal paragraph once per result — ten
copies — which is the repeated-warning shape `CLAUDE.md` §5 names outright: *aggregate repeated
warnings by reason, with a count, never one per row.* It was the run's loudest complaint about output
volume, in a report that had eleven other things to complain about.

The reason is now written once, with the count. Every row keeps its machine-readable
`refusal="redundancy_bearing"` token, so a caller filtering on it loses nothing — the prose was the
only duplicated part, and the prose is the expensive part.

**Status (2026-09-25): resolved —** `discovery._DOI_REFUSAL` is written once, on the first withheld row with the count (`"… ({n} DOIs withheld in this result.)"`), and every later row carries `_DOI_REFUSAL_REPEAT`; each keeps `refusal="redundancy_bearing"`.

## F74 — the same argument, accepted by two of our tools and refused by the third

**Found:** 2026-08-31 · **Severity:** medium · **Status:** fixed here, 0.26.0.

`declared_use` takes `non_commercial`; the enricher's CLI flag is written `non-commercial`. So an
author who has just read a `--use` line types the hyphen. `enrich_facts` and `refresh_sidecar` folded
it; `registry_check` passed it straight through and the server answered 422 without naming the hyphen
or the accepted spellings.

**Two-and-a-half rules, not two.** `passes.py` also carried its own hardcoded
`("unstated", "non_commercial", "commercial")` tuple — the hardcoded-vocabulary defect §2 forbids,
sitting next to a correct call that read format's `VALID_DECLARED_USE`. One helper in `_shared` now,
reading the format's own vocabulary, with all three call sites through it and a test that exercises
the entry points rather than the helper: the defect was never in the fold, it was in a call site that
did not use one.

**Status (2026-09-25): resolved —** `tools/_shared.normalize_declared_use` reads format's `VALID_DECLARED_USE` and folds the hyphen, and every entry point goes through it: `tools/checks.py` (two sites), `tools/registry.py` (`registry_check`), `tools/passes.py` and `tools/refresh.py`.

## F71b — `record_override`'s returned note described a mode the call had not used

**Found:** 2026-08-31 · **Severity:** medium · **Status:** fixed here, 0.26.0.

`F71` split the persisted log line on `source_value` — *outranks* with one, *authored* without — and
left the returned `note` unconditional. So a call recording a judged cell got back *"the cross-check
still reports this mismatch … a recorded outrank is downgraded, never passed"*, when there was no
source, no mismatch and nothing to downgrade. The note is the one field a caller reads to learn what
just happened.

**Kept under `F71`'s number with a suffix on purpose**: it is the same defect, one field over, and
numbering it separately would hide that fixing half a surface is how this happened. The test asserts
both branches and was run against the old code and watched to fail.

**Status (2026-09-25): resolved —** `record_override`'s returned `note` branches the same way as `move_line` (`tools/provenance.py`, the `note=(…)` block with the `F71b` comment): table-scope, outranking (with `source_value`) and authored (without) each get their own sentence.

## F71c — `OverrideRecord.authored_value` promised what the read path cannot deliver

**Found:** 2026-08-31 · **Severity:** low · **Status:** documented here, 0.26.0; not fixable in code.

`review_queue` reports `authored_value: ""` on every entry, always. Upstream's `ProvenanceItem` has no
slot for it, so our field, value, source and timestamp are packed into a `[jmc field=… value_sha256=…]`
suffix inside the free-text rationale and only the digest survives. The code says so in a comment —
`# not stored; the digest is what binds` — while the field's own description said *"What the module
says, at the moment of the record."*

**The description was the defect, not the design.** The digest is the right binding and
`current_value` / `still_bound` answer the question a reader actually has. The field now says it is
set on write and empty on read-back, and points at the two that work. A gap named in a comment and
denied in a description is the shape §7 exists to catch.

**Status (2026-09-25): resolved —** `OverrideRecord.authored_value`'s description (`overrides.py`) now says it is set on write and empty on read-back, explains that upstream's `ProvenanceItem` has no slot for it, and points at `current_value` / `still_bound`.

## F73 — a paper's published coordinates are GRCh37 and nothing warns you; two independent runs caught it, and neither was told to look

**Found:** 2026-08-31, both centenarian benchmark runs, independently · **Severity:** high ·
**Status:** open. The behaviour is correct at every layer; the gap is that nothing *says* so in time.

Both runs authoring from PMID 41057961 discovered the paper publishes **GRCh37/hg19** coordinates
while the module declares **GRCh38**, and both reached the same repair: author `rsid` only, never
paste the paper's `chrom`/`start`/`ref`/`alts`.

**Verified here, not taken on trust** (live Ensembl, both assemblies):

| rsID | GRCh37 | GRCh38 | delta |
|---|---|---|---|
| `rs61849494` | `chr10:51613269 G/A` | `chr10:45982565 C/T` | **5.6 Mb, and strand-flipped** |
| `rs11228733` | `chr11:56468368 C/T` | `chr11:56700892 C/T` | 232 kb |

**Why this is worse than an ordinary mistake.** A pasted GRCh37 coordinate is a *well-formed* row.
`lint_rows` passes it, `validate_module` passes it, and the compile is green — because
`compiler.resolution._verify` compares an authored coordinate against the resolver's, and an author
who pastes both a GRCh37 `chrom/start` **and** the matching GRCh37 `ref` has written a
self-consistent pair. The module then annotates nothing, or worse, annotates the wrong locus. `F73`
is the coordinate half of the same shape as the `provenance_quote` title problem: a check that
passes over a value nobody could have got wrong in the way the check tests for.

**One run put the rule in its own words**, which is the phrasing worth keeping: *"author rsid-only
rows; never paste the paper's chrom/start/ref/alt"*. The other reached it from the methods section
and cross-checked one variant. Two independent arrivals at the same repair, from the same paper, with
nothing in the prompt pointing either of them at it.

**They also agreed on a second consequence.** The paper's supplementary carries **47 variants with no
rsID**, which are unusable without a liftover this plugin does not do. Both excluded them and said so
rather than pasting the GRCh37 positions. That is the right call and it is a real capability gap: a
module cannot carry a position-only variant from a GRCh37 source at all.

**What the skills say today, and why it was not enough.** `module-enrich` covers the off-by-one
signature and the *recovery* of an rsID from an old-assembly coordinate — the repair after the fact.
`module-curate` warns about the coordinate mistake no offline gate catches. Neither says *check the
source's assembly before you author a coordinate at all*, which is the moment the decision is made.
Both runs got there by reading the paper's methods, not by being told.

**Measured properly the next day, and the picture is sharper than the first report.** Probed with a
minimal spec pasting `rs61849494`'s GRCh37 coordinate onto a GRCh38 module: `validate_spec` passes
(correctly — it is offline); **`enrich(mode="strict")` REFUSES**, raising `EnrichmentError` and
leaving the module untouched, with a diagnosis that names the repair outright; `best_effort` reports
all three lines then writes the wrong coordinate into `resolution.csv`; and
**`compile_module(strict=True)` then succeeds silently** over that file. So the enricher's strict flag
already does the right thing, and the hole is that the diagnosis is discarded before the compiler sees
it. Filed as `S78`. Our own default is `best_effort`, which is the path that meets this.

**The ask filed is broader than the coordinate**, on the owner's framing: *a `compile --strict` over a
`resolution.csv` produced by a `best_effort` enrichment should be blocked.* The two strict flags
promise different things — the enricher's means every row was checked against the reference, the
compiler's means the artifact is reproducible — and a module that ran `best_effort` then compiled
`--strict` collects the second stamp without the first having been earned, with nothing in the
artifact recording which happened. That makes the mode a property of the **sidecar** rather than of
the run: `resolution.csv` should carry the mode that wrote it. Refusal rather than a warning, because
the softer option has already failed once here — upstream's diagnosis is excellent and a green
artifact still came out the end, since a report nobody must read is not a gate. Migration cost is
real and stated in the item: an existing sidecar carries no stamp, so absent must read as *unknown*
rather than as `best_effort`, or the rule retroactively blocks recompiling published modules — `None`
is not `False`, at the artifact level.

**Surface it, and the fix is prose plus possibly a check.**

- **The prose fix, which is ours and cheap:** `module-curate` and `module-start` should say that a
  source's genome build is a triage question, and that the safe authoring default from any paper is
  **rsID-only** — let resolution supply the coordinate, so the compiler's rsid-vs-coordinate check has
  something independent to compare. That is the rule both runs invented.
- **A check is harder than it looks and may be upstream's.** "Does this authored coordinate match the
  declared build" is exactly what resolution already answers — but only for rows that carry an rsID.
  A position-only row from a GRCh37 source has nothing to disagree with. That may be worth an `S`
  once we can state the ask precisely; not filed yet, because we have not established what upstream
  could check that it does not already.

**Status (2026-09-25): resolved —** both halves the entry asked for are done. The prose is `skills/module-start/GUIDE.md` step 0: ask what build the source is on, default to `rsid` only, and exclude variants that have no rsID. The check is upstream `S78` → `RM143`, in installed compiler 0.7.1: `verification_findings_recorded` makes strict validate and compile refuse over a coordinate the enricher found to be on the wrong build. Carrying a position-only GRCh37 variant still needs a liftover nothing here does. The skill states that limit and nothing plans to build it.

## F72 — a corpus-sized `enrich` is indistinguishable from a hang, and the fix is upstream's but not ours to wait for

**Found:** 2026-08-31 · **Severity:** medium · **Status:** worked around here, with a dismantle note.
Upstream's real fix is `S66` ask 4, accepted and shipping in **0.7** (`RM128`).

A 263-rsID module ran **20+ minutes** inside `enrich_module` writing nothing. `enrich()` persists
`resolution.csv` only at the end, so silence is the expected appearance of work — and an operator
watching it cannot tell that from a dead process. The run that left the short sidecar in `F70` died
during one of these silences — though the sidecar itself turned out to be a completed write, so the
ambiguity is what made the death invisible, not what shortened the file.

**Upstream already owns this and already answered it.** `S66` ask 4 is the progress callback; it is
accepted, minor-legal, and lands in 0.7 with the transaction and the `flock`. Verified against the
**installed** package rather than the changelog: `inspect.signature(enrich)` has no `progress`
parameter and `just_dna_format.layout` has neither `atomic_writer` nor `atomic_write_text` at 0.6.6.

**So we hold a workaround, and the owner's call is the reason:** 0.7 is being built and is not
expected soon, so waiting means every long run stays ambiguous until it lands.

**What the workaround is careful about.** It reports **elapsed seconds, never a fraction**. We cannot
know the denominator — upstream batches inside `resolver.py` rather than looping per subject, which
is precisely why *they* have not settled what the callback counts — and a percentage of ours would be
a fabricated measurement of another layer's work. A heartbeat answers the question actually being
asked, which is *alive or dead*, and answers nothing it cannot.

**TO DISMANTLE AT 0.7**, and the marker is in the code beside the task group: delete `_heartbeat`,
`_HEARTBEAT_SECONDS` and the task group, pass `progress=` into `enrich()`, report real
`(done, total)`, and delete
`test_a_long_enrich_reports_it_is_alive_without_inventing_a_fraction`. The subject count then comes
from upstream instead of being unknown, which is the whole reason to stop doing it ourselves.

**Status (2026-09-25): resolved —** the upstream half is installed (enricher 0.7.2: `enrich(…, progress=…)`, `RM128`), and `enrich_module` passes a `progress` callback and reports real `(done, total)` (`tools/passes.py`, `_note_progress`, commit `160ee5a`). The heartbeat was kept on purpose, because the callback is silent while the resolver batches. It now says elapsed time only before the first subject completes. Left for cleanup: `_ENRICH_TAKES_PROGRESS` / `_progress_kwarg` and the workaround test's docstring still treat pre-0.7 as possible, and the floor is 0.7.

## F70 — a completed `enrich` can leave a `resolution.csv` covering fewer subjects than the module authored, and nothing in the file says so

**Found:** 2026-08-31, in the benchmark round · **Severity:** medium ·
**Status:** filed upstream as format-tree `S76`, withdrawn there as a duplicate of `S66`, and the
withdrawal's arithmetic was **wrong in the reporter's favour** — corrected upstream 2026-08-31 under
the same entry. The reading that closes it is upstream's `RM141`, which is **in the 0.7.0 tree and not
installable**: 0.7.0 is bumped and untagged, and `uv sync` still gives 0.6.6.

**The heading and the mechanism both changed. What was reported first, and why it was wrong.** The
original write-up said an *interrupted* `enrich` left a *partial* file, that merge-not-clobber made
re-running entrench it, and that the correct recovery was to delete the sidecar or `refresh_sidecar`
first. Two of those three are false, and the preserved artifact is what says so.

**Proven, from the file** (`evidence-S76-partial-resolution/resolution.partial.csv`, hash-verified):
203 rows over **201 distinct rsIDs**, against **263** authored in that run's `variants.csv`. The rows
are sorted by rsid end to end and the last line terminates with a clean CRLF, and the 62 absent rsIDs
scatter across the whole alphabetical range of the authored set rather than falling off the tail. That
is a **complete write of an incomplete resolution set**, not a truncated file.

**Why the enricher produces one, by design.** `_write_resolution_csv` runs once, at the end. A subject
whose live request could not be *made* joins `unreachable_rsids` and is written as **no row at all** —
deliberately, because `status="not_found"` would state that a source was asked and said no, which is a
negative nobody established. So an ordinary `best_effort` run over a source that stops answering
produces exactly this file, with no interruption anywhere.

**Re-running is the correct recovery, and the original advice to delete first was wrong.** In the
installed 0.6.6, `need_pos` and `need_rsid` skip only the subjects an existing row already covers
(`enrich.py`, the partition below the merge). The 62 missing subjects are not in `existing`, have
nothing to merge onto, and go to the resolver like any other. Upstream measured the same on their tree
and on `v0.6.6` from its own tag. **Do not delete a sidecar to recover from this** — that is the
destructive move `refresh_sidecar` exists to make safe, and here it buys nothing.

**What survives, and it is the whole finding.** Nothing in the file, its header or any sibling records
that it covers 201 of 263. A reader opening the directory has to count distinct authored rsIDs and diff
the two sets. The `verification.json` half also survives for 0.6.6: it was written before the run ended
and attests bytes a completed enrich would change, and that half at least announces itself through the
stale-verification warning. Upstream reports the two are inside one commit block in 0.7.

**Where the fix actually comes from, which the first write-up got wrong too.** This is not `S66`'s
family: `RM128`'s transaction and atomic write cannot prevent a file that was never half-written.
`RM141` is what closes it — `validate --strict` refuses a table that cannot place every authored
subject and names them, `validate` warns per uncovered row — and it is a **reading computed from the
spec beside the table**, not a marker in it. Upstream refuses a durable partial marker on the grounds
that it is a fact about a *run* living in a table of facts about *variants*, and that a killed process
writes no marker anyway. Both arguments hold.

**Ours, until 0.7 is installable.** Count `resolution.csv`'s distinct subjects against the authored
set before trusting anything downstream — which is what `enrich_module`'s own refusal text already
tells a caller to do. A detector of ours would belong beside `audit_module`'s decision list, three-valued,
with `unknown` where the authored subject set cannot be determined; it is **not worth building**, because
upstream's own `validate` answers it in the command our loop already runs first.

**Status (2026-09-25): resolved —** upstream `RM141` shipped in 0.7.0 and is installed (compiler 0.7.1). Probed on a copy of `assets/longevity_2026` with `resolution.csv` cut to two rows: `validate_spec` warns `rsid_unresolved: 11` and strict refuses with `strict compile: 17 variant(s) have unresolved genomic positions` and names them. A short sidecar is now caught by the command the loop already runs.

## F69 — a `p_value` and an `effect_size` on one row are asserted to belong together, and nothing records or checks that they do

**Found:** 2026-08-31, reviewing the two-agent reproducibility benchmark · **Severity:** medium ·
**Status:** filed upstream as format-tree `S75`; nothing to build here until the column exists.

The benchmark's two runs overlapped on exactly one row and disagreed on it: `rs117385980` / PMID
41249831, both writing `effect_size 1.42 / OR / not_significant`, one writing `p_value 0.36` and the
other `0.75`. **Neither was a misreading.** The paper reports two tests of the same association —
Table 3/5's allelic Fisher's exact (`OR 1.4, p 0.36`) and Table 6's univariate logistic
(`OR 1.42, CI 0.18–11.67, p 0.75`) — and each run took one.

Run B's row is internally consistent. **Run A's is not**: Table 6's effect size beside Table 3's
p-value, with its own `conclusion` citing Table 6's CI, so the row names one analysis's estimate and
another's p-value. Run A identified this itself when asked, and the run is frozen with the mispairing
in place and annotated, because repairing it would have destroyed the comparison it is evidence for.

**Everything was green** — strict validate, strict compile, `audit_module`, and `quotes_found`. The
provenance quote is verbatim and correct: it grounds the significance *verdict* and contains no
statistic, so quote verification is structurally blind to this. `audit_module`'s
`effect_size_is_its_own_z` is a different check and does not reach it.

`StudyRow` has `study_design` (*"e.g. meta-analysis, GWAS"*), which describes the **study**; nothing
describes the **analysis**. And `key.columns` is `["variant_key", "pmid"]` on equality, so a paper
reporting several analyses of one variant is representable by exactly one — chosen silently, with no
field recording which. A correct row and a mispaired one are byte-indistinguishable to every consumer.

**Ours to file, not to build, and that is the unusual part.** §11 says an authoring-workflow gap is
ours to build first — this is not one. The missing thing is a **column**, which is schema, which we own
none of. Until `S75` lands there is nowhere to put the fact, and a lint of ours could only compare two
numbers it has no way to attribute. What we can do meanwhile is what the reference module does: carry
one analysis, name the other in the README and `logs/authoring.log`, and say which was chosen.

**Surface it, and why the candidate repairs are wrong.**

- **A lint comparing `p_value` against `effect_size`.** There is nothing to compare. Both can be
  verbatim-correct and still come from different tables; correctness is not a property of either number
  alone. Only provenance separates them, and provenance is exactly what is not recorded.
- **Requiring `study_design` to carry the test.** It would overload a field that already means
  something else, on rows six published modules have already written, and it would still not associate
  the test with a *particular* pair on a multi-analysis paper.
- **A convention in our skills — "always take the regression model".** It picks a winner the source
  does not; here the right answer is the *other* one, because a zero cell makes Fisher's exact the
  appropriate test and the logistic MLE unstable. A rule that would have produced the wrong number on
  the first case it met is not a rule.

**Status (2026-09-25): resolved —** upstream `S75` shipped as `RM140` and is installed: `StudyRow.statistical_test` exists in format 0.7.0 (`__file__` under `.venv/site-packages`), described as which analysis produced the row's `p_value`/`effect_size`. `skills/module-tables/references/studies.md` teaches it. It is not part of the row key, so one `(variant, pmid)` still carries one analysis, but which one is now recorded.

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

  > **Overturned 2026-09-01, by measurement, and the error is worth naming.** This bullet bundled two
  > different acts under one refusal. *Choosing which sheet answers a row's claim* is a judgement and
  > is still refused — `describe_supplementary` returns no rows and `read_supplementary` picks no sheet.
  > *Handing back the cells of a sheet the author named* is not a judgement; it is decoding a zip
  > container, and the layer argument never applied to it. Four independent authoring runs — 4 of 4 —
  > then hand-wrote an xlsx parser to get past the gap, two with a column-alignment bug that puts a
  > BETA in the chromosome column, one calling it 40% of its run. `read_supplementary` ships in 0.29.0
  > with `openpyxl` as a hard dependency. **The general lesson: a refusal that names a judgement should
  > be checked against what it actually blocks** — this one blocked the mechanical half for a month and
  > sent every author to write the same buggy parser.

**Not filed upstream, and nothing is owed.** This is authoring workflow, which is ours to build
(§11); the schema and the checks are unchanged. `S54` was the obvious place for a corroboration — its
evidence was that a rule against machine-located quotes produced 3668 titles, and the 42-of-65 number
says those rows had a real passage in reach the whole time — but **`S54` is answered and has moved to
`CONSUMER_SUGGESTIONS_HISTORY.md`**, and an answered entry is a closed record rather than an inbox.
The number is recorded here instead. Checked 2026-08-30, so nobody re-investigates whether it was
filed.

**Status (2026-09-25): resolved —** the tool half is built. `list_supplementary`, `fetch_supplementary`, `describe_supplementary` and `read_supplementary` are in `tools/research.py`, and `read_supplementary` shipped in 0.29.0 with `openpyxl` as a hard dependency (see the overturn note above). They return the cells of a sheet the author names and never pick one, which keeps choosing a sheet as a judgement. One thing remains and belongs to upstream: `LiteratureRow.quote_source` records only `fulltext|abstract`, so the pass still cannot say a quote was checked against a supplementary file.

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

**Status (2026-09-25): resolved —** the marker codec reads `source=(?P<source>.+?)` (`overrides.py`, the pattern under the comment dated 2026-08-24), so a source name with spaces or parentheses round-trips; the parametrized round-trip test covers the real names that failed.

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

**Status (2026-09-25): resolved —** closed by the `F76` fix in 0.26.0: `compile_module` now warns at the call that causes it when `output_dir` is inside `spec_dir` (`tools/authoring.py`, `layout_note`), naming the later `ambiguous_spec_layout` 422. It warns rather than refuses because working modules use that layout, which is the reasoning recorded under `F76`.

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

**Status (2026-09-25): resolved —** the upstream half (`S66` → `RM128`) shipped in 0.7.0 and is installed in enricher 0.7.2 (`just_dna_enricher/transaction.py`: `spec_lock` advisory `flock`, `ResolutionJournal` staging, `atomic_writer`, with `__file__` under `.venv/site-packages`). An interrupted run keeps its staged answers, the table is renamed into place, and a second concurrent run refuses. Those are the three things listed above as upstream's. Our in-process claim stays and is harmless.

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

**Status (2026-09-25): resolved —** fixed upstream and installed. Measured on compiler 0.7.1 (`__file__` under `.venv/site-packages`): `validate_spec(strict=True)` on `assets/fto_bmi` with `resolution.csv` removed returns `valid=False` with the same `strict compile: 3 variant(s) have unresolved genomic positions` error the compile gives, plus the `resolution_not_injected` warning. A green strict pre-flight no longer precedes a refused compile, so the sentence in `skills/module-compile/GUIDE.md` holds.

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

**Status (2026-09-25): resolved —** `server.INSTRUCTIONS` opens with `plugin v{__version__}` beside the format and compiler versions (`server.py`, commit `efc8fa9`, 2026-08-22), read from package metadata, so a stale process shows its own version before the first call. This is the stronger candidate the entry nominated. What it cannot do is stated above and is not a defect: a tool that is not registered stamps nothing, so the reader still has to compare the version.

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

**Status (2026-09-25): resolved —** same fix as `F19`: `server.INSTRUCTIONS` names the plugin version (`efc8fa9`), the candidate this entry called the natural home. The residual is the one the entry already names: a docstring edit made while a server runs moves no version string. The venv-swap variant of a stale server is tracked separately as `F107`.

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

**Status (2026-09-25): resolved —** fixed with `F78` in 0.26.0. `discovery.parse_pubmed_summaries` now returns `pmcid=pmcid_token(ids.get("pmcid"))`, which strips the `pmc-id:` label and trailing `;` and returns `None` for a string with no accession, so every service in a mixed search yields the bare `PMC…` form. The retrieval half (`F31`) is still open.

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

**Status (2026-09-25): resolved —** the licence-pair check is in the pre-flight in installed compiler 0.7.1: `_validate_spec` calls `_check_declared_license_agrees` on the `SourceRow` table. Probed on a copy of `assets/longevity_2026`: `validate_spec` reports `declared_license_disagrees: 1`. `skills/module-compile/GUIDE.md` states which checks appear only at compile (those that need resolved rows).

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

**Status (2026-09-25): resolved —** overtaken by a reversal rather than fixed as asked. The row this entry wanted `lookup_open_access` to announce, a `licensing.csv` row at `layer=annotation` for the article, is one upstream `RM46` and our own skills now say must not be written. Per-article terms live on `literature.csv` (`LiteratureRow.license`, `commercial_use`, `share_alike`, `redistribution` in installed format 0.7.0), `discovery._licensing_notes` says so and points at `lookup_open_access` before quoting (`F109`, 2026-09-24), and the installed compiler 0.7.1 warns `quoted_article_license_restrictive` when a quoted PMID's article forbids commercial reuse.

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

**Status (2026-09-25): resolved —** the recipe is fixed where it is read. `CLAUDE.md` §8 now requires `uv run --project /data/sources/just-module-creator` and printing `just_dna_format.__file__` beside the symbol check, and says `hasattr` or the version string alone does not tell the two trees apart. Nothing in code was owed.

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

**Status (2026-09-25): resolved —** upstream `S63` is released and installed. `ModuleInfo.description` in format 0.7.0 carries *"One short sentence — roughly 5–15 words — saying what this module is about…"*, and `title` and `report_title` have descriptions too. Our point-of-write repetition at `scaffold_module`'s `next_step` stays, as the pending-fixes entry says it should.

## F110 — `lookup_variant(frequencies=true)` is silent on every multi-allelic locus (upstream `S108`)

**Found:** 2026-09-24, same run · **Severity:** medium · **Status:** format-tree `S108` accepted
2026-09-24 as their `RM255`, fixed in tree, **not in a release we install** — close on the release

15 of 25 GWAS lead rsIDs came back with `populations: []` and no finding, because the enricher's
`_lookup_frequencies` returns early when `alts` holds a comma. That left the MAF match, which is the
only way to fix a palindromic pair's strand, with nothing to work from. HLA-DRB1 rs9271058 (T/A) was
dropped from the module for that reason. Our tool passes the upstream result through, so there is
nothing to add on our side beyond a finding, and once upstream answers, that belongs to them.

**Status (2026-09-25): resolved —** upstream `S108` → `RM255` shipped in enricher 0.7.2 (2026-09-25) and is installed. `just_dna_enricher/lookup.py` now splits `alts` on commas and asks about every allele, where it used to return early on a comma. `lookup_variant` passes the result through, so there was nothing to change on our side.

## F104 — a table-level authoring move had no honest home in the log

Found 2026-09-20 by the dogfooding seat. `record_override` is the only writer to
`logs/authoring.log` and its shape is one `(variant_key, field, authored_value)` per call. The tester
trimmed `pharm_variants.csv` in eleven modules to the panel's rsIDs (DPYD: 30 of 233 drafted rows
kept, 203 dropped across ~50 rsIDs) and deleted the file plus its ClinPGx licence row in two. Logging
per rsID would have been a hundred calls, so each module got one record with
`variant_key="pharm_variants.csv"` and `field="rows"` — which the tool accepted without comment,
logged with the cell verb *"authored … (judged; no value from clinpgx to disagree with)"*, and which
`review_queue` would have reported as a row it could not find. §2 says a hand move should go through
a tool that logs, and no tool trims a table.

**Half fixed 2026-09-20 (unreleased on 0.36.0), half surfaced.** The convention the tester improvised
is now the documented one: a `.csv` in the row slot with `field` in `{rows, file}`, counts in
`authored_value`, the derivation in `reason`; any other `field` beside a table name is refused with
the convention in the message. The log line carries its own verb (`table pharm_variants.csv rows=…`),
the returned note says what was recorded, and `review_queue` lists such records as `scope: table`
with a `table_scope` count, no longer folded into `subject_absent`. **Not built: a `prune_rows` that
applies a keep-list and logs the sweep.** Three written rules stand in its way and none is mine to
settle in an unattended run: `module-curate` says twice, in bold, that the trim is a decision no tool
makes; §10's silent-apply rulebook is TO-POPULATE-LATER and forbids settling a boundary case ad hoc;
and a row deletion is authored content destroyed, the strongest form of the write the counterstance
gates on a verified capture. The questionnaire is in the session report; `refresh.capture_now` is the
capture-and-verify step if the answer is build it. The tester's eleven logs are left as written — the
records are valid under the convention, only the verb on the line predates it.

**Fixed 2026-09-24, on the owner's decision** — *"making decision != executing it"* (CLAUDE.md §10). `prune_rows` applies a keep-list the author hands it to one authored table: refuses derived sidecars, an empty list and any keep value matching no row (unless `allow_unmatched`); copies the table outside the spec directory and hash-verifies the copy before rewriting; logs one table-scope record through the same `move_line` `record_override` uses. `module-curate` now says the keep-list is the curation and applying it is not, which leaves *"no tool makes it"* true. Tests in `tests/test_prune.py` over the real DPYD ClinPGx rows, `assets/pgx/dpyd_pharm_variants.csv`.

## F105 — the AlphaGenome pass cannot be aimed at "my rows", so scoring a module means writing a window planner

Found 2026-09-21 by the unattended seat porting `longevitymap` (1033 rows, 527 rsIDs, 272 genes) to
0.7 and adding expression predictions, on plugin 0.37.0 against enricher 0.7.1.
`enrich_expression_effects` takes one `gene` and one interval, and the interval is the corpus: the
whole module's genes span about 2 Mb of positions, roughly 6 M SNVs, an hour and a half of queries
and a table nobody could read. The honest query for an author's module is *the module's own
positions*, and nothing offers it — so the run planned 393 windows of 21 bases (positions merged
within 100 bp, keyed on the row's own `gene`), drove them through an in-memory client at ~2 s each,
and got 23,700 rows of which 714 module rows are actually scored. Two things the tool would have
known and the planner had to rediscover: a row whose `gene` label is not at that locus (the six
`TP53` rows on other chromosomes, the `LOC…`/antisense symbols the Atlas has no gene axis for) comes
back as a window with 63 rows and `withheld: {no_gene_axis: 63}` or a MANE warning, and a row with
no `gene` at all (256 here) cannot be asked about anywhere.

**Surface it, do not build it yet**: a `rows=true` mode that walks `variants.csv` × `resolution.csv`,
groups by `(gene, chrom)`, merges neighbours and reports per-row *scored / no gene / gene not at
locus* is one afternoon, and it is the mode every author of an existing module wants. Whether it
should also take a gene from the reference when the row has none is the question — that is an
authored value written from a source, and the rule is to surface it.

**Built 2026-09-24.** `enrich_expression_effects(rows=true)` plans windows from the module's own rows (`expression.plan_windows`: by row `gene` and chromosome, merged within 100 bp, padded 10 bp; 377 windows for longevitymap), queries them in order, stops at the first failure because of `F95`, and returns `windows`, `windows_run` and the same `row_status` as `F106`. A rows-mode `dry_run` is a plan read off local files and answers under offline too. **Left surfaced, as the finding asked**: a row with no `gene` is reported as `no_gene` and never given one from a reference — that would be an authored value written from a source. Not run against the live Atlas from this seat; the window loop is tested with the upstream call replaced.

## F106 — `top_expression_effects` cannot answer "which of MY variants does the model call disruptive"

Same run. The question the owner asked — *how many of the longevity-favourable SNPs does AlphaGenome
predict to disrupt their gene* — is a join of `expression_effects.csv` onto `variants.csv` through
`resolution.csv`, keyed on `(chrom, start, alt, gene)` with the effect allele read off the row's
genotype minus the locus ref. `top_expression_effects` ranks the whole table and filters by gene,
consensus and magnitude; `in_gene_only` filters by the gene span, not by the module's rows. The
join was fifty lines of script and produced the README's table (441 favourable pairs scored, 237
predicted decreases, 97 at ≥ 80 % consensus). The tool that reads the table back should take
`module_rows_only=true` and report the same per-row status as F105. Two facts to preserve when it
does: `effect_direction` is the track-majority sign and disagrees with the sign of `effect_size` on
some rows, so the direction column is the one to count; and a null direction is a real answer.

**Fixed 2026-09-24.** `top_expression_effects(module_rows_only=true)` keeps only predictions for a `variants.csv` row's own gene and effect allele (placed through `resolution.csv`), reports a `row_status` per authored row — `scored`, `gene_not_at_locus`, `not_scored`, `reference_only`, `no_gene`, `unresolved`, `unreadable` — and a `direction_counts` tally over the track-majority `effect_direction` with null counted as `unknown`. The join lives in `expression.py` so the reader and the `F105` planner cannot disagree. On the longevitymap port it reads 1033 rows as 584 scored, 144 reference-only, 252 without a gene and 53 unscored. Tests in `tests/test_passes.py`, one fixture row per status.

## F108 — `fetch_fulltext` returns the abstract for a PMC author manuscript that PMC's BioC endpoint serves whole

**Found:** 2026-09-24, building a module from PMID `30820047` (Kunkle 2019, *Nat Genet*,
`PMC6463297`) · **Severity:** medium · **Status:** open

The paper's per-locus results — lead rsID, major/minor allele, OR per minor allele — are in the
article's **Tables 1 and 2**, not in its supplementary workbook (ST5 has ORs without alleles, ST9
alleles without ORs). So the body text is the only route to a row, and `fetch_fulltext` did not reach
it:

| call | result |
|---|---|
| `fetch_fulltext(pmcid="PMC6463297")` | `retrieved: false`, `locations: []` — `F50` reproduced |
| `fetch_fulltext(pmid="30820047")` | `text_source: "abstract"` |
| `fetch_fulltext(doi=…)` | `retrieved: false`, seven repository locations, no text |
| Europe PMC `…/PMC6463297/fullTextXML` | HTTP 500 |
| PMC BioC `research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC6463297/unicode` | **200, 276 KB, both tables intact as table passages** |

The module was finished from the BioC copy, fetched with a raw `curl` — the ad-hoc route the product
exists to remove. **Candidate fix:** add PMC BioC as a rung after Europe PMC in the fulltext ladder,
behind `ServiceGate` under the NCBI budget, and return table passages as text rather than dropping
them: for a GWAS paper the tables are where the rows are.

**Fixed here 2026-09-24; the quote-check half is owed upstream as format-tree `S110`.** `discovery._bioc_fulltext` is the rung after Europe PMC: PMC BioC behind the shared NCBI gate, `text_source: "pmc_bioc"`, tables kept as tab-separated rows, the reference list dropped, and three outcomes kept apart — text, *PMC holds no copy* (an HTTP 200 whose body starts `[Error]`), and *could not be asked* (a warning that says UNCHECKED). Verified live: `PMC6463297` returns 68 KB including Tables 1 and 2. Tests in `tests/test_fulltext_bioc.py` over a trimmed real answer, `assets/literature/pmc_bioc_PMC6463297.json`. The enricher's own `quotes_found` check still reads Europe PMC only and only when `isOpenAccess`, so a module's quotes against this paper stay abstract-checked until `S110` lands — see `just-dna-format-pending-fixes.md`.

## F109 — `literature_search` tells the author to add the `pubmed` licensing row three skills forbid

**Found:** 2026-09-24, same run as `F108` · **Severity:** low · **Status:** open

Every `literature_search` result carries a `licensing` note from `discovery.py`: *"You read pubmed by
hand, so nothing wrote a licensing.csv row for it and the compile gate cannot see it. Add the row
yourself."* But `module-start`, `module-tables/references/licensing.md` and `.../literature.md` all say
**no `pubmed` row, ever** (upstream RM46: literature terms are per article and live on
`literature.csv`), and the 2026-08-31 measurement there found the row changes nothing. An agent that
trusts the tool over the skill writes a row upstream has refused. This run followed the skills and
compiled strict with no licensing warning. **Candidate fix:** drop the "add the row" sentence for
literature services and keep the second half about the article's licence, pointing at
`lookup_open_access`.

**Fixed 2026-09-24.** `discovery._licensing_notes` now says no `licensing.csv` row is owed for a literature service at any layer, that the article's terms live on `literature.csv`, and to read them with `lookup_open_access` before quoting. The old note's second half — a `layer='annotation'` row carrying the article's licence — contradicted the same rule and went with it. `SourceLicenseNote`'s field descriptions followed. Pinned by `tests/test_discovery.py::test_a_literature_source_is_never_told_to_take_a_licensing_row`, which fails on the old text.

## F98 — `clinical_claims_without_studies` keys on `clin_sig`, so a module can assert a clinical direction with no study behind it and the audit calls it clear

Found 2026-09-12 building `apoe_locus_compound` against 0.7.0 — a module deliberately shaped to have
a layer that *should* trip this signal.

Six of its fifteen `variants.csv` rows are `category=alphagenome_predicted`: they carry
`state=protective|risk`, `direction=protective|risk`, a non-zero `weight`, and **no `studies.csv` row
at all**. Their clinical role is assumed from an AlphaGenome expression prediction and nothing else.
That is exactly the shape "a clinical claim with no paper behind it" names.

`audit_module` reports:

```
clinical_claims_without_studies  clear
  "no row in this module asserts a clinical significance"
```

Correct as written, and misleading as read. The signal keys on `clin_sig`, which this module does not
author. `state`, `direction` and `weight` are clinical claims a consumer acts on just as readily — a
report saying "protective" does not first check whether the claim arrived via `clin_sig`.

**This is §8's prose rule 1 in our own code**: *a check is only as wide as the table it reads, and
naming a check without naming its scope is how a reader over-trusts it.* The headline says "no row in
this module asserts a clinical significance" when the defensible claim is "no row authors a `clin_sig`
value".

**Two repairs, and the cheap one is not obviously wrong.** Either widen the signal to count a row with
a directional `state`/`direction` and no grounding study, or leave the scope and fix the headline to
name the column. Widening is the one that would have caught this module; but it would also fire on
every legitimately ungrounded directional row, of which there are many in real modules, so it needs a
severity below `decide` or it becomes noise the first time somebody runs it on a GWAS module. Not
repaired here — it wants the decision, not a patch.

**Fixed 2026-09-12, and the fix had to be measured twice.** `directional_claims_without_studies`
now asks, per row, whether *this row's own variant* is named by a study — not whether `studies.csv`
has any row at all, which is what the sibling asks and what passes a thousand-row module carrying one
citation. `clinical_claims_without_studies` keeps its scope and loses its overclaiming headline: it
now says *"no row authors a clin_sig value"* and names the tables it read.

**The first cut of the new signal was wrong in both directions and the reference corpus caught it.**
Run over 21 real modules it fired on four; two were its own join failing, not a gap in the module:

- `mt_common_deletion` reported all three rows uncited. Its `variants.csv` says `chrM` and its
  `studies.csv` says `MT`, and the hand-rolled fold `lstrip("chrCHR")` turns those into `M` and `MT`.
  The signal was inverted by a contig spelling. It uses `just_dna_format.vrs.normalize_chrom` now —
  the schema-fact rule at a different address.
- `cyp2d6_structural` reported its CNV uncited. A symbolic allele spans an interval and its study
  cites a point 99 bp away. Those rows are now set aside **and counted**, never silently dropped: a
  row the signal could not assess is not a row it cleared.

After both, 3 of 21 fire and all three are true positives, verified by grepping each rsID:
`hboc_palb2` (rs786203382, rs1597101776) and `shox_par1` (rs1170991098) each carry a directional row
whose rsID appears zero times in their own `studies.csv` — two uncited rows in upstream's own
reference examples — plus this module's six. `pathogenic_clinvar`'s 328 leaning rows stay quiet.

**What saved this module is not the audit.** The prediction-only rows are legible because the author
put `PREDICTION ONLY` at the head of every `conclusion`, set `flags=predicted_only`, `method=
alphagenome-expression-prediction` and `stat_significance=unknown`, and said so in the README. All of
that is convention, none of it is checked, and a less careful author gets a green audit over the same
shape.

## F100 — the taught scaffold → draft path dead-ends on a fresh scaffold, twice

Found 2026-09-20 by the dogfooding seat, first module of the ClawBio PGx run, plugin 0.35.0 on
compiler/enricher 0.7.0. `scaffold_module(kinds=["haplotypes.csv","allele_function.csv",
"diplotypes.csv"])` then `draft_from_cpic(gene="TPMT", use="non_commercial", dry_run=True)`:

1. *"cannot read the module's genome_build: module_spec.yaml []: … unreplaced template placeholder
   '<<REPLACE>>' … module.description, module.report_title, module.title … fix module_spec.yaml, or
   pass genome_build= explicitly."* `draft_from_cpic` has no `genome_build` argument, and neither
   does upstream's `draft_gene`: the remedy is the enricher CLI's, relayed raw because
   `EnrichmentError` was not in the tuple `_guard` translates.
2. After filling the three fields: *"existing haplotypes.csv does not validate, so a draft cannot be
   keyed against it: haplotypes.csv line 2 []: … '<<REPLACE>>' in HaplotypeRow row: allele,
   haplotype_name, rsid."* The compiler's `draft.merge_rows` refuses a file that does not validate,
   and the scaffold's stub is a placeholder in every required cell — so the tables scaffolded *for*
   the drafter are what block it. A header-only file drafts cleanly, and upstream's `stub_template`
   takes `rows=0`; our `scaffold_module` refused anything under 1.

Reproduced offline in a scratch directory against the built CPIC snapshot, both errors in order.
The promise it broke is `create-module`'s stage table, 1 scaffold → 2 draft, with nothing in between.
Upstream's own reference README recipe fails identically; the tester filed that as format-tree
`S103` (read `genome_build` leniently, or say to fill the titles and scaffold without `--kind`).

**Upstream half released 2026-09-21 — enricher/compiler 0.7.1 carry `S103` (their RM250):** a
draft reads past the scaffold's stubs in the fields it never uses, so only a placeholder in
`genome_build` itself refuses now, and the compiler names a stub row by its line. Adopted in 0.37.0:
the remedy text and its test moved to that one case.

**Fixed 2026-09-20.** `rows=0` on `scaffold_module`; `EnrichmentError` and `DraftError` translated
by `_guard`, each with the repair this surface can make appended after upstream's verbatim text and
keyed on `<<REPLACE>>`; the order written into `module-start` (stage 1 owns it), the two messages
into `module-draft`'s symptoms and `SYMPTOMS.md`. Not run: the tester's `probe/` directories and the
live CPIC path — the reproduction and the tests use the snapshot, `dry_run` and `offline`. **Not
re-probed**: the run ended with the tester's stdio server still on 0.35.0, and a `/mcp` reconnect is
not something that session could do for itself, so the re-probe needs the user or a fresh session.

## F101 — the two PGx cross-checks had no tool, so a PGx module could not read its own function calls back

Found 2026-09-20 by the dogfooding seat on the second module of the ClawBio PGx run, plugin 0.35.0.
`skills/module-check/GUIDE.md` listed `just-dna-enricher pgx` and `just-dna-enricher clinpgx check`
as bare CLI lines beside four tools, and `CLI.md`'s wrapped-or-not table carried them with an empty
tool column. Eleven of the run's thirteen modules are `haplotypes` + `allele_function` +
`diplotypes`, so none had an in-surface way to compare `function_status` against PharmVar or CPIC,
and a `pharm_variants.csv` module had no check against ClinPGx. The tester ran the CLI instead —
*"sources recorded: 2 … routes: cpic=snapshot, pharmvar=snapshot"* — which is the ad-hoc route the
product exists to remove, and the "surface teaches a step it cannot run" shape §5 names. The parity
rule that wrapped `check_acmg`, `check_repeat_bands` and `check_literature_coverage` at 0.35.0 had
left these two, with no written reason.

**Fixed 2026-09-20, 0.36.0.** `check_pgx` and `check_clinpgx` in the `pgx` toolbox group beside the
drafters they pair, carrying upstream's `PgxResult` / `ClinPgxResult` field-for-field: `compared` as
the denominator, `routes` for who answered, the licence skip and the offline skip as two lists, and
`not_checked` verbatim as the third value. Neither exposes `mode`, on the tester's point and the
guide's own ROADWORKS: upstream stores it and never reads it. Both let upstream attest and read
`verification.json` back for `attested`. Measured on a scratch copy of the tester's CYP2C19 module
against the built snapshots: 5 compared, PharmVar answered, CPIC reported `tautology`. Tested with a
disagreeing snapshot client injected under the real comparison, and hermetic offline runs.

**Left open, named rather than forgotten**: `clinpgx check-labels` (a module's drug claims against
five regulators' labels) is the third PGx check and is still CLI-only; `CLI.md` says so on its own
row. Not run: the tester's module directories and the live PharmVar path. **Not re-probed**: same as
`F100` — the tester's server stayed on 0.35.0 for the whole run, so a `/mcp` reconnect by the user or
a fresh session is what the re-probe needs.

## F102 — eleven dry runs in one batch: one verdict, four `503 enrichment_busy`, six `429 rate_limited`, and nothing said which budget or what to do

Found 2026-09-20 by the dogfooding seat, thirteen modules into the ClawBio PGx run, plugin 0.35.0.
`registry_check` fired once per module against the polygon; the tool surfaced each refusal raw —
*"the polygon could not complete the dry run: HTTP 429: rate_limited"* — with no bucket named, no
`Retry-After`, and no `next_step`. Read from the registry's own tree: `/check` sits on the `enrich`
bucket (operator default five an hour, refilling one per twelve minutes) plus a concurrency gate that
answers `503 enrichment_busy`; `/validate` is on its own `validate` bucket (sixty an hour), `/publish`
on `publish` (ten). So the taught rehearsal — a dry run before every publish — caps an author at five
modules an hour, and the tester switched to `registry_validate` + `registry_publish` for the remaining
eleven; only two went through the full dry run. The registry-tree half (name the bucket in `detail`,
derive `Retry-After` from the bucket's refill) is the tester's `S23`.

**Fixed 2026-09-20 (unreleased on 0.36.0).** `targets.throttle_note` is the suffix beside
`instance_note` on the three write arms: a 429 names the bucket (`enrich`, `validate`, `publish`) and
says it is the instance's budget rather than the module, and on the dry run's bucket points at
`registry_validate` as the pre-flight for a batch; a `503 enrichment_busy` says the instance runs one
dry run at a time and to re-run sequentially. No retry inside the tool: a five-an-hour bucket cannot
be waited out in a call, and a retry on the busy gate would be a policy invented here.
`registry_check`'s docstring and `module-publish` state the rule — rationed by design, never batched,
validate for a batch — and deliberately not the numbers, which are the operator's settings. Not run
against the live polygon from this seat; the refusal shapes come from the registry's source.

## F103 — `resolved: 5, sources: ["authored"], vrs_minted: 0` read as a clean run on every CPIC-drafted module

Found 2026-09-20 by the dogfooding seat on `cyp2c19`, and the tester corrected their own reading the
same day. Every CPIC-drafted `haplotypes.csv` row carries `rsid` + `chrom` + `start`, and the
enricher's last resolver branch — *"already complete, or has a position — nothing to resolve"* —
restates the authored coordinate into `resolution.csv` under `source=authored` with empty `ref`/`alts`
and no VRS id. `compile_module` then warns *"VRS allele identity covers 0/5 allele(s)"* on all
thirteen modules. **What is true and what is not**: the coordinate-agreement check *does* run —
`verification.json` carries `rsid_coordinate_agreement` with five subjects on CYP2C19, and on CYP2D6
it found five CPIC positions off Ensembl's — so the skills' sentence *"the resolution table is the
independent second value the cross-check needs"* was right about the check and wrong about the
sidecar, which holds no second value for this shape. Upstream half is the tester's `S104`.

**Upstream half released 2026-09-21 — enricher 0.7.1 carries `S104` (their RM251):** a row authoring
both an rsID and a coordinate takes the forward branch when the reference knows its rsID, so a fresh
`enrich` records the loci and mints an id, and a pair that disagrees with Ensembl warns in
`best_effort` and refuses in `strict`. A sidecar written before the fix keeps its `authored` rows under
merge-not-clobber, so the warning below now names `refresh_sidecar` as the repair instead of calling
the shape expected; the thirteen polygon rehearsals from 2026-09-20 are exactly that case. Adopted in
0.37.0.

**Fixed 2026-09-20 (unreleased on 0.36.0).** `enrich_module` now appends a warning counting the rows
that came back `resolved` under `source=authored` with an rsID and no VRS id, naming the shape, the
compile warning it will produce and `S104`. The sentence in `module-start` and `module-curate` is
narrowed to what the sidecar actually carries per shape; `module-draft`'s CPIC section says the VRS
warning is expected on every drafted module and why; `SYMPTOMS.md`'s VRS-coverage entry gains the
fourth cause. Nothing here alters the sidecar — the second value is upstream's to record. The tool
path is tested with a faked enrichment result; the predicate was measured over a real sidecar, the
scratch copy of the tester's CYP2C19 `resolution.csv`, where it counts 5 of 5 rows.

## F71 — `record_override` logged every authored cell as "outranks", claiming disputes that never happened

**Found:** 2026-08-31, reading six benchmark runs' `logs/authoring.log` · **Severity:** medium ·
**Status:** fixed here. Not upstream's — their field is scoped correctly and we were misusing it.

`record_override` has two jobs, stated in its own docstring: *"outranks a source, **or** that you
edited"*. `server.INSTRUCTIONS` rule 2 tells every agent to call it for **every** hand edit. Both
outputs said only the first thing:

```
override rs117385980 weight='-0.2 on C/T…' outranks authored judgement, no source consulted
```

**Six of seven records across two runs were judged cells** — `weight`, `conclusion`, `genotype`,
`state`, `stat_significance`, `direction` — cells no source supplies. One record was a real
disagreement (`effect_size='3.58' outranks pmid:28399814 ('3.53')`). The agents were compliant; the
surface mislabelled them.

**Both artifacts publish.** `logs/**.log` is swept into every compile with no opt-out, and
`provenance.json` is in `RECOGNIZED_SPEC_FILES`. So a module reaches the catalog asserting its author
overruled sources they never consulted — and it corrodes the signal `overrides.py` exists to protect:
if most records say *outranks* but mean *authored*, the real disputes stop standing out.

**Upstream is not at fault and there is no `S` to file.** `ProvenanceItem.outranks` is documented as
*"per-column justification for this row deliberately disagreeing with a source"*, and *"a key's
presence is what a tool may read"*. That is exact. We were writing a key for records that are not
disagreements. `rationale` — *"why this annotation was made"* — is the right shelf and every record
already filled it.

**The fix, and it needed no schema change:** `source_value is None` already separated the two cases.
The log now writes `authored … (judged; no value from X to disagree with)` where there is no source
value, and `to_items` leaves `outranks` empty for those records while still writing the reason to
`rationale`. Verified by reverting the fix and watching
`test_a_judged_cell_claims_no_dispute_it_did_not_have` fail.

**One agent diagnosed this unprompted**, which is the part worth keeping: *"the log renders my entries
as 'outranks [the sources]' when I passed no `source_value` and was recording authorship of a judged
cell, not overriding a source. That wording publishes verbatim."* A run asked for blunt feedback about
the surface produced a defect report about the surface.

## F77 — the version handshake certifies a registry pair that then refuses our own rows, and our workspace note said the opposite

**Found:** 2026-08-31, in a single-run SIRT6 benchmark on plugin 0.25.0 · **Severity:** high ·
**Status: CLOSED 2026-09-12** — both instances now serve format 0.7.0 and the column is accepted.
Filed as registry-tree `S18`; symptom entry shipped; `CLAUDE.md` §11 corrected at the time.

> **Closed on a measurement rather than on the handshake**, because the handshake is what made this
> finding possible: `assert_compatible()` passed throughout the outage. The proof is the call that
> failed, re-run — a `studies.csv` carrying `curator` put through `registry_validate` against the
> live polygon on 2026-09-12 returns `valid: true` with **zero findings**, where it returned
> `studies.csv line 2 [curator]: Extra inputs are not permitted`. `registry_health(target="test")`
> reports `server_format 0.7.0 / client_format 0.7.0 / contract_compatible true` beside it.
>
> **What generalises is the closing procedure, not the fix.** A contract finding is closed by
> re-running the call that produced it, never by reading a version line: the whole content of this
> entry is that the two disagree. Plugin 0.35.0 moved the floor to `>=0.7.0,<0.8` for the same
> reason in the opposite direction — the instances moved first, so a 0.6.6 client is now the
> refused end.

A module green through every local gate — strict validate, strict enrich, strict compile, verified
digests, closed with eleven check records — is refused by both live registries:

```
valid: false — studies.csv line 2 [curator]: Extra inputs are not permitted
```

`StudyRow.curator` shipped in format **0.6.5**. Both instances validate at **0.6.1**
(`/api/v1/version`, prod and polygon, measured) and `StudyRow` is `extra="forbid"`. Removing that one
column returns `verdict: true, blocking: []`.

**The part that is ours is the claim we had written down.** `CLAUDE.md` §11 said *"every 0.6.x
interoperates"*, measured on `assert_compatible()`, which is scoped to major.minor below 1.0 and
therefore **cannot fail** for the class of change that actually breaks a publish — a field added in a
patch release. That is the "could this check have failed?" defect, in our own workspace facts, and it
stood for ten days.

**The obvious repair is the wrong one and the run got that right.** Dropping `curator` makes the
publish go green and silently deletes the per-row record of *who located a quote* — the attribution
that field exists for, and which `server.INSTRUCTIONS` rule 5 pushes an author toward filling. The run
kept the column, published nothing, and surfaced it as a decision. Conforming a module to a registry
that lags the format is the stale-source move §2 forbids.

**Surface it, and why one candidate is wrong.** Pre-stripping fields the target instance does not know
would require us to model their validation, would delete authored provenance, and would make a
module's bytes depend on which registry it was aimed at. `S18` asks instead that the refusal name the
version gap. **A product guard is worth building** — compare the fields a module uses against the
target's reported format version and warn by name — and is deferred rather than dismissed: it needs a
version-to-model mapping and a probe, which is more than a patch.

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

## F80 — a benchmark's isolation was breached by our own memory index, and by "read" not covering "list"

**Found:** 2026-08-31, running three scored benchmark runs on 0.27.0 · **Severity:** high ·
**Status:** memory entry retired the same day; runbook in `docs/BENCHMARKING.md`.

Every benchmark prompt banned reading `data/interim/` and `assets/benchmarks/`, where the
adjudicated reference and the sibling runs live. Two things got past that, and neither is the
agents' fault.

**The project memory told each run to open the answer key.** A memory entry read *"read
`data/interim/repro-bench-2/HANDOFF.md` first"* — the round's own handoff, naming the reference, the
scores and the findings. One run flagged the contradiction and refused; nothing in the setup would
have detected compliance. **The prompt is not the isolation boundary**: `CLAUDE.md`, the memory
index and the skills all reach a subagent unasked.

**"Read" did not cover "list".** A run's first bundled command included `ls data/interim/` and it
saw five directory names. Names only, no contents, it never descended, and it disclosed this before
being asked — but the clause has to say *list* too.

**Neither voided a run, and that is why they are worth writing down.** Both were caught by an agent
volunteering against its own interest, which is not a control.

**Surface it, and the candidates that are wrong.** Rewriting prompts is necessary and not
sufficient, since the leak was in injected context. Removing the memory entirely loses a real
pointer. What is built instead is a transcript audit that does not depend on anyone's honesty —
parse `tool_use` inputs in the subagent JSONL for forbidden paths, check which tool first surfaced
the answer, and ask for the reasoning chain separately, since grep cannot tell a derivation from a
reconstruction. **Counting name mentions does not work**: `registry_download` and `registry_search`
appeared 18 times in one transcript with zero invocations, the hits being tool-schema text.

## F47 — a skill can teach a step the running tier cannot run

**Found:** 2026-08-20, trying to refresh `literature.csv` from a default-tier session ·
**Resolved:** 2026-08-27 in 0.21.0, by removing the tier

`find-evidence`'s loop ended with `enrich_literature_pass(spec_dir="spec")` as the verify step, with
`paper_citations` in the same code block. Both were extended, so on a default install neither
existed, and nothing in that skill said so — the only mention of a tier anywhere near the topic was
one parenthesis in `literature.md`. The guard written for exactly this,
`test_the_taught_workflow_runs_in_the_default_tier`, read `server.INSTRUCTIONS` and not the skills,
which are the other half of the taught workflow and much the larger half.

**What it cost.** `literature.csv` needed re-deriving (`quotes_authored: 0` beside authored quotes —
`F44` / upstream `S56`). The two tools for that were both extended, so on a default server there was
no route at all: the module was published with the sidecar as found, and the log says so.

**How it was closed, and why not the way this entry proposed.** The candidate fix here was a test
extracting `name(` call sites from every `skills/**/*.md` block and requiring an `EXTENDED` marker on
any that was not in the default roster — and the entry explicitly ruled out moving the passes into
essentials, on the grounds that *"the tier line is cost, and a pass that rewrites every row of a
corpus is squarely extended. The defect is the silence, not the tier."*

The cost argument was right and the conclusion was wrong, which took three more instances to see.
This was the fourth time the same shape shipped — `enrich_module` taught while extended-only (0.4.0),
`compare_to_published`'s docstring naming `registry_download` from a tier that lacked it,
`refresh_sidecar` invisible to both 2026-08-21 unattended runs — and each of the first three was
fixed by moving one tool across the line rather than by asking what the line bought. **What it bought
was nothing a caller could not be told in prose**: hiding a tool never made its pass cheaper, and the
sessions that could not see it were exactly the ones doing the work that needed it. 0.21.0 removed
`JMC_MODE`, `--mode` and the `extended` tier; the cost moved into each expensive tool's own
description, where a caller can weigh it, and
`tests/test_surface_and_auth.py::test_the_corpus_sized_tools_say_what_they_cost` fails if one stops
saying it. The skills-scanning test was not written: with one surface, the check that matters is
"does this name resolve", and `test_docstrings_only_name_tools_that_exist` asserts that over every
tool description.

## F52 — the review queue accused an author of an edit nobody made

**Found:** 2026-08-20, dogfooding `review_queue` on `assets/fto_bmi` · **Resolved:** same session

`record_override` was recorded against `rs1421085`'s `clin_sig`, and `review_queue` came back
`still_bound: false` — which reads as *the authored cell was edited again after the reason was
written*. Nobody had edited anything. `fto_bmi/variants.csv` **carries no `clin_sig` column at all**,
so there was no cell to compare, and the boolean had collapsed "no value" into "a different value".

That is the failure `CLAUDE.md` §2 names in its own words — *never collapse "unknown" into a boolean;
`None` is never `False`* — committed by the very tool written to satisfy §2's other half. It shipped in
0.11.0 and was found an hour later by using the surface rather than by testing it, which is exactly the
split §7 describes: the tests asserted the two states the author of the tool had in mind, and a real
module had a third.

`QueuedOverride.still_bound` is now `bool | None`: `true` the reason still describes the value, `false`
the value moved under it, **`null` there is no such cell — the row is gone or the column does not
exist**. `ReviewQueue` counts them apart as `unbound` and `subject_absent`, and the ranking puts a
broken binding first, an unanswerable one second, a live one last.

Pointer: `src/just_module_creator/overrides.py`, `QueuedOverride` / `review_queue`;
`tests/test_overrides.py::test_a_record_for_a_column_the_table_does_not_carry_is_unknown_not_unbound`
reproduces the `fto_bmi` shape.

---

## F3 — a strict compile failed with no indication of which step was missing

**Found:** 2026-08-11, first end-to-end run · **Resolved:** 2026-08-11

Compiling a complete, valid spec with `strict=True` returned `success: false`.
The spec was fine; it had simply never been enriched, so no `resolution.csv`
existed and strict refuses what it cannot reproduce.

The finding was not the refusal — that is correct — but that our result gave no
signal about *where in the workflow* the caller was. Fixed by surfacing upstream's
`errors` verbatim in `CompileReport` (it names the unresolved variants and says
what to inject) rather than reducing the outcome to a boolean, and by stating the
enrich→compile ordering in `compile_module`'s docstring and in the skill.

Pointer: `src/just_module_creator/tools/authoring.py`, `compile_module`;
`tests/test_pipeline.py::test_strict_compile_refuses_unresolved_rows` pins that
the refusal arrives as structured errors rather than an exception.

## F4 — the test suite could not import its own helpers

**Found:** 2026-08-11 · **Resolved:** 2026-08-11

`from tests.conftest import offline_settings` resolved to a `tests` package
shipped by a transitive dependency inside `site-packages`, not to this repo's
`tests/`. Collection failed with a confusing `ImportError` naming a path in
`.venv`.

Fixed by importing as `from conftest import ...`, which resolves through the
directory pytest puts on `sys.path`. Recorded in `CLAUDE.md` §6 so the next agent
does not "fix" it back.

Pointer: `tests/test_modes_and_auth.py` import block.

## F12 — the first step of the publishing workflow was not in the tool surface

**Found:** 2026-08-11, asked to create an account and a namespace on the live
registry · **Resolved:** 2026-08-11, 0.3.0

Every registry tool needed a token, and the only route to one the surface named was
`registry-client register` — a shell command in another package, pointed at by
`authenticate`'s docstring. So the plugin gated every registry action behind a
credential nothing in it could mint, and onboarding quietly cost a second toolchain
despite install instructions that promise one command.

Not an upstream gap: `RegistryClient.register(install_id, account)` is public in the
**published** 0.9.1, `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email), and
`generate_install_id()` grinds the proof-of-work locally in 0.3–1.2 s. A public
onboarding API we had simply never wrapped.

Fixed by `registry_register(account, install_id=None, difficulty=None)`. Three
decisions worth keeping:

- **It lives in `auth.py`, always on.** It writes to the registry but cannot be
  token-gated — it is what produces the token — and extended-only would have
  reproduced the same dead end behind a mode flag. `CLAUDE.md` §5 now states the
  exception and its test: a registry write is gated *unless the token is its output*.
- **The token goes into the caller's own session slot**, so registering leaves the
  session usable and no secret has to be copied back through the transcript.
  `authenticate` is now only for a token you already hold.
- **Both secrets come back, and the install-id carries the warning.** It is the
  account's only recovery path; re-registering it reissues a key for the same
  account, while registering again without it creates a *different* account and
  strands the first. `JMC_INSTALL_ID` was added so a later session can reuse it,
  which is a value we read and never write — persisting it ourselves would widen the
  write surface. The `account_taken` error says outright that retrying will not help.

Pointer: `src/just_module_creator/auth.py` — `registry_register`,
`resolve_install_id`, `_registration_failure`;
`models.RegistrationResult`; `settings.install_id`;
`tests/test_modes_and_auth.py::test_an_illegal_account_name_is_refused_before_any_socket`
and `::test_install_id_precedence_and_origin`.

**Not verified end to end from this side, deliberately.** The wrap, the local
refusals and the offline ceiling are covered by the suite, and the live service was
exercised read-only plus one real failure path (a deliberately invalid install-id
returning `422 invalid_install_id`, mapped to actionable text). Actually minting an
account and claiming a namespace belong to the dogfooding side — a builder who also
runs the irreversible probe has graded their own work. **A shipped fix is not a
passed probe.**

## F13 — an irreversible claim had no pre-flight, though upstream shipped one

**Found:** 2026-08-11, same session · **Resolved:** 2026-08-11, 0.3.0

`registry_claim_namespace`'s docstring warned that a namespace "is claimed once and
then owns every module published under it, so this is not a step to run
speculatively" — and then offered no way to be non-speculative. The only way to
learn whether a name was free was to try to take it.
`RegistryClient.namespace_available` is public, read-only and needs no token, and
was unwrapped.

Fixed by `registry_namespace_available` in `research.py`, essentials — beside
`registry_search`, which was already the home for token-free registry reads, and in
the default surface because a pre-flight for an irreversible step belongs there.

**`valid` and `available` are returned separately, and the live registry proves why:**
it answers `test_modules` with `valid: false, available: true`. Collapsing them into
one boolean would have told an author that an illegal name was claimable.

The naming half was the sharper finding. Accounts are validated with the *namespace*
rule (`is_valid_namespace`, `^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` and
`test_modules` were rejected before anything else could happen — and our docstring
said only "Lowercase, hyphen-separated", which reads as a style preference rather
than a hard reject. Module names are the opposite rule, `^[a-z][a-z0-9_]*$`, which
is why a spec holds `my-ns/lactose_tolerance`. That asymmetry is now stated in
`registry_claim_namespace`, `registry_register`, `registry_namespace_available`, the
server instructions, the skill and the README, and an illegal account name is
refused locally with the pattern named, before a round trip is spent.

Pointer: `src/just_module_creator/tools/research.py` —
`registry_namespace_available`; `models.NamespaceAvailability`;
`src/just_module_creator/tools/registry.py` — `registry_claim_namespace`'s docstring.

## F9 — `lookup_citation` could not detect a fabricated PMID, and our docs said it could

**Found:** 2026-08-11, designing the search tool · **Resolved:** 2026-08-11 ·
**Upstream:** `S12`, released in compiler/enricher **0.5.4**

`CitationHint` carried `pmid_exists`, `doi`, `pmcid`, `open_access` — and no title, journal
or year. PMIDs are densely allocated across roughly 1–40,000,000, so a recalled 8-digit
number is almost always a real record for a **different** paper, and `lookup_citation`
answered `pmid_exists: true` for it. Both our skill and the tool docstring said "verify each
PMID with `lookup_citation`", a rule the surface could not enforce: fabrication is a failure
of *identity*, and that call only answered existence.

**Two things fixed it, and the order matters.** First, ours: this is the finding that put
`literature_search` in the **essentials** tier rather than extended, because discovery is the
missing half of an anti-fabrication promise the default surface had already made. Then
upstream's: 0.5.4 added `CitationHint.title` / `journal` / `year` / `first_author`, which
arrive in the same `esummary` response that answers existence and therefore cost no extra
request. Both tools now report a title, and the docs tell a caller to read it and compare.

The working rule survived the fix unchanged, for a reason that was never about titles: a
title checks an id you already hold, and only a search finds the id you should be citing.

Pointer: `models.CitationLookup`, `tools/research.py::lookup_citation`;
`tests/test_discovery.py::test_upstream_supplies_the_bibliographic_fields_identity_needs`
asserts the fields exist on the *installed* package, so the docstring's promise fails with
them if they ever go away, and
`test_an_offline_citation_lookup_withholds_the_title_rather_than_denying_it` pins that a
missing title reads as unchecked rather than as "no such paper".

## F20 — `list_tables` advertised `sources.csv`; `describe_table` and `get_template` rejected it

**Found:** 2026-08-11, authoring `assets/fto_bmi` · **Resolved:** 2026-08-11 ·
**Upstream:** `S21`, released in **0.5.4**

The done-checklist required `sources.csv`, and every route to its columns refused:
`list_tables()` named it under `sidecars`, while `describe_table("sources.csv")` and
`get_template("sources.csv")` both answered *"Unknown table kind"* and helpfully listed
eleven alternatives, none of which was what was asked for — which reads as "you invented
that filename", not "this kind is real but undescribed".

**Two separate defects, and both had to be fixed.** Upstream's: `authoring_reference()`
omitted `SourceRow` entirely, and the root cause was a level below the report —
`SourceRow.layer` and `.declared_use` ran closed-vocabulary validators with no `vocabulary=`
marker, and the guard that discovers enforcement by behaviour iterates `_ALL_MODELS`, which
the model was not in. One omission hid the other. 0.5.4 fixes both and puts `sources.csv`
in `draft.DRAFTABLE` with `(source, layer)` as its natural key.

Ours: the sidecar list in `tools/authoring.py` was a hardcoded literal while the authorable
set came from `draft.DRAFTABLE`, so one tool named a file the next two denied existed. With
upstream's half released, that literal made it *worse* — `sources.csv` appeared as a table
kind **and** as a "do not hand-author" sidecar, telling an author two opposite things.

Fixed by giving it a `_SUBJECTS` entry and removing it from the sidecar list, so all four
schema tools now answer for it. `authoring_reference`'s sidecar sentence says it is the one
fact sidecar a human writes rather than carrying an "except" clause.

What was at stake was not cosmetic: `share_alike` / `commercial_use` / `redistribution` are
three independent axes where an empty cell means **unknown** and never *permitted*, and
`sources.csv` is the only input the compile licence gate reads. An author reconstructing that
from the filename gets the licence declaration wrong in the permissive direction. The
candidate fix we rejected — restating the columns in the skill — would have been the exact
drift the "never hardcode a schema fact" rule forbids.

Pointer: `tools/authoring.py::_SUBJECTS` and `list_tables`;
`tests/test_authoring.py::test_sources_csv_is_a_table_kind_not_a_sidecar`. The related
strengthening is worth noting: `test_list_tables_covers_every_draftable_kind` asserted
`all(t.subject and t.keyed_on)`, which the placeholder fallback satisfied — so it passed
while telling an author nothing, and did not notice `sources.csv` arriving. It now names the
placeholders, verified by removing the entry and watching it fail.

## F21 — the skill's `sources.csv` rule was backwards: compliance warned, omission was silent

**Found:** 2026-08-11, compiling `assets/fto_bmi` · **Resolved:** 2026-08-11 ·
**Upstream:** `S23`, released in **0.5.4**

The skill said a missing `sources.csv` row "is a warning, not an error, so it is easy to ship
without noticing". Both halves were wrong for the literature layer, found by doing what it
said — declaring `pubmed` and `europepmc` earned *"sources.csv declares 2 source(s) no table
in this module uses"*, and deleting the file entirely was completely silent.

Upstream's cause: the orphan and undeclared checks both compared `declared` against a
`used_sources` set gathered from the `source` **columns** of the generated tables, and
`studies.csv` has no `source` column by design — the same design that already exempts the
annotation layer. So `pubmed` could never enter `used_sources` and both branches followed
mechanically.

**The harm was the incentive, not the warning.** An author who reads a warning makes it go
away, and the only way to silence this one was to delete a true row, after which the module
carried no record of the literature terms and the compile was clean. Our skill sent them to
write the row; the compiler told them it was superfluous; the tidy resolution was the wrong
one.

0.5.4 puts `literature` into the same exemption as `annotation` whenever the module's
literature evidence is `studies.csv`, and adds the converse warning: a source a fact table
*does* cite with no `sources.csv` row now reports that its terms are unrecorded. Verified on
the real asset's three rows — compliance is silent, omission warns, exactly inverted from
before:

```
0.5.4, studies.csv has rows:  []
same rows, clinvar row removed:
  ["sources.csv has no row for 1 source(s) the module's fact tables cite:
    ['clinvar'] — their terms are unrecorded."]
```

Ours was a doc fix, and the two candidates we rejected are worth keeping on record: telling
authors to omit literature rows to keep compiles clean would have optimised the warning count
and lost the provenance, and suppressing the warning in `to_findings` would have hardcoded a
judgement about which layers are joinable — a schema fact we do not own.

Pointer: `skills/create-module/SKILL.md` §"sources.csv and licensing".

## F23 — the `gene` column was unverified, and it is the column that exposes a fabricated source

**Found:** 2026-08-11, triaging an LLM-written source · **Resolved:** 2026-08-11 ·
**Upstream:** `S24`, released in **0.5.4**

`variants.csv:gene` was checked against nothing, so a deliberately wrong pairing linted
clean: `rs2252481` (chromosome 6) beside gene `NEGR1` (chromosome 1) gave zero errors and
zero warnings. `check_identifiers` did not cover it — it asked HGNC whether the *symbol* was
current and answered `state: "approved"` for `FTO` without ever asking whether `rs1421085`
is in FTO. The two questions read alike in a result payload, which is what made this easy to
believe already handled.

**Why it mattered more than an unchecked free-text column usually would.** This was the
single check that separated the honest half of a machine-written source from the fabricated
half: four of seven rows named a real gene with an rsID on another chromosome, and every
other check passed on each half separately — the rsID resolved, the symbol was approved, only
the *pairing* was false.

0.5.4 adds `IdentifierReport.gene_loci` (a `GeneLocusConflict` per disagreeing row, naming
both chromosomes) and `gene_loci_not_checked`, which exists for the same reason
`clin_sig_not_checked` does: an empty conflict list otherwise says two opposite things,
"compared everything, nothing disagreed" and "never compared". Upstream kept the granularity
at chromosome level on the argument our note made — a variant legitimately names a distal
gene (`rs1421085` sits in an FTO intron and acts on IRX3/IRX5), so an inside-the-gene-body
check would fire on correct rows until somebody disabled it.

**Adopted rather than merely available**, which is the part that closes this: our
`IdentifierReport` carries `gene_locus_conflicts` and `gene_locus_check_skipped`, and
`check_identifiers`' docstring says to read them even when `stale` is empty. Upstream's own
sentence is passed through verbatim rather than reformatted — it already names both
chromosomes and what to do — because a second wording in front of one finding is how two
answers to one question start. **The manual step is out of the skill**: triage step 2 now
names the tool instead of sending an author to a service outside the toolchain, which was the
consequence this finding was filed for.

We were right not to build the lookup here: `identifiers.py` already resolved symbols against
HGNC and `resolution.csv` already carried the chromosome, so upstream held both halves and
the value was entirely in the comparison.

Pointer: `models.IdentifierReport`, `tools/research.py::check_identifiers`;
`tests/test_discovery.py::test_the_gene_locus_conflict_check_reaches_our_model_three_valued`.

## F24 — the suite's hermeticity was a convention with no guard, and a bare `Settings()` read the real `.env`

**Found:** 2026-08-11, while adding tests for the contact-email chain · **Resolved:** 2026-08-12 ·
**No upstream half** — ours entirely

`CLAUDE.md` §6 claimed "the suite is hermetic: every fixture forces `offline=True` and
`_env_file=None`, so no test can reach the network or read a developer's `.env`." The first
half was a mechanism; the second was discipline, and it held only for as long as every
construction remembered the kwarg.

**Re-confirmed live on 2026-08-12 before fixing, and it had got worse.** `.env` by then held a
real polygon token, so from inside the suite under the real `conftest.py`:

```
JMC_TEST_API_KEY in os.environ           : False        # .env never reaches the process env
Settings(_env_file=None).test_api_key    : None         # hermetic, as documented
Settings().test_api_key                  : 'mk_live_…'  # the developer's REAL polygon token
Settings().offline                       : False        # ← worse than the finding said
```

That last line is the part the original note missed: a forgotten kwarg lost **both**
hermeticity properties, so a test could reach the network *while holding a live credential*.
Nothing failed when the kwarg was forgotten — the test simply started reading whatever the
developer happened to have configured, which is the worst failure shape available: it passes
locally, passes in CI where `.env` is absent, and quietly means something different on each
machine.

**Fixed with the mechanism the note proposed**, as an autouse fixture in `tests/conftest.py`
(`_hermetic_configuration`), in two halves because the file is not the only route:

1. `env_file` is pointed at a path that cannot exist. **Not** removed from `model_config` —
   the rejected candidate — because the product genuinely needs it: that is how one `.env`
   serves both this surface and the enricher, and breaking the product to protect the suite is
   the wrong trade.
2. The ecosystem's variables are cleared from `os.environ`, so an *exported* shell variable
   cannot do what the file no longer can.

`delenv` rather than `setenv(VAR, "")` there, which does not contradict §6's rule: that rule is
about `load_dotenv(override=False)` skipping a key that is merely present, and nothing in the
suite calls it. With the dotenv source neutralized, pydantic reads `os.environ` directly, where
absent genuinely means unset. A test that means "no credential" to a reader doing
`x or os.environ.get(...)` still uses `setenv(VAR, "")`, and running after the autouse fixture
it wins.

**The clear-list is derived, not written, and that mattered immediately.** Every field on
`Settings` is readable as `JMC_<FIELD>`, so a hand-written list drifts the first time a setting
is added — and it did, within the same change: the first draft covered the credentials and
missed `JMC_API_KEY_HEADER`, `JMC_TRANSPORT`, `JMC_PORT`, `JMC_HOST`, `JMC_LOG_LEVEL`,
`JMC_REGISTRY_TIMEOUT` and `JMC_TEST_API_KEY_HEADER`. An exported `JMC_API_KEY_HEADER` changes
what `test_the_two_instances_read_different_http_headers` asserts just as effectively as a
token does and far less visibly. Deriving removes the failure mode rather than testing for it;
only the four upstream names — read by code we do not control, so no field of ours can name
them — stay hand-maintained.

Pointer: `tests/conftest.py::_hermetic_configuration`;
`tests/test_modes_and_auth.py::test_a_bare_settings_reads_no_developer_configuration` fails on
the old behaviour by exposing the real token (verified by flipping the fixture to
`autouse=False` and watching it fail), and
`test_the_clear_list_covers_every_variable_settings_reads` pins that the list stays derived.
A companion test records whether this checkout even has a `.env`, so a green suite cannot be
mistaken for proof the leak is closed when there was nothing to leak.

## F33 — our registry floor pinned us below the fix upstream shipped, and `amend_readme` was unwrapped

**Found:** 2026-08-12, publishing `assets/longevity_2026` · **Resolved:** 2026-08-12 ·
**Upstream half:** `F27` / registry `S5`, released in **0.14.0**

The defect was upstream's — a spec-directory `README.md` never reached the module card — and it was
fixed in registry 0.14.0. What was ours: our floor said `>=0.13.0`, so `uv sync` gave us a client
without `amend_readme`, `longevity_2026@1.0.0` had an empty readme, and **our own pin was what kept
us off the fix**. Released upstream, state 2 for us — the exact case the three-states rule exists to
name.

All three pieces of the filed work list are done.

**1. The floor is `just-dna-registry>=0.14.0`**, verified the way the rule requires — by importing the
symbol from the installed package rather than reading a changelog:

```
installed just-dna-registry: 0.14.0
amend_readme present: True
```

**2. `amend_readme` is wrapped** as `registry_amend_readme`, and it earned a wrapper for the reason
the finding gave: the readme sits **outside `artifact.digest`**, so this is the one write against a
published version that spends nothing and can be redone. Everything else about a published version is
permanent.

Two refusals were worth building into it, and both are tested:

- **A path is not prose.** Upstream's `amend_readme(readme=…)` disambiguates a file path from markdown
  *by type*, and every MCP argument arrives as a string — so one collapsed parameter would let
  `readme="spec/README.md"` publish the path itself as the card's text, quietly, on a module whose
  whole problem was an unreadable card. Hence `spec_dir` and `readme_text` as separate arguments, with
  both-at-once refused.
- **An empty body is refused.** The field is last-publish-wins, so empty prose replaces what is there.
  A tool for fixing a blank card must not be able to make one.

The checks that need no credential run **before** `require_key`, matching `registry_publish`'s
order and its stated reason: sending an author to fetch a token for a call that could never have
succeeded is a dead end. The first draft had that backwards and the tests caught it — they were
written to assert refusals and instead got an unauthenticated result.

**Verified on the waiting caller rather than a fixture.** `test-sheep/longevity_2026@1.0.0` on the
polygon went from `readme` of length 0 to 6860 characters, and the artifact digest afterwards was
byte-identical to the one `published.json` recorded at publish time:

```
digest now     : sha256:809facbf…de2f
digest recorded: sha256:809facbf…de2f
unchanged by the readme amend: True
```

That check is the tool's central claim, so it is worth having actually run.

**3. `README.md` is taught.** The skill's directory layout listed `logo.png` as optional and mentioned
no readme at all, so an author following it shipped a blank card. It now names `README.md` as the file
that *becomes* the card, says what to write in it (what the module claims, which population the
evidence came from, what it does not cover), and records that `MODULE.md` is renamed on upload with a
warning while any other spelling is carried but never read.

**A record correction went upstream as registry `S8`.** Their `specfiles.py` comment and changelog
both attribute `MODULE.md` to "`just-module-creator`'s `write_module_md` tool". That tool has never
existed here — no match in the tree, and `git log --all -S` finds none in the history either. It lives
in `just-dna-pipelines`, in a file named `module_creator.py`, which is a good enough reason for the
mix-up. Their rename decision is unaffected and correct; the cost is a wrong address for anyone who
later wants the producer to emit `README.md` at the source.

## F36 — re-drafting a pre-0.6.3 ClinVar panel restores the lost rows and keeps the wrong ones, with nothing to tell them apart

**Severity:** medium · **Status: CLOSED 2026-08-19 — filed as format-tree `S45`, accepted, fixed
and released in enricher 0.6.4 the same day, installed, and adopted here in 0.10.2.** Verified by
driving a real stale-then-re-draft cycle through our own `draft_from_clinvar` and reading the
notice off the tool result, not off their changelog.

Enricher 0.6.3 fixed `multi_allelic_rsids` (upstream `S41`): the site key included `ref`, so an
ordinary ClinVar dup/del mirror pair — `A>AT` beside `ATT>A` at one position — landed in two groups
of one alt each, the rsID was never flagged as multi-allelic, both records reduced to the same
rsid-only identity, and `append_partial_rows` dropped the second as `already_present`. Upstream
measured 725 records lost over five genes, 187 of them dropping the *better*-reviewed half, and said
already-published modules "need a re-draft" while stating plainly that they had not measured that
end to end.

**We measured it, because our surface is where an author performs the remediation.** One gene,
`MLH1`, `min_review_stars=2`, against the local snapshot on installed 0.6.3, drafting three times:
once with the predicate monkeypatched back to 0.6.2 (a stand-in for a pre-fix module), once fresh
with the fix (the ground truth), and then re-drafting the first into its own directory.

| | rows | distinct identities |
|---|---:|---:|
| first draft, 0.6.2 predicate | 996 | — |
| fresh draft, 0.6.3 | 1,030 | 882 |
| re-draft of the first, 0.6.3 | 1,061 | 913 |

`added=65, already_present=965`. Against the ground truth: **0 identities missing** and **31
present that a fresh draft does not contain** — 1,061 − 1,030 = 31, and 913 − 882 = 31. The re-draft
is additive, so it adds the correct coordinate-keyed rows *beside* the collapsed rsid-only rows
rather than retracting them, and the module then states both the right answer and the wrong one for
the same locus. Those 31 are exactly the rows carrying `S41`'s downstream consequence: the surviving
rsID resolves onto both loci and renders the dropped record's coordinate under the survivor's
`clin_sig`, gene and condition.

**The reason it is worth an `F` rather than a changelog line: the stale rows are not findable.** The
obvious predicate — an rsid-only row whose rsID also appears on a coordinate row — finds **0 of 31**,
because `draft_gene_panel` writes no `rsid` onto a coordinate-identity row (327 such rows in both
drafts, none carrying one). No column separates a stale row from a legitimate rsid-only row, so an
author who reads "re-draft" as "re-run the drafter" gets a module worse-formed than either the one
they had or a fresh one, and nothing says so.

**Mitigated as advice, deliberately not as code.** The docstring now says to draft into a *fresh*
directory and reconcile, and says why re-running over the existing file looks like it worked. We do
not attempt detection: we would have to re-query the snapshot to know which rsIDs the current
predicate flags, which is `draft_gene_panel`'s own job and where the fix belongs. Our upstream
candidate is that `append_partial_rows` name those rows on the draft report — it already holds both
halves at merge time — and explicitly **not** that it delete them, since by re-draft time a human may
have curated the `genotype`, `state` and `conclusion` on a drafted row.

**The contrast that names the condition, measured the same day.** The equivalent probe on
`clinpgx_draft` for `S44`'s genotype-gate widening — with a stand-in gate deliberately *broader* than
0.6.2's, so 12,410 rows where the fix gives 18,895 — re-drafts to **18,895 rows, 0 stale, 0 missing**,
exactly the fresh draft. `S44` *skipped* rows; `S41` *wrote them under an identity that has since
moved*. Only the second leaves anything behind, which is why `draft_from_clinpgx` carries the opposite
advice in its docstring and why the two notes must not be collapsed into one rule about drafters.

**How it closed.** `clinvar_draft._superseded_rsid_rows` now names those rows after the append,
counted and aggregated through the house `examples` helper, reading the written file back through
`DraftReport.path`. Confirmed arriving through our tool on the same MLH1 cycle that produced the
numbers above — `added=65, already_present=965`, and the notice naming **31 rows** with five rsIDs and
"and 26 more".

**Our candidate was accepted in substance and corrected on location, and the correction is the part
worth keeping.** We proposed `append_partial_rows`, reasoning that it holds both halves at merge time.
It holds the *file* but not the *predicate*: it is the compiler's generic drafting helper, shared by
every provider, and teaching it about rsIDs would put a source's identity rule into the tier that must
not carry one. The rule belongs in `clinvar_draft`, where the source convention already lives. Worth
remembering the next time we name a layer in a suggestion — "it has the data" is not "it is the right
tier".

**Report-and-never-remove was upheld for our reason**: by re-draft time a drafted row is authored
material, a human may have curated its `genotype`, `state` and `conclusion`, and deleting curated work
to repair a drafting defect is a trade only the author can make. Our fresh-directory advice went into
their reference as the cleaner remediation, with the notice framed as the net for an author who
followed the shorter instruction.

**One thing upstream left open and it is ours to watch.** Neither side re-measured the downstream
label errors — both established only that the rows carrying them survive a re-draft. If a module
drafted after 0.6.4, with its superseded rows deleted, still shows mislabelled expansions, that is a
separate defect and upstream wants it as its own item.

**Still not guarded by a test here, deliberately.** Reproducing it requires monkeypatching an
upstream private predicate to manufacture the old behaviour — a fixture for someone else's
regression, which would fail the day they rename the function and would be testing their fix
rather than our wrapper. Upstream carries three tests for it, including the MLH1 measurement
asserted as a relationship. Ours is the pass-through, and the warning list is already covered.

---

## F48 — a reversed rule reached the docstring and not the message the agent reads while acting

**Found:** 2026-08-20, remediating a real module's quotes · **Resolved:** 2026-08-20, `fdbc5f9`

`CLAUDE.md` §2 reversed the machine-located-quote prohibition, and `211dac5` corrected
`fetch_fulltext`'s docstring to match: *"Retrieve a paper's text so you can read it — and you may
quote it."* The **finding emitted on every retrieval** was not corrected. `discovery._NO_PASSAGE_NOTE`
still read *"a machine-located quote asserts a reading that did not happen. Locate the passage
yourself."*

So the tool handed over the article, told the caller in its description that quoting was
legitimate, and told the same caller in the payload that it was not — the second one arriving
attached to the text itself, at the moment the decision is actually made. Found by being that
caller.

Two smaller sites carried the same inherited claim: `describe_table`'s gloss that
`attestation_bearing` cells *"assert that a **human** read something, so filling one from a fetched
document states something false"*, and `discovery.py`'s own module docstring, whose *never extract a
passage* rule is still correct behaviour and rested on the retired reason.

Fixed in `fdbc5f9`. The note now carries what survives — locate it yourself because relevance to a
row is a judgement about a row nothing here has read; never the article's title, with the
one-string-per-PMID signature named; and the pairing-check cost stated rather than used to refuse.
`discovery.py`'s prohibition keeps its behaviour and gets a reason that is ours: a tool-picked
sentence would be pasted unread, and that is the actual failure.

**The general lesson, and it is not fixed.** A policy reversal reaches docstrings because docstrings
are where a reviewer looks. It does not reach constants like `_NO_PASSAGE_NOTE`, `SourceLicenseNote.note`
or a `Field(description=...)`, which is where an agent reads it under time pressure. Nothing pins the
two against each other, and a grep for the retired sentence was what found this — cheap, and worth
running after any §2 change.

Pointer: `src/just_module_creator/discovery.py`, `_NO_PASSAGE_NOTE` and the module docstring;
`src/just_module_creator/tools/authoring.py`, `describe_table`.
