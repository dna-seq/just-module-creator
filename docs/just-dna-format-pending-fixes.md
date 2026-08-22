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

**Format 0.6.6 / compiler 0.6.6 / enricher 0.6.6 RELEASED and adopted on 2026-08-21**, with the
registry at 0.18.2. `uv sync` installs those and the floors say so. The three moved back into lockstep
at 0.6.5, which is the aligned number (schema, compiler and enricher all moved in it); 0.6.6 is the
patch round that followed. Verified by symbol in the **installed** packages, not the sibling checkout:
`StudyRow.curator`, `hints.DERIVED_TABLE_MODELS`, `hints.key_fields`, `hints.REDUNDANCY_BEARING_TABLES`,
`compiler.compiler.spec_tables`, `compiler.compiler.module_stats`, `scaffold.companions_for` — note
`scaffold` lives in the **compiler**, not in format. That release retired nine entries in this file at
once. The paragraph below is the previous adoption and is kept as the record of it.

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


## F53 — a module without `variants.csv` cannot be found by gene (upstream `S57`)

**Status: CLOSED 2026-08-21 — released in compiler 0.6.6 as their `RM121`, installed, and adopted
here.** They answered the question the note asked — `stats` describes the **module**, and `Stats`'s own
docstring already said "derived from the spec", so it was an unimplemented sentence rather than a
scoping choice. `module_stats` ships **beside** `variant_stats` (renaming it would be a major), with the
gene-bearing kinds derived from the table roster and the derived fact sidecars structurally excluded.
Re-measured on `cyp2c19_star_alleles`: `gene_count: 1, genes: ['CYP2C19']`.

**One thing does not close with it, and it is not a defect:** a `pgs`-led module still publishes
`genes: []`, because `PgsRow` carries no `gene` column to contribute. And a module **published** before
0.6.6 keeps the stats its own compile wrote — a manifest is immutable, so being findable by gene needs a
recompile and a new version. Both are stated where the guard used to be.

`compiler.variant_stats` derives `stats.genes` from `variants.csv` alone and the registry's gene index
reads that field, so a PGx, copy-number or activity-bin module publishes `gene_count: 0, genes: []`
however many rows carry a `gene` cell. Measured on their own `cyp2c19_star_alleles`: `genes: []` beside
**106 rows** carrying `gene=CYP2C19`. Six independent reproductions, three of our dossiers reaching it
separately.

**Our guard is prose, and it is deliberate.** `module-101` and `module-tables` both carry it, and both
say the same thing: **do not add an empty or invented `variants.csv` to fix it** — that trades a
discoverability gap for a dishonest module, and it makes `studies.csv` required. Name the genes in the
README and the display prose, where a text search finds them.

The `S57` note asks which of two things `stats` is meant to describe — the module or the table — because
that decides whether the fix is theirs or the registry's. If they answer "the table", this re-files in
the registry intake.

## F54 — the binning family annotates nothing end to end (upstream `S58`)

**Status: HALF ANSWERED, and the half that mattered — released in 0.6.6 as their `RM122`.**
`SCHEMAS.md` now carries the normative **measure lookup** beside the genotype join contract: scope to
the group, select the row whose inclusive range contains the value, greatest `measure_min` on a shared
endpoint, compare in float32, `unresolved` on a missing measurement, withhold on no match, and
`trait_efo_id` multiplies the answer rather than disambiguating it. That was the ask — a normative
statement a conforming consumer can be held to.

**Still true, and why this entry stays open:** no consumer implements it. `just-dna-lite` touches all
four binning kinds in exactly two places and both count rows. Upstream's `RM122` remains open for the
question we did not ask — whether the rule should also be a public function — and waits on a consumer to
fix a signature against. Their own framing is that the family is specified *ahead of* its consumers,
deliberately.

No consumer implements the bin lookup, so `repeat_alleles.csv`, `copynumbers.csv`, `heteroplasmy.csv`
and `activity_phenotype.csv` produce nothing a reader renders today. Three independent reproductions.
The format side is complete; what is missing is a normative statement that the lookup is a conforming
consumer's obligation — `SCHEMAS.md` specifies the genotype join in that detail and specifies nothing
equivalent for a measure.

**Our guard:** `module-consumer` carries it as a 🚧 and `module-curate` points at it. We tell authors the
tables are still worth writing — they are correct and publishable — and to say in the README what the
bins mean, because prose is the only path to a reader right now. **Do not promise an author that a
heteroplasmy module will produce a report today.**

## F55 — three attestations record a check that could not have failed (upstream `S59`)

**Status: TWO OF THREE released in 0.6.6 as their `RM123`; the third did not reproduce.**

- **`enrich_pgx` grading CPIC's own table** — `_function_check_record`'s *answered* branch built
  `detail` from the answered legs alone, so a CPIC-drafted module with PharmVar answering published a
  clean two-authority comparison with no sign that half of it was a copy against itself. Both branches
  now sort by source, since `verification.json` is a hashed input.
- **`hints._flag_advisory_columns` naming checkers that never open the table** — scoped by
  `REDUNDANCY_BEARING_TABLES`. The **explanation** only: the provider refusal stays column-keyed,
  because whether a drafter should start filling `clin_sig` on a binning row is a separate decision
  nobody has taken, and making it fillable as a side effect of fixing a message is not a repair. Six
  columns are deliberately unscoped and each absence is a checked claim.
- **`enrich_facts` collapsing "no constraint published" into "not asked"** — **did not reproduce**.
  Read as the gene-constraint pass, the two states have been separate since their RM98 in **0.6.1**: a
  looked-up gene gnomAD publishes nothing for gets a `not_found` row, while a gene reachable through
  neither route gets no row at all and lands in `unconsulted` with its own warning. We were running
  enricher 0.6.4 and the report named no symbol.

**The test the note gave survives all of it and is the durable half** — ask of any green attestation:
*could this check have failed?* Their reply put it better: a check that could not have failed should
record why rather than record a zero.

`enrich_pgx` grading CPIC's own table; `hints._flag_advisory_columns` naming checkers that never open the
table quoted; `enrich_facts` collapsing "no constraint published" into "not asked". The record cannot
carry the distinction between *checked and agreed* and *compared a source with itself*.

