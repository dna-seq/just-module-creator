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
`[seat.liaison.watch.compiler]` says each new tag. `/data/sources/just-dna-format` is the compiler's own working
clone, where its seats commit: read it, never fetch or write there.

## Read mark

**Installed: format 0.7.1, compiler 0.7.2, enricher 0.7.3** (`uv.lock`, 2026-11-07), capped `<0.8` in
`pyproject.toml` on the person's decision of 2026-09-04: the 0.8 move is an explicit bump, made once both
registry instances serve 0.8 (`/api/v1/version`). polars and duckdb are capped `<2` in the lock beside it
(`c361614`) until that move.

**Read to: `v0.8.0`** (tag `e97339a`, on PyPI 2026-11-05), through `docs/INTEGRATION_0_8.md` as it stands on
their `main` at `911a2fd` (2026-11-07), which postdates the `0.8` branch head `edf2661`. Read for the adoption map
below, not entry by entry through the changelog: the integration file is the release's own per-consumer
reading, and its § 3 block for this plugin is answered here.

## Backlog

- **0.7.0 to 0.7.3, read for levers.** 0.7 was adopted for what broke us (CLAUDE.md §11), not read for what it
  fixed of ours. The pending-fixes table "Against 0.8.0" lists fourteen entries whose fix is *in our lock*: each
  closes once its reproduction passes on the installed package. Next slice: those reproductions, one entry at a
  time.
- **`v0.8.0`'s changelog, entry by entry**, for what the integration file does not name (the registry liaison
  read it at the cut; ask before repeating it).
- **0.8.1**: cut on their `main` (enricher 0.8.1 only, not on PyPI on 2026-11-07, the registry liaison). RM400 stops
  live Ensembl REST writing patch and alt-contig loci, so a `--rederive` under it drops them. Read at its tag and
  publish; the 0.8 adoption should floor the enricher at it if it is out by then.

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
   return the version that landed instead of raising) — read against `registry_publish` (`tools/registry.py`).
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
   and RM382 for F85. Each mitigation comes out only once the pinned release passes its reproduction.
10. **`artifact.digest` moves on every recompile** (§ 1.11, `toolchain_differs` between polars 1 and 2): a
    published module compared by digest reads as changed. `compare_to_published` (`tools/comparison.py`) already
    compares by `content_signature`; what it may add is `compilation.toolchain` beside a moved digest, so an author
    reads "another polars" rather than "changed". *Cost*: an hour.

Nothing for us in § 1: the release-sweep readers (§ 1.11 sweep fields, RM342/RM352), the snapshot publishers
(§ 1.27, § 1.40), `reverse` (§ 1.28, § 1.34, unless a tool wraps it), the HF `HfApi` stubs.
