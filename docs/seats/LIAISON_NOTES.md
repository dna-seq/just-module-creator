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
weekly dependency bump), `desk`, `brief`. All started 2026-11-07. The hosts have none: read `claude --version` and
`codex --version` at each start against `docs/UPSTREAM_HOSTS.md`.

## Half read

- The polygon answers again (21:22 UTC, 2026-11-10) on format 0.8.0; production on 0.7.1. Main (0.7) cannot rehearse there until `adopt-0.8` lands; read production's version for the adoption.

## The dependency bump

- Last run 2026-11-10, `ebca264` (56 packages; tenacity `initial=` to `multiplier=`, floor 9.2.1). Next: the
  nightly watcher's Tuesday.
- **Run the whole `uv run pyright` and `uv run ruff check .`, not just the files you touched.** This run checked
  only `net.py` and its test; pydantic 2.14's typing of `FieldInfo.annotation` broke `tools/config.py`, and the
  lead fixed it forward in `6d9f3d0`.
- Filed with the kit as #378 (2026-11-10): step 3 of "The dependency bump" to run the type checker and linter too.
- A stash made by mistake during the 2026-11-10 bump (a copy of `ebca264`'s `net.py` change) was dropped by the
  person the same day. Test a change against the old spelling in a scratch copy, never with `git stash`.

## Waiting on others

- The lead: five pending-fixes entries reproduced as fixed leave code of ours to lift (F94, F93, F63, F59, F67;
  told in `#just-module-creator>0.8`, 2026-11-07).
- Format v0.8.3 (2026-11-10) released RM422 (F137) and RM423's patch half (F139); not in our lock. The 0.8 adoption floors move to `>=0.8.3`; told the lead.
- The 0.8.4 re-run (2026-11-12): F142, F137, F130, F131, F127, F115, F113, F116 and F146's S143 half closed; F132, F135, F139 pass their patch halves. Still open, mine: F118 and F85's RM382 need a run over a real module (checked by symbol only).
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
