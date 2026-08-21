# Changelog

What actually shipped, newest first. Includes cross-repo integration changes made
on our side, so agents in sibling repos are not surprised.

## 0.16.0 — 0.6.6 adopted: four restatements retire, and one of ours contradicted itself

**Format / compiler / enricher 0.6.1–0.6.4 → 0.6.6, floors raised, adopted 2026-08-21.** The three
moved back into lockstep at 0.6.5 and 0.6.6 is the patch round after it. Nine `F<n>` of ours close on
it — `S47`, `S48`, `S49`, `S50`, `S51`, `S54`, `S55`, `S56`, `S57` — which is what filing at the
moment of discovery buys: every one was written in a single day's work five days earlier.

### Four maps we restated are now generated, and the fourth had teeth

- **`hints.DERIVED_TABLE_MODELS`** (`S47`) replaces `_PRODUCED_MODELS` *and* the roster, which had been
  borrowed from the registry so it could grow by itself while the models stayed by hand. One source
  now, and it is the compiler's own loader tuple. The `describe_machine_table` arm for a table that is
  real and undescribable by this build is gone with it: the two halves can no longer disagree.
- **`hints.key_fields`** (`S48`) replaces the `keyed_on` half of `_SUBJECTS` — the hand-kept string
  that named `modifier_cn` for all of 0.6 after upstream deprecated it, which is what the report was
  about. `list_tables` gains `key_rule` and both `describe_table` and `describe_machine_table` carry
  the whole `key` block, because `equality`, `overlap` and `subject` are three different claims about
  what a repeated key means and one string could only imply one of them.
- **`scaffold.companions_for`** (`S49`) applies the conditional half of the companion mapping and is
  what `scaffold_module` itself uses, so our answer and the act cannot disagree. Scaffolding a binning
  module beside `studies.csv` no longer invites an empty `variants.csv` that compiles strict-green
  while asserting nothing.
- **`hints.key_fields` again, for `refresh_sidecar`** (`S51`), and this is the one that changed
  behaviour rather than tidying it. Row identity there approximated each pass's merge key and was
  *different* on the two tables where one subject carries several rows: `clinical_assertions.csv` was
  keyed `(variant_key, dataset)` against a real key of `(variant_key, variation_id)`, so two ClinVar
  assertions on one variant collapsed into one subject and were **reported as a conflict**; and
  `gene_validity.csv` on `(gene, dataset)` against `assertion_id`, whose two-level fallback we had no
  way to express at all.

### `compare_modules` reported thirteen changed rows and no content change, in one payload

`authored_tables` read each CSV directly and never folded the spec's `defaults:` block. A `curator`
written on every row in one version and declared once under `defaults:` in the next is the same
content — `content_signature` says so — and the report came back `content: same` beside thirteen rows
changed on `curator` and `method`. Measured on a pair built from `hfe_hemochromatosis`: identical
digest, thirteen rows moved.

That is the defect we filed against upstream's `lookup_variant` the day before (`S61`), on our side of
the boundary this time: a finding that contradicts the data teaches the reader to discount findings.
`compiler.spec_tables` (`S53`) returns the folded rows, which is exactly what this needed and had no
public way to get — the fold lives in two private symbols and reimplementing it is what produces the
wrong answer.

### The one new authored column in the whole range

**`StudyRow.curator`** (`S55`) — who located this row's quote, on the table where the attestation
lives. `find-evidence` and the `studies.csv` dossier tell an author to fill it and say the two things
that keep it honest: it is free text resolvable against `authorship` rather than a `machine_located`
boolean, and **nothing checks it**, because it is legible to a reviewer routing scrutiny and not to a
gate. Responsibility stays with the human author however the cell is filled.

**`ProvenanceItem.outranks`** (`S52`) is written by `record_override`, so the column a row disagrees
with is legible to a reader who is not us. The marker stays and is not a duplicate: it carries the
digest binding the record to the cell, which source was disagreed with, when and by whom. The *check*
half — whether a mismatch is downgraded on the strength of a record — did not ship and is not assumed:
a record still downgrades nothing and passes nothing.

**`titles_as_quotes`** (`S54`) is surfaced on `LiteratureReport` with a warning naming the PMIDs. Ours
and theirs both stay: theirs runs in the pass and answers for a pinned sidecar row, ours runs in
`lint_rows` and `validate_module` before any pass has. The four modules that provoked the finding have
every row pinned, so a check living in the fetch loop would have fired on none of the 3668 quotes it
was written for.

### Three behaviours changed for anyone recompiling

Stated in the skills where they land, because none of them reaches an already-published module — a
manifest is written at compile time.

- **A duplicate `(source, layer)` row in `licensing.csv` is an error** in validate and compile both
  (RM107). An inherited module carrying one stops compiling, which is the pair being noticed rather
  than the module breaking; `merge_sources_csv` keeps the **last** row under the key, so it is the
  wrong tool exactly where the two rows disagree.
- **`manifest.stats` describes the module** (RM121), so a recompiled PGx, copy-number or binning
  module becomes findable by gene. Thirteen passages across nine files said otherwise. A `pgs`-led
  module is the one shape it does not reach — `PgsRow` has no `gene` column to contribute.
- **The `faf95` warning is published once** (RM106), so a recompile publishes one fewer warning with
  no text changed.

Five other guards come out — `RM104` (the gene-metrics re-run raised `UnboundLocalError`), `RM105`
(`logo.jpeg` was attested and never uploaded; **re-publish a module that shipped one**), `RM109` (a
`source="manual"` row now suppresses the fetch, though a duplicate pair written earlier is still in
the file), `RM111` (three strings claiming a registry override of `license`, two of them
`Field(description=…)` that reach authors through our own tools) and `RM123` (a redundancy advisory
now says when its checker cannot see your table). **`RM108` and `RM110` stay open as minors and their
guards stay live.**

The `lookup_variant` snapshot-miss strings lost their trailing clause and `position remains unset` is
its own finding now (`S61`), so `SYMPTOMS.md` carries all three phrases and says which to grep for.

### Also in 0.16.0 — three quarters of the server's instructions were never reaching the model

**`Server instructions truncated from 9220 to 2048 chars`.** Found in Claude Code's own MCP debug log
while diagnosing an unrelated startup timeout. Nothing on our side raises, so this had been true for
every release that grew the text: the cut landed mid-rule-3, leaving the surviving instructions ending
on *"A mismatch against a source is not a defect report. Archi"*, and **every registry rule was absent**
— the polygon default, the irreversibility of production, the explicit-yes before promoting. A surface
whose entire job is to carry those rules was not carrying them.

**Dried to 2020 characters, and the rules are all still there.** The fix was not fewer rules but moving
the *procedure* out to the skills that already owned it — `module-publish` holds the two instances,
`find-evidence` the PMID and quote rules, `module-start` the email consent, `module-curate` the
1-based trap. Each fact was checked to have a home before it was cut. What is left is the map, the
taught order, and the six rules no skill may soften, ending in a pointer to `module-101`.
`test_the_instructions_fit_in_what_the_host_will_actually_keep` holds the budget with 24 characters
held back, because the text interpolates two version numbers and `0.10.12` is longer than `0.6.1`.

**Cold-start timeout, diagnosed and documented.** A first launch on a fresh install has to create the
venv and build the package; that overran a 30 s connect limit by 4 ms, and the retry connected in
3180 ms. Both manifests now set `UV_LINK_MODE=copy`, which is read by the `uv` we spawn — the plugin
cache and uv's cache sit on different filesystems, so uv was attempting a hardlink, failing, warning,
and falling back to a full copy. The README says how to warm the environment after an install, where
the MCP logs live, and that **`MCP_TIMEOUT` is read from the client's environment and cannot be set per
server in a manifest** — so we do not pretend to set it.

**Three places still called this a Claude-only plugin with one skill**: `pyproject.toml`'s packaging
summary, `docs/DOMAIN.md`, and `CLAUDE.md`'s own opening sentence. README prose was already dual.

## 0.15.0 — a module can run on a genome without a registry

**465 tests. Nineteen skills.** Everything below was already written up in the three sections that
follow; this is what the release is *for*.

**`module-install-local` — the third destination.** Until now the shortest honest path from *"it
compiled"* to *"it matched something real"* ran through a polygon publish, which costs a namespace, a
token and a name you have to live with. It does not have to. A compiled module can be registered into a
local `just-dna-lite` install and annotated against a real VCF with no registry in the loop. Verified
end to end against `assets/fto_bmi` compiled by our own `compile_module`: discovered with
`lead = weights`, position join, provenance read straight off the manifest. **Our artifacts need no
adjustment to be consumable.** The skill is explicit that this verifies nothing and is not a rehearsal
for publishing — it exercises the annotation seam where the polygon exercises the registry one.

**Three defects that were all the same shape: a claim nothing read.** The plugin listing named four
literature sources while six ship (OpenAlex and Crossref landed in 0.14.0, the version the manifest
declared). `CLAUDE.md`'s asset table had never learned `module-status` or `module-symptom`, so an agent
reading the roster would conclude the two doors did not exist. The README told Codex users about
sixteen skills that were eighteen, and called all of them commands when eight are. None of these could
fail, because nothing checked them. All three now have guards derived from the code —
`discovery.SEARCHABLE` and the skills directory — and the roster guard caught `module-install-local`'s
own omission within the hour of being written.

**`check_identifiers` no longer returns a traceback on a real path**, and argument checks precede the
offline ceiling there as they already did elsewhere. **arXiv stopped ORing query words**, which had made
every multi-word preprint search return noise, and **`paper_citations` stopped reading `cited_by` as its
own opposite**. All three were found by running the tools against real identifiers rather than by
reading code.

**Filed upstream this cycle:** `S61` to the format tree (`lookup_variant` returning a correct coordinate
and a *"position remains unset"* finding in one payload), and — through the unnumbered handoff channel,
which `CLAUDE.md` §8 now names as the third intake — the missing CLI wrapper for
`register_downloaded_module`, plus two probe-to-learn findings and two stale doc lines.

## Unreleased — the lookup, check and registry surfaces exercised live

**`module-install-local` — the third destination.** Nineteen skills. Until now the shortest honest path
from *"it compiled"* to *"it matched something real"* ran through a polygon publish, which costs a
namespace, a token and a name you have to live with. It does not have to: a compiled module can be
registered into a local `just-dna-lite` install and annotated against a real VCF with no registry
involved at all. The skill teaches the three routes in, which one preserves the `artifact_digest` you
tested (only the one that does not recompile), and the two failure modes that are silent.

**Measured, not inferred.** `assets/fto_bmi` compiled through `compile_module` and put in front of
-lite's own discovery with a scratch `JUST_DNA_MODULES_YAML` and `--no-sync`, so nothing in that tree
was touched: discovered with `lead = weights`, `_lead_join_strategy` → `('position', 'lead table
carries coordinates')`, 3 rows scanned, `read_module_provenance` → `('1.0.0', 'sha256:c3d633f0…',
None)`. **A module this plugin compiles is annotatable as-is.** Also settled a worry that looked real:
a locally compiled manifest carries `identity.namespace: null`, and local discovery keys on the
directory name and never reads it, so the missing namespace costs nothing.

**What the skill refuses to sell.** -lite calls `just_dna_format.integrity.verify_manifest` nowhere and
recomputes no hash on the annotation path — their own spec says so under *"specified, NOT
implemented"*, and we quote them rather than paraphrase. So the skill states plainly that a local
install verifies nothing and that a clean annotation run is not evidence the module is correct — the
same rule as a green compile, in a new place. It also says what it is *not*: the polygon exercises the
registry seam, this exercises the annotation seam, and neither substitutes for the other.

**Filed with the -lite team**, in the handoff doc that already exists rather than a numbered series
they never agreed to run: `register_downloaded_module` is the right function and has no CLI wrapper, so
our skill currently ships a `python -c` that reaches past their CLI into an internal — which we would
rather not do. Plus two probe-to-learn findings (a partial `manifest.artifact.files` makes a module
invisible while `list-custom` still lists it; name collisions resolve to the earliest source silently)
and two stale doc lines.

**The roster guard that caught its own successor.** `CLAUDE.md`'s asset table had never learned
`module-status` or `module-symptom`, so "sixteen skills" was right about the table and wrong about the
directory. Fixed, and `tests/test_skills.py` now pins the roster against the directory — it failed on
`module-install-local` within the hour, which is the whole point. The manifest description had the same
shape of bug: it named four literature sources while six ship, OpenAlex and Crossref having landed in
0.14.0, the version the manifest declares. Also guarded now, derived from `discovery.SEARCHABLE`.

**458 tests.** Everything below was found by running tools against real identifiers and the real
instances, not by reading code. One defect was ours and shipped; one is upstream's and is filed.

**`check_identifiers` was broken on a real path, and it was mine.** Shipped in 0.13.0 with the "does
not apply" case *computed and then not acted on*: the underlying call raises `ValueError` on a missing
`variants.csv`, so a module without one got a raw traceback where it should have got the considered
answer. Now it returns early, before the call. A malformed-but-present file is a third state and gets
the row and column (*"variants.csv line 2 [genotype]: Field required"*) rather than a stack trace, and
neither path writes anything. Verified live in both directions: **0 records → 3** on a real module
(`gene_locus_agreement` 13 subjects, `gene_symbol_currency` 1, `trait_currency` 0 with
`skipped=nothing_to_check` — the tri-state doing its job), existing closure preserved, and **no
`verification.json` created** on the module that never asked.

**Argument checks now precede the offline ceiling** there too, matching `registry_publish`'s naming
refusal and `paper_citations`: what is decidable without a network is decided first, so nobody is told
"you are offline" about a call that could never have succeeded.

**Filed upstream as `S61`:** `lookup_variant` returns, in one payload, `loci` carrying the correct
live coordinate **and** a finding reading *"position remains unset"*. The warning is the cache stage's
and nothing revisits it after the live lookup fills the gap. On a surface whose discipline is that a
warning on a green run is the interesting output, a warning that contradicts its own payload teaches
the reader to discount warnings.

**Confirmed working:** `lookup_variant` resolves `rs4988235` → 2:135851076 G>A and `rs1799945` →
6:26090951 C>G, `rsid_state: live`. `lookup_identifier` reports `MCM6` approved and `FAM58A` **retired
→ CCNQ**, a real HGNC rename. Both registry instances answer, serve **0.18.2**, and confirm their own
mode, so `mode_matches_target` is `True` rather than assumed; the polygon token resolves to account
`sheep` / namespace `test-sheep`.

**Workspace fact corrected:** production holds **seven** modules, not five — `CLAUDE.md` said five for
a day, which is precisely the staleness that line warns about. Two are new, and one is from a
namespace that did not previously exist.

## Unreleased — the literature surface was exercised live, end to end

Every literature tool run against real identifiers rather than fixtures. **454 tests.** What follows
is what the exercise found; the arXiv defect below was the largest.

**Confirmed working, and worth recording because none of it had been shown before:**
`literature_search` dispatches all six sources and `merge` combines across them — Enattah 2002
(`11788828`) arrives as **one** candidate carrying pubmed + europepmc + crossref. A Semantic Scholar
429 is reported `results=null, rate_limited=true` with the *"UNCHECKED, not empty"* warning rather
than as a zero. `lookup_open_access(pmid=…)` resolves the DOI through Europe PMC first and then asks
Unpaywall, both reporting `queried=true`, so its `false` is a real answer rather than a silent skip —
that was checked specifically because a `false` from a source that was never asked would be the
`F6` failure. `fetch_fulltext` returns `text_source=fulltext` for an open-access paper and
`text_source=abstract` for a closed one, which is the distinction that keeps an abstract miss from
reading as a verdict. `lookup_citation` withholds `doi` and publishes the same value as
`registry_doi`, so the refusal does not hide the number — it keeps it out of the field an agent would
copy.

**`paper_citations`: the `cited_by` spelling reads as its own opposite.** Everywhere else in
bibliometrics "cited by" labels the citations a paper *received* — Scholar's "Cited by 1,234" — and
here it means the works in its own bibliography. The docstring was already correct ("cited by it");
the token alone was not, and the token is what an agent passes. `references` and `cites` are now
accepted as unambiguous spellings, **`cited_by` still works** because the tool surface is a contract
and a dropped spelling breaks a caller silently, and the docstring leads with the trap.

**Argument validation now runs before the offline ceiling** in `paper_citations`. A bad `direction`
was answered with "the server is configured offline", which sends the caller to fix the wrong thing —
the same dead end `registry_publish`'s naming refusal already avoids by checking the decidable thing
first. Found because a test asserting the direction message could not reach it.

**Measured and not a defect:** Semantic Scholar returns **zero** references for Enattah 2002 — its
own API, HTTP 200, empty. The paper obviously has a bibliography; S2's coverage of older closed
literature does not. The docstring already says a short list is weak evidence of little citation
rather than proof of none. And `fetch_fulltext` output opens with ~411 characters of JATS front
matter (ISSNs, PMC ids) before the title, which only bites a caller passing a small `max_chars`;
the default is `None`, meaning no limit.

## Unreleased — the arXiv leg was returning noise, and only a live run showed it

**Found by dogfooding the shipped surface, not by reading it or testing it.** Asked whether the
literature features had been exercised with live queries, they had not — parsers were validated
against real payloads and raw calls made to capture fixtures, but `literature_search` itself had
never been run end to end. Running it returned, among lactase-persistence hits, a **particle-physics
paper**: *"Observation of the rare B⁰ₛ→μ⁺μ⁻ decay"*.

**Cause.** The shared query string is PubMed-flavoured — parenthesised groups joined by `AND`, plus a
`2019:3000[dp]` date clause — and it was handed to arXiv behind a bare `all:` prefix. arXiv splits an
unquoted `all:` value on whitespace and ORs the words, so `all:lactase persistence` matched on
*persistence* alone. Measured directly: four of four hits were topology and statistics papers, none
about lactase. **Every multi-word query had been returning noise since the arXiv leg was written.**

**No fixture test could have caught this**, and that is the part worth keeping: the fixture was
captured with a query chosen by whoever wrote the test, so it agreed with itself. The defect lived in
the *request*, and every test here checked the *response*.

