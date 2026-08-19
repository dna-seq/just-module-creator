# Primer — where this stands, for whoever picks it up next

Written 2026-08-20 at the end of the session that did the work below. **Read `CLAUDE.md` first, then
this.** `docs/HANDOFF-skills-split.md` and `docs/HANDOFF-upstream-audit-2026-08-20.md` are still live
and still accurate; this file is what changed after them.

**If you are here to run the philosophy audit, stop and read `docs/PRIMER-philosophy-audit.md`
instead** — it is written for a clean context and this file will only distract you.

---

## 1. The single most important thing

**Four rules changed this session, and three of them invert something you may have already absorbed
from an earlier read of `CLAUDE.md`.** They are in §2, §10 and §11 in the owner's words, and in memory.
Do not act on the old versions:

| | Now |
|---|---|
| **report, never repair** | **that is the FORMAT's stance.** We hold a counterstance: we may write, every move is logged, and the agent is owed a discriminator. `RM15` (high) audits the 19 places the old stance reached |
| **legacy handling** | **there is no era axis.** *"Idempotent `to_current_state`, so to say."* Recipes target the current release only; uplift mechanics stay upstream's; a backwards-compat measurement is their property, not our result |
| **an old module that does not meet today's bar** | **not "broken."** It *"needs this this and this decision to work in latest."* A revisit returns a **decision list**, not a findings dump. Auto-correct the evident silently |
| **an authoring-workflow gap** | **build it here first, then show them.** *"Asking them is no big deal; but don't come empty handed — show them the tool."* Schema/contract gaps are still filed immediately |

The hazard behind the first one is worth internalising because it is not the obvious one. It is **not**
that a check might agree with itself. It is that **the source lags the edge** — a retraction, a
refuting meta-analysis — so *"your row disagrees with ClinVar"* may be the module being right while the
archive is stale, and silently conforming it **degrades** the module under a green check.

## 2. What got built

**Skills — 7 of 17 written, and the second-pass half is complete.**

| Written | Lines | Owns |
|---|---|---|
| `module-101` | 300 | the map. Minimal authored surface only (spec + variants + studies + README) |
| `module-tables` | 301 | the router: table choice by grain, the on-disk shapes, `derived/`. Plus **25 references** — 24 per-table dossiers and `LAYOUT.md` |
| `module-revise` | 281 | pass two and beyond, the six kinds, the review-vs-`reviews`-row split, the revisit voice |
| `module-refresh` | 188 | merge-not-clobber, per-sidecar delete costs, `refresh_sidecar`, what a re-draft cannot repair |
| `module-diff` | 184 | the identity ledger, the canary decision tree, the two-command diff recipe |
| `create-module` | 1431 | still the one copy of the pass-one procedure, stages 1–8 |
| `find-evidence` | 280 | untouched this session |

**Still scaffolds, all pass-one spine:** `module-start`, `module-draft`, `module-curate`,
`module-enrich`, `module-check`, `module-compile`, `module-close`, `module-publish`, plus
`module-consumer` and `module-weights` as references. **An author's actual load has not dropped yet** —
`create-module` still holds all of it at 1431 lines.

**Tools — four items shipped.** `produced_by` on every generated schema answer (RM13);
`describe_machine_table` for the seven machine-produced tables (RM11); `enrich_gwas_effects` (RM12);
`refresh_sidecar` (override-preserving re-derive). Plus three restated schema facts made generated or
test-guarded (RM10). 204 tests pass, ruff and pyright clean.

## 3. What is open, in priority order

**`RM15` — the philosophy audit. HIGH, and it gates the rest.** Its own primer exists. It blocks the
**discriminator** (§2 part 3) and the **auto-correct rulebook** (§10). More practically: **writing the
ten remaining scaffolds before the audit means writing ten more copies of a stance under audit.**
`tools/refresh.py` already inherited it from a brief written that same morning — the failure reproducing
in real time.

**`RM16` — capture the outrank reason. HIGH.** The substrate exists upstream and is unread:
`manifest.ProvenanceItem` already has `rationale`, `reviewer_verdict`, `confidence`, `human_reviewed`
and an AI-aware header, is in the registry's `RECOGNIZED_SPEC_FILES`, and **nothing reads it** — the
compiler takes `len(doc.items)` and no field. Ours: write `provenance.json`, capture the reason *in
response to a reported mismatch* (not at edit time — otherwise pathway 1 loses its only signal), share
one mask representation with `refresh_sidecar`, detect the terminal state, ship the grading
recommendations. Theirs: whether a check downgrades the mismatch — filed as `S52`.

**`RM6`, `RM9`** — unchanged from before, lower.

