"""Registry 0.31's variant-level catalog: `registry_claims`, and `registry_search(pgs_id=)`.

The replies are production's own (`assets/registry_replies/README.md`), so a stub answers in the
shape the server gives. Three readings the tool must never give an answer, each pinned below: an
empty answer read as "no module covers this variant" (it is about the spelling, registry S32), a
`compared` of 0 read as agreement, and a conflict pair read as a verdict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastmcp.exceptions import ToolError
from just_dna_registry import RegistryError
from just_dna_registry.version import VersionInfo

from just_module_creator.settings import Settings
from just_module_creator.tools import research

REPLIES = Path(__file__).resolve().parent.parent / "assets" / "registry_replies"
RS429358 = json.loads((REPLIES / "variant_claims_rs429358.json").read_text())
RS1801133 = json.loads((REPLIES / "variant_claims_rs1801133.json").read_text())
APOE = json.loads((REPLIES / "gene_claims_apoe.json").read_text())

V030 = VersionInfo(registry="0.30.0", format="0.8.4", compiler="0.8.4", mode="test")
V031 = VersionInfo(registry="0.31.0", format="0.8.6", compiler="0.8.6", mode="prod")


class _ClaimsStub:
    """Answers the claims routes and the listing from fixed replies, and records every call."""

    def __init__(
        self,
        *,
        variant: dict | None = None,
        gene: dict | None = None,
        listing: dict | None = None,
        version: VersionInfo | None = V031,
        missing_route: bool = False,
    ) -> None:
        self.variant, self.gene, self.listing = variant, gene, listing
        self.version, self.missing_route = version, missing_route
        self.calls: list[tuple[str, Any]] = []

    def __enter__(self) -> _ClaimsStub:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def _route(self, name: str, arg: object, reply: dict | None) -> dict:
        self.calls.append((name, arg))
        if self.missing_route:
            raise RegistryError(404, "Not Found")
        assert reply is not None, f"the test gave no reply for {name}"
        return reply

    def variant_claims(self, key: str) -> dict:
        return self._route("variant_claims", key, self.variant)

    def gene_claims(self, symbol: str) -> dict:
        return self._route("gene_claims", symbol, self.gene)

    def list_modules(self, **kwargs: object) -> dict:
        self.calls.append(("list_modules", kwargs))
        return self.listing or {"items": [], "total": 0, "page": 1}

    def server_version(self) -> VersionInfo | None:
        self.calls.append(("server_version", None))
        return self.version


def _online() -> Settings:
    return Settings(offline=False, _env_file=None, api_key=None)  # type: ignore[call-arg]


async def _call(make_client, monkeypatch, stub: _ClaimsStub, tool: str, args: dict) -> dict:
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool(tool, args)
    return result.structured_content or {}


async def test_nothing_compared_is_not_read_as_agreement(make_client, monkeypatch):
    """rs429358 on production: five modules, fifteen claim pairs, none comparable for want of a
    trait."""
    assert RS429358["conflicts"] == {"pairs": [], "compared": 0, "incomparable": {"no_trait": 15}}
    stub = _ClaimsStub(variant=RS429358)
    payload = await _call(
        make_client, monkeypatch, stub, "registry_claims", {"target": "prod", "variant": "rs429358"}
    )

    assert payload["conflicts"] == RS429358["conflicts"], "the marker passes through verbatim"
    assert payload["modules"] == RS429358["modules"]
    assert payload["claims_total"] == len(RS429358["claims"]) == 14
    assert payload["truncated"] is False
    assert "could be compared, which is not agreement" in payload["message"]
    assert "no_trait 15" in payload["message"]
    assert "none gives opposite" not in payload["message"]


async def test_a_gene_answer_is_cut_and_says_what_stayed_whole(make_client, monkeypatch):
    """APOE: 57 claims over 8 modules, more than the default limit of 50."""
    stub = _ClaimsStub(gene=APOE)
    payload = await _call(
        make_client, monkeypatch, stub, "registry_claims", {"target": "prod", "gene": "APOE"}
    )

    total = len(APOE["claims"])
    assert total > 50, "the fixture must exceed the default limit to test the cut"
    assert payload["claims_total"] == total
    assert len(payload["claims"]) == 50
    assert payload["truncated"] is True
    assert sum(payload["claims_by_module"].values()) == total
    assert set(payload["claims_by_module"]) == set(APOE["modules"]) == set(payload["modules"])
    assert payload["variants"] == APOE["variants"]
    assert payload["conflicts"] is None, "the gene route computes no marker"
    assert f"shows 50 of {total}" in payload["message"]
    assert "says nothing about whether modules disagree" in payload["message"], (
        "a null marker must not read as nothing to report (F151)"
    )


async def test_the_cut_is_the_same_whatever_order_the_registry_sends(make_client, monkeypatch):
    """A fixed order, so two calls cut at the same rows."""
    reversed_reply = {**APOE, "claims": list(reversed(APOE["claims"]))}
    first = await _call(
        make_client,
        monkeypatch,
        _ClaimsStub(gene=APOE),
        "registry_claims",
        {"target": "prod", "gene": "APOE", "limit": 20},
    )
    second = await _call(
        make_client,
        monkeypatch,
        _ClaimsStub(gene=reversed_reply),
        "registry_claims",
        {"target": "prod", "gene": "APOE", "limit": 20},
    )
    assert first["claims"] == second["claims"]
    assert first["claims"][0]["module"] == min(APOE["modules"])


async def test_an_empty_answer_is_about_the_spelling(make_client, monkeypatch):
    """`RS429358` on production: a well-formed empty answer for a variant five modules cover."""
    empty = {
        "key": "RS429358",
        "variant_keys": ["RS429358"],
        "claims": [],
        "modules": [],
        "conflicts": {"pairs": [], "compared": 0, "incomparable": {}},
        "not_projected": 0,
    }
    payload = await _call(
        make_client,
        monkeypatch,
        _ClaimsStub(variant=empty),
        "registry_claims",
        {"target": "prod", "variant": "RS429358"},
    )
    assert payload["claims_total"] == 0
    assert "under the spelling 'RS429358'" in payload["message"]
    assert "S32" in payload["message"]
    assert "not evidence that no module" in payload["message"]


async def test_two_modules_that_never_meet_on_a_genotype_are_not_called_agreeing(
    make_client, monkeypatch
):
    """rs1801133 on production: two modules, both stating G/G, but only one module's claims are
    `weight` (pharmgkb's are `pharm`, which never enter the marker): nothing compared, nothing
    counted as skipped, and the message must not invent the reason."""
    assert RS1801133["conflicts"] == {"pairs": [], "compared": 0, "incomparable": {}}
    assert len(RS1801133["modules"]) == 2
    payload = await _call(
        make_client,
        monkeypatch,
        _ClaimsStub(variant=RS1801133),
        "registry_claims",
        {"target": "prod", "variant": "rs1801133"},
    )
    assert "the registry gives no reason" in payload["message"]
    assert "That is not agreement." in payload["message"]
    assert "same genotype" not in payload["message"]


def test_a_conflict_pair_is_named_as_a_fact_not_a_verdict() -> None:
    """No live capture holds a pair; this one is built in the shape `services/claims.conflicts`
    writes, and the modules are two real ones that both name rs1801133."""
    pair = {
        "modules": RS1801133["modules"],
        "genotype": "A/G",
        "trait_efo_id": "EFO_0004286",
        "effect_allele": "A",
        "directions": ["risk", "protective"],
    }
    message = research.claims_message(
        asked="variant",
        key="rs1801133",
        total=9,
        shown=9,
        not_projected=2,
        conflicts={"pairs": [pair], "compared": 1, "incomparable": {"other_trait": 3}},
    )
    assert "1 pair(s) of claims from different modules give one allele opposite" in message
    assert "not a verdict on either" in message
    assert "never a reason to change a row" in message
    assert "other_trait 3" in message
    assert "2 visible module(s) have no projection yet" in message


async def test_an_instance_older_than_031_is_named_not_answered_not_found(make_client, monkeypatch):
    """The polygon on registry 0.30.0 answers both routes `HTTP 404: Not Found` (measured
    2026-11-14). Passed on bare, that reads as "this variant is not in the catalog"."""
    stub = _ClaimsStub(missing_route=True, version=V030)
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match="runs registry 0.30.0") as raised:
            await client.call_tool("registry_claims", {"target": "test", "variant": "rs429358"})
    assert "0.31" in str(raised.value)
    assert "Not Found" not in str(raised.value)
    assert "registry_search(gene=" in str(raised.value), "the refusal says what to do instead"


async def test_a_symbol_that_would_address_another_route_is_refused_before_the_call(
    make_client, monkeypatch
):
    """The client puts the symbol into the path unquoted (registry S32)."""
    stub = _ClaimsStub(gene=APOE)
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)
    async with make_client(settings=_online()) as client:
        for symbol in ("APOE/../x", "APOE?y=1", "AP OE", " "):
            with pytest.raises(ToolError, match="not a gene symbol"):
                await client.call_tool("registry_claims", {"target": "prod", "gene": symbol})
        with pytest.raises(ToolError, match="exactly one"):
            await client.call_tool(
                "registry_claims", {"target": "prod", "gene": "APOE", "variant": "rs429358"}
            )
        with pytest.raises(ToolError, match="exactly one"):
            await client.call_tool("registry_claims", {"target": "prod"})
    assert stub.calls == []


async def test_pgs_id_is_not_sent_to_an_instance_that_would_ignore_it(make_client, monkeypatch):
    """A 0.30 server drops `pgs_id` and answers all 47 polygon modules (measured 2026-11-14)."""
    stub = _ClaimsStub(version=V030, listing={"items": [], "total": 47, "page": 1})
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match="runs registry 0.30.0"):
            await client.call_tool("registry_search", {"target": "test", "pgs_id": "PGS000205"})
    assert ("server_version", None) in stub.calls
    assert not [c for c in stub.calls if c[0] == "list_modules"]


async def test_pgs_id_reaches_a_031_instance(make_client, monkeypatch):
    stub = _ClaimsStub(version=V031, listing={"items": [], "total": 1, "page": 1})
    await _call(
        make_client, monkeypatch, stub, "registry_search", {"target": "prod", "pgs_id": "PGS000205"}
    )
    sent = [c[1] for c in stub.calls if c[0] == "list_modules"]
    assert sent and sent[0]["pgs_id"] == "PGS000205"


async def test_a_search_without_pgs_id_costs_no_version_request(make_client, monkeypatch):
    stub = _ClaimsStub(version=V030)
    await _call(make_client, monkeypatch, stub, "registry_search", {"target": "test"})
    assert [c[0] for c in stub.calls] == ["list_modules"]


@pytest.mark.parametrize(
    ("info", "expected"),
    [(V031, True), (V030, False), (None, None), (VersionInfo(registry="dev"), None)],
)
def test_serves_claims_is_three_valued(info: VersionInfo | None, expected: bool | None) -> None:
    assert research.serves_claims(info) is expected
