---
name: module-revise
description: >-
  Open a module again — the second, third or twenty-fifth pass. Which kind of pass it is decides what it invalidates, what has to re-run, and whether it costs a version at all.
  Triggers: "open it again", "second pass", "revise", "update the module", "new evidence", "the source changed", "should this be a new version", "bump the version", "re-review", "what does this invalidate", "I need to change one row", "add a variant to an existing module".
---

# Pass two and beyond — revise

**Lifecycle stage:** 10 → back to 3, or 2, or 1, or 6. **Never back to 0.**

A second pass is the **normal state of a module**, not a correction of a botched first one. Every real
authoring session we have transcripts for was a second pass. A module at version 25 is a module
somebody kept caring about.

## First, get the module onto disk

Everything below assumes a spec directory you can read. When the module you are opening is somebody
else's, or is yours but only survives in the catalog, `registry_download` is how you get it — always
registered, no flag. It verifies the bytes as it fetches, so a corrupted or tampered version raises instead
of landing.

```
registry_download(target="prod", namespace=ns, name=name, version="2.0.0", dest="./work")
```

**`target` is required and the two instances share no database**, so name the one the version was
published to. **Leave `include_inputs` at its default `true`**: without it you get the compiled
parquets and `manifest.json` and none of the authored CSVs, and it is the authored CSVs a second pass
edits. With them present you do **not** need `reverse_module` — that tool reconstructs a spec from
parquet, and here the spec arrived as itself. Reach for it only on a compiled-only artifact, and read
[`module-compile`](../module-compile/GUIDE.md) first for what a round trip drops.

Then read the directory before touching it: `module-status` says which stage it is actually at, and a
downloaded module is by definition somebody's finished work rather than a fresh start.

## How to talk to the author about an old module

**An old module is out of date, not defective — and those are different claims about somebody's
work.** It usually met the requirements that existed when it was written. So:

- **Never say broken, invalid or failing** about a module being brought forward. Say **"this needs
  these decisions to work in the latest"**, and then list them. Save failure language for a module
  that is wrong on its own terms — a shifted coordinate, a quote that is not in the paper.
- **Report decisions, not findings.** If a human has to choose, it goes in the list. If nothing has to
  be chosen, it does not appear at all. Noise about work nobody had to do is what buries the three
  things that mattered.
- **Fix the evident silently.** A rename, a deprecated spelling, a column that moved — apply it and
  say nothing.

**And the line that governs that last one, because it is one step from a serious mistake.** This
layer **may** write — `RM15` retired "report, never repair" as our rule on 2026-08-20, and the
business decision is delegated here. What replaces it is not permission to rewrite anything: the two
split on **judgement**, and this table is the discriminator itself.

| | |
|---|---|
| evident, mechanical — no judgement exists to exercise | **apply it, say nothing** |
| a checked or authored value — `genotype`, `weight`, `clin_sig`, `conclusion`, `provenance_quote` | **never touch it. It goes in the decision list** |

Writing one of the second kind silently fails twice over. A later check would compare a source
against itself and agree — and worse, **the source may be the stale one**: an archive lags a
retraction or a bigger cohort, so conforming a row to it can *degrade* a module that was right, with
the check then reporting green. Editing against a source needs a reason that outranks the source, and
that reason gets written down. **When you cannot tell which side a case falls on, surface it** —
over-surfacing is recoverable and a silent wrong write is not.

A `provenance_quote` is on the never-touch side for the same reason as the rest: it is an authored
value. That is **not** a bar on writing one where none exists — since `RM15` an agent may read the
article and locate the passage itself. Adding a missing quote is authoring; overwriting somebody's
existing one is a decision for the list.

**The question is never "what version does this deserve."** It is these four, in order:

1. **What moved?** — which of the six kinds below
2. **What has to be regenerated?** — [`module-refresh`](../module-refresh/GUIDE.md) owns this
3. **What claims were invalidated?** — the attestation and the closure
4. **What will a consumer see?** — [`module-consumer`](../module-consumer/GUIDE.md) owns this

## The six kinds, and where each re-enters

| Kind | What the author did | Re-enters at | Typical trigger |
|---|---|---|---|
| **Prose** | README, changelog, logo | nothing — **amend, do not publish** | a caveat was unclear |
| **Review** | appended an `authorship` entry; changed no data | 5 (cross-check) → close | somebody read the module |
| **Evidence** | added or replaced citations, quotes, `studies.csv` rows | 3 (curate) | the preprint was published; a replication landed |
| **Data** | edited or added annotation rows | 3 (curate) | a call was wrong, a genotype was missing, scope grew |
| **Source refresh** | re-drafted from a newer snapshot | 2 (draft) | ClinVar/CPIC/ClinPGx cut a release |
| **Rebuild** | changed nothing; recompiled under a newer toolchain | 6 (compile) | a contract tightened, or the catalog asked |

