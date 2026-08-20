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

## RM6 — two literature parsers have no fixture, so nothing tests them

**Severity:** medium · **Status:** open · **Owner:** unassigned

`parse_semantic_scholar` and `parse_arxiv` are exercised by nothing. Every other
parser has a real captured payload under `assets/literature/`; these two do not,
because both services answer HTTP 429 to this machine's IP regardless of
user-agent or pacing — arXiv on a first request with no prior traffic, confirmed
with plain `curl` outside the client.

The block itself is not a defect anywhere and not ours to fix. **The untested
parser is ours**, and a parser with no test breaks silently when the API shape
moves.

Two ways out, not exclusive: capture the fixtures from a host that is not
blocked, or set `S2_API_KEY` — Semantic Scholar's keyed pool is not the one being
throttled — and capture at least that half. Recorded as **F6** in
[dogfooding.md](dogfooding.md).

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
understood. Either the check tools move out of that module, or the promise is narrowed
to "writes no authored cell", which is upstream's own wording and is the narrower claim
that actually matters. Do not do this by quietly making the promise false.

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
> 1. **`refresh_sidecar` reading the records.** The capture is keyed by `(variant_key, field)`, which
>    fits `variants.csv` and not a sidecar keyed by gene or by locus. Mapping a sidecar subject onto a
>    record subject is a design question that only came into existence once the capture did, so it was
>    not settled at 3 a.m. Both docstrings in `refresh.py` now state the narrowed reason rather than the
>    old "the log is empty".
> 2. **The grading recommendations** (item 4 below) — skill-side, and they belong with a real corpus of
>    overrides rather than invented ahead of one.
> 3. **`S52`'s answer**, which is upstream's and decides whether a check downgrades a mismatch.

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

## RM15 — we absorbed the format layer's philosophy wholesale, and it is load-bearing in 19 files

**Severity: HIGH** · **Status:** audit complete; narrowed to the residue below · **Owner:** agent A · **Opened** 2026-08-20

> **Done, 2026-08-20 night run.** All three "done when" conditions are met for every surface this item
> named. `server.INSTRUCTIONS` rewritten (rule 2 replaced; a new rule 3 carries the lag hazard) and it
> agrees with `CLAUDE.md` §2. All sixteen §2 domain bullets judged — thirteen stand, "never widen the
> write surface" split, the `provenance_quote` prohibition reversed. Code surfaces re-justified
> (`models.py`, `_shared.py`, `research.py`, `authoring.py`); `refresh.py` audited as *conditional*
> physics — it is two data points because we keep no third, and a filled log settles it. Skills swept:
> `module-101` realigned, the ten scaffold seeds disarmed, `create-module`'s last prohibition removed,
> seven slogan sites and five "a human read it" sites corrected. **§1's questionnaire ran with the
> owner; the attestation contradiction is settled and recorded in §10 — do not re-open it.** Filed
> upstream as `S54`/`S55`, tracked as `F42`/`F43`.
>
> **The residue is closed, 2026-08-20 later the same night.**
> `docs/DESIGN-version-compare.md` — the one surface this item named that had not been read — has had
> the pass. Two sites: §3.6's heading was the retired stance, and the reason a comparator refuses is
> its own (**pairing two rows is an assertion** that two directory listings cannot support); and the
> changelog refusal argued by analogy to a machine-located quote, which is now the legitimate act. The
> refusal survives on a sharper distinction — a located quote is a found passage a check can test, a
> generated changelog sentence is a claim about **motive** that nothing can test.
>
> Three of the four "create-module is stale" dossier claims were resolved when that skill was
> dismantled: two described a pre-0.6 claim already corrected, and the third is now carried as a
> ROADWORKS in `module-curate`. **`RM15` may be closed.** The one unreproduced report of
> `describe_table` returning a 0.5 shape under 0.6.1 still stands and is not this item's.
>
> The three delegated files landed and were then swept against the same stance grep: `find-evidence`
> and `studies.md` were already correct, `literature.md` still carried the reversed proposition live
> and is fixed. The six contradicted dossier banners are all fixed; of the four "create-module is
> stale" claims, one was checked and was largely a false alarm, three remain. One unreproduced report
> of `describe_table` returning a 0.5 shape under 0.6.1 stands.
>
> The **discriminator** this item was blocking is now specified in part: `INSTRUCTIONS` rule 3 and §2
> state it, upstream `S52` is the mask's schema half, and what remains is the record — RM16's capture.
> The auto-correct rulebook stays unpopulated on purpose; it is built from real transcripts, not
> designed.

