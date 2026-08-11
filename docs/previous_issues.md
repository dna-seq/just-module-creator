# Previously resolved findings

Dogfooding findings (`F#`) resolved **here**, each with its resolution and a code
pointer. Findings move into this file from [dogfooding.md](dogfooding.md); they
are not copied.

**Check here before re-investigating a finding that looks fixed.**

---

## F3 — a strict compile failed with no indication of which step was missing

**Found:** 2026-08-11, first end-to-end run · **Resolved:** 2026-08-11

Compiling a complete, valid spec with `strict=True` returned `success: false`.
The spec was fine; it had simply never been enriched, so no `resolution.csv`
existed and strict refuses what it cannot reproduce.

The finding was not the refusal — that is correct — but that our result gave no
signal about *where in the workflow* the caller was. Fixed by surfacing upstream's
`errors` verbatim in `CompileReport` (it names the unresolved variants and says
what to inject) rather than reducing the outcome to a boolean, and by stating the
enrich→compile ordering in `compile_module`'s docstring and in the skill.

Pointer: `src/just_module_creator/tools/authoring.py`, `compile_module`;
`tests/test_pipeline.py::test_strict_compile_refuses_unresolved_rows` pins that
the refusal arrives as structured errors rather than an exception.

## F4 — the test suite could not import its own helpers

**Found:** 2026-08-11 · **Resolved:** 2026-08-11

`from tests.conftest import offline_settings` resolved to a `tests` package
shipped by a transitive dependency inside `site-packages`, not to this repo's
`tests/`. Collection failed with a confusing `ImportError` naming a path in
`.venv`.

Fixed by importing as `from conftest import ...`, which resolves through the
directory pytest puts on `sys.path`. Recorded in `CLAUDE.md` §6 so the next agent
does not "fix" it back.

Pointer: `tests/test_modes_and_auth.py` import block.

## F12 — the first step of the publishing workflow was not in the tool surface

**Found:** 2026-08-11, asked to create an account and a namespace on the live
registry · **Resolved:** 2026-08-11, 0.3.0

Every registry tool needed a token, and the only route to one the surface named was
`registry-client register` — a shell command in another package, pointed at by
`authenticate`'s docstring. So the plugin gated every registry action behind a
credential nothing in it could mint, and onboarding quietly cost a second toolchain
despite install instructions that promise one command.

