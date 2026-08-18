# just-module-creator

A **Claude Code and Codex plugin** that writes [just-dna](https://module-registry.just-dna.life) annotation
modules with you. You bring a topic and some sources — a paper, a PDF, a lecture. The agent does the
rest: reads the evidence, writes the rows, checks them, compiles the module and publishes it.

You do not need to be a geneticist, and you do not need to write code.

## What a module is, in 30 seconds

**A module is a rulebook**: *if the DNA says X at spot Y, that means Z, and here is who showed it.*

| | |
|---|---|
| **A variant is a street address** | `rs1421085` names one specific spot where people differ |
| **Your genotype is which letters you have there** | `C/C`, `C/T`, `T/T` |
| **Every row is a claim with a receipt** | the conclusion is the claim, the paper's PMID is the receipt |
| **A blank cell means "we don't know"** | never "no" |

There are two separate jobs: **writing the rulebook**, and **reading somebody's DNA file against
it**. This tool only does the first. It never opens a genome, never calls a genotype, and gives no
medical advice — whoever runs the module later brings the measurement.

## Install

### Claude Code

```bash
/plugin marketplace add /path/to/just-module-creator
/plugin install just-module-creator@just-dna
```

Or for a single session, straight from a checkout: `claude --plugin-dir /path/to/just-module-creator`

### Codex

Add the DNA Seq marketplace, install the plugin, then start a new task:

```bash
codex plugin marketplace add dna-seq/dna-seq-claude-marketplace
codex plugin add just-module-creator@dna-seq
```

The `create-module` and `find-evidence` skills appear in Codex's skill and slash-command picker.
The Codex package uses `${PLUGIN_ROOT}` to start the same source checkout as the Claude plugin.

Needs [`uv`](https://docs.astral.sh/uv/) on PATH and Python ≥ 3.13; dependencies install on first
use. Nothing else to configure — you only need an account when you decide to publish.

## How a module gets made

Just say what you want: *"make me a module about FTO and body weight from this paper"*. The agent
follows this order.

| | Step | Who decides |
|---|---|---|
| 1 | **Start the spec** — a folder with `module_spec.yaml` and a stub CSV per table | agent |
| 2 | **Draft** from a source that already publishes the data, if one does | agent |
| 3 | **Curate** — what survives, what each genotype means, which paper backs it | **agent, and it is the real work** |
| 4 | **Enrich** — look each variant up and fill in its coordinates, recording where they came from | agent (the one step that needs the network) |
| 5 | **Check** — what you wrote against what the sources actually say | agent |
| 6 | **Compile** — the folder becomes a data file with a fingerprint | agent |
| 7 | **Rehearse**, then **publish** | **you**, for the production catalog |

Step 3 is where a module is won or lost. Four rules the tools enforce rather than merely suggest:

- **Look-ups report, they never fill a cell in.** A later check compares what you wrote against the
  same source. If the source filled it in, the check compares that source with itself and always
  agrees. Those refusals are the feature.
- **Unknown is not "no".** A check that could not run is not a check that passed, and nothing here
  quietly turns a failed lookup into a zero.
- **Nobody quotes a paper they did not read.** There are two columns that mean *a person read this
  article and found the sentence*. No tool will fill them from a document it fetched for you.
- **Drop what you cannot support.** A source that lists seven variants often supports one. See
  `assets/fto_bmi/README.md` for a real case where six of seven were dropped, and why.

## A worked example you can run

One variant, one paper: **rs1421085 in FTO**, from the 2015 study that dissected the FTO obesity
locus (PMID `26287746`). The finished module is committed at [`assets/fto_bmi`](./assets/fto_bmi).

**1 — start the spec.**

```
scaffold_module(spec_dir="fto_bmi", name="fto_bmi", kinds=["variants.csv", "studies.csv"])
```

You get `module_spec.yaml`, `variants.csv` and `studies.csv`, with `<<REPLACE>>` wherever a decision
is owed. `studies.csv` comes along because a variant claim without a receipt is not a claim.

**2 — find the evidence, and read it.** `literature_search` returns papers *with titles*, so you can
confirm a PMID names the paper you meant. Never take a PMID from memory: they are dense enough that
a half-remembered one is usually a real record for a different paper.

**3 — write the rows.** One row per genotype — three, because there are three ways to carry a
two-letter address:

```csv
rsid,gene,genotype,state,direction,effect_allele,weight,phenotype,conclusion
rs1421085,FTO,C/C,risk,risk,C,-0.5,Body mass index / adiposity,Two copies of the FTO obesity-associated C allele…
rs1421085,FTO,C/T,risk,risk,C,-0.25,Body mass index / adiposity,One copy…
rs1421085,FTO,T/T,neutral,neutral,C,0.0,Body mass index / adiposity,No copy…
```

`lint_rows` checks that text before it is even saved, and tells you which cells it is deliberately
leaving to you:

```
errors: 0, warnings: 0
info  chrom — left to the author on purpose: a later check compares it against a source,
      and filling it from that same source would make the check vacuous
info  start, ref, alts, clin_sig, acmg_sf — same reason
```

Note what is **not** in those rows: no chromosome, no position. You never paste coordinates you
looked up yourself. That is step 4's job, and it is what makes the cross-check mean something.

**4 — enrich.** `enrich_module` resolves the rsID to a coordinate and writes `resolution.csv`,
recording the source it came from. It is the only thing that catches a variant whose position
silently shifted. Delete `resolution.csv` from the committed example to watch it run.

**5 and 6 — validate, then compile.**

```
validate_module(spec_dir="assets/fto_bmi", strict=True)
→ valid: true, 0 errors, 0 warnings

compile_module(spec_dir="assets/fto_bmi", output_dir="out", strict=True)
→ sha256:c3d633f06c216440892ca571e2b88e6e2b7734cbffd0ac76991bbd7e8071aa09
```

That digest is reproducible: compiling the untouched folder gives the same one every time, on any
machine, and the registry's own server recomputes it independently on publish. It is reproducible
**under one compiler version** — upgrading the compiler moves it on purpose, which is why this line
changed when the toolchain went to format 0.6. What does *not* move is `content_signature`, the
identity of the authored rows; that is the one to compare across an upgrade.

`strict` means **reproducible**, not **correct**. A green compile says the module rebuilds
identically; it has no opinion on whether the biology is right. Read the warnings on a green run —
they are the interesting output.

**7 — say you are finished.** `close_module` writes the one thing no check can write for you: that a
person considers this module done, bound to the exact bytes of the files as they stand.

```
close_module(spec_dir="assets/fto_bmi", closed_by="your-name")
→ closed: true
```

Edit any authored file afterwards and the binding moves, the closure is dropped, and the module is
open again — that is the feature. Compiling without one is a warning, not a refusal, so an
unfinished module stays compilable and simply says it is unfinished.

## Publishing

The catalog comes in two instances: a **polygon**, where a publish is a rehearsal you can delete
again, and **production**, which is what people install from. They share no database.

```
registry_register(account="my-name")      # self-service — no admin, no email, no approval
registry_claim_namespace("my-ns")
registry_check(target="test")             # would this publish? costs nothing, spends no version
registry_publish(target="test")           # rehearse
registry_publish(target="prod")           # promote, once you are happy
```

**Rehearse first.** A production version is immutable: it cannot be edited, and the claim on your
rows outlives even a withdrawal. Publishing to the polygon is the default everywhere for that
reason, and an agent should ask you explicitly before touching production.

Publishing an AI-written module is normal, not a shortcut. The bar is *honest, checked and
declared* — record who wrote and who reviewed it in `authorship:`, and let a reader judge from
that.

## Where to go next

| | |
|---|---|
| [**What more can be done**](./docs/BEYOND_BASICS.md) | drug response and star alleles, polygenic scores, repeat counts and other measured quantities, digging into replication, learning from published modules |
| [**For developers**](./docs/FOR_DEVELOPERS.md) | running the server standalone, the full tool list, modes, auth, configuration, deployment |
| [`skills/create-module`](./skills/create-module/SKILL.md) | the authoring procedure in full — the agent reads this |
| [`skills/find-evidence`](./skills/find-evidence/SKILL.md) | finding, verifying and legally reusing the literature |
| [`docs/DOMAIN.md`](./docs/DOMAIN.md) | what a just-dna module is, and the traps that shaped these tools |
| [`CLAUDE.md`](./CLAUDE.md) | house rules for agents working *on* this repo |

## License

MIT — see [LICENSE](./LICENSE).
