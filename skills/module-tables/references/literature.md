# literature.csv — does each citation this module makes actually check out, and on what terms

> **Audit banner — 2026-08-19.** This file was re-checked against the installed toolchain
> (format 0.6.1, compiler 0.6.1, enricher 0.6.4 — the versions it was written against) by a
> three-way pass: this file, versus the format repo's `docs/`, versus the code, with **the code as
> arbiter**. Symbol references held up; the `file:line` numbers have drifted with the tree, so
> anchor on the symbol name and not the line. Two markers were added below — 🚧 **ROADWORKS** for a
> surface that is broken or unfinished, always with a guard saying what to do instead, and
> ⚠️ **CHECK** for a claim whose current state is not what the surrounding text would lead you to
> expect. Anything unmarked either held on re-check or was not reached; coverage was thorough, not
> exhaustive.

> **Correction, 2026-08-20 (later than the banner above).** This file says `describe_table`
> refuses this table and quotes that refusal's wording. Both were true when written and are not
> now: **ask `describe_machine_table`**, which answers the live columns of all seven
> machine-produced tables and carries `hand_authored=False` in its own schema. Nothing about
> *you read this, you never hand-finish it* has changed — that signal is now carried by the tool
> split rather than by a refusal.

## What it is

`literature.csv` answers one question per **cited article**: *does that citation exist, do its
identifiers agree with the registries', was the quoted passage found, and what licence does the
article carry.* It is the third derived-fact sidecar and **the first not keyed on a variant** — "a
DOI, a PMCID and 'does PubMed have this record' are properties of the *article*" — so "a module with
three hundred variants citing five papers carries five rows here, not three hundred with the same DOI
repeated" (`schema/src/just_dna_format/literature.py:1-14`). Its audience is a compile-time reviewer
and a downloader asking whether a module's evidence base resolves; it is **not** bibliography (see
*What does not exist*).

Read it against its two lookalikes. `studies.csv` is authored annotation and asks *why do I believe
this row?*; `literature.csv` is a verification record **over** those citations; `sources.csv` /
`licensing.csv` is one level up again and describes *datasets* (`docs/SCHEMAS.md:1050-1062`).

