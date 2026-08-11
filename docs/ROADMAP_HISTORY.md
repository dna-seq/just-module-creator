# Roadmap history

Items no longer on [ROADMAP.md](ROADMAP.md) — **shipped**, or **deferred with a
reason**. Nothing is deleted; it is relocated. Newest first.

An item that left the roadmap because the work turned out not to be ours is not
here: it is filed upstream as an `S<n>` and tracked in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).

---

## The essentials tier was defined by the wrong axis

**Shipped:** 2026-08-11 in 0.4.0 · *"If you find essentials surface lacking
before I even started, maybe reconsider the essential stack?"*

Never a numbered roadmap item — it arrived as a dogfooding observation (the
default tier could not verify a trait CURIE) and was widened into a rule change
because the survey found the observation was a symptom.

The old rule, *essentials = everything that only reads, plus the ClinVar draft*,
was false in both directions: `scaffold_module` and `compile_module` write and
were always in it, and six read-only tools were not. The decisive case was
`enrich_module` — extended-only while being step 6 of the workflow the server's
own `INSTRUCTIONS` teach. **A tier that teaches a step it cannot run is the
failure mode**, and it is now asserted rather than remembered: a test parses the
tool names out of that instruction text and requires all of them in essentials.

The replacement axis is **cost**: essentials is everything bounded by what the
caller named (one identifier, one paper, one spec directory); extended is what a
corpus sizes, plus reading back somebody else's artifact. Nine tools moved in,
none moved out.

**The scope decision was the user's**, and it went wider than the recommendation.
The proposal was the three tools that closed the gap; the answer was "6 +
fulltexts + lookup_openaccess + enrich which can be useful for common snip
modules" — reading the tier from the perspective of the module people actually
write first, which is what surfaced `enrich_module` as the real defect.

## RM3 — signing is unwrapped

**Deferred:** 2026-08-11 · *"signing thing is a prototype rather than a real
thing. Currently the registry is the authority and gives out identity keys."*

`keygen` / `sign` stay CLI-only, and not for the key-hygiene reason this item
originally gave. The reason is that **module identity is the registry's**: it
stamps `namespace`, `owner`, `version` and `canonical_id` on publish and
overrides anything authored (upstream `S1` documents this). Ed25519 signing sits
beside that as a prototype of a second, author-held identity scheme, and wrapping
a prototype would give it a durability its design has not earned.

`keygen` writing an unencrypted PKCS#8 key remains true and remains a reason not
to have an agent generate one on its own initiative, but it is now the second
argument rather than the first.

**What came out of this instead**, because it is the half that mattered: the
registry hands back the authoritative identity on publish and `registry_publish`
was returning it in a message and dropping it. It now writes a `published.json`
receipt beside the spec — the identity keys, the digest, the content signature and
an ISO-8601 UTC timestamp — because a receipt that does not survive the session is
not a record, and it cannot live in `module_spec.yaml` where `extra="forbid"`
rejects those exact keys.

**Reopens if** author-held signing stops being a prototype.

## RM4 — nothing verifies `enrich_module` or `registry_publish` end to end

**Reclassified:** 2026-08-11 · *"RM4 is a dogfooding run."*

Correct, and it was mis-filed. This was never a thing to build — it is a probe to
run, and a probe belongs in [dogfooding.md](dogfooding.md) under "Probes not yet
run", where it now is. Keeping it on the roadmap implied a deliverable and made
the roadmap look longer than the work.

The substance is unchanged: the offline ceiling keeps the suite hermetic, so
neither tool can be a normal test. What fits is a marked, opt-in integration run
plus authoring a small real module all the way through.

---

## RM1 — the drafting path is unwrapped, so the authoring loop has a hole in the middle

**Shipped:** 2026-08-11 · `draft_from_clinvar` (essentials), `draft_from_cpic` and
`draft_from_clinpgx` (extended), in `tools/passes.py`.

The skill taught `scaffold -> draft -> curate -> ...` and `draft` was CLI-only, so
an agent left the tool surface at step 2 and came back at step 4.

**Its stated difficulty was stale and is worth recording as such.** RM1 said
wrapping was hard because `draft` "refuses and lists the choices when a
`(phenotype, drug)` pair spans several populations". Upstream removed that in
0.5.1: `DiplotypeRow.clinical_context` keeps the settings as distinct rows and
the consumer picks at query time, so `population` is now a plain filter. Our own
`SKILL.md` and `DOMAIN.md` still claimed the old behaviour and were corrected in
the same change.

What *did* constrain the design was licensing, and that part held: `use` is
required with no default on all three tools, enforced at the schema layer, and a
licence refusal comes back as `skipped=true` with its reason rather than as a
failure — because a failure invites retrying with a different `use`, which is
fabricating a licence position to get data.

Three tools rather than one with a `source` argument: the upstream signatures
share almost nothing, and a merged tool would carry twelve arguments most of
which are inapplicable per source. `lookup_identifier(kind=...)` merges because
both kinds take the same pair; these do not.

## RM2 — the fact passes are unwrapped

**Shipped:** 2026-08-11 · `enrich_facts` (frequencies, gene_metrics, dosage) and
`enrich_literature_pass`, both extended and both background tasks.

One tool for the three sidecar passes because they share a shape — spec in,
sidecar out — and `dosage` writes onto `gene_metrics.csv` rather than a file of
its own. `use` applies only to `dosage`, so the result names where it landed in
`declared_use_applied_to` rather than letting the argument look universally
meaningful. That remains the softest seam in the design.

`enrich_literature_pass` stayed separate: it is keyed on `studies.csv` rather
than on variants, and its answer is a coverage sentence rather than a row count.

## RM5 — `lint_rows` promises refusals it does not currently produce

**Shipped:** 2026-08-11 · docstring and field description narrowed.

Resolved by narrowing the promise rather than by synthesizing alterations
upstream never made: `to_alterations` exists to carry upstream's distinctions
field-for-field, not to fabricate them. The docstring now says where the
redundancy-bearing columns actually appear on this tool — as `info` findings —
and that refusals come from the lookup tools.

Recorded as **F2**, now in [previous_issues.md](previous_issues.md).
