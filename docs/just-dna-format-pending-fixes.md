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
and its next id comes from `.claude/triage-state.sh --next` in that repo (`S4` as
of 2026-08-11, after ours). Check there before filing — a second consumer hitting a known
one appends a corroboration rather than opening a new number. Write the note and
stop; never commit in that repo.

**Read the answered half too.** The format tree's inbox holds only *open* items; an
answered `S<n>` moves to `../just-dna-format/docs/CONSUMER_SUGGESTIONS_HISTORY.md`,
whose index table carries the verdict and where the fix landed. Its inbox has been
empty since 2026-08-11 — every one of `S1`–`S18` is answered — so an entry of ours
that has vanished from it was replied to, not dropped. The registry's intake gained
the same two-file split on 2026-08-11; its history file exists but is still empty,
because `S1` was answered in place and not yet archived. So there, for now, read the
`**Status —**` paragraphs in the inbox itself.

**Number a new one with `.claude/triage-state.sh --next`, never from what the inbox
shows** — it is empty, ids are never reused, and the next is `S19`.

**Three states, not two, and only the third releases a guard.** *accepted and
filed* (an upstream `RMn`, still open) → *fixed in tree* (the symbol exists in
`../just-dna-format`, not in what we install) → *released* (on PyPI, in our
lockfile). Every status line below names both halves, because "open upstream" said
neither and was wrong on every entry in this file until 2026-08-11.

**As of 2026-08-11, upstream's 0.5.4 is written but unreleased.** PyPI's newest is
compiler/enricher 0.5.3 and format 0.5.0. Confirm by symbol, not changelog:
`hints.ATTESTATION_BEARING`, `hints._report_ragged` and `Finding.line` are in
`../just-dna-format/compiler/src/just_dna_compiler/hints.py` and absent from the
installed `just_dna_compiler.hints`.

## Answered items that carry no `F<n>` here

`S11`, `S15`, `S16` and `S17` were filed without an `F<n>` because each shipped a
mitigation the same day and nothing was blocked — the three documentation gaps are
recorded in [CHANGELOG.md](CHANGELOG.md) under "Three documentation gaps filed
upstream". All four have since been answered, and all four fixes are **in tree for
the unreleased 0.5.4**, so none of the mitigations may come out yet:

| `S<n>` | Verdict | Landed in (unreleased) | Our mitigation, which stays |
|---|---|---|---|
| `S11` — `provenance_quote` / `provenance_regex` are redundancy-bearing and the map does not say so | accepted and fixed, **including the fifth refusal reason we argued for**: a quote is an *attestation*, not a spent comparison | `hints.ATTESTATION_BEARING`; `ENRICHER.md` | the refusal to extract a passage from a fetched document (`CLAUDE.md` §2) |
| `S15` — `PacingGate`'s concurrency contract is unstated and it is not safe to share | accepted and fixed — the injection API asks callers to share a gate, so the gate had to be safe to share | `net.PacingGate` slot reservation under a lock; `ENRICHER.md` | `ServiceGate`'s lock in `net.py` |
| `S16` — whether a spec directory may hold files the compiler does not know is unspecified | accepted — tolerance is now a stated, tested contract, **and probing it found the case where "ignored" is wrong**: a mistyped table name | `COMPILER.md` + `_check_misspelled_tables` | `published.json` relies on the tolerance we tested |
| `S17` — `source` exists only on enricher-produced rows, so an authored table cannot declare provenance | accepted and fixed both ways; our proposed table was right, and there is a fifth column — on `sources.csv` itself | `SCHEMAS.md` + `vocab.MISPLACED_COLUMN_REASONS` | none needed |

`S15`'s answer is the one to note when tempted to drop the lock: upstream fixed the
gate *because* the injection API asks callers to share one, which is exactly what
`ServiceGate` does. Two locks is harmless; none is a race.

---

## F5 — resolution never reaches the non-SNP table families

**Filed upstream:** **S9** (opened by just-dna-lite, 2026-08-11; corroborated by us
the same day), now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: answered — the legibility half shipped in 0.5.3 and we have it; the
coordinates themselves are open as upstream RM43, tracked in `RM_TOC.md`**

