"""F108: PMC BioC as the fulltext rung after Europe PMC.

Fixtures are trimmed from the real BioC answer for PMC6463297 (Kunkle 2019, PMID
30820047), the paper whose per-locus rows live only in Tables 1 and 2 and whose
Europe PMC fulltext answered HTTP 500.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from conftest import offline_settings

from just_module_creator import discovery
from just_module_creator.discovery import PMC_BIOC, Discovery, fulltext, parse_bioc
from just_module_creator.net import ServiceUnavailable, build_services

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "literature"
BIOC = (ASSETS / "pmc_bioc_PMC6463297.json").read_text()
NOT_FOUND = (ASSETS / "pmc_bioc_not_found.txt").read_text()
ABSTRACT = "Risk for late-onset Alzheimer's disease (LOAD) is partially driven by genetics."


def test_the_tables_survive_and_the_reference_list_does_not() -> None:
    text = parse_bioc(BIOC)
    assert text is not None
    assert text.startswith("Genetic meta-analysis of diagnosed Alzheimer")
    assert "[Table" in text and "Major/minor alleles" in text
    assert "\t" in text  # cells stay separable

    ref = next(
        p["text"]
        for p in json.loads(BIOC)[0]["documents"][0]["passages"]
        if p["infons"].get("section_type") == "REF"
    )
    assert ref and ref not in text


def test_no_copy_at_pmc_is_an_answer_not_text() -> None:
    assert NOT_FOUND.startswith("[Error]")
    assert parse_bioc(NOT_FOUND) is None


class _EuropePmc:
    """Europe PMC as it answered for this paper: a record with a PMCID, no fulltext."""

    def lookup(self, pmids: list[str]) -> dict:
        return {p: {"pmcid": "PMC6463297", "abstract": ABSTRACT} for p in pmids}

    def fulltext(self, pmcid: str) -> None:
        return None


class _Bioc:
    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def get(self, path: str, params=None) -> httpx.Response:
        self.asked.append(path)
        if isinstance(self.answer, Exception):
            raise self.answer
        return httpx.Response(200, text=self.answer)


def _services(monkeypatch, bioc: _Bioc):
    services = build_services(offline_settings())
    services.lookup_clients.europepmc = _EuropePmc()  # type: ignore[assignment]
    real = Discovery.service

    def service(self, name):
        return bioc if name == PMC_BIOC else real(self, name)

    monkeypatch.setattr(Discovery, "service", service)
    return services


def test_a_europe_pmc_miss_is_read_from_pmc_bioc(monkeypatch) -> None:
    bioc = _Bioc(BIOC)
    result = fulltext(
        _services(monkeypatch, bioc), pmid="30820047", pmcid=None, doi=None, max_chars=None
    )
    assert bioc.asked == ["BioC_json/PMC6463297/unicode"]
    assert result.text_source == "pmc_bioc"
    assert result.retrieved and result.text and "Major/minor alleles" in result.text


def test_no_copy_at_pmc_falls_to_the_named_abstract(monkeypatch) -> None:
    result = fulltext(
        _services(monkeypatch, _Bioc(NOT_FOUND)),
        pmid="30820047",
        pmcid=None,
        doi=None,
        max_chars=None,
    )
    assert result.text_source == "abstract" and result.text == ABSTRACT
    assert not any("PMC BioC could not be asked" in f.message for f in result.findings)


def test_an_unreachable_bioc_is_unchecked_not_no(monkeypatch) -> None:
    down = _Bioc(ServiceUnavailable(PMC_BIOC, "HTTP 503"))
    result = fulltext(
        _services(monkeypatch, down), pmid="30820047", pmcid=None, doi=None, max_chars=None
    )
    assert result.text_source == "abstract"
    warned = [f.message for f in result.findings if "PMC BioC could not be asked" in f.message]
    assert len(warned) == 1 and "HTTP 503" in warned[0] and "UNCHECKED" in warned[0]


def test_bioc_spends_the_shared_ncbi_budget() -> None:
    services = build_services(offline_settings())
    assert Discovery(services=services).service(PMC_BIOC).gate is services.ncbi_gate
    assert discovery.SOURCES[PMC_BIOC].base_url.startswith("https://www.ncbi.nlm.nih.gov/")


@pytest.mark.parametrize("raw", ["PMC6463297", "pmc6463297"])
def test_the_accession_is_normalised_before_asking(monkeypatch, raw: str) -> None:
    bioc = _Bioc(BIOC)
    fulltext(_services(monkeypatch, bioc), pmid=None, pmcid=raw, doi=None, max_chars=None)
    assert bioc.asked == ["BioC_json/PMC6463297/unicode"]
