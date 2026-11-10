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
- **`/mcp reconnect all` retries only the servers that failed; a connected one keeps running old code**
  (2026-11-08 08:20 UTC). The kit typed it for 0.48.3, the host answered "Reconnected 4 of 22", and this
  session's server was still the 19:38 process (v0.48.2) with no new line in its connect log. The kit's typer
  types only that fixed text. What does work: kill the session's own server child (the python under its
  `uv run`; it **ignores SIGTERM**, so `kill -KILL`), the host marks it failed, then
  `watchdog.sh reload --mcp`. Find the child by the session's pid (`$PPID` of a Bash call) as the `uv run`'s
  parent; never another session's.
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

**2026-11-08: recheck of 0.48.3 on the shipped plugin (v0.48.3 in the host, server started 09:24 CET).**

| claim | result |
|---|---|
| F122: a DOI alone joins to its PMID | **holds** on both DOIs (bioRxiv `10.64898/2026.10.26.761951` → 42990418/PMC13733956; `10.1038/ng826` → 11788828, abstract). The joined call still **retrieves nothing** for the PMC paper the PMID route reads whole: **F133**. |
| F123: the no-token refusal names saved accounts | **holds**: `remote_derive(target="prod")` leads with `registry_accounts(action="add", …)`. |
| F124: `check_pgx` calls the CPIC leg a copy | **holds**: "5 compared against pharmvar … cpic answered with a copy, not a comparison". |
| F125: the stub-row refusal ends in this surface's repair | **holds** on `probe_f100/tpmt_default`: `scaffold_module(kinds=[...], rows=0)`. |
| F129: `draft_from_strchive` drafts HTT | **holds** (1 locus row, MIT licence row). The row has no bands, by upstream design, and our docstring promises them: **F134**. |
| F120: findings labelled by source | **holds**: every `fetch_fulltext` finding above says `just-module-creator`. |

The polygon still answers HTTP 502 (17:3x UTC), so the 0.48.1 token-sending leg and the HTT rehearsal wait.

**F133 was misdiagnosed by this seat** (the lead, 7c188be): the cause wasn't the DOI/PMCID route. Europe PMC's
`fullTextXML` answered HTTP 500 on 5 of 10 plain requests for the same PMCID, and enricher 0.7.3 folds a 500 into
`None`. My "3 by DOI, 2 by PMCID, PMID works" pattern was chance, against one direct control call. **Lesson:
before naming a route as the cause, repeat the control as often as the failing call, because a flaky upstream
produces route-shaped patterns.** F133 (now a "call again" warning) and F134 are fixed on main, unreleased:
recheck both at the next release.

