"""F113 bandaid: a DOI looked up on its own comes back with the paper's title.

Upstream's DOI branch (format-tree `S113`) asks Crossref whether the DOI exists and
drops the record. Delete this file with `crossref_work` and `_crossref_identity`
when a release we install fills `title` on the DOI path.

The fixture is Crossref's real `/works/10.1038/ng826` record, trimmed to the fields
read: Enattah 2002, PMID 11788828.
"""

from __future__ import annotations

import httpx
import pytest
from conftest import offline_settings
from just_dna_enricher.lookup import CitationHint

from just_module_creator import discovery, net
from just_module_creator.discovery import CROSSREF, crossref_work
from just_module_creator.net import HttpService, ServiceGate, ServiceUnavailable, build_services
from just_module_creator.settings import Settings
from just_module_creator.tools import research

DOI = "10.1038/ng826"
TITLE = "Identification of a variant associated with adult-type hypolactasia"
WORK = {
    "status": "ok",
    "message-type": "work",
    "message": {
        "DOI": DOI,
        "title": [TITLE],
        "container-title": ["Nature Genetics"],
        "issued": {"date-parts": [[2002, 1, 14]]},
        "author": [
            {"given": "Nabil Sabri", "family": "Enattah"},
            {"given": "Timo", "family": "Sahi"},
        ],
        "URL": "https://doi.org/10.1038/ng826",
    },
}


def test_one_works_record_parses_to_the_paper_it_names(monkeypatch) -> None:
    monkeypatch.setattr(net, "_JITTER", lambda _state: 0.0)
    asked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.path)
        return httpx.Response(200, json=WORK)

    fake = HttpService(name=CROSSREF, base_url="https://api.crossref.org", gate=ServiceGate(0.0))
    fake._client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(discovery.Discovery, "service", lambda self, name: fake)

    work = crossref_work(build_services(offline_settings()), DOI)
    assert asked == [f"/works/{DOI}"]
    assert work is not None
    assert (work.title, work.venue, work.year) == (TITLE, "Nature Genetics", 2002)
    assert work.authors[0] == "Nabil Sabri Enattah"


def _online() -> Settings:
    return Settings(offline=False, api_key=None, _env_file=None)  # type: ignore[call-arg]


def _upstream_says_it_exists(monkeypatch) -> None:
    """What enricher 0.7.2 returns for a bare DOI: existence and nothing else."""

    def lookup_citation(*, pmid, doi, offline, clients):
        return CitationHint(pmid=pmid, doi=doi, doi_exists=True)

    monkeypatch.setattr(research.enricher_lookup, "lookup_citation", lookup_citation)


async def test_a_bare_doi_gets_crossrefs_title_and_says_who_answered(
    make_client, monkeypatch
) -> None:
    _upstream_says_it_exists(monkeypatch)
    monkeypatch.setattr(
        research,
        "crossref_work",
        lambda services, doi: discovery.parse_crossref({"message": {"items": [WORK["message"]]}})[
            0
        ],
    )
    async with make_client(_online()) as client:
        data = (await client.call_tool("lookup_citation", {"doi": DOI})).data

    assert data.title == TITLE
    assert (data.journal, data.year, data.first_author) == (
        "Nature Genetics",
        "2002",
        "Nabil Sabri Enattah",
    )
    # A PMID is never filled from the DOI's record.
    assert data.pmid is None
    notes = [f for f in data.findings if f.source == "just-module-creator"]
    assert len(notes) == 1 and "Crossref" in notes[0].message


async def test_a_crossref_outage_leaves_the_title_null_and_says_so(
    make_client, monkeypatch
) -> None:
    _upstream_says_it_exists(monkeypatch)

    def down(services, doi):
        raise ServiceUnavailable(CROSSREF, "HTTP 503")

    monkeypatch.setattr(research, "crossref_work", down)
    async with make_client(_online()) as client:
        data = (await client.call_tool("lookup_citation", {"doi": DOI})).data

    assert data.title is None
    assert any("could not be asked" in f.message for f in data.findings)


@pytest.mark.parametrize("args", [{"doi": DOI, "offline": True}, {"doi": DOI, "pmid": "11788828"}])
async def test_crossref_is_not_asked_offline_or_when_a_pmid_names_the_paper(
    make_client, monkeypatch, args
) -> None:
    _upstream_says_it_exists(monkeypatch)
    asked: list[str] = []
    monkeypatch.setattr(research, "crossref_work", lambda services, doi: asked.append(doi))
    async with make_client(_online()) as client:
        data = (await client.call_tool("lookup_citation", args)).data
    assert data.doi == DOI  # the call ran; the absence below is about a real response
    assert asked == []
