"""The retracing join (RM31 part 2, `docs/DESIGN-traceability.md` §4.4, §10, §11).

Reads a module's provenance ledger (`logs/trace/*.jsonl`, written by `tracehook`) and its authored
tables, and puts every row in one state. Pure and offline: it opens no socket and writes nothing.

**What it can say, and what it cannot.** Whether a recorded edit wrote a row, and, for a row in the
quote-bearing table, whether its citation holds together: the cited article came back from a
recorded search, was fetched, and the quote sits verbatim in that fetched text. It never says a
row is right, and it reads no basis for a judged cell (`weight`, `direction`, `conclusion`): a row
whose citation is `traced` may still carry a weight nothing recorded (the tester's read of the
hand trial, §10). The report says that scope in its own words.

**Three states, and unknown is not a pass.** `traced` is a complete chain. `contradicted` is
evidence against the row: a quote that is the article's own title or a piece of it, a quote not in
the text fetched for its citation, a quote found in another article. A citation no recorded search
returned is `not_traceable`, never `contradicted`: the ledger cannot see every route (F161).
`not_traceable` is no record, with the reason: a row written before the ledger, a hand edit between
sessions, a call whose result could not be read.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from just_module_creator.tracehook import _RSID, read_rows, row_sha256, title_sha256

#: The column a citation row names its paper by. Not generated: guarded by
#: `tests/test_trace.py::test_the_citation_column_is_the_formats`, against the format's own model.
CITATION_COLUMN = "pmid"
#: The column holding the passage located for a row's claim. The table that carries it is upstream's
#: (`hints.REDUNDANCY_BEARING_TABLES[QUOTE_COLUMN]`); the name is guarded by the same test.
QUOTE_COLUMN = "provenance_quote"

TRACED = "traced"
CONTRADICTED = "contradicted"
NOT_TRACEABLE = "not_traceable"


@dataclass(frozen=True)
class RowState:
    file: str
    line: int  # 1-based line in the CSV, header being line 1
    row_sha256: str
    written: str  # recorded | not_recorded | unknown
    citation: str | None  # None for a table with no citation column
    why: str


@dataclass
class Ledger:
    """Everything the ledger files establish, gathered once."""

    files: list[str] = field(default_factory=list)
    counts: Counter[str] = field(default_factory=Counter)
    unreadable_lines: int = 0
    searched: set[str] = field(default_factory=set)
    unread_searches: int = 0
    titles: dict[str, str] = field(default_factory=dict)  # id -> title sha256
    fetched: dict[str, set[str]] = field(default_factory=dict)  # pmid -> text sha256s
    unread_fetches: set[str] = field(default_factory=set)  # pmids asked, result unreadable
    written: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # row sha -> anchors
    blind_files: set[str] = field(default_factory=set)  # edited with no before-copy
    decisions: list[dict[str, Any]] = field(default_factory=list)


def read_ledger(spec_dir: Path) -> Ledger:
    ledger = Ledger()
    trace_dir = spec_dir / "logs" / "trace"
    for path in sorted(trace_dir.glob("*.jsonl")) if trace_dir.is_dir() else []:
        ledger.files.append(path.name)
        for line in path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                ledger.unreadable_lines += 1
                continue
            _take(ledger, event)
    return ledger


def _take(ledger: Ledger, event: dict[str, Any]) -> None:
    kind = event.get("kind")
    ledger.counts[str(kind)] += 1
    unread = "result" in event and event["result"] is None
    if kind == "search":
        if unread:
            ledger.unread_searches += 1
            return
        ledger.searched.update(str(i) for i in event.get("returned") or [] if i)
        ledger.titles.update(event.get("titles") or {})
    elif kind == "fetch":
        pmid = str((event.get("asked") or {}).get("pmid") or event.get("pmid") or "")
        if unread:
            if pmid:
                ledger.unread_fetches.add(pmid)
            return
        if pmid and event.get("sha256"):
            ledger.fetched.setdefault(pmid, set()).add(event["sha256"])
    elif kind == "decision":
        ledger.decisions.append(event)
    elif kind == "edit":
        if "added" not in event:
            ledger.blind_files.add(str(event.get("file")))
            return
        for added in event.get("added") or []:
            ledger.written[added["row_sha256"]] = added.get("anchors") or []


def citation_state(
    row: dict[str, str], anchors: list[dict[str, Any]], ledger: Ledger
) -> tuple[str, str]:
    """One recorded row of the quote-bearing table: does its citation hold together?"""
    pmid = (row.get(CITATION_COLUMN) or "").strip()
    quote = (row.get(QUOTE_COLUMN) or "").strip()
    if quote and pmid in ledger.titles and title_sha256(quote) == ledger.titles[pmid]:
        return CONTRADICTED, "the quote is the cited article's own title"
    if not pmid:
        return NOT_TRACEABLE, "the row cites no PMID"
    if any(a.get("column") == QUOTE_COLUMN and a.get("title_of") == pmid for a in anchors):
        return CONTRADICTED, "the quote is a piece of the cited article's own title"
    if pmid not in ledger.searched:
        # Never `contradicted`: a route the ledger cannot see (a drafter, a lookup, a paper the
        # author handed over) is an unknown, not evidence against the row (F161).
        unread = (
            f"; {ledger.unread_searches} search result(s) could not be read"
            if ledger.unread_searches
            else ""
        )
        return NOT_TRACEABLE, (
            f"no recorded search or citation list returned PMID {pmid}: recalled, or found by a "
            f"route the ledger does not see{unread}"
        )
    texts = ledger.fetched.get(pmid, set())
    if not quote:
        if texts:
            return NOT_TRACEABLE, "searched and fetched, but there is no quote to anchor the claim"
        return NOT_TRACEABLE, "searched, but no quote and no fetch of the article"
    placed = [a for a in anchors if a.get("column") == QUOTE_COLUMN and "sha256" in a]
    if any(a.get("sha256") in texts for a in placed):
        return TRACED, f"search, then fetch of PMID {pmid}, then the quote at its offset"
    if placed:
        return CONTRADICTED, "the quote sits in a fetched article other than the one cited"
    if texts:
        return CONTRADICTED, f"the quote is not in the text fetched for PMID {pmid}"
    if pmid in ledger.unread_fetches:
        return (
            NOT_TRACEABLE,
            f"the fetch of PMID {pmid} was recorded but its text could not be read",
        )
    return NOT_TRACEABLE, f"PMID {pmid} was searched but never fetched in a recorded session"


def trace(spec_dir: Path, tables: list[str], quote_tables: frozenset[str]) -> list[RowState]:
    """Every authored row of `tables`, in file order, with its state."""
    ledger = read_ledger(spec_dir)
    return trace_with(spec_dir, tables, quote_tables, ledger)


def trace_with(
    spec_dir: Path, tables: list[str], quote_tables: frozenset[str], ledger: Ledger
) -> list[RowState]:
    states: list[RowState] = []
    for name in tables:
        path = spec_dir / name
        if not path.is_file():
            continue
        rows = read_rows(path.read_text("utf-8"))
        quoted = name in quote_tables and bool(rows) and CITATION_COLUMN in rows[0]
        for index, row in enumerate(rows, start=2):
            digest = row_sha256(row)
            if digest in ledger.written:
                written = "recorded"
            elif name in ledger.blind_files:
                written = "unknown"
            else:
                written = "not_recorded"
            if not quoted:
                citation, why = (
                    None,
                    (
                        "written in a recorded session"
                        if written == "recorded"
                        else "no recorded edit wrote this row"
                    ),
                )
            elif written != "recorded":
                citation = NOT_TRACEABLE
                why = (
                    "an edit to this file was recorded without its before-copy"
                    if written == "unknown"
                    else "no recorded edit wrote this row: written before the ledger, or by hand"
                )
            else:
                citation, why = citation_state(row, ledger.written[digest], ledger)
            states.append(RowState(name, index, digest, written, citation, why))
    return states


@dataclass(frozen=True)
class DecisionState:
    subject: str
    verdict: str
    by: str
    witness: str  # anchored | declared | recalled
    why: str
    because: str
    passages: list[dict[str, Any]] = field(default_factory=list)  # pmid, sha256, offset, len


def _never_checked(event: dict[str, Any], tied: list[str]) -> list[str]:
    """Variants the decision names that its recorded `unnamed` was never computed against.

    The hook records `tied` beside `unnamed` since both covered the subject and the reason; an
    older event's `unnamed` covered the reason alone. Empty for any event that records `tied`.
    """
    if "tied" in event:
        return []
    from_reason = {r.lower() for r in _RSID.findall(str(event.get("why") or ""))}
    return sorted(set(tied) - from_reason)


def decision_states(ledger: Ledger) -> list[DecisionState]:
    """How each stated decision's reason is known. Never whether the reason holds.

    `anchored` means: a passage sits verbatim in a text fetched that session, is not cut from a
    title, and names every variant the subject or reason names, of which there is at least one.
    It does NOT mean the passage supports the reason: a passage can name the right variant and
    say the opposite (F162, case B), and only a reader settles that, so each anchored decision
    carries `passages` (PMID, offset, length) to read it at. A reason that names no variant has
    nothing tying it to a passage and reads `declared` (F162, case C). The rsID test is the
    tester's hand-trial finding: an LD reason about rs1421085 anchored to a paper that never
    names rs1421085.
    """
    by_sha = {sha: pmid for pmid, shas in ledger.fetched.items() for sha in shas}
    states: list[DecisionState] = []
    for event in ledger.decisions:
        basis = str(event.get("basis") or "")
        anchors = event.get("anchors")
        placed = [a for a in anchors or [] if "sha256" in a]
        from_title = [a for a in anchors or [] if "title_of" in a]
        unnamed = event.get("unnamed") or []
        # Derived here from the event's own words, not read from the hook's `tied`, so the rule
        # lives in one place and a ledger written before that field existed reads the same.
        tied = sorted(
            {
                r.lower()
                for r in _RSID.findall(f"{event.get('subject') or ''} {event.get('why') or ''}")
            }
        )
        passages: list[dict[str, Any]] = []
        if basis == "recalled":
            witness, because = "recalled", "stated as recalled from knowledge, not read"
        elif anchors is None:
            witness, because = "declared", "no passage was given for the reason"
        elif from_title:
            witness, because = "declared", "the passage is a piece of an article's title"
        elif not placed:
            witness, because = "declared", "the passage is in no text fetched that session"
        elif not tied:
            witness = "declared"
            because = "the reason names no variant, so nothing ties the passage to it"
        elif unnamed:
            witness = "declared"
            because = f"the passage never names {', '.join(unnamed)}, which the reason relies on"
        elif unchecked := _never_checked(event, tied):
            # F163: a hook before `tied` checked the passage against the reason's variants only,
            # so a variant named in the subject alone was never looked for. Unknown, not anchored.
            witness = "declared"
            because = (
                f"the passage was never checked for {', '.join(unchecked)}: the ledger predates "
                "that check"
            )
        else:
            witness = "anchored"
            because = (
                "the passage sits in a fetched text and names the reason's variants; whether it "
                "supports the reason is for a reader, at `passages`"
            )
            passages = [
                {
                    "pmid": by_sha.get(a["sha256"]),
                    "sha256": a["sha256"],
                    "offset": a.get("offset"),
                    "len": a.get("len"),
                }
                for a in placed
            ]
        states.append(
            DecisionState(
                subject=str(event.get("subject") or ""),
                verdict=str(event.get("verdict") or ""),
                by=str(event.get("by") or "agent"),
                witness=witness,
                why=str(event.get("why") or ""),
                because=because,
                passages=passages,
            )
        )
    return states
