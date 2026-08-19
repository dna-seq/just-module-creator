# Design study — comparing two versions of a module

**Status:** design study, 2026-08-20. Nothing here is implemented. It specifies the `module_diff`
entry sitting in `ROADMAP.md`'s idea book, and it is written to be implementable without a second
round of measurement.

**Measured against** format 0.6.1 / compiler 0.6.1 / enricher 0.6.4 / registry client 0.18.2, with
production serving `{"api":"v1","registry":"0.18.2","format":"0.6.1","compiler":"0.6.1","mode":"prod"}`.
Every number below names the command that produced it in §5. Re-run them rather than trusting the
number; the counted claims in this ecosystem's prose have gone stale repeatedly and these will too.

---

## 1. The recommendation

**Build it, as one comparator over two local spec directories plus one cheap companion that compares a
local spec against a published manifest.** The comparison itself is a pure function of two directories
and needs no network, no compile and no upstream *symbol* that is private — and a working prototype over
the whole reference corpus and the whole published corpus runs in under a fifth of a second per module
pair. One piece of *logic* is restated rather than imported and that is the honest exception: the RM37
`defaults:` fold, filed as format-tree `S53` the moment it was found, with the guard that pins it and the
proposed fix that would delete it in §5.

**The output must be a three-level ladder — signature, table, row-with-column-set — and never a cell
dump.** One number says whether the content moved at all; the table level says where; the row level
groups changed rows by *the set of columns that changed* and reports a count plus a couple of
exemplars. On the largest table in the reference corpus that turns 400 changed rows into two lines, and
on the only real published version chain it turns 990 changed rows into one line that is *more accurate
than the changelog the publisher wrote*.

**The strongest argument for building is that the corpus already contains a change nobody recorded.**
`antonkulaga/big_five_personality_snps` has four published versions. The prototype found that 1.0.1
rewrote `state` on all 990 variant rows while its changelog names three other columns, and that 2.0.0
silently reverted that rewrite while its changelog says only "variant set unchanged from 1.0.0". Both
facts are true, neither is written down anywhere, and both fall out of one command. That is the gap
`MODULE_LIFECYCLE.md` §7 names, and it is an authoring-workflow gap, which by CLAUDE.md §11 is ours to
build first and offer upstream second.

Two consequences to schedule with the build rather than after it. **`skills/module-diff/SKILL.md` says
plainly that no tool does this** — in its "what exactly changed" table and again under "what this stage
cannot do" — and both change in the same commit as the tool, because a skill's claim about a refusal is
part of the contract. And once it runs it is worth offering to the format tree: their §7 names the
absence, `RM83`'s refresh item sits next to it, and a proposal with a running tool attached costs them
nothing to decline.

---

## 2. The tool surface

### 2.1 `compare_modules` — essentials

```python
async def compare_modules(
    left_dir: str,
    right_dir: str,
    detail: Literal["signatures", "tables", "rows"] = "rows",
    max_groups: int = 12,
    examples_per_group: int = 2,
) -> ModuleComparison
```

**Tier: essentials.** CLAUDE.md's line is cost, not usefulness, and the cost here is bounded by the two
directories the caller named — the same shape as `module_signature` and `compile_module`, both
essentials. Measured: the largest reference example (`cyp2c19_star_alleles`, 1,190 + 106 + 36 + 1
authored rows) compares against a mutated copy of itself in **0.18 s**, and against an identical copy in
0.17 s, so the floor is parsing rather than diffing. No network, no compile, no parquet. Nothing about
this is corpus-sized: there is no citation graph, no whole-source draft and no pass over every row of
somebody else's artifact.

It is also the tool the taught workflow needs. `module-diff`'s standing advice — download both
versions, diff the CSVs — is a two-command recipe that an author in a chat session cannot act on
without shelling out, and `test_the_taught_workflow_runs_in_the_default_tier` exists because a tier
that teaches a step it cannot run is the failure mode to watch.

### 2.2 `compare_to_published` — essentials

```python
async def compare_to_published(
    spec_dir: str,
    namespace: str | None = None,
    name: str | None = None,
    version: str = "latest",
    target: RegistryTarget = "prod",
) -> PublishedComparison
```

Answers *"am I ahead of the catalog, and how?"* with **one or two bounded GETs and no download**
(`resolve_version` when `version="latest"`, then the manifest). `namespace` and
`name` default from `module_spec.yaml`'s `module:` block. It reads the published version's manifest and
compares three things it can get for free:

1. `content_signature` — the exact content verdict.
2. Per-authored-file byte identity, by recomputing `compiler.file_entries(spec_dir, names)` against
   `manifest.inputs`. Measured to reproduce the published entries byte for byte on two versions.
3. Each fact-signature block, and the metadata the manifest carries outside every hash: `readme`,
   `verification.closure`, `compiler_version`.

**The byte layer is subordinate to the signature layer and must be labelled that way.** Byte equality is
decisive — an identical hash means an identical file. Byte *inequality* means almost nothing on its own:
a CRLF difference, a reordered column, a `1.00` written as `1.0` and a reordered row all move the file
hash and leave `content_signature` exactly where it was, all four measured (§5). So the report reads
`content_signature` first and uses the per-file hashes only to say *which files to look at*, never to
claim a content change.

