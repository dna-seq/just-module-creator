# Dogfooding — open findings

Open quirks, bugs and UX gaps found by **using the shipped surface for real
work**, not by testing it. Read before touching the tool surface.

Findings carry stable `F#` IDs and **move** between files rather than being
duplicated: resolved here → [previous_issues.md](previous_issues.md); blocked on
an upstream change → [just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).
One legitimately appears in two files when we have mitigated it and upstream
still owes the fix.

Layer 1 (the suite) proves the code does what it was told. This asks whether it
is usable, and what is missing.

---

## F6 — two of five literature sources refuse this host, and the tool is right to say so

**Found:** 2026-08-11, capturing fixtures · **Severity:** medium ·
**Status:** open · **Roadmap:** [RM6](ROADMAP.md#rm6--semantic-scholar-and-arxiv-are-unreachable-from-this-host-so-two-parsers-are-untested)

Semantic Scholar and arXiv both answer HTTP 429 from this machine regardless of
user-agent, arXiv on a *first* request with no prior traffic — so it is an IP
block, not our pacing. Confirmed with plain `curl` outside the client.

Reported here rather than routed around because it is the best available
evidence that the tri-state design earns its keep. A live `literature_search`
returns `results=null` and `rate_limited=true` for those two, plus a warning that
their part of the literature is **unchecked, not empty** — while PubMed and
Europe PMC answer normally. Had the model used `0`, the same call would have
read as "no preprints exist on this subject", which is a conclusion an author
would act on.

The cost is real: `parse_semantic_scholar` and `parse_arxiv` have no committed
fixture and therefore no test.

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

## F8 — the literature sources have no recordable licence terms

**Status:** mitigated here, open upstream. Full entry in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md); filed as
`S10`.

Listed here too because the mitigation is reporting only: each literature result
carries a `SourceLicenseNote` naming the row the author owes, and a module still
compiles green with the terms unrecorded because it is a warning.

It briefly had a roadmap item (`RM7`), which was wrong — there is no work here for
us to do. Removed on 2026-08-11 during a sweep for upstream gaps this repo had
absorbed as its own.

## F9 — `lookup_citation` cannot detect a fabricated PMID, and our docs said it could

**Found:** 2026-08-11, designing the search tool · **Severity:** high ·
**Status:** mitigated here, open upstream (`S12`)

`CitationHint` carries `pmid_exists`, `doi`, `pmcid`, `open_access` — and no
title, journal or year. PMIDs are densely allocated across roughly 1–40,000,000,
so a recalled 8-digit number is almost always a real record for a **different**
paper, and `lookup_citation` answers `pmid_exists: true` for it.

Both our skill and the tool docstring said "never invent a PMID — verify each one
with `lookup_citation`", which is a rule the surface could not enforce.
Fabrication is a failure of *identity*; that call only answers existence.

This is the finding that put `literature_search` in the **essentials** tier
rather than extended: discovery is the missing half of an anti-fabrication
promise the default surface had already made. `literature_search(pmids=[...])`
reads titles back, and both docs now say to take every PMID from a search result
rather than from memory.


---

## Probes not yet run

Recorded so the gaps in *this* file are visible too, per the completeness rule.

- **Author a real module end to end and publish it.** Everything up to
  `compile_module` has been exercised on a real spec; `enrich_module` and
  `registry_publish` have not ([RM4](ROADMAP.md)). This probe would also hit F1
  from the inside rather than by inspection.
- **A binning module — partly run, 2026-08-11.** Probed at the `lint_rows` level
  with real HTT CAG repeat bins (≤26 normal / 27–35 intermediate / 36–39 reduced
  penetrance / ≥40 full penetrance, plus the `unresolved` sentinel). The bounds
  handling held up better than expected: the coverage check reports a genuine hole
  (`no bin covers (26.0, 36.0)` when a bin is missing) and correctly does **not**
  invent one between adjacent integer bins 26 and 27, and the missing-sentinel
  warning states the contract outright — a consumer with no measurement selects the
  sentinel, never the lowest bin. What it did find is [F14](just-dna-format-pending-fixes.md)
  (`S18` upstream): a ragged row is silently shifted and misdiagnosed. **Still not
  run:** scaffold → validate → compile on a binning module, and `heteroplasmy.csv`,
  the other endpoint convention, where bins genuinely do share a bound on a
  continuous measure.
