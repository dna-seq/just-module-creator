"""Loading a fixture, and the five ways one can lie about what it scores.

Every refusal here is silent if it is not checked at load: the score comes out, it
looks like a number, and it is a number about something other than what the fixture
claims. So they are raised where a person is looking at the fixture, not where they
are reading a result.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from just_module_creator.bench import BenchFixtureError, load_fixture

BENCHMARKS = Path(__file__).resolve().parent.parent / "assets" / "benchmarks"
SHIPPED = sorted(p.parent.name for p in BENCHMARKS.glob("*/metadata.json"))


def _fixture_with(tmp_path: Path, **changes) -> Path:
    """A copy of the sirt6 fixture with metadata.json patched. The reference is shared."""
    out = tmp_path / "fixture"
    shutil.copytree(BENCHMARKS / "sirt6", out)
    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    meta.update(changes)
    (out / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    return out


def test_every_shipped_fixture_loads():
    assert SHIPPED, "the corpus should ship fixtures"
    for name in SHIPPED:
        fixture = load_fixture(BENCHMARKS / name)
        assert fixture.name == name
        assert fixture.prompt.strip(), f"{name} ships no prompt"


def test_a_fixture_with_no_reference_says_so_rather_than_scoring_nothing():
    """Two of three papers have no adjudicated answer, and that is stated, not hidden.

    `reference: None` is the honest shape. An empty expected set would score every
    run as perfect recall over nothing.
    """
    unreferenced = [n for n in SHIPPED if load_fixture(BENCHMARKS / n).reference is None]

    assert set(unreferenced) == {"ards", "centenarian"}
    for name in unreferenced:
        assert load_fixture(BENCHMARKS / name).expected_keys == {}


def test_the_reference_is_read_through_upstreams_own_key():
    """The manuscript's '(rsID, genotype) pair' is `draft.natural_key`, not a spelling of ours."""
    fixture = load_fixture(BENCHMARKS / "sirt6")

    assert fixture.expected_keys["variants.csv"] == {
        ("rs117385980", "C/C"),
        ("rs117385980", "C/T"),
        ("rs117385980", "T/T"),
    }
    # studies.csv keys on (rsid, pmid) — a different key from the same helper,
    # which is the reason it is asked for rather than written down.
    assert fixture.expected_keys["studies.csv"] == {
        ("rs117385980", "28399814"),
        ("rs117385980", "41249831"),
    }


def test_a_tier_naming_a_variant_the_reference_lacks_is_refused(tmp_path):
    """It would inflate the weighted denominator with a row nobody could recover."""
    path = _fixture_with(
        tmp_path,
        variant_tiers={"tier1": {"weight": 3.0, "rsids": ["rs4988235"]}},
        decoy_variants={"rsids": []},
    )

    with pytest.raises(BenchFixtureError, match="does not carry"):
        load_fixture(path)


def test_an_rsid_in_two_tiers_is_refused(tmp_path):
    path = _fixture_with(
        tmp_path,
        variant_tiers={
            "tier1": {"weight": 3.0, "rsids": ["rs117385980"]},
            "tier2": {"weight": 2.0, "rsids": ["rs117385980"]},
        },
    )

    with pytest.raises(BenchFixtureError, match="two weights"):
        load_fixture(path)


def test_a_decoy_that_is_also_expected_is_refused(tmp_path):
    """recall would count it as a hit and decoy_rate as a false positive."""
    path = _fixture_with(tmp_path, decoy_variants={"rsids": ["rs117385980"]})

    with pytest.raises(BenchFixtureError, match="both expected and a decoy"):
        load_fixture(path)


def test_an_absolute_expected_spec_is_refused(tmp_path):
    """A fixture that points at somebody's home directory does not travel."""
    path = _fixture_with(tmp_path, expected_spec=str(BENCHMARKS / "sirt6" / "reference"))

    with pytest.raises(BenchFixtureError, match="must be relative"):
        load_fixture(path)


def test_an_unkeyed_table_cannot_be_a_scored_table(tmp_path):
    """`repeat_alleles.csv` keys on the `overlap` rule, so its rows pair with nothing."""
    path = _fixture_with(tmp_path, scored_tables=["repeat_alleles.csv"])

    with pytest.raises(BenchFixtureError, match="overlap"):
        load_fixture(path)


def test_an_untiered_expected_variant_is_counted_rather_than_refused(tmp_path):
    """Adding a variant to a reference must not break its fixture.

    It weighs 1.0 and is named, so the gap is visible without being fatal.
    """
    path = _fixture_with(tmp_path, variant_tiers={})

    fixture = load_fixture(path)

    assert fixture.untiered_rsids == ["rs117385980"]
    assert fixture.tier_of == {}


@pytest.mark.parametrize("name", SHIPPED)
def test_a_prompt_never_leaks_the_answer(name):
    """A prompt naming an rsID or a PMID is a benchmark that measures nothing.

    A DOI is the input rather than the answer — the whole task is *build a module
    from this paper* — so it is allowed and the identifiers the run must find are
    not.
    """
    prompt = load_fixture(BENCHMARKS / name).prompt

    assert not re.search(r"\brs\d{3,}\b", prompt), "the prompt names an rsID"
    assert not re.search(r"(?<!\d)\d{8}(?!\d)", prompt), "the prompt names a PMID"
