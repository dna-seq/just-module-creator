"""Amending what a published version's page says, with no version spent: changelog, logo, subtitle.

The readme has its own tests in `test_registry_targets.py`; these cover its two siblings and the
module-level subtitle (F59's open half).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError
from just_dna_registry import RegistryError

from just_module_creator import localstore
from just_module_creator.settings import Settings
from just_module_creator.tools import registry as registry_tools

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _online() -> Settings:
    return Settings(offline=False, _env_file=None, api_key=None)  # type: ignore[call-arg]


def _seed() -> None:
    def _add(state: localstore.State) -> None:
        localstore.save_account(
            state,
            target="test",
            account="sheep",
            token="mk_sheep_aaaa",
            install_id="install-sheep",
            namespaces=["test-sheep"],
        )

    localstore.update(_add)


class _AmendStub:
    def __init__(self, *, refuse_logo: RegistryError | None = None) -> None:
        self.refuse_logo = refuse_logo
        self.calls: list[tuple] = []

    def __call__(self, target, settings, *, token=None, timeout=None):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def amend_changelog(self, namespace, name, version, changelog, *, append=False):
        self.calls.append(("amend_changelog", namespace, name, version, changelog, append))
        return {"changelog": changelog}

    def amend_logo(self, namespace, name, version, logo_path):
        self.calls.append(("amend_logo", namespace, name, version, Path(logo_path).name))
        if self.refuse_logo is not None:
            raise self.refuse_logo
        return {"logo": Path(logo_path).name}

    def set_short_description(self, namespace, name, short_description):
        self.calls.append(("set_short_description", namespace, name, short_description))
        return {"short_description": short_description}


async def _call(make_client, monkeypatch, stub, tool: str, args: dict) -> dict:
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool(tool, args)
    return result.structured_content or {}


MODULE = {"namespace": "test-sheep", "name": "test_fto_bmi"}


async def test_a_changelog_append_reaches_upstream_as_an_append(make_client, monkeypatch):
    _seed()
    stub = _AmendStub()
    payload = await _call(
        make_client,
        monkeypatch,
        stub,
        "registry_amend_version",
        {**MODULE, "version": "0.1.0", "changelog": "Readme caveat added.", "append": True},
    )
    assert stub.calls == [
        ("amend_changelog", "test-sheep", "test_fto_bmi", "0.1.0", "Readme caveat added.", True)
    ]
    assert payload["success"] is True
    assert payload["message"].startswith("Changelog appended to test-sheep/test_fto_bmi@0.1.0")


async def test_a_logo_refused_after_the_changelog_says_the_changelog_landed(
    make_client, monkeypatch, tmp_path
):
    """Two upstream calls, so a refusal of the second must not read as nothing done."""
    _seed()
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    stub = _AmendStub(refuse_logo=RegistryError(413, "logo_too_large"))
    payload = await _call(
        make_client,
        monkeypatch,
        stub,
        "registry_amend_version",
        {**MODULE, "version": "0.1.0", "changelog": "New text.", "logo_path": str(logo)},
    )
    assert [c[0] for c in stub.calls] == ["amend_changelog", "amend_logo"]
    assert payload["success"] is False
    assert "logo_too_large" in payload["message"]
    assert "Already done: changelog replaced on test-sheep/test_fto_bmi@0.1.0" in payload["message"]


@pytest.mark.parametrize(
    ("args", "match"),
    [
        ({}, "Pass `changelog`, `logo_path`, or both"),
        ({"changelog": "  "}, "The changelog is empty"),
        ({"logo_path": str(ASSETS)}, "is not a file"),
    ],
)
async def test_an_amendment_with_nothing_to_send_is_refused_before_any_call(
    make_client, monkeypatch, args, match
):
    _seed()
    stub = _AmendStub()
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match=match):
            await client.call_tool("registry_amend_version", {**MODULE, "version": "0.1.0", **args})
    assert stub.calls == []


@pytest.mark.parametrize(
    ("args", "sent"),
    [
        ({"subtitle": "FTO and body-mass index, one locus"}, "FTO and body-mass index, one locus"),
        ({"subtitle": ""}, ""),
        ({"clear": True}, None),
    ],
)
async def test_clearing_the_subtitle_and_blanking_it_stay_two_requests(
    make_client, monkeypatch, args, sent
):
    """Upstream reads `None` as "show the authored one" and `""` as a deliberately blank one."""
    _seed()
    stub = _AmendStub()
    payload = await _call(
        make_client, monkeypatch, stub, "registry_set_subtitle", {**MODULE, **args}
    )
    assert stub.calls == [("set_short_description", "test-sheep", "test_fto_bmi", sent)]
    assert payload["success"] is True
    assert ("authored description" in payload["message"]) is (sent is None)


@pytest.mark.parametrize("args", [{}, {"subtitle": "x", "clear": True}])
async def test_a_subtitle_request_must_say_which_it_is(make_client, monkeypatch, args):
    _seed()
    stub = _AmendStub()
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match="Pass `subtitle`, or `clear=true`"):
            await client.call_tool("registry_set_subtitle", {**MODULE, **args})
    assert stub.calls == []
