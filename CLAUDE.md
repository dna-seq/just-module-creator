# Agent Guidelines — just-module-creator

A plugin for **Claude Code and Codex** — two manifests, one server, one skill set —
shipping two halves: an MCP server that wraps the just-dna toolchain with
agent-shaped tools, and the skills that teach the workflow those tools serve. It is
an **application, not a published library** — the contract is the MCP tool surface
and the skills, not Python imports, so internals are free to change and no
`__all__` is curated. **Neither host is the primary one**: a change to the tool
surface or the skill set owes the same to both, which is why the version bump
touches two manifests rather than one.

It is **not** a format, a schema or an annotation engine. We own no schema:
every column list, vocabulary and requirement comes from the live pydantic
models in `just-dna-format`. It also never executes a VCF — nothing here reads a
sample or calls a genotype.

`AGENTS.md` is a symlink to this file. If the two ever differ, that is a bug —
`ln -sf CLAUDE.md AGENTS.md`.

---

## Read these first, in this order

Obligatory. Read them yourself. **Do not delegate a document you are about to
judge a design against** — a subagent returns a summary, and a summary of a rule
drops the qualifier the decision turned on. Delegation is for finding, never for
deciding.

1. **[docs/DOMAIN.md](docs/DOMAIN.md)** — what a just-dna module is, what the
   four upstream packages guarantee, and the traps that constrain what we may
   build. Every tool here is a promise about one of its rules.
2. **[docs/ROADMAP.md](docs/ROADMAP.md)** — active-only, forward-only. One
   `## RMn — name` section per *open* item.
3. **[docs/CHANGELOG.md](docs/CHANGELOG.md)** — what actually shipped, newest first.
4. **[docs/dogfooding.md](docs/dogfooding.md)** — open findings from using the
   shipped surface for real work. Read before touching the tool surface.

Everything below is self-contained: no rule here requires following a link to
know what you must not do. Links carry positive detail only.

### The agent assets this repo ships