**Our guard:** `module-check` states all three and gives the test that catches the next one — **ask of
any green attestation: could this check have failed?** The note asks upstream to generalise the skip
reason their ClinVar `panel:` pin already produces, and explicitly does **not** ask for a severity
change.

## Upstream `RM104`–`RM111` — filed from our 2026-08-20 dossier audit; six shipped in 0.6.6

Eight code defects the three-way dossier audit found in `just-dna-format` / `-compiler` / `-enricher`.
They are **upstream roadmap items, not our `F<n>`** — recorded here so a guard in one of our skills is
traceable to the thing it guards against, and so nobody re-files them. **Six shipped in 0.6.6 and their
guards came out on 2026-08-21; `RM108` and `RM110` are open as minors and their guards stay live.**

| Upstream | What | State | Our text lives in |
|---|---|---|---|
| `RM104` | `enrich_gene_metrics` raised `UnboundLocalError` on an ordinary idempotent re-run, outside `GeneMetricsEnrichmentError` | **released 0.6.6** | `module-refresh`, `references/gene_metrics.md` |
| `RM105` | `logo.jpeg` won discovery and was attested, but the publisher allowlist did not carry it | **released 0.6.6** — re-publish a module that shipped one | `module-publish`, `references/logo.md` |
| `RM106` | the `faf95` warning was published twice into `manifest.compilation.warnings` | **released 0.6.6** — a recompile publishes one fewer warning | `module-check`, `module-compile`, `references/frequencies.md` |
| `RM107` | a duplicate `(source, layer)` row in `licensing.csv` compiled green under `--strict` | **released 0.6.6, and it TIGHTENS** — now an error in validate and compile both | `module-start`, `module-check`, `references/licensing.md` |
| `RM108` | a ClinGen re-curation appends beside the old row with nothing marking it superseded | **open** — needs a currency notion decided first | `module-refresh`, `references/gene_validity.md` |
| `RM109` | the gene-metrics fetch-suppression key was not derived from the merge key, so an override duplicated | **released 0.6.6** — a pair written earlier is still in the file | `module-refresh`, `references/gene_metrics.md` |
| `RM110` | `constraint_flags` has two producers with two encodings — 17,403 of 18,111 snapshot rows carry the truthy literal `"[]"` | **open** — normalizing moves `gene_metrics.signature` for every module holding snapshot rows | `references/gene_metrics.md` |
| `RM111` | three shipped strings asserted a registry override of `license` that nothing performs | **released 0.6.6** — two were `Field(description=…)`, so the text `describe_table` returns changed | `references/module_spec.md` |

**`RM107` is the one that can stop a build.** An inherited module carrying a duplicate pair compiles
today and will not under this toolchain. That is the pair being noticed rather than the module breaking,
and the repair is a decision: `licensing.merge_sources_csv` merges on the key but keeps the **last** row,
which discards a claim silently exactly where the two disagree.

**`RM110` has a consumer-visible edge worth acting on whatever upstream does:** anything writing
`if row.constraint_flags:` reads 96% of snapshot rows as *flagged*. Compare against the literals and
treat `"[]"`, `""` and `None` alike as **no flags**.


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

## F38 — `--no-study-facts` is a permanent choice on `gwas_effects.csv`, and nothing upstream says so

**Status: CLOSED 2026-08-21 — the clause landed in enricher 0.6.5's `ENRICHER.md` and CLI help,
which is what this asked for.** No `RMn`: the merge rule was correct throughout and the prose read as
a per-run trade. **Our warning stays**, and deliberately — it is in front of an author at the moment
they pass the argument, which upstream prose is not.

`ENRICHER.md:2797` and the CLI's own `--no-study-facts` help both describe the flag as "keeping the
effects and losing the linked metadata", which reads as a per-run trade. It is not one: `_merge_key`
is `("id", association_id)` alone and `enrich_gwas` skips any association already in the file before
`_build_row` runs, so a row written without study facts keeps `pmid`, `study_accession`, `ancestry`,
`trait` and `trait_efo_id` null permanently. A later run with study facts on is a no-op for exactly
those rows; only deleting `gwas_effects.csv` recovers them.

**Why it reached us.** RM12 wrapped the pass as `enrich_gwas_effects`, and `study_facts` is an
argument an author sets without being able to read `_merge_key`. The cost asymmetry makes the cheap
run the likely first choice — the 382-request measurement is loud and is what points an author at
the flag.

**Mitigation.** `enrich_gwas_effects` warns whenever `study_facts` is off, naming the five columns
and saying a later run will skip rather than backfill, and the `study_facts` field on `GwasReport`
carries the same sentence. `tests/test_passes.py::test_study_facts_off_says_the_nulls_it_leaves_are_permanent`
asserts the three-step sequence — thin run, re-run with study facts (still null), delete and re-derive
(populated) — against the real pass with an injected transport.

**Closes when** the clause lands in `ENRICHER.md` and the CLI help. The warning stays regardless: it
is in front of an author at the moment they pass the argument, which upstream prose is not.

---

## F56 — the machine-produced fact tables have no public `(csv → row model)` enumeration

> **Renumbered from `F38` on 2026-08-20.** Two different findings were minted as `F38` hours apart,
> which is not an id that is load-bearing — it is an id that resolves to two things. The **other**
> `F38` (`--no-study-facts` / format-tree `S50`) keeps the number, because `CHANGELOG.md` names it
> beside `S50` and that reference is unambiguous. This one takes the next free id.


**Status: CLOSED 2026-08-21 — released in compiler 0.6.5 as their `RM112`, installed, and adopted
here.** `hints.DERIVED_TABLE_MODELS` + `hints.derived_model_for(csv_name)` are public: keyed on the
filename, derived from `_FACT_TABLES` rather than restated, and answering both licence spellings.
`_PRODUCED_MODELS` and `_PRODUCED_CSVS` now both read that map, minus the draftable kinds, so the
licensing carve-out stays derived and the cross-package hop below is gone. They declined to widen
`describe_table` — deliberately, since a caller relies on its refusal — which leaves our separate
read-only route as the shape they endorsed.

