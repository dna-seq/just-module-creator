# Where every file may sit — the spec tree, the artifact, and the registry's `derived/`

> **Not a per-table dossier.** The 24 files beside this one each describe *one table*. This one
> describes the **tree** they sit in: which names are recognised, which directory a file may arrive
> from, what is renamed on the way in, what is refused, and what a download hands back. Written
> 2026-08-20 against format 0.6.1 / compiler 0.6.1 / enricher 0.6.4 / registry 0.18.2, from the code
> in `just_dna_format.layout`, `just_dna_registry.specfiles` and `just_dna_registry.client` — with
> one docstring in that last file deliberately **not** used as a source, for the reason in
> *Roadworks*, below.
>
> **Re-measured 2026-09-13 against the installed packages — format/compiler 0.7.0, registry 0.25.2 —
> and the five roster sizes below are that measurement, not the 0.6.1 one this header opens with.**
> Three of the five moved between registry 0.25.0 and 0.25.2, a patch release, so run the snippet
> rather than reading the numbers. The prose around them is still 0.6.1-era and was not re-argued
> sentence by sentence.

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
| `_INPUT_FILES` | `just_dna_compiler.compiler` | what is hashed into `manifest.inputs[]` and what `content_signature` reads: `module_spec.yaml` + the authored table kinds |
| `RECOGNIZED_SPEC_FILES` | `just_dna_registry.specfiles` | what a **storage round-trip** carries. `revalidate` and `upgrade` rebuild a spec directory from this tuple, so a name missing here is a file lost on the next rebuild |
| `DERIVED_FILES` | `just_dna_registry.specfiles` | what `download(layout="split")` moves into `derived/` |
| `SIGNATURE_INPUTS` | `just_dna_registry.specfiles` | the registry's mirror of `_INPUT_FILES` — **entirely root-level**, which is what makes `derived/` safe |

**Run the call rather than reading a number off this page**, because two packages on two release
cadences fill these and a size written here is stale by construction:

```
uv run python -c "
from just_dna_compiler import compiler
from just_dna_registry import specfiles as S
print('_INPUT_FILES        ', len(compiler._INPUT_FILES))
for n in ('RECOGNIZED_SPEC_FILES', 'DERIVED_FILES', 'SIGNATURE_INPUTS', 'FACT_CSVS'):
    print(f'{n:20}', len(getattr(S, n)))"
```

Measured 2026-09-13 against the installed packages (format/compiler 0.7.0, registry 0.25.2):
`_INPUT_FILES` 13, `RECOGNIZED_SPEC_FILES` 28, `DERIVED_FILES` 12, `SIGNATURE_INPUTS` 13,
`FACT_CSVS` 10. **Three of those five moved between registry 0.25.0 and 0.25.2** — a patch
release — which is the whole argument for running the snippet rather than reading these numbers. The shape of `RECOGNIZED_SPEC_FILES` is worth knowing even though its size is not,
because it is wider than most people guess and it is the one that decides whether your file survives
a re-publish: `module_spec.yaml`, `provenance.json`, `README.md`, `verification.json`, then every
accepted spelling of every spec data file — `variants.csv` and `studies.csv`, the authored table
kinds, `overrides.csv`, the fact tables including both spellings of `sources.csv`/`licensing.csv`,
and `resolution.csv`.

**Three files joined the rosters in 0.7 and one did not, which is the thing to check.**
`overrides.csv` reached `RECOGNIZED_SPEC_FILES` **and** `SIGNATURE_INPUTS` — authored input, so its
`value` cells move `content_signature` ([`overrides.md`](overrides.md)) — and
`clin_sig_concordance.csv` and `clin_sig_authority_calls.csv` reached the derived rosters
([`clin_sig_concordance.md`](clin_sig_concordance.md)). All three arrived in registry 0.25.0, which
was our `S19`.

