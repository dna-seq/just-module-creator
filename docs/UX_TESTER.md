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

**Benchmark round 4, handed over by the lead 2026-11-19 (the person's word).** Fixture `sirt6`, plugin 0.48.15, model
`claude-opus-5`, three runs (`data/interim/repro-bench-4/run-sirt6-{a,b,c}`), `claude -p --permission-mode auto` from
the repository, one after another in the lead's background job. Its briefs, JSON outputs (session ids), stderr and
`round.log` are in the lead's scratchpad (`a8d51777…/scratchpad/bench4`). Scored: a, b, c (2026-11-19 ~02:40 CET). Mine
once the job ends (the lead says): the leak check from each transcript, `bench_score.py --fixture
assets/benchmarks/sirt6` against Table 3 (`runs/1-3`), the census, the report to the writer. If the three match
Table 3, the person asks for one more run on `claude-opus-5-5` with the same brief; that run is the only thing that moves.
Result:
- Leak check clean for a, b and c. No banned path. Each prod `registry_search` returned only longevitymap and pathogenic,
  and `registry_claims` found no module claiming rs117385980. The variant first appeared from `lookup_citation` on the
  DOI.
- All six runs (round 4's three and Table 3's three) meet every threshold. a, b and c have pair recall 1.00 against
  Table 3's 0.67 / 1.00 / 1.00. Run a authored two more SIRT6 variants and three more PMIDs (precision over the
  fixture 0.33, no decoy).