`compiler._FACT_TABLES` is the authoritative tuple — `(csv, parquet, model)` for the seven fact
tables — and it is **private**. `hints.model_for` / `draft.DRAFTABLE` cover authored kinds only.
`specfiles.FACT_CSVS` + `RESOLUTION_CSV` (registry) are public and carry **names only**.
`ARTIFACT_PARQUETS − LEAD_PARQUETS` was tried and does not isolate them: `annotations.parquet` and
`studies.parquet` are in neither set. `reference.authoring_reference()["models"]` describes every
derived model but is keyed by **model name**, and what a tool caller holds is a filename.

**Why it reached us.** RM11 makes a sidecar's columns answerable, which needs the model behind the
name.

**What the mitigation was.** The roster came from the registry's public pair
(`specfiles.FACT_CSVS` + `RESOLUTION_CSV`) and the `csv → model` half was a seven-entry hand-kept map,
with a test pinning the two to each other. Its real cost was that the roster came from a *different
package* than the loader it described, so a registry release lagging a compiler release made our
answer lag too — that is gone with it, and the arm in `describe_machine_table` for a name that is real
and undescribable by this build is gone as well, because the two halves can no longer disagree.

**The test that replaced the pin is the one worth keeping**: the roster is now compared against the
registry's independent enumeration, which is a different package on a different cadence. A fact table
that reaches one and not the other is a file an author can be handed and cannot be told about.

---

## F39 — a table kind's natural-key *columns* are unobtainable, only its key *values*

**Status: CLOSED 2026-08-21 — released in compiler 0.6.5 as their `RM113`, installed, and adopted
here.** `hints.key_fields(csv_name) -> TableKey | None` carries `columns`, `rule` and `stamped`, plus a
`fallback` for the one kind with two levels, resolving through `model_for` then `derived_model_for` so
one route answers authored and machine-produced kinds alike. It returns the **authored** spelling of a
column rather than the grouper's property — `modifier_copy_number`, the same correction we had made by
hand. `rule` gained a third member on the way, `subject`, for a table where one subject legitimately
carries several rows; eight models now declare `_KEY_FIELDS` and both dupe-key dicts derive from it,
so `key_fields` and `natural_key` cannot drift.

`list_tables` reports `keyed_on` and a new `key_rule` from it, `describe_table` and
`describe_machine_table` both carry the whole `key` block, and the `keyed_on` half of `_SUBJECTS` is
gone. **The subject half stays**, and stays the one deliberate exception: it answers *which table?*,
which is about intent and not structure.

`draft.natural_key(row)` is public and row-level: an instance in, a tuple of *values* out, so it
cannot say which columns they came from, and it returns `None` for the four binning kinds on purpose
(their rule is overlap, not equality). `compiler._TABLE_DUPE_KEYS` holds the names as **lambdas** and
is private; `MeasureBinRow._KEY_FIELDS` holds them as strings and is private, and names the
`effective_modifier_copy_number` *property* rather than the authorable column.

**Why it reached us, and it is our defect first.** `list_tables().keyed_on` is a hand-kept string —
the only structural claim on this surface that is not generated — and it said
`(gene, modifier_gene, modifier_cn)` for all of 0.6, after upstream deprecated that column. An author
was being told to key on a column that is removed at format 1.0.

**The guard stays and its subject moves.**
`test_every_documented_key_column_is_a_live_undeprecated_field` was written to pin a hand-kept map;
run against the pre-fix map it flagged six tokens, `modifier_cn` among them, which was watched rather
than assumed. The drift it caught can no longer arrive from our side — but it can still arrive from
theirs, and an author reading a deprecated key column is misled either way, so it now asks whether the
**generated** answer resolves on the live model and is not retired. One test, whole class, unchanged
cost.

---

## F40 — `COMPANION_KINDS` pulls `variants.csv` in behind `studies.csv`, which RM47 made wrong

**Status: CLOSED 2026-08-21 — released in compiler 0.6.5 as their `RM114`, installed, and adopted
here.** `scaffold.companions_for(kinds)` applies the conditional half and is what `scaffold_module`
itself uses, so the answer and the act cannot disagree. `variants.csv` still pulls `studies.csv`
unconditionally — that direction has no condition, since a variant claim needs grounding evidence
however the module is composed — while `studies.csv` pulls `variants.csv` only when nothing else
recognised was asked for. Both our sites route through it, and
`test_scaffolding_a_binning_module_beside_studies_invites_no_empty_variants_csv` asserts it on disk
rather than in the warning text.

`scaffold.COMPANION_KINDS["studies.csv"] == ("variants.csv",)`, justified in its own comment by
"`studies.csv` alone fails with *module has no recognized table*" — true when it is literally alone,
not when it sits beside a binning table. Probed: `module_spec.yaml` + `copynumbers.csv` (two SMN1
bins, each citing PMID 9382095) + `studies.csv` (one row, no variant identity) validates
**strict-green**, which is the shape RM47 exists to allow. So `scaffold_module(kinds=["copynumbers.csv",
"studies.csv"])` reports that `variants.csv` is owed, and upstream's scaffold would create a stub for
it — inviting an empty table into a module whose author was doing the right thing, against our own
composition rule.

**Mitigation.** None in the data: we report `COMPANION_KINDS` verbatim, because restating it is the
drift we are trying to remove. What changed is the composition note our tools return, which now says
a binning module may carry `studies.csv` without `variants.csv` —
`tests/test_authoring.py::test_a_binning_module_may_carry_studies_without_variants` validates such a
spec rather than asserting the sentence.

**Closes when** the pull becomes conditional on no other recognised table being requested.

---

## F41 — a derived sidecar's *merge key* lives inside its pass, so nothing can reproduce it

**Status: CLOSED 2026-08-21 — released in compiler 0.6.5 as their `RM115`, installed, and adopted
here.** This was `F39` asked of the machine-written tables, where the answer was one step further
away: an authored kind's key at least *existed* as a lambda in `compiler._TABLE_DUPE_KEYS`; a fact
sidecar's existed only as a dict-key expression in the body of the pass that wrote it. Now the seven
fact models declare a key like any other, **every pass keys its `existing` map through
`base.merge_key`**, which reads the same declaration — that is what stops the two drifting — and
`KEY_RULES` gained `subject` for `resolution.csv`, where one rsID resolving to several loci would
otherwise report a legal file as duplicated.

