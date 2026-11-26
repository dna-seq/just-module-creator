# Round 5: the plugin against the same model without it

The runs behind the paper's comparison of the plugin with two no-plugin arms (Results, "Against the
same model without the plugin"). The person asked for this round on 2026-11-25, answering the EASRP
reviews. The tester seat ran it on 2026-11-25 and 2026-11-26.

**Each fixture's runs:**

| Run | Model | Arm |
|---|---|---|
| `<fixture>/runs/r5-opus5-p` | claude-opus-5 | the plugin |
| `<fixture>/runs/r5-opus5-b` | claude-opus-5 | docs + compiler, no plugin |
| `<fixture>/runs/r5-opus5-c` | claude-opus-5 | published examples + paper, no plugin |
| `<fixture>/runs/r5-opus55-{p,b,c}` | claude-opus-5-5 | the same three arms, same briefs, fresh directories |

**What is kept:**

- Each P and B run directory is the spec directory exactly as the run left it, minus the compiled
  `build/` outputs.
- C wrote parquet, never a spec. Its run directory holds `reverse_module`'s reconstruction of that
  parquet, which is what the scorer reads. Its own README sits under `as-run/`.
- Transcripts and the machine's paths stay local.

## The arms

- **Every arm:** one session per run, `claude -p --permission-mode auto`, the fixture's `prompt.txt`
  as the task. Both waves ran on one build of the plugin: main c2d93ee (plugin 0.48.20). Wave 2 started
  from c034eb7, which differs from c2d93ee only outside the plugin's paths.
- **P, the plugin.** Run from the plugin's repository, with the plugin and the account's usual
  connectors, as an author has them. It got the same meta block as rounds 1 to 4 (version pin,
  no git, one spec directory, no reading other runs; `sirt6/runs/README.md` has it).
- **B, docs plus compiler.**
  - Run from a directory outside any repository, with `--strict-mcp-config --setting-sources
    project,local --disable-slash-commands --tools Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch`.
    The session's init message listed no MCP server, no skill and none of the plugin.
  - It had the plugin's `skills/` tree and README as plain files, which name tools it does not have.
    It also had a Python environment with `just-dna-compiler` 0.8.9 and its dependencies, with no
    enricher.
  - Prompt: `prompt.txt` with "how was the plugin to actually use?" read as "how were the docs and
    tools you had to actually use?", plus the block below.
- **C, examples plus paper.**
  - Run as B.
  - It had two published modules as parquet and README: `winternewt/adhd_gwas_loci` 1.0.1 and
    `antonkulaga/bodybuilding` 1.0.2. Their `manifest.json` files were removed because they name the
    compiler.
  - It also had the paper's full text, every supplementary file the paper publishes, and a Python
    environment with polars, pyarrow and pandas only.
  - The examples were checked to carry no fixture's answer. `eric-mods/lactose_tolerance` was swapped
    out because it carries sirt6's decoy rs4988235.

**The block B and C got.** `<DOCS>`, `<ENV>`, `<RUN_DIR>`, `<SCRATCH>`, `<EXAMPLES>` and `<PAPER_DIR>`
stand for machine paths. C's prompt names the examples and the paper's files in place of the docs.

```text
**What you have, and the rules of this run:**

- Documentation on authoring just-dna modules is in `<DOCS>`. It was written for a plugin you do not have here: the tools it names are not available to you.
- A Python environment with the just-dna compiler: `<ENV>/bin/python` and `<ENV>/bin/just-dna-compiler`. Use it as it is. Do not install or download any package, plugin or code (no pip, no uv add, no git clone, no fetching a package or repository); reading papers and databases on the web is fine.
- Work only inside your run directory, your scratch directory `<SCRATCH>`, and the two directories named above. Do not read or list anything else on this machine.
- Don't run any git command.
- Put exactly one module spec directory inside your run directory; throwaway copies go in your scratch directory.
```

## Isolation, read from the transcripts

