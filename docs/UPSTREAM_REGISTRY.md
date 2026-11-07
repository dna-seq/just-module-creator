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
person's), still 502 at 17:0x UTC, and it has asked the person. Registry 0.28.3 (enricher 0.8.1) is being cut; the
polygon gets it at the next deploy.

**Read to: `v0.28.3`, by its `Client surface:` lines** (2026-11-07), which CLAUDE.md §11 trusts for "did our
methods move". 0.27.1 and 0.28.1, 0.28.2: client surface unchanged. **0.28.0** moves it: `catalog_stats()`
makes one request to the new `GET /stats`; `publish()` gains `recover_within=600.0` (a publish whose response
was lost may return the version that landed instead of raising, after waiting up to that long); `whoami()` gains
`site_admin`; account merge and rename methods are new. **0.28.3** (2026-11-07): client surface unchanged; new
admin-only `runs`, `run`, `run_log` (upgrade logs over REST), nothing for us. It floors enricher `>=0.8.1`, as our
map item 1 does, and `upgrade --online` now asks dbSNP (RM398's `dbsnp` witness rows reach republished modules). 0.28.x requires `just-dna-format>=0.8.0`, so our
`<0.8` cap holds us at 0.27.x until the 0.8 adoption (`docs/UPSTREAM_COMPILER.md`, map item 1).

## Backlog

- **0.27.1 to 0.28.2, entry by entry** (only the client-surface lines are read). 0.27.1's server entries touch
  what `registry_check` reports (`/check?identifiers=true` on a module without `variants.csv`, a strict
  `/check` on another assembly's rows, a refused publish over a withheld indel): read against the
  `module-publish` skill's reading of a verdict before the deploy reaches the polygon.

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
