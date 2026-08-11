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

## F12 — the first step of the publishing workflow is not in the tool surface

**Found:** 2026-08-11, asked to create an account and a namespace on the live
registry · **Severity:** high · **Status:** open

The task was "create the `test_creator` account with the `test_modules`
namespace". It stops at step zero. `registry_whoami`, `registry_claim_namespace`
and `registry_publish` all need a token; the only instruction the surface gives
for obtaining one is `authenticate`'s docstring, which says *"Get one by
registering with the registry (`registry-client register`)"* — a shell command in
another package. Every tool that could act is gated behind a credential no tool
can mint.

`RegistryClient.register(install_id, account)` is public upstream and does the
whole thing: it POSTs `/auth/register` and returns `{token, account, namespaces}`.
Registration is deliberately self-service — no admin, no email — gated only by a
Hashcash-style install-id that `just_dna_registry.installid.generate_install_id`
grinds locally in about a second. So this is not an upstream gap to file; it is a
public onboarding API we simply never wrapped.

**Why it counts rather than being a shrug:** the moment the answer is "shell out
to `uv run registry-client register`", the plugin has stopped being the surface
and become a thing you keep a terminal next to. The install instructions promise
one command; onboarding quietly costs a second toolchain.

**Desires, in the order they matter:**

- A `registry_register(account, install_id=None)` tool that grinds the
  proof-of-work when no install-id is passed, registers, and hands back the
  token. It writes to the registry but *cannot* be token-gated — it is what
  produces the token — so it belongs beside `authenticate` in `auth.py`, not in
  the gated `registry.py`. The tiering rule in `CLAUDE.md` §5 ("token-gated =
  registry writes") has no row for this and would need one sentence added.
- It should store the minted token into the caller's own session slot, the same
  way `authenticate` does, so registering leaves the session usable instead of
  making the agent copy a secret back through the transcript.
- **The install-id is the account's only recovery path** and nothing in our
  surface has anywhere to put it. Re-registering the same install-id reissues a
  key for the *same* account; lose it and the account is unreachable, since there
  is no email and no admin. The CLI merely prints it. Returning it with a "save
  this to `.env`" note is the honest minimum; persisting it ourselves would widen
  the write surface (§2) and should not be done casually.

## F13 — an irreversible claim has no pre-flight, though upstream ships one

**Found:** 2026-08-11, same session · **Severity:** medium · **Status:** open

`registry_claim_namespace`'s own docstring says a namespace "is claimed once and
then owns every module published under it, so this is not a step to run
speculatively" — and then offers no way to be non-speculative. The only way to
find out whether `test-modules` is free is to try to take it.

`RegistryClient.namespace_available(namespace)` is public upstream, read-only and
needs no token. It is unwrapped. It belongs next to `registry_search` in
`research.py`, which is already the home for token-free registry reads.

Two things surfaced while establishing this, both of which a pre-flight would
have answered without a round trip:

- **Neither name in the request was legal.** Accounts are validated with the same
  slug rule as namespaces — `is_valid_namespace`, lowercase alphanumeric plus
  hyphens (`api/routers/auth.py:104`). `test_creator` and `test_modules` are
  rejected with `invalid_account` / a `ValueError`; they have to be
  `test-creator` and `test-modules`. `registry_claim_namespace` does validate
  locally before spending a call, which is right. Nothing validates an account
  name, because nothing creates an account (F12).
- **The underscore rule is only discoverable by reading upstream source.** Our
  docstring says "Lowercase, hyphen-separated", which a reader can take as a
  style preference rather than a hard reject. Saying what is rejected, and that
  the same rule governs the account name, costs one clause.

**Desire:** wrap `namespace_available` as a read-only tool, and have
`registry_claim_namespace` name the pattern in its error rather than passing
through `ValueError`'s text.

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
  **Blocked on [F12](#f12--the-first-step-of-the-publishing-workflow-is-not-in-the-tool-surface)**:
  the token cannot currently be obtained from the tool surface at all.
- **A module with two of something the examples show one of.** The worked example
  throughout is a single-gene, single-rsID module. A paralogous rsID mapping to
  several loci, or one gene carrying two variants with different thresholds, is
  where a key that works for one instance stops working.
