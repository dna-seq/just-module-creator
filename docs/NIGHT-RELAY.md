# Night relay — the semaphore

**One file, one writer at a time. Both night agents read this FIRST and write to it LAST.**

The whole point: agent A runs alone, finishes, flips the state. Agent B refuses to exist until it sees
that flip. No overlap, no shared files, no coordination beyond this document.

## State

```
STATE: AUDIT-DONE
SINCE: 2026-08-20T01:40Z
BY: agent A — philosophy audit (RM15), complete
```

**Legal transitions, in order. Nothing skips.**

| From | Who moves it | To |
|---|---|---|
| `READY-FOR-AUDIT` | agent A (philosophy audit) on start | `AUDIT-RUNNING` |
| `AUDIT-RUNNING` | agent A on finish | `AUDIT-DONE` |
| `AUDIT-DONE` | agent B (builder) on start | `BUILD-RUNNING` |
| `BUILD-RUNNING` | agent B on finish | `BUILD-DONE` |

## The rules, both agents

1. **Read the `STATE:` line before doing anything else.** If it is not the state your role starts
   from, **stop immediately and write nothing.** Say which state you found and exit. A wrong-state
   start is the only failure mode this file exists to prevent.
2. **Claim it by writing your transition first**, with a UTC timestamp, before any other work. Commit
   that immediately — a claim nobody can see is not a claim.
3. **`AUDIT-RUNNING` or `BUILD-RUNNING` older than 4 hours is a dead agent.** Append a note saying
   so, move the state back one step, and stop. Do not take over its work.

   **Measure that from the newest history entry at the bottom of this file, not from the `SINCE:`
   line.** `SINCE:` records when the state was *claimed* and never moves; a live agent appends
   timestamped proof-of-life entries. Added 2026-08-20 by agent A, whose track includes a
   deliberately long-running subagent — reading `SINCE:` alone would have called a working agent
   dead.
4. **Never edit another role's section.** Append to your own.
5. **On finish, write the handoff below your transition** — not a summary of what you did, but what
   the next role needs *decided*. Then commit.

## Agent A — verdicts

*Per RM15's three-way test. You read this and nothing else about the audit. Written for someone who
was not here. **Draft from 00:5xZ, finalised at `AUDIT-DONE`** — if the state says `AUDIT-RUNNING`
this section is still moving.*

### report-never-repair in `server.INSTRUCTIONS`

**Replaced.** Rule 2 read *"Report, never repair. Lookups show you a value and refuse to write it into
an authored cell… Those refusals are the feature."* It now states the counterstance: **we may write,
and every write is logged**, plus the two cells still withheld — a value a later check compares
against *that same source*, and a value only a pilot can settle (genotype, weight, conclusion,
direction). It also says our writes are ours, logged as ours, and never laundered as upstream's.

**A new rule 3 was added and it is the important one**: *a mismatch against a source is not a defect
report.* Archives lag the edge, so a row disagreeing with ClinVar may be the module being right and
current while the archive is stale; conforming it silently **degrades** the module and turns the check
green. Editing against a source needs a reason that outranks the source, and an outranked row keeps
warning. The header now says "Five rules" and the numbering shifted — that broke a test, see below.

### §2 domain rules, per bullet

All sixteen read. **Thirteen stand**, three moved. The banner is flipped from under-audit to audited.

- **Physics, unchanged** — three-valued answers / `None` is not `False`; a determinism gate is not a
  correctness gate; `fully_resolved` without `resolution_subjects` (`all()` over empty); `*Unavailable`
  except-arm ordering; never silently fall back.
- **Ours already, kept** — never hardcode a schema fact; the `resolve_with_ensembl=False` pin; one
  spelling per sidecar; never delete a derived sidecar without a *verified* capture; the offline
  ceiling combining by OR; never resolve a rule contradiction by inference.
