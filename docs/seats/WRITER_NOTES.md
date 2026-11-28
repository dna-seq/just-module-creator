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
- **EASRP 2026 reviews**: decided 2026-11-25, desk #368 option 1 (all 23 as proposed, the two declines and the
  new measurements named); ledger ffa5f0c. The person's answer adds the control design: a no-plugin run with the
  module-creator docs plus the compiler, and one with parquet examples plus the paper; isolated, no adjacent tools,
  risk that it fetches just-dna-compiler from PyPI. Forwarded to the tester 2026-11-25 (#just-module-creator >
  benchmarks, 643696214). Its plan (643717646, tester notes 5b92948): arms on sirt6, centenarian, ards; P plugin
  0.48.20 (all arms one build), B skills docs + just-dna-compiler venv, no plugin, outside /data/sources, web on;
  C published parquets + the paper's full text, no just-dna package, scored after reverse_module; isolation read
  from init lists and tool_use blocks. Only sirt6 has an adjudicated reference: ards and centenarian get cross-arm
  counts and a per-row check against the paper, so the paper must not call those an expert reference.
  Both waves written (Opus 5 on 2026-11-26, Opus 5.5 on 2026-11-28; assets/benchmarks/ROUND5.md, runs r5-opus5-*
  and r5-opus55-*): Results sec:baseline, Tables 4-5 stacked by model, abstract, contribution 4, Limitations,
  Conclusion, availability. Ledger: 10 measurement items landed. Still pending: R2.S2 (several curators,
  inter-rater) and R2.Q3 (rows an expert corrects), both needing people (asked of the person).
  What the paper now says: no run invented a paper or rsID; all 6 plugin modules pass strict validation, 8 of 12
  without it fail validation or carry no position (a validation count, not an install test); direction on sirt6
  does not separate the arms consistently (Opus 5: both no-plugin arms call C/C protective; Opus 5.5: all three
  arms call T/T risk where the reference is blank, unscored); ARDS has two outcomes (ST5, ST9) and each run
  matches the one it states. The plugin arm's own slips (a directory listing, a longevitymap download) are
  disclosed beside the examples arm's doc fetch.
- **Round 4** (the tester, 2026-11-19, notes f869fe9): sirt6 on plugin 0.48.15, claude-opus-5, runs a-c all 1.00
  rsID/pair recall, decoy 0, citation and direction 1.00; run d on claude-opus-5-5, citation recall 0.50. Caveat
  F168: module-curate's worked case names this fixture's answer and runs c and d read it, so a and b are the clean
  comparison (Table 3's runs never opened it). F169: runs not held at the tag. Whether Table 3 moves to round 4 is
  the person's call (desk #369). Reruns (notes 1513e9c, from main ebfdb61, not the tag): clean set is a, b, e on
  Opus 5 (pair recall 1.00, 1.00, 0.67) and f on Opus 5.5 (0.67); every miss a whole genotype row left out, never a
  wrong one. #369 updated with this 2026-11-19.
  If round 4 enters Table 3: runs e and f ran on main a few hours after the 0.48.15 tag (three differences, none
  feeding a scored cell, per the lead's milestone correction); the Opus 5.5 row is a single run, one observation.
- **Benchmark rounds** after round 4 are the tester's (f2a4483); its reports come to this seat. A changed number
  for Table 3 is the person's call (keep the 0.27.0 runs, or switch).
- **Asked of the lead**: all done (5f9900d; desk #366's four in e0801ee: wake_from, CLAUDE.md's manuscript
  section and reading list, §11's tectonic line, manuscript-skills@dna-seq in the tracked settings).
- **Asked of the pm** (2026-11-18; the pm seat unheld since, both still undone on 2026-11-19): PM.md's "the writing is the lead's or the person's", its wake_from.
- **Appendix counts**: checked 2026-11-19. 60 tools and 20 skills (7 + 13) were true of 0.27.0 (decorators at
  221b95f); today 100 tools and 21 skills (7 + 14). The text now pins the counts to 0.27.0. Whether the appendix
  moves to the current surface waits on desk #369's answer (which version Table 3 reports).
- **On the desk** (filed 2026-11-19): #369 Table 3 and round 4 (default: August runs only). #367 closed on its
  default 2026-11-27 (no authors printed; the title block was already empty). #368 answered 2026-11-25.
- **Catalog split** (2026-11-25): 31 August's eight modules were 5 antonkulaga, 2 ksuha-dna, 1 eric-mods; the text
  says 3 of 8 from outside; the authors still confirm which namespaces are outside (record outside-namespaces).

## Blind spots

- The improvement run's 17 decisions are not yet read item by item; nothing here says which are still live
  after three weeks of code changes.
- No revision marks are known to be in the master; who signed which segment is unread.