**Tier: essentials**, because reading one named published record over the network is already essentials
— `registry_get_module` and `registry_is_published` both live in `tools/research.py`, whose opening line
is "ESSENTIALS (network, read-only)". This is the same bounded read.

**It ends by handing over rather than escalating.** Row detail needs the published version's authored
inputs on disk, which is `registry_download`'s cost and is deliberately extended, so the result names
the exact `registry_download` + `compare_modules` pair that gets it. It never downloads on its own.

`registry_is_published` should be called first and often makes this unnecessary: it already answers
"is my exact content published, under any name". Verified — `lookup_by_signature` on a local copy of
2.1.0 returns `antonkulaga/big_five_personality_snps@2.1.0`, and on `hfe_hemochromatosis` returns
nothing.

**Build `compare_modules` first.** It is useful alone; `compare_to_published` without it is a signature
comparison with no way to look inside.

### 2.3 The return model

Every verdict is a three-state string, never a bool. `same` / `moved` / `unknown`, and `unknown` is
never rendered as either of the others.

```
ModuleComparison
  left, right          : ComparedSide
  frame                : FrameVerdict          # the declared-build comparison. Top of the output.
  content              : SignatureVerdict      # content_signature both sides + same|moved
  tables               : list[TableComparison]  # authored tables
  derived              : list[DerivedComparison]
  metadata             : list[MetadataDelta]   # what changed outside every hash
  unknown              : list[Unknown]         # what could not be compared, and why
  note                 : str

ComparedSide           path or canonical_id; declared genome_build; compiler_version when a manifest
                       is in hand; which sidecar spelling this side uses

FrameVerdict           left_build, right_build, verdict. When the builds differ this is the whole
                       answer and the row counts below are not a reassurance — see §3.7.

TableComparison        csv (preferred spelling), spelling_left, spelling_right,
                       identity_scope: "content_signature" | "sources.signature",
                       presence: "both" | "left_only" | "right_only" | "unknown",
                       rows_left, rows_right   : int | None
                       unchanged, added, removed: int | None
                       row_key: "keyed" | "unkeyed",
                       key_collisions: int,
                       changed: list[ChangeGroup]

ChangeGroup            columns: list[str] (sorted), rows: int, examples: list[RowExample]
RowExample             key: the natural key, cells: {column: (left, right)} with values truncated

DerivedComparison      csv, verdict, left_signature, right_signature,
                       signature_source: "recomputed" | "manifest" | "unavailable",
                       and, only when both files are readable, the same
                       unchanged/added/removed/changed shape projected onto that table's fact fields

MetadataDelta          what: "module_spec.yaml:<key>" | "readme" | "closure" | "compiler_version",
                       left, right, and in_hash: false — the field exists to say
                       "this moved and no identity records it"

Unknown                subject, reason. One reason per absence, never a silent omission.
```

Every field answers a question an author actually asks:

| Field | The question |
|---|---|
| `frame` | do the two sides even mean coordinates in the same assembly |
| `content` | did anything an author typed change, at all |
| `tables[].identity_scope` | which hash will move when I publish this |
| `tables[].presence` | is this table new, gone, or unreadable |
| `tables[].changed[].columns` | what kind of edit was this — one column across many rows, or many columns on one row |
| `tables[].row_key` | can this table's rows be paired at all |
| `derived[].verdict` | did a source revise an answer under me (the canary) |
| `metadata[]` | what moved that no hash will tell me about |
| `unknown[]` | what this report is *not* telling me |

---

## 3. The seven tensions

### 3.1 What is "a change"? — a ladder, not a choice of grain

**Decision: all three grains, always, in one report, with the row level aggregated by changed-column
set.** `detail` exists only as a ceiling for a caller who wants less, and its default is the deepest
level. Grain does not depend on module size and it does not depend on the table.

The reason a cell diff on 1,190 diplotype rows is noise is not that there are 1,190 rows. It is that
1,190 rows changing *in the same column for the same reason* is one fact printed 1,190 times. Group by
the frozenset of columns that differ and the noise disappears without discarding anything:

- `cyp2c19_star_alleles` diplotypes, 400 rows edited and seven of those in a second column as well →
  **two** grouped lines, plus one added and one removed row.
- `big_five_personality_snps` 2.0.0 → 2.1.0, 990 variant rows → **one** line: `660 rows changed in
  ['weight']`, and 330 unchanged. The 330 are the reference genotypes whose weight is zero, which the
  grouping surfaces for free.
- 1.0.0 → 1.0.1, 990 rows → **one** line: `990 rows changed in ['state']`.

That last line is the whole argument. The published changelog for 1.0.1 says it "back-populated the 0.3
axes (direction/stat_significance/clin_sig) for 990 variant row(s)". Measured against both versions'
authored inputs, `direction` and `stat_significance` were already authored in 1.0.0 and did not move,
`clin_sig` arrived as an empty column, and the one column that changed is `state`, from
330 `ref` / 660 `significant` to 990 `neutral`. It is documented behaviour — `VariantRow.upgraded()`
trims `state` to a mirror of `direction` and `trimmed_state("unknown")` is `"neutral"` — but no record
of this module says it happened. The aggregated row level found it in one line.

