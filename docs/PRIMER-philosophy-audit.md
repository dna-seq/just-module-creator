# Primer — the philosophy audit (RM15)

**You are running `RM15` with a clean context. This file is self-contained: it assumes you have read
`CLAUDE.md` and nothing else about this session.** Read `docs/ROADMAP.md`'s `## RM15` entry too — it is
the item; this is the briefing.

Written 2026-08-20 by the session that opened RM15.

---

## 1. What happened, in one paragraph

`just-dna-format` holds a stance called **report, never repair**: a lookup shows a value and refuses to
write it into an authored cell. That stance is **correct for that layer** — the compiler cannot record
*who decided* a value, so writing one would launder a machine's guess as an author's judgement.

**This repo adopted it as a non-negotiable of its own, and never asked whether it belonged here.** It
was written into `CLAUDE.md` §2, into `server.INSTRUCTIONS` rule 2, and from there quoted, argued and
built on across fourteen skills, four table dossiers, `models.py` field descriptions and one tool.

The owner corrected it on 2026-08-20:

> *"Report-never-repair is format's stance, correct for that layer: they delegate business decision to
> us here; we're more high-level user-facing app level, we have a counterstance."*

§2 now states that counterstance. **Nothing else has been re-read.** That is your job.

## 2. The counterstance, as it now stands in §2

Three parts. Do not treat any one of them alone — the first without the other two is reckless.

1. **We may write. Full stop.** *"Yes, we may write, fullstop… we may revise and fix — yes
   absolutely."* A business decision is delegated to this layer.
2. **Every authoring move goes through the log.** The `logs/` surface exists and is empty — its own
   dossier is titled *the provenance subtree nobody fills*. It is swept by every compile and published
   with no opt-out. A move made by hand is harder to capture, so route it through a skill that logs.
3. **The agent needs a discriminator.** See §3 — this is the part most likely to be got wrong.

## 3. The hazard, and why the obvious reading of it is too shallow

The argument this repo had been using: *fill `clin_sig` from ClinVar, then a check compares `clin_sig`
against ClinVar and agrees with itself.* True, and **secondary**. Reading only that is how the stance
survived unexamined for so long, because it makes the rule look like arithmetic.

The real hazard, in the owner's words:

> *"Why not?? ClinVar lags behind edge, say the article is retracted, metaresearch refutes conclusion
> etc — validation against ClinVar this way makes the correction done mindlessly, wrong."*

So **"your row disagrees with ClinVar" is not a defect report.** It may be the module being right and
current while the archive is stale. An agent that silently conforms the row to the source **degrades**
the module — and the check then agrees with itself and reports green. That is a worse outcome than the
mismatch it "fixed".

**Editing against a source needs a reason that outranks the source.** Whether a retraction, a
meta-analysis or a larger cohort outranks an archive call is a natural-language judgement — an
evidence-grading pyramid exists but does not decide it. So the instrument is **recommendations plus a
freeform record**, never a vocabulary.

### The two pathways, which is the discriminator's actual specification

Both start identically. They diverge only *afterwards*, which is why no check can tell them apart at
the moment of the mismatch:

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

Three consequences you will need while judging individual rules:

- **The record is a response to a warning, never a filter filed ahead of one.** If a row could be
  marked outranked before the mismatch is reported, pathway 1 loses the only signal that catches it.
- **An outranked row is never silent** — warn or info, always visible. The reason is time: whoever
  wrote the justification understood it, and two source releases later nobody remembers whether the
  retraction that motivated it was itself superseded.
- **"No longer warns" never means green.** A row where the module and the archive disagree is
  interesting forever. The record says who decided and why; it does not make the disagreement go away.

## 4. Your test — apply it to every instance

For each rule, refusal, docstring and piece of prose, decide which of three it is:

| | | What to do |
|---|---|---|
| **1. Physics** | true at any layer | keep unchanged |
| **2. Format's policy, correctly ours too** | keep — **but rewrite the justification to stand on *our* purpose** | a rule whose only support is "upstream does it" is the defect, even when the rule is right |
| **3. Format's policy we should not hold** | replace with the counterstance | and **follow it through to the tool's behaviour**, not only its prose |

Known **physics**, for calibration — confirm rather than assume, but these are the shape:

- A check that could not run is not a check that passed. `null`/`unknown` never collapse into a pass.
- `None` is never `False`. Three-valued answers stay three-valued.
- A determinism gate is not a correctness gate — `--strict`, a digest match, a reproducible build all
  mean *reproducible*, and a module shifted one base reproduces perfectly.
- Never silently fall back when primary data is missing; name the substitute or refuse.

