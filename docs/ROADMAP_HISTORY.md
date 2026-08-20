# Roadmap history

Items no longer on [ROADMAP.md](ROADMAP.md) — **shipped**, or **deferred with a
reason**. Nothing is deleted; it is relocated. Newest first.

An item that left the roadmap because the work turned out not to be ours is not
here: it is filed upstream as an `S<n>` and tracked in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).

---

## RM17 — nothing on the authored side can see that one quote is repeated across every row citing a paper

**Severity:** high · **Status:** SHIPPED 2026-08-20 (night run) · **Owner:** agent B · **Opened** 2026-08-20

The measured case is `F44`. `registry_check(target="test", literature=true, strict=true)` returns
byte-identical output — `verdict: true`, every finding list empty — for a module whose 69
`provenance_quote` cells are all the article's title and for the same module remediated. `lint_rows`
on three rows carrying the same title string reports `0 errors, 0 warnings`. `validate_module` and
`compile_module` say nothing either. Four published modules reached production through this workflow
carrying 3668 title-quotes.

**Why waiting for upstream is not the plan.** `S54` asks the compiler to compare a quote against
`CitationHint.title` inside `_study_quote_found`. That is the right fix for their layer and it will
not fire on the modules that motivated it, because `S56` established that the quote check never ran
on any of them. Ours is a different check in a different place.

### What to build

A finding over `studies.csv` alone, offline, no pass and no network:

> group the rows by `pmid`; for any `pmid` with more than one row, count the **distinct** non-empty
> `provenance_quote` values. One distinct value across many rows is reported.

`warning` level, aggregated by reason with a count (never one per row), in **both** `lint_rows` and
`validate_module`, beside the other authored-table findings. The message should name the PMID, the
row count and the quote's first few words, because the author needs to recognise which paper it is.

The title comparison is a *second*, stronger signal and needs a network call
(`lookup_citation(pmid).title`), so it does not belong in the offline linter. It fits
`registry_check`, where a round trip is already being paid for.

### Decisions already taken, so they are not re-argued

- **Warning, never error.** One quote per PMID is legitimate when a module cites a paper for one
  row, and a deliberate trait-level grain is a defensible authoring choice — see `find-evidence`'s
  *what may honestly go in `provenance_quote`*. The signal is one quote across *many* rows.
- **The grain is the shape, not the string.** A rule that only catches the title would miss the next
  variant of this, which is one real sentence pasted onto 2000 rows.
- **It reads the authored file directly.** It must not depend on `literature.csv`, whose counters
  are stale on every module that has the problem (`F49` / `S56`).

### The one thing to settle before writing code, and it is why this was not built the night it was found

**Whose finding is it, in a tool that transports upstream's verbatim?** `validate_module`'s
`warnings` are upstream's own, carried across the MCP boundary field-for-field by
`_shared.to_findings` precisely so `error`/`warning`/`info` and `None`-means-unchecked survive.
Mixing a finding **we** computed into that same list makes it impossible for a caller to tell which
layer said what — which is the distinction §2 exists to protect, one level up.

Three shapes, none obviously right:

1. **A separate field** — `authored_findings`, beside `warnings`. Honest and additive; costs every
   caller a second list to read, and invites a second one after it.
2. **A `source` on `LintFinding`** — `upstream` vs `just-module-creator`. Preserves the ladder and
   the distinction in one list; changes a model every tool returns.
3. **`lint_rows` only, and never `validate_module`.** `lint_rows` is already ours end to end, so
   nothing blurs. Costs the check its reach: the pre-publish path an author actually runs is
   `validate_module`, and a linter you have to remember to call is the one that does not get called.

The third is tempting and is probably wrong for exactly the reason `F44` exists. Run §1 rather than
picking one.

### Done when

`lint_rows` and `validate_module` both report it — with the layer that computed it legible — a test
builds the failing shape from a real module copy and watches the finding appear, and
`find-evidence` + `studies.md` point at the tool instead of at a hand-written group-by.

### How the open question was settled, and how to reverse it if that was wrong

