---
name: create-module
description: >-
  Make a just-dna annotation module — from nothing, from sources somebody handed you, from a source that publishes rows, or from a module that already exists. Routes to the stage that owns the work and names the tools it calls; it holds no procedure itself.
  Triggers: "make a module", "create a module", "build an annotation module", "I have some papers", "start a module", "where do I begin", "turn this into a module", "add a gene panel", "/create-module", "what does this plugin do", "explain modules", "module overview", "getting started", "what are the four packages", "i have a zip", "triage these sources", "which tables do i need".
---

# Making a module — the route, not the procedure

**This file routes and stops.** It answers *where do I enter, and what runs next*; every column value,
every warning phrase and every judgement call lives in the stage skill that owns it. If you find
yourself deciding a cell from this file, load the stage skill instead — or ask the tool.

For what a module *is*, what this plugin cannot do, and the framings that work on a beginner, load
[`module-101`](../module-101/GUIDE.md). You do not need it to follow this route — **but you do need it
the moment the person is the one asking**, because that file is written to be explained *from*, not
just read.

## Step 0 — work out where the author is actually standing

Ask before routing. The answer decides which arrow you enter on, and it is almost never step 0.

| What they brought | Enter at | Load first |
|---|---|---|
| a trait or a gene, and nothing else | 0 origin | [`module-start`](../module-start/GUIDE.md) |
| a theme plus sources — PDFs, links, a podcast, a video | 0 origin | [`module-start`](../module-start/GUIDE.md) (triage is yours, not theirs) |
| a zip or a spec directory from an outside session | triage, then read the disk | [`module-start`](../module-start/GUIDE.md), then `module-status` |
| a spec directory whose state nobody knows | a reading, not a stage | `module-status` |
| a module that exists and something moved | 10 feedback | `module-revise` |
| a module that exists **in the catalog**, with nothing on your disk | fetch it, then read it | `registry_download` (essentials, verifies as it fetches), then `module-status` |
| "the whole of gene X as ClinVar has it" | 1 then 2 | [`module-start`](../module-start/GUIDE.md), then [`module-draft`](../module-draft/GUIDE.md) |
| a message they do not recognise | not a stage at all | `module-symptom` |
| **a question rather than a task**, or a wish in their own words with none of this vocabulary in it | nowhere yet | [`module-101`](../module-101/GUIDE.md), and answer them from it before routing |

### Check the ask against the sources before you author anything

**A source that makes no claim about the module's subject contributes no rows. Say so; do not pad.**
The failure to avoid is silent subversion: an ask that the sources cannot support, formally satisfied
by authoring whatever identifiers the papers happen to name. That produces a module that looks
complete, passes every check, and asserts something none of its sources says. **Nothing downstream can
detect it** — the rows are well-formed, the quotes are verbatim, the compile is green.

So triage the ask first, one source at a time, and ask of each: *does this source make a claim about
the thing being asked for?* Where it does not:

- **author no rows from it**, and
- **report it** — name the source, say what it does claim, and hand the decision back. An author who
  learns a paper does not support their ask can supply a different paper, widen the ask, or accept a
  smaller module. None of those is your call to make silently.
- A module with fewer rows and an honest report beats a fuller one that padded. **Zero rows is a
  legitimate outcome** and it is a finding, not a failure — it is `module-status`' decision list, one
  stage earlier.

**Do not narrow the subject while you do it, which is the opposite error and just as easy.** A module
about a trait covers that trait in **both directions**: a variant that worsens the outcome belongs
beside one that improves it, and a subject named by a desirable word does not restrict the module to
the desirable half. The test is only whether the source makes a claim about the subject — never
whether the claim is favourable, and never whether the effect points the way the name suggests.

Two more distinctions worth holding here, because both look like a mismatch and neither is one: a
source may support the subject with a *different* table kind than expected ([`module-tables`](../module-tables/GUIDE.md) decides that,
not this step), and a source may support it weakly rather than not at all — a claim with no comparison
group or no test still says something, and belongs with its limits written into the row rather than
being dropped. Drop a source only where the claim is genuinely absent.

**When two rows apply, the later one wins.** Almost every real session is a second pass, and a second
pass entered as a first one re-derives work that is already on disk and overwrites judgements nobody
recorded. Ask whether the directory has been here before.

