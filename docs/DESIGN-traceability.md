# Row-level traceability for agent-authored modules

**Status:** designed 2026-10-05, nothing built yet. The work item is `RM31` in
[ROADMAP.md](ROADMAP.md). The one upstream dependency, which file types `logs/` may carry, is filed as
format-tree `S125` and tracked here as `F116` in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).

This document is the reasoning and the decisions behind `RM31`, written out as prose. The roadmap entry
says what to build; this says why it looks the way it does.

---

## Condensed summary

just-module-creator lets an AI agent co-author genetic annotation modules with a person: it searches
the literature, reads articles, and writes the rows that say which variant is linked to which trait,
on what evidence. A finished module today records *which* paper backs each row and the passage quoted
from it, but not *how* the paper was found, what else was read and set aside, or why. We are adding a
traceability ledger that closes that gap without asking anyone to keep notes. The server and a
lightweight host hook record each search, each article retrieved (by content hash, never the text),
each edit to the module's tables, and each decision the human author confirmed. The ledger is
structured, versioned, and travels inside the published module. At review time, every row is joined
back to its evidence and classified as traced, contradicted (for example, a quote that does not occur
in the article it cites), or not traceable. An independent reviewer agent then flags rows whose stated
reasoning does not support them, or that have no supporting chain at all. The result is a module whose
evidence can be audited row by row, at a cost to the author that is close to zero.

---

## 1. The problem

A module is a set of authored tables. Each row in `variants.csv` says what a genotype means, and each
row in `studies.csv` names the paper behind it, the passage that supports it (`provenance_quote`) and
who located that passage (`curator`). That is the end of the chain. The steps before it are not kept:
which search found the paper, which other papers came back and were rejected, and on what grounds.

When a human curator built a database, recording those steps was a lab journal written by hand, and it
cost roughly as much again as the curation itself. So it mostly was not done, and database formats grew
up without a place for it. For an agent the cost has reversed. Every step already passes through a tool
call, so recording it is nearly free. What is missing is somewhere to put the record and something to
read it.

## 2. Why a transcript is not the answer

An earlier pipeline built on Agno solved this by dumping every step: every message and every tool call
went into a log. That worked because the pipeline owned the whole loop. It does not carry over here, for
three reasons.

First, the plugin does not own the loop. It runs inside a host (Claude Code or Codex) beside other tool
servers. The agent may read a paper through a different server, fetch a page with the host's own web
tool, or rely on a PDF the author dropped into the folder, and none of that passes through us. A person
may also edit the tables by hand between sessions.

Second, a transcript is the wrong kind of record. It is unstructured, so nothing can query it. It also
carries things nobody means to publish: system prompts, local file paths, very long lines. One real
transcript from that earlier pipeline, measured in RM25, carried all three.

Third, logs here are published. Anything placed under a module's `logs/` folder is swept into the
compiled artifact and uploaded with it, and a published version is permanent.

## 3. The shift: record evidence, not process

Instead of recording what the agent did, the design records what the agent was shown and what it
changed, and reconstructs the link between the two afterwards.

A search returned these article IDs. This article's text, with this hash, was retrieved. This row was
written. This passage in the row sits at this offset in that text. None of these facts depend on the
agent describing its own work, and each one can be checked. The step in the middle, where the agent read
the article and decided it supports the row, remains a judgement. The ledger cannot witness it, but it
can anchor both ends of it.

## 4. Design

### 4.1 The ledger

The ledger is a set of append-only files under the module's `logs/trace/` folder, one per working
session, so two sessions, two machines or two authors never write to the same file. Each line is one JSON
object carrying a format version, which lets the format change while old published modules keep their
old records. Paths are relative to the module folder and never absolute.

A few illustrative lines:

