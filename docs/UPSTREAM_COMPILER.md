# Upstream ledger: the compiler's three packages

`just-dna-format`, `just-dna-compiler` and `just-dna-enricher`, released together from
`dna-seq/just-dna-compiler` with tags `vX.Y.Z` (the tag names the cut; each package carries its own version).
Kept by the liaison seat (`docs/seats/LIAISON.md`); another seat that meets a symptom in these packages sends it
there rather than writing here.

**Two files, split by direction.** This ledger holds the inbound read (each release against what the plugin uses)
and the register of our pieces that duplicate an upstream one. The outbound half, every finding of ours blocked on
an upstream change with its filing state, stays in `docs/just-dna-format-pending-fixes.md` (CLAUDE.md §7), so this
file links an `F<n>` rather than copying it.

Watched on this machine from a clone outside the repository, `/data/sources/just-dna-compiler` (the line
`just-dna-compiler` in the liaison state file, which is the registry liaison's and is reused, never edited):
`[seat.liaison.watch.compiler]` says each new tag. **Since 2026-11-12 that path is a symlink to
`/data/sources/just-dna-format`, the compiler's own working clone** (their maintainer: two copies with different
content were "unacceptable"; the old clone is at `just-dna-compiler.old-2026-11-12`). So reading a tag there reads
the live clone: read with `git show <tag>:<path>` and `git grep`, write only the inbox note, and leave fetching to the
watcher. Restrict a `git grep` to paths: a whole-tree grep on NTFS times out.

## Read mark

**Pre-release trial of 0.9, 2026-11-19 (their request before the cut):** branch `0.9` at `d9c578ae` (all three tiers, still labelled 0.8.10) in a throwaway worktree, our suite: 1096 pass, 1 skip, 3 fail, all three ours, none an upstream break. (1) `test_cli_map`: two new enricher commands, `clinvar-gkm publish` and `opentargets publish`, belong in `cli_map._PUBLISH`; (2) the same file: the new `ensembl_rsid_index` lane's build command maps to `provision_caches(lanes=["ensembl_rsid_index"])`, and the test reads the lane name as a tool name, a false positive in our test; (3) `test_toolbox`'s layered-header budget is 2 characters over because the instructions quote the installed version (`0.8.10` against `0.8.6`). Read, not run: the new lane state `stale` (a derived lane whose parents moved) reads as not present to `provisioning`, which then plans a pull or build, the same ladder as `prepare_lane`; the plan does not yet say why (`LaneStatus.stale`). `lookup_variant`'s new `ValueError` comes only from the `remote` (`RemoteSnapshots`) route, which we do not pass, so it cannot reach `lookup_variant` here today. Reported to their liaison; the three fixes are the lead's at adoption.

**Installed: format, compiler and enricher 0.8.10** (the lead's `666518d`, released as 0.48.21, `v0.48.21`, 2026-11-26; floors `>=0.8.10`; F171's case compiles strict; polygon `registry_check` of fto_bmi verdict true). Before that, 0.8.9 (`0091b06`, 2026-11-20, released in 0.48.17, `v0.48.17` `4aa5e56`, 2026-11-21). Before that, **format and compiler 0.8.6, enricher 0.8.8** (`uv.lock` on main; enricher 0.8.8 floored and locked in `33d706c`, 2026-11-17, released in 0.48.14; the lead started the repairing `cache pull` of civic, clinvar, mitomap and ensembl_variations on this machine the same night; 0.8.7 in `37caadb`, 2026-11-15, release 0.48.12; the trio `319765c`, release 0.48.10; capped `<0.9`). Before that: 0.8.5 (release 0.48.9), 0.8.4 (`uv.lock`, 2026-11-12, release 0.48.7); format 0.7.1, compiler 0.7.2, enricher 0.7.3 (`uv.lock`, 2026-11-07), capped `<0.8` in
`pyproject.toml` on the person's decision of 2026-09-04: the 0.8 move is an explicit bump, made once both
registry instances serve 0.8 (`/api/v1/version`). polars and duckdb are capped `<2` in the lock beside it
(`c361614`) until that move.

