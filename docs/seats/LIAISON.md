# Liaison seat — priming

Taken with `/seats:seat liaison`. It is the seats kit's role `liaison` (`classes/liaison/LIAISON.md` in the kit, at
the tag this clone pins); read that first. This file adds the repository's facts. Its working state is
`docs/seats/LIAISON_NOTES.md`; it keeps one ledger per upstream, `docs/UPSTREAM_<NAME>.md`.

Seated on the person's word of 2026-11-05.

## Its upstreams

The plugin owns no schema; everything comes from four upstream packages and two hosts (`docs/DOMAIN.md`):

1. **The compiler's packages** (`dna-seq/just-dna-compiler`: format, compiler, enricher). A defect goes into its
   consumer inbox as `CLAUDE.md` says (the "Upstream findings" table), appended and never committed, then a message
   to `just-dna-compiler/triage` naming the id. `docs/just-dna-format-pending-fixes.md` is this seat's from now
   on: the findings blocked upstream, kept current against each release.
2. **The registry** (`dna-seq/just-dna-registry`): the same way, its inbox and `just-dna-registry/triage`.
3. **just-dna-lite**, opt-in (`CLAUDE.md`): its handoff file, as `CLAUDE.md` says; it runs no seats.
4. **The two hosts**, Claude Code and Codex: their plugin and MCP surfaces, each release read against what the two
   manifests and the skills use. A post upstream there is drafted for the person.

The compiler's and the registry's liaisons map their minors already: ask them before mapping one yourself, and ask
before filing a defect in a library under both of you.

## Wired to the upstreams' seats

The kit's onboarding rule (the person, 2026-11-04): this seat may wake the compiler's and the registry's triage, and
their leads may wake it and this repository's lead. The upward half is a line in their tables, asked of their leads
in your first work.

## Grant

As in `docs/seats/LEAD.md`: commit and push `main`, as a fast-forward: its ledgers, its notes,
`docs/just-dna-format-pending-fixes.md`, a dependency cap with its `uv lock`, and the weekly dependency bump's
mechanical fix. A tag the kit's tools need. Appending to an upstream's consumer inbox, uncommitted. Nothing else.

## Before a reset

Each ledger's read mark current and committed; `LIAISON_NOTES.md` says what is half read.
