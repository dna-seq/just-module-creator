# UX tester — working memory

Read this to resume dogfooding cold. It is the tester's state, not a spec: what the
role is, what has been established, and what was in flight. Everything durable has
already been filed in `dogfooding.md`, `just-dna-format-pending-fixes.md` or upstream —
this file is the thread connecting them, and it should stay short enough to stay true.

## The role

**Use the shipped surface for real work and report what is missing. Do not fix it.**
A second agent implements; this seat tests. That split was set deliberately on
2026-08-11 ("The second agent will fix it, you stay in tester role") and it is the whole
value of the arrangement — the moment the tester patches the thing, nobody is left
experiencing the product.

The tango: probe → hit friction → record it → hand over → user reloads → probe again.

Two rules do most of the work here:

- **Reaching for a script to get around the tooling is the finding.** Not an obstacle to
  route around — the signal that the product is missing something. Stop and write it up.
- **File upstream findings the moment you find them.** Not after the probe finishes, not
  batched at the end. A note that arrives after the release window buys nothing.

Attack claims, not gaps. A documented deferral is a decision; what counts is where a
docstring or doc *promises* something the code does not do.

## Credentials — you have none right now

State only. **How to obtain and save a token is the skill's job**, not this file's:
`skills/create-module/SKILL.md` §7 covers registering, what the two secrets are, and why
the install-id has to be kept. Read it there; do not restate it here, or the two drift.

**The `test-creator` account and its `test-modules` namespace are gone from production**
(2026-08-11). Production now refuses `test-`prefixed data outright, so that account could
not exist there again under that name even if you re-registered. Its token has been
**cleared from `.env`** rather than left in place: a dead token makes every registry tool
fail as *"the registry rejected your token"*, which sends you to debug auth instead of
telling you the truth, which is that you have no account.

**There are two instances now and they share no database** — an account, a token and a
namespace live on one of them only. So starting again means registering on whichever one
you are aiming at:

| | production | the polygon |
|---|---|---|
| what it is | the catalog everyone installs from | the rehearsal instance |
| `test-` names | `422 test_data_on_prod` | accepted |
| deleting a bad publish | impossible | `registry_delete_version` |
| token env var | `JMC_API_KEY` (**cleared**) | `JMC_TEST_API_KEY` (never set) |

**Rehearse on the polygon.** A production publish is immutable *and* claims its authored
data by a content hash that `yank` does not release, so one botched publish burns the
version number and the right to publish that data under any other name.

`JMC_INSTALL_ID` is **still in `.env` and was deliberately left there.** It is a
proof-of-work string, not a credential for a specific instance, and it exists nowhere else
— clearing it would be unrecoverable for a value that costs a second to reuse and may
still be worth registering with. If you want it gone, say so; it is not mine to destroy.

## What has been established

- `/reload-plugins` does **not** re-exec a stdio MCP server; `/mcp` reconnect does.
  Verified by process start times against the commit time — a reload spawned no new
  process and the old tool list survived. Stale servers accumulate rather than being
  replaced.
- The plugin runs from this working tree (`uv run --project ${CLAUDE_PLUGIN_ROOT}`), so
  Python edits need only the subprocess restarted, never a reinstall.
- Upstream's intake is split: `CONSUMER_SUGGESTIONS.md` is the inbox and holds **only
  unanswered** items, so an empty one means nothing is owed. Never number a new `S<n>`
  from what it shows — run `python3 .claude/triage-state.sh --next` in
  `../just-dna-format` (it is Python despite the `.sh` name; invoking it with `bash`
  fails). S1–S18 are answered; S19 is filed and open.

## Filed this session

