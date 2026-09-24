# Previously resolved findings

Dogfooding findings (`F#`) resolved **here**, each with its resolution and a code
pointer. Findings move into this file from [dogfooding.md](dogfooding.md); they
are not copied.

**Check here before re-investigating a finding that looks fixed.**

---

## F105 — the AlphaGenome pass cannot be aimed at "my rows", so scoring a module means writing a window planner

Found 2026-09-21 by the unattended seat porting `longevitymap` (1033 rows, 527 rsIDs, 272 genes) to
0.7 and adding expression predictions, on plugin 0.37.0 against enricher 0.7.1.
`enrich_expression_effects` takes one `gene` and one interval, and the interval is the corpus: the
whole module's genes span about 2 Mb of positions, roughly 6 M SNVs, an hour and a half of queries
and a table nobody could read. The honest query for an author's module is *the module's own
positions*, and nothing offers it — so the run planned 393 windows of 21 bases (positions merged
within 100 bp, keyed on the row's own `gene`), drove them through an in-memory client at ~2 s each,
and got 23,700 rows of which 714 module rows are actually scored. Two things the tool would have
known and the planner had to rediscover: a row whose `gene` label is not at that locus (the six
`TP53` rows on other chromosomes, the `LOC…`/antisense symbols the Atlas has no gene axis for) comes
back as a window with 63 rows and `withheld: {no_gene_axis: 63}` or a MANE warning, and a row with
no `gene` at all (256 here) cannot be asked about anywhere.

**Surface it, do not build it yet**: a `rows=true` mode that walks `variants.csv` × `resolution.csv`,
groups by `(gene, chrom)`, merges neighbours and reports per-row *scored / no gene / gene not at
locus* is one afternoon, and it is the mode every author of an existing module wants. Whether it
should also take a gene from the reference when the row has none is the question — that is an
authored value written from a source, and the rule is to surface it.

**Built 2026-09-24.** `enrich_expression_effects(rows=true)` plans windows from the module's own rows (`expression.plan_windows`: by row `gene` and chromosome, merged within 100 bp, padded 10 bp; 377 windows for longevitymap), queries them in order, stops at the first failure because of `F95`, and returns `windows`, `windows_run` and the same `row_status` as `F106`. A rows-mode `dry_run` is a plan read off local files and answers under offline too. **Left surfaced, as the finding asked**: a row with no `gene` is reported as `no_gene` and never given one from a reference — that would be an authored value written from a source. Not run against the live Atlas from this seat; the window loop is tested with the upstream call replaced.

## F106 — `top_expression_effects` cannot answer "which of MY variants does the model call disruptive"

Same run. The question the owner asked — *how many of the longevity-favourable SNPs does AlphaGenome
predict to disrupt their gene* — is a join of `expression_effects.csv` onto `variants.csv` through
`resolution.csv`, keyed on `(chrom, start, alt, gene)` with the effect allele read off the row's
genotype minus the locus ref. `top_expression_effects` ranks the whole table and filters by gene,
consensus and magnitude; `in_gene_only` filters by the gene span, not by the module's rows. The
join was fifty lines of script and produced the README's table (441 favourable pairs scored, 237
predicted decreases, 97 at ≥ 80 % consensus). The tool that reads the table back should take
`module_rows_only=true` and report the same per-row status as F105. Two facts to preserve when it
does: `effect_direction` is the track-majority sign and disagrees with the sign of `effect_size` on
some rows, so the direction column is the one to count; and a null direction is a real answer.

**Fixed 2026-09-24.** `top_expression_effects(module_rows_only=true)` keeps only predictions for a `variants.csv` row's own gene and effect allele (placed through `resolution.csv`), reports a `row_status` per authored row — `scored`, `gene_not_at_locus`, `not_scored`, `reference_only`, `no_gene`, `unresolved`, `unreadable` — and a `direction_counts` tally over the track-majority `effect_direction` with null counted as `unknown`. The join lives in `expression.py` so the reader and the `F105` planner cannot disagree. On the longevitymap port it reads 1033 rows as 584 scored, 144 reference-only, 252 without a gene and 53 unscored. Tests in `tests/test_passes.py`, one fixture row per status.

## F108 — `fetch_fulltext` returns the abstract for a PMC author manuscript that PMC's BioC endpoint serves whole

**Found:** 2026-09-24, building a module from PMID `30820047` (Kunkle 2019, *Nat Genet*,
`PMC6463297`) · **Severity:** medium · **Status:** open

The paper's per-locus results — lead rsID, major/minor allele, OR per minor allele — are in the
article's **Tables 1 and 2**, not in its supplementary workbook (ST5 has ORs without alleles, ST9
alleles without ORs). So the body text is the only route to a row, and `fetch_fulltext` did not reach
it:

| call | result |
|---|---|
| `fetch_fulltext(pmcid="PMC6463297")` | `retrieved: false`, `locations: []` — `F50` reproduced |
| `fetch_fulltext(pmid="30820047")` | `text_source: "abstract"` |
| `fetch_fulltext(doi=…)` | `retrieved: false`, seven repository locations, no text |
| Europe PMC `…/PMC6463297/fullTextXML` | HTTP 500 |
| PMC BioC `research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC6463297/unicode` | **200, 276 KB, both tables intact as table passages** |

The module was finished from the BioC copy, fetched with a raw `curl` — the ad-hoc route the product
exists to remove. **Candidate fix:** add PMC BioC as a rung after Europe PMC in the fulltext ladder,
behind `ServiceGate` under the NCBI budget, and return table passages as text rather than dropping
them: for a GWAS paper the tables are where the rows are.

**Fixed here 2026-09-24; the quote-check half is owed upstream as format-tree `S110`.** `discovery._bioc_fulltext` is the rung after Europe PMC: PMC BioC behind the shared NCBI gate, `text_source: "pmc_bioc"`, tables kept as tab-separated rows, the reference list dropped, and three outcomes kept apart — text, *PMC holds no copy* (an HTTP 200 whose body starts `[Error]`), and *could not be asked* (a warning that says UNCHECKED). Verified live: `PMC6463297` returns 68 KB including Tables 1 and 2. Tests in `tests/test_fulltext_bioc.py` over a trimmed real answer, `assets/literature/pmc_bioc_PMC6463297.json`. The enricher's own `quotes_found` check still reads Europe PMC only and only when `isOpenAccess`, so a module's quotes against this paper stay abstract-checked until `S110` lands — see `just-dna-format-pending-fixes.md`.

## F109 — `literature_search` tells the author to add the `pubmed` licensing row three skills forbid

**Found:** 2026-09-24, same run as `F108` · **Severity:** low · **Status:** open

Every `literature_search` result carries a `licensing` note from `discovery.py`: *"You read pubmed by
hand, so nothing wrote a licensing.csv row for it and the compile gate cannot see it. Add the row
yourself."* But `module-start`, `module-tables/references/licensing.md` and `.../literature.md` all say
**no `pubmed` row, ever** (upstream RM46: literature terms are per article and live on
`literature.csv`), and the 2026-08-31 measurement there found the row changes nothing. An agent that
trusts the tool over the skill writes a row upstream has refused. This run followed the skills and
compiled strict with no licensing warning. **Candidate fix:** drop the "add the row" sentence for
literature services and keep the second half about the article's licence, pointing at
`lookup_open_access`.

**Fixed 2026-09-24.** `discovery._licensing_notes` now says no `licensing.csv` row is owed for a literature service at any layer, that the article's terms live on `literature.csv`, and to read them with `lookup_open_access` before quoting. The old note's second half — a `layer='annotation'` row carrying the article's licence — contradicted the same rule and went with it. `SourceLicenseNote`'s field descriptions followed. Pinned by `tests/test_discovery.py::test_a_literature_source_is_never_told_to_take_a_licensing_row`, which fails on the old text.

## F98 — `clinical_claims_without_studies` keys on `clin_sig`, so a module can assert a clinical direction with no study behind it and the audit calls it clear

Found 2026-09-12 building `apoe_locus_compound` against 0.7.0 — a module deliberately shaped to have
a layer that *should* trip this signal.

Six of its fifteen `variants.csv` rows are `category=alphagenome_predicted`: they carry
`state=protective|risk`, `direction=protective|risk`, a non-zero `weight`, and **no `studies.csv` row
at all**. Their clinical role is assumed from an AlphaGenome expression prediction and nothing else.
That is exactly the shape "a clinical claim with no paper behind it" names.

`audit_module` reports:

```
clinical_claims_without_studies  clear
  "no row in this module asserts a clinical significance"
```

Correct as written, and misleading as read. The signal keys on `clin_sig`, which this module does not
author. `state`, `direction` and `weight` are clinical claims a consumer acts on just as readily — a
report saying "protective" does not first check whether the claim arrived via `clin_sig`.

