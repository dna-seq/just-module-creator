# heteroplasmy.csv — how much of the mtDNA carries the variant, and what that fraction means in this tissue

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

## What it is

`heteroplasmy.csv` answers *"the sample's heteroplasmy fraction for this mtDNA variant in this tissue
is 0.34 — what do I tell the reader?"* mtDNA sits at hundreds of copies per cell and a pathogenic
variant occupies some **fraction** of them; below a threshold the cell compensates and there is no
phenotype, above it there is. One row is one **range → conclusion** band. The module holds no
measurement — the consumer supplies the fraction at query time and the table says what it means
(`binning.py:11-15`, the data-agnostic north star). Its audience is an author who has read the
mitochondrial literature and knows that the threshold is *variant-specific* and *tissue-specific*, and
a consumer that would implement one "bin a measure" code path across all four binning kinds. That
consumer does not exist yet — see **Consumption today**.

It is one of four `MeasureBinRow` subclasses (`activity_phenotype.csv`, `copynumbers.csv`,
`repeat_alleles.csv`, `heteroplasmy.csv`) and the only one that is also **positional** — it can name a
variant by coordinate, so it is joinable to a VCF and can mint a VRS allele id.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.binning.HeteroplasmyRow` (`schema/src/just_dna_format/binning.py:578`), subclass of `MeasureBinRow` (`binning.py:237`) |
| Becomes | `heteroplasmy.parquet` — registered in `compiler._TABLE_KINDS` (`compiler.py:227`); in `ARTIFACT_PARQUETS` (`compiler.py:278`) **and** in `LEAD_PARQUETS` (`compiler.py:307`), so its presence alone makes a directory "a module" |
| Bin group key | `_KEY_FIELDS = ("gene", "reference_sequence", "tissue", "variant_key")` (`binning.py:604-606`), **plus `trait_efo_id`**, which `_bin_groups` appends and `_KEY_FIELDS` does not name (`binning.py:696`) |
| Dedup key | **none.** Binning kinds are deliberately absent from `_TABLE_DUPE_KEYS` (`compiler.py:236-239`): an exact duplicate resolved bin surfaces as an *overlap* error, and a duplicate `unresolved` sentinel as its own error |
| Authored or machine-produced | **authored, entirely.** No drafter emits a heteroplasmy row — `clinvar_draft` writes `variants.csv`/`studies.csv`, `pgx_draft` writes the three PGx tables, `clinpgx_draft` writes `pharm_variants.csv`. `clinvar_draft.py:666` only *redirects* you here |
| Fact signature | **none.** Fact hashes exist only for the seven derived sidecars (`integrity.py:289-397`) |
| In `content_signature`? | **yes**, as parsed rows (`compiler.content_signature`, `compiler.py:3848-3887`, via `_TABLE_KINDS`) |
| In `artifact.digest`? | **yes**, through `heteroplasmy.parquet` |
| In the attestation binding? | **yes** — in `compiler._INPUT_FILES` (`compiler.py:267`), so in `manifest.inputs[]` (raw bytes) *and* in `authored_input_entries` (newline-normalized, RM82) |
| Parquet width | 25 columns, measured on `reference_examples/mt_heteroplasmy`: the 22 authored ones plus injected `module` plus stamped `variant_key`/`authored_ident` |

**Two worked reference examples, and read both.** `reference_examples/mt_heteroplasmy` is the
two-variants-in-one-gene case (MT-TL1 m.3243A>G and m.3271T>C, blood and muscle, 10 rows, grounded by
`studies.csv`). `reference_examples/mt_common_deletion` is the harder one: it carries a **symbolic
allele** (`<DEL:4977>`), grounds every threshold by `pmid` on the bin row rather than by identity, and
puts three bins on one variant where the *disease changes with the level* (m.8993T>G: subclinical →
NARP → Leigh syndrome).

> ⚠️ **CHECK — it is not the only example on the `pmid` route.**
> **Current state.** Measured across `reference_examples/`: `fmr1_cgg_repeat/repeat_alleles.csv`
> (4 rows, PMID `23099194`), `cyp2d6_structural/copynumbers.csv` and
> `cyp2d6_structural/activity_phenotype.csv` (4 rows each, PMID `26479518`) all carry a filled bin
> `pmid` as well. **Four** examples use RM47's route, not one.
> **Expected state.** What *is* singular about `mt_common_deletion` is the combination — symbolic
> allele plus three bins on one variant plus grounding by `pmid` — so read it as the richest example
> of the route rather than the only one.

## Who populates what

- **author — everything that means anything.** `gene`, `reference_sequence` and `conclusion` are the
  three always-required columns; `measure_min`/`measure_max` (see gotcha 3 for why they read as
  merely optional), `tissue`, `assay_context`, `measure_tiling`, `direction`, `clin_sig`, `phenotype`,
  `trait_efo_id`, `unresolved`, `source_field`, `source_element`, `pmid`, and the identity set
  `rsid` / `chrom` / `start` / `ref` / `alts`. Run `table_requirements("heteroplasmy.csv")` for the
  live list; as of format 0.6.1 it reports `always: [conclusion, gene, reference_sequence]`,
  `defaulted: {measure_kind: allele_fraction, unresolved: false}`, `any_of: []`.
- **drafter — none, ever.** Confirmed in the installed enricher: no drafter writes this file. Every
  row here is hand-authored or AI-co-authored. `get_template("heteroplasmy.csv", stub=True)` gives you
  a 22-column header with `measure_kind` pre-filled, `<<REPLACE>>` in exactly three cells
  (`conclusion`, `gene`, `reference_sequence`), an appended `unresolved=true` sentinel row — and
  **empty** `measure_min`, `measure_max`, `tissue`, `pmid`, `trait_efo_id` and the whole identity set.
  The two columns that carry the design (`tissue`, the variant identity) are not flagged.
- **enricher pass — none writes into this file.** `enrich` reads it to collect resolution *subjects*
  (`enricher/…/enrich.py:187-203`) and writes `resolution.csv`; `literature` reads
  `MeasureBinRow.pmid` through `compiler.load_binning_rows` / `binning_citations`
  (`literature.py:761`, `compiler.py:1779,1811`) and writes `literature.csv`. Inject-only doctrine: no
  pass mutates an authored cell.
- **compiler-stamped (tolerates an authored value and overwrites it)** — `variant_key` and
  `authored_ident`, both via `base.stamped_identity_field` (`binning.py:666,676`), so both are
  `COMPILER_MANAGED`, `exclude=True` (outside `content_signature`), absent from `describe_table`, and
  re-emitted as nothing by `reverse_module`. A CSV that ships its own `variant_key` column does not get
  to declare its own identity — the value is silently replaced (`base.stamp_identity`).
- **compiler-*filled*, and this is the subtle one** — `chrom` / `start` / `ref` / `alts` are
  **authored** columns here, and the compiler fills the ones you left empty from the injected
  `resolution.csv` (`resolution.resolve_positional_rows`, `resolution.py:299-360`; RM43). Fill-only-what-is-empty,
  fill-from-exactly-one-locus-or-none, and a row whose own coordinate contradicts the table is
  *reported, never repaired*. `base.reject_compiler_filled` does **not** apply here — its error message
  names `heteroplasmy.csv` as one of the two tables where these cells *are* authored. `reverse_module`
  re-blanks whatever `authored_ident` does not name (`compiler.py:492-520`), which is what keeps
  `content_signature` stable across a round trip.
- **registry-stamped — nothing.** `normalize.IDENTITY_AUTHORITY_KEYS` covers the `module:` block of
  `module_spec.yaml`, not table cells.
- **nobody, ever — nothing.** Every column here is authorable or stamped; there is no permanently
  unwritten column.

**Cells no tool may fill.** Of this table's 22 authored columns, seven are in
`hints.REDUNDANCY_BEARING` (verified against the installed `just_dna_compiler.hints`): `clin_sig`,
`pmid`, `rsid`, `chrom`, `start`, `ref`, `alts`. `describe_table("heteroplasmy.csv")` prints the
reason per column — e.g. `clin_sig` → *"enricher.clinical.verify_clin_sig (authored call vs
ClinVar's)"*, `pmid` → *"enricher.literature (authored pmid vs PubMed's record: LiteratureRow.exists)"*,
`ref` → *"enricher.sequences.verify_reference_alleles (authored ref vs the genome)"*. Fill one of
those from the source that later checks it and the check compares a convention against itself. A
`lookup_variant` / `lookup_citation` result reports the value with `applied: false` and a `refusal`;
carry the refusal, do not write the cell.
`hints.ATTESTATION_BEARING` is `{provenance_quote, provenance_regex}` and has **no intersection with
this table** — those columns live on `studies.csv`.

**And the hole worth naming: the threshold itself is redundancy-bearing under no map.**
`measure_min`, `measure_max`, `measure_kind`, `measure_tiling`, `tissue`, `reference_sequence`,
`assay_context`, `conclusion` and `unresolved` are in neither set. The number an author actually
decides — *where 30% rather than 40%* — has no cross-check anywhere in the toolchain. `pmid` (RM47) is
the only thing that grounds it, and it is optional.

## What moving this table moves

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row / delete a row | **moves** | n/a (none) | **moves** | **dropped** — module un-closed |
| edit an authored cell (`source_field` `FORMAT/AF`→`AF`) | **moves** | n/a | **moves** | **dropped** |
| edit a group-key cell (`tissue` `blood`→`whole_blood`) | **moves** | n/a | **moves** | **dropped** |
| edit a *stamped* cell (`variant_key`, `authored_ident`) | unchanged | n/a | unchanged | unchanged — overwritten at load |
| reorder rows | **unchanged** | n/a | **moves** | **dropped** |
| rewrite the file with CRLF terminators | unchanged | n/a | unchanged | **unchanged** (RM82) — but `manifest.inputs[heteroplasmy.csv].sha256` **moves** |
| append an `authorship:` entry to `module_spec.yaml` | unchanged | n/a | unchanged | **dropped** |
| re-run `enrich` so `resolution.csv` appears (the RM43 fill) | **unchanged** | `resolution_signature` moves | **moves** | unchanged — `resolution.csv` is outside the binding |
| delete `resolution.csv` and re-derive it | unchanged | `resolution_signature` may move | **moves** | unchanged |
| recompile under a newer toolchain | unchanged | n/a | **may move** | unchanged |

All measured on format/compiler 0.6.1 against `reference_examples/mt_heteroplasmy`. Baseline
`content_signature sha256:9b22b978…`, `artifact.digest sha256:c905c762…`, `manifest.verification`
present with a closure, **zero** compilation warnings, and byte-identical on a second compile.
`FORMAT/AF`→`AF` on all ten rows gave `49ac5813… / 9145e8a4…` and no verification block. A pure row
reversal gave `9b22b978… / 7e255043…` — content identical, digest moved. A CRLF rewrite reproduced
both hashes exactly while moving that file's `manifest.inputs` entry from `sha256:f0285cf7…` to
`sha256:dc4fd58b…` and keeping the closure. An `authorship:` append moved neither hash and dropped the
closure. The RM43 row was measured on a purpose-built rsid-only module: identical
`content_signature sha256:d48f791e…` with and without `resolution.csv`, and
`artifact.digest sha256:2d88f849…` (fill applied, `positional_rows 3 / placed 3`) versus
`sha256:247a3aef…` (no table, `3 / 0`).

1. **Inside `content_signature`?** Yes — authored table, rows hashed as parsed
   (`model_dump(mode="json", exclude_none=True)`, sorted), so the signature is **order-independent**
   and blind to CSV formatting and to an unset optional column. `variant_key`/`authored_ident` are
   `exclude=True` here and stay out, unlike `VariantRow`'s grandfathered pair (`base.py:297-305`) —
   which is why a coordinate fill cannot move this table's content identity.
2. **Inside `artifact.digest`?** Yes, through `heteroplasmy.parquet`, and the digest **preserves
   authored row order** where `content_signature` does not. It also carries the *stamped* and *filled*
   columns, so the digest moves for changes the content signature cannot see — the `resolution.csv`
   row above is exactly that.
3. **Does an edit here un-close the module?** Yes, for any byte change other than line endings:
   `heteroplasmy.csv` is an authored input, so `module_binding(authored_input_entries(spec_dir))` moves
   and the whole `manifest.verification` block including the closure is withheld, with the stale-attestation
   warning naming both hashes. Note the asymmetry both ways: a CRLF rewrite changes bytes and keeps the
   closure, and an `authorship:` append moves no identity at all and drops it.
4. **Part of the §5.1 canary?** **No.** The canary is *content unmoved + a **fact** signature moved*,
   and this table has no fact signature, so it can never produce that reading directly. It can produce
   canary **row 2** (content unmoved, digest moved) three ways: a bare row reorder, a toolchain change,
   and the RM43 coordinate fill appearing or disappearing — the third is the one worth watching,
   because it means the *coordinates* under your bins changed without a word from the content
   signature. Detecting upstream drift in those coordinates requires delete-and-re-derive of
   `resolution.csv`: merge-not-clobber never re-asks (`MODULE_LIFECYCLE.md` § 5.1).

## Required to exist

- **Nothing drags it in, and it drags in nothing.** A module carrying only `heteroplasmy.csv` is
  legal and complete: composition requires *at least one* recognized table (`compiler.py:3602`), and
  `heteroplasmy.parquet` is a `LEAD_PARQUETS` member, so it satisfies a consumer's "is this a module"
  probe on its own. Measured: a three-row heteroplasmy-only module with no `variants.csv` and no
  `studies.csv` validated with **zero** errors.
- **`studies.csv` is required iff `variants.csv` is present** (`compiler.py:3624-3637`) — so a
  heteroplasmy-only module is exempt. The comment there is worth reading: the exemption is *not*
  because binning rows carry their own evidence (they do not), it is because `StudyRow` could only
  name a variant, so for a gene-keyed table the requirement would be unsatisfiable rather than merely
  unmet (S19 / RM47).
- **What you get instead is a warning.** `_check_binning_grounding` (`compiler.py:1380-1470`) fires
  only when the module records **no** `studies.csv` rows at all *and* some resolved bin has no `pmid`.
  Measured message: *"heteroplasmy.csv: 2 of 2 bin(s) state a threshold and the module records no
  grounding evidence at all (no studies.csv rows, no bin pmid)"* with **two** remedies, because this
  is the one binning kind that can be pointed at by identity as well as by `pmid`. A bin carrying a
  `pmid` is grounded and is not counted. Naming a variant is **not** a second route — that exemption
  was removed as vacuous (D1-3, `mt_common_deletion` README finding 3).
- `module_spec.yaml` is required, as always, and `genome_build` matters: the fill and the VRS minting
  are GRCh38-only (RM15), so a non-GRCh38 heteroplasmy module is skipped with a warning and keeps the
  coordinates its author typed (`compiler.py:1190-1197`).

## The columns that carry judgement

- **`measure_min` / `measure_max`** — the whole point of the table, inclusive at **both** ends on
  every kind. `min == max` is a sharp value, a null bound is open. Constrained to `[0, 1]`; a bound
  outside raises *"allele_fraction bounds must be within [0, 1]"*. No tool checks the number.
- **`unresolved`** — the mandatory (by contract, not by validator) sentinel row for *measurement
  absent*. A consumer with no reading selects it, **never** the lowest bin: no heteroplasmy read is not
  a homoplasmic-reference read. It carries no bounds; one per key group maximum. This is the
  three-valued algebra made into a row.
- **`tissue`** — optional in the schema, load-bearing in fact, and part of the group key. The same
  fraction bins differently in blood and muscle: `mt_heteroplasmy` puts the m.3243A>G threshold at
  0.3 in blood and 0.4 in muscle, and its low-blood conclusion tells the reader to measure urine or
  muscle before reassuring anyone. A heteroplasmy table with no tissue is quietly unsafe.
- **`reference_sequence`** — required, part of the key, free text with one landmine rejected. `rCRS`
  / `NC_012920.1` and the legacy `NC_001807` lineage disagree on coordinates *and* bases and yield a
  confidently-wrong haplogroup, so `NC_001807*` raises. Write `NC_012920.1`.
- **`variant_key` (through `rsid`/`chrom`/`start`/`ref`/`alts`)** — optional, and the thing that
  makes a two-variant gene expressible at all. See gotcha 1.

> 🚧 **ROADWORKS — the sentinel and the bins it is meant to cover can sit in different groups.**
> **Current state.** `trait_efo_id` is part of the bin-group key (`_bin_groups` appends it), and so
> are `tissue` and `variant_key`. An `unresolved` row written with those cells blank is therefore a
> sentinel for the group `(gene, reference_sequence, None, None, None)` — **not** for the groups its
> bins are in. Nothing objects: the compile-path rule only refuses a *second* sentinel in one group,
> and the authoring hint only asks whether the **table** has one anywhere. So a table can look
> complete and leave every real bin group with no no-call row.
> **Expected state.** No rule says which sentinel a consumer selects when the groups do not line up,
> and there is no consumer implementing sentinel selection at all yet — so the ambiguity is
> unresolved in both senses.
> **Guard.** Write **one sentinel per bin group**, repeating that group's `tissue`, `variant_key` and
> `trait_efo_id` cells verbatim, and leaving only the bounds empty. Group your rows on paper first;
> neither surface will do it for you.
- **`source_field` + `source_element`** — a declarative *pointer* at where the consumer reads the
  measurement, never an expression. `FORMAT/AF` + `source_element=annotated_alt` is the authored
  answer for both mito reference examples. See gotcha 2.
- **`pmid`** — the boundary citation (RM47, 0.6). It grounds *this threshold*, not the module: the bin
  row cites, `studies.csv` describes. Free-form like `StudyRow.pmid`. Take it from a
  `literature_search` result, never from memory.
- **`trait_efo_id`** — in the group key even though `_KEY_FIELDS` does not list it. Two bins that
  overlap under different `trait_efo_id` are legal pleiotropy (measured). Do **not** reach for it to
  separate two variants — see gotcha 1.
- **`measure_tiling`** — leave it empty. Empty means the kind's default, which for `allele_fraction`
  is `continuous`. Writing `quantised` here is actively harmful (gotcha 5).
- **`assay_context`** — optional, documented as load-bearing beside `tissue`, and **not in the key**
  (gotcha 6).

## Gotchas

Ordered by how likely a first-timer is to hit them.

**1. Two variants in one gene collide, and `trait_efo_id` is not the way out.** Before 0.5.1 the key
was `(gene, reference_sequence, tissue)` with no variant identity at all, so MT-TL1's m.3243A>G and
m.3271T>C landed in one group and `validate_bins` refused the module — an **error**, so it would not
compile. Measured today with the identity columns left empty:
`overlapping bins for key ('MT-TL1', 'NC_012920.1', 'blood', None, None): [0.0, 0.099] and [0.0, 0.149]`.
`trait_efo_id` is in the group key and would separate them, but both variants cause MELAS, so using two
ontology ids means falsifying the data to satisfy the tool. **Fill `chrom`/`start`/`ref`/`alts` (or
`rsid`) on every row of a table that describes more than one variant.** With them filled, the same two
bins validate clean. MT-ATP6 m.8993T>G vs m.9176T>C is the same shape one gene over, and m.8993T>G vs
m.8993T>C is why `alts` is in the key.

**2. `source_field=AF` is the wrong `AF`, and nothing catches it downstream.** Both mito reference
examples shipped `AF` and `DP` bare and both were wrong. `INFO/AF` is the *cohort* allele frequency of
that ALT; `FORMAT/AF` is *this sample's* fraction of it. Both are floats in `[0, 1]` and both bin
cleanly against `0.0–0.1 / 0.1–0.3 / 0.3–1.0`, and one of them tells a carrier they are asymptomatic on
the strength of how rare the variant is in a reference panel. The compiler now warns — measured:
*"10 VCF pointer cell(s) name a key that INFO and FORMAT both define … Qualify the pointer"* — but a
bare key is still **legal** and still means unqualified, so this is a warning, not a refusal. Write
`FORMAT/AF`, and `source_element=annotated_alt` because `FORMAT/AF` is one value per ALT.
`FORMAT/AF` earns no *cardinality* warning, ever: the spec reserves `INFO/AF` and does not reserve
`FORMAT/AF`, so the compiler has no `Number` to assert and withholds — which is why the reference
example authors `annotated_alt` deliberately rather than being prompted. The mirror error is one
column over on `variants.csv`: `callable_from=FORMAT/DP`, not `DP`.
`REFERENCE_EXAMPLES.md` § 4 still prints `source_field=AF` in its illustration — read the built module,
not the doc snippet.

**3. `table_requirements` will not tell you a bin needs a bound.** `MeasureBinRow._validate_range`
enforces *"a resolved bin needs at least one of measure_min/measure_max"* and *"an unresolved row
carries no measure_min/measure_max"* — but `HeteroplasmyRow.REQUIRED_ANY_OF` is `()` (verified), so
`table_requirements` / `authoring_reference` / `draft.required_fields` report both bounds as plain
`optional` and say nothing about the disjunction. This is exactly the drift `REQUIRED_ANY_OF` was
introduced to close on `VariantRow`, and it is not closed here. Flagged upstream-shaped below.

**4. A row that names an allele but no position keys as if it named nothing.** Measured: `ref="A",
alts="G"` with no `chrom`/`start` gives `variant_key = None` and `authored_ident = ['ref','alts']` —
`base.stamp_identity` returns early unless `rsid` or `start` is set. So the row silently joins the
gene-only group and collides with every other variant's bins. `alts` alone does not identify anything.

**5. Declaring `measure_tiling: quantised` on this table switches gap reporting off entirely.**
`quantised`'s step is hardcoded to whole numbers and there is no `measure_step` column, so on a domain
bounded by `[0, 1]` no hole can ever exceed one. Measured: bins `[0.0, 0.1]` and `[0.2, 0.3]` under
the default reported `coverage gap … no bin covers (0.1, 0.2)`; the identical pair declared `quantised`
reported **no gap** — only the separate *"declared 'quantised' and the data contradicts it"* warning,
because a fractional bound is not a grid point. The declaration **stands**; nothing overrides it. This
is documented on the column's own description and it is a limit, not a tightening. Leave the column
empty.

**6. `assay_context` is not in the key, so it cannot separate two assays.** Measured: two otherwise
identical rows differing only in `assay_context` (`WGS` vs `amplicon`) raise
`overlapping bins for key ('MT-TL1', 'NC_012920.1', 'blood', 'ga4gh:VA.J9tZ…', None)`. The model
docstring calls `tissue`/`assay_context` jointly "optional but load-bearing", which reads as though
both discriminate. Only `tissue` does. If your bins genuinely differ by assay, there is nowhere to
put that today.

**7. `reference_sequence` is a group key with no vocabulary, so a spelling variant splits a group
silently.** Measured: three rows with `NC_012920.1`, `NC_012920` and `rCRS` and *identical* bins
produced **zero** findings — three groups, one reference. Only the `NC_001807` stem is rejected. The
format defines `binning.CANONICAL_MT_REFERENCE_SEQUENCES = {"NC_012920.1"}` (`binning.py:575`) and
**no code reads it**. `tissue` and `gene` have the same exposure (`blood` vs `Blood` measured as two
groups). Pick one spelling per module and grep for it before you compile.

**8. An rsid-authored row does not mint a VRS id.** `derive_variant_key` short-circuits on `rsid`
(case 1, `base.py:227-280`), so `variant_key` stays the rsid. Measured: an rsid-authored row keys
`rs199474657`, while the coordinate-authored m.3243A>G keys
`ga4gh:VA.J9tZBPJHObSDmLtUrywDERwHt2LXGIr-` and m.3271T>C keys `ga4gh:VA.LQzSis117nNBV1Z4_t19RM7EdZfl9wYH`.
A symbolic allele (`<DEL:4977>`) is unmintable *permanently* and keys `MT:8470:N:<DEL:4977>` — the
compiler now says so with its own reason class rather than telling you to re-run online. So "this table
can mint a VRS id" is true only for a coordinate-authored single-base substitution.

**9. A lengthless symbolic allele is fatal in both modes here, and droppable on `variants.csv`.**
`_SYMBOLIC_DROPPABLE_TABLES` is `{variants.csv, pharm_variants.csv}` (`compiler.py:2326`). Measured on
`mt_common_deletion` with `<DEL:4977>`→`<DEL>`: an error at `strict=False` *and* `strict=True`, with
the reason in-line — *"a heteroplasmy.csv row is part of a composite (a haplotype's definition, a bin
tiling), so dropping it would not make a smaller module but a quietly different one"*. Spell the
length.

**10. The contig is not validated on this table.** `variants.csv` refuses anything outside 1-22/X/Y/MT
at the model; `heteroplasmy.csv` runs no `chrom` validator (`binning.py:611-613`, deliberate — "no
`chromosome` vocabulary marker, matching the other tables that run no chrom validator"). Measured:
`chrom="7"` is accepted and mints a VRS id on chromosome 7. What *is* checked is the position against
the contig length (RM48): a row at `chrM:16600` is refused because GRCh38's MT is 16,569 bp.

**11. Compare in float32, not float64 (RM62), and this is the consumer's obligation.** A VCF `Float`
is 32-bit. A measured `0.3` widens to `0.300000011920928955…`, strictly **above** an authored
inclusive `measure_max` of `0.3`; a measured `0.9` widens to `0.899999976158142…`, strictly **below** a
`measure_min` of `0.9`. Both directions lose a row, so neither bound is the safe one. The rule is to
narrow the bound the same way the measurement was narrowed
(`struct.unpack("f", struct.pack("f", bound))[0]`) and compare in float32 — never an epsilon, never
narrowing only the bound. `mt_heteroplasmy`'s boundaries (`0.1`, `0.3`, `0.4`, `0.15`) are exactly the
exposed decimals. Nothing in the toolchain enforces this; it is a contract on a consumer that does not
exist yet.

**12. `measure_kind` accepts a separator slip.** Measured: `allele-fraction` is accepted and stored as
the declared member `allele_fraction` (RM95 — `check_vocab` canonicalizes `-` for `_`). Deliberate;
the cell is not being ignored.

**13. RM55/RM56 never fire here, and the second absence is real.** `measurement_shape_warnings` is
scoped to `_VCF_MEASURE_FIELDS`, which holds only `copy_number` and `repeat_count`
(`binning.py:213-232`), so an `allele_fraction` table gets neither the fractional-grid warning (it does
not need one — `continuous` is its default) nor the *"one measurement can span several bins"* warning.
The spanning problem is not absent, only unreported: `FORMAT/AF` carries depth uncertainty and the
format has no state for a measurement that spans bins. House default — the consumer **withholds**.

## What does not exist

- **No consumer-side lookup.** The rule *select the row with the greatest `measure_min ≤ x` within the
  group* is written down in three places and implemented in none. See **Consumption today**.
- **No `measure_step` column**, so `quantised` cannot express a finer grid. A full-cost authored
  column nobody has asked for; it waits for the demand that would fix its shape (P5's one-way door).
- **No half-open `[min, max)` for continuous kinds.** Refused, with reasons: `measure_max` would mean
  two different things depending on `measure_kind`, the number in the cell would not be in the bin,
  and a bounded domain's top value (`AF = 1.0` is homoplasmy, and real) becomes unreachable unless the
  last bin is authored open. `measure_max` is inclusive on every kind and the top bin stays closed.
- **No sixth `measure_kind` for the continuous/quantised product** (`copy_number_continuous`), and no
  quiet move of the fraction kinds into `_DENSE_KINDS`. Both refused: the first is the
  overloaded-field anti-pattern, the second silently re-reads every published table.
- **No policy vocabulary for a spanning measurement** (withhold / worst bin / point estimate). RM56,
  deferred until a real caller VCF is in hand. Widening the *measurement* into an interval is refused
  permanently — that puts a measurement in the module.
- **No `bin_evidence.csv` join table.** Refused: it would have to key on the thresholds, and they are
  floats. `pmid` on the row is the answer instead, carrying a pointer only — population, `p_value_num`,
  `effect_size` and the provenance columns stay in `studies.csv`.
- **No `--no-ensembl` flag on the compiler.** Refused upstream with a reason: the compiler has no
  network branch, so the flag would assert something false.

  > ⚠️ **CHECK — resolution *can* be turned off; it is a default, not a pin.**
  > **Current state.** `compile_module(..., resolve_with_ensembl: bool = True, ...)` is a **default
  > argument**, and the CLI wires `--resolve/--no-resolve` straight to it (`compiler/…/cli.py`).
  > `--no-resolve` skips resolution of every kind, including this table's.
  > **Expected state.** The surrounding point stands and is the one that matters: there is no
  > `--no-ensembl`, and the parameter's name understates its reach — it is the master switch for
  > **all** resolution, not just the Ensembl leg. Turning it off leaves every positional row
  > unresolved, which is a different module, not a faster compile.
- **No expansion of a one-to-many rsid on this table.** `variants.csv` expands into N coordinate-keyed
  rows; a positional table does not — that would multiply a bin across loci the author never named.
  Several candidate loci means the row stays unplaced and is counted.
- **No cross-check on a threshold**, and **no dedup key** (two byte-identical resolved rows are caught
  as an overlap, so the message talks about phenotypes rather than a repeated row).
- **No tissue vocabulary, no `assay_context` in the key, no `reference_sequence` allow-list.**

## Consumption today

**Nothing bins a measurement. Not one consumer, not even a stub.** Across `just-dna-lite`,
`just-dna-registry`, `just-dna-marketplace`, `just-prs` and `just-prs-mcp` there is no `argmax`,
`join_asof`, `searchsorted`, `bisect` or *greatest `measure_min ≤ x`* anywhere; the string
`allele_fraction` does not appear in any consumer at all, and `measure_min`/`measure_max`/`MeasureBinRow`
appear only inside two `pyproject.toml` floor-pin comments and CHANGELOG prose.

Every read site treats `heteroplasmy` as an opaque table **name**:

- `/data/sources/just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/module_config.py:499,514,518-534`
  — `"heteroplasmy"` in `LEAD_TABLES`; `find_lead_table` / `has_lead_table` probe
  `heteroplasmy.parquet` **for existence only**.
- `/data/sources/just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/annotation/hf_logic.py:222-250`
  — **where it dies.** `_lead_join_strategy` classifies a binning table `unsupported` (no populated
  `chrom`/`start`, no `rsid`+`genotype` pair), the per-module loop records `UnsupportedLeadTable`, and
  the module is skipped. `just-dna-lite/CLAUDE.md:471` documents this as intentional.
- `hf_logic.py:151-177` (`_normalize_vcf_contigs`, folds `chrM`→`MT`, motivated by mito but generic);
  `hf_modules.py:157-199,527` (the fsspec twin, building a `heteroplasmy.parquet` URL on HF);
  `report_logic.py:1296-1312` (report-card routing — only `pharm_variants` and `longevitymap` get
  bespoke builders, heteroplasmy falls to the generic one, no measure rendering anywhere). All under
  `/data/sources/just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/annotation/`.
- `/data/sources/just-dna-lite/webui/src/webui/state.py:6017,6043-6051` — counts **lines** of
  `heteroplasmy.csv` to route `/check` between enrich and validate. Line count, not parse.
- `/data/sources/just-dna-registry/src/just_dna_registry/specfiles.py:61` — `heteroplasmy.csv` in
  `TABLE_KIND_CSVS`, flowing into `SPEC_DATA_FILES`, `RECOGNIZED_SPEC_FILES` and `SIGNATURE_INPUTS`:
  a legal upload part, hashed into the module signature. Name-level only.
- `/data/sources/just-dna-registry/src/just_dna_registry/services/upgrade.py:34,156,180-200` — imports
  `HeteroplasmyRow` solely for `set(model.model_fields)`, to detect and trim unknown CSV columns. It
  never validates a value.
- `/data/sources/just-dna-registry/src/just_dna_registry/services/enrich.py:352,356-375` —
  `heteroplasmy.csv` in `ENRICHMENT_SUBJECT_TABLES`; its **row count** feeds the pre-flight bound that
  gates `422 too_many_variants`.
- `/data/sources/just-dna-registry/src/just_dna_registry/db/facets.py:53,183-240` +
  `db/schema.py:283-295` — the only binning-adjacent facets are `positional_rows` /
  `positional_rows_placed`, two integers copied out of `manifest.compilation`. The registry never
  learns which table they came from, so **catalog search cannot filter for "modules with heteroplasmy
  bins"**, and no module card mentions the table.
- `just-prs` and `just-prs-mcp` — **zero hits**, all sixteen search terms.

Net: a heteroplasmy-led module today is discoverable, listable, publishable, digest-covered,
signature-hashed — and annotates nothing.

## Blanks for just-dna-lite

- **Implement the one lookup rule.** *Select the row with the greatest `measure_min ≤ x` within the
  group `(gene, reference_sequence, tissue, variant_key, trait_efo_id)`, comparing in float32.* One
  function serves all four binning kinds; `binning.DEFAULT_MEASURE_TILING` is the table it reads for
  shared-endpoint and gap semantics. **What breaks today:** `hf_logic._lead_join_strategy` classifies
  the whole binning family `unsupported`, so every published binning module is skipped with a recorded
  reason. Two reference modules and a whole schema family annotate nothing.
- **Route an absent measurement to the `unresolved` sentinel, and say so.** Three states, and only
  three: a bin matched, no bin matched, the measurement absent. **What breaks today:** nothing reads
  the sentinel, so a consumer that later adds naive binning will fall to the lowest bin and report
  "asymptomatic carriage" for a sample that was never measured — the precise failure `unresolved`
  exists to prevent, and the reason `mt_heteroplasmy` authors one per group.
- **Take the measurement from `source_field` + `source_element`, and honour the namespace.** Read
  `FORMAT/AF` element `annotated_alt`, not a bare `AF`. **What breaks today:** the pointer columns
  have **zero** occurrences in any consumer repo, so any future implementation will guess — and the
  guess that reads `INFO/AF` reports a carrier as asymptomatic on the strength of a reference panel's
  allele frequency. The columns exist precisely so the consumer does not have to guess.
- **Condition on `tissue` before answering.** The sample's tissue of origin is already in the annotate
  UI's own config; it is simply never joined to a bin row's `tissue`. **What breaks today:** nothing,
  because nothing bins — but the moment something does, ignoring `tissue` collapses two group keys
  into one wrong answer, and `mt_heteroplasmy` puts the same variant's threshold at 0.3 in blood and
  0.4 in muscle.
- **Withhold on an interval that spans bins.** Not implemented anywhere and not decided upstream
  (RM56); the house default is stated — withhold, do not pick, do not fall back to `unresolved`.
  **What breaks today:** a first implementation will silently pick a bin for an uncertain measurement.
- **Give the registry a table-kind facet.** `positional_rows` is the only signal a catalog gets, and
  it does not say which table produced it. **What breaks today:** a reader cannot search for
  mitochondrial or binning modules at all, and a module card is silent about a lead table it carries.

## Ask the live schema

Every column list, vocabulary and requirement above drifts with each release. As of format 0.6.1:

```
describe_table("heteroplasmy.csv")      # columns, categories, vocabularies, redundancy_bearing reasons
table_requirements("heteroplasmy.csv")  # always / any_of / defaulted / optional
authoring_reference()                   # whole-schema: vocabularies, vocabulary_notes, required_any_of
get_template("heteroplasmy.csv", stub=True, rows=3)
lint_rows("heteroplasmy.csv", …)        # runs validate_bins + the sentinel check, offline
```

CLI equivalents, when driving the compiler directly:

```bash
just-dna-compiler describe heteroplasmy.csv
just-dna-compiler reference
just-dna-compiler validate <spec-dir> --strict
```

Read from code, never from this file, when you need to be certain:
`binning.VALID_MEASURE_KINDS`, `binning.VALID_MEASURE_TILINGS`, `binning.DEFAULT_MEASURE_TILING`,
`binning.LEGACY_MT_REFERENCE_BASES`, `HeteroplasmyRow._KEY_FIELDS`, `vocab.VALID_ELEMENT_RULES`,
`vocab.VCF_COLLIDING_KEYS`, `hints.REDUNDANCY_BEARING`, `hints.ATTESTATION_BEARING`.