**Rejected: a caller-chosen grain, defaulting to signature-level.** It puts the decision on the person
who does not yet know what moved, which is the only reason they called. And a signature-level default
would have reported "content_signature moved" for 1.0.0 → 1.0.1 and stopped, which is what the module
already knows.

**Rejected: an unaggregated cell diff.** It is what `diff` already does, worse. If somebody wants the
raw cells they should run `diff`, and the report should say so.

**Rejected: making the grain depend on row count.** Then the tool's answer changes shape as a module
grows, and two versions of one module can be compared with different rules. The grouping already makes
size irrelevant: a two-row module produces two lines and a 1,190-row module produces two lines.

### 3.2 Which two things — two tools, not three, and one of them is nearly free

**Decision: local-vs-local is the comparator; local-vs-published is a separate, manifest-only tool;
published-vs-published is the first tool applied to two downloads.** The three questions are one
comparison and three *acquisitions*, and acquisition is where the cost differs, so that is where the
split belongs.

Concretely, published-vs-published is:

```
registry_download(ns, name, v1, dest1)   # extended; our wrapper already defaults include_inputs true
registry_download(ns, name, v2, dest2)
compare_modules(dest1, dest2)            # essentials
```

which is the recipe `module-diff` already teaches, with the third step no longer being `diff`.

**And on registry 0.19.0 the signature half of that stops needing any download.** `S14`, filed while
measuring this and answered the same day, put `content_signature` on every version row and populated
`resolution.signature` there. So `client.versions(ns, name)` becomes one call that yields the whole
chain's content and resolution identities, and the four-manifest walk §5 measured is only needed against
a 0.18 server. **0.19.0 is in their tree and not on PyPI — our installed client is 0.18.2 and
`VersionSummary` has no `content_signature` field on it — so the implementation needs both paths**: read
the field when the server sends it, and fall back to per-version manifests when it does not. An absent
field there is `unknown` (an old server), never a null identity.

**Local-vs-published deserves its own tool because it is not a diff.** The useful answer needs no
second directory: `content_signature` gives the verdict, `manifest.inputs` gives per-file byte
identity, and the fact blocks give the derived verdicts. One GET. Forcing it through the two-directory
comparator would mean downloading a whole artifact to answer a question the manifest already answers,
which is the shape of an unnecessary extended-tier call.

**Rejected: one tool with a `mode` parameter and optional network arguments.** The signature would
carry two mutually exclusive halves (`right_dir` xor `namespace`+`name`+`version`), which is the
argument shape `registry_is_published` already had to guard against by refusing both at once. Two
tools with one job each are cheaper to describe and cheaper to tier.

**Rejected: a tool that downloads on its own when the right side is a version string.** It would put an
extended-tier cost behind an essentials-tier signature. Naming the download in the result is the
honest version of the same convenience.

### 3.3 Authored versus derived — two ladders, and the line is not where it looks

**Decision: the authored tables and the derived sidecars get two parallel sections with different
verdict vocabularies, and the report never merges them into one count.** The authored section answers
"did somebody edit this module". The derived section answers "did a source say something different".
They are different questions with different actors.

Three measured corrections to the naive reading:

**The authored/derived split is not the same as the content_signature boundary.** `licensing.csv` (and
its deprecated spelling `sources.csv`) is hand-authored, is in `draft.DRAFTABLE`, and is **outside
`content_signature`** — the compiler's table roster does not include it, so a licence edit moves
`sources.signature` and leaves `content_signature` byte for byte identical. Measured on
`hfe_hemochromatosis`: editing a `notice` cell left `content_signature` at `sha256:44ad4449…` and moved
`source_signature` from `sha256:0afb6361…` to `sha256:f63f2881…`. So every authored table in the report
must carry `identity_scope`, or an author will conclude their licence edit is invisible to the registry.

**A fact signature is recomputable, not merely quotable.** `integrity.fact_signature` with the matching
`*_FACT_FIELDS` set, run over the sidecars in a downloaded published module, reproduces that version's
manifest signatures exactly — `sha256:4d47d18f…` for resolution, `sha256:e7712321…` for literature,
`sha256:0d07f74b…` for sources, on all three versions that ship their sidecars. So the derived section
can compare two directories with no manifest, and can cross-check a manifest it does have.

**Provenance noise is excluded by construction, not by our filtering.** The whole point of the fact-field
sets is that `fetched_at`, `source` and `status` are not in them. A fresh `fetched_at` moves the file's
bytes and moves no fact signature. So the derived section reports fact-level verdicts and, when it
reports row detail, projects rows onto the fact fields before comparing. It never diffs the whole
derived row, which is where the meaningless differences live.

**Rejected: diffing only the authored tables, as `module-diff` currently advises.** That is right for
change *detection* and it throws away the canary. The canary is the only signal in this format that the
world moved rather than the author, and it lives entirely in the derived side.

**Rejected: one merged "rows changed" total.** A single number cannot distinguish an edit from an
upstream revision, which is the one distinction the identity ledger was built to preserve — and it is the
distinction that decides whether the author or the world moved.

