"""Score a benchmark run. The command line is `scripts/bench_score.py`.

Deterministic: same inputs, same bytes out. Wraps `compare_modules`'
`_compare` rather than re-deriving a diff, so the score can never drift from
what the shipped tool says — a hand-rolled comparison is a second opinion
nobody asked for and it disagrees eventually.

**Engine, not a tool surface.** Nothing here is registered with the MCP server, so
its models live in this module rather than in `models.py` — the rule there is that
every *tool* returns a model from `models.py`, and `overrides.py` is the precedent
for a pydantic model at engine level. If a `bench_score` tool is ever added, its
return type moves to `models.py` and these become its inputs.

**Two modes, because two questions are being asked.** Scoring is
reference-relative and answers *did this run reproduce that one*. The census is
reference-free and answers *what does this run assert* — which is the only form
available to a paper that will never have a reference, and it is the shape the
corrected benchmark criterion needs: a source running no association test should
produce rows asserting no direction, and zero rows and sixty honest rows are both
passes. The census **reports and does not judge**: the expectation for a given
paper is a sentence in the round's results, never a threshold in here.

**Either mode locates the spec directory.** Benchmark runs put `module_spec.yaml`
at the run root, under `spec/`, or under `longevity_*/`, and all three satisfy the
ask that produced them. A script assuming one shape silently scores nothing, so a
path with no `module_spec.yaml` is searched beneath, and zero or several matches
is an error naming what it found rather than a guess.

Prints JSON to stdout. Two properties matter and both are deliberate:

- **Volatile columns are excluded by name, and the exclusions are printed**
  in the output rather than applied silently. `fetched_at` moves on every run
  by construction and `curator` names who did the work, so neither is evidence
  about agreement; anything else that gets excluded has to be argued for here.
- **Key agreement and cell agreement are reported separately.** A run that
  authors the right variants with the wrong values, and one that authors half
  the variants perfectly, are different failures, and one score cannot say
  which happened.

`unscored` is not a zero. A table nothing could be counted over is reported as
absent, never folded into the denominator as a miss — the same rule the tools
apply to a check that could not run. **Two different tables land there and only
one was handled**: a table present on one side, and an *unkeyed* one present on
both, whose rows cannot be paired because upstream's `hints.key_fields` gives it
the `overlap` rule rather than `equality`. The second raised `TypeError` on the
first binning module it met, because the filter asked about `presence` when the
question is whether anything was counted.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

from just_dna_compiler import hints

from just_module_creator.tools.comparison import _compare

#: Columns whose disagreement is not evidence about the run. `fetched_at` is a
#: wall-clock stamp; `curator` is the identity of whoever authored the row,
#: which differs between two runs by definition and says nothing about whether
#: they agreed on the genetics.
VOLATILE = ("fetched_at", "curator")

#: Columns the census counts. Every one is a cell that asserts something a source
#: must have *measured* — a direction, a significance verdict, an effect, a
#: clinical call, a weight — as against a cell that records what a source *says*.
#: This is a benchmark judgement about which claims are worth watching, not a
#: schema fact: the tables are read by header, so a column that does not exist in
#: a given CSV is simply absent from that CSV's census rather than reported as
#: empty.
ASSERTION_COLUMNS = (
    "direction",
    "stat_significance",
    "clin_sig",
    "effect_size",
    "p_value",
    "weight",
)

#: What an empty cell and the literal `unknown` have in common is that neither
#: asserts anything, and what separates them is whether the author said so. Both
#: are counted, and they are counted apart.
_WITHHELD = ("", "unknown")


def locate_spec(path: Path) -> Path:
    """The directory holding `module_spec.yaml`, at or beneath `path`."""
    if (path / "module_spec.yaml").is_file():
        return path
    found = sorted(p.parent for p in path.rglob("module_spec.yaml"))
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit(f"no module_spec.yaml at or beneath {path}")
    listed = ", ".join(str(f) for f in found)
    raise SystemExit(f"several spec directories beneath {path}: {listed}")


def census(run: Path) -> dict:
    """Count what a run's authored CSVs assert. Reference-free, report-only.

    Machine-written sidecars are skipped, because the question is what the *run*
    asserted and a fact pass's `p_value` is the source's claim rather than the
    author's. The roster is upstream's own `hints.DERIVED_TABLE_MODELS`, never a
    list here: a sidecar we did not know about would otherwise be counted as
    authored, which is the reading the census exists to avoid.
    """
    derived = set(hints.DERIVED_TABLE_MODELS)
    tables = []
    for path in sorted(run.glob("*.csv")):
        if path.name in derived:
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        header = rows[0].keys() if rows else []
        present = [c for c in ASSERTION_COLUMNS if c in header]
        if not present:
            continue
        columns = {}
        for column in present:
            values = Counter((r.get(column) or "").strip() for r in rows)
            columns[column] = {
                "values": dict(sorted(values.items())),
                "withheld": sum(values[v] for v in _WITHHELD),
                "asserted": sum(n for v, n in values.items() if v not in _WITHHELD),
            }
        tables.append({"csv": path.name, "rows": len(rows), "columns": columns})
    return {"run": str(run), "tables": tables}


def _score_table(table) -> dict:
    if table.unchanged is None:
        # One-sided, or otherwise uncounted upstream. Every count is `None` here
        # rather than `0`: the table was not compared, and a zero would read as a
        # comparison that found nothing.
        return {
            "csv": table.csv,
            "presence": table.presence,
            "rows_reference": table.rows_left,
            "rows_run": table.rows_right,
            "keys_shared": None,
            "keys_only_reference": table.removed,
            "keys_only_run": table.added,
            "key_jaccard": None,
            "rows_changed_any_column": None,
            "rows_changed_after_volatile_exclusions": None,
            "cell_agreement_over_shared_keys": None,
            "changed_groups": [],
        }
    # `changed` is a list of GROUPS, not rows — a row belongs to exactly one
    # group, so the shared-key count sums each group's rows. Counting groups
    # here made agreement exceed 1 and go negative on the first real input.
    changed_rows = sum(g.rows for g in table.changed)
    shared = table.unchanged + changed_rows
    union = shared + table.added + table.removed
    substantive = [
        {"columns": sorted(set(g.columns) - set(VOLATILE)), "rows": g.rows}
        for g in table.changed
        if set(g.columns) - set(VOLATILE)
    ]
    substantive_rows = sum(g["rows"] for g in substantive)
    return {
        "csv": table.csv,
        "presence": table.presence,
        "rows_reference": table.rows_left,
        "rows_run": table.rows_right,
        "keys_shared": shared,
        "keys_only_reference": table.removed,
        "keys_only_run": table.added,
        "key_jaccard": round(shared / union, 4) if union else None,
        "rows_changed_any_column": changed_rows,
        "rows_changed_after_volatile_exclusions": substantive_rows,
        "cell_agreement_over_shared_keys": (
            round(1 - substantive_rows / shared, 4) if shared else None
        ),
        "changed_groups": sorted(
            substantive, key=lambda g: (-g["rows"], ",".join(g["columns"]))
        ),
    }


def score(reference: Path, run: Path) -> dict:
    cmp = _compare(reference, run, max_groups=64, examples_per_group=0)
    tables = [_score_table(t) for t in cmp.tables]
    # Keyed on what was actually counted, never on `presence`. An **unkeyed** table
    # — the binning kinds, whose `hints.key_fields(...).rule` is `overlap` rather
    # than `equality` — is `presence="both"` with every count `None`, so filtering
    # on presence put a `None` into the totals and raised. The rule this file
    # already stated is the right one and it is now the one implemented: a table
    # that was not counted is unscored, whichever way it failed to be counted.
    scored = [t for t in tables if t["keys_shared"] is not None]
    unscored = [t["csv"] for t in tables if t["keys_shared"] is None]
    return {
        "reference": str(reference),
        "run": str(run),
        "frame": {
            "reference_build": cmp.frame.left_build,
            "run_build": cmp.frame.right_build,
            "verdict": cmp.frame.verdict,
        },
        "comparable": cmp.frame.verdict == "same",
        "content_signature_reference": cmp.left_content_signature,
        "content_signature_run": cmp.right_content_signature,
        "content_identical": cmp.content == "same",
        "volatile_columns_excluded": list(VOLATILE),
        "tables": sorted(tables, key=lambda t: t["csv"]),
        "totals": {
            "keys_shared": sum(t["keys_shared"] for t in scored),
            "keys_only_reference": sum(t["keys_only_reference"] for t in scored),
            "keys_only_run": sum(t["keys_only_run"] for t in scored),
            "rows_disagreeing": sum(
                t["rows_changed_after_volatile_exclusions"] for t in scored
            ),
        },
        "unscored_tables": sorted(unscored),
    }


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] == "--census":
        if len(args) < 2:
            sys.stderr.write(__doc__ or "")
            return 2
        out = [census(locate_spec(Path(a).resolve())) for a in args[1:]]
    else:
        if len(args) < 2:
            sys.stderr.write(__doc__ or "")
            return 2
        reference = locate_spec(Path(args[0]).resolve())
        out = [score(reference, locate_spec(Path(a).resolve())) for a in args[1:]]
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
