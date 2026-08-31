# The authoring scorer: the framework, and what the prep runs showed

The design this file used to hold was written **before** anything ran. Prep runs
then corrected it in four places. This is the version that describes what is built
— `src/just_module_creator/bench.py`, the corpus in `assets/benchmarks/`, and what
each of its three modes is worth.

**The framework is the deliverable here; the numbers are not yet results.** The
runs that produced them were preparation — they surfaced the prompt changes and
the upstream items, and the plugin changed between them — so they demonstrate that
the instrument measures something and no more. The scored round runs against a
stable build.

Lineage is ClawBio's genomic evaluation infrastructure, adapted from scoring
**pipeline filtering** to scoring **module authoring**. What we kept and what we
had to redraw:

| ClawBio pattern | What it became here |
|---|---|
| Tiered ground-truth JSON with positive/negative sets | `metadata.json` per fixture: tiers, decoys, thresholds, and a `provenance` block ClawBio has no equivalent for |
| `BenchmarkScorer` with precision / recall / F1 | `score_ground_truth` — recall, **two of them**, and `decoy_rate` in place of precision |
| Tier weighting (causal 3×, GWAS 2×, novel 1×) | Evidence-tier weighting, but assigned from what the evidence *is*, not from a template |
| `nightly_demo_sweep.py` aggregate scoring | `bench_score.py --fixture` over a fixture's runs |
| — | `score_agreement`: run-to-run reproducibility, which needs no ground truth and which ClawBio has no reason to want |
| — | `census`: what a run asserts versus withholds, reference-free |

---

## The measurement that is not in ClawBio, and why it exists

**A fixture is expensive and partly a judgement.** For a filtering pipeline, ground
truth is a gene list somebody already published. For authoring, "the right module"
is a curation — so a benchmark that can *only* score against an expert answer can
score only the traits an expert has already answered.

So there are three modes, in rank order:

| Mode | Question | Needs |
|---|---|---|
| `--fixture` | Did this run recover the adjudicated answer? | a reference |
| *(default)* | Did two runs of one prompt agree, and on what? | another run |
| `--census` | What does this run assert, and what does it withhold? | nothing |

The second and third exist because two of this corpus's three papers have no
adjudicated reference and may never have one.

## How the reference was made, and why that is the method

`assets/benchmarks/sirt6/reference/` is **not a copy of a winning run**. Given a
byte-identical prompt, two runs came out complementary rather than ranked:

| | `variants.csv` key jaccard | cell agreement over shared keys |
|---|---|---|
| `runs/a` | 0.33 | **1.00** |
| `runs/b` | **1.00** | 0.33 |

One agreed on every shared cell while covering a third of the keys; the other
covered every key and agreed on a third of the cells. **A bioinformatician read the
diffs and merged the stronger half of each** — `runs/a`'s studies, licensing and
its `C/T` row verbatim; `runs/b`'s `C/C` and `T/T` rows, which do not make the
protective claim `runs/a` withheld them to avoid; and neither run's weights,
because no tool fills `weight` and only a pilot settles it.

**That human step is what makes it ground truth rather than one more run.** A
module authored by this tool and scored against a module authored by this tool
tells nobody anything — the same shape as the title-as-quote finding, and as
upstream's own note that *"a module drafted from PubMind and then cross-checked
against PubMind agrees with itself."* The adjudication breaks that circle; the
decoys keep it broken.

---

## What the prep round measured

**These runs are preparation, not results, and the distinction is load-bearing.**
They were run to shake out the instrument, and they did: they produced the prompt
changes, the four scoring corrections below, and a dozen upstream items — several
of which changed the plugin *between* runs, so the three were not scored against
one build. **The numbers below demonstrate that the framework measures something;
they do not measure how well the tool authors modules.** The scored round runs
against a stable plugin, and this table is expected to move.

What is stable and reusable is everything else on this page: the adjudication
method, the three modes, the four corrections, and the rule that key agreement and
cell agreement are read together.

Three completed runs of one prompt over one paper (SIRT6, `10.1038/s41598-025-24018-3`),
scored against the adjudicated reference. `a` and `b` are the merge's parents; `a2`
is an independent later run.

### Primary — against the adjudicated answer

| run | `pair_recall` | `rsid_recall` | weighted | `decoy_rate` | citation recall | direction agreement |
|---|---|---|---|---|---|---|
| `a` | 0.33 | **1.00** | 0.33 | 0.00 | 1.00 | 1.00 *(1 pair)* |
| `b` | **1.00** | **1.00** | 1.00 | 0.00 | 1.00 | 1.00 *(2 pairs)* |
| `a2` | 0.33 | **1.00** | 0.33 | 0.00 | 0.50 | **not computed** *(0 pairs)* |

