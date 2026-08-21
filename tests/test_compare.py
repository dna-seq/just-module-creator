"""Comparing two spec directories — the grains, and the four things it refuses.

`RM19`. Every case here is built from a **real reference example** rather than from
a synthetic table, because the design's decisions were measured on that corpus and a
test against invented rows would not reproduce them. `hfe_hemochromatosis` is 13
variant rows, 33 studies, a `sources.csv` under the deprecated spelling, and two
derived sidecars.

The cases that matter are the ones where the naive answer is wrong: a row reorder is
not a content change, a licence edit moves no `content_signature`, and a retyped
rsID is one row removed and one added rather than one changed.
"""

from __future__ import annotations

import csv
import io
import shutil
from pathlib import Path

import pytest

from just_module_creator.compare import _window
from just_module_creator.tools.comparison import _compare

REFERENCE = Path("/data/sources/just-dna-format/reference_examples/hfe_hemochromatosis")

pytestmark = pytest.mark.skipif(
    not REFERENCE.is_dir(),
    reason="the sibling format checkout is not present; these cases are measured on its corpus",
)


@pytest.fixture
def pair(tmp_path: Path) -> tuple[Path, Path]:
    left, right = tmp_path / "a", tmp_path / "b"
    shutil.copytree(REFERENCE, left)
    shutil.copytree(REFERENCE, right)
    return left, right


def _rewrite(path: Path, mutate) -> None:
    rows = list(csv.DictReader(io.StringIO(path.read_text())))
    mutate(rows)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buf.getvalue())


def _table(report, csv_name: str):
    return next(t for t in report.tables if t.csv == csv_name)


def test_moving_a_column_into_the_defaults_block_is_not_a_content_change(pair):
    """The `defaults:` fold, and the answer that contradicted itself without it.

    A `curator` written on every variant row and the same value declared once under
    `defaults:` are the same content: the compiler folds the block in before hashing, so
    `content_signature` agrees across the pair. Reading each CSV directly does not fold,
    and this report used to carry both answers at once — `content: same` beside thirteen
    rows changed on `curator` and `method`. A finding that contradicts the payload
    carrying it teaches a reader to discount findings, which is the cost worth a test.

    `compiler.spec_tables` (upstream 0.6.5) returns the folded rows, which is why this
    passes: nothing here reimplements the fold, and the private pieces it needs are not
    ours to reach for.
    """
    left, right = pair
    spec = right / "module_spec.yaml"
    text = spec.read_text()
    assert "defaults:" in text, "the fixture's defaults block is the subject of this test"
    _rewrite(
        right / "variants.csv",
        lambda rows: [
            row.update(curator="ai-module-creator", method="literature-review") for row in rows
        ],
    )
    spec.write_text(
        text.replace("defaults:\n  curator: ai-module-creator\n  method: literature-review\n", "")
    )

    report = _compare(left, right, 12, 2)
    assert report.content == "same"
    variants = _table(report, "variants.csv")
    assert not variants.changed, f"changed on: {[g.columns for g in variants.changed]}"
    assert variants.unchanged == variants.rows_left


def test_a_module_against_an_identical_copy_moves_nothing(pair):
    left, right = pair
    report = _compare(left, right, 12, 2)
    assert report.content == "same"
    assert report.frame.verdict == "same"
    variants = _table(report, "variants.csv")
    assert (variants.unchanged, variants.added, variants.removed) == (13, 0, 0)
    assert variants.changed == []
    assert all(d.verdict == "same" for d in report.derived)
    assert report.unknown == []


def test_the_deprecated_spelling_is_the_same_table(pair):
    """`sources.csv` and `licensing.csv` are one table with one model.

    Reporting them as two would say a file was removed and another added when nothing
    about the data moved.
    """
    left, right = pair
    (right / "sources.csv").rename(right / "licensing.csv")
    report = _compare(left, right, 12, 2)
    licensing = _table(report, "licensing.csv")
    assert licensing.presence == "both"
    assert (licensing.spelling_left, licensing.spelling_right) == ("sources.csv", "licensing.csv")
    assert licensing.unchanged == 2


def test_a_licence_edit_moves_no_content_signature_and_says_so(pair):
    """The measured case behind `identity_scope`: an author watching the wrong hash
    concludes their edit was invisible."""
    left, right = pair
    _rewrite(right / "sources.csv", lambda rows: rows[0].update(notice="edited notice"))
    report = _compare(left, right, 12, 2)
    assert report.content == "same", "licensing is authored and outside content_signature"
    licensing = _table(report, "licensing.csv")
    assert licensing.identity_scope == "sources.signature"
    assert [(g.columns, g.rows) for g in licensing.changed] == [(["notice"], 1)]


def test_reordering_rows_is_not_a_content_change(pair):
    left, right = pair
    path = right / "variants.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], *reversed(lines[1:])]) + "\n")
    report = _compare(left, right, 12, 2)
    assert report.content == "same"
    variants = _table(report, "variants.csv")
    assert (variants.unchanged, variants.added, variants.removed) == (13, 0, 0)


def test_rows_changing_in_one_column_are_one_group_not_many_lines(pair):
    left, right = pair
    _rewrite(
        right / "variants.csv",
        lambda rows: [r.update(conclusion=r["conclusion"] + " (reworded)") for r in rows[:5]],
    )
    report = _compare(left, right, 12, 2)
    variants = _table(report, "variants.csv")
    assert [(g.columns, g.rows) for g in variants.changed] == [(["conclusion"], 5)]
    assert variants.unchanged == 8
    assert report.content == "moved"