> **Progress, 2026-08-20.** `server.INSTRUCTIONS` rewritten (rule 2 replaced, a new rule 3 for the
> lag hazard). All sixteen `CLAUDE.md` §2 bullets judged — thirteen stand, "never widen the write
> surface" split, the `provenance_quote` prohibition reversed. Code surfaces re-justified
> (`models.py`, `_shared.py`, `research.py`, `authoring.py`'s `_MACHINE_REFUSAL`), `refresh.py`
> audited as *conditional* physics. **§1's questionnaire ran with the owner and the attestation
> contradiction is settled** — recorded in §10; do not re-open it. Filed upstream as `S54`/`S55`,
> tracked as `F42`/`F43`. The skills sweep landed too, and the verdicts that guided it are absorbed
> into this entry, `CLAUDE.md` §2/§10/§11 and `CHANGELOG.md`; the relay file they were written in is
> retired, and stays readable in `git log`.

**This is an audit item, not a code change.** Nothing here is known to be wrong yet. What is known is
that a stance was adopted without ever being tested against this layer's own purpose, and it then
propagated into the surface an agent reads first.

### What happened

`report, never repair` is `just-dna-format`'s stance and is **correct for that layer**: the compiler
cannot record who decided a value, so writing one would launder a machine's guess as an author's
judgement. This repo adopted it as a **non-negotiable of its own** — §2, `server.INSTRUCTIONS` rule 2,
and from there into fourteen skills and four table dossiers.

The user's correction, 2026-08-20: *"report-never-repair is format's stance, correct for that layer:
they delegate business decision to us here; we're more high-level user-facing app level, we have a
counterstance."* §2 now states the counterstance — we may write, every authoring move is logged, and
the agent is owed a discriminator.

**Flipping one bullet does not undo the propagation.** The stance is quoted, argued and built on
across the surface, and each instance has to be read on its own terms.

### The test to apply to each instance

For every rule, refusal and piece of prose below, decide which of three it is:

1. **Physics** — true at any layer, keep. *A check that could not run is not a check that passed.*
   *A determinism gate is not a correctness gate.* `None` is not `False`.
2. **Format's policy, correctly ours too** — keep, but say **why it is ours**, not "because upstream
   does it". A rule whose only justification is another layer's stance is the defect this item is about.
3. **Format's policy that we should NOT hold** — replace with the counterstance, and follow it through
   to the tool behaviour, not just the prose.

**And the deeper correction the pivot came with, which changes what "safe" means.** The vacuity
argument — *fill `clin_sig` from ClinVar, then a check compares the two and agrees with itself* — is
true but shallow, and reading only it is how the stance survived unexamined. The real hazard is that
**the source lags the edge**: an article is retracted, meta-research refutes the conclusion. So *"your
row disagrees with ClinVar"* is not a defect report; it may be the module being right and current while
the archive is stale, and an agent that silently conforms the row **degrades** the module while the
check reports green. Every instance below should be re-read against *that* hazard, which several of
them do not mention at all.

### Surfaces to read, most load-bearing first

- **`src/just_module_creator/server.py` — `INSTRUCTIONS` rule 2.** *"Lookups show you a value and
  refuse to write it into an authored cell… Those refusals are the feature."* This is the **first thing
  an agent reads**, before any tool call, and it now contradicts §2.
- **`CLAUDE.md` §2, "the domain rules this server exists to enforce".** Every bullet, against the
  three-way test. Named individually because they are not all the same kind:
  - *never fill a value from the same source that checks it* — the vacuity rule. Physics or policy?
  - *never let a tool write a checked value from a lookup* — already flipped in §2; check that the
    flip is coherent with the rest of the section.
  - *never extract a passage from a document a tool fetched* — **see the contradiction below.**
  - *never collapse unknown into a boolean*, *never treat a determinism gate as a correctness gate*,
    *never silently fall back* — these look like physics; confirm rather than assume.
- **Fourteen skills and four dossiers** carry the stance as instruction to an author or an agent:
  `module-101`, `create-module`, `module-check`, `module-close`, `module-compile`, `module-consumer`,
  `module-curate`, `module-draft`, `module-enrich`, `module-publish`, `module-start`, `module-weights`,
  plus `module-tables/references/{studies,gwas_effects,pharm_variants,repeat_alleles}.md`. Several
  frame a refusal as a **feature**, which is exactly the framing under review.
- **`models.py` field descriptions and every lookup tool's docstring.** An agent reads these as the
  contract. A description that says a tool refuses on principle is a behavioural claim.
- **`tools/refresh.py`** — written 2026-08-20 *from a brief that cited the old stance*, so it inherited
  it by construction rather than by decision.

### The contradiction this audit must resolve, and it needs §1

**§2 forbids extracting a passage from a fetched document; §10 records the user saying the opposite
about who can read a paper.**

- §2: *"Never extract a passage from a document a tool fetched… a machine-located quote asserts a
  reading that never happened, which is a false claim of provenance."*
- §10: *"Here you kinda ask v2 work from a wrong person"* — asking a gardener for a
  `provenance_quote` is a reviewer's job and a different person's — and, flatly, **"AI totaly can
  read articles."**

Under the pivot these cannot both stand as written. If the agent is a legitimate reader, a located
quote is a reading that *did* happen, and the attestation question becomes *whose* reading was
recorded rather than whether one occurred. **Run §1's questionnaire; do not resolve this by
inference** — it is the highest-stakes instance of exactly the absorption this item is about, and
`hints.ATTESTATION_BEARING` shipped upstream on the argument now in question.

### What this unblocks

The **discriminator** (§2 part 3) cannot be specified until this read is done — it is the thing that
tells an evident auto-correction from a judgement call, and its shape depends on which refusals
survive. The auto-correct rulebook (§10, *to-populate-later*) waits on the same answer.

### Done when

Every surface above carries a rule that is justified **from this layer's own purpose**, with no
prohibition standing only on "upstream does it that way"; `server.INSTRUCTIONS` and §2 agree; the
§1 questionnaire on the attestation contradiction has been run and its answer recorded in §10.

---


---

## RM18 — the four published modules carry decisions only their owner can make

**Severity:** medium · **Status:** open · **Owner:** **the repo owner, not an agent** · **Opened** 2026-08-20

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

**A third question from the same file is answered and recorded**: `create-module` did not survive as a
thin index — it was deleted, and `CLAUDE.md` says why.

---

## Owed to `just-dna-lite`, and not yet packaged

Every one of the 24 dossiers carries a `## Blanks for just-dna-lite` section naming, with `path:line`,
each read site that exists and each that does not. **That set is the hand-off** — it turns "annotation
is behind the tables" into a list of individually small asks — and it has never been packaged as one.

Lead with `licensing.csv`: it is read properly, with tests, which is what shows the gap is *"nobody
asked for the other six"* rather than *"the consumer ignores everything"*.
