# Installing a module into just-dna-lite by hand

> **The fallback, not the door.** [`../SKILL.md`](../SKILL.md) drives just-dna-lite through its MCP
> server: `install_module` is route A below with the collision checks done for you, and a job runs,
> validates and reports without a shell. Read this file when that server is not connected and the
> author would rather run commands in the -lite checkout than connect it, or when you need to know
> what the server does underneath.

| Section | What it answers |
|---|---|
| Where the modules live | the registered-modules directory, asked of the code |
| Route A / B / C | copy the compiled bytes / point a source at them / recompile from the spec |
| Which route | a two-column decision |
| What decides whether -lite can see it | the lead table, and the manifest line that hides a module |
| What decides whether it matches anything | position join, rsID fallback, skip |
| Sharp edges | name collisions, symlinks, import-time discovery, env-dropped sources |
| Read the outcome | what `annotate` prints and what each line means |

The consumer is **just-dna-lite** (with its workspace member `just-dna-pipelines`). It is a separate
repository and this plugin does not depend on it — every command below runs *in* that project, so
locate it first and keep it in a variable:

```bash
LITE=/path/to/just-dna-lite      # the checkout that holds pyproject.toml with [tool.uv.workspace]
```

## Where the modules live

Ask the code, never a path in a document — the answer moves with an environment variable:

```bash
uv run --project "$LITE" --no-sync python -c \
  "from just_dna_pipelines.annotation.resources import get_registered_modules_dir as d; print(d())"
```

It resolves as `JUST_DNA_PIPELINES_OUTPUT_DIR/registered_modules` when that variable is set, otherwise
`{workspace}/data/interim/registered_modules`. The workspace root is itself resolved
(`JUST_DNA_PIPELINES_ROOT`, then a walk up for a `pyproject.toml` carrying `[tool.uv.workspace]`), so
**run these commands with the working directory inside the -lite checkout**. If the walk fails, the
writable `modules.yaml` falls back to the copy *inside the installed package* — you would be editing
site-packages and wondering why nothing persisted.

## Route A — the registry's own install path, minus the registry

This is what the web UI does after it downloads a tarball, so it is the best-tested shape. **It does
not recompile, so the `artifact_digest` you got from `compile_module` is the digest that runs.**

```bash
DEST=$(uv run --project "$LITE" --no-sync python -c \
  "from just_dna_pipelines.annotation.resources import get_registered_modules_dir as d; print(d())")

cp -r /path/to/compiled_module "$DEST/my_module_name"          # copy, never symlink — see below

cd "$LITE" && uv run --no-sync python -c "
from pathlib import Path
from just_dna_pipelines.module_registry import register_downloaded_module
print(register_downloaded_module(Path('$DEST/my_module_name')))"
```

`register_downloaded_module` does exactly three things: adds the registered-modules directory to
`sources:` in the writable `modules.yaml` if it is not already there, copies `display.{title,
description, report_title, icon, color}` out of the module's `manifest.json` into `module_metadata`,
and refreshes discovery. It returns the module name.

**There is no CLI for this.** `pipelines module` offers `validate / register / unregister /
list-custom / compile / reverse`, and `register` takes a **spec** directory and recompiles (route C).
The python line above is the gap, and it is filed in their handoff doc rather than worked around
silently.

**Pass it a directory that is already inside the registered-modules dir.** It reads `module_dir.name`
but only ever adds *that* directory as the source, so calling it on a path elsewhere registers display
metadata for something discovery will never scan.

## Route B — leave the module where it is and point at it

Pure configuration, no code. Add the **parent** directory as a source in the writable `modules.yaml`:

```yaml
sources:
- url: /absolute/path/to/the/parent   # the dir that CONTAINS my_module_name/
  kind: collection
```

A `kind: collection` source is listed and each subdirectory probed; a `kind: module` source is the
module itself. Defaults and the working copy are **merged**, not replaced, so adding a source keeps
every source that was already there.

What route B loses is only the display metadata: without `register_downloaded_module`, the title and
description are generated from the directory name instead of read from your manifest.

## Route C — you hold the spec, not the artifact

```bash
cd "$LITE" && uv run pipelines module register /path/to/spec_dir
```

Supported, documented, one command — and it **recompiles**. The `content_signature` will match what
you compiled; the `artifact_digest` will not, because it is a different compile. Use it when you want
-lite's own compile of your spec, not when you want to run the bytes you tested.

