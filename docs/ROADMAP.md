# Roadmap

Active-only, forward-only. One `## RMn — name` per **open** item. Shipped and
deferred items move to [ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) with their
rationale; nothing is deleted, only relocated.

**An item belongs here only if the work is ours.** A gap whose fix lives in
`just-dna-format` / `-compiler` / `-enricher` / `-registry` is filed upstream as
an `S<n>` and tracked in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md) as an
`F<n>` — never as a roadmap item, because putting it here says we intend to build
something and invites a workaround where a note was owed. A probe belongs in
[dogfooding.md](dogfooding.md), not here.

---

## RM9 — a module authored only through this server carries no check attestation

**Severity:** medium · **Status:** open · **Owner:** unassigned

Format 0.6 made `verification.json` a real surface: the registry projects a
`verification` block onto the module page, and a record says *the question was put*
rather than *the answer was clean*. The enricher writes those records from its
**CLI commands** — `check-identifiers` and `check-acmg` do it unconditionally, with
no flag, precisely so that "not run" and "ran and found nothing" stop reading alike.

The underlying functions do not, and the functions are what we call. So `close_module`
is the only thing on this surface that writes into `verification.json`, and a module
authored entirely through these tools shows nothing where a CLI-driven author's module
shows two records. That is the `F33` shape again — our own pin being what keeps an
author off a surface that exists.

It is not a missing upstream API: `identifiers.verification_records()` and
`verification.merge_records()` are both public, and `close_module` already proves the
write path works from here. What has to be decided first is a policy question, because
`tools/research.py` opens by promising that **no tool in it writes to a spec directory**
— a line that is currently true and load-bearing for how the read-only tier is
understood.

> **Decided 2026-08-20: the check tools move out.** Not the narrowed promise. A module whose
> opening sentence is a literal claim keeps it literal, and the boundary then means something a
> reader can rely on rather than something qualified by an exception. The tier line is cost, not
> read-versus-write, so nothing about the tiers moves with them — they stay essentials.
>
> **Reversal recipe:** if the split ever reads as ceremony, narrow the promise to "writes no
> authored cell" (upstream's own wording) and move them back. What must not happen either way is
> the promise quietly becoming false while the sentence stays.

---

## Idea book

Freeform, unscheduled, no commitment implied.

- A `module_diff` tool: two spec directories in, the authored rows that differ
  out. `module_signature` answers *whether* two specs differ but not *where*, and
  "diff the tables" is the standing advice whenever a digest moves without an
  intended content change.
- Surfacing `hints.REDUNDANCY_BEARING` as a resource rather than only as a field
  on `describe_table`, so an agent can read the whole list once instead of per table.

---

## RM16 — capture the outrank reason, and write `provenance.json` (absorbs RM14)

**Severity:** high · **Status:** **the capture shipped 2026-08-20 (night run); the residue below is open** · **Owner:** agent B · **Opened** 2026-08-20

> **Shipped.** `src/just_module_creator/overrides.py` plus two essentials tools,
> `record_override` and `review_queue`, with 15 tests.
>
> - **`provenance.json` is written in upstream's own shape** — `ProvenanceDoc` / `ProvenanceItem`,
>   recognised by the registry, outside `artifact.digest`. An item already there that is **not** ours is
>   kept and reported, never rewritten.
> - **Per-field, inside a per-row schema.** One item per `(variant_key, field)` — their `items` list has
>   no uniqueness rule — with the machine fields in a marker appended to `rationale`. So the per-field
>   record **travels with the module** rather than sitting in a local cache a second author would never
>   see, and it re-emits into whatever shape `S52` settles on. That was the open question this entry
>   said not to design around; this designs around *today's schema* instead of around a guess.
> - **Bound by digest to the value it justifies**, so a later edit to the cell makes the record stale by
>   construction rather than carrying an old reason onto a new value.
> - **The move is logged** to `logs/authoring.log`, which is swept up by every compile and published
>   with no opt-out — the surface §2 requires, and it now has its first writer. Nothing absolute-path or
>   credential-shaped goes into it, because it publishes verbatim.
> - **The terminal state is detected** where it can be, offline: `review_queue` reads
>   `clinical_assertions.csv` and reports `resolved` when the archive has caught up — the only evidence
>   in this format that an authored judgement was later vindicated. Everything else is `unknown`, which
>   is **not** agreement, and it says so.
> - **It produces no pass.** A record downgrades nothing and silences nothing.
>
> **What is left, and why each is left:**
>
> 1. **`refresh_sidecar` reading the records.** **Answered 2026-08-20, and the answer was that the
>    question was wrong — see the architecture note directly below.** The capture is keyed by
>    `(variant_key, field)`, which fits `variants.csv` and not a sidecar keyed by gene or by locus.
>    Both docstrings in `refresh.py` state the narrowed reason rather than the old "the log is empty".
> 2. **The grading recommendations** (item 4 below) — skill-side, and they belong with a real corpus of
>    overrides rather than invented ahead of one.
> 3. **`S52`'s answer**, which is upstream's and decides whether a check downgrades a mismatch.

