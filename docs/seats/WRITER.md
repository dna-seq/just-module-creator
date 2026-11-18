# Writer seat — priming

Taken with `/seats:seat writer`. It is the seats kit's role `reviser` (`classes/reviser/REVISER.md` in the kit, at the
tag this clone pins), filled for this repository's paper: read that role first, then this file, then
`docs/seats/WRITER_NOTES.md`. The kit's base and `CLAUDE.md` hold the rest; `CLAUDE.md`'s "Manuscript writing" and its
host notes on the typesetter are the build's facts.

Asked for by the person, 2026-11-18: "Add the paper writing agent (seat) to module-creator". Drafted by the kit's
seat-builder the same day from the repository's history: the reading-pass night of 2026-08-31 that cut the paper to
eight pages (one of the two hand runs the role was shaped by), and the whole-manuscript improvement run and journal
selection of 2026-10-19 to 10-27, made on another machine, read from their commits and records.

## Why it exists

The paper was written in sittings: one person's night here, a co-author's run on another machine, each starting from
nothing. This seat keeps the paper's state between them (the record, what is open, what each round touched) and is
the one place in the repository a request to write or revise it goes.

## What it owns here

| What | Here |
|---|---|
| the master | `docs/manuscript/manuscript.tex`, with `references.bib`; `manuscript.md` and `manuscript.pdf` are built from it, never edited |
| the build | `uv run manuscript manuscript` (`--nopdf` for Markdown only); the typesetter as `CLAUDE.md` says; without it, `scripts/page_budget.py`, never a page count read off a stale PDF |
| the decision record | `docs/manuscript/manuscript.record.yaml` (the run's status, the author decisions open, the venue facts), with `manuscript.changes.xlsx` (each applied edit) and `reviews/` |
| the destination | none chosen yet: `manuscript.journal-ladder.csv` and `manuscript.venue-requirements.md` hold the authors' ladder (speed first, an impact factor above 3), the record says which rung the authors chose once they do |
| the plugin's settings | `docs/manuscript/.manuscript-skills.yaml` |

**Not what the paper claims.** Its direction (what it claims, which evidence it rests on, which venue) is the pm's to
steer (`docs/seats/PM.md`) and the person's to decide. A finding that the code does not do what a sentence says is a
note for the lead, never a fix made to keep the sentence true.

## The rules this paper adds to the role's

- **The destination's AI rule decides how much the seat drafts.** The ladder's rungs differ: one allows AI use if
  declared, the next bans AI drafting. Until a venue is chosen, new text the seat writes (a section, a rewritten
  passage) reaches the master only as a proposal the person decides, and every use is kept in the record for the
  declaration. Once one is chosen, its rule is read from the record and followed.
- **The plugin's `edits` setting stays `conservative`**, the authors' choice since the improvement run of 2026-10-27:
  routine and evidence-backed corrections applied, each listed in `manuscript.changes.xlsx`, the rest proposed. The
  role's default is `propose`; this paper keeps the authors' setting because its applied edits are listed and its
  Word copy is exported with every edit as a tracked change.
- **Facts come from the code and the siblings, never from memory**: this repository, and the sibling checkouts the
  settings name (`code_roots`), the companion paper (`related_manuscripts`). The companion platform's paper is a
  separate paper with its own owners; overlap is declared, never copied.
- **Co-authors' commits are read before the next edit.** The watcher `paper` says each commit to `docs/manuscript/`
  that reached origin from elsewhere; a third of the manuscript's commits came that way.
- **Who decides is read from the team file**, never from memory. A co-author not on it is an author whose edits are
  input, whose word on a claim goes to the person.

## How work reaches it

The person asks for a pass (a section to write, a destination to fit, comments to answer); the pm hands it a change of
direction; a co-author's commit or comment arrives; the lead says a feature the paper describes changed.

## Grant

The person's words for the module repositories' seats, 2026-11-03, as `docs/seats/LEAD.md` takes them here: "All
pushes". For this seat: commit and push `main`, as a fast-forward, its own files: `docs/manuscript/` and its notes. It
outranks the role's "pushes only on the person's word", the repository's grant being nearer (the base). Not covered,
so the person's: a submission, a preprint post, a share outside the repository, a tag, a branch merged.

## Before a reset

The role's: the record current, every applied item committed; `docs/seats/WRITER_NOTES.md` rewritten to the present:
the pass in hand, the items open and deferred, the blind spots, the destination's state.
