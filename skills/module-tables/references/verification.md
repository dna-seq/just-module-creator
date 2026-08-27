# `verification.json` — the attestation that says whether anything was ever *checked*, and the closure that says authoring ended

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

Every other file in a module states a **claim**. This one states whether the claims were ever **put
to a source**, and separately whether a human declared the authored set **finished**. Before 0.6 a
module whose `clin_sig` calls had been cross-checked against ClinVar and one where that check never
ran shipped byte-identical manifests — "not through an oversight in some path, but because no field
existed that could differ" (`schema/src/just_dna_format/manifest.py:890-892`). `verification.json` is
that field. Its audience is a **downloader**: a consumer holding a manifest wants to know whether
`clinical_significance` was compared, over how many rows, against which ClinVar release, or why it
could not be. Its second audience is the author's own future self — the closure is the only artefact
in the format that distinguishes *a spec still being edited* from *one its author considers done*.

It is **not a table**. There is no CSV, no parquet, no `describe_table` entry, and it is not in
`draft.DRAFTABLE`. Where this dossier's siblings say "column", read "field of `VerificationRecord`".

## Identity card

| | |
|---|---|
| Models | `just_dna_format.manifest.VerificationDoc` (`manifest.py:1002`), `VerificationRecord` (`:887`), `Closure` (`:843`), and the manifest projection `Verification` (`:1088`). All `extra="forbid"` |
| Behaviour | `just_dna_format.verification` — binding, proof-of-work, merge, closure (`schema/src/just_dna_format/verification.py`) |
| On-disk name | `layout.VERIFICATION_JSON = "verification.json"` (`layout.py:47`). Spec root **or** `derived/` (`layout.DERIVED_SUBDIR`, `:79`); both present is a `SidecarCollision` |
| Parquet | **none, and it never gets one.** Not in `compiler.ARTIFACT_PARQUETS` (`compiler.py:278`). It is an attestation *over* the tables, not a table |
| Natural / dedup key | `record.check` — **at most one record per check name**. The merge enforces it (`verification.py:338-349`) |
| Authored or machine-produced | machine-produced, and the one derived artefact that is **not** human-overridable by design (gotcha 3) |
| Who writes it | the enricher's `record_verification` (`enricher/.../verification.py:82`) and `just-dna-compiler close` → `compiler.close_module` (`compiler.py:4600`). Nothing else |
| Fact signature | `verification.verification_signature` over `VERIFICATION_FACT_FIELDS = (check, subjects, findings, skipped, source, release)` (`verification.py:67`), published as `manifest.verification.signature` |
| In `content_signature`? | **no** — not in `compiler._INPUT_FILES` (`compiler.py:267`) |
| In `artifact.digest`? | **no** — no parquet, and the file is not copied into the compiled output dir at all (measured: `ls` of a compiled `mt_common_deletion` output holds seven entries, none of them this) |
| Elsewhere in the manifest | byte-hashed into `manifest.derived` via `compiler._DERIVED_FILES` (`compiler.py:354`), and summarized into `manifest.verification` |
| Binding | `verification.module_binding(compiler.authored_input_entries(spec_dir))` (`compiler.py:361`) — the **authored** files only, `\r\n` read as `\n` since RM82 |

## Who populates what

There is no author column here. Use these words:

- **enricher pass — seven commands, fifteen of the seventeen check members.** Verified by AST walk
  over the **installed** `just_dna_enricher 0.6.4`, not from a docstring:

  | command | members it can emit |
  |---|---|
  | `just-dna-enricher enrich` (jmc `enrich_module`) | `reference_allele`, `rsid_currency`, `clinical_significance`, `genome_build_agreement`, `rsid_coordinate_agreement` |
  | `literature` (jmc `enrich_literature_pass`) | `citation_existence`, `citation_identifier`, `provenance_quote` |
  | `check-identifiers` | `gene_symbol_currency`, `trait_currency`, `gene_locus_agreement` |
  | `check-acmg` | `acmg_secondary_findings` |
  | `pgx` | `allele_function` |
  | `clinpgx check` | `pgx_evidence_level` |
  | `vrs mint` | `vrs_allele_id` — **skip only**, see gotcha 6 |