**Boundary with `refresh_sidecar`, which landed while this was being written.** A comparator compares
two states that already exist. It never deletes a sidecar and never re-derives one, so it can never
*perform* the canary: `refresh_sidecar` owns that — it captures the file outside the spec directory,
deletes, re-derives, classifies every row, reapplies the provable set and reports `signature_moved` as
the canary. **So the classification of a refreshed row belongs to that tool and this one must not
restate it.** What the comparator adds is the case refresh cannot serve: two states that were never
produced by one refresh run — two versions, or a local spec against the catalog — where there is no
capture and no fresh derivation, only two recorded files. Where both tools could answer, the caller
should be sent to `refresh_sidecar`, because it is the one that knows which side it just derived.

### 3.4 Row order — reported as an artifact fact, never as a content change

**Decision: the report carries no row-order section at all, and the digest is not compared unless both
sides supply a manifest.** Re-measured, not inherited: reversing `variants.csv` on
`hfe_hemochromatosis` and recompiling leaves `content_signature` at `sha256:44ad4449…` on both sides and
moves `artifact.digest` from `sha256:6c6e103d…` to `sha256:83635ace…`. The prototype comparator reports
zero changed rows in every table, which is correct.

So a reordering is *not* a content change, and the tool's job is not to hide it either. The place it
belongs is the `metadata` list, as `artifact.digest` with `in_hash: false` beside a note that a digest
move with every signature still is an act of the holder — and there are three routes to it, reordering
included. The comparator cannot tell which route, and must not guess.

**A digest comparison across different `compiler_version`s is refused rather than reported.**
`big_five_personality_snps` 1.0.0 was compiled by `just-dna-compiler 0.5.4` and every later version by
0.6.1, so its digest difference from 1.0.1 carries a toolchain change and cannot be read. Parquet is not
byte-deterministic across arrow versions; that is why reproducibility is scoped to a fixed compiler
version. The report states the two compiler versions and declines the comparison, rather than printing
two hashes that differ for a reason nobody asked about.

**Rejected: a "rows reordered" verdict computed by comparing the two row sequences.** It is computable
and it is a trap: authored row order is preserved into the parquet, so it is real, but reporting it
beside content changes invites reading it as one. And the one thing an author needs to know — whether
the reorder was intended — is not knowable here.

### 3.5 Float comparison — the premise was wrong, and the correct rule is stricter

**Measured: nothing in a compiled module is float32.** Every float column in every parquet the compiler
wrote for `hfe_hemochromatosis` is `Float64` — `weights.parquet` (`weight`, `effect_size`,
`min_quality`), `studies.parquet` (`effect_size`, `p_value_num`, `neg_log10_p`) and
`gwas_effects.parquet` (`effect_size`, `standard_error`, `risk_allele_frequency`, `p_value_num`).

float32 in this ecosystem is a **consumer-side join concern and not a storage format**. `binning.py`'s
comment on `measure_max` says why: VCF 4.4 §1.3 makes every `Float` in a VCF a 32-bit value, so a
measured `0.3` arrives above an authored `0.3` and a measured `0.9` below it, and the repair is to
narrow the authored bound the same way the measurement was narrowed. That is a rule about comparing a
module's bound against somebody's genotype file. It has nothing to do with comparing two versions of the
module, and importing it here would be borrowing a hazard from the wrong side of the seam.

**Decision: compare the parsed pydantic models' `model_dump(mode="json")`, never the CSV text and never
the parquet.** No epsilon, no rounding, no tolerance. The reasons compound:

- It is the same normalization `integrity.content_signature` applies, so the row level cannot contradict
  the signature level. A comparator that disagreed with the hash the registry deduplicates on would be
  worse than no comparator.
- It makes formatting differences invisible for free. Measured on the 990 authored `weight` cells of
  `big_five_personality_snps@2.1.0` — the only weight-bearing corpus there is — by rewriting every one
  of them four ways (trailing zeros, a leading `+`, `%.12e` scientific notation, and a `repr(float(…))`
  round trip). `content_signature` stays at `sha256:657aa303…` through all four, and the comparator
  reports 990 rows unchanged each time.
- An epsilon would be a guess about magnitude in a place where the representation is exact, which is the
  argument upstream already made against an epsilon for bin bounds.

**The honest limitation, measured rather than assumed:** multiplying those same 990 cells by
`1 + 2⁻⁵²` moves `content_signature` to `sha256:9022cd15…` and the comparator reports `660 rows changed
in ['weight']` — 660 rather than 990 because the 330 zeros are unmoved by the multiplication. So one
unit in the last place *is* a change, in both the hash and the report, and the two agree. If a module's
weights are recomputed by a marginally different pipeline the report will say so, and the author is the
only one who can say whether it matters. That is the same 660 the real 2.0.0 → 2.1.0 recomputation
produces, which is a coincidence of this module's shape (330 reference genotypes carry weight zero) and
worth knowing so it is not mistaken for a signature of anything.

**Rejected: comparing the compiled parquets.** Both sides then need a compile, the floats arrive after a
round trip through a writer, and the comparison is against derived data rather than against what
somebody typed.

### 3.6 Report, never repair — the eight refusals, with their reasons, are §4

Summarised there rather than split across two sections. The load-bearing one for this tool is that it
must not *pair* rows whose natural key changed, because pairing is itself an assertion.

### 3.7 Three-valued — where `unknown` lives, and the mechanism that forces it

