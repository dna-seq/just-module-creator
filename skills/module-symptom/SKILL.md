---
name: module-symptom
description: >-
  You got a message and do not know what it means. This is the door to the symptom lookup: how to work
  out which layer emitted a message before searching for it, how to match on the part of the text that
  does not vary, what error, warning and info actually cost, why a warning on an otherwise green run is
  the interesting output, and why a check that reports skipped is not a check that passed.
  Triggers: "what does this message mean", "I got an error", "what went wrong", "it says", "unexpected
  warning", "compile failed", "validate failed", "enrich failed", "unreplaced template placeholder",
  "ref mismatch", "why is this a warning", "not run", "skipped", "unverifiable", "is this bad", "can I
  ignore this", "it did not compile", "the registry rejected", "error message", "traceback".
---

# A message you do not recognise

**The lookup is `../module-101/references/SYMPTOMS.md`.** Real message text → cause → action, in five
sections: authoring and loading, resolution and enrichment, validation and compile, the checks, and
this server's own. The first four are the toolchain reporting on your module; the fifth is the plugin
reporting on its configuration, where no edit to the module changes anything. It
sits with the map rather than with a stage because every stage reads from it. Go there first; this file
exists to get you there with the right search string and to tell you how to read what you find.

**Nothing here restates it.** If you want to know what a specific sentence means, open that file.

## Match on the part that does not vary

Messages are quoted as the CLIs print them, and the MCP tools surface the same text: compiler findings
arrive in `validate_module` / `compile_module`'s `errors` and `warnings`, row-level findings in
`lint_rows`'s `findings`, and enrichment findings in `enrich_module`'s own fields.

So search for the **distinctive phrase**, not the line you were given. Strip out everything the message
computed: counts, rsIDs, positions, digests, gene symbols, column names, file paths. What is left —
*"cannot host the authored genotype"*, *"coverage gap"*, *"is not among the resolved alleles"* — is what
the file is keyed on. A search that returns nothing has usually kept a number in it.

## Classify before you look up: which layer said it

The layer tells you which skill owns the fix, whether the network was involved, and whether re-running
can change the answer at all. Four packages plus us, and the tells are reliable:

| Layer | It sounds like | What that means for the fix |
|---|---|---|
| **format** | pydantic's own wording — a model and a field named together, *"Input should be a valid …"*, *"Extra inputs are not permitted"* | the row is wrong, or a column is. Fix the CSV. Ask `describe_table` / `table_requirements` for what the cell may hold rather than guessing |
| **compiler** | a finding with a level and a row, talking about tables, bins, ploidy, vocabularies, spellings, the licence gate or the closure | it read only your module. It can catch two of your rows contradicting each other; it holds no reference, so it can never tell you a coordinate is wrong |
| **enricher** | coordinates, alleles, the reference base, the PAR, VRS ids, a sidecar, or a cross-check against an archive | the only tier that fetches. *"Could not"* here is often the network or a snapshot, not your rows — and a mismatch is a finding, not a defect report |
| **registry** | publishing, namespaces, tokens, versions, a contract or an instance | it arrives from a `registry_*` tool. Ask which `target` you were on before anything else; the two instances share no database |
| **us** | a path outside the workspace, an offline refusal, a missing token, a `target` that was refused, a tool that is not in this tier | a setting, never a row. Nothing in your CSVs will fix it — see SYMPTOMS' *This server* section |

**The one that arrives as silence rather than a message: a tool you are sure exists is simply not
there.** Anything `module-101`'s tool table marks **extended** is absent unless `JMC_MODE=extended`,
and an MCP surface has no *switched off* state — only absence, which is indistinguishable from never
built. Check that table, which marks the tier on every row and says how to widen it, before
concluding the plugin cannot do something. **Reaching for a shell
recipe or a raw HTTP call instead is how you lose what the tool did beyond fetching** — for
`enrich_gwas_effects` that is the sidecar it writes and the licence rows it records on the way.

**Two absences that are not tier absences at all**, and both cost an unattended run its whole task
before they were fixed: `registry_download` and `refresh_sidecar` are in **every** tier. If either is
missing, the server is older than 2026-08-22 rather than narrow, and neither has a shell substitute
worth reaching for — the download verifies the bytes as it fetches, and the refresh captures and
verifies before it deletes anything.

