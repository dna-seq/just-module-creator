"""Findings this layer computes itself, over authored tables.

Everything else in this package transports what upstream said. This module is the
exception and it is deliberate: `RM17` established that nothing anywhere in the
toolchain can see the defect that put 3668 article titles into published
`provenance_quote` cells, and waiting for the compiler to grow the check would
leave the modules that motivated it unexamined either way.

**The layer distinction is preserved rather than blurred.** Upstream's own strings
stay in `errors` / `warnings` / `info` exactly as they arrived; anything computed
here is a :class:`LintFinding` carrying ``source="just-module-creator"``, so a
caller can always tell which layer spoke. See `RM17` for the three shapes that
were on the table and why this one was chosen.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from just_module_creator.models import LintFinding

OURS = "just-module-creator"

#: Rows carrying fewer than this many quotes for one PMID say nothing either way:
#: a module that cites a paper once, or twice, has no shape to detect.
_MIN_QUOTED_ROWS = 2

_QUOTE = "provenance_quote"
_PMID = "pmid"


def _preview(quote: str, words: int = 6) -> str:
    parts = quote.split()
    head = " ".join(parts[:words])
    return f"{head}…" if len(parts) > words else head


def repeated_quote_findings(rows: Sequence[Mapping[str, str | None]]) -> list[LintFinding]:
    """Report each PMID whose every quoted row carries the *same* passage.

    A `provenance_quote` locates one row's claim in the cited article. Different
    rows cite one paper for different findings, so a real passage varies with the
    claim. **One identical string across every quoted row citing a PMID is the
    signature of a quote that was never located** — the measured case is the
    article's own title, which occurs in its own fulltext and therefore satisfies
    `quotes_found` every time.

    The check is on the **shape, not the string**: it never compares against the
    title, because the next variant of this is one real sentence pasted onto two
    thousand rows. Confirming that the repeated string *is* the title needs
    `lookup_citation`, which is a network call and belongs where a round trip is
    already being paid for.

    Aggregated per PMID with a row count, never one finding per row. Rows with an
    empty quote are not counted: a paper quoted on one row of five is a module with
    one quote, not a module with a repeated one.
    """
    quoted: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        pmid = (row.get(_PMID) or "").strip()
        quote = (row.get(_QUOTE) or "").strip()
        if pmid and quote:
            quoted[pmid].append(quote)

    findings: list[LintFinding] = []
    for pmid in sorted(quoted):
        quotes = quoted[pmid]
        if len(quotes) < _MIN_QUOTED_ROWS or len(set(quotes)) != 1:
            continue
        findings.append(
            LintFinding(
                column=_QUOTE,
                level="warning",
                source=OURS,
                message=(
                    f"pmid {pmid}: all {len(quotes)} quoted row(s) carry the same passage "
                    f'("{_preview(quotes[0])}"). A quote locates one row\'s claim, so rows citing '
                    "one paper for different findings should not share one string — and a passage "
                    "that is the article's title satisfies quotes_found without witnessing "
                    "anything. Quote verbatim for each row's own claim, or leave the cell empty."
                ),
            )
        )
    return findings


def _rows_from_text(csv_text: str) -> list[dict[str, str | None]]:
    return list(csv.DictReader(io.StringIO(csv_text)))


def findings_for_csv_text(csv_name: str, csv_text: str) -> list[LintFinding]:
    """Our own findings for one authored table, given its text. Reads no file."""
    if csv_name != "studies.csv":
        return []
    return repeated_quote_findings(_rows_from_text(csv_text))


def findings_for_spec_dir(spec_dir: Path) -> list[LintFinding]:
    """Our own findings for a spec directory. Reads the authored files only.

    `studies.csv` is an authored table, so it has exactly one legal name in one
    legal place and there is no `derived/` spelling to consider. Deliberately does
    **not** read `literature.csv`: its counters are stale on every module that has
    this problem, which is what `F49` measured.
    """
    studies = spec_dir / "studies.csv"
    if not studies.is_file():
        return []
    return repeated_quote_findings(_rows_from_text(studies.read_text(encoding="utf-8")))


def count_levels(findings: Iterable[LintFinding], level: str) -> int:
    return sum(1 for f in findings if f.level == level)