`RM17` said to run §1 rather than pick one of the three shapes. The owner was unreachable — the night
brief was explicit that a defensible decision written down beats a blocked night — so it was decided
and this is the reasoning.

**None of the three shapes was taken whole, because the two surfaces cannot express the same thing.**
`LintResult.findings` is a list of `LintFinding`; `ValidationReport.warnings` is a list of **bare
strings**. Option 2 (a `source` on the finding) is unavailable on validate; option 1 (a separate
field) is redundant on lint; option 3 gives up the surface an author actually runs before publishing,
which is the reason `F44` happened at all.

So the rule is stated once and each surface expresses it in the only way it can:

> **Upstream's own strings stay in `errors` / `warnings` / `info`, untouched. Anything this layer
> computed is a `LintFinding` carrying `source`.**

On `lint_rows` that means our findings append to `findings` with `source="just-module-creator"`; on
`validate_module` it means a new `authored_findings` list, because appending a string to `warnings`
would be irreversible — a caller could never separate the layers again.

**To reverse:** the whole decision is one field on `LintFinding` and one on `ValidationReport`. Moving
to option 3 is deleting the `validate_module` line in `tools/authoring.py`; moving to option 1
everywhere is adding a second list to `LintResult`. Nothing else depends on the shape.

### Measured against the corpus that motivated it, 2026-08-20

Run over the five externally authored modules in
`../just-dna-format/data/output/corrected_modules/`:

| Module | studies rows | rows quoted | distinct PMIDs | distinct quotes | flagged |
|---|---|---|---|---|---|
| `aggression_anger` | 69 | 69 | 3 | **3** | 2 |
| `big_five_personality` | 859 | 859 | 26 | **26** | 24 |
| `cognitive_intelligence` | 2045 | 2045 | 33 | **33** | 28 |
| `risk_impulsivity` | 695 | 695 | 19 | **19** | 14 |
| `muscle_lean_mass` | 11 | 0 | 0 | 0 | 0 |

**One distinct quote per PMID, exactly, on all four** — the `F42` signature, reproduced by counting
rather than by trusting the earlier measurement. The check flags **68 of the 81** PMIDs; the thirteen
it does not are cited on a **single row each**, which is legitimately one quote and is the decision
`RM17` recorded in advance.

**`muscle_lean_mass`'s zero is not a discrimination** and should not be read as one: its `studies.csv`
has no `provenance_quote` column at all. It is the same module that was immune to the coordinate-shift
class, for the same reason — it authors the least it can get away with.

### Shipped

`src/just_module_creator/authored_checks.py`, wired into `lint_rows` and `validate_module`, with
`tests/test_authored_checks.py` — twelve tests including the discrimination the whole item exists for:
the honest `studies.csv` and the repeated-quote one produce the same `valid` and a different
`authored_findings`, which is exactly the pair `registry_check` returned byte-identically.

Left for the network surface, as the item specified: comparing the repeated string against
`lookup_citation(pmid).title` inside `registry_check`, where a round trip is already paid for. Upstream
`S54` may also land it in `_study_quote_found`; check before duplicating.

---

## RM14 — `provenance.json` is recognised by the registry and by nothing here

**Absorbed into RM16 on 2026-08-20, the same day it was opened. Not shipped, not dropped —
re-scoped, because it had been read from the wrong end.**

Opened as a low-severity tidiness item: `provenance.json` is in the registry's
`RECOGNIZED_SPEC_FILES`, survives a storage round-trip, and no tool or dossier here writes or reads
one. True, and the wrong frame.

What it actually is: the **missing half of the counterstance**. §2 was corrected the same day to say we
may write and revise, with the agent owed a discriminator for when editing against a source is right —
and the hazard there is not vacuity but that **the source lags the edge** (a retraction, a refuting
meta-analysis). An override may be the module being more current than the archive, and nothing recorded
that judgement anywhere. `ProvenanceItem.rationale` is exactly the freeform record such a judgement
needs, and it already exists upstream, AI-aware, unread by any check.

So the item is not "write a file nobody reads". It is "capture the reason an authored value outranks a
source, at the moment of the override". Re-opened at **high** severity as `RM16`, with the contract half
— whether a check downgrades a mismatch to INFO when a record exists — filed upstream as `S52`.

