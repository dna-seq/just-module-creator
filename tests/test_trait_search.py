"""`search_trait_terms` — a trait CURIE picked from candidates rather than recalled (RM28).

The payloads are the shape OLS4's `/api/search` returned on 2026-11-16 for the case RM28 records:
"lifespan" finds the current `OBA_VT0005372` ("life span determination trait"), and "longevity"
finds the current `EFO_0007796`, which is "parental longevity" and the wrong trait for a lifespan
module, beside the obsolete `EFO_0004300`, whose record points to `OBA_VT0005372`. Frozen here,
because a test that needs the network reports an outage as a defect.
"""

from __future__ import annotations

import re

import httpx
import pytest
from conftest import offline_settings
from fastmcp.exceptions import ToolError
from just_dna_enricher.identifiers import TraitStatus
from just_dna_format.spec import StudyRow

from just_module_creator import traitsearch
from just_module_creator.net import HttpService, ServiceGate
from just_module_creator.settings import Settings


def _docs(*docs: dict, found: int | None = None) -> dict:
    return {"response": {"numFound": len(docs) if found is None else found, "docs": list(docs)}}


_CURRENT = _docs(
    {
        "short_form": "EFO_0007796",
        "label": "parental longevity",
        "ontology_prefix": "EFO",
        "description": [
            "length of an individual's parents' life, either taken individually (paternal or "
            "maternal longevity) or in combination and sometimes used as an indicator of an "
            "individual longevity"
        ],
    },
    {
        "short_form": "MONDO_0015903",
        "label": "hyperalphalipoproteinemia",
        "ontology_prefix": "MONDO",
    },
    found=6,
)
_OBSOLETE = _docs(
    {
        "short_form": "EFO_0004300",
        "label": "obsolete_longevity",
        "ontology_prefix": "EFO",
        "description": ["The  length of time of an organism's life."],
    }
)


def _service(handler) -> HttpService:
    """A real `HttpService` over a mock transport: the code under test is the whole call path."""
    service = HttpService(
        name="ols4_search", base_url=traitsearch.OLS4_BASE, gate=ServiceGate(interval=0.0)
    )
    service._client = httpx.Client(transport=httpx.MockTransport(handler))  # noqa: SLF001
    return service


def _ols(current: dict | int, obsolete: dict | int, asked: list[httpx.Request]):
    """Answer by whether `obsoletes=true` was sent; an int is an HTTP status to fail with."""

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        payload = obsolete if request.url.params.get("obsoletes") == "true" else current
        if isinstance(payload, int):
            return httpx.Response(payload)
        return httpx.Response(200, json=payload)

    return handler


def _successor(curie: str) -> TraitStatus:
    assert curie == "EFO_0004300", curie
    return TraitStatus(
        curie=curie, state="obsolete", label="obsolete_longevity", replaced_by="OBA_VT0005372"
    )


def test_obsolete_terms_are_kept_with_their_successor() -> None:
    """RM28's case: the obsolete record is the one that names the right term."""
    asked: list[httpx.Request] = []
    result = traitsearch.search(
        _service(_ols(_CURRENT, _OBSOLETE, asked)), "longevity", successor=_successor
    )

    assert result.current is not None and result.obsolete is not None
    assert [h.curie for h in result.current] == ["EFO_0007796", "MONDO_0015903"]
    assert result.current[0].description is not None
    assert result.current[0].description.startswith("length of an individual's parents' life")
    assert result.current_found == 6
    (gone,) = result.obsolete
    assert (gone.curie, gone.state, gone.replaced_by) == (
        "EFO_0004300",
        "obsolete",
        "OBA_VT0005372",
    )
    assert gone.replacement_checked == "obsolete"
    # Two searches, one of them for obsolete terms, both on the defining ontology only.
    assert sorted(str(r.url.params.get("obsoletes")) for r in asked) == ["None", "true"]
    assert {r.url.params["isDefiningOntology"] for r in asked} == {"true"}
    assert {r.url.params["ontology"] for r in asked} == {"efo,mondo,oba,hp"}