**They compose, and they are not stages.** What separates them is which consequences each triggers —
and those were **measured, not derived**, because the answers are not what intuition suggests.

## There is no versioning contract, and that is a decision

A version number is a **signal a reader weighs, not a schedule.**

- `2.0.0` does not mean reviewed. `1.0.0` does not mean unreviewed.
- A human may curate from the very first version, or never.
- A module may sit at `1.0.0` forever and be fine.

The registry states SemVer *conventions* — major = the annotation results change, minor = rows added
without changing existing answers, patch = metadata only — and **enforces none of them.** It enforces
exactly two things: that the version parses as SemVer, and that this exact `(namespace, name, version)`
is free. Ordering against `latest` is a **client-side** check; the API does not compare.

> **Any rule of the form "version N means stage X" is invented.** Inventing one makes a tool withhold a
> publish waiting for a milestone that does not exist. **No agent may do that.**

What accumulates trust is what the module *records*: `authorship` entries and their `kind`, the checks
in `verification.json`, the closure. A reader weighs those directly. `v25` with two non-AI curators
says something; `v2.0.0` on its own says nothing.

## What each edit actually moves

Measured against `reference_examples/hfe_hemochromatosis` under `compile --strict`.

| Edit | `artifact.digest` | `content_signature` | attestation | closure |
|---|---|---|---|---|
| recompile, nothing touched | same | same | kept | kept |
| `README.md` edited | same | same | kept | kept |
| **an `authorship:` entry appended** | **same** | **same** | **dropped** | **dropped** |
| line endings normalized in a CSV | same | same | kept (RM82) | kept (RM82) |
| a provenance column hand-edited | **moved** | same | kept | kept |
| a `conclusion` reworded | moved | moved | dropped | dropped |

Four readings that are not obvious from the table:

**A review pass moves no identity and destroys both claims — and that is correct.** Appending a
reviewer leaves the compiled bytes byte-identical, and the compile *still* warns *"verification.json is
stale: the attestation was computed over different module bytes"* and drops the block plus the closure.
It reads as a defect: the one pass the trust model is built on appears to discard the record of having
been checked. It is not. **A review that changes nothing is an attestation *of* zero changes** — a
reviewer saying *I submit this exactly as received*. That is a new claim, made by someone who had not
made it before, so the old closure is genuinely spent, and the reviewer is exactly the person who
should re-close.

**Line endings cost nothing since format 0.6 (RM82).** The binding reads `\r\n` as `\n`, because no
human made a claim there — an editor did, or Git did through `core.autocrlf`. **It stops at newlines:** a
BOM, trailing whitespace and a missing final newline are still edits, because a human typed those.
And it is the *binding* only — `manifest.inputs[]` still lists the raw hash and size, so that entry
does move on a rewrite. Two questions, two answers: *is this the same module* versus *are these the
exact bytes*.

**Editing an authored file is what re-opens a module.** There is no `reopen` command and none is
needed. What un-closes: any changed *value* in `module_spec.yaml` or an authored CSV, a row added or
removed, a column reordered, a cell requoted — and an `authorship:` entry. What no longer does: line
endings, and a re-enrichment that rewrites a derived sidecar.

**Prose is genuinely free.** README and logo sit outside both identities *and* outside the binding.
The registry has **three amend endpoints** — changelog, logo, readme — that move no digest and no
content claim. **Do not spend a version on prose.**

## Should a review be a version at all?

This is the one question where the honest answer is a split rather than a rule, and the registry
answered it directly:

| | `reviews` row | `authorship` entry |
|---|---|---|
| version cost | **none** | one version |
| on the card | yes — `review_count`, `avg_rating`, `curated` | no |
| drives `?group=curated` | yes | no |
| moderatable | yes | no |
| a **non-author** can post one | **yes** | no |
| carries the reviewer's key | **no** | **yes** |
| travels inside the module | no | yes |

> **A `reviews` row by default; an `authorship` entry when the record has to travel inside the module
> or be signed; both when both matter.** They are not substitutes, and the deciding asymmetry is that
> a `reviews` row cannot carry the reviewer's key — so provenance-of-review is `authorship` or nothing.

