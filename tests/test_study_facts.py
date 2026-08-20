"""`study_facts` — the ancestry the module already holds (RM22).

Measured on `hfe_hemochromatosis` rather than on invented rows, because the
property that decides the tool's whole design only shows up in real Catalog
data: an `ancestry` is frequently a *joined string* naming several cohorts
("African American or Afro-Caribbean, European, Hispanic or Latin American"),
so which part belongs in a given `studies.csv` row is a judgement and the tool
must surface rather than fill.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest
from conftest import offline_settings

REFERENCE = Path("/data/sources/just-dna-format/reference_examples/hfe_hemochromatosis")

pytestmark = pytest.mark.skipif(
    not REFERENCE.is_dir(),
    reason="the sibling format checkout is not present; this case is measured on its corpus",
)


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    target = tmp_path / "spec"
    shutil.copytree(REFERENCE, target)
    return target


async def _facts(make_client, spec: Path):
    async with make_client("essentials", offline_settings()) as client:
        return (await client.call_tool("study_facts", {"spec_dir": str(spec)})).data


async def test_it_collapses_associations_to_studies(make_client, spec: Path) -> None:
    """`studies.csv` is per (paper, variant); ancestry is a property of the study.

    Ground truth computed from the fixture, so a change in the corpus moves the
    expectation with it rather than failing on a pasted number.
    """
    rows = list(csv.DictReader((spec / "gwas_effects.csv").open(encoding="utf-8")))
    expected = {(r.get("pmid") or None, r.get("study_accession") or None) for r in rows}

    data = await _facts(make_client, spec)

    assert {(s.pmid, s.study_accession) for s in data.studies} == expected
    assert sum(s.rows for s in data.studies) == len(rows)
    # Collapsing has to be doing something, or this test proves nothing.
    assert len(data.studies) < len(rows)


async def test_the_ancestry_is_carried_through_verbatim(make_client, spec: Path) -> None:
    """No normalising, no splitting, no picking one. It is the Catalog's own text.

    Splitting a joined ancestry here would be this layer inventing a per-row
    answer the Catalog never gave — the judgement the tool exists to hand back.
    """
    rows = list(csv.DictReader((spec / "gwas_effects.csv").open(encoding="utf-8")))
    from_file = {r["ancestry"] for r in rows if r.get("ancestry")}

    data = await _facts(make_client, spec)
    reported = {s.ancestry for s in data.studies if s.ancestry}

    assert reported <= from_file
    assert data.with_ancestry == sum(1 for s in data.studies if s.ancestry)
    # The fixture must contain a multi-cohort string, or the claim above is untested.
    assert any("," in a for a in from_file), "fixture should carry a joined ancestry"


async def test_a_blank_row_never_erases_an_answer_an_earlier_row_gave(
    make_client, spec: Path
) -> None:
    """First non-null wins per field.

    The fixture carries `not_found` rows with every study column empty, sharing
    the `(None, None)` key. Last-wins would let one of those blank the ancestry
    of a study that had one, which is a silent loss of the exact value the tool
    exists to surface.
    """
    path = spec / "gwas_effects.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    header = list(rows[0])

    donor = next(r for r in rows if r.get("ancestry") and r.get("pmid"))
    blank = dict.fromkeys(header, "")
    blank["association_id"] = "synthetic:blank-after"
    blank["pmid"] = donor["pmid"]
    blank["study_accession"] = donor["study_accession"]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows([*rows, blank])

    data = await _facts(make_client, spec)
    same = next(
        s
        for s in data.studies
        if s.pmid == donor["pmid"] and s.study_accession == donor["study_accession"]
    )
    assert same.ancestry == donor["ancestry"]


async def test_a_module_with_no_gwas_pass_is_told_so_rather_than_reported_empty(
    make_client, tmp_path: Path
) -> None:
    """An absent file is "the pass never ran", which is not "no ancestry exists"."""
    bare = tmp_path / "bare"
    bare.mkdir()

    data = await _facts(make_client, bare)

    assert data.studies == []
    assert data.with_ancestry == 0
    assert "not a defect" in data.note