### The architecture changed, 2026-08-20 — an overlay, not a wider key

**The owner's call, and it dissolves the residue rather than answering it:** *"editing the derived
schemas, although feasible technically, shouldn't be a preferred way of action; I see an authored
table like 'override masks' that just lies upon any of the derived tables. This separates concern.
Authored stays authored, derived stays derived, no complex logic, no schema bends, no redraft
problem, a whole subgenre of bugs — gone."*

**Why the residue was unanswerable as posed.** RM16 demanded one shared representation because it
treated two different objects as one. The case it was written for — `variants.csv` says Benign,
ClinVar says Pathogenic — is an **authored** cell, and an authored cell survives re-derivation *by
construction*: nothing re-derives a table you wrote, which `check_sidecar` refuses outright. That
case never needed a mask. It needed a **reason**. A mask is only ever needed where a human edits a
**derived** cell — and the right answer there is that they should not, ever.

**What follows.** Derived tables become `f(source, overlay)`. `refresh_sidecar`'s refusal stops being
necessary rather than being satisfied: its "two data points and three explanations" has a third
explanation only because a human may have edited the file, and under an overlay nobody does. So a
difference between two derivations means the source revised, full stop.

**Filed as format-tree `S60`, tracked here as `F57`, and asked of their COMPILER rather than built
here** — the owner's call again: *"large yes, 0.7 yes, yet it's their bread."* The argument that makes
it theirs is that an overlay is **authored input, not a repair**: a compiler reading it does what it
already does with every other authored table, so report-never-repair is not at stake. If each
downstream tool applied its own overlay instead, two consumers compiling one spec directory could
disagree about what the module says and the artifact would stop being a function of the spec.

**`S60` depends on `S51`** (`F41`) — an overlay's subject must name a derived row exactly and the
per-table merge key is not public. Deriving it is fine for classifying and not fine for a persisted
key.

**What this repo does meanwhile: nothing new.** `record_override` and `review_queue` stay exactly as
shipped, narrowed in purpose to the **authored** cell that outranks a source, which is the job
`provenance.json` reads like it was designed for. We deliberately do **not** invent an
`overrides.csv` in the spec directory — absent from `specfiles.RECOGNIZED_SPEC_FILES`, so a
server-side rebuild would drop it silently, the way `licensing.csv` was lost before registry 0.16.2.

---

**Supersedes RM14** (*"`provenance.json` is recognised by the registry and by nothing here"*), which
was the same gap seen from the wrong end. RM14 read as a tidiness item — a recognised file nothing
touches. It is actually the missing half of the counterstance.

### Why this is high rather than low

§2 now says we may write and revise, and that **the agent needs a discriminator** for when editing
against a source is right. The hazard is not vacuity, it is that **the source lags the edge**: a
retraction, a refuting meta-analysis, a reclassification ClinVar has not absorbed. So an override may
be the module being *more* current than the archive — and today **nothing records that judgement
anywhere.** The value changes, the cross-check warns, and no one can tell a considered outrank from a
careless overwrite.