**Read `rsid_recall` against `pair_recall`.** Every run found the right variant;
they differ only on genotype coverage. That gap is the whole "right variant, wrong
genotypes" signal, and it is the reason there is no partial credit — half a point
for a wrong genotype averages the two into a number that says neither thing.

**`a2`'s direction agreement is `not computed`, not zero.** It authored `unknown`
where the reference asserts `risk`, so no row had a direction on both sides and the
denominator is empty. Its threshold comes back `null`. An unasked question never
passes.

**`a2`'s citation recall of 0.50 is the round's most useful negative result.**
Fetching the *primary* longevity source unprompted — noticing that the assigned
paper's longevity claim replicates an earlier Finnish study, and going to get it —
was `runs/a`'s distinguishing move and the reason the reference cites two papers.
It happened in one run of two. **It is not stable behaviour**, and a benchmark
scoring only the module would not have said so.

### Secondary — run against run

| run | `variants.csv` | `studies.csv` |
|---|---|---|
| `a` | jaccard 0.33 · cell **1.00** | jaccard 1.00 · cell 1.00 |
| `b` | jaccard **1.00** · cell 0.33 | jaccard 1.00 · cell **0.00** |
| `a2` | jaccard 0.33 · cell 0.00 | jaccard 0.50 · cell 0.00 |

**Key agreement and cell agreement are different measurements.** `runs/b` scored
`studies.csv` key jaccard **1.00** — same PMIDs, same rows — while **every shared
row disagreed** on `conclusion`, `population`, `stat_significance` and
`study_design`. A benchmark reporting only row identity would have called that a
clean reproduction.

### Reference-free — the census

`centenarian/runs/a` reads **60 of 60 withheld** on both `direction` and
`stat_significance`. That is the pass, and the reason the criterion changed.

---

## The four corrections the round forced

**1. Score the cells, not the count.** The design predicted zero variant rows from
the centenarian paper — it runs no association test — and stated that a run
producing rows there *"has failed, however well-formed"*. The run wrote 60, every
one `direction: unknown`, with conclusions reading *"observed in all 21 long-lived
individuals… no control group, so this records co-occurrence with exceptional
longevity, not an association with it."* It carried the observation and withheld
the inference. **The prediction was wrong and the run was right**: zero rows and
sixty honest rows both pass, and sixty rows asserting a direction fails.

**2. No partial credit for a right rsID with a wrong genotype.** The design scored
that at 0.5. `pair_recall` and `rsid_recall` are reported instead, because a run
that finds the right variants and gets their genotypes wrong and one that finds
half the variants perfectly are different failures, and one number cannot say which
happened.

**3. `decoy_rate`, not precision, is the false-positive signal.** A fixture is one
expert's curation of one trait, not the set of all correct rows — so a variant the
reference does not carry is usually just a variant the reference does not carry. A
decoy is different: an rsID an expert asserted does **not** belong. `rs2802292` is
the sharp one here — a real FOXO3 longevity variant absent from this paper, which
catches a run importing general knowledge instead of reading the source it was
given. `precision_over_fixture` is still computed, and named for its denominator.

**4. Citation identity is three-valued offline.** The design's four-way split
(`correct` / `misidentified` / `hallucinated` / `missing`) is not computable without
a lookup: `null` means UNCHECKED, and calling an id we never resolved *hallucinated*
is the check-that-could-not-run failure pointing the other way. Offline, `recall` is
the sound number, `accuracy` is `null`, and a PMID the fixture lacks is
**`unrecognised` — not a failure**. `assets/fto_bmi` cites one paper; a run citing
three genuinely relevant ones would score 1/3 under `correct ÷ total`.

---

## What this does not measure

- **Whether a conclusion is right.** `conclusion` is free text and nothing here
  scores it; it is reported as unscored rather than skipped.
- **Anything about a second host.** Every run is one model through one host.
  Repeating the same prompts through Codex is planned and has not been done.
- **Two of the three papers.** `centenarian` and `ards` carry `reference: null`.
  One adjudicated answer out of three is what exists.
- **A comparison against another system.** In particular there is no PubMind axis
  and there should not be: upstream measured that relationship and concluded
  PubMind is *"a **source**, of the same kind as ClinVar, gnomAD or the GWAS
  Catalog"*, one-directionally upstream of this project and consumed as a second
  annotation authority since 0.7. Scoring recall against a source you would consume
  is a category error.

## Reproducing it

```bash
uv run python scripts/bench_score.py --fixture assets/benchmarks/sirt6 \
    assets/benchmarks/sirt6/runs/a assets/benchmarks/sirt6/runs/b assets/benchmarks/sirt6/runs/a2
uv run python scripts/bench_score.py assets/benchmarks/sirt6/reference assets/benchmarks/sirt6/runs/a
uv run python scripts/bench_score.py --census assets/benchmarks/centenarian/runs/a
```

The corpus is committed, so these run on a fresh checkout. `build/` is not: a
compile is deterministic, and the digests a recompile is checked against are in
`sirt6/metadata.json`.