**Fix.** `arxiv_query()` translates rather than forwards: each parenthesised group becomes its own
quoted phrase joined with arXiv's `AND`, the PubMed date clause is dropped because arXiv has no
equivalent field, and an embedded quote is stripped so it cannot close the phrase early and silently
change the search. Measured after: the same query returns a population-genetics preprint on IBD tracts
and runs of homozygosity, and the query that produced the physics paper now returns **zero** preprint
hits — which is the honest answer, arXiv having little on lactase.

Live end-to-end run also confirms the rest of the surface behaves: all six sources dispatch, `merge`
combines correctly across them (Enattah 2002 arrives as one candidate carrying pubmed + europepmc +
crossref), and a Semantic Scholar 429 is reported as `results=null, rate_limited=true` with the
*"UNCHECKED, not empty"* warning rather than as a zero.

## 0.14.0 — OpenAlex and Crossref, ported rather than depended on

Five literature sources become seven. **452 tests**, ruff clean, pyright 0 errors. Version bumped in
all three files. No upstream floor moves.

**`RM23` shipped as a port.** The evaluation ranked three shapes — depend on `paper-search-mcp`, fork
it with a `[scihub]` extra, or port the two sources we actually wanted — and the port won because it
is the only one where the Sci-Hub question **stops existing** instead of being managed. The fact that
settled it: `download_with_fallback(..., use_scihub: bool = True)` at their `server.py:763` is
**default-on**, against their own README, and a wheel ships every module whether imported or not.

What was taken is **API knowledge**: endpoints, parameter names, response shapes, and OpenAlex's
inverted-index abstract encoding. Not the code — theirs calls `requests` directly with a hardcoded
contact, and both are rules here. `NOTICE` carries their MIT text byte-identical to their `LICENSE`,
and a test pins the attribution, because attribution living only in a comment is one refactor from
vanishing and that is a licence violation rather than an untidiness.

**Two of their defects were fixed in the port rather than inherited.** Their polite-pool contacts are
the literals `openags@example.com` and `paper-search@example.org`; ours resolve through the three-step
chain, and a test forbids the literals returning in a quoted position. Their `Paper.citations: int = 0`
types "not reported" as zero; ours is `int | None`, and Crossref's absent open-access verdict stays
`None` rather than becoming `False` — Crossref says nothing about OA, so `False` would be a claim it
never made.

**One defect found by using the parser rather than reading it:** Crossref carries HTML entities in
`container-title` as well as in titles, so a real record's venue arrived as `http://isrctn.org/&gt;`.
Routed through `_title`, the decoder the Europe PMC parser already used. The test asserts the fixture
really contains entities, so it cannot pass vacuously.

Fixtures are real captured responses to the request `Discovery` actually makes, contact included.
Two tests that hardcoded "four searchable sources" now derive from `SEARCHABLE` — the hand-kept-list
rot, caught in a test.

**What we gave up:** seven further sources (CORE, DOAJ, Zenodo, HAL, OpenAIRE, BASE, dblp), and two
clients are ours to maintain. Their suite covered neither of the two we took.

**`RM24` is answered by construction** for these two: a ported client goes through our gate, so there
is no unpaced third-party transport. It stays deferred for anything not yet taken.

## Unreleased — logs get read before the catalog keeps them

**`RM25` shipped.** `logscan.py`, a `review_logs` tool, and a warning inside `registry_publish` so it
fires at the one moment the decision can still be made. **443 tests**, ruff clean, pyright 0 errors.

`_collect_logs` runs on every compile with no flag and no opt-out, so any `*.log` in a spec directory
is hashed into the manifest and uploaded — and a published version is immutable, with `yank`
delisting rather than removing. That sweep is correct as designed; what was missing was anyone
looking first.

**Calibrated on real data in both directions, which is the part worth keeping.** The true negative is
`assets/logs/quote-remediation.log` — a real log that really travelled to two polygon rehearsals —
and it returns **zero** findings. The true positive is a real submitted bundle's transcript
(`chd_depression_v1.zip`, 450 KB): **16** findings, three absolute paths shaped like
`/tmp/module_spec_szu7uiko` and thirteen lines up to **8304 characters**, the embedded-system-prompt
signature. The clean fixture tops out at 92 characters, so neither is a close call.

The one measured false positive was designed out before the code was written: the fixture contains
*"every rsID token"*, so credential detection matches a **shape** — a name, an assignment, a value of
real length — and never a wordlist. A finding also never reprints the whole line, because this output
is read by an agent whose transcript is itself retained.

**It reports and never strips, and it refuses nothing.** A log is a provenance record; publishing a
flagged one is often right and is the author's call.

**Five roadmap items closed to history** with their verdicts: `RM9`, `RM19`, `RM20`, `RM21`, `RM22`.
`RM24` deferred by the owner — timing, not substance; do not open the upstream issue without asking.

**`RM23` evaluated, and the recommendation changed.** Licence confirmed MIT. The finding that decides
it: `download_with_fallback(..., use_scihub: bool = True)` — **default on**, contradicting that
project's own README. Verified independently, as were the other two load-bearing claims: zero
`sci.?hub` references across all ten platform modules and all four substrate files, so vendoring is
clean; and fabricated polite-pool contacts (`mailto:openags@example.com`,
`paper-search@example.org`) that §5 forbids outright. Recommendation is now **vendor OpenAlex and
Crossref only** — 661 lines, MIT-attributed, rewritten onto `ServiceGate` — which is the one option
where the Sci-Hub question stops existing rather than being managed, and which takes the split NCBI
budget, the second HTTP stack, an import-time `.env` mutation and an `F6` tri-state loss out with it.

## 0.13.0 — four roadmap items ship, and the skill surface gets a front door

Version bumped in all three files (`pyproject.toml` and both plugin manifests). **431 tests**,
`ruff` clean, `pyright` 0 errors. No upstream floor moves: format/compiler stay 0.6.1, enricher
0.6.4, registry 0.18.2.

**`RM9` — the check tools moved out, rather than the promise being narrowed.** `tools/research.py`
opens with *"no tool in this module writes to a spec directory"*, which was true and quietly costing
something: `check_identifiers` lived there and therefore left no trace, so a module authored entirely
through this server showed nothing where a CLI-driven author's showed a record. The alternative was to
soften the sentence to "writes no authored cell" — upstream's own wording — and it was **rejected**: a
module whose opening line is a literal claim keeps it literal. New `tools/checks.py` writes the
attestation and says so in its first line.

What it writes is an attestation, never a value, and it follows the enricher's own three rules rather
than inventing any: a module with **no `variants.csv` gets no record** (the check does not *apply*,
which is not a skip, and writing one would mine a nonce onto a module that never asked); an
**outage is attested too**, because that is the run where the report is empty and an empty report
with no record reads exactly like a clean one; and **one call for every record**, since the
proof-of-work binds the whole document. `check_genes` / `check_traits` are now arguments and are
recorded, so narrowing a run narrows what the record claims. Tier unchanged — the tier line is cost,
not read-versus-write.

**`RM19` — `compare_to_published`.** One or two bounded GETs, no download: `resolve_version` when the
version is `latest`, then the manifest. It compares `content_signature`, per-file digests, every
fact-signature block, and the metadata outside every hash, and it **hands over** rather than
escalating — `registry_download` + `compare_modules` for row detail.

One defect found by testing rather than by reading: the design specified `compiler.file_entries` for
the per-file layer, and the publisher actually hashes through `authored_input_entries`, which
**normalizes newlines**. Measured on the HFE reference example, the raw hasher disagrees with the
published entry on two of three files — so the first implementation would have reported a byte
difference on every module authored on a machine whose newlines differ, forever. Upstream states the
reason that function is public: *"two tiers must agree on it byte for byte."*

**`RM21` — `registry_yank` / `registry_unyank`.** The client had both and we wrapped neither, so an
agent that published a mistake had no route back and the bad version stayed at `latest`. Token-gated
like every registry write, defaulting to the polygon like every other one — an unaimed yank that
silently delisted a production version would be the same class of mistake the tool exists to recover
from. The wording refuses to let it read as a fix: it stops a version being recommended, corrects
nothing, does not release the content claim, and the fixed publish is a separate act.

**`RM22` — `study_facts`.** The enricher already fetches the GWAS Catalog's `ancestry` into
`gwas_effects.csv`, and nothing surfaced it, so `studies.csv`'s `population` was being written from
memory — a published module carries `"Nagel M et al. — GWAS Catalog GCST006941"` in every
`population` cell, a citation label in a column that wanted a cohort, by an author who had the cohort
in the next file over. Surfaced and never filled: the Catalog frequently answers with several
ancestries at once, so which applies to a row is a judgement. `find-evidence` now says where the
answer is.

**Two new skills and eight commands (`RM20`).** `module-status` answers *where is this module and
what is the next decision* — the lifecycle was spread across eight stage skills and nothing answered
it. `module-symptom` is the front door to `SYMPTOMS.md`, which previously required loading
`module-101` and knowing to look. Eight commands, not sixteen: a command is what somebody
deliberately types to start something, never a stage an agent walks through. A test pins the set and
another keeps a command thin enough to stay a router.

**Upstream: `S60` was answered the same night** — accepted as their **RM124 for 0.7**, and it
unblocks their RM83. They also report `S51` shipped as RM115 and cut as **0.6.5**, which would make
our derived sidecar subject keys stale on four of seven tables. **Not adopted: 0.6.5 is not on PyPI**
(0.6.1 is the newest published), so this is §8's *fixed in tree, not released* state and our
derivation stays.

**`RM23` / `RM24` filed** on adopting a 25-source literature library, and `RM23`'s first draft was
corrected the same day: it led with `JMC_OFFLINE` as the objection to bundling, and that was a niche
capability vetoing a broad improvement. Offline belongs to annotation-time, where a genome is being
read — not to author-time, which is networked by nature. The objection that stands on its own is the
shared NCBI budget.

## Unreleased — two untested parsers get real fixtures, and a paywall stops being a dead end

No tool change, so no version bump: tests, fixtures and documents only. Suite **385 → 391**;
`ruff` clean, `pyright` 0 errors.

**`RM6` closed, and its premise was stale.** `parse_semantic_scholar` and `parse_arxiv` had no
fixture and no test since 2026-08-11, on the finding that both services 429 this host at IP level.
Re-probed through `Discovery` itself — the same endpoint, params and pacing the client uses, not a
curl approximation — **arXiv answers 200** and Semantic Scholar's throttle is intermittent and
endpoint-specific (`paper/search` sheds load, `paper/{id}` does not). arXiv had a real rate-limit
incident in late February 2026 which its maintainers acknowledged and fixed; we measured inside that
window and carried the conclusion for six months without re-probing.

Both fixtures are now committed, each a genuine response to the request the client actually makes:

- `assets/literature/arxiv_query.xml` — `all:population genetics selection`, 5 entries, **3 carrying
  `arxiv:doi` and 2 not**, so the published-preprint DOI branch is covered in both directions. That
  branch is load-bearing: a DOI is the only handle that reaches Unpaywall.
- `assets/literature/semanticscholar_search.json` — `lactase persistence`, 3 records, captured with
  the full `_S2_FIELDS` list so every field the parser reads is present. Real PMIDs on the trait this
  repo already fixtures elsewhere.

Six tests, ground truth computed from each payload rather than pasted. `F6` keeps its entry in
`dogfooding.md` with the diagnosis corrected — the tri-state result it was really about is
unaffected, and **the lesson is the re-probe**: an environmental verdict is a measurement with a date
on it, and this one had no expiry.

**`find-evidence` gains "When there is no legal copy".** The skill refused a paywall bypass and then
said nothing about what to do instead, so the refusal was a dead end. Four routes, ordered by how
fast they actually work — preprint check, asking the corresponding author (usually the fastest for a
recent paper), Open Access Button, then institutional access or ILL — plus the rule that matters more
than any of them: a row waiting on a copy stays **unchecked**, never downgraded to the much stronger
"read and not found". Triggers extended so it fires on *"paywalled"* and *"how do I get this paper"*.
The Sci-Hub question was put and answered **no**: shipping the code is the act regardless of what
triggers it, and it is the opposite of the `declared_use` gate this repo already enforces.

Its 429 troubleshooting entry is corrected to the measured behaviour rather than the assumed one.

**`RM15` closed.** Its last loose thread — one unreproduced report of `describe_table` returning a
0.5 shape under 0.6.1 — reproduced, and it is not a `describe_table` defect: the plugin cache holds
two stale servers (`0.2.0` on format 0.5.0, `0.7.0` on format 0.5.4) while the workspace runs 0.6.1,
so a 0.5 server answered a caller who believed otherwise. `RM13`'s `produced_by: SchemaVersions`
already guards it.

**Filed upstream: format-tree `S60`** (`F57` here) — an authored **overlay table** so a correction to
a derived sidecar never has to be written inside it. Asked of their compiler rather than built here,
because an overlay is authored input rather than a repair; it depends on `S51`.

