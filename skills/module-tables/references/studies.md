# studies.csv — the receipt for every claim the module makes

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

`studies.csv` answers *why do I believe this row?* One row is one **(subject, paper)** link: a
PubMed id, plus — optionally, since 0.6 — the variant it is about, plus whatever the curator can
honestly say about what that paper found. It is written by the curator, for a reader who wants to
check the module against the literature. It is not a bibliography (`literature.csv` is the machine's
verification record over these citations) and it is not a provenance ledger (`licensing.csv` /
`sources.csv` records where *datasets* came from). Upstream states the three-way split at
`/data/sources/just-dna-format/docs/SCHEMAS.md:1050-1063`: *"a paper is not a data source"*.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.spec.StudyRow` — `schema/src/just_dna_format/spec.py:895` |
| Base | `AuthoredModel` (reserved-namespace guard; shared `rsid`/`trait_efo_id`/`stat_significance`/`effect_size` validators) |
| Becomes | `studies.parquet` — built by `_build_studies`, `compiler/src/just_dna_compiler/compiler.py:5889`; listed in `ARTIFACT_PARQUETS` at `compiler.py:281` |
| Natural / dedup key | `(variant_key, pmid)` — `compiler/src/just_dna_compiler/draft.py:93` (`_CORE_DUPE_KEYS`) and `compiler.py:3164`. `variant_key` may be `None`; `(None, pmid)` is still a key, so two subject-less rows citing one paper are a duplicate |
| Authored or produced | **Authored.** Listed in `_INPUT_FILES` (`compiler.py:267`), so it is hashed as authored data, not as facts |
| Who writes it | the curator; `just-dna-enricher draft-panel` seeds *only* `rsid`/`chrom`/`start`/`ref`/`pmid` |
| Fact signature | **none — it has no fact signature and never will.** Fact signatures exist for derived sidecars (`resolution`, `frequency`, `gene_metrics`, `literature`, `gene_validity`, `clinical_assertions`, `sources`). An authored table's identity is `content_signature` |
| In `content_signature`? | **Yes**, via `_INPUT_FILES` → `integrity.content_signature` (`schema/src/just_dna_format/integrity.py:189`) |
| In `artifact.digest`? | **Yes**, as `studies.parquet` |
| Legal spellings / locations | exactly one name in exactly one place — the spec root. `layout.py:12` says so explicitly; `studies.csv` is **not** in `SIDECAR_SPELLINGS` and may **not** live under `derived/` |

## Who populates what

| Column(s) | Who |
|---|---|
| `pmid` | **author**, or **drafter** — `clinvar_draft._study_rows` (`enricher/src/just_dna_enricher/clinvar_draft.py:400-452`) reads ClinVar's own `var_citations` links. Also **redundancy-bearing**: `LiteratureRow.exists` asks PubMed whether *this authored id* resolves |
| `rsid` / `chrom` / `start` / `ref` | **author**, or **drafter** (same function; it copies whichever identity the matching `variants.csv` row got, or the coordinate when the rsID is multi-allelic) |
| `population`, `p_value`, `p_value_num`, `conclusion`, `study_design`, `stat_significance`, `effect_size`, `effect_measure`, `effect_allele`, `trait_efo_id` | **author only.** No drafter and no enricher pass has ever written one. `_study_rows` constructs `StudyRow(rsid=…, pmid=…, **coordinate)` and nothing else (`clinvar_draft.py:449`) |
| `doi` | **author.** The literature pass *reads* PubMed's DOI and writes it onto `literature.csv`, never here — `literature.py:8-11`: *"Neither is ever written back into `studies.csv` — the enricher does not edit authored files, because `content_signature` is defined as reference-independent"* |
| `provenance_quote`, `provenance_regex` | **author only**, and see the refusals below |
| `module` (parquet only) | **compiler-stamped** from the module name (`compiler.py:5902`); stripped again by `_write_studies_csv`, so a reverse round-trip never authors it |
| `neg_log10_p` (parquet only) | **compiler-derived** from `p_value_num` (`spec.py:1018`, materialized `compiler.py:5926`). Deliberately absent from the CSV writer (`compiler.py:6676`) — re-emitting it would author a value the next compile recomputes |
| registry-stamped | **none.** The registry stamps identity onto `module_spec.yaml`, never onto a data row |
| nobody, ever | no column is permanently unwritten — but see the corpus measurement in *Gotchas* |

**Cells no tool may fill, and why the refusal is the feature**

- `hints.REDUNDANCY_BEARING` (`compiler/src/just_dna_compiler/hints.py:81-109`) names nine of this
  table's columns: `rsid`, `chrom`, `start`, `ref`, `pmid`, `doi`, `p_value_num`,
  `provenance_quote`, `provenance_regex`. Each is compared against a source by a later check;
  filling it *from* that source makes the check compare the source with itself.
  `lookup_citation` therefore returns PubMed's DOI in `withheld` with
  `applied=false, refusal="redundancy_bearing"` rather than as a cell to paste.
- `hints.ATTESTATION_BEARING` (`hints.py:72`) is the **subset** `{provenance_quote,
  provenance_regex}`. `hints.py:66-71` glosses it as *a curator read this passage in this paper*,
  and reads that as a human. **Correct for their layer, not the rule here** — an agent reading a
  fetched article is a reading that happened, so what the column needs is attribution rather than
  abstention: locate the passage, quote it verbatim, and record who located it. The reasoning we
  originally supplied for that constant is withdrawn upstream as `S55`. What survives, and it is
  physics: no *lookup* may write the cell, and the cell must never hold something obtainable without
  reading the article — see the title gotcha below.
- **The corollary you must say out loud:** once `fetch_fulltext` has read a PMID in this session,
  `quotes_found` on that row has degraded to a **citation-pairing check** — it still catches a quote
  filed against the wrong PMID, and it no longer shows anyone read the paper (`hints.py:102-106`).

## What moving this table moves

Measured on a scratch copy of `reference_examples/hfe_hemochromatosis` (33 study rows), compiled
with `compile_module(strict=False)` and `module_binding(authored_input_entries(spec_dir))`.
Baseline: `content_signature sha256:44ad4449…` (matches the value published in
`docs/MODULE_LIFECYCLE.md:276`), `artifact.digest sha256:6c6e103d…`,
`studies.parquet sha256:19d25aa4…`, `module_binding sha256:99d2dc1b…`.

| An edit here | `content_signature` | fact signature | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row / delete a row | **moves** | n/a — none exists | **moves** | **un-closed** |
| edit an authored cell (filled one `population`) | **moves** (`a65110a2…`) | n/a | **moves** (`876793d8…`) | **un-closed** (`d17a2aa9…`) |
| provenance-only cell (`fetched_at`, `source`, `status`) | — | — | — | — · **this table has no such column**; `source` is refused by name (see *What does not exist*) |
| reorder two rows | **same** (`44ad4449…`) | n/a | **MOVES** (`439b5ead…`, parquet `fc937ebc…`) | **un-closed** (`1396dea0…`) |
| widen the header with 3 all-blank columns | **same** | n/a | **same** (parquet byte-identical) | **un-closed** (`390c19dc…`) |
| rewrite CRLF → LF | **same** | n/a | **same** | **stays closed** — only `manifest.inputs[studies.csv]` moves (`48a85052…`/849 B → `a4fa9feb…`/815 B) |
| recompile unchanged | same | n/a | same | same |
| re-run the producing pass | n/a — no pass produces this table | | | |
| delete the file and re-derive | **impossible.** Nothing can re-derive an authored table; deleting it deletes curated work and, if `variants.csv` is present, breaks the compile | | | |
| recompile under a newer toolchain | same (it is over parsed rows) | n/a | may move (parquet bytes / compiler version) | unaffected |

1. **Inside `content_signature`? Yes.** It is one of `_INPUT_FILES`, hashed as
   `model_dump(mode="json", exclude_none=True)` per row, rows sorted by canonical JSON, files sorted
   by name (`integrity.py:232-246`). Two consequences you will meet: **row order does not matter**,
   and **an unset optional column does not exist** — which is why widening the header with blanks
   changed nothing at all. It has no fact-field constant, because fact signatures are for derived
   sidecars only.
2. **Inside `artifact.digest`? Yes** — `studies.parquet` is in `ARTIFACT_PARQUETS`, and that tuple
   is `artifact.digest` order. The parquet **preserves authored row order**, so the digest is
   sensitive to a reorder that `content_signature` deliberately ignores. That asymmetry is stated at
   `integrity.py:222-225` and is the single most surprising thing about this table.
3. **Does an edit un-close the module? Yes, for any byte change except a newline rewrite.** The
   closure binds `compiler.authored_input_entries` (`compiler.py:361`), which reads `\r\n` as `\n`
   since RM82 (`integrity.newline_normalized_file_entry:93`) and normalizes the reported `size` too.
   Everything else is bytes: the blank-column widening above moved **no identity of any kind** and
   still un-closed the module — the exact shape of the `authorship:` append the lifecycle doc warns
   about, reproduced on this table.
4. **Part of the §5.1 canary? No, and it cannot be.** The canary is *content unmoved + a **fact**
   signature moved* (`docs/MODULE_LIFECYCLE.md:260-272`). `studies.csv` has no fact signature, so it
   can never produce that reading. What it can do is **feed** the one canary that touches citations:
   `literature.signature` is over `LITERATURE_FACT_FIELDS = (pmid, doi, pmcid, exists)`
   (`schema/src/just_dna_format/literature.py:70`), so a paper being pulled from PubMed's index moves
   it with nothing authored. And, as everywhere, detecting that requires **delete-and-re-derive**:
   `literature.csv` is merge-not-clobber and a re-run never re-asks (`literature.py` docstring at
   `enricher/src/just_dna_enricher/literature.py:730-733`).

## Required to exist

- **`studies.csv` is required iff `variants.csv` is present.** Missing with variants →
  `"studies.csv is missing. Grounding evidence is mandatory; add study rows with PMIDs."`
  (`compiler.py:3635-3637`), a hard **error** in both modes. The reason is at `compiler.py:3609-3616`
  and it is *not* the one you would guess: the 0.4 tables are exempt because `StudyRow` could only
  name a variant, so for a gene-keyed table the requirement was **unsatisfiable**, not merely unmet.
- **Legal with no `variants.csv` at all.** It loads, validates and compiles to `studies.parquet`.
  `reference_examples/fmr1_cgg_repeat` is the worked case: `repeat_alleles.csv` + `literature.csv` +
  a two-row `studies.csv` whose header is `pmid,conclusion`.
- **Present but empty is an error even in a module with no variants** —
  `"studies.csv is present but has no study rows. Grounding evidence is mandatory."`
  (`compiler.py:3625-3628`), unconditional. Never scaffold an empty one to keep another table
  company.
- **`studies.csv` alone is not a module.** It is not a "recognized table"; a spec with only
  `module_spec.yaml` + `studies.csv` fails with *"module has no recognized table"*
  (`compiler.py:3605`). The scaffolder pairs them symmetrically —
  `COMPANION_KINDS` at `compiler/src/just_dna_compiler/scaffold.py:48-51`.
- **It drags in `literature.csv`** the moment you run the literature pass, and that pass **refuses**
  a module with neither study rows nor a bin `pmid` (`literature.py:765-769`).

## The columns that carry judgement

- **`pmid`** — required, free-form, kept **verbatim**. The check is *"does the cell contain at least
  one PubMed token"*, not *"is the cell a PMID"*. Read the grammar traps below before writing one.
- **`conclusion`** — what this paper concluded, in the curator's words. The only place the module
  says why the citation is here; nothing checks it, which is exactly why it is worth writing.
- **`population`** — an effect estimated in one ancestry frequently does not transfer. A blank means
  *unknown*, never *all populations*.
- **`p_value` vs `p_value_num`** — the string is the record, the number is what a consumer
  thresholds on. The compiler compares them at **1 % relative tolerance** and skips any string that
  does not denote one definite value (`"<0.001"`, `"NS"`, `"5e-8 (adjusted)"`) —
  `_check_p_value_num`, `compiler.py:2542-2574`. Warning in `best_effort`, **error** in `strict`.
- **`p_value_num` is (0, 1]** and an exact `0` is **refused**, not stored: a zero is a source's own
  float64 underflow, not a probability (`spec.py:993-1000`). A mantissa/exponent pair was drafted
  and dropped — see *What does not exist*.
- **`effect_size` + `effect_measure` + `effect_allele`** — `effect_allele` is new in 0.6 (RM91,
  `spec.py:952-966`) and it is what the magnitude is *relative to*. Absent means the study did not
  state one, **which is not the reference allele**. Getting it wrong **inverts** the finding rather
  than breaking it, which is why the compiler checks it against `resolution.csv`
  (`_check_study_effect_alleles`, `compiler.py:2105-2153`) — and **withholds** on any row it cannot
  resolve, because unresolvable is unknown.
- **`stat_significance`** is a **closed** vocabulary (`significant|suggestive|not_significant|unknown`)
  — `unknown` is a real member, so use it rather than leaving a blank you mean as "checked, unclear".
  **`effect_measure` is OPEN** — `"wibble"` is accepted (measured). Do not read the pick-list as a
  guard.
- **`provenance_quote` / `provenance_regex`** — the attestation pair. `quote_matches` is
  whitespace- and case-insensitive literal containment (`literature.py:620`); a regex runs in a
  **child process under a wall-clock timeout**, and a timeout is recorded as **not checked**, never
  as not found (`regex_matches`, `literature.py:630-646`). The regex must `re.compile` at author
  time (`spec.py:1053-1066`).
- **`doi`** — must contain a `10.<registrant>/<suffix>` token, kept verbatim; a `doi.org` URL is
  fine. It does **not** relax the `pmid` requirement.

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **The article's own title passes every quote check there is.** A title occurs in its own
   fulltext, so `quote_matches` finds it, `quotes_found` counts it, and the module reports quote
   coverage over a string obtainable from `esummary` without retrieving a word of the article.
   Measured across the four published `antonkulaga/*` modules: 3668 of 3668 rows carry a
   `provenance_quote`, 81 PMIDs, and there is **exactly one distinct quote per PMID** — the title,
   verbatim, trailing period included, byte-for-byte what `lookup_citation` returns as `title`
   (`F42` / upstream `S54`).

   **The detection rule is the shape, not the string.** One identical quote across every row citing
   a PMID is not a located passage whatever it says, because different rows cite the same paper for
   different findings. Check your own module with a two-line group-by before publishing.

   Two consequences worth carrying:

   - **On those four modules the check never even ran.** `literature.csv` records
     `quotes_authored: 0` and an empty `quotes_found` on every row, because the literature pass ran
     before the quotes were authored and the sidecar is merge-not-clobber. The manifest then
     publishes `quotes_authored: 0, quotes_found: 0` beside 3668 authored quotes — a confident zero
     over a null (upstream `S56`). So `quotes_found` is not a detector for this; the group-by is.
   - **A catalog-derived row may have no quotable passage at all.** Where a `studies.csv` row comes
     from a GWAS Catalog association rather than from the paper's prose, the paper frequently never
     names the variant: measured on `aggression_anger`, none of the 65 rsIDs cited to PMID 29500382
     appears in that article's retrievable text, because the associations are in its supplementary
     data. The honest cell there is **empty**, and empty splits into *read and not found* versus
     *no fulltext retrievable* — see `find-evidence`.

2. **A bibliographic string in `pmid` silently cites a different paper.** `PMID_PATTERN` is
   `\b(\d{1,8})\b` (`spec.py:81`) and it runs over the **whole free-form cell**. Measured on
   format 0.6.1:

   | authored `pmid` | `extract_pmids` returns |
   |---|---|
   | `Goto 1990` | `['1990']` — accepted |
   | `[PMID: 9545397] Goto 1990` | `['9545397', '1990']` — **two** citations |
   | `Monaghan 2013 (ACMG)` | `['2013']` |
   | `doi:10.1038/ng.3097` | `['10', '1038', '3097']` |
   | `chr6:26093141` | `['26093141']` |

   PMID `1990` is a real record: *"Correlation between molecular size and interferon- inducing
   activity of poly I:C."* (Arimura H, *Acta virologica*, 1975) — checked with `lookup_citation`.
   Nothing refuses it, the literature pass fetches it, `exists=True`, and
   `split_cited_literature` (`compiler.py:5563`) counts it as cited, so **no orphan warning fires**.
   The module ships a confident citation of a 1975 virology paper. **Write the digits and nothing
   else**, or the bracketed `[PMID: N]` form with no year beside it. This is the same class as the
   PMC trap below.

   > ⚠️ **CHECK — "not filed upstream" is half right.**
   > **Current state.** The format repo's 1.0 queue does carry an item titled *"`StudyRow.pmid`
   > required + PMID-shaped"*, so the *shape* fix is tracked. Its body argues only the requiredness
   > half, and nothing anywhere records what the permissive grammar does **today** — which is the
   > substantive point above, and it stands.
   > **Expected state.** Until that item ships, `extract_pmids` keeps returning every 1–8 digit run
   > in the cell. Write the digits alone, or `[PMID: N]` with no year beside it.
3. **PMC is not PubMed, and it used to turn on a space (RM50).** `PMC 3110566` once parsed as PMID
   3110566, a real record for another paper. Both spellings now refuse, and the message **names the
   id it saw** (`validate_pmid_cell`, `spec.py:134-172`). It **never repairs** — use
   `lookup_citation(pmcid=…)`, which reports the PMID as an advisory. A cell carrying **both**
   (`21551363; PMC3110566`) is accepted and yields the real PMID.
4. **A reorder moves `artifact.digest` and un-closes the module while `content_signature` stays
   identical.** Measured above. Sorting your `studies.csv` "to tidy it up" spends a rebuild and the
   closure, and a registry content-dedup lookup will still say the data is already published.
5. **A row may name no variant at all (0.6 / RM47) — but never half of one.** `REQUIRED_ANY_OF` is
   `()` (`spec.py:920`). `StudyRow(pmid="12345", conclusion="x")` is accepted and its `variant_key`
   is `None`. But `start` or `ref` with neither `rsid` nor `chrom` **raises** — that is a blank cell
   in the middle of a coordinate, not an absent subject (`spec.py:1066-1105`). Consumers holding a
   negative test broke on this (S40, `docs/CONSUMER_SUGGESTIONS_HISTORY.md:1760-1790`); the
   load-bearing consequence is that **a null `variant_key` in a polars join is a silently smaller
   result, not an error**.
6. **`chrom` is not validated on a `StudyRow`.** Measured: `StudyRow(pmid="1", chrom="banana",
   start=1)` is accepted and keys as `banana:1:None`. `spec.py:902-903` says so deliberately (only
   `VariantRow` runs a chrom validator). A typo'd chromosome therefore surfaces only as the
   generic *"Studies reference variants not in variants.csv"* warning.
7. **The study must carry the *same identity* its variant row got.** Matching is on any shared
   handle — same rsid, or same `chrom:start:ref` **regardless of alt**
   (`_cross_validate_studies`, `compiler.py:3130-3160`; and
   `reference_examples/pathogenic_clinvar/README.md:137`). Key a variant by coordinate and cite it
   by rsID and it is an orphan. The ClinVar drafter handles this for you (`clinvar_draft.py:428-432`)
   and its comment records that a real panel found it the hard way.
8. **A ClinVar re-draft after 0.6.3 leaves stale rsid-only rows in `studies.csv`, and nothing names
   them.** `_superseded_rsid_rows` (`clinvar_draft.py:344-390`) is the S45 repair and it is called
   **once**, over `report.path` — the `variants.csv` report (`clinvar_draft.py:610`). `_study_rows`
   honours the same `ambiguous` set (`clinvar_draft.py:431-432`) and appends coordinate-keyed rows
   beside the old rsid-only ones, whose dedup key differs, so both survive. The stale study rows do
   surface — as an *orphan* warning, because their rsID is no longer in `variants.csv` — but the
   diagnosis points at the wrong thing.

   > 🚧 **ROADWORKS — the S45 supersession sweep does not reach `studies.csv`.**
   > **Current state.** Confirmed against the code: `_superseded_rsid_rows` has exactly one call
   > site, and it is handed the `variants.csv` append report. No pass looks at the study rows, so a
   > re-draft leaves both the stale rsid-only row and its coordinate-keyed replacement on disk, and
   > the only symptom is a *"Studies reference variants not in variants.csv"* orphan warning that
   > blames the citation rather than the supersession.
   > **Expected state.** Either the sweep covers every table the re-draft appended to, or the orphan
   > warning distinguishes *superseded* from *miscited*. Neither exists today.
   > **Guard.** After any ClinVar re-draft of an existing module, diff `studies.csv`'s rsIDs against
   > `variants.csv`'s and delete the stale rows by hand **before** compiling. Do not read that orphan
   > warning as "my citation is wrong" — rule out supersession first.
9. **`p_value_num` is redundancy-bearing, so do not derive it from `p_value` mechanically and then
   treat the agreement as a check.** It is one number written twice on purpose; the check catches a
   transcription slip and nothing else.
10. **A quoted passage from a non-commercial article warns and never gates.** `_check_quoted_article_licenses`
   (`compiler.py:5607-5640`) fires only when a study row carries a quote **and** the matching
   `literature.csv` row says `commercial_use is False`. `None` is unknown and withholds. The format
   refuses to arbitrate copyright — that is a decision, not an omission (`SCHEMAS.md:1066-1078`).
11. **A `strict` compile does not mean the citations are right.** `--strict` means *reproducible*.
    A module citing PMID 1990 for everything compiles green.
12. **Drafted files are CRLF; hand-written ones are LF.** Measured across the reference corpus: 4 of
    the 10 `studies.csv` files are CRLF (`hboc_palb2`, `hfe_hemochromatosis`, `par_boundary`,
    `shox_par1` — all drafter-written; `csv.DictWriter` defaults to `\r\n`), 6 are LF. RM82 is what
    stops your editor's newline normalization from un-closing the module.
13. **Most of this table is never used.** Measured over all 10 reference `studies.csv` files: only
    **6 of the 18 authored columns appear anywhere** — `pmid` (10 files), `rsid`/`chrom`/`start`/`ref`
    (6), `conclusion` (5), `study_design` (1), `population` (1). Zero instances of `p_value`,
    `p_value_num`, `stat_significance`, `effect_size`, `effect_measure`, `effect_allele`,
    `trait_efo_id`, `doi`, `provenance_quote`, `provenance_regex`. Treat the reference corpus as
    evidence of the *floor*, not of good practice.
14. **`describe_table` can be stale if the MCP server process is older than the installed
    packages.** Measured in this workspace: the plugin-cache server at
    `~/.claude/plugins/cache/just-dna/just-module-creator/0.7.0` runs format **0.5.4** and answers
    `any_of: [["rsid"],["chrom"]]` with **no `effect_allele` column**, while
    `/data/sources/just-module-creator/.venv` (format 0.6.1) answers `any_of: []` and lists
    `effect_allele`. *Ask the tool* only beats *ask memory* when the tool is current — check
    `importlib.metadata.version("just-dna-format")` against `StudyRow.REQUIRED_ANY_OF == ()` if an
    answer looks pre-RM47.

## What does not exist

- **No fact signature, and there will not be one.** Fact signatures are the derived-sidecar
  mechanism. An authored table's identity is `content_signature`.
- **No `source` column, refused by name.** Measured: `StudyRow(pmid=…, source="clinvar")` raises
  *"'source' is recorded on GENERATED tables only — resolution.csv, frequencies.csv,
  gene_metrics.csv and literature.csv, where a pass names the link that answered."* A consumer
  proposed adding one so a `layer='literature'` licence row would join; it was **refused on both
  sides**, upstream and by the reporter (`docs/history/CONSUMER_SUGGESTIONS_HISTORY_PRE_0_6.md:1783,1831`).
- **No DOI-only citation.** `pmid` is required and must parse to a PubMed token, so a preprint,
  book or thesis with only a DOI is **unauthorable**. Demoting a required field is barred by
  Principle 8 within a major; the fix is *doi-first at 1.0* — require at least one of `{doi, pmid}`.
  Explicitly parked, not forgotten (`docs/USE_CASES.md:283-291`).
- **No `neg_log10_p` in the CSV.** Derived on write, materialized only into the parquet
  (`spec.py:1018-1033`). Authoring it would make a human compute a logarithm to write a row down.
- **No mantissa/exponent pair for sub-float64 p-values.** Drafted and dropped: it is the GWAS
  Catalog's representation and a catalogue-of-millions problem, and two columns plus a
  both-or-neither rule is a cost every author pays. A value below ~1e-308 now reads as *indefinite*,
  not as zero (`docs/SCHEMAS.md:425-431`).
- **No `sample_size`, `standard_error`, `confidence_interval`, `ancestry`, `effect_unit`,
  `study_accession`.** Those live on `just_dna_format.gwas.GwasEffectRow` → `gwas_effects.csv`, the
  0.6 derived-fact table filled by `just-dna-enricher gwas`. If you want machine-transcribed
  published effect sizes, that is the table — not this one.
- **Nothing here can key a binning bound.** A study row identifies a *variant* or nothing; it can
  never name "the 36/40 CAG threshold". The 0.6 rule is **the bin row cites, the citation table
  describes** — put the PubMed id on `MeasureBinRow.pmid` and describe the paper in a subject-less
  `studies.csv` row. Both citation sites are read by the literature pass and by
  `_cross_check_literature` (`compiler.py:5510-5530`).
- **No `bin_evidence.csv` join table.** Rejected: it would have to key on the thresholds, and they
  are floats — re-authoring `40` as `40.0` orphans the evidence with nothing able to notice
  (`docs/SCHEMAS.md:74-79`).
- **No enricher pass writes into this file, ever.** Not a gap — `content_signature` is documented as
  reference-independent, and a network fetch that could move it would make that property false
  (`literature.py:8-11`).

## Consumption today

Every read site found outside format/compiler/enricher.

**just-dna-lite — the only consumer of the compiled table, and it reads 5 of 18 columns.**

- `just-dna-pipelines/src/just_dna_pipelines/annotation/report_logic.py:810-860` —
  `load_studies_for_variants`: scans `studies.parquet`, filters to the annotated rsID/locus sets,
  and projects exactly `pmid`, `population`, `p_value`, `conclusion`, `study_design`.
- `report_logic.py:764-787` — `_study_key`: rsID where present, else `chrom:start:ref`. Its
  docstring records that keying on rsID alone lost **34,697 of 121,467** cardio study rows.
- `report_logic.py:838-839` — sniffs for `chrom`/`start` before taking the coordinate branch (0.5+).
- `report_logic.py:723-725`, `891`, `990`, `1046` — attaches the rows to each variant view model;
  called by the longevity, generic-module and pharmacogenomics report builders.
- `report_logic.py:636-644` — `pmid`s go into the "ask an LLM about this variant" prefill prompt.
- `templates/longevity_report.html.j2:669-694` — the one rendering surface: a "Supporting studies"
  table linking each PMID to PubMed.
- `annotation/hf_modules.py:207,240,536-543` — resolves `studies_url` from `manifest.artifact.files`.
  `hf_modules.py:587` (`scan_module_studies`) is public and called by nothing.
- Producer side (writes, does not consume): `v1_port/adapters.py:255,377,403,537,768,785,879`,
  `v1_port/writer.py:95`, `v1_port/runner.py:314-329`, `v1_port/clinvar_panel.py:277-380`.
- **No test covers the report-side path** — `load_studies_for_variants` / `_study_key` appear in the
  pipelines test suite only in a comment (`tests/test_module_compiler.py:275`).

**just-dna-registry (and `just-dna-marketplace`, a symlink to it) — reads the CSV, never the parquet.**

- `src/just_dna_registry/specfiles.py:53` — `CORE_CSVS = ("variants.csv", "studies.csv")`: upload
  acceptance and spec rebuild. The comment at `:51-53` says the required-iff rule is *the
  compiler's, not this module's*.
- `specfiles.py:280` — `SIGNATURE_INPUTS` includes it; `services/signatures.py:100-113` materializes
  it into a temp spec dir and calls the compiler's `content_signature`.
- `services/upgrade.py:152` — `_ROW_MODELS["studies.csv"] = StudyRow`, used at `:471`/`:478` to trim
  or block a stored CSV carrying a column the current contract rejects.
- `services/revalidate.py:130-143` — `gather_pmids`: `csv.DictReader` + `extract_pmids` over the
  `pmid` column. Reached only from `registry revalidate --check-pmids` (`cli.py:528-578` →
  `services/pmid_check.py:15`). Opt-in ops path; never on publish.
- `api/routers/publish.py:441` + `services/enrich.py:1086-1130` — `?literature=true` preflight runs
  `enrich_literature(write=False)`. Transient; nothing stored.
- `services/catalog.py:245` — `study_count` copied from `manifest.stats` onto every module card
  (`models/api.py:16`). `client.py:1009` sums it across pages.
- **Zero hits** under `src/` for `studies.parquet`, `p_value_num`, `neg_log10_p`,
  `provenance_quote`, `provenance_regex`, `literature.parquet`. No DB column, no facet, no filter,
  no sort on anything study-derived. `has_clinical_assertions` is ClinVar, **not** studies.

**just-prs / just-prs-mcp — nothing reads it.** Their `pmid`/`doi`/`effect_allele`/`trait_efo_id`
columns are PGS Catalog metadata; `gwas_studies.parquet` in
`just-prs/prs-pipeline/src/prs_pipeline/metadata_assets.py:211` is the GWAS Catalog bulk TSV, a
different table entirely.

**Verdict:** exactly one code path anywhere reads a compiled `studies.parquet` —
`report_logic.load_studies_for_variants` — and it keeps five columns. The registries treat the table
as opaque compiler-owned payload and surface one scalar.

## Blanks for just-dna-lite

- **`p_value_num` and `neg_log10_p` are written and never read — including by lite's own producer.**
  `v1_port/adapters.py:250-257` computes `_p_value_pair` and stores both, and
  `report_logic.py:853-858` projects only the free-form `p_value` string. Ask: sort the "Supporting
  studies" table by `neg_log10_p` and mark rows at ≥ 7.3 as genome-wide significant. What breaks
  today: the report lists studies in parquet order, so a nominal `p=0.04` sits above a `5e-30`.
- **`provenance_quote` / `provenance_regex` reach no reader.** They are the only columns in the
  whole format that let a reader jump from a claim to the sentence behind it, and no consumer
  renders them. Ask: show the quote under the citation, and show
  `literature.quotes_found` as a three-state badge — **checked/found**, **checked/not found**,
  **could not be checked** (null). What breaks today: a curator who does the most expensive
  authoring work in the format gets no surface for it, which is why 0 of 10 reference modules
  bother.
- **`effect_size` + `effect_measure` + `effect_allele` are unrendered, so a wrong effect allele is
  invisible to a reader.** The compiler warns when the allele is not at the locus
  (`compiler.py:2105`), but the report shows neither. Ask: render `effect_size (effect_measure)
  relative to effect_allele` as one string, and **withhold entirely** when `effect_allele` is null
  rather than showing a bare number. What breaks today: a magnitude with no referent is worse than
  no magnitude — it inverts rather than breaks.
- **`literature.parquet` is never read anywhere in lite.** Every citation quality signal the
  enricher produces — `exists`, `is_open_access`, `license`, `doi_exists`, `quotes_found` — dies in
  the module. Ask: join it to the studies rows and mark a citation PubMed has no record of.
- **The subject-less study row has no home in the report.** RM47 rows carry `variant_key = None`,
  and `load_studies_for_variants` filters `rsid.is_in(rsids)` — correct, and it means a citation
  that grounds the *module* or a *bin boundary* is dropped silently. Ask: a module-level "Evidence"
  section fed by rows with a null key, plus the bin `pmid`s. What breaks today: `fmr1_cgg_repeat`'s
  ACMG threshold citation reaches no reader at all.
- **No test covers the studies read path.** Ask for one against a real compiled module, asserting
  the coordinate branch and the null-key case — the coordinate join is what recovered 34,697 rows
  and it is pinned by nothing.

## Ask the live schema

Never write a column list or a vocabulary from this file. Run:

```python
describe_table("studies.csv")     # columns, types, vocabularies + closed/open,
                                  # redundancy_bearing per column, attestation_bearing subset
table_requirements("studies.csv") # always / any_of / defaulted / optional
authoring_reference()             # every model at once; large — prefer describe_table
get_template("studies.csv", stub=True)   # header + <<REPLACE>> stubs
lint_rows("studies.csv", csv_text)       # per-cell validation with line numbers, no disk, no network
```

Sanity-check that the surface you are talking to is current — `any_of` must be **empty** on
format ≥ 0.6 and `effect_allele` must be in the column list:

```python
from just_dna_format.spec import StudyRow
assert StudyRow.REQUIRED_ANY_OF == ()          # RM47
assert "effect_allele" in StudyRow.model_fields # RM91
```

Everything quoted verbatim in this file was checked against format 0.6.1 / compiler 0.6.1 /
enricher 0.6.4 on 2026-08-19.