**`docs/DESIGN-version-compare.md`** — the version-compare design study came back and says **build it
now**, 699 lines, committed. Two tools, both **essentials** because both are bounded by what the caller
named: `compare_modules(left_dir, right_dir)`, a pure function of two local spec directories with no
network and no compile (0.18 s on the largest reference example), and `compare_to_published(spec_dir)`,
manifest-only, one or two bounded GETs and no download. Published-vs-published is the first tool applied
to two downloads, which stays extended. Output is a three-level ladder — signature, table, then rows
**grouped by the set of columns that changed** — with eight named refusals and a three-valued verdict
per axis. Nothing is waiting on an upstream release: the in-tree additions (`hints.key_fields`,
`hints.DERIVED_TABLE_MODELS`, registry 0.19's per-version `content_signature`) are symbol-gated
improvements rather than prerequisites. **This is the next buildable item after RM15/RM16.**

## 4. Upstream state — they answer within the hour

That is not a figure of speech. `S46` was filed, answered, and had RM86 closed inside an hour; `S47`
and `S48` were answered *and shipped in tree* the same session.

| Filed | State |
|---|---|
| `S46` §6.6 said the closure reached nothing downstream | **answered, RM86 closed, §6.6 rewritten** |
| `S47` no public csv→row-model map | **answered, shipped as their RM112** — not installed yet |
| `S48` a kind's natural-key columns unobtainable | **shipped as their RM113** — not installed yet |
| `S49` `COMPANION_KINDS` pulls `variants.csv` in behind `studies.csv` | open |
| `S50` `study_facts=false` is permanent, not a per-run trade | open |
| `S51` a sidecar's merge key lives inside its pass | open — **ranked first of ours**, it degrades shipped code |
| `S52` `rationale` is the outrank marker no check reads (+ two addenda) | open — ranked second; **shapes `RM16`** |
| registry `S13` a `split_derived` docstring contradicts the code beside it | open |

Ours: `F37`–`F41` in `docs/just-dna-format-pending-fixes.md`.

**We ranked our own open notes for them**, because both upstream agents have their hands full and an
unranked pile of five is not a favour. `S51` first — it degrades `refresh_sidecar` *today*: the merge key
had to be approximated from required fact fields, and the approximation is coarse on two of seven tables
(`gene_validity.csv` drops `disease_id`, `clinical_assertions.csv` drops `variation_id`), so rows that
could be safely repaired are reported as unresolvable conflicts instead. `S52` second, and the note says
plainly that the **granularity answer is cheaper and more useful to us than the severity change** —
three shapes are on the table, it is their document, and we are not designing around a guess. `S49` and
`S50` lower, neither blocking. All of it behind anything of their own.

**Two consequences of that speed.** *Re-check the tree before quoting your own mitigation as current* —
a 0.10.1 docstring was wrong before anyone read it. And **verify by symbol, never by a version line**:
`S47`/`S48` are fixed in their tree and **not in what `uv sync` gives us**, so our substitutes stay
until a release carries them.

## 5. Corrections made to things that read as settled

Every one of these was measured, not argued. If you find prose that contradicts them, the prose is
older.

- **`MODULE_LIFECYCLE.md` §5.1's row 2 has three routes, not "exactly two".** Reordering authored rows
  leaves `content_signature` identical and moves `artifact.digest` — measured on
  `hfe_hemochromatosis`, `sha256:6c6e103d…` → `sha256:83635ace…`. Their conclusion survives (row 3 is
  still the only canary); the enumeration was short.
- **There are eight fact-signature families, not seven**, and `hfe_hemochromatosis` publishes **four**
  numbers where §5.1 says three — it gained a `gwas_effects.csv`. `module-diff` therefore refuses to
  state a count and tells you to read your own manifest.
- **A re-draft that appends nothing is inert.** `create-module` had said it always moves the digest.
  Measured byte-identical across two `record_source_terms` runs.
- **The 0.6 positional fill exists.** `create-module` taught the pre-0.6 rule — resolution reaching
  `weights.parquet` only. `_POSITIONAL_TABLE_KINDS` fills `pharm_variants`, `haplotypes`,
  `heteroplasmy` in validate *and* compile. `diplotypes.csv` and `pgs.csv` are unfilled for a
  *different* reason: those models have no coordinate columns at all.
- **The shared-endpoint rule keys on `measure_tiling`, not on `measure_kind`** — an authorable column;
  the kind supplies only the default.
- **`manifest.json` has 34 top-level keys**, not 33. **Registry is 0.18.2+**, and **production holds
  five modules**, not one — four `antonkulaga/*` at 2.x plus `eric-mods/lactose_tolerance@1.0.1`.
- **The `unresolved` bin sentinel is a contract nobody enforces**: the compile path refuses a *second*
  per group and refuses zero nowhere, so a sentinel-less binning table compiles green under `--strict`.

## 6. Traps this session hit, so you do not

- **A memory can be actively wrong and cost you.** `anton-authoring-transcripts` claimed findings were
  filed as `F37`–`F43`; they never were, the ceiling was `F36`, and a real `F37` was minted into the
  apparent collision. Corrected — but **verify a memory's specifics before acting on them.**
- **`cd` leaks between Bash calls.** A `git add`/`git commit` pair ran inside `just-dna-format` because
  of an earlier `cd`. The `add` failed on a non-matching path so the commit never executed, but that is
  luck, not safety. **Use absolute paths in git commands**, and every git grant is bounded to this repo.
- **Never take an `S<n>` or `F<n>` from a document.** Both series moved by several within single hours,
  and two of this session's parallel agents claimed numbers between one reading and the next write.
- **Anchoring text by "the last line matching a pattern" put seven correction notes in the wrong place.**
  Verify placement after a scripted multi-file edit.
- **A skill claim can be falsified by a tool you just shipped.** Each agent was told to *report* false
  skill claims rather than edit `skills/`, which worked well — three separate reports, all correct, one
  of them a pre-existing error nobody had noticed (`create-module` calling the fact passes CLI-only,
  wrong since 0.6).

## 7. Standing decisions from this session

- **The dossiers are audited** (2026-08-20, code as arbiter). **Anchor on symbol names, never
  `file:line`** — the reasoning held, the numbers drifted. Read the 🚧 **ROADWORKS** and ⚠️ **CHECK**
  markers; a 🚧 on a tool you are about to recommend means you owe the guard, not the happy path.
- **`create-module/references/TABLES.md` is now a pointer**; the decision lives in `module-tables`.
- **`skills/` is one owner's surface at a time.** Sub-agents were told to report false claims rather
  than edit them, and that kept four parallel agents from colliding. Keep doing it.
- **Both handoff docs and this primer are tracked**, deliberately — the audit consumable is the source
  the remaining skills get written from.
- **Commit and tag without asking; push never.** Meaningfully sized commits, explicit paths, never
  `git add -A`. Upstream notes are written and never committed in their tree.

## 8. If you want the shortest useful next step

Run `RM15` (it has its own primer), then write **`module-start`** — the entry point every real session
hits first, where the "needs decisions, not broken" voice matters most, and whose seeds are already
verified in `docs/HANDOFF-upstream-audit-2026-08-20.md` §3. Then **`module-curate`**, which is the
biggest chunk still inside `create-module` and the stage where the counterstance bites hardest: it is
*the* place an agent decides a value a source disagrees with, so writing it is how RM15's answer gets
tested against something real.

---

## Night run — the semaphore, and your autonomy

**`docs/NIGHT-RELAY.md` is the semaphore. Read its `STATE:` line before anything else.**

**You are agent B. You start from `AUDIT-DONE` and move it to `BUILD-RUNNING`.** If you find
`READY-FOR-AUDIT` or `AUDIT-RUNNING`, **the audit has not finished: stop immediately and write
nothing.** Your work depends on its verdicts — ten skills written against a stance under audit is
exactly the waste this relay prevents. Read *Agent A — verdicts* before touching a skill, and fill
*Agent B — handoff* on finish.

Claim it by writing your transition into that file *first*, with a UTC timestamp, and commit that
immediately — a claim nobody can see is not a claim. Fill your section on finish: not a summary of
what you did, but **what the next role needs decided.**

**A `*-RUNNING` state older than four hours is a dead agent.** Append a note, move the state back one
step, stop. Do not take over its work.

### Full autonomy for this run

You are running unattended. **Do not stop to ask.** Specifically:

- **Commit as you go**, meaningfully sized, explicit paths. Never `git add -A`. **Never push**, never
  tag, never touch a branch.
- **Decide.** Where this session would have asked a question, pick the option you can defend, write
  the reasoning where it will be read again (`CLAUDE.md` §10 for a rule, the relay file for a
  handoff), and continue. A blocked night is worth less than a defensible call.
- **File upstream at discovery**, never batched. Compute the next `S<n>` with
  `.claude/triage-state.py --next` in the target repo — never from any document, both series move
  hourly. **Write the note, never commit in their tree.** Leaving it dirty is the expected outcome.
- **Measure rather than trust.** Every count, every version, every claim about upstream: run it. This
  session found seven "settled" facts that were false, and every one came from prose.
- **Verify by symbol, not by version.** `S47`/`S48` are fixed in their tree and absent from what
  `uv sync` installs.
- **`uv run pytest`, `uv run ruff check .`, `uv run pyright` must all pass before each commit.** Never
  bare `python`.
- **Use absolute paths in git commands.** A leaked `cd` put git commands in the upstream repo this
  session; the `add` failed by luck.
- **If you genuinely cannot proceed**, write why into the relay file, move the state back, and stop.
  A clean stop with a stated reason is a good outcome. A guess committed at 4am is not.
