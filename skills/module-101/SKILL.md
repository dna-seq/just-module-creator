---
name: module-101
description: >-
  Start here to understand the thing. What a just-dna annotation module is, what this plugin can and
  cannot do, the tool roster and its tiers, how the four packages fit together, and the corpus of
  worked examples to read before writing one. The map, not the route: `create-module` owns where
  to enter the lifecycle and which stage skill runs next, and `module-tables` owns which table a
  finding belongs in.
  Triggers: "what is a module", "what is just-dna", "what can I do with this", "what does this plugin
  do", "explain modules", "module overview", "getting started", "is this for reading my DNA", "what
  kinds of module", "why does this exist", "what are the four packages", "which tier is this tool in",
  "show me an example module", "which skill do I need", "which tool do I use".
---

# just-dna modules — the overview

**This is the map, not the route.** It exists so you know what you are looking at and what is
possible; `create-module` answers *where do I enter and what runs next*, and each stage skill owns its
own procedure. If you find yourself deciding a column value from this file, you have gone one level too
deep — stop and load the stage skill, or ask the tool.

## What a module is

**A module is a rulebook.** *If the DNA says X at spot Y, that means Z, and here is who showed it.*

Concretely: a directory of authored CSVs plus `module_spec.yaml`, compiled into a set of parquet
files with a content-addressed `manifest.json`. It carries **annotation only** — lookup tables
mapping a genotype, a diplotype or a measured quantity to a phenotype. *What it looks like on disk* —
below — has the real trees for all four shapes you will meet one in.

## What you can do with this plugin

| You want to | This is possible | Owned by |
|---|---|---|
| author a module from a trait and some sources | yes, end to end | `create-module` routes it |
| draft rows from a source that publishes them | ClinVar panels, CPIC star alleles, ClinPGx drug response | `module-draft` |
| find the papers behind a row, and read them | PubMed, Europe PMC, Crossref, preprints, open-access fulltext | `find-evidence` |
| turn rsIDs into coordinates and mint allele ids | yes, and it catches an off-by-one nothing offline can | `module-enrich` |
| check what you asserted against what the sources say | reference base, ClinVar call, PMIDs, identifiers, ACMG SF, gene↔locus | `module-check` |
| record published GWAS effect sizes | yes — **beside** `weight`, never into it | `module-weights` |
| point at a published polygenic score | yes, as a manifest of PGS Catalog ids | `module-weights` |
| build and verify the artifact | yes, reproducibly and offline once resolved | `module-compile` |
| rehearse a publish, then publish | polygon first, then the immutable catalog | `module-publish` |
| **revise a module that already exists** | yes — and this is the common case | `module-revise` |
| read back somebody else's published module | yes | `module-diff` |
| compare two versions row by row | yes, offline, grouped by what changed | `module-diff` |

**What it cannot do, and will not pretend to.** It never opens a VCF, calls a genotype, or gives
medical advice. It does not lift coordinates between assemblies (it recovers the rsID instead). No
tool fills `weight` — that is the author's model of the finding. It does not compute a polygenic
score. And it cannot tell you whether your annotation is medically *correct*: it can only make what
you claimed legible, attributable and checkable.

**One thing worth knowing about a module you did not just compile: `manifest.stats` describes the
whole module only since compiler 0.6.6.** Before that the gene facets came from `variants.csv` alone,
so a PGx, copy-number or activity-bin module published `genes: []` and `registry_search(gene=…)` would
not return it however many rows carried a `gene` cell. A manifest is written at compile time, so a
version published earlier still carries the old numbers — recompiling and publishing again is what
moves them. Never repair it with an empty `variants.csv`. `module-tables` carries the detail.

**`--strict` is not a correctness gate.** It means *reproducible*. The compiler never fetches, so it
holds no reference to check a coordinate against: a module shifted one base passes validate, passes
strict compile, reports `fully_resolved: true`, and mints allele ids the compiler then reports
**verified** — a content-addressed id is a correct digest of whatever it is handed. That is not
hypothetical. Four real modules shipped 3,038 shifted variants through every offline gate because one
docstring said `start` was 0-based; **`start` is always the 1-based VCF position — paste it, never
subtract one.**

## The architecture — four packages, one of which fetches

The dependency arrow points inward: **enricher → compiler → format**, plus the registry beside them.
Most confusion comes from mixing them up.

