---
name: create-module
description: >-
  Author, validate, compile and publish a just-dna annotation module end to end —
  scaffold, draft from a source, curate what only a human can decide, enrich, cross-check, compile,
  publish. Use when creating or extending a module spec directory (module_spec.yaml + CSVs), when
  choosing which table kind a finding belongs in, when preparing a module for the registry, or when
  validate/enrich/compile reports something you do not recognise. Triggers: "write a module",
  "author a module", "create a just-dna module", "add a gene/panel/variant", "draft from ClinVar",
  "draft from CPIC", "heteroplasmy", "star alleles", "diplotypes", "module_spec.yaml",
  "variants.csv", "publish a module", "why does my module not compile".
---

# Creating a just-dna module

A module is a directory of human-authored CSVs plus `module_spec.yaml`, compiled into a parquet
artifact with a content-addressed `manifest.json`. It carries **annotation only** — lookup tables
mapping a genotype or a measured quantity to a phenotype. It never holds a sample, a genotype under
test, or a measured value: the consumer supplies the measurement at query time.

You never write parquet by hand, and you never commit coordinates you looked up yourself — a
separate resolution step fills those and records where they came from.

Three companions ship beside this file:

| Read | When |
|---|---|
| `references/TABLES.md` | Choosing which table kind a finding belongs in, or which axes must go in a key. |
| `references/SYMPTOMS.md` | Anything reports a message you do not recognise. Match on the quoted phrase. |
| `references/CLI.md` | The full CLI surface, what is *not* wrapped by a tool, and the environment. |

## Explaining this to someone who is not a geneticist