**0.10 consumers' preview, tried 2026-11-27** (branch `0.10` at `992e85b1`, versions still 0.9.0; asked by their lead before the first review round; not a release, so the read-to line below stays). Tried on `adopt-0.9` in `.worktrees/liaison-try-0.10` with the trio from the branch's git source (proved by `StudyRow.effect_direction` and `derivation_records.needs_rederive` importing): 1116 pass, 1 skip, 1 fail, pyright and ruff clean. Nothing filed upstream. **RM468**, a per-host store of live answers, is on by default (`JUST_DNA_ANSWER_STORE`, off with an empty value) and keyed by the release that answered; an offline enrich does not read it (the needs-sequence warning stays with the sequence stored; offline with it on and off gives identical results), a second online run takes from it, and the suite writes none. The fail is ours: `test_the_rs_number_at_an_hg19_position_comes_back_without_the_hgmd_record` asserts the overlap is the hg19 client's first request, and with the store on the `/info/data` release probe comes first; it passes with the store off. **RM460**'s `rsid_genotype_reads_as_two_events` reaches our compile warnings on the F171 case; **RM435**'s `effect_direction` reaches `describe_table` unchanged. Not run: RM385 (no local FASTA here) and `needs_rederive` (nothing of ours calls it). Handed to the lead for adoption: neutralize `ANSWER_STORE_VAR` in conftest; carry `EnrichResult.answer_usage` through `enrich_module` and decide the shared `EutilsClient`'s default store (attribution, §2); sweep `effect_direction` into the studies dossier and module-curate, and `describe_table`'s 'never increase/decrease' wording; a SYMPTOMS entry for the new code; the format floor for the new codes; wrap or abstain on `needs_rederive` and `--sequence-uri`. **Read to: `v0.9.0`** (all three tiers, on PyPI 2026-11-26 21:11 UTC, tag `93160691`; read by `INTEGRATION_0_9.md` the same evening). **0.9.0**, the next minor: the enricher reads reference data wherever it lives (local, the registry's proxy, Hugging Face); the compiler's source does not move, and `RELEASE_RECORDS["0.9.0"]` records no axis moving on a recompile. Its § 3 list for us: `LANE_STATES` gains `stale` (our `CachePlanLane.state` description lists the other three by hand; `provisioning` reads the state as a string, so a stale lane already reads as not present), and repin the trio. Nothing in `src/` imports a name § 1.10 removes, builds `EnsemblSettings` or passes a URL to `lane_status`. **Tried from PyPI** in `.worktrees/liaison-try-0.9.0` (caps moved to `<0.10`, the lock moves exactly the three, registry client 0.32.1 resolves beside it): 1109 pass, 1 skip, 1 fail, pyright and ruff clean; the fail is `test_every_upstream_command_is_mapped_or_abstained_with_a_reason`, for the two new operator publish commands (`clinvar-gkm publish`, `opentargets publish`). Handed to the lead, who builds the adoption on `lead/adopt-0.9`; main keeps `<0.9` until both instances serve 0.9 (both on format 0.8.10 at 21:40 UTC) and the person's word on the minor. Earlier: **`v0.8.10`** (all three tiers, on PyPI 2026-11-26 11:12 UTC, tag `65cfa25b`; read the same day). **0.8.10**, a patch, floors `>=0.8.10` throughout; format changes only its release record. RM453: a mirrored indel site that no witness placed (`unplaced` on both spellings) fills both spellings again, so 0.8.9's strict refusal of that row goes; a recompile is declared (`RELEASE_RECORDS["0.8.10"]`), `content_signature` unmoved. RM456: `compile_module` over an unsearchable `logs/` no longer raises on Python 3.13. RM455: a `batch_size` below 1 raises `ValueError` (we pass none), non-UTF-8 pull records read as unreadable, additive `CacheLane.payload_filename` and `net.check_batch_size`. Our upstream-tag copies of the two reference examples are unchanged since `v0.8.9`. **Measured in `.worktrees/liaison-try-0.8.10`** (floors raised, the lock moves exactly the three): **F171's case now compiles strict.** Upstream's `v0.8.8` `pathogenic_clinvar` with its two `rs80356821` rows deleted, `enrich_module(offline=true)` then `compile_module(strict=true)` through the in-memory client: success on 0.8.10, while the same steps on main's 0.8.9 refuse with the F171 sentence. Suite 1109 pass, 1 skip (no `.env`), 1 fail, pyright and ruff clean. The fail is the upgrade's own: `test_the_layered_header_still_fits_what_the_host_keeps`, 2014 characters against 2012, because `INSTRUCTIONS` prints both versions and `0.8.10` is one character longer than `0.8.9` twice; main sits on the budget exactly. Handed to the lead for the floor move, taken the same day in 0.48.21 (1111 pass there). Earlier: `v0.8.9` (on PyPI 2026-11-18 22:45 UTC; read 2026-11-20, late because the quota hold kept the watcher line back). **0.8.9**, a patch: RM449 (an rsID row's indel genotype at a mirrored insertion/deletion site is filled on the spelling a witness placed, not on both events; a declared corrected derivation, so modules it reaches want a recompile, `content_signature` unmoved), RM448 (online, one witnessed ALT of a multi-allelic indel no longer withholds the whole site), RM451 (`reverse` stops inventing `resolution.csv` rows), RM447 (an `ensembl-rest` allele refusal names REST's older dbSNP build), RM446 (a reused client's old 410 no longer misreads a later outage), RM452 (a NULL snapshot `start` places nothing). New under `--strict`: an rsID row at a mirrored indel site whose `placement_verdict` places neither spelling is refused as unresolved (RM453, 0.8.10, fixes the offline merged-rsID case). Our F171 (the tester, 2026-11-21) is that case: an offline `enrich_module` leaves a mirrored-indel row unplaced and the strict compile refuses it; the lead routed the refusal in `9d19bcd` (released in 0.48.18, `v0.48.18` `73e3962`, 2026-11-22) rather than wait, since the strict unplaced-row refusal predates 0.8.9 and 0.8.10 removes only one way in. No new warning code; additive public names `Withholding.retired_met`, `net.retired_mark`, `withheld_reason(since=)`. Each tier floors the others at `>=0.8.9`. Our suite on it, in a throwaway worktree: 1099 passed, 0 failed (2026-11-20). In our lock and floored `>=0.8.9` on all three since `0091b06` (the lead, 2026-11-20, after the 0.48.16 tag, so unreleased; a polygon `registry_check` of a 0.8.9 compile read verdict true). Earlier: `v0.8.8` (tag `655f1ebc`; the enricher alone, on PyPI 2026-11-17). **0.8.8** carries RM445: a pull no longer puts the hub's `release.json` over cached files it kept and nothing attests, so old bytes stop carrying a new release's label (their remote-read trial found a ClinVar cache serving August data as `clinvar_2026-11-01`); `cache pull`/`cache prepare` repair such caches; `enrich` no longer fetches beside a local build, and a missing part is could-not-run. New refusal for a direct caller: `ensure_*_snapshot` raises the lane's error when `release.json` could not be fetched and the cache is absent or unfinished (Ensembl's lane now asks too), where it went on unlabelled; `provision_caches` reaches that through `prepare_caches`, so an outage now refuses instead of pulling unlabelled. Their steps after upgrading: floor the enricher `>=0.8.8`; before the first pull, read each lane's `pull-record.json` (no `release_sha256` key marks a cache that may have served an older release under a newer label, and modules enriched against it since may carry old answers); then `cache pull` once. **This machine (2026-11-17):** `civic`, `clinvar`, `ensembl_variations` (14 GB) and `mitomap` have no `release_sha256`; `gnomad_constraint` has one. Floor and the pull are the lead's (told in `#just-module-creator>0.8`). `v0.8.7` (its release entry, below; the enricher alone, on PyPI 2026-11-15); `v0.8.6` (its release entry; all three on PyPI 2026-11-13); `v0.8.5` (its release entry; all three on PyPI 2026-11-12); `v0.8.4` (its release entry on their `main`; all three on PyPI 2026-11-11, tag `36cbc20` pushed later that day); `v0.8.3` (its release entry; all three on PyPI 2026-11-10); `v0.8.2` (its release entry; on PyPI 2026-11-08); `v0.8.0` (tag `e97339a`, on PyPI 2026-11-05), through `docs/INTEGRATION_0_8.md` as it stands on
their `main` at `911a2fd` (2026-11-07), which postdates the `0.8` branch head `edf2661`. Read for the adoption map
below, not entry by entry through the changelog: the integration file is the release's own per-consumer
reading, and its § 3 block for this plugin is answered here.

