---
name: module-revise
description: >-
  What to do the second, third and twenty-fifth time somebody opens a module. Covers the six kinds of
  second pass and which stage each re-enters, what each one invalidates, why a review pass destroys the
  attestation and why that is correct, semantic versioning with no contract behind it, whether a review
  should cost a version at all, and why prose is free. Load this whenever a module already exists —
  which is the normal case, not the exception. Triggers: "update a module", "second pass", "new
  version", "revise", "review pass", "bump the version", "which version", "already published",
  "amend", "what version should this be", "somebody reviewed it", "re-close", "verification.json is
  stale", "v2", "the module already exists".
---

# Pass two and beyond — revise

**Lifecycle stage:** 10 → back to 3, or 2, or 1, or 6. **Never back to 0.**

A second pass is the **normal state of a module**, not a correction of a botched first one. Every real
authoring session we have transcripts for was a second pass. A module at version 25 is a module
somebody kept caring about.

**The question is never "what version does this deserve."** It is these four, in order:

1. **What moved?** — which of the six kinds below
2. **What has to be regenerated?** — `module-refresh` owns this
3. **What claims were invalidated?** — the attestation and the closure
4. **What will a consumer see?** — `module-consumer` owns this

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

⚠️ **`MODULE_LIFECYCLE.md` §6.6 currently argues this is unsettled, on a premise that has moved.** It
says the closure *"reaches nothing — `verification.json` is uploaded, stored, and then read by no code
path, absent from `RECOGNIZED_SPEC_FILES`"*, and concludes that a re-close costs a version for an
invisible record. Measured against registry 0.18.2 today: it **is** in `RECOGNIZED_SPEC_FILES` (so
`revalidate` materializes it and `upgrade` carries it forward) and **is** in `DERIVED_FILES` (so a
split download places it in `derived/`), both since registry 0.16/0.17, and `manifest.verification`
attests it. It is still **not** in `SIGNATURE_INPUTS`, which is the property that makes carrying an
unread file safe. What remains true is that the registry will not read it *as a verdict* — it compiles
what it publishes, so the digest is theirs and the attestation is the publisher's word. Filed upstream
as `S46`; if §6.6 is updated, cite them and delete this box.

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

## What only an author may decide

- **Which side is right when a re-draft reports `differs`.** That is the source disagreeing with
  something you already authored. It is left unchanged deliberately, because only you know which is
  correct. `module-draft` owns the report.
- **Whether the prose still tells the truth.** Nothing checks a README against the rows beneath it. In
  the real corpus, prose is **identical across versions whose data doubled** — and one pair carries an
  identical `content_signature` while claiming a "maintenance update".
- **Whether a stale hand-curated row should survive a re-derive.** Deleting a sidecar to refresh it
  discards curation along with staleness. `module-refresh` owns the costs, table by table.
- **The version number itself.** Nothing enforces it, so nothing can check it. Say what changed in the
  changelog and let the number be a signal rather than an argument.

## What this stage cannot do

**Nothing compares two versions of a module.** There is no diff tool, no parent digest, no "what
changed since v1" report — you compare signatures and read the changelog. `module-diff` owns what
*can* be read off the identities.

**No consumer is notified that v2 exists.** There is no upgrade action anywhere in the install path —
no "update available" badge, no SemVer comparison. A published v2 sits there until someone looks.

**A re-draft cannot repair a module drafted before a drafter fix.** It appends and reports; it never
rewrites. Whether a re-run converges depends on whether the old bug *skipped* rows or *wrote* them
under an identity that has since moved — and those need opposite remediations. `module-refresh` owns it.

**Nothing un-publishes.** Yank delists a version; it does not remove it and does not release its
content claim.

## Symptoms

Do not guess at a message — `../create-module/references/SYMPTOMS.md` maps upstream text to cause and
action. The three you will actually meet on a second pass:

- *"verification.json is stale: the attestation was computed over different module bytes"* — expected
  after any authored edit, including an `authorship` append. Re-run the checks and close again.
- *"Studies reference variants not in variants.csv"* after a re-draft — usually a stale rsid-only study
  row beside its coordinate-keyed replacement, not a bad citation.
- `already_present` / `differs` from a drafter — the first is inert, the second is a decision.

## Where to go next

| You need | Load |
|---|---|
| what to delete before re-deriving, and what deleting costs | `module-refresh` |
| what moved, and which signature says so | `module-diff` |
| the table you are about to edit, in full | `module-tables` |
| rehearsing and promoting v2 | `module-publish` |
| the closure and the attestation in detail | `module-tables` → `references/verification.md` |
| the whole first-pass procedure | `create-module` |