- **compiler-stamped — the closure, and only the closure.** `close_module` writes `closed_at`,
  `closed_by?`, `signature?`. It writes no record and never invents one; on a document whose binding
  no longer holds it emits `attest([], binding, closure=…)` with `producer` and `produced_at` both
  left `null` deliberately, "as a pair: they describe the run that put the checks, and this document
  has none" (`compiler.py:4688-4692`).

  > 🚧 **ROADWORKS — closing a module can throw away its check records, and only the CLI says so.**
  > **Current state.** When a check record was attested over bytes that no longer match, `close_module`
  > **drops** it and names it in `CloseResult.dropped_checks`. That is correct behaviour — carrying it
  > across would re-bind a claim to different bytes — but it is reported as a *field on the result*.
  > The Typer CLI prints one line for it (`cli.py`, *"dropped N check record(s) attested over
  > different bytes"*); a **library** caller that ignores the field is told nothing, it is not a
  > compile warning, and nothing about the loss reaches `manifest.verification`. This has already
  > happened in the format repo's own history, and 15 of its 16 reference examples now record **zero**
  > checks.
  > **Expected state.** At minimum a warning on the compile surface, so the loss is visible to
  > whoever reads the manifest rather than to whoever read stdout. There is none.
  > **Guard.** Call `close` through the CLI, or read `dropped_checks` explicitly and fail your own
  > pipeline on a non-empty list. Re-run the checks **after** closing, never before — and treat an
  > empty `verification.json` on a closed module as "the records were dropped" until you have proven
  > otherwise.
- **registry-stamped — a real category here, and it is new.** The registry's publish path runs
  enrichment itself and **its record displaces whatever arrived under the same check name**; a check
  it does not run is carried verbatim. Pinned as
  `just-dna-registry/tests/test_specfiles.py::test_a_publisher_cannot_forge_a_check_this_server_runs`
  (`:208`).
- **nobody, ever — `release` on a continuously-updated source.** `PubMed` "has nothing true to put
  here", so the field stays `null` and must not be read as unknown-provenance
  (`manifest.py:946-952`).
- **author (hand) — forbidden in practice.** Editing any field inside `records[]` that is in the fact
  set invalidates `signature` and the compiler drops the whole document. Editing a field *outside* the
  fact set is undetected — that is gotcha 3.

**Which cells no tool may fill even though it easily could.** `hints.REDUNDANCY_BEARING` and
`hints.ATTESTATION_BEARING` name columns in the *authored* tables, not fields here, and this file is
the reason those maps exist: the checks recorded here are exactly the comparisons that a filled-from-
source cell would make vacuous. The rule turned inside out for this file is stronger — **no tool may
fabricate a record at all.** `attest()` takes the records it is handed; `record_verification` returns
`None` on an empty list rather than writing a document, because "writing an empty attestation would
create a file asserting that a module was checked and nothing was found"
(`enricher/.../verification.py:91-93`). And every field of `manifest.Verification` carries
`UNTRUSTED_NOTE`, because "a forged pass is worse than silence" (`manifest.py:1102-1103`).

## What moving this table moves

Measured on `reference_examples/mt_common_deletion` — the **one** reference example that still carries
check records (4 of them) — compiled with `compile_module(resolve_with_ensembl=True,
ensembl_cache=None, strict=False)` under installed format/compiler **0.6.1**, enricher 0.6.4.
Baseline: `digest 98eb773eef`, `content 4b75315cb4`, `manifest.derived[verification.json] b1c68395f6`,
`manifest.verification.signature ab5d05702f`, 4 checks, closed.

| An edit | `content_signature` | `manifest.verification.signature` | `artifact.digest` | `manifest.derived[]` | the attestation + closure |
|---|---|---|---|---|---|
| reword a record's `detail` | same | same `ab5d05702f` | same | moved `cf0091accf` | **kept**, 4 checks |
| rewrite a record's `checked_at` | same | same | same | moved `af768e9ea0` | **kept**, 4 checks |
| reorder the `records[]` array | same | same | same | moved `9f04c4da58` | **kept**, 4 checks |
| edit a **fact** field (`subjects` 2→999) | same | — | same | moved `58dc94df18` | **DROPPED** — *"the recorded check signature … is not the hash of the records beside it"* |
| hand-add a record | same | — | same | moved `b822ffa56f` | **DROPPED**, same reason |
| rewrite `closure.closed_by` | same | same | same | moved `ebbe8b8a7d` | **kept and published**, unchallenged |
| rewrite `closure.closed_at` | same | same | same | moved `b35b2da6d6` | **kept and published**, unchallenged |
| claim `difficulty: 8` | same | — | same | moved | **DROPPED** — *"claims 8 bits and this reader requires 20"* |
| set `nonce: 1` | same | — | same | moved | **DROPPED** — *"assembled by hand rather than by a run of the checks"* |
| corrupt a **present** closure signature | same | — | same | moved | **DROPPED** — *"the closure is signed and the signature does not verify"* |
| delete the file | same | — | same | entry gone | absent; compile warns *"This module records no closure"* |
| edit an authored cell (`variants.csv` coordinate) | **moved** `4df131aea1` | — | **moved** `5f6cbce35e` | same | **DROPPED** — *"computed over different module bytes"* |
| **reorder rows in `variants.csv`** | **same** | — | moved `2ded5011c4` | same | **DROPPED** |
| **delete the final newline of `variants.csv`** | **same** | — | **same** `98eb773eef` | same | **DROPPED** |
| CRLF `variants.csv` | same | same | same | same (`manifest.inputs[variants.csv]` moves `251d…`→`1c33…`) | **kept** — RM82 working |
| **append an `authorship:` entry** | **same** | — | **same** | same (`inputs[module_spec.yaml]` moves) | **DROPPED** |
| edit `README.md` | same | same | same | same | **kept** |
| edit a derived sidecar (`resolution.csv`) | same | same | same | same | **kept** |
| `reverse_module` → recompile | same | — | fixed point | no entry | reversed spec carries **no** `verification.json`; recompile is **open** and warns |

Four answers:

1. **Inside `content_signature`? No, and it must never be.** It is derived and it is hashed by its own
   fact set, `VERIFICATION_FACT_FIELDS` (`verification.py:67`). Left out: **`detail`**, because "prose
   — rewording a sentence must not move a signature", and **`checked_at`**, "for the reason
   `fetched_at` is out everywhere: when a pass ran is a fact about the run, not about the module"
   (`verification.py:63-66`). The registry pins the same property from its side: `VERIFICATION_FILE`
   is out of `SIGNATURE_INPUTS` (`just-dna-registry/src/just_dna_registry/specfiles.py:133`,
   `:280`), so "a module's identity must not depend on whether its author happened to ship one".
2. **Inside `artifact.digest`? No.** It has no parquet and is not copied into the output directory,
   so unlike every fact sidecar a byte-level edit here moves the digest by exactly nothing. Rows 1–3
   and 6–7 of the table above move `manifest.derived` only. `resolution.csv` is the *other* sidecar
   with no parquet; measured, neither is copied into the compiled output dir, so what travels with an
   artifact is the `manifest.verification` summary and not the document.
3. **Does an edit here un-close the module? No — this file is outside its own binding.** The binding
   is over `_INPUT_FILES` only. So the honest statement is the inverse: **this file is the thing that
   gets un-closed**, by an edit somewhere else. And the reach is wider than intuition: a pure row
   reorder and a deleted final newline both dropped the block above while moving `content_signature`
   by nothing (the newline case moved `artifact.digest` by nothing either — *zero* identity movement,
   module un-closed). An `authorship:` append does the same and is the documented case
   (`docs/MODULE_LIFECYCLE.md:350-372`; `docs/FAQ.md:274-281`).
4. **Part of the canary? No, and it is the wrong instrument for it.** MODULE_LIFECYCLE § 5.1's canary
   is *content unmoved + a derived **fact** signature moved = the upstream source said something
   different this time*. `verification.signature` does move when a source changes its answer — a
   `findings` count going 0→1 moves it — but it moves on a re-run for a dozen innocent reasons too
   (a skip reason changing, a `release` string advancing), and unlike `resolution.csv` there is no
   merge-not-clobber problem to defeat: `merge_records` is *newest wins per check*, so a re-run **does**
   re-ask. What it cannot do is distinguish "the source revised its answer" from "we ran with
   different flags this time". Read source currency off each record's own `release` field, never off
   the binding and never off this signature (`verification.py:20-24`).

## Required to exist

**Never.** There is no module shape that requires a `verification.json`, and its absence is silent at
the record level: "no `verification.json` → `(None, [])`. Nothing was attested and nothing is said,
silently: an unverified module is the ordinary case and warning about it would fire on every module in
this repository" (`compiler.py:5010-5013`).

What it *drags in*: nothing. What drags **it** in: any of the seven attesting commands, which create
or merge unconditionally and with no flag (RM72 removed the `--attest` idea explicitly — "an optional
record is ambiguous between *not run* and *ran without the flag*", `docs/RM_TOC.md:273`); and `close`,
which creates it if absent with an empty `records[]`.

The **closure** half is different: its absence **warns**, in both modes, in `validate` and `compile`
alike — *"This module records no closure: nothing in it states that authoring is finished, so a
consumer cannot tell a spec still being edited from one its author considers done."* Requiring it is
filed for 1.0 and is **blocked** there, because `reverse` cannot re-emit the document, so under a gate
`compile → reverse → compile` would refuse on step 3 (`docs/SCHEMAS.md:1450-1454`).

## The fields that carry judgement

- **`check`** — closed vocabulary, `vocab.VALID_VERIFICATION_CHECKS` (`vocab.py:687`), 17 members as
  of format 0.6.1. Closed because "free-string check names would recreate RM44 one level down — one
  spelling from the enricher, another from a registry, a substring match from a consumer".
- **`subjects` / `findings`** — **two counts, never a boolean, never one union-typed slot.** `subjects`
  is the denominator. `subjects=0` with `skipped=null` means *the check ran and had nothing in scope*.
  That is not the same statement as `skipped` being set, and they can never occupy one value
  (`manifest.py:894-899`).
- **`skipped`** — closed vocabulary, `vocab.VALID_VERIFICATION_SKIPS` (`vocab.py:735`), 8 members.
  Closed for a second reason beyond spelling: "backfill triage branches on *why*, so prose here would
  relocate the substring matching rather than end it". `not_requested` (a caller's choice) and
  `offline` (a capability the run lacked) "are different facts about the same absence and must not be
  merged: … only the second is cleared by re-running with egress" (`vocab.py:725-728`).
- **`detail`** — the human sentence, **beside** the machine key, never instead of it. Outside the fact
  set, so rewording moves no signature. Capped by aggregation: `verification.DETAIL_LIMIT = 5`
  examples plus a count, so "a module whose whole panel disagreed would otherwise put one sentence per
  row into `manifest.verification`" (`enricher/.../verification.py:56-60`).
- **`release`** — the one field that answers *how current is this check*. `null` where the source
  publishes none. The binding deliberately does **not** answer this: re-running against a fresher
  ClinVar leaves the attestation matching, so a consumer reads currency here or nowhere
  (`verification.py:21-24`).
- **`closure.closed_by`** — free text, untrusted, and unchecked by anything (measured above). "Who
  they say they are, not who they are" (`just-dna-registry/src/just_dna_registry/models/api.py:213`).
- **`closure.signature`** — optional Ed25519 over the `module_hash` string. **Absence merely warns; a
  present one that fails to verify drops the whole document.** Absence is a limit, a claim is a claim
  (`verification.py:267-278`).

## Gotchas

Ordered by how likely a first-timer is to hit them.

1. **A closed module is not a checked module, and the corpus proves it.** Measured across all 16
   reference examples on 2026-08-19: **16 of 16 carry a closure, 15 of 16 record zero checks.**
   Fifteen of them carry the identical `signature`
   `sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` — which is
   `verification_signature([])`, i.e. `sha256("[]")`. That string is a machine-readable marker for
   *closed and attesting nothing*; if you read it off a manifest, the module records no check at all.
   How they got there is gotcha 2.
2. **`close` silently destroys check records, returns `closed: true`, and warns about nothing.**
   `close_module` keeps an existing document verbatim only while `attestation_failure(previous,
   binding) is None`; otherwise it drops every record and names them in `ClosureResult.dropped_checks`
   — which is a *field*, not a warning (`compiler.py:4683-4695`). Measured: edit one coordinate in
   `mt_common_deletion/variants.csv`, then `close_module(...)` → `closed: True`,
   `dropped_checks: ['clinical_significance','genome_build_agreement','reference_allele','rsid_currency']`,
   `warnings: []`, and the next compile publishes `verification: {closed: true, checks: []}` **with no
   warning at all**. This is exactly what happened to the corpus: `git log -p` on
   `reference_examples/hboc_palb2/verification.json` shows commit `5db616a` *"Re-close the sixteen
   reference examples against the normalized binding"* replacing four real records with `[]`, because
   RM82's own binding change moved every `module_hash`. **Read `dropped_checks` after every close, and
   re-run the checks after closing, not before.**
3. **Everything outside the fact set is hand-editable and nothing challenges it.** `detail`,
   `checked_at`, `closed_by` and `closed_at` are outside both `VERIFICATION_FACT_FIELDS` and
   `pow_digest`'s payload (`module_hash|signature|nonce`, `verification.py:122`). Measured: rewriting
   `closed_by` to *"somebody else entirely"* and `closed_at` to `2099-12-31` both published unchallenged.
   The registry says so plainly — `closed` is "the one field here with a check behind it"
   (`models/api.py:206-210`). Do not read `closed_by` as attribution unless `signature` is present
   **and** you pin the key: the signature block carries its own `public_key`, so verifying it proves
   only that *the holder of that key* signed, never *whose* key it is.
4. **A `--offline` re-run used to overwrite a real answer with "never asked" — RM72 fixed it, and the
   fix has a condition.** `merge_records` refuses to let a fresh `skipped` displace an existing `ran`
   (`verification.py:299-349`). Measured directly:
   `merge_records([ran(clinical_significance, subjects=13)], [skipped(clinical_significance, "offline")],
   existing_still_binds=True)` → keeps `subjects=13`; with `existing_still_binds=False` → `skipped=offline`.
   The condition is not a knob: once the authored bytes have moved, the old answer "describes rows that
   no longer exist". Newest-wins still holds `ran`→`ran` (measured: 13→99) and `skip`→`skip`.
5. **The corpus's own README is stale about which checks exist, and it is the most-cited source.**
   `reference_examples/hboc_palb2/README.md:37-56` says *"five of seven checking passes attest
   nothing"* and *"of `VALID_VERIFICATION_CHECKS`' seventeen members, five can ever be emitted"*, with
   a twelve-name "never emitted by anything" table. That was true on 2026-08-14 and was **fixed by
   RM72, shipped in 0.6 PT2 on 2026-08-17** (`docs/RM_TOC.md:273`). Verified against the *installed*
   enricher 0.6.4 by AST walk: **15 of the 17 members have live emitters**; only
   `gene_disease_validity` and `dosage_sensitivity` do not. The README was never corrected. Treat it
   as a historical probe record, not as current behaviour.
6. **`vrs_allele_id` is wired to a command that can only ever emit a skip.** `_mint_record`
   (`enricher/.../cli.py:1694`) returns `skipped("vrs_allele_id", "nothing_to_check")`
   unconditionally — there is no `ran` path. The reasoning is exactly right and worth reading: the
   member names a *cross-check* of a source's own `ga4gh:VA.…` against the re-minted one, and
   `resolution.csv` "records the ids the tier minted and never where an id came from, so the question
   was not put. That is a skip, not a clean pass." The coverage counts travel in `detail`;
   `manifest.compilation.vrs_alleles` / `vrs_alleles_identified` is where a consumer reads them.
7. **`gene_disease_validity` and `dosage_sensitivity` are reserved with no emitter, deliberately.**
   `enrich_gene_validity` and `enrich_dosage_sensitivity` *record* ClinGen/GenCC verdicts into
   `gene_validity.csv` / `gene_metrics.csv` and compare **nothing authored** — no model carries an
   authored gene–disease or dosage claim to compare against. Emitting a member for them "would let a
   manifest report a check where no question was put". The names exist ahead of the emitters on
   purpose: "adding one later is legal; adding the *name* late would leave the release that needs it
   with nothing to write (the `withdrawn` precedent)" (`vocab.py:706-715`).
8. **A module authored entirely through this plugin attests 8 of the 15 reachable members.**
   `enrich_module` calls `just_dna_enricher.enrich.enrich` (5 records) and `enrich_literature_pass`
   calls `enrich_literature`, which attests internally via `literature._attest` (3 records). The
   plugin's `check_identifiers` calls the *function*, and the write lives in the **CLI command** —
   `src/just_module_creator/tools/research.py:20-31` says so, and it is tracked as `RM9` in
   `docs/ROADMAP.md:38`. Missing from a plugin-only module: `gene_symbol_currency`, `trait_currency`,
   `gene_locus_agreement`, `acmg_secondary_findings`, `allele_function`, `pgx_evidence_level`,
   `vrs_allele_id`. Say so rather than implying the checks left a trace.
9. **`reverse` is not a recovery path for this file.** A reversed spec carries no `verification.json`
   at all — measured: `(rev/"verification.json").exists() == False` — and the recompile is **open**.
   The compiler warns first, at length: *"the checks were put by the enricher, against sources this
   tier does not reach … re-run the enricher … and close it yourself — reverse holds no authority to
   declare someone else's authoring finished"* (`compiler.py:6023-6048`).
10. **Both spellings present is a *warning* here, where it is an error on a fact table.**
    `_read_verification_block` returns the collision as a warning "because the outcome is already the
    weaker one: two attestations are two claims, neither may be preferred, so nothing is published"
    (`compiler.py:5031-5034`). A module with `verification.json` in both the root and `derived/`
    publishes no block and compiles green.
11. **The proof-of-work is real but small, and it is honest about that.** Measured on this
    interpreter: 5 runs of `find_nonce` at 20 bits took 0.22–1.46 s, median **0.65 s**, matching the
    documented ~0.7 s. It is one per document per run, never per record. It defeats *accidental*
    forgery — an attestation left behind after an edit, or copied from another module — and "nothing
    here is built to resist a deliberate one" (`docs/SCHEMAS.md:1462-1466`). The real guarantee is
    `manifest.signature`, a detached Ed25519 signature over `artifact.digest` by a party the client
    pins.
12. **Era gap: no real-world submission carries one.** Checked all 27 bundles in
    `/data/sources/just-dna-registry/data/input/`: **0 of 27** contain a `verification.json`. That is
    an era gap, not a defect — the whole submitted corpus predates 0.6. The two 0.6-era `v1_port`
    modules in `just-dna-lite/data/interim/v1_port/` *do* carry a manifest block, written by enricher
    0.6.4 on 2026-08-19, and they are the largest real attestations in the workspace:
    `pathogenic` records `clinical_significance subjects=618629 findings=32`, `cancer` records
    `141616 / 20`, and **both have `closure: null`** — attested but never closed, the legitimate
    "either alone" state (`SCHEMAS.md:1423-1425`).

## What does not exist

- **No CSV, no parquet, no `describe_table` entry.** `describe_table` and `table_requirements` gate on
  `draft.DRAFTABLE` (`src/just_module_creator/tools/authoring.py:180`, `:222`) and
  `verification.json` is not in it, so both refuse. A JSON document rather than a fifth fact CSV,
  structurally: "the object has two levels — one attestation over many records — and a CSV expresses
  that only with a non-data service row (the shape RM36 rejected) or by repeating the attestation on
  every row, where two rows can then disagree about a per-run fact" (`manifest.py:1005-1011`). And
  because it must stay out of the family whose human-overridability is a *designed feature*.
- **No `reopen` command, and none is needed.** "Editing an authored file is what re-opens a module"
  (`docs/MODULE_LIFECYCLE.md:490-491`).
- **No stamping on a clean `validate`, and this was asked and refused.** `docs/FAQ.md:153-155`:
  *"Why can't `validate` stamp the closure when everything passes?"* — because "a record stamped by
  whatever happened to execute says only *someone ran a tool*", the exact defect RM73 exists to fix.
  `validate` stays read-only however cleanly it passes.
- **No fatal on a stale attestation.** Considered and rejected: "the goal is that a stale record never
  becomes a *published claim*, not that it be impossible to write, and dropping the block achieves
  that without stopping an author mid-edit" (`compiler.py:5019-5023`).
- **No content-aware binding.** RM82 normalizes `\r\n`→`\n` and **stops there**. A BOM, trailing
  whitespace and a missing final newline remain edits, "because those are things a human typed rather
  than things a tool did on their behalf" (`integrity.py:116-122`). A lone `\r` is left alone. Measured
  above: deleting the final newline of `variants.csv` un-closes the module while moving neither
  identity.
- **No run-level record.** The counter-argument to RM72's skip protection — that a reader may want to
  know *today's* run could not reach the source — is answered rather than dismissed: "That is a fact
  about the **run**, not about the **check**, and this is a per-check document … deliberately not
  opened here" (`verification.py:333-336`).
- **No `--attest` flag** (RM72 wired the four blocked members unconditionally), **no accumulation**
  (`merge_records` replaces per check — "two answers to that are not two facts"), and **no signing
  from this plugin**: `close_module` takes `closed_by` only, and `--private-key` is the CLI's
  ([`module-close`](../../module-close/GUIDE.md)).

## Consumption today

**The consumer picture changed in the last three days and the format tree's own docs have not caught
up. Verify before you repeat either version.**

- **`just-dna-registry` — reads it, since 0.16, and *surfaces* it since 0.17.** Installed and checked
  out at **0.18.2** (2026-08-19).
  - `specfiles.py:133` — in `RECOGNIZED_SPEC_FILES`, so `revalidate`/`upgrade` rebuild a spec dir
    *with* it (their S11); `:234` — in `DERIVED_FILES`, so `download(layout="split")` puts it in
    `derived/` (`client.py:125`); `:280` — out of `SIGNATURE_INPUTS`, so shipping one cannot move a
    module's identity or its `409 duplicate_content` claim.
  - `services/catalog.py:178`, wired at `:359` — projects `manifest.verification` onto
    `ModuleDetail.verification` as `VerificationInfo` (`models/api.py:179`, field at `:307`).
    `None` and an empty block are **not** collapsed: "absent means no attestation survived into the
    manifest, which is a different statement from an attestation that recorded no checks."
  - **The publish path attests its own checks and displaces the publisher's.** Pinned by
    `tests/test_specfiles.py:208`: an upload claiming `clinical_significance subjects=999` publishes
    as the server's own record; `acmg_secondary_findings`, which that deployment does not run,
    survives verbatim at 999; and the forged closure is dropped (`verification.closure is None`)
    because it is hash-bound.
  - **Deliberately not a card facet and not a filter** (`models/api.py:201-203`, asserted at
    `tests/test_format_06.py:234`): "a registry that let you sort by someone else's unverifiable pass
    would be lending it our credibility."
  - Registry changelog: *"All 16 upstream reference examples publish through this registry under 0.6 …
    Every one of the 16 comes back with an attested readme, a verification block, a surviving closure"*
    (`just-dna-registry/docs/CHANGELOG.md:546`).
- **`just-dna-lite` / `just-dna-pipelines` — reads nothing.** Grepped the whole tree: the only hits
  are the word "verification" in unrelated prose and two `data/interim/v1_port/*/manifest.json`
  fixtures that *carry* a block nothing opens. The annotation half reads
  `manifest.artifact.files` (`hf_modules.py:153`), `manifest.identity.version` (`:695`) and
  `manifest.artifact.digest` (`:696`) and stops there. **No closure, no check record and no
  `skipped` reason reaches a genotype-annotation run.**
- **`just-prs` / `just-prs-mcp` — nothing.** Zero hits for `verification`.
- **This plugin — writes the closure, and drops the block on the way back.** `close_module`
  (`src/just_module_creator/tools/authoring.py:495`) is the only writer here. On the read side,
  `research._module_card` (`tools/research.py:83`) projects a registry card onto `RegistryModule` and
  carries no verification field — and the block is on the *detail*, not the card, so
  `registry_get_module` never surfaces `closed` even though the registry serves it.
- **Format-tree doc drift to be aware of.** `docs/MODULE_LIFECYCLE.md:516` and RM86 in
  `docs/RM_TOC.md:288` still say the closure "reaches **nothing** — `verification.json` is uploaded,
  stored, and then read by no code path, absent from `RECOGNIZED_SPEC_FILES`". That was verified true
  on 2026-08-16 and was fixed by the registry in 0.16 (recognised) and 0.17 (surfaced). The upstream
  finding worked; the sentence describing it did not get retired. Worth an `S<n>` — see the summary.

## Blanks for just-dna-lite

Every one of these is unread today, and each has a concrete consumer action behind it.

- **`manifest.verification.closure` is unread — nothing distinguishes a finished module from a
  draft.** `hf_modules` decides what to load from `artifact.files` and never asks whether a human
  declared the bytes final. A reader could surface *"this module is open — its author has not
  declared it finished"* beside an annotation result, or rank an open module below a closed one in
  discovery. What breaks today: a half-authored module downloaded from HuggingFace annotates a
  genome exactly like a closed one, and the field that would have said otherwise is sitting in the
  manifest already parsed.
- **`checks[].skipped` is unread — "not checked" and "checked, clean" are one state to the
  annotator.** This is RM45's founding complaint, still true one tier downstream. A reader could
  refuse to present a `clin_sig`-driven conclusion from a module whose `clinical_significance` record
  says `skipped: tautology` without also showing that reason. What breaks today: the `v1_port`
  `pathogenic` module carries `clinical_significance subjects=618629 findings=32` — 32 authored calls
  that **disagree with ClinVar** — and nothing between that manifest and a rendered report mentions it.
- **`checks[].release` is unread — no consumer can tell how stale a check is.** The binding
  deliberately does not answer currency; the record does, and it is the only place that does. A
  reader could warn when a module's `clinical_significance` was put against `clinvar_2026-06-27`
  while the pipeline's own snapshot is newer. What breaks today: a module re-published unchanged for
  a year reads as freshly checked.
- **The `closed`/`producer` pair is not carried into the plugin's registry surface.**
  `research._module_card` builds `RegistryModule` from nine fields and the registry serves
  `ModuleDetail.verification` beside them. Adding `closed` alone would let an author see, before
  publishing, that the catalog is about to show their module as open.
- **`RM9`: a module authored through this plugin attests 8 of 15 members.** `check_identifiers` and
  `check-acmg`'s records are the visible loss. Everything needed is public —
  `identifiers.verification_records()` and `verification.merge_records()` — and `close_module` already
  proves the write path works from here.

## Ask the live schema

`verification.json` is **not** a `describe_table` subject — both `describe_table` and
`table_requirements` gate on `draft.DRAFTABLE` and will refuse it. The current field list and both
vocabularies come from `authoring_reference`, which does carry `VerificationRecord`:

```python
authoring_reference()            # jmc tool; JSON, includes "VerificationRecord" with
                                 # the full closed `verification_check` option list
```

Directly, for the pieces `authoring_reference` does not expose:

```python
from just_dna_format.vocab import VALID_VERIFICATION_CHECKS, VALID_VERIFICATION_SKIPS
from just_dna_format.verification import (
    VERIFICATION_FACT_FIELDS,      # what the signature hashes
    VERIFICATION_DIFFICULTY_BITS,  # 20 as of 0.6.1 — a reader requires at least its own minimum
    module_binding, attestation_failure, merge_records,
)
from just_dna_format.manifest import VerificationDoc, VerificationRecord, Closure, Verification
from just_dna_compiler.compiler import authored_input_entries   # the file set the binding covers
```

To confirm a block you hold the bytes for — the only confirmation available to anyone but the
producer:

```python
from just_dna_format.verification import module_binding, attestation_failure, read_verification
from just_dna_compiler.compiler import authored_input_entries
doc = read_verification(spec_dir / "verification.json")
attestation_failure(doc, module_binding(authored_input_entries(spec_dir)))  # None == it holds
```

Write path, and the only two things that may write it:

```
just-dna-enricher enrich|literature|check-identifiers|check-acmg|pgx|clinpgx check|vrs mint  <spec-dir>
just-dna-compiler close <spec-dir> [--by NAME] [--private-key key.pem]
```

jmc equivalents: `enrich_module`, `enrich_literature_pass`, `close_module` (no signing —
use the CLI for `--private-key`). Always read `ClosureResult.dropped_checks` after closing.