**Outranking cannot be formalized and should not be.** An evidence-grading pyramid exists, but which of
a retraction, a meta-analysis and a single larger cohort outranks an archive call is a natural-language
judgement — *"only a natlang agent can really judge here (human or ai or a tandem)"*. So the instrument
is **a set of recommendations plus a freeform record**, not a vocabulary.

### The substrate exists upstream and is unused

`just_dna_format.manifest.ProvenanceItem` already carries `variant_key`, `rationale` (*"Why this
annotation was made"*), `reviewer_verdict`, `confidence` and `human_reviewed`, under a header with
`generator`, `model` (*"Model id, if AI-authored"*) and `agent_version`. It is explicitly AI-aware, it
is in the registry's `RECOGNIZED_SPEC_FILES` so it survives a rebuild, and it is hashed like a log and
kept out of `artifact.digest` — so writing one costs no identity.

**Nothing reads it.** `compiler._collect_provenance` validates, copies, hashes and returns a summary;
from the items it takes `len(doc.items)` and no field. Verified by grep across `compiler/src` and
`enricher/src`: two hits, the import and one `model_validate_json`.

### Ours to build

1. ~~**Write `provenance.json`** in upstream's existing shape.~~ **Done** — `record_override`.
2. **Capture the outrank reason at the moment of the override** — when an agent or author changes a
   checked value against what a source says, the reason is recorded then, not reconstructed later.
3. **Log the move** into the `logs/` subtree as well, per §2 part 2: every authoring move that goes
   through a tool gets logged, and a move made by hand should be routed through a skill so it is.
4. **Ship the recommendations** — the grading guidance an agent weighs a source against. Skill-side.

### Not ours

Whether a **check changes severity** on the presence of a record — the *"mismatch + outrank reason →
INFO on the field rather than WARNING"* shape — is a contract question and is filed as format-tree
**`S52`**. Do not implement a severity change here; we do not own their check. Build the capture
regardless, because a record read by humans only is still better than a changed value with no record.

### Known open question, inherited from S52

`rationale` is **one string per `variant_key`** and an outrank is naturally **per field** — a row may
outrank ClinVar on `clin_sig` while its `direction` is ordinary. Three shapes are on the table upstream
(a per-field map, a `field` on the item, or accepting row-level bluntness) and we asked them to pick,
since it is their document. **Do not design our writer around a guess** — write what today's schema
allows, and keep the capture's internal representation per-field so it can be emitted either way.

### The two pathways — this is the discriminator's specification

Both start identically. **They diverge only afterwards, which is why no check can tell them apart at
the moment of the mismatch:**

```
1  hallucination, or an author's stale knowledge
     -> erroneously authored item -> check -> MISMATCH -> WARN
     -> the agent sees the flag and corrects the item          <- the warning did its job

2  the module is right and the archive is stale
     -> item corrected -> check -> MISMATCH -> WARN
     -> reasoning provided -> no longer warns on this row
     -> the edit is preserved as a MASK across re-revisions
     -> eventually the source catches up and the mismatch disappears
```

**Three requirements fall out, and all three are ours:**

- **The record is a response to a warning, never a filter filed ahead of one.** An author must not be
  able to mark a row outranked *before* the mismatch is reported, or pathway 1 loses the only signal
  that catches it. So the capture point is "an agent or author is reacting to a reported mismatch", not
  "an author is editing a cell".
- **The edit must survive re-revision as a mask.** *"Such edits are the highest value manual overrides,
  so we need to tread around them carefully."* This is the **same mask** the sidecar-refresh work
  captures — an outranking edit is precisely the hand-curated row a delete-and-re-derive would discard.
  The two must share one representation rather than growing two.
- **Detect the terminal state.** Pathway 2 ends with the source catching up. **An outrank whose mismatch
  has since resolved is an outrank that turned out to be right** — a trust signal available nowhere else,
  and free, because the check already runs every compile. A resolved record is retirable; one standing
  across several source releases is worth aging, because it is either a genuine standing disagreement or
  a stale correction nobody revisited, and a human decides which. And a record whose authored value has
  changed *again* is stale by construction — the same shape as the attestation binding, so it probably
  wants to be hash-bound to the value it justifies.

**What none of this may do is produce a pass.** "No longer warns" means downgraded and still visible.
A row where the module and the archive disagree stays interesting forever; the record says who decided
and why, it does not make the disagreement go away.

### Standing visibility, and the re-review queue it feeds

**An outranked row is never silent — warn or info, always highlighted.** The reason is time, not
policy: *"easy to forget as time passes."* The person who wrote the justification understood it; six
months and two source releases later, nobody remembers whether the retraction that motivated it was
itself superseded. A row that stopped reporting is a row nobody will revisit, and the module keeps
asserting a judgement no living person is standing behind.

**So the outranked rows are the FIRST candidates for a re-review**, and that is a concrete deliverable
rather than a sentiment. A review pass (`module-revise`'s review kind) currently has **no priority
list** — a reviewer opens a module and picks somewhere to start. The outrank records are that list, and
they are ranked by construction: a record standing across the most source releases without resolving is
the one most likely to be stale, and a resolved one can be retired on sight.

This is where the pieces meet: the capture (this item) produces the queue, `module-revise` consumes it
as the review pass's starting point, and the terminal-state detection above is what keeps the queue from
growing without bound.

### Done when

A tool writes `provenance.json`; an override through any tool of ours captures its reason **in response
to a reported mismatch** and logs the move; the capture shares one mask representation with the
sidecar-refresh work; a resolved outrank is detected and reported as retirable; the skills carry the
grading recommendations; and `S52`'s answer decides whether a severity change follows upstream.

## RM18 — the four published modules carry decisions only their owner can make

**Severity:** medium · **Status:** open · **Owner:** **the repo owner, not an agent** · **Opened** 2026-08-20

> **Decided 2026-08-20, and it settles the output form.** *"It's not our item. Its output form is a
> handout with proposed solutions: reread articles to iron out discrepancy, get fulltexts, and so on.
> Each item has a more-or-less clear path."* So nothing below is work this repo schedules — the
> deliverable is **prose for Anton**, one item per row-set, each with its route attached. Three
> consequences, and none is optional:
>
> 1. **The skills get patched so nobody steps on the same landmine.** That is the half that *is* ours,
>    and it is where the real repair lives — `authorship` undeclared and title-as-quote both came from
>    a surface that never asked.
> 2. **Republished versions will carry `authorship`.** Whether to **yank** the old ones is Anton's
>    call and nobody else's; a published version is immutable and yank does not touch that.
> 3. **Expose yank in the toolset** — *"if an agent publishes and spots a grave error"*. Tracked as
>    `RM21` below; the client already has `yank`/`unyank` and we wrap neither.
>
> **The quote column, decided:** empty it, keep only the real quotes. The honest reading of a 2–3%
> yield — a sparse column that means something beats a full one that witnesses nothing. The visible
> cost is real and is accepted: coverage drops from apparently-complete to nearly empty.
>
> **`population`, decided:** it is the studied cohort's ancestry. And the follow-through is a
> **finding about us**, not about the module — the enricher already fetches ancestry and nothing here
> surfaces it. Tracked as `RM22`.

Carried out of `docs/HANDOFF-antonkulaga-quotes.md` before that file was deleted. **A published version
is immutable, so none of this is a repair** — each item is a decision about what a *next* version says,
or about whether one is worth cutting at all. Nothing below was touched.

**The rows, most specific first:**

1. **Four rows of `big_five_personality_snps` cite a paper that does not support them.**
   `rs34588274`, `rs3742021`, `rs4245154` and `rs527528` cite PMID `34054130` via GWAS Catalog
   `GCST012111` for `EFO_0009589` (a neuroticism item). The article names all four rsIDs — in a table of
   hits for **sociability**. So exactly one of three is wrong: the trait label, the accession, or the
   PMID. Settling it needs the `GCST012111` record. **This is the finding that justifies the whole
   attestation reversal**: under the retired rule those four rows carried the article's title and looked
   exactly like the other 855, and only going after the actual passage surfaced it.
2. **Three rows of `aggression_anger_snps` are behind a paywall.** `rs11838918`, `rs16891867`,
   `rs7950811` cite PMID `20585324`, whose abstract names only `C1QTNF7` and no rsID. Somebody with
   journal access settles all three in ten minutes; nobody without it can.
3. **`population` holds a citation label rather than a population** in every `aggression_anger_snps`
   row — *"Nagel M et al. — GWAS Catalog GCST006941"*. Flagged and not touched: it is an authored cell
   and the fix is a judgement about what the column is for.
4. **None of the four declares `authorship`.** They are AI-authored and say so nowhere, which is the one
   failure mode a later reviewer cannot detect from the artifact. A prose-only amend cannot fix it —
   `authorship` is inside the spec — so it costs a version.
5. **Whether a quote change is a version at all**, and **whether emptying the column beats leaving a
   title in it.** Both are defensible; the second is the honest reading of a 2–3% yield, and the cost is
   that a module goes from apparently-complete coverage to visibly sparse.

**The two untouched modules, with their budget:** `cognitive_intelligence` (2045 rows, 33 PMIDs) and
`risk_impulsivity` (695 rows, 19 PMIDs). Expect the **low** end of the 2–3% yield on both, because both
are dominated by papers cited for hundreds of variants at once — the three papers grounding the most
rows in the remediated pair named none of them.

**One positive result worth keeping**, and it is stated nowhere else: on all **18** rows where both were
available, every module p-value agreed with its paper's own table to one significant figure.

**The grain decision, if a later pass redoes this:** quote per `(pmid, rsid)`, not per `(pmid, trait)`.
The second degenerates on a single-trait module — every row shares the trait, so one quote covers the
whole file and you have rebuilt the defect under a better name.

---

## RM19 — build `compare_modules` and `compare_to_published`

**Severity:** medium · **Status:** **`compare_modules` shipped 2026-08-20 (night run); `compare_to_published` open** · **Owner:** agent B · **Opened** 2026-08-20

> **Shipped: `compare_modules`.** `src/just_module_creator/compare.py` plus `tools/comparison.py`,
> essentials, offline, with 15 tests built on the `hfe_hemochromatosis` reference example rather than on
> synthetic rows — the design's decisions were measured on that corpus and invented tables would not
> reproduce them.
>
> The cases where the naive answer is wrong all behave as specified, verified against the real module:
> a **row reorder** reports `content: same` and 13 unchanged rows; a **licence edit** reports
> `content: same` with the change under `identity_scope: sources.signature`; a **retyped rsID** reports
> one added and one removed and **zero changed**; a **changed `genome_build`** reports `frame: moved`
> with the note that the clean row counts beneath it are *not comparable*; and the deprecated
> `sources.csv` spelling compares as the same table as `licensing.csv`, reporting each side's spelling.
>
> **One defect found by using it rather than by testing it**: an example whose two cells differ past
> the truncation point rendered as two identical strings, which reads as *the row did not really
> change*. The window is now centred on the first character where the two diverge.
>
> **Still open: `compare_to_published`** — manifest-only, one or two bounded GETs, no download. The
> design specifies it fully; it was not started rather than half-built.

[DESIGN-version-compare.md](DESIGN-version-compare.md) is a completed design study, 699 lines, and its
recommendation is **build it now**. This entry exists because the study had no roadmap item, so its
ranking lived only in a primer that has been deleted.

**Both essentials**, because both are bounded by what the caller named. `compare_modules(left_dir,
right_dir)` is a pure function of two local spec directories — no network, no compile, no parquet;
measured at 0.18 s on the largest reference example. `compare_to_published(spec_dir)` is manifest-only:
one or two bounded GETs and no download, ending by **handing over** the `registry_download` +
`compare_modules` pair rather than escalating to a tier of its own.

**Build `compare_modules` first** — it is useful alone, and the other without it is a signature
comparison with no way to look inside.

Output is a three-level ladder — signature, then table, then rows **grouped by the set of columns that
changed** — with eight named refusals and a three-valued verdict per axis. **Read `genome_build` before
any row count**: when the declared builds differ the comparison is *not comparable* rather than clean,
and the reassuring answer is the dangerous one.

**Nothing waits on an upstream release.** The in-tree additions the study names (`hints.key_fields`,
`hints.DERIVED_TABLE_MODELS`, registry 0.19's per-version `content_signature`) are symbol-gated
improvements, not prerequisites.

**Why it matters beyond convenience:** `module-diff` currently teaches a two-command download-and-diff
recipe that an author in a chat session cannot run without shelling out, and
`test_the_taught_workflow_runs_in_the_default_tier` exists precisely because a tier that teaches a step
it cannot run is the failure mode to watch for.

---

## RM20 — two questions about the skill surface that nobody has answered

**Severity:** low · **Status:** open · **Owner:** unassigned · **Opened** 2026-08-20

Carried out of `docs/HANDOFF-skills-split.md`. Both are cheap, both are reversible, and neither should be
decided by an agent on its own — they are about what the surface *is*, not about what it says.

1. **Does `find-evidence` become `module-evidence`?** Fifteen of the sixteen skills share a `module-`
   prefix and this one does not. Against renaming: the name is the clearest trigger in the set and it
   predates the family. For: an agent scanning a listing groups by prefix.
2. **Do the stage skills also become slash commands (`commands/`)?** This was *the original ask that
   started the split*, and nothing has been added to either manifest. The scaffolds were written
   command-shaped, so the cost is low; the question is whether sixteen commands help or crowd the
   picker.

> **Both answered 2026-08-20.**
>
> **1. `find-evidence` keeps its name, and the principle is inverted.** *"Keep it as find-evidence and
> actually revisit the rest, in terms of not having module-spam."* Applied, the test is **does this
> task exist without a module?** — searching literature, verifying a PMID and reading a paper all do.
> Nothing else in the set passes: eight are lifecycle stages, three are second-pass kinds, and
> `module-101` / `module-tables` / `module-weights` are a module's map, structure and columns. So the
> inconsistency is the naming working. **One borderline recorded rather than decided:**
> `module-consumer` documents the far side of the seam — the join contract, the unobservable-allele
> marker, float32 comparison — and its subject is the consumer's obligations; its own description
> also says *"what an author can do to make a module readable"*, which is what keeps the prefix.
>
> **2. Commands: eight, not sixteen.** *"Up to 8 — find-evidence can be user-requested during the
> creative process; place yourself in user shoes, but keep the surface clean."* A command is what
> somebody **deliberately types to start something**, never a stage an agent walks through:
> `/module-101`, `/module-start`, `/find-evidence`, `/module-tables`, `/module-check`,
> `/module-compile`, `/module-publish`, `/module-revise`. The eight left out — `draft`, `curate`,
> `enrich`, `close`, `refresh`, `diff`, `weights`, `consumer` — are reached from inside a session by
> an agent that already knows where it is. **The one judgement call:** `/module-compile` took the
> last slot over `/module-diff`; compile is usually an agent step between check and publish, while
> diff answers a question a user asks out loud. Swap without argument if it reads wrong in use.
>
> **3. Two meta-skills to add**, both proposed and both answering a question a *stuck* user asks,
> where today the only route is already knowing which skill to load:
> - **`module-status`** — point it at a spec directory, get *where is this module now and what is the
>   next decision*. The lifecycle is spread across eight stage skills and nothing answers it; an agent
>   resuming somebody else's module infers it from which files exist. Its output is the **decision
>   list** §10 asks for, not a diff and not a findings dump.
> - **`module-symptom`** — paste the message, get cause and action. `references/SYMPTOMS.md` already
>   holds the mapping and the only door to it is `module-101` plus knowing to look.
>
> A `module-doctor` was considered and **rejected**: it would overlap `module-check` and split one
> job across two surfaces.

**A third question from the same file is answered and recorded**: `create-module` did not survive as a
thin index — it was deleted, and `CLAUDE.md` says why.

---

## RM21 — a publish that turns out to be wrong has no route back

**Severity:** medium · **Status:** open · **Owner:** unassigned · **Opened** 2026-08-20

*"Expose the yank feature to the toolset if an agent publishes and spots a grave error."* Opened out
of `RM18`, where the question *"does Anton yank the four?"* had no tool behind it either way.

**Nothing upstream is missing.** `RegistryClient.yank` and `.unyank` both exist and we wrap neither.
The semantics are already the right ones for this: yank *"drops the version from default listings and
`latest`, keeps it fetchable"* — so anyone who already installed it keeps verifying, which is exactly
what an immutable registry should do. It is **not** `delete_version`, which is test-instance-only and
does not release the name-independent content claim.

**Why it matters more here than a wrapper usually would.** An agent that publishes is an agent that
can publish a mistake, and right now the discovery of a grave error ends at a dead end with the bad
version still sitting at `latest`. That is `F12`'s shape — the only route to a fix existing outside
the surface that created the need for it.

**Tier and gating:** a registry write, so token-gated, tagged `registry_write`, listed in
`auth.GATED_TOOLS` — no exception applies, since the token is not its output.

**Care to take in the skill, not in the tool.** Yank is not a correction and never repairs anything;
it stops recommending a version. Publishing the fixed version is a separate act, and an agent must not
present a yank as having undone the mistake.

---

## RM22 — the enricher fetches the ancestry that `population` wants, and nothing here surfaces it

**Severity:** low · **Status:** open · **Owner:** unassigned · **Opened** 2026-08-20

Opened out of `RM18` item 3, where `population` in every `aggression_anger_snps` row holds a citation
label rather than a population. The owner's rule decided where it lands: *"file an item into the
enricher if it doesn't provide ancestry data by id; if it provides but is not wired in our tool, it's
our bug to fix in MCP + skills."* **It provides.** So this is ours.

**Measured.** `GwasEffectRow.ancestry` exists and is populated — `gwas.py::_study_facts` reads
`ancestries` out of the GWAS Catalog study payload and `gwas_effect_row` writes it, whenever
`study_facts` is on. Its description: *"The study population, free text as the Catalog records it
('European', 'East Asian', 'Hispanic or Latin American')"*, deliberately free rather than a
vocabulary. `StudyRow.population` is the authored twin, `str | None`, described only as *"Study
population"*. Nothing in `src/just_module_creator/` joins them; our four mentions of ancestry are all
docstrings warning that `--no-study-facts` nulls it.

**So an author writing `studies.csv` after a GWAS pass has the answer sitting in their own module,
in a derived sidecar, and no surface offers it.** The join is `pmid` or `study_accession`, both of
which sit on `GwasEffectRow` and `pmid` on `StudyRow`.

**Surface it; do not fill it.** `population` is **not** in `hints.REDUNDANCY_BEARING` (checked), so
filling it would not be vacuous — but a study carries several ancestries and `ancestry` is a joined
string, so the grain is a judgement and the discriminator says surface. Offer the value, name where
it came from, let the pilot take it.

**The skill half is the other deliverable**, and it is the one that would have prevented `RM18`
item 3: `find-evidence`'s *"Population is where modules overreach"* section tells an author what the
column is not, and cannot yet tell them where the answer already is.

---

## Owed to `just-dna-lite`, and not yet packaged

Every one of the 24 dossiers carries a `## Blanks for just-dna-lite` section naming, with `path:line`,
each read site that exists and each that does not. **That set is the hand-off** — it turns "annotation
is behind the tables" into a list of individually small asks — and it has never been packaged as one.

Lead with `licensing.csv`: it is read properly, with tests, which is what shows the gap is *"nobody
asked for the other six"* rather than *"the consumer ignores everything"*.

> **Decided 2026-08-20: one document into their `docs/`, and no intake.** `just-dna-lite` has no
> `CONSUMER_SUGGESTIONS.md` and setting up a third repo's triage process is not ours to do — the
> split inbox works in the other two because their maintainers run a loop, and nobody has agreed to
> run one here. The cost is accepted: no numbered series, so a reply has nowhere structured to land
> and follow-up happens by conversation.
>
> **Note the count before quoting it.** `CLAUDE.md` says 24 dossiers; **25** files carry a
> `## Blanks for just-dna-lite` section, `LAYOUT.md` among them. State the rule and run the grep
> rather than repeating either number.
