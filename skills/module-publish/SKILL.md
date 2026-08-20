---
name: module-publish
description: >-
  Rehearse on the polygon, then promote to the catalog. Covers the two registry instances and what
  differs, the pre-flights that cost nothing, reading a three-valued verdict, what the server fills in
  for you, the content claim that is name-independent and survives a yank, when to advocate for
  production rather than wait to be asked, and the files that publish without your noticing.
  Triggers: "publish", "rehearse", "polygon", "registry", "namespace", "would_publish", "duplicate
  content", "yank", "publish to production", "register", "install id", "token", "amend readme",
  "test data on prod".
---

# Stages 7–8 — rehearse, then publish

**Lifecycle stage:** 7 (rehearse) and 8 (publish).

Getting a module into a catalog without spending something irreversible. **The polygon exists because
on production a botched publish is permanent in two ways at once.**

## Two registries, and every registry tool takes a `target`

| | `target="test"` — the polygon | `target="prod"` — production |
|---|---|---|
| what it is | where a publish is a **rehearsal** | the catalog everyone installs from |
| `test-` namespaces / `test_` module names | accepted | `422 test_data_on_prod`, at the claim as well as the publish |
| deleting what you published | `registry_delete_version` / `registry_delete_module` | not possible — `yank` delists and does **not** free the content claim |
| default for writes | **yes** | only when you ask |
| default for catalog reads | no | **yes** (`registry_search`, `registry_get_module`, `registry_download`) |

**Nothing is shared between them.** Separate databases, so an account, a token and a namespace exist on
one instance only, and promoting a rehearsal means **publishing again** with `target="prod"`.

**A polygon result is never evidence about production.** Its namespace table, its catalog and its
duplicate-content rule are its own — the polygon scopes `duplicate_content` to the publishing account,
so a rehearsal cannot prove somebody *else's* identical data would be refused.

`registry_health(target=…)` confirms you are pointed where you think you are: **both instances report
their own mode**, so a target is verified rather than declared, and a publish aimed at the polygon that
would land on production refuses before spending anything.

## Three pre-flights that cost nothing

```
registry_is_published(spec_dir="spec")                    # already out there, under ANY name?
registry_check(namespace="test-ns", name="m", spec_dir="spec", target="test")
registry_validate(...)                                    # the same call without the network tier
```

`registry_check` is the full dry run: the server's own publish gates, **without spending a version
number**. It answers two things your machine cannot — whether `module.name` matches the path, and
whether identical authored data is already published under someone else's name.

**Read the verdicts as three-valued, because they are:**

- **`verdict: null` is not a pass.** The dry run never reached one — an invalid spec, or no token. The
  errors beside it are already the answer.
- **`module_level_clear` means "nothing module-level blocks this"**, never "it will publish". It covers
  three gates and excludes the network tier entirely.
- **`verdict: false` beside `rerun_rather_than_fix` means RE-RUN.** A strict publish against an
  unreachable Ensembl really does refuse, and the variants may be perfectly findable. **Changing the
  spec here is how real rows get deleted.**
- **`unchecked` is worth reading on a green run.** A `clin_sig` check the operator has no snapshot for
  never blocks a publish and is not a passed check either.
- **`non_blocking` too.** Identifier findings never move the verdict, because a publish does not run
  that pass — but `gene_locus_conflicts` living in there is the clearest sign of a fabricated row.

## Onboarding: two secrets that exist nowhere else

`registry_register` needs no token — **it makes one**, which is why it is the single registry write
that is not itself token-gated. Onboarding is self-service, gated only by a proof-of-work install-id
ground locally in about a second.

```
registry_register(account="my-name", target="test")
```

It hands back **the token and the install-id**. Save both in `.env` — `JMC_INSTALL_ID`, plus
`JMC_API_KEY` for production and `JMC_TEST_API_KEY` for the polygon. `.env` is what the server reads on
the next boot; a token that lives only in the session dies with it, and an install-id that lives only in
a transcript is gone.

- **The install-id is the account's only recovery path.** There is no email and no admin. Re-registering
  that same id reissues a key for the same account; registering again *without* it creates a
  **different** account and leaves the first unreachable.
- **Register on each instance with the same install-id.** They are separate accounts either way, but
  reusing the id keeps them recognisably yours. A token is only ever a credential for the instance that
  issued it — presenting the production key to the polygon fails as an unknown key rather than degrading.
- **The account name is not a secret and needs no saving.** `registry_whoami` reports it from the token,
  and re-registering with the same install-id returns the account that id already owns and **ignores**
  the `account` argument. So a second register will not rename an account, and it mints a fresh key
  every time — the last one you saved is the one that works.