**When you do take the `authorship` route, the pass is four steps and the middle two are not optional:**
append the entry → **re-run the checks** → **close again** → publish. The re-close *is* the review being
recorded, not a workaround for it.

### Where a reviewer should start

**Read the rows that disagree with a source first.** A row whose authored value contradicts what
ClinVar, ClinGen or the GWAS Catalog says is either the module being more current than the archive — a
retraction, a refuting meta-analysis the archive has not absorbed — or somebody's stale knowledge that
never got caught. **Both look identical in the file**, and only reading the reasoning tells them apart.

They are the highest-value rows in the module and the easiest to forget: whoever wrote the justification
understood it, and six months later nobody remembers whether the retraction that motivated it was itself
superseded. So a mismatch that carries a recorded reason **stays visible** — downgraded, never silenced —
precisely so a later reviewer lands on it.

**And if such a row no longer disagrees, the archive caught up: the override was right, and the record
can go.** That is the one piece of evidence in the whole format that an authored judgement was later
vindicated.

**`review_queue(spec_dir)` produces that list.** It reads the override records in
`provenance.json` and ranks them worst-first, offline:

| State | Means | What a reviewer does |
|---|---|---|
| `still_bound: false` | the authored cell was **edited again** after the reason was recorded, so the reason no longer describes the value it is attached to | read first — the justification and the value have come apart |
| `standing` | the module and the archive still disagree | read the reason and decide whether it still holds |
| `resolved` | **the archive caught up**: it now says what the module said | the override was vindicated — the only such evidence this format holds. Retire the record |
| `unknown` | the question could not be put offline | **not agreement.** Only `clin_sig` has the archive's current answer inside the module, in `clinical_assertions.csv` |

The queue exists because a reviewer previously had nowhere to start. **A record never makes a check
pass** — whether upstream downgrades a mismatch's severity when a reason is on file is their contract
question, filed as `S52` and unanswered, and a downgrade would still mean *visible*.

**The re-close IS visible downstream, and that still does not make it the default.** Both halves
matter, and the second is the one an agent gets wrong:

- **Visible, by two independent routes.** `manifest.verification` is projected onto the registry's
  module-detail response as a `VerificationInfo` block — `closed`, `closed_at`, `closed_by`, `producer`,
  `produced_at`, and a per-check list of `check`/`subjects`/`findings`/`skipped`. It reads the **latest**
  version's manifest; per-version access is the `…/manifest` route. And the bytes come back too:
  `include_inputs=True` has fetched the machine-written sidecars since registry 0.17, so
  `verification.json` arrives with the rest. `layout` only decides where they land — `split` moves
  them under `derived/` **after** the download so a reader can tell the author's files from the
  enricher's — and `registry_download` pins `flat`, which is the tree a compile wants, so you get
  the file either way. Deliberately not a card facet, not a filter, not sortable, and
  `None` is not collapsed with an empty block: **absent means no attestation survived**, which is a
  different statement from an attestation that recorded no checks.
- **That `closed: true` is hash-checked, not asserted.** The projection reads the manifest, never the
  file, and the registry compiles the spec itself — so the closure in that block was re-bound by *their*
  compiler against the authored bytes and dropped if it did not match. It is the strongest form of
  "visible" available, and it is still **not a registry verdict about your checks**: they will not read
  your attestation as one, because they cannot reproduce offline what your enricher saw against live
  sources.
- **So do not invert the advice.** *Visible* is not *recommended*. The default instrument for a plain
  review is still the `reviews` row above. A skill that told authors to bump a version for every review
  would be the opposite error to the one this box used to correct.

Two neighbouring facts, both current:

- **The pre-flight no longer refuses a review publish.** It did, and that disagreement was repaired in
  registry **0.16.0**: `would_publish_module_level` now quantifies over `published_elsewhere` — content
  hits under a *different* `(namespace, name)`, which is what the gate actually refuses — while
  `published_as` still lists the same-module hit, because *"this data is already published as 1.0.0"* is
  exactly what a review pass wants to confirm. **The honest caveat is a version floor**: a deployment
  older than 0.16.0 still refuses.
- **`authorship` reaches no projected field, and that is policy rather than an omission.** It is
  payload, so the card never renders an author's claim about their own reviewer beside the server's own
  claims. **Read it from the manifest.**

*(This section was the subject of `S46`, filed and answered 2026-08-20. `MODULE_LIFECYCLE.md` §6.6 and
RM86 are rewritten and RM86 is closed; the facts above are theirs, not our correction of theirs.)*

## What the registry does with v2

