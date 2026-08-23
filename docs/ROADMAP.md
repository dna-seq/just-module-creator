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

## RM16 — capture the outrank reason, and write `provenance.json` (absorbs RM14)

**Severity:** high · **Status:** **the capture shipped 2026-08-20 (night run); the residue below is open** · **Owner:** agent B · **Opened** 2026-08-20

> **Shipped.** `src/just_module_creator/overrides.py` plus two essentials tools,
> `record_override` and `review_queue`, with 15 tests.
>
> - **`provenance.json` is written in upstream's own shape** — `ProvenanceDoc` / `ProvenanceItem`,
>   recognised by the registry, outside `artifact.digest`. An item already there that is **not** ours is
>   kept and reported, never rewritten.
> - **Per-field, and the schema is per-field too since 0.6.5.** `S52` was answered with
>   `ProvenanceItem.outranks` — `{column: why}`, per column because a row may outrank an archive on
>   `clin_sig` while its `direction` is unjustified, and per *variant* because `Provenance.item_count`
>   is a published number meaning *variants carrying a record*. `record_override` writes it, so the
>   column is legible to a reader who is not us. The marker stays and is not a duplicate of it: it
>   carries the digest binding the record to the cell, which source was disagreed with, when and by
>   whom — none of which upstream's schema holds. Still one item per `(variant_key, field)`, since
>   their `items` list has no uniqueness rule.
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
> 3. **Whether a check downgrades a mismatch on the strength of a record.** `S52`'s *field* shipped
>    in 0.6.5; the check half is open as their `RM117`, for two stated reasons — the pre-emption guard
>    is a convention the code cannot see, and a record is not yet bound to the value it justifies on
>    their side. Nothing here assumes it will land: a record downgrades nothing, silences nothing and
>    passes nothing, which was true before the field existed and is still the design.

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

**`S60` depended on `S51`** (`F41`), and that dependency is discharged: `hints.key_fields` shipped in
0.6.5, so a derived row's merge key is public and an overlay's subject can name one exactly rather than
being derived approximately. Upstream's `RM124` reply names the sharp remaining question, and it is one
only `RM115` could expose — `(table, subject, field)` cannot key `resolution.csv`, whose published rule
is `subject`: one rsID legitimately resolves to several loci, so the subject alone does not identify a
row.

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

## RM24 — a third-party client cannot be paced by our gate

**Severity:** low · **Status: DEFERRED 2026-08-20** — owner's call, and it stays here rather than
moving to history because nothing was decided about the substance, only about the timing. Do not open
the upstream issue without asking again. · **Owner:** unassigned · **Opened** 2026-08-20

Falls out of `RM23` and is worth its own line because it survives whichever shape that takes.

**Never open a socket outside `net.py`** exists so pacing, User-Agent and the shared NCBI budget
cannot drift between clients. A borrowed client that calls `requests` internally does not pass
through `ServiceGate`, so its requests are unpaced by us however well-behaved they are on their own
terms. Their own documented mitigations are per-source and ad hoc — Semantic Scholar wants a key,
CORE backs off exponentially, OpenAIRE retries three times — where ours is one gate with one policy.

**Three ways out, and the first is what to try:** an injectable client or session parameter on their
side, which is the ask to make of them and costs them little; routing the sources we care about
through our own thin clients and taking only the ones we do not pace; or accepting the drift
explicitly and saying so where an operator reads it, rather than letting the `net.py` rule quietly
become untrue.

**What must not happen is the silent version** — the rule in `CLAUDE.md` §2 stating that every
outbound request goes through a `ServiceGate`, while some of them do not.

---

## RM25 — nothing reads a log before it is published, and the catalog is immutable

**Severity:** medium · **Status: SHIPPED 2026-08-20** — `logscan.py`, the `review_logs` tool, and a
warning inside `registry_publish`. Kept open until the calibration has met a second real transcript;
one is not a corpus. · **Owner:** unassigned · **Opened** 2026-08-20

> **Shipped, and calibrated against real data in both directions rather than against invented logs:**
>
> - **True negative.** `assets/logs/quote-remediation.log` — a real log that really travelled to two
>   polygon rehearsals — returns **zero** findings. That was the requirement this entry set, and a
>   test asserts it, because a check that flags an honest run log teaches everyone to ignore it.
> - **True positive.** A real submitted bundle's transcript (`chd_depression_v1.zip`, 450 KB) returns
>   **16** findings: three absolute paths of the shape `/tmp/module_spec_szu7uiko`, and thirteen
>   lines up to **8304 characters** — the embedded-system-prompt signature. The clean fixture tops out
>   at 92 characters, so the threshold sits far from both and neither is a close call.
> - **The measured false positive was designed out.** The fixture contains *"every rsID token"*, so
>   credential detection is on **shape** — a name, an assignment and a value of real length — never on
>   a wordlist.
> - **It reports and never strips**, and it never refuses a publish. The `registry_publish` note
>   fires at the one moment the decision can still be made, which is what makes it a check rather
>   than the advice the dossier already carried and that changed nothing.
> - **A finding never reprints the whole line.** This output is read by an agent whose transcript is
>   itself retained, so echoing a credential in full would copy it somewhere new.
>
> **What is deliberately not built:** a secret scanner. The question stays *would the author be
> surprised to see this in the catalog?*

