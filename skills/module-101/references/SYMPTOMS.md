# Symptom → cause → action

| Section | Covers | The skill that owns the fix |
|---|---|---|
| [Authoring and loading](#authoring-and-loading) | placeholders, defaulted columns, ragged rows, vocabularies, the sign warning, an unfiltered star-allele draft | `module-curate`, `module-draft` |
| [Resolution and enrichment](#resolution-and-enrichment) | ref mismatch and the off-by-one, hosting verdicts, expansion, the PAR, a sidecar that did not change | `module-enrich`, `module-refresh` |
| [Validation and compile](#validation-and-compile) | validate-then-compile disagreements, VRS ids, bins, ploidy, the licence gate, the closure warning | `module-compile`, `module-close` |
| [Checks](#checks) | ACMG SF, the `clin_sig` cross-check and its two skip reasons, ClinVar citation ids, a re-draft's superseded rows | `module-check`, `module-refresh` |

Real message text, matched on the distinctive phrase. Most of these cost someone a day.

Messages are quoted as the CLIs print them. The MCP tools surface the same text: compiler findings
arrive in `validate_module`/`compile_module`'s `errors` and `warnings`, row-level findings in
`lint_rows`'s `findings` (with the `level` that decides whether it blocks), and enrichment findings
in `enrich_module`'s `ref_mismatches`, `clin_sig_conflicts` and `stale_rsids`.

An `RMn` in a message is a tracked upstream roadmap item: known and deliberate. Leave the data honest
rather than working around it.

## Authoring and loading

**`unreplaced template placeholder '<<REPLACE>>' in VariantRow row: genotype`**
A scaffolded stub or a drafted partial row still needs a human. This blocks **every** loader, including
`enrich` — deliberately, since forward resolution is allele-aware and a placeholder genotype would skip
that filter. Do not try to enrich first: the draft report already printed the allele pair for each
stubbed row (`genotype for rs…: ClinVar publishes C>T — an allele pair from {C, T}`). Curate from that.

**…`in VariantRow row: genotype, state`** — the same message naming **two** columns
The row is an `uncertain_significance` (or otherwise undecided) ClinVar record, so `state` is stubbed as
well. That is not an omission: no vocabulary member means "undecided", and every candidate asserts
something the submitters did not — `neutral` says the variant is benign, `risk` says a direction. The
draft report explains it once per clinical call and names the affected rows. Decide it per row alongside
the genotype; `risk` for a variant you have reason to treat as actionable, `neutral` for one you have
reason to discount, and if you can justify neither, the honest move is to drop the row rather than pick
a `state` to make the compile pass.

**`Input should be a valid boolean, unable to interpret input` on a column you wrote correctly**
An unquoted comma inside a free-text cell — `conclusion` and `phenotype` invite one — split the row and
shifted every later column left by one, so the error names the wrong column. Since compiler/enricher
0.5.4 the ragged row is reported **first**, ahead of the error it causes, so read the findings in order
rather than jumping to the last one. Quote every free-text cell.

**A finding whose `row` and `line` disagree about the same CSV**
Both are correct and they count differently: `row` is a 0-based index into the *data* rows, `line` is the
1-based file line an editor shows, header included. So data row 1 is line 3. Jump to `line`; quote `row`
when talking about the row itself. `line` is null when upstream could not locate one — it is never
derived from `row`.

**`Input should be a valid string [input_value=None]` on a column you were not told to fill**
A *defaulted* column left empty. An empty cell arrives as `None` and overrides the default. Run
`just-dna-compiler requirements <kind>` — its "never leave empty (defaults)" line names them. A list of
required fields alone is not enough; requiredness has three shapes.

**`ref/alts require chrom and start to also be provided`**
Identity is filled whole or not at all. Either give the complete coordinate or use the rsID alone. A
lone `alts` on a position-only row would make the key a VRS allele id instead of `chrom:start:ref`,
silently changing which variant the row is.

**`direction must be one of ['neutral', 'protective', 'risk', 'unknown'], got: 'increase'`**
`direction` is not a magnitude — it is the same axis as `state`. Every closed vocabulary is printed by
`just-dna-compiler describe <kind>`; do not write one from intuition.

**`state='risk' but weight=1.0 > 0`** — a **warning**, so it still compiles
The sign convention is inverted from the one you probably assumed. `weight` contributes to a
wellness-style score rather than to a hazard, so `risk` wants a **negative** weight and `protective` a
positive one. The same warning exists for `direction`. Nothing refuses on it, so a green compile is not
evidence you got it right.

**`trait_efo_id tokens must be ontology CURIEs`** on a value that is not a trait
Almost always a column shift in a hand-edited CSV. Re-write it with a CSV writer rather than by
splitting on commas — several `conclusion` values contain commas.

**`must be a non-empty haplotype name without whitespace`**
A haplotype name is an identity, not a grammar — `*4`, `e4`, `ε4` are all fine. This fires on an empty
cell or one with a space. Note CPIC's `x≥3` copy-number notation is *not* accepted by the star-allele
pattern the CPIC provider checks, so those rows are skipped and counted (RM5's notation gap).

**`draft --gene CYP2D6` produced thousands of diplotype rows**
Expected without a filter, and the fix is `--allele`: name the star alleles your consumer's caller can
emit and every table is drafted to that set (`*1` is kept automatically). Six alleles turn CYP2D6's
16,290 diplotypes into 21. One `--gene` at a time, because `*2` means a different allele in each gene.

## Resolution and enrichment

**`not in the injected Ensembl snapshot, position remains unset`**
The local snapshot does not contain it — **not** a claim that Ensembl does not. Online, the live link
runs next. Offline, that is the end of the road and the row stays unresolved.

**`cannot host the authored genotype … The event sizes differ`**
A real contradiction, and a decidable one: re-anchoring an indel never changes how many bases it adds or
removes, so this is a different variant sharing the rsID rather than another spelling of yours. One rsID
legitimately covers several records at a locus (`rs281864532` is `G>GT`, `GT>G` *and* `GTT>G`), so check
which record your genotype was written from. Two spellings of *one* indel reconcile automatically —
ClinVar's `X:634689 CAG>C` and Ensembl's `X:634690 AGAG>AG` are the same 2 bp deletion and both resolve.

**`could not be decided here … the same size but different content`**
Not a contradiction and not your mistake: the two spellings describe an event of the same size in
different bases, which is either one indel re-anchored inside a repeat or two different variants, and
telling those apart needs the reference sequence. **The locus is kept** — nothing is dropped and
`--strict` still compiles. Run the enricher (it has sequence access) if you want the ambiguity
resolved; do not edit an allele to silence it.

**`maps to N loci in the resolution table; expanded to N rows`**
Normal for a **paralogous** rsID — one id, several genuinely distinct places. Expected, not an error; do
not delete rows to suppress it. To count *findings* rather than rows, count distinct `rsid` in
`weights.parquet` — the expanded rows keep it.

**`rsN is pseudoautosomal: it maps to 2 loci (X:… and Y:…) that are 1 place(s)`**
A different message for a different situation, and the wording is the point: PAR1/PAR2 are shared
between X and Y, so this is **one place spelled twice**, not two places. You only see it if the table
carries both contigs — `enrich` records the X spelling alone by default, since ClinVar holds no PAR
variant on Y and gnomAD excludes the Y PAR from its callset, so the Y row could match nothing in a
standard (analysis-set-masked) GRCh38 pipeline. Re-run `enrich` without `--keep-par-twin` to record X
only; keep both deliberately if your reference is unmasked. Not an error either way.

**`pseudoautosomal: kept the X spelling of N locus/loci; left out …`** (from `enrich`)
Informational, and printed rather than silent precisely so a table half the size you expected is never a
surprise. The named Y loci are the same places as the X ones kept. `--keep-par-twin` records both.

**`N coordinate-authored row(s) have no rsid in the resolution table, so they stay coordinate-keyed`**
Not an error and usually not worth acting on: a coordinate is a complete identity and an rsID is a label
on top of it, so these rows are fully resolved. Re-run the enricher if you want the labels back-filled.

**`Enrichment is GRCh38-bound; the module declares genome_build='GRCh37'`** (from `enrich`)
Expected, and the only honest answer: resolution and VRS minting have one refget table (**RM15**). No
link runs and **no row is recorded** for anything needing a lookup — not even `not_found`, which would
claim the source was asked. Your authored coordinates are still transcribed, under your own build, and
the module compiles: it keeps build-relative coordinate keys instead of `ga4gh:VA.…` ids. Author
coordinates rather than rsIDs on a non-GRCh38 module, since an rsID is only resolvable against GRCh38.

**`GA4GH VRS allele identity is GRCh38-only (RM15), so N variant(s) are keyed by coordinate instead`**
The companion message at compile time, and it is a statement about the key, not a defect. A coordinate
key is **build-relative** — it will not join against a GRCh38-keyed module — which is true of
coordinates and is said out loud rather than hidden behind an id that looks portable.

**``ref mismatch: N row(s) — coordinate shifted 1 base to the right: `start` is the 1-based VCF position and must not be converted``**
The one to read carefully, because the column it names is not the column you would have guessed. Your
`ref` cells are **right**; your `start` cells are each one too low, which is what subtracting one from a
VCF position produces. `start` is the 1-based VCF POS — the same number Ensembl, dbSNP, ClinVar and
gnomAD show you — and nothing in this pipeline wants an interbase offset. Add one back to every `start`,
delete `resolution.csv`, and re-enrich.

Two things about how this reaches you. It is **not** caught offline: a uniformly shifted module passes
`validate`, passes `compile --strict`, reports `fully_resolved: True`, and mints `ga4gh:VA.…` ids the
compiler then reports as *verified* — a content-addressed id is a correct digest of whatever it is
given, so it certifies the wrong locus perfectly happily. And it is caught here only for the rows where
the neighbouring base differs from your `ref`; roughly one row in four escapes by coincidence, so treat
the count as a floor, not a total. Every id minted for a shifted row names the wrong place and must be
regenerated, not patched.

Then find the source, because the shift arrived with it and will arrive again: UCSC's Table Browser
columns and `pysam`'s `record.start` are 0-based while the same tools' browser display and
`record.pos` are 1-based. `module-curate`'s *The mistake nothing offline can catch* has the full list and
the one-call check that catches it on row 1 instead of row 3,000.

**`ref mismatch: N row(s) — single-base ref disagrees at a position nothing else contradicts`**
The residue after the shift check: the base at your coordinate is not the one you wrote, and neither
neighbour explains it — either the `ref` cell really is wrong, or it is a shifted row whose neighbours
happen to carry the same base so the direction could not be established. If the run also reported a
shift group, assume these belong to it and fix them the same way. The minted id is the true allele *at
the position recorded*, which is only reassuring if the position is right.

**`ref mismatch: N row(s) — multi-base ref disagrees, so the allele spans the wrong bases`**
The corrupting case, and the reason `ref` is checked at all. A multi-base `ref` *sets the interval*, so
a wrong one mints a well-formed id for an allele you did not mean, and nothing downstream can notice.
Fix the row.

All three are **reported, never repaired** — the authored value survives so the evidence of the upstream
mistake is not destroyed — and all three need sequence access, so `--offline` reports nothing here. A
check that could not run is not a check that passed. They are grouped by cause rather than listed per
row, so `N` is a count and only the first few keys are named.

**A sidecar did not change after you edited the spec**
An existing `resolution.csv` / `frequencies.csv` / `gene_metrics.csv` is authoritative and merged.
**Delete the file** and re-run, or stale rows persist silently. This is also the only way to ask whether
an injected `resolution.csv` still agrees with the sources: move it aside, enrich, and compare. The
compiler cannot ask for you — it never fetches, so it takes the table you give it.

**`no gnomAD frequency: [ga4gh:VA.…, …]`** (from `frequencies`)
gnomAD has no record for those alleles, which is ordinary — a GWAS-tag SNP absent from the exome/genome
callset, or a locus gnomAD does not cover. They are recorded as `not_found`, and the rest of the pass is
unaffected. The keys are variant keys, so a resolved substitution appears as its VA digest rather than
its rsID; look it up in `resolution.csv`. Distinct from **`not_covered`**, which means the source cannot
cover that locus at all (the Y PAR) — an absence nobody established is not a finding, and neither status
fails `--strict`.

**`sources.csv has no row for … ['gnomad']`**
A real finding: a source contributed facts and the module records no terms for it. Fixed by
**re-running the pass that consulted it** — `enrich`, `frequencies` and `gene-metrics` each write their
own `sources.csv` row, and merging never clobbers a row you wrote by hand. A `resolution.csv` written
before the `authority` column existed simply says nothing here; re-enrich to fill it.

## Validation and compile

**`validate` says `valid` and `compile` then refuses**
**Check the modes first — that is the likely cause.** Several checks are a ladder: a warning under
`--best-effort` (the default for both commands) and an error under `--strict`. A bare `validate` followed
by `compile --strict` is a pre-flight for the *other* compile, so pass the same flag to both:
`validate spec/ --strict`.
With the modes matched it should not happen, and if it does, that is a bug worth reporting upstream
rather than working around. Two shapes genuinely did on format 0.6.0 — a module with
`frequencies.csv`, and a table-only module with `studies.csv` — both fixed in 0.6.1, which is this
plugin's floor. `validate` covers `resolution.csv`, the four fact sidecars (`licensing.csv`,
`literature.csv`, `frequencies.csv`, `gene_metrics.csv`), the licence gate, the stored `vrs_id`, the
p-value pair, and whether every genotype and `effect_allele` names an allele its locus actually has.
What still only appears at compile is anything computed from *resolved* rows — the expansion and hosting
findings above — because resolution has not run when `validate` does.

**A `pmid` cell holding a PMC id is refused by name**
`PMC 3110566` used to be accepted as PMID 3110566 — a real identifier, for an unrelated article. A
cell that compiled before can refuse now (RM50), and that is the fix rather than a regression: the
row was citing the wrong paper. Look the record up again and write the PMID it actually has.

**A coordinate past its contig's end, or on a contig only the other assembly names**
An error in **both** modes (RM48). `--strict` is deliberately not the switch, because this is
arithmetic rather than judgement — the position cannot exist on the build the module declares. Two
usual causes: the module is GRCh37 data declared as GRCh38, or the coordinate is an off-by-one that
happened to land past the end. `just-dna-enricher hint recover` tells you which rs-number GRCh37
dbSNP records at that coordinate, which usually settles it in one call.

**`effect_allele … is not among the resolved alleles at this locus`**
A `studies.csv` row states an effect relative to an allele the locus cannot host (RM91). A warning
under `--best-effort`, an **error** under `--strict`. Usually the effect allele was copied from a
paper reporting the other strand.

**`--no-resolve switches off resolution entirely, including the injected resolution.csv`**
You passed `--no-resolve` (or `resolve_with_ensembl=False`) with a `resolution.csv` beside the spec. The
flag reads as "do not use Ensembl" and is actually the master switch for resolution of *every* kind, so
the compile succeeds and writes a module whose every row has no `chrom`/`start` — rows no VCF can match.
Drop the flag: consuming an injected table involves no reference and no network either way.

**`allele(s) C are not among the authored alleles at this locus (T/Y) — the genotype is not the problem:
'Y' is an IUPAC ambiguity code`** — a warning under `--best-effort`, an error under `--strict`
The genotype is fine; one cell of `ref`/`alts` is not a nucleotide. Two cases, and the message says which:

* **an IUPAC ambiguity code** (`Y` is C-or-T, `R` is A-or-G, `N` is any base). It records an
  *uncertainty*, so it is never expanded into the alleles it could stand for — expanding would assert
  alleles your source declined to. Write the alleles the locus actually has: if the site really carries
  both, `alts` is `C,T`, and each gets its own `ga4gh:VA.` id.
* **a symbolic or structural allele** (`<DEL>`, a repeat notation). Not a grammar this release holds; the
  variant cannot be expressed as a nucleotide string yet, so leave the row out rather than approximating
  it.

Without this the message blamed the genotype, which sent authors to re-check a correct cell.

**`stored vrs_id ga4gh:VA.… does not match the id recomputed from 11:5225715 G>T`** — an **error in both
modes**, so `--best-effort` will not get you past it
A `ga4gh:VA.…` is content-addressed: for a substitution it is computed from the coordinate and the
alleles alone, with no reference and no network, so the recomputation is deterministic and a
disagreement can only mean the stored id is wrong. Nothing to decide — delete the `vrs_id` cell and let
`vrs mint` write it, or fix whichever of `chrom`/`start`/`ref`/`alts` is wrong. Usual causes are a
hand-built `resolution.csv`, a row copied between variants, or an id kept after the coordinate was
edited.

**`vrs_id ga4gh:VA.… could not be verified — …`** — a warning in both modes
Not the same claim as the one above: nothing was compared, so no verdict was reached. The compiler
cannot recompute an id for an indel, an MNV, an off-assembly contig, or a non-GRCh38 build — justifying
those needs the reference sequence, which this tier never fetches. **Nothing is wrong with your
module**, and `--strict` does not refuse it: the id was minted upstream by the enricher, which does have
sequence access, and it is carried and marked unverified. A multi-allelic row is *not* in that list:
`vrs_id` holds one id per ALT, comma-joined in the same order as `alts`, and each is checked on its own.

**`vrs_id … could not be verified — the row carries no coordinate` / `… against no ALT`** — an error in
both modes
The other half of the same message, and this one *is* about your data. An id is a digest of a place and
an allele, so a row asserting one while recording neither cannot be checked by anything, ever. Re-run
the enricher so the row resolves, or drop the `vrs_id` if the row is meant to stay unresolved.

**`VRS allele identity covers 289/474 allele(s) … Anything keying on the VA sees only the covered
fraction`** — a warning in both modes
Not a defect in the module: it reports how much of your resolution table a `ga4gh:VA.` id actually
names, with the remainder grouped by what each is blocked on. If a line says the ids are *computable
offline*, the mint pass has not run — `just-dna-enricher vrs mint <spec_dir>` fills them. If it says
indel/MNV, re-run that command **without** `--offline`, which is what lets it read the reference
sequence. If it names a build with no refget table, nothing can be done today and the module is fine.
It never refuses, in either mode, because the last two causes are fixable by no edit you could make.

**`p_value '1.2e-14' reads as 1.2e-14, but p_value_num says 1.2e-41`** — a warning under
`--best-effort`, an error under `--strict`
Two encodings of one number disagree, so one is a transcription slip. `p_value` is the free-form record
and `p_value_num` is what a consumer filters on, so the number is usually the one to fix. Compared
relatively at 1%, so a rounding (`5.23e-8` beside `5.2e-8`) is silent — a wrong digit or a wrong power of
ten is not. A string that does not denote one definite value (`<0.001`, `NS`, `5e-8 (adjusted)`) is
skipped in silence and disagrees with nothing.

**`module_spec.yaml is not valid YAML: … line 4, column 10`**
A syntax error in your hand-written spec, with pyyaml's own line and column. The usual causes are an
unclosed `[`/`{`, a tab used for indentation, or an unquoted value containing `:`.
**`module_spec.yaml must be a mapping of top-level keys`** is the neighbour case: the file parses but is
a list or a bare scalar.

**`overlapping bins for key (…)`** — an **error**, so the module cannot compile
Two resolved bins in one group select two phenotypes for one measurement. Check the group key first:
bins are grouped by the kind's key columns **plus** `trait_efo_id`. If two different variants are
colliding in a heteroplasmy table, give each its variant identity (`chrom`/`start`/`ref`/`alts`) — that
is what the key is for.

**`coverage gap … no bin covers (0.099, 0.1)`** on a fraction or percentile
The fix is to **make the bounds touch**: write `0.0–0.1` and `0.1–0.3` rather than `0.0–0.099`. Under
`continuous` tiling two bins may share an endpoint and the higher bin owns it, so a measurement of
exactly `0.1` selects the second row. Author the top bin **closed** (`0.3–1.0`) — the top of that domain
is a real measurement, and `allele_fraction` genuinely ends at `1.0`.

The rule is keyed on **`measure_tiling`**, not on the kind: under `quantised` a shared endpoint is still
an overlap and still an error, because there the bins genuinely both claim that value. The kind only
supplies the *default* — `continuous` for `allele_fraction`/`prs_percentile`, `quantised` for
`repeat_count`/`copy_number`, neither for `activity_score`. Two consequences worth knowing before you
"fix" a gap warning by declaring a tiling: a quantised-default group carrying a **fractional** bound is
read as `continuous` anyway (and the compiler says it did that), and declaring `quantised` on a bounded
fractional domain **switches interior gap reporting off entirely** — the warning stops, and nothing was
repaired.

**`bins with the same lower bound for key (…)`** — an **error**
Two bins in one group start at the same number, so the shared-endpoint rule has nothing to order and a
measurement at that number has two answers. Usually a sharp bin (`0.1–0.1`) written beside the range
that begins there; drop the sharp row or move the range's start.

**`chrom=MT is not diploid here`** / **`chrom=Y is not diploid here`**
A two-allele genotype on a non-diploid contig. Use a single allele (`G`) for a homoplasmic or hemizygous
call. If the locus is in **PAR1 or PAR2** it really is diploid and this does not fire — if it does,
check the coordinate.

**`chrom=Y with two alleles on build 'GRCh37', which has no pseudoautosomal table`**
Ploidy could not be decided on that build. The message names both readings and asserts neither.

**`genome_build is 'GRCh37': … keyed by coordinate instead … build-relative`**
Your identities will not join against GRCh38-keyed data (gnomAD, ClinVar, ClinGen), and the same key
means a different locus on another build. VRS identity is GRCh38-only (RM15). Publish GRCh38
coordinates unless the module is deliberately build-local.

**`inconsistent reference allele`**
Two rows share a key while disagreeing about `ref`. Exactly one can be right — a VRS allele id names the
place and the alt, not the reference base, so this is the only place the contradiction surfaces
offline. An authored `ref` contradicting the *genome* is a different check, and needs the enricher.

**`Star allele(s) used but not defined in haplotypes.csv`**
`allele_function.csv` or `diplotypes.csv` names an allele nothing defines, so a caller can never emit it
and those rows are dead. Either define it or drop the rows. `*1` is exempt — the reference allele is
defined by carrying no variants.

**`diplotype rows … name haplotypes this module defines identically`**
Different names, identical defining-variant sets, disagreeing conclusions — so at most one can be right,
and **phase does not help**. Either the definitions are incomplete or the rows describe one allele under
several names. Distinct from the next entry.

**`diplotype rows … are indistinguishable without phase`**
Same unphased genotype, different conclusions, but the haplotype definitions *do* differ — so phase
resolves it. Correct and expected for a cis/trans pair; a consumer with unphased calls must withhold.

**`sources.csv declares N source(s) no table in this module uses`**
Over-declaration; usually a stale row after you removed a table. Harmless. It also fired
spuriously on the pubmed/europepmc rows of any module carrying `studies.csv` — that was `F21`/`S23`
and it is **fixed as of format 0.6**, so on the current floor this message means what it says.

**`sources.csv is the deprecated spelling of this table and will be removed at 1.0`**
Format 0.6 renamed the file to `licensing.csv`. Nothing is broken: it reads exactly as before, and
`sources.parquet` and `manifest.sources` deliberately keep their names. Rename the CSV. Do not
"finish" the rename into the parquet or the manifest key — a test upstream pins those, because
renaming either breaks every reader.

**`… are the same table in two places, and both are present`**
A module carrying **both** `licensing.csv` and `sources.csv` (or one of them twice, once under
`derived/`). This is an error rather than a warning and there is no correct silent behaviour
available: these tables are fact-hashed and hand-editable, so two copies are two claims, and
preferring either would discard somebody's curation without saying so. Keep one, delete the other,
and keep the spelling the message names.

**`This module records no closure`**
Nothing has stated that authoring is finished, so a consumer cannot tell a spec still being edited
from one its author considers done. Run `close_module` when the module actually *is* done — not to
clear the warning. Editing any authored file afterwards drops the closure again, which is the point.
A warning today; required at format 1.0 (RM73).

**The compile refuses over licensing**
An annotation-layer source forbids sale and the module records no declaration. Draft with
`--use non-commercial` so the terms are recorded, or drop the source. There is no compiler flag for this
by design — a flag cannot survive `reverse`, so the third compile would refuse.

## Checks

**`acmg_sf=false but <GENE> is on ACMG SF v3.3`**
The column is gene-level list membership. If the row is about a variant in a listed gene that is not
itself a reportable finding, leave the cell **blank** — blank means "not stated". ACMG scopes some
entries more narrowly than the gene (HFE is *"c.845G>A; p.C282Y homozygotes only"*).

**`unverifiable: …` and `the list read is ACMG SF v3.2 but v3.3 is published`**
**Not a finding about your module.** You ran `check-acmg` without `--sf-list`, so it fell back to NCBI's
page, which is a release behind — it does not carry `ABCD1`, `CYP27A1` or `PLN`, all of which v3.3
lists. Every disagreement is withheld rather than reported, and `--strict` will not fail on one. To get
an answer, build the snapshot from ACMG's published workbook
(`just-dna-enricher acmg build <workbook.xlsx> --out acmg/`) and re-run with `--sf-list acmg/`, which
also works `--offline`.

**A note saying a gene is listed and `acmg_sf` is blank**
Informational, never a defect, and `--strict` does not escalate it. Blank is a legitimate answer.

**`clin_sig cross-check not run: this module declares it was drafted from the very snapshot the check
reads`**
Working as intended, and more honest than the alternative. Your `panel:` block pins the release the
rows were drafted from, and it is the release the check would compare them against — so every value
would be matched with its own source and the answer would be zero conflicts whatever the data said. A
guaranteed zero looks like evidence without being any. The moment a human edits those calls, drop or
change the pin and the check runs again. `--no-verify-clinsig` is the manual switch and reports
`not_requested`.

**`clin_sig cross-check not run: no ClinVar snapshot this run`**
Different sentence, different meaning: nothing was compared because there was nothing to compare
against. Provision a snapshot (`just-dna-enricher cache pull --only clinvar`) or pass
`--clinvar-cache`. An unasked question is never a passed check.

**`N ClinVar citation(s) skipped: the id ClinVar filed under PubMed is not a PMID`**
A defect in the source, not in your module, and nothing to fix by hand: a few hundred of ClinVar's
citation ids are nine digits where a PMID is eight. They are counted rather than listed, and the
remaining citations for the same variant are drafted normally. Rebuilding the snapshot from a current
`clinvar citations` drops them at the source. Reported apart from the `--max-citations` line, which is
about a cap you chose.

**`N row(s) on non-diploid contigs were written with a single-allele genotype`**
Not a warning about a mistake — it is the provider telling you which cells it filled. MT is haploid and
chrY outside the pseudoautosomal regions is hemizygous, so exactly one genotype is expressible and
nothing was pre-empted. Those rows read as homoplasmic/hemizygous; if you mean a heteroplasmic
*fraction*, that is `heteroplasmy.csv`, not a second allele here. A chrY row *inside* PAR1/PAR2 keeps
its placeholder, because there the locus really is diploid.

**`chrom=MT is not diploid here — use a single-allele genotype`**
You (or a tool of your own) wrote `A/G` where only one copy exists. Write the single allele. The same
message covers chrY outside PAR1/PAR2; inside them a pair is correct and no warning is emitted.

**`clin_sig` differs from ClinVar's** and `--strict` did not fail
Deliberate. Two opinions differing is not a factual error, and ClinVar is not truth — a curator who has
read the primary literature may correctly disagree with a one-star submission. The finding carries
ClinVar's review-star count so you can weigh it. The allele-function check behaves the same way.

**`N row(s) already in variants.csv identify by rsID alone … this run writes those rsIDs with their full coordinate`**
Your module was drafted before enricher 0.6.3, when the drafter keyed a site on `ref` and an ordinary
dup/del mirror pair (`A>AT` beside `ATT>A` at one position) collapsed onto a single rsid-only row —
the second ClinVar record was dropped, in silence, and which one survived was decided by allele
spelling rather than by review stars. Re-drafting recovered every dropped record; it did **not**
retract the collapsed row, because drafting appends and never mutates. So the module now carries both
the coordinate-keyed replacements and the row they replace, and the stale one is the row that
resolution expands onto every locus its rsID reaches, wearing the survivor's `clin_sig`, gene and
condition.

**Action: delete each named row once the coordinate rows cover its records.** The drafter will not do
it for you and should not — by re-draft time that row is authored material and you may have curated
its `genotype`, `state` or `conclusion`. Nothing in the file can find these rows on its own (a
coordinate row carries no `rsid`), so this warning is the only signal; do not filter it. Drafting into
a fresh directory and reconciling is the cleaner remediation if you have not already re-run in place.

**A wall of near-identical warnings**
Should not happen; findings aggregate per gene with a count and examples. If you see one, that is a bug
worth reporting upstream rather than filtering.
