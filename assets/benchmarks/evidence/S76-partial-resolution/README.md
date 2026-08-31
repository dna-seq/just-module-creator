# Evidence for S76 / F70 — a `resolution.csv` that covers fewer subjects than the module authored

`resolution.partial.csv` is the sidecar found in `run-ards-a` after it died during `enrich`,
2026-08-31. Captured and hash-verified before the original was deleted. **Do not edit the CSV** — it
is the artifact the finding rests on; this README is the part that has been corrected.

- **203 data rows, 201 distinct rsIDs** — against **263 distinct rsIDs** authored in that run's
  `variants.csv` (789 variant rows).
- Every row has `status=resolved` and real coordinates and VRS ids. Three sources are represented:
  `ensembl-rest`, `cache` and `clinvar`.
- **Nothing in the file records that it is short.** No marker, no count, no sentinel — which is the
  finding, and it survives everything below.

## The first reading was wrong, and the file is what says so

It was reported as a **partial write** left by the kill, with merge-not-clobber entrenching it on the
next run. Neither half holds.

- The rows are **sorted by rsid end to end** and the last line terminates with a clean CRLF.
- The 62 absent rsIDs **scatter across the whole alphabetical range** of the authored set — indices 0
  and 262 among them — rather than falling off the tail.

So this is a **complete write of an incomplete resolution set**. It matches the enricher's design:
`_write_resolution_csv` runs once at the end, and a subject whose live request could not be *made*
joins `unreachable_rsids` and is written as **no row at all**, deliberately, since `status="not_found"`
would state that a source was asked and said no. An ordinary `best_effort` run over a source that
stops answering produces the same file with nothing interrupted.

**Re-running is the correct recovery.** In the installed 0.6.6, the partition below the merge skips
only subjects an existing row already covers, so the 62 have nothing to merge onto and go to the
resolver. Upstream measured the same on their tree and on `v0.6.6` from its own tag.

**Likely cause of the 62 unanswered requests, stated as inference:** six benchmark agents sharing one
pacing gate, plus a worker thread that outlives a dead client. Neither is measured.

## Where it is filed

Format-tree `S76`, withdrawn there as an `S66` duplicate, with a dated reporter's correction appended
under the same entry: `RM128`'s atomic write cannot prevent a file that was never half-written, so
what closes it is `RM141` — `validate --strict` reading the table against the spec beside it — which
upstream landed anyway. Tracked here as `F70` in `docs/dogfooding.md`.

Kept because both reports cite it; do not delete without checking they are closed.
