# The CLI surface

The MCP server wraps the authoring loop. Everything else is still CLI-only, and the CLIs remain the
fallback whenever a tool is unavailable (essentials-only mode, no MCP server configured, a flag the
wrapper does not expose).

Install: `pip install just-dna-enricher` pulls the compiler and the format tier. Python ≥ 3.13.

## What is wrapped, and what is not

| Task | MCP tool | CLI |
|---|---|---|
| choose a table, learn its columns | `list_tables`, `describe_table`, `table_requirements` | `describe`, `requirements`, `reference` |
| templates, scaffolding | `get_template`, `scaffold_module` | `template`, `stub`, `scaffold` |
| lint authored rows | `lint_rows` | `hint <kind> --file F` |
| validate / compile | `validate_module`, `compile_module` | `validate`, `compile` |
| resolve coordinates | `enrich_module` | `enrich` |
| signature / integrity / round-trip | `module_signature`, `verify_artifact`, `reverse_module` | `signature`, `verify`, `reverse` |
| identifier currency | `check_identifiers`, `lookup_identifier` | `check-identifiers`, `hint gene/trait` |
| variant + citation lookup | `lookup_variant`, `lookup_citation` | `hint variant`, `hint citation` |
| **literature search** | `literature_search` | — (nothing upstream searches) |
| **open access + full text** | `lookup_open_access`, `fetch_fulltext` | — |
| **citation graph** | `paper_citations` | — |
| registry search / read / publish | `registry_search`, `registry_get_module`, `registry_download`, `registry_publish` | `registry-client list / download / publish` |
| drafting from a source | `draft_from_clinvar`, `draft_from_cpic`, `draft_from_clinpgx` | `draft-panel`, `draft`, `draft-clinpgx` |
| fact passes | `enrich_facts`, `enrich_literature_pass` | `frequencies`, `gene-metrics`, `dosage`, `literature` |
| **signing** | — | `keygen`, `sign` |
| **PGx cross-checks** | — | `pgx`, `clinpgx check`, `check-acmg` |
| **snapshot building** | — | `clinvar build`, `clinpgx build`, `acmg build`, `cache pull` |

## `just-dna-compiler` (offline, never fetches)

| Command | Does |
|---|---|
| `scaffold <dir> --kind K --name N` | create `module_spec.yaml` + a stub CSV per kind. Never overwrites. `--rows`, `--dry-run` |
| `template <kind>` / `stub <kind>` | header-only CSV / header plus placeholder rows |
| `requirements <kind>` | always / one-of / never-empty-defaults / optional. `--json` |
| `describe <kind>` | full JSON: columns, vocabularies, pick-lists, requirements |
| `reference` | every model at once. `--summary`, `--schemas` |
| `hint <kind> --file F` | inspect authored rows; report wrong / rewritten / left-to-you. Writes nothing |
| `validate <dir>` | full pre-flight, exit 1 if invalid. `--strict/--best-effort` — pass the mode you will compile with |
| `compile <dir> <out>` | parquet + `manifest.json`. `--strict`, `--compression`, `--compiled-by` |
| `signature <dir>` | the content signature of the raw authored data — no compile, no reference |
| `reverse <artifact> <out>` | artifact → authored spec DSL. `--resolution/--no-resolution`, `--genome-build` |
| `keygen --out key.pem` | Ed25519 key; prints the public key `verify` pins |
| `sign <dir> --private-key K` | signs `artifact.digest`, writes the signature into the manifest |
| `verify <dir>` | re-hash every file, recompute the digest, check the signature. `--public-key`, `--no-require-marketplace`, `--check-inputs/-logs/-provenance/-logo` |

**Never pass `--no-resolve` (`resolve_with_ensembl=False`) with a `resolution.csv` beside the spec.**
The flag reads as "do not use Ensembl" and is actually the master switch for resolution of *every*
kind, so the compile succeeds and writes a module whose every row has no `chrom`/`start`. The MCP
`compile_module` tool cannot reach that branch; the CLI can.

## `just-dna-enricher` (the only tier that fetches)