**Our approximation was coarse on two tables and simply different on two others**, which is what the
note predicted and understated. `refresh_sidecar` keyed `clinical_assertions.csv` on
`(variant_key, dataset)` against a real key of `(variant_key, variation_id)`, so two ClinVar assertions
on one variant collapsed into one subject and were reported as a conflict; and `gene_validity.csv` on
`(gene, dataset)` against `assertion_id`, whose two-level fallback we had no way to express. Both now
come from `hints.key_fields`, fallback included.

`enrich_frequencies` builds `existing: dict[tuple[str, str], FrequencyRow]` keyed
`(row.variant_key, row.population)`. `enrich` builds `existing[variant_key] -> list[ResolutionRow]`,
so a subject there holds several rows — one per locus of a one-to-many rsID. `gwas_effects.csv` keys
on `association_id`, which we know only because `S50` states it in prose while explaining something
else. `draft.natural_key` returns `None` for all of them (they are not authored kinds).

**Why it reached us.** `refresh_sidecar` classifies every row of a sidecar it re-derived against the
copy it captured, and the whole classification turns on which columns decide that two rows are the
same row. The *fact* half needed nothing: `integrity.fact_signature` and the eight public
`<table>_signature` functions and `*_FACT_FIELDS` tuples are exactly right and are used as-is. The
subject half had no public route at all.

**Mitigation.** The subject is derived as `[f for f in FACT_FIELDS if
model.model_fields[f].is_required()]` — public pydantic over a public tuple, so it cannot silently
drift with a schema change — and the tuple it produced is reported on **every call** as
`subject_fields`, so a caller reads what "same subject" meant rather than assuming it. Measured
against the four keys above it is exact on five of the eight tables, harmlessly wide on two
(`dataset` is a constant), and **coarse on `gene_validity.csv` and `clinical_assertions.csv`**, where
it drops `disease_id` / `variation_id`. Coarse is the safe direction here — a coarse subject reports
more rows as conflicting and therefore repairs fewer — but it means a gene's second real disease
assertion is demoted into an ambiguity the author adjudicates by hand, on exactly the table where a
gene legitimately carries several rows. `tests/test_refresh.py::test_the_subject_key_is_derived_from_the_live_models`
recomputes the derivation from the models rather than asserting a typed tuple.

**Closes when** a public `key_fields(csv_name)` (whatever shape `F39`/`S48` settles on) answers for
`resolution.csv` and the seven fact CSVs as well as for the authored kinds, and is installed.

> **Answered upstream 2026-08-20 as their `RM115`, cut as 0.6.5 — and NOT installable, so this stays
> open.** PyPI's newest is 0.6.1 for all three packages, verified against `.venv` rather than their
> checkout. When it lands, `hints.key_fields` replaces the derivation and **four of our seven tables
> move**: `frequencies.csv` drops `dataset`, `gene_validity.csv` becomes `(assertion_id)` with a
> five-column fallback, `clinical_assertions.csv` becomes `(variant_key, variation_id)`, and
> `gwas_effects.csv` becomes `(association_id)` alone. Read `rule` and `fallback`, not just
> `columns`: `resolution.csv`'s key is a **subject** rather than a uniqueness constraint, so one
> `variant_key` legitimately spans several rows. **Until then the derivation is knowingly coarse on
> more tables than this entry originally measured**, which is safe in the direction it already
> states — coarse reports more rows as conflicting and therefore repairs fewer. The tier
that ought to own it is the format, beside each table's `*_FACT_FIELDS`, so each pass keys its
`existing` dict off the published tuple instead of restating it — which is the half that makes the two
unable to disagree.

## F42 — `quotes_found` is satisfied by the article's own title, so full quote coverage can witness nothing

**Status: CLOSED 2026-08-21 — released in enricher 0.6.5 as their `RM118`, installed, and surfaced
here.** `enrich_literature_pass` carries `titles_as_quotes` on `LiteratureReport` and warns naming the
PMIDs, so the check reaches an author through the tool and not only through the CLI. Their fix is
`LiteratureResult.titles_as_quotes`,
listing the PMIDs whose every `provenance_quote` is the article's title, printed as a warning and
never an exit code — the reason being ours: whether a title is an acceptable locator is the author's
decision, and what the tool can honestly say is that `quotes_found` is not evidence there.

**Our half is `RM17` and is unaffected by any of that, so both stay.** Their check lives in the
literature pass, which needs the network; ours reads `studies.csv` directly and runs inside `lint_rows`
and `validate_module`, before any pass has run. Theirs answers for a **pinned** sidecar row, which is
the case ours cannot see from the authored file alone — and those four modules have every row pinned,
so a check living in the fetch loop would have fired on none of the 3668 quotes it was written for.
Two checks, two reaches; keeping both is deliberate.

**The discriminator is the metadata, not the string's shape**, which is the thing a re-implementation
gets wrong: length cannot separate a 17-word title from a 17-word sentence.

Measured across every `studies.csv` in `../just-dna-format` (33 files, 44342 rows) while auditing our
own `S11`. The ten `reference_examples/` do not carry `provenance_quote` at all. The four
`data/output/corrected_modules/` — the published `antonkulaga/*` modules — carry one on **every** row,
3668 of 3668, and in all four there is **exactly one distinct quote per PMID** (81 PMIDs, 7–17 words).
It is the article title, verbatim: `pmid 24489884` carries *"Genome-wide association study of proneness
to anger."*, which is byte-for-byte what `lookup_citation` returns as `title`, trailing period included.

A title always occurs in its own fulltext, so `_study_quote_found` matches every time. The check
cannot fail on a title, and the value is obtainable from `esummary` metadata — the one thing the
column exists to witness is exactly the thing it does not.

> **Corrected 2026-08-20 by measurement — see `F49`.** This paragraph used to continue *"`quotes_found`
> equals `quotes_authored`, and the module reports complete quote coverage"*. It does not. All four
> modules ship `literature.csv` with `quotes_authored: 0` and an empty `quotes_found`, because the
> literature pass ran before the quotes were authored: **the check never ran on any of these 3668
> rows.** The title measurement above is unaffected. The consequence is that `S54`'s candidate fix —
> compare the quote against `CitationHint.title` inside `_study_quote_found` — would not fire on the
> modules that motivated it, which is why `F49` / `S56` exists.

