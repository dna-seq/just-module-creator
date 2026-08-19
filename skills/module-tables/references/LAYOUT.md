# Where every file may sit — the spec tree, the artifact, and the registry's `derived/`

> **Not a per-table dossier.** The 24 files beside this one each describe *one table*. This one
> describes the **tree** they sit in: which names are recognised, which directory a file may arrive
> from, what is renamed on the way in, what is refused, and what a download hands back. Written
> 2026-08-20 against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4 / registry 0.18.2, from the code
> in `just_dna_format.layout`, `just_dna_registry.specfiles` and `just_dna_registry.client` — with
> one docstring in that last file deliberately **not** used as a source, for the reason in
> *Roadworks*, below.

## The one idea to hold

**The compiler reads one flat directory.** Authored tables, machine-written sidecars, `module_spec.yaml`
— all of it, side by side, no subdirectories. Every other layout you will meet is a *presentation* laid
over that flat truth and normalised away before anything is hashed.

So `derived/` is not a place a file lives. It is a place a file is **shown**.

## The four rosters, and what each one governs

Four constants decide four different questions. Confusing them is how a file gets silently dropped —
which has happened twice in released code, to `licensing.csv` and to `README.md`.

| Roster | Lives in | Governs |
|---|---|---|
| `_INPUT_FILES` (12 names) | `just_dna_compiler.compiler` | what is hashed into `manifest.inputs[]` and what `content_signature` reads: `module_spec.yaml` + the 11 authored table kinds |
| `RECOGNIZED_SPEC_FILES` | `just_dna_registry.specfiles` | what a **storage round-trip** carries. `revalidate` and `upgrade` rebuild a spec directory from this tuple, so a name missing here is a file lost on the next rebuild |
| `DERIVED_FILES` (9 names) | `just_dna_registry.specfiles` | what `download(layout="split")` moves into `derived/` |
| `SIGNATURE_INPUTS` | `just_dna_registry.specfiles` | the registry's mirror of `_INPUT_FILES` — **entirely root-level**, which is what makes `derived/` safe |

`RECOGNIZED_SPEC_FILES` is worth spelling out, because it is wider than most people guess and it is
the one that decides whether your file survives a re-publish:

```
module_spec.yaml        provenance.json        README.md        verification.json
+ every accepted spelling of every spec data file
  = variants.csv, studies.csv
  + the 9 table kinds (activity_phenotype, copynumbers, repeat_alleles, heteroplasmy,
    haplotypes, allele_function, diplotypes, pgs, pharm_variants)
  + the 7 fact tables (frequencies, gene_metrics, literature, sources.csv/licensing.csv,
    gene_validity, clinical_assertions, gwas_effects)
  + resolution.csv
```

**Two names in there deserve attention.**

**`provenance.json` is recognised, and no dossier here covers it.** Optional structured provenance
authored beside the spec — "shipped and hashed like a log, kept out of `artifact.digest`". It survives
a storage round-trip. It is deliberately *not* carried by `upgrade` the way `verification.json` is, on
upstream's own reasoning: provenance describes how the *predecessor* was built, whereas an attestation
is hash-bound to the authored bytes and invalidates itself if they move. If you author one, know that
nothing in this plugin writes or reads it.

**`logo.png` is NOT in `RECOGNIZED_SPEC_FILES`** — and it survives anyway, by a different mechanism.
`upgrade` carries it forward from `manifest.logo` (`upgrade.py:497-507`), described there as
"version-independent branding". So the logo is safe, but it is safe because the *manifest* names it,
not because the spec-file roster does. A file that is neither recognised nor manifest-named is
tolerated by the compiler and dropped by a rebuild.

## Going in: liberal in, strict out

`specfiles.plan_layout` normalises an uploaded tree from **names alone**, before anything is hashed.

**Recognised files are hoisted to the root from *any* subdirectory** — not only from `derived/`. The
docstring's reason is worth knowing: producers already ship `metadata/`, `enriched/` and `authored/`
trees, and accepting whichever arrived costs nothing, "while blessing a second name in this module
would make it a name we then have to keep."

