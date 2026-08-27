---
name: module-compile
description: >-
  Build the artifact and read what the build actually says. Covers pre-flighting with the same
  strictness you will compile at, what `--strict` does and does not mean, the three signatures and
  five counters a successful compile reports, the one check that discards an authored row, the
  warnings that matter on a green run, the round trip and what it silently costs, and the flag that
  ships a module no VCF can match.
  Triggers: "compile", "validate", "strict", "artifact.digest", "content_signature",
  "verify_artifact", "sign", "why did my digest change", "manifest.json", "reverse", "round trip",
  "fully_resolved", "no-resolve", "reproducible".
---

# Stage 6 — compile, verify, sign

**Lifecycle stage:** 6. Offline from here on, provided `resolution.csv` and `literature.csv` exist.

This stage produces the parquet set and the manifest, reproducibly. It proves a module is
**well-formed and self-consistent**, and it says nothing whatever about whether the module is **true**.
Holding those two apart is most of what this skill is for.

## Pre-flight, then build

```
validate_module(spec_dir="spec", strict=True)
compile_module(spec_dir="spec", output_dir="out", strict=True)
verify_artifact(module_dir="out")
```

`validate_module` refuses everything `compile_module` refuses that does not need resolved rows, so a
green pre-flight should mean a green compile. **Pass it the same `strict` as the compile you intend to
run** — several checks are a ladder, so a mismatched pre-flight answers for the *other* compile.

What `validate` covers: `resolution.csv`, the fact sidecars, the licence gate, the stored `vrs_id`, the
p-value pair, and whether every genotype and `effect_allele` names an allele its locus actually has.
What appears only at compile is anything computed from **resolved** rows — the expansion and hosting
findings — because resolution has not run when `validate` does.

