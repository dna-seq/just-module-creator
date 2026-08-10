---
name: create-module
description: >-
  Author, validate, compile and publish a just-dna annotation module (format 0.5) end to end —
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

Two companions ship beside this file:

| Read | When |
|---|---|
| `references/TABLES.md` | Choosing which table kind a finding belongs in, or which axes must go in a key. |
| `references/SYMPTOMS.md` | Anything reports a message you do not recognise. Match on the quoted phrase. |

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
| check a PMID exists | `lookup_citation` | essentials |
| see whether a module already exists | `registry_search` | essentials |
| resolve coordinates, mint VRS ids, catch a ref mismatch | `enrich_module` | extended |
| gene/trait currency | `check_identifiers`, `lookup_identifier` | extended |
| content signature, integrity, round-trip | `module_signature`, `verify_artifact`, `reverse_module` | extended |
| the whole generated DSL at once | `authoring_reference` | extended |
| publish | `authenticate` → `registry_whoami` → `registry_publish` | gated |

Extended tools need `JMC_MODE=extended`. Publishing needs a registry token; nothing else does.

**Never ask a schema question from memory — ask the tool.** Column lists, vocabularies and
requirements are generated from the live pydantic models, so `describe_table` /
`table_requirements` / `authoring_reference` cannot drift from what the compiler accepts. Nothing in
this file restates them.

The CLIs (`just-dna-compiler`, `just-dna-enricher`, `registry-client`) remain available and are the
fallback for anything the server does not wrap — chiefly **drafting from a source** (`draft`,
`draft-panel`, `draft-clinpgx`), the **fact passes** (`frequencies`, `gene-metrics`, `dosage`,
`literature`), **signing** (`keygen`, `sign`), and the PGx cross-checks. See `references/CLI.md`.

## Answer three questions first — each one closes off wrong turns later

1. **What is each row's subject?** A variant? A diplotype pair? A measured quantity? That picks the
   table kind, and a module includes **only** the kinds it uses — never an empty `variants.csv` to
   keep another table company. → `references/TABLES.md`, or `list_tables`.
2. **Are the coordinates GRCh38, and are they VCF positions?** Two separate questions, and the
   second has bitten harder. `start` is the **1-based VCF position** — the number Ensembl, dbSNP,
   ClinVar and gnomAD all show you. Paste it; never convert it. On build: anything but GRCh38 falls
   back to a **build-relative** key that will not join against gnomAD, ClinVar or ClinGen.
3. **What is the source, and may you use it this way?** Every PGx upstream (ClinPGx, CPIC,
   PharmVar) is CC BY-SA **plus a no-sale clause**, so none is sellable — do not read a bare
   "CC BY-SA" as permission. Pass `--use unstated | non-commercial | commercial` to every command
   that copies rows out of a source. The terms land in `sources.csv`, which is the only thing the
   compile gate reads — so a source you copied from by hand is invisible to it, and you must add the
   row yourself.

## The order, and the one place deviating from it deadlocks

```
scaffold ──▶ draft ──▶ curate ──▶ enrich ──▶ check ──▶ compile ──▶ publish
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
`<<REPLACE>>` in `module_spec.yaml`:

```yaml
schema_version: '1.0'
module:
  title: <<REPLACE>>          # required
  description: <<REPLACE>>    # required
  report_title: <<REPLACE>>   # required
  name: my_module             # required — lowercase, underscores, no spaces
  icon: database              # icon within icon_set
  icon_set: fomantic          # 'fomantic' or 'awesome'
  color: '#6435c9'
  # version: "1.0.0"          # advisory. A SemVer STRING — unquoted 1 parses as int and is rejected
defaults:                     # optional; folded into every row before hashing
  curator: ai-module-creator
  method: literature-review
genome_build: GRCh38
# panel:                      # optional provenance for a module derived from a gene panel
#   source: clinvar
#   reference: '2026-06-27'
#   reference_sha256: 'sha256:…'
# authorship: [{who: your-name, role: created, kind: [human]}]
# license: CC-BY-SA-4.0       # advisory; must not contradict sources.csv
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
be left empty: an empty cell arrives as `None` rather than as the field's default, and fails on type.
`table_requirements` reports it under `defaulted`. It also reports the one-of rules — the "rsid
**or** chrom+start" kind — which no per-field flag can express.

**A generated stub cannot compile until you replace it.** `<<REPLACE>>` is rejected before type
coercion, so an unreplaced placeholder in an `int` column reads as "unreplaced template placeholder
in column start", not as a number-parsing error. That is the design: a half-filled table fails loudly
on exactly the rows still to do, rather than compiling into a module that asserts nothing.

## 2 — Draft from a source, if one publishes the table

Not wrapped by the MCP server — use the CLI:

