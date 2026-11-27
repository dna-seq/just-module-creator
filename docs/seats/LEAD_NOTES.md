# Lead — notes

The lead seat's working state, rewritten to the present before a reset (`docs/seats/LEAD.md`).

## Now

Released 0.48.22 (tag `v0.48.22`, `8b2f724`, 2026-11-27): `registry_rotate_key` (b862f69), registry client floor >=0.34.1 (0.34.3 locked by the liaison, f547e16). 1115 pass; polygon `registry_check` of fto_bmi `verdict: true`. Tester's recheck on a throwaway polygon account pending (kit #676's rule is in v0.1.287). Next release no earlier than 2026-11-28, nothing queued. Before it: 0.48.21 (`666518d`, 2026-11-26, just-dna 0.8.10), 0.48.20 (`18407b6`, 2026-11-24, F172), 0.48.19 (`c58fc0a`, 2026-11-23, fastmcp 4.2.5).

Registry 0.32 adopted and the enricher floored at 0.8.8: released in 0.48.14. The RM445 cache re-pull ran on this machine 2026-11-17.
away at 05:02Z on 2026-11-05.

**0.8 adopted and released as 0.48.7 (2026-11-12, `ae11551`)**: production and the polygon both serve registry 0.30.0 on format 0.8.4, so `adopt-0.8` was merged (`d2032a4`, main's v1 GWAS-410 note dropped for 0.8.4's own `GwasRetired`) and main fast-forwarded. 923 pass; `registry_check` of fto_bmi on the polygon at those versions `verdict: true` (no production token is saved here, so production itself was not dry-run). The worktree is unlocked; the branch stays (a branch checked out in a worktree cannot be `-d`'d; removing the worktree is the person's). Still open from the adoption map: items 6-7 (the pm's), item 10's digest note (done 2026-11-15, `01800ab`: the `toolchain` lines), F116's ledger naming (F116 closed upstream; the ledger is RM31, `blocked: desk #204`), RM420's cache pull (operator's). **New, mine, `unattended`**: registry 0.30.0 parity: `derived()`'s `passes`, `offline`, `gene`, `chrom`/`start`/`end` for `remote_derive`, and `lane_tables`/`lane_rows` (a keyed lookup on any snapshot lane) as a tool; plus `rename_account`, `merge_accounts`, `create_org_namespace`. From the liaison's 0.8.4 re-run (c22a3a8), also mine, `unattended`: F105, wrap `gene_spans.genes_covering(chrom, position)` (RM259) so rows mode offers MANE genes within 512 kb as query hints for a row with no gene, where it now says `no_gene`; F139, decide whether `checks_older_than_the_last_edit` comes out now that RM423 drops stale records (read their binding first). F137's signal stays.

**Registry S28 (namespace rename): reversed in registry 0.29.0** (2026-11-11; the polygon serves it). `registry_rename_namespace` is on adopt-0.8 (`6f5e7e3`, floor `>=0.29.0`, dry run by default). The real call's dry run `test-sheep` → `test-winternewt` was refused: `namespace_taken`. `test-winternewt` is empty and held by an account not saved here (the saved `sheep` owns only `test-sheep`). `blocked: desk #255`, updated with the new options (that account's owner frees it; another name; leave it). Default: leave it. Account parity **released in 0.48.10 (`6ba23f6`)**: `registry_rename_account` (dry run by default), `registry_create_org`, `registry_create_org_namespace`; an applied rename now moves the name on the saved account (the namespace rename left it stale). `merge_accounts` and `admin_rename_account` are site-admin only (the saved `sheep` has `site_admin: false`), so unwrapped; the reason handed to the liaison for F143's parity paragraph. Registry S31 filed (uncommitted in their tree): `whoami` lists only owned namespaces and no orgs. **New, mine, `unattended`, after the 0.31 reads: the registry parity sweep.** About 30 client methods have no tool and no written abstention: `add_member`, `remove_member`, `members`, `add_org_member`, `remove_org_member`, `set_org_role`, `org_members`, `update_org_settings`, `update_profile`, `set_short_description`, `amend_changelog`, `amend_logo`, `review`, `reviews`, `delete_review`, `highlight_review`, `star`, `unstar`, `versions`, `lookup_by_digest`, `get_tarball`, `pubkey`, `import_module`, `issue_jwt_token`, `catalog_stats`, `cache_status`, `logs`, `runs`, `run_log`. Each ends as a tool or as an abstention on CLAUDE.md §5's grounds (operator, build hook, deployment-only). **Registry 0.31.0 parity: released in 0.48.10 (`6179692`, tag `v0.48.10`, 2026-11-14; wording fixed in `1ce0d5b`)**: `registry_claims` (one tool, `variant` or `gene`) and `registry_search(pgs_id=)`, floors at just-dna 0.8.6 / registry 0.31.0. Tried live on production (0.31.0, back up overnight): rs429358 five modules, nothing comparable (`no_trait 15`); MTHFR 385 claims, cut at `limit`. The polygon still serves 0.30.0, where both are refused by name (it 404s the routes and ignores `pgs_id`). Registry S32 filed and answered the same hour (their `f4eca0b`): the alias lookup is exact (`RS429358`, `chr19:…` answer empty); a patch folding case/`chr`/`-` and a minor saying whether the key matched are on their roadmap, undecided. The spelling fix is server-side: it counts when an instance we read serves it (`/api/v1/version`), not when our lock moves; then reword the S32 sentences in `claims_message`, the tool's docstring and `module-curate` (they name 0.31.0). Only the `gene_claims` quoting is client-side.

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

## The registry parity sweep: what each unwrapped client call becomes (2026-11-14)

Measured against the installed client (just-dna-registry 0.31.0): 36 public methods no code here references.
Reads probed on both instances the same day. Built in this order, serially, each with its tests, skill row and
changelog line; the abstentions go to the liaison for `docs/just-dna-format-pending-fixes.md`.

| Client calls | Becomes | Why |
|---|---|---|
| `members`, `add_member`, `remove_member`, `org_members`, `add_org_member`, `remove_org_member`, `set_org_role` | tool `registry_members` (gated; list/add/remove/role, a namespace or an org) | 0.48.10 ships `registry_create_org` and nothing adds anyone to it. `members` needs a bearer token on both instances (401 measured), so the read is gated too. |
| `update_profile`, `update_org_settings` | tool `registry_profile` (gated) | The author's or an owned org's display name, funding URL, avatar, email. Email only as an argument the author gives, never from the session. |
| `amend_changelog`, `amend_logo`, `set_short_description` | tools beside `registry_amend_readme` | Metadata an author amends without a version bump; `set_short_description` is F59's open half. |
| `star`, `unstar` | tool `registry_star` (gated) | User-facing; no §5 ground. |
| `reviews`, `review`, `delete_review`, `highlight_review` | tools `registry_reviews` (read, anonymous) and `registry_review` (gated) | Reviews and the owner's highlight are the trust signal (§10: trust is read off the module). |
| `catalog_stats` | tool `registry_stats` (read) | Per-namespace totals; `registry_health`'s `catalog` block is the instance-wide one only. |
| `hint_old_assembly` | tool `lookup_old_assembly`, local via `just_dna_enricher.grch37.recover_rsid` | Nothing here takes an hg19 coordinate; `cli_map` already names `hint recover` as a gap. The registry hint is the same recovery proxied; no snapshot lane is involved, so there is no miss to route. |
| `hint_citation`, `hint_gene`, `hint_trait` | abstain: covered | `lookup_citation` and `lookup_identifier` ask the same sources directly. No snapshot lane stands behind them, so routing through the registry would add a third party and spend its budget with no miss to justify it. |
| `logs`, `get_tarball` | abstain: covered | `registry_download` calls `download(include_logs=True)`, which fetches the logs; a tarball is the same version in another container. |
| `versions` | abstain: covered while measured | `get_module` returned every version for every module on both instances (longest history 6). Trigger: a module past 20 versions, the client's page size; then wrap. |
| `lookup_by_digest`, `lookup_by_digests`, `lookup_by_signatures` | abstain | `registry_is_published` asks by `content_signature`, the identity that survives a compiler change; a digest moves with the build. The batch forms classify a corpus: an operator's sweep. |
| `pubkey` | abstain until an instance signs | Both instances answer `None` (measured). Trigger: one signs; then pin it in `registry_download`. |
| `import_module` | abstain | A spec archive is unpacked and published through `registry_publish`; the legacy parquet-only form has no spec for any check here to read before a permanent publish. |
| `admin_rename_account`, `merge_accounts`, `runs`, `run_log` | abstain: operator | Site admins only. |
| `assert_compatible`, `issue_jwt_token` | abstain: transport | The client calls the first itself on every connection; the second is a web session's exchange, and a static token serves every call. |

**Built, all on main and unreleased (2026-11-14), each tried live:** `registry_members` (a9fae2b),
`registry_profile` (3b12409), `registry_amend_version` and `registry_set_subtitle` (0395250, F59 closed and
told to the liaison), `registry_reviews`, `registry_review`, `registry_star` (5c2b2f2), `registry_stats`
(93d209f), `lookup_old_assembly` (c3d7785, also closing `cli_map`'s `hint recover` gap). The abstentions are
the liaison's f37c6d5. Full suite 996 passed with the Codex reinstall test deselected: earlier the same day
it timed out after 300 s on `codex plugin add`; run alone afterwards it passed in 95 s, so transient, cause
not established. Release as 0.48.11 on or after
2026-11-15. **Done the same evening:** the enricher's `diagnose_wrong_build` already runs inside `enrich` over the
ref-mismatched rows; `enrich_module` dropped its result. It now reports `build_diagnoses` and
`build_not_diagnosed` and hands `enrich` the server's GRCh37 client. Tested on a fake result built from
upstream's own `BuildDiagnosis`; not run live (a GRCh38 module with hg19 rows was not at hand).
**Fixed forward after review (same day):** a highlight is signed by the account saved for the module's
namespace (it was the default account); `lookup_old_assembly` names upstream's `unchecked`, not an invented
`unreachable`, and its client is built in `net.build_services` behind a `ServiceGate`; `registry_members` takes
its roles from `just_dna_registry.permissions` and refuses to re-role a non-member (upstream's re-role is
`add_member`, which would add them); `routing.PROXY_METHODS` no longer says this layer calls all nine.
**Also new, mine, `unattended`:** `lookup_citation` does not pass `pmcid` to upstream's `lookup_citation`, which
takes it; so `hint_citation`'s PMCID form is a gap, not covered, and the liaison's abstention reason narrows to
PMID and DOI. Wiring it needs the `withheld` logic re-read for a third identifier.
**Done the same evening:** `lookup_citation(pmcid=)` passes it through; upstream's advisory needed no logic of ours. Tried live: `PMC3498066` alone offers PMID 23128226 in `withheld`; beside the wrong PMID it warns the pair names different articles.

## Acting: the pm's milestones duty (from kit v0.1.187, 2026-11-12)

The pm seat is free, so the lead holds it (`classes/pm/PM.md`, `## Duty: milestones`) and hands it back when a pm is seated. `state`: one post kept in place, source `docs/seats/LEAD_STATE.md`, refreshed with `watchdog.sh keep lead state '#just-module-creator>state' docs/seats/LEAD_STATE.md` whenever where-it-stands, a headline result or the next actions change. `milestones`: one post per landed result. Links point at `dna-seq/just-module-creator` (the remote), not the person's own account; the first 0.48.7 post had that wrong and was deleted and reposted.

## Practice

- **A commit queued behind a long suite takes its named files as they stand when it runs** (2026-11-13: `d9651d1`, F148, swept in the F149 fix and a half-finished test, and pushed a failing test until `26009a1`). While such a run is pending, edit none of the files it names; start the next fix after it lands.
- **A change in the shared tree that I did not make is another seat's until shown otherwise** (2026-11-17: the release bump's `uv lock` showed 14 upgraded packages that were the liaison's uncommitted weekly bump, and I ran `git checkout -- uv.lock` on it; the liaison redid it as `af1f0c6`, nothing lost). Before restoring or overwriting a file, run `git status --short` and ask whether I touched it; if not, ask its seat first.

## Plan states (set 2026-11-05)

- RM16, RM25: waits until 2026-12-05. RM24: waits until 2027-01-05. Each line says what is looked at then.
- RM28: shipped in 0.48.13 (2026-11-17); moved to `ROADMAP_HISTORY.md`.
- RM31: shipped in 0.48.14 (2026-11-18), moved to `ROADMAP_HISTORY.md`. Open as new items when taken up: an author's decisions from the question tool (decision 4), a live Codex run. The worktree `../just-module-creator-rm31` is unlocked and holds branch `rm31-build`; removing it is the person's, after which `git branch -d rm31-build`. Branch pushes are not in this seat's grant: two made (`rm31-trial`, `rm31-build`), named to the person.
- RM18: moved to `ROADMAP_HISTORY.md` 2026-11-16; the handout is `docs/HANDOUT-antonkulaga-modules.md`, sending it is the person's.
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
- **Kit pin**: 0.1.287 (moved on each announcement; 0.1.287 on 2026-11-27) (`move-to-tag.py`; the pin is in the untracked
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
- **RM32 (an author's answers reach the ledger), `unattended`.** On main, unreleased: slice 1 and the report half of
  slice 2 (`7f70195`: answered `AskUserQuestion` counted with no text, set beside `basis="author"` decisions) and
  slice 3 (`ab441e8`: `record_decision(basis="author")` elicits approval; declined is not recorded, no elicitation
  support is `approved: null`). Tested in memory against the recorded result shape and fastmcp's own elicitation;
  no live run on either host. Left: a live run (needs a person at a session) and Codex's `request_user_input`
  once its hook payload is measured. Tester probed it (interactive Claude Code holds; F166 under `claude -p`).
  Fixed: `756ee80` (only an undeclared host reads null; by='author' bypass refused), `7d2fad5` (F166: `cancel`,
  measured as print mode's answer, is no answer seen, kept null; only `decline` drops it). Tester confirmed on 069e6a9 (046dd56).
- **Registry 0.33 parity, mine, `unattended`** (the liaison, 2026-11-18, `87c49fa`): `lane_tables`/`lane_rows`
  answers now carry `release`, `release_unreadable` and `revision` (the hub commit a remote read used), and
  `registry_lane_lookup`'s model drops them. Neither instance serves 0.33 yet (both 0.32.1). **Done** 2026-11-19:
  passed through as stated, null from an older registry; test values real (CIViC's label, its hub head).
- **Desk #255, the person answered 2026-11-18: the `winternewt` account is theirs** (relayed to the desk). Waiting on
  them to hand over its test-registry token; then dry runs (move the empty `test-winternewt` aside, rename
  `test-sheep` into it), shown before anything real. Fallback: a site admin's `merge_accounts sheep -> winternewt`.
- **The writer seat (seated 2026-11-18, 39aa78f) asked for six changes.** Done: its README row and
  `page_budget.py`'s docstring (`5f9900d`). On the desk as `blocked: desk #366` (CLAUDE.md or config, not changed on a
  seat's request): `wake_from` gains the writer, CLAUDE.md's manuscript section and reading list, §11's typesetter line
  (`~/.local/bin/tectonic` 0.17.0 runs; `tectonic-musl` is gone), `manuscript-skills@dna-seq` in tracked settings.
  Default: nothing changes.
- **Released 0.48.15 (2026-11-19, `55a42b6`, tag `v0.48.15`):** F164, F165, RM32 slices 1 and 3, F166, F93/F94
  removed, F67/F63 kept. 1098 pass; polygon `registry_check` of fto_bmi `verdict: true`. Next release no earlier than
  2026-11-20.
- **Benchmark round 4, the person's ask 2026-11-19** ("rerun eval on current plugin version and send an update to
  writer seat"; then new papers). Table 3's runs archived first (`f778e2d`, the person's "Aa" via the writer). Round 4:
  three sirt6 runs in sequence, plugin 0.48.15, model held at `claude-opus-5` (Table 3's), `claude -p --permission-mode
  auto` from the repo, briefs = `prompt.txt` + the isolation block naming "read or list", run dirs
  `data/interim/repro-bench-4/run-sirt6-{a,b,c}`. Then: leak check from the transcripts, score, census, send the writer.
  The person, on the result: "same model for reproducibility/tracking of drift. If results are same -> +1 run on
  opus-5.5 for stability testing" (`claude-opus-5-5`, same brief, run dir `run-sirt6-d`). Runner duty: "ok, tester";
  forwarded to the seat-builder for the tester's priming (tester's brief f2a4483). Round 4's evaluation handed to
  the tester too (the person: "with you or tester? The bench run"); the lead only keeps the background job running
  and tells the tester when it ends. Ended 2026-11-19 00:37Z, all three exit 0 on claude-opus-5; told the tester.
- **Desk #366's CLAUDE.md hunks reverted (`8304ac2`) on the person's word** ("revernt on 3n decision, adjust sections,
  show me the suggested changes"); wake_from and the plugin setting kept. Proposed A (reading list), B (manuscript
  section), C (§11 tectonic) shown; the person picked B and C (`2d820e8`). What they meant by "3n decision" was the
  paper: adjust the abstract and sections to the talk's eligibility criteria, and a raw link to the built PDF for
  Anton; forwarded to the writer (the paper is its).
- **Registry 0.34.1 `rotate_key`: `registry_rotate_key` released in 0.48.22 (2026-11-27); the tester rechecks it at the tag on a throwaway polygon account.** (was: waits until an instance serves 0.34) (the liaison, e633db2): wrap it as a
  gated tool; the new key is shown once and must replace the saved token in `state.json` through the backed-up
  write, read back, or the next call meets a dead key. Needs the floor at 0.34.1; both instances serve 0.32.1, so
  the tool must refuse by name on an older server. `deploy`/`deploy_status` are site-admin only (abstained).
- **F168 fixed (`8941717`), F169 mitigated (`e8d8461`)** from round 4. F169's isolation is open: find why
  `--plugin-dir <worktree>` starts no plugin server. The probe worktree `.worktrees/bench-v0.48.15` is unlocked.
- **Round 4 reruns asked of the tester (2026-11-19):** c (claude-opus-5) and d (claude-opus-5-5) read the F168
  leak, so the person's "+1 run on opus-5.5" is not met clean; rerun both on main with step 1's check. Not a desk
  question: the person's ask decides it, and quota is no drawback (kit #510).
  Done (tester 1513e9c): clean a, b, e on claude-opus-5 pair recall 1.00/1.00/0.67, f on Opus 5.5 0.67, all
  thresholds met; hold lifted. The fixture's shape left module-curate too (`f400344`).
- **just-dna 0.9: built on `adopt-0.9` (`.worktrees/adopt-0.9`, d38c5f9 + merge of main), 1113 pass; merges to main when both instances serve format 0.9 (both 0.8.10 at 2026-11-26), the person having said 0.9 is published.** Earlier prep, kept for its reasons: **just-dna 0.9 prep, mine, `unattended`, after the round's hold lifts** (the liaison's trial of d9c578ae, e46f560,
  `docs/UPSTREAM_COMPILER.md`): 3 of our tests fail, all ours. `cli_map._PUBLISH` needs `clinvar-gkm publish` and
  `opentargets publish`; `test_every_tool_a_mapping_names_exists` reads the new `ensembl_rsid_index` lane name as a
  tool (exclude lane names); the layered-header budget is 2 characters over with 0.8.10/0.9.0 in the version line.
  Also a stale lane (new state) plans a pull or build without saying why; `LaneStatus.stale` carries the reason.
  Wrong of me to say each could land on 0.8: `test_cli_map` also fails on a command the installed version does not
  register, so the two `_PUBLISH` entries, the header budget and `LaneStatus.stale` wait for the adoption, as the
  liaison wrote. Done now: the lane-name exclusion reads `routing.CACHE_LANES` (`2026-11-19`). The `<0.9` pin moves
  only on the person's word after both instances serve 0.9.
- **Desk #366 done (`e0801ee`)** on the person's own "Yes" in this chat, after the writer relayed "yes to all":
  wake_from gains the writer, CLAUDE.md's manuscript section and §11's tectonic line, manuscript-skills in tracked
  settings.
- **Lesson, 2026-11-18: a stray `git stash` in the shared tree.** I ran a bare `git stash` while reading a file; it
  took my seven uncommitted RM32 files (no other seat's work was in it, and no other stash existed). `git stash pop`
  put them back clean. Never type `git stash` in this clone; commit or leave the tree as it is.
- **The liaison's re-run of pending-fixes (`f032ecb`): the four lifts are done, 2026-11-18.** F93: `proxy`'s
  spelling shim out, `sidecar_write_path` asked directly (`43a36f5`). F94: `_LANE_KB`/`_DECLARED_KB` out, every
  lane priced from `approx_mb` (`3934432`). F67: decided to keep our own YAML parse, since `load_spec` raises on
  an incomplete spec the audit must read; reason rewritten and pinned by a two-sided test (`e0ea8d4`). F63:
  decided to keep the in-process claim beside upstream's `flock`, comment corrected (`18c3319`, `f974123`). The
  pending-fixes entries are the liaison's to retire or restate; told them. F59 (`set_short_description`) stays
  the pm's scope question.
- Desk #255 (the `test-sheep` rename): waiting on the person. #203, #204, #205 withdrawn 2026-11-16 as no fork (base rule, kit #510).
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