| Package | Owns | Never |
|---|---|---|
| `just-dna-format` | the schema: models, vocabularies, identity, the hashes, signing | fetches; ships a CLI |
| `just-dna-compiler` | spec → parquet + `manifest.json`; validate, reverse, close, templates, hints | fetches; invents a row |
| `just-dna-enricher` | resolution, VRS ids, the derived sidecars, the drafters, **every cross-check** | decides what a variant *means*; repairs an authored cell |
| `just-dna-registry` | accounts, namespaces, publish, search, download, the module card | authors anything |

Two consequences worth holding on to. **The compiler is inject-only** — it consumes a
`resolution.csv` the enricher produced and will not look a coordinate up for you. And **a check that
needs a reference can only live in the enricher**: the compiler can catch two rows contradicting each
other about a reference base, and only the enricher can catch a row contradicting the genome.

`pip install just-dna-enricher` pulls the compiler and the format tier. Python ≥ 3.13. This plugin
wraps all four as MCP tools; `references/CLI.md` names the few things it deliberately does not wrap.

## The lifecycle

Origin, scaffold, draft, curate, enrich, cross-check, compile, close, rehearse, publish, install — and
a feedback arrow back into the middle of it. **`create-module` holds the diagram**, the entry points
into it, and the tools each stage calls, along with the two ordering rules that matter more than the
order itself and the fact that only enrich and cross-check ever fetch. Load it when the question is
*what runs next*.

**A second pass is the normal state of a module, and it has six shapes** — prose, review, evidence,
data, source refresh, rebuild. They compose, they differ in what they invalidate, and the version
number is *not* how you tell them apart: **there is no versioning contract.** `2.0.0` does not mean
reviewed, a module may sit at `1.0.0` forever and be fine, and no agent may withhold a publish
waiting for a milestone that does not exist. What accumulates trust is what the module *records* —
`authorship` and its `kind`, the checks in `verification.json`, the closure. `module-revise` owns all
of this.

## What it looks like on disk

**A spec directory is flat**: `module_spec.yaml` plus the CSVs you use plus the sidecars the machine
wrote, all side by side, because the compiler reads authored and derived tables from **one directory**.
A compiled artifact is parquets plus `manifest.json` in an `out/` dir you never edit. A module you
download from the registry is the artifact, optionally plus every input — and under one download flag
the machine-written half is re-homed under `derived/`, which is a *presentation* rather than a place a
file lives.

**`module-tables` holds all three trees, file by file**, along with what the registry hoists, renames
and refuses on the way in. Load it when you need to know where something goes.

## A bundle somebody hands you — the common starting point

**This is the common starting point, not the rare one.** An author arrives with a zip from an outside
session — CSVs already written, a README already claiming things. Such a bundle typically carries the
deprecated `sources.csv` spelling, no `verification.json`, no closure, and no coordinates you can
trust. Triage it before extending it; do not assume the previous author's convention.

The worked case is upstream in `../just-dna-format/data/output/corrected_modules/`: five externally
authored modules where **every coordinate in four of them was one base too low**, because the author
converted the GWAS Catalog's position to "0-based" against a docstring that has since been fixed. All
four passed validate, passed `compile --strict`, reported `fully_resolved: true`, and minted allele ids
the compiler reported **verified**. What defeated the cross-check as well is worth knowing: each module
shipped its own hand-built `resolution.csv`, so validate-by-redundancy compared one author's
convention against itself and agreed.

Three lessons for a handed bundle, all of them cheap:

- **The fifth module was immune, and the reason is a design choice you can copy.** `muscle_lean_mass`
  authors **rsIDs only** and carries no coordinates, so the whole class could not touch it. Author the
  rsID and let resolution place it.
- **Delete a stale sidecar rather than re-running over it.** The repair was `start + 1`, then *delete
  each `resolution.csv`* and re-enrich — because an existing sidecar is authoritative and merged, so a
  stale one persists in silence.
- **Fixing coordinates does not make the module reviewed.** That correction left `weight` values
  rank-normalized by the original agent, `direction` unknown on most rows, `conclusion` prose unread,
  and a README asserting allele validation *that had been performed over the shifted coordinates*.
  Say which of those you did and which you did not; a bundle's own README is a claim, not a receipt.

