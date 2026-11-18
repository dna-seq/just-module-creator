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
weekly dependency bump), `desk`, `brief`. All started 2026-11-07. `upstream-index` (the package index, `--upstream`, over the format trio, the registry client and fastmcp; added 2026-11-13 on the seat-builder's handoff, `dffb355`): a `published` line starts the per-release read, often before the tag line; fastmcp's 4.x lines are read against the `<4` lift gate, not taken. 4.2.1 (2026-11-17) read 2026-11-18: OAuth and token hardening, nothing about the session-state loss (#4920) the gate is for; its security floors (`opentelemetry-api>=1.45.2`, the traceparent ReDoS GHSA-mf5v-w3w3-f6cg on the default telemetry path, and dnspython 2.9.2) are already what our lock holds under fastmcp 3.4.11. The hosts have none: read `claude --version` and
`codex --version` at each start against `docs/UPSTREAM_HOSTS.md`.

## Half read

- Nothing. Release 0.48.14 (2026-11-18, `7e6d673`) carries format/compiler 0.8.6, enricher 0.8.8 (RM445) and registry client 0.32.0; F148/S29, S31, S32, F153/S33 and `upgrade_status` marked released and closed the same day. Read to v0.8.8 and registry 0.32.1. Both instances serve registry 0.32.0 on format 0.8.6 (2026-11-17). Watch: registry 0.33 (S35's verdict-change rule) reaching PyPI and an instance.

## The dependency bump

- Last run 2026-11-17, `af1f0c6` (13 packages; registry client held at 0.31.0 by `uv lock --upgrade-package just-dna-registry==0.31.0` after the upgrade, on the lead's word until an instance we read serves 0.32; pytest-asyncio 1.5's loop-scope warning settled in `pyproject.toml`). Next: the nightly watcher's Tuesday.
- **The tree is shared: a peer's `git checkout -- uv.lock` before its merge discarded an uncommitted bump mid-run once (2026-11-17; the lead, who owned it), and a peer's `uv run` re-syncs `.venv` to the committed lock.** Commit the lock as soon as the checks pass, and read `git diff --stat uv.lock` right before committing.
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
