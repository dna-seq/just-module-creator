# The just-dna domain

What a module *is*, what the four packages we wrap guarantee, and the traps that
constrain what this repo may build. Read it before changing a tool signature, a
docstring or the skill: every tool here is a promise about one of the rules
below, and a wrapper that quietly breaks one is worse than no wrapper.

Distilled from two independent write-ups of real module-creation experience,
made against different surfaces so that each reached traps the other missed.
Both are unified into `skills/create-module/`, which is the canonical copy of
the authoring *procedure* — this file carries the *facts* the procedure rests
on, and does not restate it.

**Prohibitions derived from this file live in `CLAUDE.md`, in full.** Nothing
here is the only statement of a `don't`.

## What this repo is


An MCP server **plus** a Claude Code skill that together help an agent author
just-dna annotation modules. We are the *authoring surface*; we own no schema.
Every column list, vocabulary and requirement is generated from the live pydantic
models in `just-dna-format`, so it cannot drift from what the compiler accepts.

**Never restate a schema fact in our own code, docstrings or skill text.** Call
`describe_table` / `table_requirements` / `authoring_reference` and pass through
what they return. A hardcoded vocabulary here is a bug waiting for the next
upstream release.

### The four packages we wrap

The dependency arrow points inward — **enricher → compiler → format** — and only
the enricher may touch the network.

| Package | Gives us | Never does |
|---|---|---|
| `just-dna-format` | schema models, vocabularies, identity + integrity rules. No CLI. | touch the network |
| `just-dna-compiler` | spec dir → parquet + `manifest.json`; scaffold, describe, hint, validate, reverse, sign | touch the network |
| `just-dna-enricher` | resolution, VRS minting, drafting from sources, cross-checks, lookups | decide what a variant *means* |
| `just-dna-registry` | catalog / publish / download REST client for `module-registry.just-dna.life` | — |

