# Lead — notes

The lead seat's working state, rewritten to the present before a reset (`docs/seats/LEAD.md`).

## Now

Released 0.48.3 (tag `v0.48.3`, `e1c9614`, 2026-11-08): F120, F122 (DOI joined to PMID/PMCID through PubMed),
F123 (no-token refusal leads with `registry_accounts add`), F124 (`check_pgx` names only legs that compared,
read from upstream's record), F125 (stub-row repair keyed on wording both compiler versions share; test fed the
compiler's real refusal), F129 (STRchive drafter reads the lane or a `catalogue`; a mitigation, out at the 0.8
move), the gene-metrics guide's gnomAD label (RM417). Also: reference examples' `logs/authoring.log` now travel
(`4b358df`). Next release no earlier than 2026-11-09. The person went away at 05:02Z on 2026-11-05.

Unreleased on main, each test run against 0.48.3's code and failing there: F134 (`62fffd5`), F133 (`7c188be`),
F142 (`d71d81e`, expression size vs direction), F136 (`d8d693c`, PubMind withheld collapsed), F135 (`a924b2d`,
check_identifiers' `next_step` when the gene/chromosome comparison skips), F138 (`4860572`, audit reads a stale
attestation as not computed; diplotypes; refresh says "you removed it"), F137 our half (`83d5f85`, signal
`sidecar_rows_nothing_authors`), F139 our half (`22a3856`, signal `checks_older_than_the_last_edit`). 904 tests.
Upstream halves: S138/RM422 (F137), S139/RM423 (F139), S140/RM425 (F142), S141 (F135's message), all the liaison's.
Still open, mine, `unattended`: F140 (medium: `top_expression_effects`' `gene_not_at_locus` reads what the sidecar
holds as a fact about the model; `rows=true` asks only a row's own gene), F141 (low: the dry run's per-window time is
a constant). Release 0.48.4 allowed from 2026-11-09.

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
- **Kit pin**: 0.1.147 (moved on each announcement; 0.1.147 on 2026-11-09) (`move-to-tag.py`; the pin is in the untracked
  `.claude/settings.local.json`). Taking it into this session is mine: `watchdog.sh reload`, then end the turn,
  and the kit's typer types `/reload-plugins` (the "left for the person" line `move-to-tag.py` prints is wrong, kit #306).

## Open

- **The tester and the liaison are seated (2026-11-07).** The tester is rechecking 0.48.0-0.48.2 (F31, F50,
  `remote_derive`/`remote_draft` live on the polygon). The liaison's 0.8 adoption map is in
  `docs/UPSTREAM_COMPILER.md` ("The 0.8 adoption map", `44a2880`); item 1 (the floors and the trio move) and item 2
  (the compile guide's reading of `not_found`) are this seat's, at the gate (prod serving 0.8); items 6-7 are
  the pm's. The liaison capped polars and duckdb `<2` in `pyproject.toml` (`c361614`).
- **F121** (seats resuming together lose the plugin server): kit #300 filed; repo-side repairs wait on it.
- **F132** (upstream text naming a CLI command reaches the agent unmapped; F125's second instance, split out
  2026-11-08): `unattended`, mine. Shape in `docs/dogfooding.md`: one CLI-to-tool map in `src/`, guarded both ways
  against upstream's typer commands, carried as our own field beside the verbatim message. Asked the liaison
  whether upstream would give a structured remedy key instead.
- **At the 0.8 move** (adoption map): drop `draft_from_strchive`'s `resolve_strchive_reference()` fallback (keep
  the `catalogue` argument); drop the gene-metrics guide's 0.7 label sentences (`gnomad_v2.1.1_constraint`);
  floors `>=0.8.2` for all three (liaison, 2026-11-08); recopy `assets/reference_examples/`; replace F133's
  "call again" sentence in `discovery.fulltext` with 0.8's `fetch_fulltext`, which names an outage as one.
- **F126** (`registry_register`'s docstring on install-id reuse) and **F128** (user-scope 0.47.0 skills; desk
  #229, the person's) remain open in `docs/dogfooding.md`; F126 is `unattended`, mine.
- **The liaison's re-run of pending-fixes (`f032ecb`) leaves five lifts of our own code**, none urgent, each
  unattended: F94 (`provisioning._LANE_KB`/`_DECLARED_KB` against every lane's `approx_mb`), F93
  (`proxy._TABLE_KEY_FOR`/`_dest_for` and their probe test), F63 (our in-process enrichment claim beside
  upstream's `spec_lock`), F67 (`compiler.load_spec` in place of `yaml.safe_load` in `compare.py`/`audit.py`,
  and perhaps the pyyaml dependency). F59 (`set_short_description` unwrapped) is a gap whose scope is the pm's.
- Desk #203 (RM28), #204 (RM31), #205 (RM18): waiting on the person.
- The tester's probe of 0.48.1's token refusal on the polygon, asked in `#just-module-creator>releases`.

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