`compile_module` applies `resolution.csv` to the SNP core only. A module led by
`pharm_variants.csv`, `diplotypes.csv` or `pgs.csv` keeps exactly the coordinates
its author typed — so for an rsid-authored module, none.

Reproduced here twice with a one-row `pharm_variants`-only module: `chrom` and
`start` are null in the artifact both with and without a `resolution.csv` that
covers the variant, which rules out "no table was available" and leaves "this
family does not consult it". The same run demonstrably *read* the file — it
warned that VRS coverage in `resolution.csv` was 0/1 — while not applying it.

### What 0.5.3 shipped, and why it is the right half first

`_check_positional_joinability` now warns, per positional table, in both
`validate` and `compile`. Verified reaching our surface unchanged on the same
one-row reproduction:

> `pharm_variants.csv: 1 of 1 row(s) have no chrom+start, so this table joins by
> rsID only — a VCF whose ID column is empty matches none of them.
> **resolution.csv can place 1 of them**, and the compiler applies that table to
> variants.csv only.`

That second count is the actionable half, and it is exactly the distinction our
corroboration argued the run already held both facts to make: it separates *this
module was never enriched* from *the coordinates exist and this tier does not
apply them here*. An author cannot otherwise tell those apart, and they call for
opposite actions.

Deliberately a warning in both modes and never a `strict` error, which we agree
with: rsid-only identity is legal by these models' own rule, so escalating would
have the format tighten a field it left open — and the remedy is a compiler
change, not an authored edit. Refusing would make a correct module uncompilable
for something its author cannot clear.

**What is still open.** The coordinates are not materialized. Upstream's reason
is worth recording because it is not a scheduling excuse: filling them breaks
Principle 7, since `reverse_module` rebuilds the CSV from the parquet and a
filled coordinate returns as an *authored* one. `VariantRow.authored_ident`
exists to prevent exactly that and no 0.4-family model has an equivalent, so the
fix needs a new column on an existing parquet — 0.6 work, tracked upstream as
**RM43** with two smaller constraints alongside (`PharmVariantRow` has no `alts`
column, and `variant_key` is a property on these models so it is materialized in
no PGx parquet).

**Our mitigation is now redundant with upstream's warning** but stays, because it
tells an author what to do rather than what happened:
`skills/create-module/SKILL.md` says to supply the rsID for these tables and that
a consumer joins on `rsid` + `genotype`. We still ship no code workaround —
filling the coordinates ourselves would author a value the compiler did not
derive, which is the redundancy-bearing mistake the rest of this repo exists to
prevent.

**Closes when** RM43 lands.

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
**Status: accepted and FIXED IN TREE for the unreleased 0.5.4 — not in the 0.5.3 we
install, so our mitigation stays.**

Upstream added `CitationHint.title` / `journal` / `year` / `first_author`, plus
`literature.bibliographic` and `hint citation --json`, agreeing that existence is
not identity and that `esummary` already carried the answer. When 0.5.4 reaches
PyPI, `lookup_citation` can report the title itself and this closes — until then
`CitationHint` in our environment still has no title and the docstring's
existence-not-identity wording is still the truth.

`CitationHint` carries `pmid_exists`, `doi`, `registry_doi`, `pmcid`,
`open_access`, `abstract_available` — and no **title**, journal or year. PMIDs are
densely allocated across roughly 1–40,000,000, so a recalled or hallucinated
8-digit number is almost always a real record *for a different paper*, and
`lookup_citation` answers `pmid_exists=true` for it. Fabrication is a failure of
*identity*; existence is the only question that surface can put.

`esummary` already returns `title`, `fulljournalname` and `pubdate` in the payload
`_check_pmid` parses — `literature._identifiers` reads that same record for the DOI
and PMCID and drops the rest — so this is surfacing fields upstream already has.

**Our mitigation, which is why this is not blocking:** `literature_search`
(essentials) returns titles, and `literature_search(pmids=[...])` reads them back
for ids the caller already holds. Both our docs now say to take every PMID from a
search result rather than from memory, and `lookup_citation`'s own docstring says
outright that it answers existence and not identity. Recorded as **F9** in
[dogfooding.md](dogfooding.md) as well, because the mitigation is ours and the fix
is not.

**Closes when** `CitationHint` carries a title.

---

## F10 — `resolve_with_ensembl=False` is the master switch for all resolution, and its name says otherwise

