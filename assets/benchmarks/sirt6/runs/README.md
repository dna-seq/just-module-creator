# The sirt6 runs

`a`, `b` and `a2` are the runs the reference was adjudicated from (`../../README.md`). `1`, `2` and `3`
are the paper's Table 3: the later evaluation round, scored against that reference.

## Table 3's runs

| Run | Spec directory as run | Finished (UTC) |
|---|---|---|
| `1` | `data/interim/repro-bench-3/run-sirt6-c/longevity_sirt6` | 2026-08-31 05:13 |
| `2` | `data/interim/repro-bench-3/run-sirt6-d/longevity_sirt6` | 2026-08-31 05:48-05:55 |
| `3` | `data/interim/repro-bench-3/run-sirt6-e/longevity_sirt6` | 2026-08-31 05:48-05:55 |

Each is the spec directory exactly as the run left it, copied 2026-11-19 from the git-ignored working tree
of the machine that ran them. The compiled `build/` outputs are not kept: they are compile products.

**What ran them:** just-module-creator plugin 0.27.0 (each brief told the run to stop on any other),
just-dna-compiler 0.6.6 (each `provenance.json`), Claude Code 2.1.251, model `claude-opus-5`, one subagent
per run.

**Re-score:**

```bash
uv run python scripts/bench_score.py --fixture assets/benchmarks/sirt6 \
  assets/benchmarks/sirt6/runs/1 assets/benchmarks/sirt6/runs/2 assets/benchmarks/sirt6/runs/3
```

Run 2026-11-19 on these copies: run 1 rsID recall 1.00, pair recall 0.67, decoy rate 0.00, citation recall
1.00, direction agreement 1.00; runs 2 and 3 the same with pair recall 1.00. Table 3 as published.

## The prompt

`../prompt.txt`, with the run directory filled in, followed by this block. `<RUN_DIR>` and `<SCRATCH>`
stand for the machine's paths, which are left out here; the transcripts stay local for the same reason.

```text
**Meta, before you start — not part of the task, just so we don't waste a run on a wrong environment:**

- Check the plugin version is **0.27.0**. If the MCP server reports anything else, stop and say so rather than working — a stale build serves an old tool surface and the run is void.
- Don't run any git command. No commits, no staging, no branches, whatever your usual habit is.
- If you need a scratch directory for temporary files, use `<SCRATCH>/run-sirt6-<c|d|e>` — nothing else, and do not read from any other scratch directory.
- Put exactly one module spec directory inside your run directory. If you need a throwaway copy to probe something, put it in your scratch directory, not beside the module.
- Do not read anything under `data/interim/` or `assets/benchmarks/` other than your own run directory. Those contain other attempts at this same task and reading them would void the run.
```

Run 1's block lacks the "exactly one module spec directory" line, which was added after it, and its last
line says "earlier attempts" where runs 2 and 3 say "other attempts". The ban names reading but not
listing; `docs/BENCHMARKING.md` says why a later round must name both.