## Backlog

- **0.7.0 to 0.7.3, read for levers: done 2026-11-07.** The fourteen pending-fixes entries whose fix is *in our
  lock* were re-run on the installed packages; each now says what of ours can come out and whose that is. Handed to
  the lead: F94 and F93 (fallbacks to delete), F63 (our in-process claim beside upstream's flock), F59 (the registry
  client's `set_short_description`, unwrapped), F67 (`compiler.load_spec` in place of our `yaml.safe_load`).
- **`v0.8.0`'s changelog, entry by entry**, for what the integration file does not name (the registry liaison
  read it at the cut; ask before repeating it).
- **`v0.8.7`, read by its release entry** (tag `3b65ab7a`, 2026-11-14, enricher 0.8.7 on PyPI; format and compiler
  stay 0.8.6). Text only: no public name, field, outcome or raise changes. RM444 (our S155, F152): `recover_rsid`'s
  `none` beside overlapping records counts them and says to retry at a neighbouring anchor, a position-only
  `recovered` makes its advice conditional, the `ambiguous` text names `ref`/`alts` instead of the CLI flags, and
  the docstring says the anchor may be neither VCF's nor HGVS's. RM442: the two AlphaGenome licence rows' `notice`
  and `license` text corrected; a module re-enriched after it carries the new text, its digest moves, no licence
  axis moves. **Done by the lead in `37caadb` (enricher 0.8.7 locked, released in 0.48.12; floored `>=0.8.7` by the lead in `147cb45`, 2026-11-16, released in 0.48.13); before it, ours read:** `research._old_assembly_next_step`'s docstring says upstream
  names the CLI flags and over-claims, which stops being true, and its `ambiguous` sentence repeats what upstream
  now says. Floor the enricher at `>=0.8.7` at the bump; format and compiler stay `>=0.8.6`.