- **No B or C run installed or downloaded a package.**
- **c-centenarian (opus-5) fetched the format's documentation from GitHub.** That was the
  compiler's `docs/SCHEMAS.md`, `COMPILER.md`, `MODULE_LIFECYCLE.md` and `ENRICHER.md`, plus two of
  just-dna-lite's pages. Its scores are marked C\*.
- **p-ards (opus-5) downloaded the published `just-dna-seq/longevitymap`** to look at its genotype
  layout. None of its rows came from it: all 263 variants are in the paper's ST5, and every direction
  matches ST5.
- **p-sirt6 (opus-5) listed the round's working directory** (names only) in its first call, which its
  brief forbids. No run read another run's files.

## Scores, claude-opus-5

**sirt6, against the adjudicated reference.** Re-score:

```bash
uv run python scripts/bench_score.py --fixture assets/benchmarks/sirt6 assets/benchmarks/sirt6/runs/r5-opus5-p assets/benchmarks/sirt6/runs/r5-opus5-b assets/benchmarks/sirt6/runs/r5-opus5-c
```

| | rsID recall | pair recall | decoy rate | precision over fixture | citation recall | direction agreement |
|---|---|---|---|---|---|---|
| P | 1.00 | 1.00 | 0 | 1.00 | 1.00 | 1.00 |
| B | 1.00 | 1.00 | 0 | 1.00 | 1.00 | 0.50 |
| C | 1.00 | 1.00 | 0 | 0.33 | 0.00 (1.00 read raw) | 0.50 |

- B and C call C/C "protective" where the reference says neutral.
- C's `studies.csv` fails the format's vocabularies, so the scorer reads none of its rows. Read raw,
  the table cites both expected PMIDs.
- C's two extra variants (rs107251, rs350846) are other SIRT6 variants the paper mentions, not decoys.

**centenarian and ards.** No adjudicated reference exists, so each row is checked against the paper.

| | variants (rows) | not in the paper | coordinate differs from P | reversed direction | PMIDs real / cited |
|---|---|---|---|---|---|
| P centenarian | 8 (10) | 0 | n/a | n/a, all `unknown` | 2 / 2 |
| B centenarian | 8 (24) | 0 | 24 rows unplaced | n/a | 2 / 2 |
| C\* centenarian | 108 (324) | 15 | 0 of 8 shared | n/a | 1 / 1 |
| P ards | 263 (789) | 0 | n/a | 0 of 263 | 2 / 2 |
| B ards | 48 (144) | 0 | 0 of 48 | 0 of 48 | 2 / 2 |
| C ards | 263 (789) | 0 | 0 of 263 | 0 of 263 | 6 / 6 |

- **Not in the paper:** the rsID appears nowhere in the paper or its supplementary files. C\*'s 15
  are variants the paper lists by GRCh37 position with no rsID; C assigned rsIDs. All 15 are live
  dbSNP records at the GRCh38 positions C wrote. Whether those match the paper's GRCh37 positions was
  not checked: Ensembl's GRCh37 service was down.
- **Reversed direction (ards):** each run's risk-raising allele (from the homozygotes' `state`, else
  `direction`), compared with the outcome the run says it scores.
  - The paper gives two: the shared disease factor (ST5 `beta`) and extreme longevity (ST9). On 64 of
    the 263 variants, the disease-raising allele is not the longevity-lowering one.
  - P and C score the disease factor and match ST5 on all 263. B kept the 48 with a nominal longevity
    effect and matches both tables on them.
  - P and C label genotypes oppositely on every variant, yet they agree on the allele. They differ
    only in which homozygote is the neutral baseline.
- **B centenarian:** with no enricher there is no `resolution.csv`, so its 24 rows compiled with no
  position and the artifact matches no genome.

**Validity.** P and B were checked with `just-dna-compiler validate --strict`; C with `validate` on
its reconstructed spec. A published module reconstructed the same way gives 0 errors.