## RM12 — `enrich_gwas` is wrapped by no MCP tool

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**What shipped.** `enrich_gwas_effects(spec_dir, strict, use, study_facts, offline)` in
`tools/passes.py`, registered in `register_extended_passes`, returning a new
`GwasReport`. `gwas_effects.csv` was the last enricher pass an author driving this plugin
had to shell out for, and the shelling-out was documented as a gap in
`skills/module-tables/references/gwas_effects.md`.

**Extended, and the cost rule decides it cleanly.** The budget is `1 + 2N` requests for
a variant with N published associations, because `pmid`, `trait`, `ancestry` and
`study_accession` all sit behind `_links` — measured upstream at **382 requests and 0
cache hits** for one real module, since rs1800562's 189 associations each name their own
study. The size is set by how much has been published about the variant, not by anything
the caller named, which is the definition CLAUDE.md §5 gives. It sits beside
`enrich_facts` and `enrich_literature_pass`, and `test_modes_and_auth.EXTENDED_ONLY`
pins it there.

**Three upstream facts the wrapper had to carry rather than smooth over.**

- **`strict` fires on the usual answer.** It escalates on `unusable` and
  `p_value_underflows` — never on `missing`, because the Catalog holding nothing for a
  variant is a fact about the variant and true of most clinically authored ones.
  `reference_examples/hfe_hemochromatosis`, a shipped flagship, carries **six** p-values
  the Catalog publishes as `0.0`, so strict refuses it while nothing about it is wrong.
  The docstring says that in those words, and the failure path says it again on the
  result. It also escalates *after* the write, so a strict failure leaves the sidecar
  holding everything `best_effort` would have written — which is the difference between
  an escalation and a fetch failure, and the message is what tells them apart.
- **Published betas are not weights, and the tool makes that readable rather than
  asserted.** `associations_without_effect_allele` and the sorted distinct `effect_units`
  are computed from the rows upstream returned: `not_found` rows are excluded from the
  first, because their null `effect_allele` means *no association exists* while a
  recorded association's null means *the study never established which allele carries
  the effect*. On one real module those come out at 33 of 186 and 12 distinct units for a
  single variant. There is no argument on this tool that could write `weight`.
- **`study_facts=false` is a sticky cut.** It drops two thirds of the budget and leaves
  `pmid`/`trait`/`trait_efo_id`/`ancestry`/`study_accession` null — and the merge is keyed
  on `association_id` alone, so a later run with study facts **on** skips those rows
  rather than backfilling them. Only deleting the file recovers them. Warned on the
  result and asserted in the test; filed upstream as a doc gap.

**No counter is coalesced to zero.** The five numeric fields are `int | None` and the failure path
passes `None` for every one. On a strict escalation `0` would be wrong rather than merely absent —
upstream's message names non-zero counts and the sidecar is already written — and `rows` is `None` on
an offline no-op as well, since an existing file keeps what it held and nothing counted it.

**No `produced_by`.** RM13 stamps *generated schema answers*; this is a verdict about a
directory at a moment, which that item explicitly left unstamped, and `SchemaVersions`
carries the format and compiler versions where a pass answer would need the **enricher's**
— a stamp naming the wrong package is worse than none.

**One `except` arm on purpose.** `GwasNotFound` is a subclass of `GwasError`, so an arm
for it would have to come first, but it cannot arrive: `associations_for` catches the
Catalog's 404 and returns the empty *answer* that becomes a `not_found` row, and `follow`
catches it so an association whose study record moved keeps null study facts. An arm for
a type that never arrives reads as if it did.

**The strict ladder now has a test, which upstream still does not have.** `strict`
appears nowhere in `enricher/tests/test_gwas.py` in either direction, so
`test_the_gwas_strict_ladder_escalates_on_the_catalogs_shape_after_writing` drives the
real `enrich_gwas` with an injected transport and asserts what it observably does: one
underflowing association raises, the row is on disk when it raises, and `best_effort` on
the same input reports the count and succeeds.