Python ≥ 3.13 (the just-dna packages require it; that is why `requires-python`
moved up from the template's 3.11).

---

## What a module is

A directory of **human-authored CSVs plus `module_spec.yaml`**, compiled into a
parquet artifact with a content-addressed `manifest.json`. It carries
**annotation only** — lookup tables mapping a genotype or a measured quantity to
a phenotype. It never holds a sample, a genotype under test, or a measured
value: the consumer supplies the measurement at query time.

```
spec/
  module_spec.yaml     # the ONLY always-present file
  variants.csv         # a lead table — or pharm_variants.csv, diplotypes.csv, pgs.csv …
  studies.csv          # required IFF variants.csv is present
  resolution.csv       # produced by `enrich`. Commit it.
  literature.csv       # produced by `literature`. Commit it.
  sources.csv          # required when data came from a licence-bearing source
  logo.png             # optional
```

**A module composes from optional table kinds.** At least one recognised table
must exist. A PGx / PRS / binning module carries only its own tables and **no
`variants.csv`** — adding an empty one "to look complete" is exactly the mistake
the composition rule exists to prevent. One CSV = one concern.

`studies.csv` is mandatory whenever `variants.csv` exists: grounding evidence is
not optional.

### Choosing the table kind

The question is **what is the row's subject** — not what data you happen to have.

| The row is about… | Table | Keyed on |
|---|---|---|
| one variant + one genotype | `variants.csv` | `(variant_key, genotype)` |
| the evidence for a variant | `studies.csv` | `(variant_key, pmid)` |
| which variants make up a named allele | `haplotypes.csv` | `(haplotype_name, variant, allele)` |
| what a named allele *does* | `allele_function.csv` | `(gene, allele)` |
| a **pair** of alleles (a diplotype) | `diplotypes.csv` | `(gene, a, b, trait, drug, clinical_context)` |
| one variant + one drug | `pharm_variants.csv` | `(variant_key, drug, genotype, category, annotation_id)` |
| a metabolizer **activity score** range | `activity_phenotype.csv` | `(gene)` |
| a **copy number** range | `copynumbers.csv` | `(gene, modifier_gene, modifier_cn)` |
| a **repeat count** range | `repeat_alleles.csv` | `(gene, repeat_unit)` |
| an mtDNA **heteroplasmy fraction** range | `heteroplasmy.csv` | `(gene, reference_sequence, tissue, variant_key)` |
| a published polygenic score | `pgs.csv` | `(pgs_id, trait)` |

Enricher-produced sidecars nobody hand-authors: `resolution.csv`,
`frequencies.csv`, `gene_metrics.csv`, `literature.csv`, `sources.csv`. The one
exception is `sources.csv` when rows were copied out of a source by hand — no
pass ran, so no pass will write the row, and the compile gate reads that file
and nothing else.

**A quantity with a threshold is a binning table, not a variant row.** If the
finding depends on *how much*, the subject is the measurement.

**Two alleles on one chromosome vs one on each is a haplotype vs a diplotype.**
`haplotypes.csv` is a junction table (one row per defining variant);
`diplotypes.csv` pairs two haplotypes, which is what *in trans* means.

---

## The pipeline, and the one place deviating deadlocks

```
scaffold ──▶ draft ──▶ curate ──▶ enrich ──▶ check ──▶ compile ──▶ sign/publish
            (if a       (only a
             source      human)
             has it)
```

**Curate before you enrich.** A drafted row leaves `<<REPLACE>>` in the cells
only a human can decide, and that placeholder makes *every* loader refuse the
file — `enrich` included. That is deliberate: forward resolution is allele-aware,
and a placeholder genotype would silently skip the allele filter on exactly the
one-to-many rsIDs that need it. You cannot "enrich first to see the alleles" —
and you don't need to, because the draft report prints the allele pair for each
stubbed row.

Only `enrich` and the fact passes use the network. Once `resolution.csv` and
`literature.csv` exist they *are* the pin: every later compile is offline and
reproducible.

---

## Requiredness has three shapes, and the middle one is invisible

`required` / **`defaulted`** / `optional`. A **defaulted** column
(`measure_kind`, `unresolved`) is not required *and must not be left empty*: an
empty cell arrives as `None` rather than as the field's default, and fails on
type with `Input should be a valid string [input_value=None]` on a column nobody
told you to fill.

Always read `table_requirements` (`draft.authoring_requirements`), never
pydantic's `is_required()` alone. It also reports the **one-of** rules
("rsid **or** chrom+start") that no per-field flag can express.

`<<REPLACE>>` is rejected *before* type coercion, so an unreplaced placeholder in
an `int` column reads as "unreplaced template placeholder in column start", not
as a number-parsing error. That is the design: a half-filled table fails loudly
on the rows still to do.

---

## The mistake nothing offline can catch

Worth its own section because it happened at scale, to a careful author, on 3,038
variants across four modules that all passed every gate.

**`start` is the 1-based VCF position. Copy it as printed; never subtract one.**
The reflex to convert to 0-based — from BED, or from VRS's own interbase model —
is the single most expensive mistake available here, because here is what does
*not* happen: `validate` passes, `compile --strict` passes, the manifest says
`fully_resolved: true`, and every `ga4gh:VA.…` id is minted and reported
**verified**. A content-addressed id is a correct digest of whatever it is
handed, so it certifies the wrong locus without hesitating.

Two things conspire:

- **Never author both sides of a redundancy check.** Hand-writing
  `resolution.csv` *and* the coordinates in `variants.csv` makes the coordinate
  cross-check compare your convention against itself, and it agrees perfectly.
  Let `enrich` produce the sidecar.
- **`--strict` means reproducible, not correct.** It refuses when resolution left
  something it could not reproduce. It has no opinion on whether your coordinates
  name the variant you meant, and cannot have one — the compiler never fetches.

Only online `enrich` catches it, reporting **`ref mismatch: N row(s) —
coordinate shifted 1 base…`**. Read that line as being about `start`, not `ref`.
It is a floor, not a total: only rows where the neighbouring base differs from
your `ref` are visible, roughly three in four.

**Prefer the rsID and let `enrich` find the coordinate.** An rsid-only row cannot
carry a coordinate mistake, and the resolution table it produces is the
independent second value the cross-check needs.

---

## Never fill a cell from the same source that checks it

`rsid`, `chrom`, `start`, `ref`, `alts`, `clin_sig`, `doi`, `acmg_sf`,
`function_status`, `evidence_level` and `p_value_num` are **redundancy-bearing**:
a check compares the independently authored value against a source, so filling it
*from* that source makes the check vacuous. Worse, for an rsid-only row the
coordinate check then does not run at all, so the row moves from honestly
unverified to apparently verified.

`hints.REDUNDANCY_BEARING` is the authoritative list. The lookup tools show the
value and **refuse to apply it** — `applied: false` with a `refusal` and a
`note`. **That refusal is the feature, not a limitation, and our MCP tools must
preserve it.** A convenience tool here that auto-fills a redundancy-bearing cell
does not bend a convention; it deletes a whole validation class.

Corollary for this repo: **no tool we expose may write an authored cell from a
lookup result.** Lookups report; the human decides; `lint_rows` checks.

### The two columns the list is missing, and why they are worse

`provenance_quote` and `provenance_regex` are absent from
`hints.REDUNDANCY_BEARING`, yet `enrich_literature` checks both against the Europe
PMC fulltext to produce `quotes_found`. By the list's own definition they belong
on it: a quote extracted from that same fulltext makes the check agree with
itself.

They are worse than the others, though, and it is worth being precise about why.
The other redundancy-bearing columns lose a *check* when auto-filled. These lose a
*fact about the world*. `provenance_quote` exists to record that a curator read
the paper and located the claim in it; a passage a machine pulled out of a
document the machine fetched asserts a reading that never happened. That is a
false claim of provenance, not a vacuous check.

So no tool in this repo extracts a passage — no best-matching passage, no
suggested quote, no search-within-text. `fetch_fulltext` returns the document and
nothing else. Filed upstream; ours to hold until it lands.

The honest consequence, which the tool and the skill both state: **once a fulltext
has been read through `fetch_fulltext`, `quotes_found` on that row is no longer
independent evidence.** It has degraded to a citation-pairing check — still
useful, because it catches a quote written against the wrong PMID, but no longer
evidence that the claim is in the paper. A tool that did not say so would be
laundering its own output.

---

## What only a human can decide

| Cell | Why |
|---|---|
| `genotype` | Sources publish **alleles, not genotypes**. Whether one copy is informative follows from the condition's inheritance mode. Exception: non-diploid contigs, where only one genotype is expressible, so `draft-panel` writes it. |
| `state` (when stubbed) | The record is `uncertain_significance` and no vocabulary member means "undecided" — `neutral` says benign, `risk` says a direction. If you can justify neither, **drop the row** rather than pick one to make the compile pass. |
| `weight`, `direction`, `effect_size` | Your model of the finding. ClinVar publishes no effect statistic. |
| `trait_efo_id` | Mapping free-text/MedGen conditions to an ontology is inference. |
| `conclusion` | What the module *says*. Keep it hedged where the biology is. |

---

## Genotype, weight and the axes

- **Alphabetically sorted, unphased.** `A/G`, never `G/A`. An unphased genotype
  is a *set*; two spellings would be two rows. Phased uses `|` and order matters.
- **`C/C`, not `CC`.** `CC` parses as one two-base allele. ClinPGx writes the
  unslashed form; disambiguate from the resolved ref/alt.
- **Alleles are `[ACGT]+`** and must be drawn from `{ref} ∪ alts` at that locus.
- **Indels are spelled out, reference-anchored**: `A/AG`, `C/CTT`.
- **Non-diploid contigs take a single allele**: `MT` always; `Y` outside PAR1/PAR2.
  The verdict is **per locus**, not per gene — `XG` and `SPRY3` straddle a
  boundary. PAR1/PAR2 on Y *are* diploid.
- **A pseudoautosomal variant is recorded once, on X** — every annotation source
  spells it that way and a standard GRCh38 analysis set hard-masks the Y PAR.
- **`ref`/`alts` may only appear *with* `chrom`+`start`.** Identity is filled
  whole or not at all; a lone `alts` on a position-only row changes *which
  variant the row is* (the key becomes a VRS id instead of `chrom:start:ref`).
- **A `risk` weight is negative.** `weight` contributes to a wellness-style
  score, not a hazard ratio: `risk` wants `weight < 0`, `protective` wants `> 0`.
  Getting the sign backwards is a **warning**, so it compiles.
- **`direction` is not a magnitude** — same axis as `state`
  (`neutral`/`protective`/`risk`/`unknown`), not `increase`/`decrease`.
- **`direction` is authored or it is empty.** Nothing derives it from `state`;
  a module carrying only `state` ships an empty `direction` column and a consumer
  keying on it sees nothing. Write it on every row it applies to, or none.
- **An rsID is position-level, not per-allele.** One rsID can span pathogenic,
  benign and uncertain alleles; a paralogous one maps to several real places
  (`expanded to N rows` is expected — do not delete rows to suppress it).
- **An rsID row's `variant_key` stays the rsID.** VRS ids are not the key; they
  live in `resolution.csv.vrs_id`, one per ALT, positionally aligned with `alts`.

## Withhold rather than assert

The house algebra is **three-valued: true / false / unknown**, and `None` is
never `False`.

- A blank cell means "not stated" and is always legitimate. Never write `false`
  to silence a reminder.
- Every binning table has an **`unresolved` sentinel** for an absent measurement.
  Never route a missing measurement to the lowest bin.
- `requires_callable=true` (with `callable_from`) wherever the *absence* of a
  variant is the informative call: a no-call is not a reference call.
- On licensing, unknown terms are **undetermined, never permitted**.
- `unchecked` / `unknown` in a report means the question was never put. **A check
  that could not run is not a check that passed** — our tool output must keep
  that distinction visible, never collapsing it to a boolean pass.

## Binning bounds

- `measure_max` is **inclusive** on every kind. `min == max` for a sharp value,
  a null bound for open-ended.
- Whether adjacent bins may share an endpoint depends on the kind, **and the two
  cases are opposite**:
  - **Dense** (`allele_fraction`, `prs_percentile`): bounds **must touch**
    (`0.0–0.1` then `0.1–0.3`). The higher bin owns the shared endpoint. A hole
    warns.
  - **Integer** (`repeat_count`, `copy_number`): bounds must **not** touch
    (`[27,35]` then `[36,39]`) — a shared endpoint is a real overlap, refused.
  - **`activity_score`** is in neither set: coarse consumer-summed grid, no gap
    warning, bins do not touch.
- Two bins sharing a *lower* bound refuse on every kind.
- Bins group by the kind's key columns **plus `trait_efo_id`**.

## PGx and star alleles

- A clinical annotation's key is `(variant_key, drug, genotype,
  phenotype_category, annotation_id)` — not the bare triple. 1,199 of 17,380
  triples collide without the last two.
- Annotations are **per genotype and can oppose each other**
  (rs4149056+simvastatin: "decreased" for CC/CT, "increased" for TT).
- **CPIC recommendations are keyed by (phenotype, drug, *population*)** and the
  populations disagree. Every clinical context is drafted, kept apart by
  `clinical_context`, and the consumer selects one at query time; `population`
  filters rather than decides.
- `recommendation_strength` is CPIC's; `evidence_level` is PharmGKB/ClinPGx's.
  Fill only the one your source states.
- A large star-allele gene needs `--allele`: *n* alleles is *n(n+1)/2*
  diplotypes; unfiltered CYP2D6 is 16,290 rows, 73% `Indeterminate`. `*1` is
  always kept. One `--gene` at a time — a star name is gene-scoped.
- A star allele can be **used without being defined**; warned, not blocked.
- CPIC activity scores are inequality strings (`"≥3.0"`), not numbers; CPIC's
  `n/a` means *not scored* — leave the cell blank.

## Licensing

- **Every PGx upstream (ClinPGx, CPIC, PharmVar) is CC BY-SA *plus a no-sale
  clause*.** None is sellable. Do not read a bare "CC BY-SA" as permission.
  (PharmGKB API docs are dead; ClinPGx is the successor, paths unchanged.)
- Pass `--use unstated | non-commercial | commercial` to anything that copies
  rows out of a source. A forbidding source is *skipped* on `unstated` and
  *refused* on `commercial`, **at acquisition**.
- **`sources.csv` is the only thing the compile gate reads.** A source copied
  from by hand is invisible to it. Only the *annotation* layer taints; a
  coordinate is a fact. Most-restrictive-wins, module-wide.
- The CLI spelling and the column value differ: `--use non-commercial`, but the
  `declared_use` column takes `non_commercial` (underscore).
- **There is no `--non-commercial` compile flag, by design** — a flag cannot
  survive `reverse`, so a third compile would refuse. The declaration must be data.

---

## Sidecars, signatures and reproducibility

- **An existing sidecar is authoritative and merged, never clobbered.** To
  regenerate `resolution.csv` / `frequencies.csv` / `gene_metrics.csv` you must
  **delete the file first**, or stale rows persist silently. Moving it aside and
  re-enriching is also the only way to ask whether an injected table still agrees
  with the sources. Any tool we expose that re-runs a pass must say this.
- **`compile_module(resolve_with_ensembl=False)` disables `resolution.csv` too.**
  Filed upstream as `S14`; tracked here as **F10**.
  The name reads as "don't use Ensembl"; it is the master switch for *all*
  resolution. Set it False and every row compiles with `chrom=None` — and the
  compile **succeeds**. The correct call is `resolve_with_ensembl=True,
  ensembl_cache=None`. **Our wrapper must never expose a way to reach the False
  branch by accident.**
- **Recompiling is reproducible; re-drafting is not.** `sources.csv` carries a
  `fetched_at` stamped when the row is written and `sources.parquet` is inside
  the Merkle root, so two builds of byte-identical content an hour apart are two
  different artifacts. Do not treat a digest change as evidence content changed;
  digest-based dedup misses rebuilds.
- **Authored row order is preserved** through compile → reverse → recompile and
  is load-bearing for `artifact.digest`.
- `content_signature` folds `module_spec.yaml`'s `defaults:` into each row before
  hashing, so `curator`/`method` on the row and in `defaults:` are one content —
  and `reverse` round-trips to the same signature. That is the fixed point the
  format guarantees.
- **Write CSVs with a CSV writer, never by splitting on commas.** Several
  `conclusion` values contain commas, and a column shift usually surfaces as a
  bizarre validation error three columns away
  (`trait_efo_id tokens must be ontology CURIEs` on a value that is not a trait).

## `--strict` vs plain

Author against `--strict`, because that is what the registry runs. Pass
`validate` **the same mode as the compile you intend to run** — several checks
are a ladder (warn under best-effort, refuse under strict), so a modeless
pre-flight answers for the other compile.

| condition | plain | `--strict` |
|---|---|---|
| genotype allele not among the locus's alleles | warning, valid | **error** |
| two-allele genotype on `MT`/`Y` | warning | warning |
| unresolved rows (no coordinate) | warning | counts against publishability |

A plain compile **succeeds** through the first two. "It compiled" is not evidence
the module is correct.

## Known gaps — do not work around these in the data

An `RMn` in a message is a tracked upstream roadmap item: **known and
deliberate**. Leave the data honest and note the limitation.

- **RM5** — symbolic/structural alleles (`<DEL>`, 5-HTTLPR, `del`/`ins`, CPIC's
  `x≥3`) are outside `^[ACGT]+$`. Rows are skipped and counted, never coerced.
  Distinct from IUPAC ambiguity codes (`R`, `Y`, `N`), which record an
  uncertainty that must never be expanded into the alleles it could stand for.
- **RM15** — multi-build. GRCh38 is the only assembly with a refget table, so
  VRS minting and rsID resolution are GRCh38-only. Off GRCh38: author
  coordinates rather than rsIDs, expect build-relative keys that will not join
  against gnomAD/ClinVar/ClinGen, and say so.

---
