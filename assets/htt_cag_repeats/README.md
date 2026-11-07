# `test_htt_cag_repeats`: HTT CAG repeat bands, and what authoring them broke

A reference example from the tester seat's probe on 2026-11-07, plugin 0.48.2 on compiler 0.7.2 and
enricher 0.7.3. It is a binning module: one locus (HTT, repeat unit CAG), four bands of repeat length and the
sentinel row a consumer selects when nothing was measured. The name is `test_`-prefixed so the registry's
test-data sweep collects a rehearsal of it. **It has not been rehearsed**: the test registry answered
HTTP 502 for the whole session.

## The module

| CAG repeats | direction | reading |
|---|---|---|
| 26 or fewer | neutral | typical length |
| 27–35 | neutral | intermediate: no disease expected in the carrier; can lengthen when passed on |
| 36–39 | risk | reduced penetrance (Kay et al. 2016, PMID 27335115) |
| 40 or more | risk | full penetrance |
| not measured | unknown | the sentinel |

The measurement is read from `FORMAT/REPCN` (ExpansionHunter), the longest allele. **Only the 36–39 band cites
a paper.** The other boundaries are the standard diagnostic ranges, but no text retrieved in the session stated
them (the ACMG technical standard, Potter et al. 2004, came back as its abstract only), so their `pmid` is
empty rather than cited unread. The compiler reports that as `bins_ungrounded`, which is the honest state.
Authored by hand and logged in `logs/authoring.log`. This module is a probe, not a catalog candidate.

## What it broke (findings in `docs/dogfooding.md`)

- **F129**: `draft_from_strchive`, the only binning drafter, drafted nothing. It reported the STRchive lane
  unprovisioned while `provision_caches` reported it present. Upstream 0.7.3's drafter never resolves the
  lane; upstream fixed it in 0.8.0.
- **F128**: the session ran this checkout's server with the released 0.47.0's skills.
- **F125, second instance**: the closure warning names `just-dna-compiler close` where this surface has
  `close_module`.
- **Compiler, filed upstream as format `S136` and `S137`** (both reproduce on compiler 0.8.0): two warnings reason about `RUC`/`CIRUC`, though every bin declares
  `source_field: FORMAT/REPCN`, and the tiling one is listed as `actionable`, advising `measure_tiling:
  continuous` for a whole-number count. The `bins_ungrounded` text says "no bin pmid" while one bin carries one.

What held: `lint_rows` was clean on the first pass, the integer bins tile with no overlap and no false hole
between 26 and 27, the strict validate and the strict compile agreed, and `record_override` logged the
table-scope authoring move.

## Reproduce

`validate_module(spec_dir="assets/htt_cag_repeats")` gives the four warnings above;
`draft_from_strchive(spec_dir=<a fresh scaffold>, genes=["HTT"], use="non_commercial", dry_run=true)` gives F129
on enricher 0.7.3.
