# Findings blocked on an upstream change

Findings that need a change in `just-dna-format` / `-compiler` / `-enricher` /
`-registry` before they can close here. Each notes the defensive mitigation
already in place on our side.

A finding legitimately appears both here and in [dogfooding.md](dogfooding.md)
when we have mitigated it but upstream still owes the fix.

**Intake — two files, and a note belongs where the fix would land.** Format,
compiler and enricher findings go to `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md`;
registry and pipelines findings go to `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md`
(a stale directory name — the project and package are `just-dna-registry`). Each
keeps its own `S<n>` series. **Both intakes now work the same way**: the registry
adopted the split inbox/history convention on 2026-08-11, so an answered `S<n>`
moves to `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS_HISTORY.md` there too,
and its next id comes from `.claude/triage-state.py --next` in that repo — **`.py`, not the
`.sh` this file named until 2026-08-20** (it answered `S14` on 2026-08-20, after ours; never
trust a number written here). Check there before filing — a second consumer hitting a known
one appends a corroboration rather than opening a new number. Write the note and
stop; never commit in that repo.

**Read the answered half too.** The format tree's inbox holds only *open* items; an
answered `S<n>` moves to `../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md`,
whose index table carries the verdict and where the fix landed. Its inbox has been
empty since 2026-08-11 — every one of `S1`–`S18` is answered — so an entry of ours
that has vanished from it was replied to, not dropped. The registry's intake gained
the same two-file split on 2026-08-11 and **its history file is now populated** — `S1`-`S12`
are archived there, answered across their 0.13.0-0.16.0 releases. So read both halves the same
way in both trees; the earlier advice to read `**Status —**` paragraphs in the registry's inbox
no longer applies.

**Number a new one with the triage script, never from what the inbox shows** — it is
empty, ids are never reused. **The script is `.claude/triage-state.py` in the format
tree as of 2026-08-18**, not the `.sh` this file used to name; run whichever one is
there. **These numbers go stale within hours** — this line has said `S25`, `S27` and
`S29` on three different days, and one of those sessions filed a duplicate because it
trusted the number instead of the script. Compute it, every time.

**Three states, not two, and only the third releases a guard.** *accepted and
filed* (an upstream `RMn`, still open) → *fixed in tree* (the symbol exists in
`../just-dna-format`, not in what we install) → *released* (on PyPI, in our
lockfile). Every status line below names both halves, because "open upstream" said
neither and was wrong on every entry in this file until 2026-08-11.

**Format 0.6.1 / enricher 0.6.2 / registry 0.17.0 RELEASED and adopted on 2026-08-18.**
`uv sync` installs those, and the floors say so. 0.6 is the first release where the
three do **not** move in lockstep: format and compiler stop at 0.6.1 and the enricher
alone goes to 0.6.2, for RM101. Verified by symbol: `just_dna_format.layout`,
`compiler.ARTIFACT_PARQUETS`, `compiler.close_module`,
`frequencies.FrequencyUnavailable`. The paragraph below is the previous adoption and
is kept as the record of it.

**0.5.4 and registry 0.13.0 both RELEASED and adopted on 2026-08-11.** `uv sync` now
installs format/compiler/enricher **0.5.4** and `just-dna-registry` **0.13.0**, and the
floors in `pyproject.toml` say so. Verified by symbol rather than changelog:
`hints.ATTESTATION_BEARING`, `hints._report_ragged`, `Finding.line`,
`CitationHint.title`, `IdentifierReport.gene_loci` and
`RegistryClient(expect_mode=…)` are all present in the *installed* packages.

That released six mitigations at once. **The entries below have been re-verified against
the installed packages, not the sibling checkouts** — which is the check this file
exists to force, and the reason its status lines name both halves.

## Answered items that carry no `F<n>` here

`S11`, `S15`, `S16` and `S17` were filed without an `F<n>` because each shipped a
mitigation the same day and nothing was blocked — the three documentation gaps are
recorded in [CHANGELOG.md](CHANGELOG.md) under "Three documentation gaps filed
upstream". All four are answered and all four fixes are **released in 0.5.4**:

| `S<n>` | Verdict | Landed in (0.5.4, installed) | Our mitigation, and what became of it |
|---|---|---|---|
| `S11` — `provenance_quote` / `provenance_regex` are redundancy-bearing and the map does not say so | accepted and fixed, **including the fifth refusal reason we argued for**: a quote is an *attestation*, not a spent comparison | `hints.ATTESTATION_BEARING`; both columns also added to `REDUNDANCY_BEARING`; `ENRICHER.md` | **the refusal stays and is now upstream's too.** `describe_table` reports `attestation_bearing` as a subset of `redundancy_bearing`, so the sharper reason reaches an agent instead of only living in `CLAUDE.md` §2 |
| `S15` — `PacingGate`'s concurrency contract is unstated and it is not safe to share | accepted and fixed — the injection API asks callers to share a gate, so the gate had to be safe to share | `net.PacingGate` slot reservation under a lock; `ENRICHER.md` | `ServiceGate`'s lock in `net.py` |
| `S16` — whether a spec directory may hold files the compiler does not know is unspecified | accepted — tolerance is now a stated, tested contract, **and probing it found the case where "ignored" is wrong**: a mistyped table name | `COMPILER.md` + `_check_misspelled_tables` | `published.json` relies on the tolerance we tested |
| `S17` — `source` exists only on enricher-produced rows, so an authored table cannot declare provenance | accepted and fixed both ways; our proposed table was right, and there is a fifth column — on `sources.csv` itself | `SCHEMAS.md` + `vocab.MISPLACED_COLUMN_REASONS` | none needed |

