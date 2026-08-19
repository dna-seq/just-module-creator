# Handoff — the skills split, and the table dossiers

Written 2026-08-19, mid-work, to continue in a fresh session. Read this before touching
`skills/`.

## Where this came from

Four real authoring transcripts (plugin 0.9.0, four modules published to the immutable production
catalog) were read in full. The verdict was blunt and specific: **`skills/create-module/SKILL.md` is
1376 lines loaded whole, it documents pass one, and every one of those four sessions was in pass
two.** Upstream's own `MODULE_LIFECYCLE.md` §3 says *"pass two normally re-enters at 3 (curate), not
at 1"* and §6.1 names six kinds of second pass; we documented none of them.

So the skill is being split into an overview plus one skill per lifecycle stage, plus the second-pass
half that never existed, backed by an exhaustive per-table dossier set.

Source material saved out of the scratchpad (git-ignored, does not travel):
`data/interim/session-2026-08-19/` — the friction analysis, the skillset proposal, the dossier brief,
the flattening script, and the five flattened transcripts.

## What exists on disk now

| Thing | State |
|---|---|
| `skills/module-101/SKILL.md` | **written**, ~390 lines. The map: what a module is, what the plugin can and cannot do, the four packages, the lifecycle *including pass two*, the four on-disk shapes with real trees, author-surface vs agent-surface, the three enforced rules, where to go next |
| `skills/module-tables/references/*.md` | **24 dossiers, 9,705 lines**, one per CSV/parquet pair plus `module_spec`, `verification`, `readme`, `logs`, `logo`. **Under audit revision — see below** |
| 14 stage/reference skills | **scaffolds only.** Frontmatter, stage, upstream sources to write from, dossiers to read, and the established seeds. Each says STATUS: SCAFFOLD and routes to `create-module` |
| `skills/create-module/` | untouched, still the one canonical copy of the procedure for stages 1–8 |
| `skills/find-evidence/` | untouched; becomes `module-evidence` in the target shape, or stays as is |

Seventeen skills ship. `plugin.json`'s description states the count and
`tests/test_plugin_manifest.py` derives the check from it, so **adding a skill means updating that
one word** — the test says which.

## In flight — do not race it

**An audit agent is reworking the `references/` dossiers.** Do not edit them, and **re-read one
before quoting it**. The first pass was written by agents I primed, and my priming was partly
recalled rather than re-derived: **four premises were corrected by measurement** —
`published.json` filtering, `aggregate_logs` ordering, RM86's "reaches nothing" (registry 0.16/0.17
reads it), and "five of seventeen checks emit" (it is 15, RM72). Every one came from an upstream
*document* rather than from code. A dossier claim with a `path:line` or a measurement is a different
animal from one with a doc citation.

## The order of work

1. **Wait for the audit.** The user is fanning cross-check agents from the format repo. Nothing goes
   into skill prose until their verdicts land.
2. **Write `module-tables/SKILL.md`** first — it is the router the other skills lean on, and it is
   the cheapest to get right.
3. **Then the spine, in lifecycle order**, moving text across from `create-module` and deleting it
   there in the same change. One copy per fact.
4. **Then the second-pass three** (`module-revise`, `module-refresh`, `module-diff`) — these are new
   capability, not a re-shaping, and they are what the transcripts prove is missing.
5. **`create-module` shrinks to nothing** as the stages absorb it, or becomes a thin index. Decide
   which at the end, not now.

Rules that govern all of it: each skill ≤ ~200 lines with depth in `references/`; each names its
stage and the upstream section it derives from; **each ends with what that stage cannot do** (the
§7 absences, scoped) so an agent stops inventing tools; no column lists, no vocabularies — ask the
tool.

## Landmines

- **The plugin an author actually runs is the cache at `~/.claude/plugins/cache/.../0.7.0`, serving
  format 0.5.4.** So `describe_table` hands out pre-RM47 contracts and omits `measure_tiling`,
  `source_element` and `pmid`. Verified in-session: `describe_table("activity_phenotype.csv")`
  returned 11 columns where the installed 0.6.1 has 14. **"Ask the tool, never memory" is currently
  unreliable**, and every skill says to do it. A `format_version` on every generated answer, compared
  against `importlib.metadata` at call time, would make it self-diagnosing.
- **Our own skill is stale in at least five places**, all 0.6-era drift in text an author would act
  on: `SKILL.md:756-773` (resolution reaches `weights.parquet` only — RM43 filled the positional
  tables), `SKILL.md:756-758` (a `pgs` row's `chrom`/`start` — `PgsRow` has neither column),
  `SKILL.md:1279` + `references/SYMPTOMS.md:295` (shared-endpoint rule keyed on `measure_kind`, no
  mention of `measure_tiling`), `references/TABLES.md:21` + `docs/DOMAIN.md:95` +
  `tools/authoring.py:74` (copy-number group key still `modifier_cn`), and `SKILL.md:708` +
  `tools/authoring.py:59` (studies.csv in pre-RM47 terms). Fix these *as* the stages are written, not
  before — the dossiers carry the corrected wording.
- **`CLAUDE.md` §11 says registry 0.18.1 and one production module.** It is 0.18.2 and five.

## Findings the gather produced

Cross-cutting, each independently reproduced, none filed yet:

- **`registry_search(gene=…)` cannot find a non-`variants.csv` module** — six reproductions.
  `compiler.variant_stats` derives genes from `variants.csv` alone; the registry indexes that field.
  `cyp2c19_star_alleles` publishes `genes: []` with 106 rows carrying `gene=CYP2C19`.
- **The binning family is unsupported end to end** — three reproductions. No consumer implements the
  bin-a-measure lookup; four table kinds annotate nothing. One lookup fixes all four.
- **Attestations that record a check nobody could run** — three instances, and this is the trust
  layer.
- **Weights: fixtures and reality are inverses.** 0 of 42 cells authored across 16 reference
  examples; **2,439 of 2,439** across 27 real submitted bundles, 26 distinct values in [−1.5, 1.5],
  and 0 of 27 carrying `gwas_effects.csv`.
- **Backwards compatibility holds, measured**: 0 genuine breaks across 27 real 0.1-era bundles under
  0.6.1, 24/27 still validating, three failures being plain author defects.

Per-dossier upstream candidates are in each file's own sections. Two of ours worth doing early:
`enrich_gwas` is wrapped by no MCP tool, and `list_tables().sidecars` omits the three format-0.6
sidecars while `resource://just-dna/tables` names all three.

## The just-dna-lite hand-off

Every dossier carries a `## Blanks for just-dna-lite` section with `path:line` for each read site
that exists and each that does not. That set *is* the hand-off — it turns "annotation is behind the
tables" into a list of individually small asks. `licensing.csv` is the counter-example worth leading
with: it is read properly, with tests, which shows the gap is "nobody asked for the other six" rather
than "the consumer ignores everything".

## Open decisions

- Does `find-evidence` get renamed to `module-evidence`, or stay?
- Does `create-module` survive as a thin index once the stages absorb it?
- Do the stage skills become slash commands (`commands/`), which was the original ask that started
  this? The scaffolds are command-shaped already; nothing has been added to either manifest.