## RM10 — three tool answers restated a schema fact instead of generating it

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**Why it was worth a roadmap item at all.** Every one of the three was a *hardcoded schema
fact*, which §2 forbids — and all three had already gone stale, which is the argument for the
rule rather than a coincidence.

**1. `keyed_on` named a deprecated column.** `_SUBJECTS["copynumbers.csv"]` said
`(gene, modifier_gene, modifier_cn)`, and `modifier_cn`'s own field description has read
*DEPRECATED since 0.6, removed at 1.0 — use modifier_copy_number* since format 0.6 landed. So the
one surface that tells an author what an append collides on was pointing at a column upstream
removes at 1.0, while `modifier_copy_number` — which holds the fractional dosages VCF 4.4 §7.2
allows — went unmentioned.

**The key half stays in `_SUBJECTS`, and that is the decision worth recording.** The
subject half is the documented exception ("which table?" is about intent, and the schema cannot
answer it); a key is structure, so the obvious move was to derive it. Nothing public derives it:
`draft.natural_key` is **row-level** — an instance in, key *values* out, never column names — and
returns `None` for the four binning kinds on purpose. The two registries that hold the names,
`compiler._TABLE_DUPE_KEYS` and `MeasureBinRow._KEY_FIELDS`, are both private, one of them as
lambdas. Removing the field was the other option and it is worse: "what will an append collide on"
is a real question, and answering it nowhere sends an author to memory.

So the string stays and the drift class is closed by a **test** instead: every token is now an
exact model field name, and
`test_every_documented_key_column_is_a_live_undeprecated_field` resolves each one against
`model_fields` (accepting a property, because `StudyRow.variant_key` is derived rather than
authored) and fails if any is missing or opens its description with `DEPRECATED`. Run against the
old map it flags six tokens: `modifier_cn`, plus `variant`, `a`, `b` and two `trait`s that were
loose prose rather than column names — which is why they were corrected too, since a token that
does not resolve cannot be checked. Filed upstream as **`S48`**, asking for a public
`key_fields(csv_name)`.

**2. `list_tables().sidecars` was a literal four and the toolchain has seven.** It named
`resolution.csv` and the three 0.5 fact tables, so the three format-0.6 ones —
`gene_validity.csv`, `clinical_assertions.csv`, `gwas_effects.csv` — were missing from the one
answer that claims to say what a machine writes, while `authoring_reference` in the same module
described all of them. Now derived from `just_dna_registry.specfiles.FACT_CSVS` + `RESOLUTION_CSV`,
minus the draftable kinds.

**Why the registry's public roster and not the compiler's authoritative one.**
`compiler._FACT_TABLES` is the tuple the compiler actually loads and carries the row model too,
which is exactly what RM11 needed — and it is private. The registry publishes the same roster
because it has to recognise every file the compiler reads. The cost is real and recorded in the
code: the roster now comes from a different package than the loader it describes, so a registry
release lagging a compiler release makes the answer lag too. Filed upstream as **`S47`**. When a
fact table is added upstream, `sidecars` grows with no edit here; `describe_machine_table` refuses
the new name explicitly (real, undescribable by this build) and
`test_the_produced_roster_and_its_models_agree` fails, which is the intended sequence.

**`S47` was answered and fixed in tree within the hour** (their RM112): `hints.DERIVED_TABLE_MODELS`
and `hints.derived_model_for` are public in their checkout and retire both the map and the
cross-package roster — in the change that raises our compiler floor, because compiler 0.6.1 is what
we install and has neither symbol. Answered is not installable; the mitigation stays until it is.

**The `licensing.csv` carve-out is derived, not special-cased.** It is a fact sidecar that a human
writes, and it is in `draft.DRAFTABLE`; subtracting the draftable kinds removes it from the roster
and leaves it a table kind with a template and a linter. A table upstream makes hand-authorable
moves surface with no edit here. It is deliberately **not** listed under `sidecars` even though
`FACT_CSVS` names it: that field means *do not hand-finish this*, and licensing is the one you do.

