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

## F1 — the drafting step is not on the tool surface, and the reflex is to route around it

**Found:** 2026-08-11, authoring the first real module · **Severity:** high ·
**Status:** open · **Roadmap:** [RM1](ROADMAP.md#rm1--the-drafting-path-is-unwrapped-so-the-authoring-loop-has-a-hole-in-the-middle)

The workflow the skill teaches is scaffold → draft → curate → enrich → compile.
Everything but *draft* is a tool. So an agent following it reaches step 2, finds
nothing to call, and the available move is to shell out to
`just-dna-enricher draft-panel` — or, worse, to fetch ClinVar directly and write
the rows by hand.

This is exactly the capability-gap rule: the moment you reach for a raw call to
get past something the product cannot do, the exercise stops producing signal.
Shelling out proves the task is possible with general tooling, which was never in
question. **The gap is the result.**

Recorded rather than routed around. The skill now names the CLI explicitly for
this step and `references/CLI.md` states what is deliberately unwrapped, so the
hole is documented rather than discovered — but it is still a hole.

## F2 — `lint_rows` documents refusals it never returns

**Found:** 2026-08-11, first lint of a real row · **Severity:** low ·
**Status:** open · **Roadmap:** [RM5](ROADMAP.md#rm5--lint_rows-promises-refusals-it-does-not-currently-produce)

`LintResult.alterations` is described as carrying "normalizations applied, plus
refusals you must act on yourself", and the tool docstring builds on that:
"`alterations` with `applied=false` are refusals, not failures".

That is true of `lookup_variant`, which returns four refused alterations for a
plain rsID query. It is not true of `lint_rows`: upstream's `inspect_rows`
reports the redundancy-bearing columns as `info`-level **findings** and returns
an empty `alterations` list. Verified on a valid one-row `variants.csv` — three
`info` findings naming `chrom`, `start` and `ref`, zero alterations.

Nothing is broken; the information is present, under a different key. But the
docstring points an agent at a field that is reliably empty, which is the kind of
claim §7's "attack claims, not gaps" is about — our own doc promising something
our code does not do.

## F5 — resolution never reaches the non-SNP table families

**Status:** mitigated here, open upstream. Full entry in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md); filed as
`S9` in `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md`.

Listed here too because the mitigation is documentation only: a
`pharm_variants`-led module still compiles green with null coordinates, and
nothing in our surface warns.

---

## Probes not yet run

Recorded so the gaps in *this* file are visible too, per the completeness rule.

- **Author a real module end to end and publish it.** Everything up to
  `compile_module` has been exercised on a real spec; `enrich_module` and
  `registry_publish` have not ([RM4](ROADMAP.md)). This probe would also hit F1
  from the inside rather than by inspection.
- **A binning module.** Every probe so far has been `variants.csv` or
  `pharm_variants.csv`. The bounds rules are the densest part of the domain — two
  kinds with opposite endpoint conventions — and nothing has tested whether the
  tools make them followable. Per "pick the probe where the design generalized
  from one case", the case to use is one with two bins sharing an endpoint.
- **A module with two of something the examples show one of.** The worked example
  throughout is a single-gene, single-rsID module. A paralogous rsID mapping to
  several loci, or one gene carrying two variants with different thresholds, is
  where a key that works for one instance stops working.