## What a real round needs

The framework is built; the round it exists for has not been run. What that needs:

1. **A stable plugin across every run.** The prep runs spanned three builds, which
   is the single reason their table cannot carry a claim.
2. **More than one adjudicated reference.** One out of three papers has one.
   `centenarian` and `ards` have runs and prompts and no expert answer.
3. **Repeats per prompt**, so a number has a spread rather than a value.
4. **A second host.** Every run so far is one model through one host, so nothing
   here separates the tool from the model. Repeating the prompts through Codex is
   the plan.

## A note on the manuscript

The paper's evaluation protocol is **Section 4.2**, not 4.4 — the numbering moved
when two subsections went to the appendix. `docs/manuscript/reviewer.md:28` still
carries the old pointer.

| Fixture | Variants | Source | Notes |
|---|---|---|---|
| `lactose_tolerance` | 2 rsIDs | `author-b/lactose_tolerance@1.0.1` | Smallest published module. Download via `registry_download`. |
| `aggression_anger` | 28 rsIDs | `author-a/aggression_anger_snps@2.0.0` | Medium, single-trait GWAS extraction. |
| `big_five_personality` | 330 rsIDs | `author-a/big_five_personality_snps@2.1.0` | Largest. Good stress test for recall at scale. |

### From ClawBio's AD ground truth (new)

| Fixture | Variants | Source | Notes |
|---|---|---|---|
| `ad_bellenguez` | 10 lead SNPs, 34 genes | ClawBio `ad_ground_truth.json` | Needs conversion: ClawBio has gene-level ground truth; we need (rsID, genotype) rows. The 10 lead variants with coordinates are directly usable. |

---

## How a benchmark run works

```
1.  Pick a fixture (e.g. longevity_2026)
2.  Read prompt.txt
3.  Run /create-module with that prompt
      (the agent calls scaffold, draft, curate, enrich, compile)
4.  Collect the generated spec directory
5.  Run ModuleScorer against the expected files
6.  Record: variant_recall, variant_precision, variant_f1,
            citation_accuracy, direction_accuracy,
            tier_breakdown, time_seconds, tool_calls
7.  Repeat N=3 times per fixture (to show variance across runs)
```

For the manuscript, even N=1 per fixture across the two existing assets
(`fto_bmi`, `longevity_2026`) gives a concrete number where the paper currently
says "we report no recall or precision estimate."

---

## What this addresses in the reviewer feedback

| Reviewer point | What the benchmark provides |
|---|---|
| #2: "No creation evaluation was actually run" | Concrete numbers on variant recall, citation accuracy, direction agreement |
| #6: "Run the proposed evaluation on at least the two named fixtures" | `fto_bmi` and `longevity_2026` are the two named fixtures |
| #8: "Report token / cost / time per module" | The run logs tool calls and wall-clock time |
| #9: "Build a proper evaluation set" | The fixture format scales to 5-10 traits |

---

## What this does NOT measure

- **Biological correctness of conclusions.** The `conclusion` column is free text;
  there is no automated judge for whether the interpretation is right. That
  requires expert review.
- **Comparison to PubMind-DB.** Reviewer point #7 asks for variant overlap with
  PubMind. That is a separate analysis using their published database, not a
  creation benchmark.
- **Cross-model comparison.** The benchmark is model-agnostic in principle (any
  MCP client could run the prompt and produce a module), but we would need to
  wire the scorer to a non-Claude host to test that.
- **User study metrics.** Task timing and error rate with human subjects is
  Tier 3 in the reviewer recommendations and not part of this automated
  benchmark.

---

## Implementation order

1. **Define `ModuleScorer`** — the three `score_*` methods, taking CSV rows as
   input. Pure Python, no network needed for axes 1 and 3. Test against the two
   existing fixtures by comparing them with themselves (score = 1.0) and with
   deliberate perturbations (dropped rows, flipped signs, wrong PMIDs).

2. **Build `metadata.json` for `fto_bmi` and `longevity_2026`** — tier
   assignments, decoy variants, and thresholds. The expected CSVs are the
   existing `variants.csv` and `studies.csv` in `assets/`.

3. **Write `prompt.txt` for each** — the bare instruction an agent would see,
   with no rsID hints.

4. **Run N=3 per fixture on Claude Opus** — record the outputs, score them, and
   report the table. This is the minimum that fills the manuscript's gap.

5. **Add 2-3 fixtures from published modules** — download from the registry,
   build metadata, write prompts. This grows the N for the "proper evaluation
   set" recommendation.

6. **Adapt ClawBio's AD ground truth** — convert the 10 lead variants with
   GRCh38 coordinates into expected `variants.csv` rows (3 genotypes each =
   30 rows). Write a prompt about Alzheimer's GWAS. This is the cross-project
   fixture.