Most authors are not, and a novice who does not understand what a module *is* will ask for things that
cannot exist. These are the framings that were tested on a real beginner session and landed — the
conversation changed the moment "module" became **rulebook** ("*a module is a rulebook, you should've
said so!*").

| Say this | It explains |
|---|---|
| **A module is a rulebook.** "If the DNA says X at spot Y, that means Z, and here is who showed it" | what a module *is*. Lead with this one; it does more work than the rest combined |
| **A variant is a street address.** `rs4988235` names one specific spot where people differ | `rsid` |
| **Your genotype is which letters you have at that address** | `genotype` |
| **There are two jobs: writing the rulebook, and reading a DNA file against it. This only writes** | the misconception that wastes the most time |
| **The module is the knowledge; whoever runs it brings the measurement** | why nothing here opens a VCF |
| **Every row is a claim with a receipt.** `conclusion` is the claim, `pmid` is the receipt | why `studies.csv` is required whenever `variants.csv` exists |
| **A blank cell means "we don't know", never "no"** | the three-valued algebra, and why you must not write `false` to tidy a warning |
| **Those two quote columns mean "a human read this and found the sentence"** — not "here is a relevant quote" | why nothing may fill them from a fetched fulltext |
| **On a dial, a shared endpoint is a boundary; on a counter, it is two bins claiming the same number** | why dense bins must touch and integer bins must not |

**Correct the DNA-reading misconception early and unprompted.** Do not wait to be asked. A beginner's
working model is usually "point this at my DNA file and it tells me about me", and every later step reads
as nonsense against that model — they will not know why they are confused, only that they are. One
sentence up front saves the whole conversation.

**And never let a metaphor make a decision.** "Rulebook" is the right way to *explain* a module and the
wrong basis for choosing a column, a vocabulary member or a table kind. The instant the question is what
a cell may contain, stop explaining and ask `describe_table` / `table_requirements`. A metaphor that
starts answering schema questions has become a second source of truth.

## The four packages, and which one you need

The dependency arrow points inward — **enricher → compiler → format** — and only the enricher
touches the network. Most confusion comes from mixing them up.

| Package | CLI | Does | Never does |
|---|---|---|---|
| `just-dna-format` | — | the schema: models, vocabularies, identity and integrity rules | touch the network |
| `just-dna-compiler` | `just-dna-compiler` | spec directory → parquet + `manifest.json` | touch the network |
| `just-dna-enricher` | `just-dna-enricher` | resolve rsIDs→coordinates, mint VRS ids, draft from sources, cross-check | decide what a variant *means* |
| `just-dna-registry` | `registry-client` | catalog: search, download, publish | — |

`pip install just-dna-enricher` pulls the compiler and the format tier. Python ≥ 3.13.

The compiler is **inject-only**: it reads a `resolution.csv` the enricher produced. It will not go
and look a coordinate up for you.

## Use the MCP tools

This plugin ships a `just-module-creator` MCP server. Prefer its tools over shelling out: they
return structured results, they refuse to write cells you must author yourself, and they cannot
reach the one compiler flag that silently produces a module no VCF can match.

| Do this | Tool | Tier |
|---|---|---|
| choose a table kind | `list_tables` | essentials |
| learn a table's columns and vocabularies | `describe_table` | essentials |
| learn what is required / defaulted / optional | `table_requirements` | essentials |
| get a CSV header or stub | `get_template` | essentials |
| create the spec directory | `scaffold_module` | essentials |
| check rows **before** writing them | `lint_rows` | essentials |
| pre-flight a compile | `validate_module` | essentials |
| build the artifact | `compile_module` | essentials |
| find the alleles for a genotype | `lookup_variant` | essentials |
| **find the papers behind a row** | `literature_search` | essentials |
| check a PMID exists (existence only — see below) | `lookup_citation` | essentials |
| see whether a module already exists | `registry_search` | essentials |
| **draft variants + studies from ClinVar** | `draft_from_clinvar` | essentials |
| resolve coordinates, mint VRS ids, catch a ref mismatch | `enrich_module` | essentials |
| gene/trait currency — what `trait_efo_id` needs | `check_identifiers`, `lookup_identifier` | essentials |
| where may I read this paper, on what terms | `lookup_open_access` | essentials |
| read a paper | `fetch_fulltext` | essentials |
| content signature, artifact integrity | `module_signature`, `verify_artifact` | essentials |
| the whole generated DSL at once | `authoring_reference` | essentials |
| read one published module's full record | `registry_get_module` | essentials |
| is a namespace legal and free | `registry_namespace_available` | essentials |
| get an account and a token | `registry_register` | always |
| draft the PGx tables | `draft_from_cpic`, `draft_from_clinpgx` | extended |
| has this finding been replicated | `paper_citations` | extended |
| fill `literature.csv` | `enrich_literature_pass` | extended |
| fill the frequency / constraint / dosage sidecars | `enrich_facts` | extended |
| turn an artifact back into a spec, or download one | `reverse_module`, `registry_download` | extended |
| publish, or rehearse a publish | `authenticate` → `registry_whoami` → `registry_claim_namespace` → `registry_publish` | gated |
| undo a rehearsal (polygon only) | `registry_delete_version`, `registry_delete_module` | gated |

**The default tier runs this whole procedure.** Everything from scaffold to publish is essentials,
including `enrich_module` — the tiers split on cost, and essentials is everything bounded by what you
named: one identifier, one paper, one spec directory. `JMC_MODE=extended` adds only what a corpus
sizes (a citation graph, a whole-source PGx draft, a pass that rewrites every row) and reading back
somebody else's compiled artifact. Publishing needs a registry token; nothing else does — and
`registry_register` mints one from inside the surface, so there is no step that sends you to another
package's CLI.

**Every registry tool takes a `target`: `"test"` is the polygon, where a publish is a rehearsal you
can delete; `"prod"` is the published catalog.** Writes default to the polygon and catalog reads
default to production — see step 7 before you publish anything.

**Never ask a schema question from memory — ask the tool.** Column lists, vocabularies and
requirements are generated from the live pydantic models, so `describe_table` /
`table_requirements` / `authoring_reference` cannot drift from what the compiler accepts. This file
therefore does not reproduce them — the per-table section below carries only the rules a schema dump
*cannot* express.

The CLIs remain the fallback for what the server still does not wrap — **signing**
(`keygen`, `sign`), the **PGx cross-checks** (`pgx`, `clinpgx check`, `check-acmg`) and **snapshot
building**. See `references/CLI.md`.

**Finding the evidence is its own skill.** Searching the literature, checking that a PMID names the
paper you meant, reading a paper legally, and deciding what may honestly be written from it are
covered in [find-evidence](../find-evidence/SKILL.md). Load it at step 3.

## Directory layout

```
my_module/
  module_spec.yaml     # required: identity + display. The ONLY always-present file.
  variants.csv         # a lead table — or pharm_variants.csv, diplotypes.csv, pgs.csv …
  studies.csv          # required IFF variants.csv is present: the grounding
  resolution.csv       # produced by enrich — coordinates + VRS ids. Commit it.
  literature.csv       # produced by `literature` — PMID/DOI existence. Commit it.
  sources.csv          # required when data came from a licence-bearing source
  logo.png             # optional
```

One CSV = one concern. A module leads with **exactly one** primary table. A drug-response module
carries `pharm_variants.csv` and **no** `variants.csv`.

## Answer three questions first — each one closes off wrong turns later

1. **What is each row's subject?** A variant? A diplotype pair? A measured quantity? That picks the
   table kind, and a module includes **only** the kinds it uses — never an empty `variants.csv` to
   keep another table company. → `references/TABLES.md`, or `list_tables`.
2. **Are the coordinates GRCh38, and are they VCF positions?** Two separate questions, and the
   second has bitten harder. `start` is the **1-based VCF position** — the number Ensembl, dbSNP,
   ClinVar and gnomAD all show you. Paste it; never convert it. On build: anything but GRCh38 falls
   back to a **build-relative** key that will not join against gnomAD, ClinVar or ClinGen. The
   compiler warns; heed it.
3. **What is the source, and may you use it this way?** Every PGx upstream (ClinPGx, CPIC,
   PharmVar) is CC BY-SA **plus a no-sale clause**, so none is sellable — do not read a bare
   "CC BY-SA" as permission. Pass `--use unstated | non-commercial | commercial` to every command
   that copies rows out of a source. The terms land in `sources.csv`, which is the only thing the
   compile gate reads — so a source you copied from by hand is invisible to it, and you must add the
   row yourself.

## The order, and the one place deviating from it deadlocks

```
scaffold ──▶ draft ──▶ curate ──▶ enrich ──▶ check ──▶ compile ──▶ rehearse ──▶ publish
             (if a          (only a
              source has it) human)
```

**Curate before you enrich.** A drafted row leaves `<<REPLACE>>` in the cells only a human can
decide, and that placeholder makes *every* loader refuse the file — `enrich_module` included. That
is deliberate: forward resolution is allele-aware, and a placeholder genotype would silently skip
the allele filter on exactly the one-to-many rsIDs that need it. So you cannot "enrich first to see
the alleles".

You do not need to: **the draft report prints the allele pair for each stubbed row**, and
`lookup_variant` gives you the same thing for a row you are writing by hand.

Steps 4 and 6 are the only ones that use the network. Once `resolution.csv` and `literature.csv`
exist they *are* the pin: every later compile is offline and reproducible.

## 0 — Where a module comes from

Authors arrive with an idea, or with nothing, or with something somebody told them. Four honest
starting points, cheapest first:

| Start | How | Good for |
|---|---|---|
| **A gap in the catalog** | `registry_search(gene=…)` / `registry_search(query=…)` — these read **production** by default | knowing the work is wanted before doing it |
| **A source that publishes the table** | `draft_from_clinvar` for a gene panel; `draft_from_cpic` / `draft_from_clinpgx` for drug response (extended) | the fastest route to real rows. Curate what it stubs |
| **A paper the author actually read** | `literature_search` to pin the PMID and title | one well-grounded finding, which is a legitimate module |
| **Something the author was told** — a video, a podcast, a blog, an AI summary | **triage first**, below | by far the most common in practice, and the only one that starts by *removing* claims |

If an author has no idea at all, the catalog gap is the best prompt: search a gene or trait they care
about, and either nothing exists (a module to write) or something does (a module to read, which teaches
more than any template).

### Triaging a source you were handed

A summary is not evidence — it is somebody's reading of evidence, and if a machine wrote it, the
citations may be generated rather than recalled. **Assume nothing, check each claim, and expect most of
them to fail.** A real run of this procedure turned **seven** offered rsIDs into **one** authored row.

1. **Does every rsID resolve?** `lookup_variant(rsid=…)`. **Re-run any no-locus answer before believing
   it** — a failed request currently reports as a definite "no such locus" (`F17` / upstream `S20`), and
   `loci: []` is also the fingerprint of a fabricated id, so a flaky network makes real variants look
   invented. Treat a bare `loci: []` as *unchecked* when `checked` lacks `ensembl-rest`.
2. **Does the rsID sit on the same chromosome as the gene the source names?** This is the step that
   catches generated citations, and **nothing in this surface answers it** (`F23` / upstream `S24`) — you
   need a gene lookup from outside the toolchain until that lands. Labelled as manual on purpose: a
   procedure that quietly requires leaving the product trains people to skip it.
3. **Does the pairing appear in any paper?** `literature_search(rsid=…, gene=…)`. Zero results from
   sources that *answered* is strong evidence; **read `sources` first**, because a source that could not
   answer reports `results: null` and a miss is not absence.
4. **Does the cited paper say what the source claims?** `literature_search(pmids=[…])` reads the title
   back — the only thing that settles identity. `lookup_citation` proves a PMID exists, which a
   fabricated one usually does.
5. **Are two survivors the same signal?** Variants in strong LD tag one finding; two rows would
   double-count it in a score. Keep the one with the mechanism behind it.
6. **Does anything state the direction?** If no located paper says *which* allele carries the risk, drop
   the row. A guessed `direction` is a coin flip that will look exactly as authoritative as a real one.

**The tell for a generated claim is a real gene name beside an invented rsID.** Both halves survive
their own checks — the symbol is approved, the number resolves — and only the relationship is false.
That is why step 2 finds what steps 1 and 3 miss.

**Most claims not surviving is the result, not a failure**, and it is worth saying to the author in those
words. Numbers a summary offers (effect sizes, "7×", kilograms per allele) are the least reliable part
and must be re-read from the paper or left out: in the run above, one such figure was the paper's
*rescue* factor reported as its deficit. A module of one checked row is worth more than seven confident
ones, and an author who sees the arithmetic understands the tool afterwards.

## 1 — Start the spec

Check first whether the module already exists:

```
registry_search(query="lactose") / registry_search(gene="MCM6")
```

Then scaffold. It never overwrites, so re-run it with different `kinds` to add a table later:

```
scaffold_module(spec_dir="spec", name="my_module", kinds=["variants.csv", "studies.csv"])
```

`name` is lowercase alphanumeric with underscores; `my-module` is rejected. Then replace every
`<<REPLACE>>` in `module_spec.yaml` — **step 2 is not optional**, the placeholder fails validation:

```yaml
schema_version: '1.0'
module:
  title: <<REPLACE>>          # required
  description: <<REPLACE>>    # required — one sentence a non-specialist can read
  report_title: <<REPLACE>>   # required — what the report section is called
  name: my_module             # required — lowercase, underscores, no spaces
  icon: database              # icon within icon_set
  icon_set: fomantic          # 'fomantic' or 'awesome'
  color: '#6435c9'
  # version: "1.0.0"          # advisory. A SemVer STRING — unquoted 1 parses as an int and is rejected
defaults:                     # optional; folded into every row before hashing
  curator: ai-module-creator
  method: literature-review
genome_build: GRCh38
# license: CC0-1.0            # SPDX id; must not contradict sources.csv
# authorship:
#   - who: your-name
#     role: created           # audited | created | edited | reviewed
#     kind: [human]
# panel:                      # optional provenance for a module derived from a gene panel
#   source: clinvar
#   reference: '2026-06-27'
#   reference_sha256: 'sha256:…'
```

`module:` is `extra="forbid"` — a typo like `colour:` is a hard error, not a silent drop. Do not
write `namespace`, `owner` or `canonical_id`: the registry stamps those.

Learning a table you have not authored before:

```
table_requirements("heteroplasmy.csv")   # required / defaulted / optional, and any one-of rule
describe_table("heteroplasmy.csv")       # every column, its vocabulary, its pick-list
get_template("heteroplasmy.csv")         # header only
get_template("heteroplasmy.csv", stub=True, rows=3)
```

**`required` is not the whole story — there are three categories, and the middle one is invisible to
a schema dump.** A **defaulted** column (`measure_kind`, `unresolved`) is not required *and* must not
be left empty: an empty cell arrives as `None` rather than as the field's default, and fails on type
with `Input should be a valid string [input_value=None]` on a column nobody told you to fill.
`table_requirements` reports those under `defaulted`. It also reports the one-of rules — the "rsid
**or** chrom+start" kind — which no per-field flag can express.

**A generated stub cannot compile until you replace it.** `<<REPLACE>>` is rejected before type
coercion, so an unreplaced placeholder in an `int` column reads as "unreplaced template placeholder
in column start", not as a number-parsing error. That is the design: a half-filled table fails loudly
on exactly the rows still to do, rather than compiling into a module that asserts nothing.

## 2 — Draft from a source, if one publishes the table

`draft_from_clinvar` is an MCP tool (essentials); the PGx drafters are extended. `use` is required
on all three and has no default: `unstated` would silently skip licence-bearing sources, and
anything else asserts a licence position you may not hold. If a draft comes back `skipped=true`,
the terms were not satisfied and nothing was fetched — **that is the gate working, and re-running
with a different `use` to get past it is fabricating a licence position.**

```
draft_from_clinvar(spec_dir="spec", genes=["HFE"], use="non_commercial", dry_run=True)
```

Read `differs` in the result: rows where the source disagrees with something you already authored.
They are left unchanged, because rewriting your value would destroy the evidence of the
disagreement and only you know which side is right.

The equivalent CLI, still available:

```bash
just-dna-enricher draft-panel spec/ --gene HFE --use non-commercial            # ClinVar → variants.csv (+ studies.csv)
just-dna-enricher draft spec/ --gene CYP2C19 --drug clopidogrel --use non-commercial  # CPIC → the 3 PGx tables
just-dna-enricher draft-clinpgx spec/ --snapshot cp/ --drug simvastatin --use non-commercial
```

`draft-panel` downloads the published ClinVar snapshot when you have no local one; add
`--snapshot cv/ --offline` to use one you built. Its `--min-review-stars` defaults to 2 (multiple
submitters, no conflicts) and `--max-citations 3` drafts study rows from ClinVar's literature links —
which is what makes the panel compilable, since a variant row needs grounding evidence.

`draft-clinpgx` is inject-only and downloads nothing: build the snapshot first with
`just-dna-enricher clinpgx build --out cp/ --use non-commercial`.

**Drafting appends and never rewrites a cell.** A row whose key already exists is reported
(`already_present` / `differs`), never overwritten — drift on existing rows is `pgx` /
`clinpgx check`'s job to report, not drafting's to fix. Re-run per gene as the module grows;
`--dry-run` first.

**Read the warnings. They are the interesting output**: skipped rows, aggregated counts, and the
allele pairs you need for step 3. Two you will see on a real ClinVar panel and should not chase:
*"N row(s) on non-diploid contigs were written with a single-allele genotype"* is the provider filling
a cell where nothing was open to decide, and *"N ClinVar citation(s) skipped: the id ClinVar filed
under PubMed is not a PMID"* is a defect in the source — a few hundred of ClinVar's citation ids are
nine digits where a PMID is eight. Both are counted rather than listed.

**A drafted panel does not need a zygosity decision on every row.** `draft-panel` writes the sole
expressible genotype where the contig leaves nothing open — MT, and chrY outside the pseudoautosomal
regions, decided **per locus**. If you expand placeholders into both zygosities, expand *only* what
is still a placeholder; do not key that off the contig yourself.

**Pin the release you drafted from** with a `panel:` block, and `enrich` will recognise that its
ClinVar cross-check would be comparing your `clin_sig` against the file it came out of, skip it, and
say so — rather than reporting a zero it could not have avoided. Leave the block out and the check
runs as usual, which is what you want the moment a human has touched those calls.

## 3 — Curate what only a human can decide

Nothing automated fills these, on purpose:

| Cell | Why it is yours |
|---|---|
| `genotype` | Sources publish **alleles, not genotypes**. Whether one copy is informative follows from the condition's inheritance mode. **Except on a non-diploid contig**, where only one genotype is expressible and `draft-panel` writes it for you. |
| `state` (when stubbed) | The record is `uncertain_significance` and no vocabulary member means "undecided" — `neutral` says benign, `risk` says a direction. If you can justify neither, **drop the row** rather than pick one to make the compile pass. |
| `weight`, `direction`, `effect_size` | Your model of the finding. ClinVar publishes no effect statistic. |
| `trait_efo_id` | A source's condition is free text / MedGen. Mapping it to an ontology is inference. |
| `conclusion` | What the module *says*. Keep it hedged where the biology is (penetrance, tissue, co-factors). |

To write a genotype you need the alleles. Ask, without writing anything:

```
lookup_variant(rsid="rs1801133")                     # loci, ref, alts — plus what it refuses to fill
lookup_variant(rsid="rs334", ambiguity=True)         # warn when the answer is not unique
lookup_variant(chrom="1", start=11796321, ref="G", alts="A")   # allele-exact by coordinate
literature_search(gene="MTHFR", trait="homocysteine")          # find the papers — with titles
lookup_citation(pmid="7647779")                                # exists? (NOT: is it the right paper)
lookup_identifier(kind="trait", identifier="EFO_0004541")      # current | obsolete | absent
lookup_identifier(kind="gene", identifier="MTHFR")             # approved | retired | unknown
```

Then lint the rows before you write them — `lint_rows` takes CSV **text**, needs no file, and writes
nothing anywhere:

```
lint_rows("variants.csv", "rsid,genotype,state,conclusion\nrs1801133,A/G,risk,…\n")
```

Read all three levels. `error` blocks a compile. `warning` does not — and several known traps arrive
only as warnings. `info` names the columns deliberately left to you.

### Never fill a cell from the same source that checks it

`rsid`, `chrom`, `start`, `ref`, `alts`, `clin_sig`, `doi`, `acmg_sf`, `function_status`,
`evidence_level` and `p_value_num` are *redundancy-bearing*: a check compares your independently
authored value against a source, so filling it from that source makes the check vacuous. Worse, for
an rsid-only row the coordinate check does not run at all, so the row moves from honestly unverified
to apparently verified.

`lookup_variant` shows you the value and refuses to apply it — it comes back in `withheld` with
`applied: false`, a `refusal` and a `note`. **That refusal is the feature, not a limitation.**
`describe_table` names the same columns under `redundancy_bearing`.

### The mistake nothing offline can catch

Worth its own heading because it has happened at scale, to a careful author, on 3,038 variants across
four modules that all passed every gate.

**`start` is the 1-based VCF position. Copy it as printed; never subtract one.** The reflex to convert
to 0-based — from BED, or from VRS's own interbase model — is the single most expensive mistake
available here, because here is what does *not* happen: `validate_module` passes, `compile_module`
with `strict` passes, the manifest says `fully_resolved: true`, and every `ga4gh:VA.…` id is minted
and then reported **verified**. A content-addressed id is a correct digest of whatever it is handed,
so it certifies the wrong locus without hesitating. The module is internally consistent,
reproducible, signed — and about the wrong bases.

Two things conspire, and knowing them tells you what to do:

- **Never author both sides of a redundancy check.** Hand-writing `resolution.csv` *and* the
  coordinates in `variants.csv` makes the coordinate cross-check compare your convention against
  itself, and it agrees perfectly. Validate-by-redundancy only works because two *independently*
  produced values must agree. Let `enrich_module` produce the sidecar.
- **`strict` means reproducible, not correct.** It refuses when resolution left something it could
  not reproduce. It has no opinion on whether your coordinates name the variant you meant, and cannot
  have one: the compiler never fetches, so it has no reference sequence to ask.

The only thing that catches it is `enrich_module` run **online**, which compares your `ref` against
the actual genome and reports **`ref mismatch: N row(s) — coordinate shifted 1 base…`**. Read that
line as being about `start`, not `ref`. It is a floor, not a total: it can only see rows where the
neighbouring base differs from your `ref`, roughly three in four.

**Prefer the rsID and let enrichment find the coordinate.** An rsid-only row cannot carry a
coordinate mistake, and the resolution table it produces is the independent second value the
cross-check needs. Author coordinates when you have a reason to — no rsID (roughly 10% of ClinVar
pathogenic variants), one rsID naming several alleles where the row must say which, or a non-GRCh38
module — not by default.

If you already have a `resolution.csv` you did not generate and want to know whether it is right,
move it aside and re-enrich; comparing the two is the check, and no command does it for you.

## Per-table contracts

Ask `describe_table` for the columns. These are the rules it *cannot* tell you.

### variants.csv

Required on every row: `genotype`, `state`, `conclusion`. Identity: `rsid` **or** `chrom` + `start`.

```csv
rsid,genotype,weight,state,conclusion,gene,clin_sig
rs1801133,A/A,-0.5,risk,Reduced MTHFR activity; homozygous,MTHFR,
rs1801133,A/G,-0.25,risk,Reduced MTHFR activity; heterozygous,MTHFR,
rs1801133,G/G,0.0,neutral,Normal MTHFR activity,MTHFR,
```

- Do **not** author `variant_key` or `authored_ident` — the compiler derives them, and `variant_key`
  is frozen at load, so an authored one is not overwritten.
- `ref`/`alts` may only appear **with** `chrom`+`start`. You cannot attach alleles to a bare rsID.
- Genotype alleles must be drawn from `{ref} ∪ alts` at that locus. A genotype whose alleles are not
  at the locus can never match a VCF — a **warning** normally, an **error** under strict.

### studies.csv

Required: `pmid`. Identity: `rsid` **or** `chrom` (+`start`, `ref`).

- **A study must carry the same identity its variant row got.** If the variant is keyed by
  coordinate, the study must be too, or it is an orphan.
- **`pmid` is 1–8 digits.** Nine-digit ids are not PubMed ids and are rejected.
- **Take every PMID from a `literature_search` result, never from memory.** `lookup_citation` proves
  a PMID *exists*, and PMIDs are dense enough that a half-remembered one is usually a real record for
  a different paper — so existence is a weak guard against fabrication. Only a title settles it, and
  `literature_search(pmids=[...])` reads titles back. See the `find-evidence` skill.

### pharm_variants.csv (drug response)

Required: `drug`, `conclusion`. Identity: `rsid` **or** `chrom`+`start`.

The duplicate key is `(variant, drug, genotype, phenotype_category, annotation_id)` — one variant and
drug legitimately carry separate efficacy, toxicity and pharmacokinetic rows, and they can disagree.
This module type carries **no** `variants.csv` and needs **no** `studies.csv`.

**Author the rsID here, not a coordinate.** Resolution is applied to `weights.parquet` only, so a
`pharm_variants` / `diplotypes` / `pgs` row's `chrom` and `start` arrive **null** in the artifact even
when `resolution.csv` covers the variant — these tables are materialized verbatim from their authored
CSV. A consumer joins them on `rsid` + `genotype`, so expect no matches from a VCF whose `ID` column
is empty.

`validate` and `compile` now say so per table, and the second number is the one to read:

> *"pharm_variants.csv: 1 of 1 row(s) have no chrom+start, so this table joins by rsID only … **resolution.csv can place 1 of them**, and the compiler applies that table to variants.csv only."*

"`resolution.csv` can place N of them" separates **this module was never enriched** — go and enrich —
from **the coordinates exist and this tier does not apply them** — nothing you can do in the data,
and inventing the coordinate yourself would author a value the compiler did not derive. It is a
warning in both modes and never a strict error, deliberately: rsid-only identity is legal, and the
remedy is a compiler change rather than an authored edit.

### resolution.csv — produced, committed, never hand-edited

`enrich` writes one row per resolved locus: `variant_key, rsid, chrom, start, ref, alts,
genome_build, vrs_id, source, status, …`. It is what makes a compile offline and reproducible, and it
travels with the module.

- **Existing rows are authoritative and merged, never overwritten.** To re-resolve after changing the
  authored table, **delete `resolution.csv` first** — otherwise stale rows survive silently.
- A locus whose authored genotype it cannot host is **left out** and reported. That is deliberate:
  recording it would hand the compiler a locus it must drop.
- `offline=true` restricts to local caches. Substitution VRS ids mint offline; **indels and MNVs need
  the reference sequence**, so an offline run leaves them unminted — expect ~50% coverage on an
  indel-heavy module, ~99% online.

### sources.csv and licensing

Any module built from a licence-bearing source needs a row recording the terms. Passes that read such
a source write it for you; a source you read by hand is invisible, so write the row yourself.

- The compiler **refuses to build** content from a no-sale source unless `declared_use` is recorded.
  Delete the cell and the compile fails — that is the gate working.
- `license:` in the YAML must not contradict `sources.csv`. A ClinVar module declaring `CC0-1.0`
  warns, because the source row says `public-domain`; they are the same grant, but the check compares
  **spellings**. Match the source's spelling.
- It must cover **every** source your fact tables cite, including PubMed if you carry studies. A
  missing row is a warning, not an error, so it is easy to ship without noticing.

## 4 — Enrich (the only tier that fetches)

```
enrich_module(spec_dir="spec")                  # → resolution.csv (rsid ↔ coordinate, VRS ids, ref check)
enrich_module(spec_dir="spec", strict=True)
enrich_module(spec_dir="spec", offline=True)    # caches only, zero egress — and the ref check does NOT run
```

It runs as a background task: you get a task id immediately and poll. It runs several links in order
(Ensembl cache → ClinVar snapshot → live Ensembl → gnomAD) and folds in three checks — ref, clin_sig
and rsID currency. Snapshots are provisioned from HuggingFace when absent.

The fact passes are CLI-only:

```bash
just-dna-enricher frequencies spec/     # → frequencies.csv   (gnomAD, paced ~6s/batch)
just-dna-enricher gene-metrics spec/    # → gene_metrics.csv  (gnomAD constraint)
just-dna-enricher dosage spec/          # → ClinGen dosage rows onto gene_metrics.csv
just-dna-enricher literature spec/      # → literature.csv    (PMID/DOI/quotes)
```

**An existing sidecar is authoritative and merged, never clobbered.** To regenerate
`resolution.csv` / `frequencies.csv` / `gene_metrics.csv` after changing the spec you must **delete
the file first**, or stale rows persist silently.

## 5 — Cross-check what you asserted against what the sources say

```
check_identifiers(spec_dir="spec")      # trait CURIEs (OLS4) and gene symbols (HGNC) still current
```

```bash
just-dna-enricher check-acmg spec/ --sf-list acmg/   # acmg_sf vs the ACMG SF list
just-dna-enricher pgx spec/                          # function_status vs PharmVar and CPIC
just-dna-enricher clinpgx check spec/ --snapshot cp/ # pharm_variants.csv vs the ClinPGx snapshot
```

Every check **reports, never repairs** — rewriting an authored value would destroy the evidence of
the upstream mistake. `--strict` escalates a finding to a refusal; `--best-effort` (the default)
warns and carries on. Two deliberately never escalate — the `clin_sig` and allele-function
cross-checks — because failing would make the format arbitrate between expert panels.

`check-acmg` needs `--sf-list` to give a real answer: NCBI's page serves SF **v3.2** while ACMG has
published **v3.3**, so without a snapshot every disagreement comes back `unverifiable` rather than as
a finding. Build it once with `just-dna-enricher acmg build <workbook.xlsx> --out acmg/` and the
check also stops needing the network.

## 6 — Compile and verify

```
validate_module(spec_dir="spec", strict=True)
compile_module(spec_dir="spec", output_dir="out", strict=True)
verify_artifact(module_dir="out")
```

`validate_module` refuses everything `compile_module` refuses that does not need resolved rows, so a
green pre-flight should mean a green compile. **Pass it the same `strict` as the compile you intend
to run** — several checks are a ladder, so a mismatched pre-flight answers for the other compile.

**Author against `strict`, because that is what the registry runs.** The difference is not cosmetic:

| condition | plain | `strict` |
|---|---|---|
| genotype allele not among the locus's alleles | warning, **valid** | **error, invalid** |
| two-allele genotype on `MT`/`Y` | warning | warning |
| unresolved rows (no coordinate) | warning | counts against publishability |

A plain compile **succeeds** through both of the first two. So "it compiled" is not evidence the
module is correct — a module can compile cleanly and contain rows that will never match a genome.

A successful compile reports four things: `artifact_digest`, `content_signature`,
`resolution_signature` and `fully_resolved`. Recompiling an untouched spec must reproduce all of
them. Signing is CLI-only (`just-dna-compiler keygen` / `sign`); `keygen` writes an unencrypted
PKCS#8 key — it bootstraps a key, it is not a key-management system.

If you changed the schema rather than the data, prove the round-trip:

```
reverse_module(parquet_dir="out", output_dir="rev")
module_signature("spec")  and  module_signature("rev")   # must match
```

That is the fixed point the format guarantees. It holds wherever you wrote a value: `curator` and
`method` can live on the row or in `defaults:`, and `reverse` re-emits them in the other place, so
the signature folds `defaults:` into each row before hashing and the two spellings are one content.

Check what you actually shipped rather than assuming:

```bash
uv run python -c "
import polars as pl; w = pl.read_parquet('out/weights.parquet')
print(w.height, 'rows;', w.filter(pl.col('chrom').is_not_null()).height, 'with a coordinate')"
```

`0 with a coordinate` means resolution did not reach the compile — see the two traps below.

## 7 — Publish: rehearse on the polygon, then promote

**There are two registries and every registry tool takes a `target`.**

| | `target="test"` — the polygon | `target="prod"` — production |
|---|---|---|
| what it is | where a publish is a **rehearsal** | the catalog everyone installs from |
| `test-`namespaces / `test_`module names | accepted | `422 test_data_on_prod`, at the claim as well as the publish |
| deleting what you published | `registry_delete_version` / `registry_delete_module` | not possible — `yank` delists, and does **not** free the content claim |
| default for writes | **yes** | only when you ask |
| default for catalog reads | no | **yes** (`registry_search`, `registry_get_module`, `registry_download`) |

Rehearse first, always. On production a version is immutable *and* its authored rows are claimed by
a name-independent content hash that `yank` never releases — so one botched publish burns the
version number **and** the right to publish that data under any other name, permanently. That is why
the write tools default to the polygon: a forgotten `target` there costs nothing.

### The polygon is the default *answer*, not just the default argument

**Publish to the polygon, name it out loud, and stop there — unless the author has asked for the real
catalog in their own words.** "Publish it", "put it online", "share it with my friends", "send it to
your site" is **not** that ask: it is somebody who does not yet know there are two registries. Say
plainly that the polygon is a rehearsal instance nobody installs from, and leave promoting as a
separate decision the author makes *after* seeing a clean run. Someone who meant production will say so
at once, and someone who did not has lost nothing.

This is a rule about the **conversation**, not about the argument. `target` already defaults to `test`,
so the mechanism is safe; the whole risk is an agent volunteering `target="prod"` to seem helpful.
Production is immutable *and* its content claim survives a `yank`, so a half-finished first module does
not merely look untidy in the catalog — it permanently spends that version number **and** the right to
publish that data under any other name. There is no overwrite, no cleanup and no admin to appeal to.
A rehearsal costs one extra call; the alternative cannot be undone by anyone.

**Get an explicit yes before either irreversible call** — `registry_claim_namespace(target="prod")` and
`registry_publish(target="prod")` — and make sure the author knows which of the two they are agreeing
to. Put the cost *in* the question rather than after the answer.

**For a first module, prefix the module name as well as the namespace**: `test_my_module` under
`test-my-ns`, not `my_module`. `purge-test-data` matches by prefix on **both** halves, so an unprefixed
module name inside a prefixed namespace is litter nobody sweeps, and a first-time author is precisely
the person who will not come back to run `registry_delete_module`. Trade the last scrap of fidelity for
a rehearsal that cleans up after itself.

### And when it genuinely is good, say so — the default is against *assuming*, not against advocating

The rule above stops you promoting a module because the author sounded keen. It is **not** a reason to
sit on a good one: the catalog is thin, and a solid module nobody publishes helps nobody. So when
**both** halves below are true, raise production yourself rather than waiting to be asked.

**Half one — the catalog is actually missing it.** Not a guess; a call. `registry_search(gene=…)` and
`registry_search(query=…)` default to production, so ask them. "Nothing covering this gene or trait" is
a finding you can show the author. If something overlapping already exists, read it with
`registry_get_module` — the honest options then are extending it or saying why yours differs, not
publishing a near-duplicate.

**Half two — the module clears every bar, and these are checks, not impressions:**

- `validate_module(strict=True)` **and** `compile_module(strict=True)` both pass, with
  `fully_resolved: true`.
- Every weighted row has a coordinate, and `resolution.csv` was *produced*, not authored.
- Every PMID came out of a `literature_search` result whose **title you read**, never from memory.
- A licence is declared and `sources.csv` covers every source cited, with the flags honestly filled or
  honestly blank.
- **No row's `state` or `direction` was settled by guessing.** Having *dropped* rows for that reason is
  evidence in favour, not against.
- A polygon rehearsal was published and **read back**, and what came back was what you meant.
- It is *enough module to be worth an immutable version* — breadth a consumer would install it for.

**That last bar is the one that fails most often, and here is the worked case.** `assets/fto_bmi` passed
every other item on this list — strict, fully resolved, VRS minted, one impeccable citation, honest
blanks throughout — and `registry_search(gene="FTO")` returned **`total: 0`**, so the catalog genuinely
had nothing. It was still right *not* to promote it: one locus, no declared licence, no readme, unsigned.
**Underrepresented is necessary and nowhere near sufficient.** An honest module and a module worth
spending an immutable `1.0.0` on are different standards, and conflating them is how a thin catalog
becomes a catalog of stubs — which is worse, because a stub occupies the search result a real module
would have had.

When you do raise it, raise it as a recommendation with its evidence — the search result, the checks
that passed, and what is still missing — and keep the explicit yes: this permission is to *advocate*,
never to skip the confirmation on `registry_claim_namespace(target="prod")` or
`registry_publish(target="prod")`.

Nothing is shared between the two. Separate databases, so an account, a token and a namespace exist
on one instance only, and promoting a rehearsal means **publishing again** with `target="prod"`.

```
# --- rehearse (defaults; every `target="test"` below could be omitted) ---------
registry_register(account="my-name", target="test")     # a polygon account + token, no prior token needed
registry_namespace_available("test-my-ns", target="test")
registry_claim_namespace("test-my-ns", target="test")
registry_publish(namespace="test-my-ns", name="test_my_module", version="1.0.0",
                 spec_dir="spec", changelog="…", target="test")
# read what the server made of it, fix, then free the slot and go again:
registry_get_module("test-my-ns", "test_my_module", target="test")
registry_delete_version("test-my-ns", "test_my_module", "1.0.0", target="test")

# --- promote ------------------------------------------------------------------
registry_register(account="my-name", target="prod", install_id="…")  # the SAME install-id
registry_whoami(target="prod")                          # the first thing that actually checks the token
registry_namespace_available("my-ns", target="prod")    # legal? free? — read-only, no token
registry_claim_namespace("my-ns", target="prod")        # once, and it cannot be undone
registry_publish(namespace="my-ns", name="my_module", version="1.0.0",
                 spec_dir="spec", changelog="…", target="prod")
```

**Rehearse under the name you will actually publish** when you can: an unprefixed name on the
polygon is accepted, and it is the most faithful rehearsal there is. The one consequence is that the
operator's `purge-test-data` sweep matches by prefix and will not collect it, so delete it yourself
when you are done. A `test-`prefixed rehearsal is the tidier default and exercises everything except
the exact name — and for a first module it is the right choice outright, per the rule above: the sweep
matches on the module name too, so fidelity here buys a mess somebody has to remember to clear.

**A polygon result is never evidence about production.** Its namespace table, its catalog and its
duplicate-content rule are its own — the polygon scopes `duplicate_content` to the publishing
account, so a rehearsal cannot prove that somebody *else's* identical data would be refused. And
nothing in a registry response says which instance answered: check the `target` field this server
puts on every registry result and in the `published.json` receipt.

**Names split two ways and both rules are enforced, not normalised.** An account or namespace is
lowercase letters and digits with single hyphens — `my_ns` is rejected outright. A *module* name is
the opposite, `[a-z][a-z0-9_]*`, so it takes underscores and rejects hyphens. Hence
`my-ns/lactose_tolerance`. Checking a namespace costs nothing and claiming one cannot be reversed, so
run `registry_namespace_available` first; note that it reports `valid` and `available` separately,
because the registry will call an illegal name "available".

`registry_register` needs no token — it makes one. Onboarding is self-service, gated only by a
proof-of-work install-id ground locally in about a second. It hands back **two secrets that exist
nowhere else**: the token, and the install-id. Save them in `.env` — `JMC_INSTALL_ID`, plus
`JMC_API_KEY` for the production token and `JMC_TEST_API_KEY` for the polygon one. The install-id is
the account's only recovery path — there is no email and no admin — so re-registering that same id
reissues a key for the same account, while registering again without it creates a *different*
account and leaves the first unreachable.

**Register on each instance with the same install-id.** They are separate accounts either way, but
reusing the id is what keeps them recognisably yours and keeps one string to protect. A token is
only ever a credential for the instance that issued it: presenting the production key to the polygon
does not degrade gracefully, it fails as an unknown key, so nothing here falls back from one to the
other.

The **account name is not a secret and needs no saving**: `registry_whoami` reports it from the
token, and re-registering with the same install-id returns the account that id already owns and
*ignores* the `account` argument you passed. So the id is what identifies you; the name is a label
the registry hands back. Two consequences worth knowing before you call it: a second
`registry_register` will not rename an existing account, and it mints a fresh key every time rather
than returning the old one, so the last one you saved is the one that works.

`.env` is where both belong because that is what the server reads on the next boot — a token that
lives only in the session dies with it, and an install-id that lives only in a transcript is gone.
Never paste either into a module, a fixture, a commit or a note; `.env` is gitignored, everything
else here is not.

`registry_publish` re-runs `validate_module(strict=True)` locally and refuses rather than shipping a
spec the server will reject; the server then recompiles it itself, so `compile_success` and the
digest are trusted rather than claimed. A published version is immutable. A spec whose raw parts
exceed the server's transfer bound needs a client-side archive import instead.

If you also have `just-dna-pipelines`, its `marketplace check` adds network checks on top of
validation and returns `would_publish` — the one field to branch on. It has a **variant ceiling**, so
a large module comes back `422 too_many_variants`: that is the check declining to run, not a verdict
on your module. `validate_module` has no network tier and is what decides publishability.

Version deliberately. A rebuild that changes the compiled shape still moves `artifact_digest`, so it
needs a version either way; a rebuild that changes *what variants are in the module* or how they are
grounded is a **major**, because someone pinned to the old major would silently receive different
content. Write the changelog as a continuation of the previous one, not a fresh "initial release".

## Checklist before you call a module done

- [ ] `validate_module(strict=True)` passes
- [ ] every weight row has a coordinate (or you can say why not)
- [ ] genotypes sorted; single-allele on `MT`/`Y` outside PAR; alleles drawn from the locus
- [ ] every PMID verified to exist, 1–8 digits, and reachable from a weighted variant
- [ ] `resolution.csv` and `literature.csv` committed alongside the CSVs
- [ ] `sources.csv` present, covering every source cited, and consistent with `license:`
- [ ] `module.version` is a quoted SemVer string
- [ ] a second **compile** of the untouched spec reproduces the same `artifact_digest` (a
      re-**draft** will not — see below)
- [ ] published to the polygon (`target="test"`) at least once, and what came back was read

---

# Gotchas

## The two traps that ship a module no VCF can match

**`compile_module(resolve_with_ensembl=False)` / `--no-resolve` disables `resolution.csv` too.** The
name reads as "don't use Ensembl", which is exactly what a spec carrying its own resolution wants. It
is the master switch for *all* resolution: set it False and every row compiles with `chrom=None`, and
the compile **succeeds** — it warns, but a script checking only the exit status ships a module that
can never match a genome. The correct call is `resolve_with_ensembl=True, ensembl_cache=None`. The
MCP `compile_module` tool pins that and cannot reach the other branch; the CLI can.

**Deleting `resolution.csv` is part of a rebuild.** Existing rows are authoritative and merged, so a
fix that changes an authored allele will not show up until you delete the file first. The table is a
pin, not a cache.

## A re-draft always changes `artifact.digest`, even when the data is identical

`sources.csv` carries a `fetched_at` timestamp stamped when the row is written, and
`sources.parquet` is one of the files the digest is a Merkle root over — so two builds of
byte-identical content, an hour apart, are two different artifacts. Consequences worth planning
around:

- **Recompiling is reproducible; re-drafting is not.** `compile` twice on an untouched spec gives the
  same digest every time. That is the property to test.
- **Do not treat a digest change as evidence that content changed.** Diff the tables.
- **Digest-based dedup will miss matches** across rebuilds, so `find-by-hash` cannot recognise a
  module you rebuilt without editing.

If you need a rebuild to be digest-stable, keep the previous `sources.csv` rather than letting the
draft re-stamp it.

## Coordinates and identity

- **`start` is the 1-based VCF position. Never subtract one.** (Above, at length.)
- **Identity is filled whole or not at all** — the rsID, else the complete `chrom`/`start`/`ref`/`alts`.
  A lone `alts` on a position-only row changes *which variant the row is*: it makes the key a VRS
  `ga4gh:VA.…` id instead of `chrom:start:ref`.
- **An rsID row's `variant_key` stays the rsID — VRS ids are not the key.** They live in
  `resolution.csv`'s `vrs_id`, **one per ALT, positionally aligned with `alts`** — an empty member
  there is a site whose id could not be minted (an indel offline), not a hole to fill by hand.
- **A genotype is `C/C`, not `CC`.** `CC` parses as a single two-base allele. Sources (ClinPGx) write
  the unslashed form; disambiguate using the resolved ref/alt.
- **Unphased genotypes are alphabetically sorted** (`A/G`, never `G/A`) because an unphased genotype
  is a *set*; two spellings of one call would be two rows. Phased uses `|` and order is significant.
- **Indels are spelled out, reference-anchored**: `A/AG`, `C/CTT`.
- **Off GRCh38, expect less and say so.** rsIDs resolve against GRCh38 only, so a `GRCh37` module
  resolves nothing and mints no VRS ids; its keys are build-relative coordinates that will not join
  against gnomAD/ClinVar/ClinGen. Author coordinates rather than rsIDs there. Known limitation
  (RM15), not a defect.
- **An rsID is position-level, not per-allele.** One rsID can legitimately span pathogenic, benign and
  uncertain alleles at one locus, and a paralogous one maps to several genuinely distinct places
  (reported as `expanded to N rows` — expected, do not delete rows to suppress it).

## Weight, state and direction

- **A `risk` weight is negative.** `weight` is a contribution to a wellness-style score, not a hazard
  ratio, so `state='risk'` or `direction='risk'` wants `weight < 0` and `protective` wants
  `weight > 0`. Getting the sign backwards is a warning, not an error, so it compiles — check it
  rather than trusting a green run.
- **`direction` is not a magnitude.** Its members are the same axis as `state`
  (`neutral`/`protective`/`risk`/`unknown`), not `increase`/`decrease`. Ask `describe_table` before
  writing any vocabulary cell from intuition.
- **`direction` is authored or it is empty — nothing computes it for you.** `state` is required;
  `direction` / `stat_significance` / `clin_sig` are orthogonal to it and optional. The compiler
  never fills a blank `direction` from `state`, since that would assert a claim you did not make
  (`state='significant'` names no direction at all). So a module carrying only `state` compiles fine
  and ships an empty `direction` column, and a consumer keying on `direction` sees nothing. Write it
  on every row it applies to, or on none.

## The checks, and the two ways to defeat them by accident

- **Never fill a cell from the same source that checks it** (the redundancy-bearing list, above).
- **Never author both sides of a redundancy check** — `resolution.csv` plus the coordinates it verifies.
- **`strict` means reproducible, not correct.**
- **A sidecar you already have is authoritative and merged, never clobbered.** Delete it to regenerate.
- **Read "ref mismatch" as possibly being about `start`.** All of it is reported, never repaired, and
  none of it runs offline. An empty result from an offline run means *unchecked*, not *clean*.

## Withhold rather than assert

The house algebra is **three-valued: true / false / unknown**, and `None` is never `False`.

- **A blank cell means "not stated" and is always legitimate.** Do not write `false` to silence a
  reminder.
- **Every binning table has an `unresolved` sentinel** a consumer selects when the measurement is
  absent. Never route a missing measurement to the lowest bin.
- **Set `requires_callable=true` (with `callable_from`)** wherever the *absence* of a variant is the
  informative call: a no-call is not a reference call.
- **On licensing, unknown terms are undetermined, never permitted** — `share_alike` /
  `commercial_use` left blank do not mean allowed.
- **`unchecked` / `unknown` in a report means the question was never put.** A check that could not run
  is not a check that passed.

## Binning bounds

- **`measure_max` is inclusive on every kind.** A bounded domain's top value (allele fraction `1.0` is
  homoplasmy, and real) has to be reachable. Use `min == max` for a sharp value and a null bound for
  open-ended.