- **`enrich_module` and `registry_publish`, end to end against the live services.**
  Was tracked as a roadmap item until 2026-08-11; it is a probe, not a
  deliverable. The offline ceiling keeps the suite hermetic, so neither can be a
  normal test — what fits is a marked, opt-in integration run alongside authoring
  a small real module all the way through. `registry_publish` needs a token, a
  namespace and a module we are willing to publish immutably; the new
  `published.json` receipt is what makes the result inspectable afterwards.
  **Unblocked 2026-08-11** — `registry_register` now mints the token from inside the
  surface ([F12](previous_issues.md)), and `registry_namespace_available` answers the
  namespace question without spending the irreversible claim to ask it
  ([F13](previous_issues.md)). Both are wrapped and covered offline; **neither has
  been driven against the live service to the point of creating anything**, which is
  precisely what this probe is for.

  **Unblocked differently on 2026-08-11, and this is the bigger change:** the registry
  now runs a *polygon* (`REGISTRY_MODE=test`), where a publish is a rehearsal that
  `registry_delete_version` frees again — version number and content claim both. The
  reason this probe kept being deferred was that it demanded "a module we are willing to
  publish immutably"; on the polygon it demands nothing of the sort. Run it there, with
  `target="test"`, as many times as it takes. Two caveats to carry into it: the polygon
  scopes `duplicate_content` to the publishing account, so a rehearsal cannot prove a
  cross-account duplicate would be refused; and as of filing the polygon host answers a
  bare 404 (DNS'd, app not deployed), so the probe waits on that deployment rather than
  on us.
- **A module with two of something the examples show one of.** The worked example
  throughout is a single-gene, single-rsID module. A paralogous rsID mapping to
  several loci, or one gene carrying two variants with different thresholds, is
  where a key that works for one instance stops working.

## F18 — "a green pre-flight should mean a green compile" is false before `resolution.csv` exists

**Found:** 2026-08-11, authoring `assets/fto_bmi` · **Severity:** medium · **Status:** open

`skills/create-module/SKILL.md` §6 says:

> `validate_module` refuses everything `compile_module` refuses that does not need resolved rows, so
> **a green pre-flight should mean a green compile**.

The qualifier is correct and the conclusion drawn from it is not. On a freshly authored spec with no
`resolution.csv`:

```
validate_module(strict=True)  →  valid: true,  errors: [],  warnings: [],  info: []
compile_module(strict=True)   →  success: false
    "strict compile: 3 variant(s) have unresolved genomic positions after resolution"
```

Green pre-flight, refused compile — the exact implication the sentence licenses. Not one of the three
finding levels carried anything, so there is no hint in the payload that the most consequential step
has not run.

**The compile gate itself is fine** and is the reason this is medium and not high: it refuses, it names
the count, and its warning names the remedy (*"No resolution.csv and no ensembl_cache injected …
Produce a resolution.csv with just-dna-enricher"*). The defect is that the pre-flight advertises
itself as predictive of that outcome when it cannot be.

**Why it matters more than the wording suggests.** `valid: true, strict: true` with three empty
finding lists is the most reassuring output this surface produces, and the state it is reassuring
about is *a module that cannot match any genome*. The skill's own done-checklist carries "every weight
row has a coordinate" as a **manual** checkbox, which concedes that nothing checks it — so the one
condition the author must remember is the one the tool is silent on. It compounds with `F19`: an author
who cannot reach `enrich_module` sees a green strict validate and no reason to doubt it.

**Candidate fix**, cheapest first: have `validate_module` emit an `info` (or `warning` under strict)
when the spec has variant rows and no `resolution.csv` — "resolution has not run; a strict compile will
refuse N row(s)". It needs no network and no resolution, only a file-existence test plus the row count
it already has in `stats`. Then correct the skill sentence to say a green pre-flight predicts a green
compile *once resolution exists*.

**A candidate that is wrong:** having `validate_module` resolve anything itself. It is documented as
writing nothing and touching no network, both worth keeping, and authoring a second resolution path
is how the two sides of a redundancy check end up produced by one process.

## F19 — nothing on the tool surface reports the running server's version, and a stale process is invisible

**Found:** 2026-08-11, blocked mid-probe · **Severity:** medium · **Status:** open

The connected stdio server was missing nine tools the skill lists as **essentials** — `enrich_module`,
`check_identifiers`, `lookup_identifier`, `lookup_open_access`, `fetch_fulltext`,
`authoring_reference`, `module_signature`, `verify_artifact`, `registry_get_module` — which is exactly
the set 0.4.0 moved *into* essentials. The tree registers `enrich_module` in `register_passes`
(`tools/passes.py:297`), the essentials tier, so the code is right and the **process** was old:

```
2669780  Tue Aug 11 17:01:58   uv run --project … just-module-creator stdio
2726281  Tue Aug 11 18:03:54   uv run --project … just-module-creator stdio
HEAD     3a6d20d              2026-08-11 20:30:30 +0300
```

Two of them, both hours older than HEAD, consistent with the known behaviour that `/reload-plugins`
does not re-exec a stdio server and stale ones accumulate.

**The finding is not the staleness — it is that the staleness is undiagnosable from inside the
surface.** No tool reports the server's version, so the symptom presented as *"the plugin does not
have `enrich_module`"*, indistinguishable from *"this tier does not include it"* and from *"the skill
documents a tool that does not exist"*. Diagnosing it took `ps`, `git log` and a grep through
`tools/passes.py` — three moves outside the product, to answer a question the product is the only
authority on.

It is worse for the taught workflow than for an arbitrary missing tool, because `enrich_module` is
step 4 and unreachable means no `resolution.csv`, which `F18` shows a green strict validate will not
mention. The failure chain is: stale process → missing step → silent pre-flight → an author with a
module that compiles under best-effort and matches nothing.

**Candidate fix:** report the version where an agent will see it without asking — appended to
`server.INSTRUCTIONS` at build time from `importlib.metadata.version("just-module-creator")`, which is
already the single source of truth and already read by `tests/test_plugin_manifest.py`. That is
cheaper than a tool and cannot be forgotten, since the instructions are always in context. A
`server_info` tool would also work but has to be *called* to help, and nothing prompts an agent to
call it before the thing it is diagnosing.

**Not a candidate:** having the server detect its own staleness against the working tree. It would
make the server read git state it has no business reading, and it is wrong for anyone who installed
from PyPI, where there is no tree to compare against.

## F20 — `list_tables` advertises `sources.csv`; `describe_table` and `get_template` reject it

**Found:** 2026-08-11, authoring `assets/fto_bmi` · **Severity:** medium · **Status:** open ·
**Upstream half:** `S21`, filed same day

The done-checklist in `skills/create-module/SKILL.md` requires `sources.csv` ("present, covering every
source cited, and consistent with `license:`"), and the skill is explicit that a source read by hand is
invisible to the gate so the author must write the row. Every route to its columns then refuses:

```
list_tables()               → sidecars: [… "literature.csv", "sources.csv"]
describe_table("sources.csv") → Unknown table kind 'sources.csv'. Authorable kinds: … (11 listed)
get_template("sources.csv")   → Unknown table kind 'sources.csv'. Authorable kinds: … (11 listed)
```

Ours, and self-inflicted: the sidecar list in `tools/authoring.py:121-127` is a hardcoded literal while
the authorable set comes from `draft.DRAFTABLE`, so one tool names a file the next two deny exists. The
error even helpfully lists eleven alternatives, none of which is what was asked for — which reads as
"you invented that filename", not "this kind is real but undescribed".

`authoring_reference` does not rescue it: `just_dna_format.reference.authoring_reference()` omits
`SourceRow` entirely, along with `layer`, `declared_use` and the three licence flags — verified by
substring search over the generated JSON. That is the upstream half, filed as `S21`. **The two are
separate defects and both need fixing:** even after upstream includes `SourceRow`, `describe_table`
would still reject the name, because the rejection is our registry lookup and not upstream's.

**Consequence.** To write two rows I imported `SourceRow` and read `model_fields` — leaving the product
to read a dependency's source, which is the shape this repo treats as a doc bug on sight. What is at
stake is not cosmetic: `share_alike` / `commercial_use` / `redistribution` are three independent axes
where `None` means UNKNOWN and never *permitted*, and `sources.csv` is the only input the compile
licence gate reads. An author reconstructing that from the filename gets the licence declaration wrong
in the permissive direction.

**Candidate fix:** let `describe_table` / `get_template` answer for any table with a model behind it,
sidecars included, and mark the row's provenance in the result — `hand_authored: true` for
`sources.csv`, `false` for the four a pass writes — so the answer also tells the author whether writing
it is their job. That removes the hardcoded sidecar literal as a side effect.

**A candidate that is wrong:** restating the columns in the skill. It is the exact drift the "never
hardcode a schema fact" rule forbids, and the licence vocabularies are the last place to accept a
second source of truth.

## F21 — the skill's `sources.csv` rule is backwards: compliance warns, omission is silent

**Found:** 2026-08-11, compiling `assets/fto_bmi` · **Severity:** medium · **Status:** open ·
**Upstream half:** `S23`, filed same day

`skills/create-module/SKILL.md:451` says:

> It must cover **every** source your fact tables cite, including PubMed if you carry studies. A missing
> row is a warning, not an error, so it is easy to ship without noticing.

Both halves of that are wrong for the literature layer, and I found out by doing what it said. Same
spec, strict compile, twice:

```
sources.csv with pubmed + europepmc rows  →  warnings: ["sources.csv declares 2 source(s)
                                                        no table in this module uses:
                                                        ['europepmc', 'pubmed']"]
sources.csv deleted entirely              →  warnings: []          # succeeds, fully_resolved: true
```

So the documented behaviour is inverted: following the rule earns a warning, and ignoring it is
completely silent. The sentence's stated risk — "easy to ship without noticing" — is real, but it is the
*omission* that ships unnoticed, and the skill implies the opposite.

**Why it happens** (upstream, filed as `S23`): the orphan and undeclared checks both compare `declared`
against a `used_sources` set gathered from the `source` **columns** of the generated tables.
`studies.csv` has no `source` column by design — `vocab.py:411` states that design and, in the same
breath, instructs the author to add a `sources.csv` row instead. So `pubmed` can never enter
`used_sources`, and both branches follow mechanically.

**The harm is the incentive, not the warning.** An author who reads a warning tends to make it go away,
and here the only way to silence it is to delete a true row — after which the module carries no record of
the literature terms and the compile is clean. Our skill sent them to write the row; the compiler tells
them it is superfluous; the tidy resolution is the wrong one.

**Candidate fix, ours:** correct `SKILL.md:451` to state what actually happens — a `layer='literature'`
row is not joinable to any table and currently draws an orphan warning; write it anyway because it is
the only record of the terms, and expect the warning until `S23` lands. Naming the warning in the skill
also stops the next author treating it as their mistake. The done-checklist line "sources.csv present,
covering every source cited" should say the same.

**A candidate that is wrong:** telling authors to omit literature rows to keep compiles clean. It
optimises the warning count and loses the provenance, which is the whole point of the file — and it
would make our skill contradict `vocab.py:411`.

**Do not mitigate by suppressing the warning** in `_shared.to_findings`. Upstream's warning is a real
signal for genuinely orphaned rows, and filtering by layer on our side would hardcode a judgement about
which layers are joinable — a schema fact we do not own.

## F22 — `published.json`, the receipt we tell the author to commit, records `owner: null`

**Found:** 2026-08-11, rehearsing `test-sheep/fto_bmi@1.0.0` · **Severity:** low · **Status:** open

`registry_publish` says *"Identity recorded in published.json; commit it with the spec"*, and the file
it writes carries:

```json
{ "target": "test", "canonical_id": "test-sheep/fto_bmi@1.0.0", "owner": null, … }
```

`owner` is null in both the tool result and the committed receipt. The registry does know it — a
`registry_get_module` on the same module one call later reports `"owner": "sheep"`, and
`registry_claim_namespace` had already returned `{"namespace": "test-sheep", "owner": "sheep"}`. So the
value was available on the claim and is absent from the publish payload we persist.

Low severity because nothing depends on it and `canonical_id` carries the namespace, from which the
owner is recoverable via the registry. Worth fixing because the receipt's whole job is to be the local
record of what was published where, and "who published it" is a field it declares and then leaves
empty — a reader cannot tell an unowned module from a dropped field.

Probably the same root as `F15` (no enumerated client-surface contract for the registry client): the
publish response shape is read defensively and `owner` may simply not be on it. If so the fix is to fill
the receipt from the claim/whoami we already hold rather than from the publish response — but confirm
where the null originates before choosing, because `research.py::_module_card`'s defensive projection is
deliberate and must not be tightened on the strength of undated client docs.

**Related payload inconsistency, same call, not filed separately:** the top-level `resolution` block
reports `sources: ["clinvar"]` with a signature, while `versions[0].resolution` reports `sources: []`
and `signature: null` for the same version. Ours is the read side only; noting it here so the next
reader of that payload does not treat the nested copy as authoritative.