**There are two jobs, and this plugin only does the first: writing the rulebook, and reading a DNA
file against it.** A module never contains a sample, a genotype under test or a measured value. The
consumer brings the measurement at query time. Correct this misconception early and unprompted with a
non-specialist — their working model is usually "point this at my DNA file and tell me about me", and
every later step reads as nonsense against it.

### The framings that landed on a real beginner

Tested in a real session with someone who had never seen a VCF. The conversation changed the moment
"module" became **rulebook** — *"a module is a rulebook, you should've said so!"*

| Say this | It explains |
|---|---|
| **A module is a rulebook.** "If the DNA says X at spot Y, that means Z, and here is who showed it" | what a module *is*. Lead with this one; it does more work than the rest combined |
| **A variant is a street address.** `rs4988235` names one specific spot where people differ | `rsid` |
| **Your genotype is which letters you have at that address** | `genotype` |
| **There are two jobs: writing the rulebook, and reading a DNA file against it. This only writes** | the misconception that wastes the most time |
| **The module is the knowledge; whoever runs it brings the measurement** | why nothing here opens a VCF |
| **Every row is a claim with a receipt.** `conclusion` is the claim, `pmid` is the receipt | why `studies.csv` is required whenever `variants.csv` exists |
| **A blank cell means "we don't know", never "no"** | the three-valued algebra, and why you must not write `false` to tidy a warning |
| **Those two quote columns mean "someone read this paper and found the sentence" — and that someone may be me** | why a quote is verbatim, says who located it, and is never the title |
| **I write it; if you want a specialist to check it, that becomes a later version with their name on it** | who does what, and why they are not being asked to check the genetics |
| **On a dial, a shared endpoint is a boundary; on a counter, it is two bins claiming the same number** | why `measure_tiling` decides whether bins must touch — the measure's kind only sets the default |

**And never let a metaphor decide a column.** "Rulebook" is the right way to *explain* a module and the
wrong basis for choosing a column, a vocabulary member or a table kind. The instant the question is what
a cell may contain, stop explaining and ask `describe_table` / `table_requirements`. A metaphor that
starts answering schema questions has become a second source of truth.

## The tools, and which tier they are in

Prefer these over shelling out: they return structured results, their schema answers are generated from
the live models, and they cannot reach the one compiler flag that silently produces a module no VCF can
match.

| Do this | Tool | Tier |
|---|---|---|
| choose a table kind, learn its columns, its requirements | `list_tables`, `describe_table`, `table_requirements` | essentials |
| the columns of a table a *pass* writes | `describe_machine_table` | essentials |
| a CSV header or a stub | `get_template` | essentials |
| create the spec directory | `scaffold_module` | essentials |
| check rows **before** writing them | `lint_rows` | essentials |
| pre-flight, then build | `validate_module`, `compile_module` | essentials |
| find the alleles for a genotype | `lookup_variant` | essentials |
| **find the papers behind a row** | `literature_search` | essentials |
| check a PMID/DOI and read the title back | `lookup_citation` | essentials |
| where may I read this paper, and read it | `lookup_open_access`, `fetch_fulltext` | essentials |
| draft variants + studies from ClinVar | `draft_from_clinvar` | essentials |
| resolve coordinates, mint ids, catch a ref mismatch | `enrich_module` | essentials |
| identifier currency, **and gene↔chromosome agreement** | `check_identifiers`, `lookup_identifier` | essentials |
| declare the authoring finished | `close_module` | essentials |
| record why an authored value outranks a source, and read the queue back | `record_override`, `review_queue` | essentials |
| compare two spec directories, at three grains | `compare_modules` | essentials |
| content signature, artifact integrity | `module_signature`, `verify_artifact` | essentials |
| the whole generated DSL at once | `authoring_reference` | essentials |
| see whether a module already exists, and read one | `registry_search`, `registry_get_module` | essentials |
| get an account and a token | `registry_register` | **always** |
| draft the PGx tables | `draft_from_cpic`, `draft_from_clinpgx` | extended |
| has this finding been replicated | `paper_citations` | extended |
| fill the fact sidecars | `enrich_facts`, `enrich_literature_pass`, `enrich_gwas_effects` | extended |
| re-derive a sidecar without losing curation | `refresh_sidecar` | extended |
| turn an artifact back into a spec, or download one | `reverse_module`, `registry_download` | extended |
| ask whether it would publish, cost-free | `registry_check`, `registry_validate` | gated |
| publish, or rehearse a publish | `authenticate` → `registry_whoami` → `registry_claim_namespace` → `registry_publish` | gated |