def test_a_failed_half_is_unknown_never_empty() -> None:
    """The obsolete search failing must not read as 'no obsolete term exists'."""
    asked: list[httpx.Request] = []
    result = traitsearch.search(
        _service(_ols(_CURRENT, 404, asked)), "longevity", successor=_successor
    )

    assert result.current is not None and len(result.current) == 2
    assert result.obsolete is None
    assert result.obsolete_found is None
    assert len(result.failures) == 1 and result.failures[0].startswith("obsolete terms:")


def test_an_unreadable_answer_is_a_failure_not_an_empty_result() -> None:
    asked: list[httpx.Request] = []
    result = traitsearch.search(
        _service(_ols({"unexpected": True}, _OBSOLETE, asked)), "longevity", successor=_successor
    )
    assert result.current is None
    assert any("no `response` block" in f for f in result.failures)


def test_the_default_ontologies_are_the_ones_the_format_names() -> None:
    """A fact this repo cannot generate, compared with the format's own field description.

    The description is prose ("EFO/MONDO/OBA/HP trait ontology id(s)..."), so the anchor is
    read first: if the prefixes ever left it, this fails on the anchor rather than passing on
    an empty set.
    """
    description = StudyRow.model_fields["trait_efo_id"].description or ""
    named = set(re.findall(r"\b([A-Z]{2,})\b", description.split(" trait", 1)[0]))
    assert "EFO" in named, description
    assert {o.upper() for o in traitsearch.DEFAULT_ONTOLOGIES} == named


async def test_the_tool_returns_both_halves_and_says_how_to_choose(
    make_client, monkeypatch
) -> None:
    from just_module_creator.tools import research

    asked: list[httpx.Request] = []
    service = _service(_ols(_CURRENT, _OBSOLETE, asked))
    monkeypatch.setattr(research, "_ols_service", lambda _services: service)
    monkeypatch.setattr(research.enricher_lookup, "lookup_trait", _successor)

    networked = Settings(offline=False, _env_file=None)  # type: ignore[call-arg]
    async with make_client(networked) as client:
        result = await client.call_tool(
            "search_trait_terms", {"query": "longevity", "ontologies": ["EFO", "oba"], "limit": 5}
        )
    report = result.data
    assert report.ontologies == ["efo", "oba"]
    assert {r.url.params["ontology"] for r in asked} == {"efo,oba"}
    assert {r.url.params["rows"] for r in asked} == {"5"}
    assert [t.curie for t in report.current] == ["EFO_0007796", "MONDO_0015903"]
    assert report.obsolete[0].replaced_by == "OBA_VT0005372"
    assert "lookup_identifier" in report.next_step
    assert "not by position" in report.next_step


async def test_both_halves_failing_says_nothing_about_existence(make_client, monkeypatch) -> None:
    from just_module_creator.tools import research

    asked: list[httpx.Request] = []
    # 4xx rather than 5xx: a 5xx is retried with backoff, which would only slow the test.
    service = _service(_ols(404, 404, asked))
    monkeypatch.setattr(research, "_ols_service", lambda _services: service)
    networked = Settings(offline=False, _env_file=None)  # type: ignore[call-arg]
    async with make_client(networked) as client:
        result = await client.call_tool("search_trait_terms", {"query": "longevity"})
    report = result.data
    assert report.current is None and report.obsolete is None
    assert len(report.failures) == 2
    assert "says nothing about whether a term exists" in report.next_step


async def test_the_tool_refuses_offline(make_client) -> None:
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError):
            await client.call_tool("search_trait_terms", {"query": "longevity"})


def test_the_service_is_built_once_on_its_own_gate() -> None:
    from just_module_creator.tools import research

    class _Services:
        def __init__(self) -> None:
            self._extra: list[HttpService] = []

        def register(self, service: HttpService) -> HttpService:
            self._extra.append(service)
            return service

        def contact_email(self) -> str:
            return "someone@example.org"

    services = _Services()
    first = research._ols_service(services)  # type: ignore[arg-type]
    assert research._ols_service(services) is first  # type: ignore[arg-type]
    assert len(services._extra) == 1
    assert first.base_url == traitsearch.OLS4_BASE
