# Lead — notes

The lead seat's working state, rewritten to the present before a reset (`docs/seats/LEAD.md`).

## Now

Released 0.48.5 (tag `v0.48.5`, `8cba3c9`, 2026-11-10): F126 (`0598c52`), F132 (`58ea0dc`, `cli_map` and
`on_this_surface`), the F140 recheck follow-up (`28cb212`), and the liaison's weekly bump, with pyright fixed forward
for pydantic 2.14 (`6d9f3d0`). 0.48.4's recheck by the tester: everything held except F133 (not exercised; Europe PMC
answered). Announced in `#just-module-creator>releases`. Next release no earlier than 2026-11-11. The person went
away at 05:02Z on 2026-11-05.

**0.8 adoption, branch `adopt-0.8`** (2026-11-10, the person: "pre-build the 0.8 branch, there's 0.8.3 already";
the polygon serves format/compiler 0.8.0, registry 0.28.5). Worktree `.claude/worktrees/adopt-0.8`, locked, own
`.venv`. Seven commits `30080cf`..`113150c`, pushed 2026-11-10 on the person's word: floors `>=0.8.3,<0.9`, registry `>=0.28.5`, polars/duckdb
kept `<2` by decision; reference examples from `v0.8.3`; 0.8's new commands/tables named as gaps (`cli_map`,
CLI.md, `refresh_sidecar`); GWAS v2 budget swept; `enrich_module.allele_mismatches` (RM382 drops the S85
`not_found` row); F133 via `fetch_fulltext`; F129 fallback out (reproduced on 0.8.3); gnomAD 0.7 label sentences
out. 918 pass, ruff/pyright clean; polygon `registry_health` contract_compatible, `registry_check` of a
`fto_bmi` copy `verdict: true`. Not done: adoption-map items 4-5 (SYMPTOMS matched by warning code), 6-7 (new
authored tables and passes, the pm's scope), 10 (`compilation.toolchain` beside a moved digest), item 3's cache
offer text, the RM420 `cache pull` (operator's), re-reading F139's `checks_older_than_the_last_edit` against
RM423. main stays 0.7 until production serves 0.8; then merge (not rebase) and release.
2026-11-11, unattended: items 4-5 done (`bbcabfb`: symptom entries titled by warning code, with a test against the live vocabulary; validate described as the compile's own pre-flight; the retired QUAL advice out). Item 9 (`7ff1fdc`): F113's Crossref read out (0.8 names the DOI's work and offers its PMID as an advisory); F108's BioC rung kept, since 0.8's `extract_bioc_text` flattens tables; F115, F118, F127, F105 have nothing to take out. F116: 0.8 ships a valid `.jsonl` from `logs/` (S125 is in 0.8.3), so whether our ledger leaves its `*.log` name is open, `unattended`, mine; it also moves the ground under desk #204 (RM31). Item 3: nothing to change (the split snapshot is 14.2 GB against the offer's 14 GB). Item 10 declined for the compare tools (neither reads `artifact.digest`); `registry_check` does return `artifact_digest`, so a toolchain note there is still an open question. `313f62e` was wrong on 0.7 and is undone (`f0368bb`); `6dce47a` passes `warnings_summary`/`carried` through `validate_module`.
Tester's probe at 113150c (2026-11-10): HTT/MTHFR strict and polygon `registry_check` true, allele_mismatches holds; F145 (false missing-lane sentence) fixed as `8ac4c82`. **The merge also waits on F146**: enricher 0.8.3 sends GWAS v2 `size=1000`, the API caps at 500 and answers 400, so `enrich_gwas_effects` fails on every module under 0.8. Upstream's to fix (liaison files it); no workaround here, and the branch's "page size 1000" budget wording follows their fix. F133's outage arm not exercised live (Europe PMC up).

**0.48.6 released 2026-11-11** (`27ed54f`, tag `v0.48.6`): F144, F146's our half, `validate_module`'s `warnings_summary`/`carried`. Upstream cuts no 0.7.4 (their maintainer), so the GWAS pass returns only with the 0.8 adoption on enricher 0.8.4, which carries RM428 (500 per page). `waits until` 0.8.4 is on PyPI: then adopt-0.8's floors move to `>=0.8.4` and its GWAS test is re-run against the live Catalog once.

**Merge hazard, adopt-0.8 ← main**: main's `_gwas_gone` (F146, `3664412`) reads a v1 410; its test overrides `FakeGwasClient.associations_for`, while the branch's fake serves `association_pages` (v2). After the merge that test no longer reaches the 410 path, and `[Unreleased]` conflicts. At the merge: decide whether a 410 can still arrive on v2 (keep `_gwas_gone` with a v2 fake) or drop it with its test.

**Registry S28 (namespace rename): reversed in registry 0.29.0** (2026-11-11; the polygon serves it). `registry_rename_namespace` is on adopt-0.8 (`6f5e7e3`, floor `>=0.29.0`, dry run by default). The real call's dry run `test-sheep` → `test-winternewt` was refused: `namespace_taken`. `test-winternewt` is empty and held by an account not saved here (the saved `sheep` owns only `test-sheep`). `blocked: desk #255`, updated with the new options (that account's owner frees it; another name; leave it). Default: leave it. Registry parity still open: `rename_account` (0.29 also moves a namespace spelled like the handle), `merge_accounts`, `create_org_namespace`.

F132's leftovers: the other result models carrying upstream `warnings` (fact passes, refresh, checks) lack
`on_this_surface`; four commands are named parity gaps in `cli_map` (`clinpgx check-labels`, `alphagenome check`,
`litvar gene`, `hint recover`). Upstream answered both as format S142 → RM427 (patch + minor), 2026-11-10. Weighed and declined for now: keying
`cli_map` by RM131's warning codes (`module_not_closed` …). The codes cover validate/compile only, still need our
command→tool map, and text matching already covers every channel under a both-directions test. Revisit when
RM427's minor ships a remedy key in what we install: then key by it and drop the text match.

Upstream halves, all the liaison's: S138/RM422 (F137's compile warning), S139/RM423 (F139's writer), S140/RM425
(F142's field description), S141 (F135's conflict message). When RM423 ships in what we install, our
`checks_older_than_the_last_edit` stays (it dates records; theirs drops them) unless their per-record binding makes
it redundant: re-read then. Not done on purpose: F140's split of never-asked from asked-and-empty (no record of the
queries exists); F141's cause (unknown).

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
- **Kit pin**: 0.1.174 (moved on each announcement; 0.1.174 on 2026-11-11) (`move-to-tag.py`; the pin is in the untracked
  `.claude/settings.local.json`). Taking it into this session is mine: `watchdog.sh reload`, then end the turn,
  and the kit's typer types `/reload-plugins` (the "left for the person" line `move-to-tag.py` prints is wrong, kit #306).

## Open

- **The tester and the liaison are seated (2026-11-07).** The tester is rechecking 0.48.0-0.48.2 (F31, F50,
  `remote_derive`/`remote_draft` live on the polygon). The liaison's 0.8 adoption map is in
  `docs/UPSTREAM_COMPILER.md` ("The 0.8 adoption map", `44a2880`); item 1 (the floors and the trio move) and item 2
  (the compile guide's reading of `not_found`) are this seat's, at the gate (prod serving 0.8); items 6-7 are
  the pm's. The liaison capped polars and duckdb `<2` in `pyproject.toml` (`c361614`).
- **F121** (seats resuming together lose the plugin server): kit #300 filed; repo-side repairs wait on it.
- **F128** (user-scope 0.47.0 skills; desk #229, the person's) remains open in `docs/dogfooding.md`. F126 and F132 shipped in 0.48.5; the 0.8-move list is done on adopt-0.8.
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
