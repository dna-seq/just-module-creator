"""The supplementary ladder, and the distinction it exists to keep.

Real identifiers throughout — the DOIs are the four articles the ladder was
measured against, and the JATS fixture is the shape Europe PMC actually returns,
double-listing included.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import httpx
import pytest
from conftest import offline_settings

from just_module_creator import net
from just_module_creator import supplementary as S
from just_module_creator.net import HttpService, ServiceGate, build_services
from just_module_creator.tools import research


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
    result = S.inventory(doi="10.1016/j.cell.2019.03.043", xml=None, xml_base_url=None, probe=None)
    assert result.verdict == "not_determinable"
    assert result.verdict != "none_published"
    assert "10.1016" in (result.why_not or "")
    assert result.files == []


def test_offline_cannot_answer_the_pattern_rung_and_says_so() -> None:
    """A rung that could not run is not a rung that found nothing."""
    result = S.inventory(doi="10.1007/s11357-025-02044-3", xml=None, xml_base_url=None, probe=None)
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


# --------------------------------------------------------------------------- #
# Reading the rows — the rung four runs hand-rolled, and the two bugs they hit
# --------------------------------------------------------------------------- #
#: A minimal but genuinely valid xlsx container, written as XML rather than with
#: openpyxl, because the cases worth testing are the ones a correct writer never
#: produces: **no `<dimension>` element** (the "missing `ref`" one run lost two
#: bugs to) and a **sparse row** whose middle cells are simply absent (the
#: column-shift the other hand-rolled reader produced). Real identifiers: the two
#: rsIDs and their GRCh38 coordinates are from the ARDS paper's ST9.
_CONTENT_TYPES = (
    '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package'
    '.relationships+xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.spreadsheetml.worksheet+xml"/></Types>'
)
_ROOT_RELS = (
    '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
)
_WORKBOOK = (
    '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
    '<sheet name="ST9" sheetId="1" r:id="rId1"/></sheets></workbook>'
)
_WORKBOOK_RELS = (
    '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
)
_SHEET = (
    '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
    'main"><sheetData>'
    '<row r="1"><c r="A1" t="inlineStr"><is><t>rsID</t></is></c>'
    '<c r="B1" t="inlineStr"><is><t>CHR</t></is></c>'
    '<c r="C1" t="inlineStr"><is><t>BP</t></is></c>'
    '<c r="D1" t="inlineStr"><is><t>BETA</t></is></c></row>'
    '<row r="2"><c r="A2" t="inlineStr"><is><t>rs1801133</t></is></c>'
    '<c r="D2"><v>-0.0154</v></c></row>'
    '<row r="3"><c r="A3" t="inlineStr"><is><t>rs6859</t></is></c><c r="B3"><v>19</v></c>'
    '<c r="C3"><v>44878777</v></c><c r="D3"><v>0.112</v></c></row>'
    # Trailing cells simply absent — the row ends after B, and the sheet is 4 wide.
    '<row r="4"><c r="A4" t="inlineStr"><is><t>rs429358</t></is></c><c r="B4"><v>19</v></c></row>'
    '<row r="5"/><row r="6"/>'
    "</sheetData></worksheet>"
)


def _degenerate_workbook(tmp_path: Path) -> Path:
    book = tmp_path / "esm.xlsx"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", _WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/worksheets/sheet1.xml", _SHEET)
    return book


def test_a_sparse_row_keeps_its_columns_instead_of_shifting_left(tmp_path: Path) -> None:
    """The bug that made a hand-rolled reader worse than no reader at all.

    Row 2 writes cells `A2` and `D2` and nothing between them. A reader that takes
    the cells in order puts `-0.0154` in the second column, so an author zipping
    against the header records the BETA as the chromosome — well-formed, plausible
    and wrong. Every row comes back padded to the sheet's width, in position.
    """
    window = S.workbook_rows(_degenerate_workbook(tmp_path), "ST9")
    assert window.rows[0] == ["rsID", "CHR", "BP", "BETA"]
    assert window.rows[1] == ["rs1801133", None, None, -0.0154]
    assert window.rows[2] == ["rs6859", 19, 44878777, 0.112]
    # And the other half of the same shape, which is OURS rather than the reader's:
    # a row whose TRAILING cells are absent arrives short, and a caller zipping it
    # against the header gets a row two columns wide with no indication why.
    assert window.rows[3] == ["rs429358", 19, None, None]
    assert all(len(row) == window.width for row in window.rows)


def test_the_counts_are_streamed_rather_than_read_off_the_dimension_record(
    tmp_path: Path,
) -> None:
    """This fixture has **no** `<dimension>` element, which is legal and common.

    `max_row` and `max_column` are read from that record, so a reader trusting them
    gets `1` or `None` here and truncates the sheet without saying so. Both counts
    are taken while streaming instead.

    `last_populated_row` is the other half: rows 5 and 6 exist and are empty, so the
    sheet spans six rows and holds four. A caller paging on the span alone spends
    the difference on nothing — measured at 734 wasted rows on one real workbook.
    """
    window = S.workbook_rows(_degenerate_workbook(tmp_path), "ST9")
    assert window.width == 4
    assert window.total_rows == 6
    assert window.last_populated_row == 3


def test_the_window_pages_and_the_offset_is_not_reindexed(tmp_path: Path) -> None:
    """An offset returns the sheet's own rows, never a renumbered view of them."""
    window = S.workbook_rows(_degenerate_workbook(tmp_path), "ST9", offset=2, limit=1)
    assert window.rows == [["rs6859", 19, 44878777, 0.112]]
    assert window.total_rows == 6, "the counts describe the sheet, not the window"