**Why this is ours too.** These four modules were authored through the workflow this plugin teaches,
under a rule of ours that forbade an agent to locate a passage. The rule did not produce human-located
quotes; it produced this. Our half is `RM15`'s reversal — an agent may now locate and write a real
passage — plus telling an author what a title in that column means.

**Closes when** upstream can distinguish a quote from article metadata it already holds (`S54`'s
candidate: compare against `CitationHint.title`, and report one identical quote repeated across every
row citing a PMID), **and** that is in the version `uv sync` installs.

## F43 — a `provenance_quote` cannot name who located it, so an honest agent-located quote has nowhere to say so

**Status: CLOSED 2026-08-21 — released in format 0.6.5 as their `RM120` (`StudyRow.curator`,
"your whole ask, verbatim as you wrote it"), installed, and adopted here.** Verified from **this**
repository, which is the check that tells the truth — both trees answered to `uv run python` and
reported the same version while only one had the field (`F51`):
`uv run --project /data/sources/just-module-creator python -c "import just_dna_format; from just_dna_format.spec import StudyRow; print(just_dna_format.__file__); print('curator' in StudyRow.model_fields)"`
now prints a `site-packages` path and `True`.

**Adopted where an author meets it**: `find-evidence` tells them to fill it on every row whose quote
they located, the `studies.csv` dossier says what it is and what it is not — free text resolvable
against `authorship`, never a `machine_located` boolean — and both say the part that keeps it honest:
**nothing checks it**. It is legible to a reviewer routing scrutiny, not to a gate, and responsibility
stays with the human author however the cell is filled.

Everything below describes what an author faced before that release.

`VariantRow.curator` is `str | None`, "Curator override" (`spec.py:513`), and `Defaults.curator`
defaults to the literal `"ai-module-creator"` (`spec.py:296`). `StudyRow` has **no** `curator` column.
So a variant row can name who decided it and a study row cannot name who located its passage — the
wrong way round, given that only one of the two is an attestation.

`Contribution` already models mixed authorship properly: `who` is *"a name, handle, or model id"*,
`kind` ladders `{human, human_expert, human_certified}` against `{ai}` + `{agent, team, swarm}`, and
its own docstring says to "route scrutiny by it". That is module-level. Real work is mixed at row
granularity — a scientist reads a review while an agent traverses its citations, in one pass — and no
module-level list can say which of the two found row 1400.

**What it costs us right now.** Under the reversal an agent may locate and write a quote provided it
records who located it. With no column for that, the record can only go beside the rows rather than on
them, and a consumer downloading the module sees a quote without being able to tell whether an agent
or a geneticist put it there.

> **Measured correction, 2026-08-20 — "does not travel with the module" was wrong, and the truth is
> more useful.** This entry said the record could only go to `logs/`, which does not travel. Both
> halves are false. Verified by publishing a remediated module to the polygon and reading the
> manifest back (`test-sheep/test_aggression_anger_snps@1.0.0`): **three** records survive a publish.
>
> | Where | Grain | On the published manifest |
> |---|---|---|
> | `module_spec.yaml: authorship` | per version | `manifest.authorship` — `{who, role, kind, at}` verbatim |
> | `provenance.json` (`ProvenanceItem.rationale`, keyed by `variant_key`) | per **variant** | `manifest.provenance` — `{generator, model, agent_version, item_count, sha256}` |
> | `logs/*.log` | per run, free text | `manifest.logs` — name, sha256, size |
>
> `provenance.json` is the closest existing thing to what `S55` asks for: a per-row free-text field
> that travels. It is not sufficient — it is keyed on `variant_key`, so a variant cited by two papers
> collapses into one item, and a `studies.csv` row is `(variant, pmid)`. But "there is nowhere to put
> it" was an overstatement, and the ask is narrower than this entry claimed: **the missing thing is
> the `(row, quote)` grain, not the concept.**
>
> **How often that grain actually matters, measured on `big_five_personality`** (859 rows, 735
> variants, 26 PMIDs): 95 variants are cited by more than one paper — 75 by two, 14 by three, 3 by
> four, 3 by five — and **37 of them are cited by different papers for different `trait_efo_id`s**.
> Those 37 are genuinely different findings about one variant, each owed its own located passage from
> its own article, all mapping onto a single `ProvenanceItem`. One row in eight, on an ordinary
> module. `aggression_anger` happens to be 1:1 and hides the problem entirely, which is why it was
> worth measuring a second module before deciding the ask was small.
>
> Two carrying limits are real. `provenance.json` and `logs/` are both **deliberately not carried
> forward** by a registry contract `upgrade` (`services/upgrade.py`: `carry = set(present) -
> {PROVENANCE_FILE}`, logs never added, commented as *"they describe how the predecessor was built"*).
> That is a documented decision and correct for build metadata — but a quote's attribution is row
> provenance, not build metadata, so an upgraded version keeps the quotes and loses who found them.
> Worth saying in `S55` rather than filing separately.

**Closes when** `StudyRow` carries a per-row attributor resolvable against `authorship`, and it is
installed. A boolean `machine_located` would not close it: it collapses the agent-found/human-confirmed
case and names neither party.

## F49 — `literature.csv` publishes `quotes_authored: 0` beside a `studies.csv` full of quotes, and the manifest turns it into a confident zero

**Status: CLOSED 2026-08-21 for both halves — released in 0.6.5 as their `RM119`, installed, and
adopted here.** `_check_quote_counter_is_current` warns naming both numbers, and
`manifest.literature.quotes_unchecked` exists, so a block summed over all-null rows no longer publishes
a confident zero. Our half is `F44` and is separate.

**What did NOT ship is the half an author feels:** the pass still does not recompute the counter when
it merges, and upstream says they still want that. So a module whose quotes were authored after its
last literature run keeps reporting zero until somebody re-runs the pass, and a **published** version
keeps it, since a manifest is written at compile time. Said plainly in `references/literature.md` and
in `find-evidence` rather than smoothed over.