**Decision: `unknown` is a first-class verdict on every axis, it is never rendered as `same` or
`moved`, and there is an `unknown[]` list that says what the report is not telling you.**

Four measured instances, in increasing order of how easy they are to get wrong, and then one
that is not an absence at all:

**A table only one side carries is *known* absent, not unknown — when a directory listing is the
evidence.** `pgs.csv` is absent from `big_five_personality_snps` 1.0.0 and present with 11 rows in
2.0.0. We read both directories; the absence is knowledge. Report it as `presence: right_only` with
`added: 11`.

**A file that was not served is unknown, and it looks exactly the same on disk.** The download of 1.0.0
contains no `resolution.csv`, no `literature.csv`, no `licensing.csv` and no `README.md`, while later
versions' downloads contain all four. Yet 1.0.0's manifest carries `literature.signature` and
`sources.signature`, so those tables existed. The absence on disk is a delivery gap, not evidence about
the module. **The authority on presence is the manifest, not the directory** — `manifest.inputs` for
authored tables, the fact blocks and `manifest.derived` for derived ones. Where a manifest is not in
hand (two plain local directories), the directory *is* the authority and absence is knowledge.

**An absent field in an older manifest reads as an empty list, and this is a mechanism rather than an
accident.** `ModuleManifest.derived`, `.inputs` and `.logs` all carry `default_factory=list`, so a
manifest written before the field existed parses as `[]`. 1.0.0's manifest presents `derived: []` while
asserting three fact signatures — and there is no way from here to tell a module that had no derived
files from a manifest that predates the field. Anything read off a list-valued manifest field must be
`unknown` when the producing `compiler_version` predates the field, and the compiler version is in the
same block.

**A null counter is not zero, and the answer to that one came back inverted from what we assumed.**
1.0.0's raw manifest states `resolution_subjects: 0` with its four sibling counters honestly `null`,
while the registry's version list and its module card both report `null` for that same version. Filed as
registry `S14`(3) on 2026-08-20 and **declined the same day, with the measurement**: the two projections
agree with each other via an era gate in the registry's `db/facets._counters`, and the manifest differs
because its job is to report its own stored bytes. `resolution_subjects` is the one counter of the five
that is a plain `int` defaulting to `0` upstream rather than `int | None`, so a pre-0.6 `0` there is
**an unmeasured default and not a count** — which is why the projections gate it to `null`.

So the design consequence flips, and the corrected version is the more useful one: the comparator must
treat `resolution_subjects: 0` from a pre-0.6 manifest as `unknown`, gated on the producing
`compiler_version`, exactly as the registry does. It must still never coalesce a genuine `null` to zero.
`resolution.signature` needs no such gate and got none — it has been `str | None` since format 0.5, so
its absence is already honest.

**And the loudest unknown is not an absence at all.** Changing only `genome_build` in
`pathogenic_clinvar`'s yaml moves `content_signature` from `sha256:239c81da…` to `sha256:5210c3fe…` and
the row comparison reports **zero changed rows in every table**, because `draft.natural_key` is
build-independent — the key lists are identical across the two builds, character for character. So the
two sides name the same keys and mean loci 228 bp apart. `frame` sits at the top of the output for that
reason, and when the declared builds differ the row counts are labelled as not comparable rather than
printed as reassurance.

---

## 4. What it must refuse

**1. No write path, and no parameter that could become one.** No `apply`, no `fix`, no `output_dir`, no
`--merge`. Not "not implemented yet" — absent from the signature. A diff tool is one keystroke from
"apply", and every cell it could apply is one somebody authored. This protects the rule that a tool
never writes a value a human should decide, and it protects a narrower thing: the values most likely to
differ between two versions are exactly the curated ones, because the machine-filled ones are merged
rather than rewritten.

**2. No verdict on which side is right.** The report says `weight: 1.0374 -> 0.2072` and never says
which is correct, newer or better. The source is not automatically newer or better than what was
authored, and a later version is not automatically more correct than an earlier one — 2.0.0 reverting
1.0.1's `state` rewrite is the corpus's own demonstration.

**3. No fuzzy row pairing.** When a row's natural key changes the report says one removed and one added,
never one changed. Verified: correcting an rsID on one `hfe_hemochromatosis` variant row reports
`added 1, removed 1` and `changed 0`. Pairing them would assert that two rows are the same row, which is
a curation claim about identity — precisely the claim the format delegates to `natural_key` and, for the
binning kinds, refuses to make at all. A "did you mean" suggestion here would be a machine inventing a
row identity.

**4. No changelog prose, and the output must not be called a changelog.** The report may be quoted into
one, and it must not phrase intent: no "corrected", "improved", "fixed", "cleaned up". The changelog is
the author's statement of *why*, it lives outside every hash, and it is the only human-readable record
of a version. A generated sentence pasted unread puts a machine's guess about motive into that record
permanently. The same argument as a machine-located provenance quote: the artefact exists to record that
a person decided something.

**5. No version-bump suggestion.** Not "this looks like a major". There is no versioning contract in
this ecosystem, deliberately, and `1.0.0`/`2.0.0` are not milestones. A tool that mapped a row count
onto a semver component would invent the policy nobody agreed to, and the trust signal actually lives in
`authorship`.