- **Kept but bounded** — *never fill a value from the same source that checks it.* Still true and it
  is ours, but it names **one cell/source pair** and is not a general "do not write". Now carries the
  cost that is specifically ours (the row moves from honestly unverified to *apparently* verified) and
  the same defect from the other direction: **a value that satisfies a check vacuously is as bad as
  one copied from the checker.** Ask of any green check: *could this have failed?*
- **Split (category 3)** — *never widen the write surface* bundled a security boundary with format's
  authoring boundary. Containment through `_shared.resolve_dir` is ours and absolute and is not under
  review. *"Tools write only where the upstream API already writes"* and *"never overwrite an authored
  file"* are **gone**: a layer that may not touch an authored file is not an authoring layer. What is
  still not licensed is named explicitly so the split does not read as blanket permission.
- **Reversed** — the `provenance_quote` prohibition. See below.

### The attestation contradiction — §1 ran, with the owner, and it is settled

Do **not** re-litigate this. The owner's ruling: *"Yes, it is a derived false direction: demolish full
force."*

`provenance_quote` attests that **a reading happened, by whoever is named** — not that a *human* read
it. `fetch_fulltext` already hands the agent the entire article, so the old rule never prevented a
machine reading; it only prevented the reading being written down, and left the column empty for the
only reader present. **An agent may now locate and write a quote**: verbatim, for the row's own claim,
never the article's title, and **saying who located it**.

Responsibility does not move with it — *"AI is not a subject of right, so the human author holds the
full responsibility"* — the attribution records the real distribution of labour so a reviewer can
route scrutiny, nothing more.

**What it cost, measured** (this is the calibration case for the whole audit, and it is in `CLAUDE.md`
§11): across every `studies.csv` upstream, the four published `antonkulaga/*` modules carry a quote on
**all 3668 rows**, exactly **one distinct string per PMID** (81 PMIDs), and that string is the
article's **title** verbatim. A title always appears in its own fulltext, so `quotes_found` matches
every one and the modules report full quote coverage while witnessing nothing. **The refusal did not
produce human-read quotes. It produced a green check over metadata.**

Filed upstream at discovery: **`S54`** (the check cannot fail on a title) and **`S55`** (withdraws our
own S11 reasoning; asks for the per-row attributor — `StudyRow` has no `curator` while `VariantRow`
does). Ours: `F42` / `F43` in `docs/just-dna-format-pending-fixes.md`. Numbers were computed with
`.claude/triage-state.py --next`; the documents said `S49` and were stale by five.

### Refusals that SURVIVE, and why they are ours

Each of these keeps its behaviour and got a new justification. **Do not read "kept" as "untouched"** —
the point of the audit was the reason, and a rule standing only on "upstream does it" was the defect.

| Refusal | Why it is ours |
|---|---|
| Don't fill a cell from the source that checks it | The row becomes *apparently* verified, and we are the layer handing somebody a module to trust |
| `check_identifiers` reports, doesn't correct | A rename is what the author needs to *see*; and rewriting destroys the evidence it moved |
| `gene_locus_conflicts` reports, doesn't correct | Pure epistemics: a lookup cannot know **which half** is wrong — fixing the gene and fixing the rsID give different modules |
| `DraftedTable.differs` left unchanged | Now the *lag* argument, which is stronger: the source may be the stale one |
| `refresh_sidecar` never resolves a conflict | Physics — **but conditionally**, see below |
| Partial re-derivation never classified against | A table never filled would report every real row as withdrawn |
| Upstream's `applied:false` / `refusal` passed verbatim | It records what the **compiler** did; restating it as ours misreports another layer's act |

**One of these has an expiry date and it is flagged in the code.** `refresh.py`'s conflict refusal is
physics *because we keep no third data point*: with only the captured value and the fresh value,
nothing separates an author's edit from a source's revision. **A filled authoring log settles it
outright**, and §2 now requires every authoring move to go through one. `logs/` is empty. Both the
module docstring and the tool docstring now say the refusal is honest today and **not permanent**, so
nobody hardens it into a principle. When RM16's capture lands, `refresh_sidecar` should read the log.

