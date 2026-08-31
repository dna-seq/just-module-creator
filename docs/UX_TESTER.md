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

## Credentials — polygon: yes. Production: still none.

**Changed 2026-08-11.** You now hold a **polygon** account: `tester`, registered with the *existing*
`JMC_INSTALL_ID` (the result reported `install_id_origin: "environment"`, so no new id was ground and
the old one still identifies you), token saved in `.env` as `JMC_TEST_API_KEY`. The namespace
**`test-ns` is claimed.** Production is untouched — no account, no token, nothing claimed — and the
paragraphs below about it are all still current.

State only. **How to obtain and save a token is the skill's job**, not this file's:
`skills/module-publish/SKILL.md` covers registering, what the two secrets are, and why
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
| token env var | `JMC_API_KEY` (**still cleared**) | `JMC_TEST_API_KEY` — **set 2026-08-11**, account `tester` |

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
| F14 / S18 | **shipped in 0.5.4 → `previous_issues.md`-adjacent; closed in `pending-fixes.md`** | `hints.inspect_rows` zips header names positionally without comparing field counts, so an unquoted comma in a free-text cell shifts every later column and the error is reported against a column the author wrote correctly. `Finding.row` is 0-based where the compiler uses 1-based `line N`. Left unmitigated here on purpose: `lint_rows` is a deliberate pass-through. **Both halves released in 0.5.4** — `_report_ragged` names the ragged row first, and `Finding.line` now carries the editor line, which `to_findings` passes through without deriving it. |
| S19 | upstream | A binning table has nowhere to record evidence. `studies.csv` keys on `rsid`/`chrom` only and is required iff `variants.csv` exists, so a `repeat_alleles.csv` row cannot be grounded and compiles green asserting a clinical threshold with no citation. |

### The assisted session — a novice user, an LLM-written source (same day)

Run in a different shape: the user role-played a non-specialist who brought a Gemini summary of two
YouTube genetics lectures and asked for a module. **That shape found more than solo probing did**, because
triaging a machine-written source exercises the lookup tools against claims that are *plausibly* wrong
rather than absent. Worth repeating deliberately. Reference example: `assets/fto_bmi/`, whose README is
the write-up.

| id | where | what |
|---|---|---|
| **S20** / F17 | **shipped in 0.5.4** → closed in `pending-fixes.md` | **high.** A failed live-Ensembl request is reported as `loci: []` + *"live Ensembl has no GRCh38 locus for it either"* — a definite negative. Same call, minutes apart: `rs6567160` and `rs13010010` both no-locus, then both resolved. `resolve_rsid` swallows transport errors into an empty list, so `if not loci:` cannot tell the two apart; the only trace is `checked` *lacking* `ensembl-rest`. **`loci: []` is the fingerprint of a fabricated rsID**, so flaky egress makes real variants look invented — it misfiled two genuine SNPs mid-triage. F17 left unmitigated on purpose; both candidate wrappers argued wrong in the note — **and the fix vindicated that**: `checked` now records the source on the answered-empty path too, so the `"ensembl-rest" not in checked` inference would have silently inverted the day 0.5.4 landed. Filed, fixed and released inside a day. |
| F18 | `dogfooding.md` | The skill's "a green pre-flight should mean a green compile" is false pre-`resolution.csv`: strict validate returned valid with **zero** findings at all three levels, strict compile refused. Compile gate itself is fine, which is why it is medium. |
| F19 | `dogfooding.md` | Nine essentials tools missing → the stdio process was 3h older than HEAD. **Nothing on the surface reports the server's version**, so this was indistinguishable from "the skill documents a tool that does not exist" without `ps` + `git log` + a grep. Suggested fix: append the version to `server.INSTRUCTIONS`, not a `server_info` tool — instructions are always in context, a tool has to be called by someone who already suspects the problem. |
| **S21** / F20 | **both halves shipped** → `previous_issues.md` | `sources.csv` is the one sidecar a human must hand-write; `list_tables` advertises it and `describe_table`/`get_template` reject the name, and `authoring_reference()` omits `SourceRow` entirely. Columns had to be read from `model_fields`. Two separate defects — fixing upstream will not fix ours. **Both done in 0.5.4**: `sources.csv` is in `DRAFTABLE` upstream, and our hardcoded sidecar literal is gone, which it had to be — with upstream's half alone it appeared as a table kind *and* as a do-not-hand-author sidecar. |
| **S23** / F21 | **shipped in 0.5.4** → `previous_issues.md` | The `sources.csv` rule is **inverted**: the pubmed/europepmc rows draw *"declares 2 source(s) no table in this module uses"*, and deleting the file entirely warns about **nothing**. Compliance is warned, omission is silent — and the tidy fix is to delete provenance. **Inverted correctly in 0.5.4**, re-verified on the asset's real rows: compliance silent, omission warns. Skill text corrected. |
| F22 | `dogfooding.md` | low. `published.json` — the receipt we tell the author to commit — records `owner: null`, though the claim and `registry_get_module` both know `tester`. |
| **S22** | upstream | Longshot, filed at the user's direction as low priority: literature reports hg19, modules must be GRCh38, no supported path. Argued **out from under RM15** (that is `❌ — 1.0` and is about supporting another build; this is a one-way authoring-time conversion) and argued that **rsID recovery beats liftover** — liftover is only reachable when there is no rsID, i.e. exactly when its output cannot be cross-checked. |