**3. `studies.csv` was described in pre-RM47 terms.** Upstream's RM47 relaxed
`StudyRow.REQUIRED_ANY_OF` from `({rsid}, {chrom})` to `()`: a paper grounding a bin threshold, a
method or a population is a legal row with no variant identity at all, and `variant_key` may be
`None`. Our subject read "the evidence for a variant", which would have an author drop exactly the
row the relaxation was for. The subject now names the relaxation, `_COMPOSITION_NOTE` says a
binning module may carry `studies.csv` without `variants.csv`, and a test validates such a spec
strict-green rather than asserting the prose. `create-module/SKILL.md`'s studies section carries the
same pre-RM47 claim and was **not** edited here — a parallel session owns `skills/`, and it is
reported to them rather than changed underneath them.

**One upstream defect surfaced by the same probe**: `scaffold.COMPANION_KINDS` still pulls
`variants.csv` in behind `studies.csv` unconditionally, so a binning module doing the right thing is
told it owes an empty `variants.csv`. Passed through rather than patched — it is upstream's answer —
and filed as **`S49`**.

**The resource was fixed in the same change**, since it restated the same roster in prose and read
`_SUBJECTS` with a bare `.get`, so `sources.csv` rendered two em-dashes in the table an author reads
to choose a kind.

---

## RM11 — no route answered a machine-produced table's columns

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**The hole.** `describe_table` gates on `draft.DRAFTABLE`, which is authored kinds only, so
`resolution.csv` and the six fact tables answered *"Unknown table kind 'resolution.csv'"* — a
sentence that is false twice: the file is known, and it is in every enriched module. Meanwhile every
skill on this surface says *ask the tool, never memory*. The rule therefore had a hole exactly where
an author is looking at a produced file and deciding whether to touch it, and the only answer was
prose in a dossier, which is the thing that drifts.

**What shipped: `describe_machine_table`, essentials tier.** One name in, the live column list out —
type, category, description, vocabulary and pick-list — for `resolution.csv`, `frequencies.csv`,
`gene_metrics.csv`, `literature.csv`, `gene_validity.csv`, `clinical_assertions.csv` and
`gwas_effects.csv`. Essentials by the cost rule: one table named, pure model reflection, no network.
It carries `produced_by: SchemaVersions` like every other generated answer (RM13).

**The columns come from upstream's own assembly, not a second one of ours.**
`reference.authoring_reference()["models"][ModelName]` already describes every derived model in the
same shape `hints.describe_table` produces for an authored kind, so the tool projects that rather
than re-deriving type/category/vocabulary — the drift upstream's own D1-4 was. `vocabulary_notes` is
merged per column for parity, a no-op today because no produced model carries a noted vocabulary.

**A separate tool rather than a flag on `describe_table`, and this is the design decision.** The
brief asked for the do-not-author signal to be *structural rather than advisory*. Extending
`describe_table` would have had to answer three fields whose entire subject is authoring —
`requirements` (what you must supply), `redundancy_bearing` and `attestation_bearing` (which cells
you must reason out independently) — with empty values, and an empty `requirements` reads as *no
requirements* rather than as *the question does not apply*. Worse, `redundancy_bearing` is a global
map narrowed to a table's columns, so a produced table carrying `chrom` would have been told to
hand-author it, which is the opposite of true.

So the separation is the signal, in four places at once: a produced table has no template, no
linter and no requirements answer; its answer model carries `hand_authored: Literal[False]` where
`TableDescription` now carries `Literal[True]`, so the distinction is in the *schema* an agent reads
before calling; and the four authoring routes (`describe_table`, `table_requirements`,
`get_template`, `lint_rows`, plus `scaffold_module`) redirect by name instead of calling the file
unknown. `refusal` states what a hand-written cell costs: the passes merge rather than overwrite, so
it survives every later run wearing the source's authority, and no check asks where a value came
from.

**`licensing.csv` gets none of that treatment, and the exemption is derived.** It is refused by
`describe_machine_table` — under both spellings — with a pointer back to `describe_table`, because
it is a fact sidecar that a human writes. The rule is `in the produced roster AND in
draft.DRAFTABLE`, computed, so nothing has to remember it.