**The default tier runs the whole procedure**, scaffold to publish. The tiers split on **cost**:
essentials is everything bounded by what you named — one identifier, one paper, one spec directory —
and `JMC_MODE=extended` adds only what a *corpus* sizes, plus reading back somebody else's artifact.
`registry_register` is ungated because it is what mints the token; gating it would be a cycle.

**Switching extended on, and the way that looks right and is not.** An MCP surface has no *switched
off* state — a tool in the other tier is simply **absent**, and absence is indistinguishable from
never built, so check this table before telling anyone the plugin cannot do something.

| How the server was started | How to widen it |
|---|---|
| plugin (`/plugin install`, `--plugin-dir`) | edit `JMC_MODE` in `.claude-plugin/plugin.json` — `.codex-plugin/plugin.json` for Codex — then reconnect |
| project MCP server (`.mcp.json` in a checkout) | edit `JMC_MODE` there, then reconnect |
| standalone CLI | `--mode extended`, or `JMC_MODE` in the shell or `.env` |

**Editing `.env` cannot switch a plugin-launched server, and that is the trap.** The manifest exports
`JMC_MODE` into the subprocess, and `.env` is loaded with `override=False`, so a variable that is
already set wins and your edit is read as nothing happening. It is the only setting this bites,
because it is the only one the manifests pin.

**Never substitute a shell recipe or a raw HTTP call for a tool that is merely switched off.** You
lose whatever the tool does beyond fetching — for `registry_download` that is the digest
verification, which is the entire point of it.

**Every registry tool takes a `target`.** Writes default to the polygon; **catalog reads have no
default and refuse to guess** — reading the instance you did not just write to is what makes a fresh
publish look like a broken catalog.
`references/CLI.md` names the few things no tool wraps — signing, the PGx cross-checks,
snapshot building, `hint recover`.


## For the author: the minimal surface

Almost every module you will meet is **three files plus one**:

| File | What it is | Required? |
|---|---|---|
| `module_spec.yaml` | who the module is, which build, what its weights mean | **yes** — the only always-present file |
| `variants.csv` | one row per (variant, genotype), with the conclusion a reader gets | no, but it is the commonest lead table |
| `studies.csv` | the receipt for each claim | **iff `variants.csv` is present** |
| `README.md` | the prose — **and it becomes the catalog card** | no, but a module without one has a blank card |

That is the whole minimal surface. Everything else is optional and additive: **nine** more authored
table kinds for pharmacogenomics, binning and polygenic scores, a licensing ledger, and **eight**
machine-produced sidecars you read but never hand-finish.

**A module includes only the tables it uses — `variants.csv` is not mandatory.** A PGx or binning module
carries no `variants.csv` and therefore no `studies.csv` requirement, which surprises people. **So the
kinds of module you can build are:** a curated variant panel; a gene panel drafted from ClinVar and then
curated; a pharmacogenomics module (star alleles, single-variant drug response, or both); a measurement
module (repeat expansion, copy number, mtDNA heteroplasmy, metabolizer activity, PRS percentile bands); a
pointer module naming published PGS scores; or a mix.

**Which table a finding belongs in, and every column of every one of them, is `module-tables`.** It
routes to an exhaustive dossier per table. Do not decide a table from this file.

### Read one before you start

Sixteen worked modules ship in `../just-dna-format/reference_examples/`, each with a README that says
what it demonstrates and often what it *broke*. Open the one shaped like what you are building.