- **Never paste either into a module, a fixture, a commit or a note.** `.env` is gitignored; everything
  else here is not.

**Names split two ways and both rules are enforced, not normalised.** An account or namespace is
lowercase letters and digits with single hyphens — `my_ns` is rejected. A *module* name is the opposite,
`[a-z][a-z0-9_]*`, so it takes underscores and rejects hyphens. Hence `my-ns/lactose_tolerance`.
`registry_namespace_available` costs nothing and reports `valid` and `available` **separately**, because
the registry will call an illegal name "available"; claiming one cannot be reversed.

## Rehearse

```
registry_namespace_available("test-my-ns", target="test")
registry_claim_namespace("test-my-ns", target="test")
registry_publish(namespace="test-my-ns", name="test_my_module", version="1.0.0",
                 spec_dir="spec", changelog="…", target="test")
registry_get_module("test-my-ns", "test_my_module", target="test")   # read back what the server made
registry_delete_version("test-my-ns", "test_my_module", "1.0.0", target="test")
```

**For a first module, prefix the module name as well as the namespace.** `purge-test-data` matches by
prefix on **both** halves, so an unprefixed module name inside a prefixed namespace is litter nobody
sweeps — and a first-time author is precisely the person who will not come back to run
`registry_delete_module`.

**Rehearsing under the name you will actually publish** is the most faithful rehearsal there is and is
accepted on the polygon; the consequence is that the operator's sweep will not collect it, so delete it
yourself. For a first module, trade that last scrap of fidelity for a rehearsal that cleans up after
itself.

**You upload the spec, not the parquets.** The server enriches, strict-compiles and stores the artifact
itself, which is why a published digest is **trusted rather than claimed**. `registry_publish` also
re-runs `validate_module(strict=True)` locally first and refuses rather than shipping a spec the server
will reject.

**Read the rehearsal back.** What came back is what a consumer sees; the card, the readme projection and
the resolution facets are all server-side.

## Promote

```
registry_register(account="my-name", target="prod", install_id="…")   # the SAME install-id
registry_whoami(target="prod")                        # the first call that actually checks the token
registry_namespace_available("my-ns", target="prod")  # read-only, no token
registry_claim_namespace("my-ns", target="prod")      # once, and it cannot be undone
registry_publish(namespace="my-ns", name="my_module", version="1.0.0",
                 spec_dir="spec", changelog="…", target="prod")
```

**Both production calls need an explicit yes, and what needs it is the irreversibility, not the
worthiness.** A version is immutable *and* its authored rows are claimed by a **name-independent content
hash that `yank` never releases** — so a botched publish spends the version number **and** the right to
publish that data under any other name. There is no overwrite, no cleanup and no admin to appeal to. Put
that cost *in* the question and name which of the two calls you are asking about.

**"Publish it" from someone who has not been told there are two registries still means: say so.**
Explain the polygon in one sentence, rehearse there, then ask about production as its own decision.
That is a rule about being clear, not about stalling.

### Do not turn "are you sure?" into "are you worthy?"

**An honest AI-authored first version belongs in the catalog.** An agent that keeps withholding
production because the module feels thin is enforcing a bar that does not exist — usually against a
person who cannot argue back on the genetics. Trust accrues afterwards, from use and from later
contributors, and none of it can start before the module is published.

**There is no versioning contract.** `2.0.0` does not mean reviewed, `1.0.0` does not mean unreviewed,
and no agent may withhold a publish or a bump waiting for a milestone that does not exist.
`module-revise` has the whole of it.

### And when it genuinely is good, say so

The default is against **assuming**, not against **advocating**. When both halves below are true, raise
production yourself rather than waiting to be asked.

**Half one — the catalog is actually missing it.** Not a guess; a call. `registry_search(gene=…)` and
`registry_search(query=…)` default to production, so ask them. If something overlapping exists, read it
with `registry_get_module` — the honest options are then extending it or saying why yours differs, not
publishing a near-duplicate.

**Half two — the module clears every bar, and these are checks rather than impressions:**

- `validate_module(strict=True)` **and** `compile_module(strict=True)` pass, with `fully_resolved: true`
  read beside `resolution_subjects`;
- every weighted row has a coordinate, and `resolution.csv` was **produced**, not authored;
- every PMID came out of a `literature_search` result whose **title you read**;
- a licence is declared and `licensing.csv` covers every source cited, honestly filled or honestly blank;
- **no row's `state` or `direction` was settled by guessing** — having *dropped* rows for that reason is
  evidence in favour;
- a polygon rehearsal was published and **read back**;
- `authorship` declares the kind honestly.

**Not on that list: whether a specialist would endorse it.** That is a question a later reviewer answers
in their own entry. A module that waits for it waits forever, because a reviewer arrives *after* there
is something to review.