- **`v0.8.6`, read by its release entry** (tag `2f03ab4a`, 2026-11-13, on PyPI). No public name, field, table,
  flag or warning code; no return value or raise changes; release record moved nothing, no recompile. Floors to
  `>=0.8.6` at our next bump (the nightly watcher's). What it carries: RM439 (`VariantRow.stat_significance`'s
  description: the module author's verdict across the variant's evidence; `describe_table` passes it through, and
  nothing of ours pins the wording), RM440 (`enrich --rederive` logs one aggregated warning naming rows that lost a
  back-filled rsID on RM438's no-host arm; a log line only), RM437's doc half (INTEGRATION_0_8 § 3: the `ensembl`
  lane carries the core only; the route that pulls `groups/` sidecars stays open for 0.9). Nothing for us to change.
- **`v0.8.5`, read by its release entry** (tag `c036c700`, 2026-11-12, on PyPI). No public name, field, table, flag
  or warning code; release record moved nothing, no recompile. Floors to `>=0.8.5` at our next bump. What it carries:
  RM432 (`gene_metrics.lookup_snapshot`, `civic_snapshot_rows` raise `FileNotFoundError` on an unreadable
  reference), RM434 (`StudyRow.stat_significance`'s description), RM436 (the enricher's tenacity floor back to 9.0,
  for google-genai), RM438 (`resolve_variants` and `enrich` narrow a back-filled rsID by the row's alleles; a direct
  `resolve_variants` caller may get no rsID and an `rsid_ambiguous` warning). Read against our source: we call none
  of `resolve_variants`, `lookup_snapshot` or `civic_snapshot_rows` directly, and our own `tenacity>=9.2.1` floor
  stays (our `net.py` spells `multiplier=`). Their step 5 (`enrich --rederive` for back-filled coordinate rows) is
  for module authors; the registry measured nothing published moving.
- **`v0.8.4`, read by its release entry** (on PyPI 2026-11-11). Format and enricher changed source, the compiler
  moves for its floor; no public name, field, table, flag or warning code; release record moved nothing, no
  recompile. **The 0.8 adoption floors all three at `>=0.8.4`.** It releases RM425 (F142), RM426's patch half
  (F135), RM427's patch half (F132: the skip names `cache pull --only clinvar` and `clinvar build`, and a guard test
  resolves every quoted command), and RM428 (F146: page of 500, one retry with no size). No 0.7.4 (their desk #252):
  the shipped plugin's GWAS pass comes back only with the 0.8 move. Their step after upgrading: re-run the GWAS
  pass on any module it ran on 0.8.0 to 0.8.3, which filled no row.
- **`v0.8.3`, read by its release entry** (tag `725eb2b`, pushed 2026-11-10; format, compiler and enricher 0.8.3 on
  PyPI the same evening). All three move; no public name, field, table, flag or warning code; release record over
  22 reference modules moved nothing, so no recompile. **The 0.8 adoption now floors all three at `>=0.8.3`** (their
  "After upgrading" step 1). What reaches us:
  - **RM422** (F137, S138): `derived_row_orphan` gains a `resolution.csv` arm, a warning in both modes. **RM423**
    (F139, S139, its patch half): `merge_records` drops carried records once the authored bytes moved, and logs
    which. Both released, neither in our lock (`<0.8`); our audit signals stay until then (pending-fixes).
  - **Steps at the adoption, from their list:** a `verification.json` written by 0.8.2 or earlier over bytes edited
    since may still carry stale records (RM423 does not repair it: re-run the named checks); and `cache pull` or
    `cache prepare` once, because RM420 moves a pulled lane to the hub's release (gnomAD constraint to
    `gnomad_v4.1.2_constraint`, STRchive to `strchive_v2.28.0`), which `provisioning.py`'s lane pricing reads then.
  - RM418 (one NCBI pacing gate per process), RM409 (Ctrl-C stops two bulk builds), RM421 (120 s bulk-download
    timeout): nothing for us now; RM418 is read against `net.py`'s shared NCBI gate at the adoption.
