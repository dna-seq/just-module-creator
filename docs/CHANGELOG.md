# Changelog

What actually shipped, newest first. Includes cross-repo integration changes made
on our side, so agents in sibling repos are not surprised.

## 0.10.1 — enricher 0.6.3, registry 0.18.1, and a drafter that had been dropping rows (2026-08-19)

Adopts **just-dna-enricher 0.6.3** and **just-dna-registry 0.18.1**; `just-dna-format` and
`just-dna-compiler` stay at **0.6.1**, so this is the second partial cut in the 0.6 line and `uv sync`
now gives `0.6.1 / 0.6.1 / 0.6.3`. No tool was added or removed and no signature changed. 153 tests
green, `ruff` clean.

### The blocker in 0.10.0's own release note is gone

0.10.0 opened by saying every version-guarded registry call was refused, because both deployed
instances answered `format: 0.5.4` against our 0.6.1 client. **Both are now on `0.6.1`, and both are
serving registry 0.18.1.** Re-probed rather than assumed, and then driven end to end: the exact call
that came back `409 just-dna-format contract mismatch: server 0.5.4, client 0.6.1` — a
`download` of `eric-mods/lactose_tolerance@1.0.0` — now returns its manifest, and
`assert_compatible()` passes against production and the polygon alike.

Nothing in our code changed for this, which is the point: `targets.instance_note` is a suffix on an
existing `except RegistryError` arm, so it costs nothing while the contract agrees and is still there
if an instance is rolled back. Worth knowing for anyone reading that module's card: the artifact
itself is still stamped `just-dna-compiler 0.5.1`, which is the contract gap registry 0.18.0's
`upgrade` now detects on its own. That is an operator's sweep, not an author's problem.

### `draft_from_clinvar` had been silently dropping ClinVar records

Upstream **S41**. Below 0.6.3 `multi_allelic_rsids` keyed the site on `ref` and fired on more than one
alt *within* that group — which is not what its own docstring claimed. An ordinary ClinVar dup/del
mirror pair (`A>AT` beside `ATT>A` at one position, the same event written from either side) is two
groups of one alt each, so the rsID was never flagged as multi-allelic, both records reduced to the
same rsid-only identity, and the second was dropped as `already_present`. Upstream measured 725
records lost over five genes, **187 of them dropping the better-reviewed half**, because
`select_by_gene` orders by `ref` before `review_stars DESC` — so which record survived was decided by
allele spelling rather than by evidence.

The fix is entirely upstream's; ours is the floor and what we tell an author holding an
already-drafted module. Upstream said such modules "need a re-draft" and said plainly they had not
measured that end to end, so we did, on `MLH1` at 2★ against the local snapshot:

| | rows | distinct identities |
|---|---:|---:|
| drafted with the 0.6.2 predicate | 996 | — |
| drafted fresh on 0.6.3 | 1,030 | 882 |
| the first, re-drafted on 0.6.3 | 1,061 | 913 |

**A re-draft recovers every dropped record and retracts none of the collapsed ones** — 0 identities
missing, 31 present that a fresh draft does not contain, and 1,061 − 1,030 = 913 − 882 = 31 exactly.
Because drafting appends, the correct coordinate-keyed rows arrive *beside* the stale rsid-only rows
rather than replacing them, and the module then asserts both the right answer and the wrong one for
the same locus. Those 31 are precisely the rows carrying the downstream half of S41.

**And they cannot be found from inside the module.** The obvious predicate — an rsid-only row whose
rsID also appears on a coordinate row — finds 0 of 31, because a coordinate-identity row carries no
`rsid` at all. So `draft_from_clinvar`'s docstring and the skill now say to draft into a **fresh
directory** and reconcile against that, and say why re-running over the existing file looks like it
worked. Filed upstream as **S45** and tracked as **F36**; the candidate we offered is that
`append_partial_rows` *name* those rows on the draft report — it holds both halves at merge time —
and explicitly not that it delete them, since by re-draft time a human may have curated the
`genotype`, `state` and `conclusion` on a drafted row.

### `draft_from_clinpgx` was dropping rows too, and the repair is the opposite one

Upstream **S44**: the genotype gate took only the doubled single-base form, so `CTT/CTT` — already
separated by the source — and the bare haploid spelling ClinPGx uses for mtDNA were declined. That
cost **CFTR F508del** (its annotation carries a `del`-spelled genotype and a pure-nucleotide one under
one `annotation_id`, so skipping the annotation discarded the writable row with it) and **every
MT-RNR1 annotation**, 32 rows at evidence level 1A.

The remediation is not the same, and assuming it was is the trap. We ran the equivalent probe with a
stand-in old gate deliberately *broader* than 0.6.2's — 12,410 rows where the fix produces 18,895, so
it declined more than the real one and is therefore the harder case — and a plain re-draft into the
same directory landed on **18,895 rows, 0 stale, 0 missing**: exactly the fresh draft. S44 *skipped*
rows; S41 *wrote them under an identity that has since moved*. Only the second leaves anything behind.
Both docstrings now say which shape they are.

### The skill was teaching a version rule that stopped being true

`SKILL.md` said `module.version` must be quoted because *"unquoted 1 parses as an int and is rejected"*.
Measured on installed 0.6.1: `ModuleInfo(version=1).version` is `'1.0.0'` — accepted. That was the
**pre-0.6** behaviour, and format 0.6's RM17 widening at `mode="before"` is what fixed it, after 26 of
61 foreign modules refused on an unquoted integer.