**The Atlas probe ran on 2026-11-09** (0.48.3, `ALPHAGENOME_API_KEY` from `.env`; polygon still 502). Work happens on
copies under `data/interim/probe_atlas_fto/`, because every call makes the directory non-commercial. F140 and F141
are in `dogfooding.md`, the reference example is `assets/fto_bmi_atlas`, and the lead has been told. I applied
F133's lesson: each timing was repeated, and no cause is named. Timings come from the host's log
(`~/.cache/claude-cli-nodejs/<project>/mcp-logs-plugin-*/`, the "completed in" lines); that log keeps the
server's stderr only from startup. The multi-window run (`longevity_2026`, 13 windows, 11 to 14 s) produced F142:
`effect_size` is one track's signed extreme and `effect_direction` is the majority vote, so their signs disagree in
128 of 819 rows. The upstream half (format's field description) went to the liaison. Upstream took it as RM425
(a wording patch). Our half is on main as d71d81e, unreleased. **At the next release, recheck F133, F134, F135 (a924b2d: `check_identifiers` names `enrich_module` when it skips), F138 (4860572, `audit_module` on `assets/mthfr_folate`) and F142's
wording** in `enrich_expression_effects` and `top_expression_effects`.

**0.48.4 recheck, 2026-11-09 (server restarted 10:17 local time, via SIGKILL and `reload --mcp`).** Each fix was checked through what
the call returns, on scratch copies under `data/interim/recheck_0484/` and the earlier probe directories:

| finding | result |
|---|---|
| F133 | not exercised: Europe PMC answered 3 of 3 for PMC13733956, so the "call again" path never fired |
| F134 | holds: `draft_from_strchive` says one row per locus, then split into bands and run `check_repeat_bands` |
| F135 | holds: on rsID-only rows, `check_identifiers`' next step names `enrich_module`, then `refresh_sidecar` |
| F136 | holds: the 28 repeated PubMind advisories collapse into one with a count. The cold call still took 3 min 34 s, which the description now warns about |
| F137 | holds once the test is right: `sidecar_rows_nothing_authors` names rs429358 in `resolution.csv`. My first try left the rsID in `studies.csv`, which counts as authored, and the audit correctly said clear |
| F138 | holds: a stale `verification.json` reads `not_computed` with upstream's reason, and diplotype directions are read |
| F139 | holds: on `assets/mthfr_folate`, `checks_older_than_the_last_edit` names 5 checks from 02:38 |
| F140 | holds in the descriptions only: the IRX3-only result still reads `gene_not_at_locus` and says nothing inline. The lead has since put it in the result's `next_step` (on main, unreleased): **recheck at the next release** on `data/interim/probe_atlas_fto/fto_irx3` |
| F141 | holds: the dry run calls its 26 s a floor, and `seconds_elapsed` and `slowest_window_seconds` are on the result |
| F142 | holds: the ranked list's next step names its 2 opposite-sign rows and says why |

**0.48.5 recheck, 2026-11-10 (server restarted via SIGKILL and `reload --mcp`).** Scratch copies under
`data/interim/recheck_0485/`:

| finding | result |
|---|---|
| F132 | holds: `validate_module` on an unclosed copy of `assets/fto_bmi` returns `on_this_surface` naming `close_module` beside the closure warning, which still says `just-dna-compiler close` |
| F126 | holds in the source (`auth.py`): the docstring gives the order `JMC_INSTALL_ID`, then the saved account, then a fresh grind, and `_echoed` withholds a reused id. ToolSearch still shows the old description (host cache), and no live register was run |
| F140 | holds in the result: on `data/interim/probe_atlas_fto/fto_irx3` the `next_step` opens "2 authored row(s) read gene_not_at_locus (rs1421085)" and names `rows=true` |

**The host keeps the tool descriptions from its first connection.** After the server restart, ToolSearch still
returned 0.48.3's descriptions, and the source has the new ones. A fix that is only in a description can't be
rechecked in a reconnected session: read the source, or recheck from a fresh session.

**2026-11-09: layman probe, MTHFR from a planted AI summary: done to a strict compile.** The write-up is
`assets/mthfr_folate/README.md`; the scratch work is `data/interim/probe_layman_mthfr/` (gitignored). It also
covered the "module with two of something" probe: a two-variant diplotype module with a cis twin, where the
compiler's phase-ambiguity warning fires as intended. Found: **F135** (the triage gene-locus check has no input
in the taught order), **F136** (`lookup_variant` size and cold start), **F137** (orphan sidecar rows after a
table is removed, upstream S138), **F138** (audit reads a stale verification), **F139** (high: a re-attestation
re-signs checks it didn't re-run; liaison filing). The polygon rehearsal waits with HTT's. Not done:
`thrombophilia` in prod lists related loci and was not read; `trait_efo_id` is empty.

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

**HTT CAG binning module: done to a strict compile (e7f2424), the rehearsal waits on the polygon.** The
README of `assets/htt_cag_repeats/` is the write-up. The plugin's own `todo` holds the rehearsal step.
F128 (skills from the released 0.47.0) is on the person's desk as #229; until it is answered, read the
checkout's `skills/` by hand. Two compiler findings went to the liaison: the RUC/CIRUC warnings ignore
`source_field`, and `bins_ungrounded` says "no bin pmid" while one bin carries one.

**Next probes, in order:** (1) the polygon leg of 0.48.1 and the HTT rehearsal, when the polygon answers;
(2) a module authored from nothing through the front door by a layman, as the handout's fallback; (3) the
list in `dogfooding.md`'s "Probes not yet run" (`enrich_expression_effects` live, a module with two of
something).

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

## Standing constraints

- Never commit in a sibling repo. Writing the upstream note is the whole job; leaving
  `../just-dna-format` dirty is the expected end state.
- Never `git add -A`. Stage explicit paths.
- Committing in **this** repo is pre-authorised and expected as you go.
