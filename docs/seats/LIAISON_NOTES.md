# Liaison — notes

The liaison seat's working state, rewritten to the present before a reset (`docs/seats/LIAISON.md`).

## Now

First seating 2026-11-07 (the seat-builder's handout and first work). Commits: `c361614` (polars, duckdb `<2` in
the lock), `09404dc` (watchers), `44a2880` (three ledgers, F85, the pending-fixes table against 0.8.0). Pushed:
not yet; `09404dc` is the seat table, which the grant does not name, so the push waits on the person's word.

## Watchers

`compiler` (tags of `dna-seq/just-dna-compiler`, from the registry liaison's state-file line `just-dna-compiler`,
reused), `registry` (this seat's line `just-dna-registry`, the registry's own clone, fetch only), `nightly` (the
weekly dependency bump), `desk`, `brief`. All started 2026-11-07. The hosts have none: read `claude --version` and
`codex --version` at each start against `docs/UPSTREAM_HOSTS.md`.

## Half read

- `docs/UPSTREAM_COMPILER.md` backlog: the fourteen pending-fixes entries whose fix is *in our lock*, each closes
  once its reproduction passes on the installed package. One at a time, unattended.
- `docs/UPSTREAM_REGISTRY.md` backlog: 0.27.1 to 0.28.2 entry by entry (only client-surface lines read).
- The polygon's `/api/v1/version` did not answer on 2026-11-07; read it again.

## Waiting on others

- `just-dna-compiler/lead`, `just-dna-registry/lead`: `just-module-creator/liaison` in their triage's
  `wake_from` (asked in `#agent-chat>wake_from`, 2026-11-07).
- The lead and the pm: the 0.8 adoption map (told in `#just-module-creator>0.8`). The caps come out with the
  adoption, not before.

## Picture

A capybara with a satchel of letters, set 2026-11-07 from the admin seat's reply.

## Handout, item 1 (tools against the kit's)

Nothing to retire or move: the repository had no liaison machinery before the kit. Upstream filing was by hand
per CLAUDE.md §8 (the triage-state scripts it names are the upstreams' own); kept as written.

## To file (unattended)

Nothing yet.