**6. No staleness verdict, and no "you are behind the catalog".** `compare_to_published` reports that
its content differs from the published version and stops. Nothing computes staleness; `resolution.trusted`
is a registry projection about resolution and not a verdict on anybody's annotations.

**7. No reconstructing a missing side.** If one side has only parquet, the answer is `unknown`, not a
`reverse_module` round trip. Reversed rows were never authored — `reverse` infers a module default from
the commonest value and re-emits cells in the other place — so a diff against them reports differences
that belong to the reverser. Before RM37 that round trip moved `content_signature` on its own.

**8. No comparison of `artifact.digest` across compiler versions.** Stated in §3.4. Two digests that
differ because arrow changed are not a finding, and printing them as one teaches the author to ignore
the digest.

---

## 5. What was measured, and how to re-run it

All commands from `/data/sources/just-module-creator`, 2026-08-20. Probe scripts were written to a
scratchpad, not to the repo; each is short enough to retype from its description.

**Installed versions.**
```bash
uv run python -c "import importlib.metadata as m; print([(p, m.version(p)) for p in ('just-dna-format','just-dna-compiler','just-dna-enricher','just-dna-registry')])"
curl -s https://module-registry.just-dna.life/api/v1/version
```
→ 0.6.1 / 0.6.1 / 0.6.4 / 0.18.2, and the server reporting registry 0.18.2, format 0.6.1, mode prod.

**The public symbols this design depends on. Print them; do not copy them into prose.**
```bash
uv run python -c "from just_dna_format import integrity; print([n for n in dir(integrity) if n.endswith('FACT_FIELDS')])"
uv run python -c "from just_dna_compiler import draft; print(sorted(draft.DRAFTABLE))"
uv run python -c "from just_dna_format import layout; print(layout.SIDECAR_SPELLINGS)"
```
Eight fact-field sets; thirteen authored CSV names, of which two are the one licensing table under its
two spellings. The set `content_signature` actually reads is `draft.DRAFTABLE` minus those two
spellings — derived, not written down.

**Row order.** Copy `reference_examples/hfe_hemochromatosis` twice, reverse the data rows of
`variants.csv` in one, `compiler.compile_module` both, read both manifests.
→ `content_signature sha256:44ad4449…` on both sides; `artifact.digest sha256:6c6e103d…` →
`sha256:83635ace…`. `compiler.content_signature(dir)` agrees with the manifest on both.

**The licensing spelling, and the content boundary.** Rename `sources.csv` to `licensing.csv` in a copy
of `hfe_hemochromatosis` → `content_signature` unchanged, because the licensing table is not in the
compiler's authored-table roster at all. Edit a fact cell in it → `content_signature` still unchanged,
`integrity.source_signature` moves `sha256:0afb6361…` → `sha256:f63f2881…`.

**Bytes move where content does not.** Reverse all 31 columns of `hfe_hemochromatosis`'s
`variants.csv`, keeping every cell.
→ the file's sha256 moves `99655a7b…` → `3539447a…`, `content_signature` stays at `sha256:44ad4449…`,
and the comparator reports zero changed rows. Together with the row-order probe above, the float
formatting probe below, and the CRLF finding further down, that is four independent ways for a byte hash
to move while the content identity does not.

**Defaults folding.** Write a `curator` value on every variant row in one copy and the same value under
`defaults:` in another, blanking the cells. → `compiler.content_signature` is `sha256:921790f3…` on both.
A per-table hash taken straight off `compiler.load_csv_rows` without folding gives `sha256:33b961b4…`
and `sha256:0b8dd27c…`. The prototype comparator, with folding, reports zero changed rows.

**This is the one restatement the design carries, so it needs a guard rather than a comment.** The fold
lives in the compiler as a private function, and the field set is derivable publicly —
`set(Defaults.model_fields) & set(VariantRow.model_fields)` equals the private tuple exactly on
0.6.1, checked — but the rule `None if effective == model_default else effective` is copied. **The
regression test is that our folded per-table rows must reproduce `compiler.content_signature` on a
defaults-bearing pair**, which is what the numbers above are: `sha256:921790f3…` from both sides, and a
failure the moment upstream changes the rule. Filed as format-tree `S53` with a proposed public
`spec_tables(spec_dir)` that would delete the restatement outright.

**Row keys over the whole reference corpus.** Load every present `draft.DRAFTABLE` table in all sixteen
reference examples through `compiler.load_csv_rows` with each module's declared build, and count
`draft.natural_key` results.
→ 2,277 authored rows. **37 keyless**, all in the four binning kinds (`activity_phenotype` 5,
`copynumbers` 5, `heteroplasmy` 17, `repeat_alleles` 10), exactly as `natural_key`'s docstring says.
**One duplicate key**, in `pathogenic_clinvar/studies.csv`: two byte-identical rows for
`('11:5225715:G', '29165669')`, which `compiler.validate_spec` does not flag (0 errors, 188 warnings,
none about it). So row pairing must be a multiset, and deleting one of the two must report `removed 1`,
which the prototype does.

**Floats.** `polars.read_parquet` over each parquet of a compiled `hfe_hemochromatosis`.
→ every float column `Float64`. `grep -rn float32` across the installed format, compiler and enricher
hits only `just_dna_format/binning.py`, on the consumer-side VCF comparison rule.