| Path | What |
|---|---|
| `skills/module-101/SKILL.md` | **The entry point and the map — high level only.** What a module is, what the plugin can and cannot do, the four packages, the lifecycle *including second and later passes*, and the **minimal** authored surface (`module_spec.yaml` + `variants.csv` + `studies.csv` + `README.md`) and nothing beyond it — the table roster, the on-disk shapes and the `derived/` layout are `module-tables`'. It holds no column list, no procedure and no symptom lookup: anything answerable only with a specific cell value, flag or warning phrase belongs in a subskill, and this file growing to hold one is the drift to watch for. |
| **The stage spine**, one skill per lifecycle stage | `module-start` (0–1: triage, licence, the spec), `module-draft` (2), `module-curate` (3), `module-enrich` (4), `module-check` (5), `module-compile` (6), `module-close` (6b), `module-publish` (7–8). **Each owns its stage's procedure outright — there is no second copy anywhere**, and each ends with the discriminator (what to apply silently, what to put in front of a pilot) rather than a list of refusals. |
| **The second-pass three** | `module-revise` (which kind of pass, and what it invalidates), `module-refresh` (re-running anything that already ran), `module-diff` (what moved, and the one reading that means an upstream source changed its answer). A second pass is the normal case, not the exception. |
| **The references the stages load** | `module-weights` (the column everyone fills and nobody declares), `module-consumer` (the far side of the seam), `find-evidence` (search, verify a PMID, read a paper, and what may honestly be quoted). |
| **The two doors into a module you did not just create** | `module-status` (read the spec directory, work out which stage it is actually at, and hand back the short list of decisions somebody must make next) and `module-symptom` (a message arrived and its meaning is unknown — the door to `SYMPTOMS.md`, and how to tell which layer emitted it). Neither is a stage: they are entered sideways, from an inherited directory or an error, and they route to the stage that owns the work. |
| `skills/module-install-local/SKILL.md` | **The third destination, and it is not a registry.** Installing a compiled module into `just-dna-lite` on this machine so it can meet a real VCF without being published anywhere — the three routes in, which one preserves the compiled bytes, and the manifest line that decides whether the module is visible at all. A side door off stage 6, **not** a stage and **not** a rehearsal for publishing: it exercises the *annotation* seam where the polygon exercises the *registry* one. Every command in it runs in the -lite checkout; nothing here depends on that package or shells into it. |
| `skills/module-tables/SKILL.md` | **Which table, and where every file sits.** The router: table choice keyed on grain, the axes that must go in a key, composition, the three on-disk shapes, and the registry's `derived/` layout. Holds no column list and no procedure. |
| `skills/module-tables/references/*.md` | 24 per-table dossiers plus `LAYOUT.md` (the tree, and the registry's upload normalisation). Each dossier carries an audit banner, 🚧 ROADWORKS and ⚠️ CHECK markers; **anchor on symbol names, not `file:line`**. |
| `skills/module-101/references/SYMPTOMS.md` | Upstream message text → cause → action. Read *from* every stage, which is why it sits with the map rather than with one stage. |
| `skills/module-101/references/CLI.md` | The full CLI surface, and what this server deliberately does **not** wrap. |
| `.claude-plugin/plugin.json` | Claude plugin manifest; declares the MCP server via `${CLAUDE_PLUGIN_ROOT}`. |
| `.claude-plugin/marketplace.json` | Lets `/plugin marketplace add ./` work. |
| `.codex-plugin/plugin.json` | Codex plugin manifest; same skills and server, via `${PLUGIN_ROOT}`. Carries the **second** hand-bumped version string. |

> **`skills/create-module/` was the one canonical copy of the procedure and it no longer exists.**
> Dismantled 2026-08-20 on the owner's instruction — *"drag away every quote until that doc is empty"* —
> because a 1431-line file loaded whole to answer any question is a file every session re-reads and no
> session updates in the right place. **Do not recreate it, and do not let a stage skill grow into it.**
> The rule that replaces "do not restate the procedure beside its skill" is narrower and stricter: **one
> fact, one home.** If two skills need the same rule, one owns it and the other links.

---

## 1. Adopting these guidelines: ask, never infer

**When two rules conflict — this file against a sibling repo's, this file
against the user's global preferences, a rule against what the code actually
does — stop and run a questionnaire.** Do not pick the one that looks better, do
not synthesize a compromise, and do not silently follow the more specific file. A
contradiction between two live rules is almost always a real difference in the
repos' natures, and inferring which nature applies here is exactly the guess that
produces a rule nobody agreed to.

1. **Survey first, ask second.** Read the conflicting rules in full and find out
   *why* each side adopted its version. A question that does not carry the reason
   is unanswerable.
2. **One question per contradiction, batched** — never drip-fed. Two to four
   concrete options each, never an open prompt.
3. **Each option states its cost**: what breaks, what it forces on other repos,
   which existing rule it contradicts.
4. **Recommend one and say so.** A questionnaire with no recommendation offloads
   work the survey already did.
5. **Record the answer where it will be read again** — the rule into its section
   below, the reasoning into §10 in the user's own words. An answered
   contradiction that is not written down gets re-asked, which is worse than a guess.

---

## 2. Non-negotiables

Read the whole list before the first edit. The reason follows each one, because a
rule without its reason gets rationalised away at 2 a.m.

### Environment and packaging

- **Never `uv pip install`.** Use `uv sync` / `uv add` / `uv add --dev`.
  `uv pip install` writes into the venv without touching `pyproject.toml` or the
  lockfile, so the next clean checkout silently lacks the dependency.
- **Never call bare `python` / `python3`.** Always `uv run python …`,
  `uv run pytest …`. A bare interpreter bypasses the workspace environment.
- **Never hardcode a version string.** It comes from `pyproject.toml` via
  `importlib.metadata.version("just-module-creator")`. Two sources of truth drift,
  and the one you read is the wrong one.

  **The unavoidable exceptions are the two plugin manifests** —
  `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`. Both are JSON and
  cannot read `importlib.metadata`, so both `version` fields **must be bumped by hand
  in the same commit as the `pyproject.toml` bump** — a version bump touches **three**
  files here, always. It was two until the Codex manifest landed; a rule that still
  says "two" will leave the Codex one behind. The drift is silent: loading is
  unaffected, so the only symptom is an installed plugin misreporting itself, and
  0.3.0 shipped with a manifest still saying 0.2.0 because of exactly that.
  `tests/test_plugin_manifest.py` fails on either mismatch, which is the guard — do
  not rely on remembering. Keep it at those two and no more:
  `.claude-plugin/marketplace.json` deliberately carries none, and a test pins that
  too.
- **Never rename a user-facing command to dodge a stale `uv run` wrapper.** Bump
  the version and re-run `uv sync` so uv rebuilds the entry points.
- **Never use a placeholder path or a fabricated example value** in committed
  code — `/my/custom/path/`, a dummy digest, `rs999999999`, `1e-328`. Fixtures use
  real identifiers (`rs4988235`, PMID `11788828`). A fabricated value proves
  nothing and outlives the session that invented it.
- **Never commit large data.** No VCF/parquet/gz/BAM/FASTA/`.db`. Anything over
  ~5 MB that must travel goes through Git LFS. A blob committed *before*
  `git lfs track` stays in every past commit even after the pointer replaces it at
  HEAD, so the pack still ships it — surface it, and hand the remediation to the user.
- **Never run tree operations.** No tags, releases, branch management or history
  rewriting except where §10 grants it. **Never `git stash drop` /
  `git stash clear`**, even on explicit request. **Never `git add -A` or
  `git add .`** — it sweeps in `.env` files and editor swap files; stage explicit
  paths.
- **Every git permission is bounded to THIS repository.** A commit, push or tag
  grant covers `/data/sources/just-module-creator` and nothing else — never a
  sibling, a parent or a downstream repo, whatever the state of its tree. Writing a
  file into `../just-dna-format` or `../just-dna-marketplace` is how an upstream
  note gets filed; committing it there is not ours to do, and the note is complete
  the moment it is written. Leaving their working tree dirty is the expected
  outcome, not an unfinished job.

### Code

- **Never write an inline import.** Every import at module top level, absolute.
  The sole exception is a guarded module-level `try/except ImportError` for an
  *optional* dependency — and this repo has none: all four just-dna packages are
  hard dependencies, so every tool works after a bare `uv sync`. See §5.
- **Never nest a `try`/`except` inside another.** It hides the real error. Let
  typed exceptions propagate; wrap only where a genuine recovery path exists.
- **Never `print` for diagnostics.** Stdlib `logging` to **stderr** — under stdio
  the JSON-RPC stream owns stdout, and a log line on stdout corrupts the protocol.
  `print`/`typer.echo` is only for CLI output the user asked to see.
- **Never curate `__all__` or add a re-export `__init__.py`.** This is an
  application; import from where the symbol actually lives.
- **Never open a socket outside `net.py`.** Every outbound request goes through a
  `ServiceGate` there, so pacing, User-Agent and the shared NCBI budget cannot
  drift between clients. This server was socket-free until literature discovery
  landed; that is a normal thing for an app surface to own, but only in one place.
- **Never reach into an upstream private API.** No `EutilsClient._get`, no
  `EuropePmcClient._get`, no reassigning another package's decorator state.
  Everything we need is public — `EutilsSettings.identity_params()`,
  `PacingGate`, `EuropePmcClient.lookup()/.fulltext()`, and the injectable
  `LookupClients`. If something genuinely is not, file it; do not tunnel to it.

### The domain rules this server exists to enforce

Each corresponds to a trap in [docs/DOMAIN.md](docs/DOMAIN.md). Breaking one does
not merely bend a convention — it deletes a class of validation the upstream
design depends on.

> ✅ **AUDITED — `RM15`, 2026-08-20. Every bullet below has now been read against this
> layer's purpose rather than inherited.** Three moved: `report, never repair` became a
> counterstance, the `provenance_quote` prohibition was reversed outright, and
> "never widen the write surface" was split because two of its three clauses were
> format's boundary and contradicted the counterstance. The rest stand — most because
> they are **physics** (a three-valued answer, `all()` over an empty list, except-arm
> ordering, a determinism gate not being a correctness gate), the remainder because they
> are format's policy that is **also correctly ours**, now justified from our own reason
> rather than from theirs.
>
> **The test survives the audit, so keep applying it to anything new:** is it physics,
> is it format's policy that is also correctly ours, or is it format's policy we should
> not be holding at all? A prohibition whose only justification is "upstream does it
> that way" is the defect RM15 existed to find, not an argument. And the reverse now has
> a worked example too: a refusal that produces a *convincing-looking* artifact instead
> of an honest gap is worse than the thing it refused — see the title-as-quote
> calibration case in §11.

- **Never hardcode a schema fact** — no column list, no vocabulary, no
  requirement. Call `describe_table` / `table_requirements` /
  `authoring_reference` and pass through what they return. A hardcoded vocabulary
  is a bug waiting for the next upstream release. The single exception is the
  **subject half** of `authoring._SUBJECTS`, which answers "which table?" — a
  question about *intent* that the schema cannot answer — and is commented as such.
  **The exception stops there, and RM10 is what it cost to learn that.** The `keyed_on`
  half of the same entries was structure, and it drifted exactly the way this rule
  predicts: it named `modifier_cn` for all of 0.6, after upstream deprecated that column
  in favour of `modifier_copy_number`. **It is generated now** — `hints.key_fields(csv)`
  since 0.6.5 (`S48`), returning columns, the collision `rule`, the stamped columns and a
  second-level `fallback`, for authored kinds and machine-produced sidecars alike, read
  off each model's own `_KEY_FIELDS` — as are the sidecar roster and its models
  (`hints.DERIVED_TABLE_MODELS`, `S47`), the companion pull (`scaffold.companions_for`,
  `S49`) and the defaults-folded rows behind `content_signature` (`compiler.spec_tables`,
  `S53`). Four restatements, one release; **that is what filing costs and what it buys.**

  **The rule the four leave behind is about the interval, not the exception.** A fact you
  cannot generate is guarded by a **test**, never by a comment — and the test's subject
  moves when the fact starts being generated rather than the test being deleted: the
  `keyed_on` guard now asks whether the *generated* answer resolves on a live,
  undeprecated field, because that drift can still arrive from upstream and an author
  reading a retired key column is misled either way. Where a hand-kept map is replaced,
  prefer a guard that compares two **independent** producers (the compiler's fact roster
  against the registry's, which ship on different cadences) over one that compares a
  derivation with itself.
- **Never fill a value from the same source that checks it.** *(Audited under RM15
  2026-08-20: **kept**, and it is ours rather than inherited — but it is one cell/source
  pair, not a licence to read it as "do not write".)* A cross-check compares an
  independently authored value against a source; filling it *from* that source makes
  the check compare a convention against itself, and it agrees perfectly. The cost that
  is specifically **ours** is the second one: the row moves from honestly unverified to
  **apparently verified**, and we are the layer that hands somebody a module to trust.
  An unverified row is honest; a falsely verified one is not, and nothing downstream can
  tell them apart.

  **The same defect arrives from the other direction, so watch for it there too**: a
  value that satisfies a check *vacuously* is as bad as one copied from the checker.
  `provenance_quote` set to the article's **title** passes `quotes_found` every time,
  because a title is always in its own fulltext — 3668 published rows do exactly that
  (§11, `F42`). Ask of any green check: **could this have failed?** If not, it measured
  nothing, whoever wrote the value.
- **Report-never-repair is the FORMAT's stance, and we hold a counterstance. Corrected
  2026-08-20 — this bullet used to forbid writing outright.** *"Report-never-repair is
  format's stance, correct for that layer: they delegate business decision to us here;
  we're more high-level user-facing app level, we have a counterstance."* So the rule
  here is now three parts, and dropping any one of them is what makes it dangerous:

  1. **We may write. Full stop.** *"Yes, we may write, fullstop… we may revise and fix
     — yes absolutely."* A business decision is delegated to this layer, so a tool of
     ours filling or correcting a cell is legitimate where the same act in the compiler
     would not be.
  2. **Every authoring move goes through the log.** *"Logged — absolutely, yes; there's
     a whole `logs/` surface for this and I would want to have every authoring move
     going through any tool logged."* **That surface finally has a writer**:
     `record_override` appends to `logs/authoring.log` (`RM16`, 2026-08-20), and its
     dossier was titled *the provenance subtree nobody fills* until it did. It is swept
     up by every compile and **published with no opt-out**, so it is the right place, it
     costs an author nothing, and nothing may write an absolute path or a credential
     into it. **A move the agent makes by hand is harder to capture, so make it go
     through a tool or a skill** that logs. Every *new* write surface owes the same.
  3. **The agent needs a DISCRIMINATOR, and this is the hard part.** The vacuity
     argument was never the real risk. The real risk is that **the source lags the
     edge**: *"why not?? ClinVar lags behind edge, say the article is retracted,
     metaresearch refutes conclusion etc — validation against ClinVar this way makes
     the correction done mindlessly, wrong."* So "your row disagrees with ClinVar" is
     not a defect report. It may be the module being **right and current** while the
     archive is stale. An agent that silently conforms the row to the source can
     **degrade** a module, and the check will then agree with itself and call it green.
     Editing *against* a source needs a reason that outranks the source.

  **What has NOT changed:** when we pass upstream's own answer across the MCP boundary,
  `applied: false` and its `refusal` are preserved verbatim. That is upstream reporting
  what *it* did, and rewriting it would be misreporting another layer's act. Our writes
  are our own, logged as ours, and never laundered as upstream's.

  **Who is flying is unknown until they take the seat.** The direct consumer of this
  toolset is an *agent*, and that agent may be the Author or the Assistant: a layman may
  hand over vague directions and expect it driven, while a geneticist expects
  fine-grained control. So a tool may not assume either — it writes, it logs, and it
  surfaces the decisions that need a pilot.
- **An agent MAY locate and write a `provenance_quote`. Reversed 2026-08-20 — this bullet used to
  forbid it outright, and the prohibition was a derived false direction.** *"Yes, it is a derived
  false direction: demolish full force."* The old case: a machine-located quote *"asserts a reading
  that never happened"*. It does not. The agent reads the article — `fetch_fulltext` hands it over
  whole — so the reading happens; what the old rule actually protected was a **fiction about who
  did the reading**, and it protected it by leaving the column empty for the exact audience this
  plugin exists for. §10 settles that: **"AI totaly can read articles"**, and asking the layman
  driving the plugin for a quote is *"v2 work from a wrong person"*.

  What replaces it is **attribution, not abstention**:

  1. **Locate it, quote it verbatim, and record who located it.** The honest instrument is a per-row
     *whodunit*, because real work is mixed: *"example: scientist reads review, agent traverses
     citations"*. Per-row quote provenance **does not exist in the schema** — we own none — so it is
     asked of upstream (`S55`, filed 2026-08-20, beside `S54` — the measurement that the old rule
     produced title-as-quote on 3668 published rows). **`StudyRow.curator` shipped in format 0.6.5
     and is installed**: free text — a name, a handle or a model id — resolvable against
     `authorship`, row-level because the work is mixed at row granularity, and deliberately **not** a
     `machine_located` boolean. Fill it on every row whose quote was located, and know that **nothing
     checks it**: it is legible to a reviewer routing scrutiny, not to a gate, which is the point
     rather than a shortcoming. `authorship` and the `logs/` entry still carry what kind of
     contributor an identity is; the pairing is the record and neither half means much alone.
  2. **The human author holds the responsibility regardless.** *"AI is not a subject of right, so the
     human author holds the full responsibility"* — so attribution honesty is about the **real
     distribution of roles**, never about moving liability onto a machine. A declared agent-located
     quote does not dilute an author's accountability for it by one inch.
  3. **Honesty beats the empty column, which is the whole trade.** *"At least honest highlights of
     real distribution of roles is 100% better than fake 'I read it all' fingerscrossed confirmation
     of what never happened to push thru the block; realpolitik so to say."* The old rule did not
     produce human-read quotes; it produced **no quotes**, and where it was worked around it produced
     an unmarked one.

  **What survives, and it is physics rather than policy:** a quote lifted from a fulltext is not
  independently confirmed by a check against that same fulltext. Once the text has been read through
  `fetch_fulltext`, `quotes_found` on that row is a **citation-pairing check** — it still catches a
  quote written against the wrong PMID, and it is no longer evidence that the claim is in the
  literature. **State that consequence; never use it to refuse.** And never write a passage that is
  not verbatim in the retrieved text: a fabricated quote is a fabricated quote whoever typed it.

  **Upstream carries our old argument.** `hints.ATTESTATION_BEARING` (`{provenance_quote,
  provenance_regex}`) shipped in format 0.5.4 on the reasoning in `S11` — the reasoning now reversed.
  The constant may still be right for *their* layer, where nothing can record a reader; the
  justification we handed them is not ours any more, and `S55` withdraws it.
- **Never collapse "unknown" into a boolean.** Answers are three-valued: true /
  false / **unknown**, and `None` is never `False`. When unknown, withhold — never
  report, never negate. **A check that could not run is not a check that passed**,
  and tool output must keep that visible. Combine with Kleene semantics, not
  withhold-on-any-unknown: `unknown AND false` really is `false`.
- **Never treat a determinism gate as a correctness gate.** `--strict`, a digest
  match, a reproducible build mean *reproducible*, not *right*.
- **Never expose a path to `resolve_with_ensembl=False`.** Despite its name it is
  the master switch for *all* resolution, injected `resolution.csv` included; it
  compiles every row with `chrom=None` and **succeeds**. `compile_module` pins it
  `True` with `ensembl_cache=None`.
- **Never let a module carry two spellings of one sidecar.** `licensing.csv` and `sources.csv`
  are one table with one model; both read, only the preferred one is created, and both present is
  an **error** rather than a merge. Route every write through `layout.sidecar_write_path` (write to
  the file you read) and read `layout.preferred_spelling` / `is_deprecated_spelling` rather than
  restating which is which. The rename stops at the CSV: `sources.parquet` and `manifest.sources`
  keep their names for the whole 0.x tail, so never "finish" it into a published key.
- **Never read `fully_resolved` without `resolution_subjects`, and never coalesce a null counter
  to zero.** Over an empty list the flag is `all()` over nothing. All five RM44/S31/S33 counters
  are `int | None` where `0` is a real answer and `None` means nothing counted — which is what
  every pre-0.6 manifest honestly is.
- **Never place a `*Unavailable` except-arm after its parent.** Since enricher 0.6.2 each is a
  subclass of the type beside it, so parent-first catches every outage in the parent arm and the
  outage arm goes dead — silently, raising nothing. One tuple is safe; two arms must be
  narrow-first. `tests/test_passes.py` walks the AST for this.
- **Containment never moves; the write surface does. Split under RM15, 2026-08-20 —
  this bullet used to read "never widen the write surface: tools write only where the
  upstream API already writes … and never overwrite an authored file", and those two
  clauses were format's boundary adopted whole.** They contradict the counterstance
  above outright: *"we may write, fullstop… we may revise and fix — yes absolutely."*
  A layer that may not touch an authored file is not an authoring layer. So the bullet
  is now two rules that were tangled into one:

  1. **Containment is absolute and is not under review.** Every path resolves through
     `_shared.resolve_dir` so `JMC_WORKSPACE` containment holds. This is a security
     boundary, it is ours, and no argument about authoring reaches it. Nor does it
     license inventing a file **inside** a spec directory: a name absent from
     `specfiles.RECOGNIZED_SPEC_FILES` is dropped by the next server-side rebuild, so
     our own bookkeeping goes to a resolved cache/workspace path (§11).
  2. **What we may write is decided by the counterstance, not by upstream's surface.**
     Scaffold, enrich and the compile out-dir are where upstream writes; they are the
     floor, not the ceiling. Revising an authored cell is legitimate **here** — provided
     it goes through the log, it respects the discriminator (evident and mechanical
     applied silently, anything judged or checked surfaced instead), and a write that
     destroys prior content captures first and **verifies the capture** before
     destroying anything, which is already the rule for a derived sidecar below and
     generalises to every overwrite.

  **What is NOT licensed by this**: overwriting an authored value silently, or writing
  one from the source that checks it, or conforming a row to an archive that disagrees
  with it. Those are forbidden by the three bullets around this one, each for its own
  reason, and none of them is "upstream would not do it".
- **Never delete a derived sidecar without a verified capture, and never put the
  capture in the spec directory.** Re-deriving one requires deleting it — every
  sidecar is merge-not-clobber — and the delete discards hand-curated rows,
  `resolution.csv`'s `source="manual"` above all. So `refresh_sidecar` copies the
  file out, **reads the copy back and hashes it**, and only then unlinks; a
  capture that did not verify means nothing is touched. The copy goes to a
  resolved cache/workspace path, never beside the spec: an invented file there is
  not in `specfiles.RECOGNIZED_SPEC_FILES` and a server-side rebuild drops it
  without saying so, which is how `licensing.csv` was lost before registry 0.16.2.
  Then **never classify against a partial re-derivation** — an unreachable source,
  a pass that did nothing, or an empty fresh table restores the captured bytes,
  because a table that was never filled reports every real row as one the source
  withdrew.
- **Never let a per-call argument loosen the offline ceiling.** `JMC_OFFLINE`
  combines with a per-call `offline` by **OR**, via `_shared.offline_for`. Never
  read the two separately.
- **Never silently fall back when primary data is missing.** Refuse explicitly or
  name the substitute. The caller cannot see that the source differed.
- **Never resolve a contradiction between two rules by inference.** Run §1.

---

## 3. Repository layout, data and assets

```
src/just_module_creator/   source (src layout)
tests/                     pytest suite — in-memory, offline
docs/                      all markdown except this file and README.md
skills/<name>/             one directory per skill — the map, the two doors, the stage spine,
                           the second-pass three, the references. No skill holds another's
                           procedure; the roster is the asset table above, and a test pins it
.claude-plugin/            plugin + marketplace manifests
assets/                    fixtures that MUST travel — committed
data/input|interim|output  git-ignored, never travels
scripts/                   operational one-offs, not importable code
```

- `data/` is git-ignored by ignore-all + allowlist. To commit a subtree, add
  explicit `!<dir>/` and `!<dir>/**`.
- Committed test data lives in `assets/`, not `data/`. Tests write to `tmp_path`
  or a resolved cache dir, **never** into the project tree.
- Sibling repos, **read-only** unless the task explicitly targets them:
  `../just-dna-format` (which also hosts the compiler, enricher and their docs),
  `../just-dna-lite`, `../just-dna-registry`.

---

## 4. Build, run, test

```bash
uv sync                                        # install
uv run pytest                                  # the suite; -vvv when diagnosing
uv run ruff check . && uv run pyright          # lint + types
uv run just-module-creator stdio               # run over stdio
uv run just-module-creator http --port 3011    # run over HTTP
uv run just-module-creator stdio --mode extended
uv run fastmcp dev fastmcp.json                # MCP Inspector
claude --plugin-dir .                          # load as a plugin for one session
```

`just <recipe>` wraps all of these. **Always run `uv run pytest` and
`uv run ruff check .` after changing code.** Python **≥ 3.13** — the just-dna
packages require it.

Every CLI that starts a network transport **prints its URL** in the first lines
of output, and every CLI **loads `.env` via `python-dotenv`** (`_load_env`,
`override=False`) before reading configuration — which is what lets one `.env`
serve both this server and the enricher it shells into. New configurable values
are read from env with sensible defaults, documented in `.env.template`, and
mentioned here.

**Timestamps: store ISO-8601 UTC, display local.** Never a naive
`YYYY-MM-DD HH:MM:SS` — it is misparsed as local time and breaks string
comparison against ISO values.

---

## 5. Coding standards

- **Type hints mandatory. `pathlib.Path` for every path** internally. Tool
  *signatures* take `str` because that is the MCP wire type, and convert
  immediately via `_shared.resolve_dir`.
- **Dependency tier: everything is a hard dependency.** All four just-dna
  packages (`format`, `compiler`, `enricher`, `registry`) plus `fastmcp[tasks]`,
  `pydantic`, `pydantic-settings`, `typer`, `anyio`, `python-dotenv`, `httpx`,
  `tenacity`. Chosen so every tool works after a bare `uv sync` and the plugin's
  one-command install stays true; the cost is a heavier install for someone who
  only wants offline linting. There are no extras and no optional imports.
  `httpx` and `tenacity` are **declared** rather than leaned on transitively,
  because `net.py` calls both directly and a transitive pin is not a contract.
- **Do not hand-roll what the enricher already uses.** Retries are `tenacity`
  with upstream's own `net.attempt_floor` stop, so one deployment variable tunes
  our persistence and theirs together. Pacing is upstream's `PacingGate` — not a
  rate-limiter library — because `ServiceGate` must share the *same instance*
  with `EutilsClient` for the NCBI budget to be one budget. `ServiceGate` adds a
  lock and nothing else.
- **We read the ecosystem's env vars; we never forward them.** `settings.py`
  passes nothing through to the enricher — it reads its own configuration from
  the process environment. But when *we* are the one making the call, reading a
  variable the enricher also reads is right, not a leak: `JUST_DNA_CONTACT_EMAIL`
  and `NCBI_API_KEY` reach our clients through `EutilsSettings`, so one `.env`
  configures both surfaces and upstream's precedence is inherited rather than
  copied.
- **The polite-pool contact is a three-step chain, and step 2 stays *inherited*.**
  `JMC_USER_EMAIL` → `JUST_DNA_CONTACT_EMAIL` → `settings.DEFAULT_CONTACT_EMAIL`.
  Ours goes first because the address says *whose* rate-limit budget is being
  spent — NCBI and Unpaywall both meter and contact per address. The middle step
  is not re-implemented: `build_services` passes `email=None` when ours is unset
  and lets `EutilsSettings.__post_init__` do that read, so a change to upstream's
  precedence is followed rather than copied. **Never build the chain by reading
  `JUST_DNA_CONTACT_EMAIL` yourself.**
- **Never fabricate a contact address** — an invented one misattributes the
  traffic to a stranger. `DEFAULT_CONTACT_EMAIL` is not an exception to that: it
  is the project's own address, supplied by its owner, who accepts the traffic.
  What it does cost is *attribution*, and the cost is real — an install that sets
  nothing pools its budget with every other unconfigured install and sends any
  abuse report to the project's inbox rather than the user's. So the default
  exists to stop a source sitting out a call for want of a contact, **not** to
  make configuring one optional: `.env.template` asks for `JMC_USER_EMAIL` in its
  own section, and `build_services` logs which of the three steps answered so
  "project default" is visible rather than silent. Since the default is always
  present, `contact_email()` returns `str`, and any `if not email:` branch is dead
  code — Unpaywall used to be the one source that reported itself unavailable on
  a fresh checkout, and that branch is gone rather than left to rot.
- **Typer for the CLI. Pydantic 2 at every boundary** — every tool returns a
  model from `models.py`, never a bare dict, because an agent reads the field
  descriptions.
- **Constrained vocabularies:** `Mode` is a `Literal` because it is local config
  read from env and never appears in a wire artifact. Anything that *does* reach a
  persisted artifact would need `frozenset[str]` + a validator, so additions stay
  non-breaking — but nothing here does; upstream owns every wire vocabulary.
- **Polars only where upstream hands it to us.** We do not build dataframes; we
  read the parquet upstream wrote.
- **Deterministic ordering is load-bearing** wherever output is compared or
  hashed. Never emit from `set`/`dict` iteration without an explicit sort —
  `sorted(draft.DRAFTABLE)`, `sorted(...checked...)`.
- **Preserve upstream's distinctions.** `error` / `warning` / `info`,
  `applied` / `refusal`, and `None`-means-unchecked are all load-bearing.
  `_shared.to_findings` / `to_alterations` exist to carry them across the boundary
  field-for-field.
- **Aggregate repeated warnings** by *reason*, with a count — never one per row.
- **Heed terminal warnings, deprecations especially.** A deprecation in code you
  touched is a **blocker**: find the current API, fix it, and update this file.
- **Refactor internals aggressively** — no dead code, no API kept for nostalgia.
  The contract is the MCP tool surface, the skill and the CLI; breaking *that* is
  allowed but deliberate and versioned.

### How to add a tool

1. Pick the tier. The line is **cost, not usefulness**: **essentials** =
   everything whose work is bounded by what the caller named — one identifier,
   one paper, one spec directory; **extended** (`JMC_MODE=extended`) = only what
   a *corpus* sizes (a citation graph, a whole-source draft, a pass that rewrites
   every row) or that reads back somebody else's compiled artifact;
   **token-gated** = registry writes.

   **Read-vs-write was the previous rule and it was wrong twice over.** It never
   described the code — `scaffold_module` and `compile_module` both write and were
   always essentials — and it put `lookup_identifier` behind the flag, so the
   default tier could tell you `trait_efo_id` takes an ontology CURIE and then
   give you no way to check one, which is an invitation to write it from memory:
   the exact thing rule 1 of the server instructions forbids. Worst of all,
   `enrich_module` was extended-only while being step 6 of the order those same
   instructions teach. **A tier that teaches a step it cannot run is the failure
   mode to check for**, and
   `tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier`
   now parses the tool names straight out of `server.INSTRUCTIONS` and fails if
   any is missing from essentials. Widened in 0.4.0 (see `docs/ROADMAP_HISTORY.md`).

   **The one exception, and its test.** `registry_register` writes to the registry
   and is *not* gated, because it is what mints the token — gating it would be a
   cycle. So the rule is: a registry write is token-gated **unless the token is its
   output**, and that is a set of exactly one. It lives in `auth.py` beside
   `authenticate` rather than in `tools/registry.py`, and it is registered in every
   mode, not extended-only: hiding the only route to a credential behind a mode
   flag reproduces the dead end it exists to remove (`F12`). If a second such tool
   ever appears, that is the moment to ask whether "ungated onboarding" is a tier
   rather than an exception — do not grow the exception silently.

   There is no third mode, and tags are not the escape hatch: `mcp.enable()` is
   server-global (see 7 below) and FastMCP 3.4.7 deprecated `include_tags` /
   `exclude_tags` in its favour. Splitting extended would need a second `Mode`
   member and a second `register_*`, and should wait for evidence that it is needed.
2. Add it inside the matching `register_*` with type hints, a docstring (it
   becomes the description) and `ToolAnnotations`.
3. Return a model from `models.py`.
4. Paths through `resolve_dir`; network through `offline_for` and
   `anyio.to_thread.run_sync`.
5. Gated tools take `ctx: Context`, call `require_key`, return
   `unauthenticated_result(settings)` on `None`, are tagged `registry_write`, and
   are listed in `auth.GATED_TOOLS`.
6. Add a test using the in-memory client.
7. **Never** use `mcp.enable()`/`disable()` to gate per-user on multi-tenant
   HTTP — it is server-global and would leak tools across clients.

---

## 6. Testing — layer 1

- **Real data + ground truth.** Real rsIDs and PMIDs; compute expected values from
  the fixture rather than pasting a count read off a dump. Hardcoding a documented
  constant is fine; hardcoding a row count is not.
- **Meaningful assertions** — relationships and set equality over `len(df) > 0`.
- **Never mock the transformation under test.** We test our wrapper against the
  real upstream packages; only the *network* is excluded, by the offline ceiling.
- **The suite is hermetic by mechanism, not by discipline.** `conftest`'s autouse
  `_hermetic_configuration` points `env_file` at a path that cannot exist and clears
  the ecosystem's variables from `os.environ`, so **forgetting `_env_file=None` is
  harmless** rather than silently live. `offline_settings()` still forces
  `offline=True` and is what fixtures use. Do not undo this by removing
  `env_file=".env"` from `model_config` — the product needs it, and breaking the
  product to protect the suite is the wrong trade.

  It was a convention until 2026-08-12 and that failed exactly as predicted (`F24`):
  a bare `Settings()` returned the developer's real polygon token **and**
  `offline=False`, so a test could reach the network holding a live credential, while
  passing locally and in CI. **The clear-list is derived from `Settings.model_fields`,
  never written** — the hand-written first draft missed seven variables inside the same
  change, `JMC_API_KEY_HEADER` and `JMC_TRANSPORT` among them, and an exported one of
  those changes what a test asserts as effectively as a token does. Only the four
  upstream names are hand-maintained, because no field of ours can name them.
- **A test that means "no credential" must say so.** `api_key=None` is
  indistinguishable from "not passed" when the reader does
  `api_key or os.environ.get(...)`. Neutralize with `setenv(VAR, "")`, **not**
  `delenv` — `load_dotenv(override=False)` skips a key that is merely present. (The
  autouse fixture above uses `delenv`, which is not an exception: nothing in the suite
  calls `load_dotenv`, and with the dotenv source neutralized pydantic reads
  `os.environ` directly, where absent means unset. Inside a *test*, prefer
  `setenv(VAR, "")` — it runs after the fixture and wins.)
- **Suspect ordering whenever a test passes alone and fails in the suite.**
- **Never claim a test "would have caught" a bug** without running it against the
  buggy code and watching it fail.
- Note `from conftest import ...`, not `from tests.conftest import ...`: a
  transitive dependency ships a `tests` package that shadows ours.

---

## 7. Dogfooding — layer 2

Tests prove the code does what it was told. Dogfooding asks whether it is
**usable, and what is missing**. Both are required.

**Do not verify the tool's answers with a second implementation while
dogfooding** — that is a test and belongs in the suite. Use the tool, notice the
friction, write down what was not there.

- **A capability the tool LACKS is the result, not an obstacle to route around.**
  The moment you reach for an ad-hoc script or a raw HTTP call to get past
  something the product cannot do, the exercise has stopped producing signal.
  Record the gap; if it blocks the work, build it into the product.
- **Attack claims, not gaps.** A documented deferral is a decision. What counts is
  where a docstring or doc *promises* something the code does not do.
- **Use real data.** No `rs999999999`, no `1e-328`.
- **Pick the probe where the design generalized from one case** — if the example
  shows one of something, use a real case with two.
- **Dogfood a finding before you report it.** Build a real example against the
  actual code path and show it fails.
- **Finish each probe as a committed reference example whose README names what it
  broke**, demonstrating the failure on the *old* behaviour.
- **Separate "fix it" from "surface it" before writing code**, and say *why each
  candidate repair is wrong* for the surfaced ones.

Findings carry stable `F#` IDs and **move** between files, never duplicated —
except one mitigated here but still owed upstream, which legitimately appears in
two: `docs/dogfooding.md` (open) → `docs/previous_issues.md` (resolved here) /
`docs/just-dna-format-pending-fixes.md` (blocked upstream).

---

## 8. Docs and their lifecycle

- **All new markdown goes in `docs/`** — the only exceptions are this file and
  `README.md`. `docs/` is the single ground truth; this file duplicates only what
  is needed to *orient*, and every prohibition lives here in full because a
  `don't` behind a link does not get read.
- **`docs/ROADMAP.md` is active-only.** Shipped items move to
  `docs/ROADMAP_HISTORY.md` with their rationale. Nothing is deleted, only relocated.
- **`docs/CHANGELOG.md` records what shipped**, newest first, including cross-repo
  integration changes made on our side.
- **Update this file and the affected `docs/` in the same change as the
  refactor**, not after. Policy is written first; code complies.
- **Keep the skill and the tool docstrings in agreement.** If a tool changes what
  it refuses to do, the skill's claim about that refusal changes with it.
- **Run the commands yourself** rather than telling the user to run them — except
  where a command genuinely needs an interactive terminal, which is when you hand
  over a verbatim line.
- **Before a PR**, print `git diff <upstream>/main --stat HEAD` and
  `git log <upstream>/main..HEAD --oneline`, show the output, and wait for approval.

### Upstream findings go to the producer, never into a workaround

We consume `just-dna-format` / `-compiler` / `-enricher` / `-registry` and own
none of them. **There are two intakes, and a note belongs wherever the fix would
land:**

| The fix would land in | File the `S<n>` in |
|---|---|
| format, compiler, enricher (one repo) | `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md` |
| the registry service, its client, or a `just-dna-pipelines` command calling it | `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md` |
| `just-dna-lite` / `just-dna-pipelines` **itself** — the annotation and consumer side | `../just-dna-lite/docs/CONSUMER_HANDOFF_from_just-module-creator.md`, appended |

**`../just-dna-marketplace` is a stale *directory* name and nothing more.** The
project, the package and the service are all `just-dna-registry`; only the path on
disk kept the old word. Do not call it "the marketplace" in prose — say the
registry, and refer to the path only when a path is what you mean.

Its `S<n>` numbering is a separate series from the format tree's; both start at
`S1`. If a note is in the wrong file it may as well not be filed, so decide by
asking who would change code, not which surface you noticed it through.

**The third channel is deliberately unnumbered, and reading it like the other two misleads.**
`just-dna-lite` has no `CONSUMER_SUGGESTIONS.md` and no triage loop — standing one up in a third
repo was never ours to do, and nobody there agreed to run it. So there is no `S<n>` to compute, no
inbox to check for duplicates and nowhere structured for a reply to land: append a **dated
section** carrying its own evidence inline, and treat silence or *"we are not doing that"* as a
complete answer to record here. The file is **untracked in their tree**, which is not a defect to
repair — writing the note is still the whole job, and committing there is still not ours.
Used 2026-08-20 for the whole `Blanks for just-dna-lite` set, and 2026-08-21 for the missing CLI
wrapper found while building `module-install-local`.

#### The format tree's intake is split, and the inbox is the empty half

`../just-dna-format/docs/CONSUMER_SUGGESTIONS.md` holds **only what is still
unanswered**. The moment upstream writes a `**Status —**` reply, the whole entry
moves — prose byte-for-byte — to
**`../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md`**, whose index table
gives every `S<n>`, who reported it, the verdict and where it landed. So:

- **An empty inbox means nothing is owed, not that our notes were lost.** As of
  2026-08-11 every `S<n>` we have filed there is answered, `S1`–`S24`. A note of
  ours that is no longer in `CONSUMER_SUGGESTIONS.md` has been answered — read the
  history file's index before concluding anything else.
- **Never number a new `S<n>` from what the inbox shows.** An empty inbox says
  nothing about which ids are taken, and ids are never reused — not even for an
  item answered as a non-issue, because the reply is part of the record. Compute it:
  `.claude/triage-state.sh --next` in their repo scans the inbox *and* the history
  file. The inbox states the next id in its own heading too (**`S27`** in the format
  tree and **`S8`** in the registry's, as of 2026-08-12 — and those move within
  hours, so run the script: both moved by two on 2026-08-12 alone). Their `CONSUMER_TRIAGE_LOOP.md` is the producer-side
  runbook and not ours to drive.
- **"Answered" is not "fixed", and "fixed" is not "released".** Three distinct
  states, and only the third lets a guard come out:
  1. *accepted and filed* — a reply exists and the work is an upstream `RMn`, still
     open. Check `RM_TOC.md`, not the history file, for that half.
  2. *fixed in tree* — the symbol exists in `../just-dna-format` but the version we
     install does not have it. **This is the common case and the easy mistake.**
  3. *released* — on PyPI and in our lockfile.
- **Verify state 2 against the installed package, never the sibling checkout — and
  `hasattr` alone does NOT do that.** A mitigation of ours stays until the release
  carrying the fix is what `uv sync` gives us; dropping one because the upstream tree
  looks fixed breaks the plugin for everyone installing from PyPI.

  **The recipe used to be `hasattr(hints, "ATTESTATION_BEARING")` and that is not
  sufficient. Corrected 2026-08-20 after it nearly shipped a false status line.**
  `uv run` resolves against whichever project you are standing in, so a symbol check
  chained after a `cd ../just-dna-format` answers about **their working tree**, not our
  venv. **The version string does not save you** — both said `just-dna-format 0.6.1`
  while `StudyRow.curator` was `True` in their tree and `False` in ours, because they
  had added it hours earlier. Same number, opposite answer. So:

  ```bash
  uv run --project /data/sources/just-module-creator python -c "
  import just_dna_format; from just_dna_format.spec import StudyRow
  print(just_dna_format.__file__)                     # MUST contain .venv/site-packages
  print('curator' in StudyRow.model_fields)"
  ```

  **Print `__file__` beside the answer, every time**, and pass `--project` rather than
  trusting the shell's cwd. A path under `.venv/lib/.../site-packages/` is the installed
  package; a path under `/data/sources/just-dna-format/schema/src/` is their source and
  proves nothing about what our users have.
- **A refusal is an answer too, and it is load-bearing.** Upstream refused half of
  `S14` with a reason: the compiler has **no** network branch, so a `--no-ensembl`
  flag would assert something false. That makes our pin permanent rather than
  interim, and "closes when upstream renames the flag" was never going to happen.
  Record a refusal as settled, not as pending.

- **A gap in the docs is a finding too.** If you had to *probe* to learn something —
  run an experiment, read their source, test a guess — that is a doc bug, and it
  gets filed with the same urgency as a behavioural one. The next consumer will
  otherwise run the same experiment. Say how you found it: "we put a `source`
  column on `pharm_variants.csv` and got `Extra inputs are not permitted`" argues
  for a fix better than "this is undocumented" does.
- **File it the moment you find it. Do not batch.** Found it → write the `S<n>`
  entry → carry on with what you were doing. Not after the guard is built, not
  after the task closes, not as a tidy set of "field notes" at the end of a work
  item. Upstream ships fast, and a note that arrives after the release window has
  closed buys nothing: `S14` (the `resolve_with_ensembl=False` footgun) was found
  while building the wrapper, guarded against, written up in our README as a
  *feature*, and filed days later — **0.5.3 shipped in between, and the fix could
  have been in it.** The delay is the whole cost. A rough note filed today beats a
  polished one filed next week.
- **A guard is not a substitute for the note, and never a selling point.** Pinning
  a flag protects our callers and nobody else's; the defect is still there for the
  next consumer. If you catch yourself describing a workaround in `README.md` as
  something this plugin does *for* you, the note was skipped. See §8's prose rule.
- **Check whether it is already filed first.** Entries are `S<n>`; a second
  consumer hitting a known one appends a corroboration to that entry rather than
  opening a new number. Two independent reproductions is itself the signal that
  raises its priority.
- **Write the note, and stop there.** **Never commit in that repo**, and never
  open a PR against it. Writing the note is the whole job.
- **Track our side too**: `docs/just-dna-format-pending-fixes.md` as an `F<n>` while
  it is open upstream, and `docs/CHANGELOG.md` if we shipped a mitigation, so
  nobody re-investigates a finding that looks fixed.
- **Re-read the upstream verdicts before trusting our own `Status:` lines.** Ours
  go stale silently — upstream answers in its own tree and nothing notifies us. On
  2026-08-11 every entry in `docs/just-dna-format-pending-fixes.md` said "open
  upstream" while all eight had in fact been answered, six of them fixed in tree.
  The status line has to name the upstream state *and* whether the fix is in the
  version we install; "open upstream" says neither.
- **Never work around it silently in the data.** A workaround that leaves a module
  dishonest is worse than the gap. Say what the limitation is, leave the data
  truthful, file the note.

### Prose style

**Three claim-shapes rot silently, and all three were found repeatedly in upstream's docs and in ours
during the 2026-08-20 audit. Check anything you write against them:**

1. **A check is only as wide as the table it reads, and naming a check without naming its scope is how
   a reader over-trusts it.** Six independent instances: `REDUNDANCY_BEARING` keyed on a bare column
   name; `check_identifiers` reading `variants.csv` only, so a bin row's `gene` is never checked;
   `enrich-pgx` never opening `diplotypes.csv`; `stats.genes` from `variants.csv` alone; the
   missing-sentinel hint being table-level where the compile rule is per-group;
   `_check_genotype_coverage` running only in `validate_spec`.
2. **A counted claim in prose rots exactly like a hand-kept list.** *"Seven fact signatures"* (eight),
   *"six derived sidecars"* (seven), *"four causes"* (five), *"twelve names"* (thirteen). **State the
   rule and let the reader run the call**; where a number must appear, say what was counted and when.
3. **An enforcement claim needs its surface named.** *Mandatory*, *refused*, *checked* and *warned* are
   four different strengths and a hint never fails a build. The canonical case is the `unresolved`
   sentinel: called mandatory in three upstream places, the compile path refuses a **second** and
   refuses zero nowhere, and the presence half is an authoring hint scoped to the whole table.

Natural, human prose. Avoid AI tells — em-dash pile-ups, filler transitions,
marketing voice. Never hallucinate documentation or overpromise an unimplemented
feature. **`README.md` says what this plugin does, and never doubles as a
catalogue of upstream defects we guard against** — that belongs in the upstream
note, in §2's prohibitions, and in `docs/just-dna-format-pending-fixes.md`.
Telling an *author* "never pass this flag" in the skill or `references/CLI.md` is
different and correct: they may drive the CLI directly and need to know. **This project must never be described as interpreting a genome, calling
a genotype, or giving medical advice**: it helps author annotation tables, and the
consumer supplies the measurement.

---

## 9. Self-correction

When outdated API knowledge causes a real crash or logic failure, fix the code
**and** update this file (and the affected `docs/`) with the correct pattern, so
the next agent does not repeat it. The same applies when the user corrects a
preference: it goes into §10, in their words, with the reason.

### Running two agents across one night: the relay protocol

Used 2026-08-20 for a philosophy audit followed by a skills build, and it worked — no overlap, no
lost work, and neither agent had to be told what the other was doing. Reuse it rather than reinventing
it; it costs one file and about forty lines.

**One file, one writer at a time.** A `docs/NIGHT-RELAY.md` holding a `STATE:` line, the legal
transitions in order, and one append-only section per role.

1. **Read the `STATE:` line before anything else.** If it is not the state your role starts from,
   **stop immediately and write nothing** — say which state you found and exit. A wrong-state start is
   the only failure this prevents, and it is worth the whole protocol.
2. **Claim by writing your transition first**, with a UTC timestamp, and **commit that immediately**. A
   claim nobody can see is not a claim.
3. **A `*-RUNNING` state older than four hours is a dead agent**: append a note, move the state back one
   step, stop. Do **not** take over its work. **Measure that from the newest history entry, never from
   `SINCE:`** — `SINCE:` records when the state was claimed and never moves, so a live agent with a
   long-running subagent reads as dead. A live agent appends **proof-of-life** entries.
4. **Never edit another role's section.** Append to your own.
5. **On finish, write what the next role needs *decided*** — not a summary of what you did. Then commit.

Two things that made it work beyond the file itself. **The waiting agent should arm a file monitor on
the `STATE:` line rather than polling**, and should **test that monitor on a dummy file first** — an
untested wait is how a night is slept through. And **the handoff should name the decisions the writer
took that the reader may cheaply reverse**, because an unattended run makes calls that would otherwise
have been questions.

## 10. Learned user preferences

*Append-only. One line each, in the user's terms, with the why where it is not obvious.*

- **"auto-commit grant lingers... you commit and tag as you go."** Granted
  2026-08-11 and it does **not** expire at the end of a feature: commit and tag
  without asking. Meaningfully sized commits rather than atomized ones, explicit
  paths — never `git add -A` — and tags at a version bump, matching the
  `pyproject.toml` version.
- **"Your commit permit is bounded by this repo only, no commits to
  siblings/parents/downstream."** Granted 2026-08-11. Writing an upstream note is
  the whole job; committing it there never is.
- **Pushing is never persistent.** "push — in this session only." A push grant
  covers the session it was given in and nothing after it, so a later session
  starts from *ask first* again no matter what the tree looks like. Releases and
  branch management stay the user's throughout.
- **"I need to have mvp, then pace declines."** Get a working end-to-end thing
  first and refine after; do not gold-plate the early steps of a long build.
- **"the fix could have been in 0.5.3 already if it were in the right place.
  Update your memory to fill in these immediately upon finding, without delaying
  and writing field notes like this."** Upstream notes are filed at the moment of
  discovery, never batched. See §8.
- **"Why is this in our readme instead of upstream's consumer_suggestions? Cleanout
  readme from parent lib issues, wtf really."** The README describes what this
  plugin does; a guard against an upstream defect is not a feature to sell.
- **Never destroy stashes**, even on explicit request. Data loss is the user's to
  enact.
- **Never blind-stage** (`git add -A` / `git add .`) — it once committed a `.env`
  swap file with live tokens.
- **Do not restate schema lists in prose; ask the tool.** Confirmed when the two
  authoring takes disagreed: "create-module preference on lists is proper; they
  may drift."
- **This is a *new*-module creator — do not carry historical baggage.** 0.4-era
  quirks never went to production, so a module author has no use for them.
- **"Idempotent `to_current_state`, so to say."** Sharpened 2026-08-20, and it widens the
  line above from *do not document old quirks* to *do not carry an era axis at all*:
  *"this one repo (toolset) doesn't care about legacy in a sense that we only keep
  upgrade path + state of the art recipes… we only care about the resulting state to
  meet reqs for a good module. Whether previous state conforms 0.1 0.2 0.3 or other
  schemas — we don't care."* So: recipes target the **current release only** (0.6 today),
  with no per-era branch in a tool and no *"under 0.5 this differed"* aside in a skill;
  **uplift mechanics stay upstream's** — registry and format already carry the minute
  handling for schemas and renames, so describe it and never shim beside it; and a
  backwards-compatibility measurement is *their* property to hold, not a result we
  report. Detecting an input's era is fine — reading the deprecated `sources.csv`
  spelling so you write back to the file you read is correct — **preserving it is not.**
  The **upgrade path is real work and is not yet populated**: it gets built from the
  authoring transcripts, from the moves a real author actually needed, rather than
  designed against the schema history. Until then, do not invent it.
- **"Don't say 'broken' to user — say: needs this this and this decision to work in
  latest."** The voice-and-scope half of the rule above, stated 2026-08-20: *"only cover
  decisions, auto-correct the evident stuff silently per rulebook (to-populate-later)."*
  An old module is **out of date, not defective**, and those are different claims about
  somebody's work — usually the module met the requirements that existed when it was
  written. So: never *broken* / *invalid* / *fails* about a module being brought forward;
  reserve failure language for a module wrong on its own terms, like a shifted coordinate
  or a quote that is not in the paper. The output of a revisit is a **decision list**, not
  a diff and not a findings dump: if a human must choose, it goes in the list; if nothing
  must be chosen, it does not appear.

  **This is not an exception to §2's *report, never repair* — the two split on judgement,
  and the split is the whole rulebook.** Evident and mechanical (a rename, a deprecated
  spelling, a column that moved) → apply it and say nothing, because no judgement exists
  to exercise and nothing downstream re-checks it against a source. A **checked or
  authored** value (a genotype, a `weight`, a `clin_sig`, a conclusion, a
  `provenance_quote`) → never touch it, put it in the decision list; writing one silently
  is exactly the redundancy-bearing mistake the design exists to prevent. **That rulebook
  is TO-POPULATE-LATER and does not exist yet** — until it does, do not settle a boundary
  case ad hoc, because an auto-applied judgement becomes precedent. When unsure, surface
  it: over-surfacing is recoverable, a silent wrong write is not.
- **The two authoring write-ups were independent takes made to reveal different
  surfaces**, not drafts of one another — so they were unified rather than one
  chosen over the other.
- **"For non-skilled users, publish to polygon explicitly, unless they explicitly
  ask for 'official catalog' or alike. This confuses the crowd and we don't want
  half-baked test modules on prod, given its immutable registry."** Decided
  2026-08-11 after an assisted session where a novice's "send it to your site"
  plainly meant *somewhere my friends can see it* and not *the immutable catalog*.
  The rule is a rule about the **conversation**, not the argument — `target`
  already defaults to `test`, so the exposure is an agent volunteering
  `target="prod"` to be helpful. It lives in `skills/module-publish/SKILL.md` and
  in `server.INSTRUCTIONS`, and it carries a corollary: prefix the **module** name
  as well as the namespace on a first rehearsal, because `purge-test-data` matches
  both halves and a first-timer will not come back to delete litter.
- **"If you find the module is genuinely good and is underrepresented in official
  catalog — suggest yourself."** Added 2026-08-11, immediately after the rule above
  and as its deliberate counterweight: the polygon default is against *assuming*,
  not against advocating, and a good module nobody publishes helps nobody. Written
  against **checks rather than impressions**, because an agent asked whether its own
  work is good will say yes — a prod `registry_search` showing the gap, plus strict
  validate and compile, produced-not-authored resolution, every PMID from a search
  result whose title was read, a declared licence, nothing guessed, and a rehearsal
  read back. `assets/fto_bmi` is the calibration case *against*: it cleared all of
  that and `registry_search(gene="FTO")` returned `total: 0`, and one locus with no
  licence and no readme was still not worth an immutable `1.0.0`. **Underrepresented
  is necessary and nowhere near sufficient** — a stub occupies the search result a
  real module would have had.

- **A machine-located `provenance_quote` is legitimate; the fake was always the unattributed one.**
  Decided 2026-08-20, reversing the §2 prohibition outright: *"Yes, it is a derived false direction:
  demolish full force."* The agent reads the article — `fetch_fulltext` hands it over whole — so the
  reading is real and the old rule only protected a fiction about **who** read it. What is required
  instead is a per-row *whodunit*: *"request per-row provenance 'whoddunit' for each quote for mixed
  ai+man tangos and combined authority from upstream (if not yet): example: scientist reads review,
  agent traverses citations."* Responsibility does not move with it — *"now AI is not a subject of
  right, so the human author holds the full responsibility, but at least honest highlights of real
  distribution of roles is 100% better than fake 'I read it all' fingerscrossed confirmation of what
  never happened to push thru the block; realpolitik so to say."* Filed upstream as `S55` (the
  attributor: `StudyRow.curator`, mirroring `VariantRow`'s) with `S54` as its evidence. The
  combined-authority half already exists upstream and we should not re-ask for it: `Contribution.who`
  is documented as *"a name, handle, or model id"* and `Contribution.kind` already ladders
  `{human, human_expert, human_certified}` against `{ai}` + `{agent, team, swarm}`.
- **"Eliminate it entirely; drag away every quote until that doc is empty."** Said 2026-08-20 of
  `skills/create-module/SKILL.md`, the 1431-line canonical procedure, with *"segment, create new
  skills, change existing skill scope at your discretion: frame yourself as primary consumer of
  these."* So the unit of a skill is **the step an agent is on**, not the document a human would write,
  and the rule that replaces "do not restate the procedure beside its skill" is **one fact, one home**:
  if two skills need the same rule, one owns it and the other links. A skill growing back toward a
  monolith is the drift to watch for; the ceiling is 500 lines and the reason is that a file loaded
  whole to answer any question is a file nobody updates in the right place.
- **"Push to the maximum; defer only items that honestly depend on architectural decisions and
  questions that came to be after now."** The unattended-run rule, 2026-08-20. A question that already
  had a written specification is **not** deferrable merely because it was labelled "run §1 first" —
  decide it, write the reasoning **and a reversal recipe** where it will be read again, and continue.
  `RM17`'s layer question was settled that way, and its entry in `ROADMAP_HISTORY.md` carries both.

- **"Offline makes sense annotation-time, not author-time."** Stated 2026-08-20, and it settles how
  much weight `JMC_OFFLINE` may carry in a design argument: *"air-gapped stuff is a very niche
  usecase, we're handicapping 99.9 in favour of 0.1%. This is not a security tool. Frankly I'd get
  rid of it altogether and ship an `-offline` version of the plugin as a separate entity if it is
  ever needed."* The distinction generalises and is worth holding: **offline belongs to the
  annotation side**, where somebody's genome is being read and privacy is the entire point — that is
  `just-dna-lite`'s problem. **Authoring is networked by nature**: literature search, rsID
  resolution, identifier checks and publishing are all network steps and a module cannot be written
  without them. The flag stays, because it is off by default and the suite's socket ceiling is built
  on it. What it may **not** do is veto a broad improvement on behalf of a niche one — it did exactly
  that in `RM23`'s first draft, where it was the lead argument against adopting a 25-source
  literature library, and the objection that actually stood was the shared NCBI budget. §2's "never
  let a per-call argument loosen the offline ceiling" is unchanged: it is about not *lying* about the
  ceiling, never about the ceiling deserving a veto.
- **Do not let a third-party evaluation turn into NIH.** Same conversation. The reflex to defend our
  own five literature clients was wrong; the source list is genuinely a bicycle and *"leeching the
  code is yikes"* — the honest routes are a dependency with attribution or a fork, not copying. What
  is **not** a bicycle is the gate: one `ServiceGate`, one contact chain, one budget shared with the
  enricher by passing the same `PacingGate` instance.

## 11. Learned workspace facts

*Append-only. Environment, ports, credential layout, host quirks, sibling paths.*

- **This repo IS the authoring tool, so an authoring-workflow gap is ours to BUILD FIRST — but
  asking upstream is still cheap, just never empty-handed.** The user's read, 2026-08-20, offered
  explicitly as an impression rather than a ruling: the format tree appears to have in-repo constraints
  keeping it out of authoring, so it leans on downstream for that half. **Do not harden that into a
  rule they never stated.** What *is* decided is the order of operations: *"asking them is no big deal;
  but don't come empty handed — show them the tool."*

  So the working line is **workflow versus contract**, applied to sequencing rather than to permission.
  A gap in authoring workflow — capture an override, re-derive without losing curation, drive a
  refresh, triage a handed source — we **build**, and *then* show it and ask whether they want it
  upstream. A proposal with a running tool attached is a different conversation from a feature request,
  and it costs them nothing to decline. A gap in the *schema*, the *hashes*, a *check's scope* or the
  *wire format* is still theirs and is still filed the moment it is found; we own no schema and that
  has not changed. First case under this: override-preserving sidecar refresh, where upstream's RM83
  already describes the need — build it, then offer it.
- **An invented file in a spec directory is silently dropped, so never store our own state there.**
  `just_dna_registry.specfiles.RECOGNIZED_SPEC_FILES` is what `revalidate` and `upgrade` rebuild a
  spec from, and a name missing from it is a file lost on the next server-side rebuild — the exact
  failure that lost `licensing.csv` before registry 0.16.2 and readmes before 0.14. So our own
  bookkeeping (an override capture, a refresh audit trail) goes to a resolved cache/workspace path
  through `_shared.resolve_dir`, never beside `module_spec.yaml`. The cost is that it does not travel
  to a second machine or a second author, which is real and is the honest limit to state rather than
  to design around.

- Sibling repos live beside this one under `/data/sources/`:
  `../just-dna-format` (hosts format, compiler and enricher, their
  `CONSUMER_SUGGESTIONS.md` intake and its answered half,
  `docs/CONSUMER_SUGGESTIONS_HISTORY.md`), `../just-dna-lite`, and the registry at
  **`../just-dna-marketplace`** — a **stale directory name only**. The project,
  package and service are `just-dna-registry`; "marketplace" is the old word,
  retained on the path and nowhere else. There is no `../just-dna-registry`
  directory, which is a path quirk and not a rename.
- The registry keeps its own intake at
  `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md`, created 2026-08-11.
- **`just-dna-registry` moves fast: 0.9.1 → 0.12.0 → 0.13.0 → 0.14.0 in two days.**
  0.14.0 is on PyPI, is what `uv sync` installs, and is our floor. **That floor is
  load-bearing rather than hygiene**: 0.14.0 is the release that projects a
  spec-directory `README.md` onto the module card, so below it every module we publish
  has a blank catalog card (`F33`). **Re-check with
  `importlib.metadata.version("just-dna-registry")` rather than trusting this
  line** — it has gone stale within hours three times.
- **Their release notes carry a `Client surface:` line, and it is trustworthy.** Their
  answer to our `S2`. Read that one line instead of the whole release to establish that
  the client methods we call did not move — 0.13.0 and 0.14.0 both say *unchanged*, and
  0.14.0's was verified upstream with `git log -S` over our eight. The **additions**
  still have to be read: 0.14.0's four all mattered to us.
- **Reading a registry upgrade got cheaper in 0.13.0** (their `S2` = our `F15`).
  Every release entry now opens with a `Client surface:` line — 0.13.0's says
  *unchanged*, checked with `git log -S` over the eight `RegistryClient` methods we
  call — and both reference docs are stamped with the versions they are normative
  for. **What is still missing is the enumeration itself**, which needs a contract
  version of its own; it exists machine-checked as `_WRAPPED_ROUTES` in their
  `tests/test_client_sdk.py` but is not published. Upstream says
  `research.py::_module_card`'s defensive projection is safe to delete against a
  0.13 server; **we keep it anyway**, for the narrower reason recorded in `F15` —
  `get_module` is not one of the six methods `assert_compatible` guards, so an
  older *server* answers it unchecked.
- **The registry is TWO instances and they share no database.** Production is the
  catalog everyone installs from; the polygon (`REGISTRY_MODE=test`) is where a
  publish is a rehearsal. An account, a token and a namespace exist on one of them
  only, so registering on one gives you nothing on the other. **Both are serving
  0.13.0 and both report their mode**, so a target is now *verified* rather than
  merely declared: `targets.client_for` passes `expect_mode=target` on every client,
  and a publish aimed at the polygon that would land on production refuses. The
  polygon is up — it was DNS'd but answering a bare Caddy 404 earlier the same day.
  See `targets.py`; the write tools default to the polygon and the catalog reads to
  production, because a forgotten `target` costs nothing on one and is
  irreversible on the other.
- **We hold a POLYGON credential and no production one, as of 2026-08-12.**
  `JMC_TEST_API_KEY` is set in `.env` and `registry_whoami(target="test")` answers
  **account `sheep`, namespace `test-sheep`** — so a polygon rehearsal needs no
  `registry_register` and no namespace claim. Production is still empty: the
  `test-creator` account and its `test-modules` namespace are **gone from
  production**, which now refuses `test-`prefixed data outright, and `JMC_API_KEY`
  was cleared from `.env` rather than left stale — a dead token makes every registry
  tool report *"the registry rejected your token"*, which sends an author to debug
  auth instead of to register. `JMC_INSTALL_ID` is still there deliberately: it is a
  proof-of-work string rather than an instance credential, it exists nowhere else,
  and destroying it is the user's call, not ours.
- **Production holds SEVEN modules / 18 versions / 5 namespaces, measured 2026-08-21** with
  `registry_health(target="prod")`, whose `catalog` block answers this in one call and is cheaper than
  a search. The polygon carries 9 modules / 13 versions / 4 namespaces. Both instances serve registry
  **0.18.2** and both confirm their own mode, so `mode_matches_target` is `True` on each. New since
  2026-08-20: `antonkulaga/bodybuilding@1.0.0` and `ksuha-dna/placebo_response_claude@1.0.0` — the
  second is a namespace that did not exist before, so the catalog is now taking modules from outside
  the two known authors. **This line said FIVE for a day, which is exactly what it warns about.**
  Earlier measurement, 2026-08-20, kept because the four `antonkulaga/*` are still the worked
  examples: measured with `registry_search()` (defaults to prod).
  Four are `antonkulaga/*` at `2.0.0`/`2.1.0` — `aggression_anger_snps` (28 variants),
  `big_five_personality_snps` (330), `cognitive_intelligence` (32), `risk_impulsivity_snps` (474) —
  and `eric-mods/lactose_tolerance` is now at **`1.0.1`**, not the `1.0.0` this file said until today.
  The `antonkulaga` four are the published outputs of the four authoring transcripts, so they are the
  worked examples of *what an outside driver actually ships*, and `lactose_tolerance` is still the
  smallest readable real spec. **This line goes stale the moment somebody publishes — re-run
  `registry_search()` rather than quoting it**, which is exactly how it came to claim "one module" for
  nine days.
- The enricher's Ensembl cache lands in
  `~/.cache/just-dna-pipelines/ensembl_variations`. The live V2 GraphQL endpoint
  currently 404s and the client falls back to REST — expected, not a defect.
- A transitive dependency ships a top-level `tests` package that shadows this
  repo's, so test helpers import as `from conftest import ...`.
- **Format 0.6.6 / compiler 0.6.6 / enricher 0.6.6 / registry 0.18.2 — adopted 2026-08-21 (our
  0.16.0).** The three moved back into lockstep at 0.6.5, the aligned number, and 0.6.6 is the patch
  round after it; the split era below is what 0.6.1–0.6.4 were. Verify by symbol, never by this line —
  and pass `--project /data/sources/just-module-creator` so the answer is about our venv:
  `StudyRow.curator` (0.6.5), `hints.key_fields` / `hints.DERIVED_TABLE_MODELS` (0.6.5),
  `compiler.compiler.spec_tables` / `compiler.compiler.module_stats`, `scaffold.companions_for`, and
  `hints.REDUNDANCY_BEARING_TABLES` (0.6.6). **`scaffold` and `hints` live in the COMPILER, not in
  format** — importing `just_dna_format.scaffold` fails and it is an easy minute to lose.

  **Three behaviours changed, not just symbols.** A duplicate `(source, layer)` row in
  `licensing.csv` is now an **error** in validate and compile both, so an inherited module carrying
  one stops compiling; the `faf95` warning is published once rather than twice, so a recompiled
  module publishes one fewer warning with no text changed; and `manifest.stats` takes its gene facets
  over every authored table, so a recompiled PGx or binning module becomes findable by gene where it
  was not. **A published version keeps what its own compile wrote** — all three reach a module only
  through a recompile.

  **The previous line was: format 0.6.1 / compiler 0.6.1 / enricher 0.6.4, adopted 2026-08-19.** 0.6.1
  through 0.6.4 is the stretch where the three did *not* move together — format and compiler sat at
  0.6.1 while the enricher took patches alone (0.6.2 for RM101's exception contract, 0.6.3 for the
  ClinVar and ClinPGx drafter fixes, 0.6.4 for S45).
- **Both live registry instances still serve `format: 0.6.1` while we compile with 0.6.6, and that is
  fine — measured 2026-08-21, not assumed.** The contract check is scoped to **major.minor** below
  1.0, so every 0.6.x interoperates: `assert_compatible()` passes against prod and the polygon with a
  0.6.6 client, and `curl -s <url>/api/v1/version` returns
  `{"registry":"0.18.2","format":"0.6.1","compiler":"0.6.1"}` on both. **A 0.7 client against a 0.6
  server is the case that would refuse**, so re-probe at the next minor rather than reading this line
  as a general permission.
- **Both live registry instances now serve `format: 0.6.1` / `registry: 0.18.x`, verified 2026-08-19,
  and the 0.5.4 contract block is over.** The installed client is **0.18.2** as of 2026-08-20 — this
  line said 0.18.1 for a day. Every version-guarded call works again — a `download` of
  `eric-mods/lactose_tolerance` returns its manifest where it 409'd a day earlier, and
  `assert_compatible()` passes on prod and polygon alike. `targets.instance_note` stays: it is a
  suffix on an existing `except RegistryError` arm, costs nothing while the contract agrees, and is
  there if an instance is rolled back. **Re-probe with `curl -s <url>/api/v1/version`, never assume** —
  this line has now been wrong in both directions within two days. Note that `lactose_tolerance` was
  stamped `just-dna-compiler 0.5.1`; that is the contract gap registry 0.18.0's `upgrade` detects, and
  an operator's sweep rather than an author's problem.
- **A drafter fix does not reach a module already drafted, and the two drafters need opposite
  repairs.** Enricher 0.6.3's ClinVar fix (S41) moved identities, so re-drafting over an existing
  spec restores the lost records and leaves the collapsed ones — measured 0 missing, 31 stale on
  MLH1. Its ClinPGx fix (S44) only *skipped* rows, so a plain re-run converges exactly (0 stale, 0
  missing). **`S44` skipped, `S41` wrote under an identity that has since moved** is the sentence
  that stops one remediation being generalised to both. Filed as `S45`, fixed in enricher **0.6.4**
  the same day: the drafter now names the superseded rows and deletes nothing. `F36`, closed.
- **Upstream answers within hours, so "filed" and "released" can be one session apart.** `S45` was
  written, accepted, built, released as 0.6.4 and adopted here inside a day, which made our 0.10.1
  docstring wrong before anyone read it — it told an author the stale rows were undetectable, and by
  then the drafter named them. **After filing an `S<n>`, re-check the tree before quoting our own
  mitigation as current**, and prefer wording that survives the fix landing.
- **The format tree's triage script is `.claude/triage-state.py`**, not the `.sh` older notes name.
- **An upstream *library* call loads your `.env`.** `just_dna_enricher.locations` calls `load_dotenv`
  while resolving a cache path, so `build_server` repopulates `os.environ` from whatever `.env` is
  above the cwd. `load_dotenv(override=False)` skips a key that is *present*, so clearing a variable
  with `delenv` is what lets the file win — which is how the suite quietly stopped being hermetic.
  `F35` / format-tree `S39`; the fixture neutralizes the loader by walking `sys.modules`.
- **0.5.4 and registry 0.13.0 both released 2026-08-11, and we installed both** (superseded above).
  `uv sync` gives format/compiler/enricher **0.5.4** and `just-dna-registry`
  **0.13.0**; the floors in `pyproject.toml` say so. Adopted in our 0.7.0, which
  retired six mitigations at once — `S11`, `S12`, `S15`, `S16`, `S17`, `S18`, plus
  `S20`/`S21`/`S23`/`S24` and the registry's `S1`/`S3`. **Re-verify by symbol, never
  by this line or a changelog**: `hints.ATTESTATION_BEARING`, `hints._report_ragged`,
  `Finding.line`, `CitationHint.title`, `IdentifierReport.gene_loci`,
  `RegistryClient(expect_mode=…)`. `hints.py` lives in the **compiler**, not the
  enricher, which is easy to get wrong when grepping; `SourceRow` lives in
  `just_dna_format.sources`, not `.spec`.
- **Three mitigations are kept on purpose and are not oversights**: `ServiceGate`'s
  lock (upstream fixed `PacingGate` *because* callers share one), `compile_module`'s
  `resolve_with_ensembl=True` pin (`S14`'s rename was **refused** with a reason, so
  the pin is permanent), and `_module_card`'s defensive projection (`get_module` is
  not one of the six methods `assert_compatible` guards, so an older *server* can
  still answer it unchecked — our floor pins the client, not the host).
- **The registry's intake adopted the same split as the format tree on 2026-08-11**:
  it now has `CONSUMER_SUGGESTIONS_HISTORY.md`, a `CONSUMER_TRIAGE_LOOP.md` runbook
  and a `.claude/triage-state.sh --next`. Read both intakes the same way — and its
  history file is now populated, so the earlier advice to read `**Status —**`
  paragraphs in its inbox no longer applies.
- Ours there: `S1` (the `would_publish` ceiling = `F11`), `S2` (no enumerated
  client-surface contract = `F15`) and `S3` (no endpoint reports an instance's mode
  = `F16`) — **all three answered and released in 0.13.0**, except `S2`'s enumerated
  contract, which is open on their roadmap because it needs a contract version of
  its own. `S5`–`S7` (the readme) — **released in 0.14.0**. `S8` (they attribute
  `write_module_md` to us) and `S9` (`amend_readme` is on their client but not their
  CLI) — filed 2026-08-12, open.
- **Never read a next-`S<n>` off a line like this one; run
  `.claude/triage-state.sh --next` in the repo you are filing into.** The proof is in
  this file's own history: it said `S25`/`S5` on 2026-08-11, `S27`/`S8` hours later,
  and both were wrong again by the next session (`S29`/`S10`). A number written down
  here is stale by construction, because either seat may file between sessions.
- **Read `docs/` before filing, not just the inbox.** On 2026-08-12 two of our own
  sessions filed the same readme defect hours apart (`F27` = registry `S5`, then
  `S7`), and the second was closed as a duplicate. The duplicate check is cheap and
  neither session ran it.
- **"The goal of this plugin is to be ai-coauthor. And it can be driven by a lyman."** Stated
  2026-08-12. The module owner brings the *theme* and the *sources* — a trait, some PDFs, a video.
  Everything after that is the agent's: triage, rows, conclusions, located passages. **"Here you
  kinda ask v2 work from a wrong person"** — the worked case was asking a gardener, who cannot read
  a genetics paper, to supply `provenance_quote` and to judge whether the module was good enough to
  publish. Both are a reviewer's job and a different person's. **"AI totaly can read articles."**
- **Versions and curation carry NO implicit contract.** Corrected 2026-08-12 after the skill turned
  an illustration into a ladder: *"1.0.0 2.0.0 arent strict milestones, it was an example, we don't
  have any implicit contracts on versioning or order of curation."* The real rule is a signal read
  off the module, never a schedule: *"if module is v25 - likely it's worked on iteratively, slightly
  more trust; module has non-ai curators - that's a silver one already, human labor costs. v52 and
  2+ curator med_geneticists? That's platinum."* So `2.0.0` does not mean reviewed, a human may
  curate from the first version or never, and **no agent may withhold a publish or a bump waiting
  for a milestone that does not exist**. Curated work is then cherry-picked into a featured catalog
  section by the operator. `authorship` is where the signal actually lives, which is why it is now
  documented in `skills/module-start/SKILL.md` rather than left to the schema.

- **The old no-machine-quote rule produced title-as-quote on 3668 published rows — measured 2026-08-20.**
  Across every `studies.csv` in `../just-dna-format` (33 files, 44342 rows): the ten
  `reference_examples/` do not carry the column at all, and the four `data/output/corrected_modules/`
  — the published `antonkulaga/*` four — carry a `provenance_quote` on **every** row, 3668 of 3668.
  Exactly **one distinct quote per PMID** in all four (81 PMIDs), 7–17 words, and it is the article
  **title** verbatim: `pmid 24489884` carries *"Genome-wide association study of proneness to anger."*
  and `lookup_citation` returns that same string as `title`, trailing period included. A title always
  appears in its own fulltext, so `quotes_found` equals `quotes_authored` and the module reports full
  quote coverage while witnessing nothing. **Use this as the calibration case for any rule that
  refuses rather than attributes**: the refusal did not produce human-read quotes, it produced a
  green check over metadata. Filed as `S54`.

- **`git add -u <dir>` swept a concurrent session's edits into three of my commits — 2026-08-21.**
  Another agent was editing this repo at the same time (making `target` a required argument on the
  catalog reads). `git add -u skills/` stages every modified file under a path, so their prose landed
  in commits whose message is about something else, while the code it describes is still in the
  working tree. Nothing was lost and nothing was overwritten — the string-replacement scripts assert
  on the old text, so a passage they had already edited fails loudly instead of being clobbered — but
  **a directory is not an explicit path**. Stage the files you actually wrote, by name. §2's
  "never blind-stage" is the same rule at a coarser grain and did not stop this; `git status --short`
  before every commit is what does.
- **`cd` leaks between Bash calls, and a leaked one put git commands in an upstream repo.** A
  `git add` / `git commit` pair ran inside `../just-dna-format` because of an earlier `cd`; the `add`
  failed on a non-matching path so the commit never executed, which was luck rather than safety. **Use
  absolute paths in git commands**, and remember every git grant is bounded to this repository.
- **The polygon carries two remediated rehearsals from the 2026-08-20 quote work**:
  `test-sheep/test_aggression_anger_snps@1.0.0` and `test-sheep/test_big_five_personality_snps@1.0.0`.
  Both are `test-`prefixed on both halves, so `purge-test-data` will collect them; they are rehearsals
  of a remediation, not a correction of anything published. Both were published **knowingly carrying a
  stale `literature.csv`** — correcting it needs extended-tier tools (`F47`), and a rehearsal that
  waited for that would have measured nothing. **Nothing in the four production
  `antonkulaga/*` modules was touched** — a published version is immutable.
- **`logs/authoring.log` now has a writer, and it publishes.** `record_override` appends to it and every
  compile sweeps `logs/**.log` up with no opt-out. So never write an absolute path, a token or a
  transcript fragment into that file: it travels to the catalog verbatim.