- **`v0.8.2`, read by its release entry** (tag `b98f7e9`, 2026-11-07; compiler 0.8.2 on PyPI 2026-11-08). All three
  packages move; no public name, field, table, flag or warning code; no recompile needed. The 0.8 adoption floors
  all three at `>=0.8.2`. What reaches us:
  - **RM414, RM415**: F130 and F131 (S136, S137) are released here.
  - **RM417, and it is true of our 0.7.3 lock too**: gene-metrics rows from the live gnomAD API were labelled
    `gnomad_v2.1.1_constraint` while the API served gnomAD 4.1.1 or later; from 0.8.2 they are
    `gnomad_api_constraint`. `skills/module-tables/references/gene_metrics.md` (lines 190, 325, 480) reads the
    label as true and explains the BRCA1 difference between snapshot and API rows as v4.1 against v2.1.1, which
    it is not. Corrected by the lead in 0.48.3 (`d99089a`). Relabelling a module means deleting `gene_metrics.csv` and
    enriching again, which moves its fact hash.
  - RM410 (the constraint snapshot moves to gnomAD 4.1.2 once published; 4.1 rows are kept on a re-run), RM416
    (`--pin` on a lane that cannot take one stops the run), RM408 (Open Targets pulls, ~5.5 GB), RM411, RM413:
    read against `provisioning.py`'s lane pricing at the adoption, nothing now.