**Category 2 is where most of your work is**, and it is the least satisfying to write. Resist the urge
to promote things into category 3 for the pleasure of changing something.

## 5. The surfaces, most load-bearing first

Measured 2026-08-20. Line numbers will have drifted — grep the phrases.

1. **`src/just_module_creator/server.py` → `INSTRUCTIONS`, rule 2.** *"Lookups show you a value and
   refuse to write it into an authored cell… Those refusals are the feature."* This is the **first
   thing an agent reads, before any tool call**, and it now contradicts §2. Highest priority.
2. **`CLAUDE.md` §2, "the domain rules this server exists to enforce".** The whole section carries an
   audit banner pointing here. Every bullet, individually — they are not all the same category.
3. **The skills.** `module-101`, `create-module`, `module-check`, `module-close`, `module-compile`,
   `module-consumer`, `module-curate`, `module-draft`, `module-enrich`, `module-publish`,
   `module-start`, `module-weights`. Several frame a refusal **as a feature**, which is exactly the
   framing under review. Note that ten of these are still scaffolds — a scaffold's *seeds* are where
   the stance will otherwise get written in when someone fills it.
4. **`skills/module-tables/references/{studies,gwas_effects,pharm_variants,repeat_alleles}.md`.**
5. **`models.py` field descriptions and every lookup tool's docstring.** An agent reads these as the
   contract; a description saying a tool refuses on principle is a behavioural claim.
6. **`src/just_module_creator/tools/refresh.py`** — written 2026-08-20 *from a brief that quoted the
   old stance*, so it inherited it by construction rather than by decision. Its central refusal is
   probably category 1 (two data points genuinely cannot distinguish your edit from the source's
   revision), but it was not *decided*, and that is the point.

## 6. The contradiction you must NOT resolve alone

**`CLAUDE.md` §2 forbids extracting a passage from a fetched document. §10 records the owner saying the
opposite about who can read a paper.**

- §2: *"Never extract a passage from a document a tool fetched… a machine-located quote asserts a
  reading that never happened, which is a false claim of provenance."*
- §10: asking a layman for a `provenance_quote` is *"v2 work from a wrong person"* — a reviewer's job,
  and a different person's — and flatly, **"AI totaly can read articles."**

Under the pivot these cannot both stand as written. If the agent is a legitimate reader, a located
quote *is* a reading that happened, and the question becomes **whose** reading was recorded rather than
whether one occurred.

**Run `CLAUDE.md` §1's questionnaire. Do not infer.** §1 is explicit: survey first, one question per
contradiction, batched, each option stating its cost, recommend one and say so, then record the answer
where it will be read again. This is the highest-stakes instance of the absorption RM15 is about, and
`hints.ATTESTATION_BEARING` shipped **upstream** on the argument now in question — so a wrong answer
here is a wrong answer in somebody else's released code.

The §2 bullet already carries a 🚩 marker pointing at this. Leave it there until §1 has run.

## 7. Rules of engagement

- **Nothing here is known to be wrong.** RM15 is an audit. A rule that survives with a better
  justification is a successful outcome, and probably the most common one.
- **Do not touch `docs/DESIGN-version-compare.md`** — a design study may still be running against it.
- **Upstream notes go to the right intake and are never committed there.** `CLAUDE.md` §8 has the two
  addresses and the rule. Compute the next `S<n>` with `.claude/triage-state.py --next` in the target
  repo; never take a number from any document. Upstream answers within the hour, so file at discovery
  and re-check before quoting your own mitigation as current.
- **What you decide gets recorded in §10 in the owner's words with the reason**, per §9. A resolved
  contradiction that is not written down gets re-asked.
- **This blocks two things**, so say plainly what you have unblocked: the **discriminator** (§2 part 3)
  and the **auto-correct rulebook** (§10, *to-populate-later*). Neither can be specified until it is
  known which refusals survive. `RM16` is building the capture half in parallel.

## 8. Done when

Every surface in §5 carries a rule justified **from this layer's own purpose**, with no prohibition
standing only on "upstream does it that way"; `server.INSTRUCTIONS` and §2 agree with each other; and
§1's questionnaire on the attestation contradiction has run with its answer recorded in §10.

---

## Night run — the semaphore, and your autonomy

**`docs/NIGHT-RELAY.md` is the semaphore. Read its `STATE:` line before anything else.**

**You are agent A. You start from `READY-FOR-AUDIT` and move it to `AUDIT-RUNNING`.** If you find
anything else — including `AUDIT-DONE` — **stop immediately, write nothing, and say which state you
found.** On finish move it to `AUDIT-DONE` and fill the *Agent A — verdicts* section. That section is
the only thing the builder will read about your work, so write it for someone who was not here.

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