**Deliberately not built.** No write path, no template, no linter for these tables, and no
`table_requirements` equivalent: requiredness is a question about authoring. Nothing was added to
`hints`-style refusal wording upstream either — the redirect is ours, in `_shared.known_kind`, which
every authoring route already funnels through.

**The dossiers in `skills/` now claim the opposite in about eight places** (each fact table's
reference says `describe_table` refuses it and quotes the old wording). A parallel session owns
`skills/`; the list was handed to them rather than edited here.

---

## RM13 — every generated schema answer names the toolchain that produced it

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**Why it was high.** A stale plugin cache serves a stale toolchain silently, and every
skill on this surface tells an agent to *ask the tool, never memory*. Measured: the
cache at 0.7.0 was serving format 0.5.4, so `describe_table("activity_phenotype.csv")`
answered with 11 columns where the installed 0.6.1 has 14 — a wrong answer, delivered
with the same confidence as a right one, from the tool the rule points at. Nothing in
the payload distinguished the two, so the rule was unreliable in exactly the case it
exists for.

**What shipped.** `_shared.schema_versions()` — one source for the whole surface, read
from `importlib.metadata` — and a `produced_by: SchemaVersions` field carrying
`format_version` and `compiler_version` on `list_tables`, `describe_table`,
`table_requirements` and `get_template`. `authoring_reference` carries the same pair as
a `produced_by` key inside its JSON, in both the summary and the `schemas=True` form.
The `resource://just-dna/tables` resource ends with the same line in prose.

**The compiler is stamped beside the format, and that is not padding.** The table
roster, the requirement shapes, the templates and the redundancy/attestation maps all
come from `just_dna_compiler.draft` / `hints` / `scaffold` — the compiler's projection
of the format's models. Since 0.6 the two no longer move in lockstep, so a skew in
either package moves these answers and one version cannot describe them.

**Read once at import, and the cache is correctness rather than speed.** A running
process keeps the modules it already imported; re-reading package metadata per call
would report the *new* distribution the moment anything upgrades the environment under
a live stdio server, while the answers still came from the old imported code. Reading at
import makes the stamp describe the code that actually produced the answer, which is the
only thing worth stamping. The RM13 text said "at call time"; that would have made the
stamp lie in precisely the scenario it is for.

**`authoring_reference` keeps returning a JSON string.** Around thirty dossiers document
the access path `authoring_reference()["models"][...]`, so a wrapper model would have
broken every one of them to add a field. The stamp goes in as a top-level key of a
shallow copy — upstream's dict is not ours to mutate — and cannot collide in either
form: the summary form's keys are fixed, and the `schemas=True` form's are CamelCase
model names.

**`server.INSTRUCTIONS` was fixed in the same change**, because it hardcoded
`(format 0.5)` while the installed format was 0.6.1 — a literal version, which §2
forbids for this exact reason, and the candidate fix `F19` and `F26` both named as the
*stronger* one: instructions are in front of an agent before the first call, where a tool field has
to be asked for. It now names the live format and compiler from the same helper.

**What was deliberately left unstamped.** `lint_rows`, `validate_module` and
`compile_module` are verdicts about a directory at a moment, not schema knowledge an
agent carries forward, and a compile is already stamped upstream inside `manifest.json`
— the catalog's one module still reads `just-dna-compiler 0.5.1` off exactly that field.
`list_tables`' hardcoded `sidecars` literal and `_SUBJECTS` were left alone too: they are
**RM10**, still open, and a stamp on a restated fact would only date the restatement.

## RM8 — the registry client surface is wrapped

**Shipped:** 2026-08-12 in 0.8.0

Four releases of `RegistryClient` had gone unwrapped since we adopted 0.12.0 for the
test/prod split. The precondition was registry 0.13.0 on PyPI, so
`would_publish_module_level` could be *wrapped* rather than feature-detected; it landed
2026-08-11 and this followed.

**What shipped, and the shape it took.** Two gated pre-flights and two ungated reads:

- **`registry_validate`** — the server's own module-level gates, including the two a
  local `validate_module` cannot know: whether `module.name` matches the path, and
  whether identical authored data is already published under some other name.
- **`registry_check`** — the full dry run, `F11`'s other half. This is what turns
  "rehearse the publish" into "ask whether it would publish" **without spending a
  version number**, which on production is irreversible.