Quoting is still right, so the checklist line stays — but for the two reasons that are actually true.
The unquoted **decimal** is the hazard, and it is refused with a good message (YAML reads `1.10` as
`1.1`, so the author's text is gone before any validator runs). The silent one is a **digitless**
version: `draft`, `TBD` and `abc` all coerce to `'0.0.0'`, which is a real version somebody could mean,
and it reaches `manifest.identity.version`. That is upstream's open **RM103** (our S42), filed rather
than fixed because refusing it would newly break specs that compile today. It is not invisible, though,
and the checklist now points at where it shows: `validate_module` warns *"module.version 'draft' was
read as SemVer '0.0.0'"*, confirmed through our own tool surface rather than read off their source.

### Also

- **Floors moved with their reasons.** `just-dna-enricher>=0.6.3` is load-bearing — a drafter that
  quietly writes fewer rows than the source has is the worst kind of floor to leave soft.
  `just-dna-registry>=0.18.1` is not: both 0.18.0 and 0.18.1 declare `Client surface: unchanged` and
  both check out. It moves anyway because 0.18.1 requires enricher 0.6.3 itself, so pinning it stops a
  resolver handing us the new enricher beside a registry built against the old one.
- **Nothing to do for S39, our own filing from 0.10.0.** 0.6.3 threads `load_dotenv_file` through the
  six cache resolvers, where it had been inert. We pass that flag nowhere, so the registry's rule for
  this release — *check the flags you already pass on a dependency bump, an inert argument becoming
  live is a behaviour change with no import to grep for* — was run and came back empty. `F35`'s
  `sys.modules` sweep stays: upstream confirmed our reproduction ran the default path, which the fix
  does not reach, and RM102 is open.
- **S43 needs nothing from us.** `likely_pathogenic` and `likely_benign` turn out to be unwritable
  rather than merely unwritten — parquet columns with no authored field behind them, a literal `False`
  since 0.1.0. Our surface never offered them (`describe_table` is generated from the model, which
  does not declare them) and `passes.py` already reads `clin_sig`. Recorded so nobody adds them.
- **Both fixtures re-verified on the new floor**, unchanged: `assets/fto_bmi` and
  `assets/longevity_2026` are literature-review modules, not ClinVar-drafted, so S41 does not reach
  them and no digest moved.

## 0.10.0 — format 0.6, and authoring gets an end (2026-08-18)

Adopts **just-dna-format 0.6.1**, **just-dna-compiler 0.6.1**, **just-dna-enricher 0.6.2** and
**just-dna-registry 0.17.0**. 0.6 is the first release where the three format-tier packages do *not*
move together — the enricher alone goes to 0.6.2, for RM101 — so the floors name three versions
rather than one.

### The thing to know before upgrading: the live registries are still on 0.5.4

`contract_compatible` treats a `0.x` **minor** as a breaking contract, in both directions. Both
deployed instances answer `format: 0.5.4` today, so on this release every version-guarded registry
call — publish, import, download, validate, check, is_published — is refused until the operator
upgrades them. Confirmed live rather than reasoned about: `registry_download` of
`eric-mods/lactose_tolerance@1.0.0` comes back `409 just-dna-format contract mismatch: server 0.5.4,
client 0.6.1`.

That is correct behaviour — a 0.6 artifact genuinely cannot be published to a 0.5 catalog — but
upstream's message names two version numbers beside the module the author was trying to publish, and
reads like something they did. `targets.instance_note` appends the sentence that says otherwise:
whose problem it is, that nothing about the spec will change the answer, and that recompiling will
not either.

It is a **suffix on the existing `except RegistryError` arm**, not a new `except` clause ahead of it.
Both mismatch types are `RegistryError` subclasses, so an arm for them placed after the parent would
be dead and silently so — the same trap the exception work below is about. There is no ordering to
get wrong if there is only ever one arm.

### `close_module` — the step 0.6 tells every author to take

A 0.6 compile warns on every module that records no closure, and told the author to run
`just-dna-compiler close`, which this surface did not wrap. A tier that teaches a step it cannot run
is the failure mode `CLAUDE.md` §5 already names, so it is wrapped.

Closing writes a `closure` into `verification.json` binding the statement to the hash of
`module_spec.yaml` plus the authored CSVs as they stand; edit one afterwards and the compiler drops
it. Deliberately not signed from here — `close --private-key` exists and a key that reaches a tool
argument has been logged, so that half stays CLI-only and the docstring says why.

Both committed fixtures are now closed, which is what makes `assets/fto_bmi` compile with **zero
warnings** for the first time. It had one under 0.5.4 — the `licensing.csv` orphan (`F21`/`S23`) —
and upstream has since fixed that, so the README line promising "expect one warning" was teaching a
warning that no longer exists.

### `licensing.csv`, and the two spellings that must never both exist

0.6 renames `sources.csv` to `licensing.csv`. Both read; only the new one is created; a module
carrying **both** is refused rather than merged, because two copies of a fact-hashed, hand-editable
table are two claims and preferring either discards somebody's curation silently.

`draft.DRAFTABLE` lists both names and backs them with one model, so `list_tables` would have
presented one table as two kinds. `TableKind` gains `deprecated` and `preferred`, both read from
`just_dna_format.layout` rather than restated, and `_SUBJECTS` carries the entry once under the
current spelling with the old one inheriting it — two entries would have answered "which table?"
twice differently the first time somebody edited one line.

`scaffold_module` now routes a deprecated spelling through `layout.sidecar_write_path`: **write to
the file you read**, and the preferred spelling when neither exists. Upstream's scaffold creates
whatever name it is handed, so asking for `sources.csv` on a fresh module used to create a file that
stops being read at format 1.0, in a module being written today. The swap is reported rather than
silent.

The rename stops at the CSV. `sources.parquet` and `manifest.sources` keep their names for the whole
`0.x` tail, so nothing here was renamed to match.

### An outage stops costing three passes their work

`enrich_facts` ran its passes inside no `try` at all, so a gnomAD 503 propagated out of the tool and
took `gene_metrics` and `dosage` with it, including whatever they had already written. Each pass now
gets its own `try`, and the report separates two verdicts that read identically before: `unreachable`
(the source was asked and never answered) from `failed` (the source answered; the problem is local).
`covered: []` beside `missing: []` cannot distinguish those, which is the whole reason the field
exists rather than a warning line. `success` is false when either is non-empty — a pass that never
reached its source did not complete.

This is what enricher 0.6.2 makes possible: every pass now raises its own type with unavailability as
a **subclass**. That is also the release's one real hazard, and it fails *silently* — a `*Unavailable`
arm written after its parent is dead, so `unreachable` comes back empty on exactly the run where a
source was down. `tests/test_passes.py` carries an AST walk that fails on any `except` clause an
earlier arm of the same `try` already catches, plus a self-test driving all three shapes, because a
guard reporting zero proves nothing until it is shown able to report one. Both were run against the
parent-first ordering and watched to fail; the walk names the line.

`_SOURCE_ERRORS` stays parents-only in one tuple, which upstream's upgrade table calls "keeps working
unchanged" — a parent and its subclass in one tuple is redundant, not dead.

### The RM44 counters, and `fully_resolved` stops being read alone

`compile_module` reports `resolution_subjects`, `positional_rows`, `positional_rows_placed`,
`expanded_keys` and `expanded_rows`. The first is the denominator `fully_resolved` quantifies over:
over an empty list that flag is `all()` over nothing, so `true` beside `0` says the module resolved
everything there was, which was nothing. All five are `int | None` and **null is never zero** — each
has a meaningful zero, so coalescing would report a module as having no positional rows where nothing
had counted them.

### The suite was not hermetic, and had not been for a while (`F35`, upstream `S39`)

`test_a_token_does_not_leak_between_sessions` was failing before any of this work — on 0.5.4 too —
and the reason was worth chasing. `just_dna_enricher.locations` calls `load_dotenv` while resolving a
cache path, which `build_server` reaches through `net.py`, and `load_dotenv(override=False)` skips a
key that is **present** — so `F24`'s fixture clearing the environment with `delenv` is precisely what
let the file win. Measured: `JMC_TEST_API_KEY` was `None` after the fixture and held a live
`mk_live_…` polygon token immediately after `build_server`. A session that had authenticated nothing
resolved a real credential, got past the auth check, and failed on the offline ceiling behind it.

The fixture now neutralizes the **loader**, by walking `sys.modules` — every module that did `from
dotenv import load_dotenv` holds its own binding, so patching `dotenv.load_dotenv` would reach none of
them. `setenv(VAR, "")` is not available as a blanket fix here and that is why `delenv` was chosen
originally: these variables reach typed fields, so `JMC_PORT=""` is a parse error rather than "unset".

Filed upstream the same day as format-tree `S39`, because a *library* path loading the caller's `.env`
surprises every consumer, not only this one.

### Also

- **`check_identifiers` still writes nothing, and that now costs something.** The enricher's
  `check-identifiers` / `check-acmg` **CLI commands** record that the question was put; the functions
  we call do not. So a module authored entirely here carries no attestation for those checks. Named
  in `tools/research.py` rather than left implied, and filed as **RM9** — the fix needs a policy
  decision about that module's read-only promise, not just code.
- **Digests re-measured and re-recorded.** `assets/fto_bmi` moved to
  `sha256:c3d633f0…` and `assets/longevity_2026` to `sha256:2df1276a…`; both `content_signature`s
  are unchanged, which is upstream's promise measured on our own fixtures. `README.md` and both
  fixture READMEs now say that a digest is reproducible **under one compiler version** and that
  `content_signature` is the one to compare across an upgrade.
- **Skill and references updated for 0.6**: the pipeline diagram gains `close`, `SYMPTOMS.md` gains
  the PMC-id refusal (RM50), the wrong-build coordinate error (RM48, an error in *both* modes), the
  sidecar collision, the deprecation and the closure warning; `CLI.md` gains `close`, `gene-validity`,
  `assertions`, `gwas` and `hint recover`, plus the `verify --require-marketplace` default that
  rejects every locally-compiled module; `TABLES.md` gains `licensing.csv` and the three new fact
  tables, with the warning that `gwas_effects.csv` deliberately does not fill `weight`.
- **RM93 and RM98 needed no mitigation** — both were 0.6.0 defects fixed in 0.6.1, which is our
  floor. Recorded so nobody builds a guard against them.

## Unreleased — Codex marketplace packaging

- Added a native `.codex-plugin` manifest with a Codex-compatible MCP declaration.
- Reused the existing `create-module` and `find-evidence` skills so they appear in
  Codex's skill and slash-command picker.
- Kept the MCP runtime checkout-relative through `${PLUGIN_ROOT}`; Codex and Claude
  now launch the same source package without duplicating the server implementation.

## 0.9.2 — the off-by-one gets a source and a check (2026-08-14)

Skill only; no code changed. `start` being the 1-based VCF position was already stated in three
places, and the shifted-module story was already told at length — but all of it was *downstream* of
the mistake. It said what goes wrong and what no gate catches. It did not say where the wrong number
comes from, or how to find out before writing the file.

- **A callout at the top of `SKILL.md`**, above everything, for anyone about to type a coordinate.
  Every gate passes on an off-by-one module; that belongs before step 1, not inside step 3.
- **Where the wrong number comes from.** Nobody decides to subtract one — it arrives with the source,
  and the dangerous sources use *both* conventions in different fields. UCSC's position box is
  1-based and its Table Browser `chromStart`/`txStart` columns are 0-based; `pysam`'s `record.pos` is
  1-based and `record.start` is 0-based. So the rule is not "know your source", it is **know which
  field**, and the failure is usually *not adding one back* rather than subtracting again.
- **The decoy in the other direction.** VCF anchors an indel on the base *before* it, so an insertion
  a paper puts at X appears at `POS` X−1 with the anchor base leading both `ref` and `alts`. That
  looks exactly like an unfixed off-by-one and must not be "repaired".
- **A one-call check that fires on row 1 instead of row 3,000.** Author one row, call
  `lookup_variant`, compare `start` — the signal is exact equality, and a difference of exactly 1 in
  a consistent direction is conversion rather than a typo. Run once per *source*. Verified against
  the real record while writing it: `rs4988235` → `2:135851076 G>A`, with the position arriving in
  `withheld` under `applied: false`. That is the point made twice — reading the number to check a
  convention is fine, pasting it is the vacuous-check mistake one section earlier.
- **A checklist line** gated on having authored a `start` at all, and a pointer from
  `references/SYMPTOMS.md`'s `ref mismatch` entry back to the source list, since that message is
  where an author meets this after the fact.

## 0.9.1 — a README for the person the plugin is for (2026-08-14)

Docs only; no code changed. The README had grown into a server manual — tool tiers, mode-switching
tables, auth resolution order, `pgrep` — and the first thing a prospective *module author* met was
`ToolAnnotations`. It is now user-first and short, and everything it used to carry moved rather than
being deleted.

- **`README.md`** — what a module is in four lines (the "rulebook" framing that landed on a real
  beginner), install, the seven steps, the four curation rules, a worked example you can actually
  run, and publishing. The DNA-reading misconception is corrected up front and unprompted, because
  every later step reads as nonsense against it.
- **`docs/FOR_DEVELOPERS.md`** — new. The full tool table, tiers, mode switching, reload semantics,
  auth, safety switches, deployment, layout, upstream.
- **`docs/BEYOND_BASICS.md`** — new. Pharmacogenomics and its no-sale licence trap, polygenic
  scores, binning tables, deeper evidence work, reading other people's modules, and what happens
  after a publish. It names capability areas and defers every column list to `describe_table`, so
  it cannot drift the way a restated schema does.

**The worked example is run, not written.** `assets/fto_bmi` — one rsID, one PMID — is verified end
to end before being documented: `scaffold_module` creates the three files, `lint_rows` reports the
six columns it leaves to the author, `validate_module(strict)` returns zero findings, and
`compile_module(strict)` reproduces `sha256:e52bd75…`, the digest the fixture's own README recorded
on 2026-08-11. The one expected compile warning is named in the README rather than hidden, so a
reader who runs it is not surprised by it.

## 0.9.0 — the card an author actually ships (2026-08-12)

Adopts `just-dna-registry` **0.14.0**. The floor moves to `>=0.14.0` and that is the load-bearing
part: 0.14.0 is the release that projects a spec-directory `README.md` onto the module card, so
**below it every module we publish has a blank catalog card** — which is the first thing a browsing
consumer sees. Our own pin was what kept us off the fix (`F33`).

Verified by importing the symbol from the installed package, per the rule: `amend_readme present:
True` on 0.14.0, `False` on 0.13.0.

**Their `Client surface: unchanged` line did its job.** `F15` asked for exactly this, and reading one
line replaced reading a release in full to establish that our eight-plus methods had not moved. Four
things were *added*, and all four turned out to matter here.

### `registry_amend_readme` — the one published-module write that spends nothing

The readme sits **outside `artifact.digest`**, deliberately, so prose cannot change a module's content
identity. That makes it the only thing about a published version that is repairable, which is why it
earned a wrapper rather than a note telling authors to shell out.

Two refusals, both tested, both about not making things worse:

- **A path is not prose.** Upstream disambiguates a file path from markdown *by type*, and every MCP
  argument arrives as a string — so one collapsed parameter would let `readme="spec/README.md"`
  publish the path itself as the card's text, on a module whose whole problem was an unreadable card.
  `spec_dir` and `readme_text` are separate, and both-at-once is refused.
- **An empty body is refused.** The field is last-publish-wins, so empty prose *replaces* what is
  there. A tool for fixing a blank card must not be able to make one.

Checks that need no credential run **before** `require_key`, matching `registry_publish`'s order:
sending an author to fetch a token for a call that could never succeed is a dead end. The first draft
had it backwards and the new tests caught it — they asserted refusals and got an unauthenticated
result instead.

**Run against the real waiting caller**, not a fixture: `test-sheep/longevity_2026@1.0.0` went from a
zero-length readme to 6860 characters, and the artifact digest afterwards was byte-identical to the
one `published.json` recorded at publish time. That is the tool's central claim, so it is worth
having actually run.

### A download now carries the authored CSVs (`include_inputs`)

`download(include_inputs=…)` is new, and upstream's default is `false` — which means the compiled
parquets and `manifest.json` arrive and the *authored spec does not*. Measured against
`eric-mods/lactose_tolerance@1.0.0`: 4 files without, 7 with, the three extra being
`module_spec.yaml`, `variants.csv` and `studies.csv`.

**Our `registry_download` defaults it to `true`**, and the docstring says it differs from the client
on purpose. This is an authoring surface; the published spec is the most instructive thing the
registry holds, and a "worked example" without the CSVs is not one. With the inputs present you
usually do not need `reverse_module` on a downloaded module — the spec arrived as itself.

`layout="split"` also shipped and is **not** exposed. It emits the enricher's files under `derived/`,
which is genuinely useful for seeing which files an author wrote — and a tree
`just-dna-compiler compile` refuses, because it wants the authored tables at the spec root. Offering
it from here would hand someone a directory they cannot rebuild.

### `available: true` that this surface still cannot act on

0.14.0 turned production's test-data ban into a **default** rather than an absolute:
`allow_test_data=true` is a documented way through, and the availability pre-flight gained
`requires_allow_test_data` and a `warnings` list to stop contradicting the claim it precedes.

Both are surfaced, and `requires_allow_test_data` is **null rather than false** when the instance did
not report it — "did not say" is not "does not require it", and the difference decides whether a name
that reads as free will actually be accepted. Confirmed live: production answers
`available: true, requires_allow_test_data: true` for `test-modules`.

**We do not expose the override**, and the refusal messages now say that the remaining refusal is
partly ours instead of claiming the server makes it impossible. Keeping it is the decision, for the
reason upstream gives for keeping the default: a mistyped namespace there spends a version number and
a global content hash that only an operator purge frees. An agent that can wave that through on an
author's behalf is what the polygon default exists to prevent.

### `README.md`, taught where an author will read it

The skill's directory layout listed `logo.png` as optional and mentioned no readme at all, so
following it produced a blank card. It now names `README.md` as the file that *becomes* the card, says
what belongs in it — what the module claims, which population the evidence came from, what it does not
cover — and records that `MODULE.md` is renamed on upload with a warning while any other spelling is
carried but never read.

### Filed upstream

- **registry `S8`** — their `specfiles.py` comment and changelog both attribute `MODULE.md` to
  "`just-module-creator`'s `write_module_md` tool". **That tool has never existed here**: no match in
  the tree, and `git log --all -S write_module_md` finds none in the history either. It lives in
  `just-dna-pipelines`, in a file named `module_creator.py` — a good enough reason for the mix-up, and
  it will only get more confusing with age. Their rename decision is unaffected and right; the cost is
  a wrong address for anyone who later wants the producer to emit `README.md` at the source.
- **registry `S9`** — `amend_readme` is on the client and not the CLI, while `amend-logo` and
  `amend-changelog` both are. Noticed because our `references/CLI.md` documents their CLI for authors
  who drive it directly, and now has to say the readme is the one amend they cannot do without our
  server.

## 0.8.0 — ask whether it would publish, and hermeticity stops being a promise (2026-08-12)

Two things: `RM8` — the registry client surface is wrapped — and `F24`, where the suite's
hermeticity was a convention that had quietly stopped holding.

### Ask whether it would publish, without spending a version number (RM8)

Four registry releases of `RegistryClient` had gone unwrapped since we adopted 0.12.0 for the
test/prod split. Registry 0.13.0 landing on PyPI yesterday was the precondition, because it
made `would_publish_module_level` a field to *wrap* rather than one to feature-detect.

Two gated pre-flights and two ungated reads:

- **`registry_check`** — the full dry run, and the reason this item mattered. It runs the
  server's own publish gates and **spends no version number**, which on production is the
  difference between a rehearsal and something irreversible.
- **`registry_validate`** — the same without the network tier. It still answers two things a
  local `validate_module` cannot: whether `module.name` matches the path, and whether identical
  authored data is already published under someone else's name.
- **`registry_is_published`** — ungated, uploads nothing. The content signature is computed
  locally, so an author can ask "is this data already out there, under any name" before they
  have a token at all.
- **`registry_health`** — reports the instance's own mode, so a rehearsal is *confirmed* rather
  than assumed. `expect_mode` already refuses a mismatch; this is how you see it beforehand.

**Where the work actually was: not letting a skip look like a verdict.** One
`PublishPreflight` carries *two*, deliberately.

`module_level_clear` is upstream's `would_publish_module_level`, renamed so nothing reads it as
a green light — it composes exactly three gates and excludes the network tier. `verdict` is the
whole dry run and is **null whenever that tier did not run**: on a bare validate, on
`skipped_reason`, and when no token was resolvable. Defaulting it to `false` would let "we could
not ask" arrive shaped like "would not publish", which is the same error as a skip producing a
pass with the sign flipped.

`rerun_rather_than_fix` carries `S20` all the way to the author's next action. A false verdict
beside unreachable rsIDs means **re-run**, not go and fix the spec: a strict publish against an
unreachable Ensembl really does refuse, while the variants may be perfectly findable. Telling an
author to fix that is how real rows get deleted. `unchecked` and `non_blocking` keep upstream's
other careful distinctions — a `clin_sig` check the operator has no snapshot for never blocks
and is never dropped either, and identifier findings never move the verdict because a publish
does not run that pass.

**Verified live against the polygon, not only in the suite.** A clean `assets/fto_bmi` returned
`verdict: true` in 1.3s; the same spec with one invalid `state` returned `verdict: null` with
`verdict_unavailable: "invalid_spec"` — null rather than false, which is the entire point.

**One RM8 bullet was already done and one is deliberately skipped.** `content_signature` was
listed, but `module_signature` has always called the same `just_dna_compiler` function the client
method wraps, so wrapping the client's would have been a second path to one answer.
`issue_jwt_token` returns 501 unless the deployment configures a signing secret and nothing here
consumes a JWT — a tool that is usually a 501 is worse than no tool.

### The suite's hermeticity was a promise, not a mechanism (F24)

`CLAUDE.md` §6 claimed no test could read a developer's `.env`. That held only for as long as
every construction remembered `_env_file=None`, and by today `.env` carried a live polygon token:

```
Settings(_env_file=None).test_api_key    : None         # hermetic, as documented
Settings().test_api_key                  : 'mk_live_…'  # the developer's REAL token
Settings().offline                       : False        # ← worse than the finding said
```

That last line is what the original note missed. A forgotten kwarg lost **both** properties, so a
test could reach the network *while holding a live credential* — passing locally, passing in CI
where `.env` is absent, and meaning something different on each machine.

Now an autouse fixture points `env_file` at a path that cannot exist and clears the ecosystem's
variables from `os.environ`, so forgetting the kwarg is harmless. `env_file` stays in
`model_config`: the product needs it, and breaking the product to protect the suite is the wrong
trade.

**The clear-list is derived from `Settings.model_fields`, not written** — and that mattered inside
the same change. The hand-written first draft covered the credentials and missed seven variables,
`JMC_API_KEY_HEADER`, `JMC_TRANSPORT` and `JMC_PORT` among them; an exported `JMC_API_KEY_HEADER`
changes what a test asserts as effectively as a token does and far less visibly. Only the four
upstream names stay hand-maintained, because no field of ours can name them.

### `assets/longevity_2026` — a second reference example, authored with no human in the loop

Thirteen longevity rsIDs, 19 authored rows, grounded in five papers that are all 2025 or 2026 — one
of them a bioRxiv preprint, cited by the PMID the NIH preprint pilot gives it. Written end to end by
an agent through the MCP surface, `authorship: [ai, agent]`, and rehearsed to
`test-sheep/longevity_2026@1.0.0` on the polygon, where the server's own recompile reproduced the
local `artifact_digest` exactly.

It complements `assets/fto_bmi` rather than repeating it. `fto_bmi` is the *triage* example — seven
offered claims, four of them fabricated gene/rsID pairings, one row surviving. This one is the
*grounding* example: nothing was fabricated and the interesting decisions are all about how much a
row may claim. Five variants named in the same papers were dropped for having no stated effect
allele, nine rare candidates carry `direction: unknown` and no weight because the preprint prioritises
them without a direction, and exactly one preprint variant is written `protective` — the *CGAS* one
with functional work behind it, at a deliberately small weight.

Two findings came out of authoring it, both in `docs/dogfooding.md`: **`F29`** (nothing can search for
a trait CURIE, so a correct `trait_efo_id` was reached only because a guess landed on a deprecated
term whose obsolescence pointer named the replacement) and a second, sharper instance of **`F26`** —
this session's server had none of the four registry tools listed above, while the repo, the manifest
and the skill were all 0.8.0. A build that has been reloaded once goes stale again at the next bump,
and the symptom this time was the skill teaching four steps the surface could not run.

`S7` was filed to the registry's intake: a `README.md` in the spec directory is uploaded by
`gather_spec_files` and never surfaces — the published card's `readme` stays empty, with no
`amend_readme` on the client and no documentation of what does populate it.

## 0.7.0 — six mitigations come out, and a target that verifies itself (2026-08-11)

Upstream shipped. `uv sync` now installs format/compiler/enricher **0.5.4** and
`just-dna-registry` **0.13.0**, and the floors say so. Between them they released every fix
this repo was holding a guard for, so this release is mostly *deletion of caution* — plus one
real behaviour change, which is why it is a minor.

**Every claim below was verified by importing the symbol from the installed package**, never
by reading the sibling checkout or a changelog. That is the rule this repo learned the hard
way: on 2026-08-11 every entry in `just-dna-format-pending-fixes.md` said "open upstream"
while all eight had been answered and six were already fixed in tree.

### The behaviour change: a declared target is now verified

`targets.client_for` is the single construction point for every `RegistryClient` in the
server, and it always passes `expect_mode=target`. Registry 0.13.0 reports `REGISTRY_MODE` on
`/health` and `/api/v1/version`, and the client raises `ModeMismatchError` before the first
call that could spend anything.

So the polygon/production split stopped being a convention. Our configuration records which
instance we *meant*; the server says which one *answered*; a publish aimed at the polygon that
would have landed on production now refuses instead of succeeding irreversibly. **A server
that reports no mode fails the check** — upstream's decision, and the right one: asking for
verification and getting silence is not a pass, and the remedy for that direction is a server
upgrade while the remedy for the other direction is nothing.

Passed uniformly rather than only where a guarded method is reached. The alternative is a
per-site judgement about which upstream method is guarded *today*, which is exactly the kind
of fact that goes stale in silence. A test scans the source so a stray `RegistryClient(...)`
anywhere else fails the suite — verified by adding one and watching it fail.

What we still do **not** do is infer a mode ourselves. Upstream's reply to `S3` says why both
halves belong: ours records the intent, the guard checks the answer.

### `lookup_citation` answers identity, not just existence (F9, closed)

`CitationHint` gained `title` / `journal` / `year` / `first_author`, all from the same
`esummary` response that answers existence, so they cost no extra request. `CitationLookup`
carries all four and the docstring now tells a caller to read the title and compare it against
the paper they meant — **a title that disagrees means the id is wrong however true
`pmid_exists` is.**

The working rule did not change, for a reason that was never about titles: a title checks an
id you already hold, and only a search finds the id you should be citing. "Take every PMID
from a `literature_search` result" stays in both skills and in `server.INSTRUCTIONS`.

### `check_identifiers` now catches the fabrication pattern (F23, closed)

The highest-value check in the triage workflow, and it used to require leaving the product.
`IdentifierReport` carries `gene_locus_conflicts` — rows whose `gene` sits on a different
chromosome than the row's own variant — and `gene_locus_check_skipped`, because an empty
conflict list otherwise says two opposite things: "compared everything, nothing disagreed" and
"never compared".

This is the pairing that separated the honest half of a machine-written source from the
fabricated half: four of seven rows named a real gene with an rsID on another chromosome, and
every other check passed on each half separately. Upstream's sentence is passed through
verbatim rather than reformatted — it already names both chromosomes and what to do, and a
second wording in front of one finding is how two answers to one question start.

`skills/create-module/SKILL.md`'s triage step 2 now names the tool instead of an
explicitly-labelled manual step.

### `sources.csv` is a table kind (F20, F21, closed)

Upstream put it in `draft.DRAFTABLE` with `(source, layer)` as its key and taught
`authoring_reference()` about `SourceRow`. **Our half had to move too, and with upstream's
alone it got worse**: `sources.csv` appeared as a table kind *and* under `sidecars` ("do not
hand-author"), telling an author two opposite things. The hardcoded sidecar literal is gone
and it has a `_SUBJECTS` entry, so all four schema tools answer for it.

`S23` also inverted the incentive back the right way: a `literature` row is no longer reported
as unused when `studies.csv` carries rows, and a source a fact table *does* cite with no row
now warns that its terms are unrecorded. Re-verified on `assets/fto_bmi`'s real rows —
compliance silent, omission warns, exactly the reverse of what shipped before. The skill's
rule is corrected to match; it previously told authors the opposite of what happened.

### Findings now carry the line an editor shows (F14, closed)

`LintFinding.line` exists and `to_findings` passes it through. **Never derived:** `row` is a
0-based data index and `line` is 1-based and header-inclusive, so computing one from the other
would bake in an offset that goes silently wrong the day upstream changes either convention.
`references/SYMPTOMS.md` gained the two entries this finding argued for — the boolean misparse
on a correctly-written column, and what to do when `row` and `line` disagree about one CSV.

### An unreachable Ensembl is unchecked, not absent (F17, closed)

Never mitigated here, and the fix vindicates that. `checked` now records the source on the
answered-empty path too — which is precisely the string the rejected workaround would have
keyed on, so `"ensembl-rest" not in checked` would have **inverted the day 0.5.4 landed**,
silently, with our tests green. Waiting cost nothing; building would have cost a wrong answer.

Nothing to adopt in code: `lookup_variant` is a pass-through and the new `warning` reaches a
caller unchanged. The guidance changed — triage step 1 says to read the finding and re-run on
the warning, rather than inferring unchecked-ness from a missing set element.

### `ATTESTATION_BEARING`, and the consequence that outlives it (S11)

`describe_table` reports `attestation_bearing` as a **subset** of `redundancy_bearing`, so the
sharper refusal reason reaches an agent instead of living only in `CLAUDE.md`. Upstream added
the constant *and* kept both provenance columns in `REDUNDANCY_BEARING`, because they qualify
under that map's own definition too.

The rule is unchanged in substance, and worth restating because a released constant can look
like a solved problem: once a fulltext has been read through `fetch_fulltext`, `quotes_found`
on that row is no longer independent evidence. It has degraded to a citation-pairing check —
still worth having, since it catches a quote filed against the wrong PMID — but nothing
establishes that a human ever looked.

### Kept on purpose

- **`ServiceGate`'s lock.** Upstream made `PacingGate` thread-safe (`S15`) *because* the
  injection API asks callers to share one. Two locks is harmless; none is a race. Registry
  0.13.0 adopted the same fix and corrected three comments that had claimed
  `enrich_max_concurrency = 1` was what made sharing a bundle correct — true through 0.5.3,
  wrong now. Ours never made that claim.
- **`compile_module`'s `resolve_with_ensembl=True` pin.** `S14`'s rename was **refused** with
  a reason — the compiler has no network branch, so a `--no-ensembl` flag would assert
  something false. That makes the pin permanent rather than interim.
- **`_module_card`'s defensive projection.** Upstream says it is safe to delete against a 0.13
  server, and the reference docs are now version-stamped, which was the condition `CLAUDE.md`
  set. Kept anyway, for a **narrower** reason than the one it was written for: `get_module` is
  not one of the six methods `assert_compatible` guards, so a self-hosted instance older than
  0.13 answers it with no compatibility check in front of it. Our floor pins the *client*; the
  server on the other end is someone else's deployment. The comment now says that instead.

### Where the findings went

`F9`, `F20`, `F21` and `F23` moved to [previous_issues.md](previous_issues.md) — moved, not
copied. `F14`, `F16`, `F17` and `F11`'s upstream half are closed in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md). `F15` is partly answered:
per-release `Client surface:` lines and version-stamped reference docs shipped, and the
enumerated contract is open on their roadmap with the reason stated — it needs a contract
version of its own, which is a promise to hold it stable across package releases.

[RM8](ROADMAP.md) is **unblocked, not done**: `would_publish_module_level` is now a field to
wrap rather than one to feature-detect. Wrapping a new tool surface is a separate change from
adopting a version, which is why it is not in this one.

## 0.6.0 — a contact address that is somebody's, and asking before assuming (2026-08-11)

A minor rather than a patch: it adds a configuration variable and changes default network
behaviour. Unpaywall used to sit out every call on a fresh checkout for want of a contact
address; it now always participates.

### `JMC_USER_EMAIL`, and a default behind it

The polite-pool contact resolves in three steps, first hit wins:

1. **`JMC_USER_EMAIL`** — new, and ours. Named for the *user* because that is what the address
   means to the services reading it: NCBI's polite pool and Unpaywall both **meter and contact
   per address**, so it says whose rate-limit budget is being spent.
2. **`JUST_DNA_CONTACT_EMAIL`** — the enricher's own variable, so one `.env` still configures
   both surfaces. **Still inherited, not reimplemented**: `build_services` passes `email=None`
   when ours is unset and lets `EutilsSettings.__post_init__` do that read, because it only
   consults the environment when `email is None`. A change to upstream's precedence is followed
   rather than copied.
3. **`settings.DEFAULT_CONTACT_EMAIL`** — the project's own address, supplied by its owner.

**The default is not the "never fabricate a contact address" rule being bent.** An invented
address misattributes traffic to a stranger; this one attributes it to the people who ship the
tool, who accept that. What it costs is *attribution*, and the cost is real: an install that sets
nothing pools its budget with every other unconfigured install and sends any abuse report to the
project's inbox rather than the author's. So the default exists to stop a source sitting out a
call, **not** to make configuring one optional — `.env.template` asks for `JMC_USER_EMAIL` in its
own section, and `build_services` logs *which of the three steps answered*, because "project
default" is the state an operator wants to notice.

Since a contact is now always present, `contact_email()` returns `str`, and the two `if not
email:` branches went with it rather than being left to rot — including the one that made
Unpaywall report itself unavailable.

### The skill now asks, at the top, instead of assuming

Two questions once, before any authoring: **do you want to read the papers or only cite them**
(fulltext work is what makes `provenance_quote` honest, since those columns record a human having
read the paper — an author who will not read anything should learn that at step 0, not step 6),
and **may your email be used for lookups**. Asked **only when neither variable is set**, written
to `.env` as `JMC_USER_EMAIL` so it outlives the session, never asked twice, and "I would rather
not" is a complete answer because the default handles it.

**And never *inferred*** — not from `git config user.email`, not off a commit, not from the
registry account. An address the author did not offer is personal data volunteered on their
behalf, and a wrong guess misattributes traffic to a real stranger.

### Found while testing this

- **`F24`** — the suite's hermeticity is a convention with no guard. `Settings(_env_file=None)` is
  hermetic as documented, but a bare `Settings()` returns the developer's **real** polygon token,
  and nothing fails when a test forgets the kwarg — it just starts meaning something different on
  every machine. (`_load_env()` living inside the CLI's `_run()` rather than at import is what
  keeps the leak narrow, and is right.)
- **`F25`** — nothing reports the resolved contact or which step supplied it, so the skill's new
  "ask only when nothing is configured" precondition can only be established by reading `.env` off
  disk. The `F23` shape again.
- `test_a_contact_address_is_never_invented` changed rather than being deleted: the invariant is
  now that the contact is either operator-configured or the *documented constant*, never
  synthesised — which is what forbids a future default derived from a hostname or a git config.

## 0.5.3 — metaphors that survive a beginner, and triage for a source you were handed (2026-08-11)

Two skill additions, both drawn from an assisted session with a genuine non-specialist rather
than invented at a desk.

### `## Explaining this to someone who is not a geneticist`

The framings that were *observed* to work, not the ones that sound good. **A module is a
rulebook** — "if the DNA says X at spot Y it means Z, and here is who showed it" — did more
than everything else combined; the session visibly turned on it (*"a module is a rulebook,
you should've said so!"*). Alongside it: a variant as a **street address**, a genotype as
**which letters you have there**, a row as **a claim with a receipt**, a blank cell as
**"we don't know" and never "no"**, and the quote columns as **"a human read this and found
the sentence"** rather than "here is a relevant quote".

Two rules travel with the table. **Correct the DNA-reading misconception early and
unprompted** — a beginner's model is "point this at my DNA file and it tells me about me", and
every later step reads as nonsense against it, so they cannot tell you why they are lost. And
**never let a metaphor make a decision**: "rulebook" is right for explaining and wrong for
choosing a column, so the moment the question is what a cell may contain, ask the tool. A
metaphor that answers schema questions has become a second source of truth.

### `## 0 — Where a module comes from`

Where ideas come from — a catalog gap (`registry_search` reads prod, so it is a call and not a
guess), a source that publishes the table, a paper the author read, or **something the author
was told**. That last is the commonest in practice and the only one that begins by *removing*
claims, so it gets a procedure.

**Triaging a source you were handed** is the new content, and it is the run's main
methodological result. A summary is somebody's reading of evidence, and if a machine wrote it
the citations may be generated rather than recalled. Six steps: does the rsID resolve (re-run a
no-locus before believing it — `F17`); **is it on the same chromosome as the named gene**; does
the pairing appear in any paper (read `sources` before trusting an empty result); does the
cited paper say what is claimed (only a title settles identity); are two survivors the same
signal; does anything state the direction, and drop the row if not.

Real numbers, stated in the skill because they calibrate expectations: **seven offered rsIDs
became one authored row.** Four paired a real gene name with an rsID on a different
chromosome — the signature of a generated citation, and invisible to every other check because
both halves pass separately and only the relationship is false. One survivor was dropped as an
LD duplicate, one because no located paper said which allele carried the risk. A number the
summary offered turned out to be the paper's *rescue* factor reported as its deficit.

**Step 2 is labelled as requiring a lookup outside the toolchain**, because it does: nothing
verifies `gene` against the resolved locus (`F23`, upstream `S24` — filed with the argument
that the check belongs at chromosome granularity, since a variant legitimately names a distal
gene and an interval check would fire on correct rows until someone disabled it). Labelling it
is deliberate — a procedure that quietly requires leaving the product trains authors to skip
the step.

## 0.5.2 — and when it genuinely is good, advocate (2026-08-11)

The other half of 0.5.1, and shipped separately only because 0.5.1 was already tagged.
0.5.1 on its own biases toward *under*-publishing: an agent told never to raise production
unasked will also sit on a module that deserves it, and a good module nobody publishes helps
nobody. So the default is now stated as being against **assuming**, not against **advocating**.

The hard part is that "genuinely good" cannot be left to judgement — an agent asked whether
its own work is good will say yes. So both halves are written as checks:

- **The catalog is actually missing it** — `registry_search(gene=…)` / `registry_search(query=…)`
  read production by default, so this is a call with a result you can show the author, not a
  guess. An overlapping module means extend it or say why yours differs, never publish a
  near-duplicate.
- **The module clears every bar** — strict validate *and* strict compile, `fully_resolved`,
  a `resolution.csv` that was produced rather than authored, every PMID from a
  `literature_search` result whose title was read, a declared licence with `sources.csv`
  covering every source, **no `state` or `direction` settled by guessing** (having dropped
  rows for that reason counts in favour), a rehearsal published *and read back*, and enough
  breadth to be worth an immutable version.

**The last bar is the one that fails, and `assets/fto_bmi` is now the worked counter-example
in the skill.** It cleared everything else — strict, fully resolved, VRS minted, one
impeccable citation, honest blanks throughout — and `registry_search(gene="FTO")` returned
`total: 0`, so the gap was real. It was still right not to promote: one locus, no declared
licence, no readme, unsigned. **Underrepresented is necessary and nowhere near sufficient.**
An honest module and a module worth an immutable `1.0.0` are different standards, and
conflating them turns a thin catalog into a catalog of stubs — worse, because a stub occupies
the search result a real module would have had.

The permission is to *advocate*, with the search result and the passing checks as evidence.
It never skips the explicit yes on `registry_claim_namespace(target="prod")` or
`registry_publish(target="prod")`.

## 0.5.1 — the polygon is the default *answer*, not just the default argument (2026-08-11)

Guidance only. No tool signature, vocabulary, artifact or digest change — but it changes
what an agent should *say*, which for a plugin whose contract includes a skill is a
shipped change and not a docs tidy-up.

0.5.0 made every registry write default to `target="test"`. That fixed the mechanism and
left the conversation open. An agent helping a first-time author could still volunteer
`target="prod"` to be helpful, and the exposure is entirely in what a novice's words mean:
**"publish it", "put it online", "share it with my friends", "send it to your site" is not
a request for the immutable catalog** — it is somebody who does not yet know there are two
registries. Observed in an assisted dogfooding session where that last phrasing came up
verbatim, from a user who had been told a module is "a rulebook" ten minutes earlier.

`skills/create-module/SKILL.md` §7 and `server.INSTRUCTIONS` now both say: publish to the
polygon, **name it out loud**, say it is a rehearsal instance nobody installs from, and
stop. Promoting is a separate decision the author makes after seeing a clean run, and it
needs an explicit yes with the cost stated *in* the question — because neither
`registry_claim_namespace(target="prod")` nor `registry_publish(target="prod")` can be
undone by anyone, and production's content claim survives a `yank`, so a half-finished
first module spends the version number *and* the right to publish that data under any
other name.

One corollary, learned the same session by leaving litter: **prefix the module name as well
as the namespace on a first rehearsal** — `test_my_module` under `test-my-ns`. The
operator's `purge-test-data` sweep matches on both halves, so a bare `my_module` inside a
prefixed namespace is rubbish nobody collects, and a first-time author is exactly the
person who will not return to run `registry_delete_module`. The existing advice to rehearse
under the real name is still correct and still there — it is now explicitly *not* the
first-module default.

Recorded in `CLAUDE.md` §10 in the user's own words, because the reasoning ("this confuses
the crowd and we don't want half-baked test modules on prod") is what makes the rule
survive contact with an author who is impatient to share.

## 0.5.0 — two registries, and a publish you can rehearse (2026-08-11)

Adopts the test/prod split the registry shipped in its 0.12.0, and takes the client
from 0.9.1 to 0.12.0 with it — three releases of catch-up in one step.

### Why a rehearsal was impossible before, and is now the default

A published version is immutable *and* its authored rows are claimed by a
name-independent `content_hash` that `yank` does **not** release. On one instance that
makes every practice run permanent: it burns the version number and the right to
publish that data under any other name. Upstream measured it (publish to a sandbox
namespace → publish for real → `409 duplicate_content`, and yanking the sandbox copy
does not help), which is why a "test subtree" in production was never the answer and
the polygon exists instead.

So every registry tool now takes **`target="test" | "prod"`**:

- **The write tools default to `test`** — `registry_register`, `authenticate`,
  `registry_whoami`, `registry_namespace_available`, `registry_claim_namespace`,
  `registry_publish`. A forgotten argument on the polygon costs nothing; the same
  omission against production cannot be undone. Going live is an explicit
  `target="prod"`.
- **The catalog reads default to `prod`** — `registry_search`, `registry_get_module`,
  `registry_download` — because the question they ask is about the published world.
  The asymmetry is deliberate and `tests/test_registry_targets.py` pins both halves, so
  a new registry tool cannot inherit an endpoint by accident or flip a default quietly.
- **`registry_delete_version` / `registry_delete_module`** (new, gated, polygon-only)
  are what make a rehearsal repeatable: they free the version number *and* the content
  claim. Aimed at production they refuse **before sending anything** and name `yank` as
  what production offers instead — a 405 from the far end is a safe answer but not a
  useful one.

### Credentials are per instance, and never substitute

The two deployments keep separate databases, so an account minted on one does not exist
on the other. `JMC_API_KEY` / `REGISTRY_TOKEN` is the production token and
`JMC_TEST_API_KEY` / `REGISTRY_TEST_TOKEN` the polygon's; the HTTP path reads
`X-Registry-Token` and `X-Registry-Test-Token`; `SessionKeyStore` is keyed by
`(session, target)`. **Nothing falls back from one to the other** — a production key on
the polygon is a key for an account that is not there, so a fallback would report "the
registry rejected your token" when the truth is "you have not registered here yet". The
same install-id may be reused on both, and should be: one secret to protect, two
recognisably-yours accounts.

### Naming, checked before the round trip

Production refuses `test-`prefixed namespaces and `test_`prefixed module names with
`422 test_data_on_prod`. We check locally first and **before the credential**, because
telling an author to go and find a token for a call that could never succeed is the
dead end this surface keeps removing. The two prefixes are duplicated from upstream's
`config.Settings.test_data_prefix` and `services.purge.module_name_prefix` rather than
imported — both live outside the client's exported surface, and an import a future
client-only wheel drops would take the server down at load time — so a test asserts
they still match.

Not refused: a `test-` **account handle** on production. The self-register route does
not check it (only the namespace claim, the publish and `issue-key` do), so refusing it
here would invent a rule the server does not have. It is reported after the fact
instead, where it is true: the handle registers, its namespaces will not.

An unprefixed rehearsal on the polygon is likewise advised, never refused — publishing
under the name the module will really carry is the most faithful rehearsal there is.
The note says the consequence: `purge-test-data` sweeps by prefix and will not collect
it, so delete it yourself.

### Also

- **`registry_publish` gained a duplicate-content pre-flight** (`is_published`, new in
  client 0.11). The signature is computed locally from the authored rows — no upload,
  no recompile — and it is the same value the registry gates `409 duplicate_content` on.
  When the check itself fails it says so and the publish proceeds: a check that could
  not run is not a check that passed, and the server runs the authoritative one anyway.
- **`published.json` records the `target`**, and prior receipts are matched on version
  *and* target. A polygon rehearsal of 1.0.0 is not a prior publish of production's
  1.0.0; treating it as one would have hidden the identity the registry stamped on the
  real publish.
- **Every registry result carries `target`.** Nothing in a registry payload says which
  instance answered, so we say it — see `F16` for why that is not something we can
  verify against the server.
- The skill's §7 is rewritten as *rehearse, then promote*, with the two-instance table,
  and `references/CLI.md` now says the client has one URL and cannot tell you which
  instance it points at.

### Filed upstream while doing this

- **`S3`** (registry intake) — no endpoint reports `REGISTRY_MODE`, so a rehearsal
  cannot prove it is not on production. Tracked here as `F16`.
- **`S1` came back answered** the same day and is fixed in the registry's tree for
  0.13.0: the `would_publish` ceiling no longer applies offline, the 422 carries what it
  computed, and `/validate` gained `would_publish_module_level`. Not on PyPI, and
  production reports 0.12.0, so `F11` stays open here until the release lands.
- Measured while adopting: `module-marketplace.just-dna.life` is an alias of production,
  and `module-polygon.just-dna.life` resolves and terminates TLS but answers a bare 404 —
  DNS'd and fronted, not yet deployed. We ship the documented URL regardless, so it
  starts working the day it comes up.

## 0.4.0 — the essentials tier now runs the whole workflow (2026-08-11)

### The tier rule was wrong, not just one tool short of right

Dogfooding reported a narrow gap: the default tier could not verify a trait CURIE, because
`lookup_identifier` and `check_identifiers` were extended-only. `describe_table` would tell an
author that `trait_efo_id` takes an ontology CURIE and then offer nothing that checks one, so the
honest move was to leave the column blank and the tempting one was to write an id from memory —
which is precisely what rule 1 of the server instructions forbids.

Surveying before fixing turned up that the gap was a symptom. The stated rule — *essentials is
everything that only reads, plus the ClinVar draft* — did not describe the code **in either
direction**. `scaffold_module` and `compile_module` both write and were always essentials, while six
read-only tools sat behind the mode flag. And the worst case was not on anyone's list:
**`enrich_module` was extended-only while being step 6 of the order the server's own INSTRUCTIONS
teach**, so an agent following the default tier's instructions reached for a tool that was not there.

So the rule changed rather than the membership. **The tiers now split on cost, not usefulness:**

- **essentials** — everything whose work is bounded by what the caller named: one identifier, one
  paper, one spec directory. That is the whole taught workflow, scaffold through publish.
- **extended** — only what a *corpus* sizes (`paper_citations`, the PGx drafters, the bulk fact
  passes) or that reads back somebody else's compiled artifact (`reverse_module`,
  `registry_download`). Seven tools, down from sixteen.

Nine tools moved into essentials: `enrich_module`, `check_identifiers`, `lookup_identifier`,
`fetch_fulltext`, `lookup_open_access`, `authoring_reference`, `module_signature`, `verify_artifact`,
`registry_get_module`. Nothing left essentials, so this is additive for every existing caller —
`extended` still lists a strict superset.

Each landed beside its siblings rather than in a second closure: the schema dump and the integrity
pair in `authoring.py` (still network-free), the identifier and paper reads in `research.py` (still
writes nothing to a spec), and `enrich_module` in `passes.py` next to `draft_from_clinvar` — they are
the only two tools that fetch and then write into a spec directory, which is now what that module
means. `advanced.py` keeps the three that stayed.

### The guard is derived, not restated

`tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier` parses tool names
straight out of `server.INSTRUCTIONS` and asserts every one exists in essentials. It is written
against the text rather than a copy of it, so editing the taught order re-checks the tier for free.
Verified to bite: the parse yields `enrich_module`, which the pre-0.4.0 essentials tier did not have.
`test_extended_mode_is_a_superset` additionally pins `extended - essentials` to an exact set, so a
tool cannot drift between tiers unnoticed.

### Also

- **`authoring_reference` was unreachable from the tier that is told to call it.** `CLAUDE.md` §2 and
  the skill both instruct an agent to ask `describe_table` / `table_requirements` /
  `authoring_reference` rather than recall a schema fact — and the third was behind a mode flag. A
  rule pointing at a tool the default tier lacks is a rule that gets ignored.
- **README gained "Reloading after a change" and "Switching mode."** `/reload-plugins` does not
  re-exec a stdio MCP server — `/mcp` reconnect does — and stale servers accumulate. Mode has three
  launch paths that do not fall back to each other, and **editing `.env` cannot switch a
  plugin-launched server**: `plugin.json` exports `JMC_MODE` into the subprocess and `.env` loads with
  `override=False`, so the file is read and then ignored for that key, silently. Probed, not assumed.
- **The credential how-to moved into the skill.** It had been living in `docs/UX_TESTER.md`, where an
  author would never see it. `SKILL.md` §7 now also answers the account-*name* half: there is nothing
  to save, because `registry_whoami` reports it and re-registering with the same install-id returns
  the account that id owns while ignoring the `account` argument.

## 0.3.0 — registry onboarding (2026-08-11)

### A version bump touches two files, and the suite now knows it

`.claude-plugin/plugin.json` is JSON and cannot read `importlib.metadata`, so it is the one place
`CLAUDE.md` §2's "never hardcode a version string" cannot be obeyed — and it shipped this release
still declaring 0.2.0, caught in review rather than by anything automated. The drift is silent:
plugin loading is unaffected, so the only symptom is an installed plugin misreporting itself.

Fixed, and `tests/test_plugin_manifest.py` now fails on the mismatch, verified by reverting the
manifest and watching it fail rather than assuming it would. The same file pins the other
hand-maintained claims in the manifest: that its `mcpServers` command is still the console script
`[project.scripts]` installs and stays `${CLAUDE_PLUGIN_ROOT}`-relative, that the declared skills
directory holds the two skills the description promises, and that `marketplace.json` carries no
version of its own — one hand-maintained version string is the ceiling.

### You can get a registry account from inside the tool surface

Dogfooding hit the wall at step zero: every registry tool needed a token, and the only route to one
the surface named was `registry-client register`, a shell command in another package. The plugin
gated every registry action behind a credential nothing in it could mint, which made a one-command
install quietly cost a second toolchain. Recorded as `F12`/`F13`, both now in
[previous_issues.md](previous_issues.md).

Nothing upstream was owed. `RegistryClient.register` and `.namespace_available` are public in the
**published** 0.9.1; `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email, self-service by design), and
`generate_install_id()` grinds the proof-of-work locally in about a second. Two public APIs we had
never wrapped.

- **`registry_register(account, install_id=None, difficulty=None)`** — always on, in `auth.py`
  beside `authenticate`. The one registry write that cannot be token-gated, because it is what
  produces the token; `CLAUDE.md` §5 now names that exception and bounds it to a set of one. Not
  extended-only either — hiding the only route to a credential behind a mode flag is the same dead
  end in a different place. The minted token goes into the caller's own session slot, so registering
  leaves the session usable and no secret travels back through the transcript by hand.
- **Both secrets are returned, and the install-id carries its warning in the field description.** It
  is the account's only recovery path: re-registering it reissues a key for the *same* account,
  while registering again without it creates a different one and strands the first. `JMC_INSTALL_ID`
  was added so a later session can reuse it — a value we read and never write, because persisting a
  secret ourselves would widen the write surface. `account_taken` now says outright that retrying
  cannot help, since a key is only ever reissued to the install-id that created the account.
- **`registry_namespace_available(namespace)`** — essentials, read-only, no token. The pre-flight
  `registry_claim_namespace` demanded and did not offer. `valid` and `available` stay separate
  answers, which the live registry justifies immediately: it reports `test_modules` as
  `valid: false, available: true`. One boolean would have called an illegal name claimable.
- **The name rules are stated wherever they bite.** Accounts obey the *namespace* rule
  (`^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` was rejected before anything else could happen,
  while module names are the opposite (`^[a-z][a-z0-9_]*$`) — hence `my-ns/lactose_tolerance`. An
  illegal account name is refused locally, with the pattern quoted, before a round trip is spent.
  "Lowercase, hyphen-separated" was replaced everywhere it appeared: it read as a style preference
  rather than a hard reject.

Verified hermetically (name refused before any socket opens, offline ceiling holds for both tools,
install-id precedence and origin) and against the live registry read-only, including one real
failure path. Minting an account and claiming a namespace are left to the dogfooding side: a builder
who runs the irreversible probe has graded their own work.

### Upstream had answered every one of our findings, and our docs did not know

Checked `../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md` for the first time. The format
tree's inbox holds only *open* items — an answered `S<n>` moves out, prose byte-for-byte — so it has
been empty since 2026-08-11 with `S1`–`S18` all answered. Meanwhile every entry in our
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md) still said "open upstream". All
eight were answered; six are fixed **in tree for the unreleased 0.5.4**.

That distinction is now written down as three states rather than two — *accepted and filed* →
*fixed in tree* → *released* — because only the third lets a mitigation come out, and the middle one
is the easy mistake. PyPI's newest is compiler/enricher 0.5.3 and format 0.5.0, which is what we
install; confirmed by symbol rather than changelog (`hints.ATTESTATION_BEARING`,
`hints._report_ragged`, `Finding.line` are in the sibling checkout and absent from the installed
package — and `hints.py` lives in the **compiler**, not the enricher).

- `S11`, `S12`, `S15`, `S16`, `S17`, `S18` — accepted and fixed in tree. Every mitigation stays until
  0.5.4 ships. `S18` (our `F14`, filed the same day it was found) had both defects fixed the same
  day, which is the counter-example to `S14`'s lateness.
- `S10` — accepted, filed as upstream `RM46`; the granularity question is design work, not an
  unanswered report.
- `S14` — **settled, and half of it refused with a reason.** A `--no-ensembl` flag would assert
  something false, because the compiler has no branch that reaches the network at all; renaming a
  published parameter is major-only regardless. Our pin is therefore permanent rather than interim,
  and `F10` is closed. A refusal is an answer, and wording a guard as "until upstream fixes it" when
  upstream has declined is its own kind of stale.
- The registry's intake behaves the opposite way: no history file, and `S1` (our `F11`) genuinely
  still open. Absence of movement there means nothing has been answered.

`CLAUDE.md` §8 gained the history path, the id rule (`.claude/triage-state.sh --next` — ids are never
reused and the inbox being empty says nothing about what is taken; the next is `S19`), and the
instruction to re-read upstream's verdicts rather than trusting our own `Status:` lines, which go
stale silently because upstream answers in its own tree and nothing notifies us.

## 0.2.0 — literature discovery, drafting, and the fact passes (2026-08-11)

### Adopted just-dna-compiler / -enricher 0.5.3

- Upstream shipped `_check_positional_joinability`, which **partly closes S9/F5**: `validate` and
  `compile` now warn per positional table how many rows have no `chrom`+`start` **and how many of
  those the injected `resolution.csv` could place**. Verified reaching our surface unchanged on the
  one-row `pharm_variants` reproduction. That second count is the actionable half — it separates
  "never enriched" from "the coordinates exist and this tier does not apply them". The coordinates
  themselves are still not materialized; upstream defers that to RM43 because filling them breaks
  Principle 7 (`reverse_module` would return a derived coordinate as an authored one).
- `heteroplasmy.csv` joined the enricher's subject list upstream, so an rsid-authored heteroplasmy
  module now resolves at all.
- `just-dna-registry` 0.11.3 is **not adopted**: it is unpublished (PyPI has 0.9.1) and lives in the
  renamed `just-dna-marketplace` repo, so taking it would mean a local path dependency and the
  plugin's one-command install would stop working for anyone else.

### `registry_publish` now keeps the identity it is given

The registry is the authority on module identity — it stamps `namespace`, `owner`, `version` and
`canonical_id` on publish and overrides anything authored. We were returning that in a message and
dropping it, so nothing on disk recorded that a spec had ever been published, under what identity, or
against which digest. It now lands in a `published.json` receipt beside the spec, with the artifact
digest, the content signature and an ISO-8601 UTC timestamp. Not a cache and not a temp dir: a receipt
that does not survive the session is not a record. It cannot go into `module_spec.yaml` either —
`module:` is `extra="forbid"` and those exact keys are rejected there because the registry owns them
(upstream S1). An already-recorded version is never overwritten; a published version is immutable, so
a changed digest is reported for investigation rather than applied.

### Three documentation gaps filed upstream

Facts we had to establish by **experiment** rather than read, filed as `S15`–`S17`
in the format tree under their own "Documentation gaps" heading — nothing is
misbehaving, so they read as a separate category:

- **`PacingGate`'s concurrency contract is unstated, and it is not thread-safe.** We
  found this by demonstration (four threads overlap inside `wait()` on a frozen
  clock) and shipped a locked `ServiceGate` subclass. `ENRICHER.md` documents the
  class in nine places without a concurrency caveat, which matters because
  `LookupClients`' own docstring tells callers to hold and reuse one — exactly the
  arrangement that needs the answer.
- **Whether a spec directory may hold files the compiler does not know is
  unspecified.** It tolerates them; we tested, and `published.json` now relies on it.
- **`source` exists on only 4 of 16 row models, and all four are enricher-produced.**
  No authored table has one, so the `sources.csv` coverage check can only see sources
  a *pass* introduced — a hand-read source is structurally invisible, not merely easy
  to forget. Found by putting a `source` column on a `pharm_variants.csv` and getting
  `Extra inputs are not permitted`.

The rule behind them is now in `CLAUDE.md` §8: a fact you had to probe is a doc bug,
and the experiment is the argument for fixing it.

### Two upstream intakes, not one

The registry keeps its own `docs/CONSUMER_SUGGESTIONS.md` (created 2026-08-11, its own
`S<n>` series) at `../just-dna-marketplace/` — a stale directory name; the project and
package are `just-dna-registry`. Our
intake rule said one file served all four packages, which had stopped being true. The
`would_publish` note was written into the format tree by mistake and moved; a note in
the wrong file may as well not be filed.

### Docs swept for upstream gaps we had absorbed as our own

Three items were sitting in our roadmap or our skill as though the work were ours:

- **`would_publish`'s variant ceiling** (`422 too_many_variants` on a large module) had never been
  filed, and the idea book proposed building our own `check_publishable` to route around it. Filed as
  **S15**, tracked as **F11**, idea-book entry withdrawn — a parallel publishability check in a
  consumer is how two answers to one question start drifting.
- **RM7** (no `sources.csv` terms for any literature source) is upstream's granularity question. There
  was never work here for us: we report it and refuse to fill it. Removed from the roadmap, now **F8**
  in `just-dna-format-pending-fixes.md`.
- **F9** (`lookup_citation` cannot check identity) gained its upstream-blocked entry alongside the
  dogfooding one, since the mitigation is ours and the fix is not.

`docs/ROADMAP.md` now states the rule at the top: an item belongs there only if the work is ours.
**RM3** (signing) is deferred with its reason, and **RM4** was reclassified — it is a dogfooding probe,
not a deliverable, and now lives in `dogfooding.md`.

### New tools

- **`literature_search`** (essentials) — PubMed, Europe PMC, Semantic Scholar and the preprint
  index, merged. `pmids=[...]` reads titles back for ids you already have.
- **`lookup_open_access`**, **`fetch_fulltext`**, **`paper_citations`** (extended).
- **`draft_from_clinvar`** (essentials), **`draft_from_cpic`**, **`draft_from_clinpgx`** (extended)
  — closes F1/RM1, the hole in the middle of the taught workflow.
- **`enrich_facts`**, **`enrich_literature_pass`** (extended) — closes RM2.

### New skill

- `skills/find-evidence/` — search strategy, evidence appraisal, and the copyright rules that decide
  whether a module is publishable. `create-module` points at it from step 3 and stays the canonical
  authoring procedure.

### Why search is in the *essentials* tier

`CitationHint` carries no title, so `lookup_citation` can only prove a PMID **exists** — and PMIDs
are dense enough that a recalled one is usually a real record for a different paper. Both our skill
and the docstring told authors to "verify every PMID with `lookup_citation`", a rule the surface
could not enforce. Discovery is the missing half of an anti-fabrication promise the default tier had
already made. Filed upstream as `S12`; recorded as **F9**.

### Fixed

- `CitationLookup` was dropping `CitationHint.alterations` entirely, so the essentials tier was
  deleting the one refusal upstream hands it (the redundancy-bearing `doi`). Now carried, with
  `abstract_available`.
- `PacingGate` is not thread-safe and every tool here runs through `anyio.to_thread.run_sync`;
  `ServiceGate` adds the lock. One shared `LookupClients` per server replaces the per-call clients
  that were discarding rate-limit state.
- `lint_rows` documented refusals it never returns (F2/RM5) — narrowed to what it does return.
- `SKILL.md` and `DOMAIN.md` both claimed `draft --drug` refuses on multi-population pairs; upstream
  removed that in 0.5.1. RM1's rationale rested on the same removed behaviour.

### Owning sockets

`net.py` is now the only module permitted to open one, with retries on `tenacity` and upstream's own
`attempt_floor` stop so one deployment variable tunes our persistence and theirs together.
`JMC_LITERATURE_SOURCES` is a policy ceiling shaped like the offline one — a per-call `sources`
narrows it and can never widen it.

## Unreleased

### Adopted the house ruleset (2026-08-11)

- `AGENTS.md` is now a symlink to `CLAUDE.md`. They had been two different
  documents — a domain briefing and a code guide — so an agent's behaviour
  depended on which it happened to read.
- `CLAUDE.md` rewritten to the house template: must-reads in order, every
  prohibition inline, the `.claude`/`skills` assets named, and the authoring
  procedure left solely in the skill rather than restated beside it.
- Domain briefing moved to `docs/DOMAIN.md`.
- Adoption questionnaire answered and recorded: all four just-dna packages stay
  **hard dependencies** (no extras, no optional imports); this repo is an
  **application, not a published library** (no `__all__`, no re-export
  `__init__.py`); **no charter** — `just-dna-format`'s `CONSTITUTION.md` governs
  the format and ours would be a second charter about someone else's invariants.
- All inline imports hoisted to module top level.
- CLI now loads `.env` via `python-dotenv` (`override=False`) before reading
  configuration, so one `.env` serves both this server and the enricher it calls.
- Network transports print their URL before binding.
- `.env.example` → `.env.template`; removed the two placeholder values
  (`authors = "Your Name"`, `JMC_WORKSPACE=/path/to/your/modules`).
- Added the `assets/`, `data/{input,interim,output}` and `scripts/` layout with
  the ignore-all + allowlist rule on `data/`.

### The plugin (2026-08-11)

- Repo became a Claude Code plugin: `.claude-plugin/plugin.json` declares the MCP
  server inline using `${CLAUDE_PLUGIN_ROOT}` so it launches from the plugin
  directory rather than the user's cwd; `.claude-plugin/marketplace.json` makes
  `/plugin marketplace add ./` work.
- `skills/create-module/` — two independent authoring write-ups unified into one
  MCP-first skill, plus `references/{TABLES,SYMPTOMS,CLI}.md`. Removed the
  `.claude/skills/` copies they came from, which would otherwise have shadowed it
  with two same-named duplicates.
- Dropped 0.4-era history from the skill: this is a *new*-module creator, and that
  format version never reached production.

### The server (2026-08-11)

- Replaced the cake-demo FastMCP template with the just-dna authoring server.
  Package renamed `mcp_template` → `just_module_creator`; env prefix `CAKE_` →
  `JMC_`; Smithery removed (not applicable).
- `requires-python` raised to **≥3.13** — `just-dna-compiler` requires it. Ruff
  target, pyright version and the Docker base image moved with it.
- Added `just-dna-compiler`, `-format`, `-enricher`, `-registry`; bumped
  `fastmcp[tasks]` to ≥3.4.7.
- Tool tiers: **essentials** (the offline authoring loop plus the read-only
  lookups curation depends on), **extended** (enrichment as a background task,
  integrity, round-trip, registry reads), **gated** (registry writes, per-session
  token, never server-global).
- `JMC_OFFLINE` added as a hard network ceiling a per-call argument cannot
  override; `JMC_WORKSPACE` added as write containment for the HTTP transport.
- `compile_module` pins `resolve_with_ensembl=True`, so the wrapper cannot reach
  the branch that silently compiles every row with `chrom=None` and succeeds.

## Cross-repo

- **2026-08-11 — `just-dna-format`**: appended an independent corroboration to
  `docs/CONSUMER_SUGGESTIONS.md` **S9** (the non-SNP table families are
  materialized verbatim, so `resolution.csv` never reaches them). Reproduced here
  from the authoring surface with a `pharm_variants`-only module, twice — with and
  without a covering `resolution.csv` — which isolates the mechanism. Note left,
  not committed. No mitigation shipped on our side; the skill now tells authors to
  supply the rsID for those tables.