**No authored weights in the reference corpus.** Nine reference examples carry `variants.csv`; across
their 381 rows, **zero** have a non-empty `weight`. The only weight-bearing corpus is the published one,
which is why 3.5's float evidence comes from `big_five_personality_snps`.

**Float formatting.** Rewrite all 990 `weight` cells of a local copy of 2.1.0 four ways and recompute
`compiler.content_signature` each time.
→ `sha256:657aa303…` unchanged by trailing zeros, a leading `+`, `%.12e`, and `repr(float(…))`; the
comparator reports 990 rows unchanged in each case. A `× (1 + 2⁻⁵²)` rewrite of the same cells moves the
signature to `sha256:9022cd15…` and the comparator reports `660 rows changed in ['weight']`, the 330
zeros being unaffected.

**The published version chain.** `client.versions`, then `client.manifest` per version, then
`client.download(..., include_inputs=True, layout="flat")` per version, for
`antonkulaga/big_five_personality_snps`.
→ four versions. 1.0.0 compiled by 0.5.4, the rest by 0.6.1. `content_signature`
`83ee4657…` / `c197eaf2…` / `cc4b7fb2…` / `657aa303…`, all four **recomputing identically** with
`compiler.content_signature` on the installed 0.6.1. `resolution_signature sha256:4d47d18f…`,
`literature sha256:e7712321…` and `sources sha256:0d07f74b…` are the same on all four, so nothing in
this chain is a canary. The only `module_spec.yaml` change across the whole chain is `module.version`,
and 1.0.1's yaml still declares `1.0.0`.

**The prototype's verdicts on that chain.**

| pair | authored result |
|---|---|
| 1.0.0 → 1.0.1 | `variants.csv` 990/990 changed in `['state']` (`ref`→`neutral`, `significant`→`neutral`); `studies.csv` unchanged; `licensing.csv` appears **in the download**, which is a delivery difference and not established to be a module change — §3.7 |
| 1.0.0 → 2.0.0 | `variants.csv` 990 **unchanged**; `studies.csv` unchanged; `pgs.csv` added (11 rows) |
| 1.0.1 → 2.0.0 | 990/990 changed in `['state']`, the exact reverse of the first row |
| 2.0.0 → 2.1.0 | 660/990 changed in `['weight']`, 330 unchanged; everything else unchanged |