**Filed upstream:** **S14**, now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: SETTLED 2026-08-11. The warning had already shipped in 0.5.2 from another
report; the rename is REFUSED with a reason. Our pin is permanent, not interim.**

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
server-side) · **Status: ANSWERED and accepted the same day, fixed in the registry's
tree for 0.13.0, and NOT released — PyPI's newest is 0.12.0 and the live production
instance reports 0.12.0. So nothing has changed for our callers yet.**

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

**What is ours now.** We wrap neither `validate` nor `check` — the whole 0.10–0.13
client surface is unwrapped, tracked as `RM8`. When we do, `would_publish_module_level`
is the field to read, and it must be reported as "nothing module-level blocks this"
rather than "this will publish", exactly as upstream named it.

**Closes when** registry 0.13.0 is on PyPI and in our lockfile. The upstream half is
done; verify by symbol against the *installed* package, not the sibling checkout.

## F14 — a ragged CSV row is misdiagnosed by `lint_rows`, on the wrong column and the wrong line

**Found:** 2026-08-11, first binning probe (HTT CAG repeat bins) ·
**Filed upstream as `S18`**, now in `CONSUMER_SUGGESTIONS_HISTORY.md` ·
**Status: both defects accepted and FIXED IN TREE the same day, for the unreleased
0.5.4. Absent from the 0.5.3 we install, so the trap is still live for our callers.**

`hints._report_ragged` names a ragged row *before* the error it causes, and
`Finding` gained a `line` field carrying the file line an editor shows — so both
halves of this note landed, including the one about `row` and `line N` disagreeing
over the same CSV. Filing it the moment it was found is what made that possible;
this is the counter-example to `S14`'s lateness.

**What this means for us now.** Nothing to build: `lint_rows` is a pass-through and
`to_findings` will carry `line` across the boundary the day it exists. The line in
the authoring skill about quoting free-text cells stays useful regardless — an
author should quote them anyway — but it stops being a workaround for a silent
mis-parse once 0.5.4 lands. Re-check `Finding.line` on the installed package before
rewording anything.

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
declared boundary in `RegistryClient`) · **Status: open, filed the day it was
raised.** Like `F11`, this sits in the intake that has **no history file**, so
absence of movement there means unanswered, not answered.

We call eight `RegistryClient` methods — `register`, `whoami`, `claim_namespace`,
`publish`, `list_modules`, `get_module`, `namespace_available`, `download` — out of
a 35-endpoint API. Nothing enumerates that subset as a contract, and neither
`API-REFERENCE.md` nor `CLIENT.md` is stamped with the versions it describes. So
each release is read in full to establish that our surface did not move, which for
0.12.0 (deployment modes, polygon instance, operator purge) it did not.

**What is ours, and stays:** the defensive projection in
`tools/research.py::_module_card` — `pick("version", "latest_version")`, tolerating
an `identity` sub-object `ModuleCard` does not document — and `registry_get_module`
passing its payload through untyped rather than modelling it. Both look like
over-caution against a schema upstream specifies exactly. They are not: without a
version stamp on the reference, we could not confirm the documented schema applied
to the client we run. Tightening either one now would be hardcoding a payload shape
on a guess, which is the same bet written into our repo.

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

**Closes when** the client surface is enumerated as its own contract — a document, a
declared boundary in the client, or per-release "client surface: unchanged/changed"
— and the reference docs say which versions they are normative for.

## F16 — nothing over the wire reports a registry instance's mode, so "am I on the polygon?" is unanswerable

**Found:** 2026-08-11, adopting the registry's test/prod split ·
**Filed upstream:** **S3** in `../just-dna-marketplace/docs/CONSUMER_SUGGESTIONS.md`
· **Status: filed the day it was found; unanswered as of writing.**

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

**What is ours, and stays ours:** `targets.py` resolves a URL per target from our own
configuration and records the target in the `published.json` receipt, so our record of
which instance answered is at least internally consistent. We deliberately do **not**
probe `openapi.json` to verify a host's mode: that would make this repo a second source
of truth for something only the server knows, and it would be a guess wearing a check's
clothing — the exact shape `F11` was withdrawn for.

**Closes when** an instance reports its mode over the API, at which point the target
argument can be *verified* rather than merely declared.
