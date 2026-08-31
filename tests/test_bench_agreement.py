"""The secondary measurement: did two runs of one prompt agree with each other.

Hermetic by construction. Nothing here reaches a network and nothing here depends
on the sibling `just-dna-format` checkout — `tests/test_compare.py` and
`tests/test_compare_published.py` both skip themselves unless that checkout exists,
which is why they are silently absent on a clean machine, and it is a pattern this
file deliberately does not copy.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from conftest import MODULE_SPEC

from just_module_creator.bench import VOLATILE, score

ASSETS = Path(__file__).resolve().parent.parent / "assets"

#: A real HTT CAG range table. `repeat_alleles.csv` is keyed `(gene, repeat_unit)`
#: under the `overlap` rule — upstream's own answer from `hints.key_fields` — so a
#: row cannot be paired by equality and the comparison reports `row_key="unkeyed"`
#: with every count `None`. The tracked `assets/htt_cag_repeats/` template cannot
#: stand in: its `<<REPLACE>>` cells fail row validation, so the table comes back
#: `presence="unknown"` and never reaches the both-sides branch this exercises.
REPEATS = (
    "measure_kind,measure_min,measure_max,direction,clin_sig,phenotype,"
    "trait_efo_id,conclusion,unresolved,source_field,gene,repeat_unit\n"
    "repeat_count,6,26,neutral,,Huntington disease,,"
    "Normal CAG range; no expansion.,false,,HTT,CAG\n"
    "repeat_count,40,250,risk,,Huntington disease,,"
    "Fully penetrant expansion.,false,,HTT,CAG\n"
)


def _binning_module(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "module_spec.yaml").write_text(MODULE_SPEC, encoding="utf-8")
    (root / "repeat_alleles.csv").write_text(REPEATS, encoding="utf-8")
    return root


def test_an_unkeyed_table_on_both_sides_is_unscored_rather_than_a_crash(tmp_path):
    """The defect the move exists to expose.

    `presence` was the filter deciding what goes into `totals`, and an *unkeyed*
    table is `presence="both"` with `unchanged=None` — so the totals summed a
    `None` and raised `TypeError`. The docstring already claimed this class of
    table was "reported as absent, never folded into the denominator as a miss";
    it was true of one-sided tables only.
    """
    left = _binning_module(tmp_path / "left")
    right = _binning_module(tmp_path / "right")

    result = score(left, right)

    table = next(t for t in result["tables"] if t["csv"] == "repeat_alleles.csv")
    assert table["presence"] == "both"
    assert table["keys_shared"] is None, "an unkeyed table pairs nothing"
    assert "repeat_alleles.csv" in result["unscored_tables"]
    # The point of the fix: totals are arithmetic over the tables that were
    # actually scored, and they are ints rather than an exception.
    assert isinstance(result["totals"]["keys_shared"], int)
    assert isinstance(result["totals"]["rows_disagreeing"], int)


def test_a_module_of_only_unkeyed_tables_totals_zero_rather_than_raising(tmp_path):
    """The degenerate case, and it is a different one: `sum([])` is 0, `sum([None])` raises.

    A module whose every table is unkeyed leaves the scored list empty. Zero is the
    honest total there — nothing was compared — and `unscored_tables` is what says
    so, which is why the count and the reason are reported apart.
    """
    result = score(_binning_module(tmp_path / "a"), _binning_module(tmp_path / "b"))

    assert result["totals"] == {
        "keys_shared": 0,
        "keys_only_reference": 0,
        "keys_only_run": 0,
        "rows_disagreeing": 0,
    }
    assert result["unscored_tables"] == ["repeat_alleles.csv"]


def test_a_one_sided_table_is_unscored_not_a_miss(tmp_path, spec_dir):
    """Unchanged behaviour, pinned so the fix cannot quietly widen.

    A table only the reference carries is absent, not zero — the same rule the
    tools apply to a check that could not run.
    """
    run = tmp_path / "run"
    shutil.copytree(spec_dir, run)
    (run / "studies.csv").unlink()

    result = score(spec_dir, run)

    assert "studies.csv" in result["unscored_tables"]
    studies = next(t for t in result["tables"] if t["csv"] == "studies.csv")
    assert studies["keys_shared"] is None
    assert studies["rows_run"] is None


def test_a_volatile_column_disagreeing_on_every_row_is_not_a_disagreement(
    tmp_path, spec_dir
):
    """`curator` differs between two runs by definition and says nothing about the genetics."""
    run = tmp_path / "run"
    shutil.copytree(spec_dir, run)
    text = (run / "variants.csv").read_text(encoding="utf-8")
    assert "curator" not in text.splitlines()[0], "fixture carries curator in defaults"

    result = score(spec_dir, run)

    assert result["volatile_columns_excluded"] == list(VOLATILE)
    assert result["totals"]["rows_disagreeing"] == 0


@pytest.mark.parametrize("fixture", ["fto_bmi", "longevity_2026"])
def test_a_tracked_module_scores_perfectly_against_itself(fixture, tmp_path):
    """Ground truth computed from the CSV, never pasted — §6's rule.

    Both published modules are complete, compilable spec directories, so this also
    pins that the scorer reads a real module rather than a synthetic one.
    """
    reference = ASSETS / fixture
    run = tmp_path / fixture
    shutil.copytree(reference, run)

    result = score(reference, run)

    assert result["content_identical"]
    assert result["totals"]["rows_disagreeing"] == 0
    assert result["totals"]["keys_only_reference"] == 0
    assert result["totals"]["keys_only_run"] == 0

    variants = next(t for t in result["tables"] if t["csv"] == "variants.csv")
    expected = len((reference / "variants.csv").read_text().strip().splitlines()) - 1
    assert variants["keys_shared"] == expected
    assert variants["cell_agreement_over_shared_keys"] == 1.0
