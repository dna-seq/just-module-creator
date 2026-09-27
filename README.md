# just-module-creator

You bring a question and a paper. An assistant in Claude Code or Codex reads the evidence, writes the claims, checks them, and builds a [just-dna](https://module-registry.just-dna.life) module other people can install.

You do not need a genetics degree, and you do not need to write code.

The thing you are making is a **rulebook**: *if the DNA says this at that spot, the claim is that, and here is the paper.* Reading someone's genome file is a different job. This plugin writes the rulebook. [just-dna-lite](https://github.com/dna-seq/just-dna-lite) is what runs it, and only if you ask.

## What a row is

| | |
|---|---|
| **A variant is a street address** | `rs1421085` names one spot where people differ |
| **A genotype is which letters you have there** | `C/C`, `C/T`, `T/T` |
| **Every row is a claim with a receipt** | the conclusion is the claim, the paper is the receipt |
| **A blank cell means "we don't know"** | never a quiet "no" |

Some topics are one spot per row. Others are a combination. A blood group is the familiar combination: several spots, one plain result ("you have blood group AB"). APOE type and some drug-response classes are the same shape. Say which kind you want. The report can lead with the result in a sentence, and keep the identifiers for a professional reader.

## Install

This repository is its own marketplace. You do not need a second catalog to get the plugin.

### Claude Code

From GitHub:

```text
/plugin marketplace add dna-seq/just-module-creator
/plugin install just-module-creator@just-dna
```

From a checkout you already have, the same two lines with `.` in place of the GitHub name. One session, without installing: `claude --plugin-dir /path/to/just-module-creator`.

### Codex

```bash
codex plugin marketplace add dna-seq/just-module-creator
codex plugin add just-module-creator@just-dna
```

Every skill shows up in Codex's skill picker and runs as a slash command under its own name. Codex starts the plugin from its installed folder.

Needs [`uv`](https://docs.astral.sh/uv/) on your PATH and Python 3.13 or newer. Dependencies install themselves the first time the plugin starts. You only need an account when you decide to publish.

<details>
<summary><strong>If the first launch times out</strong></summary>

Expected once, on a cold install. `uv` builds the environment the first time, and a host that allows about 30 seconds for a server to come up can lose that race. Reconnect. The second start is a few seconds.

Codex allows 300 seconds for this first start, so it is mostly a Claude Code issue.

Or warm it yourself right after installing:

```bash
uv sync --project ~/.claude/plugins/cache/dna-seq/just-module-creator/<version>
```

`MCP_TIMEOUT=120000 claude` raises the limit from Claude Code's own environment. The plugin manifest cannot set that for you.

</details>

## How a module gets made

Say what you want, in your own words: *"make me a module about caffeine metabolism from this paper."*

1. It opens a folder for the module.
2. If a public source already publishes the rows, it can draft from that.
3. It decides what survives, what each genotype means, and which paper backs it. This is the real work.
4. It looks up where each variant sits, and records where the coordinate came from.
5. It checks what was written against what the sources say.
6. It compiles the folder into a file with a fingerprint.
7. Publishing waits for you.

Four habits the tools hold you to:

- A lookup shows you a value. It does not paste that value in, because a later check compares what you wrote with the same source.
- A check that could not run stays unknown. Nothing here turns a failed lookup into a zero.
- A quote is a sentence someone found in the paper. The assistant can be that someone: it fetches the article, reads it, quotes it word for word, and the row records who found it. Pasting the article's title passes every automatic check and proves nothing.
- A source that lists seven variants often supports one. The rest get dropped. [`assets/fto_bmi`](./assets/fto_bmi) is a real case: six of seven rows were dropped, and the README there says why.

<details>
<summary><strong>The FTO example, command by command</strong></summary>

One variant, one paper: **rs1421085 in FTO**, from the 2015 study that took apart the FTO obesity locus (PMID `26287746`). The finished module is [`assets/fto_bmi`](./assets/fto_bmi).

Start the folder. `studies.csv` comes along because a claim without a paper is not a claim.

```text
scaffold_module(spec_dir="fto_bmi", name="fto_bmi", kinds=["variants.csv", "studies.csv"])
```

Find the paper with `literature_search`, which returns titles, so you can see that a PMID is the article you meant. A half-remembered PMID is usually a real paper about something else.

Three rows, because a two-letter address has three genotypes:

```csv
rsid,gene,genotype,state,direction,effect_allele,weight,phenotype,conclusion
rs1421085,FTO,C/C,risk,risk,C,-0.5,Body mass index / adiposity,Two copies of the FTO obesity-associated C allele…
rs1421085,FTO,C/T,risk,risk,C,-0.25,Body mass index / adiposity,One copy…
rs1421085,FTO,T/T,neutral,neutral,C,0.0,Body mass index / adiposity,No copy…
```

No chromosome and no position in those rows. You do not paste a coordinate you looked up yourself. `enrich_module` does that, writes `resolution.csv`, and is what catches a variant whose position quietly shifted.

`validate_module` then `compile_module` turn the folder into a build. A green compile means the module rebuilds the same way. It has no opinion on whether the biology is right. Read the warnings. `audit_module` asks the other question: what a person still has to decide, such as what the `weight` column means.

`close_module` is you saying these bytes are finished. Edit an authored file afterwards and the module is open again.

</details>

## Try it on a real genome

Optional. The module is finished, as a module, when it compiles.

If you want to see what it says about genomes on your machine, say so. The assistant can connect [just-dna-lite](https://github.com/dna-seq/just-dna-lite) and will ask which files to use. It can tell you which of the module's variants those genomes carry, which variants from the papers none of them has, and whether the scores come out lopsided. Then you fix what you agree to fix, and run the same files again. Nothing is published along the way.

The assistant reads the results you ask it to look at, and those results go to whichever model provider is running the chat. Use genomes you are allowed to share with it.

<details>
<summary><strong>Connect just-dna-lite yourself</strong></summary>

The assistant can register the server once you have said you want a run, and once you have pointed it at a checkout (it can clone [just-dna-lite](https://github.com/dna-seq/just-dna-lite) if you agree). If you would rather add it by hand, in Claude Code:

```bash
claude mcp add -s user just-dna-lite -- uv run --project /path/to/just-dna-lite python -m just_dna_pipelines.lite_mcp
```

Reconnect the session afterwards. Clients load a new server's tools at start. The steps, including Codex and Cursor, are in [`/module-install-local`](./skills/module-install-local/SKILL.md).

</details>

## Publishing

There are two catalogs. The **polygon** is a rehearsal you can delete. **Production** is what other people install, and a version there stays. Start on the polygon. An assistant should ask you before it touches production.

Publishing a module an assistant wrote is ordinary. Record who wrote it and who reviewed it, and let a reader judge from that.

<details>
<summary><strong>The publish commands</strong></summary>

```text
registry_register(account="my-name")
registry_claim_namespace("my-ns")
registry_check(target="test")
registry_publish(target="test")
registry_publish(target="prod")
```

`registry_check` asks whether a publish would succeed. It spends no version.

</details>

## Where to go next

| | |
|---|---|
| [`/create-module`](./skills/create-module/SKILL.md) | make one, from a paper, from a source, or from a module you already have |
| [`/find-evidence`](./skills/find-evidence/SKILL.md) | find the papers behind a row, and quote them honestly |
| [What more can be done](./docs/BEYOND_BASICS.md) | drug response, scores, repeat counts, learning from modules already published |

<details>
<summary><strong>For contributors</strong></summary>

The product is the tools and the skills, not a library people import. [docs/FOR_DEVELOPERS.md](./docs/FOR_DEVELOPERS.md) covers running the server on its own, auth, and configuration. [docs/DOMAIN.md](./docs/DOMAIN.md) is what a module is and which mistakes the tools exist to prevent. [`skills/module-101`](./skills/module-101/GUIDE.md) is the map an agent reads. House rules for working *on* this repo are in [`CLAUDE.md`](./CLAUDE.md).

```bash
uv sync
uv run pytest
uv run ruff check .
```

</details>

## License

MIT. See [LICENSE](./LICENSE).
