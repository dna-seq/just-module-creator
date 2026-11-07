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

## Credentials — polygon: yes. Production: none.

**As of 2026-11-07**, read with `registry_accounts(action="list")`, which is the call to make rather than
trusting this line. There is one saved account: `sheep` on the polygon (`target="test"`), namespace
`test-sheep` claimed, the default for that instance. It lives in the plugin's `state.json` (0.47.0+), not in
`.env`. `JMC_TEST_API_KEY` and `JMC_INSTALL_ID` in `.env` are the fallback that the 0.48.0 start-up import
copied in. **Production: no account, no token, nothing claimed.** A prod call refuses before sending anything,
and that refusal is the 0.48.1 behaviour probed today.

The install-id is a proof-of-work string and the account's only recovery path; it exists nowhere else.
Destroying it is the person's call, never this seat's. How to obtain and save a token is
`skills/module-publish/SKILL.md`'s job. Read it there, don't restate it here.

**Two instances, no shared database**: an account, a token and a namespace live on one only. Production
refuses `test-` data, a publish there is immutable, and its content claim survives `yank`. The polygon's
publishes are deletable. **This seat publishes to the polygon only** (its priming), and the module name
is `test_`-prefixed as well as the namespace, so `purge-test-data` collects it.

## What has been established

- **A seat cannot bring its own plugin server back once the host gives up on it** (checked 2026-11-07, host
  Claude Code, seat sessions in this clone). At 13:51 UTC the host's 30 s connect timeout fired on a server that
  answers `initialize` in 7.7 s when started by hand (`uv run --no-dev --project . just-module-creator stdio`).
  The cause was load, not the server: at that minute the machine restarted every repo's sessions, watchdogs and
  `uv run` servers at once (the kit's pin moving to v0.1.140; 15-minute load average still 13.7 at 14:39 UTC).
  What the logs show:
  - the start that timed out was the **liaison's** session (`a85b4db8`, 13:51:04–13:51:34 UTC); the host log
    holds only its own lines, no server stderr, so where those 30 s went is not recorded anywhere;
  - **the tester's session (13:58) never tried**: it has no log file for this server at all. The host keyed the
    cached failure to the project, so one session's lost race left every later session in the repo without
    the product;
  - the same burst gave prepare-annotations' 0.47.0 copy a 12 s connect at 13:49, so 30 s is within reach;
  - normal-load costs, measured 14:40 UTC: `uv run`'s sync check 0.03 s, `import just_module_creator.server`
    2.2 s, `build_server()` 2.4 s, a full start to the `initialize` answer 7.7 s. The headroom is about 4×.

  What the session could then do about it, each tried:
  - the host's own message, *"retries automatically in 15 min"*: no new connect attempt in
    `~/.cache/claude-cli-nodejs/-data-sources-just-module-creator/mcp-logs-plugin-just-module-creator-just-module-creator/`
    after 46 min;
  - its other hint, *"edit the plugin config to retry now"*: a `touch` of `.claude-plugin/plugin.json` started
    nothing (a content edit was not tried: the manifest is the lead's file);
  - `ListMcpResourcesTool` on the server: answers "no resources" from the cache and connects nothing;
  - `/mcp` and `/reload-plugins` are typed by the person; a session cannot invoke either.

  So an unattended seat whose server lost the start-up race stays without the product until the person returns.
  The fallback that keeps work going is F107's in-process driver (`fastmcp.client.Client` on a server built in
  the script), which tests the tools but not the host wire; a probe run through it says so.
- `/reload-plugins` does **not** re-exec a stdio MCP server; `/mcp` reconnect does.
  Verified by process start times against the commit time — a reload spawned no new
  process and the old tool list survived. Stale servers accumulate rather than being
  replaced.
- The plugin runs from this working tree (`uv run --project ${CLAUDE_PLUGIN_ROOT}`), so
  Python edits need only the subprocess restarted, never a reinstall.
- Upstream's intake is split: `CONSUMER_SUGGESTIONS.md` is the inbox and holds **only
  unanswered** items, so an empty one means nothing is owed. Never number a new `S<n>`
  from what it shows, and never from a count written down here either — ids are claimed
  between sessions and by the other seat. This command answers it, and it is the one that
  runs rather than the one that reads right: run from anywhere, no `cd`, and the
  interpreter is explicit because a bare `python`/`python3` is not on this box's PATH.

  ```
  uv run python /data/sources/just-dna-format/.claude/triage-state.py --next
  ```

  **Run verbatim 2026-09-11 and it answered.** Three things this line had wrong until
  then, each of which stops it dead: `python3` with nothing behind it, `triage-state.sh`
  for a script since renamed to `.py`, and a relative path that needed a `cd` nobody
  wrote. It also carried *"S1–S18 are answered; S19 is filed and open"*, which was a
  counted claim about a moving corpus — exactly what the rule two lines up forbids.

## History

The August 2026 rounds (F12–F22, S18–S23, the `assets/fto_bmi/` assisted session) are all filed:
`previous_issues.md`, `just-dna-format-pending-fixes.md`, and `assets/fto_bmi/README.md` for the write-up. The
tables that used to sit here are in git (`git log -p -- docs/UX_TESTER.md`, before 2026-11-07). The last two
unfiled notes from then became **F126** on 2026-11-07. **What held up then and needs no re-probe:** every
refusal fired; the strict compile refused an unresolved module and named the remedy; `artifact_digest`
reproduced across a local recompile and the registry's own; an unanswered source was reported `null`, not `0`.
**The shape worth repeating:** a layman bringing a machine-written source. It exercised the lookups against
claims that were plausibly wrong, and it found more than solo probing.

## In flight

**2026-11-07: recheck of 0.48.0–0.48.2 on the shipped plugin (v0.48.2, in the host), part done.**

| claim | result |
|---|---|
| F31: `fetch_fulltext(pmid)` joins through PubMed | **holds**: the developer's case 41427385, and an independent one, 42990418 (a bioRxiv preprint in PMC). Both retrieved, and both name the ids PubMed supplied. Two publisher-OA papers (42988005, 42979923) got their DOI from PubMed the same way. 42967576 was answered by Europe PMC directly, so no PubMed note appeared, which is correct. |
| F50: "Try the locations below" only when there are some | **holds** on both branches: one real location each (42988005, 42979923), and a DOI-only call with none (`10.1038/ng826`) names the DOI. That call is where **F122** turned up. |
| 0.48.0: env token saved at start; skip a check answered `valid` under 1 h | **not exercisable here**: `sheep` has been saved since 2026-09-27, and the start-up check recorded `unreachable` (polygon HTTP 502). Forgetting the account to re-test it is not worth the risk. |
| 0.48.1: `remote_derive`/`remote_draft` send the token, refuse without one | refusal **holds**: `remote_derive(target="prod")` on `assets/fto_bmi` refused at once, naming how to get a token (**F123**: the saved accounts are missing from that list). Sending the token **waits on the polygon**, which still answers 502 (14:58 to at least 20:10 UTC). |
| F119 | suite-only; nothing to probe from the surface. |
| F100/F101 (never re-probed by this seat) | both **hold** on their own terms. The taught `rows=0` route drafts TPMT cleanly, and `check_pgx` gives the measured 5 compared. Found on them: **F125** (F100's appended repair is dead text since upstream reworded the refusal) and **F124** (`check_pgx`'s `next_step` counts the CPIC copy as agreement). Probe dirs: `data/interim/probe_f100/`, `data/interim/probe_f101/`. |

Found on the way: **F120** (fixed on main by the lead, 34de4b2, unreleased) and **F121** (simultaneous seat
restarts lose the server; reproduced twice). Both are in `dogfooding.md`. The way back from F121 inside a
session is `watchdog.sh reload --mcp` (kit v0.1.141), which types `/mcp reconnect all` once the session is idle.

**Then:** the HTT CAG binning module below, scaffold → compile → a polygon rehearsal.

**`assets/fto_bmi/` — done through the rehearsal.** Authored, enriched, strict-compiled, and published
to `test-sheep/fto_bmi@1.0.0` on the polygon; server-side recompile reproduced our digest. **Two things
remain open on it:**

1. **The production decision is the user's and has not been made.** They chose "polygon first, then
   decide". Do not promote without asking again — a production publish burns the version number *and*
   the right to publish that data under any other name.
2. ~~The polygon copy needs cleaning up.~~ **Done** — `registry_delete_module` removed it after the
   read-back, verified by a `404 module_not_found`. It mattered because the module name is not
   `test_`prefixed (only the namespace is), so `purge-test-data` would never have collected it. The
   committed `assets/fto_bmi/published.json` is therefore a *historical* receipt; its README says so, so
   nobody reads the 404 as a regression.

The namespace `test-sheep` is left claimed — it *is* `test-`prefixed, so the operator's sweep collects
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
