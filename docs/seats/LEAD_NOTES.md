# Lead — notes

The lead seat's working state, rewritten to the present before a reset (`docs/seats/LEAD.md`).

## Now

Released 0.48.2 (tag `v0.48.2`, `b2f4622`, 2026-11-06): F31, F50, F119, and the suite's reference examples
copied into `assets/reference_examples/` from just-dna-format `v0.7.3` (`496f658`; the sibling checkout's move
to 0.8 had failed five tests the morning of the release). Announced in `#just-module-creator>releases` for the
tester's probe; daily line posted 2026-11-06. Nothing unreleased on `main`. The person went away at 05:02Z on
2026-11-05.

## Plan states (set 2026-11-05)

- RM16, RM25: waits until 2026-12-05. RM24: waits until 2027-01-05. Each line says what is looked at then.
- RM28: blocked on desk #203, yes after a present (the trait-term search tool; a minor).
- RM31: blocked on desk #204, no default (format's S125 was accepted for their 0.8, so the design's ground moved).
- RM18: blocked on desk #205 (whether this seat drafts the handout for Anton); owner the person.
- The "Owed to just-dna-lite" section had been done on 2026-09-26; moved to `ROADMAP_HISTORY.md`.
- No plan watcher runs for this seat (`classes/lead/plan-watch.py`); asking the seat-builder is on the to-file list.

## Findings (the tester's inbox)

- Fixed and released in 0.48.2: F31, F50 (`5dfb942`, `7a8463e`); F119 (`84aa78f`: no test reaches a live
  `httpx` transport). The tester's probe of F31/F50 asked in `#just-module-creator>releases`.
- F34 (each publish uploads the previous `published.json`): the upload is the registry client's
  `gather_spec_files`, filed upstream long ago as registry `S5`; nothing here to fix.
- F22 (`published.json` records `owner: null`): needs a call on what "owner" means (namespace owner or the
  account that published) and whether a `whoami` per publish is worth a request on a rate-limited polygon.
  Next: the account name in the saved account is a no-request answer for a saved token; a session token has none.

## To file (unattended)

- Plan watcher: added on the seat-builder's word (`[seat.lead.watch.plan]`), running.
- Pyright: clean since the codex-install test narrows its pipes (was 4 errors before this seat).

## First seating, 2026-11-05

- **The repository's own machinery against the kit's.** Retired: the hand-run NIGHT-RELAY protocol in
  `CLAUDE.md` §9 (the card rack, watchdog and unattended mode do it). Kept: `scripts/bench_score.py` and
  `scripts/page_budget.py` (this repository's own operational one-offs, nothing the kit does), and the
  tracked `.claude/settings.json` (it only pins the plugin, with no hooks or wakers). Git hooks were the
  samples only.
- **Watchers**: `watch.desk`, `watch.issues`, `watch.brief` started.
- **Picture**: a platypus with a DNA strand, set 2026-11-05 from the admin seat's reply.
- **`CLAUDE.md`**: read-first list names `docs/seats/README.md`; §7 says the tester finds and the lead fixes,
  and that the liaison keeps `docs/just-dna-format-pending-fixes.md`.
- **Leak gate**: `.leak_words` written (home and scratch paths, host forms of the hostname, the chat server,
  the person's joined name), `bin/leak-gate.sh install` on, tested on a sample line.
- **Open issues**: none on the repository.
- **Trust register (`docs/TRUST.md`)**: the person declined, 2026-11-05: "no, not now". Not asked again
  unless something changes what the plugin can reach.
- **Downward wake**: asked `longevity-loci/lead` in `#agent-chat>wake_from` to add `just-module-creator/lead`
  to its lead's and liaison's `wake_from`; done there in their cdd95d3.
- **Kit pin**: 0.1.138 (moved on each announcement, 2026-11-05) (`move-to-tag.py`; the pin is in the untracked
  `.claude/settings.local.json`). The person's `/reload-plugins` takes it into this session.

## Open

- Desk #203 (RM28), #204 (RM31), #205 (RM18): waiting on the person.
- The tester's probe of 0.48.1's token refusal on the polygon, asked in `#just-module-creator>releases`.
- The person's `/reload-plugins` here takes the kit's 0.1.138 hooks (the watchdog already runs 0.1.138).

## Downstream

- longevity-loci (its liaison, 2026-11-05) stands on the plugin at 0.48.0, and its first longevitymap v2 module
  waits on our `<0.8` format cap until the registry serves 0.8. That belongs to the pm's 0.8 scope call.
- **just-dna 0.8.0 is cut and on PyPI (format, compiler, enricher; checked 2026-11-05); both registry
  instances still serve format 0.7.1 / compiler 0.7.2 (registry 0.27.0), so the deploy is what remains.** Our `<0.8` ceiling holds
  until it is published and both instances' `/api/v1/version` serve it (the recipe in `pyproject.toml`); the
  scope is the pm's. 0.8 moves the trio to polars 2 and, once their RM344 lands, duckdb 2. Until we adopt it,
  no `uv lock --upgrade` here: a duckdb 2.0-built `ensembl_variations.duckdb` in the shared cache crashes a
  1.x enricher (their RM344), and a polars change alone moves `artifact.digest`. longevity-loci capped both
  `<2` until this plugin moves. At that move, copy `assets/reference_examples/` again from the adopted tag
  (its README). longevity-loci asked for a word when we plan it: post it in `#agent-chat>upstream`.
