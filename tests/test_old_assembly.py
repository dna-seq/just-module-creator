"""`lookup_old_assembly`: which rs-number GRCh37 dbSNP records at an hg19 coordinate.

The service is answered by a mock transport from a reply captured live
(`assets/grch37_replies/README.md`), so upstream's own anchoring and filtering run on the shape the
service sends. The reply carries an HGMD record beside rs429358 at the same position, which is
what makes the rs-number filter something that could fail.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastmcp.exceptions import ToolError
from just_dna_enricher.grch37 import Grch37Client

from just_module_creator.settings import Settings
from just_module_creator.tools import research

REPLIES = Path(__file__).resolve().parent.parent / "assets" / "grch37_replies"
APOE_E4 = json.loads((REPLIES / "overlap_19_45411941.json").read_text())


def _online() -> Settings:
    return Settings(offline=False, _env_file=None, api_key=None)  # type: ignore[call-arg]


def _serving(monkeypatch, reply: object) -> list[str]:
    """Hand the server a GRCh37 client whose transport answers every request with `reply`."""
    asked: list[str] = []

    def _answer(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        return httpx.Response(200, json=reply)

    monkeypatch.setattr(
        research,
        "new_grch37_client",
        lambda: Grch37Client(_client=httpx.Client(transport=httpx.MockTransport(_answer))),
    )
    return asked


async def test_the_rs_number_at_an_hg19_position_comes_back_without_the_hgmd_record(
    make_client, monkeypatch
):
    ids = [record["id"] for record in APOE_E4]
    assert "rs429358" in ids and any(not i.startswith("rs") for i in ids), (
        "the fixture must carry a record that is not an rs-number, or the filter is untested"
    )
    asked = _serving(monkeypatch, APOE_E4)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool(
            "lookup_old_assembly", {"chrom": "19", "start": 45411941, "ref": "T", "alts": "C"}
        )
    payload = result.structured_content or {}
    assert payload["outcome"] == "recovered"
    assert payload["rsids"] == ["rs429358"]
    assert "author that rs-number instead of the coordinate" in payload["message"]
    assert asked and "19:45411941-45411941" in asked[0]


async def test_a_position_dbsnp_does_not_record_is_none_not_unchecked(make_client, monkeypatch):
    _serving(monkeypatch, [])
    async with make_client(settings=_online()) as client:
        result = await client.call_tool("lookup_old_assembly", {"chrom": "1", "start": 1})
    payload = result.structured_content or {}
    assert payload["outcome"] == "none" and payload["rsids"] == []


async def test_an_offline_server_reports_unchecked_and_asks_nothing(make_client, monkeypatch):
    asked = _serving(monkeypatch, APOE_E4)
    settings = Settings(offline=True, _env_file=None, api_key=None)  # type: ignore[call-arg]
    async with make_client(settings=settings) as client:
        result = await client.call_tool("lookup_old_assembly", {"chrom": "19", "start": 45411941})
    payload = result.structured_content or {}
    assert payload["outcome"] == "skipped_offline"
    assert payload["rsids"] == []
    assert asked == []


async def test_one_client_serves_every_call(make_client, monkeypatch):
    """Upstream: hold one per session, or its pacing gate is thrown away on every question."""
    built: list[Grch37Client] = []

    def _build() -> Grch37Client:
        client = Grch37Client(
            _client=httpx.Client(
                transport=httpx.MockTransport(lambda r: httpx.Response(200, json=APOE_E4))
            )
        )
        built.append(client)
        return client

    monkeypatch.setattr(research, "new_grch37_client", _build)
    async with make_client(settings=_online()) as client:
        for _ in range(3):
            await client.call_tool("lookup_old_assembly", {"chrom": "19", "start": 45411941})
    assert len(built) == 1


async def test_a_position_below_one_is_refused_before_any_request(make_client, monkeypatch):
    asked = _serving(monkeypatch, APOE_E4)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match="1-based"):
            await client.call_tool("lookup_old_assembly", {"chrom": "19", "start": 0})
    assert asked == []
