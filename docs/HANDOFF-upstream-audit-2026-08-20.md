# Consumable — the upstream audit of 2026-08-19/20, for whoever writes the skills

Written for the agent filling in `skills/*/SKILL.md`. It carries the actionable half of a three-way
validation of `skills/module-tables/references/` — all 24 dossiers, against `just-dna-format`'s own
`docs/`, against **the code as arbiter** (format 0.6.1, compiler 0.6.1, enricher 0.6.4).

Read this before writing a stage skill. It answers three questions: **which sentence on disk here is
wrong today**, **which seeds each stub skill has earned**, and **how far you may trust a dossier when
you quote one**.

---

## 0. What the audit changes about the dossiers

**The dossiers held up.** About 250 `file:line` citations across the 24 were spot-checked and
near-zero named the wrong symbol. Their **line numbers have drifted** with the upstream tree; their
**reasoning is sound**. The `module-enrich` stub's standing warning — *"the dossiers are under audit
revision, re-read one before quoting it"* — can now be narrowed to: **anchor on the symbol name, never
on the line number**, and read the markers.

**Every dossier now opens with an audit banner** and carries two inline markers. They are your
interface to this audit; you do not need the audit's own reports.

- 🚧 **ROADWORKS** — a surface that is **broken or unfinished**. Always three parts: *Current state*,
  *Expected state*, and a **Guard** naming what an author should do instead. 25 of them.
- ⚠️ **CHECK** — a claim whose current state is not what the surrounding text implies. *Current state*
  and *Expected state*, no guard needed. 10 of them.

**When a skill tells an author to rely on a tool, grep that tool's dossier for 🚧 first.** If there is
a guard, the skill owes the guard, not the happy path.

**Two things the audit got wrong about the dossiers, so nobody "fixes" them back.** Two of its reports
accused `pgs.md` and `gene_metrics.md` of fabricating `describe_table`'s return value and of calling a
`table_requirements` symbol that does not exist. Both accusations are false. Those are **this
plugin's own MCP tools** (`src/just_module_creator/tools/authoring.py`): `describe_table` really does
return `redundancy_bearing` / `attestation_bearing`, and `table_requirements` really does exist here.
The audit checked `just_dna_compiler.hints`, which is a *different surface with the same names* — the
library raises `DraftError: '<name>' is not an authored table of this format. Known: [...]` where our
wrapper raises `Unknown table kind '<name>'. Authorable kinds: …`. Both wordings are right for the
surface each names. **Only the count was wrong: thirteen authorable kinds, not twelve.**

The lesson generalises and belongs in whatever you write about tool surfaces: **establish which
surface owns a name before calling a claim about it a misread.**

---

## 1. The one thing on disk here that is wrong today — fix this first

### `skills/create-module/SKILL.md`, the paragraph beginning *"Author the rsID here, not a coordinate"*

It teaches the **pre-0.6 rule**. RM43 shipped the fill in format/compiler 0.6, and the passage was
written before it. Three of its four claims are now false, and the fourth sends an author to wait for
a release that already happened.

**On disk (quoted so you can find it — it is around line 755, followed by the block quote around 764):**

> **Author the rsID here, not a coordinate.** Resolution is applied to `weights.parquet` only, so a
> `pharm_variants` / `diplotypes` / `pgs` row's `chrom` and `start` arrive **null** in the artifact even
> when `resolution.csv` covers the variant — these tables are materialized verbatim from their authored
> CSV. […]
>
> > *"pharm_variants.csv: 1 of 1 row(s) have no chrom+start, so this table joins by rsID only …
> > **resolution.csv can place 1 of them**, and the compiler applies that table to variants.csv only."*
>
> […] It is a warning in both modes and never a strict error, deliberately: rsid-only identity is
> legal, and the remedy is a compiler change rather than an authored edit.

**What the code does now.**

- `compiler._POSITIONAL_TABLE_KINDS` is derived — every `_TABLE_KINDS` model carrying both `chrom` and
  `start` — and evaluates to exactly `['heteroplasmy.csv', 'haplotypes.csv', 'pharm_variants.csv']`.
  `_apply_positional_resolution` fills those rows from the injected table, in `validate_spec` **and**
  in `compile_module`.