`_collect_logs` runs on **every** compile with no flag and no opt-out: any `*.log` in a spec
directory is copied into the artifact, hashed into the manifest, and uploaded on publish
(`gather_spec_files` skips only `.parquet`, `manifest.json` and `WHERE-THIS-CAME-FROM.md`). Our own
`logs.md` dossier states the consequence and then states the gap in the same breath — *"read a log
before you publish it — no tool will read it for you"* — and `grep` confirms nothing in
`tools/registry.py` looks at `logs/` before sending.

**The exposure is unrealized, and that is the point of filing now rather than later.** Measured:
**zero** of the 16 published versions across the 5 production modules carry a log entry, the polygon
carries none from anyone else, and none of the 16 reference examples ships a `.log`. Meanwhile the
registry operator's `data/input/` holds real agent transcripts — gitignored, untracked, never
published — that contain the full Agno team system prompt, every member model id, and upload paths
like `data/agent_uploads/40246_2025_Article_772.pdf`. **A published version is immutable**, so the
first time somebody drops one of those into a spec directory the catalog keeps it, and `yank` delists
without removing.

**We are the layer that should catch it**, by the workflow-versus-contract line in §11: what gets
*swept up* is the format's business and is correct as designed — the whole point of `logs/` is that
it accumulates across versions and travels. What is missing is an authoring-time read, and authoring
is ours.

**The shape, and it is small:** a pre-publish pass over `logs/**.log` reporting size, and flagging
what nobody means to publish — an absolute path, an `Authorization`/`Bearer`/`api_key`-shaped string,
a home directory, a system-prompt-sized block. **Report, never strip.** A log is a provenance record
and silently editing one is the opposite of what it exists for; the author decides whether to delete
it, and they cannot decide about a file nobody showed them.

**A worked example of the good case exists in this repo** and should be the fixture:
`data/interim/rm15_remediation/*/logs/quote-remediation.log`, which travelled to two polygon
rehearsals. 73 lines, no paths, no credentials, and an honest header — *"who: claude-opus-5,
unattended … human_confirmation: none — no human read any of these articles in this run"*. That is
what a published log should look like, and a check that flagged it would be a check with a false
positive, which is the calibration.

**Do not generalise it into a secret scanner.** The question is narrow: *would the author be
surprised to see this in the catalog?*

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

## RM26 — an audit surface: the offline arithmetic both runs had to write by hand

**Severity:** high · **Status:** open · **Owner:** unassigned · **Opened** 2026-08-22

Two independent unattended runs found every real defect by writing Python over the CSVs,
while five tools answered *"will this build?"* in different words. `F60` and `F61` carry the
measurements. The scope decision taken 2026-08-22 was to fix the surfaces and discovery in
that pass and roadmap this, because it is new product rather than a surface repair.

**The bar this has to clear is that every signal is computable offline from files the
plugin already reads.** That is what makes it buildable rather than a wish, and it is also
the boundary: anything needing a live source is a check and belongs in the check pass.

Candidate signals, each already measured by hand in one of the two runs:

- **Weight cells with no declared scale.** `weight` populated on N rows and no `weighting:`
  block. Also the opposite sign, which run 2 hit: `weight` empty on *every* row and no
  `weighting:` — so "the author authors none deliberately" and "the author forgot" are the
  same bytes, which is the distinction `weighting:` exists to carry.
- **Checks that have never run.** `verification.json` read for records that are absent, or
  present with `skipped` set, or present with `subjects: 0`. Run 1 measured the reference-base
  check at zero of eight modules, and the three states read very differently: a `skipped`
  record and a record that ran over nothing are both not-a-pass, and only one of them says so.
- **A record that counts findings and does not keep them.** Run 2 found 52 unresolved ClinVar
  disagreements across two modules with `detail: null` and no sidecar naming the rows. The
  rollup is ours even though the retention is upstream's.
- **`effect_measure` disagreeing with its own p-value.** Compare `effect_size` against
  `-Φ⁻¹(p/2)` per row. This is arithmetic on two authored columns and needs nothing external.
- **Per-column fill counts.** Run 2's ask, and the cheapest item here: one pass over rows the
  validator has already loaded turns "what is there to curate" from a question into a table.
  Five of its six curated modules had `category` empty on every row, reported as `categories:
  []` and treated as unremarkable.
- **A module with no `studies.csv` beside rows that make clinical claims.** The rule exists in
  `module-status` and is scoped to `variants.csv`, so a 1,482-row PGx module falls outside it
  and nothing fires.

**Two design constraints that are not negotiable.** First, this reports and never repairs: a
disagreement is not a defect report, and several of these signals have honest explanations —
run 1 retracted two of its own three findings, and nothing in the toolchain contributed to
either retraction. Second, the output is a **decision list**, not a findings dump: if a human
must choose, it goes in the list; if nothing must be chosen, it does not appear. An old module
is out of date, not defective.

**Where it should live is an open question.** A separate `audit_module` is the obvious shape.
The alternative worth weighing first is carrying the voice into the success path of tools that
already run — a green `validate_module` on a module whose reference-base check has never run
should say so. Both runs independently observed that this surface says difficult things well
and mostly says them when something breaks, and that a green result is a tool call while the
caveat is prose. That argues for the second shape, or for both.

`review_queue` is part of this entry rather than a separate one: `F61` is the same defect
seen from the far end, and widening it to emit `unknown` entries for fields whose archive
answer is not in the module is a smaller change than a new tool.
