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
- **Asked of the lead** (2026-11-18): seats README row and `page_budget.py`'s docstring done (5f9900d). The rest
  (wake_from, CLAUDE.md's "Manuscript writing" and reading list, §11's typesetter line, manuscript-skills in
  tracked settings) is `blocked: desk #366` (the lead's recommendation: 1-3 yes, the plugin in personal settings;
  default nothing changes).
- **Asked of the pm** (same topic): PM.md's "the writing is the lead's or the person's", its wake_from.
- **Claims to check before any edit to them** (`unattended`): the appendix counts "Tools (60)" and "Skills (20)"
  against today's surface (the command/guide split is seven plus the guides; tool count moved since August).

## Blind spots

- The improvement run's 17 decisions are not yet read item by item; nothing here says which are still live
  after three weeks of code changes.
- No revision marks are known to be in the master; who signed which segment is unread.
