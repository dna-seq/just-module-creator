---
name: module-start
description: >-
  Triage the sources somebody handed you and turn them into a spec directory that declares what it
  is. Covers the three questions that close off wrong turns later, checking that the copy you were
  handed is still the current one, the six checks that survive a summary, asking once about the
  contact email, and what to declare at birth — the module kind, `weighting:`, `authorship:`, the
  licence and the `--use` position.
  Triggers: "start a module", "new module", "scaffold", "I have a zip", "triage these sources",
  "which tables do I need", "module_spec.yaml", "somebody sent me a PDF", "is this claim real",
  "declare the licence", "what goes in the spec".
---

# Stage 0–1 — where a module comes from, and the spec that declares it

**Lifecycle stage:** 0 (origin) and 1 (scaffold). Every real session starts here, including the ones
that think they are starting at stage 3.

This stage is cheap and it is where the expensive mistakes are made. Nothing downstream re-asks any
of these questions: a module that declared no `weighting:` never gets asked again, an rsID that was
never checked is authored into 400 rows, and a licence position taken here is the only one the
compile gate will ever read.

## The three questions, before anything is created

Each one closes off a class of wrong turn.

1. **What is each row's subject?** A variant? A diplotype pair? A measured quantity? That picks the
   lead table, and **a module carries only the kinds it uses** — never an empty `variants.csv` to keep
   another table company. → [`module-tables`](../module-tables/GUIDE.md), or `list_tables`.
2. **Are the coordinates GRCh38, and are they VCF positions?** Two separate questions, and the second
   has bitten harder. `start` is the **1-based VCF position** — the number Ensembl, dbSNP, ClinVar and
   gnomAD all show you. Paste it; never convert it. Off GRCh38 the module falls back to a
   **build-relative** key that will not join against gnomAD, ClinVar or ClinGen. [`module-curate`](../module-curate/GUIDE.md) has
   the full trap.
3. **What is the source, and may you use it this way?** Every PGx upstream (ClinPGx, CPIC, PharmVar)
   is CC BY-SA **plus a no-sale clause**, so none is sellable — do not read a bare "CC BY-SA" as
   permission. The answer becomes `--use` on every command that copies rows out of a source, and it
   lands in `licensing.csv`, which is the only file the compile gate reads.

**Prefer the rsID to a coordinate wherever the source gives you both.** An rsid-only row cannot carry
a coordinate mistake, and the resolution table [`module-enrich`](../module-enrich/GUIDE.md) produces is then the independent second
value the cross-check needs. Author coordinates only when you have a reason: no rsID exists (roughly
10% of ClinVar pathogenic variants), one rsID names several alleles and the row must say which, or the
module is not GRCh38.

## Where a module comes from — four honest starts

| Start | How | Good for |
|---|---|---|
| **A gap in the catalog** | `registry_search(target="prod", gene=…)` / `registry_search(target="prod", query=…)` — `target` is required, so production is something you state | knowing the work is wanted before doing it |
| **A source that publishes the table** | `draft_from_clinvar` for a gene panel; `draft_from_cpic` / `draft_from_clinpgx` for drug response | the fastest route to real rows — then curate what it stubs |
| **A paper the author actually read** | `literature_search` to pin the PMID and read the title back | one well-grounded finding, which is a legitimate module |
| **Something the author was told** — a video, a podcast, a blog, an AI summary | **triage first**, below | by far the most common in practice, and the only one that starts by *removing* claims |

If the author has no idea at all, the catalog gap is the best prompt: search a gene or trait they care
about, and either nothing exists (a module to write) or something does (a module to read, which
teaches more than any template — [`module-101`](../module-101/GUIDE.md) lists the sixteen worked examples).

**Read one before you start.** Sixteen modules ship in `../just-dna-format/reference_examples/`, each
with a README saying what it demonstrates and often what it *broke*. Open the one shaped like what you
are building; [`module-101`](../module-101/GUIDE.md) has the table.

## The author brings the theme; the rest is yours