| Command | Does |
|---|---|
| `enrich <dir>` | → `resolution.csv`. `--strict`, `--offline`, `--no-clinvar`, `--no-gnomad`, `--no-vrs`, `--no-verify-ref/-clinsig/-rsids`, `--keep-par-twin`, `--ensembl-cache`, `--clinvar-cache` |
| `frequencies <dir>` | → `frequencies.csv` from gnomAD. `--populations`, `--dataset`. Online only |
| `gene-metrics <dir>` | → `gene_metrics.csv` constraint. Snapshot first, live API as fallback |
| `dosage <dir>` | ClinGen dosage rows onto `gene_metrics.csv`. `--use`, `--url` |
| `literature <dir>` | → `literature.csv`. `--fulltext/--no-fulltext`, `--doi/--no-doi` |
| `draft <dir> --gene G` | CPIC → the three PGx tables. `--drug`, `--allele`, `--population`, `--use`, `--dry-run` |
| `draft-panel <dir> --gene G` | ClinVar → `variants.csv` + `studies.csv`. `--snapshot`, `--offline`, `--clin-sig`, `--min-review-stars`, `--max-citations`, `--use`, `--dry-run` |
| `draft-clinpgx <dir> --snapshot S` | ClinPGx → `pharm_variants.csv`. `--gene`, `--drug`, `--min-evidence-level`, `--use`, `--dry-run` |
| `check-identifiers <dir>` | trait CURIEs (OLS4), gene symbols (HGNC). `--no-traits`, `--no-genes` |
| `check-acmg <dir>` | `acmg_sf` vs the ACMG SF list. `--sf-list` (strongly preferred), `--offline`, `--url` |
| `pgx <dir>` | `function_status` vs PharmVar + CPIC. `--no-pharmvar`, `--no-cpic`, `--use` |
| `clinpgx check <dir> --snapshot S` | `pharm_variants.csv` vs the ClinPGx snapshot, offline-capable |
| `hint variant\|citation\|trait\|gene` | look up one identifier. Writes nothing. `--json`, `--offline`, `--ambiguity`, `--frequencies` |
| `vrs mint <dir>` | stamp `ga4gh:VA.…` ids onto `resolution.csv` (substitutions offline, indels online) |
| `enrich-and-compile <dir> <out>` | enrich + compile in one call. `--frequencies`, `--gene-metrics` |

The three sources this server reaches that the enricher does not — Semantic Scholar, arXiv and
Unpaywall — have no CLI equivalent anywhere in the toolchain. Discovery is an app-surface feature;
the enricher's literature tier verifies citations you already have and deliberately does not search.

Snapshot builders (dev/publisher surface): `clinvar build|citations|publish`, `clinpgx build`,
`acmg build`, `gnomad constraint`, `cpic build`, `pharmvar build`, `cache status|pull`, `upload`.

Every pass takes `--strict` / `--best-effort`, and every pass that can degrade takes `--offline`.
`--offline` is the only switch; an explicit `--*-cache` path is the inject-only escape hatch and is
never second-guessed.

## `registry-client`

`version, list, download, import-module, publish, register, namespace-available, claim-namespace,
find-by-hash, amend-changelog, amend-logo, update-module-version`.

Reads `REGISTRY_URL`, `REGISTRY_TOKEN`, `REGISTRY_TIMEOUT`. The MCP server reads the same
`REGISTRY_TOKEN` as a fallback, so an author already logged in does not have to re-declare it.

`register` and `namespace-available` are wrapped as `registry_register` and
`registry_namespace_available`, so onboarding no longer needs this CLI. The wrapped register also
stores the token it mints into the session and returns the install-id with a warning about what it
is for; the CLI prints both and leaves saving them to you. Use the CLI if you want an account
without a running server, or `--difficulty` control the tool exposes as `difficulty`.

## Environment

A `.env` found by walking up from the working directory is loaded automatically.

| Variable | For |
|---|---|
| `JUST_DNA_PIPELINES_CACHE_DIR` | base for all three snapshot caches (else a platform cache dir) |
| `JUST_DNA_ENSEMBL_CACHE` / `JUST_DNA_CLINVAR_CACHE` / `JUST_DNA_GNOMAD_CONSTRAINT_CACHE` | override one cache path |
| `NCBI_API_KEY` | tightens PubMed/dbSNP pacing from 1/3 s to 1/10 s |
| `JUST_DNA_CONTACT_EMAIL` | sent to NCBI/Europe PMC as the polite-pool contact; omitted when unset |
| `PHARMVAR_API_KEY` | the PharmVar leg of `pgx`. **Personal under PharmVar's ToS §2 — never bake it into a module, fixture or snapshot.** |

The MCP server reads none of these; the enricher reads them straight from the process environment.
Set them once in `.env` and both surfaces see them.

## Python, when neither CLI nor tool is enough

`just-dna-format` ships no CLI, so a few things are import-only:

```python
from just_dna_format import alleles, reference, vocab
from just_dna_format.base import derive_variant_key
from just_dna_format.integrity import verify_manifest
from just_dna_format.manifest import read_manifest

reference.authoring_reference()  # what `reference` prints, as a dict
manifest = read_manifest(module_dir / "manifest.json")
verify_manifest(module_dir, manifest, require_marketplace=False)  # raises IntegrityError
alleles.parsimony_reduce({"CAG", "C"})  # the indel reduction
derive_variant_key(rsid, chrom, start, ref, alts=None, build="GRCh38")
vocab.VALID_STATES  # every closed vocabulary, as a frozenset
```

Pass a row's own `build` to `derive_variant_key` whenever the module is not GRCh38 — the default
silently mints GRCh38 identity.

Row models live in `just_dna_format.spec` (`VariantRow`, `StudyRow`), `.pgx`, `.binning`, `.pgs`,
`.frequency`, `.literature`, `.sources`, `.resolution`. `just_dna_format.identity` is unrelated to
variant identity — it holds module naming, versions and canonical ids.