- **`v0.8.1`, read by its release entry** (tag `6330f90`, recut 2026-11-07 15:33 UTC; not on PyPI at 16:40 UTC,
  the enricher's latest there is 0.8.0). Enricher 0.8.1 only; format and compiler stay 0.8.0, so no recompile and
  no release record. No new field, table, parameter, public function or warning code. What reaches us:
  - **RM400**: live Ensembl REST no longer writes loci on GRCh38 patch and alt contigs, and `--rederive` leaves
    recorded ones out instead of reporting `lost_allele`. The 0.8 adoption floors the enricher at 0.8.1.
  - **RM398**: the third placement witness is dbSNP's own record (from the merge check's `esummary`, no new
    request): new `resolution.csv` rows name `dbsnp` as `placement_witness` where they named `ensembl`, and
    `sources.csv` gains a `dbsnp` row. Map item 2 and the licensing readers take both. A run with
    `verify_rsids=False` counts those indels as not asked (the compiler's triage, answering the registry's S134).
  - **RM403**: every retry logs a WARNING on `just_dna_enricher.net`, so a count of logged warnings rises during
    an outage; a give-up names its attempts and seconds.
  - RM401 (20 rsIDs per live Ensembl request), RM407 (an indel's VRS mint reads the reference once per locus),
    RM397 (wheel packaging): nothing for us.

## What the plugin uses

From the module-level imports under `src/` (an AST walk, 2026-11-07). A release is read against this list; a
symbol that moves here is a change to read whole. Counts are files importing it.

### just-dna-format

- `layout`: `SIDECAR_SPELLINGS`, `SidecarCollision`, `preferred_spelling`, `resolve_sidecar`, `sidecar_write_path`.
- `manifest`: `ProvenanceDoc`, `ProvenanceItem`, `read_manifest`. `integrity`: `IntegrityError`, `verify_manifest`
  and the seven `*_signature` functions (clinical assertion, frequency, gene metrics, gene validity, GWAS effect,
  literature, resolution).
- Row models with their `*_FACT_FIELDS`: `assertions`, `frequency`, `gene_metrics`, `gene_validity`, `gwas`,
  `literature`, `resolution` (`ResolutionRow`, `RESOLUTION_FACT_FIELDS`).
- `identity`: `NAMESPACE_PATTERN`, `is_valid_namespace`, `is_valid_version`, `validate_namespace`.
- `spec`: `DOI_PATTERN`, `ModuleSpecConfig`. `vocab`: `VALID_DECLARED_USE`. `vrs`: `normalize_chrom`.
  `reference` (module import).

### just-dna-compiler

- `compiler` (six files; `load_csv_rows`, `load_spec_variants` by name), `draft` (`DraftError`), `hints` (five
  files: `DERIVED_TABLE_MODELS`, `key_fields`, …), `scaffold`.

### just-dna-enricher

- `enrich`: `enrich`, `EnrichmentError`, `IdentifierUnavailable` (`tools/passes.py`, `tools/refresh.py`).
- Check passes and their errors, each caught narrow-first (CLAUDE.md §2): `acmg`, `assertions`, `clingen`,
  `clinpgx`, `cpic`, `expression`, `frequencies`, `gene_metrics`, `gene_validity`, `gwas`, `identifiers`,
  `litvar`, `pgx`, `strchive`, `verification`.
- Drafters: `civic_draft`, `clinpgx_draft`, `clinvar_draft`, `mitomap_draft`, `pgx_draft`, `pubmind_draft`,
  `strchive_draft`.
- Shared plumbing: `net` (`PacingGate`, `attempt_floor`), `eutils` (`EutilsClient`, `EutilsSettings`),
  `literature` clients, `lookup.LookupClients`, `caches` (`CACHE_LANES`, `lane_status`, `prepare_lane`,
  `provisioning_closure`, …), `licensing` (the `*_TERMS`, `check_declared_use`), `locations` (`CACHE_BASE_VAR`,
  `default_ensembl_cache_dir`).

## Our pieces an upstream one may now do

| Ours | Theirs | Since | Replacing ours would cost |
|---|---|---|---|
| `refresh_sidecar` (`tools/refresh.py`): capture, delete, re-enrich, classify, restore on a partial answer | `enrich --rederive` (`INTEGRATION_0_8` § 2 step 5), which asks every source again and labels each changed subject (`respelled`, `moved`, `lost_allele`, …, § 1.43) | 0.8.0 | Not a replacement: `--rederive` re-asks in place, ours guards hand-curated rows (`source="manual"`) with a verified capture. A lever: our classification could read upstream's labels instead of diffing. The lead's call at adoption. |

## The 0.8 adoption map

Written 2026-11-07 against `INTEGRATION_0_8.md` at `911a2fd`, for the lead (who owns the code) and the pm (who owns
the scope). **The gate is unchanged: both registry instances serving format 0.8.** On 2026-11-07 production
answered `format 0.7.1, compiler 0.7.2, registry 0.27.0`; the polygon did not answer within 15 s. The registry's
own `main` has adopted 0.8 (registry 0.28.0, 2026-11-06; 0.28.2 on PyPI requires format `>=0.8.0`), so the deploy
is what remains. A 0.8 module published to a 0.7 server is refused by its `extra="forbid"` models (§ 2 surface 5;
CLAUDE.md §11, "The handshake is not validation").

Sorted hardest first. *Touches* names our code or skill; *cost* is an estimate for the lead.

1. **Breaks us: the pins, the lock and the registry client move together.** format, compiler and enricher to
   `>=0.8.0,<0.9`, `just-dna-registry>=0.28` (0.28 requires format 0.8, so our `>=0.27.0` cannot resolve with
   0.8 and the bump is one commit), the polars/duckdb caps lifted or kept by decision, `uv lock`. Then the
   reference examples copied again from `v0.8.0` (`assets/reference_examples/README.md`). *Touches*
   `pyproject.toml`, `uv.lock`, `assets/reference_examples/`. *Cost*: 1 to 2 hours with
   the suite. Registry 0.28.0's client changes `publish()` (`recover_within=600.0`: a lost response may now
   return the version that landed instead of raising) — read against `registry_publish` (`tools/registry.py`); the `/check` fields 0.28.0 adds
   go into `registry_check`'s projection (`docs/UPSTREAM_REGISTRY.md`, "Read entry by entry").
