# Upstream ledger: the registry

`dna-seq/just-dna-registry`: the registry service (production and the polygon) and its Python client,
`just-dna-registry` on PyPI, tagged `vX.Y.Z`. Kept by the liaison seat (`docs/seats/LIAISON.md`). The outbound
half (findings blocked on the registry: F87, F88, F92 and the registry `S<n>` they cite) stays in
`docs/just-dna-format-pending-fixes.md`; defects are filed in `../just-dna-registry/docs/CONSUMER_SUGGESTIONS.md`
and named to `just-dna-registry/triage`.

Watched from the registry's own clone, `/data/sources/just-dna-registry` (the line `just-dna-registry` in the
liaison state file, this seat's): `[seat.liaison.watch.registry]` says each new tag. The watcher only fetches;
nothing here writes in that clone.

**Two things to read, and they move apart.** The client we install (`uv.lock`) and the server each instance runs
(`curl -s https://module-registry.just-dna.life/api/v1/version`; polygon: `module-polygon.just-dna.life`). A
guarded call answers `HTTP 409: contract mismatch` on a minor skew (CLAUDE.md §11).

## Read mark

**Installed client: 0.27.0** (`uv.lock`, 2026-11-07). **Servers, 2026-11-07:** production `registry 0.27.0,
format 0.7.1, compiler 0.7.2`; the polygon gave no answer within 15 s (not read, so unknown), then answered HTTP 502 from at least 14:58 to
16:40 UTC (the tester's `registry_health`, and a curl here); asked of `just-dna-registry/lead` the same day: not a deploy it knows of (deploys are the
person's), still 502 at 17:0x UTC, and it has asked the person; still 502 at 02:37 UTC on 2026-11-09 and at 20:50 UTC on 2026-11-10 (production answers, 0.27.0). Registry 0.28.3 (enricher 0.8.1) is being cut; the
polygon gets it at the next deploy.

**Read to: `v0.28.5`, by its `Client surface:` lines** (2026-11-10), which CLAUDE.md §11 trusts for "did our
methods move". 0.27.1 and 0.28.1, 0.28.2: client surface unchanged. **0.28.0** moves it: `catalog_stats()`
makes one request to the new `GET /stats`; `publish()` gains `recover_within=600.0` (a publish whose response
was lost may return the version that landed instead of raising, after waiting up to that long); `whoami()` gains
`site_admin`; account merge and rename methods are new. **0.28.3** (2026-11-07): client surface unchanged; new
admin-only `runs`, `run`, `run_log` (upgrade logs over REST), nothing for us. **0.28.4** (2026-11-07, tagged 2026-11-09): client surface unchanged; `warm-caches`/`drop-caches` name each lane's readers, `warm-caches --proxy`/`--exclude`, and `REGISTRY_LOG_FILE` (the server's own log, added after the polygon's 502 left nothing to read). Operator only; the `/caches` API's `read_here`, which `registry_caches` passes on, is unchanged. **0.28.5** (2026-11-09, tagged 2026-11-10): client surface unchanged; `CacheLaneStatus` gains `readers`, and `read_here` is true exactly when a lane has one, so five more lanes (`pubmind`, `civic`, `clinvar_gkm`, `strchive`, `mitomap_miss`) read as used here. `registry_caches` passes the field through and nothing of ours branches on it. 0.28.4 floors enricher `>=0.8.1`, as our
map item 1 does, and `upgrade --online` now asks dbSNP (RM398's `dbsnp` witness rows reach republished modules). 0.28.x requires `just-dna-format>=0.8.0`, so our
`<0.8` cap holds us at 0.27.x until the 0.8 adoption (`docs/UPSTREAM_COMPILER.md`, map item 1).

**Filed:** `S28` (F143, the lead, 2026-11-10): no namespace rename; `rename_account` moves the handle only. Unanswered.

## Backlog

Nothing open: 0.27.1 to 0.28.3 read entry by entry, 2026-11-07 (below); 0.28.4 read whole, 2026-11-09, and 0.28.5, 2026-11-10 (above).

## Read entry by entry, 2026-11-07

- **0.27.1** (in our lock's reach, a server release): nothing for us. Its `/check` changes (the identifier pass
  on a module without `variants.csv`, `would_publish_module_level: false` for a strict refusal over another
  assembly's rows, the re-run hint on a refused publish over a withheld indel, the dataset-release probe off by
  default) pass through `registry_check`'s projection unchanged, and no skill keys on the readings they change.
- **0.28.1, 0.28.2, 0.28.3**: operator commands (`upgrade --jobs`, `prune-runs`, `replay-upgrade`,
  `warm-caches`, `drop-caches`, run logs over REST), `?gene=`/`?category=` matching the current version.
  Nothing for us.
- **0.28.0, for the 0.8 adoption** (0.28 requires format 0.8, so none of it reaches us before). Fields a
  `/check` or a version list gains, which `registry_check`'s projection (`tools/registry.py`,
  `PublishPreflight`) and `compare_to_published` should carry rather than drop:
  - the four withheld-placement cases, `unanchored_rsids` (transient, the one a re-run fixes),
    `non_nucleotide_rsids`, `reference_rejected_loci`, `placement.withheld`, and the `placement` / `spelling`
    objects;
  - `retired` beside every unreachable-source list (HTTP 410: upgrade the server's enricher, not re-run);
  - `allele_mismatches` (the rsID is known and the genotype does not sit on it, or fits the other strand),
    the registry's side of F85;
  - `pgx.recorded_use` (a leg that ran under the module's own declared use);
  - the identifier check's `trait_tables_not_read`, `gene_tables_not_read`, `unreadable_tables`, `pgs_ids`,
    `stale_pgs`, `pgs_not_checked` (the PGS Catalog accession check now runs);
  - per version, `toolchain` and `digest_moved_by_toolchain` (map item 10 in `docs/UPSTREAM_COMPILER.md`);
    per verification check, `agreement_is_evidence` with its witness fields.
  Also: strict findings move to `errors` only (format RM359); the subtitle `set_short_description` takes 240
  characters, up from 0.27's 120 (F59); `publish(recover_within=600.0)` (read mark above).

## What the plugin uses

From the imports under `src/` (an AST walk, 2026-11-07):

- `just_dna_registry`: `RegistryError` (eight files), `generate_install_id`.
- `client`: `RegistryClient`, `ModeMismatchError`, `VersionMismatchError` (`tools/registry.py` and the proxy
  lane; `publish(pack=True)` since 0.27.0).
- `specfiles`: `RECOGNIZED_SPEC_FILES`, `DERIVED_FILES`, `DERIVED_REPORT_FILE`, `FACT_CSVS`, `LICENSING_CSV`,
  `RESOLUTION_CSV`, `SOURCES_CSV`.
- `version`: `VersionInfo`, `compatibility_error`.

## Our pieces an upstream one may now do

None read yet. 0.28.0's `recover_within` is the candidate: whether `registry_publish`'s own handling of a lost
response duplicates it is read at the 0.28 adoption.
