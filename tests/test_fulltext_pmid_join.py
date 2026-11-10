"""F31 and F50: `fetch_fulltext(pmid=…)` when Europe PMC cannot join the PMID to its PMCID.

The fixture is PubMed's real `esummary` answer for PMID 41427385 (trimmed to two authors):
the bioRxiv preprint with the cGAS work, PMCID PMC12713140, DOI 10.64898/2025.12.04.689698.
When F31 was found Europe PMC's lookup returned no record for that PMID, so the PMCID, the
DOI and the abstract were all lost, while PubMed held both ids.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from conftest import offline_settings
from just_dna_enricher.literature import FulltextUnavailable, LiteratureUnavailable

from just_module_creator import discovery
from just_module_creator.discovery import PUBMED, Discovery, fulltext
from just_module_creator.models import OURS, OpenAccessLocation, OpenAccessResult
from just_module_creator.net import ServiceUnavailable, build_services

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "literature"
ESUMMARY = (ASSETS / "pubmed_esummary_41427385.json").read_text()
PMID = "41427385"
PMCID = "PMC12713140"
DOI = "10.64898/2025.12.04.689698"
TEXT = "Rare longevity-associated variants, including a reduced-function mutation in cGAS"


class _EuropePmc:
    """Europe PMC with no record for the PMID, and the fulltext under the PMCID."""

    def __init__(self, lookup: dict | Exception, down: bool = False) -> None:
        self.answer = lookup
        self.down = down
        self.fulltext_asked: list[str] = []

    def lookup(self, pmids: list[str]) -> dict:
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def fetch_fulltext(self, pmcid: str) -> str | None:
        self.fulltext_asked.append(pmcid)
        if self.down:
            raise FulltextUnavailable(f"Europe PMC could not be reached for {pmcid}: HTTP 500")
        return TEXT if pmcid == PMCID else None


class _PubMed:
    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def get(self, path: str, params=None) -> httpx.Response:
        self.asked.append(path)
        if isinstance(self.answer, Exception):
            raise self.answer
        return httpx.Response(200, text=self.answer)


def _services(monkeypatch, epmc: _EuropePmc, pubmed: _PubMed | _PubMedByPath):
    services = build_services(offline_settings())
    services.lookup_clients.europepmc = epmc  # type: ignore[assignment]
    real = Discovery.service

    def service(self, name):
        return pubmed if name == PUBMED else real(self, name)

    monkeypatch.setattr(Discovery, "service", service)
    return services


def test_the_fixture_is_the_record_f31_was_found_on() -> None:
    assert PMCID in ESUMMARY and DOI in ESUMMARY and f'"{PMID}"' in ESUMMARY


def test_a_europe_pmc_miss_is_joined_through_pubmed(monkeypatch) -> None:
    epmc, pubmed = _EuropePmc({}), _PubMed(ESUMMARY)
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=PMID, pmcid=None, doi=None, max_chars=None
    )
    assert pubmed.asked == ["esummary.fcgi"]
    assert epmc.fulltext_asked == [PMCID]
    assert (result.pmcid, result.doi) == (PMCID, DOI)
    assert result.retrieved and result.text_source == "fulltext" and result.text == TEXT
    said = [f.message for f in result.findings if "PubMed's record of PMID" in f.message]
    assert len(said) == 1 and PMCID in said[0] and DOI in said[0]
    assert {f.source for f in result.findings} == {OURS}  # F120: the join is ours


def test_pubmed_is_not_asked_when_europe_pmc_answered_both(monkeypatch) -> None:
    epmc = _EuropePmc({PMID: {"pmcid": PMCID, "doi": DOI}})
    pubmed = _PubMed(ServiceUnavailable(PUBMED, "must not be asked"))
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=PMID, pmcid=None, doi=None, max_chars=None
    )
    assert pubmed.asked == []
    assert result.text == TEXT


def test_an_unreachable_europe_pmc_is_unchecked_and_pubmed_still_joins(monkeypatch) -> None:
    epmc = _EuropePmc(LiteratureUnavailable("Europe PMC could not be asked: HTTP 503"))
    result = fulltext(
        _services(monkeypatch, epmc, _PubMed(ESUMMARY)),
        pmid=PMID,
        pmcid=None,
        doi=None,
        max_chars=None,
    )
    assert result.text == TEXT
    warned = [f.message for f in result.findings if "Europe PMC could not be asked" in f.message]
    assert len(warned) == 1 and "UNCHECKED" in warned[0]


def test_both_unreachable_is_unchecked_and_names_no_locations(monkeypatch) -> None:
    epmc = _EuropePmc({})
    pubmed = _PubMed(ServiceUnavailable(PUBMED, "HTTP 503"))
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=PMID, pmcid=None, doi=None, max_chars=None
    )
    messages = [f.message for f in result.findings]
    assert not result.retrieved and result.locations == []
    assert any("PubMed could not be asked" in m and "HTTP 503" in m for m in messages)
    nothing = [m for m in messages if m.startswith("Nothing was retrieved")]
    assert len(nothing) == 1
    assert "No DOI is known" in nothing[0]
    assert "Try the locations below" not in nothing[0]
    assert len(messages) >= 3 and {f.source for f in result.findings} == {OURS}  # F120


def test_an_empty_open_access_answer_is_not_called_locations_below(monkeypatch) -> None:
    """F50: the advice pointed at a list the failure had left empty."""
    epmc = _EuropePmc({PMID: {"doi": DOI}})
    monkeypatch.setattr(
        discovery, "open_access", lambda *_a, **_k: OpenAccessResult(doi=DOI, locations=[])
    )
    result = fulltext(
        _services(monkeypatch, epmc, _PubMed(ServiceUnavailable(PUBMED, "HTTP 503"))),
        pmid=PMID,
        pmcid=None,
        doi=None,
        max_chars=None,
    )
    nothing = [f.message for f in result.findings if f.message.startswith("Nothing was retrieved")]
    assert len(nothing) == 1
    assert DOI in nothing[0] and "lookup_open_access" in nothing[0]
    assert "Try the locations below" not in nothing[0]


def test_a_missing_doi_costs_no_request_when_the_text_arrives(monkeypatch) -> None:
    """The DOI is read only when nothing was retrieved, so it is not fetched before."""
    epmc = _EuropePmc({PMID: {"pmcid": PMCID}})
    pubmed = _PubMed(ServiceUnavailable(PUBMED, "must not be asked"))
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=PMID, pmcid=None, doi=None, max_chars=None
    )
    assert result.text == TEXT
    assert pubmed.asked == []


def test_nothing_retrieved_fills_the_doi_and_names_real_locations(monkeypatch) -> None:
    """With a PMCID that yields no text, PubMed is asked once, for the DOI the lookup needs."""
    epmc = _EuropePmc({PMID: {"pmcid": "PMC0000001"}})
    pubmed = _PubMed(ESUMMARY)
    asked: list[str | None] = []
    here = OpenAccessLocation.model_validate({"url": f"https://doi.org/{DOI}"})

    def open_access(*_a, doi=None, **_k):
        asked.append(doi)
        return OpenAccessResult(doi=doi, locations=[here])

    monkeypatch.setattr(discovery, "open_access", open_access)
    monkeypatch.setattr(discovery, "_bioc_fulltext", lambda *_a, **_k: (None, None))
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=PMID, pmcid=None, doi=None, max_chars=None
    )
    assert not result.retrieved
    assert pubmed.asked == ["esummary.fcgi"]
    assert asked == [DOI] and result.doi == DOI
    assert result.locations == [here]
    nothing = [f.message for f in result.findings if f.message.startswith("Nothing was retrieved")]
    assert len(nothing) == 1 and nothing[0].endswith("Try the locations below.")


# --------------------------------------------------------------------------- #
# F122: a DOI is joined to its PMID and PMCID the way a PMID is joined to its DOI
# --------------------------------------------------------------------------- #
class _PubMedByPath:
    """`esearch` answers with the PMID it was given; `esummary` with the real record."""

    def __init__(self, idlist: list[str]) -> None:
        self.idlist = idlist
        self.asked: list[tuple[str, str | None]] = []

    def get(self, path: str, params=None) -> httpx.Response:
        self.asked.append((path, (params or {}).get("term")))
        if path == "esearch.fcgi":
            return httpx.Response(200, json={"esearchresult": {"idlist": self.idlist}})
        return httpx.Response(200, text=ESUMMARY)


def test_a_doi_alone_reaches_the_text_a_pmid_would(monkeypatch) -> None:
    """F122: `fetch_fulltext(doi=…)` came back empty for a paper it returned whole by PMID."""
    epmc, pubmed = _EuropePmc({}), _PubMedByPath([PMID])
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=None, pmcid=None, doi=DOI, max_chars=None
    )
    assert pubmed.asked == [("esearch.fcgi", f'"{DOI}"[doi]'), ("esummary.fcgi", None)]
    assert (result.pmid, result.pmcid) == (PMID, PMCID)
    assert result.retrieved and result.text_source == "fulltext" and result.text == TEXT
    said = [f.message for f in result.findings if f.message.startswith("PubMed's record for DOI")]
    assert len(said) == 1 and PMID in said[0] and PMCID in said[0]
    assert {f.source for f in result.findings} == {OURS}


def test_a_record_whose_doi_is_not_the_one_asked_is_not_taken(monkeypatch) -> None:
    """Existence never settles identity: PubMed's hit must carry the DOI that was asked."""
    other = "10.1038/ng826"
    assert other not in ESUMMARY
    monkeypatch.setattr(
        discovery, "open_access", lambda *_a, **_k: OpenAccessResult(doi=other, locations=[])
    )
    epmc, pubmed = _EuropePmc({}), _PubMedByPath([PMID])
    result = fulltext(
        _services(monkeypatch, epmc, pubmed), pmid=None, pmcid=None, doi=other, max_chars=None
    )
    assert [path for path, _ in pubmed.asked] == ["esearch.fcgi", "esummary.fcgi"]
    assert result.pmid is None and result.pmcid is None and not result.retrieved
    assert epmc.fulltext_asked == []