2. **Breaks us: every 0.7-shaped `resolution.csv` reading.** Seven new optional columns (§ 1.18, 1.19, 1.31,
   1.32, 1.38), a 0.7 `ResolutionRow` refuses a 0.8 table; keys lose `:None` (§ 1.26); a rejected answer leaves
   no row (§ 1.36). *Touches* `tools/refresh.py`, `tools/passes.py`, `models.py` (the `not_found` readings), and
   the skills that read `not_found`: `module-101/references/SYMPTOMS.md`, `module-compile`, `module-enrich`,
   `module-refresh`, `module-tables/references/resolution.md`. *The two corrections § 3 asks of us*: F85 in the
   pending-fixes file (done by the liaison, 2026-11-07) and the compile guide's reading of `not_found` (the
   lead's, at the pin). *Cost*: half a day.
3. **The shared Ensembl cache has already moved on this machine** (§ 1.29). `/data/just-dna-cache/ensembl_variations`
   holds the split snapshot (`just-dna-seq/ensembl_variations_split`) since 2026-11-04 22:38, the old one kept
   beside it as `ensembl_variations.pre-0.8` (the registry liaison, 2026-11-07). **Probed against our enricher
   0.7.3, 2026-11-07:** `resolver.lookup_loci` reads the split cache and gives the same loci and alleles as the old
   one for ten rsIDs (`rs4988235`, `rs1801133`, `rs429358`, `rs7412`, `rs1799945`, `rs1800562`, `rs4244285`,
   `rs12248560`, `rs2231142`, and the indel `rs113993960`); `lane_status` reports the lane `present`, and
   0.7.3's `_provision_snapshot` returns early on intact parquets, so it does not pull the old repo
   (`just-dna-seq/ensembl_variations`) on top. It would, file by file, for a parquet whose footer is corrupt: that
   is the one way a 0.7 tool here mixes the cache. Not probed: positional (coordinate → rsID) lookups, and
   multi-ALT indels, which the split snapshot writes ALT by ALT (§ 1.35). The duckdb-2 hazard (RM344) is the
   same cache and is held off by our `<2` cap. At adoption: nothing to pull here; another machine pulls once.
   *Touches* `skills/module-start/GUIDE.md` (the cache offer) and `provisioning.py`'s lane pricing.