**Roadmap decisions recorded** for `RM9`, `RM16`, `RM18`, `RM20` and the `just-dna-lite` hand-off,
plus two new items: **`RM21`** (expose `yank` — the client has it, we wrap it nowhere, and a publish
that turns out wrong has no route back) and **`RM22`** (the enricher already fetches the ancestry
`studies.csv`'s `population` wants, and nothing here surfaces it).

## Unreleased — the skills surface finally has a gate, and three docs stopped saying false things

No tool change, so no version bump: tests and documents only.

**`tests/test_skills.py` — 137 checks where there were none.** Sixteen skills and ~4,300 lines that
nothing ever gated, which is part of how the monolith reached 1431 lines and how tonight's move of
`SYMPTOMS.md` and `CLI.md` could have broken thirteen pointers with the suite still green. It holds
portable frontmatter (the six fields that survive outside Claude Code), the published name and
description limits, the 500-line body ceiling, every named skill actually shipping, every relative link
resolving, the stage spine being complete, and a long reference opening with a way in.

One of its checks pins `RM15` rather than a style: *"report, never repair"* is **not** banned — three
skills quote it in order to say it was retired, one of them being the canonical statement of what
replaced it — so what fails is stating it as **current**.

**Three claims the night made false, corrected where they were made:**

- **`logs/` was "the provenance subtree nobody fills"** in its own dossier title, in `module-tables`'
  router row and in `CLAUDE.md` §2. `record_override` is its first writer.
- **`provenance.json` was "recognised, and nothing here writes or reads it"** in the layout dossier,
  the spec-directory tree and `RM16`'s own build list.
- **`docs/FOR_DEVELOPERS.md`'s tool table read as the roster and listed 32 of 48.** That is the
  counted-claim shape `CLAUDE.md` §8 now warns about, so the repair is the one that rule prescribes:
  say what the table is for and give the call that cannot drift.

---

## 0.12.0 — `compare_modules`: what moved between two spec directories (2026-08-20)

`RM19`, built from the 699-line design study that had been sitting without a roadmap entry. **Essentials
and offline** — the cost is bounded by the two directories the caller named, which is the same shape as
`module_signature` and `compile_module`.

Three grains in one report, because the caller does not yet know which one they need — that is why they
called. `content` and `frame`; then per-table presence, counts and `identity_scope`; then **rows grouped
by the set of columns that changed**. The grouping is what makes the row level readable: 1,190 rows
moving in one column for one reason is one fact printed 1,190 times, and grouped it is one line.

Two rules the implementation turns on, both from the study:

- **Compare the parsed models' `model_dump(mode="json")`**, never the CSV text and never the parquet. It
  is the same normalization `content_signature` applies, so the row level cannot contradict the
  signature level, and formatting differences become invisible for free.
- **Never pair rows whose natural key changed.** One removed and one added, never one changed — pairing
  asserts *this row became that row*, which two directory listings cannot support.

Verified on `hfe_hemochromatosis` rather than on synthetic rows: a row reorder is `content: same` with
13 unchanged; a licence edit is `content: same` with the change under `sources.signature`; a retyped
rsID is `+1 -1 changed 0`; a changed `genome_build` is `frame: moved` with the counts beneath it
labelled *not comparable*; and `sources.csv` compares as the same table as `licensing.csv`.

`module-diff` and `module-revise` no longer say nothing compares two versions. What they say now is
narrower and still true: **nothing in the artifact or the catalog relates two versions** — no parent
digest, no stored record — and a comparison of two directories you already have does not create one.

`compare_to_published` is specified and **not built** (`RM19`).

---

## 0.11.1 — the review queue stops accusing an author of an edit nobody made (2026-08-20)

`F52`, found by dogfooding 0.11.0's own `review_queue` on `assets/fto_bmi` an hour after it shipped.
The module carries no `clin_sig` column, so there was no cell to compare a record against — and
`still_bound` reported `false`, which reads as *somebody edited this after the reason was written*.

`QueuedOverride.still_bound` is now `bool | None` and `ReviewQueue` counts `unbound` and
`subject_absent` apart. `null` means the question could not be put; it is not a `false`. That is
`CLAUDE.md` §2's own rule — *never collapse unknown into a boolean* — broken by the tool written to
satisfy §2's other half, and caught by using the surface rather than by testing it.

---

## 0.11.0 — the skills split completed, and two checks the audit's own findings needed (2026-08-20)

The night run after the audit. **`skills/create-module/` is deleted** and `RM17` ships. No floor move:
format/compiler 0.6.1, enricher 0.6.4, registry 0.18.2. 216 tests green, `ruff` clean, `pyright` 0
errors.

### One skill per lifecycle stage, and no skill holds another's procedure

`create-module` was 1431 lines loaded whole to answer any question — the shape that guarantees every
session re-reads it and none updates it in the right place. Every line now sits in the stage that owns
it, and the file is gone rather than left as a husk:

| Written | Owns |
|---|---|
| `module-start` | stage 0–1: triage a handed source, the preprint-currency check, the six-step claim triage, the email asked once, and what to declare at birth — `weighting:`, `authorship:`, the licence position `--use` asserts |
| `module-draft` | stage 2: the three drafters, `differs` as a decision rather than a defect, the eleven CPIC genes that lose every allele, star-allele filtering |
| `module-curate` | stage 3: the cells only a pilot settles, the off-by-one essay, genotype spellings, **how many rows is a report** |
| `module-enrich` | stage 4: the resolver chain, the ref-mismatch report and why its count is a floor, unreachable ≠ absent |
| `module-check` | stage 5: severity, the skip vocabulary, the attestations that record a check nobody could have run |
| `module-compile` | stage 6: strict as *reproducible*, the three signatures, the round trip and what it silently costs |
| `module-close` | stage 6b: the closure, what re-opens a module, the check records closing can drop |
| `module-publish` | stages 7–8: the two instances, the pre-flights, onboarding, and when to advocate for production |
| `module-weights`, `module-consumer` | the references the stages load |

`module-101` grew to hold the map-level half — the tool roster and its tiers, the beginner framings,
the two known gaps — and `SYMPTOMS.md` / `CLI.md` moved to `module-101/references/` with a table of
contents each, because they are read *from* every stage rather than *by* one. Sixteen skills ship;
the manifest description and `tests/test_plugin_manifest.py` moved with the count, and the test's
pinned pair is now `{module-101, module-start}`.

**All sixteen end with the same discriminator section** — what to apply silently, what to put in front
of a pilot — replacing the "cells no tool fills, with the refusal reasons" framing `RM15` retired.

### `RM16` — the counterstance gets its record, and a review pass gets a queue

§2 says this layer may write, that every move is logged, and that editing **against** a source needs a
reason that outranks it. None of that was real: no tool wrote a reason anywhere and `logs/` had no
writer at all.

`record_override` writes one into **`provenance.json`** — upstream's own file, already carrying
`variant_key`, `rationale`, `human_reviewed`, already in the registry's `RECOGNIZED_SPEC_FILES`, and
already outside `artifact.digest`, so the record costs no identity — and appends the move to
`logs/authoring.log`, which every compile sweeps up and publishes with no opt-out.

Four properties are the design rather than the implementation:

- **The record answers a reported mismatch; it cannot precede one.** A row markable as outranked
  *before* the check runs would destroy the only signal that catches the other pathway — a
  hallucination or a stale recollection, where the warning is doing its job. The two are
  indistinguishable at the moment the check fires, which is exactly why the ordering carries the
  weight.
- **It never produces a pass.** Downgraded, still visible, still in the queue.
- **It is bound by digest to the value it justifies**, so editing that cell again makes the record
  stale rather than silently attaching an old reason to a new value.
- **Per-field inside a per-row schema.** An outrank is per field; `ProvenanceItem` is per
  `variant_key`. Rather than design around a guess at `S52`'s answer, this writes one item per
  `(variant_key, field)` with the machine fields in a marker on `rationale` — so the per-field record
  **travels with the module** instead of living in a local cache a second author would never see.

`review_queue` reads them back, ranked worst-first, and is the priority list a review pass has never
had. `still_bound: false` first (the value moved under the reason), then `standing`, then `resolved` —
which means the archive caught up and the override was **vindicated**, the only such evidence this
format holds. `unknown` is honest rather than green: only `clin_sig` has the archive's current answer
recorded inside the module.

Left open and named in `RM16`: `refresh_sidecar` reading these records, which needs a sidecar-subject
mapping that only became a question once the capture existed; both docstrings in `refresh.py` now
state that narrowed reason instead of the retired "the log is empty".

### `RM17` — the check that can see a quote nobody located

Two spec directories differing *only* in `provenance_quote`, one honestly located and one all article
titles, came back byte-identical from `registry_check(literature=true, strict=true)`. Nothing in the
product could tell them apart, which is how four published modules reached production carrying 3668
title-quotes.

`src/just_module_creator/authored_checks.py` groups `studies.csv` by `pmid` and reports any PMID whose
every **quoted** row carries the same passage — a `warning`, aggregated per PMID with the row count and
the first few words. Offline, over the authored file alone; deliberately **not** `literature.csv`,
whose counters are stale on exactly the modules that have the problem (`F49`).

**The layer question `RM17` left open is answered by making the layer legible rather than by choosing
a surface.** `LintFinding` gains `source` (`upstream` | `just-module-creator`) and `ValidationReport`
gains `authored_findings`, kept out of `errors`/`warnings`/`info` so the lists that transport
upstream's own strings stay untouched. So the rule is one line: **upstream's strings stay where they
are; anything we computed is a `LintFinding` that says so.** An authored finding does not move `valid`
— the compiler would still build the module, which is the whole reason it has to be visible here.

Keyed on the **shape, not the string**: a rule that only caught the title would miss the next variant,
which is one real sentence pasted onto two thousand rows. The title comparison needs
`lookup_citation`, a network call, so it stays out of the offline linter.

**Measured on the corpus that motivated it**: across the four externally authored modules, every one of
3,668 study rows carries a quote and each has **exactly one distinct quote per PMID** — 3, 26, 33 and 19
quotes for 3, 26, 33 and 19 PMIDs. The check flags 68 of those 81 PMIDs; the thirteen it leaves are
cited on a single row each, which is one quote and legitimately so. The fifth module reports nothing
because it carries no quote column at all — an absence, not a pass, and the same module that was immune
to the coordinate-shift class.

---

## 0.11.0 — the philosophy audit: what we may write, and who may say they read a paper (2026-08-20)

`RM15`. No new tool, no floor move: format/compiler 0.6.1, enricher 0.6.4, registry 0.18.2. 204 tests
green, `ruff check` clean, `pyright` 0 errors. **Released as 0.11.0** together with the night run below it — all three files bumped
(`pyproject.toml` and both plugin manifests), which is what `server.INSTRUCTIONS` changing required.

### The stance we were holding was the format's, and this is not that layer

`report, never repair` is correct for `just-dna-format`: the compiler cannot record *who* decided a
value, so writing one would launder a machine's guess as an author's judgement. This repo adopted it
as a non-negotiable of its own and never asked whether it belonged here. The owner's correction: they
delegate the business decision to us, so **we may write, revise and fix** — provided the move is
logged and the agent respects a discriminator.

Every surface that carried the stance was re-read against a three-way test: is it *physics*, is it
format's policy that is *also correctly ours*, or is it format's policy *we should not hold*. Most
bullets are physics and stand unchanged. What moved:

- **`server.INSTRUCTIONS` rule 2** said *"Report, never repair… those refusals are the feature."* It
  now says the writes are ours and logged, and names the two cells still withheld — one a check
  compares against that same source, one only a pilot can settle.
- **A new rule 3**, which was nowhere in the instructions and is the one an agent can do most damage
  by not knowing: **a mismatch against a source is not a defect report.** Archives lag the edge — a
  retraction, a refuting meta-analysis, a bigger cohort. A row disagreeing with ClinVar may be the
  module being right and current while the archive is stale, so silently conforming it *degrades* the
  module and the check then agrees with itself and reports green.
- **`CLAUDE.md` §2's "never widen the write surface"** bundled a security boundary with format's
  authoring boundary. Split: containment through `resolve_dir` is ours and absolute; "tools write only
  where the upstream API already writes" and "never overwrite an authored file" are gone, because a
  layer that may not touch an authored file is not an authoring layer.
- **The machine-sidecar refusal** (`_MACHINE_REFUSAL`, `describe_machine_table`) said a produced
  sidecar is "not yours to finish by hand". The hazard is real — passes merge, no check asks where a
  value came from, so an unmarked cell is hashed as though the source said it — but the remedy was
  wrong and contradicted our own `refresh_sidecar`, which exists to protect hand-curated
  `source="manual"` rows that upstream's vocabulary documents. Now: mark it, don't avoid it.
- **`models.py` / `_shared.py`** cited the slogan as the reason for carrying upstream's
  `applied`/`refusal` across the boundary. The behaviour is right and the reason is different: an
  `applied: false` records what the *compiler* did, and restating it as ours misreports another
  layer's act. Says so, and says it implies nothing about what this layer may write.
- **`refresh.py`'s conflict refusal** is physics, but conditionally — see above.

### An agent may locate a `provenance_quote`, and the old rule cost more than it bought

The rule said never extract a passage from a fetched document, because "a machine-located quote
asserts a reading that never happened". It does not: `fetch_fulltext` hands the agent the whole
article, so the reading is real. What the rule protected was a fiction about **who** read it, and it
left the column empty for the only reader present. Reversed: locate the passage, quote it verbatim for
the row's own claim, and **say who located it**.

Measured what the prohibition actually produced, across every `studies.csv` upstream (33 files, 44342
rows): the ten reference examples do not carry the column at all, and the four published
`antonkulaga/*` modules carry a quote on **all 3668 rows** — with exactly **one distinct string per
PMID** across 81 PMIDs, and that string is the article's **title**, verbatim from `esummary`. A title
always appears in its own fulltext, so `quotes_found` matches every one and the modules report
complete quote coverage while witnessing nothing. The refusal did not produce human-read quotes; it
produced a green check over metadata.

Filed upstream the same night: **`S54`** (the check cannot fail on a title — compare against
`CitationHint.title`, and flag one identical quote repeated across every row citing a PMID) and
**`S55`** (we withdraw S11's reasoning, and ask for the per-row attributor it was missing:
`StudyRow` has no `curator` while `VariantRow` does). Tracked here as `F42` / `F43`.

### Also

`tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier` sliced the taught
workflow on the literal string `"Three rules"`. Renumbering those rules silently widened the slice to
the whole document and reported an unrelated tool as a tiering bug. Bounded on the blank line that
ends the block instead — the docstring always claimed it derived from the text, and now the boundary
does too.

### The remediation track: one module's quotes made honest, and four findings from doing it

A dogfooding run took `antonkulaga/aggression_anger_snps` — one of the four modules `S54` measured —
and replaced its title-quotes with what the articles actually say, end to end through this surface,
publishing to the polygon as `test-sheep/test_aggression_anger_snps@1.0.0`. Only `provenance_quote`
was touched. The yield is **1 real quote from 69 rows**, and that is the honest number: 65 rows cite
a paper whose text names none of their variants, because the associations live in its supplementary
data, and 3 cite a paywalled paper whose abstract names no rsID. The three paywalled rows are named in
[`ROADMAP.md`](ROADMAP.md)'s `RM18`, along with everything else that needs a human.

- **`_NO_PASSAGE_NOTE` still carried the retired rule** and was corrected in the same pass as
  `fetch_fulltext`'s docstring should have been. The tool handed over the article, said in its
  description that quoting was legitimate, and said in the payload that it was not — the second one
  arriving attached to the text, at the moment the decision is made. `describe_table`'s
  `attestation_bearing` gloss and `discovery.py`'s module docstring carried the same claim. `F48`.
- **`find-evidence`** gains *what may honestly go in `provenance_quote`*: never the article's
  property, choose and state a grain, an empty cell is a result and there are two kinds, and record
  who located it — with the three places that record can go and what each survives.
- **`studies.md` and `literature.md`** carry the measurements as gotchas, so the rule travels with
  its evidence.
- **`F44`–`F47`** are the friction, `F44` first: `registry_check(literature=true)` returns
  byte-identical output for the remediated module and for a baseline whose every quote is the
  article title. The pre-flight we tell authors to run says nothing about the one column carrying
  the module's evidence, and the cheap detector — group `studies.csv` by `pmid`, count *distinct*
  quotes — needs no network at all.
- **Upstream `S56`, filed on discovery**, plus corrections to `S54` and `S55` from measurement: all
  four published modules ship `quotes_authored: 0` beside 3668 authored quotes, so the quote check
  never ran on any of them; and `provenance.json`, `logs/` and `authorship` *do* travel with a
  publish, which narrows what `S55` is actually asking for to the `(row, quote)` grain. `F42`, `F43`
  and `F49` record our side.
- **The decision list for whoever maintains those four modules is [`ROADMAP.md`](ROADMAP.md)'s
  `RM18`** — decisions, not a diff: the published versions are immutable, the modules met the rules
  that existed when they were written, and emptying the column is one of the defensible answers. It
  was written as a handoff document and moved to the roadmap when that document was deleted, because
  a decision nobody has taken belongs where open work is listed.

A second module, `big_five_personality`, was then remediated the same way and published as
`test-sheep/test_big_five_personality_snps@1.0.0` — 859 rows, 21 quoted, 21 distinct strings. It is
where the interesting cases live, because `aggression_anger` is 1:1 variant-to-row and hides them:

- **The yield is 2–3% and the relationship is inverse.** All 26 cited PMIDs were retrieved and every
  rsID in their text intersected with the rsIDs cited to them: 25 rows quotable, 300 read-and-not-
  found, 527 unchecked (abstract only), 7 unchecked (nothing retrievable). The more rows a paper
  grounds the less likely its text names any of them — the three biggest, at 298, 197 and 69 rows,
  yielded nothing.
- **Four rows cite an article that names their variant and reports a different trait.** A sociability
  GWAS cited for a neuroticism item, p-values orders of magnitude apart. Left empty and escalated,
  because attaching a real sentence to an assertion the article does not make is worse than an empty
  cell. Under the old rule they carried the title and were indistinguishable from the other 855 —
  which is the argument against simply emptying the column, and it only appeared because somebody
  went looking for the passage.
- **One article is free to read with no reuse grant**, so its rights are recorded UNKNOWN and the
  module's own `licensing.commercial_use` drops to `null` on the published card. `find-evidence` and
  `studies.md` carry all three cases, plus the table-row question: 15 of the 21 quotes are a
  flattened JATS table row, which is verbatim and varies per row but is not the "human-legible"
  passage the column documents.
- **`F51`** nearly cost a false status line: `uv run` answers about whichever repo you are standing
  in, both trees report `just-dna-format 0.6.1`, and a symbol check chained after a `cd` into the
  sibling reported an upstream field as installed. It is not.
- **Upstream accepted and fixed all three notes the same night** — `RM118` (`titles_as_quotes`),
  `RM119` (the sidecar comparison plus `quotes_unchecked`) and `RM120` (`StudyRow.curator`, our whole
  ask verbatim). **None of it is released**, so every mitigation and every honest limitation stated
  in the skills stays exactly as it is until `uv sync` carries them. `RM17` is unaffected either way:
  upstream's title check lives in the literature pass, and the modules that have the problem never
  ran it.

## Unreleased — refreshing a derived sidecar stops being a destructive manual sequence (2026-08-20)

New tool `refresh_sidecar`, extended tier, in a new `tools/refresh.py`. No floor moves and no upstream
version changes: format/compiler 0.6.1, enricher 0.6.4, registry 0.18.2. 204 tests green, `ruff check`
clean, `pyright` 0 errors. No version bump in this change.

### The only drift detector this format has was also its most destructive operation

Every derived sidecar is merge-not-clobber, which is what lets a hand-corrected number survive a
re-run and is exactly why a re-run refreshes nothing. So asking a source whether it still says what
`resolution.csv` says means **deleting the file first** — and that discards the author's rows with the
stale ones. `source="manual"` rows are the case that is not recoverable by re-running: nothing fetches
them, because a human worked them out. `module-refresh` teaches the sequence, and the sequence is
irreversible.

`refresh_sidecar` does it reversibly: copy the file to a durable location **outside** the spec
directory and read the copy back and hash it *before* deleting anything; re-derive by running the pass
(or passes) that own the table; classify every row; put back only what is provably the author's; report
the rest. `signature_moved` is the answer to read first — the fact signature is taken with the same
`integrity.<table>_signature` function the manifest publishes, so a moved signature with nothing
reapplied and no conflict is the source having changed its answer.

### What it refuses to do, which is most of the design

- **A conflict is not resolved — and RM15 checked whether that is physics or inherited policy.** A
  subject in both copies with differing facts is either a cell the author edited or a revision the
  source published, and the two values alone cannot separate those. It is physics *conditionally*: it
  is two data points because we keep no third, and a filled authoring log would settle it. `logs/` is
  empty, so the refusal is honest today and is explicitly **not permanent**. Neither
  side is preferred, nothing is merged, and `conflicts[].unresolvable` says so per entry. Where the
  captured row's `source` is a value no fresh row uses, `source_proves_authored` surfaces that per row
  — a real narrowing, and still **not acted on**: knowing who wrote a row does not settle which of two
  answers about the world is right.
- **A partial re-derivation is never classified against.** Unreachable source, a pass that did nothing,
  or an empty fresh table: the captured bytes go back verbatim and `restored` says so. Classifying
  against a table that was never filled would report every real row as one the source withdrew — the
  exact false negative the tool exists to prevent. `offline` refuses up front with nothing touched, for
  the same reason.
- **A sidecar with no verified capture is never deleted**, and a file that does not validate is never
  deleted either — a table this tool cannot classify is one it will not touch.
- **`licensing.csv` cannot be refreshed at all.** It is the one derived sidecar with no producer:
  licence rows are written as a side effect of a pass that *took* data, and a row copied out of a
  source by hand has no producer. Deleting it would discard the whole declaration the compile gate
  reads with nothing to rebuild it. Refused with that reason rather than attempted.

### Row identity is derived from the live models, and the half that is not published is filed

The fact half needed nothing written down: `integrity.fact_signature`, the eight public
`<table>_signature` functions and the eight `*_FACT_FIELDS` tuples are all public — the compiler's
`_resolution_signature` and its siblings are underscore-*aliased imports* of those, so **no private
symbol is reached for**. `source` sits outside every fact set except `sources.csv`'s (where it is the
subject rather than the provenance), which is why a hand-authored and a fetched row with identical
facts hash equal, and why `source` is the only column that can prove authorship.

The **subject** key has no public route: each pass keys its own `existing` dict on a local expression
(`(row.variant_key, row.population)` inside `enrich_frequencies`). It is derived as the fact columns
the row model marks required, reported on every call as `subject_fields`, exact on five of the eight
tables and coarse on two — and coarse reports *more* rows as conflicting, which repairs fewer. Filed
upstream the moment it was found as format-tree **`S51`**, tracked as **`F41`**.

### Three decisions worth keeping

- **Extended tier, on cost and not usefulness.** A refresh runs whichever pass owns the sidecar, up to
  the GWAS one measured at 382 requests for one real module. In essentials the default tier would reach
  an extended budget through a different door. `resolution.csv` alone would qualify as essentials by
  the cost rule, and splitting the tool per sidecar to get that is not worth a second `Mode` member.
