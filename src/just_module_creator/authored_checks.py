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
import re
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


# --------------------------------------------------------------------------- #
# The conclusion, against the row it sits on — `RM27`
# --------------------------------------------------------------------------- #
_CONCLUSION = "conclusion"
_RSID = "rsid"
_GENOTYPE = "genotype"
_STATE = "state"
_WEIGHT = "weight"

#: Only single-base alleles build a genotype token. An indel spelled `-`, `del` or
#: `CTT` is left out deliberately: the token forms below are two characters, and a
#: multi-base allele would put arbitrary substrings of the prose in scope.
_BASES = frozenset("ACGT")

#: How many examples a table-wide finding carries before it stops listing them.
#: One module in the measured corpus produced 480 groups of the second kind; a
#: finding per group is the one-per-row spam that aggregation exists to prevent.
_EXAMPLES = 5


def _alleles(cell: str | None) -> tuple[str, ...] | None:
    """A genotype cell as a sorted allele pair, or `None` when it is not one.

    `None` rather than an empty tuple, and the difference is load-bearing: a cell this
    cannot read is a row the check has no opinion about, never a row that passed.
    Handles the three spellings that reach `variants.csv` — `A/G`, `A|G` and `AG` —
    and refuses everything else, including star alleles and indels.
    """
    text = (cell or "").strip().upper()
    if not text:
        return None
    if "/" in text or "|" in text:
        parts = [part.strip() for part in re.split(r"[/|]", text)]
    elif len(text) == 2:
        parts = [text[0], text[1]]
    else:
        return None
    if not parts or not all(len(part) == 1 and part in _BASES for part in parts):
        return None
    return tuple(sorted(parts))


def _locus_alleles(rows: Sequence[Mapping[str, str | None]]) -> set[str]:
    """Every single base seen at one rsID — from the genotypes, `ref` and `alts`.

    **This set is the whole reason the check is usable.** An earlier version of the
    rule looked for any two-letter genotype-shaped token and flagged `TG` inside
    "raised plasma triglyceride (TG) levels". Requiring the token to be built from
    alleles that occur at *this* site excludes that by construction rather than by a
    stop-list, which is what makes the rule survive prose nobody anticipated.
    """
    found: set[str] = set()
    for row in rows:
        pair = _alleles(row.get(_GENOTYPE))
        if pair:
            found.update(pair)
        for column in ("ref", "alts"):
            for value in (row.get(column) or "").upper().split(","):
                base = value.strip()
                if len(base) == 1 and base in _BASES:
                    found.add(base)
    return found


def _token_pattern(alleles: set[str]) -> tuple[re.Pattern[str], dict[str, tuple[str, ...]]] | None:
    """A matcher for the bare two-letter genotype tokens this locus can build.

    **The slashed spelling is deliberately NOT matched, and it is the one the column
    itself uses, so the omission needs its reason stated.** In a conclusion, `C/A`
    overwhelmingly names *the SNP's two alleles* rather than somebody's genotype —
    "rs2943634 C/A single nucleotide polymorphism", "Two SNPs, rs1042718 (C/A) and
    rs1042719 (G/C)". Matching it added four findings across the measured corpus and
    **all four were that sentence**, on rows whose prose was otherwise correct. A
    doubled bare letter carries no such second reading: `AA-carriers` is a claim about
    a genotype or it is nothing.

    Checked rather than assumed: with the slashed forms in, this rule returns 24 over
    the six modules; without them, 20 — which is the count whose precision was
    measured by hand.
    """
    if len(alleles) < 2:
        return None
    spellings: dict[str, tuple[str, ...]] = {
        f"{first}{second}": tuple(sorted((first, second)))
        for first in sorted(alleles)
        for second in sorted(alleles)
    }
    return (
        re.compile(r"\b(?:" + "|".join(re.escape(t) for t in sorted(spellings)) + r")\b"),
        spellings,
    )


