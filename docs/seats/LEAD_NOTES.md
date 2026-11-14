# Lead — notes

The lead seat's working state, rewritten to the present before a reset (`docs/seats/LEAD.md`).

## Now

Released 0.48.5 (tag `v0.48.5`, `8cba3c9`, 2026-11-10): F126 (`0598c52`), F132 (`58ea0dc`, `cli_map` and
`on_this_surface`), the F140 recheck follow-up (`28cb212`), and the liaison's weekly bump, with pyright fixed forward
for pydantic 2.14 (`6d9f3d0`). 0.48.4's recheck by the tester: everything held except F133 (not exercised; Europe PMC
answered). Announced in `#just-module-creator>releases`. Next release no earlier than 2026-11-11. The person went
away at 05:02Z on 2026-11-05.

**0.8 adopted and released as 0.48.7 (2026-11-12, `ae11551`)**: production and the polygon both serve registry 0.30.0 on format 0.8.4, so `adopt-0.8` was merged (`d2032a4`, main's v1 GWAS-410 note dropped for 0.8.4's own `GwasRetired`) and main fast-forwarded. 923 pass; `registry_check` of fto_bmi on the polygon at those versions `verdict: true` (no production token is saved here, so production itself was not dry-run). The worktree is unlocked; the branch stays (a branch checked out in a worktree cannot be `-d`'d; removing the worktree is the person's). Still open from the adoption map: items 6-7 (the pm's), item 10's `registry_check` digest note, F116's ledger naming (`unattended`, mine), RM420's cache pull (operator's). **New, mine, `unattended`**: registry 0.30.0 parity: `derived()`'s `passes`, `offline`, `gene`, `chrom`/`start`/`end` for `remote_derive`, and `lane_tables`/`lane_rows` (a keyed lookup on any snapshot lane) as a tool; plus `rename_account`, `merge_accounts`, `create_org_namespace`. From the liaison's 0.8.4 re-run (c22a3a8), also mine, `unattended`: F105, wrap `gene_spans.genes_covering(chrom, position)` (RM259) so rows mode offers MANE genes within 512 kb as query hints for a row with no gene, where it now says `no_gene`; F139, decide whether `checks_older_than_the_last_edit` comes out now that RM423 drops stale records (read their binding first). F137's signal stays.

**Registry S28 (namespace rename): reversed in registry 0.29.0** (2026-11-11; the polygon serves it). `registry_rename_namespace` is on adopt-0.8 (`6f5e7e3`, floor `>=0.29.0`, dry run by default). The real call's dry run `test-sheep` → `test-winternewt` was refused: `namespace_taken`. `test-winternewt` is empty and held by an account not saved here (the saved `sheep` owns only `test-sheep`). `blocked: desk #255`, updated with the new options (that account's owner frees it; another name; leave it). Default: leave it. Account parity **done on main (`6ba23f6`, unreleased)**: `registry_rename_account` (dry run by default), `registry_create_org`, `registry_create_org_namespace`; an applied rename now moves the name on the saved account (the namespace rename left it stale). `merge_accounts` and `admin_rename_account` are site-admin only (the saved `sheep` has `site_admin: false`), so unwrapped; the reason handed to the liaison for F143's parity paragraph. Registry S31 filed (uncommitted in their tree): `whoami` lists only owned namespaces and no orgs. **New, mine, `unattended`, after the 0.31 reads: the registry parity sweep.** About 30 client methods have no tool and no written abstention: `add_member`, `remove_member`, `members`, `add_org_member`, `remove_org_member`, `set_org_role`, `org_members`, `update_org_settings`, `update_profile`, `set_short_description`, `amend_changelog`, `amend_logo`, `review`, `reviews`, `delete_review`, `highlight_review`, `star`, `unstar`, `versions`, `lookup_by_digest`, `get_tarball`, `pubkey`, `import_module`, `issue_jwt_token`, `catalog_stats`, `cache_status`, `logs`, `runs`, `run_log`. Each ends as a tool or as an abstention on CLAUDE.md §5's grounds (operator, build hook, deployment-only). **Registry 0.31.0 parity: done on main (`319765c`, unreleased, 2026-11-14)**: `registry_claims` (one tool, `variant` or `gene`) and `registry_search(pgs_id=)`, floors at just-dna 0.8.6 / registry 0.31.0. Tried live on production (0.31.0, back up overnight): rs429358 five modules, nothing comparable (`no_trait 15`); MTHFR 385 claims, cut at `limit`. The polygon still serves 0.30.0, where both are refused by name (it 404s the routes and ignores `pgs_id`). Registry S32 filed and answered the same hour (their `f4eca0b`): the alias lookup is exact (`RS429358`, `chr19:…` answer empty); a patch folding case/`chr`/`-` and a minor saying whether the key matched are on their roadmap, undecided. The spelling fix is server-side: it counts when an instance we read serves it (`/api/v1/version`), not when our lock moves; then reword the S32 sentences in `claims_message`, the tool's docstring and `module-curate` (they name 0.31.0). Only the `gene_claims` quoting is client-side.

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

## Acting: the pm's milestones duty (from kit v0.1.187, 2026-11-12)

The pm seat is free, so the lead holds it (`classes/pm/PM.md`, `## Duty: milestones`) and hands it back when a pm is seated. `state`: one post kept in place, source `docs/seats/LEAD_STATE.md`, refreshed with `watchdog.sh keep lead state '#just-module-creator>state' docs/seats/LEAD_STATE.md` whenever where-it-stands, a headline result or the next actions change. `milestones`: one post per landed result. Links point at `dna-seq/just-module-creator` (the remote), not the person's own account; the first 0.48.7 post had that wrong and was deleted and reposted.

## Practice

- **A commit queued behind a long suite takes its named files as they stand when it runs** (2026-11-13: `d9651d1`, F148, swept in the F149 fix and a half-finished test, and pushed a failing test until `26009a1`). While such a run is pending, edit none of the files it names; start the next fix after it lands.

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
- **Kit pin**: 0.1.205 (moved on each announcement; 0.1.205 on 2026-11-14) (`move-to-tag.py`; the pin is in the untracked
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