| If you are building | Read | It is |
|---|---|---|
| a curated variant panel | `hfe_hemochromatosis` | 13 rows, one gene, the whole SNP core done by hand |
| a panel drafted from ClinVar | `pathogenic_clinvar`, `hboc_palb2` | 328 rows drafted then curated; and the one module that exercises every derived producer |
| star alleles | `cyp2c19_star_alleles`, `apoe_epsilon` | the biggest module here (1190 diplotypes, curated by *subtraction*); and haplotypes named `e2`/`e3`/`e4` rather than `*2` |
| single-variant drug response | `pgx_slco1b1_simvastatin` | nine rows for one variant and one drug, and the only module with a pinned licence hash |
| a repeat expansion | `fmr1_cgg_repeat`, `htt_repeat_expansion` | bins with a citation on each; and the same thing left deliberately uncited so the gap stays visible |
| mtDNA heteroplasmy | `mt_heteroplasmy` | tissue in the key, and VCF pointers that must name their namespace |
| structural or copy-number | `cyp2d6_structural`, `mt_common_deletion` | symbolic alleles, and a deletion no VRS id will ever name |
| compound heterozygosity | `hfe_compound_het` | cis and trans as two rows, indistinguishable to a consumer without phase |
| anything on GRCh37 | `grch37_build`, `cyp2c9_warfarin_grch37` | the non-GRCh38 paths, and the hand-injected `source=manual` resolution rows |
| anything near a PAR | `par_boundary`, `shox_par1` | pseudoautosomal as a property of the *locus*, never of the gene |

**Four facts from that corpus that will recalibrate what you think a module needs.**

- **Seven of the sixteen carry no `variants.csv` at all**, and six of those carry no `studies.csv`
  either. `htt_repeat_expansion` is three files total and holds no coordinate anywhere.
- **`weight` has never been authored.** The column appears in four of the sixteen and is blank in all
  42 cells. One module declares `weighting:` and it is a *negative* declaration — *"scale: none — this
  module authors no weights"*, pointing a reader at `gwas_effects.parquet` instead.
- **Two declare a `version:`; one carries `authorship:`.** Neither is required, and their absence says
  nothing bad about a module.
- **All sixteen are closed, and fifteen record zero checks.** A closure says *a human declared these
  bytes final*; it does not say anything was verified, and `close` drops check records that no longer
  describe the authored bytes. **A closed module is not a checked module.**

**Never ask an author for what only a reviewer can give.** The person you are working with brings the
theme and the sources — a trait they care about, three PDFs, a podcast. The triage, the rows, the
conclusions and the located passages are yours. An author who cannot read a genetics paper cannot
tell you whether your `state` is right, and asking sends them away to find someone who can — which
is a later pass, performed by a different person.

## For the agent: the surface beyond the author's

Eight tables are written by a **machine**, not by you: `resolution.csv`, `frequencies.csv`,
`gene_metrics.csv`, `literature.csv`, `gene_validity.csv`, `clinical_assertions.csv`,
`gwas_effects.csv` and `verification.json`. You need to know they exist and that they behave unlike
authored ones — they **merge rather than clobber**, they are hashed **by their facts rather than their
bytes**, and re-deriving one means deleting it first, which discards hand-curated rows along with stale
ones. `licensing.csv` is the one of them a human is expected to write.

**`module-tables` carries the roster, who writes each, and a dossier apiece.** The compiled artifact is
nineteen possible parquets plus `manifest.json`; you never write parquet by hand, and `reverse` is a
fixed point rather than a backup — it cannot restore `authorship`, the verification record or the
closure. **The module in your repository is the source of truth.**

## The rules the tools enforce rather than merely document

*These mirror `server.INSTRUCTIONS` deliberately — if the two ever disagree, the server is right and
this is stale.*

1. **Ask the tool, never memory.** Every column list, vocabulary and requirement is generated from
   the live models, so `describe_table` / `table_requirements` / `authoring_reference` cannot drift
   from what the compiler accepts. No skill here reproduces them.
2. **You may write, and every write is logged.** This is the authoring layer — the business decision
   is delegated here, so filling or correcting a cell is legitimate where the same act inside the
   compiler would not be. Two kinds of cell are still withheld, and neither is a refusal to write on
   principle: **a value a later check compares against that same source** (filling it from there
   makes the check agree with itself, permanently, and moves the row from honestly unverified to
   *apparently* verified), and **a value only a pilot can settle** — a genotype, a weight, a
   conclusion, a direction. Where a lookup reports `applied: false` with a `refusal`, that is
   upstream reporting what *it* did; pass it through untouched and never present your own write as
   theirs.
3. **A mismatch against a source is not a defect report.** Archives lag the edge — a retraction, a
   refuting meta-analysis, a bigger cohort. A row that disagrees with ClinVar may be the module
   being right and current while the archive is stale, so conforming it silently *degrades* the
   module and the check then agrees with itself and reports green. Editing against a source needs a
   reason that outranks the source, and that reason gets written down.
