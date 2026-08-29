# ClawBio-Inspired Benchmark for just-module-creator

A benchmark design inspired by ClawBio's genomic evaluation infrastructure,
adapted to measure **module authoring quality** rather than pipeline filtering
accuracy.

---

## What ClawBio does and why it does not transfer directly

ClawBio's benchmarks test **analysis pipelines**: given a VCF or a trait, did the
tool filter the right variants, compute the right heritability, or classify the
right alleles? Their AD ground truth (`tests/benchmark/ad_ground_truth.json`)
scores gene recovery — did the pipeline find BIN1, APOE, TREM2? Their
`BenchmarkScorer` computes precision, recall, F1, and a tier-weighted composite.

Our task is different. We do not filter variants from a genome. We **author
module rows from source literature**. The input is a prompt describing a trait
and optionally naming papers; the output is a `variants.csv` (or other table)
plus `studies.csv`, `module_spec.yaml`, and sidecars. The benchmark must ask:
did the assistant recover the right variants, cite the right papers, and assign
the right effect directions?

What we borrow from ClawBio:

| ClawBio pattern | Our adaptation |
|---|---|
| Tiered ground-truth JSON with positive/negative sets | Ground-truth fixture per trait with expected rows and decoy variants |
| `BenchmarkScorer` with precision/recall/F1 | `ModuleScorer` that compares generated vs expected (rsID, genotype) pairs |
| Per-skill `bench_test_cases/` with input + ground_truth | Per-fixture directories with prompt + expected module files |
| `nightly_demo_sweep.py` aggregate scoring | Sweep across all fixtures, aggregate per-axis scores |
| Tier weighting (causal 3x, GWAS 2x, novel 1x) | Evidence-tier weighting (peer-reviewed 3x, replicated GWAS 2x, preprint/candidate 1x) |

---

## The three axes

The manuscript (Section 4.4) already proposes these. The benchmark makes them
concrete.

### Axis 1: Variant recovery

**Question:** Did the generated module contain the right (rsID, genotype) rows?

**Metric:** Precision, recall, F1 over the set of (rsID, genotype) pairs.

A variant row is a true positive when the generated `variants.csv` contains a
row with the same `rsid` and the same `genotype` as the ground truth. A row
with the right rsID but wrong genotype counts as a partial match (scored at
0.5). A generated row whose rsID is not in the ground truth is a false positive.
A ground-truth row not present in the output is a false negative.

Tier weighting applies: a missed Mendelian variant (APOE) costs 3x a missed
candidate from a preprint. This directly mirrors ClawBio's
`tier1_causal` / `tier2_gwas_replicated` / `tier3_novel` weighting.

### Axis 2: Citation identity

**Question:** Is every cited PMID real, and does it name the paper the module
claims it does?

**Metric:** Citation accuracy = correct citations / total citations.

For each row in the generated `studies.csv`:
1. Does the PMID exist? (`lookup_citation`)
2. Does the returned title match the paper the row's claim is about?

A PMID that exists but names a different paper is a **misidentification**, not a
true positive. This is the "existence never settles identity" rule from the
server instructions. A fabricated PMID is a hallucination.

Breakdown:
- `correct`: PMID exists and title matches
- `misidentified`: PMID exists, title is wrong paper
- `hallucinated`: PMID does not exist
- `missing`: ground truth has a citation the output lacks

### Axis 3: Effect-direction agreement

**Question:** Does the generated `weight` sign agree with the ground truth?

**Metric:** Direction accuracy = agreeing rows / rows where both sides have a
direction.

For each (rsID, genotype) pair present in both generated and ground truth:
compare `direction` (or sign of `weight`). Agreement is binary: the sign
matches, or it does not. Rows where either side has `unknown` or no weight are
excluded from the denominator.

Magnitude is reported separately as mean absolute error but is **not** a
pass/fail criterion — weight magnitude is an authored choice, not a fact to
recover.

---

## Ground-truth fixture format

Each fixture is a directory under `assets/benchmarks/`:

```
assets/benchmarks/
  longevity_bellenguez/           # a trait-specific fixture
    prompt.txt                    # the natural-language input to the agent
    expected_variants.csv         # ground-truth variants.csv
    expected_studies.csv          # ground-truth studies.csv (PMIDs + titles)
    metadata.json                 # fixture metadata and scoring config
  fto_bmi/
    prompt.txt
    expected_variants.csv
    expected_studies.csv
    metadata.json
  ad_bellenguez/                  # adapted from ClawBio's AD ground truth
    prompt.txt
    expected_variants.csv
    expected_studies.csv
    metadata.json
```