**One trap if you take this route:** it copies spec-directory files into the output afterwards and its
suffix list includes `.json`. A `manifest.json` sitting in your spec directory — `registry publish`
stamps one there — is copied **over** the freshly compiled one, leaving a manifest that describes
different bytes. Remove or move a spec-dir `manifest.json` before running it.

## Which route

| you have | you want | route |
|---|---|---|
| a compiled output dir | the exact bytes you tested to be what runs | **A** |
| a compiled output dir you keep re-compiling | no copying, iterate in place | **B** |
| a spec directory only | one command, digest identity does not matter | **C** |

## What decides whether -lite can see it at all

Discovery picks the module's **lead table** — the first match in its `LEAD_TABLES` order, which starts
`weights`, `pharm_variants`, `diplotypes`, … Ask for the live tuple rather than trusting that line:

```bash
uv run --project "$LITE" --no-sync python -c \
  "from just_dna_pipelines.module_config import LEAD_TABLES; print(LEAD_TABLES)"
```

**When a readable `manifest.json` is present, the answer comes from `artifact.files` and the filesystem
is not consulted.** A manifest whose attested file list omits your lead parquet makes the module
**invisible**, and the failure is quiet in the worst way: `pipelines module list-custom` probes the
filesystem directly and will still list it, so the two surfaces disagree and neither says why. No
manifest at all is *safer* than a partial one — that falls back to probing.

Measured on 2026-08-21 against `assets/fto_bmi` compiled by `compile_module`: the manifest attests
`annotations.parquet`, `sources.parquet`, `studies.parquet`, `weights.parquet`, discovery found the
module with `lead = weights`, and `read_module_provenance` returned the version and artifact digest off
the manifest. **A module this plugin compiles is discoverable as-is** — the hazard is a manifest that
came from somewhere else, or a directory assembled by hand.

Also measured, because it looks alarming and is not: a locally compiled `manifest.json` carries
`identity.namespace: null` and `identity.canonical_id: null`, since the registry is what fills those.
Local discovery keys on the **directory name** and never reads either, so nothing here needs a
namespace.

## What decides whether it matches anything

The lead parquet's own schema, at annotation time: a non-null `chrom` gives a join by position,
otherwise `rsid` + `genotype`, otherwise the module is **skipped** and the run still succeeds. A module
whose coordinates were never resolved therefore downgrades silently to an rsID join, and against a VCF
with no rsIDs — which is most WGS callers' output — it matches nothing while reporting success.

That is [`module-enrich`](../../module-enrich/GUIDE.md)'s stage (resolve before you install), and the three-valued join contract
underneath it belongs to [`module-consumer`](../../module-consumer/GUIDE.md). Neither is restated here.

## Sharp edges

- **Name collisions are silent, and you lose.** Discovery takes the **earliest** source that supplies a
  name, and the published HuggingFace collection is the first source in the shipped `modules.yaml`
  while the local directory is *appended*. Naming your module after one of theirs shadows yours with no
  warning at all. Run `uv run pipelines list-modules` **before** choosing the directory name and pick
  something absent from it.
- **Copy, never symlink.** `pipelines module unregister <name>` does a recursive delete of the
  directory, which through a symlink deletes the original.
- **Discovery is import-time state.** A long-running process — the web UI, a Dagster daemon — will not
  see the module until it is refreshed or restarted. The `annotate` CLI imports per invocation and is
  unaffected.
- **Setting `JUST_DNA_PIPELINES_OUTPUT_DIR` drops project-local sources.** With that variable set,
  sources whose URL is an absolute path under the project's own `data/` are filtered out of the loaded
  config. A module placed in a project-relative directory works in a dev checkout and vanishes in a
  containerised run.
- **The registry's own local key is `{namespace}__{name}`.** Avoid that shape for a hand-installed
  module unless you mean to collide with a future registry install of the same thing.

## Read the outcome, not the exit code

```bash
cd "$LITE" && uv run pipelines list-modules        # is it discovered, and from your source?
uv run annotate /path/to/genome.vcf -m my_module_name
```

`annotate` validates `-m` against discovered names and exits with a did-you-mean on an unknown one — so
a name error is loud. Everything after that is quiet:

| what you see | what it means |
|---|---|
| the module in `Skipped` | its lead table supports neither join; nothing ran |
| the module in `Failed` | it raised; **other modules still succeeded and the run still exited 0** |
| `Variants annotated: 0` | it ran and matched nothing — usually the rsID downgrade above |
| a number, and a report | rows joined. **This says nothing about whether they are true.** |