**What held up, and is not worth re-probing:** every refusal fired (`lookup_variant`'s withheld
coordinates, every DOI, `check_identifiers` reporting without writing); the strict compile gate refused
the unresolved module and named the remedy; `artifact_digest` reproduced exactly across a local
recompile *and* the registry server's independent one; Semantic Scholar 429'd all session and was
reported `results: null` rather than `0` (F6 earning its keep in the same session S20 fused the same
distinction).

## Observations not yet filed

Small, and each belongs to the second agent rather than upstream:

- **`registry_register`'s docstring says "Omit `install_id` and one is ground for you."** It grinds only
  when the environment has none — `auth.py:141` reads `settings.install_id` first and reports
  `install_id_origin: "environment"`. The imprecision costs both ways: an agent either pastes a live
  secret into a transcript to be safe, or avoids the call for fear of orphaning the existing account. One
  clause fixes it.
- **`registry_register` echoes the install-id back even when it came from the environment.** The caller
  already has it in `.env`, so returning the value only writes an existing secret into the transcript.
  Returning `install_id_origin` without the value would be strictly better in that branch.

- ~~**`authenticate`'s docstring is stale.**~~ **Fixed** in `6ad1898` — it now points at
  `registry_register` and says a token is needed only to publish.
- ~~**`plugin.json` says `0.2.0`; `pyproject.toml` says `0.3.0`.**~~ **Fixed** in `a1f50a2`,
  with `tests/test_plugin_manifest.py` failing on any future mismatch.
- ~~**The essentials tier cannot verify a trait CURIE.**~~ **Fixed in 0.4.0** — this one
  turned out to be the visible corner of a wrong tier rule, and the tier was widened
  rather than the single tool moved. Essentials now runs the whole workflow: the
  identifier checks, `enrich_module`, `fetch_fulltext`, `lookup_open_access`,
  `authoring_reference`, the integrity pair and `registry_get_module`. Extended kept
  only what a corpus sizes — and in **0.21.0 it went too**, after the same defect shipped
  three more times. There is one surface now, so a probe that finds a tool missing is
  reading an old install rather than a narrow tier.
- ~~**The README documents installing the plugin and not reloading it.**~~ **Fixed** —
  README now has "Reloading after a change" and "Switching mode", including the trap that
  `.env` cannot switch a plugin-launched server.

## In flight

**`assets/fto_bmi/` — done through the rehearsal.** Authored, enriched, strict-compiled, and published
to `test-ns/fto_bmi@1.0.0` on the polygon; server-side recompile reproduced our digest. **Two things
remain open on it:**

1. **The production decision is the user's and has not been made.** They chose "polygon first, then
   decide". Do not promote without asking again — a production publish burns the version number *and*
   the right to publish that data under any other name.
2. ~~The polygon copy needs cleaning up.~~ **Done** — `registry_delete_module` removed it after the
   read-back, verified by a `404 module_not_found`. It mattered because the module name is not
   `test_`prefixed (only the namespace is), so `purge-test-data` would never have collected it. The
   committed `assets/fto_bmi/published.json` is therefore a *historical* receipt; its README says so, so
   nobody reads the 404 as a regression.

The namespace `test-ns` is left claimed — it *is* `test-`prefixed, so the operator's sweep collects
it, and there is no unclaim operation anyway.

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