- **`registry_is_published`** — ungated and needs no upload: the content signature is
  computed locally, so an author can ask "is this data already out there, under any
  name" before they have a token.
- **`registry_health`** — reports the instance's own mode, so a rehearsal can be
  *confirmed* rather than assumed. `expect_mode` (shipped in 0.7.0) already refuses a
  mismatch; this is how you see it before it matters.

**One bullet turned out to be already done.** RM8 listed `content_signature`, but
`module_signature` has always called `just_dna_compiler.compiler.content_signature` —
the same function the client method wraps. Wrapping the client's would have been a
second path to one answer, so `registry_is_published` calls the compiler directly and
sends only the resulting signature.

**One bullet is deliberately not done.** `issue_jwt_token` returns 501 unless the
deployment configures a signing secret, and nothing in this surface consumes a JWT —
every call authenticates with the registry token. A tool that is usually a 501 and
useful to nobody here is worse than no tool.

**Where the design work actually was: not letting a skip look like a verdict.** Both
pre-flights return one `PublishPreflight`, and it carries *two* verdicts on purpose:

- `module_level_clear` is upstream's `would_publish_module_level`, renamed so nothing
  reads it as a green light — it composes exactly three gates and excludes the network
  tier entirely.
- `verdict` is the whole dry run, and it is **`None` whenever the tier did not run** —
  on a bare validate, on `skipped_reason`, and when no token was resolvable. Defaulting
  it to `False` would let "we could not ask" arrive shaped like "would not publish",
  which is the same error as a skip producing a pass, one sign flipped.

`rerun_rather_than_fix` carries the `S20` distinction all the way to the author's next
action: a false verdict beside unreachable rsIDs means *re-run*, not *go fix your
spec*, because a strict publish against an unreachable Ensembl really does refuse while
the variants may be perfectly findable. Telling an author to fix that is how real rows
get deleted.

`unchecked` and `non_blocking` keep the distinctions upstream is careful about — a
`clin_sig` check the operator has no snapshot for never blocks and is never dropped
either, and identifier findings never move the verdict because a publish does not run
that pass, so a finding predicts nothing about one.

**Verified live against the polygon**, not just in the suite: a clean `assets/fto_bmi`
returned `verdict: true` in 1.3s, and the same spec with one invalid `state` returned
`verdict: null` with `verdict_unavailable: "invalid_spec"` — null rather than false,
which is the whole point.

## The essentials tier was defined by the wrong axis

**Shipped:** 2026-08-11 in 0.4.0 · *"If you find essentials surface lacking
before I even started, maybe reconsider the essential stack?"*

Never a numbered roadmap item — it arrived as a dogfooding observation (the
default tier could not verify a trait CURIE) and was widened into a rule change
because the survey found the observation was a symptom.

The old rule, *essentials = everything that only reads, plus the ClinVar draft*,
was false in both directions: `scaffold_module` and `compile_module` write and
were always in it, and six read-only tools were not. The decisive case was
`enrich_module` — extended-only while being step 6 of the workflow the server's
own `INSTRUCTIONS` teach. **A tier that teaches a step it cannot run is the
failure mode**, and it is now asserted rather than remembered: a test parses the
tool names out of that instruction text and requires all of them in essentials.

The replacement axis is **cost**: essentials is everything bounded by what the
caller named (one identifier, one paper, one spec directory); extended is what a
corpus sizes, plus reading back somebody else's artifact. Nine tools moved in,
none moved out.

**The scope decision was the user's**, and it went wider than the recommendation.
The proposal was the three tools that closed the gap; the answer was "6 +
fulltexts + lookup_openaccess + enrich which can be useful for common snip
modules" — reading the tier from the perspective of the module people actually
write first, which is what surfaced `enrich_module` as the real defect.

## RM3 — signing is unwrapped

**Deferred:** 2026-08-11 · *"signing thing is a prototype rather than a real
thing. Currently the registry is the authority and gives out identity keys."*