def test_a_wrong_sheet_name_lists_the_real_ones_rather_than_guessing(tmp_path: Path) -> None:
    """`ST9` and `Supplementary Table S9` are both plausible and only one is a sheet."""
    with pytest.raises(S.SupplementaryError) as raised:
        S.workbook_rows(_degenerate_workbook(tmp_path), "Supplementary Table S9")
    assert "ST9" in str(raised.value)


def test_a_pdf_supplement_is_this_readers_limit_and_says_so(tmp_path: Path) -> None:
    """The distinction the whole module exists for, one rung further down.

    A PDF has rows a person can read. Reporting "no rows" would record our own
    limit as a fact about the file, which is what `not_determinable` versus
    `none_published` keeps apart at the inventory rung.
    """
    pdf = tmp_path / "esm.pdf"
    pdf.write_bytes(b"%PDF-1.4 not a zip")
    with pytest.raises(S.SupplementaryError) as raised:
        S.workbook_rows(pdf, "ST9")
    message = str(raised.value)
    assert "not a statement that the file has no rows" in message


async def test_the_tool_reports_truncation_against_populated_rows(make_client, tmp_path) -> None:
    """Trailing blank rows must not make every sheet report as truncated.

    Four populated rows and two blank ones: a window of two is genuinely short, and
    a window of four is complete even though the sheet spans six.
    """
    book = _degenerate_workbook(tmp_path)
    async with make_client(offline_settings()) as client:
        short = await client.call_tool(
            "read_supplementary", {"path": str(book), "sheet": "ST9", "limit": 2}
        )
        whole = await client.call_tool(
            "read_supplementary", {"path": str(book), "sheet": "ST9", "limit": 4}
        )
    assert short.data.truncated is True
    assert whole.data.truncated is False, (
        "rows 5 and 6 are blank; counting them as outstanding would report every "
        "sheet with trailing padding as incomplete forever"
    )
    assert whole.data.sheets_available == ["ST9"]


# --------------------------------------------------------------------------- #
# F114: every URL handed out is one a host serves
# --------------------------------------------------------------------------- #
#: The real PLOS article F114 was re-probed on, and the Nature Genetics one whose
#: MOESM names Springer's store serves.
_PLOS_DOI = "10.1371/journal.pgen.1006528"
_NATURE_DOI = "10.1038/s41588-019-0358-2"
_PLOS_STORE = "https://storage.googleapis.com/plos-corpus-prod/10.1371/journal.pgen.1006528/1"


def _host(routes: dict[str, httpx.Response], monkeypatch) -> HttpService:
    """A paced service whose transport answers from ``routes`` (full URL → response),
    404 for anything else, and records what it was asked."""
    monkeypatch.setattr(net, "_JITTER", lambda _state: 0.0)

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append((request.method, str(request.url)))
        return routes.get(str(request.url), httpx.Response(404))

    asked: list[tuple[str, str]] = []
    service = HttpService(name="fake", base_url=S.ESM_HOST, gate=ServiceGate(interval=0.0))
    service._client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    service.asked = asked  # type: ignore[attr-defined]
    return service


def _plos_redirect(index: str, extension: str) -> dict[str, httpx.Response]:
    target = f"{_PLOS_STORE}/pgen.1006528.{index}.{extension}"
    return {
        S.plos_url(_PLOS_DOI, index): httpx.Response(302, headers={"location": target}),
        target: httpx.Response(200, headers={"content-length": "37084"}),
    }


def test_a_jats_name_is_addressed_on_the_publishers_host_never_europe_pmcs() -> None:
    springer = S.resolve_url(_NATURE_DOI, "41588_2019_358_MOESM3_ESM.xlsx")
    plos = S.resolve_url(_PLOS_DOI, "pgen.1006528.s002.docx")
    assert springer == (
        f"{S.ESM_HOST}/esm/art%3A10.1038%2Fs41588-019-0358-2/MediaObjects/"
        "41588_2019_358_MOESM3_ESM.xlsx"
    )
    assert plos == S.plos_url(_PLOS_DOI, "s002")
    # Elsevier: no host we can address, so no URL rather than a guessed one.
    assert S.resolve_url("10.1016/j.ajhg.2018.11.008", "mmc2.xlsx") is None