### Refusals REPLACED, and what the tool must now do

1. **`fetch_fulltext` — "returns no passage, ever"** → returns the text *and* tells the agent to quote
   it. Verbatim, for the row's own claim, never the title, with the F42 signature named (one identical
   string across every row citing a PMID) and the honest cost still stated: once you have read that
   fulltext, `quotes_found` on that row is a **citation-pairing check**, not evidence the claim is in
   the paper. Say it; don't let it stop you quoting.
2. **`_MACHINE_REFUSAL` / `describe_machine_table` — "not yours to finish by hand"** → **attribution,
   not abstention.** The hazard is real (passes merge, no check asks where a value came from, so an
   unmarked cell is fact-hashed as though the source said it) but the remedy contradicted our own
   `refresh_sidecar`, which exists to protect hand-curated rows. `resolution.csv` documents
   `source="manual"` in **upstream's own vocabulary**. So: write if you must, but **mark it**, and
   `source` is the marker. The unmarked cell is the defect, and a re-run will not clear one.
3. **`server.INSTRUCTIONS` rule 2 and `CLAUDE.md` §2's write surface** — above.

### DISCRIMINATOR: specified in part, and here is exactly what remains

Better than "blocked". Three of its four pieces now exist:

- **The statement** — `INSTRUCTIONS` rule 3 and `CLAUDE.md` §2. Evident and mechanical (a rename, a
  deprecated spelling, a moved column) → apply silently. Checked or authored (genotype, weight,
  `clin_sig`, conclusion, `provenance_quote`) → never touch, surface it. When unsure, surface:
  over-surfacing is recoverable, a silent wrong write is not.
- **The hazard it guards against** — the source lagging the edge, now written into the instructions
  rather than living only in `CLAUDE.md`.
- **The mask's schema half** — **upstream `S52` is already open and is exactly this**:
  *"`ProvenanceItem.rationale` is the outrank marker a cross-check needs, and no check reads it."*
  Read it before designing anything; someone has done the schema thinking already.

**What remains, and what it is blocked by:**

- **The record** — where an outranking reason is written and how a re-revision preserves it as a mask.
  Needs `logs/` filled: **RM16's capture half**, which the primer says is building in parallel.
- **`S52`'s answer** — whether a check will read the rationale. Not ours; do not build a parallel one.
- **The auto-correct rulebook** (§10, *to-populate-later*) is **still unpopulated and should stay
  that way tonight.** It is meant to be built from real authoring transcripts — the moves an author
  actually needed — not designed against the schema. Do not invent it.

### Actionables I did NOT do — the owner set my scope at prose/rules/docstrings

Code only where a docstring lied. These are yours to weigh:

1. **The title-vs-quote guard — highest value, and specified so you don't have to think.** Flag a
   `provenance_quote` that is not distinguishable from metadata we already hold: (a) equal to the
   article `title` for that PMID, normalised for case / trailing period / whitespace —
   `lookup_citation` already returns `title`, and `CitationHint.title` shipped upstream for `S12`, so
   it costs no extra request; (b) one identical quote repeated across **every** row citing a PMID,
   which is the structural signature regardless of the title. **A length or word-count heuristic is
   the wrong discriminator** — 17 words is an ordinary title *and* an ordinary sentence. Home is
   probably `lint_rows`; if it needs the title it may belong nearer `enrich_literature`. Upstream may
   also fix it (`S54`), so check before duplicating.
2. **The logged write path** — §2 requires every authoring move to go through the log and no tool
   routes to `logs/` yet. Nothing in the counterstance is real until this exists. Coordinate with
   RM16.
3. **`refresh_sidecar` reading the log** — promised in its docstring as the thing that ends the
   conflict refusal. Do not ship the promise without eventually shipping the read.