```bash
just-dna-enricher draft-panel spec/ --gene HFE --use non-commercial            # ClinVar → variants.csv (+ studies.csv)
just-dna-enricher draft spec/ --gene CYP2C19 --drug clopidogrel --use non-commercial  # CPIC → the 3 PGx tables
just-dna-enricher draft-clinpgx spec/ --snapshot cp/ --drug simvastatin --use non-commercial
```

**Drafting appends and never rewrites a cell.** A row whose key already exists is reported
(`already_present` / `differs`), never overwritten. Re-run per gene as the module grows; `--dry-run`
first.

**Read the warnings. They are the interesting output**: skipped rows, aggregated counts, and the
allele pairs you need for step 3. Two you will see on a real ClinVar panel and should not chase:
*"N row(s) on non-diploid contigs were written with a single-allele genotype"* is the provider filling
a cell where nothing was open to decide, and *"N ClinVar citation(s) skipped: the id ClinVar filed
under PubMed is not a PMID"* is a defect in the source.

**Pin the release you drafted from** with a `panel:` block, and `enrich` will recognise that its
ClinVar cross-check would be comparing your `clin_sig` against the file it came out of, skip it, and
say so — rather than reporting a zero it could not have avoided.

## 3 — Curate what only a human can decide

Nothing automated fills these, on purpose:

| Cell | Why it is yours |
|---|---|
| `genotype` | Sources publish **alleles, not genotypes**. Whether one copy is informative follows from the condition's inheritance mode. **Except on a non-diploid contig**, where only one genotype is expressible and `draft-panel` writes it for you: MT always, chrY outside the pseudoautosomal regions. |
| `state` (when stubbed) | The record is `uncertain_significance` and no vocabulary member means "undecided" — `neutral` says benign, `risk` says a direction. If you can justify neither, **drop the row** rather than pick one to make the compile pass. |
| `weight`, `direction`, `effect_size` | Your model of the finding. ClinVar publishes no effect statistic. |
| `trait_efo_id` | A source's condition is free text / MedGen. Mapping it to an ontology is inference. |
| `conclusion` | What the module *says*. Keep it hedged where the biology is. |

To write a genotype you need the alleles. Ask, without writing anything:

```
lookup_variant(rsid="rs1801133")                     # loci, ref, alts — plus what it refuses to fill
lookup_variant(rsid="rs334", ambiguity=True)         # warn when the answer is not unique
lookup_variant(chrom="1", start=11796321, ref="G", alts="A")   # allele-exact by coordinate
lookup_citation(pmid="7647779")                      # does it exist, and what DOI does it carry
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
so it certifies the wrong locus without hesitating.

Two things conspire, and knowing them tells you what to do:

- **Never author both sides of a redundancy check.** Hand-writing `resolution.csv` *and* the
  coordinates in `variants.csv` makes the coordinate cross-check compare your convention against
  itself, and it agrees perfectly. Let `enrich_module` produce the sidecar.
- **`strict` means reproducible, not correct.** It refuses when resolution left something it could
  not reproduce. It has no opinion on whether your coordinates name the variant you meant, and cannot
  have one: the compiler never fetches, so it has no reference sequence to ask.

The only thing that catches it is `enrich_module` run **online**, which compares your `ref` against
the actual genome and reports **`ref mismatch: N row(s) — coordinate shifted 1 base…`**. Read that
line as being about `start`, not `ref`. It is a floor, not a total: it can only see rows where the
neighbouring base differs from your `ref`, roughly three in four.

**Prefer the rsID and let enrichment find the coordinate.** An rsid-only row cannot carry a
coordinate mistake, and the resolution table it produces is the independent second value the
cross-check needs. Author coordinates when you have a reason to — no rsID, or a non-GRCh38 module —
not by default.

## 4 — Enrich (the only tier that fetches)

```
enrich_module(spec_dir="spec")                  # → resolution.csv (rsid ↔ coordinate, VRS ids, ref check)
enrich_module(spec_dir="spec", strict=True)
enrich_module(spec_dir="spec", offline=True)    # caches only, zero egress — and the ref check does NOT run
```

It runs as a background task: you get a task id immediately and poll.

The fact passes are CLI-only:

```bash
just-dna-enricher frequencies spec/     # → frequencies.csv   (gnomAD, paced ~6s/batch)
just-dna-enricher gene-metrics spec/    # → gene_metrics.csv  (gnomAD constraint)
just-dna-enricher dosage spec/          # → ClinGen dosage rows onto gene_metrics.csv
just-dna-enricher literature spec/      # → literature.csv    (PMID/DOI/quotes)
```

**An existing sidecar is authoritative and merged, never clobbered.** To regenerate
`resolution.csv` / `frequencies.csv` / `gene_metrics.csv` after changing the spec you must **delete
the file first**, or stale rows persist silently. Moving it aside and re-enriching is also the only
way to ask whether an injected table still agrees with the sources.

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
the upstream mistake. Two deliberately never escalate — the `clin_sig` and allele-function
cross-checks — because failing would make the format arbitrate between expert panels.

`check-acmg` needs `--sf-list` to give a real answer: NCBI's page serves SF **v3.2** while ACMG has
published **v3.3**, so without a snapshot every disagreement comes back `unverifiable`.

## 6 — Compile and verify

```
validate_module(spec_dir="spec", strict=True)
compile_module(spec_dir="spec", output_dir="out", strict=True)
verify_artifact(module_dir="out")
```

`validate_module` refuses everything `compile_module` refuses that does not need resolved rows, so a
green pre-flight should mean a green compile. **Pass it the same `strict` as the compile you intend
to run** — several checks warn under best-effort and refuse under strict, so a mismatched pre-flight
answers for the other compile.

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
the signature folds `defaults:` into each row before hashing.

Check what you actually shipped rather than assuming:

```bash
uv run python -c "
import polars as pl; w = pl.read_parquet('out/weights.parquet')
print(w.height, 'rows;', w.filter(pl.col('chrom').is_not_null()).height, 'with a coordinate')"
```

`0 with a coordinate` means resolution did not reach the compile.

## 7 — Publish

```
authenticate(token="…")           # per session; nothing local validates it
registry_whoami()                 # the first thing that actually checks the token
registry_claim_namespace("my-ns") # once, if you have no namespace yet
registry_publish(namespace="my-ns", name="my_module", version="1.0.0",
                 spec_dir="spec", changelog="…")
