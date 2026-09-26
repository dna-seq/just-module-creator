---
name: module-install-local
description: >-
  Run a module you compiled against real genomes on this machine through just-dna-lite's MCP server, then read what it did: which variants each genome carries, how the scores are distributed, whether the join worked. Publishes nothing. Also the loop back into curation when the run shows something odd.
  Triggers: "run it on my genome", "try it locally", "try it on these genomes", "apply the module", "test the module", "annotate with my module", "just-dna-lite", "does it actually match anything", "0 variants annotated", "the scores look weird", "none of my genomes have these variants", "my module does not show up", "install without publishing", "local install".
---

# Run a module on real genomes, without publishing it

**Not a lifecycle stage.** It is a side door off stage 6 and, more often than not, the way back into
stage 3. The module compiles; now you want to see it meet genomes, and the author wants to know
whether the variants from the papers are in those genomes at all and whether the scores come out
sensible. Nothing here touches a registry, and nothing here is a prerequisite for `module-publish`.

The consumer is **just-dna-lite**. This plugin does not depend on it and never reads a VCF. The work
happens in just-dna-lite's own MCP server (`just-dna-lite`), which the host runs **next to** this one.
You drive the two servers yourself; neither calls the other.

| | the polygon | production | **this machine** |
|---|---|---|---|
| what it proves | the **registry** seam: naming, namespace, tarball, contract | the same, irreversibly | the **annotation** seam: does this module meet a genome and match anything |
| who else sees it | anyone with the polygon URL | everyone | nobody |
| undo | `registry_delete_version` | a yank, and the content claim never comes back | `uninstall_module` |

These catch **different failures** and neither substitutes for the other.

## 1. Is just-dna-lite connected?

Look for the `just-dna-lite` server's tools in your tool list (`status`, `list_samples`,
`start_annotation`, `validate_module`, …) and call **`status`**. It answers with the checkout's
path, its versions, how many genomes and modules it holds, and any jobs already running. Say which
checkout answered; a machine can hold two.

**If the tools are not there, say so plainly and offer to connect it.** Do not shell into the -lite
checkout on your own initiative. The author runs one of these, then reconnects (`/mcp` in Claude
Code, or restart the session; Cursor picks up `mcp.json` on reload):

```bash
# stdio: works whether or not the app is running
claude mcp add just-dna-lite -- uv run --project /path/to/just-dna-lite python -m just_dna_pipelines.lite_mcp
# HTTP: served by `uv run start` in the -lite checkout, port 3006 by default
claude mcp add --transport http just-dna-lite http://localhost:3006/mcp
```

For Cursor, the same two go under `mcpServers` in `.cursor/mcp.json`: `{"command": "uv", "args":
[...]}` for stdio, `{"url": "http://localhost:3006/mcp"}` for HTTP. The -lite repository's
`docs/MCP_SERVER.md` is the reference. If the author would rather run commands than connect a
server, [`references/MANUAL_INSTALL.md`](references/MANUAL_INSTALL.md) has the three manual routes.

## 2. Offer the run, and let the author choose the genomes

After a green compile, **ask** whether to try the module now. Do not start a run unasked. If the
answer is yes, call `list_samples` and show a short table (sample id, label, size, whether it is
already normalized), and ask which genomes to use. Things worth saying while they choose:

- **Three whole genomes or more** make the distribution checks meaningful; fewer and those checks
  report `not_assessed`. A family is not a population either: related genomes share genotypes, so a
  shared-genotype finding over a family says less than it looks.
- **Exome, panel and tiny test VCFs** get no hom-ref restoration, so a module that authors reference
  genotypes will look emptier on them than it is.
- **A public genome** (the `public_not_downloaded` list, e.g. `anton`, `livia`) makes a run anyone can
  repeat. The worker downloads it on first use, which is hundreds of MB.
- **These are real people's genotypes, and what you read goes to the model provider.** Ask before
  using a genome that is not the author's own, and quote per-genome rows only as far as the question
  needs.