def test_an_unreachable_pubmed_leaves_the_doi_route_unchecked(monkeypatch) -> None:
    monkeypatch.setattr(
        discovery, "open_access", lambda *_a, **_k: OpenAccessResult(doi=DOI, locations=[])
    )
    epmc = _EuropePmc({})
    result = fulltext(
        _services(monkeypatch, epmc, _PubMed(ServiceUnavailable(PUBMED, "HTTP 503"))),
        pmid=None,
        pmcid=None,
        doi=DOI,
        max_chars=None,
    )
    messages = [f.message for f in result.findings]
    assert not result.retrieved
    warned = [m for m in messages if "which record carries DOI" in m]
    assert len(warned) == 1 and "HTTP 503" in warned[0] and "UNCHECKED" in warned[0]


# --------------------------------------------------------------------------- #
# F133: a Europe PMC outage is named as one; an absent copy is not
# --------------------------------------------------------------------------- #
def _nothing_for_known_pmcid(monkeypatch, epmc: _EuropePmc) -> str:
    monkeypatch.setattr(discovery, "_bioc_fulltext", lambda *_a, **_k: (None, None))
    result = fulltext(
        _services(monkeypatch, epmc, _PubMed(ServiceUnavailable(PUBMED, "must not be asked"))),
        pmid=None,
        pmcid="PMC0000001",
        doi=None,
        max_chars=None,
    )
    assert not result.retrieved and epmc.fulltext_asked == ["PMC0000001"]
    nothing = [f.message for f in result.findings if f.message.startswith("Nothing was retrieved")]
    assert len(nothing) == 1 and nothing[0].endswith("no open-access location was looked up.")
    return nothing[0]