- Build: a and b ran on the tag. c started 00:09Z, after 59e11d5 (F167's wording), read the changed `module-start`
  and called `provision_caches`; all three still report "0.48.15". All loaded skills from the working copy.
- Run d (claude-opus-5-5, same brief and flags) started from HEAD noted below, run dir `run-sirt6-d`, scratch in my
  scratchpad `bench4/run-sirt6-d`.

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

**The polygon answers again on format 0.8.0, 2026-11-10 (registry 0.28.5, compiler 0.8.0; production still
0.7.1).** Two legs, on scratch copies under `data/interim/recheck_08/`:

| leg | result |
|---|---|
| shipped 0.48.5, host wire: `registry_health(target="test")` | `contract_compatible: false`, and the message says every publish, validate, check and download will 409. Clear |
| shipped 0.48.5: `registry_check` on HTT | 409, with the instance note: "This is the instance, not your module". Clear |
| shipped 0.48.5: `remote_derive` on HTT (the 0.48.1 token leg) | 409 with advice about 503 and 422 instead of the instance note: **F144**. Whether the token was sent cannot be seen from a 409; that leg now waits for main to move to 0.8, not for the polygon |
| branch adopt-0.8 at 113150c (format 0.8.3), **in-process driver, not the host wire**: strict `validate_module` on HTT and MTHFR | both valid, no new decision to come forward from 0.7 |
| same: `registry_check(target="test")` on HTT | `verdict: true`, nothing blocking or unchecked, `content_signature` sha256:1d82655b... |
| same: `registry_check(target="test")` on MTHFR | `verdict: true`, nothing blocking or unchecked, `content_signature` sha256:7294cc72... |

The polygon's warnings on HTT read differently from the local ones: "no bin pmid" and "the field a consumer
reads ... (RUC)". That is its compiler 0.8.0, older than RM414 and RM415 (cut in 0.8.2), which fixed exactly
these two texts after our report. Nothing is lost in the upload: the local 0.8.3 run on the same bytes sees
the bin's pmid and `FORMAT/REPCN`.

The lead's list for the branch, same driver, same evening:

| item | result |
|---|---|
| `draft_from_strchive` with no `catalogue` (F129) | **holds**: HTT and FMR1 drafted from the provisioned lane. Beside them, a false "No `strchive` lane on this machine": **F145** |
| `enrich_module`'s `allele_mismatches` (RM382) | **holds**: on a strand-flipped copy of `assets/fto_bmi` (`recheck_08/fto_flip`), rs1421085 is in `unresolved` and the line names G/G, each of four sources' `16:53767042 T>C`, and "(fits the other strand)" |
| `enrich_gwas_effects` on the v2 API | **fails upstream**: the enricher asks for a page of 1000 and the Catalog refuses anything above 500: **F146**, handed to the liaison |
| `fetch_fulltext`'s outage line (F133) | not exercised: 5 of 5 calls for PMC13733956 returned `fulltext`, so no 500 came |
| recheck: F144 fixed on main (4f0085a), in-process on this checkout | **holds**: `remote_derive` on the polygon's 409 now carries the instance note, with no 503/422 advice |
| recheck: F145 fixed on the branch (8ac4c82) | **holds**: an HTT draft from the lane carries no missing-lane sentence |
| `enrich_gwas_effects` on **main** (shipped 0.48.5, host wire) | **fails**: the Catalog retired v1 (410), so F146 covers both builds |
| recheck: F146's half on main (3664412), in-process on this checkout | **holds**: the 410 now says the Catalog retired the API this build reads, that no retry or spec edit helps, and that the pass comes back with an enricher on v2 (RM428). The description keeps `1 + 2N`, by the lead's choice: it is what this build spends |

**Both rehearsals ran, from the branch, and left nothing behind** (2026-11-11 ~00:05 UTC, same driver).
`registry_publish(target="test")` as `test-sheep/test_htt_cag_repeats@0.1.0` and `test-sheep/test_mthfr_folate@0.1.0`.
Each was read back with `registry_get_module(target="test")`, with the same `content_signature` as its dry run,
then removed with `registry_delete_module`; a second read gives 404. The polygon's catalog counts are 50 modules
and 112 versions before and after. An earlier draft of these notes held the publishes to spare the `test-sheep`
cleanup (F143). That reason was wrong: a rehearsal deleted after its read-back adds nothing to the cleanup.

**0.48.6 recheck, 2026-11-11, over the host wire** (server restarted by SIGKILL plus `reload --mcp`; the
instructions name v0.48.6). The polygon now serves format 0.8.3.

| finding | result |
|---|---|
| F144 | holds: `remote_derive` on `assets/htt_cag_repeats` (`target="test"`) gets the 409 with the instance note, and no 503/422 advice |
| F146, our half | holds: `enrich_gwas_effects` on `recheck_08/fto_gwas_main` carries "The GWAS Catalog has retired the API this build reads (HTTP 410, Gone) ... (upstream's RM428)" beside the raw 410 |
| new: `validate_module`'s `warnings_summary` and `carried` | present: on `recheck_08/mthfr`, `warnings_summary` counts the three warnings by code, and `carried` holds the one restated from `verification.json` |

**F146 on adopt-0.8 at f4793de (just-dna 0.8.4), 2026-11-11, in-process driver: holds.** `enrich_gwas_effects`
on `recheck_08/fto_gwas` (the copy that got the 400 at 113150c): `success: true`, 223 rows for rs1421085,
`requests_made` 218 and `requests_saved` 6. Of the 223, 38 name no effect allele and 3 have p-values below
float64's range; there are 6 distinct `effect_unit` values. All of these are stated in `warnings`. It took
**4 min 45 s of wall time for one rsID** (7.5 s of CPU); at that rate a 50-rsID module runs for hours. The
branch's description gives the budget in requests (a page per variant plus one per distinct study), not in time.

**0.48.7 recheck (just-dna 0.8 on main), 2026-11-12, over the host wire** (server restarted by SIGKILL plus
`reload --mcp`; the instructions name v0.48.7 and format 0.8.4). Both registries serve registry 0.30.0 on format 0.8.4.

| check | result |
|---|---|
| `registry_health` on test and prod | `contract_compatible: true` on both (0.8.4 / 0.8.4); the 409 skew is gone |
| `registry_check(target="test")` on `assets/htt_cag_repeats` | `verdict: true`, signature sha256:1d82655b... as before. The polygon's warnings now read the bin pmid and `FORMAT/REPCN` (RM414/RM415 are on the server) |
| F145: `draft_from_strchive(["HTT"])` without a catalogue, dry run | holds: one locus from the lane, no missing-lane sentence |
| F146: `enrich_gwas_effects` on `recheck_08/fto_gwas_main` (the copy that got the 410) | holds: `success: true`, 223 rows, 218 requests; same warnings as on the branch. It ran past the host's 120 s and finished as a background task |
| new: `registry_rename_namespace` dry run on the polygon | works: `test-sheep` to `test-winternewt` is refused, `namespace_taken` (the lead saw this too). To a free name it reports 20 modules and 44 versions that would move, `test-sheep` kept as an alias, `applied: false`. Two of the 20 module names have no `test_` prefix (`longevity_2026`, `longevity_rare_variants`); that bears on desk #255, not on the tool |

The GWAS description in the source gives the v2 budget and the time ("rs1421085's 218 took 4 min 45 s"). ToolSearch
still shows the old `1 + 2N` text: the host cache noted below, not a regression.

**F147 recheck on main at bed200b (unreleased), 2026-11-12, in-process: holds.** Same dry run on
`recheck_08/apoe_nogene`: 3 hints for 3 positions, each naming both row keys there (VRS id and `chrom:pos:ref`).
Every gene carries `start`, `end` and `distance_bp`; the containing gene is at 0 (TOMM40, TOMM40, APOC1), and the
nearest distances match the ones I measured from upstream's spans (NECTIN2 2,455 bp, APOE 9,778 bp). Order is
upstream's (by start), not ranked: the lead's call, since nearer is not likelier. The containing gene is
findable by `distance_bp == 0`. Note for my driver: its 12,000-character cut breaks JSON on a large result;
`drive08_full.py` writes it whole.

**0.48.8 probe, 2026-11-12** (host wire for `registry_lane_lookup`; in-process for `remote_derive`'s new arguments,
which the host's cached schema lacks). Found **F148** (the lane lookup serves pharmvar, pubmind and mane rows
that `/caches` refuses to redistribute; registry S29 answered "by design", our terms field is on main), **F149**
(`remote_derive` crashed on any spec holding a `verification.json`) and **F150** (`passes_report` always null:
`check.json`'s `passes` is a list; the polygon skips a live GWAS pass because its own `enrich_offline` outranks the
caller, registry S30, fixed in their tree).

Rechecks on main, in-process, each after the polygon's 429 cleared (enrich bucket, about 10 minutes per call):

| finding | result |
|---|---|
| F149 (d9651d1 + 26009a1) | holds: on `recheck_08/fto_remote`, which keeps its `verification.json`, no crash. `decisions` names `verification.json` as replaced whole. Its wording, "Installing captures your copy first" (8f5b473), now holds on a dry run too |
| F150 (2a4b421) | holds: `passes_report` is `[{"command": "gwas", "status": "skipped", "detail": "offline: this pass needs a live source ...", "tables": ["gwas_effects.csv"]}]` |

Lessons for this seat. **Run the release, not the working tree**: the lead's uncommitted edits sit in the shared
tree, and one import caught a file mid-save (`git archive <tag> src` plus `PYTHONPATH` runs the release whole).
**Pace polygon derives at one per ten minutes**: six in four minutes bought a 429 per call after that.

**0.48.9 smoke, 2026-11-13, over the host wire** (instructions name v0.48.9, format 0.8.5).

| finding | result |
|---|---|
| F148 | holds: `registry_lane_lookup` on `pharmvar`/`alleles` (`CYP2C19*2`) carries `licence: CC-BY-SA-4.0`, the notice, the URL and `redistribution: "refused: ..."` beside the row |
| F149 | holds: `remote_derive` on `recheck_08/fto_remote` (keeps its `verification.json`) answers with the decision line, no crash |
| F150 | not re-run over the wire: this session's cached listing has no `passes` argument (the known first-connection cache). 2a4b421, which I rechecked in-process on main, is in v0.48.9 and `_passes_from` is unchanged since |

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

**Next probes, in order:** (1) the polygon leg of 0.48.1 and the HTT and MTHFR rehearsals: dry runs pass from
the 0.8 branch (2026-11-10, above); both were rehearsed and deleted on 2026-11-11 (above). The token leg waits on a
build that speaks 0.8 being what the host runs;
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

**S33 recheck on registry 0.32.0 (both instances, read 02:40 CET 2026-11-17), polygon `test-sheep/test_statin_response@0.1.1`.**
The owner's own highlighted review leaves the card `curated: false` with verdict `concerns`, and still with `verified`
(0.31 made it `true` on 2026-11-15). So curated now needs an outside `verified` highlight, and the live descriptions of
`registry_review` and `registry_reviews` ("curated whatever its verdict") are false on both instances; rewording them is
in the lead's 0.32 adoption. Seen in passing: re-posting a highlighted review with another verdict kept
`highlighted: true`. With an outside reviewer that would let a highlighted `concerns` become `verified`, and the card
curated, without the owner acting again; untested, since `sheep` is the only account. Cleaned up: unhighlight, delete,
card back to `curated: false, review_count: 0`.

**RM31 hand trial, fresh-eyes read (2026-11-16, at the lead's request; `test-sheep/test_fto_bmi_trace@0.1.0`).**
Read from the download alone, then compared with the lead's DESIGN-traceability §10 (branch `rm31-trial`, 0838354).
Both fulltexts refetched: sha256 and length match the ledger and every anchor resolves. What §10 does not say:

1. **The `rs9939609 not_used` reason has no witness.** Its `why` is LD with rs1421085; both anchors sit in PMID
   28642257 (FTO x depression meta-analysis) and say rs9939609 is associated with BMI. That paper never names
   rs1421085. The anchors look like support for the reason and witness something else.
2. **`traced` covers the quote, not the row.** The MC4R rows' weights (-0.3/-0.15 against FTO's -0.5/-0.25) have
   nothing behind them; the paper gives SMDs and no event maps one to a weight. §10 drops `basis` as not needed;
   the weight is where a basis was missing.
3. **The rs17782313 conclusion keeps the publication bias and drops the next sentence** (trim-and-fill changed nothing).
4. **Nothing records the candidates not read** (7 of 8 PMIDs per search), nor why rs17782313 replaced the README's
   dropped rs6567160, nor the A allele at a T>A,C site.
5. **All nine events carry 19:21:32Z**, so the ledger reads as written after the fact; edits carry no values written.
6. **What ships contradicts the module:** licensing.csv's europepmc/pubmed notices say no fulltext was fetched and
   provenance_quote is empty by design; README.md is fto_bmi's; the spec says 1.0.0 against identity 0.1.0 (F158).
   Manifest `authorship`/`authors` are empty and every decision is the agent's.

Full reading kept in the session scratchpad; the summary went to the lead.

**`registry_members` add/role/remove on the polygon, 2026-11-16, after kit rule 23 was applied** (it answers kit
#491; the classifier let every call through). On `test-sheep`: `add test-nobody-probe` → `HTTP 404: account_not_found`;
`role` on a non-member is refused locally with "not a member ... nothing was sent", as the description promises;
`remove` a non-member → `HTTP 404: account_not_found`; `add` with no `account` refused locally. The list still reads
`sheep`/owner alone. **The success path of add and role is still unexercised**: `sheep` is the only saved account, and
adding a real person's polygon account, or registering a second one (an account cannot be deleted), would leave a write
the polygon does not get back. It waits for a second account the person makes available.
**0.48.13 recheck, 2026-11-17, over the wire (server restarted by SIGKILL and `reload --mcp`; header v0.48.13).**
F155 holds (`antonkulaga/apoe_epsilon@1.1.1` copy: added `variants.csv` `only_local`, removed `diplotypes.csv`
`only_published`, `unknown` empty). F156 and F157 hold (`longevity`: three defining terms and the obsolete
`EFO_0004300` -> `OBA_VT0005372`; `["efo","ebo"]` refused by name). F158 holds for version and for a different name;
its `test_` allowance is refused by the registry: **F160**. F159 holds: a planted `logs/trace/*.jsonl` with a home path
is flagged (the scan notes, it never refuses, by design). The installed enricher is 0.8.7, so the floor is met. F154's
wording is in the live description.

**RM31 F161 recheck, 2026-11-17, on `rm31-build` eef1fb4 (local).** The first session's ledger re-joined: the
citation-traversal row now reads `not_traceable` ("found by a route the ledger does not see"). A second headless session
(`paper_citations(26287746)` -> 42968160, fetched, two rows): the ledger records `paper_citations` as a search; the
row quoting a sentence of 42968160 reads `traced`; a quote of the title's first five words reads `contradicted`, "a
piece of the cited article's own title". Holds. Codex still untried.

**RM31 F162 recheck, 2026-11-17, `rm31-build` 22a4ef4.** A fresh headless session, same four decisions: A (true LD
reason) and B (reason its passage contradicts) read `anchored`, "whether it supports the reason is for a reader", each
with `passages` (pmid, sha256, offset, len); C (weight reason naming no variant) reads `declared`; D `recalled`. Holds,
with B honestly labelled rather than caught. The revised reviewer brief now re-fetches and reads each anchored span,
names the judged cells and the non-table files, notes unopened results, and reads `trace_module` last. One leftover:
re-joining a ledger written by 18b6cec's hook (no `tied` field) reads all four as "the reason names no variant",
including A and B, whose `why` names two rsIDs; only pre-release ledgers carry that shape.

**Polygon claims and `pgs_id` reads on registry 0.32.0, 2026-11-17 (pending since the polygon served 0.30).**
`registry_claims(variant="RS429358", target="test")` folds the spelling (`variant_keys: ["RS429358","rs429358"]`), 11
modules, 32 claims, each carrying `haplotype`; `conflicts.compared: 0` with reasons. `registry_search(pgs_id=...)` is
accepted on the polygon now (0 matches for PGS000001). The live `registry_claims` description still says 0.31 answers
`RS429358` empty; false on both instances now, and its rewording is in the lead's 0.32 adoption. F150 closed by the
liaison (c577c01).

**Owed when an instance serves registry 0.33 (S35, decided 2026-11-17):** a re-post that changes the verdict should clear
the owner's highlight; a notes- or rating-only edit keeps it. Testable with `sheep`'s own review on
`test-sheep/test_statin_response`: post, highlight, re-post with another verdict, read `highlighted`; then a notes-only
re-post; clean up.

**0.48.14 recheck, 2026-11-18, over the wire (server restarted by SIGKILL and `reload --mcp`; header v0.48.14).**
F160 holds (`test_fto_bmi` over spec `fto_bmi` refused locally; publish's description is stale from the host cache only).
F163 holds. A released-plugin session (`claude -p --plugin-dir` this checkout, `env -u JMC_TRACE`, transcript `4e010476`):
search, citation traversal, two fetches, a decision and a `Write`; `trace_module` over the wire reads both quotes
`traced` (one through `paper_citations`) and the decision `anchored` with its passage. New: F164 (the released
description still promises F161's `contradicted`; fixed on main) and F165 (a shell-written edit leaves no ledger, the
end hook drops pending events). The first headless connect timed out (added to F121).

**F165 recheck, 2026-11-18, on main 81af555 (unreleased).** A headless session told to write `studies.csv` only through
`Bash` (a Python `csv` script): the ledger holds both searches, both fetches, the decision and an edit with route
`Bash`; both quotes read `traced` (one via `paper_citations`), the decision `anchored`; no path in the ledger. A module
with no ledger now names all four causes and says which is not recorded. Holds.

**Owed at 0.48.15, 2026-11-18.** The lead lifted four mitigations on main (641496903): F93 (the proxy asks
`sidecar_write_path` directly, 43a36f5), F94 (every lane priced from `approx_mb`, 3934432), F67 and F63 (kept, comments
and a test). Over the wire after the release: a `remote_derive` into a module carrying only `sources.csv` writes back to
that spelling, never a second file; `provision_caches` prices each lane from its own size, none at a flat guess.

**RM32 probe, 2026-11-18, on main ab441e8 (unreleased).** Interactive Claude Code driven through tmux
(`tmux -L rm32`, `--debug`, the folder trusted once): question counts only, the declined wording nowhere under the
module or in the hook cache, the approved one `approved: true`. Holds. Print mode auto-answers the elicitation: F166.
Recheck F166's fix with one `claude -p` run (`scratchpad/rm32b/prompt.md`) and one tmux run (`rm32c/prompt.txt`).

**F166 recheck, 2026-11-18 evening, on main 069e6a9 (7d2fad5, 756ee80; unreleased).**
- `claude -p`: `approved: null` with the "dismissed, or nobody was there" note, and the decision is in the ledger as
  `approved: null`.
- tmux: a decline returns `approved: false`, "The person declined this wording", and records nothing. Esc returns
  `approved: null`, kept, and `trace_module` reads "no approval of this wording was seen by the tool". `by='author'`
  with `basis='recalled'` is refused.
- Neither the declined wording nor the refused wording is under the module or in the hook cache.

Holds. The first headless connect timed out again (added to F121).

**0.48.15 recheck, 2026-11-19, over the wire (server restarted; it announces v0.48.15).**
- F164 holds. A fresh server's `tools/list` carries the fixed `trace_module` description. This session's host still
  shows the old text from its cache, which a new session doesn't have.
- F93 holds. `remote_derive(dry_run=false, target="test")` on a copy of `hfe_hemochromatosis`, which carries
  `sources.csv` only, installed into `sources.csv`, and no `licensing.csv` appeared.
- F94 holds. Every lane is priced from its own `approx_mb`, labelled so. New: F167, the note and the description still
  say the sizes are not the lanes' declarations, and still count fifteen lanes where the call lists 17.
- F165 is carried from the main check (81af555). The tag's shell route is unchanged; the hook config only adds
  `AskUserQuestion`.

## Standing constraints

- Never commit in a sibling repo. Writing the upstream note is the whole job; leaving
  `../just-dna-format` dirty is the expected end state.
- Never `git add -A`. Stage explicit paths.
- Committing in **this** repo is pre-authorised and expected as you go.