- **Whether adjacent bins may share an endpoint depends on the kind, and the two cases are opposite.**
  - **Dense — `allele_fraction`, `prs_percentile`: bounds must touch**, e.g. `0.0–0.1` then `0.1–0.3`.
    A shared endpoint is a *boundary*, not an overlap, and the higher bin owns it (lookup selects the
    row with the greatest `measure_min ≤ x`). A hole between bins warns, because on a continuous
    measure it can be arbitrarily small.
  - **Integer — `repeat_count`, `copy_number`: bounds must NOT touch**, e.g. `[27,35]` then `[36,39]`.
    Adjacent integer bins are already contiguous, so a shared endpoint is a real overlap — both bins
    claim that integer — and it is refused.
  - **`activity_score` is in neither set.** It is a consumer-summed value on a coarse grid, so
    interior holes are not meaningful (no gap warning) and bins do not touch.
- **Two bins sharing a *lower* bound refuse on every kind** — the boundary rule selects the greatest
  `measure_min ≤ x` and these two are the same, so there is nothing to order.
- Bins are grouped by the kind's key columns **plus** `trait_efo_id`. If two different variants
  collide in a heteroplasmy table, give each its own variant identity — that is what the key is for.

## PGx and star alleles

- **A clinical annotation's key is `(variant_key, drug, genotype, phenotype_category, annotation_id)`**
  — not the bare triple. One variant+drug carries several distinct annotations (rs4149056+simvastatin
  is Metabolism/PK 1A, Efficacy 3 *and* Toxicity 1A).
