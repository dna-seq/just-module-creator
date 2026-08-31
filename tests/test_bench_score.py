"""The primary measurement: did a run recover the adjudicated answer.

Everything here is offline and works from `tmp_path` copies of the tracked corpus,
so nothing is written into the project tree and no test depends on the sibling
format checkout. The perturbations are one-cell edits, each isolating one axis:
the point of separate metrics is that a run can fail one and pass the others, and
a test that moved two cells could not show it.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from just_module_creator.bench import (
    load_fixture,
    score_ground_truth,
)

BENCHMARKS = Path(__file__).resolve().parent.parent / "assets" / "benchmarks"
SIRT6 = BENCHMARKS / "sirt6"


def _copy(tmp_path: Path, source: Path, name: str = "run") -> Path:
    out = tmp_path / name
    shutil.copytree(source, out)
    return out


def _edit(spec: Path, csv_name: str, mutate) -> None:
    path = spec / csv_name
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    mutate(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def fixture():
    return load_fixture(SIRT6)


def test_the_reference_scored_against_itself_is_perfect(fixture, tmp_path):
    run = _copy(tmp_path, SIRT6 / "reference")

    score = score_ground_truth(fixture, run)

    assert score.comparable
    assert score.variants.pair_recall == 1.0
    assert score.variants.rsid_recall == 1.0
    assert score.variants.weighted_recall == 1.0
    assert score.variants.missing_pairs == []
    assert score.variants.extra_pairs == []
    assert score.variants.decoy_rate == 0.0
    assert score.direction.agreement == 1.0
    assert score.direction.disagreeing == 0


def test_pair_recall_and_rsid_recall_are_two_numbers_because_they_fail_apart(
    fixture, tmp_path
):
    """The gap between them IS the 'right variant, wrong genotypes' signal.

    `runs/a` authored one of the reference's three genotypes for the one variant
    both agree on. Partial credit for a right rsID with a wrong genotype would
    average these into a single number that says neither thing.
    """
    score = score_ground_truth(fixture, SIRT6 / "runs" / "a")

    assert score.variants.rsid_recall == 1.0, "it found the right variant"
    assert score.variants.pair_recall is not None
    assert score.variants.pair_recall < 1.0, "and not all of its genotypes"
    assert score.variants.missing_pairs == ["rs117385980:C/C", "rs117385980:T/T"]


def test_dropping_a_heavier_tier_costs_more_at_the_same_row_count(fixture, tmp_path):
    """The test that proves tier weighting does anything at all.

    Two runs drop the same *number* of rows, one from a weighted tier and one from
    an untiered variant that weighs 1.0. Unweighted recall cannot tell them apart;
    weighted recall must.
    """
    reference = _copy(tmp_path, SIRT6 / "reference", "reference")
    _edit(
        reference,
        "variants.csv",
        lambda rows: rows.append({**rows[0], "rsid": "rs4988235", "genotype": "A/A"}),
    )
    meta = json.loads((SIRT6 / "metadata.json").read_text(encoding="utf-8"))
    meta["expected_spec"] = "reference"
    meta["decoy_variants"] = {"rsids": []}
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    (tmp_path / "prompt.txt").write_text("build it", encoding="utf-8")
    two_tier = load_fixture(tmp_path)

    assert two_tier.tier_of == {"rs117385980": "tier2_replicated_trend"}
    assert two_tier.untiered_rsids == ["rs4988235"], "the added row weighs 1.0"

    drop_heavy = _copy(tmp_path, reference, "heavy")
    _edit(drop_heavy, "variants.csv", lambda rows: rows.remove(rows[0]))
    drop_light = _copy(tmp_path, reference, "light")
    _edit(drop_light, "variants.csv", lambda rows: rows.remove(rows[-1]))

    heavy = score_ground_truth(two_tier, drop_heavy).variants
    light = score_ground_truth(two_tier, drop_light).variants

    assert heavy.pair_recall == light.pair_recall, "same number of rows lost"
    assert heavy.weighted_recall is not None and light.weighted_recall is not None
    assert heavy.weighted_recall < light.weighted_recall, "and not the same evidence"


def test_a_flipped_direction_is_a_disagreement_and_not_a_missing_row(fixture, tmp_path):
    run = _copy(tmp_path, SIRT6 / "reference")
    _edit(run, "variants.csv", lambda rows: rows[0].update(direction="protective"))

    score = score_ground_truth(fixture, run)

    assert score.variants.pair_recall == 1.0, "the row is still there"
    assert score.direction.disagreeing == 1
    assert score.direction.agreement is not None and score.direction.agreement < 1.0
    assert score.direction.disagreements == [
        "rs117385980:C/T reference=risk run=protective"
    ]


def test_blanking_a_direction_shrinks_the_denominator_and_is_never_a_miss(
    fixture, tmp_path
):
    """`None` is not `False`. A withheld cell leaves the denominator; it does not fail."""
    reference = score_ground_truth(fixture, SIRT6 / "reference").direction
    run = _copy(tmp_path, SIRT6 / "reference")
    _edit(run, "variants.csv", lambda rows: rows[0].update(direction=""))

    score = score_ground_truth(fixture, run).direction

    assert score.both_asserted == reference.both_asserted - 1
    assert score.disagreeing == 0
    assert score.reference_asserted_run_withheld == 1
    assert score.agreement == 1.0, "the rows that were compared still agree"
    # Every row lands in exactly one bucket.
    assert (
        score.both_asserted
        + score.reference_asserted_run_withheld
        + score.run_asserted_reference_withheld
        + score.both_withheld
        == score.pairs_compared
    )


def test_writing_unknown_everywhere_scores_nothing_rather_than_everything(
    fixture, tmp_path
):
    """The gaming case, and the reason the four tallies are reported.

    A run that asserts no direction anywhere cannot be wrong about one. It must
    read as *nothing measured*, not as a clean sheet — and the threshold must come
    back `None` rather than passed.
    """
    run = _copy(tmp_path, SIRT6 / "reference")
    _edit(run, "variants.csv", lambda rows: [r.update(direction="unknown") for r in rows])

    score = score_ground_truth(fixture, run)

    assert score.direction.both_asserted == 0
    assert score.direction.agreement is None
    assert score.direction.reference_asserted_run_withheld == 2
    assert score.thresholds_met["direction_agreement"] is None, (
        "an unasked question never passes"
    )
    assert any(u.subject == "threshold:direction_agreement" for u in score.unscored)


def test_a_decoy_is_reported_and_an_ordinary_extra_variant_is_not_scored_as_wrong(
    fixture, tmp_path
):
    """A fixture is one curation, not the set of all correct rows.

    So an unexpected variant is reported and not counted against the run, while a
    decoy — an rsID an expert asserted does not belong — is the false-positive
    signal. `rs2802292` is the sharp one: a real longevity variant (FOXO3) that is
    not in this paper, so it catches a run importing general knowledge instead of
    reading the source it was given.
    """
    run = _copy(tmp_path, SIRT6 / "reference")
    _edit(
        run,
        "variants.csv",
        lambda rows: rows.extend(
            [
                {**rows[0], "rsid": "rs2802292", "genotype": "G/G"},
                {**rows[0], "rsid": "rs1801133", "genotype": "C/T"},
            ]
        ),
    )

    variants = score_ground_truth(fixture, run).variants

    assert variants.decoys_present == ["rs2802292"]
    assert variants.decoy_rate is not None and variants.decoy_rate > 0
    assert variants.extra_pairs == ["rs1801133:C/T"], "not a decoy, so not a failure"
    assert variants.pair_recall == 1.0, "an extra row never lowers recall"
    assert "rs2802292:G/G" not in variants.extra_pairs


def test_a_fixture_with_no_reference_scores_nothing_rather_than_perfectly(tmp_path):
    """`centenarian` has no adjudicated answer, and an empty expected set is not 1.0."""
    fixture = load_fixture(BENCHMARKS / "centenarian")

    score = score_ground_truth(fixture, BENCHMARKS / "centenarian" / "runs" / "a" / "spec")

    assert score.variants.pair_recall is None
    assert score.variants.weighted_recall is None
    assert score.direction.agreement is None
    assert any("no adjudicated reference" in u.reason for u in score.unscored)


def test_the_free_text_conclusion_is_unscored_rather_than_passed(fixture):
    """No judge is supplied, so the cell a string comparison cannot score says so."""
    score = score_ground_truth(fixture, SIRT6 / "reference")

    assert any(u.subject == "variants.csv:conclusion" for u in score.unscored)
    assert all("conclusion" not in name for name in score.thresholds_met)


def test_the_payload_is_byte_stable_across_runs(fixture):
    """Deterministic ordering is load-bearing wherever output is compared."""
    first = score_ground_truth(fixture, SIRT6 / "runs" / "a").model_dump_json()
    second = score_ground_truth(fixture, SIRT6 / "runs" / "a").model_dump_json()

    assert first == second


def test_citation_recall_is_the_offline_number_and_accuracy_is_not(fixture, tmp_path):
    """`runs/a2` cited the assigned paper and not the source it replicates.

    That is the round's own finding as a number: fetching the primary longevity
    source unprompted happened in one run of two, so it is not stable behaviour.
    """
    both = score_ground_truth(fixture, SIRT6 / "runs" / "a").citations
    one = score_ground_truth(fixture, SIRT6 / "runs" / "a2" / "spec").citations

    assert both.recall == 1.0
    assert both.correct == ["28399814", "41249831"]
    assert one.recall == 0.5
    assert one.missing == ["28399814"]
    for report in (both, one):
        assert report.resolver == "none"
        assert report.accuracy is None, "identity needs a lookup and none was made"
        assert report.hallucinated == []
        assert report.misidentified == []


def test_a_pmid_the_fixture_lacks_is_unrecognised_and_never_hallucinated(
    fixture, tmp_path
):
    """Offline, `null` means UNCHECKED.

    Calling an id we never looked up 'hallucinated' is the check-that-could-not-run
    failure pointing the other way — and an extra citation is not a failure at all,
    because a fixture is one curation rather than the set of all correct papers.
    """
    run = _copy(tmp_path, SIRT6 / "reference")
    _edit(run, "studies.csv", lambda rows: rows[0].update(pmid="11788828"))

    citations = score_ground_truth(fixture, run).citations

    assert "11788828" in citations.unrecognised
    assert citations.hallucinated == []
    assert citations.misidentified == []
    assert "41249831" in citations.missing, "swapping one out loses it from recall"
    assert citations.recall == 0.5