> ✅ **CLOSED 2026-09-11 — `expression_effects.csv` was in the compiler's rosters and in none of the
> registry's, and the registry's caught up the same afternoon.** Its parquet is in
> `ARTIFACT_PARQUETS` (**23** on this install, not the 22 `INTEGRATION_0_7.md` § 2.2 states — the
> AlphaGenome round landed after that count was taken) and
> the CSV is in `hints.DERIVED_TABLE_MODELS`. For one afternoon it was in none of
> `RECOGNIZED_SPEC_FILES`, `DERIVED_FILES` or `FACT_CSVS`, which meant **a server-side rebuild
> dropped it** — the `licensing.csv`-before-registry-0.16.2 failure exactly: not refused, dropped,
> and the only symptom a module that quietly stops carrying a table it compiled with. Filed as
> registry-tree `S22` on 2026-09-11
> and **answered and closed the same day**: it is a fact table (the compiler's `_FACT_TABLES`, beside
> the two concordance tables), it is absent from `_INPUT_FILES` so a drop never moves
> `content_signature`, and the registry then carried the name into all three rosters within the hour.
> **So a publish no longer drops it, and the remaining limit is a different one**: its producer is the
> enricher's `expression` pass, gated on an AlphaGenome Atlas credential and a declared licence use,
> and nothing here wraps it. `refresh_sidecar` refuses the table with that sentence rather than
> deleting bytes it could not re-derive.
> **Guard, narrowed:** the table is fine to carry and fine to publish; do not expect `refresh_sidecar`
> to rebuild it, and run `just-dna-enricher expression` on a machine holding the credential instead.

**One transient directory is new and is not a roster member.** `enrich` stages its raw answers in
`.<name>.staging/` (format `RM128`) and removes it on a successful commit unless `--keep-staging`.
**A killed run leaves it either way, and the next run resumes from it** — so finding one is not
damage to clean up, it is work in progress. It is not a recognised spec file and must never be
treated as one.

**Two names in there deserve attention.**

**`provenance.json` is recognised, and this plugin now writes it.** Optional structured provenance
beside the spec — "shipped and hashed like a log, kept out of `artifact.digest`", so it costs no
identity. It survives a storage round-trip. It is deliberately *not* carried by `upgrade` the way
`verification.json` is, on upstream's own reasoning: provenance describes how the *predecessor* was
built, whereas an attestation is hash-bound to the authored bytes and invalidates itself if they move.

**`record_override` writes one item per `(variant_key, field)`** recording why an authored value
outranks a source, and `review_queue` reads them back — `module-revise` owns the queue. An item that is
**not** ours is kept and reported, never rewritten. Nothing upstream reads any field of an item:
`_collect_provenance` validates, copies, hashes and takes `len(doc.items)`.

**`logo.png` is NOT in `RECOGNIZED_SPEC_FILES`** — and it survives anyway, by a different mechanism.
`upgrade` carries it forward from `manifest.logo` (`upgrade.py`), described there as
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

`DERIVED_FILES` — exactly what lands in the folder — is the ten `FACT_CSVS` **under their preferred
spelling** (so `licensing.csv`, never `sources.csv`), plus `resolution.csv`, plus `verification.json`. That last one **joined at registry 0.17**,
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

**`verification.json` is also *projected*, not merely carried.** The registry's module-detail response
renders `manifest.verification` as a `VerificationInfo` block — `closed`, `closed_at`, `closed_by`,
`producer`, `produced_at`, plus a per-check list of `check`/`subjects`/`findings`/`skipped` — built from
the **latest** version's manifest (per-version access is the `…/manifest` route). It reads the manifest
and never the file, and since the registry compiles the spec itself that `closed: true` was **re-bound
by their compiler against the authored bytes** and dropped if it did not match. So it is hash-checked
rather than asserted — and still not a registry verdict about your checks, which they deliberately will
not read as one. Not a card facet, not a filter, not sortable, and `None` is **not** collapsed with an
empty block: absent means no attestation survived, which is a different statement from an attestation
that recorded no checks.

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

## The sidecar roster is derived now, so ask for it

`list_tables().sidecars` was a hardcoded four until 2026-08-20 (RM10) and is now derived from
`just_dna_registry.specfiles.FACT_CSVS + RESOLUTION_CSV` minus what is authorable — so a fact table
added upstream appears with no edit here. It answered seven on registry 0.18.2 and answers ten on
0.25.0, which is the point of deriving it: **ask the tool for the count, and if a number matters to
you, read it off the call.** `licensing.csv` is absent from it *by
derivation* rather than by exception: it is both produced and authorable, so it belongs to
`describe_table`.

**Note the roster now comes from a different package than the loader it describes**, so a registry
release lagging a compiler release makes the answer lag. A pinning test is the guard, not a version
floor.

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
