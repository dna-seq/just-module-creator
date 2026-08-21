---
name: create-module
description: >-
  The router for making a just-dna annotation module. Where to enter the lifecycle from wherever the
  author is actually standing — nothing yet, a handed bundle, a source that publishes rows, or a
  module that already exists — the stage order, and which skill and which tools own each step. It is
  not the procedure: every stage skill owns its own and this file only gets you to the right one.
  Load it whenever somebody asks for a module and the starting point is not yet settled.
  Triggers: "create a module", "create-module", "make a module", "build a module", "write a module",
  "author a module", "new module", "how do I create a module", "module for this gene", "module from
  these papers", "walk me through it", "what order", "what do I do next", "which skill do I need",
  "where do I start", "I want to annotate this trait".
---

# Making a module — the route, not the procedure

**This file routes and stops.** It answers *where do I enter, and what runs next*; every column value,
every warning phrase and every judgement call lives in the stage skill that owns it. If you find
yourself deciding a cell from this file, load the stage skill instead — or ask the tool.

For what a module *is*, what this plugin cannot do, and the framings that work on a beginner, load
`module-101` once. You do not need it to follow this route.

## Step 0 — work out where the author is actually standing

Ask before routing. The answer decides which arrow you enter on, and it is almost never step 0.

| What they brought | Enter at | Load first |
|---|---|---|
| a trait or a gene, and nothing else | 0 origin | `module-start` |
| a theme plus sources — PDFs, links, a podcast, a video | 0 origin | `module-start` (triage is yours, not theirs) |
| a zip or a spec directory from an outside session | triage, then read the disk | `module-start`, then `module-status` |
| a spec directory whose state nobody knows | a reading, not a stage | `module-status` |
| a module that exists and something moved | 10 feedback | `module-revise` |
| "the whole of gene X as ClinVar has it" | 1 then 2 | `module-start`, then `module-draft` |
| a message they do not recognise | not a stage at all | `module-symptom` |

**When two rows apply, the later one wins.** Almost every real session is a second pass, and a second
pass entered as a first one re-derives work that is already on disk and overwrites judgements nobody
recorded. Ask whether the directory has been here before.

**Nobody arrives with a table kind chosen.** They arrive with a finding. `module-tables` is the router
for that question and it is read from every stage, not just this one.

## The spine

```
0 origin ─▶ 1 scaffold ─▶ 2 draft ─▶ 3 curate ─▶ 4 enrich ─▶ 5 cross-check ─▶ 6 compile ─▶ 7 rehearse ─▶ 8 publish ─▶ 9 install & join
            (spec dir)    (if a      (only an                (report; you      verify      (polygon)    (immutable)   (consumer)
                           source     author can)             decide)           sign, close
                           has it)                                                                          │
   ┌──────────────────── 10 feedback ◀───────────────────────────────────────────────────────────────────────┘
   └─▶ pass 2+ re-enters at 3 (curate) — usually. Or 2 for a source refresh, 1 to add a table kind,
       6 to rebuild under a newer toolchain. Never at 0: a second pass never starts from nothing.
```

**Steps 4 and 5 are the only ones that fetch.** Once `resolution.csv` and `literature.csv` exist they
*are* the pin, so every later compile is offline and reproducible.

**Curate before you enrich, and the order is load-bearing rather than tidy.** A drafted row leaves
`<<REPLACE>>` where a human must decide, and that placeholder makes every loader refuse the file —
deliberately, since resolution is allele-aware and a placeholder genotype would skip the allele filter
on exactly the rows that need it. You do not have to enrich to see the alleles: the draft report prints
the allele pair, and `lookup_variant` gives you the same for a row you are writing by hand.

## Each stage — what it exists to decide, and what to call

| Stage | The decision it exists for | Skill | The tools |
|---|---|---|---|
| 0 origin | is there a module here, who else has built one, may its sources be redistributed | `module-start` | `registry_search`, `list_tables` |
| 1 scaffold | which tables, which build, what the weights will mean | `module-start` | `scaffold_module`, `describe_table`, `table_requirements`, `get_template` |
| 2 draft | which of the rows a source already publishes are worth carrying | `module-draft` | `draft_from_clinvar`; `draft_from_cpic`, `draft_from_clinpgx` (extended) |
| 3 curate | **the cells only a pilot can settle** — genotype, weight, state, direction, conclusion | `module-curate` | `lint_rows`, `lookup_variant`, `record_override`; `module-weights` for the one column no tool fills |
| 3′ evidence | which paper stands behind each claim, and what may honestly be quoted | `find-evidence` | `literature_search`, `lookup_citation`, `lookup_open_access`, `fetch_fulltext` |
| 4 enrich | nothing — you read the report. It is the only tier that can catch an off-by-one | `module-enrich` | `enrich_module`, `refresh_sidecar` |
| 5 cross-check | what to do about each disagreement, one by one | `module-check` | `check_identifiers`, `lookup_identifier`, `review_queue`; `enrich_facts` (extended) |
| 6 compile | whether the build's warnings are acceptable — `--strict` is determinism, not correctness | `module-compile` | `validate_module`, `compile_module`, `module_signature`, `verify_artifact` |
| 6b close | that these bytes are final, and how the module was made | `module-close` | `close_module` |
| 7 rehearse | nothing irreversible. This is where mistakes are supposed to happen | `module-publish` | `registry_check`, `registry_validate`, `registry_publish(target="test")` |
| 8 publish | **the immutable one.** Only on an explicit ask for the official catalog | `module-publish` | `registry_register` → `registry_whoami` → `registry_claim_namespace` → `registry_publish` |
| 9 join | how a consumer will read what you wrote — decided long before this step | `module-consumer`, `module-install-local` | none here; `just-dna-lite` runs it |

**Tiers, not stages.** Everything above marked *extended* needs `JMC_MODE=extended`; the default tier
runs the spine end to end, scaffold to publish. `module-101` carries the whole roster and the reason
the line is drawn on cost.

## The three re-entries, which are the normal case

| You are | Load | Because |
|---|---|---|
| opening a module again — second pass or twenty-fifth | `module-revise` | which kind of pass it is decides what it invalidates. There is **no versioning contract**: `2.0.0` does not mean reviewed and no agent may withhold a publish waiting for a milestone that does not exist |
| re-running something that already ran | `module-refresh` | every sidecar merges rather than clobbers, so a plain re-run refreshes **nothing** and says so quietly |
| asking what actually moved | `module-diff` | and one reading there is the only way to detect an upstream source revising its answer |

## What does not change, whichever arrow you entered on

Four rules the tools enforce rather than merely document. `module-101` states them in full and
`server.INSTRUCTIONS` is the authority if the two ever disagree.

1. **Ask the tool, never memory** — no column list, vocabulary or requirement is written down in any
   skill, because the generated answer cannot drift from what the compiler accepts.
2. **You may write, and every write is logged.** Two kinds of cell are still withheld: one a later
   check compares against that same source, and one only a pilot can settle.
3. **A mismatch against a source is not a defect report.** Archives lag the edge; conforming a row
   silently can degrade the module and the check will then agree with itself.
4. **A check that could not run is not a check that passed.**

And one about voice, which matters most on a module somebody hands you: **out of date is not broken.**
The output of a revisit is a decision list, not a findings dump — apply the evident and mechanical
silently, and surface only what a human must choose.

## Where to go next

| | Load |
|---|---|
| what a module is, the four packages, the whole tool roster | `module-101` |
| which table a finding belongs in, and where every file sits | `module-tables` |
| a message you do not recognise | `module-symptom` |
| run the finished module on a genome here, publishing nothing | `module-install-local` |
