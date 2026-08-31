# The authoring benchmark corpus

Three papers, one prompt each, several agent runs per paper, and — for one of the three — a
**reference that a human adjudicated from those runs**. This is what the scorer in
`src/just_module_creator/bench.py` scores against, and it is committed rather than gitignored so
that a test can reach it and a reader can re-run it.

```
uv run python scripts/bench_score.py sirt6/reference sirt6/runs/a sirt6/runs/b sirt6/runs/a2
uv run python scripts/bench_score.py --census centenarian/runs/a
```

## What is here

| Fixture | Paper | Runs | Reference |
|---|---|---|---|
| `sirt6/` | Sheikholmolouki 2025, `10.1038/s41598-025-24018-3` | `a`, `b`, `a2` | **yes — adjudicated** |
| `centenarian/` | `10.1186/s40246-025-00772-3` | `a`, `b` | no |
| `ards/` | `10.1007/s11357-025-02044-3` | `b` | no |

`evidence/S76-partial-resolution/` is a preserved artifact rather than a run: the short
`resolution.csv` behind `F70`, captured and hash-verified. Its README explains what it turned out to
be, which is not what it was first reported as.

## How the reference was made, and why that is the whole point

`sirt6/reference/` is **not** a copy of a winning run. Given a byte-identical prompt, two runs came
out complementary rather than ranked:

| | `variants.csv` key jaccard | cell agreement over shared keys |
|---|---|---|
| `runs/a` | 0.33 | **1.00** |
| `runs/b` | **1.00** | 0.33 |

One agreed on every shared cell while covering a third of the keys; the other covered every key and
agreed on a third of the cells. Neither is a reference. **A bioinformatician read the diffs and
merged the stronger half of each** — `runs/a`'s studies, licensing, README argument and its `C/T` row
verbatim; `runs/b`'s `C/C` and `T/T` rows, which do not make the protective claim `runs/a` withheld
them to avoid; and neither run's weights, because no tool fills `weight` and only a pilot settles it.
`sirt6/metadata.json` records that provenance and `verification.json`'s closure carries
`closed_by: human-adjudicated`.

**That human step is what makes this ground truth rather than one more run.** A module authored by
this tool and then scored against a module authored by this tool tells nobody anything — the same
shape as the title-as-quote finding, and as upstream's own note that *"a module drafted from PubMind
and then cross-checked against PubMind agrees with itself."* The adjudication is what breaks that
circle; the decoys in `metadata.json` are what keep it broken.

## Reading a score

**Key agreement and cell agreement are different measurements and both are reported.** In this round
`studies.csv` scored key jaccard **1.00** while every shared row disagreed on `conclusion`,
`population`, `stat_significance` and `study_design`. A benchmark reporting only the first would have
called that a clean reproduction.

**Score the cells, not the count.** The round's design predicted zero variant rows from the
centenarian paper — it runs no association test — and declared that any rows would be a failure. The
run wrote 60, every one `direction: unknown`, with conclusions reading *"observed in all 21 long-lived
individuals… no control group, so this records co-occurrence with exceptional longevity, not an
association with it."* It carried the observation and withheld the inference, which is what the
authoring skills ask for. **The prediction was wrong and the run was right**: zero rows and sixty
honest rows both pass; sixty rows asserting a direction fails.

## What does not travel, and why

- **No `build/`.** A compile is deterministic, so the artifact is reproducible from the spec.
  `*.parquet` and `assets/benchmarks/**/build/` are both in `.gitignore` so a stray `git add` cannot
  sweep one in. The digests worth keeping — `content_signature`, `artifact_digest`, the closure
  `module_hash` — are in `sirt6/metadata.json`, where a recompile is checked against them.
- **Not `run-ards-a`.** It was killed before finishing and left 789 rows, no artifact, and a
  `verification.json` attesting bytes that were never written. `ards/VOID.md` is the record; the bytes
  are not committed and the run **must never be scored**.
- The run directories keep **their original layouts** — `runs/a` at its root, `runs/b` under
  `longevity_sirt6/`, `runs/a2` under `spec/`. All three satisfied the same ask, and a scorer that
  assumes one layout silently scores nothing, so the corpus exercises `locate_spec` as it shipped
  rather than being tidied into uniformity.

## What this corpus is not

- **Not an independent ground truth for the two fixtures with no reference.** `centenarian` and
  `ards` carry `expected_spec: null` deliberately: one adjudicated case out of three is what exists,
  and claiming more would be the thing this corpus is built to avoid.
- **Not unbriefed, for `centenarian`.** Its `metadata.json` carries `pre_briefed`, because two skills
  a run loads name this paper, its PMID, `rs61849494`'s coordinates on both builds, and what two
  earlier runs on it decided. A run's rsID-only identity and its exclusion of the coordinate-only
  variants are therefore guidance-following rather than independent judgement — the briefing is
  constant across runs, so run-to-run agreement still measures something, but no score here says an
  unbriefed author would land in the same place. `F82`: this is structural, not an accident. Every
  paper a dogfooding probe learns from ends up in the guidance the next run reads, so **budget a fresh
  paper per round rather than expecting the corpus to keep.**
- **Not a comparison against another system.** In particular there is no PubMind axis here and there
  should not be: upstream measured that relationship and concluded PubMind is *"a **source**, of the
  same kind as ClinVar, gnomAD or the GWAS Catalog"*, one-directionally upstream of this project.
  Scoring recall against a source you would consume is a category error.
- **Not a claim about models or hosts.** Every run here is one model through one host. Repeating the
  same prompts through Codex is planned and has not been done.

Working notes for the round that produced this — what was killed and why, what each run cost — stay
in `data/interim/repro-bench-2/`, which does not travel.