| id | where | what |
|---|---|---|
| F12 | `dogfooding.md` → now shipped | No way to create an account from the tool surface. **Fixed by the second agent** — `registry_register` mints the token in-surface. |
| F13 | `dogfooding.md` → now shipped | No pre-flight before an irreversible namespace claim. **Fixed** — `registry_namespace_available`. |
| F14 / S18 | `just-dna-format-pending-fixes.md` + upstream | `hints.inspect_rows` zips header names positionally without comparing field counts, so an unquoted comma in a free-text cell shifts every later column and the error is reported against a column the author wrote correctly. `Finding.row` is 0-based where the compiler uses 1-based `line N`. Left unmitigated here on purpose: `lint_rows` is a deliberate pass-through. |
| S19 | upstream | A binning table has nowhere to record evidence. `studies.csv` keys on `rsid`/`chrom` only and is required iff `variants.csv` exists, so a `repeat_alleles.csv` row cannot be grounded and compiles green asserting a clinical threshold with no citation. |

## Observations not yet filed

Small, and each belongs to the second agent rather than upstream:

- ~~**`authenticate`'s docstring is stale.**~~ **Fixed** in `6ad1898` — it now points at
  `registry_register` and says a token is needed only to publish.
- ~~**`plugin.json` says `0.2.0`; `pyproject.toml` says `0.3.0`.**~~ **Fixed** in `a1f50a2`,
  with `tests/test_plugin_manifest.py` failing on any future mismatch.
- ~~**The essentials tier cannot verify a trait CURIE.**~~ **Fixed in 0.4.0** — this one
  turned out to be the visible corner of a wrong tier rule, and the tier was widened
  rather than the single tool moved. Essentials now runs the whole workflow: the
  identifier checks, `enrich_module`, `fetch_fulltext`, `lookup_open_access`,
  `authoring_reference`, the integrity pair and `registry_get_module`. Extended keeps
  only what a corpus sizes. **Re-probe from the default tier** — the friction you
  recorded should be gone, and what is left of extended is worth its own look.
- ~~**The README documents installing the plugin and not reloading it.**~~ **Fixed** —
  README now has "Reloading after a change" and "Switching mode", including the trap that
  `.env` cannot switch a plugin-launched server.

## In flight

`assets/htt_cag_repeats/` — scaffolded, **not yet authored**. `module_spec.yaml` still
carries `<<REPLACE>>` in title/description/report_title, and `repeat_alleles.csv` holds
the two generated stub rows.

The intent is the probe `dogfooding.md` lists as outstanding: a binning module taken
scaffold → validate → compile → publish, which would close both remaining probe entries
at once.

**The publish half needs re-planning.** It was written against a single instance and a
`test-modules` namespace on production, and neither exists now — the account is gone and
production refuses `test-` names. The publish now goes to the **polygon**
(`target="test"`), which is the better probe anyway: it is deletable, so the run can be
repeated, and it exercises the two-target surface that shipped after this plan was
written. Register on the polygon first; nothing carries over from the old account.

The rows to author are real HTT CAG bins, already linted clean (0 errors, 0 warnings)
in an earlier probe:

| min | max | direction | meaning |
|---|---|---|---|
| — | 26 | neutral | normal |
| 27 | 35 | neutral | intermediate; may expand on paternal transmission |
| 36 | 39 | risk | reduced penetrance |
| 40 | — | risk | full penetrance |

plus the `unresolved: true` sentinel row, which the scaffold generates for you.

Two things that matter when writing them:

- **Integer bins must not touch.** `repeat_count` and `copy_number` are contiguous
  already, so a shared endpoint is a real overlap and is refused — `[27,35]` then
  `[36,39]`. The dense kinds (`allele_fraction`, `prs_percentile`) are the opposite and
  must touch. Getting this backwards is the trap the probe was chosen to test.
- **Quote every free-text cell.** `conclusion` values contain commas, and an unquoted one
  produces a validation error naming a different column entirely (F14).

What held up well and does not need re-probing: the coverage check reports a genuine hole
and correctly invents none between adjacent integers 26 and 27; the missing-sentinel
warning states the contract outright; `literature_search` reproduced F6 faithfully
(Semantic Scholar and preprints 429, reported as *unchecked, not empty*) and withheld
every DOI as redundancy-bearing.

## Standing constraints

- Never commit in a sibling repo. Writing the upstream note is the whole job; leaving
  `../just-dna-format` dirty is the expected end state.
- Never `git add -A`. Stage explicit paths.
- Committing in **this** repo is pre-authorised and expected as you go.