Their fix is the first candidate we offered: `_check_quote_counter_is_current` counts the non-empty
`provenance_quote` / `provenance_regex` cells per PMID at compile and warns when the sidecar
disagrees, naming both numbers, aggregated to one line. The second candidate — recompute the counter
when the pass merges — is **not** shipped and they say they still want it, so an
already-published module keeps reporting zero until somebody re-runs the pass.

> **Upstream state, checked by symbol rather than by reading their changelog.** `quotes_unchecked:
> int` is on `Literature` in the **installed** format 0.6.6 — ten fields, with `_literature_block`
> computing `sum(1 for r in rows if r.quotes_found is None)`. It was state 2 of three (fixed in tree,
> not released) for exactly one day, while both trees reported `just-dna-format 0.6.1` and only one
> had the field (`F51`).

**The sharpest reproduction, on a module we published ourselves.** After remediating
`big_five_personality`'s quotes we published to the polygon and read the manifest back
(`test-sheep/test_big_five_personality_snps@1.0.0`, compiled by the registry's own server). It says
both of these, in one document:

```
"literature": { "row_count": 26, "quotes_authored": 0, "quotes_found": 0, ... }
"sources":    { "notices": [ "7 passage(s) from this article are quoted verbatim in studies.csv
                              as provenance_quote. ...", … five more, counting 1, 1, 2, 3, 4 ] }
```

Eighteen quoted passages counted in the `sources` block of the same manifest that reports zero
authored quotes in its `literature` block — and 21 rows actually carry one. Neither number is wrong
on its own terms; the notices are authored `licensing.csv` prose and the counters are a stale
sidecar's, and nothing looked at both. **Not filed upstream**, deliberately: `S56` was already
answered and fixed in tree by the time this was measured, and the process rule is that answered prose
stays byte-for-byte. It is recorded here as the reproduction to point at if the fix ever regresses.

Measured on the four published `antonkulaga/*` modules while remediating one of them:

```
module                    studies rows   rows with a quote   lit rows   quotes_authored   quotes_found   quote_source
aggression_anger                    69                  69          3           0             ""             ""
big_five_personality               859                 859         26           0             ""             ""
cognitive_intelligence            2045                2045         33           0             ""             ""
risk_impulsivity                   695                 695         19           0             ""             ""
```

**First mechanism: the sidecar predates the quotes and nothing revisits it.** The literature pass ran
while `provenance_quote` was still empty, wrote what was true then, and `literature.csv` is
merge-not-clobber — an existing row is authoritative, so a later run never moves the counter. The
compiler reads both files, joined on `pmid`, and does not compare them. So the sidecar can be stale
in exactly the way that matters and look identical to a current one.

**Second mechanism: the aggregate collapses null into zero.** `_literature_block`'s docstring is
right and its per-row guard works — *"folding that into zero would report an unchecked quote as a
missing one — the single most misleading thing this block could say"*. What it cannot express is a
total over rows that are **all** null: `sum(...)` over an empty selection is `0`,
`manifest.Literature.quotes_found` is `int` with `default=0`, and there is no `quotes_unchecked`
beside it. The published manifest therefore says `quotes_authored: 0, quotes_found: 0` for a module
carrying 859 authored quotes.

**This corrects `F42`.** That entry states that `quotes_found` equals `quotes_authored` and the
modules report full quote coverage. They do not — the quote check **never ran** on any of those 3668
rows. The title measurement in `F42` stands; its consequence paragraph does not, and `S54` carries
the same correction upstream. It matters because `S54`'s candidate fix lands inside
`_study_quote_found`, a code path these modules never reach.

**Closes when** the compiler reports the disagreement between the two files (or recomputes
`quotes_authored`, which upstream's own `LITERATURE_FACT_FIELDS` comment already calls derivable from
`studies.csv`), **and** the manifest can say "unchecked" rather than `0` — and that is in the version
`uv sync` installs.

## F57 — an author's correction to a derived sidecar has nowhere to live except inside it

**Status — ACCEPTED the same night as their `RM124`, scheduled for 0.7, and it unblocks their
`RM83`.** Filed 2026-08-20 as format-tree `S60`. Our tier argument was accepted and is not among
their open questions. Nothing here changes until 0.7 ships.

> **Their reply names three open questions and one discharged prerequisite**, and the prerequisite
> matters to us right now:
>
> - **`S51` shipped as their `RM115` and was cut as 0.6.5.** `hints.key_fields` now answers for
>   `resolution.csv` and all seven fact CSVs. Against our measured derivation it moves **four of the
>   seven**: `frequencies.csv` is `(variant_key, population)` not `(…, dataset)`; `gene_validity.csv`
>   is `(assertion_id)` with a five-column fallback; `clinical_assertions.csv` is
>   `(variant_key, variation_id)`; `gwas_effects.csv` is `(association_id)` alone. **Not adopted:
>   0.6.5 is not on PyPI** — 0.6.1 is the newest published, verified against the installed package
>   rather than their tree — so this is §8's *fixed in tree, not released* state and `F41`'s
>   derivation stays until `uv sync` gives us the symbol.
> - **`resolution.csv`'s key is a `rule="subject"`**, not a uniqueness constraint: one `variant_key`
>   resolves onto several loci and a pass replaces the group whole. So a `(table, subject, field)`
>   overlay cannot say *which locus* it corrects — on precisely the table whose `source="manual"`
>   rows we called the unrecoverable case.
> - **Their `S52` shipped `ProvenanceItem.outranks: dict[str, str]`**, so the split we proposed
>   (overlay for derived, `provenance.json` for authored) is one they think may erode: an author
>   explaining why their `clin_sig` beats ClinVar *and* why their `chrom` beats Ensembl would have to
>   learn which of two files each belongs in.
> - **Whether merge-not-clobber survives** is the real prize and the real cost, and is why this is
>   0.7 rather than a minor.

Asked as a 0.7-sized item, and asked of the **compiler** rather than built here — see the last
paragraph.

Every derived sidecar is merge-not-clobber, so a hand-corrected cell survives a re-run and a re-run
therefore refreshes nothing. Asking a source whether it still says what the file says means deleting
the file and re-deriving it, which discards the author's rows with the stale ones —
`resolution.csv`'s `source="manual"` rows above all, because nothing fetches them back.

`refresh_sidecar` already makes that sequence reversible and reported (verified capture, delete,
re-derive, classify, reapply what is provably the author's). It stops at the one thing no wrapper can
do: a subject present in both copies with a differing fact is **either** a cell the author edited
**or** a revision the source published, and two data points do not separate them. So it reports and
refuses to resolve.

**That refusal is a symptom, and the cause is architectural.** An author's judgement is stored inside
a machine-derived file with nothing marking it as authored. Authored and derived are mixed in one
table.

**The ask** is a recognized authored overlay — one row per `(table, subject, field)` carrying the
value, the reason in prose, who decided and when — that lies on top of a derived table and is never
merged into it. Derived files become `f(source, overlay)`: nothing is hand-edited, so re-derivation
is non-destructive *by construction* rather than by a wrapper being careful, and a difference between
two derivations means the source revised, full stop. The three-explanations ambiguity stops existing
rather than being reported. `RM16`'s terminal-state detection then falls out free — an overlay row
that no longer changes anything is a source that caught up, which is evidence an authored judgement
was vindicated and is available nowhere else in this format.

**It depends on `F41` / `S51`.** The overlay's subject must name a derived row exactly, and the
per-table merge key is not public; we derive it and report the derivation on every call, which is
fine for classifying and not fine for a persisted key. S51 is a prerequisite, not a nice-to-have.

**It also narrows `F43`/`S52`.** S52 asked upstream to pick a per-field shape for `provenance.json`.
With an overlay, the overlay carries corrections to **derived** tables and `provenance.json` goes
back to being the reason-record for an **authored** cell that outranks a source. S60 says we would
rather have the overlay if only one is possible; the per-field records `record_override` writes today
re-emit into whatever shape either answer settles on.

**Mitigation.** None beyond `refresh_sidecar`'s capture-and-report, which is the honest floor. We
deliberately did **not** invent an `overrides.csv` in the spec directory: it is absent from
`specfiles.RECOGNIZED_SPEC_FILES` (24 entries, no overlay of any kind) and a server-side rebuild
would drop it silently, the way `licensing.csv` was lost before registry 0.16.2.

**Why we asked rather than built it.** We can apply an overlay at build time ourselves. An overlay is
**authored input, not a repair** — a compiler reading it is doing what it already does with every
other authored table, so none of report-never-repair is at stake. If each downstream tool applies its
own overlay instead, two consumers compiling the same spec directory can disagree about what the
module says and the artifact stops being a function of the spec. The business decision — whether this
authored value outranks that source — stays ours and we did not ask them to take it.

**Closes when** an overlay table is recognized by the format, applied by the compiler, and installed
by `uv sync`.

## F58 — the three required `ModuleInfo` fields carry no `Field(description=…)` (upstream `S63`)

**Status: filed 2026-08-21 against format 0.6.6, open. Our side is mitigated and does not wait on it.**

`module.title`, `module.description` and `module.report_title` are the three fields an author must
replace before a spec validates, and the only three in `ModuleInfo` whose `Field` carries no
description — while `icon`, `icon_set`, `color`, `name` and `version` beside them all do. So the model
tells an author what `icon_set` accepts and says nothing about the field that becomes their catalog
card's subtitle.

Measured on the live production catalog: six of seven published `description`s run 25–79 words, two to
five sentences, rendered whole. Only `eric-mods/lactose_tolerance` at 8 words is inside the readable
band. Four of the five reference specs end with the byte-identical *"Curated from the GWAS Catalog
(GRCh38), allele/strand-validated against dbSNP with a gnomAD r4 second witness."* — the field's one
differentiating job spent on a sentence four cards share.

**What we asked for:** a `Field(description=…)` on the three, naming the band and saying that
methodology belongs in `weighting:` / `authorship:` / `README.md`.

**What we argued against, in the note itself:** a `max_length` or a validator. It refuses a merely
verbose spec, refuses it at validate time after the prose is written, and makes six published modules
retroactively invalid — a false claim about work that met every requirement that existed. We also did
**not** file a card-clamp suggestion in the registry's intake: rendering is theirs, and clamping hides
content the author chose to write. The repair belongs where the prose is authored, which is here.

**Mitigation, and it is complete on our side.** The norm has one home
(`skills/module-tables/references/module_spec.md`) and is repeated at the single point an author meets
the field — `scaffold_module`'s `next_step`, the string an agent reads immediately before replacing the
`<<REPLACE>>`. The two pre-existing *"description is one sentence"* assertions
(`registry_amend_readme`'s docstring, the readme dossier) now agree with it and name what overrunning
costs: `description` sits inside the attestation binding, so on a published module it is a line for the
decision list rather than a repair.

**Closes when** the three fields carry field descriptions in a release `uv sync` installs. Nothing of
ours comes out then — the point-of-write repetition is still worth having, because the model's field
description does not reach an agent replacing a `<<REPLACE>>` in a YAML file.

## F59 — display metadata is inside the attestation binding (format `S64`, registry `S16`)

**Status: filed 2026-08-21 against format/compiler 0.6.6 and registry 0.18.2, both open. Nothing of ours
can mitigate it — the field, the binding and the card all sit upstream.**

**This supersedes half of what `F58` assumed.** `F58` recorded that shortening a published description
"costs a version". It costs a version **and the closure record**, in exchange for changing nothing a
consumer can measure. That is a materially different claim and it is the one to quote.

### The measurement, which is the whole note

`assets/fto_bmi` copied twice; in one copy only `module.description` was edited, 44 words to 11, `diff`
over the rest of the file empty. Both compiled strict under compiler 0.6.6:

| | 44 words | 11 words |
|---|---|---|
| `content_signature` | `sha256:d519efda…fbfe` | **identical** |
| `artifact.digest` | `sha256:c3d633f0…aa09` | **identical** |
| `resolution_signature` | `sha256:63ab1af5…fd59` | **identical** |
| `inputs["module_spec.yaml"].sha256` | `sha256:4a010e53…aba0` | `sha256:8ee80caf…7799` |
| `verification` | closure block — `closed_at`, `closed_by`, `module_hash`, `signature` | **`null`** |
| `compilation.warnings` | `[]` | *"verification.json is stale…"*, *"This module records no closure…"* |

`manifest.inputs` was `["module_spec.yaml", "variants.csv", "studies.csv"]` — **`README.md` is not in
it**, it has its own `manifest.readme` entry outside the binding, which is exactly why `amend_readme`
exists and is safe. The shortest fixable prose in the system is the only prose that cannot be fixed.

### Why we think it is a defect

Format already partitions these fields as display and says so twice: `integrity.py:215-218` excludes the
*"identity and display half of `module_spec.yaml`"* from `content_signature` because *"a metadata edit
or a registry strip does not change it"*, and the manifest block holding them is named `Display`. Only
the attestation binding still treats display as provenance. Meanwhile the registry's `amend_readme`
docstring defines its amendable family as *"out-of-digest metadata … no version bump is needed"*, which
the table above shows `description` satisfies byte-for-byte — so the refusal is format's binding
overriding the registry's own rule from a layer below.

### The two shelves, and the ordering between them

**Format `S64` — justify or split.** Either name what the binding buys by covering the six `Display`
fields, which we will then teach as a cost worth paying, or draw the binding along the line
`content_signature` already uses. We named the real cost of the split ourselves: the binding stops being
"any byte of an authored file" and starts having to hash a parse, inheriting every canonicalization
question, and two hashes that disagree about what counts as display would give an author two answers to
"did my edit count". **A justification closes this; we are not pushing for the split.**

**Format `S64`, second half — a `short_description` with a character `max_length`** (~120, the band our
owner named; `lactose_tolerance` is 71 chars and fits). We asked upstream **not** to bound `description`
in `S63` one day earlier and the distinction is load-bearing: a bound on a *new optional* field
invalidates nothing published and is the field's definition rather than a taste judgement applied after
the prose was written. It must land on the amendable side of whatever `S64` decides, or it reproduces
the problem in a new place.

**Registry `S16` — read the bounded field for the card, and an amend endpoint once `S64` lands.** We
suggested `amend_display` over a description-only endpoint since all six fields share the status, and
said explicitly that it **cannot ship first**: rewriting a stored `module_spec.yaml` puts it out of
agreement with `manifest.inputs` and a downloaded spec would fail `verify_manifest`, while an amend that
also rewrites the inputs entry yields a manifest that is no longer what the compiler wrote. Only the
card-preference half — `ModuleCard.description` preferring `short_description` when present — is theirs
to do independently.

### What we argued against in both notes

Render-time truncation or folding: it hides prose the author chose to write, leaves the spec as wrong as
it was, and gives the author no signal. A bound at the schema is what protects the grid; a clamp at the
renderer only protects the pixels. And no retroactive fix to the seven published modules — they met the
requirements that existed, and shortening one costs its author a version and their closure, which is a
decision for each of them.

**Closes when** either a justification we can quote lands in an upstream reply, or the binding is split
and a release `uv sync` installs carries it. The `short_description` half closes separately, when the
field exists with its bound *and* the registry's card reads it.

## F63 — an interrupted enrichment persists nothing, and its terminal write is unlocked (format `S66`)

**Status: filed 2026-08-22 against enricher 0.6.6, open. Mitigated here, and the mitigation is
narrower than the fix.**

`enrich()` writes `resolution.csv` once, at the very end, after every network link — so a run killed
at minute 29 has written nothing, and thirty minutes of successful per-variant resolution is
discarded. The write itself is `open(path, "w")` + `csv.DictWriter`: in place, truncating, no
tmp+rename and no fsync, so a kill mid-write leaves a valid-looking short file. `record_verification`
and `record_source_terms` sit in the same tail. And there is **no advisory lock anywhere** in either
tree, while the pass reads the existing sidecar at its start and rewrites it at its end — so the
read-modify-write window is the whole run.

**What made it a data-integrity finding rather than a scaling one.** A worker thread cannot be
interrupted, so a client that gives up leaves the work running. Measured: an aborted 330-variant run
was still alive when the author restored the published sidecar and re-enriched; the second call read
the restored file, reported `resolved: 330, sources: ["cache"]` correctly and instantly, and the first
then wrote its partial result over it, leaving **162** distinct rsIDs plus a rewritten
`verification.json`. The module validated, closed and compiled green, because every count in it agreed
with every other. An unresolved subject contributes no row at all in some branches, which is why the
file shrank rather than degrading visibly.

**Our mitigation, and what it does not cover.** A directory being enriched is claimed in process, and
a second `enrich_module` on it raises with what is running and when it began instead of succeeding
into a file about to be overwritten; the claim releases in `finally`, which covers exactly the window
the abandoned write can land in because `run_sync` defaults to `abandon_on_cancel=False`. That stops
the sequence that actually happened, where both calls came from one session. It **cannot** see an
enrichment started by another process, it does not make an interrupted run keep what it resolved, and
it does not make the write atomic. Those three are upstream's and are what `S66` asks for.

## F64 — the warning surface cannot be read on the module that needs it most (format `S67`, `S68`)

**Status: filed 2026-08-22 against compiler 0.6.6, open. No mitigation here and none is right.**

Two findings, filed separately because the asks differ. `_verify_vrs_ids` emits one warning per
allele while `_vrs_coverage` aggregates the same class a few lines away in the same file, and which
path a module lands in is decided by whether `resolution.csv` carries a `vrs_id` at all — so **the
module whose enricher minted more identities is the one that becomes unreadable.** Measured: 101
resolution rows all carrying `vrs_id`, 47 of them indels, produced **85 warnings, 80 per-allele**;
57,595 rows with 26,810 indels and no `vrs_id` on any produced **7, one aggregated**. On the first
module the three warnings an author can act on are items 83, 84 and 85.

Beside it, `warnings` is a flat `list[str]` with no code, no count and no cap across `validate_module`,
`compile_module` and `registry_check`, and nothing separates a finding an author can clear from one
they cannot — the VRS warnings say of themselves that they are *"minted upstream by the enricher, not
recomputable here"*. The compiler already holds that discriminator and spends it on severity rather
than presentation: *"a finding no authored edit could clear is not a `strict` matter."*

**Why we are not mitigating.** Aggregating on our side would mean re-deriving upstream's grouping from
warning text, which is the hardcoded-schema-fact this repo forbids, and it would hide the raw list an
author may need. Every skill here insists warnings on a green run are the real output; that
instruction is only followable if the list is readable, and readability is the producer's to give.