Two consequences worth holding on to. **A message about a coordinate being wrong can only have come
from the enricher**, so if a strict compile is green that is not evidence the coordinates are right.
And **a message that names an `RMn` is a tracked upstream item**: known and deliberate, not broken.
Leave the data honest, say what the limitation is, and do not invent a workaround —
`../just-dna-format/docs/RM_TOC.md` says what any given number is.

## Error, warning, info — three strengths, and only one stops you

**Name the surface before you decide what a message costs.** *Refused*, *checked*, *warned* and
*hinted* are four different strengths, and a hint never fails a build. The same subject can be an error
in one place and a warning in another, which is not an inconsistency: it usually means one surface can
prove the problem and the other can only suspect it.

- **An error blocks.** Something downstream cannot run on the bytes as they stand.
- **A warning does not.** It compiled anyway, and that is exactly why it matters: **the warnings on a
  green run are the interesting output.** A module can pass every offline gate and still be wrong, so a
  warning is often the only place that shows.
- **Info is a record.** It is printed rather than left silent so that a table half the size you expected
  is never a surprise.
- **`--strict` changes what some findings cost, and it is a determinism gate.** It means *reproducible*,
  never *right*. `module-check` names the passes whose strict gate fires on the ordinary answer.

**Aggregate before you report.** Repeated warnings are grouped by *reason* with a count, never one line
per row. A hundred lines of the same finding hides the one that is different.

## The message that is an absence

**A check that could not run is not a check that passed.** `skipped`, `not run`, `unverifiable`, `null`
and `unknown` are their own answer, and none of them collapses into a pass. When you find one:

- **Read the skip reason, not just the fact of the skip.** Two skips of the same check can mean
  opposite things — one saying the comparison would have been vacuous, another saying the source was
  simply not there this run. The lookup's *Checks* section carries that pair worked through.
- **A skip you can clear is worth clearing.** A reachable source, a snapshot nobody built, a pass that
  was run offline: re-run it and the answer stops being silence.
- **Never write a value to tidy a warning away.** A blank cell means *we do not know*, never *no*, and
  filling it to make output green moves the row from honestly unverified to apparently verified, which
  nothing downstream can tell apart.

## When nothing matches

In order, and the first three are cheap:

1. **Read the findings from the top, not the bottom.** A ragged CSV row is reported ahead of the errors
   it causes, and the error it causes names the wrong column. The first finding is usually the real one.
2. **Check `row` against `line`.** Both are correct and they count differently — one indexes data rows,
   the other is the file line an editor shows. Jump to `line`.
3. **Ask the tool.** If the message is about what a cell may contain, `describe_table` /
   `table_requirements` / `authoring_reference` generate the answer from the live models. Nothing in
   any skill reproduces those lists, deliberately.
4. **Then go to the owning stage skill**, from the layer table above. Every stage ends with a short
   symptoms section naming the messages you actually meet there.
5. **A message you had to experiment to understand is a documentation gap**, and it is worth reporting
   to whoever owns the layer that emitted it, with the experiment attached. The next person otherwise
   runs the same experiment.

## Where to go next

| The message is about | Load |
|---|---|
| the full lookup, all four sections | `../module-101/references/SYMPTOMS.md` |
| a placeholder, a stub, or a cell only a pilot can settle | `module-curate` |
| a draft that produced too much, or the wrong rows | `module-draft` |
| coordinates, alleles, the reference base, the PAR, VRS ids | `module-enrich` |
| a cross-check, a skip reason, or an attestation | `module-check` |
| validate disagreeing with compile, bins, ploidy, the licence gate | `module-compile` |
| a closure that vanished, or a module that records none | `module-close` |
| publishing, tokens, namespaces, an instance | `module-publish` |
| a re-run that changed nothing, or a sidecar that stayed stale | `module-refresh` |
| which table a value belongs in, and what its columns are | `module-tables` |
| where you are in the lifecycle, and what has to be decided | `module-status` |
| a CLI flag no tool wraps | `../module-101/references/CLI.md` |
| *"has this already been decided?"* | `../just-dna-format/docs/FAQ.md` — keyed by question, and a refusal is an answer |
