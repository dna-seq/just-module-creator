# Roadmap

Active-only, forward-only. One `## RMn — name` per **open** item. Shipped and
deferred items move to [ROADMAP_HISTORY.md](ROADMAP_HISTORY.md) with their
rationale; nothing is deleted, only relocated.

**An item belongs here only if the work is ours.** A gap whose fix lives in
`just-dna-format` / `-compiler` / `-enricher` / `-registry` is filed upstream as
an `S<n>` and tracked in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md) as an
`F<n>` — never as a roadmap item, because putting it here says we intend to build
something and invites a workaround where a note was owed. A probe belongs in
[dogfooding.md](dogfooding.md), not here.

---

## RM6 — two literature parsers have no fixture, so nothing tests them

**Severity:** medium · **Status:** open · **Owner:** unassigned

`parse_semantic_scholar` and `parse_arxiv` are exercised by nothing. Every other
parser has a real captured payload under `assets/literature/`; these two do not,
because both services answer HTTP 429 to this machine's IP regardless of
user-agent or pacing — arXiv on a first request with no prior traffic, confirmed
with plain `curl` outside the client.

The block itself is not a defect anywhere and not ours to fix. **The untested
parser is ours**, and a parser with no test breaks silently when the API shape
moves.

Two ways out, not exclusive: capture the fixtures from a host that is not
blocked, or set `S2_API_KEY` — Semantic Scholar's keyed pool is not the one being
throttled — and capture at least that half. Recorded as **F6** in
[dogfooding.md](dogfooding.md).

---

## RM8 — three registry releases of client surface are unwrapped

**Severity:** medium · **Status:** open · **Owner:** unassigned

We adopted registry 0.12.0 (from 0.9.1) for the test/prod split and wrapped only what
that needed: `target` everywhere, plus `delete_version` / `delete_module`. The rest of
what 0.10–0.12 added to `RegistryClient` is still unwrapped, and one of it is load-bearing:

- **`validate` and `check`** — server-side pre-flight. `check` is the `would_publish`
  dry run behind [F11](just-dna-format-pending-fixes.md); upstream's 0.13.0 adds
  `would_publish_module_level` to `validate`, which is the ceiling-free half we asked
  for. Wrapping these is what turns "rehearse the publish" into "ask whether it would
  publish" without spending a version number at all.
- **`is_published`** — wrapped *inside* `registry_publish` as the dedup pre-flight, and
  not exposed as a tool of its own. It probably should be: "has this data been published
  already, under any name" is a question an author has before they are ready to publish.
- **`content_signature`, `lookup_by_signature(s)`** — the local signature and the
  name-independent lookup that `lookup_by_digest` cannot do.
- **`health`**, **`issue_jwt_token`** — the first is how we would report an instance is
  reachable; the second is optional and returns 501 when the server has no secret.

Not urgent, and deliberately not done in the same change as the split: adopting a
version and wrapping its surface are separate risks, and the split had to ship first.
Do it when 0.13.0 is on PyPI, so `would_publish_module_level` is there to wrap rather
than a field we would have to feature-detect.

---

## Idea book

Freeform, unscheduled, no commitment implied.

- A `module_diff` tool: two spec directories in, the authored rows that differ
  out. `module_signature` answers *whether* two specs differ but not *where*, and
  "diff the tables" is the standing advice whenever a digest moves without an
  intended content change.
- Surfacing `hints.REDUNDANCY_BEARING` as a resource rather than only as a field
  on `describe_table`, so an agent can read the whole list once instead of per table.