- **Annotations are per genotype, and can oppose each other** — rs4149056/simvastatin is "decreased"
  for CC/CT and "increased" for TT. Genotype is in the key for that reason.
- **CPIC recommendations are keyed by (phenotype, drug, *population*)**, and the populations disagree
  — the same Poor Metabolizer diplotype is `strong` in one clinical context and `moderate` in another.
  **Every clinical context is drafted**, kept apart by `clinical_context`, and the *consumer* picks
  at query time — which is the right owner, since which indication a patient is being treated for is
  knowable then and not at authoring time. So `population` **filters, it does not decide**: leave it
  unset to get them all, and set it only when you genuinely want one setting. An unrecognised value
  is an error listing what CPIC actually publishes, so a typo cannot quietly draft nothing.
- **`recommendation_strength` is CPIC's; `evidence_level` is PharmGKB/ClinPGx's.** Different axes —
  fill only the one your source states.
- **A large star-allele gene needs `draft --allele`.** *n* alleles is *n(n+1)/2* diplotypes;
  unfiltered CYP2D6 is 16,290 rows, 73% `Indeterminate`. Your real bound is the allele set your caller
  emits — six alleles turn those 16,290 into 21. The filter covers all three PGx tables, `*1` is
  always kept, and it takes a single `--gene` because a star name is gene-scoped.