`variants.csv` is byte-identical between 1.0.0 and 2.0.0 (`sha256:a8c0a77aa…`, 373,646 bytes, in both
manifests' `inputs`), which is how the revert is confirmed rather than inferred.

**Byte identity against a manifest, with no download.** `compiler.file_entries(spec_dir, names)`
reproduces `manifest.inputs` exactly for 2.0.0 and 2.1.0. `compiler.authored_input_entries` does **not**,
and that is correct — it newline-normalizes for the attestation binding, and the registry serves these
CSVs with CRLF endings (991, 391 and 12 CRLF pairs in 2.1.0's three CSVs). Use `file_entries` against
`manifest.inputs` and `authored_input_entries` against `verification.module_hash`; they are two
different bindings.

**Fact signatures recomputed from a download.** `integrity.fact_signature` with
`RESOLUTION_FACT_FIELDS` / `LITERATURE_FACT_FIELDS` / `SOURCE_FACT_FIELDS` over 1.0.1's, 2.0.0's and
2.1.0's sidecars reproduces the manifest values exactly. 1.0.0's download has none of those files.

**The build frame.** Change only `genome_build` to `GRCh37` in a copy of `pathogenic_clinvar`'s yaml.
→ `content_signature sha256:239c81da…` → `sha256:5210c3fe…`, and zero changed rows in either table.
`draft.natural_key` lists are identical across the two builds, including for the 27 coordinate-authored
variant rows.

**Scale and cost.** `cyp2c19_star_alleles` against a copy with 400 `conclusion` edits, 7 of which also
change a second column, one row deleted and one added.
→ `393 rows changed in ['conclusion']`, `7 rows changed in ['conclusion','recommendation_strength']`,
`added 1`, `removed 1`. **0.18 s** for the whole module; 0.17 s for an identical pair.

**The cheap catalog questions that already work.** `client.lookup_by_signature` on a local copy of
2.1.0 returns that version; on `hfe_hemochromatosis` returns nothing. `client.is_published(spec_dir)`
agrees. `client.resolve_version(..., "latest")` returns `2.1.0`.

**Two upstream notes filed while measuring**, both into
`../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md` on 2026-08-20:

- **`S14`** — the version list is the only cross-version endpoint and carries no `content_signature`,
  a `resolution.signature` that is `null` on every version of both modules checked while each manifest
  has it, and a `resolution_subjects` that is `null` for 1.0.0 where the manifest says `0`.
  **Answered the same day. Parts 1 and 2 accepted and shipped in 0.19.0** — `VersionSummary` gains
  `content_signature`, `resolution.signature` and `resolution.sources` are populated, and it cost no new
  column because the builder was already parsing each manifest for the `signed` boolean. **Part 3
  declined, with the measurement** — see §3.7; our reading of the `0` was wrong and the corrected rule is
  stricter.
- **`S15`** — the `upgrade` action's auto-changelog names the three columns it back-populated and not
  the one it rewrote, which is how 1.0.1's `state` rewrite came to be unrecorded. Not a behaviour bug;
  `VariantRow.upgraded()` documents the trim. **Accepted and shipped in 0.19.0**: the sentence is now
  derived from a measured `changed_cells` / `added_columns` rather than from a hardcoded column list, and
  the dry run prints the same thing. Prospective only — 1.0.1's published sentence stays as it is, which
  is an owner's call, so **a comparator still may not trust a changelog**.

**Both replies landed inside the session that filed them, and 0.19.0 is in their tree rather than on
PyPI.** Our floor is the installed 0.18.2, so nothing here may assume the new fields exist; verify by
symbol (`"content_signature" in VersionSummary.model_fields`) rather than by version string.

**One more filed into the format tree**, `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md`, same day:

- **`S53`** — `content_signature` is whole-module-only, so a per-table or per-row comparison has to
  re-derive the table roster and **restate the RM37 `defaults:` fold**, whose rule is private. Both
  measurements are §5's licensing-boundary and defaults-folding probes. Candidate fix: name the first
  half of `content_signature` — a public `spec_tables(spec_dir)` returning the parsed, folded mapping
  and the declared build — so `content_signature` becomes a one-liner over it and no logic moves. The
  smaller alternative offered is a documentation fix naming which CSVs feed the hash, since the licensing
  table being outside it had to be probed.

**And two notes we had already filed there were answered while this study was running, both fixed in
their tree and neither released** — verify by symbol before relying on either, our floor is compiler
0.6.1 where both are absent:

- **`S47`** → `hints.DERIVED_TABLE_MODELS` and `hints.derived_model_for(csv_name)`. That is the public
  derived-table roster the `derived[]` section wants; until it releases, the sidecar-to-model-to-fact-field
  wiring is ours to hold, which is three entries and a place for drift.
- **`S48`** → `hints.key_fields(csv_name)` returning `TableKey(columns, rule, stamped)`, plus a `key`
  block on `describe_table`. Two consequences for this design. `RowExample.key` can name its columns
  instead of printing a bare tuple, which is the difference between `('CYP2C19', '*1', '*1', …)` and a
  labelled key. And **the binning kinds do get grouping columns**, with `rule="overlap"` saying why
  `natural_key` still returns `None` for them — see §6, where that softens an item this study had to
  leave open.

---

## 6. What could not be settled

**Whether a stored `content_signature` is comparable across a compiler major.** All four published
versions recompute identically on 0.6.1 including the 0.5.4-compiled one, which is the documented
intent — the `genome_build` term was added "only when non-default" precisely so every GRCh38 module kept
its signature. But **all five published modules declare GRCh38** (checked one by one against the
catalog on 2026-08-20), so the case the normalization was
introduced to change is the one case with no published example. A non-default-build module compiled
before that change would have a stored signature the current code does not reproduce, and there is no
way to test that from here. The implementation should recompute both sides where it has the rows and
treat a *stored* signature as evidence only when the producing `compiler_version` matches.

**Why 1.0.0's derived sidecars were not served.** The download has none and the manifest asserts three
fact signatures. Registry versions below 0.16.2 lost `licensing.csv` and versions below 0.14 lost
readmes, and `manifest.derived` only landed in format 0.6 — so the empty list may be a manifest that
predates the field, a publish that predated the preservation fix, or a module that genuinely shipped
without them. Three candidate explanations, no way to distinguish them from the outside, which is
exactly why the verdict has to be `unknown` rather than any of the three.

**Whether the binning kinds deserve better than added/removed.** They have no equality key by design —
their duplicate rule is bin *overlap*, and two bins can conflict while sharing no key. So a changed bin
is not a well-defined object, and the honest report on compiler 0.6.1 is a weaker one: rows added, rows
removed, and a statement that this table has no row identity.

**This is the one item that moved while the study was being written, and it moved in the direction of
buildable.** Upstream's answer to our `S48`, fixed in their tree the same day, gives
`hints.key_fields(csv_name) -> TableKey(columns, rule, stamped)` where the binning kinds *do* return
grouping columns and `rule == "overlap"`. So "match the bins that share a group and report the bounds
that moved" stops needing `validate_bins`' internals. It is still not designed here: it needs a decision
about what "the same bin with moved bounds" means when a bin can split into two, and the whole corpus is
37 such rows across four modules. Revisit when `key_fields` releases, not before — and until then the
weaker report is the correct one rather than a placeholder.

**Whether `metadata` should include `authorship`.** It moves outside every hash, it is where the trust
signal actually lives, and a version that gained a human curator changed something an author cares
about. Reporting it is easy; the open question is whether a *comparison* of authorship blocks belongs in
a diff tool or in the publish flow, and nothing in the corpus exercises it — one reference example
carries an `authorship:` block and the four published versions carry the same single agent entry.

**How much of the report an agent should be shown by default.** The prototype's text output for a
four-table module is around fifteen lines, which is fine. A module with all nine table kinds, changes in
each, and several change groups per table could be several hundred. `max_groups` is in the signature as
a ceiling, but where the cut should fall, and whether the tail should be a count or a pointer to a
narrower call, was not tested — no corpus module is big enough to find out.
