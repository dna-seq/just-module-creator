# Roadmap

Active-only, forward-only. One `## RMn — name` per **open** item. Shipped items
move to [ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) with their rationale; nothing is
deleted, only relocated.

---

## RM1 — the drafting path is unwrapped, so the authoring loop has a hole in the middle

**Severity:** high · **Status:** open · **Owner:** unassigned

`draft-panel` (ClinVar → `variants.csv` + `studies.csv`), `draft` (CPIC → the
three PGx tables) and `draft-clinpgx` are CLI-only. They are the step between
"scaffold" and "curate", so an agent following the skill has to leave the tool
surface exactly once, in the middle, and come back.

This is the capability gap dogfooding is supposed to surface rather than route
around, and it is recorded as **F1** in [dogfooding.md](dogfooding.md).

Wrapping it is not mechanical. `draft` refuses and lists the choices when a
`(phenotype, drug)` pair spans several populations, and that refusal has to
survive as a structured result rather than as a raised error. The `--use`
licensing gate must be an explicit required argument, never defaulted, because
defaulting it to `unstated` would silently skip sources and defaulting it to
anything else would assert a licence position the user never took.

## RM2 — the fact passes are unwrapped

**Severity:** medium · **Status:** open · **Owner:** unassigned

`frequencies`, `gene-metrics`, `dosage` and `literature` each produce a sidecar
the compile gate reads. `enrich_module` is wrapped and they are not, so the
`sources.csv` a module needs is easy to end up without — and a missing row there
is a warning, not an error, so it ships unnoticed.

Wrapping them wants the same background-task treatment as `enrich_module`
(gnomAD paces at roughly one batch per six seconds) and the same
delete-to-regenerate warning in the result, since an existing sidecar is merged
rather than clobbered.

## RM3 — signing is unwrapped, and the key handling is the reason to be careful

**Severity:** low · **Status:** open · **Owner:** unassigned

`keygen` / `sign` are CLI-only. `keygen` writes an unencrypted PKCS#8 key, which
is a bootstrap rather than a key-management system, so a tool that generates one
into a workspace on an agent's initiative is the wrong default. A `sign` wrapper
that takes an *existing* key path is the safer half and could land alone.

## RM4 — nothing verifies `enrich_module` or `registry_publish` end to end

**Severity:** medium · **Status:** open · **Owner:** unassigned

Every other tool is exercised against the real upstream packages by the suite,
and the read-only network tier was confirmed by hand against the live services.
These two are not: `enrich_module` needs a real enrichment run, and
`registry_publish` needs a token, a namespace and a module we are willing to
publish immutably.

The offline ceiling keeps the suite hermetic, so neither can be a normal test.
The shape that fits is a marked, opt-in integration run plus a dogfooding probe
that authors a small real module all the way through — which would also exercise
RM1's gap from the inside.

## RM5 — `lint_rows` promises refusals it does not currently produce

**Severity:** low · **Status:** open · **Owner:** unassigned

`LintResult.alterations` is documented as carrying "refusals you must act on
yourself", and that is true of `lookup_variant`. On `lint_rows`, upstream's
`inspect_rows` reports the redundancy-bearing columns as `info`-level *findings*
and returns no refused alterations, so the field is reliably empty and the
docstring over-promises.

Either narrow the docstring to what the tool actually returns, or surface the
`info` findings under a name that matches the promise. Recorded as **F2** in
[dogfooding.md](dogfooding.md).

---

## Idea book

Freeform, unscheduled, no commitment implied.

- A `module_diff` tool: two spec directories in, the authored rows that differ
  out. `module_signature` answers *whether* two specs differ but not *where*, and
  "diff the tables" is the standing advice whenever a digest moves without an
  intended content change.
- Surfacing `hints.REDUNDANCY_BEARING` as a resource rather than only as a field
  on `describe_table`, so an agent can read the whole list once instead of per table.
- A `check_publishable` tool that runs the local strict validate plus the
  identifier checks and returns one branchable verdict — the useful half of the
  upstream `would_publish` field, without the variant ceiling that makes the
  server-side version unusable on a large module.
