# Liaison — notes

The liaison seat's working state, rewritten to the present before a reset (`docs/seats/LIAISON.md`).

## Now

First seating 2026-11-07 (the seat-builder's handout and first work). Commits: `c361614` (polars, duckdb `<2` in
the lock), `09404dc` (watchers), `44a2880` (three ledgers, F85, the pending-fixes table against 0.8.0). Pushed
2026-11-07 on the person's word ("push granted", this session only), with the tester's and the lead's commits
between. Later ledger commits: `a9eee8c`, `b5be9c4` (v0.8.1 read), `2d8b3a5` (the polygon's 502).

## Watchers

`compiler` (tags of `dna-seq/just-dna-compiler`, from the registry liaison's state-file line `just-dna-compiler`,
reused), `registry` (this seat's line `just-dna-registry`, the registry's own clone, fetch only), `nightly` (the
weekly dependency bump), `desk`, `brief`. All started 2026-11-07. `upstream-index` (the package index, `--upstream`, over the format trio, the registry client and fastmcp; added 2026-11-13 on the seat-builder's handoff, `dffb355`): a `published` line starts the per-release read, often before the tag line; fastmcp's 4.x lines were read against the `<4` lift gate until 0.48.19 lifted it (2026-11-23); now for what a release moves. 4.2.1 (2026-11-17) read 2026-11-18: OAuth and token hardening, nothing about the session-state loss (#4920) the gate is for; its security floors (`opentelemetry-api>=1.45.2`, the traceparent ReDoS GHSA-mf5v-w3w3-f6cg on the default telemetry path, and dnspython 2.9.2) are already what our lock holds under fastmcp 3.4.11. 4.2.2 (2026-11-18) read the same day: skills discovery under tool-only transforms only; #4920 still open, so the gate stands. 4.2.3 (2026-11-20) read the same day: opt-in `parent_task_spans` for background-task traces, three output-schema conversion fixes, an OpenAPI missing-path-argument fix, `pydocket>=0.29.1` under `fastmcp-tasks`; nothing about #4920 (still open), so the gate stands; no new 3.4.x. 4.2.4 (2026-11-21) read the same day: fixes GHSA-78c8-3jhx-5mg7 (medium; an OAuth proxy authorization code or refresh token redeemed twice under concurrency), affected `>=2.13.0,<=4.2.3` so our 3.4.11 too, patched only in 4.2.4; not reachable here, since nothing in `src/` or `fastmcp.json` configures fastmcp's OAuth proxy or any server auth. Also a transform that cannot apply hides only its own tool. #4920 still open; the gate stands. **4.2.5 (2026-11-23) closes #4920** (by fastmcp#6551: `subscriptions/listen` served on 2026-07-28 connections, `notify_*` pushes change events; on by default, `FASTMCP_ENABLE_SUBSCRIPTIONS_LISTEN=false` turns it off). Measured the same day in `.worktrees/liaison-try-fastmcp-4.2.5` (pin `>=4.2.5,<5`, `TasksExtension` re-added, `McpError`→`MCPError` in two places; mcp SDK 2.3.0): **the gate passes**, the default client negotiates 2026-07-28 and `toolbox(groups=["evidence"])` lands 7 tools on the next `list_tools`. Whole suite 1098 pass, 4 fail, one cause: `ctx.elicit()` now refuses `response_type=None` (`record_decision`, `tests/test_trace.py`). **Session state still does not persist** on that wire (a bare `ctx.set_state` then `get_state` on the next call returns `None`, in-memory default client), so `session_state_persists`' unconditional `True` would report a stored token the next call cannot find; the suite has no default-mode token test to show it. Handed to the lead as a lift measurement, not taken. **The lead lifted the pin** on that base the same day (`220747d`, released in 0.48.19, `v0.48.19` `c58fc0a`): the modern-wire branch back in `session_state_persists`, `record_decision`'s question a bool (a modern connection reads as cannot-ask, F172 open), `make_client` on `mode="legacy"`. From now the upstream-index lines for fastmcp are read for what a 4.x release moves under us, no longer against a gate. 4.2.6 (2026-11-25) read the same day: Authlib dropped from fastmcp's dependencies (only fastmcp-slim pulled it in here; nothing in `src/` or `tests/` imports it), `fastmcp.experimental.events` moved to a `fastmcp-events` package (not used here), a client-side `CodeModeClient`, and client, OpenAPI and response-limit fixes. Nothing about session state or server-pushed elicitation on the 2026-07-28 wire, so `session_state_persists` and F172's input-required path stay as they are. Inside `>=4.2.5,<5`; the weekly bump of 2026-12-01 takes it. The hosts have none: read `claude --version` and
`codex --version` at each start against `docs/UPSTREAM_HOSTS.md`.

## Half read

- Nothing. Release 0.48.14 (2026-11-18, `7e6d673`) carries format/compiler 0.8.6, enricher 0.8.8 (RM445) and registry client 0.32.0; F148/S29, S31, S32, F153/S33 and `upgrade_status` marked released and closed the same day. Read to v0.8.8 and registry 0.34.1 (2026-11-19; 0.34.1 from the wheel, untagged then). Both instances serve registry 0.32.0 on format 0.8.6 (2026-11-17). Registry 0.33.1 on PyPI 2026-11-18 carries S35; watch an instance serving it (then the tester checks and S35 closes); the lanes' `release`/`revision` passthrough is on main (`54134ca`), for the next release.

## The dependency bump

- Last run 2026-11-24, `33bc35e` (24 packages; suite 1110 pass and 1 skip in a fresh worktree, the same 8 ResourceWarnings as the old lock, ruff and pyright clean), then the registry client held back to 0.32.1, what both instances serve, in the commit after it (`ec2c96a`); both released in 0.48.20. **Hold the registry client at what the instances serve**: `uv lock --upgrade-package 'just-dna-registry==X'` after the upgrade, as the lead did on 2026-11-17. The hold ended 2026-11-26: both instances serve 0.34.4, the client moved to 0.34.3 (`f547e16`). Next: Tuesday 2026-12-01; hold the client again at what the instances serve. Registry 0.35.0 (2026-11-28) floors format 0.9, so on main the resolver keeps it out by itself; it moves with the lead's `adopt-0.9`, with its `compares` and `routes` fields (handed over 2026-11-28).
- Run 2026-11-17, `af1f0c6` (13 packages; registry client held at 0.31.0 by `uv lock --upgrade-package just-dna-registry==0.31.0` after the upgrade, on the lead's word until an instance we read serves 0.32; pytest-asyncio 1.5's loop-scope warning settled in `pyproject.toml`). Next: the nightly watcher's Tuesday.
- **The tree is shared: a peer's `git checkout -- uv.lock` before its merge discarded an uncommitted bump mid-run once (2026-11-17; the lead, who owned it), and a peer's `uv run` re-syncs `.venv` to the committed lock.** Commit the lock as soon as the checks pass, and read `git diff --stat uv.lock` right before committing. **Before any `uv lock` in the main checkout, read `git status --short pyproject.toml uv.lock` first**: 2026-11-20 I upgraded the lock over the lead's uncommitted 0.48.16 bump and had to restore it (HEAD lock plus `uv lock`). Test an upgrade in my own worktree; in main, only when both files are clean.
- 2026-11-10, `ebca264` (56 packages; tenacity `initial=` to `multiplier=`, floor 9.2.1).
- **Run the whole `uv run pyright` and `uv run ruff check .`, not just the files you touched.** This run checked
  only `net.py` and its test; pydantic 2.14's typing of `FieldInfo.annotation` broke `tools/config.py`, and the
  lead fixed it forward in `6d9f3d0`.
- Filed with the kit as #378 (2026-11-10): step 3 of "The dependency bump" to run the type checker and linter too.
- A stash made by mistake during the 2026-11-10 bump (a copy of `ebca264`'s `net.py` change) was dropped by the
  person the same day. Test a change against the old spelling in a scratch copy, never with `git stash`.

## Waiting on others

- Nothing from the lead's lifts: F59 closed in 0.48.11; F93 and F94 lifted on main 2026-11-18 (`43a36f5`, `3934432`,
  ship in 0.48.15); F63 and F67 kept by the lead's decision (`18c3319`/`f974123`, `e0ea8d4`). All five closed in the ledger.
- Format minors still open upstream: RM429 (F146, parked; our interim on main), the minor halves of RM427 (F132),
  RM426 (F135) and RM423 (F139; our audit signal removed by the lead in `c14cee2`). Registry: S29's per-answer
  terms field, undecided.
- Desk #255 (the lead's, the person's): the polygon's `test-sheep` namespace; default leave it.
- The 0.8.4 re-run (2026-11-12): F142, F137, F130, F131, F127, F115, F113, F116 and F146's S143 half closed; F132, F135, F139 pass their patch halves. F118 closed the same evening over `statin_response`. F85 closed 2026-11-13 over a strand-flipped `fto_bmi`. Nothing from the 0.8 re-run is left open on my side.
- Format: RM427 (S142, F132: `clinvar pull` at two sites; guard walk; remedy key a minor), answered 2026-11-10.

- `just-dna-registry/lead`: `just-module-creator/liaison` in its triage's `wake_from` (asked in
  `#agent-chat>wake_from`, 2026-11-07). The compiler's lead did it (their `8de1fa80`).
- Desk #221 (the person): whether the liaison or the lead does an in-house minor's mechanical half (floors,
  lock). The seat-builder added this repository to it, 2026-11-07. Until answered, the lead keeps the format minor.
- The lead and the pm: the 0.8 adoption map (told in `#just-module-creator>0.8`). The caps come out with the
  adoption, not before.

## Picture

A capybara with a satchel of letters, set 2026-11-07 from the admin seat's reply.

## Handout, item 1 (tools against the kit's)

Nothing to retire or move: the repository had no liaison machinery before the kit. Upstream filing was by hand
per CLAUDE.md §8 (the triage-state scripts it names are the upstreams' own); kept as written.

## To file (unattended)

Nothing yet.