### `metadata.json`

Adapted from ClawBio's `ad_ground_truth.json` structure:

```json
{
  "version": "1.0.0",
  "trait": "Human longevity / healthy aging",
  "description": "Longevity-associated variants from 2025-2026 GWAS and linkage studies",
  "source_references": [
    "Deelen et al. 2019 (Nature Communications 10:3669)",
    "Timmers et al. 2025 (preprint)"
  ],
  "variant_tiers": {
    "tier1_established": {
      "description": "Replicated across multiple GWAS at genome-wide significance",
      "weight": 3.0,
      "rsids": ["rs429358", "rs7412", "rs2802292"]
    },
    "tier2_replicated": {
      "description": "Reported in at least two independent studies",
      "weight": 2.0,
      "rsids": []
    },
    "tier3_candidate": {
      "description": "Preprint or single study, no independent replication",
      "weight": 1.0,
      "rsids": [
        "rs200818241", "rs146711285", "rs758447806", "rs535256255",
        "rs151230291", "rs141426527", "rs372893802", "rs61745123",
        "rs1209730474", "rs143389605"
      ]
    }
  },
  "decoy_variants": {
    "description": "Variants NOT associated with this trait, to catch false positives",
    "rsids": ["rs1421085", "rs4988235", "rs12913832", "rs1800497", "rs53576"]
  },
  "scoring": {
    "minimum_acceptable": {
      "variant_recall": 0.5,
      "citation_accuracy": 0.8,
      "direction_accuracy": 0.9
    }
  }
}
```

### `prompt.txt`

The bare prompt an agent would receive. No hints about which rsIDs to include:

```
Create a module about human longevity and healthy aging.
Focus on the APOE locus, FOXO3, and any rare variants from
recent linkage studies in long-lived families. Use the 2026
cross-trait longevity GWAS meta-analysis and the December 2025
bioRxiv preprint on affected sib-pair analysis in 212 sibships.
```

---

## The scorer

A Python class adapted from ClawBio's `BenchmarkScorer`:

```python
class ModuleScorer:
    """Score a generated module against a ground-truth fixture."""

    def __init__(self, fixture_dir: Path):
        self.metadata = json.loads((fixture_dir / "metadata.json").read_text())
        self.expected_variants = load_csv(fixture_dir / "expected_variants.csv")
        self.expected_studies = load_csv(fixture_dir / "expected_studies.csv")

    def score_variant_recovery(self, generated_variants: list[dict]) -> dict:
        """Precision, recall, F1 over (rsid, genotype) pairs, tier-weighted."""
        ...

    def score_citation_identity(self, generated_studies: list[dict]) -> dict:
        """For each PMID: exists? title matches? Requires network."""
        ...

    def score_direction_agreement(self, generated_variants: list[dict]) -> dict:
        """Sign agreement on rows present in both sets."""
        ...

    def score_all(self, spec_dir: Path) -> dict:
        """Run all three axes against a generated module directory."""
        ...

    def summary_markdown(self, result: dict) -> str:
        """Produce a report table, similar to ClawBio's."""
        ...
```

The scorer is **offline for axes 1 and 3** (CSV comparison) and **online for
axis 2** (PMID lookup). A cached mode can store lookup results alongside the
fixture for reproducibility.

---

## Fixtures we can build now

### From existing `assets/`

| Fixture | Variants | Source | Notes |
|---|---|---|---|
| `fto_bmi` | 1 rsID, 3 genotypes | Expert-authored | Already in `assets/fto_bmi/`. Smallest possible test. |
| `longevity_2026` | 7 rsIDs, 20 genotypes | Expert-authored | Already in `assets/longevity_2026/`. Mixed tiers: established + preprint candidates. |

### From published production modules

| Fixture | Variants | Source | Notes |
|---|---|---|---|
| `lactose_tolerance` | 2 rsIDs | `eric-mods/lactose_tolerance@1.0.1` | Smallest published module. Download via `registry_download`. |
| `aggression_anger` | 28 rsIDs | `antonkulaga/aggression_anger_snps@2.0.0` | Medium, single-trait GWAS extraction. |
| `big_five_personality` | 330 rsIDs | `antonkulaga/big_five_personality_snps@2.1.0` | Largest. Good stress test for recall at scale. |

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