def test_a_europe_pmc_outage_says_to_call_again(monkeypatch) -> None:
    """Europe PMC refuses some `fullTextXML` requests with HTTP 500, so the same call
    retrieves the article on one try and nothing on the next: that is said as an outage."""
    message = _nothing_for_known_pmcid(monkeypatch, _EuropePmc({}, down=True))
    assert "PMC0000001" in message and "HTTP 500" in message and "call again" in message


def test_an_absent_copy_does_not_suggest_calling_again(monkeypatch) -> None:
    """Europe PMC answered that it holds no copy: asking again buys nothing."""
    message = _nothing_for_known_pmcid(monkeypatch, _EuropePmc({}))
    assert "Nothing was retrieved" in message and "call again" not in message


def test_no_pmcid_does_not_suggest_calling_again(monkeypatch) -> None:
    """With no PMCID, nothing was asked of Europe PMC's fulltext, so a retry buys nothing."""
    result = fulltext(
        _services(monkeypatch, _EuropePmc({}), _PubMed(ServiceUnavailable(PUBMED, "HTTP 503"))),
        pmid=PMID,
        pmcid=None,
        doi=None,
        max_chars=None,
    )
    nothing = [f.message for f in result.findings if f.message.startswith("Nothing was retrieved")]
    assert len(nothing) == 1 and "No DOI is known" in nothing[0]
    assert "call again" not in nothing[0]