**This plugin is an AI co-author and a module written entirely by an agent is the normal first
artifact, not a compromise.** The person you are working with may never have seen a VCF. They bring
the *theme* and the *sources* — a trait they care about, three PDFs, a podcast. The triage, the rows,
the conclusions and the located passages are yours.

**Do not ask them for what only a reviewer can give.** An author who cannot read a genetics paper
cannot tell you whether your `state` is right, and asking sends them away to find someone who can —
which is a later pass, performed by a different person.

**Correct the DNA-reading misconception early and unprompted.** A beginner's working model is usually
*"point this at my DNA file and it tells me about me"*, and every later step reads as nonsense against
it. One sentence up front saves the whole conversation: **there are two jobs — writing the rulebook and
reading a DNA file against it — and this only does the first.** [`module-101`](../module-101/GUIDE.md) has the rest of the
beginner vocabulary.

## First: is the copy you were handed still the current one?

**Do this before authoring a single row from a PDF, and before the triage below.** A file on disk has
a date; the literature does not stop moving because somebody saved it. Two drifts, both of which change
what you should cite:

- **A preprint may since have been peer reviewed.** Cite the journal version: it is the better trust
  level, and review changes things — numbers corrected, panels dropped, conclusions softened or
  reversed. A module grounded on the preprint's figures can disagree with the published paper while
  looking perfectly checked.
- **A preprint server version is not the paper, it is *a* paper.** You may be holding arXiv `v1` while
  `v5` is current. Same trap, one server earlier.

```
literature_search(query="<the exact title>", year_from=<the PDF's year>)
literature_search(pmids=["<the id you have>"])          # read the venue and the title back
```

**A preprint record and a journal record are two records with two ids**, so the check is *"does a
second record exist for this title"*, not *"is my id valid"*. If one does, re-read the claims you took
from the old copy **before** switching the `pmid` — the point is not to relabel the citation, it is
that the content may have moved under it.

**Read `sources` before concluding it is current.** Semantic Scholar links a preprint to its published
version better than anything else here, and it rate-limits often; a run reporting `results: null` has
not answered the question. Two of four sources 429'ing means **unchecked**, and "no journal version
found" is then a statement about your search rather than about the world. Say which you mean.

**A module built on a preprint carries this as a standing obligation.** When the journal version lands,
the citation and possibly the rows change — a version bump with a changelog line. `module-revise` owns
that pass.

## Triaging a source you were handed

A summary is not evidence — it is somebody's reading of evidence, and if a machine wrote it the
citations may be generated rather than recalled. **Assume nothing, check each claim, and expect most of
them to fail.** A real run of this procedure turned **seven** offered rsIDs into **one** authored row.

1. **Does every rsID resolve?** `lookup_variant(rsid=…)`. Read the finding, not just `loci`: an
   unreachable Ensembl reports *"could not be reached, so its answer is unchecked rather than empty"*
   at `warning`, while a genuine absence stays `info`. **Re-run on the warning** — it says nothing
   about whether the id is real. A bare `loci: []` with no such warning is a real negative, and that is
   the fingerprint of a fabricated id.
2. **Does the rsID sit on the same chromosome as the gene the source names?** `check_identifiers`
   answers it: read `gene_locus_conflicts`. **Read it even when `stale` is empty** — the symbol is
   approved and the number resolves, so only the *relationship* is false and no per-identifier check
   sees it. If `gene_locus_check_skipped` is non-null the comparison never ran, which is not a pass.
3. **Does the pairing appear in any paper?** `literature_search(rsid=…, gene=…)`. Zero results from
   sources that *answered* is strong evidence; read `sources` first, because a source that could not
   answer reports `results: null` and a miss is not an absence.
4. **Does the cited paper say what the source claims?** Read the **title** back — the only thing that
   settles identity. Existence is no guard: a fabricated PMID usually exists, for another paper.
5. **Are two survivors the same signal?** Variants in strong LD tag one finding; two rows would
   double-count it in a score. Keep the one with the mechanism behind it.
6. **Does anything state the direction?** If no located paper says *which* allele carries the risk,
   drop the row. A guessed `direction` is a coin flip that will look exactly as authoritative as a real
   one.

