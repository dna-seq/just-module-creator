"""The reference-free measurement: what does a run assert, and what does it withhold.

Three ways a watched column can fail to produce a number, and they are three
different facts. All three occur in the tracked corpus, which is why the assertions
below are against real modules rather than a fixture written to agree with them.
Every expected count is computed from the CSV here, never pasted — a count read off
a dump is a test agreeing with whatever the code did last.
"""

from __future__ import annotations

import collections
import csv
import shutil
from pathlib import Path

from just_dna_compiler import hints
from just_dna_format.spec import VariantRow

from just_module_creator.bench import ASSERTION_COLUMNS, census

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _table(report, name: str):
    return next(t for t in report.tables if t.csv == name)


def _column(table, name: str):
    return next(c for c in table.columns if c.column == name)


def test_a_column_absent_from_the_header_is_not_a_file_full_of_withheld_cells():
    """`assets/fto_bmi/variants.csv` carries no `stat_significance` at all.

    It is a real `VariantRow` field, so the author had the option and did not take
    it. That is a choice, and it is reported as one — not as three withheld rows,
    which would say the question was put and declined. Nothing was asserted and
    nothing was withheld, because the question was never put.
    """
    report = census(ASSETS / "fto_bmi")
    variants = _table(report, "variants.csv")

    assert "stat_significance" not in _rows(ASSETS / "fto_bmi" / "variants.csv")[0]
    assert "stat_significance" in variants.columns_not_carried
    assert all(c.column != "stat_significance" for c in variants.columns), (
        "a column the file does not carry must contribute no tally at all"
    )
    # And it is genuinely a field of the model, or this test is asserting the
    # wrong distinction.
    assert "stat_significance" in hints.authored_field_names(VariantRow)


def test_a_column_that_is_not_a_field_of_the_table_kind_is_a_different_fact():
    """`studies.csv` has no `direction`, `weight` or `clin_sig` — not an authoring choice."""
    report = census(ASSETS / "fto_bmi")
    studies = _table(report, "studies.csv")

    assert set(studies.columns_absent_from_table_kind) >= {"clin_sig", "direction", "weight"}
    assert not set(studies.columns_absent_from_table_kind) & set(studies.columns_not_carried), (
        "the two absences are disjoint: a column is one or the other, never both"
    )


def test_the_literal_unknown_and_an_empty_cell_are_counted_apart():
    """Both withhold; only one of them says so on purpose.

    `assets/longevity_2026` carries both in one table — `direction` withholds by
    writing `unknown`, `weight` withholds by being blank — which is what makes it
    the right module to pin this against.
    """
    path = ASSETS / "longevity_2026" / "variants.csv"
    rows = _rows(path)
    report = census(ASSETS / "longevity_2026")
    variants = _table(report, "variants.csv")

    direction = _column(variants, "direction")
    weight = _column(variants, "weight")
    expected = collections.Counter((r.get("direction") or "").strip() for r in rows)

    assert direction.withheld_unknown == expected["unknown"] > 0
    assert direction.withheld_blank == expected[""] == 0
    assert weight.withheld_blank > 0
    assert weight.withheld_unknown == 0

    # The invariant, asserted rather than described: every row lands in exactly
    # one bucket, so a withheld row is never a miss and never a hit.
    for column in variants.columns:
        assert (
            column.asserted
            + column.withheld_blank
            + column.withheld_unknown
            + sum(column.values[v] for v in column.off_vocabulary)
            == variants.rows
        )


def test_a_value_outside_the_closed_vocabulary_is_named_and_not_counted_as_asserted(tmp_path):
    """The vocabulary is asked, so this test cannot pass by agreeing with a list of ours."""
    run = tmp_path / "module"
    shutil.copytree(ASSETS / "fto_bmi", run)
    path = run / "variants.csv"
    rows = _rows(path)
    rows[0]["direction"] = "riskk"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    direction = _column(_table(census(run), "variants.csv"), "direction")

    assert direction.off_vocabulary == ["riskk"]
    assert direction.asserted == len(rows) - 1, "an unrecognised cell claims nothing"
    assert "riskk" not in hints.field_vocabularies(VariantRow)["direction"]["options"]


def test_machine_written_sidecars_are_not_counted_as_what_the_author_asserted():
    """A fact pass's `p_value` is the source's claim, not the author's.

    The roster is upstream's `DERIVED_TABLE_MODELS`, so a sidecar added in a later
    release — 0.7 adds PubMind's — is absorbed without an edit here.
    """
    report = census(ASSETS / "longevity_2026")
    scored = {t.csv for t in report.tables}

    assert "resolution.csv" in {p.name for p in (ASSETS / "longevity_2026").glob("*.csv")}
    assert not scored & set(hints.DERIVED_TABLE_MODELS)


def test_the_census_needs_no_reference_and_judges_nothing():
    report = census(ASSETS / "fto_bmi")

    assert report.tables
    assert "does not judge" in report.note
    assert set(ASSERTION_COLUMNS)  # the watched set is a benchmark judgement, and it is non-empty