```

`registry_publish` re-runs `validate_module(strict=True)` locally and refuses rather than shipping a
spec the server will reject; the server then recompiles it itself, so `compile_success` and the
digest are trusted rather than claimed.

Version deliberately. A rebuild that changes the compiled shape still moves `artifact_digest`, so it
needs a version either way; a rebuild that changes *what variants are in the module* or how they are
grounded is a **major**, because someone pinned to the old major would silently receive different
content. Write the changelog as a continuation of the previous one, not a fresh "initial release".

A published version is immutable.

There is a **second, separate** destination: the HuggingFace annotator collection, which takes the
**compiled** artifacts rather than the spec. The two are published independently and no command does
both.

## Checklist before you call a module done

- [ ] `validate_module(strict=True)` passes
- [ ] every weight row has a coordinate (or you can say why not)
- [ ] genotypes sorted; single-allele on `MT`/`Y` outside PAR; alleles drawn from the locus
- [ ] every PMID verified to exist, 1–8 digits, and reachable from a weighted variant
- [ ] `resolution.csv` and `literature.csv` committed alongside the CSVs
- [ ] `sources.csv` present and consistent with `license:` if a licensed source was used
- [ ] `module.version` is a quoted SemVer string
- [ ] a second **compile** of the untouched spec reproduces the same `artifact_digest` (a
      re-**draft** will not — `sources.csv` re-stamps `fetched_at`, which is inside the digest)

---

# Gotchas

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
  is a *set*. Phased uses `|` and order is significant.
- **Indels are spelled out, reference-anchored**: `A/AG`, `C/CTT`.
- **Off GRCh38, expect less and say so.** rsIDs resolve against GRCh38 only, so a `GRCh37` module
  resolves nothing and mints no VRS ids. Author coordinates rather than rsIDs there. Known limitation
  (RM15), not a defect.
- **An rsID is position-level, not per-allele.** One rsID can legitimately span pathogenic, benign and
  uncertain alleles at one locus, and a paralogous one maps to several genuinely distinct places
  (reported as `expanded to N rows` — expected, do not delete rows to suppress it).

## Weight, state and direction

- **A `risk` weight is negative.** `weight` is a contribution to a wellness-style score, not a hazard
  ratio, so `state='risk'` or `direction='risk'` wants `weight < 0` and `protective` wants
  `weight > 0`. Getting the sign backwards is a warning, not an error, so it compiles.
- **`direction` is not a magnitude.** Its members are the same axis as `state`
  (`neutral`/`protective`/`risk`/`unknown`), not `increase`/`decrease`. Ask `describe_table` before
  writing any vocabulary cell from intuition.
- **`direction` is authored or it is empty — nothing computes it for you.** The compiler never fills a
  blank from `state`, since that would assert a claim you did not make. A module carrying only `state`
  ships an empty `direction` column and a consumer keying on `direction` sees nothing. If you want
  the newer axis read, write it — on every row it applies to, not on some.

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
- **On licensing, unknown terms are undetermined, never permitted.**
- **`unchecked` / `unknown` in a report means the question was never put.** A check that could not run
  is not a check that passed.

## Binning bounds

- **`measure_max` is inclusive on every kind.** Use `min == max` for a sharp value and a null bound
  for open-ended.
- **Whether adjacent bins may share an endpoint depends on the kind, and the two cases are opposite.**
  - **Dense — `allele_fraction`, `prs_percentile`: bounds must touch**, e.g. `0.0–0.1` then `0.1–0.3`.
    The higher bin owns the shared endpoint. A hole between bins warns.
  - **Integer — `repeat_count`, `copy_number`: bounds must NOT touch**, e.g. `[27,35]` then `[36,39]`.
    A shared endpoint is a real overlap and is refused.
  - **`activity_score` is in neither set** — a coarse consumer-summed grid: no gap warning, bins do
    not touch.
- **Two bins sharing a *lower* bound refuse on every kind.**
- Bins are grouped by the kind's key columns **plus** `trait_efo_id`.

## PGx and star alleles

- **A clinical annotation's key is `(variant_key, drug, genotype, phenotype_category, annotation_id)`**
  — not the bare triple.
- **Annotations are per genotype, and can oppose each other** — rs4149056/simvastatin is "decreased"
  for CC/CT and "increased" for TT.
- **CPIC recommendations are keyed by (phenotype, drug, *population*)**, and the populations disagree.
  `draft --drug` refuses and lists the choices rather than picking one. Narrow with `--population`.
- **`recommendation_strength` is CPIC's; `evidence_level` is PharmGKB/ClinPGx's.** Fill only the one
  your source states.
- **A large star-allele gene needs `draft --allele`.** *n* alleles is *n(n+1)/2* diplotypes;
  unfiltered CYP2D6 is 16,290 rows, 73% `Indeterminate`. `*1` is always kept; one `--gene` at a time.
- **A star allele can be *used* without being *defined*.** Warned, not blocked.
- **CPIC activity scores are inequality strings (`"≥3.0"`), not numbers**, and CPIC's `n/a` means
  *not scored* — leave the cell blank.
- **A PGx module carries no `variants.csv`, and that is correct.**

## Licensing

- **Every PGx upstream (ClinPGx, CPIC, PharmVar) is CC BY-SA *plus a no-sale clause*.** None is
  sellable. (PharmGKB's API was retired 2026-07-20; the successor is ClinPGx, paths and formats
  unchanged. CPIC is not an unrestricted alternative.)
- **Pass `--use unstated | non-commercial | commercial`** to anything that copies rows out of a
  source. A forbidding source is *skipped* on `unstated` and *refused* on `commercial`, at
  acquisition — nothing is even fetched.
- **`sources.csv` is the only thing the compile gate reads.** Only the *annotation* layer taints; a
  coordinate is a fact. Most-restrictive-wins, module-wide.
- **The CLI spelling and the column value differ.** `--use` accepts `non-commercial`, but the
  `declared_use` *column* takes `non_commercial` (underscore).
- **There is no `--non-commercial` compile flag, by design** — a flag cannot survive `reverse`.

## Sex chromosomes and the PAR

- **A pseudoautosomal variant is recorded once, on X**, because that is the spelling every annotation
  source uses and a standard GRCh38 analysis set hard-masks the Y PAR.
- **`chrom=Y` is not "never diploid": PAR1 and PAR2 are diploid in every karyotype.** The verdict is
  **per locus** — `XG` and `SPRY3` each straddle a boundary.
- **`chrom=MT` is not diploid.** Use a single allele (`G`).

## Module structure

- **One CSV = one concern.** Compose from optional table kinds. `studies.csv` is required **iff**
  `variants.csv` is present. At least one recognised table must exist.
- **A value every row shares belongs in `module_spec.yaml`'s `defaults:`.** Both spellings are the
  same content to the signature; the defaults block is the tidier module.
- **Authored row order is preserved** through compile → reverse → recompile and is load-bearing for
  `artifact_digest`.
- **Write CSVs with a CSV writer, not by splitting on commas.** Several `conclusion` values contain
  commas, and a column shift usually surfaces as a bizarre validation error three columns away.

## Known gaps — do not work around these in your data

Messages sometimes cite an `RMn` — a tracked item in the upstream roadmap. That marker means **known
and deliberate**: leave the data honest and note the limitation rather than inventing a workaround.

- **RM5** — symbolic and structural alleles (`<DEL>`, 5-HTTLPR, ClinPGx `del`/`ins`, CPIC's `x≥3`)
  are outside the `^[ACGT]+$` grammar. Such rows are skipped and counted rather than coerced.
  Distinct from IUPAC ambiguity codes (`R`, `Y`, `N`), which record an uncertainty that was never
  expressible and must never be expanded into the alleles they could stand for.
- **RM15** — multi-build support. GRCh38 is the only assembly with a refget table, so VRS identity
  minting and rsID resolution are GRCh38-only.

# When something looks wrong

`references/SYMPTOMS.md` maps the actual message text → cause → what to do. Start there before
reading code; most of those entries are traps that cost someone a day already.
