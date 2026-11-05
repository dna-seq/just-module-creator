# Seats: standing roles a session can take in this repo

A **seat** is a fixed role a Claude Code session takes for its whole run. The seats here run on the seats kit
(`agent-seat-blueprints`): its plugin is pinned in the clone, and its base, loaded at every session start, holds
what every seat knows: messages, the desk, unattended runs, who speaks. Every seat also loads `CLAUDE.md`.

| Seat | Priming | Notes | Reached by | What it does |
|---|---|---|---|---|
| **lead** | [LEAD.md](LEAD.md), on the kit's `lead` role | [LEAD_NOTES.md](LEAD_NOTES.md) | the person; the tester's findings; an issue on the repository; the liaison; the pm | Builds the plugin (tools, skills, both hosts' manifests), fixes what the tester finds, answers the repository's issues, prepares releases. |
| **pm** | [PM.md](PM.md), on the kit's `pm` role | [PM_NOTES.md](PM_NOTES.md) | the person; a direction call from a seat | Who the plugin serves, what each minor holds, the manuscript's direction, the research list. Writes no code. |
| **tester** | [TESTER.md](TESTER.md), this repository's own | [../UX_TESTER.md](../UX_TESTER.md) | a release; the lead asking for a probe | The beta tester: uses the shipped plugin for real module work and records what is missing, as `F#` findings in `docs/dogfooding.md`. Fixes nothing. |
| **liaison** | [LIAISON.md](LIAISON.md), on the kit's `liaison` role | [LIAISON_NOTES.md](LIAISON_NOTES.md) | an upstream's release; a symptom from a seat | Tracks the compiler's packages, the registry and the two host clients; files their defects where each producer takes them; keeps `docs/just-dna-format-pending-fixes.md`. |

The tester's split from the lead is this repository's oldest rule (`docs/UX_TESTER.md`, 2026-08-11: "The second agent
will fix it, you stay in tester role"): the seat that experiences the product never patches it.

No tooling seat: a fault in the kit's tools is filed on the kit's issues (the skill `report-to-kit`), and the lead
moves the kit's pin. The team file is on the person's desk, since this repository is public.