**Underrepresented is necessary and nowhere near sufficient.** A stub occupies the search result a real
module would have had. The bar that applies is honesty, and failing it looks like: a `state` settled by
guessing, a PMID recalled rather than searched, a licence flag written `false` where the terms were
merely unknown, a coordinate authored beside the `resolution.csv` that verifies it, or an `authorship`
block that does not say an agent wrote it. Each ships a module that *looks* checked and is not.

## What publishes that you did not intend

🚧 **ROADWORKS — never name a logo `logo.jpeg`.** Discovery sorts `LOGO_EXTENSIONS`, so **`jpeg` beats
`jpg` beats `png`**, and a spec directory holding two logos silently ships the jpeg — the loser is not
even copied. The publisher allowlist holds `logo.png` and `logo.jpg` and **not** `logo.jpeg`, so the
result is a manifest attesting bytes the published repo does not carry, which
`verify_manifest(check_logo=True)` will not catch either, because an absent file is not a failure there.
**Guard: ship exactly one logo, named `logo.png`.** Upstream **RM105**.

**A stray `*.log` publishes silently.** `logs/` is swept up by every compile and published **with no
opt-out**, and real bundles carry system prompts and local paths — a measured submitted transcript
runs to 450 KB with single lines past 8000 characters. It is the one subtree whose contents are kept
verbatim, and a published version is immutable: `yank` delists without removing.

**`review_logs(spec_dir)` shows you what would travel**, and `registry_publish` appends the same
warning to its own result, so nothing publishes a log unseen. It **reports and never strips** — a log
is a provenance record, and publishing a flagged one is often the right call. The question it asks is
narrow: *would you be surprised to see this in the catalog?* An honest hand-written run log comes back
clean; the calibration case is `assets/logs/quote-remediation.log`, which really did travel to two
rehearsals and flags nothing.

**Two modules differing only in `weighting:` are `409 duplicate_content`**, because that block sits
outside `content_signature`. Declare it at scaffold time — `module-start`.

## Prose costs no version

Changelog, logo and readme each have an amend endpoint (`registry_amend_readme` here; the other two are
on the client). They move no digest and no content claim. **Do not spend a version on prose.**

**Version deliberately.** A rebuild that changes the compiled shape moves `artifact_digest` and needs a
version either way; a rebuild that changes *what variants are in the module* or how they are grounded is
a **major**, because someone pinned to the old major would silently receive different content. Write the
changelog as a continuation of the previous one, not a fresh "initial release" — and remember a changelog
is a claim: the catalog contains an unrecorded rewrite of 990 rows and its unrecorded revert, both
described as something else.

## What needs a pilot, and what you may simply fix

**Apply it and say nothing:** renaming `logo.jpeg` to `logo.png`; clearing a stray `logs/*.log` out of the
spec directory before publishing; deleting your own polygon rehearsal; fixing a readme through the amend
endpoint rather than a version.

**Surface it, and let a pilot settle it:**

- **Whether to spend a production version.** Irreversible in two ways; always an explicit yes.
- **Whether a near-duplicate should be extended instead of published.**
- **What the changelog says.** Nothing derives it and nothing checks it.
- **Which name to rehearse under**, and therefore who cleans up.

## What this stage cannot do

**Nothing un-publishes.** `yank` delists a version; it does not remove it and does not release its
content claim.

**Nothing notifies a consumer that a new version exists.** No badge, no SemVer comparison anywhere in
the install path.

**A rehearsal cannot prove a production outcome.** Different database, different duplicate scope,
different namespace table.

**The registry will not read your attestation as a verdict**, and cannot: it compiles the spec itself
but cannot reproduce offline what your enricher saw against live sources.

## Symptoms

`../module-101/references/SYMPTOMS.md` maps upstream message text to cause and action. Here the
messages are mostly the registry's:

- `422 test_data_on_prod` — a `test-` namespace or `test_` module name aimed at production, refused at
  the claim as well as the publish.
- `409 duplicate_content` — this authored data is already published, possibly under another name.
  Check `weighting:` before assuming it is the rows.
- *"the registry rejected your token"* — usually the wrong instance's token, not a broken account.
- `422 too_many_variants` from `just-dna-pipelines`' `marketplace check` — that check declining to run,
  never a verdict on your module.

## Where to go next

| You need | Load |
|---|---|
| the closure and the record the card projects | `module-close` |
| publishing a second version | `module-revise` |
| what the download layouts look like | `module-tables` → `references/LAYOUT.md` |
| what the card renders from | `module-tables` → `references/readme.md` |
| the client surface and the operator commands | `../module-101/references/CLI.md` |