`S15`'s answer is the one to note when tempted to drop the lock: upstream fixed the
gate *because* the injection API asks callers to share one, which is exactly what
`ServiceGate` does. Two locks is harmless; none is a race. Registry 0.13.0 adopted the
same fix and corrected three comments that had claimed `enrich_max_concurrency = 1` was
what made sharing a bundle *correct* — true through 0.5.3, wrong now. Ours never made
that claim, and the lock stays.

`S11` is the one whose consequence outlives the fix. Upstream added the constant **and**
kept both columns in `REDUNDANCY_BEARING`, because they qualify under that map's own
definition too. So the rule is unchanged in substance: once a fulltext has been read
through `fetch_fulltext`, `quotes_found` on that row is no longer independent evidence —
it has degraded to a citation-pairing check, which still catches a quote written against
the wrong PMID. A released constant does not make a machine-located quote honest.

---

## F5 — resolution never reaches the non-SNP table families

**Filed upstream:** **S9** (opened by just-dna-lite, 2026-08-11; corroborated by us
the same day), now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: CLOSED here on 2026-08-20 — RM43 shipped in format/compiler 0.6.0 and we
install it. One residue is open under a different number (RM69), recorded below.**

The original report: `compile_module` applied `resolution.csv` to the SNP core only,
so a module led by `pharm_variants.csv`, `diplotypes.csv` or `pgs.csv` kept exactly
the coordinates its author typed — for an rsid-authored module, none. Reproduced
here twice with a one-row `pharm_variants`-only module: `chrom` and `start` null in
the artifact both with and without a covering `resolution.csv`, which ruled out "no
table was available" and left "this family does not consult it".

### What shipped, verified by symbol on 2026-08-20

**The fill exists and runs in both paths.** `compiler._apply_positional_resolution`
joins the injected table onto every *positional* table kind, in `validate_spec` as
well as `compile_module` — the docstring says it must, because the joinability
warning is computed from those rows in both and filling on one side only would have
the pre-flight report a gap the compile had already closed.

**The set is derived, not listed.** `compiler._POSITIONAL_TABLE_KINDS` is every
`_TABLE_KINDS` model carrying both `chrom` and `start`, and evaluates today to
`heteroplasmy.csv`, `haplotypes.csv`, `pharm_variants.csv`. Five fields are written
per row — `rsid`, `chrom`, `start`, `ref`, `alts` — by
`just_dna_compiler.resolution.resolve_positional_rows`.

**`diplotypes.csv` and `pgs.csv` are still unfilled, and this entry was wrong to
group them with `pharm_variants.csv`.** `DiplotypeRow` and `PgsRow` carry no
`chrom`, `start`, `alts`, `variant_key` or `authored_ident` **at all** — measured. So
there is nothing to fill rather than a tier declining to fill it. Different fact,
different remedy: a consumer joins those two on `rsid` + `genotype`, and no
enrichment changes it. Not a defect to track.

**The Principle-7 objection this entry recorded was answered rather than waived.**
The blocker was that `reverse_module` rebuilds the CSV from the parquet, so a filled
coordinate would return as an *authored* one. Each 0.4-family model gained stamped
`variant_key` + `authored_ident` naming what the author actually wrote, both
`Field(exclude=True)`, so the fill stays out of `content_signature`. `alts` landed
on `PharmVariantRow` and `HaplotypeRow` as data and not identity. There is no
`resolution.parquet` (confirmed absent from `ARTIFACT_PARQUETS`) — reverse rebuilds
the lookup from the positional parquets, which is what P7 forces.