Structurally v2 is the same call as v1 — same multipart publish, same files, same gates. What differs
is what is already claimed.

- **No content relationship between versions is enforced or recorded.** No diff requirement, no parent
  digest, no monotonic stats. The one cross-version rule is the duplicate-content gate, keyed on
  `content_signature`, and it **exempts a later version of the same module** — which is what makes a
  pure review pass publishable at all.
- **v1's data is claimed forever.** Publishing v1's rows under a *different* `(namespace, name)` is
  refused, and **yanking v1 does not release the claim.** Yank delists; it never edits.
- **v2 compiles under today's contract; v1 did not.** This is the real asymmetry of a rebuild pass — a
  spec that passed two releases ago can hit a tightened validator on the way back in. The registry's
  `revalidate` classifies every published version (`ok` / `upgradable` / `needs_upgrade` / `blocked` /
  `strict_blocked` / `superseded`), and `upgrade` remediates by **re-publishing the latest non-yanked
  version as the next patch, never mutating old bytes.**
- **v2 replaces the card.** README, title and display come from the newest spec; `updated_at` advances,
  `created_at` does not. A spec with **no** README leaves the existing prose alone rather than blanking
  it.
- **Rehearse v2 too.** A first pass is not the only thing worth rehearsing — on production a botched
  publish is permanent in two ways at once. `module-publish` owns the rehearsal.

## What needs a pilot, and what you may simply fix

The discriminator is the table at the top of this skill, and it is the canonical statement of the
split: **evident and mechanical → apply it and say nothing; a checked or authored value → it goes in
the decision list.** What follows is the second half of that table, worked through for a second pass.

**Surface it, and let a pilot settle it:**

- **Which side is right when a re-draft reports `differs`.** That is the source disagreeing with
  something you already authored. It is left unchanged deliberately, because only you know which is
  correct. [`module-draft`](../module-draft/GUIDE.md) owns the report.
- **Whether the prose still tells the truth.** Nothing checks a README against the rows beneath it. In
  the real corpus, prose is **identical across versions whose data doubled** — and one pair carries an
  identical `content_signature` while claiming a "maintenance update".
- **Whether a stale hand-curated row should survive a re-derive.** Deleting a sidecar to refresh it
  discards curation along with staleness. [`module-refresh`](../module-refresh/GUIDE.md) owns the costs, table by table.
- **The version number itself.** Nothing enforces it, so nothing can check it. Say what changed in the
  changelog and let the number be a signal rather than an argument.

## What this stage cannot do

**Nothing in the artifact or the catalog relates two versions.** No parent digest, no "what changed
since v1" record, nothing stored. What you *can* do is compare two directories you have with
`compare_modules`, and read the signatures — [`module-diff`](../module-diff/GUIDE.md) owns both.

**No consumer is notified that v2 exists.** There is no upgrade action anywhere in the install path —
no "update available" badge, no SemVer comparison. A published v2 sits there until someone looks.

**A re-draft cannot repair a module drafted before a drafter fix.** It appends and reports; it never
rewrites. Whether a re-run converges depends on whether the old bug *skipped* rows or *wrote* them
under an identity that has since moved — and those need opposite remediations. [`module-refresh`](../module-refresh/GUIDE.md) owns it.

**Nothing un-publishes.** Yank delists a version; it does not remove it and does not release its
content claim.

## Symptoms

Do not guess at a message — `../module-101/references/SYMPTOMS.md` maps upstream text to cause and
action. The three you will actually meet on a second pass:

- *"verification.json is stale: the attestation was computed over different module bytes"* — expected
  after any authored edit, including an `authorship` append. Re-run the checks and close again.
- *"Studies reference variants not in variants.csv"* after a re-draft — usually a stale rsid-only study
  row beside its coordinate-keyed replacement, not a bad citation.
- `already_present` / `differs` from a drafter — the first is inert, the second is a decision.

## Where to go next

| You need | Load |
|---|---|
| what to delete before re-deriving, and what deleting costs | [`module-refresh`](../module-refresh/GUIDE.md) |
| what moved, and which signature says so | [`module-diff`](../module-diff/GUIDE.md) |
| the table you are about to edit, in full | [`module-tables`](../module-tables/GUIDE.md) |
| rehearsing and promoting v2 | `module-publish` |
| the closure and the attestation in detail | [`module-tables`](../module-tables/GUIDE.md) → `references/verification.md` |
| the first pass, stage by stage | [`module-101`](../module-101/GUIDE.md) names the spine; start at [`module-start`](../module-start/GUIDE.md) |