**This is §8's prose rule 1 in our own code**: *a check is only as wide as the table it reads, and
naming a check without naming its scope is how a reader over-trusts it.* The headline says "no row in
this module asserts a clinical significance" when the defensible claim is "no row authors a `clin_sig`
value".

**Two repairs, and the cheap one is not obviously wrong.** Either widen the signal to count a row with
a directional `state`/`direction` and no grounding study, or leave the scope and fix the headline to
name the column. Widening is the one that would have caught this module; but it would also fire on
every legitimately ungrounded directional row, of which there are many in real modules, so it needs a
severity below `decide` or it becomes noise the first time somebody runs it on a GWAS module. Not
repaired here — it wants the decision, not a patch.

**Fixed 2026-09-12, and the fix had to be measured twice.** `directional_claims_without_studies`
now asks, per row, whether *this row's own variant* is named by a study — not whether `studies.csv`
has any row at all, which is what the sibling asks and what passes a thousand-row module carrying one
citation. `clinical_claims_without_studies` keeps its scope and loses its overclaiming headline: it
now says *"no row authors a clin_sig value"* and names the tables it read.

**The first cut of the new signal was wrong in both directions and the reference corpus caught it.**
Run over 21 real modules it fired on four; two were its own join failing, not a gap in the module:

- `mt_common_deletion` reported all three rows uncited. Its `variants.csv` says `chrM` and its
  `studies.csv` says `MT`, and the hand-rolled fold `lstrip("chrCHR")` turns those into `M` and `MT`.
  The signal was inverted by a contig spelling. It uses `just_dna_format.vrs.normalize_chrom` now —
  the schema-fact rule at a different address.
- `cyp2d6_structural` reported its CNV uncited. A symbolic allele spans an interval and its study
  cites a point 99 bp away. Those rows are now set aside **and counted**, never silently dropped: a
  row the signal could not assess is not a row it cleared.

After both, 3 of 21 fire and all three are true positives, verified by grepping each rsID:
`hboc_palb2` (rs786203382, rs1597101776) and `shox_par1` (rs1170991098) each carry a directional row
whose rsID appears zero times in their own `studies.csv` — two uncited rows in upstream's own
reference examples — plus this module's six. `pathogenic_clinvar`'s 328 leaning rows stay quiet.

**What saved this module is not the audit.** The prediction-only rows are legible because the author
put `PREDICTION ONLY` at the head of every `conclusion`, set `flags=predicted_only`, `method=
alphagenome-expression-prediction` and `stat_significance=unknown`, and said so in the README. All of
that is convention, none of it is checked, and a less careful author gets a green audit over the same
shape.

## F100 — the taught scaffold → draft path dead-ends on a fresh scaffold, twice

Found 2026-09-20 by the dogfooding seat, first module of the ClawBio PGx run, plugin 0.35.0 on
compiler/enricher 0.7.0. `scaffold_module(kinds=["haplotypes.csv","allele_function.csv",
"diplotypes.csv"])` then `draft_from_cpic(gene="TPMT", use="non_commercial", dry_run=True)`:

1. *"cannot read the module's genome_build: module_spec.yaml []: … unreplaced template placeholder
   '<<REPLACE>>' … module.description, module.report_title, module.title … fix module_spec.yaml, or
   pass genome_build= explicitly."* `draft_from_cpic` has no `genome_build` argument, and neither
   does upstream's `draft_gene`: the remedy is the enricher CLI's, relayed raw because
   `EnrichmentError` was not in the tuple `_guard` translates.
2. After filling the three fields: *"existing haplotypes.csv does not validate, so a draft cannot be
   keyed against it: haplotypes.csv line 2 []: … '<<REPLACE>>' in HaplotypeRow row: allele,
   haplotype_name, rsid."* The compiler's `draft.merge_rows` refuses a file that does not validate,
   and the scaffold's stub is a placeholder in every required cell — so the tables scaffolded *for*
   the drafter are what block it. A header-only file drafts cleanly, and upstream's `stub_template`
   takes `rows=0`; our `scaffold_module` refused anything under 1.

Reproduced offline in a scratch directory against the built CPIC snapshot, both errors in order.
The promise it broke is `create-module`'s stage table, 1 scaffold → 2 draft, with nothing in between.
Upstream's own reference README recipe fails identically; the tester filed that as format-tree
`S103` (read `genome_build` leniently, or say to fill the titles and scaffold without `--kind`).

**Upstream half released 2026-09-21 — enricher/compiler 0.7.1 carry `S103` (their RM250):** a
draft reads past the scaffold's stubs in the fields it never uses, so only a placeholder in
`genome_build` itself refuses now, and the compiler names a stub row by its line. Adopted in 0.37.0:
the remedy text and its test moved to that one case.

**Fixed 2026-09-20.** `rows=0` on `scaffold_module`; `EnrichmentError` and `DraftError` translated
by `_guard`, each with the repair this surface can make appended after upstream's verbatim text and
keyed on `<<REPLACE>>`; the order written into `module-start` (stage 1 owns it), the two messages
into `module-draft`'s symptoms and `SYMPTOMS.md`. Not run: the tester's `probe/` directories and the
live CPIC path — the reproduction and the tests use the snapshot, `dry_run` and `offline`. **Not
re-probed**: the run ended with the tester's stdio server still on 0.35.0, and a `/mcp` reconnect is
not something that session could do for itself, so the re-probe needs the user or a fresh session.

## F101 — the two PGx cross-checks had no tool, so a PGx module could not read its own function calls back

Found 2026-09-20 by the dogfooding seat on the second module of the ClawBio PGx run, plugin 0.35.0.
`skills/module-check/GUIDE.md` listed `just-dna-enricher pgx` and `just-dna-enricher clinpgx check`
as bare CLI lines beside four tools, and `CLI.md`'s wrapped-or-not table carried them with an empty
tool column. Eleven of the run's thirteen modules are `haplotypes` + `allele_function` +
`diplotypes`, so none had an in-surface way to compare `function_status` against PharmVar or CPIC,
and a `pharm_variants.csv` module had no check against ClinPGx. The tester ran the CLI instead —
*"sources recorded: 2 … routes: cpic=snapshot, pharmvar=snapshot"* — which is the ad-hoc route the
product exists to remove, and the "surface teaches a step it cannot run" shape §5 names. The parity
rule that wrapped `check_acmg`, `check_repeat_bands` and `check_literature_coverage` at 0.35.0 had
left these two, with no written reason.

**Fixed 2026-09-20, 0.36.0.** `check_pgx` and `check_clinpgx` in the `pgx` toolbox group beside the
drafters they pair, carrying upstream's `PgxResult` / `ClinPgxResult` field-for-field: `compared` as
the denominator, `routes` for who answered, the licence skip and the offline skip as two lists, and
`not_checked` verbatim as the third value. Neither exposes `mode`, on the tester's point and the
guide's own ROADWORKS: upstream stores it and never reads it. Both let upstream attest and read
`verification.json` back for `attested`. Measured on a scratch copy of the tester's CYP2C19 module
against the built snapshots: 5 compared, PharmVar answered, CPIC reported `tautology`. Tested with a
disagreeing snapshot client injected under the real comparison, and hermetic offline runs.

