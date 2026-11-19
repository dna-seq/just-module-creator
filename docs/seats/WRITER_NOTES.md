# Writer seat — notes

The seat's working state, rewritten to the present before each reset (docs/seats/WRITER.md).

## The paper now (read 2026-11-18, first seating)

- **Master**: `docs/manuscript/manuscript.tex` (+ `references.bib`). Still on the EASRP 2026 skeleton
  (`easrp2026.sty`, anonymous, `Anonymous` author, anonymized repo URL in the abstract). Sections: Introduction,
  Related work, Method (artifact, architecture, determinism/evidence, stores, evaluation dimensions), Results
  (command menu, production catalog), Discussion, Conclusion, Code and data availability, Appendix (research use,
  plugin surface: "Tools (60)", "Skills (20)").
- **Record** (`manuscript.record.yaml`, updated 2026-10-27): the 2026-10-26/27 improvement run (manuscript-skills
  0.27.1/0.31.1, on the co-author's machine) applied 99 edits for 38 of 88 confirmed problems; 17 author
  decisions open; its run folder (`reviews/20261026T154912Z-1fd1e924/`) is not on this machine (`reviews/` is
  local-only by its `.gitignore`), so the 17 decisions are readable only from `manuscript.dashboard.html`,
  `.review.docx`, `.changes.xlsx` and `.proposed.tex` here.
- **Destination**: none chosen. Ladder: BMC Bioinformatics (recommended), then Bioinformatics; preprint bioRxiv,
  arXiv fallback. The authors' priorities: "above 3 fast publish" (2026-10-19). Referees in the run: major revision
  at BMC, Application Note or reject at Bioinformatics.
- **Open in the record**: `evaluation-corpus` (later-round raw archive not recovered), `no-baseline` (never scored
  against the same model without the plugin), `outside-namespaces` (IC-7), `scored-round-version` (RP-4),
  `fee-route`, `biorxiv-version-boundary`; `ai_use_case` (the paper's own AI-assistance account) not confirmed.
- **Build**: renders. `uv run manuscript manuscript` with `MANUSCRIPT_TECTONIC=~/.local/bin/tectonic` (0.17.0):
  15 pages, 5705 words in the Markdown twin (appendix included); the built `.md` is byte-identical to the
  committed one. `.env` was pointed there on 2026-11-18; the old `tectonic-musl` binary is gone from this box.
- **Plugin**: `edits: conservative` in `.manuscript-skills.yaml` (kept, per the priming). manuscript-skills 0.58.0
  is installed on this machine, not in the tracked settings (asked of the lead, below).

## Open items

- **Frontier Research Club retrofit** (the person, 2026-11-18): section 5 `sec:loop` in the master (daf9c2d),
  facts from longevity-loci origin/main 662e366, framed as non-blocking asynchronous HITL; its limits in the
  Discussion's Limitations. Paper now 17 pages. Follow-ups not yet proposed: abstract/intro framing; the club wants
  "accepted paper or preprint" (pm asked, 2026-11-18).

- **People list**: done, `docs/manuscript/rev-marks.toml` (antonkulaga, winternewt; the person, 2026-11-19).
- **Table 3's runs found** (2026-11-19, cb8b861): `data/interim/repro-bench-3/run-sirt6-{c,d,e}`, re-scored to an
  exact match; identifiers in the record's `evaluation-corpus`. Open: archiving them somewhere that travels, and the
  caption naming the versions (RP-4), both put to the person.
  Both done: archived at f778e2d (lead), caption at 9c38608; record `evaluation-corpus` resolved (6988cf3).
- **EASRP 2026 reviews** (7051ad1): `docs/manuscript/easrp2026-reviews/letter.md` verbatim (sender's address left
  out, public repo) and `review-ledger.yaml`, 23 items, all `undecided`; the person's one confirmation question
  asked 2026-11-19 in chat. The baseline comparison (same model, no plugin) is the evaluation the tester's rounds
  could run.
- **Round 4** (the tester, 2026-11-19, notes f869fe9): sirt6 on plugin 0.48.15, claude-opus-5, runs a-c all 1.00
  rsID/pair recall, decoy 0, citation and direction 1.00; run d on claude-opus-5-5, citation recall 0.50. Caveat
  F168: module-curate's worked case names this fixture's answer and runs c and d read it, so a and b are the clean
  comparison (Table 3's runs never opened it). F169: runs not held at the tag. Whether Table 3 moves to round 4 is
  the person's call; not yet asked as its own item (it bears on the EASRP ledger's R1.W1/R2.W2).
- **Benchmark rounds** after round 4 are the tester's (f2a4483); its reports come to this seat. A changed number
  for Table 3 is the person's call (keep the 0.27.0 runs, or switch).
- **Asked of the lead**: all done (5f9900d; desk #366's four in e0801ee: wake_from, CLAUDE.md's manuscript
  section and reading list, §11's tectonic line, manuscript-skills@dna-seq in the tracked settings).
- **Asked of the pm** (2026-11-18; the pm seat unheld since, both still undone on 2026-11-19): PM.md's "the writing is the lead's or the person's", its wake_from.
- **Appendix counts**: checked 2026-11-19. 60 tools and 20 skills (7 + 13) were true of 0.27.0 (decorators at
  221b95f); today 100 tools and 21 skills (7 + 14). The text now pins the counts to 0.27.0. Whether the appendix
  moves to the current surface waits on desk #369's answer (which version Table 3 reports).
- **On the desk** (filed 2026-11-19, the person away): #367 author list (default: no authors printed), #368 the
  EASRP reviews' plan (default: nothing changes), #369 Table 3 and round 4 (default: August runs only).

## Blind spots

- The improvement run's 17 decisions are not yet read item by item; nothing here says which are still live
  after three weeks of code changes.
- No revision marks are known to be in the master; who signed which segment is unread.