**Never write a sample id, a person's name or anyone's genotype into the module.** Not into a CSV,
not into the README, and not into `record_override`'s reason: `logs/authoring.log` is published with
the module, with no opt-out. Name the *finding* instead ("trial run: called_but_never_matched at
rs1421085 in 3 of 3 genomes").

## 3. Install and run

1. **`install_module(compiled_dir=<compile_module's output dir>, name=<name>)`.** It copies the bytes
   and does not recompile, so the `digest` it returns should equal the one `compile_module` gave you;
   say so if it does not. It refuses a name another source already supplies (discovery would silently
   keep theirs) and refuses to overwrite a registry install. **Keep the same name across iterations**:
   a re-install replaces the previous one. Read its `warnings`: `discovered: false` means the module
   is invisible, and `rows_without_coordinates` means those rows can only join a VCF that carries
   rsIDs.
2. **`start_annotation(samples=[...], modules=[<name>])`.** Add a published module with a comparable
   subject if the author wants a baseline for scale. It returns a `job_id` at once; the job runs in its
   own process and outlives this session.
3. **`wait_for_job(job_id)`.** In Claude Code a call still running after two minutes moves to a
   background task and you are told when it settles; elsewhere, poll `get_job`. A genome's first run
   normalizes it (a minute or more for a whole genome); later runs reuse that and take seconds per
   genome. Jobs queue one after another, so tell the author if something is already running.

Runs write into each sample's normal output directory, as a web-UI run does: the latest run is what
the -lite UI shows for that genome, and each run leaves a timestamped HTML report. Say that once, the
first time.

## 4. Read what it did

`get_results(job_id)` gives each genome's status, the report path, and per module whether it
annotated, was skipped or failed, with rows matched and restored. **A skipped or failed module inside
a successful job is the most common quiet outcome**; its reason is verbatim, so read it out.

`validate_module(job_id, module)` is the reading the author asked for. Every finding names the
threshold that fired, and `not_assessed` means the check could not run, **never that it passed**.
Where each finding goes:

| Finding | What it usually means | Where the decision is made |
|---|---|---|
| `loci_never_observed` | no genome here carries a call at that locus: often a rare variant, or hom-ref in a variant-only VCF the module has no reference row for | **the author's**: keep it, author the hom-ref genotype, or add genomes that carry it. Not a defect by itself. |
| `called_but_never_matched` | genomes are called there, but with a genotype the module never authored: a missing row, a strand or allele-orientation mistake, an effect allele that is really the other one | [`module-curate`](../module-curate/GUIDE.md); compare `observed_unmatched_genotypes` with `authored_genotypes`, then `lookup_variant` |
| `reference_allele_mismatch` | the genome's ref at that position is not the module's `ref`: a wrong coordinate, a GRCh37 position, a different indel spelling | [`module-enrich`](../module-enrich/GUIDE.md) and `lookup_variant` |
| `rsid_join_only`, `rows_without_coordinates` | coordinates never resolved | [`module-enrich`](../module-enrich/GUIDE.md) |
| `constant_score`, `one_sided_scores`, `weight_shared_by_all_genomes`, `dominated_by_one_variant`, `weight_outliers` | the shape of the score, not whether any one row is right | [`module-weights`](../module-weights/GUIDE.md) |
| `score_carried_by_inferred_rows` | the score comes mostly from reference genotypes inferred from an *absent* call | [`module-weights`](../module-weights/GUIDE.md); whether a hom-ref row should carry weight at all |
| `phased_rows_unmatchable`, `ambiguous_positions` | the join cannot use those rows as written | [`module-consumer`](../module-consumer/GUIDE.md) |
| `module_skipped`, `module_failed` | the engine did not read the module on that genome | the reason text; [`module-consumer`](../module-consumer/GUIDE.md) for the join contract |

`loci_preview` lists the loci most worth a look. `get_variant_rows(job_id, module,
coverage_status=...)` pulls the (genome, locus) rows behind any status; without `coverage_status` it
returns each genome's matched rows with genotype and weight. Ask for what the question needs.

## 5. Iterate

A trial run is **a reading, not a defect report**, and the editing discipline is the owning stage's:

1. Take each finding to the stage the table above names. Genotype, weight, direction and conclusion
   are pilot cells: propose, and let the author settle them.
2. Every edit goes through `record_override`, with the finding code as the reason and no sample data.
3. `validate_module(strict)` → `compile_module` → `install_module` with the **same name** →
   `start_annotation` on the **same genomes**, so two jobs compare like with like.
4. Put the two `validate_module` results side by side (score statistics, finding codes, coverage
   totals) and say what moved. Stop when the author says so. A clean validation is not a finish line.

## 6. Clean up

`uninstall_module(name)` removes the trial install when the author is done with it. The runs' outputs
and reports stay in the sample directories, as a web-UI run's would.

## A green run is not evidence the module is right

just-dna-lite verifies nothing on the way in (`verify_manifest` is called nowhere there), and a run
that matched rows says that polars could read the parquet and some rows joined, not that the
conclusions are true. `validate_module` is a set of heuristics about coverage and distribution shape:
it can say a score is odd, and it cannot say what the right one is. Same rule as a green compile, see
[`module-compile`](../module-compile/GUIDE.md).

## What needs a pilot, and what you may simply fix

**Apply silently:** choosing a non-colliding install name, keeping it across iterations, re-running
on the same genomes, reading findings aloud with their thresholds.

**Put in front of a pilot:** which genomes to use (and whether someone else's may be used), whether
a never-observed locus stays, and above all **any impulse to edit an authored cell because a run
looked wrong**. The discriminator for editing against a source is [`module-curate`](../module-curate/GUIDE.md)'s, and a run
over five genomes is weaker evidence than the paper the row came from.

## What this cannot do

- **It does not publish.** Nobody else can install this; `module-publish` is the other door.
- **It does not score PRS.** The -lite server runs annotation modules only.
- **It does not compare versions of the module itself.** [`module-diff`](../module-diff/GUIDE.md) reads what moved in the
  artifact; this compares what moved in the *results*.
- **No tool in this plugin talks to just-dna-lite.** You call its server's tools; when it is not
  connected, the author connects it or runs [`references/MANUAL_INSTALL.md`](references/MANUAL_INSTALL.md) by hand.

## Symptoms

For compiler, enricher and registry messages, see
[`../module-101/references/SYMPTOMS.md`](../module-101/references/SYMPTOMS.md). just-dna-lite's own
messages come back as tool errors naming the cause and the fix; its `get_job` log tail is the next
place to look.

## Where to go next

- The module is not compiled yet → [`module-compile`](../module-compile/GUIDE.md).
- A finding names a cell → [`module-curate`](../module-curate/GUIDE.md), [`module-weights`](../module-weights/GUIDE.md) or [`module-enrich`](../module-enrich/GUIDE.md), per the table above.
- It should be in a catalog after all → `module-publish`.
- What a consumer can and cannot tell you → [`module-consumer`](../module-consumer/GUIDE.md).