4. **A check that could not run is not a check that passed.** `null` and `unknown` never collapse
   into a pass, a blank cell means *we do not know* and never *no*, and the warnings on a green run
   are the interesting output.

> **Rule 2 was "Report, never repair" until 2026-08-20, and it was the *format* layer's rule.** The
> compiler cannot record who decided a value, so writing one there would launder a machine's guess as
> an author's judgement. Here, that decision is delegated to us. `RM15` is the audit that separated
> the two; `CLAUDE.md` §2 carries the counterstance in full.

## "How do I create one?"

**Load `create-module`.** It asks where the author is actually standing — nothing yet, a theme plus
some sources, a bundle from an outside session, a source that publishes the rows, or a module that
already exists — and routes to the stage that owns that answer. Expect a small module's first pass to
be one working session, and expect a second pass later: that is normal, not a sign the first one was
wrong.

## Where to go next

**Reading the pointers:** `` `module-tables` → `references/variants.md` `` means *that file, under that
skill's directory* — `skills/module-tables/references/variants.md`. A `references/` path with no skill
in front of it belongs to the skill you are reading. Dossiers are files, not skills: read them on
demand, do not invoke them.

| Step or question | Load |
|---|---|
| **make a module — where to enter, what runs next, what to call** | `create-module` |
| **a spec directory whose state nobody knows** | `module-status` |
| **run it on a genome here, without publishing** | `module-install-local` |
| what a `weight` means | `module-weights` |
| how a reader joins this to a VCF | `module-consumer` |
| which table kind a finding belongs in, and every column of it | `module-tables` |
| what a module looks like on disk, and what `derived/` is | `module-tables` → `references/LAYOUT.md` |
| a message you do not recognise | `references/SYMPTOMS.md` |
| the CLI surface, and what is not wrapped | `references/CLI.md` |
| finding, verifying and reading the literature | `find-evidence` |
| **"has this already been decided?"** | `../just-dna-format/docs/FAQ.md` — keyed by *question*, one or two sentences and a link, and **a refusal is an answer**. Most of it is a repair somebody proposed that was checked and rejected for a reason worth knowing. Read it before proposing a fix to the format. |
| the design behind any of it | `../just-dna-format/docs/`: `MODULE_LIFECYCLE.md` (the stages and every later pass), `SCHEMAS.md` (the models), `COMPILER.md` (the transform, and its blind spots), `ENRICHER.md` (the network tier and every check) |

**A message that cites an `RMn` means known and deliberate, not broken.** Leave the data honest, note
the limitation, and do not invent a workaround — `../just-dna-format/docs/RM_TOC.md` says what any
given number is. The two you will actually meet:

- **RM5 — symbolic and structural alleles are outside the grammar.** `<DEL>`, 5-HTTLPR, ClinPGx
  `del`/`ins`, CPIC's `x≥3` and `DELTCT` are not `^[ACGT]+$`, so the PGx passes skip such rows and count
  them rather than coercing them. Distinct from IUPAC ambiguity codes (`R`, `Y`, `N`), which record an
  uncertainty that was never expressible and **must never be expanded** into the alleles they could
  stand for.
- **RM15 — multi-build support.** GRCh38 is the only assembly with a refget table, so VRS minting and
  rsID resolution are GRCh38-only. Off GRCh38, expect less and say so in the README.

**No skill carries the whole procedure, and `create-module` is not one either.** The 1431-line version
that did was dismantled on 2026-08-20 and every line of it now sits in the stage that owns it; what came
back under that name on 2026-08-21 is a **router** — the entry points, the stage order and the tools each
stage calls, and nothing a stage skill already owns. **Load the stage you are in**, and load
`create-module` when you do not yet know which stage that is: it names the spine in lifecycle order, the
second-pass three (`module-revise`, `module-refresh`, `module-diff`) and the references the stages read.

## What this file deliberately does not contain

No column lists, no vocabularies, no requirement tables — **ask the tool.** No procedure — that is the
stage skills. No route — that is `create-module`, and the lifecycle diagram lives there rather than here. No per-table contracts — that is `module-tables` and its dossiers. The symptom lookup and
the CLI surface live in `references/` here rather than in the body, because they are read *from* every
stage rather than *by* this one. If a question is answerable only with a specific cell value, a specific
flag or a specific warning phrase, it is a subskill's question and this file should not have grown to
hold it.