def conclusion_genotype_findings(
    rows: Sequence[Mapping[str, str | None]],
) -> list[LintFinding]:
    """Report conclusions that name a genotype other than the row's own.

    `conclusion` is the sentence a person reads about themselves and it is
    `required: true`, yet nothing in the toolchain compares it against the cells it
    sits beside. Measured over 1,418 rows in six real modules, this rule found 20
    rows; about twelve are real and six of those are severe — one module has the
    `C/C` and `A/A` conclusions swapped at a locus where all three rows read
    `state: neutral, weight: 0.0`, and another scores `T/T` as `protective, +1.2`
    under text saying `GG` is protective.

    **`warning`, never `error`, and the measurement is the reason.** Precision is
    roughly 60%: the rest are legitimate comparative or quoted prose, an abstract
    excerpt reading `HR (MnSOD(CC/CT)) = 0.91` among them. A rule that is right six
    times in ten belongs in front of a reviewer, not in front of a compile.

    Aggregated per rsID, because a locus with the pair swapped produces one decision
    and not one per row.
    """
    by_rsid: dict[str, list[Mapping[str, str | None]]] = defaultdict(list)
    for row in rows:
        rsid = (row.get(_RSID) or "").strip()
        if rsid:
            by_rsid[rsid].append(row)

    findings: list[LintFinding] = []
    for rsid in sorted(by_rsid):
        group = by_rsid[rsid]
        built = _token_pattern(_locus_alleles(group))
        if built is None:
            continue
        pattern, spellings = built
        named: list[str] = []
        for row in group:
            own = _alleles(row.get(_GENOTYPE))
            conclusion = (row.get(_CONCLUSION) or "").strip()
            if own is None or not conclusion:
                continue
            others = sorted(
                {token for token in pattern.findall(conclusion) if spellings[token] != own}
            )
            if others:
                named.append(f"{row.get(_GENOTYPE)} names {', '.join(others)}")
        if named:
            findings.append(
                LintFinding(
                    column=_CONCLUSION,
                    level="warning",
                    source=OURS,
                    message=(
                        f"{rsid}: {len(named)} conclusion(s) name a genotype other than the "
                        f"row's own — {'; '.join(named)}. Both readings are live: the prose may "
                        "be comparative or quoting an abstract, or the conclusions may be "
                        "attached to the wrong genotypes, which is a person reading the "
                        "opposite of their own result. Check which, then leave it or swap it."
                    ),
                )
            )
    return findings


def shared_conclusion_findings(
    rows: Sequence[Mapping[str, str | None]],
) -> list[LintFinding]:
    """Report one conclusion shared by genotypes that score differently.

    **A question rather than a defect, which is why it is `info`.** A heterozygote
    and a homozygote sharing one association sentence and differing only in dose is
    arguably right for a GWAS port — 480 of the 492 groups measured across six
    modules are exactly that, in one module. The point is that nobody is asked: a
    reader with `C/T` and a reader with `T/T` see identical prose and different
    numbers, and nothing in the module records whether that was intended.

    One finding for the table, with examples, because per-group would be 480 of them.
    """
    grouped: dict[tuple[str, str], list[Mapping[str, str | None]]] = defaultdict(list)
    for row in rows:
        rsid = (row.get(_RSID) or "").strip()
        conclusion = (row.get(_CONCLUSION) or "").strip()
        if rsid and conclusion:
            grouped[(rsid, conclusion)].append(row)

    shared: list[str] = []
    for key in sorted(grouped):
        group = grouped[key]
        genotypes = {(row.get(_GENOTYPE) or "").strip() for row in group}
        scores = {
            ((row.get(_STATE) or "").strip(), (row.get(_WEIGHT) or "").strip()) for row in group
        }
        if len(genotypes) > 1 and len(scores) > 1:
            shared.append(f"{key[0]} ({', '.join(sorted(genotypes))})")
    if not shared:
        return []
    listed = ", ".join(shared[:_EXAMPLES])
    tail = f", and {len(shared) - _EXAMPLES} more" if len(shared) > _EXAMPLES else ""
    return [
        LintFinding(
            column=_CONCLUSION,
            level="info",
            source=OURS,
            message=(
                f"{len(shared)} rsID(s) carry one conclusion across genotypes that score "
                f"differently: {listed}{tail}. This is a question, not a defect — one "
                "association sentence over a heterozygote and a homozygote is reasonable when "
                "only the dose differs. Nothing records that you decided it, so decide it: "
                "either write per-genotype prose, or say in `weighting:` that the dose is what "
                "the numbers carry."
            ),
        )
    ]


def _rows_from_text(csv_text: str) -> list[dict[str, str | None]]:
    return list(csv.DictReader(io.StringIO(csv_text)))


def findings_for_csv_text(csv_name: str, csv_text: str) -> list[LintFinding]:
    """Our own findings for one authored table, given its text. Reads no file."""
    rows = _rows_from_text(csv_text)
    if csv_name == "studies.csv":
        return repeated_quote_findings(rows)
    if csv_name == "variants.csv":
        return conclusion_genotype_findings(rows) + shared_conclusion_findings(rows)
    return []


def findings_for_spec_dir(spec_dir: Path) -> list[LintFinding]:
    """Our own findings for a spec directory. Reads the authored files only.

    `studies.csv` is an authored table, so it has exactly one legal name in one
    legal place and there is no `derived/` spelling to consider. Deliberately does
    **not** read `literature.csv`: its counters are stale on every module that has
    this problem, which is what `F49` measured.
    """
    findings: list[LintFinding] = []
    for name in ("studies.csv", "variants.csv"):
        path = spec_dir / name
        if path.is_file():
            findings += findings_for_csv_text(name, path.read_text(encoding="utf-8"))
    return findings


def count_levels(findings: Iterable[LintFinding], level: str) -> int:
    return sum(1 for f in findings if f.level == level)