**The warning text this entry quoted no longer exists.** Only the fragment
`have no chrom+start` is pinned — `compiler.UNJOINABLE_PHRASE`, substring-matched by
the registry's facet builder — and the sentence around it was rewritten. It now
names *why* a row is unplaced, in three branches whose order is load-bearing: the
fill did not run (`--no-resolve`, or off GRCh38); nothing was enriched (*"run
`just-dna-enricher enrich` first"*); or the rsID resolves to more than one locus, or
to one whose alleles contradict the row, and the compiler declines to pick. A
`<partial note>` appends when a row carries half a coordinate. **Only the third is a
curation question.**

### Two live residues, neither of them this number

- **The fill is skipped off GRCh38**, with its own line citing RM15: the compiler is
  GRCh38-bound, so the injected table is not joined and those rows keep the
  coordinates their author typed. That is the open half, and it is **two upstream
  numbers rather than one** — the skip itself is **RM15** (multi-build support), and
  its consequence is **RM69**: `resolution_signature` is not a round-trip invariant
  on a non-GRCh38 module carrying a positional table. RM69 is blocked on RM15 and is
  explicitly **not** a Principle 7 breach, because `resolution.csv` is a derived
  sidecar. Neither is RM43, which shipped. (Upstream's own `RM_TOC.md` entry for RM43
  compresses the two into *"skipped off GRCh38 (RM15), which is what RM69 is about"*;
  read both.)
- **The stamped fields are `Field(exclude=True)` on the 0.4-family models and are
  *not* excluded on `VariantRow`** — measured: `VariantRow.authored_ident` and
  `.variant_key` have `exclude=None`. Grandfathered, and a 1.0-cleanup candidate
  upstream rather than a defect for us.

**Our text was the stale half, and it is fixed.** `skills/create-module/SKILL.md`
taught the pre-0.6 rule — that resolution reaches `weights.parquet` only, that a
`pharm_variants` row's coordinates arrive null, and that the remedy was a compiler
change rather than an authored edit. Three of those four claims were false and the
fourth pointed at a release that had already happened. Rewritten 2026-08-20 from the
code, along with the same file's binning-bounds section and
`references/SYMPTOMS.md`'s shared-endpoint entry, both of which keyed the rule on
`measure_kind` where 0.6 keys it on the authorable `measure_tiling`.

We still ship no code workaround, and now need none.

---

## F8 — no literature source has recordable `sources.csv` terms

**Filed upstream:** **S10**, now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: answered 2026-08-11 — accepted, and the granularity question is filed as
upstream RM46 (0.6, with RM27). Nothing to adopt; nothing more to say.**

Upstream agreed a per-source constant would be the wrong fix, for the reason this
entry argues below: a literature licence is per article. So the question is open as
*design work*, not as an unanswered report, and `RM_TOC.md` rather than the
suggestions inbox is where its progress lives.

`enrich_literature` writes `source="pubmed"` into every `literature.csv` row.
`_source_checks` builds `used_sources` from the `source` column of every fact
table. `TERMS_BY_SOURCE` has no `pubmed`. So **every literature-enriched module
warns** that a source's terms are unrecorded — a source the enricher introduced
itself, not one the author chose — and it is a warning, never an error, so it
ships unnoticed. Our literature tools widen the same gap to `europepmc`,
`crossref`, `unpaywall`, `semanticscholar` and `preprints`.

**The substantive point, and why a constant would be the wrong fix:** a literature
source's terms are **per article, not per source**. PubMed's metadata is a
US-government work; the article belongs to its publisher, and Europe PMC's OA
subset spans CC-BY, CC-BY-NC and bronze. One `pubmed` row would be right for a
module that only cites PMIDs and wrong for any module carrying a
`provenance_quote` from a CC-BY-NC article — where `taints_commercial_use`
actually bites. So it is a question about `SourceRow` granularity.

**Our mitigation is reporting, and deliberately nothing more.** Every literature
result carries a `SourceLicenseNote` with the source, the layer, a `terms_url` and
`stateable_upstream` read from `licensing.TERMS_BY_SOURCE` rather than hardcoded.
We do not write the row and never guess `declared_use`: `licensing.py` states the
enricher is the only tier permitted to hold a source convention, and a fabricated
licence string is worse than a missing warning. `lookup_open_access` returning the
*article's* licence is the closest thing to an answer we can give, because that
fact is retrievable per DOI.

**This was briefly a roadmap item (`RM7`)**, which was a mistake — there is no
work here for us. Removed 2026-08-11.

**Closes when** upstream decides the granularity question.

---

## F9 — `lookup_citation` cannot detect a fabricated PMID, because nothing returns a title

**Filed upstream:** **S12**, now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: CLOSED 2026-08-11 — released in 0.5.4, installed, and adopted here.**

Upstream added `CitationHint.title` / `journal` / `year` / `first_author`, plus
`literature.bibliographic` and `hint citation --json`, agreeing that existence is
not identity and that `esummary` already carried the answer at no extra request.

**Adopted:** `CitationLookup` carries all four, `lookup_citation`'s docstring now tells
a caller to read the title and compare it, and the `find-evidence` skill's
"existence is not identity" section names both tools instead of routing around one of
them. `tests/test_discovery.py` asserts the upstream fields exist on the *installed*
package — so if they ever vanish, the docstring's promise fails with them — and that an
offline lookup withholds the title as `null` rather than denying the paper.

What did **not** change is the working rule: a title checks an id you already hold, and
only a search finds the id you should be citing. So "take every PMID from a search
result" stays, for a reason that was never about titles.

`CitationHint` carries `pmid_exists`, `doi`, `registry_doi`, `pmcid`,
`open_access`, `abstract_available` — and no **title**, journal or year. PMIDs are
densely allocated across roughly 1–40,000,000, so a recalled or hallucinated
8-digit number is almost always a real record *for a different paper*, and
`lookup_citation` answers `pmid_exists=true` for it. Fabrication is a failure of
*identity*; existence is the only question that surface can put.

`esummary` already returns `title`, `fulljournalname` and `pubdate` in the payload
`_check_pmid` parses — `literature._identifiers` reads that same record for the DOI
and PMCID and drops the rest — so this is surfacing fields upstream already has.

**Our mitigation, which is why this was never blocking:** `literature_search`
(essentials) returns titles, and `literature_search(pmids=[...])` reads them back
for ids the caller already holds. That half was ours and shipped first — it is why
`literature_search` is in the default tier at all. The dual listing has ended now
that both halves are done: the full history is in
[previous_issues.md](previous_issues.md) under `F9`.

**Closed.** `CitationHint` carries a title, in a release `uv sync` installs.

---

## F10 — `resolve_with_ensembl=False` is the master switch for all resolution, and its name says otherwise

**Filed upstream:** **S14**, now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: SETTLED 2026-08-11. The warning had already shipped in 0.5.2 from another
report; the rename is REFUSED with a reason. Our pin is permanent, not interim.**
**Independently corroborated by the upstream audit of 2026-08-20**, which reached the
same reading from the code without this entry: `heteroplasmy.md` now carries a
⚠️ CHECK correcting its own opposite claim — it had said `compile_module` *pins* the
parameter, where it is a **default**, and the CLI wires `--resolve/--no-resolve`
straight to it. Ours is the pin; theirs is not. Nothing here changes.

This one stays in this file precisely because a refusal is an upstream state worth
keeping, and it is the entry to read before anyone reopens the question:

- **(1) shipped, before we filed.** The compiler already warns when a present
  `resolution.csv` goes unread — someone hit the same flag a day earlier. The row
  count our note asked for is added in 0.5.4: `… ({N} row(s), covering {K} variant
  key(s)), which was not read …`, rows before keys because a one-to-many rsID makes
  those different numbers.
- **(2) refused, and the reason is stronger than "unnecessary".** A `--no-ensembl`
  flag would *assert something false*: the compiler has no branch that reaches the
  network at all, so the flag would imply it otherwise might. Passing no flag is how
  the request is already spelled. Our instinct that this should be `--offline` was
  right about the concept and wrong about the tier — egress lives in the enricher.
- **(3) not doing it.** Renaming a published parameter removes a name, which is
  major-only under their P3 whatever the charter says about additive columns. An
  additive alias would be legal and they decline it, because the only honest alias
  (`--no-resolution`) buys a better name for the price of two flags meaning one
  thing.

Upstream calls our pin "belt-and-braces rather than load-bearing" now that (1) warns.
**We keep it anyway**, and the rule in `CLAUDE.md` §2 stays absolute: a warning tells
an author what happened after the fact, while the pin means no agent driving our
surface can produce the empty-but-green module in the first place. There is nothing
left to wait for here — do not re-file it, and do not word the guard as interim.

`compile_module(resolve_with_ensembl=False)` / `--no-resolve` reads as "do not go
out to Ensembl", which is a reasonable thing to want and the obvious flag to
reach for when building offline from a committed `resolution.csv`. It actually
disables resolution **entirely**, injected table included: every row compiles
with `chrom`/`start` null, and the compile **succeeds**.

**How this was mishandled on our side, which is the part worth remembering.** We
found it while building the wrapper, guarded against it, and then described the
guard in `README.md` as a feature — *"the wrapper cannot reach the flag that…"* —
without ever filing it. That is the intake rule backwards. The guard protects our
callers and nobody else's; the flag is still there for the next consumer, who gets
a green build and an empty module. Filed as S14 on 2026-08-11 and removed from the
README, which should describe what this plugin does rather than enumerate what
upstream gets wrong.

**Our mitigation, which stays:** `compile_module` pins `resolve_with_ensembl=True`
with `ensembl_cache=None`, so no agent driving our surface can reach the branch.
`CLAUDE.md` §2 forbids exposing a path to it, and the authoring docs say never to
pass it — that guidance is legitimately ours to give, because an author reading
`references/CLI.md` may well use the CLI directly.

**Closed.** The first half of that condition was already met in 0.5.2; the second is
refused on a principle, not a schedule.

---

## F11 — `would_publish`'s variant ceiling withholds the check on the modules that need it

**Filed upstream:** **S1** in `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md`
(2026-08-11 — the *registry's* intake, not the format tree's: the ceiling is
server-side), now in that repo's `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: RELEASED 2026-08-11 in registry 0.13.0, installed, and both live instances
report `0.13.0`. The upstream half is done; the remaining work is ours and is `RM8`.**

Upstream took options 1 and 3 and deferred 2 with its reasoning:

- **The ceiling no longer applies to `offline=true`** — the bound exists for gnomAD's
  paced per-subject cost, and an offline run issues no request for it to bound. So
  `check(..., offline=True)` is the answer for a panel, with no ceiling.
- **`422 too_many_variants` now carries what it computed** — `subject_count`, `limit`,
  the full validation report and `would_publish_module_level`.
- **`/validate` gained `would_publish_module_level`**: validity under strict, the
  name↔path match and the dedup claim, composed server-side. Deliberately *not*
  called `would_publish`, because a skip must never produce a positive verdict — the
  same argument as `None`-is-not-`False` here, one level up.

Their reply also found something our report did not: the ceiling was checked *after*
validation, so an **invalid** spec over the ceiling always returned 200 with a full
report while a valid one was refused. The check was answering the specs that cannot
publish and refusing the ones that can.

`marketplace check` is the only surface that adds the network tier on top of
`validate_spec` and reduces it to one branchable field. On a large module it
answers `422 too_many_variants` — the check declining to run rather than a verdict
— so the automated pre-publish signal is missing exactly where a failed publish is
most expensive.

**How this was mishandled here, which is the reason it is written down.** The
ceiling sat in our authoring skill as advice for two weeks and in our roadmap as
the justification for building a `check_publishable` tool of our own — "the useful
half of the upstream `would_publish` field, without the variant ceiling". Nobody
had filed it. Building a parallel publishability check in a consumer to route
around a bound in the producer is how two answers to one question start drifting;
the idea-book entry is withdrawn and the ask is upstream.

**What stays ours, correctly:** the skill tells an author that a 422 here is the
check declining rather than a verdict, and that `validate_module` is what decides
publishability. That is true, and an author driving the CLI needs it.

**What is ours now, and it is the only thing left.** We wrap neither `validate` nor
`check`, so none of this reaches an author yet — the unwrapped client surface is `RM8`.
When we do wrap it: `check(..., offline=True)` is the call for a panel, since the ceiling
no longer applies to a run that egresses nothing; and `would_publish_module_level` must be
reported as **"nothing module-level blocks this"** rather than "this will publish", exactly
as upstream named it, for the same reason `None` is not `False` one level down.

**The upstream half is closed** — verified by symbol on the installed 0.13.0 and by
`/health` on both live instances. `RM8` is where the rest lives; this entry is no longer
blocked on anybody else.

## F14 — a ragged CSV row is misdiagnosed by `lint_rows`, on the wrong column and the wrong line

**Found:** 2026-08-11, first binning probe (HTT CAG repeat bins) ·
**Filed upstream as `S18`**, now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: CLOSED 2026-08-11 — both defects released in 0.5.4, installed, and carried
across our boundary.**

`hints._report_ragged` names a ragged row *before* the error it causes, and
`Finding` gained a `line` field carrying the file line an editor shows — so both
halves of this note landed, including the one about `row` and `line N` disagreeing
over the same CSV. Filing it the moment it was found is what made that possible;
this is the counter-example to `S14`'s lateness.

**Adopted:** `LintFinding.line` exists and `to_findings` passes it through. It is
**never derived** — `row` is a 0-based data index and `line` is 1-based and
header-inclusive, so computing one from the other would bake in an offset that goes
silently wrong the day upstream changes either convention, which is the same argument
that kept us from renumbering rows in the first place. Two tests in
`tests/test_passes.py` pin both directions, including that an absent `line` stays
`null` rather than becoming `row + 1`.

`references/SYMPTOMS.md` gained the two entries this note argued for: the boolean
misparse on a correctly-written column, and what to do when `row` and `line` disagree.
Quoting free-text cells is still the advice — an author should quote them anyway — but
it is no longer a workaround for a silent mis-parse.

`hints.inspect_rows` positionally zips header names against parsed values
(`hints.py:268`) without comparing the two lengths. An unquoted comma in a
free-text column — `conclusion` and `phenotype` invite one — shifts every later
column left by one and drops the surplus. The reported error then names a column
the author wrote correctly:

```
row 1, unresolved, error: Input should be a valid boolean, unable to interpret input
```

with `unresolved` reading `false` on that row. Separately, `Finding.row` is a
0-based index into the data rows, so the row reported as `1` is line 3 of the file,
and the compiler's own errors use 1-based header-inclusive `line N` for the same
CSV. Both confirmed by moving the malformed row between positions.

**Why unmitigated.** `lint_rows` is a deliberate pass-through — `to_findings`
carries upstream's level, row and column across the boundary field-for-field, and
that fidelity is the point. Re-parsing the CSV on our side to second-guess the row
count would put a second parser in front of upstream's, which is the "two answers to
one question" mistake `F11` was withdrawn for. Renumbering rows in the wrapper would
be worse: our `+1` would silently become `+2` the day upstream switches to line
numbers, and nothing would fail.

**What is ours, correctly:** nothing yet in the surface, but the trap is worth a line
in the authoring skill — quote every free-text cell, because the linter will not tell
you that a comma split it. Recorded in [dogfooding.md](dogfooding.md) as the probe
that found it.

**Closes when** `_parse` reports a field-count mismatch, and `Finding.row` either
documents its convention or is renamed to a 1-based `line` matching the compiler.

---

## F15 — the registry has no enumerated client-surface contract, so we cannot tell an upgrade that affects us from one that does not

**Filed upstream:** **S2** in `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md`
(2026-08-11 — the *registry's* intake; the fix is a producer-side document or a
declared boundary in `RegistryClient`), now in that repo's
`CONSUMER_SUGGESTIONS_HISTORY.md` · **Status: answered 2026-08-11 and PARTLY shipped in
0.13.0 — the two halves that cost us real code are in; the enumerated contract itself is
open on their roadmap, with the reason it is not a changelog-pass job.**

We call eight `RegistryClient` methods — `register`, `whoami`, `claim_namespace`,
`publish`, `list_modules`, `get_module`, `namespace_available`, `download` — out of
a 35-endpoint API. Nothing enumerates that subset as a contract, and neither
`API-REFERENCE.md` nor `CLIENT.md` is stamped with the versions it describes. So
each release is read in full to establish that our surface did not move, which for
0.12.0 (deployment modes, polygon instance, operator purge) it did not.

**What shipped, and what it means for our code.** Both reference docs now carry the
version range they are normative for, and every release entry opens with a
`Client surface:` line — 0.13.0's says *unchanged*, and upstream checked it with `git log -S`
over our eight methods rather than taking our word for it (last signature change:
`c48deae`, the 0.9.0 rename). So the conclusion we paid a full release read to reach is now
a line we can read. **What is still open is the enumeration itself**, and the reason is worth
recording: it already exists and is machine-checked as `_WRAPPED_ROUTES` in their
`tests/test_client_sdk.py`; what is missing is publishing it with a *contract version of its
own*, which is a promise to hold it stable across package releases and therefore not
something to do in the same pass as a changelog line.

**Upstream says the defensive projection is now safe to delete** — against a 0.13 server the
answer is `latest_version` with no `identity` key — and confirms our reading of why it was
written: an unstamped schema could not tell us whether it described the server answering us.

**We are keeping it anyway, as a decision rather than an omission.** `get_module` is not one
of the six methods `assert_compatible` guards, so a self-hosted instance older than 0.13 will
answer `registry_get_module` with no compatibility check in front of it, and the tolerance is
what keeps that answer readable instead of a `KeyError`. Our *client* floor is 0.13.0; the
*server* on the other end is somebody else's deployment and our floor says nothing about it.
`pick(...)` costs one dict lookup. What changes is the comment: it is no longer "we cannot
confirm the schema", it is "this tolerates an older server on an unguarded read", which is a
narrower and checkable claim.

**The host half of this was measured on 2026-08-11 and is now known**, which is worth
recording because the answer was three different things at once:

- `module-registry.just-dna.life` — production, `{"status":"ok","version":"0.12.0"}`.
  Our `DEFAULT_REGISTRY_URL`, unchanged.
- `module-marketplace.just-dna.life` — answers identically. An alias of the same
  deployment, not a third instance.
- `module-polygon.just-dna.life` — resolves to the *same* A record (57.128.215.86)
  and terminates TLS, but `/health` answers a bare Caddy `404`: DNS'd and fronted,
  app not yet behind it. We ship it as `DEFAULT_POLYGON_URL` anyway so it starts
  working the day it comes up, and a `target="test"` call fails saying the polygon
  did not answer.

The `test-modules` claim that succeeded on production predates the 0.12.0 deployment.
The namespace still exists and is now a dead end: production refuses to publish into
a `test-`prefixed namespace, so it cannot be used for what it was claimed for.

**Closes when** the client surface is enumerated as its own contract, with a contract
version of its own. The other two halves — per-release `Client surface:` lines and
version-stamped reference docs — landed in 0.13.0.

## F16 — nothing over the wire reports a registry instance's mode, so "am I on the polygon?" is unanswerable

**Found:** 2026-08-11, adopting the registry's test/prod split ·
**Filed upstream:** **S3**, now in that repo's `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: CLOSED 2026-08-11 — filed, answered and released in registry 0.13.0 the same
day, and adopted here.**

Registry 0.12 runs two deployments of one image, and `REGISTRY_MODE` decides which
refuses test data and which mounts the DELETE verbs. No endpoint reports it:
`/health` gives `{status, version, storage}` and `/api/v1/version` gives the contract
versions. The only inference available is fetching `openapi.json` and testing whether
the DELETE paths are mounted — deducing a deployment's identity from its route table,
which is right until the next refactor.

`RegistryClient.delete_version` says it outright: *"a client cannot know a host's mode
before asking"*, and lets the 405 answer. For a delete that is a safe failure. The two
that matter are not: a publish aimed at the polygon that lands on production
**succeeds** and cannot be undone, and the reverse — believing you published for real
while on the polygon — looks identical in every response.

**What 0.13.0 shipped.** `mode` is on `GET /health` and `GET /api/v1/version` — both,
because they serve different callers — and `RegistryClient(expect_mode="test")` raises
`ModeMismatchError` before the first call that could spend anything, on the six methods the
contract guard already covers (publish, import, download, validate, check, is_published).
Two decisions upstream stated because they could have gone the other way: the check is
independent of `check_version`, since silencing a contract check is not consent to publish
on an unidentified instance; and **a server that reports no mode fails it**, because asking
for verification and getting silence is not a pass. A server test asserts the advertised
mode agrees with which routes are actually mounted — which makes the field strictly better
than the `openapi.json` probe we declined to build.

**Adopted:** `targets.client_for` is now the single construction point for every
`RegistryClient` in this server, and it always passes `expect_mode=target`. Uniformly, not
only where a guarded method is reached: the alternative is a per-site judgement about which
upstream method is guarded *today*, which is the kind of fact that goes stale in silence.
`tests/test_registry_targets.py` pins the pin, pins that the mode and the URL name the same
instance, and scans the source so a stray `RegistryClient(...)` anywhere else fails the
suite — verified by adding one and watching it fail.

Our own half was right and stays: the target still resolves to a URL from our configuration
and is still recorded in the `published.json` receipt. Upstream's reply says why both
belong — **ours records what we *intended*, the guard checks what *answered*.** We still
never infer a mode ourselves.

**Closed.** Both live instances report their mode (`prod` and `test`), and the polygon is
serving — it was DNS'd but answering a bare Caddy 404 when this was filed.

---

## F17 — a failed Ensembl request is reported as "no such locus", and it flips a fabrication verdict

**Found:** 2026-08-11, dogfooding · **Upstream:** `S20`, filed same day ·
**Status: CLOSED 2026-08-11 — released in 0.5.4 and installed.** Filed, fixed and shipped
inside a day, which is the whole argument for filing on discovery · **Severity:** high

`lookup_variant` on a cache-cold rsID can answer `loci: []` with the finding *"live
Ensembl has no GRCh38 locus for it either"* when what actually happened is that the
request failed. The two states are fused before our code sees them:
`EnsemblResolver.resolve_rsid` swallows transport errors into an empty list, so
`enricher.lookup._lookup_live_loci` tests `if not loci:` on an empty that has two
possible meanings and writes a finding asserting one of them.

Reproduced by re-running an unchanged call: `rs6567160` and `rs13010010` both reported
no locus on the first attempt and resolved to `chr18:60161902` and `chr2:100236272` on
the second, minutes later, same batch of seven where the other five succeeded.

**Why it is `high` and not a cosmetic wording bug.** `loci: []` plus "Ensembl has no
locus" is the exact fingerprint of a *fabricated* rsID, which is what the check is most
often used to detect. The probe that found this was triage of an LLM-written document
where four of seven rsIDs really were fabricated — a real dbSNP id paired with a gene on
a different chromosome — so the false negative put two genuine variants into the
fabricated pile. The failure mode is an author deleting true rows and reporting a source
as less trustworthy than it is, with a green run and no warning. It contradicts the
tri-state rule the rest of the ecosystem keeps: `literature_search` reports an
unreachable source as `results=null`, never `0`, for exactly this reason.

**The one signal that exists is an absence.** `hint.checked` gains `ensembl-rest` only on
the success path, so a failed run omits it:

```
failed    checked: ["…/ensembl_variations"]
succeeded checked: ["…/ensembl_variations", "ensembl-rest"]
```

Correct, and unreadable — a missing set element beside a prose finding that states the
opposite conclusion, at level `info`.

**Never mitigated here, and that was the right call.** Both candidate wrappers were
wrong for reasons the fix confirms: retrying inside `lookup_variant` would have narrowed
the window without closing it, and inferring the failure from `"ensembl-rest" not in
checked` would have hardcoded a provenance string upstream owns in order to synthesise a
state upstream did not expose — a guess wearing a check's clothing. **The string it would
have keyed on is exactly what upstream changed:** `checked` now records the source on the
answered-empty path too, so that inference would have inverted the moment the fix landed,
silently, with our tests green. Waiting cost nothing and building would have cost a wrong
answer.

**What 0.5.4 does.** `resolve_rsid` returns three outcomes — loci, `[]` for an answered
absence, `None` for could-not-ask — and `_lookup_live_loci` reports the failure at
`warning` (*"could not be reached, so its answer is unchecked rather than empty"*) against
`info` for a genuine absence. A 4xx stays an *answer*, because Ensembl 400s on rsIDs it
cannot resolve. The artifact half was worse and invisible from `lookup_variant`: `enrich()`
had written `status="not_found", source="ensembl"` for a request that failed, asserting in
the injected table that Ensembl was asked. That row is gone, the key stays unresolved so
strict still refuses, and `unreachable_rsids` names them.

**Adopted:** nothing in code — `lookup_variant` is a pass-through and `to_findings` already
carries level and message, so the warning reaches a caller unchanged. What changed is the
*guidance*: `skills/create-module/SKILL.md`'s triage step 1 now says to read the finding and
re-run on the warning, instead of telling an author to infer unchecked-ness from a missing
`checked` element.

**Closed.** Verified on the installed 0.5.4.

## F27 — a module card cannot carry a readme; the registry reads the column but never writes it

**Found:** 2026-08-12, rehearsing a longevity module on the polygon ·
**Upstream:** registry `S5`, filed 2026-08-12 · **Status:** **answered and fixed in registry
0.14.0** — released upstream, not installable here, because `pyproject.toml` floors us at 0.13.0.
The "no mitigation is possible" below was true when written and is now false: see `F33`.

> **Answered same day, and re-reported independently.** A second session of ours filed the identical
> defect as registry `S7` before reading this entry, and upstream closed it as a duplicate of `S5`.
> Two independent reproductions inside one day is itself the signal; the cost is that the second
> report was work already done. **Read this file before filing** — the check the rule asks for is
> cheap and neither session ran it.
>
> Their reply settles the three-way ambiguity the second report raised. (1) In 0.13.0 the server
> genuinely ignored the file — the field was declared, stored and returned with **no writer at all**.
> (2) It also wanted a different name: `MODULE.md` was what their own docs advertised and *nothing
> read that either*; 0.14.0 picks `README.md` and **renames `MODULE.md` on upload** rather than
> dropping it. (3) It is module-level, fed by publish, **last-publish-wins**, and a publish carrying
> no readme leaves the existing one alone instead of blanking it — now stated in their
> `API-REFERENCE.md` §37 instead of left to be inferred.
>
> `amend_readme` shipped too: outside `artifact.digest`, no version bump, so an already-published
> module's readme is repairable without spending a version. A misspelt readme — `readme.md`,
> `README.txt`, bare `README` — now warns on `/validate`, `/check` and publish, naming `README.md`
> and pointing at `amend_readme`; deliberately **not** auto-renamed, since guessing that `README.txt`
> meant the card would be inventing intent, whereas repairing `MODULE.md` repairs their own advice.
>
> **The half that is still open is the one this file is for.** A readme reaches the *card* and no
> further: `/files/{path}` and the tarball are built from what the **manifest** attests, and the
> manifest has a `logo` field and no `readme` field. So a reader who clones the spec gets the prose
> and a reader who downloads the module does not. That is format-tree `S25` — *"the manifest attests
> a logo but not a readme"* — **answered, fixed in tree, and landing in format 0.6.0**, against our
> installed 0.5.4. Upstream named `assets/longevity_2026` in it: an AI-authored module whose readme
> is where the authoring decisions are auditable was the argument they used for the field.

`ModuleDetail.readme` is declared, stored with a `''` default, and returned by
`services/catalog.py` — and `grep -rn 'readme=' --include=*.py` over `just_dna_registry/` finds
exactly one hit, which is that read. There is no writer. Every card is blank, including
production's `eric-mods/lactose_tolerance@1.0.0`.

**Why we cannot mitigate it.** `client.gather_spec_files` already uploads `.md` (it skips only
`*.parquet` and `manifest.json`), so `README.md` reaches the server and lands nowhere. There is no
`amend_readme` to call — the logo has `amend_logo`, out-of-digest and version-bump-free, and the
readme has no equivalent. Nothing on our side can put prose on a card, so this is a note and a
`README.md` that travels with the spec, not a guard.

**Two publish cycles were spent on it**, and that is the part worth remembering: a field that is
always `""` reads as *this module has no readme*, not as *this registry cannot store one*. We
guessed `MODULE.md` from the lone comment at `services/upgrade.py:198`, republished, and got `""`
again. **Do not repeat the experiment** — the answer is in the absence of a writer, not in the
filename.

**What it costs this project specifically.** A module whose honest content is "these are candidates,
most from a preprint, one association was not significant" has nowhere on the catalog to say so.
`description` is one sentence. The card otherwise shows a title, a gene list and a green
`compile_success: true`, which reads as more confidence than the rows support — the precise
inversion §2's three-valued rule exists to prevent, arriving through presentation rather than data.


## F35 — a library call loads the caller's `.env`, and it un-did our test isolation

**Severity:** high (in the suite) · **Status:** filed upstream 2026-08-18 as format-tree
**`S39`**, open · **Mitigated here:** yes, in `tests/conftest.py`

`just_dna_enricher.locations` calls `load_dotenv(env_path, override=override)` while
resolving a cache path — a *library* path, not a CLI entry point — so `build_server`
repopulates `os.environ` from whatever `.env` sits above the working directory.

That is a mild surprise for a consumer generally and a sharp one for us specifically,
because `load_dotenv(override=False)` **skips a key that is present**. `F24`'s fixture
cleared the ecosystem's variables with `delenv`, which is exactly what made the file
win. Measured on this tree: `JMC_TEST_API_KEY` was `None` after the fixture and held a
live `mk_live_…` polygon token immediately after `build_server`, so a session that had
authenticated nothing resolved a real credential. It surfaced as
`test_a_token_does_not_leak_between_sessions` failing with *"the server is configured
offline"* rather than with its own assertion — the token was real enough to get past the
auth check.

**The mitigation is to neutralize the loader, not the file.** The autouse fixture walks
`sys.modules` and replaces every `load_dotenv` binding with a no-op returning `False`.
Walking rather than patching `dotenv.load_dotenv` is the load-bearing part: every module
that did `from dotenv import load_dotenv` holds its own binding, so patching the source
module reaches none of them, and a dependency that starts calling it in a later release
is covered without anybody remembering this exists.

`setenv(VAR, "")` — §6's usual answer to this shape — is **not** available as a blanket
fix here, and that is why the fixture used `delenv` in the first place: these variables
reach typed fields, so `JMC_PORT=""` and `JMC_OFFLINE=""` are parse errors rather than
"unset". The rule still holds inside an individual test, where the field is a string.

**Closes when** the enricher stops loading `.env` from a library path, or documents that
it does. The sweep is cheap and correct either way, so it is not urgent to remove.

**Guarded by** `tests/test_modes_and_auth.py::test_building_a_server_cannot_repopulate_the_environment_from_dotenv`
and `::test_the_dotenv_sweep_actually_finds_the_loader_that_broke_this`, both run against
the unfixed fixture and watched to fail.

---

## F37 — the registry client's own docstring says a downloaded module gets no derived files, and the function beside it fetches them

**Status —** filed 2026-08-20 as registry `S13`, against `just-dna-registry` 0.18.2 (installed, and
the same in their checkout). Open. **A documentation defect only; the code is correct.**

`client.py::split_derived`'s closing paragraph reads *"the derived CSVs are stored server-side but
the manifest attests none of them, so a downloader only receives what
`artifact.files`/`inputs`/`logs` list"*, and cites a `just-dna-format` `CONSUMER_SUGGESTIONS.md`
entry that has since been answered. Forty lines further down in the same file,
`RegistryClient.download` does `names += [e.name for e in manifest.derived or []]` and passes
`check_derived=True` to `verify_manifest`. `specfiles.py` states the change twice in its own
comments, both times attributing it to 0.17, and `ModuleManifest` carries `derived` among its 34
top-level fields at format 0.6.1.

**Why it reached us.** It is the only sentence in the client that says what a downloader actually
receives, and we were writing the author-facing account of the `derived/` layout from that file.
Taken at face value it would have had `skills/module-tables` tell an author that `--with-inputs`
returns no sidecars — the opposite of what 0.17 ships, and a claim they would then design around.

**Mitigation.** The skill's text is written from the code and from `specfiles.py`'s 0.17 comments,
not from that paragraph: `manifest.derived` attests **bare filenames at the flat root**, the split
runs *after* `verify_manifest`, and a re-upload is flattened back with `content_signature` unmoved
because `SIGNATURE_INPUTS` is root-only. No code of ours changed — we call `download` and read
`manifest.derived`, both of which behave as the code says.

**Closes when** the paragraph is replaced (we argued in `S13` for replacing rather than deleting it,
since the question it answers is one a reader has at that point).

**Not guarded by a test.** There is nothing of ours to assert: the defect is in prose we do not
ship, and the behaviour we depend on is already what we test against.