- **A star allele can be *used* without being *defined*.** If `haplotypes.csv` never defines an allele
  that `diplotypes.csv` or `allele_function.csv` names, a caller can never emit it and every row about
  it is dead. Warned, not blocked — leaning on an external caller's definitions is legitimate.
- **CPIC activity scores are inequality strings (`"≥3.0"`), not numbers**, so they do not drop into
  numeric bin bounds; and CPIC's `n/a` means *not scored* — an absence, so leave the cell blank.
- **A PGx module carries no `variants.csv`, and that is correct.**

## Licensing

- **Every PGx upstream (ClinPGx, CPIC, PharmVar) is CC BY-SA *plus a no-sale clause*.** None is
  sellable. Do not read a bare "CC BY-SA" as permission — read the surrounding terms. CPIC is not an
  unrestricted alternative: its licence page redirects to the same ClinPGx data-usage policy. (If you
  find PharmGKB API documentation, it is dead — ClinPGx is the successor, paths and formats
  unchanged.)
- **Pass `--use unstated | non-commercial | commercial`** to anything that copies rows out of a
  source (`draft`, `draft-panel`, `draft-clinpgx`, `dosage`, `pgx`, `clinpgx build/check`). A
  forbidding source is *skipped* on `unstated` and *refused* on `commercial`, at acquisition —
  nothing is even fetched.
