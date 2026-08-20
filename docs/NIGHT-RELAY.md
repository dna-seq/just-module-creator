# Night relay — the semaphore

**One file, one writer at a time. Both night agents read this FIRST and write to it LAST.**

The whole point: agent A runs alone, finishes, flips the state. Agent B refuses to exist until it sees
that flip. No overlap, no shared files, no coordination beyond this document.

## State

```
STATE: AUDIT-RUNNING
SINCE: 2026-08-19T23:56Z
BY: agent A — philosophy audit (RM15)
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

Everything else in `skills/` was swept — see the section below, written when the inventory returned.

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