```
{"v":1,"t":"2026-10-05T14:02:11Z","kind":"search","via":"literature_search","query":"FTO BMI GWAS","returned":["20935630","17434869"]}
{"v":1,"t":"2026-10-05T14:03:40Z","kind":"fetch","via":"fetch_fulltext","pmid":"20935630","sha256":"9f1c…","chars":84213}
{"v":1,"t":"2026-10-05T14:09:02Z","kind":"decision","by":"agent:<model id>","subject":"pmid:17434869","verdict":"not_used","why":"cohort overlaps 20935630","anchors":[{"sha256":"…","offset":2210,"len":96}]}
{"v":1,"t":"2026-10-05T14:11:30Z","kind":"decision","by":"author","wording":"paraphrase","approved_at":"2026-10-05T14:11:52Z","text":"Author decided to keep only European-ancestry effect sizes."}
{"v":1,"t":"2026-10-05T14:15:07Z","kind":"edit","file":"studies.csv","key":{"rsid":"rs9939609","pmid":"20935630"}}
```

Article text is never stored, only its hash, its length and offsets into it. That keeps the ledger small
and keeps copyrighted text out of a published file.

### 4.2 Witnessing by a host hook

Our own tools can record what passes through them, but most of the chain does not. So capture moves to a
hook in the host that runs after every tool call. It records an allowlist of tool kinds: literature
searches and article retrieval (ours and other servers'), web fetches, edits to files in a module folder,
and questions put to the author together with their answers. It records metadata only: queries, the IDs
that came back, hashes, the row keys an edit touched. It never records fetched text and never the
conversation.

A session that never touches a module leaves nothing behind. Calls are held in a buffer outside the
module until the session writes into a module folder or calls one of our tools on one, and only then are
they written to that module's ledger. Before anything is written, a post-processing step drops what is
sensitive. The existing pre-publish log check already reads every `*.log` under `logs/`, so it covers
the trace files too, as long as they keep that name.

### 4.3 Decisions come from tools, not from reminders

A skill can tell an agent to note down each decision, and an agent will forget some of them. So the
design avoids asking. The author's decisions are captured from the question tool the agent already uses
to ask them, and from the arguments of tools that already take a decision as input: pruning rows,
recording an override of a source, answering an audit item. A paper read and set aside goes through one
tool that records the paper, the verdict and the reason in the ledger.

An author's decision is written as a short paraphrase in English ("Author decided to …") and only after
the author approves the wording. That approval is a step inside a tool the agent runs anyway at the end of
the work, not a reminder in a skill.

What an agent does forget is not prevented, it is caught: the review step in 4.4 reports any row with no
chain behind it.

### 4.4 Retracing

At review time, every authored row is joined back to the ledger and placed in one of three states.

- **Traced:** a complete chain exists, from a search through a retrieved article to a passage that
  occurs in it.
- **Contradicted:** the evidence argues against the row. The cited article never appeared in any search,
  the quoted passage is not in the retrieved text, or the "quote" is the article's title.
- **Not traceable:** there is no record, and the reason is stated. The source may have been a PDF the
  author supplied, a person's own knowledge, or a row written before the ledger existed. This is an
  unknown, not a failure.

Every link in a chain is labelled by how it is known: witnessed (a tool saw it), computed (the join
established it), or declared (an agent or person said so). A query tool reads one row's chain back.

This check never declares a row correct. It says how a row came to exist and whether its stated evidence
holds together, which is a different and narrower claim.

### 4.5 An independent reviewer

The join cannot judge reasoning. So a reviewer agent, started on a fresh context and never the same agent
that wrote the rows, reads the module together with its ledger. It reports two things: rows whose stated
reasoning does not support what the row claims, and rows that appeared from nowhere, with no search, no
retrieval and no recorded decision behind them. Its output is a list of questions for the author, not a
verdict, because a row with no recorded chain may still be right.

## 5. Rules the design keeps

- **Witnessed and narrated are different records.** What a tool saw is evidence. What an agent says about
  why it decided is self-report, and may have been written after the fact. Both are kept and labelled,
  and only the first ever feeds a classification.
- **Unknown is not a pass.** A row with no record is "not traceable", never "fine".
- **A check that could not have failed measured nothing.** Classification is built so that each state can
  actually be reached by a real module; a title used as a quote, for instance, is caught rather than
  counted as a match.
- **The human author stays responsible.** Recording which steps an agent took describes the division of
  labour honestly. It does not move accountability for the module away from the person who publishes it.

## 6. Relationship with the format

just-module-creator owns no schema. The module format, the compiler that builds the artifact and the
registry that publishes it belong to the upstream just-dna packages. Two consequences shaped the design.

**Where the record lives.** Upstream had already answered a narrower version of this question (their
S82 and RM147): a paper that was read and produced no row should be recorded as an uncited row in
`literature.csv`, and nobody should build a `logs/` writer for it, since a log is unstructured and cannot
be queried. That is the right answer for a format library, which cannot standardise a structure nobody
has built yet. For an authoring tool it is too lossy. That row records that a paper was read and that no
row came of it, and drops the reasoning between the two. It is also a row written by hand into a table
the format otherwise treats as machine-produced. A record stays unstructured only until somebody builds
the writer, and building it is authoring workflow, which is this project's layer. So the ledger is built
here first. Once it exists and works, upstream can decide whether any part of it deserves a typed home in
the format.

**Which files travel.** The compiler currently carries only files named `*.log` from `logs/` into the
published artifact. Tested on a real module, a `.jsonl`, `.json`, `.md`, `.txt` or image file placed
beside one compiled without a warning and was silently left out. We asked upstream (`S125`) to decide by
content rather than by file name, with cheap checks (valid UTF-8 for text, a successful parse for JSON and
for each line of JSON Lines), or at least to warn about what it leaves behind. Until they answer, ledger
files are named `*.log` and contain JSON Lines.

## 7. Decisions taken

All on 2026-10-05, by the project owner.

1. **Build the ledger here rather than wait for a format.** *"It remains unstructured and unqueryable
   until somebody makes it; it's not a theoretical limitation, rather a format constraint and layer
   problem."* Upstream's advice against a log writer is right for their layer and was not theirs to give
   for ours.
2. **The ledger lives in the module, as files under `logs/`**, so it travels with the module to the
   registry and to the next author. A record kept only on the author's machine was considered and
   rejected for that reason.
3. **Capture is by host hook, always on, with a notice**, rather than a question put to the author for
   each module. The hook's post-processing decides what to drop as sensitive.
4. **An author's decisions are recorded as an English paraphrase, after approval.** Nothing about the
   author is written that they have not seen.
5. **Tooling over journaling.** *"Journaling in skills should be minimized and substituted by tooling
   where possible. LLMs forget stuff."* Capture happens in a hook or a tool argument, and an omission is
   caught by the review step rather than prevented by instructions.
6. **A rejected paper goes to the ledger only.** No row is written into `literature.csv` on its behalf;
   whether ledger entries deserve a table of their own is for upstream to decide once the ledger exists.
7. **Ask upstream for wider file types in `logs/`** (`S125`), and meanwhile name ledger files `*.log`.

## 8. What this enables, and what it does not

It makes several existing rules checkable for the first time. The rule that every cited article must come
from a literature search becomes something a tool can verify instead of something an agent is asked to
honour. A title passed off as a quote, a pattern found on thousands of rows in previously published
modules, is caught by the join. A reviewer, human or agent, can see for each row whether there is a chain
behind it and spend their attention on the rows where there is not. Re-running the recorded searches later
and comparing the results shows when the literature has moved under a module.

It does not make a module correct. A fully traced row can still rest on a weak paper or a misreading. It
also cannot see reasoning that never passed through a tool, and it does not reach work done before the
ledger existed. Those rows are reported as not traceable, which is honest, and is the point at which a
human reviewer is most useful.

## 9. Status and next steps

Nothing is built yet. In order:

1. The host hook and the ledger writer, in both plugin manifests (about one day).
2. The retracing join, its three-state classification in the module audit, and the per-row query (about
   one day).
3. The independent reviewer pass and the tool for recording a rejected paper (about one day).

The work closes when a real module authored end to end under the hook can be retraced row by row, the
reviewer flags the rows it cannot trace, and upstream has answered `S125`.