**Nobody arrives with a table kind chosen.** They arrive with a finding. [`module-tables`](../module-tables/GUIDE.md) is the router
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
| 0 origin | is there a module here, who else has built one, may its sources be redistributed | [`module-start`](../module-start/GUIDE.md) | `registry_search`, `list_tables` |
| 1 scaffold | which tables, which build, what the weights will mean | [`module-start`](../module-start/GUIDE.md) | `scaffold_module`, `describe_table`, `table_requirements`, `get_template` |
| 2 draft | which of the rows a source already publishes are worth carrying | [`module-draft`](../module-draft/GUIDE.md) | `draft_from_clinvar`; `draft_from_cpic`, `draft_from_clinpgx` (a corpus sizes those two) |
| 3 curate | **the cells only a pilot can settle** — genotype, weight, state, direction, conclusion | [`module-curate`](../module-curate/GUIDE.md) | `lint_rows`, `lookup_variant`, `record_override`; [`module-weights`](../module-weights/GUIDE.md) for the one column no tool fills |
| 3′ evidence | which paper stands behind each claim, what may honestly be quoted, **and how to reach the supplementary table the numbers are actually in** | [`find-evidence`](../find-evidence/SKILL.md) — **load it; the tool list beside it is not a substitute** | `literature_search`, `lookup_citation`, `lookup_open_access`, `fetch_fulltext`, and for the tables the body does not print, `list_supplementary`, `fetch_supplementary`, `describe_supplementary` ([`SUPPLEMENTARY.md`](../find-evidence/references/SUPPLEMENTARY.md)) |
| 4 enrich | nothing — you read the report. It is the only tier that can catch an off-by-one | [`module-enrich`](../module-enrich/GUIDE.md) | `enrich_module`, `refresh_sidecar` |
| 5 cross-check | what to do about each disagreement, one by one | [`module-check`](../module-check/GUIDE.md) | `check_identifiers`, `lookup_identifier`, `review_queue`; `enrich_facts` |
| 6 compile | whether the build's warnings are acceptable — `--strict` is determinism, not correctness | [`module-compile`](../module-compile/GUIDE.md) | `validate_module`, `compile_module`, `module_signature`, `verify_artifact` |
| 6b close | that these bytes are final, and how the module was made | [`module-close`](../module-close/GUIDE.md) | `close_module` |
| 7 rehearse | nothing irreversible. This is where mistakes are supposed to happen | `module-publish` | `registry_check`, `registry_validate`, `registry_publish(target="test")` |
| 8 publish | **the immutable one.** Only on an explicit ask for the official catalog | `module-publish` | `registry_register` → `registry_whoami` → `registry_claim_namespace` → `registry_publish` |
| 9 join | how a consumer will read what you wrote — decided long before this step | [`module-consumer`](../module-consumer/GUIDE.md), `module-install-local` | none here; `just-dna-lite` runs it |

**One surface, no tiers.** Every tool named above is registered, always — the `extended` tier went
in 0.21.0. A few tools are expensive because a corpus sizes their work rather than your rows, and
each says so in its own description; [`module-101`](../module-101/GUIDE.md) carries the whole roster and which those are. What
still gates is a **token**, and only for registry writes.

## The three re-entries, which are the normal case

| You are | Load | Because |
|---|---|---|
| opening a module again — second pass or twenty-fifth | `module-revise` | which kind of pass it is decides what it invalidates. There is **no versioning contract**: `2.0.0` does not mean reviewed and no agent may withhold a publish waiting for a milestone that does not exist |
| re-running something that already ran | [`module-refresh`](../module-refresh/GUIDE.md) | every sidecar merges rather than clobbers, so a plain re-run refreshes **nothing** and says so quietly |
| asking what actually moved | [`module-diff`](../module-diff/GUIDE.md) | and one reading there is the only way to detect an upstream source revising its answer |

## What does not change, whichever arrow you entered on

Four rules the tools enforce rather than merely document. [`module-101`](../module-101/GUIDE.md) states them in full and
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
| what a module is, the four packages, the whole tool roster — **and the words to explain any of it to the person in front of you** | [`module-101`](../module-101/GUIDE.md) |
| which table a finding belongs in, and where every file sits | [`module-tables`](../module-tables/GUIDE.md) |
| a message you do not recognise | `module-symptom` |
| run the finished module on a genome here, publishing nothing | `module-install-local` |