- **`sources.csv` is the only thing the compile gate reads.** Only the *annotation* layer taints; a
  coordinate is a fact, so a fact-layer row carries attribution rather than a prohibition.
  Most-restrictive-wins, module-wide.
- **The CLI spelling and the column value differ.** `--use` accepts `non-commercial`, but the
  `declared_use` *column* takes the vocabulary member `non_commercial` (underscore). The flag
  normalizes; a cell you type by hand does not.
- **There is no `--non-commercial` compile flag, by design.** A flag cannot survive `reverse`, so a
  third compile would refuse. The declaration has to be data.

## Sex chromosomes and the PAR

- **A pseudoautosomal variant is recorded once, on X**, because that is the spelling every annotation
  source uses and a standard GRCh38 analysis set hard-masks the Y PAR. Pass `--keep-par-twin` to
  `enrich` only if your reference is unmasked.
- **`chrom=Y` is not "never diploid": PAR1 and PAR2 are diploid in every karyotype.** The verdict is
  **per locus**, not per gene or per module — `XG` and `SPRY3` each straddle a boundary.
- **`chrom=MT` is not diploid.** Use a single allele (`G`) for a homoplasmic or hemizygous call. A
  mixed mitochondrial population is heteroplasmy and belongs in `heteroplasmy.csv`, not in a het
  genotype.