**Left open, named rather than forgotten**: `clinpgx check-labels` (a module's drug claims against
five regulators' labels) is the third PGx check and is still CLI-only; `CLI.md` says so on its own
row. Not run: the tester's module directories and the live PharmVar path. **Not re-probed**: same as
`F100` — the tester's server stayed on 0.35.0 for the whole run, so a `/mcp` reconnect by the user or
a fresh session is what the re-probe needs.

## F102 — eleven dry runs in one batch: one verdict, four `503 enrichment_busy`, six `429 rate_limited`, and nothing said which budget or what to do

Found 2026-09-20 by the dogfooding seat, thirteen modules into the ClawBio PGx run, plugin 0.35.0.
`registry_check` fired once per module against the polygon; the tool surfaced each refusal raw —
*"the polygon could not complete the dry run: HTTP 429: rate_limited"* — with no bucket named, no
`Retry-After`, and no `next_step`. Read from the registry's own tree: `/check` sits on the `enrich`
bucket (operator default five an hour, refilling one per twelve minutes) plus a concurrency gate that
answers `503 enrichment_busy`; `/validate` is on its own `validate` bucket (sixty an hour), `/publish`
on `publish` (ten). So the taught rehearsal — a dry run before every publish — caps an author at five
modules an hour, and the tester switched to `registry_validate` + `registry_publish` for the remaining
eleven; only two went through the full dry run. The registry-tree half (name the bucket in `detail`,
derive `Retry-After` from the bucket's refill) is the tester's `S23`.

**Fixed 2026-09-20 (unreleased on 0.36.0).** `targets.throttle_note` is the suffix beside
`instance_note` on the three write arms: a 429 names the bucket (`enrich`, `validate`, `publish`) and
says it is the instance's budget rather than the module, and on the dry run's bucket points at
`registry_validate` as the pre-flight for a batch; a `503 enrichment_busy` says the instance runs one
dry run at a time and to re-run sequentially. No retry inside the tool: a five-an-hour bucket cannot
be waited out in a call, and a retry on the busy gate would be a policy invented here.
`registry_check`'s docstring and `module-publish` state the rule — rationed by design, never batched,
validate for a batch — and deliberately not the numbers, which are the operator's settings. Not run
against the live polygon from this seat; the refusal shapes come from the registry's source.

## F103 — `resolved: 5, sources: ["authored"], vrs_minted: 0` read as a clean run on every CPIC-drafted module

Found 2026-09-20 by the dogfooding seat on `cyp2c19`, and the tester corrected their own reading the
same day. Every CPIC-drafted `haplotypes.csv` row carries `rsid` + `chrom` + `start`, and the
enricher's last resolver branch — *"already complete, or has a position — nothing to resolve"* —
restates the authored coordinate into `resolution.csv` under `source=authored` with empty `ref`/`alts`
and no VRS id. `compile_module` then warns *"VRS allele identity covers 0/5 allele(s)"* on all
thirteen modules. **What is true and what is not**: the coordinate-agreement check *does* run —
`verification.json` carries `rsid_coordinate_agreement` with five subjects on CYP2C19, and on CYP2D6
it found five CPIC positions off Ensembl's — so the skills' sentence *"the resolution table is the
independent second value the cross-check needs"* was right about the check and wrong about the
sidecar, which holds no second value for this shape. Upstream half is the tester's `S104`.

**Upstream half released 2026-09-21 — enricher 0.7.1 carries `S104` (their RM251):** a row authoring
both an rsID and a coordinate takes the forward branch when the reference knows its rsID, so a fresh
`enrich` records the loci and mints an id, and a pair that disagrees with Ensembl warns in
`best_effort` and refuses in `strict`. A sidecar written before the fix keeps its `authored` rows under
merge-not-clobber, so the warning below now names `refresh_sidecar` as the repair instead of calling
the shape expected; the thirteen polygon rehearsals from 2026-09-20 are exactly that case. Adopted in
0.37.0.

**Fixed 2026-09-20 (unreleased on 0.36.0).** `enrich_module` now appends a warning counting the rows
that came back `resolved` under `source=authored` with an rsID and no VRS id, naming the shape, the
compile warning it will produce and `S104`. The sentence in `module-start` and `module-curate` is
narrowed to what the sidecar actually carries per shape; `module-draft`'s CPIC section says the VRS
warning is expected on every drafted module and why; `SYMPTOMS.md`'s VRS-coverage entry gains the
fourth cause. Nothing here alters the sidecar — the second value is upstream's to record. The tool
path is tested with a faked enrichment result; the predicate was measured over a real sidecar, the
scratch copy of the tester's CYP2C19 `resolution.csv`, where it counts 5 of 5 rows.

## F71 — `record_override` logged every authored cell as "outranks", claiming disputes that never happened

**Found:** 2026-08-31, reading six benchmark runs' `logs/authoring.log` · **Severity:** medium ·
**Status:** fixed here. Not upstream's — their field is scoped correctly and we were misusing it.

`record_override` has two jobs, stated in its own docstring: *"outranks a source, **or** that you
edited"*. `server.INSTRUCTIONS` rule 2 tells every agent to call it for **every** hand edit. Both
outputs said only the first thing:

```
override rs117385980 weight='-0.2 on C/T…' outranks authored judgement, no source consulted
```

**Six of seven records across two runs were judged cells** — `weight`, `conclusion`, `genotype`,
`state`, `stat_significance`, `direction` — cells no source supplies. One record was a real
disagreement (`effect_size='3.58' outranks pmid:28399814 ('3.53')`). The agents were compliant; the
surface mislabelled them.

**Both artifacts publish.** `logs/**.log` is swept into every compile with no opt-out, and
`provenance.json` is in `RECOGNIZED_SPEC_FILES`. So a module reaches the catalog asserting its author
overruled sources they never consulted — and it corrodes the signal `overrides.py` exists to protect:
if most records say *outranks* but mean *authored*, the real disputes stop standing out.

**Upstream is not at fault and there is no `S` to file.** `ProvenanceItem.outranks` is documented as
*"per-column justification for this row deliberately disagreeing with a source"*, and *"a key's
presence is what a tool may read"*. That is exact. We were writing a key for records that are not
disagreements. `rationale` — *"why this annotation was made"* — is the right shelf and every record
already filled it.

**The fix, and it needed no schema change:** `source_value is None` already separated the two cases.
The log now writes `authored … (judged; no value from X to disagree with)` where there is no source
value, and `to_items` leaves `outranks` empty for those records while still writing the reason to
`rationale`. Verified by reverting the fix and watching
`test_a_judged_cell_claims_no_dispute_it_did_not_have` fail.

**One agent diagnosed this unprompted**, which is the part worth keeping: *"the log renders my entries
as 'outranks [the sources]' when I passed no `source_value` and was recording authorship of a judged
cell, not overriding a source. That wording publishes verbatim."* A run asked for blunt feedback about
the surface produced a defect report about the surface.

## F77 — the version handshake certifies a registry pair that then refuses our own rows, and our workspace note said the opposite

**Found:** 2026-08-31, in a single-run SIRT6 benchmark on plugin 0.25.0 · **Severity:** high ·
**Status: CLOSED 2026-09-12** — both instances now serve format 0.7.0 and the column is accepted.
Filed as registry-tree `S18`; symptom entry shipped; `CLAUDE.md` §11 corrected at the time.

> **Closed on a measurement rather than on the handshake**, because the handshake is what made this
> finding possible: `assert_compatible()` passed throughout the outage. The proof is the call that
> failed, re-run — a `studies.csv` carrying `curator` put through `registry_validate` against the
> live polygon on 2026-09-12 returns `valid: true` with **zero findings**, where it returned
> `studies.csv line 2 [curator]: Extra inputs are not permitted`. `registry_health(target="test")`
> reports `server_format 0.7.0 / client_format 0.7.0 / contract_compatible true` beside it.
>
> **What generalises is the closing procedure, not the fix.** A contract finding is closed by
> re-running the call that produced it, never by reading a version line: the whole content of this
> entry is that the two disagree. Plugin 0.35.0 moved the floor to `>=0.7.0,<0.8` for the same
> reason in the opposite direction — the instances moved first, so a 0.6.6 client is now the
> refused end.

A module green through every local gate — strict validate, strict enrich, strict compile, verified
digests, closed with eleven check records — is refused by both live registries:

```
valid: false — studies.csv line 2 [curator]: Extra inputs are not permitted
```

`StudyRow.curator` shipped in format **0.6.5**. Both instances validate at **0.6.1**
(`/api/v1/version`, prod and polygon, measured) and `StudyRow` is `extra="forbid"`. Removing that one
column returns `verdict: true, blocking: []`.

**The part that is ours is the claim we had written down.** `CLAUDE.md` §11 said *"every 0.6.x
interoperates"*, measured on `assert_compatible()`, which is scoped to major.minor below 1.0 and
therefore **cannot fail** for the class of change that actually breaks a publish — a field added in a
patch release. That is the "could this check have failed?" defect, in our own workspace facts, and it
stood for ten days.

**The obvious repair is the wrong one and the run got that right.** Dropping `curator` makes the
publish go green and silently deletes the per-row record of *who located a quote* — the attribution
that field exists for, and which `server.INSTRUCTIONS` rule 5 pushes an author toward filling. The run
kept the column, published nothing, and surfaced it as a decision. Conforming a module to a registry
that lags the format is the stale-source move §2 forbids.

**Surface it, and why one candidate is wrong.** Pre-stripping fields the target instance does not know
would require us to model their validation, would delete authored provenance, and would make a
module's bytes depend on which registry it was aimed at. `S18` asks instead that the refusal name the
version gap. **A product guard is worth building** — compare the fields a module uses against the
target's reported format version and warn by name — and is deferred rather than dismissed: it needs a
version-to-model mapping and a probe, which is more than a patch.

## F65 — four of the runs' registry findings did not survive verification, and one was ours

**Found:** 2026-08-22, verifying before filing · **Severity:** n/a ·
**Status:** closed. Recorded so nobody re-investigates.

Checked against the live instances and the registry's own source before filing upstream.
Four claims from the two runs were **not filed**, because they are wrong:

- **"Every warning a local strict compile produced was discarded at publish."** Refuted
  three ways. Production manifests carry `compilation.warnings` — two to four each —
  **including the licence-conflict warning the finding said was dropped**. The server's
  compiler version is readable at `/api/v1/version`, and digest non-reproducibility across
  compiler versions is documented twice in their API reference (*"a recompile of the same
  spec need not produce the same digest"*). The remaining true part is a **deployment lag**,
  not a defect: their 0.20 roadmap already adopts 0.6.6.
- **"`module_spec.yaml` never matches its own published digest."** Refuted by sweep: every
  input of all eight production modules fetched through `/files/` and hashed — **29 of 29
  match on both `sha256` and `size`**. The "374 bytes recorded vs 1198 served" observation
  does not reproduce.
- **"The `/files/` endpoint is undocumented."** It is documented in their API reference, and
  the supported client route to authored source is `download(include_inputs=True)`, also
  documented. Our own tier is what made it unreachable, which is `F60`'s neighbour and is
  fixed.
- **"The registry truncates the gene list without saying so."** The truncation is real and
  documented, and `gene_count` sits beside the three genes in the live payload. **The bug
  was ours**: `_module_card` read `genes` and never read `gene_count`, so a module naming 22
  genes projected three and looked complete. Fixed; a caller filtering on `genes` now has
  the number that says the list is a sample.

**The pattern worth keeping.** Every one of these read as a confident measurement in a
careful report, and three of the four dissolved on contact with the source. One run said it
of itself — two of its three findings needed retracting, and the toolchain contributed to
neither retraction. **Verify before filing, and verify against the producer rather than
against the observation**; a note filed on a refuted claim costs upstream a triage cycle and
costs us the next note's credibility.

## F60 — the surface answers "will this build?" four ways and "is this any good?" not at all

**Found:** 2026-08-21, two independent unattended runs · **Severity:** high ·
**Status: closed 2026-08-24.** The tier and discovery half shipped 2026-08-22; the audit surface
shipped in 0.20.0 as `audit_module` (`RM26`).

Run 1 curated the eight modules then on the production registry; run 2 revised the ten
modules in `just-dna-lite`'s v1 port. Neither had prior context. Both ran in the default
tier. **Every module passed `validate_module(strict=true)` with zero errors**, and every
real defect either run found was found by writing arithmetic over the CSVs.

`registry_check`, `registry_validate`, `validate_module`, `compile_module` and `lint_rows`
all answer *"will this build?"*. The offline gate is **right** to pass those modules and
says so itself — *"strict means reproducible, not correct"* — so this is not a broken
check. It is that the entry point to a curation pass tells you nothing, and the caveat
that says so is prose while the green result is a tool call.

What run 1 measured in modules that passed every gate, all by hand:

| defect | how it was found | scale |
|---|---|---|
| `effect_measure` says `beta` on a Z-statistic | compare `effect_size` against `-Φ⁻¹(p/2)` | 242 variants, 4 modules |
| `effect_size` dosage-doubled on hom rows | hom value = 2 × het value | 10 of 13 variants, 1 module |
| `weighting:` never declared | read `module_spec.yaml` | every module in both runs |
| the reference-base check had never run | read `verification.json` | every module in run 1 |
| `gene: KIBRA` not HGNC-approved | `check_identifiers` — the one tool that found anything | 1 module |

A "beta" of 7.29 on an item-level irritability score is not a possible effect size; it is
the Z for that row's own p-value to three decimals, and in one module that column then
held Z-statistics beside genuine per-allele betas of order 0.02 under one unit label.

Run 2 found the same shape from the other side: a module with **190 rows and an empty
`weight` on every one**, no `weighting:` block, passing strict and compiling green with
`weights_rows: 190`. Nothing distinguishes "the author deliberately authors none" from
"the author forgot", which is the question `weighting:` exists to answer.

**Every signal in that table is computable offline from files the plugin already reads.**
That is what makes this a gap rather than a wish, and `audit_module` now computes them: it
reproduces `superhuman`'s 190 empty weights, the six curated modules' undeclared scale, the 52
`detail: null` findings split 20/32 across two modules, and `clinical_significance` recorded at
`subjects: 0` on all eight modules of the other corpus — measured against those directories rather
than against fixtures. **It also finds seven rows the hand-repair pass missed**, still labelled
`beta` while carrying the Z of their own p-value, which is the argument for the tool in one line.
The one row in that table it does **not** cover is `gene: KIBRA` — that is `check_identifiers`,
which needs HGNC and is therefore a check rather than an audit. See `RM26` in
[ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) for what was deliberately not built and why.

## F6 — two of five literature sources refuse this host, and the tool is right to say so

**Found:** 2026-08-11, capturing fixtures · **Severity:** medium ·
**Status:** **RESOLVED 2026-08-20 — and the diagnosis below was wrong.** Both fixtures are
captured and both parsers are tested; `RM6` is closed in
[ROADMAP_HISTORY.md](ROADMAP_HISTORY.md). The tri-state finding this entry exists for **stands
unchanged** and is why it stays here.

> **Corrected 2026-08-20.** *"IP block"* was the wrong conclusion from a real observation.
> Re-probed through our own client: **arXiv answers HTTP 200** — six requests, no throttling —
> and Semantic Scholar's 429 is **intermittent and endpoint-specific**, `paper/search` shedding
> load while `paper/{id}` answers reliably. arXiv had a genuine rate-limit incident in late
> February 2026 that its maintainers acknowledged and fixed; we measured it during that window
> and then carried the conclusion for six months without re-probing. **The lesson is the
> re-probe, not the block:** an environmental verdict is a measurement with a date on it, and
> ours had no expiry. `assets/literature/` now holds `arxiv_query.xml` and
> `semanticscholar_search.json`, captured through `Discovery` itself so each is a real response
> to the exact request the client makes.

The original observation, which was accurate on the day: Semantic Scholar and arXiv both answered
HTTP 429 from this machine regardless of user-agent, arXiv on a *first* request with no prior
traffic. Confirmed with plain `curl` outside the client.

Reported here rather than routed around because it is the best available
evidence that the tri-state design earns its keep. A live `literature_search`
returns `results=null` and `rate_limited=true` for those two, plus a warning that
their part of the literature is **unchecked, not empty** — while PubMed and
Europe PMC answer normally. Had the model used `0`, the same call would have
read as "no preprints exist on this subject", which is a conclusion an author
would act on.

The cost was real while it lasted: `parse_semantic_scholar` and `parse_arxiv` had no committed
fixture and therefore no test, for six months. Both now have both — six tests, including the
`arxiv:doi` branch that only fires for a preprint that was later published, which is the branch a
fixture-less parser was most likely to have got wrong.

## F7 — a `limit` was spent entirely on whichever source was asked first

**Found:** 2026-08-11, first live search · **Severity:** medium ·
**Status:** resolved same day, kept here as the reason the ordering rule exists

The first working `literature_search` asked four sources with `limit=5` and
returned five PubMed papers. Europe PMC had answered with five of its own and
none of them appeared: the merge preserved first-appearance order, so source one
filled every slot.

Nothing was broken and every count in `sources` was accurate — which is what made
it easy to miss. It only showed up because the live run printed `found_in` per
paper and every row said `['pubmed']`.

Merge now interleaves by each source's own rank, so every source's top hit
outranks anyone's second. Ties break on first appearance, so the order stays
deterministic.

**Why it stays in this file rather than moving to previous_issues.md:** the
finding is not the bug, it is that asking several sources can silently degrade
into asking one, and nothing in the result said so. A future federated tool wants
the same guard.

## F28 — `literature_search` tells you a preprint has no PMID while handing you one that does

**Found:** 2026-08-12, authoring a module from three PDFs · **Severity:** medium ·
**Status:** fixed in this change

`discovery.py` fired this on `any(p.preprint for p in papers)`:

> *"Some results are preprints: not peer-reviewed, and they carry no PMID, so they cannot ground a
> studies.csv row (pmid is required)."*

It fired on a result whose `pmid` was **`41427385`** — a bioRxiv posting with a PMID *and* a PMCID
(`PMC12713140`), because bioRxiv and medRxiv are indexed in PubMed under the NIH preprint pilot. The
warning contradicted the payload in the same response.

**The cost is a citation not made.** An agent reading the warning rather than the field concludes the
paper cannot ground a row, and either drops the finding or hunts for a journal version that may not
exist yet. Here it was the *centrepiece* — the cGAS variant with the functional work — and only
re-reading the raw `pmid` recovered it.

**Fixed by counting instead of assuming**: the finding now reports how many preprints carry a PMID and
how many do not, and leads with the part that is always true and got buried — none of them is peer
reviewed, so a row grounded on one must say so in its `conclusion`. `skills/find-evidence/SKILL.md`
carried the same false claim ("A preprint has **no PMID** … full stop") and is corrected.

**The generalisable bug is a class claim standing in for a field read.** "Preprints have no PMID" was
true of the arXiv index and got written as a property of the category; the fix is that the record
answers, never the class.

---

## F80 — a benchmark's isolation was breached by our own memory index, and by "read" not covering "list"

**Found:** 2026-08-31, running three scored benchmark runs on 0.27.0 · **Severity:** high ·
**Status:** memory entry retired the same day; runbook in `docs/BENCHMARKING.md`.

Every benchmark prompt banned reading `data/interim/` and `assets/benchmarks/`, where the
adjudicated reference and the sibling runs live. Two things got past that, and neither is the
agents' fault.

**The project memory told each run to open the answer key.** A memory entry read *"read
`data/interim/repro-bench-2/HANDOFF.md` first"* — the round's own handoff, naming the reference, the
scores and the findings. One run flagged the contradiction and refused; nothing in the setup would
have detected compliance. **The prompt is not the isolation boundary**: `CLAUDE.md`, the memory
index and the skills all reach a subagent unasked.

**"Read" did not cover "list".** A run's first bundled command included `ls data/interim/` and it
saw five directory names. Names only, no contents, it never descended, and it disclosed this before
being asked — but the clause has to say *list* too.

**Neither voided a run, and that is why they are worth writing down.** Both were caught by an agent
volunteering against its own interest, which is not a control.

**Surface it, and the candidates that are wrong.** Rewriting prompts is necessary and not
sufficient, since the leak was in injected context. Removing the memory entirely loses a real
pointer. What is built instead is a transcript audit that does not depend on anyone's honesty —
parse `tool_use` inputs in the subagent JSONL for forbidden paths, check which tool first surfaced
the answer, and ask for the reasoning chain separately, since grep cannot tell a derivation from a
reconstruction. **Counting name mentions does not work**: `registry_download` and `registry_search`
appeared 18 times in one transcript with zero invocations, the hits being tool-schema text.

## F47 — a skill can teach a step the running tier cannot run

**Found:** 2026-08-20, trying to refresh `literature.csv` from a default-tier session ·
**Resolved:** 2026-08-27 in 0.21.0, by removing the tier

`find-evidence`'s loop ended with `enrich_literature_pass(spec_dir="spec")` as the verify step, with
`paper_citations` in the same code block. Both were extended, so on a default install neither
existed, and nothing in that skill said so — the only mention of a tier anywhere near the topic was
one parenthesis in `literature.md`. The guard written for exactly this,
`test_the_taught_workflow_runs_in_the_default_tier`, read `server.INSTRUCTIONS` and not the skills,
which are the other half of the taught workflow and much the larger half.

**What it cost.** `literature.csv` needed re-deriving (`quotes_authored: 0` beside authored quotes —
`F44` / upstream `S56`). The two tools for that were both extended, so on a default server there was
no route at all: the module was published with the sidecar as found, and the log says so.

**How it was closed, and why not the way this entry proposed.** The candidate fix here was a test
extracting `name(` call sites from every `skills/**/*.md` block and requiring an `EXTENDED` marker on
any that was not in the default roster — and the entry explicitly ruled out moving the passes into
essentials, on the grounds that *"the tier line is cost, and a pass that rewrites every row of a
corpus is squarely extended. The defect is the silence, not the tier."*

The cost argument was right and the conclusion was wrong, which took three more instances to see.
This was the fourth time the same shape shipped — `enrich_module` taught while extended-only (0.4.0),
`compare_to_published`'s docstring naming `registry_download` from a tier that lacked it,
`refresh_sidecar` invisible to both 2026-08-21 unattended runs — and each of the first three was
fixed by moving one tool across the line rather than by asking what the line bought. **What it bought
was nothing a caller could not be told in prose**: hiding a tool never made its pass cheaper, and the
sessions that could not see it were exactly the ones doing the work that needed it. 0.21.0 removed
`JMC_MODE`, `--mode` and the `extended` tier; the cost moved into each expensive tool's own
description, where a caller can weigh it, and
`tests/test_surface_and_auth.py::test_the_corpus_sized_tools_say_what_they_cost` fails if one stops
saying it. The skills-scanning test was not written: with one surface, the check that matters is
"does this name resolve", and `test_docstrings_only_name_tools_that_exist` asserts that over every
tool description.

## F52 — the review queue accused an author of an edit nobody made

**Found:** 2026-08-20, dogfooding `review_queue` on `assets/fto_bmi` · **Resolved:** same session

`record_override` was recorded against `rs1421085`'s `clin_sig`, and `review_queue` came back
`still_bound: false` — which reads as *the authored cell was edited again after the reason was
written*. Nobody had edited anything. `fto_bmi/variants.csv` **carries no `clin_sig` column at all**,
so there was no cell to compare, and the boolean had collapsed "no value" into "a different value".

That is the failure `CLAUDE.md` §2 names in its own words — *never collapse "unknown" into a boolean;
`None` is never `False`* — committed by the very tool written to satisfy §2's other half. It shipped in
0.11.0 and was found an hour later by using the surface rather than by testing it, which is exactly the
split §7 describes: the tests asserted the two states the author of the tool had in mind, and a real
module had a third.

`QueuedOverride.still_bound` is now `bool | None`: `true` the reason still describes the value, `false`
the value moved under it, **`null` there is no such cell — the row is gone or the column does not
exist**. `ReviewQueue` counts them apart as `unbound` and `subject_absent`, and the ranking puts a
broken binding first, an unanswerable one second, a live one last.

Pointer: `src/just_module_creator/overrides.py`, `QueuedOverride` / `review_queue`;
`tests/test_overrides.py::test_a_record_for_a_column_the_table_does_not_carry_is_unknown_not_unbound`
reproduces the `fto_bmi` shape.

---

## F3 — a strict compile failed with no indication of which step was missing

**Found:** 2026-08-11, first end-to-end run · **Resolved:** 2026-08-11

Compiling a complete, valid spec with `strict=True` returned `success: false`.
The spec was fine; it had simply never been enriched, so no `resolution.csv`
existed and strict refuses what it cannot reproduce.

The finding was not the refusal — that is correct — but that our result gave no
signal about *where in the workflow* the caller was. Fixed by surfacing upstream's
`errors` verbatim in `CompileReport` (it names the unresolved variants and says
what to inject) rather than reducing the outcome to a boolean, and by stating the
enrich→compile ordering in `compile_module`'s docstring and in the skill.

Pointer: `src/just_module_creator/tools/authoring.py`, `compile_module`;
`tests/test_pipeline.py::test_strict_compile_refuses_unresolved_rows` pins that
the refusal arrives as structured errors rather than an exception.

## F4 — the test suite could not import its own helpers

**Found:** 2026-08-11 · **Resolved:** 2026-08-11

`from tests.conftest import offline_settings` resolved to a `tests` package
shipped by a transitive dependency inside `site-packages`, not to this repo's
`tests/`. Collection failed with a confusing `ImportError` naming a path in
`.venv`.

Fixed by importing as `from conftest import ...`, which resolves through the
directory pytest puts on `sys.path`. Recorded in `CLAUDE.md` §6 so the next agent
does not "fix" it back.

Pointer: `tests/test_modes_and_auth.py` import block.

## F12 — the first step of the publishing workflow was not in the tool surface

**Found:** 2026-08-11, asked to create an account and a namespace on the live
registry · **Resolved:** 2026-08-11, 0.3.0

Every registry tool needed a token, and the only route to one the surface named was
`registry-client register` — a shell command in another package, pointed at by
`authenticate`'s docstring. So the plugin gated every registry action behind a
credential nothing in it could mint, and onboarding quietly cost a second toolchain
despite install instructions that promise one command.

Not an upstream gap: `RegistryClient.register(install_id, account)` is public in the
**published** 0.9.1, `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email), and
`generate_install_id()` grinds the proof-of-work locally in 0.3–1.2 s. A public
onboarding API we had simply never wrapped.

Fixed by `registry_register(account, install_id=None, difficulty=None)`. Three
decisions worth keeping:

- **It lives in `auth.py`, always on.** It writes to the registry but cannot be
  token-gated — it is what produces the token — and extended-only would have
  reproduced the same dead end behind a mode flag. `CLAUDE.md` §5 now states the
  exception and its test: a registry write is gated *unless the token is its output*.
- **The token goes into the caller's own session slot**, so registering leaves the
  session usable and no secret has to be copied back through the transcript.
  `authenticate` is now only for a token you already hold.
- **Both secrets come back, and the install-id carries the warning.** It is the
  account's only recovery path; re-registering it reissues a key for the same
  account, while registering again without it creates a *different* account and
  strands the first. `JMC_INSTALL_ID` was added so a later session can reuse it,
  which is a value we read and never write — persisting it ourselves would widen the
  write surface. The `account_taken` error says outright that retrying will not help.

Pointer: `src/just_module_creator/auth.py` — `registry_register`,
`resolve_install_id`, `_registration_failure`;
`models.RegistrationResult`; `settings.install_id`;
`tests/test_modes_and_auth.py::test_an_illegal_account_name_is_refused_before_any_socket`
and `::test_install_id_precedence_and_origin`.

**Not verified end to end from this side, deliberately.** The wrap, the local
refusals and the offline ceiling are covered by the suite, and the live service was
exercised read-only plus one real failure path (a deliberately invalid install-id
returning `422 invalid_install_id`, mapped to actionable text). Actually minting an
account and claiming a namespace belong to the dogfooding side — a builder who also
runs the irreversible probe has graded their own work. **A shipped fix is not a
passed probe.**

## F13 — an irreversible claim had no pre-flight, though upstream shipped one

**Found:** 2026-08-11, same session · **Resolved:** 2026-08-11, 0.3.0

`registry_claim_namespace`'s docstring warned that a namespace "is claimed once and
then owns every module published under it, so this is not a step to run
speculatively" — and then offered no way to be non-speculative. The only way to
learn whether a name was free was to try to take it.
`RegistryClient.namespace_available` is public, read-only and needs no token, and
was unwrapped.

Fixed by `registry_namespace_available` in `research.py`, essentials — beside
`registry_search`, which was already the home for token-free registry reads, and in
the default surface because a pre-flight for an irreversible step belongs there.

**`valid` and `available` are returned separately, and the live registry proves why:**
it answers `test_modules` with `valid: false, available: true`. Collapsing them into
one boolean would have told an author that an illegal name was claimable.

The naming half was the sharper finding. Accounts are validated with the *namespace*
rule (`is_valid_namespace`, `^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` and
`test_modules` were rejected before anything else could happen — and our docstring
said only "Lowercase, hyphen-separated", which reads as a style preference rather
than a hard reject. Module names are the opposite rule, `^[a-z][a-z0-9_]*$`, which
is why a spec holds `my-ns/lactose_tolerance`. That asymmetry is now stated in
`registry_claim_namespace`, `registry_register`, `registry_namespace_available`, the
server instructions, the skill and the README, and an illegal account name is
refused locally with the pattern named, before a round trip is spent.

Pointer: `src/just_module_creator/tools/research.py` —
`registry_namespace_available`; `models.NamespaceAvailability`;
`src/just_module_creator/tools/registry.py` — `registry_claim_namespace`'s docstring.

## F9 — `lookup_citation` could not detect a fabricated PMID, and our docs said it could

**Found:** 2026-08-11, designing the search tool · **Resolved:** 2026-08-11 ·
**Upstream:** `S12`, released in compiler/enricher **0.5.4**

`CitationHint` carried `pmid_exists`, `doi`, `pmcid`, `open_access` — and no title, journal
or year. PMIDs are densely allocated across roughly 1–40,000,000, so a recalled 8-digit
number is almost always a real record for a **different** paper, and `lookup_citation`
answered `pmid_exists: true` for it. Both our skill and the tool docstring said "verify each
PMID with `lookup_citation`", a rule the surface could not enforce: fabrication is a failure
of *identity*, and that call only answered existence.

**Two things fixed it, and the order matters.** First, ours: this is the finding that put
`literature_search` in the **essentials** tier rather than extended, because discovery is the
missing half of an anti-fabrication promise the default surface had already made. Then
upstream's: 0.5.4 added `CitationHint.title` / `journal` / `year` / `first_author`, which
arrive in the same `esummary` response that answers existence and therefore cost no extra
request. Both tools now report a title, and the docs tell a caller to read it and compare.

The working rule survived the fix unchanged, for a reason that was never about titles: a
title checks an id you already hold, and only a search finds the id you should be citing.

Pointer: `models.CitationLookup`, `tools/research.py::lookup_citation`;
`tests/test_discovery.py::test_upstream_supplies_the_bibliographic_fields_identity_needs`
asserts the fields exist on the *installed* package, so the docstring's promise fails with
them if they ever go away, and
`test_an_offline_citation_lookup_withholds_the_title_rather_than_denying_it` pins that a
missing title reads as unchecked rather than as "no such paper".

## F20 — `list_tables` advertised `sources.csv`; `describe_table` and `get_template` rejected it

**Found:** 2026-08-11, authoring `assets/fto_bmi` · **Resolved:** 2026-08-11 ·
**Upstream:** `S21`, released in **0.5.4**

The done-checklist required `sources.csv`, and every route to its columns refused:
`list_tables()` named it under `sidecars`, while `describe_table("sources.csv")` and
`get_template("sources.csv")` both answered *"Unknown table kind"* and helpfully listed
eleven alternatives, none of which was what was asked for — which reads as "you invented
that filename", not "this kind is real but undescribed".

**Two separate defects, and both had to be fixed.** Upstream's: `authoring_reference()`
omitted `SourceRow` entirely, and the root cause was a level below the report —
`SourceRow.layer` and `.declared_use` ran closed-vocabulary validators with no `vocabulary=`
marker, and the guard that discovers enforcement by behaviour iterates `_ALL_MODELS`, which
the model was not in. One omission hid the other. 0.5.4 fixes both and puts `sources.csv`
in `draft.DRAFTABLE` with `(source, layer)` as its natural key.

Ours: the sidecar list in `tools/authoring.py` was a hardcoded literal while the authorable
set came from `draft.DRAFTABLE`, so one tool named a file the next two denied existed. With
upstream's half released, that literal made it *worse* — `sources.csv` appeared as a table
kind **and** as a "do not hand-author" sidecar, telling an author two opposite things.

Fixed by giving it a `_SUBJECTS` entry and removing it from the sidecar list, so all four
schema tools now answer for it. `authoring_reference`'s sidecar sentence says it is the one
fact sidecar a human writes rather than carrying an "except" clause.

What was at stake was not cosmetic: `share_alike` / `commercial_use` / `redistribution` are
three independent axes where an empty cell means **unknown** and never *permitted*, and
`sources.csv` is the only input the compile licence gate reads. An author reconstructing that
from the filename gets the licence declaration wrong in the permissive direction. The
candidate fix we rejected — restating the columns in the skill — would have been the exact
drift the "never hardcode a schema fact" rule forbids.

Pointer: `tools/authoring.py::_SUBJECTS` and `list_tables`;
`tests/test_authoring.py::test_sources_csv_is_a_table_kind_not_a_sidecar`. The related
strengthening is worth noting: `test_list_tables_covers_every_draftable_kind` asserted
`all(t.subject and t.keyed_on)`, which the placeholder fallback satisfied — so it passed
while telling an author nothing, and did not notice `sources.csv` arriving. It now names the
placeholders, verified by removing the entry and watching it fail.

## F21 — the skill's `sources.csv` rule was backwards: compliance warned, omission was silent

**Found:** 2026-08-11, compiling `assets/fto_bmi` · **Resolved:** 2026-08-11 ·
**Upstream:** `S23`, released in **0.5.4**

The skill said a missing `sources.csv` row "is a warning, not an error, so it is easy to ship
without noticing". Both halves were wrong for the literature layer, found by doing what it
said — declaring `pubmed` and `europepmc` earned *"sources.csv declares 2 source(s) no table
in this module uses"*, and deleting the file entirely was completely silent.

Upstream's cause: the orphan and undeclared checks both compared `declared` against a
`used_sources` set gathered from the `source` **columns** of the generated tables, and
`studies.csv` has no `source` column by design — the same design that already exempts the
annotation layer. So `pubmed` could never enter `used_sources` and both branches followed
mechanically.

**The harm was the incentive, not the warning.** An author who reads a warning makes it go
away, and the only way to silence this one was to delete a true row, after which the module
carried no record of the literature terms and the compile was clean. Our skill sent them to
write the row; the compiler told them it was superfluous; the tidy resolution was the wrong
one.

0.5.4 puts `literature` into the same exemption as `annotation` whenever the module's
literature evidence is `studies.csv`, and adds the converse warning: a source a fact table
*does* cite with no `sources.csv` row now reports that its terms are unrecorded. Verified on
the real asset's three rows — compliance is silent, omission warns, exactly inverted from
before:

```
0.5.4, studies.csv has rows:  []
same rows, clinvar row removed:
  ["sources.csv has no row for 1 source(s) the module's fact tables cite:
    ['clinvar'] — their terms are unrecorded."]
```

Ours was a doc fix, and the two candidates we rejected are worth keeping on record: telling
authors to omit literature rows to keep compiles clean would have optimised the warning count
and lost the provenance, and suppressing the warning in `to_findings` would have hardcoded a
judgement about which layers are joinable — a schema fact we do not own.

Pointer: `skills/create-module/SKILL.md` §"sources.csv and licensing".

## F23 — the `gene` column was unverified, and it is the column that exposes a fabricated source

**Found:** 2026-08-11, triaging an LLM-written source · **Resolved:** 2026-08-11 ·
**Upstream:** `S24`, released in **0.5.4**

`variants.csv:gene` was checked against nothing, so a deliberately wrong pairing linted
clean: `rs2252481` (chromosome 6) beside gene `NEGR1` (chromosome 1) gave zero errors and
zero warnings. `check_identifiers` did not cover it — it asked HGNC whether the *symbol* was
current and answered `state: "approved"` for `FTO` without ever asking whether `rs1421085`
is in FTO. The two questions read alike in a result payload, which is what made this easy to
believe already handled.

**Why it mattered more than an unchecked free-text column usually would.** This was the
single check that separated the honest half of a machine-written source from the fabricated
half: four of seven rows named a real gene with an rsID on another chromosome, and every
other check passed on each half separately — the rsID resolved, the symbol was approved, only
the *pairing* was false.

0.5.4 adds `IdentifierReport.gene_loci` (a `GeneLocusConflict` per disagreeing row, naming
both chromosomes) and `gene_loci_not_checked`, which exists for the same reason
`clin_sig_not_checked` does: an empty conflict list otherwise says two opposite things,
"compared everything, nothing disagreed" and "never compared". Upstream kept the granularity
at chromosome level on the argument our note made — a variant legitimately names a distal
gene (`rs1421085` sits in an FTO intron and acts on IRX3/IRX5), so an inside-the-gene-body
check would fire on correct rows until somebody disabled it.

**Adopted rather than merely available**, which is the part that closes this: our
`IdentifierReport` carries `gene_locus_conflicts` and `gene_locus_check_skipped`, and
`check_identifiers`' docstring says to read them even when `stale` is empty. Upstream's own
sentence is passed through verbatim rather than reformatted — it already names both
chromosomes and what to do — because a second wording in front of one finding is how two
answers to one question start. **The manual step is out of the skill**: triage step 2 now
names the tool instead of sending an author to a service outside the toolchain, which was the
consequence this finding was filed for.

We were right not to build the lookup here: `identifiers.py` already resolved symbols against
HGNC and `resolution.csv` already carried the chromosome, so upstream held both halves and
the value was entirely in the comparison.

Pointer: `models.IdentifierReport`, `tools/research.py::check_identifiers`;
`tests/test_discovery.py::test_the_gene_locus_conflict_check_reaches_our_model_three_valued`.

## F24 — the suite's hermeticity was a convention with no guard, and a bare `Settings()` read the real `.env`

**Found:** 2026-08-11, while adding tests for the contact-email chain · **Resolved:** 2026-08-12 ·
**No upstream half** — ours entirely

`CLAUDE.md` §6 claimed "the suite is hermetic: every fixture forces `offline=True` and
`_env_file=None`, so no test can reach the network or read a developer's `.env`." The first
half was a mechanism; the second was discipline, and it held only for as long as every
construction remembered the kwarg.

**Re-confirmed live on 2026-08-12 before fixing, and it had got worse.** `.env` by then held a
real polygon token, so from inside the suite under the real `conftest.py`:

```
JMC_TEST_API_KEY in os.environ           : False        # .env never reaches the process env
Settings(_env_file=None).test_api_key    : None         # hermetic, as documented
Settings().test_api_key                  : 'mk_live_…'  # the developer's REAL polygon token
Settings().offline                       : False        # ← worse than the finding said
```

That last line is the part the original note missed: a forgotten kwarg lost **both**
hermeticity properties, so a test could reach the network *while holding a live credential*.
Nothing failed when the kwarg was forgotten — the test simply started reading whatever the
developer happened to have configured, which is the worst failure shape available: it passes
locally, passes in CI where `.env` is absent, and quietly means something different on each
machine.

**Fixed with the mechanism the note proposed**, as an autouse fixture in `tests/conftest.py`
(`_hermetic_configuration`), in two halves because the file is not the only route:

1. `env_file` is pointed at a path that cannot exist. **Not** removed from `model_config` —
   the rejected candidate — because the product genuinely needs it: that is how one `.env`
   serves both this surface and the enricher, and breaking the product to protect the suite is
   the wrong trade.
2. The ecosystem's variables are cleared from `os.environ`, so an *exported* shell variable
   cannot do what the file no longer can.

`delenv` rather than `setenv(VAR, "")` there, which does not contradict §6's rule: that rule is
about `load_dotenv(override=False)` skipping a key that is merely present, and nothing in the
suite calls it. With the dotenv source neutralized, pydantic reads `os.environ` directly, where
absent genuinely means unset. A test that means "no credential" to a reader doing
`x or os.environ.get(...)` still uses `setenv(VAR, "")`, and running after the autouse fixture
it wins.

**The clear-list is derived, not written, and that mattered immediately.** Every field on
`Settings` is readable as `JMC_<FIELD>`, so a hand-written list drifts the first time a setting
is added — and it did, within the same change: the first draft covered the credentials and
missed `JMC_API_KEY_HEADER`, `JMC_TRANSPORT`, `JMC_PORT`, `JMC_HOST`, `JMC_LOG_LEVEL`,
`JMC_REGISTRY_TIMEOUT` and `JMC_TEST_API_KEY_HEADER`. An exported `JMC_API_KEY_HEADER` changes
what `test_the_two_instances_read_different_http_headers` asserts just as effectively as a
token does and far less visibly. Deriving removes the failure mode rather than testing for it;
only the four upstream names — read by code we do not control, so no field of ours can name
them — stay hand-maintained.

Pointer: `tests/conftest.py::_hermetic_configuration`;
`tests/test_modes_and_auth.py::test_a_bare_settings_reads_no_developer_configuration` fails on
the old behaviour by exposing the real token (verified by flipping the fixture to
`autouse=False` and watching it fail), and
`test_the_clear_list_covers_every_variable_settings_reads` pins that the list stays derived.
A companion test records whether this checkout even has a `.env`, so a green suite cannot be
mistaken for proof the leak is closed when there was nothing to leak.

## F33 — our registry floor pinned us below the fix upstream shipped, and `amend_readme` was unwrapped

**Found:** 2026-08-12, publishing `assets/longevity_2026` · **Resolved:** 2026-08-12 ·
**Upstream half:** `F27` / registry `S5`, released in **0.14.0**

The defect was upstream's — a spec-directory `README.md` never reached the module card — and it was
fixed in registry 0.14.0. What was ours: our floor said `>=0.13.0`, so `uv sync` gave us a client
without `amend_readme`, `longevity_2026@1.0.0` had an empty readme, and **our own pin was what kept
us off the fix**. Released upstream, state 2 for us — the exact case the three-states rule exists to
name.

All three pieces of the filed work list are done.

**1. The floor is `just-dna-registry>=0.14.0`**, verified the way the rule requires — by importing the
symbol from the installed package rather than reading a changelog:

```
installed just-dna-registry: 0.14.0
amend_readme present: True
```

**2. `amend_readme` is wrapped** as `registry_amend_readme`, and it earned a wrapper for the reason
the finding gave: the readme sits **outside `artifact.digest`**, so this is the one write against a
published version that spends nothing and can be redone. Everything else about a published version is
permanent.

Two refusals were worth building into it, and both are tested:

- **A path is not prose.** Upstream's `amend_readme(readme=…)` disambiguates a file path from markdown
  *by type*, and every MCP argument arrives as a string — so one collapsed parameter would let
  `readme="spec/README.md"` publish the path itself as the card's text, quietly, on a module whose
  whole problem was an unreadable card. Hence `spec_dir` and `readme_text` as separate arguments, with
  both-at-once refused.
- **An empty body is refused.** The field is last-publish-wins, so empty prose replaces what is there.
  A tool for fixing a blank card must not be able to make one.

The checks that need no credential run **before** `require_key`, matching `registry_publish`'s
order and its stated reason: sending an author to fetch a token for a call that could never have
succeeded is a dead end. The first draft had that backwards and the tests caught it — they were
written to assert refusals and instead got an unauthenticated result.

**Verified on the waiting caller rather than a fixture.** `test-sheep/longevity_2026@1.0.0` on the
polygon went from `readme` of length 0 to 6860 characters, and the artifact digest afterwards was
byte-identical to the one `published.json` recorded at publish time:

```
digest now     : sha256:809facbf…de2f
digest recorded: sha256:809facbf…de2f
unchanged by the readme amend: True
```

That check is the tool's central claim, so it is worth having actually run.

**3. `README.md` is taught.** The skill's directory layout listed `logo.png` as optional and mentioned
no readme at all, so an author following it shipped a blank card. It now names `README.md` as the file
that *becomes* the card, says what to write in it (what the module claims, which population the
evidence came from, what it does not cover), and records that `MODULE.md` is renamed on upload with a
warning while any other spelling is carried but never read.

**A record correction went upstream as registry `S8`.** Their `specfiles.py` comment and changelog
both attribute `MODULE.md` to "`just-module-creator`'s `write_module_md` tool". That tool has never
existed here — no match in the tree, and `git log --all -S` finds none in the history either. It lives
in `just-dna-pipelines`, in a file named `module_creator.py`, which is a good enough reason for the
mix-up. Their rename decision is unaffected and correct; the cost is a wrong address for anyone who
later wants the producer to emit `README.md` at the source.

## F36 — re-drafting a pre-0.6.3 ClinVar panel restores the lost rows and keeps the wrong ones, with nothing to tell them apart

**Severity:** medium · **Status: CLOSED 2026-08-19 — filed as format-tree `S45`, accepted, fixed
and released in enricher 0.6.4 the same day, installed, and adopted here in 0.10.2.** Verified by
driving a real stale-then-re-draft cycle through our own `draft_from_clinvar` and reading the
notice off the tool result, not off their changelog.

Enricher 0.6.3 fixed `multi_allelic_rsids` (upstream `S41`): the site key included `ref`, so an
ordinary ClinVar dup/del mirror pair — `A>AT` beside `ATT>A` at one position — landed in two groups
of one alt each, the rsID was never flagged as multi-allelic, both records reduced to the same
rsid-only identity, and `append_partial_rows` dropped the second as `already_present`. Upstream
measured 725 records lost over five genes, 187 of them dropping the *better*-reviewed half, and said
already-published modules "need a re-draft" while stating plainly that they had not measured that
end to end.

**We measured it, because our surface is where an author performs the remediation.** One gene,
`MLH1`, `min_review_stars=2`, against the local snapshot on installed 0.6.3, drafting three times:
once with the predicate monkeypatched back to 0.6.2 (a stand-in for a pre-fix module), once fresh
with the fix (the ground truth), and then re-drafting the first into its own directory.

| | rows | distinct identities |
|---|---:|---:|
| first draft, 0.6.2 predicate | 996 | — |
| fresh draft, 0.6.3 | 1,030 | 882 |
| re-draft of the first, 0.6.3 | 1,061 | 913 |

`added=65, already_present=965`. Against the ground truth: **0 identities missing** and **31
present that a fresh draft does not contain** — 1,061 − 1,030 = 31, and 913 − 882 = 31. The re-draft
is additive, so it adds the correct coordinate-keyed rows *beside* the collapsed rsid-only rows
rather than retracting them, and the module then states both the right answer and the wrong one for
the same locus. Those 31 are exactly the rows carrying `S41`'s downstream consequence: the surviving
rsID resolves onto both loci and renders the dropped record's coordinate under the survivor's
`clin_sig`, gene and condition.

**The reason it is worth an `F` rather than a changelog line: the stale rows are not findable.** The
obvious predicate — an rsid-only row whose rsID also appears on a coordinate row — finds **0 of 31**,
because `draft_gene_panel` writes no `rsid` onto a coordinate-identity row (327 such rows in both
drafts, none carrying one). No column separates a stale row from a legitimate rsid-only row, so an
author who reads "re-draft" as "re-run the drafter" gets a module worse-formed than either the one
they had or a fresh one, and nothing says so.

**Mitigated as advice, deliberately not as code.** The docstring now says to draft into a *fresh*
directory and reconcile, and says why re-running over the existing file looks like it worked. We do
not attempt detection: we would have to re-query the snapshot to know which rsIDs the current
predicate flags, which is `draft_gene_panel`'s own job and where the fix belongs. Our upstream
candidate is that `append_partial_rows` name those rows on the draft report — it already holds both
halves at merge time — and explicitly **not** that it delete them, since by re-draft time a human may
have curated the `genotype`, `state` and `conclusion` on a drafted row.

**The contrast that names the condition, measured the same day.** The equivalent probe on
`clinpgx_draft` for `S44`'s genotype-gate widening — with a stand-in gate deliberately *broader* than
0.6.2's, so 12,410 rows where the fix gives 18,895 — re-drafts to **18,895 rows, 0 stale, 0 missing**,
exactly the fresh draft. `S44` *skipped* rows; `S41` *wrote them under an identity that has since
moved*. Only the second leaves anything behind, which is why `draft_from_clinpgx` carries the opposite
advice in its docstring and why the two notes must not be collapsed into one rule about drafters.

**How it closed.** `clinvar_draft._superseded_rsid_rows` now names those rows after the append,
counted and aggregated through the house `examples` helper, reading the written file back through
`DraftReport.path`. Confirmed arriving through our tool on the same MLH1 cycle that produced the
numbers above — `added=65, already_present=965`, and the notice naming **31 rows** with five rsIDs and
"and 26 more".

**Our candidate was accepted in substance and corrected on location, and the correction is the part
worth keeping.** We proposed `append_partial_rows`, reasoning that it holds both halves at merge time.
It holds the *file* but not the *predicate*: it is the compiler's generic drafting helper, shared by
every provider, and teaching it about rsIDs would put a source's identity rule into the tier that must
not carry one. The rule belongs in `clinvar_draft`, where the source convention already lives. Worth
remembering the next time we name a layer in a suggestion — "it has the data" is not "it is the right
tier".

**Report-and-never-remove was upheld for our reason**: by re-draft time a drafted row is authored
material, a human may have curated its `genotype`, `state` and `conclusion`, and deleting curated work
to repair a drafting defect is a trade only the author can make. Our fresh-directory advice went into
their reference as the cleaner remediation, with the notice framed as the net for an author who
followed the shorter instruction.

**One thing upstream left open and it is ours to watch.** Neither side re-measured the downstream
label errors — both established only that the rows carrying them survive a re-draft. If a module
drafted after 0.6.4, with its superseded rows deleted, still shows mislabelled expansions, that is a
separate defect and upstream wants it as its own item.

**Still not guarded by a test here, deliberately.** Reproducing it requires monkeypatching an
upstream private predicate to manufacture the old behaviour — a fixture for someone else's
regression, which would fail the day they rename the function and would be testing their fix
rather than our wrapper. Upstream carries three tests for it, including the MLH1 measurement
asserted as a relationship. Ours is the pass-through, and the warning list is already covered.

---

## F48 — a reversed rule reached the docstring and not the message the agent reads while acting

**Found:** 2026-08-20, remediating a real module's quotes · **Resolved:** 2026-08-20, `fdbc5f9`

`CLAUDE.md` §2 reversed the machine-located-quote prohibition, and `211dac5` corrected
`fetch_fulltext`'s docstring to match: *"Retrieve a paper's text so you can read it — and you may
quote it."* The **finding emitted on every retrieval** was not corrected. `discovery._NO_PASSAGE_NOTE`
still read *"a machine-located quote asserts a reading that did not happen. Locate the passage
yourself."*

So the tool handed over the article, told the caller in its description that quoting was
legitimate, and told the same caller in the payload that it was not — the second one arriving
attached to the text itself, at the moment the decision is actually made. Found by being that
caller.

Two smaller sites carried the same inherited claim: `describe_table`'s gloss that
`attestation_bearing` cells *"assert that a **human** read something, so filling one from a fetched
document states something false"*, and `discovery.py`'s own module docstring, whose *never extract a
passage* rule is still correct behaviour and rested on the retired reason.

Fixed in `fdbc5f9`. The note now carries what survives — locate it yourself because relevance to a
row is a judgement about a row nothing here has read; never the article's title, with the
one-string-per-PMID signature named; and the pairing-check cost stated rather than used to refuse.
`discovery.py`'s prohibition keeps its behaviour and gets a reason that is ours: a tool-picked
sentence would be pasted unread, and that is the actual failure.

**The general lesson, and it is not fixed.** A policy reversal reaches docstrings because docstrings
are where a reviewer looks. It does not reach constants like `_NO_PASSAGE_NOTE`, `SourceLicenseNote.note`
or a `Field(description=...)`, which is where an agent reads it under time pressure. Nothing pins the
two against each other, and a grep for the retired sentence was what found this — cheap, and worth
running after any §2 change.

Pointer: `src/just_module_creator/discovery.py`, `_NO_PASSAGE_NOTE` and the module docstring;
`src/just_module_creator/tools/authoring.py`, `describe_table`.