def test_a_second_changed_column_makes_a_second_group(pair):
    """Grouping is by the *set* of columns, so 'these five also moved X' stays legible."""
    left, right = pair

    def mutate(rows):
        for row in rows[:5]:
            row["conclusion"] += " (reworded)"
        for row in rows[:2]:
            row["gene"] = "HFE2"

    _rewrite(right / "variants.csv", mutate)
    variants = _table(_compare(left, right, 12, 2), "variants.csv")
    assert [(g.columns, g.rows) for g in variants.changed] == [
        (["conclusion"], 3),
        (["conclusion", "gene"], 2),
    ]


def test_a_retyped_key_is_one_removed_and_one_added_never_one_changed(pair):
    """Refusal 3. Pairing them would assert that two rows are the same row."""
    left, right = pair
    path = right / "variants.csv"
    path.write_text(path.read_text().replace("rs1800562", "rs1799945", 1))
    variants = _table(_compare(left, right, 12, 2), "variants.csv")
    assert (variants.added, variants.removed) == (1, 1)
    assert variants.changed == []


def test_a_different_declared_build_is_the_whole_answer(pair):
    """The row counts stay clean and mean nothing — the natural key is build-independent."""
    left, right = pair
    spec = right / "module_spec.yaml"
    spec.write_text(spec.read_text().replace("GRCh38", "GRCh37"))
    report = _compare(left, right, 12, 2)
    assert report.frame.verdict == "moved"
    assert "not comparable" in report.frame.note
    assert report.content == "moved", "the declared build is part of the content"
    assert _table(report, "variants.csv").unchanged == 13


def test_a_table_on_one_side_only_is_known_absent_rather_than_unknown(pair):
    left, right = pair
    (right / "gwas_effects.csv").unlink()
    report = _compare(left, right, 12, 2)
    gwas = next(d for d in report.derived if d.csv == "gwas_effects.csv")
    assert gwas.verdict == "unknown"
    assert any("left only" in u.reason for u in report.unknown)


def test_a_derived_sidecar_is_compared_on_facts_not_bytes(pair):
    """`fetched_at` is not a fact field, so re-stamping it moves the bytes and no signature."""
    left, right = pair
    path = right / "resolution.csv"
    rows = list(csv.DictReader(io.StringIO(path.read_text())))
    if "fetched_at" not in rows[0]:
        pytest.skip("this reference example records no fetched_at to re-stamp")
    _rewrite(path, lambda rs: [r.update(fetched_at="2026-08-20T00:00:00Z") for r in rs])
    resolution = next(d for d in _compare(left, right, 12, 2).derived if d.csv == "resolution.csv")
    assert resolution.verdict == "same"


def test_an_unreadable_table_is_unknown_and_never_a_diff(pair):
    left, right = pair
    (right / "variants.csv").write_text("rsid,genotype\nnot-an-rsid,??\n")
    report = _compare(left, right, 12, 2)
    variants = _table(report, "variants.csv")
    assert variants.presence == "unknown"
    assert (variants.unchanged, variants.added, variants.removed) == (None, None, None)
    assert any("could not be read" in u.reason for u in report.unknown)


def test_the_group_cap_says_what_it_left_out(pair):
    """A silent truncation reads as 'covered everything'."""
    left, right = pair

    extra = ["gene", "phenotype", "category"]

    def mutate(rows):
        # Grouping is by the *set* of columns, so a distinct set per row needs a
        # distinct second column — varying the value alone would make one group.
        for index, row in enumerate(rows):
            row["conclusion"] = f"{row['conclusion']} #{index}"
            row[extra[index % len(extra)]] = f"changed-{index}"

    _rewrite(right / "variants.csv", mutate)
    uncapped = _compare(left, right, 12, 2)
    # Three groups, not four: every row also gets a second column, so there is no
    # bare `[conclusion]` set left over.
    assert len(_table(uncapped, "variants.csv").changed) == 3
    assert not any("further group(s)" in u.reason for u in uncapped.unknown)

    capped = _compare(left, right, 2, 2)
    assert len(_table(capped, "variants.csv").changed) == 2
    dropped = next(u for u in capped.unknown if "further group(s)" in u.reason)
    assert "raise `max_groups`" in dropped.reason
    assert _table(capped, "variants.csv").unchanged == _table(uncapped, "variants.csv").unchanged


def test_metadata_reports_what_no_hash_records(pair):
    left, right = pair
    (right / "README.md").unlink()
    report = _compare(left, right, 12, 2)
    readme = next(m for m in report.metadata if m.what == "README.md")
    assert (readme.left, readme.right) == ("present", "absent")
    assert readme.in_hash is False
    assert report.content == "same", "the readme is outside every identity"


# --------------------------------------------------------------------------- #
# The example window
# --------------------------------------------------------------------------- #
def test_an_example_shows_the_difference_rather_than_the_head():
    """Truncating from the start renders two long values that differ late as two
    identical strings — worse than showing nothing, because the reader concludes the
    row did not really change. Found by dogfooding the tool on a real conclusion."""
    base = "Two pathogenic HFE alleles - the genotype HFE-related haemochromatosis is defined by"
    left, right = _window(base, base + " (reworded)")
    assert left != right
    assert "reworded" in right


def test_short_values_are_shown_whole():
    assert _window("risk", "neutral") == ["risk", "neutral"]