`keygen` / `sign` stay CLI-only, and not for the key-hygiene reason this item
originally gave. The reason is that **module identity is the registry's**: it
stamps `namespace`, `owner`, `version` and `canonical_id` on publish and
overrides anything authored (upstream `S1` documents this). Ed25519 signing sits
beside that as a prototype of a second, author-held identity scheme, and wrapping
a prototype would give it a durability its design has not earned.

`keygen` writing an unencrypted PKCS#8 key remains true and remains a reason not
to have an agent generate one on its own initiative, but it is now the second
argument rather than the first.

**What came out of this instead**, because it is the half that mattered: the
registry hands back the authoritative identity on publish and `registry_publish`
was returning it in a message and dropping it. It now writes a `published.json`
receipt beside the spec — the identity keys, the digest, the content signature and
an ISO-8601 UTC timestamp — because a receipt that does not survive the session is
not a record, and it cannot live in `module_spec.yaml` where `extra="forbid"`
rejects those exact keys.

**Reopens if** author-held signing stops being a prototype.

## RM4 — nothing verifies `enrich_module` or `registry_publish` end to end

**Reclassified:** 2026-08-11 · *"RM4 is a dogfooding run."*

Correct, and it was mis-filed. This was never a thing to build — it is a probe to
run, and a probe belongs in [dogfooding.md](dogfooding.md) under "Probes not yet
run", where it now is. Keeping it on the roadmap implied a deliverable and made
the roadmap look longer than the work.

The substance is unchanged: the offline ceiling keeps the suite hermetic, so
neither tool can be a normal test. What fits is a marked, opt-in integration run
plus authoring a small real module all the way through.

---

## RM1 — the drafting path is unwrapped, so the authoring loop has a hole in the middle

**Shipped:** 2026-08-11 · `draft_from_clinvar` (essentials), `draft_from_cpic` and
`draft_from_clinpgx` (extended), in `tools/passes.py`.

The skill taught `scaffold -> draft -> curate -> ...` and `draft` was CLI-only, so
an agent left the tool surface at step 2 and came back at step 4.

**Its stated difficulty was stale and is worth recording as such.** RM1 said
wrapping was hard because `draft` "refuses and lists the choices when a
`(phenotype, drug)` pair spans several populations". Upstream removed that in
0.5.1: `DiplotypeRow.clinical_context` keeps the settings as distinct rows and
the consumer picks at query time, so `population` is now a plain filter. Our own
`SKILL.md` and `DOMAIN.md` still claimed the old behaviour and were corrected in
the same change.

What *did* constrain the design was licensing, and that part held: `use` is
required with no default on all three tools, enforced at the schema layer, and a
licence refusal comes back as `skipped=true` with its reason rather than as a
failure — because a failure invites retrying with a different `use`, which is
fabricating a licence position to get data.

Three tools rather than one with a `source` argument: the upstream signatures
share almost nothing, and a merged tool would carry twelve arguments most of
which are inapplicable per source. `lookup_identifier(kind=...)` merges because
both kinds take the same pair; these do not.

## RM2 — the fact passes are unwrapped

**Shipped:** 2026-08-11 · `enrich_facts` (frequencies, gene_metrics, dosage) and
`enrich_literature_pass`, both extended and both background tasks.

One tool for the three sidecar passes because they share a shape — spec in,
sidecar out — and `dosage` writes onto `gene_metrics.csv` rather than a file of
its own. `use` applies only to `dosage`, so the result names where it landed in
`declared_use_applied_to` rather than letting the argument look universally
meaningful. That remains the softest seam in the design.

`enrich_literature_pass` stayed separate: it is keyed on `studies.csv` rather
than on variants, and its answer is a coverage sentence rather than a row count.

## RM5 — `lint_rows` promises refusals it does not currently produce

**Shipped:** 2026-08-11 · docstring and field description narrowed.

Resolved by narrowing the promise rather than by synthesizing alterations
upstream never made: `to_alterations` exists to carry upstream's distinctions
field-for-field, not to fabricate them. The docstring now says where the
redundancy-bearing columns actually appear on this tool — as `info` findings —
and that refusals come from the lookup tools.

Recorded as **F2**, now in [previous_issues.md](previous_issues.md).