**`logs/` is the one subtree never touched.** The compiler discovers `logs/**.log` and the manifest
records that path *verbatim*, so flattening one would rename a file the manifest attests. A top-level
`*.log` is equally discovered and equally left alone.

**Unrecognised files stay exactly where they are, at whatever depth.** The compiler tolerating unknown
files is a contract, and a rule invented at the registry for them would quietly break it.

### Renamed on the way in — two repairs pointing opposite ways

| Arrives as | Stored as | Why |
|---|---|---|
| `MODULE.md` | `README.md` | **the corpus lags us.** This project advised `MODULE.md` for two releases and `just-dna-pipelines`' `write_module_md` still emits it. Refusing it — or silently dropping the prose, which is what happened until registry 0.14 — would charge the author for our rename |
| `sources.csv` | `licensing.csv` | **the direction inverted at format 0.6.** A 0.6 compiler reads both, prefers `licensing.csv`, and warns that the old spelling is removed at 1.0. Left alone, every publish of a legacy spec would carry that deprecation into `manifest.compilation.warnings` forever |

That second map is **derived from `SIDECAR_SPELLINGS`, never written down** — upstream owns which
spellings exist and which are deprecated, and restating it is how the two halves got out of step in
the first place. When 1.0 removes `sources.csv`, nothing in the registry needs editing.

### Refusal versus warning — the line, and why it moved

Three outcomes, and they are graded deliberately: `notes` are accepted-and-noteworthy (the server
changed your spec and you should know), `warnings` cost nothing, `conflicts` are refusals.

**Refused — two paths claiming one root name.** `resolution.csv` beside `derived/resolution.csv` is a
question only the author can answer, and "picking one silently is how the wrong table gets published
under a signature that looks perfectly valid."

**Refused — both spellings of one sidecar.** `sources.csv` beside `licensing.csv`. This *used* to pass
with a warning; at 0.6 it became a refusal because `layout.resolve_sidecar` raises `SidecarCollision`,
so carrying the loser through would produce a `ValueError` out of the compiler with the registry's own
upload as its cause. The refusal names both paths so the author can act on it. Upstream's reasoning is
the reason to agree with it rather than route around it: **these tables are fact-hashed and
hand-editable, so two copies are two claims, and preferring either discards somebody's curation
silently.**

**Warned — `MODULE.md` beside `README.md`.** The legacy file is ignored and *carried unchanged*.
Still only a warning because "overwriting prose the author wrote with prose they did not is the single
most surprising thing this pass could do", and unlike a sidecar an extra markdown file makes the
compiler do nothing at all.

**Warned — a readme lookalike.** `readme`, `readme.md`, `readme.txt`, `readme.rst`, `readme.markdown`,
`module.markdown`. **Warned, never renamed**: `MODULE.md` is renamed because this project told authors
to write it, which makes that rename a repair of our own advice — guessing at `README.txt` would be
inventing intent, and "a rename this module does not have to keep is a rename it should not make." The
consequence is concrete and easy to miss: **the module card's `readme` stays empty.** Skipped entirely
once a real `README.md` is present. Fixable after publishing with `registry_amend_readme`, no version
spent.

## Coming out: what `derived/` actually is

`RegistryClient.download` serves three shapes, and `layout="split"` is the only place `derived/`
appears in the wild.

| Flags | You get | For |
|---|---|---|
| *(none)* | `manifest.json` + the parquets + `README.md` | installing and reading — the consumer's shape |
| `--with-inputs --layout flat` | the above **plus** every authored CSV and every attested sidecar, all at the root | re-authoring, diffing, auditing |
| `--with-inputs --layout split` | the same bytes, sidecars re-homed under `derived/` | keeping the authored half visually apart |
| `--tarball` | one server-built `.tar.gz`, flat, everything | archiving |

`DERIVED_FILES` — exactly what lands in the folder — is the seven fact CSVs **under their preferred
spelling**, plus `resolution.csv`, plus `verification.json`. That last one **joined at registry 0.17**,
once `manifest.derived` attested the file and a downloader therefore received it. The folder is created
only if something actually lands in it, so a module with no sidecars gets no empty directory.

