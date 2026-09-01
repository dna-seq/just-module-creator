"""Turning a constructed HGVS expression into an allele identity, and the traps.

Real identifiers throughout: `NM_000551.3` is VHL, `CA020450` is the allele
`c.499C>T` names, and the two insertion spellings are the pair upstream's
`IDENTITY_FROM_A_NAME` handout measured. Every payload here is the shape the
ClinGen Allele Registry actually returns — verified against the live service on
2026-09-01 and then frozen, because a test that needs the network is a test that
reports an outage as a defect.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from conftest import offline_settings

from just_module_creator import alleles
from just_module_creator.net import HttpService, ServiceGate, ServiceUnavailable
from just_module_creator.settings import Settings


class _Canned:
    """An `HttpService` stand-in. Only `probe` is used, which is the contract."""

    name = "clingen_allele_registry"

    def __init__(self, by_expression: dict[str, tuple[int, dict[str, Any]]]) -> None:
        self._by = by_expression
        self.asked: list[str] = []

    def probe(self, path: str) -> httpx.Response:
        expression = path.split("hgvs=", 1)[1]
        from urllib.parse import unquote

        expression = unquote(expression)
        self.asked.append(expression)
        if expression not in self._by:
            raise AssertionError(f"unexpected expression: {expression}")
        status, payload = self._by[expression]
        return httpx.Response(status, content=json.dumps(payload).encode())


def _registered(caid: str, title: str | None = None, external: dict | None = None) -> dict:
    """`communityStandardTitle` is a **list**, which is the shape the service sends.

    This fixture said `str` until the tool was run against the live registry and
    the wire model rejected the real answer. Written back this way so the suite
    would have caught it.
    """
    return {
        "@id": f"http://reg.genome.network/allele/{caid}",
        "communityStandardTitle": [title] if title else [],
        "externalRecords": external or {},
        "type": "nucleotide",
    }


#: What the service returns for an allele it does NOT hold: **HTTP 200**, a
#: populated payload, and a blank-node id. Frozen from the live response.
_BLANK = {"@id": "_:CA", "genomicAlleles": [], "transcriptAlleles": [], "type": "nucleotide"}


def test_a_200_with_a_blank_node_is_unregistered_and_not_a_hit() -> None:
    """The negative control that makes every other answer worth anything.

    A classifier keying on the status code records this as resolved — the payload
    is populated and the status is 200. Asserting on the identifier is the whole
    difference between a result set and an artefact of asking.
    """
    service = _Canned({"NM_000551.3:c.301_311del": (200, _BLANK)})
    answer = alleles.lookup_allele(service, "NM_000551.3:c.301_311del")  # type: ignore[arg-type]
    assert answer.outcome == "unregistered"
    assert answer.caid is None
    assert "not evidence the allele does not exist" in (answer.detail or "")


def test_an_incorrect_reference_base_is_evidence_about_direction_not_a_failure() -> None:
    """HTTP 400, and it is the most informative answer the service gives.

    It says which base is actually reference, so the opposite expression is the one
    the locus can host — which is how an inverted ref/alt is caught. Rendering it
    as a failed request throws away the finding.
    """
    payload = {
        "errorType": "IncorrectReferenceAllele",
        "description": "Given allele from reference sequence is incorrect.",
        "givenAllele": "G",
        "actualAllele": "C",
        "referenceSequence": "NC_000003.12",
    }
    service = _Canned({"NC_000003.12:g.10142030G>A": (400, payload)})
    answer = alleles.lookup_allele(service, "NC_000003.12:g.10142030G>A")  # type: ignore[arg-type]
    assert answer.outcome == "reference_mismatch"
    detail = answer.detail or ""
    assert "'C'" in detail and "'G'" in detail, "both bases must survive to the caller"
    assert "opposite expression" in detail


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (400, "HgvsParsingError"),
        (400, "IncorrectHgvsPosition"),
        # A position past the end of the transcript. A 500 that is really a 400 —
        # and the reason this is not left to the retry layer, which would spend
        # the budget three times to learn the same thing.
        (500, "InternalServerError"),
    ],
)
def test_an_unreadable_expression_records_no_negative(status: int, kind: str) -> None:
    """`malformed` is not `unregistered`, and the difference is load-bearing.

    Nothing was asked about an allele, so nothing may be concluded about one. A
    resolver that folds these into "not found" reports its own bad expression as
    evidence the allele does not exist.
    """
    service = _Canned({"NM_000551.3:c.204insG": (status, {"errorType": kind, "description": "x"})})
    answer = alleles.lookup_allele(service, "NM_000551.3:c.204insG")  # type: ignore[arg-type]
    assert answer.outcome == "malformed"
    assert answer.caid is None


def test_an_outage_is_unavailable_rather_than_a_negative() -> None:
    class _Down:
        name = "clingen_allele_registry"

        def probe(self, path: str) -> httpx.Response:
            raise ServiceUnavailable(self.name, "HTTP 503")

    answer = alleles.lookup_allele(_Down(), "NM_000551.3:c.499C>T")  # type: ignore[arg-type]
    assert answer.outcome == "unavailable"
    assert answer.caid is None


def test_two_readings_of_one_legacy_insertion_collapse_to_one_allele() -> None:
    """The step that dissolves the ambiguity for free, before any discriminator.

    `c.204insG` does not say which side of position 204 the base goes. Both
    readings are sent, both come back as `CA913189244`, and there was never a
    choice to make — measured against the live registry, not assumed.
    """
    both = {
        "NM_000551.3:c.204_205insG": (200, _registered("CA913189244")),
        "NM_000551.3:c.203_204insG": (200, _registered("CA913189244")),
    }
    service = _Canned(both)
    answers = [alleles.lookup_allele(service, e) for e in both]  # type: ignore[arg-type]
    ids, note = alleles.collapse(answers)
    assert ids == ["CA913189244"]
    assert note is None, "one allele under two spellings is not an ambiguity to report"


def test_the_registry_titles_in_a_list_and_the_title_survives_as_a_string() -> None:
    """A frozen fixture agreed with itself; the live service did not.

    `communityStandardTitle` comes back as a one-element list on every registered
    allele. The wire model types it `str | None`, so the first live call raised a
    validation error the whole suite had passed over.
    """
    service = _Canned(
        {
            "NM_000551.3:c.499C>T": (
                200,
                _registered("CA020450", "NM_000551.4(VHL):c.499C>T (p.Arg167Trp)"),
            )
        }
    )
    answer = alleles.lookup_allele(service, "NM_000551.3:c.499C>T")  # type: ignore[arg-type]
    assert answer.title == "NM_000551.4(VHL):c.499C>T (p.Arg167Trp)"


def test_two_readings_that_name_different_alleles_are_reported_not_ranked() -> None:
    """Registration does not rank candidates, and this must not pretend it does.

    5 of 11 legacy insertions in the survey had BOTH readings registered. Picking
    one because it came back first is exactly the confident wrong answer the
    procedure exists to avoid — so both ids travel, with what that means.
    """
    service = _Canned(
        {
            "NM_000551.3:c.204_205insG": (200, _registered("CA913189244")),
            "NM_000551.3:c.203_204insG": (200, _registered("CA999000111")),
        }
    )
    answers = [
        alleles.lookup_allele(service, "NM_000551.3:c.204_205insG"),  # type: ignore[arg-type]
        alleles.lookup_allele(service, "NM_000551.3:c.203_204insG"),  # type: ignore[arg-type]
    ]
    ids, note = alleles.collapse(answers)
    assert ids == ["CA913189244", "CA999000111"]
    assert note is not None
    assert "judgement about this row" in note
    assert "Registration alone does not rank them" in note


async def test_the_tool_reports_every_outcome_and_never_ranks_two_alleles(
    make_client, monkeypatch
) -> None:
    """End to end, and the property is that the report carries what it cannot decide."""
    from just_module_creator.tools import research

    canned = _Canned(
        {
            "NM_000551.3:c.204_205insG": (200, _registered("CA913189244")),
            "NM_000551.3:c.203_204insG": (200, _registered("CA999000111")),
            "NM_000551.3:c.301_311del": (200, _BLANK),
        }
    )
    monkeypatch.setattr(research, "_allele_service", lambda _services: canned)

    # Networked settings: the tool refuses under the offline ceiling, and what is
    # under test here is the report rather than the ceiling. No socket opens — the
    # service is canned.
    networked = Settings(offline=False, _env_file=None)  # type: ignore[call-arg]
    async with make_client(networked) as client:
        result = await client.call_tool(
            "lookup_allele_identity",
            {
                "expressions": [
                    "NM_000551.3:c.204_205insG",
                    "NM_000551.3:c.203_204insG",
                    "NM_000551.3:c.301_311del",
                ]
            },
        )
    report = result.data
    assert [a.outcome for a in report.answers] == ["registered", "registered", "unregistered"]
    assert report.collapsed is False
    assert report.distinct_ids == ["CA913189244", "CA999000111"]
    assert report.note is not None


async def test_the_tool_refuses_offline_rather_than_answering_from_nothing(make_client) -> None:
    from fastmcp.exceptions import ToolError

    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "lookup_allele_identity", {"expressions": ["NM_000551.3:c.499C>T"]}
            )


def test_the_service_is_built_once_and_shares_no_budget_with_ncbi() -> None:
    """Its own gate: read-only, credential-free, and not metered against NCBI.

    Built once so a second call reuses the connection pool and the pacing state
    rather than starting a fresh 1/s budget beside the first.
    """
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
    first = research._allele_service(services)  # type: ignore[arg-type]
    second = research._allele_service(services)  # type: ignore[arg-type]
    assert first is second
    assert len(services._extra) == 1
    assert isinstance(first.gate, ServiceGate)