4. **Breaks us: new refusals in `validate` and `compile`** (§ 2 surface 13: `rsid_placements_disagree` under
   strict, half-stated pairs, HLA grammar, a DOI in `pmid`). `validate_spec` now refuses wherever the compile
   would (§ 1.23). *Touches* `tools/authoring.py`'s compile and validate wrappers, `SYMPTOMS.md`. Match by code,
   never by sentence (surface 12): check `lint_rows`' and the symptom table's phrase matches. *Cost*: 2 hours.
5. **Breaks us: new warning codes and `quality_floor_inverted` retired** (§ 1.1). `warnings_summary` is read in
   `tools/authoring.py:1098`. *Cost*: under an hour, mostly the symptom table.
6. **Lever: new authored columns and tables to sweep into the skills** (§ 1.2.1 `meta.csv`, § 1.2.2
   `model_organisms.csv`, § 1.5 `pmid=NONE` plus `doi`, § 1.6 optional columns; CLAUDE.md §11: "a floor bump is
   not adoption"). *Touches* `module-draft`, `module-curate`, `module-tables/references/`, `scaffold` companions.
   *Cost*: a day; the pm's scope call.
7. **Lever: derived tables a drafting or pass tool could fill** (§ 1.2.3 `locus_to_gene`, `colocalisations`,
   `consequences`; § 1.2.4 `ld_pairs`; § 1.14 the `clinvar_gkm` lane). Parity is the default (CLAUDE.md §5): each
   needs a tool or a written reason in the pending-fixes file. *Cost*: per pass, an hour or two.
8. **Lever: `enrich --rederive`** against our `refresh_sidecar` (the register above).
9. **Fixed what we worked around** (0.8.0 only, the pending-fixes table): F115, F118, F113, F108, F105, F116,
   F127, and RM382 for F85. Also F129 (`docs/dogfooding.md`, the tester, 2026-11-07, high): on 0.7.3
   `draft_repeat_loci` skips when handed no catalogue and does not resolve the provisioned STRchive lane, so
   `draft_from_strchive` cannot draft; RM395 fixes it in 0.8.0. Mitigated by the lead in 0.48.3 (`02b8ce7`: our wrapper
   passes `resolve_strchive_reference()`); the mitigation comes out with the move. Each mitigation comes out only once the pinned release passes its reproduction.
10. **`artifact.digest` moves on every recompile** (§ 1.11, `toolchain_differs` between polars 1 and 2): a
    published module compared by digest reads as changed. `compare_to_published` (`tools/comparison.py`) already
    compares by `content_signature`; what it may add is `compilation.toolchain` beside a moved digest, so an author
    reads "another polars" rather than "changed". *Cost*: an hour. **Done (2026-11-15)**: `compile_module`'s `toolchain` and
    `compare_to_published`'s `toolchain` metadata line.

Nothing for us in § 1: the release-sweep readers (§ 1.11 sweep fields, RM342/RM352), the snapshot publishers
(§ 1.27, § 1.40), `reverse` (§ 1.28, § 1.34, unless a tool wraps it), the HF `HfApi` stubs.