| | P | B | C |
|---|---|---|---|
| sirt6 | clean | clean | 46 errors |
| centenarian | clean | refused: 24 unplaced | 109 errors (C\*) |
| ards | clean | clean | 527 errors |

C's errors are values outside the format's vocabularies (`ancestry` "Finnish", `age_of`
"participants", `sample_unit` "effective_n", and so on). A loader refuses those tables.

## Scores, claude-opus-5-5

All nine runs ran on the same build as wave 1, with the same briefs, in fresh directories. No
transcript shows a read outside the run's own permitted directories, and no B or C run fetched any
of the format's code or docs.

**sirt6, against the adjudicated reference.**

```bash
uv run python scripts/bench_score.py --fixture assets/benchmarks/sirt6 assets/benchmarks/sirt6/runs/r5-opus55-p assets/benchmarks/sirt6/runs/r5-opus55-b assets/benchmarks/sirt6/runs/r5-opus55-c
```

| | rsID recall | pair recall | decoy rate | precision over fixture | citation recall | direction agreement |
|---|---|---|---|---|---|---|
| P | 1.00 | 1.00 | 0 | 1.00 | 1.00 | 1.00 |
| B | 1.00 | 1.00 | 0 | 1.00 | 0.50 | 1.00 |
| C | 1.00 | 1.00 | 0 | 1.00 | 0.00 (1.00 read raw) | 1.00 |

- All three call T/T "risk", where the reference withholds a direction.
- B cites only the fixture paper, not the earlier Finnish study.
- C's `studies.csv` again fails the vocabularies; read raw, it cites both expected PMIDs.

**centenarian and ards.**

| | variants (rows) | not in the paper | coordinate | reversed direction | PMIDs real / cited |
|---|---|---|---|---|---|
| P centenarian | 11 (33) | 0 | Ensembl-resolved | n/a, all `unknown` | 2 / 2 |
| B centenarian | 8 (18) | 0 | 18 rows unplaced | n/a | 1 / 1 |
| C centenarian | 108 (324) | 15 | 0 differ of 11 shared | n/a | 1 / 1 |
| P ards | 49 (147) | 0 | Ensembl-resolved | 0 of 49 (longevity) | 1 / 1 |
| B ards | 6 (18) | 0 | 0 differ of 6 | 0 of 6 | 1 / 1 |
| C ards | 263 (789) | 0 | 0 differ of 263 | 0 of 263 (disease factor) | 2 / 2 |

- C centenarian chose the same 108 variants as wave 1's C\*, at the same positions. Its 15 not in the
  paper are the same 15, all live at those positions in dbSNP. This time it fetched no docs.
- P ards kept the 49 variants with a nominal longevity effect, and B ards the 6 that survive
  correction. Both score longevity (ST9) and match it on every variant.
- P ards' one variant that differs from ST5 is a discordant one (rs34333163), correct for
  longevity.
- C ards' positions match wave 1's Ensembl-resolved ones on all 263.

**Validity.**

| | P | B | C |
|---|---|---|---|
| sirt6 | clean | clean | 10 errors |
| centenarian | clean | refused: 18 unplaced | 255 errors |
| ards | clean | clean | 263 errors |

**Effort (wall clock, turns), both waves.** Runs within a fixture ran side by side.

| | sirt6 | centenarian | ards |
|---|---|---|---|
| P opus-5 | 58 min, 121 | 49 min, 123 | 52 min, 132 |
| B opus-5 | 21 min, 96 | 25 min, 107 | 30 min, 100 |
| C opus-5 | 56 min, 80 | 24 min, 90 | 24 min, 81 |
| P opus-5-5 | 6 min, 35 | 24 min, 130 | 20 min, 104 |
| B opus-5-5 | 6 min, 43 | 10 min, 58 | 7 min, 64 |
| C opus-5-5 | 9 min, 37 | 18 min, 64 | 14 min, 61 |

**Not computed:**

- rows an expert would correct;
- free-text conclusions;
- any spread, since there is one run per cell.
