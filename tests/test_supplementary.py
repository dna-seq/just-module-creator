"""The supplementary ladder, and the distinction it exists to keep.

Real identifiers throughout — the DOIs are the four articles the ladder was
measured against, and the JATS fixture is the shape Europe PMC actually returns,
double-listing included.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from just_module_creator import supplementary as S


@pytest.mark.parametrize(
    ("doi", "expected"),
    [
        ("10.1007/s11357-025-02044-3", "11357_2025_2044"),
        ("10.1186/s40246-025-00772-3", "40246_2025_772"),
        ("10.1038/s41598-025-24018-3", "41598_2025_24018"),
        ("10.1038/s41467-018-03242-8", "41467_2018_3242"),
    ],
)
def test_the_stem_strips_leading_zeros_and_expands_the_year(doi: str, expected: str) -> None:
    """Both transformations are load-bearing and neither is guessable from one case.

    `02044` becomes `2044` and `018` becomes `2018`; a stem that keeps either
    literal addresses a key that does not exist, and on this host that reads as a
    403, which is indistinguishable from a file the publisher never posted.
    """
    assert S.esm_stem(doi) == expected


def test_an_unparseable_doi_yields_no_stem_rather_than_a_wrong_one() -> None:
    assert S.esm_stem("10.5281/zenodo.1234567") is None


def test_the_path_keeps_the_doi_encoded_inside_the_art_segment() -> None:
    """The `art%3A` prefix and the encoded slash are the whole addressing scheme."""
    path = S.esm_path("10.1007/s11357-025-02044-3", "11357_2025_2044", 2, "xlsx")
    assert path.startswith("/esm/art%3A10.1007%2Fs11357-025-02044-3/MediaObjects/")
    assert path.endswith("/11357_2025_2044_MOESM2_ESM.xlsx")


def test_the_jats_inventory_deduplicates_the_double_listing() -> None:
    """Europe PMC lists every file twice — body and back matter.

    A naive parse doubles the inventory, which is a wrong count reported
    confidently. Built from the real element shape rather than a simplified one.
    """
    xml = """
    <body><sec><supplementary-material id="MOESM1">
      <media xlink:href="41467_2018_3242_MOESM5_ESM.xlsx"/>
      <caption><p>Supplementary Data 1</p></caption>
    </supplementary-material></sec></body>
    <back><supplementary-material id="MOESM1">
      <media xlink:href="41467_2018_3242_MOESM5_ESM.xlsx"/>
      <caption><p>Supplementary Data 1</p></caption>
    </supplementary-material>
    <supplementary-material><media xlink:href="41467_2018_3242_MOESM3_ESM.pdf"/>
      <caption><p>Peer Review File</p></caption></supplementary-material></back>
    """
    files = S.parse_jats_supplementary(xml, "https://europepmc.org/articles/PMC5834468/bin")
    assert [f.name for f in files] == [
        "41467_2018_3242_MOESM5_ESM.xlsx",
        "41467_2018_3242_MOESM3_ESM.pdf",
    ]
    assert [f.extension for f in files] == ["xlsx", "pdf"]
    assert "Supplementary Data 1" in (files[0].caption or "")


def test_an_unknown_publisher_is_not_determinable_and_never_none_published() -> None:
    """The distinction the whole module exists for.

    Two agents recorded a surface limit as a fact about the world; collapsing these
    two verdicts is how that happens. An Elsevier DOI must come back as a gap in
    our coverage, naming the prefix, not as an article without supplements.
    """
    result = S.inventory(
        doi="10.1016/j.cell.2019.03.043", xml=None, xml_base_url=None, probe=None
    )
    assert result.verdict == "not_determinable"
    assert result.verdict != "none_published"
    assert "10.1016" in (result.why_not or "")
    assert result.files == []


def test_offline_cannot_answer_the_pattern_rung_and_says_so() -> None:
    """A rung that could not run is not a rung that found nothing."""
    result = S.inventory(
        doi="10.1007/s11357-025-02044-3", xml=None, xml_base_url=None, probe=None
    )
    assert result.verdict == "not_determinable"
    assert "Offline" in (result.why_not or "")


def test_the_xml_rung_wins_and_says_the_names_were_not_guessed() -> None:
    xml = (
        '<supplementary-material><media xlink:href="40246_2025_772_MOESM1_ESM.txt"/>'
        "<caption><p>Additional file 1.</p></caption></supplementary-material>"
    )
    result = S.inventory(
        doi="10.1186/s40246-025-00772-3",
        xml=xml,
        xml_base_url="https://europepmc.org/articles/PMC12506250/bin",
        probe=None,
    )
    assert result.verdict == "found"
    assert result.rung == "europepmc_xml"
    # `.txt` is exactly the extension a probe list would have missed.
    assert result.files[0].extension == "txt"


def test_a_workbook_is_described_by_sheets_and_titles_without_openpyxl(tmp_path: Path) -> None:
    """Built as a real xlsx container, so the reader is exercised, not mocked.

    The two halves are separate on purpose: a sheet is named `ST8` while the title
    written inside it reads `Supplementary Table S8: …`, and an author holding only
    one of them cannot say which sheet answers their question.
    """
    book = tmp_path / "esm.xlsx"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook><sheets><sheet name="Table of Contents" sheetId="1"/>'
            '<sheet name="ST8" sheetId="2"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            "<sst><si><t>Supplementary Table S8: Number of trait associations of mvARD "
            "lead SNPs in GWAS Catalog</t></si><si><t>rs6547692</t></si></sst>",
        )
    sheets, titles = S.workbook_sheets(book)
    assert sheets == ["Table of Contents", "ST8"]
    assert titles == [
        "Supplementary Table S8: Number of trait associations of mvARD lead SNPs in GWAS Catalog"
    ]


def test_a_non_workbook_reports_empty_rather_than_raising(tmp_path: Path) -> None:
    """A PDF supplement is common and is not an error."""
    pdf = tmp_path / "esm.pdf"
    pdf.write_bytes(b"%PDF-1.4 not a zip")
    assert S.workbook_sheets(pdf) == ([], [])