**The tell for a generated claim is a real gene name beside an invented rsID.** Both halves survive
their own checks — the symbol is approved, the number resolves — and only the relationship is false.
That is why step 2 finds what steps 1 and 3 miss.

**Most claims not surviving is the result, not a failure**, and it is worth saying to the author in
those words. Numbers a summary offers (effect sizes, "7×", kilograms per allele) are the least reliable
part and must be re-read from the paper or left out: in the run above, one such figure was the paper's
*rescue* factor reported as its deficit. A module of one checked row is worth more than seven confident
ones.

**Do not ask which schema era a handed bundle came from.** The operation is `to_current_state` and it
is idempotent: bring it up to what a good module needs today and stop. Whether it was authored against
0.1, 0.3 or last week is an input property, not a thing to classify or preserve — uplift mechanics are
the format's and the registry's, already handled. Read the deprecated spelling so you write back to the
file you read, and leave the history to them. **A discrepancy is either something to fix now or
something to record honestly**, and that judgement needs no era.

**And do not trust a bundle's own README.** One asserted allele validation performed over coordinates
that were shifted by one base. A bundle's README is a claim, not a receipt; [`module-101`](../module-101/GUIDE.md) has the worked
case of five externally authored modules, four of them shifted.

**26 of 27 real submitted bundles carry `MODULE.md`, not `README.md`.** A local compile of such a
bundle yields `manifest.readme: null` in silence — `_collect_readme` does not recognise the name.
**Rename it on intake.** Do not route around it by pointing a config at `MODULE.md`: that mints a
manifest attesting a filename the registry's recognised-file list does not contain.

## Ask about the email — once, at the top

One question, once, and it is about somebody's personal data, so it is not yours to assume.

**"May I use your email address for the lookups?"** NCBI's polite pool and Unpaywall both **meter and
contact per address**:

| | their traffic | their rate limit | a problem reaches |
|---|---|---|---|
| configured | theirs | theirs | them |
| not configured | pooled with every other unconfigured install | shared | the project's inbox |

Nothing breaks without an answer — which is exactly why you ask *once*, take no for an answer, and
never raise it again.

**Only ask when nothing is configured.** Check `JMC_USER_EMAIL` first, then the enricher's
`JUST_DNA_CONTACT_EMAIL`. No tool reports the resolved contact or which step supplied it, so read
`.env` directly. If either is set, say nothing at all.

**If they agree, write it into `.env` as `JMC_USER_EMAIL`.** A value that lives only in the session
dies with it. Never overwrite an address already there, and never put one anywhere else — `.env` is
gitignored and every other file in the tree is not.

**Never invent an address, and never *infer* one.** Not from `git config user.email`, not off a commit,
not from the registry account. An address the author did not offer is personal data volunteered on
their behalf, and a wrong guess misattributes traffic to a real stranger. *"I'd rather not"* is a
complete answer and the default handles it.

## Create the spec

Check first whether the module already exists:

```
registry_search(target="prod", query="lactose")   /   registry_search(target="prod", gene="MCM6")
```

Then scaffold. It never overwrites, so re-run it with different `kinds` to add a table later:

```
scaffold_module(spec_dir="spec", name="my_module", kinds=["variants.csv", "studies.csv"])
```

`name` is lowercase alphanumeric with underscores; `my-module` is rejected.

Learning a table you have not authored before — **ask, never recall**:

```
table_requirements("heteroplasmy.csv")   # required / defaulted / optional, and the one-of rules
describe_table("heteroplasmy.csv")       # every column, its vocabulary, its pick-list
get_template("heteroplasmy.csv", stub=True, rows=3)
```

