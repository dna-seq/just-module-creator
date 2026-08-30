"""Score a benchmark run against the adjudicated reference module.

Deterministic: same inputs, same bytes out. Wraps `compare_modules`'
`_compare` rather than re-deriving a diff, so the score can never drift from
what the shipped tool says — a hand-rolled comparison is a second opinion
nobody asked for and it disagrees eventually.

    uv run python scripts/bench_score.py REFERENCE_SPEC RUN_SPEC [RUN_SPEC ...]

Prints JSON to stdout. Two properties matter and both are deliberate:

- **Volatile columns are excluded by name, and the exclusions are printed**
  in the output rather than applied silently. `fetched_at` moves on every run
  by construction and `curator` names who did the work, so neither is evidence
  about agreement; anything else that gets excluded has to be argued for here.
- **Key agreement and cell agreement are reported separately.** A run that
  authors the right variants with the wrong values, and one that authors half
  the variants perfectly, are different failures, and one score cannot say
  which happened.

`unscored` is not a zero. A table absent from one side is reported as absent,
never folded into the denominator as a miss — the same rule the tools apply to
a check that could not run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from just_module_creator.tools.comparison import _compare

#: Columns whose disagreement is not evidence about the run. `fetched_at` is a
#: wall-clock stamp; `curator` is the identity of whoever authored the row,
#: which differs between two runs by definition and says nothing about whether
#: they agreed on the genetics.
VOLATILE = ("fetched_at", "curator")


def _score_table(table) -> dict:
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
    scored = [t for t in tables if t["presence"] == "both"]
    unscored = [t["csv"] for t in tables if t["presence"] != "both"]
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
    if len(argv) < 3:
        sys.stderr.write(__doc__ or "")
        return 2
    reference = Path(argv[1]).resolve()
    out = [score(reference, Path(a).resolve()) for a in argv[2:]]
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