4. **A version bump.** `server.INSTRUCTIONS` is user-facing text and it changed; I deliberately did
   **not** bump mid-relay. Currently `0.10.2`. A bump touches **three** files —
   `pyproject.toml`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` — and
   `tests/test_plugin_manifest.py` fails on either manifest lagging.

### Coverage — what I did not read, and who has it

A **remediation dogfood** is running on my track and **owns three files**; I did not touch them and
neither should you until it lands: `skills/find-evidence/SKILL.md`,
`skills/module-tables/references/studies.md`, `skills/module-tables/references/literature.md`. It also
owns `docs/dogfooding.md` (appending `F44`+), `docs/HANDOFF-antonkulaga-quotes.md` and
`docs/RM15-remediation-log.md`. **Check its commits landed before treating those three as audited.**
Its brief: remediate the title-quotes on working copies of two of the four published modules, publish
the refreshed one to the **polygon** (never production), and map the friction.

### The skills sweep — ~15k lines, inventoried then judged

A read-only agent inventoried every skill and dossier and quoted ~80 passages; **I judged them, it did
not.** What changed:

- **`module-101` rule 2.** It mirrored `server.INSTRUCTIONS` and so contradicted the server the moment
  that changed. Now four rules matching the server's five, including the lag hazard, plus a line
  saying the server wins if they drift. The lifecycle diagram no longer labels cross-check
  *"report only, never repair"*.
- **The ten scaffold seeds — the highest-leverage edit of the night.** Every unwritten stage skill
  carried the identical bullet *"the cells no tool fills, with the refusal reasons"*. That is how the
  retired stance would have been written into ten skills one at a time, by ten different sessions.
  Replaced with the discriminator. `module-check` was worse: its *"What this skill owns"* sentence
  **was** the stance (*"Reporting, never repairing"*).
- **`create-module`** was already half-reversed (*"you may author these, and you should"*) but still
  forbade quoting the fulltext `fetch_fulltext` had just handed over, because the check "proves
  nothing". It proves something — the passage belongs to the paper you cited, which catches the
  wrong-PMID error. Table now says **yes** on all three rows with the honest cost per row, and the
  title prohibition replaces it as the one hard rule.
- **Seven "the refusal is the feature / output / answer / design" sites** — the framing under review,
  where the slogan was doing the arguing. Each now states its own reason.
- **Five "the quote columns attest a HUMAN read it" sites** — corrected to attribution.
  `references/readme.md` held the strongest form (*"which cells no tool may fill: all of them"*).
- **`module-revise`'s discriminator table is kept verbatim** — it was already right, and it is the
  canonical statement of the split. Only its subordination to the retired rule changed.

**What I deliberately did NOT change, so you don't redo it:** the recurring dossier heading *"cells no
tool may fill even though it easily could"* stands. It is accurate — it scopes to redundancy-bearing
cells and to judgement cells, and it is about a **tool auto-filling**, which is still wrong; it says
nothing about what an agent may author. Same for three surviving *"reported, never repaired"* uses in
`SYMPTOMS.md`, `heteroplasmy.md` and `create-module.md:1305`: those describe what the **upstream**
checks do on a ref mismatch, which is true of the compiler and is not a rule of ours.

### Loose ends the sweep turned up that are NOT RM15, and are yours if you want them

1. **Six dossiers contradict their own correction banners.** `resolution.md`, `frequencies.md`,
   `gene_metrics.md`, `gene_validity.md`, `clinical_assertions.md`, `gwas_effects.md` each carry a
   2026-08-20 banner saying *"this file says `describe_table` refuses this table… ask
   `describe_machine_table`"* — and their bodies still say the call refuses. The banner was prepended
   and the bodies were never swept. **I fixed only `clinical_assertions.md`**, because its wording was
   also a stance claim ("the refusal is correct, not a bug"). **All six are now fixed** — the other
   five landed in a follow-up commit; each says `describe_machine_table` is the route that answers.
2. **Four dossiers say `create-module/SKILL.md` is wrong.** `variants.md:213` (the
   homozygous/undecided promise), `pharm_variants.md:197`, `pgs.md:222`, `repeat_alleles.md:213`
   (the pre-0.6 integer-bin rule). **I checked the fourth and it was mostly a false alarm** —
   `create-module`'s body keys the bin rule on `measure_tiling` exactly as 0.6 does; only its beginner
   summary row stated it as a property of the measure's kind. Both are fixed and the dossier's
   complaint is narrowed. **Take that as the lesson for the other three: verify against live models
   before believing the dossier over the skill.** A dossier's complaint can itself be stale, and
   "the skill is wrong" is cheaper to write than to check.
3. **`activity_phenotype.md:443` claims a live `describe_table` returned the format **0.5** shape
   while `importlib.metadata` reported 0.6.1.** If that reproduces it undercuts rule 1 —
   *ask the tool, never memory* — and is worth an upstream note. I did not reproduce it.
4. **A false alarm, checked so you don't recheck it:** the inventory flagged `refresh_sidecar` and
   `describe_machine_table` as possibly not existing. Both exist. `refresh_sidecar` is
   **extended-only**, which is why an essentials roster does not show it, and `module-refresh`
   already says "Extended tier". No defect.
5. **`docs/DESIGN-version-compare.md` carries the stance twice** (a "report, never repair" section
   heading and a machine-located-quote analogy) and I left it alone — the primer says a design study
   may still be running against it. It will need the same pass.
6. **A duplicate `F38`** exists in `docs/just-dna-format-pending-fixes.md` (two different findings
   share the number). I did not renumber; ids are load-bearing. Next free is **F44**.

## Agent B — handoff (fill on finish)

```
built:
skills written:
left undone, and why:
```

---

*Appended history below. Newest last. Never rewrite an earlier entry.*

### 2026-08-19T23:56Z — agent A claims the audit

Found `READY-FOR-AUDIT`, moved to `AUDIT-RUNNING`. Running RM15 per
`docs/PRIMER-philosophy-audit.md`. Unattended run; the owner is reachable for the first ten minutes
only, which is being spent on §6's questionnaire (the attestation contradiction) because that is the
one item the primer forbids deciding alone.

### 2026-08-20T00:34Z — agent A, proof of life

Still `AUDIT-RUNNING`, ~38 min in. Not a dead agent. Landed so far: the attestation contradiction
decided (§1 ran with the owner — the prohibition is reversed, not narrowed), `server.INSTRUCTIONS`
rewritten, all sixteen §2 domain bullets judged, five code surfaces re-justified, `refresh.py`
audited. Upstream `S54`/`S55` filed in the format tree (uncommitted there, as required).

Two subagents are live on my track and **agent B must not touch what they own**:
- a remediation dogfood owning `skills/find-evidence/SKILL.md`,
  `skills/module-tables/references/{studies,literature}.md`, `docs/dogfooding.md`,
  `docs/HANDOFF-antonkulaga-quotes.md`, `docs/RM15-remediation-log.md`;
- a read-only inventory of the remaining skills (edits nothing).

Remaining before `AUDIT-DONE`: judge the skills inventory, `docs/ROADMAP.md` RM15 + `CHANGELOG.md`,
and the verdicts section.

### 2026-08-20T00:52Z — agent A, audit complete; holding for the remediation track

**The RM15 audit itself is finished** and every "done when" condition is met — verdicts are in the
section above, all gates green (204 tests, ruff, pyright), tree clean, everything committed.

**Still `AUDIT-RUNNING` on purpose.** The owner defined this track as completing when the remediation
dogfood completes too, so the semaphore stays until that subagent returns. It owns
`skills/find-evidence/SKILL.md`, `skills/module-tables/references/{studies,literature}.md`,
`docs/dogfooding.md`, `docs/HANDOFF-antonkulaga-quotes.md` and `docs/RM15-remediation-log.md`.

If it has not returned by **03:30Z** I flip to `AUDIT-DONE` anyway and record what it left unfinished
— a late remediation is not a reason to burn the rest of the night.

## Agent A — the remediation track (addendum to the verdicts)

The dogfood returned. Its own findings are `F44`–`F51` in `docs/dogfooding.md`, `RM17` on the roadmap,
and `docs/HANDOFF-antonkulaga-quotes.md`. Three things from it change what **you** should do:

1. **`F44` is the defect that let this happen, and it is deliberately NOT built.** Two spec dirs
   differing *only* in `provenance_quote` — one honest, one all titles — come back byte-identical from
   `registry_check(literature=true, strict=true)`: `verdict: true`, nothing blocking, nothing
   unchecked. `validate_module`, `compile_module` and `lint_rows` are equally silent. **Nothing in the
   product can tell them apart.** The detector needs no network — group `studies.csv` by `pmid`, count
   *distinct* quotes. It was left unbuilt for a real reason: `validate_module`'s warnings are
   upstream's, carried verbatim, and mixing a finding *we* computed into that list destroys the layer
   distinction `_shared.to_findings` exists to keep. **That is a §1 question, not a 2 a.m. choice** —
   `RM17` states it. This supersedes the title-guard actionable in my list above; read `RM17` first.
2. **`F51` corrected a rule of mine, and I have fixed `CLAUDE.md` §8.** `uv run` resolves against
   whichever project you stand in, so a symbol check chained after a `cd ../just-dna-format` answers
   about *their working tree*. **The version string is no guard**: both report `just-dna-format 0.6.1`
   while `StudyRow.curator` is `True` there and `False` in our venv. Print `__file__` beside the
   answer and pass `--project`. I re-verified every upstream claim in these verdicts that way.
3. **Upstream accepted `S54`, `S55` and the dogfood's `S56` and fixed all three in tree the same
   night** — `RM118`/`RM119`/`RM120`; `S55` got `StudyRow.curator` verbatim, which I confirmed by
   symbol in their tree. **None is released.** `F42`/`F43` stay open and every mitigation stays.

**The finding that justifies the whole reversal**, and worth reading before you touch this area: four
rows of `big_five_personality` cite PMID `34054130` for a *neuroticism* item; the article names all
four rsIDs — in a table of hits for **sociability**. Only going after the actual passage could surface
that. Under the old rule those four carried the article title and looked exactly like the other 855.
They were left empty and escalated, not repaired.

Yield was **2–3%** (21 located passages in 859 rows) and *inverse* to row count — the three papers
grounding the most rows named none of them. So the honest output of this work is mostly **empty
cells**, and that is the correct result, not a failure.

### Ownership released

Everything is committed and the tree is clean. **No file is reserved any more** — the three skills I
had delegated (`find-evidence`, `references/{studies,literature}.md`) landed, and the dogfood also
touched `src/just_module_creator/{discovery.py,tools/authoring.py}`, `docs/ROADMAP.md` (RM17),
`docs/CHANGELOG.md` (inside my Unreleased entry), `docs/previous_issues.md` and
`docs/just-dna-format-pending-fixes.md`.

Still untouched and still needing the same pass: **`docs/DESIGN-version-compare.md`** (the primer
fenced it off; it carries the stance twice).

---

### 2026-08-20T01:40Z — agent A finishes; AUDIT-RUNNING -> AUDIT-DONE

RM15 complete: all three "done when" conditions met, §1 ran with the owner and its answer is in
`CLAUDE.md` §10, `server.INSTRUCTIONS` and §2 agree. 204 tests, `ruff`, `pyright` all green; tree
clean. Verdicts are the two sections above — read the actionables list and the `RM17` note before
planning, because one of my actionables was superseded by a better-reasoned decision not to build it.

**Agent B: the state is yours. Nothing is reserved.**