*(Two shapes broke that promise on format 0.6.0 — a module with `frequencies.csv`, and a table-only
module with `studies.csv`. Both fixed in 0.6.1, which is this plugin's floor.)*

## `--strict` means reproducible, never right

**The compiler never fetches, so it holds no reference sequence to check a coordinate against.** A
module shifted one base passes `validate`, passes `compile --strict`, reports `fully_resolved: true`,
and mints `ga4gh:VA.…` ids the compiler then reports **verified** — a content-addressed id is a correct
digest of whatever it is handed, so it certifies the wrong locus without hesitating.

**Author against `strict`, because that is what the registry runs.** The difference is not cosmetic:

| condition | plain | `strict` |
|---|---|---|
| genotype allele not among the locus's alleles | warning, **valid** | **error, invalid** |
| two-allele genotype on `MT` / `Y` | warning | warning |
| unresolved rows (no coordinate) | warning | counts against publishability |
| `effect_allele` not among the resolved alleles (RM91) | warning | **error** |
| `p_value` and `p_value_num` disagreeing past 1% | warning | **error** |
| a coordinate past its contig's end (RM48) | **error** | **error** |
| a stored `vrs_id` that does not recompute | **error** | **error** |

A plain compile **succeeds** through the first two. So *"it compiled"* is not evidence the module is
correct — a module can compile cleanly and contain rows that will never match a genome.

The last two rows are the shape worth internalising: **`--strict` is not the switch for arithmetic.** A
position that cannot exist on the declared build, or an id that disagrees with its own inputs, is wrong
in both modes because no judgement is involved.

## What a successful compile reports

Three signatures — `artifact_digest`, `content_signature`, `resolution_signature` — plus
`fully_resolved` and five counters. **Recompiling an untouched spec must reproduce all of them under
one compiler version.**

**Across a version boundary the rule is different**, and worth knowing before you panic:
`artifact_digest` is the **byte** identity and moves on a compiler upgrade by design, while
`content_signature` is the identity of your **authored rows** and does not. So compare
`content_signature` when you upgrade, and re-pin any stored `artifact_digest`. [`module-diff`](../module-diff/GUIDE.md) owns the
full decision tree over which of them moved.

**Read `resolution_subjects` beside `fully_resolved`.** Over an empty list that flag is `true`
vacuously — it is `all()` over nothing — so `fully_resolved: true` with `resolution_subjects: 0` says
the module resolved everything there was to resolve, which was nothing.

The other four are `positional_rows` / `positional_rows_placed` (how much of the PGx side actually
joins to a VCF; complete is `placed == rows`, and it is two numbers rather than a ratio on purpose)
and `expanded_keys` / `expanded_rows` (the one-to-many rsID expansion).

> **A null counter is not a zero.** `0` is a real answer and `None` means nothing counted. Never
> coalesce one into the other, and never read a null as a failure: an artifact that counted nothing is
> a normal artifact, and every pre-0.6 manifest honestly is one.

## Warnings are the interesting output on a green run

Several are **unclearable by any authored edit**, and chasing them is wasted work:

- **VRS coverage below 100%** on a structural or indel-heavy module. The message names what each
  remainder is blocked on. *Computable offline* means the mint pass has not run; *indel/MNV* means
  re-run it **without** `--offline`; a build with no refget table means nothing can be done today.
- **`not_covered` frequencies** — the source cannot cover that locus at all (the Y PAR). An absence
  nobody established is not a finding, and it is distinct from `not_found`, which is an ordinary miss.
- **A skipped positional fill** on a non-GRCh38 module (RM15) — it says so on its own line.
- **`This module records no closure`** — a true statement about a module still being written. Do not
  run `close_module` to clear it. [`module-close`](../module-close/GUIDE.md) owns why.

**A warning count moved in compiler 0.6.6, and no text did.** The `faf95` arithmetic warning was
published **twice** into `manifest.compilation.warnings` — the check runs in `validate_spec` and again
on the compile side, and only the compile side lacked the dedup filter its neighbour carries. Fixed
(upstream **RM106**), measured at 15 warnings and 14 distinct beforehand. A recompile under 0.6.6
publishes one fewer warning on such a module; if something of yours pins a count, that is why.

**A wall of near-identical warnings should not happen** — findings aggregate per gene with a count and
examples. If you see one, that is a bug worth reporting upstream rather than filtering.

### The one check that discards an authored row

A **lengthless symbolic allele** is dropped rather than compiled, and the warning says **DROPPED** for a
reason: `reverse` cannot re-emit what never reached the parquet, so the row is gone from the round trip
as well as from the artifact. Symbolic and structural alleles (`<DEL>`, repeat notations, ClinPGx
`del`/`ins`, CPIC's `x≥3`) are outside the `^[ACGT]+$` grammar — upstream **RM5**, known and deliberate.
Leave the row out honestly rather than approximating it into nucleotides.

## The two traps that ship a module no VCF can match

**`compile_module(resolve_with_ensembl=False)` / `--no-resolve` disables `resolution.csv` too.** The
name reads as *"don't use Ensembl"*, which is exactly what a spec carrying its own resolution wants. It
is the master switch for **all** resolution: set it false and every row compiles with `chrom=None`, and
the compile **succeeds** — it warns, but a script checking only the exit status ships a module that can
never match a genome. The correct call is `resolve_with_ensembl=True, ensembl_cache=None`. **The MCP
`compile_module` tool pins that and cannot reach the other branch; the CLI can.**

**Deleting `resolution.csv` is part of a rebuild.** Existing rows are authoritative and merged, so a fix
that changes an authored allele will not show up until you delete the file first. The table is a pin,
not a cache. [`module-refresh`](../module-refresh/GUIDE.md) owns what deleting each sidecar costs.

## The round trip, and what it silently costs

If you changed the schema rather than the data, prove the fixed point:

```
reverse_module(parquet_dir="out", output_dir="rev")
module_signature("spec")  and  module_signature("rev")   # must match
```

That is the guarantee the format makes, and it holds wherever you wrote a value: `curator` and `method`
can live on the row or in `defaults:`, and `reverse` re-emits them in the other place, because the
signature folds `defaults:` into each row before hashing.

🚧 **ROADWORKS — a reverse costs you the VRS ids while every identity check calls the round trip
lossless.** `reverse_module` writes eleven columns of `resolution.csv` and drops seven, including
`vrs_id`, `vrs_spec` and `caid`. Because none of them is in `RESOLUTION_FACT_FIELDS`,
`compile → reverse → compile` reproduces `content_signature`, `resolution_signature` **and**
`artifact.digest` exactly — so nothing tells you. **Guard:** keep the authored `resolution.csv` in
version control, and re-mint before publishing anything built from a reverse. **`reverse` is a fixed
point, not a backup** — it also cannot restore `authorship`, the verification record or the closure.
**The module in your repository is the source of truth.**

## Check what you actually shipped

```bash
uv run python -c "
import polars as pl; w = pl.read_parquet('out/weights.parquet')
print(w.height, 'rows;', w.filter(pl.col('chrom').is_not_null()).height, 'with a coordinate')"
```

`0 with a coordinate` means resolution did not reach the compile — one of the two traps above.

**Signing is CLI-only** (`just-dna-compiler keygen` / `sign`, and `close --private-key`). `keygen`
writes an unencrypted PKCS#8 key: it bootstraps a key, it is not a key-management system. **This server
deliberately takes no private key** — a key that reaches a tool argument has been logged.

⚠️ **CHECK — a bare `just-dna-compiler verify` rejects every locally-compiled module**, ours included,
because `--require-marketplace` defaults on and the reference compiler leaves `compiled_by` null by
design. That is the registry's policy rather than a verdict on your artifact. The guarantee that is
actually load-bearing is the pinned `--public-key`.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** dropping `resolve_with_ensembl=False`; deleting `resolution.csv` before a
rebuild that changed an authored identity; re-minting ids after a reverse; matching the pre-flight's
strictness to the compile you intend to run.

**Surface it, and let a pilot settle it:**

- **Whether a warning is acceptable.** Nothing escalates for you below `--strict`, and several warnings
  are permanent properties of an honest module.
- **Whether to drop a row the grammar cannot express.** Approximating a symbolic allele into
  nucleotides asserts something the source did not.
- **Whether a moved digest matters.** A digest move with every signature still is by construction
  something you did — [`module-diff`](../module-diff/GUIDE.md) names the three routes.

## What this stage cannot do

**It cannot tell you the module is correct.** No reference, no network, no opinion on whether your
coordinates name the variant you meant.

**It cannot fetch anything.** The compiler is inject-only: it consumes the `resolution.csv` the
enricher produced and will not look a coordinate up for you.

**It cannot compare two versions.** No diff, no parent digest, no monotonic stats anywhere in the
artifact. [`module-diff`](../module-diff/GUIDE.md) owns what *can* be read off the signatures.

**It cannot stamp a closure.** `validate_module` stays read-only however cleanly it passes, and that is
deliberate — [`module-close`](../module-close/GUIDE.md).

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action. The ones that
land here:

- *"validate says valid and compile then refuses"* — check the modes first; a bare `validate` is a
  pre-flight for the *other* compile.
- *"stored vrs_id … does not match the id recomputed from …"* — an error in **both** modes, and
  nothing to decide: the stored id is wrong.
- *"vrs_id … could not be verified"* — nothing was compared, so no verdict was reached. Your module is
  fine.
- *"overlapping bins"* / *"bins with the same lower bound"* — errors; check the group key first.
- *"inconsistent reference allele"* — two rows share a key and disagree about `ref`. Exactly one can be
  right.
- *"--no-resolve switches off resolution entirely"* — the trap above. Drop the flag.

## Where to go next

| You need | Load |
|---|---|
| which signature moved and what it means | [`module-diff`](../module-diff/GUIDE.md) |
| to declare the authoring finished | [`module-close`](../module-close/GUIDE.md) |
| to re-derive a sidecar before rebuilding | [`module-refresh`](../module-refresh/GUIDE.md) |
| the coordinates to be right in the first place | [`module-enrich`](../module-enrich/GUIDE.md) |
| what a consumer will do with the artifact | [`module-consumer`](../module-consumer/GUIDE.md) |
| the full CLI surface, and what is not wrapped | `../module-101/references/CLI.md` |