- So `pharm_variants` **is** filled. `diplotypes.csv` and `pgs.csv` are not — not because resolution
  skips them, but because **those models have no `chrom`/`start` columns at all**. That is a different
  fact with a different remedy, and the current text merges the two into one wrong sentence.
- The quoted warning text **no longer exists**. The fragment `"have no chrom+start"` is pinned
  (`compiler.UNJOINABLE_PHRASE`, substring-matched by the registry's facet builder), and the rest of
  the sentence was rewritten. Today it reads, per positional table:

  > `pharm_variants.csv: 1 of 1 row(s) have no chrom+start, so this table joins by rsID only — a VCF
  > whose ID column is empty matches none of them. <detail>.<partial note>`

  with `<detail>` one of three, and the branch order is load-bearing:

  1. *"resolution.csv names N of them and was not consulted for this table — see the skip reported
     above"* (or *"the resolution table was not consulted…"* when it names none) — **the fill did not
     run**: `--no-resolve`, or a non-GRCh38 module.
  2. *"no resolution.csv row places them — run `just-dna-enricher enrich` first"* — nothing was
     enriched.
  3. *"resolution.csv names N of them, but at more than one locus or at one the row's own allele
     contradicts, so the compiler leaves them unplaced rather than picking"*.

  `<partial note>` appends when a row carries half a coordinate: *"N carries one half of a coordinate
  (a start with no chrom, or the reverse), which reads as a position and is not one."*
- On a non-GRCh38 module the fill is skipped with its own line (RM15):
  *"Positional-table fill skipped: the compiler is GRCh38-bound and this module's genome_build is
  'GRCh37', so the injected resolution table is not joined onto <tables> (RM15). Those rows keep the
  coordinates their author typed."*
- A row whose authored identity the table disagrees with is **left exactly as authored** and warned
  about separately: *"N row(s) authored an identity the resolution table disagrees with, and are left
  exactly as authored — …"*.

**Drop-in replacement (adapt the voice, keep every fact):**

> **Author the rsID here, not a coordinate — and since 0.6 the compiler fills the coordinate for you.**
> `resolution.csv` reaches three positional tables — `pharm_variants.csv`, `haplotypes.csv`,
> `heteroplasmy.csv` — in `validate` as well as `compile` (RM43). A row you keyed by rsID arrives in
> the artifact with `rsid` / `chrom` / `start` / `ref` / `alts` filled from the resolution table —
> those five and no others (`resolve_positional_rows`) — and the fill stays out
> of `content_signature` because each row also carries `authored_ident` naming what you actually
> wrote. `diplotypes.csv` and `pgs.csv` are **not** filled for a different reason: those models have no
> coordinate columns at all, so there is nothing to fill and a consumer joins them on `rsid` +
> `genotype`.
>
> Three things still leave a row unplaced, and the warning tells you which: the fill never ran
> (`--no-resolve`, or a non-GRCh38 module — RM15, and it says so on its own line), nothing was
> enriched (*"run `just-dna-enricher enrich` first"*), or the rsID resolves to more than one locus (or
> to one whose alleles contradict the row) and the compiler **declines to pick**. Only the third is a
> curation question, and the answer is to author the coordinate yourself.
>
> **Never invent a coordinate to silence the first two.** And grep the warning by the fragment
> `have no chrom+start` — that substring is a pinned contract; the sentence around it is not.

**While you are in there:** the same file's binning bullet (*"Every binning table has an `unresolved`
sentinel a consumer selects when the measurement is absent"*) is true as a **contract** and false as an
**enforcement** claim. See §3, `module-check`.

---

## 2. Stale in `docs/just-dna-format-pending-fixes.md`

**`F5 — resolution never reaches the non-SNP table families` — the fix shipped; the status line says it is open.**

The entry reads *"the coordinates themselves are open as upstream RM43, tracked in `RM_TOC.md`"*. RM43
is **shipped in 0.6.0**: the positional parquets are filled in `validate_spec` as well as
`compile_module`, each model gained stamped `variant_key` + `authored_ident` (plus `alts` on
`PharmVariantRow` / `HaplotypeRow`, as data and not identity), and upstream's own record cites
`pgx_slco1b1_simvastatin` going from nine all-null rows to `12 / 21178615 / T / A,C`. There is no
`resolution.parquet` — reverse rebuilds the lookup table from the positional parquets, which P7 forces.

The block quote inside F5 carries the same retired warning text as §1. Update the status, re-quote the
current sentence, and keep the two live residues:

- the fill is **skipped off GRCh38** (RM15), which is the open half and is upstream **RM69**;
- the stamped fields are `Field(exclude=True)`, which leaves `VariantRow`'s own two inconsistent —
  grandfathered, filed as a 1.0-cleanup candidate.

**`F10 — `resolve_with_ensembl=False` is the master switch for all resolution, and its name says otherwise`** — independently
confirmed by the audit, and `heteroplasmy.md` now carries a ⚠️ CHECK correcting its own opposite claim
(it had said `compile_module` *pins* the parameter; it is a default, and the CLI wires
`--resolve/--no-resolve` straight to it). Nothing to change in F10 — quote it as corroborated.

---

## 3. Seeds per skill, from the audit

Each is stated as **what the skill should tell an author**, with the evidence to cite and the guard.
All were re-checked against the code; where a number appears it was measured. The matching dossier
carries the long form under a 🚧 or ⚠️ marker.

### `module-enrich`

1. **`enrich_gene_metrics` cannot be re-run.** `reference` is bound only inside `if wanted:` and read
   unconditionally below, so the *ordinary idempotent re-run* — every gene already carrying a `gnomad*`
   row — and any module with **no `variants.csv`** raise `UnboundLocalError` straight out of the pass.
   It is not a subclass of `GeneMetricsEnrichmentError`, so the `except …EnrichmentError` contract
   RM101 built does not hold for it. **Guard:** run the pass once, on a module that has a
   `variants.csv`; to re-run, delete `gene_metrics.csv` first (which costs you any override in it — and
   see seed 2, where overrides are broken anyway); catch `Exception` at that call site until fixed.
   → `gene_metrics.md`, upstream **RM104**.
2. **A curator override on `gene_metrics.csv` duplicates instead of overriding.** The merge key is
   `(gene, dataset)`; the *fetch-suppression* key is a `gnomad`-prefix scan over `source`. An honest
   `source="manual"` correction therefore does not suppress the fetch and lands beside the fetched row,
   two rows sharing the key and contradicting each other, with **zero** compiler warnings (fact tables
   have no duplicate check). `clingen.py` — same package — derives its suppression set from its merge
   key and is right. **Guard:** edit the cell, leave `source` as the fetched one; or delete the fetched
   row in the same edit. → `gene_metrics.md`, upstream **RM109**.
3. **`--strict` refuses the *usual* answer on three passes, and each is a different sentence.**
   Clinical assertions: strict raises when any resolved allele has no ClinVar record, which is true of
   most alleles — the error says so itself (*"Most variants are not in ClinVar at all, so this is
   usually correct data rather than a read failure"*). GWAS: strict escalates on `unusable` and
   `p_value_underflows`, and `hfe_hemochromatosis` — a shipped flagship — fails today on six Catalog
   underflows. Gene metrics: the gate fires on a gene gnomAD has no constraint row for. **Guard:** run
   these three at their default; if a pipeline sets `--strict` globally, exempt them **by name**, and
   never read the failure as "the module is wrong". → `clinical_assertions.md`, `gwas_effects.md`,
   `gene_metrics.md`; upstream note: the GWAS ladder has **no test coverage** in either direction.
4. **A non-GRCh38 module gets zero frequencies, and the skip barely surfaces.** `_alleles_from_resolution`
   skips any resolution row off `FREQUENCY_GENOME_BUILD` — correct, because gnomAD v4's variant id
   carries no assembly, so a GRCh37 coordinate is a well-formed request that returns *a different
   variant's* frequency. But the only trace is one counted log line: there is no `off_build` on the
   result a caller can read (the assertions pass does expose one), and the compiled module looks
   exactly like one gnomAD had nothing for. **Guard:** do not read an empty `frequencies.csv` as
   "gnomAD has nothing"; lift the module to GRCh38 or say so in the README, because no artifact field
   records it. → `frequencies.md`.
5. **`enrich_pgx(mode=…)` is accepted and does nothing**, and two shipped user-facing strings promise
   otherwise — `PgxEnrichmentError`'s docstring (*"Raised in strict mode when the PGx cross-check finds
   a discrepancy"* — it is only ever raised for an unparsable CSV) and the CLI's `--strict/--best-effort`
   help. The *reporting* behaviour is deliberate: the format will not arbitrate a PharmVar/CPIC
   disagreement. **Guard:** never gate a pipeline on `enrich_pgx(mode="strict")`; read `PgxResult`'s
   conflicts and decide in your own code. → `allele_function.md`.
6. **`enrich-pgx` never opens `diplotypes.csv`.** Both PGx cross-checks are driven from
   `haplotypes.csv`; without that file they early-return. A diplotype-only module therefore passes
   every gate with **no cell of it compared to anything**, and looks identical to a checked one.
   **Guard:** ship `haplotypes.csv` + `allele_function.csv` beside your diplotypes even when the
   diplotypes are the point. → `diplotypes.md`.

### `module-draft`

1. The `DPYD` seed already on disk is right; **finish it with the second half.** A draft that adds
   zero rows also writes **no `SourceRow`**, so the module can end up with no `licensing.csv` entry for
   CPIC at all — and `licensing.csv` is the file the compile gate keys on. Eleven CPIC genes lose every
   allele (`ABCG2, CACNA1S, CFTR, DPYD, G6PD, HLA-A, HLA-B, IFNL3, MT-RNR1, RYR1, VKORC1`); the model
   accepts those names, the *provider* refuses them. **Guard:** hand-author the table, write the source
   row yourself, and never read `added 0 row(s)` as a clean run. → `allele_function.md`.
2. **408 of CPIC's 1,275 graded alleles map to a blank `function_status`, silently** — `ivacaftor
   responsive` (103), `III/Deficient` (37), the MT-RNR1 aminoglycoside-risk phrases (25 rows across
   four distinct strings, including a `Normal risk…`/`normal risk…` case-variant pair), `IV/Normal` (5)
   and others. A blank is indistinguishable from "CPIC has not graded this". **Guard:** count blank
   cells after every `draft --gene` and check each against CPIC's own table. → `allele_function.md`.
3. **Two skip families in `pgx_draft` are un-aggregated, not one** — measured on one `--gene DPYD` run:
   84 lines from the allele-function loop, 164 from `_haplotype_rows`.

### `module-check`

1. **The `unresolved` bin sentinel is enforced on one side only, and the two surfaces disagree about
   scope.** `_validate_table_kind` counts sentinels **per bin group** and refuses a *second*; nothing on
   the compile path refuses **zero** — a sentinel-less binning table compiles green under `--strict`.
   The presence half lives on the authoring surface (`hints._check_bins` → *"no unresolved sentinel
   row"*, reachable through `lint_rows`) and is `not any(...)` over the **whole table**. So on a table
   whose key fields fragment it into several groups — `copynumbers.csv`'s modifier columns are in the
   group key — one sentinel anywhere satisfies the hint while most groups have none. **Guard:** run the
   hint, then count sentinels **per group** by hand. → `activity_phenotype.md`, `copynumbers.md`,
   `heteroplasmy.md`.
2. **Deduplicate warnings before you count them.** The `faf95` arithmetic warning is published
   **twice** into `manifest.compilation.warnings` — the check runs in `validate_spec` and again in the
   compile-side `_frequency_checks` with no filter, while `_literature_checks` eleven lines away does
   filter and names the hazard in a comment. Measured: 15 warnings, 14 distinct. → `frequencies.md`,
   upstream **RM106**.
3. **A duplicate `(source, layer)` row in `licensing.csv` compiles green under `--strict`** — even one
   carrying the opposite `commercial_use`. `SourceRow` is in the *drafter's* dupe map and absent from
   the *compiler's*, while `licensing.merge_sources_csv` merges on that pair. **Guard:** after any hand
   edit, sort on `(source, layer)` and check for repeats yourself. → `licensing.md`, upstream **RM107**.
4. **Nothing checks bin coverage above the highest bin or below the lowest**, in either tiling. A
   closed top bin on an unbounded axis strands every measurement above it — it matches no bin and not
   the sentinel either, because a measurement *was* made. **Guard:** leave the top bin's `measure_max`
   blank unless the axis really ends. → `copynumbers.md`, `activity_phenotype.md`.

### `module-close`

**Closing a module can throw its check records away, and only the CLI says so.** A record attested over
bytes that no longer match is dropped and named in `CloseResult.dropped_checks` — correct behaviour,
because carrying it across would re-bind a claim to different bytes. But it is a *field on the result*:
the Typer CLI prints one line for it, a **library** caller that ignores the field is told nothing, it is
not a compile warning, and nothing about the loss reaches `manifest.verification`. It has already
happened in the format repo's own history, and **15 of its 16 reference examples now record zero
checks**. **Guard:** close through the CLI or read `dropped_checks` explicitly and fail on a non-empty
list; re-run checks **after** closing; treat an empty `verification.json` on a closed module as "the
records were dropped" until proven otherwise. → `verification.md`.

### `module-publish`

1. **Never name a logo `logo.jpeg`.** Discovery sorts `LOGO_EXTENSIONS`, so **`jpeg` beats `jpg` beats
   `png`** and a spec dir holding two logos silently ships the jpeg — the loser is not even copied. The
   enricher's publisher allowlist holds `logo.png` and `logo.jpg` and **not** `logo.jpeg`, by an
   explicit deferral in its own comment. Result: a manifest attesting bytes the published repo does not
   carry, which `verify_manifest(check_logo=True)` will not catch either, because an absent file is not
   a failure there. **Guard:** ship exactly one logo, named `logo.png`. → `logo.md`, upstream **RM105**.
2. The `MODULE.md` seed already on disk is right and is the highest-frequency real breakage (26 of 27
   submitted bundles). Worth adding: **the rename is the registry's, not the format's**, it arrives as
   an `info` note that lands nowhere durable, and a **local** compile of such a bundle produces
   `manifest.readme: null` in silence. Do not route around it with `readme_file=MODULE.md` — that mints
   a manifest attesting a name the registry's recognised-file list does not contain. → `readme.md`.

### `module-refresh` (pass two)

1. **A ClinGen re-curation adds a row and nothing marks the superseded one.** ClinGen's `assertion_id`
   embeds the curation timestamp, so a re-curated assertion misses the merge key and is appended beside
   the old one — `manifest.gene_validity.classifications` can then publish a pair as far apart as
   `["definitive", "refuted"]` with no currency notion anywhere. **Guard:** read `classifications` as
   *everything ever curated*, not the module's current call; sort by `classification_date` per
   `(gene, disease, moi, submitter)` and delete stale rows by hand before publishing. → `gene_validity.md`,
   upstream **RM108**.
2. **The S45 supersession sweep does not reach `studies.csv`.** `_superseded_rsid_rows` has one call
   site and is handed the `variants.csv` append report, so a ClinVar re-draft leaves both the stale
   rsid-only study row and its coordinate-keyed replacement — surfacing only as a *"Studies reference
   variants not in variants.csv"* orphan warning that blames the citation. **Guard:** after any
   re-draft, diff `studies.csv`'s rsIDs against `variants.csv`'s and delete the stale rows before
   compiling. → `studies.md`.
3. **The three article licence rights are frozen at write time.** `article_terms` has exactly one call
   site, in the enricher's fetch loop, and its values are persisted onto the row; the compiler reads
   `row.commercial_use` and never re-derives anything. Several upstream docs said the opposite and were
   wrong. **Guard:** after changing a licence mapping or correcting a `license` cell, **delete
   `literature.csv` and re-run** — merge-not-clobber keeps every stale right otherwise, silently. The
   same delete-the-sidecar rule covers any derived column you expect to move. → `literature.md`.

### `module-revise` / `module-diff`

**A reverse costs you the VRS ids while every identity check calls the round trip lossless.**
`reverse_module` writes eleven columns of `resolution.csv` and drops seven, including `vrs_id`,
`vrs_spec` and `caid`. Because none is in `RESOLUTION_FACT_FIELDS`, `compile → reverse → compile`
reproduces `content_signature`, `resolution_signature` and `artifact.digest` exactly. **Guard:** keep
the authored `resolution.csv` in version control; after a reverse, re-mint before publishing.
→ `resolution.md`.

### `module-curate`

The `hosting_verdict` seed on disk is right, including its note that create-module promises otherwise —
that promise is the blanket *"a warning normally, an error under strict"*, and it is wrong for the
homozygous and undecided cases. Add the neighbouring one: **a redundancy advisory can name a checker
that never sees your table.** `hints.REDUNDANCY_BEARING` is keyed on a **bare column name** with no
model attached, so `_flag_advisory_columns` prints the `clin_sig` advisory on binning tables and the
`clin_sig`/`evidence_level` advisories on `diplotypes.csv`, while the checkers it names
(`enricher.clinical.verify_clin_sig`, the ClinPGx leg) are driven from `variants.csv` and the PGx
annotation tables. The advice stays right — author those cells yourself — but **a green run is not
evidence they agree with anything**. → `activity_phenotype.md`, `diplotypes.md`.

### `module-101`

One line worth adding to the "what the plugin cannot do" half: **`manifest.stats` is computed from
`variants.csv` alone.** A gene-keyed table-only module — CYP2D6 activity bins, an SMN copy-number
table, a PGx star-allele module — publishes `gene_count: 0, genes: []`, and the registry's gene index
is fed from `stats.genes`, so `registry_search(gene=…)` cannot find it. Three dossiers reached this
independently. → `copynumbers.md`, `diplotypes.md`, `allele_function.md`.

### `module-tables`

State the marker convention (§0) in the skill itself, so a reader who opens one dossier knows what 🚧
and ⚠️ mean without opening this file. Replace the standing *"under audit revision"* caveat with
*"audited 2026-08-20; anchor on symbols, not line numbers; read the markers."*

---

## 4. Upstream tracking — do not re-file these

The code half of the audit is filed in `just-dna-format` as **RM104–RM111** (`docs/ROADMAP.md`,
indexed in `docs/RM_TOC.md`). All eight are **filed, none fixed**, so every guard above stays live
until a release says otherwise.

| RM | what | shape |
|---|---|---|
| RM104 | `enrich_gene_metrics` `UnboundLocalError` on the re-run | one-line patch + test |
| RM105 | `logo.jpeg` compiles and is attested but never publishes | patch — derive the allowlist |
| RM106 | the `faf95` warning is published twice | one-line patch + test |
| RM107 | duplicate `(source, layer)` compiles green under `--strict` | patch |
| RM108 | ClinGen re-curation leaves nothing marking the superseded row | needs a currency rule first |
| RM109 | gene-metrics suppression key not derived from the merge key | one-line patch |
| RM110 | `constraint_flags` has two producers with two encodings | moves `gene_metrics.signature`; needs a release |
| RM111 | three shipped strings assert a registry override of `license` that nothing performs | patch |

**RM110 is the one with a consumer-visible edge you should write about now**, whatever upstream does:
the snapshot leg keeps gnomAD's JSON literal, so **17,403 of 18,111** rows carry the two-character
string `"[]"`, which is truthy. Anything writing `if row.constraint_flags:` reads 96% of snapshot rows
as *flagged*. Compare against the literals and treat `"[]"`, `""` and `None` alike as *no flags*.

---

## 5. Three shapes worth carrying into the prose

The audit found the same three defects repeatedly, in upstream's docs and in ours. They are worth
stating once wherever you write about checks, because they generalise past the instances above.

1. **A check is only as wide as the table it reads, and naming a check without naming its scope is how
   a reader over-trusts it.** Six independent instances: `REDUNDANCY_BEARING` keyed on a bare column
   name; `check_identifiers` reading `variants.csv` only, so a bin row's `gene`/`trait_efo_id` is never
   checked for currency; `enrich-pgx` never opening `diplotypes.csv`; `stats.genes` from `variants.csv`
   only; the missing-sentinel hint being table-level where the compile rule is per-group;
   `_check_genotype_coverage` running in `validate_spec` and only there.
2. **A counted claim in prose rots exactly like a hand-kept list.** *"Seven fact signatures"* (eight),
   *"six derived sidecars"* (seven), *"four causes"* (five), *"twelve names"* (thirteen), *"16 model
   fields"* (15), *"six columns"* followed by nine of them. Where you can, state the **rule** and let
   the reader run the call; where you must state a number, say what you counted and when.
3. **An enforcement claim needs its surface named.** *Mandatory*, *refused*, *checked* and *warned* are
   four different strengths, and a hint never fails a build. The sentinel case is the canonical one: it
   is called mandatory in three upstream places, the compile path refuses a **second** and refuses zero
   nowhere, and the presence half is an authoring hint scoped to the whole table.