- **`gene_metrics.csv` runs BOTH its producers.** `enrich_dosage_sensitivity` writes ClinGen's
  haploinsufficiency and triplosensitivity onto that same file rather than one of its own, so
  re-deriving with only the constraint pass would rebuild half a table and then report every dosage row
  as withdrawn. That is why `use` is required for this sidecar and for `gwas_effects.csv`, and why
  `declared_use_applied_to` names where it mattered.
- **`produced_by` is stamped, unlike the other directory answers.** `lint_rows` and `compile_module`
  are deliberately unstamped because they answer about a directory at a moment. This one *also* returns
  a generated schema answer — `fact_fields` and `subject_fields` are the identity it classified by — and
  a stale process would classify against an old fact set with exactly the same confidence. RM13's stamp
  travels with the derived facts, not with the file report.

### The measured thing that makes the headline case honest

For `resolution.csv`, an online run that reaches Ensembl writes a `status="not_found"` row for an rsID
it cannot resolve (`enrich`'s `elif genome_build == "GRCh38":` branch). So a `source="manual"` row for
that variant has its subject present in the fresh table and lands in `conflicts` — reported, not
reapplied — while one whose rsID no link was able to ask about has no fresh row at all and *is*
reapplied. The docstring says both, because a tool that claimed to have kept the row either way would
be laundering its own output.

### Also

- The refreshed file is moved back to **where the module kept it**. With the original deleted,
  `sidecar_write_path` creates the preferred spelling at the spec root — right for a fresh file, and
  wrong here, because a module keeping its sidecars under `derived/` would have its layout migrated by
  a refresh. `resolve_sidecar`'s `SidecarCollision` is caught and reported rather than raised.
- Reapplied rows keep their **cells as text**, appended with a `csv.DictWriter` and never re-serialized
  from the parsed model, so a value spelled `1.00` stays `1.00`. They land at the end of the file rather
  than in the pass's sort order, so `artifact.digest` may move on the next compile for a reason that is
  not a content change — the note says so, and the fact signature is order-independent.
- **The skill claim this makes stale:** `module-refresh` teaches delete-first as the only route, and
  says deleting each sidecar costs the hand-curated rows in it. Both are now conditional on the tier —
  extended has a reversible route. `skills/` is owned by a parallel session and was not touched.

## Unreleased — the sidecars an author reads are answerable, and three restated facts are generated (2026-08-20)

**RM10 and RM11**, shipped and moved to `ROADMAP_HISTORY.md`. No floor moves and no upstream version
changes: format/compiler 0.6.1, enricher 0.6.4, registry 0.18.2. 181 tests green, `ruff check` clean,
`pyright` 0 errors. No version bump in this change.

### `describe_machine_table` — "ask the tool, never memory" now covers the files you only read

`describe_table` gates on `draft.DRAFTABLE`, so `resolution.csv` and the six fact tables answered
*"Unknown table kind 'resolution.csv'"* — false twice over, since the file is known and is in every
enriched module. The new essentials-tier tool answers the live column list for all seven, projected
from `reference.authoring_reference()["models"][…]` so the column dicts are upstream's own assembly
rather than a second one of ours, with `produced_by` like every generated answer.

**The do-not-author signal is structural, not advisory**, which was the brief's real constraint. A
separate answer model rather than a flag on `TableDescription`, because extending it would have had
to fill `requirements`, `redundancy_bearing` and `attestation_bearing` — three fields whose whole
subject is authoring — with empty values, and an empty `requirements` reads as *no requirements*
rather than *the question does not apply*. Instead: no template, no linter and no requirements answer
exists for these tables; `MachineTableDescription.hand_authored` is `Literal[False]` where
`TableDescription`'s is now `Literal[True]`, so the difference is in the schema an agent reads before
calling; and the authoring routes redirect by name through `_shared.known_kind` instead of calling a
real file unknown. `refusal` says what a hand-written cell costs — the passes merge rather than
overwrite, so it survives every later run wearing the source's authority.

**`licensing.csv` is exempt, and the exemption is derived**: it is refused by the machine route under
both spellings with a pointer back to `describe_table`, because it is in `draft.DRAFTABLE` — the one
fact sidecar a human writes. Nothing has to remember that.

### Three answers that restated a schema fact now generate it

- **`list_tables().sidecars` was a literal four; the installed toolchain has seven.** It omitted the
  format-0.6 fact tables `gene_validity.csv`, `clinical_assertions.csv` and `gwas_effects.csv` while
  `authoring_reference` in the same module described all three. Derived now from
  `just_dna_registry.specfiles.FACT_CSVS` + `RESOLUTION_CSV` minus the draftable kinds — the public
  roster, because `compiler._FACT_TABLES` is the authoritative one and is private (`S47`). The
  `resource://just-dna/tables` prose restated the same list and is rendered from the same constant.
- **`keyed_on` for `copynumbers.csv` named `modifier_cn`**, whose own field description has read
  *DEPRECATED since 0.6, removed at 1.0* for two releases. Now `modifier_copy_number`. The key half
  stays hand-kept because nothing public derives it — `draft.natural_key` is row-level and the two
  name registries are private (`S48`) — so the drift class is closed by a test that resolves every
  token against `model_fields` and rejects one whose description opens with `DEPRECATED`. Run against
  the old map it flags six tokens; three of them were loose prose (`variant`, `a`/`b`/`trait`,
  `trait`) and are now real column names, since a token that does not resolve cannot be checked.
- **`studies.csv` was described in pre-RM47 terms.** Upstream relaxed
  `StudyRow.REQUIRED_ANY_OF` to `()` in 0.6: a paper grounding a bin threshold, a method or a
  population is a legal row naming no variant, and `variant_key` may be null. The subject said "the
  evidence for a variant", which would have an author drop exactly that row. `_COMPOSITION_NOTE` now
  adds that a binning module may carry `studies.csv` without `variants.csv`, checked by validating
  such a spec strict-green rather than by asserting prose.

### Three upstream notes, filed the day they were found

`S47` (no public `csv -> row model` map for the fact tables, so a consumer must hand-keep one —
**accepted and fixed in their tree the same hour** as `hints.derived_model_for`, which retires our map
the release it installs, and they declined to widen `describe_table` for the reason this change
assumed),
`S48` (a kind's natural-key *columns* are unobtainable — `natural_key` returns values, the registries
are private — which is how `modifier_cn` went stale here), and `S49` (`COMPANION_KINDS` pulls
`variants.csv` in behind `studies.csv` unconditionally, which RM47 made wrong for a binning module;
probe attached, strict-green). Tracked here as `F56` (renumbered from a duplicate `F38` on
2026-08-20), `F39` and `F40`.

### What was NOT edited, on purpose

`skills/` is owned by a parallel session this session, and about eight of its dossiers now claim the
opposite of what ships — each fact table's reference says `describe_table` refuses it and quotes the
old *"Unknown table kind"* wording, `module-tables/references/LAYOUT.md:194` restates the four-item
roster, and `create-module/SKILL.md`'s studies section still gives the pre-RM47 identity rule. The
list was reported rather than applied; a skill edited underneath its author is a worse outcome than a
stale line with a known owner.

## Unreleased — the GWAS Catalog pass is wrapped (2026-08-20)

**RM12**, shipped and moved to `ROADMAP_HISTORY.md`. No floor moves and no upstream version changes:
format/compiler 0.6.1, enricher 0.6.4. 165 tests green, `ruff check` clean, `pyright` 0 errors. No
version bump in this change.

### `gwas_effects.csv` was the last enricher pass with no route through this surface

`enrich_gwas_effects(spec_dir, strict=False, use="unstated", study_facts=True, offline=False)` in
`tools/passes.py`, registered in `register_extended_passes`, returning a new `GwasReport`. One row
per published **association**, not per variant. Before this an author driving the plugin had to shell
out to `just-dna-enricher gwas <dir>`, which the dossier documented as a gap.

**Extended, decided by cost.** `1 + 2N` requests for a variant with N associations, because `pmid`,
`trait`, `ancestry` and `study_accession` all sit behind `_links` — measured upstream at **382
requests and 0 cache hits** on one real module, since rs1800562's 189 associations each name their
own study. Sized by how much has been published, not by what the caller named.

### What the tool refuses to smooth over

- **`strict` fires on the usual answer.** It escalates on `unusable` and `p_value_underflows` and
  never on `missing`, because the Catalog holding nothing for a variant is a *fact* about the
  variant and true of most clinically authored ones — recorded as a `not_found` row.
  `reference_examples/hfe_hemochromatosis`, a shipped flagship, carries **six** p-values the Catalog
  publishes as `0.0`, so strict refuses it while nothing about it is wrong. The docstring says so,
  and the failure path repeats it on the result. It also escalates **after** the write, so a strict
  failure leaves the sidecar holding everything `best_effort` would have written — a fetch failure
  writes nothing, and upstream's verbatim message is what distinguishes them.
- **Published betas are not weights, and that is now readable rather than asserted.**
  `associations_without_effect_allele` and the sorted distinct `effect_units` are computed from the
  rows upstream returned. `not_found` rows are excluded from the first: their null `effect_allele`
  means *no association exists*, while a recorded association's null means *the study never
  established which allele carries the effect*, and counting them together reports the first as if
  it were the second. On one real module: **33 of 186** associations name no effect allele, and one
  variant carries **12 distinct `effect_unit` values**, several of them the Catalog's uninformative
  `unit`. There is no argument on this tool that could write `weight`.
- **`study_facts=false` is a sticky cut.** It saves two thirds of the budget and leaves
  `pmid`/`trait`/`trait_efo_id`/`ancestry`/`study_accession` null — and the merge is keyed on
  `association_id` alone, so a later run with study facts **on** skips those rows rather than
  backfilling them. Only deleting the file recovers them. Warned on the result, asserted in the
  test, and filed the same day as format-tree `S50` / our `F38` — a doc gap, since the code is the
  merge rule working correctly.
- **`use` gates nothing here and says so.** EMBL-EBI names no licence, so `commercial_use` is
  recorded **unknown** rather than permitted; the terms of the thousands of publications the Catalog
  summarizes are not settled by its terms page.

### Two decisions worth keeping

- **No `produced_by`.** RM13 stamps generated *schema* answers; this is a verdict about a directory
  at a moment, which RM13 explicitly left unstamped, and `SchemaVersions` carries the format and
  compiler versions where a pass answer would need the **enricher's**. A stamp naming the wrong
  package is worse than none.
- **No counter is coalesced to zero on a failure.** `rows`, `requests_made`, `requests_saved`,
  `p_value_underflows` and `unusable` are `int | None`, and the failure path passes `None` for all
  five. On a strict escalation `0` would be a *wrong* answer rather than a missing one: upstream's
  message names non-zero counts and the sidecar is already on disk. `rows` is `None` on an offline
  no-op too, because an existing file keeps every row it had and the pass never looked.
- **One `except` arm on purpose.** `GwasNotFound` is a subclass of `GwasError`, so an arm for it
  would have to come first — but it cannot arrive: `associations_for` catches the Catalog's 404 and
  returns the empty *answer* that becomes a `not_found` row, and `follow` catches it so an
  association whose study record moved keeps null study facts. An arm for a type that never arrives
  reads as if it did.

### The strict ladder has a test here, and still has none upstream

`strict` appears nowhere in `enricher/tests/test_gwas.py`, in either direction. Four tests drive the
real `enrich_gwas` with an injected transport (only the network is excluded) and assert what it
observably does: one underflowing association raises and the row is **on disk** when it raises;
`best_effort` on the same input reports the count and succeeds without duplicating the row; offline
is a no-op that says it did nothing; and `study_facts=false` costs exactly one request and does not
heal on a later run. `test_modes_and_auth.EXTENDED_ONLY` pins the tier.

## Unreleased — every generated schema answer names the toolchain that produced it (2026-08-20)

**RM13**, shipped and moved to `ROADMAP_HISTORY.md`. No floor moves and no upstream version changes:
format/compiler stay at 0.6.1. 161 tests green, `ruff check` clean, `pyright` 0 errors. No version
bump in this change.

### The rule was unreliable in exactly the case it exists for

Every skill says *ask the tool, never memory*, because every column list, vocabulary and requirement
is generated from the live pydantic models. A stale plugin cache breaks that silently: the cache at
0.7.0 was serving format 0.5.4, so `describe_table("activity_phenotype.csv")` answered **11 columns
where the installed 0.6.1 has 14** — a wrong answer, in the same shape and with the same confidence
as a right one, from the tool the rule points at. Nothing in the payload said which release produced
it, so a caller had no way to tell.

### What carries the stamp

`_shared.schema_versions()` is the one source, and `produced_by: SchemaVersions` (`format_version`,
`compiler_version`) is now a **required** field on `list_tables`, `describe_table`,
`table_requirements` and `get_template` — required so a schema tool added later cannot quietly omit
it. `authoring_reference` carries the same pair as a `produced_by` key inside its JSON, in the
summary and the `schemas=True` form alike, and `resource://just-dna/tables` ends with the same
sentence in prose.

**`server.INSTRUCTIONS` too, and that is the half that needs no tool call.** It opened with a
hardcoded `(format 0.5)` while the installed format was 0.6.1 — a literal version string, which §2
forbids for this precise failure, and stale by a minor release. It now names the live format and
compiler from the same helper. `F19` and `F26` both nominated the instructions as the *stronger* fix
because they are in front of an agent before the first call; both are updated with what this covers
and what it does not.

### Three decisions worth keeping

- **The compiler is stamped beside the format.** The table roster, requirement shapes, templates and
  the redundancy/attestation maps come from `just_dna_compiler.draft` / `hints` / `scaffold`, and
  since 0.6 the two packages no longer move in lockstep — so one version cannot describe these
  answers.
- **Read once at import, and that is correctness rather than speed.** RM13's own text said "at call
  time"; a per-call read would report the *new* distribution the moment anything upgrades the
  environment under a live stdio server, while the answers still came from the already-imported old
  code. The stamp has to describe the code that produced the answer or it is worse than absent.
- **`authoring_reference` keeps returning a JSON string.** Around thirty dossiers document
  `authoring_reference()["models"][...]`; a wrapper model would have broken all of them to add one
  field. The key goes into a shallow copy, and cannot collide in either form — the summary form's
  keys are fixed, the schemas form's are CamelCase model names.

### What is deliberately not stamped

`lint_rows`, `validate_module` and `compile_module` answer *about a directory at a moment*; they are
not schema knowledge an agent carries forward, and a compile is already stamped upstream inside
`manifest.json` (the catalog's one module still reads `just-dna-compiler 0.5.1` off that field).
`list_tables`' hardcoded `sidecars` literal and `_SUBJECTS` were left alone: they are **RM10**, still
open, and stamping a restated fact only dates the restatement.

## 0.10.2 — enricher 0.6.4: the drafter now names what it supersedes (2026-08-19)

Adopts **just-dna-enricher 0.6.4**, released hours after 0.10.1 shipped and carrying the fix for the
finding 0.10.1 filed. Format, compiler and registry are unchanged at 0.6.1 / 0.6.1 / 0.18.1. One
floor, three documents, no code. 153 tests green, `ruff` clean, `pyright` 0 errors.

### What we told an author yesterday stopped being true overnight

0.10.1 measured what a re-draft actually does to a module drafted before enricher 0.6.3 — recovers
every dropped ClinVar record, retracts none of the collapsed ones, 0 missing and 31 stale on `MLH1` —
and filed it as **S45**. The docstring we shipped with it ended: *"Nothing in the file distinguishes
them."* True of the file, and upstream accepted it and then removed the premise: **0.6.4's
`_superseded_rsid_rows` names those rows after the append**, counted and aggregated, because the
drafting run holds the one thing a file-level predicate cannot reconstruct — the set of rsIDs it is
deliberately writing by coordinate this time.

Verified through our own surface rather than read off their changelog: a real stale-then-re-draft
cycle driven through `draft_from_clinvar`, `added=65, already_present=965`, and the notice arriving in
`warnings` naming **31 rows**, five rsIDs and "and 26 more" —

> 31 row(s) already in variants.csv identify by rsID alone (rs1060500703, rs1553653237, …) — but this
> run writes those rsIDs with their full coordinate … This run has ADDED the coordinate-keyed rows
> beside them and has removed nothing: drafting never deletes an authored row, and yours may have
> been curated since.

`draft_from_clinvar`'s docstring, the skill and `references/SYMPTOMS.md` now say this. The framing
that matters is that **the warning is the safety net, not the plan**: a fresh directory reconciled
against the old module is still the cleaner remediation, and the notice is for the author who re-ran
in place — which is what the shorter instruction told them to do.

### Nothing deletes the stale rows, and that was upheld for our reason

We argued the drafter must name and never remove, because by re-draft time a drafted row is authored
material and a human may have curated its `genotype`, `state` and `conclusion` — deleting curated work
to repair a drafting defect is a trade only the author can make. Upstream took that and left the
deletion with the author. So the action lands in the checklist, not in a tool: **delete each named row
once the coordinate rows cover its records.**

### The correction to our suggestion is worth more than the fix

We proposed the fix belong in `append_partial_rows`, reasoning it has both halves at merge time. It
has the *file* but not the *predicate*: it is the compiler's generic drafting helper, shared by every
provider, and teaching it about rsIDs would put a source's identity rule into the tier that must not
carry one. It went into `clinvar_draft`, where the source convention already lives. Recorded in `F36`
because the lesson generalises to the next suggestion we write — **"it has the data" is not "it is the
right tier"**.

### Also

- **`F36` closed and moved** to `previous_issues.md`, prose intact. Filed, accepted, fixed, released
  and adopted inside one day.
- **Our ClinPGx contrast was independently re-run upstream** and confirmed — 18,691 stale rows
  re-drafting to 18,895 with 0 missing and 0 stale — and **`S44` skipped rows, `S41` wrote them under
  an identity that has since moved** is now the frame for the whole finding in their ENRICHER.md and
  changelog. That sentence is what stops the next reader generalising one remediation to both.
- **One thing left open on our side, by upstream's request.** Neither of us re-measured the downstream
  label errors — both established only that the rows carrying them survive a re-draft. A module
  drafted after 0.6.4 with its superseded rows deleted that *still* shows mislabelled expansions is a
  separate defect, and upstream wants it as its own item.
- **No test added, deliberately.** Reproducing this needs an upstream private predicate monkeypatched
  to manufacture the old behaviour — a fixture for someone else's regression, which would break the
  day they rename the function and would be testing their fix rather than our pass-through. Upstream
  carries three tests including the MLH1 measurement asserted as a relationship.

## 0.10.1 — enricher 0.6.3, registry 0.18.1, and a drafter that had been dropping rows (2026-08-19)

Adopts **just-dna-enricher 0.6.3** and **just-dna-registry 0.18.1**; `just-dna-format` and
`just-dna-compiler` stay at **0.6.1**, so this is the second partial cut in the 0.6 line and `uv sync`
now gives `0.6.1 / 0.6.1 / 0.6.3`. No tool was added or removed and no signature changed. 153 tests
green, `ruff` clean.

### The blocker in 0.10.0's own release note is gone

0.10.0 opened by saying every version-guarded registry call was refused, because both deployed
instances answered `format: 0.5.4` against our 0.6.1 client. **Both are now on `0.6.1`, and both are
serving registry 0.18.1.** Re-probed rather than assumed, and then driven end to end: the exact call
that came back `409 just-dna-format contract mismatch: server 0.5.4, client 0.6.1` — a
`download` of `eric-mods/lactose_tolerance@1.0.0` — now returns its manifest, and
`assert_compatible()` passes against production and the polygon alike.

Nothing in our code changed for this, which is the point: `targets.instance_note` is a suffix on an
existing `except RegistryError` arm, so it costs nothing while the contract agrees and is still there
if an instance is rolled back. Worth knowing for anyone reading that module's card: the artifact
itself is still stamped `just-dna-compiler 0.5.1`, which is the contract gap registry 0.18.0's
`upgrade` now detects on its own. That is an operator's sweep, not an author's problem.

### `draft_from_clinvar` had been silently dropping ClinVar records

Upstream **S41**. Below 0.6.3 `multi_allelic_rsids` keyed the site on `ref` and fired on more than one
alt *within* that group — which is not what its own docstring claimed. An ordinary ClinVar dup/del
mirror pair (`A>AT` beside `ATT>A` at one position, the same event written from either side) is two
groups of one alt each, so the rsID was never flagged as multi-allelic, both records reduced to the
same rsid-only identity, and the second was dropped as `already_present`. Upstream measured 725
records lost over five genes, **187 of them dropping the better-reviewed half**, because
`select_by_gene` orders by `ref` before `review_stars DESC` — so which record survived was decided by
allele spelling rather than by evidence.

The fix is entirely upstream's; ours is the floor and what we tell an author holding an
already-drafted module. Upstream said such modules "need a re-draft" and said plainly they had not
measured that end to end, so we did, on `MLH1` at 2★ against the local snapshot:

| | rows | distinct identities |
|---|---:|---:|
| drafted with the 0.6.2 predicate | 996 | — |
| drafted fresh on 0.6.3 | 1,030 | 882 |
| the first, re-drafted on 0.6.3 | 1,061 | 913 |

**A re-draft recovers every dropped record and retracts none of the collapsed ones** — 0 identities
missing, 31 present that a fresh draft does not contain, and 1,061 − 1,030 = 913 − 882 = 31 exactly.
Because drafting appends, the correct coordinate-keyed rows arrive *beside* the stale rsid-only rows
rather than replacing them, and the module then asserts both the right answer and the wrong one for
the same locus. Those 31 are precisely the rows carrying the downstream half of S41.

**And they cannot be found from inside the module.** The obvious predicate — an rsid-only row whose
rsID also appears on a coordinate row — finds 0 of 31, because a coordinate-identity row carries no
`rsid` at all. So `draft_from_clinvar`'s docstring and the skill now say to draft into a **fresh
directory** and reconcile against that, and say why re-running over the existing file looks like it
worked. Filed upstream as **S45** and tracked as **F36**; the candidate we offered is that
`append_partial_rows` *name* those rows on the draft report — it holds both halves at merge time —
and explicitly not that it delete them, since by re-draft time a human may have curated the
`genotype`, `state` and `conclusion` on a drafted row.

### `draft_from_clinpgx` was dropping rows too, and the repair is the opposite one

Upstream **S44**: the genotype gate took only the doubled single-base form, so `CTT/CTT` — already
separated by the source — and the bare haploid spelling ClinPGx uses for mtDNA were declined. That
cost **CFTR F508del** (its annotation carries a `del`-spelled genotype and a pure-nucleotide one under
one `annotation_id`, so skipping the annotation discarded the writable row with it) and **every
MT-RNR1 annotation**, 32 rows at evidence level 1A.

The remediation is not the same, and assuming it was is the trap. We ran the equivalent probe with a
stand-in old gate deliberately *broader* than 0.6.2's — 12,410 rows where the fix produces 18,895, so
it declined more than the real one and is therefore the harder case — and a plain re-draft into the
same directory landed on **18,895 rows, 0 stale, 0 missing**: exactly the fresh draft. S44 *skipped*
rows; S41 *wrote them under an identity that has since moved*. Only the second leaves anything behind.
Both docstrings now say which shape they are.

### The skill was teaching a version rule that stopped being true

`SKILL.md` said `module.version` must be quoted because *"unquoted 1 parses as an int and is rejected"*.
Measured on installed 0.6.1: `ModuleInfo(version=1).version` is `'1.0.0'` — accepted. That was the
**pre-0.6** behaviour, and format 0.6's RM17 widening at `mode="before"` is what fixed it, after 26 of
61 foreign modules refused on an unquoted integer.

Quoting is still right, so the checklist line stays — but for the two reasons that are actually true.
The unquoted **decimal** is the hazard, and it is refused with a good message (YAML reads `1.10` as
`1.1`, so the author's text is gone before any validator runs). The silent one is a **digitless**
version: `draft`, `TBD` and `abc` all coerce to `'0.0.0'`, which is a real version somebody could mean,
and it reaches `manifest.identity.version`. That is upstream's open **RM103** (our S42), filed rather
than fixed because refusing it would newly break specs that compile today. It is not invisible, though,
and the checklist now points at where it shows: `validate_module` warns *"module.version 'draft' was
read as SemVer '0.0.0'"*, confirmed through our own tool surface rather than read off their source.

### Also

- **Floors moved with their reasons.** `just-dna-enricher>=0.6.3` is load-bearing — a drafter that
  quietly writes fewer rows than the source has is the worst kind of floor to leave soft.
  `just-dna-registry>=0.18.1` is not: both 0.18.0 and 0.18.1 declare `Client surface: unchanged` and
  both check out. It moves anyway because 0.18.1 requires enricher 0.6.3 itself, so pinning it stops a
  resolver handing us the new enricher beside a registry built against the old one.
- **Nothing to do for S39, our own filing from 0.10.0.** 0.6.3 threads `load_dotenv_file` through the
  six cache resolvers, where it had been inert. We pass that flag nowhere, so the registry's rule for
  this release — *check the flags you already pass on a dependency bump, an inert argument becoming
  live is a behaviour change with no import to grep for* — was run and came back empty. `F35`'s
  `sys.modules` sweep stays: upstream confirmed our reproduction ran the default path, which the fix
  does not reach, and RM102 is open.
- **S43 needs nothing from us.** `likely_pathogenic` and `likely_benign` turn out to be unwritable
  rather than merely unwritten — parquet columns with no authored field behind them, a literal `False`
  since 0.1.0. Our surface never offered them (`describe_table` is generated from the model, which
  does not declare them) and `passes.py` already reads `clin_sig`. Recorded so nobody adds them.
- **Both fixtures re-verified on the new floor**, unchanged: `assets/fto_bmi` and
  `assets/longevity_2026` are literature-review modules, not ClinVar-drafted, so S41 does not reach
  them and no digest moved.

## 0.10.0 — format 0.6, and authoring gets an end (2026-08-18)

Adopts **just-dna-format 0.6.1**, **just-dna-compiler 0.6.1**, **just-dna-enricher 0.6.2** and
**just-dna-registry 0.17.0**. 0.6 is the first release where the three format-tier packages do *not*
move together — the enricher alone goes to 0.6.2, for RM101 — so the floors name three versions
rather than one.

### The thing to know before upgrading: the live registries are still on 0.5.4

`contract_compatible` treats a `0.x` **minor** as a breaking contract, in both directions. Both
deployed instances answer `format: 0.5.4` today, so on this release every version-guarded registry
call — publish, import, download, validate, check, is_published — is refused until the operator
upgrades them. Confirmed live rather than reasoned about: `registry_download` of
`eric-mods/lactose_tolerance@1.0.0` comes back `409 just-dna-format contract mismatch: server 0.5.4,
client 0.6.1`.

That is correct behaviour — a 0.6 artifact genuinely cannot be published to a 0.5 catalog — but
upstream's message names two version numbers beside the module the author was trying to publish, and
reads like something they did. `targets.instance_note` appends the sentence that says otherwise:
whose problem it is, that nothing about the spec will change the answer, and that recompiling will
not either.

It is a **suffix on the existing `except RegistryError` arm**, not a new `except` clause ahead of it.
Both mismatch types are `RegistryError` subclasses, so an arm for them placed after the parent would
be dead and silently so — the same trap the exception work below is about. There is no ordering to
get wrong if there is only ever one arm.

### `close_module` — the step 0.6 tells every author to take

A 0.6 compile warns on every module that records no closure, and told the author to run
`just-dna-compiler close`, which this surface did not wrap. A tier that teaches a step it cannot run
is the failure mode `CLAUDE.md` §5 already names, so it is wrapped.

Closing writes a `closure` into `verification.json` binding the statement to the hash of
`module_spec.yaml` plus the authored CSVs as they stand; edit one afterwards and the compiler drops
it. Deliberately not signed from here — `close --private-key` exists and a key that reaches a tool
argument has been logged, so that half stays CLI-only and the docstring says why.

Both committed fixtures are now closed, which is what makes `assets/fto_bmi` compile with **zero
warnings** for the first time. It had one under 0.5.4 — the `licensing.csv` orphan (`F21`/`S23`) —
and upstream has since fixed that, so the README line promising "expect one warning" was teaching a
warning that no longer exists.

### `licensing.csv`, and the two spellings that must never both exist

0.6 renames `sources.csv` to `licensing.csv`. Both read; only the new one is created; a module
carrying **both** is refused rather than merged, because two copies of a fact-hashed, hand-editable
table are two claims and preferring either discards somebody's curation silently.

`draft.DRAFTABLE` lists both names and backs them with one model, so `list_tables` would have
presented one table as two kinds. `TableKind` gains `deprecated` and `preferred`, both read from
`just_dna_format.layout` rather than restated, and `_SUBJECTS` carries the entry once under the
current spelling with the old one inheriting it — two entries would have answered "which table?"
twice differently the first time somebody edited one line.

`scaffold_module` now routes a deprecated spelling through `layout.sidecar_write_path`: **write to
the file you read**, and the preferred spelling when neither exists. Upstream's scaffold creates
whatever name it is handed, so asking for `sources.csv` on a fresh module used to create a file that
stops being read at format 1.0, in a module being written today. The swap is reported rather than
silent.

The rename stops at the CSV. `sources.parquet` and `manifest.sources` keep their names for the whole
`0.x` tail, so nothing here was renamed to match.

### An outage stops costing three passes their work

`enrich_facts` ran its passes inside no `try` at all, so a gnomAD 503 propagated out of the tool and
took `gene_metrics` and `dosage` with it, including whatever they had already written. Each pass now
gets its own `try`, and the report separates two verdicts that read identically before: `unreachable`
(the source was asked and never answered) from `failed` (the source answered; the problem is local).
`covered: []` beside `missing: []` cannot distinguish those, which is the whole reason the field
exists rather than a warning line. `success` is false when either is non-empty — a pass that never
reached its source did not complete.

This is what enricher 0.6.2 makes possible: every pass now raises its own type with unavailability as
a **subclass**. That is also the release's one real hazard, and it fails *silently* — a `*Unavailable`
arm written after its parent is dead, so `unreachable` comes back empty on exactly the run where a
source was down. `tests/test_passes.py` carries an AST walk that fails on any `except` clause an
earlier arm of the same `try` already catches, plus a self-test driving all three shapes, because a
guard reporting zero proves nothing until it is shown able to report one. Both were run against the
parent-first ordering and watched to fail; the walk names the line.

`_SOURCE_ERRORS` stays parents-only in one tuple, which upstream's upgrade table calls "keeps working
unchanged" — a parent and its subclass in one tuple is redundant, not dead.

### The RM44 counters, and `fully_resolved` stops being read alone

`compile_module` reports `resolution_subjects`, `positional_rows`, `positional_rows_placed`,
`expanded_keys` and `expanded_rows`. The first is the denominator `fully_resolved` quantifies over:
over an empty list that flag is `all()` over nothing, so `true` beside `0` says the module resolved
everything there was, which was nothing. All five are `int | None` and **null is never zero** — each
has a meaningful zero, so coalescing would report a module as having no positional rows where nothing
had counted them.

### The suite was not hermetic, and had not been for a while (`F35`, upstream `S39`)

`test_a_token_does_not_leak_between_sessions` was failing before any of this work — on 0.5.4 too —
and the reason was worth chasing. `just_dna_enricher.locations` calls `load_dotenv` while resolving a
cache path, which `build_server` reaches through `net.py`, and `load_dotenv(override=False)` skips a
key that is **present** — so `F24`'s fixture clearing the environment with `delenv` is precisely what
let the file win. Measured: `JMC_TEST_API_KEY` was `None` after the fixture and held a live
`mk_live_…` polygon token immediately after `build_server`. A session that had authenticated nothing
resolved a real credential, got past the auth check, and failed on the offline ceiling behind it.

The fixture now neutralizes the **loader**, by walking `sys.modules` — every module that did `from
dotenv import load_dotenv` holds its own binding, so patching `dotenv.load_dotenv` would reach none of
them. `setenv(VAR, "")` is not available as a blanket fix here and that is why `delenv` was chosen
originally: these variables reach typed fields, so `JMC_PORT=""` is a parse error rather than "unset".

Filed upstream the same day as format-tree `S39`, because a *library* path loading the caller's `.env`
surprises every consumer, not only this one.

### Also

- **`check_identifiers` still writes nothing, and that now costs something.** The enricher's
  `check-identifiers` / `check-acmg` **CLI commands** record that the question was put; the functions
  we call do not. So a module authored entirely here carries no attestation for those checks. Named
  in `tools/research.py` rather than left implied, and filed as **RM9** — the fix needs a policy
  decision about that module's read-only promise, not just code.
- **Digests re-measured and re-recorded.** `assets/fto_bmi` moved to
  `sha256:c3d633f0…` and `assets/longevity_2026` to `sha256:2df1276a…`; both `content_signature`s
  are unchanged, which is upstream's promise measured on our own fixtures. `README.md` and both
  fixture READMEs now say that a digest is reproducible **under one compiler version** and that
  `content_signature` is the one to compare across an upgrade.
- **Skill and references updated for 0.6**: the pipeline diagram gains `close`, `SYMPTOMS.md` gains
  the PMC-id refusal (RM50), the wrong-build coordinate error (RM48, an error in *both* modes), the
  sidecar collision, the deprecation and the closure warning; `CLI.md` gains `close`, `gene-validity`,
  `assertions`, `gwas` and `hint recover`, plus the `verify --require-marketplace` default that
  rejects every locally-compiled module; `TABLES.md` gains `licensing.csv` and the three new fact
  tables, with the warning that `gwas_effects.csv` deliberately does not fill `weight`.
- **RM93 and RM98 needed no mitigation** — both were 0.6.0 defects fixed in 0.6.1, which is our
  floor. Recorded so nobody builds a guard against them.

## Unreleased — Codex marketplace packaging

- Added a native `.codex-plugin` manifest with a Codex-compatible MCP declaration.
- Reused the existing `create-module` and `find-evidence` skills so they appear in
  Codex's skill and slash-command picker.
- Kept the MCP runtime checkout-relative through `${PLUGIN_ROOT}`; Codex and Claude
  now launch the same source package without duplicating the server implementation.

## 0.9.2 — the off-by-one gets a source and a check (2026-08-14)

Skill only; no code changed. `start` being the 1-based VCF position was already stated in three
places, and the shifted-module story was already told at length — but all of it was *downstream* of
the mistake. It said what goes wrong and what no gate catches. It did not say where the wrong number
comes from, or how to find out before writing the file.

- **A callout at the top of `SKILL.md`**, above everything, for anyone about to type a coordinate.
  Every gate passes on an off-by-one module; that belongs before step 1, not inside step 3.
- **Where the wrong number comes from.** Nobody decides to subtract one — it arrives with the source,
  and the dangerous sources use *both* conventions in different fields. UCSC's position box is
  1-based and its Table Browser `chromStart`/`txStart` columns are 0-based; `pysam`'s `record.pos` is
  1-based and `record.start` is 0-based. So the rule is not "know your source", it is **know which
  field**, and the failure is usually *not adding one back* rather than subtracting again.
- **The decoy in the other direction.** VCF anchors an indel on the base *before* it, so an insertion
  a paper puts at X appears at `POS` X−1 with the anchor base leading both `ref` and `alts`. That
  looks exactly like an unfixed off-by-one and must not be "repaired".
- **A one-call check that fires on row 1 instead of row 3,000.** Author one row, call
  `lookup_variant`, compare `start` — the signal is exact equality, and a difference of exactly 1 in
  a consistent direction is conversion rather than a typo. Run once per *source*. Verified against
  the real record while writing it: `rs4988235` → `2:135851076 G>A`, with the position arriving in
  `withheld` under `applied: false`. That is the point made twice — reading the number to check a
  convention is fine, pasting it is the vacuous-check mistake one section earlier.
- **A checklist line** gated on having authored a `start` at all, and a pointer from
  `references/SYMPTOMS.md`'s `ref mismatch` entry back to the source list, since that message is
  where an author meets this after the fact.

## 0.9.1 — a README for the person the plugin is for (2026-08-14)

Docs only; no code changed. The README had grown into a server manual — tool tiers, mode-switching
tables, auth resolution order, `pgrep` — and the first thing a prospective *module author* met was
`ToolAnnotations`. It is now user-first and short, and everything it used to carry moved rather than
being deleted.

- **`README.md`** — what a module is in four lines (the "rulebook" framing that landed on a real
  beginner), install, the seven steps, the four curation rules, a worked example you can actually
  run, and publishing. The DNA-reading misconception is corrected up front and unprompted, because
  every later step reads as nonsense against it.
- **`docs/FOR_DEVELOPERS.md`** — new. The full tool table, tiers, mode switching, reload semantics,
  auth, safety switches, deployment, layout, upstream.
- **`docs/BEYOND_BASICS.md`** — new. Pharmacogenomics and its no-sale licence trap, polygenic
  scores, binning tables, deeper evidence work, reading other people's modules, and what happens
  after a publish. It names capability areas and defers every column list to `describe_table`, so
  it cannot drift the way a restated schema does.

**The worked example is run, not written.** `assets/fto_bmi` — one rsID, one PMID — is verified end
to end before being documented: `scaffold_module` creates the three files, `lint_rows` reports the
six columns it leaves to the author, `validate_module(strict)` returns zero findings, and
`compile_module(strict)` reproduces `sha256:e52bd75…`, the digest the fixture's own README recorded
on 2026-08-11. The one expected compile warning is named in the README rather than hidden, so a
reader who runs it is not surprised by it.

## 0.9.0 — the card an author actually ships (2026-08-12)

Adopts `just-dna-registry` **0.14.0**. The floor moves to `>=0.14.0` and that is the load-bearing
part: 0.14.0 is the release that projects a spec-directory `README.md` onto the module card, so
**below it every module we publish has a blank catalog card** — which is the first thing a browsing
consumer sees. Our own pin was what kept us off the fix (`F33`).

Verified by importing the symbol from the installed package, per the rule: `amend_readme present:
True` on 0.14.0, `False` on 0.13.0.

**Their `Client surface: unchanged` line did its job.** `F15` asked for exactly this, and reading one
line replaced reading a release in full to establish that our eight-plus methods had not moved. Four
things were *added*, and all four turned out to matter here.

### `registry_amend_readme` — the one published-module write that spends nothing

The readme sits **outside `artifact.digest`**, deliberately, so prose cannot change a module's content
identity. That makes it the only thing about a published version that is repairable, which is why it
earned a wrapper rather than a note telling authors to shell out.

Two refusals, both tested, both about not making things worse:

- **A path is not prose.** Upstream disambiguates a file path from markdown *by type*, and every MCP
  argument arrives as a string — so one collapsed parameter would let `readme="spec/README.md"`
  publish the path itself as the card's text, on a module whose whole problem was an unreadable card.
  `spec_dir` and `readme_text` are separate, and both-at-once is refused.
- **An empty body is refused.** The field is last-publish-wins, so empty prose *replaces* what is
  there. A tool for fixing a blank card must not be able to make one.

Checks that need no credential run **before** `require_key`, matching `registry_publish`'s order:
sending an author to fetch a token for a call that could never succeed is a dead end. The first draft
had it backwards and the new tests caught it — they asserted refusals and got an unauthenticated
result instead.

**Run against the real waiting caller**, not a fixture: `test-sheep/longevity_2026@1.0.0` went from a
zero-length readme to 6860 characters, and the artifact digest afterwards was byte-identical to the
one `published.json` recorded at publish time. That is the tool's central claim, so it is worth
having actually run.

### A download now carries the authored CSVs (`include_inputs`)

`download(include_inputs=…)` is new, and upstream's default is `false` — which means the compiled
parquets and `manifest.json` arrive and the *authored spec does not*. Measured against
`eric-mods/lactose_tolerance@1.0.0`: 4 files without, 7 with, the three extra being
`module_spec.yaml`, `variants.csv` and `studies.csv`.

**Our `registry_download` defaults it to `true`**, and the docstring says it differs from the client
on purpose. This is an authoring surface; the published spec is the most instructive thing the
registry holds, and a "worked example" without the CSVs is not one. With the inputs present you
usually do not need `reverse_module` on a downloaded module — the spec arrived as itself.

`layout="split"` also shipped and is **not** exposed. It emits the enricher's files under `derived/`,
which is genuinely useful for seeing which files an author wrote — and a tree
`just-dna-compiler compile` refuses, because it wants the authored tables at the spec root. Offering
it from here would hand someone a directory they cannot rebuild.

### `available: true` that this surface still cannot act on

0.14.0 turned production's test-data ban into a **default** rather than an absolute:
`allow_test_data=true` is a documented way through, and the availability pre-flight gained
`requires_allow_test_data` and a `warnings` list to stop contradicting the claim it precedes.

Both are surfaced, and `requires_allow_test_data` is **null rather than false** when the instance did
not report it — "did not say" is not "does not require it", and the difference decides whether a name
that reads as free will actually be accepted. Confirmed live: production answers
`available: true, requires_allow_test_data: true` for `test-modules`.

**We do not expose the override**, and the refusal messages now say that the remaining refusal is
partly ours instead of claiming the server makes it impossible. Keeping it is the decision, for the
reason upstream gives for keeping the default: a mistyped namespace there spends a version number and
a global content hash that only an operator purge frees. An agent that can wave that through on an
author's behalf is what the polygon default exists to prevent.

### `README.md`, taught where an author will read it

The skill's directory layout listed `logo.png` as optional and mentioned no readme at all, so
following it produced a blank card. It now names `README.md` as the file that *becomes* the card, says
what belongs in it — what the module claims, which population the evidence came from, what it does not
cover — and records that `MODULE.md` is renamed on upload with a warning while any other spelling is
carried but never read.

### Filed upstream

- **registry `S8`** — their `specfiles.py` comment and changelog both attribute `MODULE.md` to
  "`just-module-creator`'s `write_module_md` tool". **That tool has never existed here**: no match in
  the tree, and `git log --all -S write_module_md` finds none in the history either. It lives in
  `just-dna-pipelines`, in a file named `module_creator.py` — a good enough reason for the mix-up, and
  it will only get more confusing with age. Their rename decision is unaffected and right; the cost is
  a wrong address for anyone who later wants the producer to emit `README.md` at the source.
- **registry `S9`** — `amend_readme` is on the client and not the CLI, while `amend-logo` and
  `amend-changelog` both are. Noticed because our `references/CLI.md` documents their CLI for authors
  who drive it directly, and now has to say the readme is the one amend they cannot do without our
  server.

## 0.8.0 — ask whether it would publish, and hermeticity stops being a promise (2026-08-12)

Two things: `RM8` — the registry client surface is wrapped — and `F24`, where the suite's
hermeticity was a convention that had quietly stopped holding.

### Ask whether it would publish, without spending a version number (RM8)

Four registry releases of `RegistryClient` had gone unwrapped since we adopted 0.12.0 for the
test/prod split. Registry 0.13.0 landing on PyPI yesterday was the precondition, because it
made `would_publish_module_level` a field to *wrap* rather than one to feature-detect.

Two gated pre-flights and two ungated reads:

- **`registry_check`** — the full dry run, and the reason this item mattered. It runs the
  server's own publish gates and **spends no version number**, which on production is the
  difference between a rehearsal and something irreversible.
- **`registry_validate`** — the same without the network tier. It still answers two things a
  local `validate_module` cannot: whether `module.name` matches the path, and whether identical
  authored data is already published under someone else's name.
- **`registry_is_published`** — ungated, uploads nothing. The content signature is computed
  locally, so an author can ask "is this data already out there, under any name" before they
  have a token at all.
- **`registry_health`** — reports the instance's own mode, so a rehearsal is *confirmed* rather
  than assumed. `expect_mode` already refuses a mismatch; this is how you see it beforehand.

**Where the work actually was: not letting a skip look like a verdict.** One
`PublishPreflight` carries *two*, deliberately.

`module_level_clear` is upstream's `would_publish_module_level`, renamed so nothing reads it as
a green light — it composes exactly three gates and excludes the network tier. `verdict` is the
whole dry run and is **null whenever that tier did not run**: on a bare validate, on
`skipped_reason`, and when no token was resolvable. Defaulting it to `false` would let "we could
not ask" arrive shaped like "would not publish", which is the same error as a skip producing a
pass with the sign flipped.

`rerun_rather_than_fix` carries `S20` all the way to the author's next action. A false verdict
beside unreachable rsIDs means **re-run**, not go and fix the spec: a strict publish against an
unreachable Ensembl really does refuse, while the variants may be perfectly findable. Telling an
author to fix that is how real rows get deleted. `unchecked` and `non_blocking` keep upstream's
other careful distinctions — a `clin_sig` check the operator has no snapshot for never blocks
and is never dropped either, and identifier findings never move the verdict because a publish
does not run that pass.

**Verified live against the polygon, not only in the suite.** A clean `assets/fto_bmi` returned
`verdict: true` in 1.3s; the same spec with one invalid `state` returned `verdict: null` with
`verdict_unavailable: "invalid_spec"` — null rather than false, which is the entire point.

**One RM8 bullet was already done and one is deliberately skipped.** `content_signature` was
listed, but `module_signature` has always called the same `just_dna_compiler` function the client
method wraps, so wrapping the client's would have been a second path to one answer.
`issue_jwt_token` returns 501 unless the deployment configures a signing secret and nothing here
consumes a JWT — a tool that is usually a 501 is worse than no tool.

### The suite's hermeticity was a promise, not a mechanism (F24)

`CLAUDE.md` §6 claimed no test could read a developer's `.env`. That held only for as long as
every construction remembered `_env_file=None`, and by today `.env` carried a live polygon token:

```
Settings(_env_file=None).test_api_key    : None         # hermetic, as documented
Settings().test_api_key                  : 'mk_live_…'  # the developer's REAL token
Settings().offline                       : False        # ← worse than the finding said
```

That last line is what the original note missed. A forgotten kwarg lost **both** properties, so a
test could reach the network *while holding a live credential* — passing locally, passing in CI
where `.env` is absent, and meaning something different on each machine.

Now an autouse fixture points `env_file` at a path that cannot exist and clears the ecosystem's
variables from `os.environ`, so forgetting the kwarg is harmless. `env_file` stays in
`model_config`: the product needs it, and breaking the product to protect the suite is the wrong
trade.

**The clear-list is derived from `Settings.model_fields`, not written** — and that mattered inside
the same change. The hand-written first draft covered the credentials and missed seven variables,
`JMC_API_KEY_HEADER`, `JMC_TRANSPORT` and `JMC_PORT` among them; an exported `JMC_API_KEY_HEADER`
changes what a test asserts as effectively as a token does and far less visibly. Only the four
upstream names stay hand-maintained, because no field of ours can name them.

### `assets/longevity_2026` — a second reference example, authored with no human in the loop

Thirteen longevity rsIDs, 19 authored rows, grounded in five papers that are all 2025 or 2026 — one
of them a bioRxiv preprint, cited by the PMID the NIH preprint pilot gives it. Written end to end by
an agent through the MCP surface, `authorship: [ai, agent]`, and rehearsed to
`test-sheep/longevity_2026@1.0.0` on the polygon, where the server's own recompile reproduced the
local `artifact_digest` exactly.

It complements `assets/fto_bmi` rather than repeating it. `fto_bmi` is the *triage* example — seven
offered claims, four of them fabricated gene/rsID pairings, one row surviving. This one is the
*grounding* example: nothing was fabricated and the interesting decisions are all about how much a
row may claim. Five variants named in the same papers were dropped for having no stated effect
allele, nine rare candidates carry `direction: unknown` and no weight because the preprint prioritises
them without a direction, and exactly one preprint variant is written `protective` — the *CGAS* one
with functional work behind it, at a deliberately small weight.

Two findings came out of authoring it, both in `docs/dogfooding.md`: **`F29`** (nothing can search for
a trait CURIE, so a correct `trait_efo_id` was reached only because a guess landed on a deprecated
term whose obsolescence pointer named the replacement) and a second, sharper instance of **`F26`** —
this session's server had none of the four registry tools listed above, while the repo, the manifest
and the skill were all 0.8.0. A build that has been reloaded once goes stale again at the next bump,
and the symptom this time was the skill teaching four steps the surface could not run.

`S7` was filed to the registry's intake: a `README.md` in the spec directory is uploaded by
`gather_spec_files` and never surfaces — the published card's `readme` stays empty, with no
`amend_readme` on the client and no documentation of what does populate it.

## 0.7.0 — six mitigations come out, and a target that verifies itself (2026-08-11)

Upstream shipped. `uv sync` now installs format/compiler/enricher **0.5.4** and
`just-dna-registry` **0.13.0**, and the floors say so. Between them they released every fix
this repo was holding a guard for, so this release is mostly *deletion of caution* — plus one
real behaviour change, which is why it is a minor.

**Every claim below was verified by importing the symbol from the installed package**, never
by reading the sibling checkout or a changelog. That is the rule this repo learned the hard
way: on 2026-08-11 every entry in `just-dna-format-pending-fixes.md` said "open upstream"
while all eight had been answered and six were already fixed in tree.

### The behaviour change: a declared target is now verified

`targets.client_for` is the single construction point for every `RegistryClient` in the
server, and it always passes `expect_mode=target`. Registry 0.13.0 reports `REGISTRY_MODE` on
`/health` and `/api/v1/version`, and the client raises `ModeMismatchError` before the first
call that could spend anything.

So the polygon/production split stopped being a convention. Our configuration records which
instance we *meant*; the server says which one *answered*; a publish aimed at the polygon that
would have landed on production now refuses instead of succeeding irreversibly. **A server
that reports no mode fails the check** — upstream's decision, and the right one: asking for
verification and getting silence is not a pass, and the remedy for that direction is a server
upgrade while the remedy for the other direction is nothing.

Passed uniformly rather than only where a guarded method is reached. The alternative is a
per-site judgement about which upstream method is guarded *today*, which is exactly the kind
of fact that goes stale in silence. A test scans the source so a stray `RegistryClient(...)`
anywhere else fails the suite — verified by adding one and watching it fail.

What we still do **not** do is infer a mode ourselves. Upstream's reply to `S3` says why both
halves belong: ours records the intent, the guard checks the answer.

### `lookup_citation` answers identity, not just existence (F9, closed)

`CitationHint` gained `title` / `journal` / `year` / `first_author`, all from the same
`esummary` response that answers existence, so they cost no extra request. `CitationLookup`
carries all four and the docstring now tells a caller to read the title and compare it against
the paper they meant — **a title that disagrees means the id is wrong however true
`pmid_exists` is.**

The working rule did not change, for a reason that was never about titles: a title checks an
id you already hold, and only a search finds the id you should be citing. "Take every PMID
from a `literature_search` result" stays in both skills and in `server.INSTRUCTIONS`.

### `check_identifiers` now catches the fabrication pattern (F23, closed)

The highest-value check in the triage workflow, and it used to require leaving the product.
`IdentifierReport` carries `gene_locus_conflicts` — rows whose `gene` sits on a different
chromosome than the row's own variant — and `gene_locus_check_skipped`, because an empty
conflict list otherwise says two opposite things: "compared everything, nothing disagreed" and
"never compared".

This is the pairing that separated the honest half of a machine-written source from the
fabricated half: four of seven rows named a real gene with an rsID on another chromosome, and
every other check passed on each half separately. Upstream's sentence is passed through
verbatim rather than reformatted — it already names both chromosomes and what to do, and a
second wording in front of one finding is how two answers to one question start.

`skills/create-module/SKILL.md`'s triage step 2 now names the tool instead of an
explicitly-labelled manual step.

### `sources.csv` is a table kind (F20, F21, closed)

Upstream put it in `draft.DRAFTABLE` with `(source, layer)` as its key and taught
`authoring_reference()` about `SourceRow`. **Our half had to move too, and with upstream's
alone it got worse**: `sources.csv` appeared as a table kind *and* under `sidecars` ("do not
hand-author"), telling an author two opposite things. The hardcoded sidecar literal is gone
and it has a `_SUBJECTS` entry, so all four schema tools answer for it.

`S23` also inverted the incentive back the right way: a `literature` row is no longer reported
as unused when `studies.csv` carries rows, and a source a fact table *does* cite with no row
now warns that its terms are unrecorded. Re-verified on `assets/fto_bmi`'s real rows —
compliance silent, omission warns, exactly the reverse of what shipped before. The skill's
rule is corrected to match; it previously told authors the opposite of what happened.

### Findings now carry the line an editor shows (F14, closed)

`LintFinding.line` exists and `to_findings` passes it through. **Never derived:** `row` is a
0-based data index and `line` is 1-based and header-inclusive, so computing one from the other
would bake in an offset that goes silently wrong the day upstream changes either convention.
`references/SYMPTOMS.md` gained the two entries this finding argued for — the boolean misparse
on a correctly-written column, and what to do when `row` and `line` disagree about one CSV.

### An unreachable Ensembl is unchecked, not absent (F17, closed)

Never mitigated here, and the fix vindicates that. `checked` now records the source on the
answered-empty path too — which is precisely the string the rejected workaround would have
keyed on, so `"ensembl-rest" not in checked` would have **inverted the day 0.5.4 landed**,
silently, with our tests green. Waiting cost nothing; building would have cost a wrong answer.

Nothing to adopt in code: `lookup_variant` is a pass-through and the new `warning` reaches a
caller unchanged. The guidance changed — triage step 1 says to read the finding and re-run on
the warning, rather than inferring unchecked-ness from a missing set element.

### `ATTESTATION_BEARING`, and the consequence that outlives it (S11)

`describe_table` reports `attestation_bearing` as a **subset** of `redundancy_bearing`, so the
sharper refusal reason reaches an agent instead of living only in `CLAUDE.md`. Upstream added
the constant *and* kept both provenance columns in `REDUNDANCY_BEARING`, because they qualify
under that map's own definition too.

The rule is unchanged in substance, and worth restating because a released constant can look
like a solved problem: once a fulltext has been read through `fetch_fulltext`, `quotes_found`
on that row is no longer independent evidence. It has degraded to a citation-pairing check —
still worth having, since it catches a quote filed against the wrong PMID — but nothing
establishes that a human ever looked.

### Kept on purpose

- **`ServiceGate`'s lock.** Upstream made `PacingGate` thread-safe (`S15`) *because* the
  injection API asks callers to share one. Two locks is harmless; none is a race. Registry
  0.13.0 adopted the same fix and corrected three comments that had claimed
  `enrich_max_concurrency = 1` was what made sharing a bundle correct — true through 0.5.3,
  wrong now. Ours never made that claim.
- **`compile_module`'s `resolve_with_ensembl=True` pin.** `S14`'s rename was **refused** with
  a reason — the compiler has no network branch, so a `--no-ensembl` flag would assert
  something false. That makes the pin permanent rather than interim.
- **`_module_card`'s defensive projection.** Upstream says it is safe to delete against a 0.13
  server, and the reference docs are now version-stamped, which was the condition `CLAUDE.md`
  set. Kept anyway, for a **narrower** reason than the one it was written for: `get_module` is
  not one of the six methods `assert_compatible` guards, so a self-hosted instance older than
  0.13 answers it with no compatibility check in front of it. Our floor pins the *client*; the
  server on the other end is someone else's deployment. The comment now says that instead.

### Where the findings went

`F9`, `F20`, `F21` and `F23` moved to [previous_issues.md](previous_issues.md) — moved, not
copied. `F14`, `F16`, `F17` and `F11`'s upstream half are closed in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md). `F15` is partly answered:
per-release `Client surface:` lines and version-stamped reference docs shipped, and the
enumerated contract is open on their roadmap with the reason stated — it needs a contract
version of its own, which is a promise to hold it stable across package releases.

[RM8](ROADMAP.md) is **unblocked, not done**: `would_publish_module_level` is now a field to
wrap rather than one to feature-detect. Wrapping a new tool surface is a separate change from
adopting a version, which is why it is not in this one.

## 0.6.0 — a contact address that is somebody's, and asking before assuming (2026-08-11)

A minor rather than a patch: it adds a configuration variable and changes default network
behaviour. Unpaywall used to sit out every call on a fresh checkout for want of a contact
address; it now always participates.

### `JMC_USER_EMAIL`, and a default behind it

The polite-pool contact resolves in three steps, first hit wins:

1. **`JMC_USER_EMAIL`** — new, and ours. Named for the *user* because that is what the address
   means to the services reading it: NCBI's polite pool and Unpaywall both **meter and contact
   per address**, so it says whose rate-limit budget is being spent.
2. **`JUST_DNA_CONTACT_EMAIL`** — the enricher's own variable, so one `.env` still configures
   both surfaces. **Still inherited, not reimplemented**: `build_services` passes `email=None`
   when ours is unset and lets `EutilsSettings.__post_init__` do that read, because it only
   consults the environment when `email is None`. A change to upstream's precedence is followed
   rather than copied.
3. **`settings.DEFAULT_CONTACT_EMAIL`** — the project's own address, supplied by its owner.

**The default is not the "never fabricate a contact address" rule being bent.** An invented
address misattributes traffic to a stranger; this one attributes it to the people who ship the
tool, who accept that. What it costs is *attribution*, and the cost is real: an install that sets
nothing pools its budget with every other unconfigured install and sends any abuse report to the
project's inbox rather than the author's. So the default exists to stop a source sitting out a
call, **not** to make configuring one optional — `.env.template` asks for `JMC_USER_EMAIL` in its
own section, and `build_services` logs *which of the three steps answered*, because "project
default" is the state an operator wants to notice.

Since a contact is now always present, `contact_email()` returns `str`, and the two `if not
email:` branches went with it rather than being left to rot — including the one that made
Unpaywall report itself unavailable.

### The skill now asks, at the top, instead of assuming

Two questions once, before any authoring: **do you want to read the papers or only cite them**
(fulltext work is what makes `provenance_quote` honest, since those columns record a human having
read the paper — an author who will not read anything should learn that at step 0, not step 6),
and **may your email be used for lookups**. Asked **only when neither variable is set**, written
to `.env` as `JMC_USER_EMAIL` so it outlives the session, never asked twice, and "I would rather
not" is a complete answer because the default handles it.

**And never *inferred*** — not from `git config user.email`, not off a commit, not from the
registry account. An address the author did not offer is personal data volunteered on their
behalf, and a wrong guess misattributes traffic to a real stranger.

### Found while testing this

- **`F24`** — the suite's hermeticity is a convention with no guard. `Settings(_env_file=None)` is
  hermetic as documented, but a bare `Settings()` returns the developer's **real** polygon token,
  and nothing fails when a test forgets the kwarg — it just starts meaning something different on
  every machine. (`_load_env()` living inside the CLI's `_run()` rather than at import is what
  keeps the leak narrow, and is right.)
- **`F25`** — nothing reports the resolved contact or which step supplied it, so the skill's new
  "ask only when nothing is configured" precondition can only be established by reading `.env` off
  disk. The `F23` shape again.
- `test_a_contact_address_is_never_invented` changed rather than being deleted: the invariant is
  now that the contact is either operator-configured or the *documented constant*, never
  synthesised — which is what forbids a future default derived from a hostname or a git config.

## 0.5.3 — metaphors that survive a beginner, and triage for a source you were handed (2026-08-11)

Two skill additions, both drawn from an assisted session with a genuine non-specialist rather
than invented at a desk.

### `## Explaining this to someone who is not a geneticist`

The framings that were *observed* to work, not the ones that sound good. **A module is a
rulebook** — "if the DNA says X at spot Y it means Z, and here is who showed it" — did more
than everything else combined; the session visibly turned on it (*"a module is a rulebook,
you should've said so!"*). Alongside it: a variant as a **street address**, a genotype as
**which letters you have there**, a row as **a claim with a receipt**, a blank cell as
**"we don't know" and never "no"**, and the quote columns as **"a human read this and found
the sentence"** rather than "here is a relevant quote".

Two rules travel with the table. **Correct the DNA-reading misconception early and
unprompted** — a beginner's model is "point this at my DNA file and it tells me about me", and
every later step reads as nonsense against it, so they cannot tell you why they are lost. And
**never let a metaphor make a decision**: "rulebook" is right for explaining and wrong for
choosing a column, so the moment the question is what a cell may contain, ask the tool. A
metaphor that answers schema questions has become a second source of truth.

### `## 0 — Where a module comes from`

Where ideas come from — a catalog gap (`registry_search` reads prod, so it is a call and not a
guess), a source that publishes the table, a paper the author read, or **something the author
was told**. That last is the commonest in practice and the only one that begins by *removing*
claims, so it gets a procedure.

**Triaging a source you were handed** is the new content, and it is the run's main
methodological result. A summary is somebody's reading of evidence, and if a machine wrote it
the citations may be generated rather than recalled. Six steps: does the rsID resolve (re-run a
no-locus before believing it — `F17`); **is it on the same chromosome as the named gene**; does
the pairing appear in any paper (read `sources` before trusting an empty result); does the
cited paper say what is claimed (only a title settles identity); are two survivors the same
signal; does anything state the direction, and drop the row if not.

Real numbers, stated in the skill because they calibrate expectations: **seven offered rsIDs
became one authored row.** Four paired a real gene name with an rsID on a different
chromosome — the signature of a generated citation, and invisible to every other check because
both halves pass separately and only the relationship is false. One survivor was dropped as an
LD duplicate, one because no located paper said which allele carried the risk. A number the
summary offered turned out to be the paper's *rescue* factor reported as its deficit.

**Step 2 is labelled as requiring a lookup outside the toolchain**, because it does: nothing
verifies `gene` against the resolved locus (`F23`, upstream `S24` — filed with the argument
that the check belongs at chromosome granularity, since a variant legitimately names a distal
gene and an interval check would fire on correct rows until someone disabled it). Labelling it
is deliberate — a procedure that quietly requires leaving the product trains authors to skip
the step.

## 0.5.2 — and when it genuinely is good, advocate (2026-08-11)

The other half of 0.5.1, and shipped separately only because 0.5.1 was already tagged.
0.5.1 on its own biases toward *under*-publishing: an agent told never to raise production
unasked will also sit on a module that deserves it, and a good module nobody publishes helps
nobody. So the default is now stated as being against **assuming**, not against **advocating**.

The hard part is that "genuinely good" cannot be left to judgement — an agent asked whether
its own work is good will say yes. So both halves are written as checks:

- **The catalog is actually missing it** — `registry_search(gene=…)` / `registry_search(query=…)`
  read production by default, so this is a call with a result you can show the author, not a
  guess. An overlapping module means extend it or say why yours differs, never publish a
  near-duplicate.
- **The module clears every bar** — strict validate *and* strict compile, `fully_resolved`,
  a `resolution.csv` that was produced rather than authored, every PMID from a
  `literature_search` result whose title was read, a declared licence with `sources.csv`
  covering every source, **no `state` or `direction` settled by guessing** (having dropped
  rows for that reason counts in favour), a rehearsal published *and read back*, and enough
  breadth to be worth an immutable version.

**The last bar is the one that fails, and `assets/fto_bmi` is now the worked counter-example
in the skill.** It cleared everything else — strict, fully resolved, VRS minted, one
impeccable citation, honest blanks throughout — and `registry_search(gene="FTO")` returned
`total: 0`, so the gap was real. It was still right not to promote: one locus, no declared
licence, no readme, unsigned. **Underrepresented is necessary and nowhere near sufficient.**
An honest module and a module worth an immutable `1.0.0` are different standards, and
conflating them turns a thin catalog into a catalog of stubs — worse, because a stub occupies
the search result a real module would have had.

The permission is to *advocate*, with the search result and the passing checks as evidence.
It never skips the explicit yes on `registry_claim_namespace(target="prod")` or
`registry_publish(target="prod")`.

## 0.5.1 — the polygon is the default *answer*, not just the default argument (2026-08-11)

Guidance only. No tool signature, vocabulary, artifact or digest change — but it changes
what an agent should *say*, which for a plugin whose contract includes a skill is a
shipped change and not a docs tidy-up.

0.5.0 made every registry write default to `target="test"`. That fixed the mechanism and
left the conversation open. An agent helping a first-time author could still volunteer
`target="prod"` to be helpful, and the exposure is entirely in what a novice's words mean:
**"publish it", "put it online", "share it with my friends", "send it to your site" is not
a request for the immutable catalog** — it is somebody who does not yet know there are two
registries. Observed in an assisted dogfooding session where that last phrasing came up
verbatim, from a user who had been told a module is "a rulebook" ten minutes earlier.

`skills/create-module/SKILL.md` §7 and `server.INSTRUCTIONS` now both say: publish to the
polygon, **name it out loud**, say it is a rehearsal instance nobody installs from, and
stop. Promoting is a separate decision the author makes after seeing a clean run, and it
needs an explicit yes with the cost stated *in* the question — because neither
`registry_claim_namespace(target="prod")` nor `registry_publish(target="prod")` can be
undone by anyone, and production's content claim survives a `yank`, so a half-finished
first module spends the version number *and* the right to publish that data under any
other name.

One corollary, learned the same session by leaving litter: **prefix the module name as well
as the namespace on a first rehearsal** — `test_my_module` under `test-my-ns`. The
operator's `purge-test-data` sweep matches on both halves, so a bare `my_module` inside a
prefixed namespace is rubbish nobody collects, and a first-time author is exactly the
person who will not return to run `registry_delete_module`. The existing advice to rehearse
under the real name is still correct and still there — it is now explicitly *not* the
first-module default.

Recorded in `CLAUDE.md` §10 in the user's own words, because the reasoning ("this confuses
the crowd and we don't want half-baked test modules on prod") is what makes the rule
survive contact with an author who is impatient to share.

## 0.5.0 — two registries, and a publish you can rehearse (2026-08-11)

Adopts the test/prod split the registry shipped in its 0.12.0, and takes the client
from 0.9.1 to 0.12.0 with it — three releases of catch-up in one step.

### Why a rehearsal was impossible before, and is now the default

A published version is immutable *and* its authored rows are claimed by a
name-independent `content_hash` that `yank` does **not** release. On one instance that
makes every practice run permanent: it burns the version number and the right to
publish that data under any other name. Upstream measured it (publish to a sandbox
namespace → publish for real → `409 duplicate_content`, and yanking the sandbox copy
does not help), which is why a "test subtree" in production was never the answer and
the polygon exists instead.

So every registry tool now takes **`target="test" | "prod"`**:

- **The write tools default to `test`** — `registry_register`, `authenticate`,
  `registry_whoami`, `registry_namespace_available`, `registry_claim_namespace`,
  `registry_publish`. A forgotten argument on the polygon costs nothing; the same
  omission against production cannot be undone. Going live is an explicit
  `target="prod"`.
- **The catalog reads default to `prod`** — `registry_search`, `registry_get_module`,
  `registry_download` — because the question they ask is about the published world.
  The asymmetry is deliberate and `tests/test_registry_targets.py` pins both halves, so
  a new registry tool cannot inherit an endpoint by accident or flip a default quietly.
- **`registry_delete_version` / `registry_delete_module`** (new, gated, polygon-only)
  are what make a rehearsal repeatable: they free the version number *and* the content
  claim. Aimed at production they refuse **before sending anything** and name `yank` as
  what production offers instead — a 405 from the far end is a safe answer but not a
  useful one.

### Credentials are per instance, and never substitute

The two deployments keep separate databases, so an account minted on one does not exist
on the other. `JMC_API_KEY` / `REGISTRY_TOKEN` is the production token and
`JMC_TEST_API_KEY` / `REGISTRY_TEST_TOKEN` the polygon's; the HTTP path reads
`X-Registry-Token` and `X-Registry-Test-Token`; `SessionKeyStore` is keyed by
`(session, target)`. **Nothing falls back from one to the other** — a production key on
the polygon is a key for an account that is not there, so a fallback would report "the
registry rejected your token" when the truth is "you have not registered here yet". The
same install-id may be reused on both, and should be: one secret to protect, two
recognisably-yours accounts.

### Naming, checked before the round trip

Production refuses `test-`prefixed namespaces and `test_`prefixed module names with
`422 test_data_on_prod`. We check locally first and **before the credential**, because
telling an author to go and find a token for a call that could never succeed is the
dead end this surface keeps removing. The two prefixes are duplicated from upstream's
`config.Settings.test_data_prefix` and `services.purge.module_name_prefix` rather than
imported — both live outside the client's exported surface, and an import a future
client-only wheel drops would take the server down at load time — so a test asserts
they still match.

Not refused: a `test-` **account handle** on production. The self-register route does
not check it (only the namespace claim, the publish and `issue-key` do), so refusing it
here would invent a rule the server does not have. It is reported after the fact
instead, where it is true: the handle registers, its namespaces will not.

An unprefixed rehearsal on the polygon is likewise advised, never refused — publishing
under the name the module will really carry is the most faithful rehearsal there is.
The note says the consequence: `purge-test-data` sweeps by prefix and will not collect
it, so delete it yourself.

### Also

- **`registry_publish` gained a duplicate-content pre-flight** (`is_published`, new in
  client 0.11). The signature is computed locally from the authored rows — no upload,
  no recompile — and it is the same value the registry gates `409 duplicate_content` on.
  When the check itself fails it says so and the publish proceeds: a check that could
  not run is not a check that passed, and the server runs the authoritative one anyway.
- **`published.json` records the `target`**, and prior receipts are matched on version
  *and* target. A polygon rehearsal of 1.0.0 is not a prior publish of production's
  1.0.0; treating it as one would have hidden the identity the registry stamped on the
  real publish.
- **Every registry result carries `target`.** Nothing in a registry payload says which
  instance answered, so we say it — see `F16` for why that is not something we can
  verify against the server.
- The skill's §7 is rewritten as *rehearse, then promote*, with the two-instance table,
  and `references/CLI.md` now says the client has one URL and cannot tell you which
  instance it points at.

### Filed upstream while doing this

- **`S3`** (registry intake) — no endpoint reports `REGISTRY_MODE`, so a rehearsal
  cannot prove it is not on production. Tracked here as `F16`.
- **`S1` came back answered** the same day and is fixed in the registry's tree for
  0.13.0: the `would_publish` ceiling no longer applies offline, the 422 carries what it
  computed, and `/validate` gained `would_publish_module_level`. Not on PyPI, and
  production reports 0.12.0, so `F11` stays open here until the release lands.
- Measured while adopting: `module-marketplace.just-dna.life` is an alias of production,
  and `module-polygon.just-dna.life` resolves and terminates TLS but answers a bare 404 —
  DNS'd and fronted, not yet deployed. We ship the documented URL regardless, so it
  starts working the day it comes up.

## 0.4.0 — the essentials tier now runs the whole workflow (2026-08-11)

### The tier rule was wrong, not just one tool short of right

Dogfooding reported a narrow gap: the default tier could not verify a trait CURIE, because
`lookup_identifier` and `check_identifiers` were extended-only. `describe_table` would tell an
author that `trait_efo_id` takes an ontology CURIE and then offer nothing that checks one, so the
honest move was to leave the column blank and the tempting one was to write an id from memory —
which is precisely what rule 1 of the server instructions forbids.

Surveying before fixing turned up that the gap was a symptom. The stated rule — *essentials is
everything that only reads, plus the ClinVar draft* — did not describe the code **in either
direction**. `scaffold_module` and `compile_module` both write and were always essentials, while six
read-only tools sat behind the mode flag. And the worst case was not on anyone's list:
**`enrich_module` was extended-only while being step 6 of the order the server's own INSTRUCTIONS
teach**, so an agent following the default tier's instructions reached for a tool that was not there.

So the rule changed rather than the membership. **The tiers now split on cost, not usefulness:**

- **essentials** — everything whose work is bounded by what the caller named: one identifier, one
  paper, one spec directory. That is the whole taught workflow, scaffold through publish.
- **extended** — only what a *corpus* sizes (`paper_citations`, the PGx drafters, the bulk fact
  passes) or that reads back somebody else's compiled artifact (`reverse_module`,
  `registry_download`). Seven tools, down from sixteen.

Nine tools moved into essentials: `enrich_module`, `check_identifiers`, `lookup_identifier`,
`fetch_fulltext`, `lookup_open_access`, `authoring_reference`, `module_signature`, `verify_artifact`,
`registry_get_module`. Nothing left essentials, so this is additive for every existing caller —
`extended` still lists a strict superset.

Each landed beside its siblings rather than in a second closure: the schema dump and the integrity
pair in `authoring.py` (still network-free), the identifier and paper reads in `research.py` (still
writes nothing to a spec), and `enrich_module` in `passes.py` next to `draft_from_clinvar` — they are
the only two tools that fetch and then write into a spec directory, which is now what that module
means. `advanced.py` keeps the three that stayed.

### The guard is derived, not restated

`tests/test_modes_and_auth.py::test_the_taught_workflow_runs_in_the_default_tier` parses tool names
straight out of `server.INSTRUCTIONS` and asserts every one exists in essentials. It is written
against the text rather than a copy of it, so editing the taught order re-checks the tier for free.
Verified to bite: the parse yields `enrich_module`, which the pre-0.4.0 essentials tier did not have.
`test_extended_mode_is_a_superset` additionally pins `extended - essentials` to an exact set, so a
tool cannot drift between tiers unnoticed.

### Also

- **`authoring_reference` was unreachable from the tier that is told to call it.** `CLAUDE.md` §2 and
  the skill both instruct an agent to ask `describe_table` / `table_requirements` /
  `authoring_reference` rather than recall a schema fact — and the third was behind a mode flag. A
  rule pointing at a tool the default tier lacks is a rule that gets ignored.
- **README gained "Reloading after a change" and "Switching mode."** `/reload-plugins` does not
  re-exec a stdio MCP server — `/mcp` reconnect does — and stale servers accumulate. Mode has three
  launch paths that do not fall back to each other, and **editing `.env` cannot switch a
  plugin-launched server**: `plugin.json` exports `JMC_MODE` into the subprocess and `.env` loads with
  `override=False`, so the file is read and then ignored for that key, silently. Probed, not assumed.
- **The credential how-to moved into the skill.** It had been living in `docs/UX_TESTER.md`, where an
  author would never see it. `SKILL.md` §7 now also answers the account-*name* half: there is nothing
  to save, because `registry_whoami` reports it and re-registering with the same install-id returns
  the account that id owns while ignoring the `account` argument.

## 0.3.0 — registry onboarding (2026-08-11)

### A version bump touches two files, and the suite now knows it

`.claude-plugin/plugin.json` is JSON and cannot read `importlib.metadata`, so it is the one place
`CLAUDE.md` §2's "never hardcode a version string" cannot be obeyed — and it shipped this release
still declaring 0.2.0, caught in review rather than by anything automated. The drift is silent:
plugin loading is unaffected, so the only symptom is an installed plugin misreporting itself.

Fixed, and `tests/test_plugin_manifest.py` now fails on the mismatch, verified by reverting the
manifest and watching it fail rather than assuming it would. The same file pins the other
hand-maintained claims in the manifest: that its `mcpServers` command is still the console script
`[project.scripts]` installs and stays `${CLAUDE_PLUGIN_ROOT}`-relative, that the declared skills
directory holds the two skills the description promises, and that `marketplace.json` carries no
version of its own — one hand-maintained version string is the ceiling.

### You can get a registry account from inside the tool surface

Dogfooding hit the wall at step zero: every registry tool needed a token, and the only route to one
the surface named was `registry-client register`, a shell command in another package. The plugin
gated every registry action behind a credential nothing in it could mint, which made a one-command
install quietly cost a second toolchain. Recorded as `F12`/`F13`, both now in
[previous_issues.md](previous_issues.md).

Nothing upstream was owed. `RegistryClient.register` and `.namespace_available` are public in the
**published** 0.9.1; `POST /auth/register` needs no auth because it mints the token,
`allow_self_register` defaults true (no admin, no email, self-service by design), and
`generate_install_id()` grinds the proof-of-work locally in about a second. Two public APIs we had
never wrapped.

- **`registry_register(account, install_id=None, difficulty=None)`** — always on, in `auth.py`
  beside `authenticate`. The one registry write that cannot be token-gated, because it is what
  produces the token; `CLAUDE.md` §5 now names that exception and bounds it to a set of one. Not
  extended-only either — hiding the only route to a credential behind a mode flag is the same dead
  end in a different place. The minted token goes into the caller's own session slot, so registering
  leaves the session usable and no secret travels back through the transcript by hand.
- **Both secrets are returned, and the install-id carries its warning in the field description.** It
  is the account's only recovery path: re-registering it reissues a key for the *same* account,
  while registering again without it creates a different one and strands the first. `JMC_INSTALL_ID`
  was added so a later session can reuse it — a value we read and never write, because persisting a
  secret ourselves would widen the write surface. `account_taken` now says outright that retrying
  cannot help, since a key is only ever reissued to the install-id that created the account.
- **`registry_namespace_available(namespace)`** — essentials, read-only, no token. The pre-flight
  `registry_claim_namespace` demanded and did not offer. `valid` and `available` stay separate
  answers, which the live registry justifies immediately: it reports `test_modules` as
  `valid: false, available: true`. One boolean would have called an illegal name claimable.
- **The name rules are stated wherever they bite.** Accounts obey the *namespace* rule
  (`^[a-z0-9]+(-[a-z0-9]+)*$`), so `test_creator` was rejected before anything else could happen,
  while module names are the opposite (`^[a-z][a-z0-9_]*$`) — hence `my-ns/lactose_tolerance`. An
  illegal account name is refused locally, with the pattern quoted, before a round trip is spent.
  "Lowercase, hyphen-separated" was replaced everywhere it appeared: it read as a style preference
  rather than a hard reject.

Verified hermetically (name refused before any socket opens, offline ceiling holds for both tools,
install-id precedence and origin) and against the live registry read-only, including one real
failure path. Minting an account and claiming a namespace are left to the dogfooding side: a builder
who runs the irreversible probe has graded their own work.

### Upstream had answered every one of our findings, and our docs did not know

Checked `../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md` for the first time. The format
tree's inbox holds only *open* items — an answered `S<n>` moves out, prose byte-for-byte — so it has
been empty since 2026-08-11 with `S1`–`S18` all answered. Meanwhile every entry in our
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md) still said "open upstream". All
eight were answered; six are fixed **in tree for the unreleased 0.5.4**.

That distinction is now written down as three states rather than two — *accepted and filed* →
*fixed in tree* → *released* — because only the third lets a mitigation come out, and the middle one
is the easy mistake. PyPI's newest is compiler/enricher 0.5.3 and format 0.5.0, which is what we
install; confirmed by symbol rather than changelog (`hints.ATTESTATION_BEARING`,
`hints._report_ragged`, `Finding.line` are in the sibling checkout and absent from the installed
package — and `hints.py` lives in the **compiler**, not the enricher).

- `S11`, `S12`, `S15`, `S16`, `S17`, `S18` — accepted and fixed in tree. Every mitigation stays until
  0.5.4 ships. `S18` (our `F14`, filed the same day it was found) had both defects fixed the same
  day, which is the counter-example to `S14`'s lateness.
- `S10` — accepted, filed as upstream `RM46`; the granularity question is design work, not an
  unanswered report.
- `S14` — **settled, and half of it refused with a reason.** A `--no-ensembl` flag would assert
  something false, because the compiler has no branch that reaches the network at all; renaming a
  published parameter is major-only regardless. Our pin is therefore permanent rather than interim,
  and `F10` is closed. A refusal is an answer, and wording a guard as "until upstream fixes it" when
  upstream has declined is its own kind of stale.
- The registry's intake behaves the opposite way: no history file, and `S1` (our `F11`) genuinely
  still open. Absence of movement there means nothing has been answered.

`CLAUDE.md` §8 gained the history path, the id rule (`.claude/triage-state.sh --next` — ids are never
reused and the inbox being empty says nothing about what is taken; the next is `S19`), and the
instruction to re-read upstream's verdicts rather than trusting our own `Status:` lines, which go
stale silently because upstream answers in its own tree and nothing notifies us.

## 0.2.0 — literature discovery, drafting, and the fact passes (2026-08-11)

### Adopted just-dna-compiler / -enricher 0.5.3

- Upstream shipped `_check_positional_joinability`, which **partly closes S9/F5**: `validate` and
  `compile` now warn per positional table how many rows have no `chrom`+`start` **and how many of
  those the injected `resolution.csv` could place**. Verified reaching our surface unchanged on the
  one-row `pharm_variants` reproduction. That second count is the actionable half — it separates
  "never enriched" from "the coordinates exist and this tier does not apply them". The coordinates
  themselves are still not materialized; upstream defers that to RM43 because filling them breaks
  Principle 7 (`reverse_module` would return a derived coordinate as an authored one).
- `heteroplasmy.csv` joined the enricher's subject list upstream, so an rsid-authored heteroplasmy
  module now resolves at all.
- `just-dna-registry` 0.11.3 is **not adopted**: it is unpublished (PyPI has 0.9.1) and lives in the
  renamed `just-dna-marketplace` repo, so taking it would mean a local path dependency and the
  plugin's one-command install would stop working for anyone else.

### `registry_publish` now keeps the identity it is given

The registry is the authority on module identity — it stamps `namespace`, `owner`, `version` and
`canonical_id` on publish and overrides anything authored. We were returning that in a message and
dropping it, so nothing on disk recorded that a spec had ever been published, under what identity, or
against which digest. It now lands in a `published.json` receipt beside the spec, with the artifact
digest, the content signature and an ISO-8601 UTC timestamp. Not a cache and not a temp dir: a receipt
that does not survive the session is not a record. It cannot go into `module_spec.yaml` either —
`module:` is `extra="forbid"` and those exact keys are rejected there because the registry owns them
(upstream S1). An already-recorded version is never overwritten; a published version is immutable, so
a changed digest is reported for investigation rather than applied.

### Three documentation gaps filed upstream

Facts we had to establish by **experiment** rather than read, filed as `S15`–`S17`
in the format tree under their own "Documentation gaps" heading — nothing is
misbehaving, so they read as a separate category:

- **`PacingGate`'s concurrency contract is unstated, and it is not thread-safe.** We
  found this by demonstration (four threads overlap inside `wait()` on a frozen
  clock) and shipped a locked `ServiceGate` subclass. `ENRICHER.md` documents the
  class in nine places without a concurrency caveat, which matters because
  `LookupClients`' own docstring tells callers to hold and reuse one — exactly the
  arrangement that needs the answer.
- **Whether a spec directory may hold files the compiler does not know is
  unspecified.** It tolerates them; we tested, and `published.json` now relies on it.
- **`source` exists on only 4 of 16 row models, and all four are enricher-produced.**
  No authored table has one, so the `sources.csv` coverage check can only see sources
  a *pass* introduced — a hand-read source is structurally invisible, not merely easy
  to forget. Found by putting a `source` column on a `pharm_variants.csv` and getting
  `Extra inputs are not permitted`.

The rule behind them is now in `CLAUDE.md` §8: a fact you had to probe is a doc bug,
and the experiment is the argument for fixing it.

### Two upstream intakes, not one

The registry keeps its own `docs/CONSUMER_SUGGESTIONS.md` (created 2026-08-11, its own
`S<n>` series) at `../just-dna-marketplace/` — a stale directory name; the project and
package are `just-dna-registry`. Our
intake rule said one file served all four packages, which had stopped being true. The
`would_publish` note was written into the format tree by mistake and moved; a note in
the wrong file may as well not be filed.

### Docs swept for upstream gaps we had absorbed as our own

Three items were sitting in our roadmap or our skill as though the work were ours:

- **`would_publish`'s variant ceiling** (`422 too_many_variants` on a large module) had never been
  filed, and the idea book proposed building our own `check_publishable` to route around it. Filed as
  **S15**, tracked as **F11**, idea-book entry withdrawn — a parallel publishability check in a
  consumer is how two answers to one question start drifting.
- **RM7** (no `sources.csv` terms for any literature source) is upstream's granularity question. There
  was never work here for us: we report it and refuse to fill it. Removed from the roadmap, now **F8**
  in `just-dna-format-pending-fixes.md`.
- **F9** (`lookup_citation` cannot check identity) gained its upstream-blocked entry alongside the
  dogfooding one, since the mitigation is ours and the fix is not.

`docs/ROADMAP.md` now states the rule at the top: an item belongs there only if the work is ours.
**RM3** (signing) is deferred with its reason, and **RM4** was reclassified — it is a dogfooding probe,
not a deliverable, and now lives in `dogfooding.md`.

### New tools

- **`literature_search`** (essentials) — PubMed, Europe PMC, Semantic Scholar and the preprint
  index, merged. `pmids=[...]` reads titles back for ids you already have.
- **`lookup_open_access`**, **`fetch_fulltext`**, **`paper_citations`** (extended).
- **`draft_from_clinvar`** (essentials), **`draft_from_cpic`**, **`draft_from_clinpgx`** (extended)
  — closes F1/RM1, the hole in the middle of the taught workflow.
- **`enrich_facts`**, **`enrich_literature_pass`** (extended) — closes RM2.

### New skill

- `skills/find-evidence/` — search strategy, evidence appraisal, and the copyright rules that decide
  whether a module is publishable. `create-module` points at it from step 3 and stays the canonical
  authoring procedure.

### Why search is in the *essentials* tier

`CitationHint` carries no title, so `lookup_citation` can only prove a PMID **exists** — and PMIDs
are dense enough that a recalled one is usually a real record for a different paper. Both our skill
and the docstring told authors to "verify every PMID with `lookup_citation`", a rule the surface
could not enforce. Discovery is the missing half of an anti-fabrication promise the default tier had
already made. Filed upstream as `S12`; recorded as **F9**.

### Fixed

- `CitationLookup` was dropping `CitationHint.alterations` entirely, so the essentials tier was
  deleting the one refusal upstream hands it (the redundancy-bearing `doi`). Now carried, with
  `abstract_available`.
- `PacingGate` is not thread-safe and every tool here runs through `anyio.to_thread.run_sync`;
  `ServiceGate` adds the lock. One shared `LookupClients` per server replaces the per-call clients
  that were discarding rate-limit state.
- `lint_rows` documented refusals it never returns (F2/RM5) — narrowed to what it does return.
- `SKILL.md` and `DOMAIN.md` both claimed `draft --drug` refuses on multi-population pairs; upstream
  removed that in 0.5.1. RM1's rationale rested on the same removed behaviour.

### Owning sockets

`net.py` is now the only module permitted to open one, with retries on `tenacity` and upstream's own
`attempt_floor` stop so one deployment variable tunes our persistence and theirs together.
`JMC_LITERATURE_SOURCES` is a policy ceiling shaped like the offline one — a per-call `sources`
narrows it and can never widen it.

## Unreleased

### Adopted the house ruleset (2026-08-11)

- `AGENTS.md` is now a symlink to `CLAUDE.md`. They had been two different
  documents — a domain briefing and a code guide — so an agent's behaviour
  depended on which it happened to read.
- `CLAUDE.md` rewritten to the house template: must-reads in order, every
  prohibition inline, the `.claude`/`skills` assets named, and the authoring
  procedure left solely in the skill rather than restated beside it.
- Domain briefing moved to `docs/DOMAIN.md`.
- Adoption questionnaire answered and recorded: all four just-dna packages stay
  **hard dependencies** (no extras, no optional imports); this repo is an
  **application, not a published library** (no `__all__`, no re-export
  `__init__.py`); **no charter** — `just-dna-format`'s `CONSTITUTION.md` governs
  the format and ours would be a second charter about someone else's invariants.
- All inline imports hoisted to module top level.
- CLI now loads `.env` via `python-dotenv` (`override=False`) before reading
  configuration, so one `.env` serves both this server and the enricher it calls.
- Network transports print their URL before binding.
- `.env.example` → `.env.template`; removed the two placeholder values
  (`authors = "Your Name"`, `JMC_WORKSPACE=/path/to/your/modules`).
- Added the `assets/`, `data/{input,interim,output}` and `scripts/` layout with
  the ignore-all + allowlist rule on `data/`.

### The plugin (2026-08-11)

- Repo became a Claude Code plugin: `.claude-plugin/plugin.json` declares the MCP
  server inline using `${CLAUDE_PLUGIN_ROOT}` so it launches from the plugin
  directory rather than the user's cwd; `.claude-plugin/marketplace.json` makes
  `/plugin marketplace add ./` work.
- `skills/create-module/` — two independent authoring write-ups unified into one
  MCP-first skill, plus `references/{TABLES,SYMPTOMS,CLI}.md`. Removed the
  `.claude/skills/` copies they came from, which would otherwise have shadowed it
  with two same-named duplicates.
- Dropped 0.4-era history from the skill: this is a *new*-module creator, and that
  format version never reached production.

### The server (2026-08-11)

- Replaced the cake-demo FastMCP template with the just-dna authoring server.
  Package renamed `mcp_template` → `just_module_creator`; env prefix `CAKE_` →
  `JMC_`; Smithery removed (not applicable).
- `requires-python` raised to **≥3.13** — `just-dna-compiler` requires it. Ruff
  target, pyright version and the Docker base image moved with it.
- Added `just-dna-compiler`, `-format`, `-enricher`, `-registry`; bumped
  `fastmcp[tasks]` to ≥3.4.7.
- Tool tiers: **essentials** (the offline authoring loop plus the read-only
  lookups curation depends on), **extended** (enrichment as a background task,
  integrity, round-trip, registry reads), **gated** (registry writes, per-session
  token, never server-global).
- `JMC_OFFLINE` added as a hard network ceiling a per-call argument cannot
  override; `JMC_WORKSPACE` added as write containment for the HTTP transport.
- `compile_module` pins `resolve_with_ensembl=True`, so the wrapper cannot reach
  the branch that silently compiles every row with `chrom=None` and succeeds.

## Cross-repo

- **2026-08-11 — `just-dna-format`**: appended an independent corroboration to
  `docs/CONSUMER_SUGGESTIONS.md` **S9** (the non-SNP table families are
  materialized verbatim, so `resolution.csv` never reaches them). Reproduced here
  from the authoring surface with a `pharm_variants`-only module, twice — with and
  without a covering `resolution.csv` — which isolates the mechanism. Note left,
  not committed. No mitigation shipped on our side; the skill now tells authors to
  supply the rsID for those tables.