**`required` is not the whole story — there are three categories and the middle one is invisible to a
schema dump.** A **defaulted** column (`measure_kind`, `unresolved`) is not required *and* must not be
left empty: an empty cell arrives as `None` rather than as the field's default and fails on type with
*"Input should be a valid string [input_value=None]"* — on a column nobody told you to fill.
`table_requirements` reports those under `defaulted`, and it also reports the one-of rules (the "rsid
**or** chrom+start" kind) that no per-field flag can express.

**A generated stub cannot compile until you replace it.** `<<REPLACE>>` is rejected before type
coercion, so an unreplaced placeholder in an `int` column reads as *"unreplaced template placeholder in
column start"* rather than as a number-parsing error. That is the design: a half-filled table fails
loudly on exactly the rows still to do.

## What to declare at birth, and why here

`module:` is `extra="forbid"` — a typo like `colour:` is a hard error, not a silent drop. Do not write
`namespace`, `owner` or `canonical_id`: the registry stamps those.

**Quote the version.** An unquoted or digitless `version:` becomes `0.0.0`, which is a real version and
a real publish.

### `weighting:` — invisible by construction, so write it now

`scaffold_module` omits every optional block, and `describe_table("module_spec.yaml")` refuses without
pointing anywhere useful. **Two real authoring sessions concluded the field did not exist.** It is where
you say what a `weight` means — the scale, the direction convention, whether the module authors weights
at all. A negative declaration is a good declaration: one reference example says *"scale: none — this
module authors no weights"* and points the reader at `gwas_effects.parquet` instead. [`module-weights`](../module-weights/GUIDE.md)
owns what goes in it.

`weighting:` sits **outside** `content_signature`, so two modules differing only in that block are
`409 duplicate_content` at the registry. Declaring it is free; discovering it late is not.

### `authorship:` — the only place a human curator's effort is recorded

Two axes, and there is **no `ai-writer` / `ai-curator` value** — it is the cross-product:

- `role` — **closed**: `created` | `edited` | `audited` | `reviewed`.
- `kind` — **open, seeded**: the human ladder `human` → `human_expert` → `human_certified`, or `ai`
  plus a scale tag `agent` / `team` / `swarm`.
- `at` — ISO-8601, optional and worth writing.

```yaml
authorship:
  - who: ai-module-creator
    role: created
    kind: [ai, agent]
    at: '2026-08-20'
```

**A joint contribution is two entries, each with its own `kind`** — the format refuses a lossy `hybrid`
tag on purpose. A later pass *appends*; it never rewrites an earlier line, because who wrote what is
exactly what a reviewer routes on. **Declare `[ai, agent]` honestly when an agent wrote it**: a module
that hides its authorship is the one failure mode no later reviewer can detect from the artifact.

`authorship` sits outside `artifact.digest`, so adding a reviewer moves no content identity — which is
what lets a pure review be a real version bump. `module-revise` owns that; [`module-close`](../module-close/GUIDE.md) owns the
closure it interacts with.

### The licence, and the `--use` position

Any module built from a licence-bearing source needs a row in `licensing.csv` recording the terms.
Passes that read such a source write it for you; **a source you read by hand is invisible to every
check, so write the row yourself.**

- **`licensing.csv` is a table kind**, so `describe_table` and `get_template` answer for it. Never
  reconstruct its columns from the filename: `share_alike` / `commercial_use` / `redistribution` are
  three independent axes where an empty cell means **unknown**, never *permitted*.
- **`license:` in the YAML must not contradict `licensing.csv`.** A ClinVar module declaring `CC0-1.0`
  warns, because the source row says `public-domain` — the same grant, but the check compares
  **spellings**. Match the source's spelling.
- **It must cover every source your fact tables cite, including PubMed if you carry studies.** A
  literature row is not reported as unused when `studies.csv` has rows: `studies.csv` has no `source`
  column by design, so nothing can corroborate the service you read the record through, and the row is
  the only record of its terms.
- **`--use` accepts `non-commercial`; the `declared_use` *column* takes `non_commercial`** with an
  underscore. The flag normalises; a cell you type by hand does not.
- **The file was `sources.csv` before format 0.6 and both spellings still read.** Create only
  `licensing.csv`; write to whichever one an inherited module already carries; **never let a module
  carry both** — that is an error naming both paths rather than a merge.

**A duplicate `(source, layer)` row is refused** — `licensing.csv: duplicate row for key
('<source>', '<layer>')`, from `validate` and `compile` both, since compiler 0.6.6. One source at two
layers is fine; the same pair twice is two claims about one thing, and where they disagree on
`commercial_use` picking the survivor is yours to do rather than a merge's.

## What needs a pilot, and what you may simply fix

**This layer writes.** The split is not between you and a tool, it is between a move with no judgement
in it and a move that commits somebody to a position.

**Apply it and say nothing** — evident, mechanical, and nothing downstream re-checks it against a
source:

- `MODULE.md` → `README.md` on intake, and any other recognised file under a near-miss name.
- The deprecated `sources.csv` spelling: **write back to the file you read**, and never create the
  second one beside it.
- A `defaulted` column the scaffold left empty, a `version:` left unquoted, an `icon_set` typo.
- Bringing a handed bundle to the current release. There is no era axis; `to_current_state` is
  idempotent and the input's schema generation is not a thing to preserve.

**Surface it, and let a pilot settle it:**

- **Whether the source may be used this way.** `--use` asserts a licence position. Re-running with a
  different one to get past a `skipped=true` draft is fabricating one, and the position is the one
  thing the compile gate will ever read.
- **Which tables the module needs.** No tool infers a module's shape from a bundle, and adding a kind
  "to look complete" is how empty tables ship.
- **Whether a triaged claim survives.** The six checks narrow the field; the last call is a judgement.
  Dropping a row for want of a stated direction is a result, not a gap.
- **The contact email.** Never inferred, never invented — it is somebody's personal data.
- **The module's own identity** — `title`, `description`, `report_title`. A `<<REPLACE>>` here is a
  question, not a chore. `description` becomes the catalog card's subtitle and is rendered whole, so it
  wants one short sentence rather than a paragraph — [`module-tables`](../module-tables/GUIDE.md) → `references/module_spec.md` has
  the band and what overrunning it costs once the module is published.

**When you cannot tell which side a case is on, surface it.** Over-surfacing is recoverable; a silent
wrong write is not.

## What this stage cannot do

**Nothing records where a module came from.** The origin picks the shape of every later pass — a
source-drafted module inherits a release cadence, a paper-drafted one inherits the literature's — and
no field anywhere holds it. **Write it in the README**, which is the only place it will survive.

**Nothing validates a handed bundle's claims.** `validate_module` checks shape, not truth. Four
externally authored modules passed every offline gate with every coordinate one base low.

**No tool triages sources for you.** The six checks above are calls you make one at a time.

**Nothing tells you a module is worth writing.** `registry_search` tells you whether one exists.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action. The four you
will meet at this stage:

- *"unreplaced template placeholder `<<REPLACE>>`"* — the scaffold or a drafted partial row still needs
  a human. It blocks **every** loader, `enrich` included, deliberately.
- *"Input should be a valid string [input_value=None]"* on a column nobody told you to fill — a
  *defaulted* column left empty.
- *"module_spec.yaml is not valid YAML"* with a line and column — usually a tab, an unclosed bracket, or
  an unquoted value containing `:`.
- *"sources.csv is the deprecated spelling of this table"* — rename the CSV, and do **not** finish the
  rename into `sources.parquet` or `manifest.sources`, which keep their names for the whole 0.x tail.

## Where to go next

| You need | Load |
|---|---|
| which table a finding belongs in, and its columns | [`module-tables`](../module-tables/GUIDE.md) |
| the spec file block by block | [`module-tables`](../module-tables/GUIDE.md) → `references/module_spec.md` |
| drafting rows from a source that publishes them | [`module-draft`](../module-draft/GUIDE.md) |
| writing the cells only an author decides | [`module-curate`](../module-curate/GUIDE.md) |
| what a `weight` means and what to declare | [`module-weights`](../module-weights/GUIDE.md) |
| finding and verifying the literature | `find-evidence` |
| getting the supplementary table a GWAS paper's numbers live in | [`find-evidence`](../find-evidence/references/SUPPLEMENTARY.md) |
| the module already exists | `module-revise` |