### Five properties of the split, each of which someone has got wrong

1. **`manifest.derived[]` names bare filenames** — `resolution.csv`, never `derived/resolution.csv`.
   The manifest attests the *flat* tree.
2. **The split runs after verification**, not before. `split_derived` is presentation only: "the
   manifest names these files at the root, so a tree split before verification is a tree that fails to
   verify."
3. **Re-uploading the split tree is safe**, in the other direction — the server flattens it back. Which
   is why re-uploading either layout publishes the same module.
4. **Nothing in `derived/` can move `content_signature`.** `SIGNATURE_INPUTS` is entirely root-level, so
   the property is true by construction rather than by care. This is the stated reason to prefer a
   folder over any in-file provenance marker.
5. **`WHERE-THIS-CAME-FROM.md` is the client's own note to a reader, not part of the module.** It is
   deliberately not called `README.md` — `plan_layout` hoists a recognised spec file out of any
   subdirectory, so a readme written there would be lifted to the root on the next upload and would
   either overwrite the module's prose or collide with it. `RegistryClient` skips it on upload
   (`_SKIP_UPLOAD_NAMES`, beside `manifest.json`). **If you rebuild an upload by hand from a
   downloaded split tree, you must skip it yourself** — otherwise you publish the registry's
   explanation as if the author had written it.

`published.json` never arrives in any shape: it is this plugin's **local receipt** of a publish, never
uploaded and never part of the module.

## What the registry fills, and strips back out

You upload the **spec, not the parquets**. The server enriches, strict-compiles and stores the artifact
itself, which is why a published digest is trusted rather than claimed. It fills the identity fields a
module must not author — `namespace`, `owner`, `version`, `canonical_id`, `published_at`, `license` —
and strips them back out on download, so a module you pull down is republishable as itself.

`REQUIRED_SPEC_FILES` at the registry is **only `module_spec.yaml`**. Composition is deliberately the
compiler's judgement, not the registry's: "module has no recognized table" and "studies.csv is missing"
come back from `validate_spec` as proper findings in the compiler's own wording.

## 🚧 Roadworks — one docstring in the client contradicts the code beside it

`client.py::split_derived`'s closing paragraph says *"the derived CSVs are stored server-side but the
manifest attests none of them, so a downloader only receives what `artifact.files`/`inputs`/`logs`
list"*, and cites a `just-dna-format` suggestion entry that has since been answered. Forty lines below,
`RegistryClient.download` does `names += [e.name for e in manifest.derived or []]` and passes
`check_derived=True` to `verify_manifest`; `specfiles.py` attributes the change to 0.17 in two separate
comments; `ModuleManifest` carries `derived` among its 34 top-level fields.

**The code is right and the docstring is stale.** Do not design around that paragraph — a
`--with-inputs` download *does* return the sidecars. Filed as registry `S13` / our `F37`
(`docs/just-dna-format-pending-fixes.md`) on 2026-08-20.

## ⚠️ Check — the plugin's own sidecar roster is short

`list_tables().sidecars` returns a hardcoded four: `resolution.csv`, `frequencies.csv`,
`gene_metrics.csv`, `literature.csv`. It omits `licensing.csv`, the three format-0.6 fact tables
(`gene_validity.csv`, `clinical_assertions.csv`, `gwas_effects.csv`) and `verification.json`, all of
which `authoring_reference` does name. **Take the roster from `authoring_reference` or from this file,
not from that field.** Recorded in `docs/HANDOFF-skills-split.md`; it is our defect, not upstream's.

## Blanks for just-dna-lite

The read sites for the tree itself, rather than for any one table:

- **`derived/` is never read by a consumer** and does not need to be — `layout.sidecar_candidates`
  accepts a sidecar at the root or under the folder, so a consumer that reads the flat root reads
  everything. Nothing to do here; noted so nobody adds a folder walk.
- **`manifest.derived[]`** is the list to check before assuming a downloaded module carries its
  sidecars. A consumer that wants frequencies from a module published before registry 0.17 will not
  find them attested.
- **`logs/` paths are verbatim in the manifest.** A consumer that rewrites or relativises them breaks
  the attestation.