Not an upstream gap: `RegistryClient.register(install_id, account)` is public in the
**published** 0.9.1, `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email), and
`generate_install_id()` grinds the proof-of-work locally in 0.3–1.2 s. A public
onboarding API we had simply never wrapped.

Fixed by `registry_register(account, install_id=None, difficulty=None)`. Three
decisions worth keeping:

- **It lives in `auth.py`, always on.** It writes to the registry but cannot be
  token-gated — it is what produces the token — and extended-only would have
  reproduced the same dead end behind a mode flag. `CLAUDE.md` §5 now states the
  exception and its test: a registry write is gated *unless the token is its output*.
- **The token goes into the caller's own session slot**, so registering leaves the
  session usable and no secret has to be copied back through the transcript.
  `authenticate` is now only for a token you already hold.
- **Both secrets come back, and the install-id carries the warning.** It is the
  account's only recovery path; re-registering it reissues a key for the same
  account, while registering again without it creates a *different* account and
  strands the first. `JMC_INSTALL_ID` was added so a later session can reuse it,
  which is a value we read and never write — persisting it ourselves would widen the
  write surface. The `account_taken` error says outright that retrying will not help.

Pointer: `src/just_module_creator/auth.py` — `registry_register`,
`resolve_install_id`, `_registration_failure`;
`models.RegistrationResult`; `settings.install_id`;
`tests/test_modes_and_auth.py::test_an_illegal_account_name_is_refused_before_any_socket`
and `::test_install_id_precedence_and_origin`.

**Not verified end to end from this side, deliberately.** The wrap, the local
refusals and the offline ceiling are covered by the suite, and the live service was
exercised read-only plus one real failure path (a deliberately invalid install-id
returning `422 invalid_install_id`, mapped to actionable text). Actually minting an
account and claiming a namespace belong to the dogfooding side — a builder who also
runs the irreversible probe has graded their own work. **A shipped fix is not a
passed probe.**

## F13 — an irreversible claim had no pre-flight, though upstream shipped one

**Found:** 2026-08-11, same session · **Resolved:** 2026-08-11, 0.3.0

`registry_claim_namespace`'s docstring warned that a namespace "is claimed once and
then owns every module published under it, so this is not a step to run
speculatively" — and then offered no way to be non-speculative. The only way to
learn whether a name was free was to try to take it.
`RegistryClient.namespace_available` is public, read-only and needs no token, and
was unwrapped.

Fixed by `registry_namespace_available` in `research.py`, essentials — beside
`registry_search`, which was already the home for token-free registry reads, and in
the default surface because a pre-flight for an irreversible step belongs there.

**`valid` and `available` are returned separately, and the live registry proves why:**
it answers `test_modules` with `valid: false, available: true`. Collapsing them into
one boolean would have told an author that an illegal name was claimable.

The naming half was the sharper finding. Accounts are validated with the *namespace*
rule (`is_valid_namespace`, `^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` and
`test_modules` were rejected before anything else could happen — and our docstring
said only "Lowercase, hyphen-separated", which reads as a style preference rather
than a hard reject. Module names are the opposite rule, `^[a-z][a-z0-9_]*$`, which
is why a spec holds `my-ns/lactose_tolerance`. That asymmetry is now stated in
`registry_claim_namespace`, `registry_register`, `registry_namespace_available`, the
server instructions, the skill and the README, and an illegal account name is
refused locally with the pattern named, before a round trip is spent.

Pointer: `src/just_module_creator/tools/research.py` —
`registry_namespace_available`; `models.NamespaceAvailability`;
`src/just_module_creator/tools/registry.py` — `registry_claim_namespace`'s docstring.

## F9 — `lookup_citation` could not detect a fabricated PMID, and our docs said it could

**Found:** 2026-08-11, designing the search tool · **Resolved:** 2026-08-11 ·
**Upstream:** `S12`, released in compiler/enricher **0.5.4**

`CitationHint` carried `pmid_exists`, `doi`, `pmcid`, `open_access` — and no title, journal
or year. PMIDs are densely allocated across roughly 1–40,000,000, so a recalled 8-digit
number is almost always a real record for a **different** paper, and `lookup_citation`
answered `pmid_exists: true` for it. Both our skill and the tool docstring said "verify each
PMID with `lookup_citation`", a rule the surface could not enforce: fabrication is a failure
of *identity*, and that call only answered existence.

**Two things fixed it, and the order matters.** First, ours: this is the finding that put
`literature_search` in the **essentials** tier rather than extended, because discovery is the
missing half of an anti-fabrication promise the default surface had already made. Then
upstream's: 0.5.4 added `CitationHint.title` / `journal` / `year` / `first_author`, which
arrive in the same `esummary` response that answers existence and therefore cost no extra
request. Both tools now report a title, and the docs tell a caller to read it and compare.

The working rule survived the fix unchanged, for a reason that was never about titles: a
title checks an id you already hold, and only a search finds the id you should be citing.

Pointer: `models.CitationLookup`, `tools/research.py::lookup_citation`;
`tests/test_discovery.py::test_upstream_supplies_the_bibliographic_fields_identity_needs`
asserts the fields exist on the *installed* package, so the docstring's promise fails with
them if they ever go away, and
`test_an_offline_citation_lookup_withholds_the_title_rather_than_denying_it` pins that a
missing title reads as unchecked rather than as "no such paper".

## F20 — `list_tables` advertised `sources.csv`; `describe_table` and `get_template` rejected it

**Found:** 2026-08-11, authoring `assets/fto_bmi` · **Resolved:** 2026-08-11 ·
**Upstream:** `S21`, released in **0.5.4**

The done-checklist required `sources.csv`, and every route to its columns refused:
`list_tables()` named it under `sidecars`, while `describe_table("sources.csv")` and
`get_template("sources.csv")` both answered *"Unknown table kind"* and helpfully listed
eleven alternatives, none of which was what was asked for — which reads as "you invented
that filename", not "this kind is real but undescribed".

**Two separate defects, and both had to be fixed.** Upstream's: `authoring_reference()`
omitted `SourceRow` entirely, and the root cause was a level below the report —
`SourceRow.layer` and `.declared_use` ran closed-vocabulary validators with no `vocabulary=`
marker, and the guard that discovers enforcement by behaviour iterates `_ALL_MODELS`, which
the model was not in. One omission hid the other. 0.5.4 fixes both and puts `sources.csv`
in `draft.DRAFTABLE` with `(source, layer)` as its natural key.

Ours: the sidecar list in `tools/authoring.py` was a hardcoded literal while the authorable
set came from `draft.DRAFTABLE`, so one tool named a file the next two denied existed. With
upstream's half released, that literal made it *worse* — `sources.csv` appeared as a table
kind **and** as a "do not hand-author" sidecar, telling an author two opposite things.

Fixed by giving it a `_SUBJECTS` entry and removing it from the sidecar list, so all four
schema tools now answer for it. `authoring_reference`'s sidecar sentence says it is the one
fact sidecar a human writes rather than carrying an "except" clause.

What was at stake was not cosmetic: `share_alike` / `commercial_use` / `redistribution` are
three independent axes where an empty cell means **unknown** and never *permitted*, and
`sources.csv` is the only input the compile licence gate reads. An author reconstructing that
from the filename gets the licence declaration wrong in the permissive direction. The
candidate fix we rejected — restating the columns in the skill — would have been the exact
drift the "never hardcode a schema fact" rule forbids.

Pointer: `tools/authoring.py::_SUBJECTS` and `list_tables`;
`tests/test_authoring.py::test_sources_csv_is_a_table_kind_not_a_sidecar`. The related
strengthening is worth noting: `test_list_tables_covers_every_draftable_kind` asserted
`all(t.subject and t.keyed_on)`, which the placeholder fallback satisfied — so it passed
while telling an author nothing, and did not notice `sources.csv` arriving. It now names the
placeholders, verified by removing the entry and watching it fail.

## F21 — the skill's `sources.csv` rule was backwards: compliance warned, omission was silent

**Found:** 2026-08-11, compiling `assets/fto_bmi` · **Resolved:** 2026-08-11 ·
**Upstream:** `S23`, released in **0.5.4**

The skill said a missing `sources.csv` row "is a warning, not an error, so it is easy to ship
without noticing". Both halves were wrong for the literature layer, found by doing what it
said — declaring `pubmed` and `europepmc` earned *"sources.csv declares 2 source(s) no table
in this module uses"*, and deleting the file entirely was completely silent.

Upstream's cause: the orphan and undeclared checks both compared `declared` against a
`used_sources` set gathered from the `source` **columns** of the generated tables, and
`studies.csv` has no `source` column by design — the same design that already exempts the
annotation layer. So `pubmed` could never enter `used_sources` and both branches followed
mechanically.

**The harm was the incentive, not the warning.** An author who reads a warning makes it go
away, and the only way to silence this one was to delete a true row, after which the module
carried no record of the literature terms and the compile was clean. Our skill sent them to
write the row; the compiler told them it was superfluous; the tidy resolution was the wrong
one.

0.5.4 puts `literature` into the same exemption as `annotation` whenever the module's
literature evidence is `studies.csv`, and adds the converse warning: a source a fact table
*does* cite with no `sources.csv` row now reports that its terms are unrecorded. Verified on
the real asset's three rows — compliance is silent, omission warns, exactly inverted from
before:

```
0.5.4, studies.csv has rows:  []
same rows, clinvar row removed:
  ["sources.csv has no row for 1 source(s) the module's fact tables cite:
    ['clinvar'] — their terms are unrecorded."]
```

Ours was a doc fix, and the two candidates we rejected are worth keeping on record: telling
authors to omit literature rows to keep compiles clean would have optimised the warning count
and lost the provenance, and suppressing the warning in `to_findings` would have hardcoded a
judgement about which layers are joinable — a schema fact we do not own.

Pointer: `skills/create-module/SKILL.md` §"sources.csv and licensing".

## F23 — the `gene` column was unverified, and it is the column that exposes a fabricated source

**Found:** 2026-08-11, triaging an LLM-written source · **Resolved:** 2026-08-11 ·
**Upstream:** `S24`, released in **0.5.4**

`variants.csv:gene` was checked against nothing, so a deliberately wrong pairing linted
clean: `rs2252481` (chromosome 6) beside gene `NEGR1` (chromosome 1) gave zero errors and
zero warnings. `check_identifiers` did not cover it — it asked HGNC whether the *symbol* was
current and answered `state: "approved"` for `FTO` without ever asking whether `rs1421085`
is in FTO. The two questions read alike in a result payload, which is what made this easy to
believe already handled.

**Why it mattered more than an unchecked free-text column usually would.** This was the
single check that separated the honest half of a machine-written source from the fabricated
half: four of seven rows named a real gene with an rsID on another chromosome, and every
other check passed on each half separately — the rsID resolved, the symbol was approved, only
the *pairing* was false.

0.5.4 adds `IdentifierReport.gene_loci` (a `GeneLocusConflict` per disagreeing row, naming
both chromosomes) and `gene_loci_not_checked`, which exists for the same reason
`clin_sig_not_checked` does: an empty conflict list otherwise says two opposite things,
"compared everything, nothing disagreed" and "never compared". Upstream kept the granularity
at chromosome level on the argument our note made — a variant legitimately names a distal
gene (`rs1421085` sits in an FTO intron and acts on IRX3/IRX5), so an inside-the-gene-body
check would fire on correct rows until somebody disabled it.

**Adopted rather than merely available**, which is the part that closes this: our
`IdentifierReport` carries `gene_locus_conflicts` and `gene_locus_check_skipped`, and
`check_identifiers`' docstring says to read them even when `stale` is empty. Upstream's own
sentence is passed through verbatim rather than reformatted — it already names both
chromosomes and what to do — because a second wording in front of one finding is how two
answers to one question start. **The manual step is out of the skill**: triage step 2 now
names the tool instead of sending an author to a service outside the toolchain, which was the
consequence this finding was filed for.

We were right not to build the lookup here: `identifiers.py` already resolved symbols against
HGNC and `resolution.csv` already carried the chromosome, so upstream held both halves and
the value was entirely in the comparison.

Pointer: `models.IdentifierReport`, `tools/research.py::check_identifiers`;
`tests/test_discovery.py::test_the_gene_locus_conflict_check_reaches_our_model_three_valued`.