## Module structure

- **One CSV = one concern.** Compose from optional table kinds; never add a foreign domain's columns
  to every row. `studies.csv` is required **iff** `variants.csv` is present. At least one recognised
  table must exist.
- **A value every row shares belongs in `module_spec.yaml`'s `defaults:`** (`curator`, `method`).
  Both spellings are the same content to the signature; the defaults block is the tidier module.
- **Authored row order is preserved** through compile → reverse → recompile and is load-bearing for
  `artifact_digest`. Drafted rows land in their gene's block or at the end; a re-run leaves anything
  already there exactly as it is.
- **Write CSVs with a CSV writer, not by splitting on commas.** Several `conclusion` values contain
  commas, and a column shift usually surfaces as a bizarre validation error three columns away.

## Known gaps — do not work around these in your data

Messages sometimes cite an `RMn` — a tracked item in the upstream roadmap. That marker means **known
and deliberate**: leave the data honest and note the limitation rather than inventing a workaround.

- **RM5** — symbolic and structural alleles (`<DEL>`, 5-HTTLPR, ClinPGx `del`/`ins`, CPIC's `x≥3` and
  `DELTCT` notations) are outside the `^[ACGT]+$` grammar. The PGx passes skip such rows and count
  them rather than coercing them. Distinct from CPIC's IUPAC ambiguity codes (`R`, `Y`, `N`), which
  record an uncertainty that was never expressible and must never be expanded into the alleles they
  could stand for.
- **RM15** — multi-build support. GRCh38 is the only assembly with a refget table, so VRS identity
  minting and rsID resolution are GRCh38-only.

# When something looks wrong

`references/SYMPTOMS.md` maps the actual message text → cause → what to do. Start there before
reading code; most of those entries are traps that cost someone a day already.
