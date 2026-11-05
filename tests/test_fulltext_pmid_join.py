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
from just_dna_enricher.literature import LiteratureUnavailable

from just_module_creator import discovery
from just_module_creator.discovery import PUBMED, Discovery, fulltext
from just_module_creator.models import OpenAccessResult
from just_module_creator.net import ServiceUnavailable, build_services

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "literature"
ESUMMARY = (ASSETS / "pubmed_esummary_41427385.json").read_text()
PMID = "41427385"
PMCID = "PMC12713140"
DOI = "10.64898/2025.12.04.689698"
TEXT = "Rare longevity-associated variants, including a reduced-function mutation in cGAS"


class _EuropePmc:
    """Europe PMC with no record for the PMID, and the fulltext under the PMCID."""

    def __init__(self, lookup: dict | Exception) -> None:
        self.answer = lookup
        self.fulltext_asked: list[str] = []

    def lookup(self, pmids: list[str]) -> dict:
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def fulltext(self, pmcid: str) -> str | None:
        self.fulltext_asked.append(pmcid)
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


def _services(monkeypatch, epmc: _EuropePmc, pubmed: _PubMed):
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
    said = [f.message for f in result.findings if "PubMed's record supplied" in f.message]
    assert len(said) == 1 and PMCID in said[0] and DOI in said[0]


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