> **Path shorthand in this file:** `format/` = `just-dna-format/schema/src/just_dna_format/`,
> `compiler.py` = `just-dna-format/compiler/src/just_dna_compiler/compiler.py`,
> `enricher/` = `just-dna-format/enricher/src/just_dna_enricher/`. Everything else is absolute
> from a repo root. Two files are both called `literature.py`; the prefix says which.

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.literature.LiteratureRow` (`schema/src/just_dna_format/literature.py:78`) |
| Parquet | `literature.parquet` — in `ARTIFACT_PARQUETS` (`compiler/src/just_dna_compiler/compiler.py:290`), so inside `artifact.digest`. Registered in `_FACT_TABLES` at `compiler.py:327` |
| Natural / dedup key | `pmid`, digits only. The enricher merges on `existing[row.pmid]` (`enricher/src/just_dna_enricher/literature.py:772-777`). One row per article, however many study rows cite it |
| Authored or machine-produced | **machine-produced, human-overridable.** Standalone `BaseModel` (not an `AuthoredModel`), `extra="forbid"` so a typo'd column is refused rather than dropped |
| Who writes it | `enricher.literature.enrich_literature` (`just-dna-enricher literature <dir>`; our `enrich_literature_pass`). **Online only** — `--offline` is a documented no-op |
| Fact signature | `integrity.literature_signature` over `literature.LITERATURE_FACT_FIELDS` = **4 of 17 fields** — `pmid`, `doi`, `pmcid`, `exists` (`format/literature.py:70-76`, `format/integrity.py:305`) → `manifest.literature.signature` |
| In `content_signature`? | **No.** Not in `_INPUT_FILES` (`compiler.py:267`). Measured: no edit here moved it |
| In `artifact.digest`? | **Yes**, via its parquet — and only over the **kept** rows (RM79). Also byte-hashed into `manifest.derived[]`, transport only |
| Manifest block | `manifest.literature` = `{signature, sources, row_count, resolved_count, missing_count, open_access_count, abstract_only_count, quotes_authored, quotes_found}` (`manifest.py:580`, built at `compiler.py:5102`); absent when the module carries no sidecar |
| Location | root or `derived/literature.csv`, resolved through `licensing.sidecar_path` (`enricher/literature.py:748`). Both at once is a `SidecarCollision` error, never a merge |
| Vocabularies | `quote_source` → `vocab.VALID_QUOTE_SOURCE` = `{fulltext, abstract}`; `status` → `vocab.VALID_RESOLUTION_STATUS` = `{resolved, not_found, ambiguous}` |

## Who populates what

- **enricher pass — everything.** `enrich_literature` (`enricher/literature.py:706`) writes every one of the 17
  columns. `pmid`, `doi`, `pmcid`, `exists`, `source="pubmed"`, `status` come from PubMed `esummary`;
  `is_open_access`, `license` and the fulltext/abstract come from Europe PMC `search`;
  `share_alike`/`commercial_use`/`redistribution` are mapped from `license` by
  `licensing.article_terms` (`enricher/licensing.py:315`); `doi_exists`/`doi_checked` come from Crossref;
  `quotes_authored`/`quotes_found`/`quote_source` are computed against `studies.csv`. The header is
  `list(LiteratureRow.model_fields)`, derived from the model, never hand-kept (`enricher/literature.py:91-96`).
- **author** — no column is *expected* of a human and every column *may* be written by one. `source`
  is open vocabulary, and a curator's correction is expected to spell it something other than
  `pubmed`: `_REGISTRY_SOURCE` is the only value the identifier cross-check compares against, because
  "a merged row spelling anything else … holds the curator's own identifiers, and calling a
  disagreement with those 'the registry's' would be a false attribution" (`enricher/literature.py:101-105`).
  A `source=manual` row is therefore **skipped** by `_compare_identifiers` and counted as
  `identifiers_foreign` (`enricher/literature.py:1120-1126`).
- **drafter** — **none.** `literature.csv` is not in `just_dna_compiler.draft.DRAFTABLE`, so there is
  no `<<REPLACE>>` stub and no `draft_from_*` route. This is also why `describe_table`,
  `table_requirements` and `get_template` all **refuse** it — see *Ask the live schema*.
- **compiler-stamped** — nothing. No column is `base.stamped_identity_field`, `COMPILER_MANAGED` or
  `reject_compiler_filled`; the model carries no compiler-stamped field at all, which is why
  `model_fields` is exactly the writable surface (`enricher/literature.py:94-95`). The compiler reads, warns,
  drops uncited rows from the artifact, and never writes a cell of this CSV.
- **registry-stamped** — nothing is in `normalize.IDENTITY_AUTHORITY_KEYS`. The registry does carry
  the file (`just-dna-registry/src/just_dna_registry/specfiles.py:97-105` `FACT_CSVS`) and re-parses
  it through `LiteratureRow` on `revalidate`/`upgrade`
  (`services/upgrade.py:43,167`) — header comparison only, which can **lossily trim an unknown
  column**.
- **nobody, ever** — no permanently-unwritten column; all 17 have a producer.

**Which cells no tool may fill even though it easily could.** None *on this table* — every column here
is machine-produced by construction. The refusals live on the **authored** side it checks, in
`studies.csv`, and they are the reason this table can say anything at all
(`compiler/src/just_dna_compiler/hints.py:81-108`):

- `doi` — `redundancy_bearing`: "enricher.literature._doi_conflicts (authored doi vs the registry's)".
  Filling it from PubMed makes the check compare PubMed against PubMed.
- `pmid` — `redundancy_bearing`: `literature.exists` asks PubMed whether the **authored** pmid
  resolves, so filling it from NCBI's id converter compares NCBI with itself. `lookup_citation(pmcid=…)`
  therefore returns the resolved id as an advisory with `applied=False`,
  `refusal="redundancy_bearing"`.
- `provenance_quote` / `provenance_regex` — in **both** `REDUNDANCY_BEARING` and
  `ATTESTATION_BEARING` (`hints.py:72`). Upstream glosses the latter as *a curator read this passage
  in this paper*, reading "curator" as a human, and on that reading extracting a passage from a
  fetched fulltext "states something false". **That gloss is correct for their layer and is not the
  rule here — reversed 2026-08-20 under `RM15`.** An agent that reads the article is a real reader,
  so the column needs **attribution, not abstention**: locate the passage, quote it verbatim for the
  row's own claim, and record who located it. The reasoning we originally supplied for that constant
  is withdrawn upstream as `S55`, which asks for the per-row attributor instead (accepted and added to
  `StudyRow` in their tree as `RM120`; **not released**, so `F43` stays open). What survives is
  physics: no *lookup* may write the cell, and the cell must never hold something obtainable **without
  reading the article** — a title, above all.

**And the honest consequence, which no constant repairs:** once a machine has retrieved the fulltext
(our `fetch_fulltext`, or the pass itself), `quotes_found` on that row has degraded to a
**citation-pairing check** — it still catches a passage filed against the wrong PMID, and it no longer
shows that the claim is in the literature (`docs/ENRICHER.md:1704-1714`). **State that; never use it to
refuse.** The alternative is not a better quote, it is an empty column — or a title, which passes the
check while witnessing nothing (`F42`).

## What moving this table moves

Measured on `reference_examples/hboc_palb2` (10 literature rows), compiling each mutation from a fresh
copy and diffing the manifest. `base`: `content_signature sha256:43ad8ac1…`,
`artifact.digest sha256:6876cc79…`, `literature.signature sha256:34ab06e5…`,
`verification.module_hash sha256:527abadc…`.

| An edit here | `content_signature` | `literature.signature` | `artifact.digest` | attestation + closure |
|---|---|---|---|---|
| add a row **nothing cites** (orphan) | same | **same** | **same** | unchanged, still closed |
| add a row for a citation the module makes | same | **moved** | **moved** | unchanged |
| edit a fact cell (`doi`) | same | **moved** | **moved** | unchanged |
| edit a non-fact cell (`license`, `is_open_access`, `quotes_*`) | same | **same** | **moved** | unchanged |
| edit a provenance-only cell (`fetched_at`, `source`, `status`) | same | **same** | **moved** | unchanged |
| reorder rows | same | **same** (order-independent) | **moved** | unchanged |
| delete the file | same | block **absent entirely** | **moved** | unchanged, still closed |
| re-run the pass, citations unchanged | same | same | same (merge rewrites nothing) | unchanged |
| delete + re-derive against an unchanged source | same | same | **moved** (fresh `fetched_at`) | unchanged |
| recompile under a newer toolchain | same | same | may move | unchanged |

The orphan row is the interesting one and it is measured, not asserted: adding
`11788828,…` to `hboc_palb2/literature.csv` moved **nothing** — not the digest, not the signature,
not `row_count` (still 10) — and produced exactly one warning, *"literature.csv describes 1
citation(s) no study or bin in this module cites … left out of the artifact, and left in the CSV"*
(`compiler.py:5553-5558`).

1. **Inside `content_signature`?** No. `content_signature` covers `variants.csv`, `studies.csv` and
   the table kinds (`_INPUT_FILES`, `compiler.py:267`). Its identity is instead
   `literature_signature` over the **four** fact fields. What is left out carries the argument
   (`format/literature.py:53-76`): `is_open_access` and the four licence columns are "the outside world's
   state on the day the pass ran" — an embargo lifting or a re-licensing would otherwise move a
   module's signature with no authored edit anywhere; `quotes_authored`/`quotes_found` are out
   because the first duplicates a fact already in `studies.csv` and the second depends on whether a
   fulltext happened to be retrievable that day. "What remains is stable identity: which article this
   is, and whether the registry has it."
2. **Inside `artifact.digest`?** Yes — `literature.parquet` sits in `ARTIFACT_PARQUETS`, whose
   **order is the digest order**, so it must never be repositioned. That is why a provenance-only
   column no signature sees still moves the digest: the parquet bytes differ. **But only the kept
   rows reach it** — `split_cited_literature` (`compiler.py:5563`) filters before the build, so the
   digest and `manifest.literature.*` describe the module's *current* citations by construction.
   The CSV is additionally byte-hashed into `manifest.derived[]`; that hash is transport only.
3. **Does an edit here un-close the module?** **No.** The attestation binds
   `compiler.authored_input_entries` (`compiler.py:361`) = the newline-normalized `_INPUT_FILES`,
   and this file is not in that set. Measured: `module_hash` byte-identical across every row above,
   deletion included. Editing `studies.csv` by one line **does** un-close it — measured, and the
   compile then warns *"verification.json is stale … the manifest records no verification for this
   compile"*. Note the asymmetry an author trips on anyway: an `authorship:` append to
   `module_spec.yaml` un-closes a module while moving no identity at all.
4. **Part of the canary?** Yes — `literature` is one of the six fact signatures MODULE_LIFECYCLE §5.1
   names, and row 3 (*content same, fact signature moved*) reads "the upstream source said something
   different this time". Here that means PubMed changed a DOI/PMCID or withdrew a record. **Detecting
   it requires delete-and-re-derive**, because `wanted = [pmid for pmid in citations if pmid not in
   existing]` (`enricher/literature.py:803`) never re-asks about a pinned row. Deleting is also what discards
   curator overrides, which is why the missing `--refresh` is still open upstream as **RM83**.

## Required to exist

- **Nothing requires this table.** It is optional at every tier: `_literature_block` returns `None` on
  empty, the parquet is skipped, and no compile check fails for its absence.
- **The pass requires at least one citation, from either of two sites.** `enrich_literature` refuses
  with *"no citations in {spec_dir} — … neither studies.csv rows nor a `pmid` on any binning row"*
  (`enricher/literature.py:766-770`). That is the correct and complete shape of a PGx-only module, and the
  registry's `/check` reports it as a warning, never a gate
  (`just-dna-registry/src/just_dna_registry/services/enrich.py:1118-1120`).
- **It drags in no licence row.** Deliberately and permanently: `TERMS_BY_SOURCE` has **no `pubmed`
  entry** (`enricher/licensing.py:365-378`), and the `literature` layer is in `_UNCORROBORABLE_LAYERS`
  (`compiler.py:4853`), so its `source` is excluded from `used_sources` and a hand-declared
  literature row is exempt from the orphan warning unconditionally (S23, then RM46).

## The columns that carry judgement

- **`exists`** — PubMed's answer, tri-state. `False` is a **fact** (the citation does not resolve);
  `None` means never checked. `strict` refuses on `False`; `best_effort` records it, and the compiler
  re-surfaces it offline because the verdict is already pinned (`compiler.py:5546-5552`).
- **`doi_exists`** — Crossref's answer, and a **different question**. A paywall hides the fulltext,
  not the record; a preprint, book, thesis or dataset has a DOI and no PMID. Two registries, two
  columns, never one overloaded `exists`. It checks the **authored** DOI in preference to the derived
  one, because "checking the registry's own DOI is circular — it exists by construction"
  (`enricher/literature.py:959-970`).
- **`doi_checked`** (0.6) — *which* DOI that verdict is about. Without it, correcting a bad DOI left
  `--strict` refusing and the attestation publishing a finding **naming the corrected DOI**: a finding
  no authored edit could clear. A verdict only stands while `doi_checked == the DOI the module cites
  now` (`enricher/literature.py:1004-1008`).
- **`quotes_found`** — **null means not checked**, `0` means a text was read and the quote was not in
  it. Folding null into zero is "the single most misleading thing" the manifest block could do
  (`compiler.py:5106-5108`).
- **`quote_source`** — `fulltext` or `abstract`, null when neither could be retrieved. It exists
  because **a hit is conclusive from either and a miss is only conclusive against fulltext**; an
  abstract miss is counted as *unchecked*, not as *not found* (`enricher/literature.py:1074-1085`).
- **`license`** — stored **verbatim** as Europe PMC spells it (`cc by`, `cc by-nc`, `cc by-nc-nd`,
  `cc0` — lowercase, probed over 100 records on 2026-08-13). Independent of `is_open_access` and not
  derivable from it: PMID 28546431 is `isOpenAccess: N` with `license: cc by`.
- **`share_alike` / `commercial_use` / `redistribution`** — **three orthogonal axes**, and `None` is
  never `False`. CC BY-NC forbids sale and expressly allows sharing, which is why redistribution is
  its own column; an unrecognised or absent licence maps to all-`None`, "unknown, withheld, never
  `False`" (`enricher/licensing.py:296-303`).
- **`source`** — names the bibliographic **registry that answered** (`pubmed`), not a licensed source.
  Europe PMC contributes `is_open_access`, the licence and the fulltext but "cannot originate a row
  (it silently omits ids it does not know)" (`enricher/literature.py:901-904`).

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **Merge-not-clobber means a re-run answers nothing new — including the columns that did not exist
   when the row was written.** `wanted` excludes every pinned PMID. Rows written before 0.6 carry no
   `license`, and re-running **will not** back-fill them, "because merge-not-clobber cannot tell an
   absent value from a curator's deliberate blank. Delete the sidecar to re-derive"
   (`enricher/literature.py:727-731`). Same for `doi_checked`. **Measured on the whole reference corpus:** all
   three modules carrying a `literature.csv` (`fmr1_cgg_repeat` 2 rows, `hboc_palb2` 10,
   `pathogenic_clinvar` 1) lack the `doi_checked` column entirely, so **13 of 13** rows have a
   `doi_exists` verdict the current pass counts as `doi_verdicts_stale` and leaves outside the
   denominator. A re-run reports *"N pinned DOI verdict(s) are about a DOI the module no longer
   cites"* — misleading wording for *written before the column existed* — and only `rm literature.csv`
   clears it.
2. **The three licence rights are frozen into the CSV, NOT re-derived at read time — the docs say
   otherwise and they are wrong.** `docs/SCHEMAS.md:1176-1178`, `docs/ENRICHER.md:1679-1681`, `enricher/licensing.py:296-298`,
   `enricher/literature.py:835-836` and
   `docs/RM_TOC.md` (RM46) all state that `licensing.article_terms` maps `license` to the three rights
   "at **read** time, so a mapping correction reaches rows already written". **Measured against
   installed 0.6.1/0.6.4:** `article_terms` is called in exactly one place — the enricher's fetch loop
   (`enricher/literature.py:838`) — and its result is *persisted* into the row. The compiler's
   `_check_quoted_article_licenses` (`compiler.py:5607`) reads `row.commercial_use` and never consults
   `row.license`. Probed: a row with `license="cc by-nc"` and `commercial_use=True` (or blank) beside a
   quoted study row produces **no warning**, while `article_terms("cc by-nc")` returns
   `commercial_use=False`. Practical consequences for you: (a) a fix to `ARTICLE_TERMS_BY_LICENSE`
   reaches only rows re-derived after `rm literature.csv`; (b) a hand-edited row whose booleans
   contradict its own `license` string is believed, silently.

   > 🚧 **ROADWORKS — the three article rights are frozen at write time; fixing the mapping fixes nothing already written.**
   > **Current state.** Independently confirmed: `article_terms` has exactly one call site, in the
   > enricher's fetch loop, and its three values are persisted onto the row. The compiler reads
   > `row.commercial_use` and never imports `article_terms`, so nothing re-derives anything at read
   > time. Several upstream docs described this the other way round; they were wrong, this file is
   > right.
   > **Expected state.** No change is planned — persisting the values is what makes the sidecar
   > self-describing offline. What is missing is any warning when a row's booleans contradict its own
   > `license` string.
   > **Guard.** After changing a licence mapping — or after correcting a `license` cell by hand —
   > **delete `literature.csv` and re-run the pass**. Merge-not-clobber will otherwise keep every
   > stale right in place, and no check will mention it. The same delete-the-sidecar rule applies to
   > any derived column you expect to move.
3. **The subject set is the citations the module makes NOW, not the rows the file holds.** Three
   separate defects came from getting this wrong, and the class is worth memorising: a module enriched
   once with `--best-effort` and then with `--strict` **was blessed on a citation PubMed has no record
   of**, because the gates read lists appended inside the fetch loop; an existing `literature.csv` hid
   every DOI/PMCID disagreement; and a citation deleted from `studies.csv` went on being counted with
   no authored edit able to clear it (`enricher/literature.py:172-193`). Fixed — every tally now runs over
   `subject_rows` — but the consequence remains: **`--strict` on an already-enriched module refuses on
   the pin, not on a fresh lookup.**
4. **There are TWO citation sites since 0.6 (RM47), and a bin-only one is not a gap.** `studies.csv`,
   and a `pmid` on a binning row grounding the threshold it sits on. `_citations`
   (`enricher/literature.py:683-704`) maps a bin-only citation to an **empty** study list — a real citation to
   check for existence and identifiers, carrying no quote and no authored DOI because a bin row has
   neither column. It reads as *nothing to check*, never as an unretrievable fulltext. Our own
   `enrich_literature_pass` docstring still says "every citation in `studies.csv`"
   (`src/just_module_creator/tools/passes.py:592`) — it reads both.
5. **An orphan row is warned about and silently dropped from the artifact (RM79).** The row stays in
   the CSV — it is the pin that keeps a re-run cheap — but never reaches `literature.parquet`,
   `manifest.literature.*` or `literature_signature`. Measured above: adding one moved nothing. So
   `row_count` is *the module's current citations*, not the file's line count, and every counter
   beside it shares that denominator (`manifest.py:596-603`).
6. **`quotes_authored: 0` everywhere in the reference corpus, and zero attested literature checks.**
   Measured: **no** `reference_examples/*/studies.csv` carries a `provenance_quote` or
   `provenance_regex`, and all three `verification.json` files with a literature sidecar carry
   `checks: []`. The entire quote-matching and attestation half of this table has **no corpus
   coverage** — it is pinned by unit fixtures only. Do not treat a green reference example as evidence
   that quote checking works on your module.

7. **`quotes_authored: 0` also happens beside a `studies.csv` full of quotes, and nothing compares
   the two files.** Measured on the four published `antonkulaga/*` modules (2026-08-20): every
   `literature.csv` row carries `quotes_authored=0`, an empty `quotes_found` and an empty
   `quote_source`, while their `studies.csv` files carry a `provenance_quote` on **3668 of 3668**
   rows. The mechanism is gotcha 1 doing its job — the literature pass ran while the column was
   still empty, wrote what was true then, and merge-not-clobber means no later run revisits it.

   Three things follow, and the third is the one that bites:

   - **The published manifest reports a confident zero.** `_literature_block` guards the per-row
     null correctly, but summing over rows that are *all* null gives `0`, and
     `manifest.literature.quotes_found` is `int` with `default=0` and has no `quotes_unchecked`
     beside it. So the manifest says `quotes_authored: 0, quotes_found: 0` for a module with 859
     authored quotes. Filed as upstream `S56`.
   - **These counters are therefore not a detector** for a module whose quotes are worthless — see
     `studies.md` gotcha 1 on the title case. Group `studies.csv` by `pmid` and count *distinct*
     quotes instead; that reads the authored file directly and needs no pass.
   - **Correcting it needs the pass, which is extended-tier.** `enrich_literature_pass` and
     `refresh_sidecar` are both `JMC_MODE=extended`, so on a default install there is no way to
     bring the counters up to date at all. The CLI is `just-dna-enricher literature <dir>`, and
     using it is stepping outside this plugin's surface.
8. **`--offline` is a no-op that keeps the pin, and it may still write the file.** It fetches nothing,
   re-examines nothing, warns, and rewrites the existing rows sorted by PMID (`enricher/literature.py:784-801`).
   If a pinned row covers every current citation it records **no verification record at all** —
   deliberately: "a record of having said nothing is worse than silence" (`enricher/literature.py:1188-1192`).
9. **Quoting a non-commercial article warns and never gates.** `_check_quoted_article_licenses`
   (`compiler.py:5607`) is keyed on the **quote**, not the citation: naming a PMID costs nothing under
   any licence, while a `provenance_quote` copies publisher text into `studies.csv`, which is authored
   content the module ships — and `studies.csv` sits in the *annotation* layer, where the licence gate
   bites. Aggregated by licence string, one line each. Refusing "would make the format arbitrate a
   copyright question".
10. **`pmid` here is digits only; the free-form form lives in `studies.csv`.** The validator refuses
   anything else and names `spec.extract_pmids` (`format/literature.py:216-224`). And PMC ids are one letter
   away from a real PMID: `PMC 3110566` used to extract as PMID **3110566**, a real record for an
   unrelated article (RM50). `_pmcid_conflicts` catches the spelling the schema cannot refuse —
   `21551363 (PMC3110567)` carries a valid PMID while the two halves name different papers.
11. **Existence is not identity (S12).** PMIDs are densely allocated, so a recalled eight-digit number
   is usually a real record for a *different* article — `exists=True` can never catch a fabricated
   citation. Read the **title** from `lookup_citation` / `literature_search` before writing a PMID; it
   comes from `literature.bibliographic(summary)`, the same `esummary` response, at no extra request.
12. **`regex` matching runs under a wall-clock bound in a child process, and a timeout is recorded as
    NOT CHECKED** — never as not-found (`enricher/literature.py:630`, `DEFAULT_REGEX_TIMEOUT = 5.0` at `:99`).

## What does not exist

- **No `dataset` column**, unlike every other fact table. PubMed and Europe PMC are continuously
  updated and publish no release identifier, so the column "could only ever be null or a fabricated
  label". `fetched_at` is this table's currency marker (`format/literature.py:22-27`).
- **No `title` / `journal` / `year` / `first_author` column.** *"That table records what was
  **checked**, not bibliography"* (`docs/ENRICHER.md:1795`). The bibliographic fields ride on
  `lookup.CitationHint` instead, from the same `esummary` payload. A consumer wanting a rendered
  reference list has to fetch them — see *Blanks*.
- **No `pubmed` row in the licence table, ever.** Refused with a reason, so do not re-propose it: "a
  literature source's terms are per article, not per source", and one `pubmed` row would be right for
  a module citing only ids and "a false all-clear for one carrying a `provenance_quote` lifted from a
  CC-BY-NC article — wrong in the dangerous direction" (`enricher/licensing.py:277-289`).
- **No PMC ID converter call in this pass, and that is not an oversight.** `esummary` already returns
  `doi` and `pmc`; worse, the converter answers a *different* question — for PMID 12345678 it replies
  `"Identifier not found in PMC"`, so wiring it in as an existence check "would report every paywalled
  article as a broken citation" (`enricher/literature.py:35-42`). The PMCID→PMID direction *is* wired, in
  `lookup_citation(pmcid=…)`, reporting only.
- **No Europe PMC existence oracle.** Asked about three ids where one does not exist it returns two
  and omits the third, with no marker. PubMed decides existence; Europe PMC decides retrievability.
- **No Google Scholar route.** No API, and automated querying violates its terms.
- **No offline snapshot, and there will not be one.** Once written, `literature.csv` *is* the pin.
- **No `--refresh`.** The only way to re-ask is `rm literature.csv`, which also discards curator
  overrides — upstream **RM83**, still open.
- **No `describe_table` / `table_requirements` / `get_template` support.** All three route through
  `known_kind(csv_name, draft.DRAFTABLE)` (`src/just_module_creator/tools/_shared.py:142-151`) and
  `literature.csv` is not draftable, so they raise *"Unknown table kind"*.

## Consumption today

**Nothing outside `just-dna-format` reads a single column of this table.** Swept across
`just-dna-lite` (incl. `just-dna-pipelines`), `just-dna-registry`, `just-dna-marketplace`, `just-prs`,
`just-prs-mcp` and this repo. In all six it is only written, hashed, uploaded or listed by name.

- **Written, result consumed in-process, file never reopened**:
  `just-dna-lite/just-dna-pipelines/src/just_dna_pipelines/v1_port/runner.py:171-180` (deletes
  `literature.csv`, re-runs the pass, keeps `len(rows)` and two warning strings);
  `just-dna-registry/src/just_dna_registry/services/enrich.py:1100-1131` (runs it with `write=False`
  and maps the *return object* to `LiteratureCheck`, explicitly "never a publish gate");
  `src/just_module_creator/tools/passes.py:620-668` (same shape).
- **Opaque bytes**: `just-dna-lite/webui/src/webui/state.py:6007` imports `ARTIFACT_PARQUETS` and
  hashes the file into the Merkle digest — the one place in lite the name appears;
  `just-dna-pipelines/src/just_dna_pipelines/v1_port/publish.py:20,100` existence-checks it and
  uploads it to HuggingFace unopened.
- **Name in a list**: `just-dna-registry/src/just_dna_registry/specfiles.py:100` (`FACT_CSVS`, carried
  forward as bytes); `services/upgrade.py:43,167` (header vs `LiteratureRow.model_fields`, no cell
  inspected); `src/just_module_creator/tools/authoring.py:154,660` (a string in `TableList.sidecars`).
- **How lite actually renders a citation**: one HTML template,
  `just-dna-pipelines/src/just_dna_pipelines/annotation/templates/longevity_report.html.j2:676-690`,
  fed by `annotation/report_logic.py:850-856`, which projects exactly five columns from
  **`studies.parquet`** — `pmid`, `population`, `p_value`, `conclusion`, `study_design` — and builds
  `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` from the bare id. The same PMIDs go into the AI-explain
  prompt at `report_logic.py:636-644`.
- **Licence columns are read — from the wrong table.** `report_logic.py:1092-1132` scans
  `sources.parquet`, filters `layer == "annotation"`, and the template renders the three rights
  tri-state ("Share-alike required" / "Non-commercial use only" / "Redistribution restricted" /
  "*Not stated*") at `longevity_report.html.j2:963-966`. `LiteratureRow.license` and its three rights
  have **zero** read sites.
- **The registry facets on five fact-table flags and literature is not one**:
  `db/schema.py:283-293` `_V017_COLUMNS` has `has_gene_validity`, `has_clinical_assertions`,
  `has_gwas_effects`, `has_frequencies`, `weighting_declared` — **no `has_literature`**. `models/api.py:222-235`
  `FactTablesInfo` matches. `manifest.literature` rides along inside `manifest_json` and nothing reads it.
- **`literature_signature` / `LITERATURE_FACT_FIELDS`: zero hits in all six repos.** So the canary this
  table is part of is, today, unperformed by any consumer.
- **`just-prs` / `just-prs-mcp`: plain negative** on every token. Their `pmid`/`doi` hits are a PGS
  Catalog `Publication` model, unrelated.

## Blanks for just-dna-lite

- **Render a real reference list, not a bare id.** The report prints `pmid` and links PubMed. A join to
  `literature.parquet` on `pmid` would add DOI and PMC links and an open-access badge for free
  (`doi`, `pmcid`, `is_open_access`) — no network, already in the artifact. What breaks today: a
  reader gets a naked eight-digit number with no way to tell a paywalled citation from a readable one.
  **Caveat: there is no `title`/`journal`/`year` in this table by design**, so a *bibliographic*
  reference list still needs `lookup_citation`; ask for the identifiers, not the citation string.
- **Surface a broken citation.** `exists is False` is a pinned fact meaning PubMed has no record — a
  defect in the module, not a coverage gap. Nothing in lite or the registry shows it; the compiler
  warns and the warning dies in a log. Ask: a per-module "N citations do not resolve" badge read off
  `manifest.literature.missing_count` (already in `manifest_json`), and a footnote on the offending
  study row in the report.
- **Show the evidence-grounding level honestly.** `quotes_authored` / `quotes_found` /
  `abstract_only_count` / `open_access_count` are all in `manifest.literature` and unread. A module
  where a curator located every quote in a fulltext is materially better evidence than one where none
  was retrievable — that is precisely the curation signal the catalog wants to cherry-pick on, and
  today it is invisible. **Render the three-valued split, never a percentage**: `quotes_found` null vs
  `0`, and an abstract miss, must not collapse into "unverified".
- **Facet the catalog on `has_literature` and on `missing_count > 0`.** Four fact tables already have a
  `has_*` column in `_V017_COLUMNS`; literature is the odd one out. A search filter for "citations
  checked" costs one integer column.
- **Read the per-article licence before quoting.** If a consumer ever renders a `provenance_quote`,
  `commercial_use is False` on the matching literature row is the flag that says the passage is
  publisher text under a no-sale licence. Lite renders the *source*-level rights from `sources.parquet`
  and would show a permissive verdict beside a CC-BY-NC quotation.

## Ask the live schema

`literature.csv` is **not** an authorable kind, so the usual three tools refuse it. Use these instead.

```python
# The current columns, types, descriptions and defaults — the only source of truth.
from just_dna_format.literature import LiteratureRow, LITERATURE_FACT_FIELDS
list(LiteratureRow.model_fields)              # column order the pass writes
LiteratureRow.model_json_schema()             # types, descriptions, vocabularies
LITERATURE_FACT_FIELDS                        # what the fact signature covers

# The vocabularies, by name, never quoted from memory.
from just_dna_format import vocab
vocab.VALID_QUOTE_SOURCE, vocab.VALID_RESOLUTION_STATUS, vocab.VALID_SOURCE_LAYERS
vocab.VALID_VERIFICATION_CHECKS               # citation_existence / citation_identifier / provenance_quote

# The licence mapping and the refusal maps.
from just_dna_enricher.licensing import ARTICLE_TERMS_BY_LICENSE, article_terms, TERMS_BY_SOURCE
from just_dna_compiler.hints import REDUNDANCY_BEARING, ATTESTATION_BEARING
```

Through the MCP surface, the **authored** side is what you can ask about:

- `describe_table("studies.csv")` — the table this one checks; its `redundancy_bearing` and
  `attestation_bearing` maps name `doi`, `pmid`, `provenance_quote`, `provenance_regex`.
- `table_requirements("studies.csv")` — read all three shapes of requiredness.
- `lookup_citation(pmid=…)` / `literature_search(...)` — **read the title** before writing a PMID.
- `enrich_literature_pass(spec_dir, strict=…, check_fulltext=…, check_doi=…)` — the pass that writes
  this file (extended tier; `just-dna-enricher literature <dir>` is the CLI equivalent).
- `validate_module` / `compile_module` — where the orphan, nonexistent-citation and non-commercial-quote
  warnings surface.

**Stamped: format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, verified by
`importlib.metadata.version` on 2026-08-19.** Every quoted value above is illustrative; re-read the
model.