def test_the_xml_rung_keeps_a_file_no_host_serves_but_hands_out_no_url_for_it(
    monkeypatch,
) -> None:
    """Listed-but-unservable is still `found`: dropping the file would turn *we
    cannot fetch it* into *the paper has none*, which this module exists to refuse."""
    xml = "".join(
        f'<supplementary-material><media xlink:href="pgen.1006528.{i}.docx"/>'
        "</supplementary-material>"
        for i in ("s001", "s002")
    )
    served = _plos_redirect("s002", "docx")
    probe = _host(served, monkeypatch)
    result = S.inventory(
        doi=_PLOS_DOI,
        xml=xml,
        xml_base_url="https://europepmc.org/articles/PMC5407576/bin",
        probe=probe,
    )
    assert result.verdict == "found"
    assert [f.name for f in result.files] == ["pgen.1006528.s001.docx", "pgen.1006528.s002.docx"]
    assert [f.url for f in result.files] == [None, S.plos_url(_PLOS_DOI, "s002")]
    assert result.files[1].size_bytes == 37084
    assert any("1 of 2" in n for n in result.notes)
    # Checked by HEAD, and nothing was asked of Europe PMC's file links.
    assert {m for m, _ in probe.asked} == {"HEAD"}  # type: ignore[attr-defined]
    assert not any("europepmc.org" in u for _, u in probe.asked)  # type: ignore[attr-defined]


def test_the_plos_pattern_rung_names_files_from_where_plos_redirects(monkeypatch) -> None:
    routes = {**_plos_redirect("s001", "xlsx"), **_plos_redirect("s002", "docx")}
    result = S.inventory(
        doi=_PLOS_DOI, xml=None, xml_base_url=None, probe=_host(routes, monkeypatch)
    )
    assert result.verdict == "found"
    assert result.rung == "publisher_pattern"
    assert result.publisher == "PLOS"
    assert [(f.name, f.extension) for f in result.files] == [
        ("pgen.1006528.s001.xlsx", "xlsx"),
        ("pgen.1006528.s002.docx", "docx"),
    ]


def test_an_unreachable_plos_is_not_determinable_never_none_published(monkeypatch) -> None:
    monkeypatch.setattr(net, "_JITTER", lambda _state: 0.0)

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    probe = HttpService(name="fake", base_url=S.ESM_HOST, gate=ServiceGate(interval=0.0))
    probe._client = httpx.Client(transport=httpx.MockTransport(down))
    result = S.inventory(doi=_PLOS_DOI, xml=None, xml_base_url=None, probe=probe)
    assert result.verdict == "not_determinable"
    assert result.files == []


def _fetch_with(routes: dict[str, httpx.Response], url: str, monkeypatch, tmp_path: Path):
    services = build_services(offline_settings(workspace=str(tmp_path)))
    service = _host(routes, monkeypatch)
    service.name = (
        "publisher_esm" if url.startswith(S.ESM_HOST) else (f"supplementary:{httpx.URL(url).host}")
    )
    services.register(service)
    return research._supplementary_fetch(services, url)


def test_a_404_off_springers_store_is_not_explained_as_a_403(monkeypatch, tmp_path) -> None:
    """F114: the fetch note said *"HTTP 404. On this host a 403 means no such object"*."""
    url = "https://europepmc.org/articles/PMC5407576/bin/pgen.1006528.s002.docx"
    got = _fetch_with({}, url, monkeypatch, tmp_path)
    assert got.retrieved is False
    assert "HTTP 404 from europepmc.org" in (got.note or "")
    assert "403" not in (got.note or "")


def test_a_plos_file_is_fetched_under_its_real_name(monkeypatch, tmp_path) -> None:
    got = _fetch_with(
        _plos_redirect("s002", "docx"), S.plos_url(_PLOS_DOI, "s002"), monkeypatch, tmp_path
    )
    assert got.retrieved is True
    assert got.path is not None and got.path.endswith("pgen.1006528.s002.docx")


def test_a_bot_challenge_page_is_not_saved_as_the_file(monkeypatch, tmp_path) -> None:
    url = "https://pmc.ncbi.nlm.nih.gov/articles/instance/5407576/bin/pgen.1006528.s002.docx"
    page = httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text="<html/>")
    got = _fetch_with({url: page}, url, monkeypatch, tmp_path)
    assert got.retrieved is False
    assert got.path is None
    assert "web page" in (got.note or "")
