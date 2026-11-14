"""The registry's people surface: who may act on a namespace or an organisation.

A stub stands in for the client and records every call, so each test can say which upstream method
an action reached and that a refusal sent nothing.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError
from just_dna_registry import RegistryError

from just_module_creator import localstore
from just_module_creator.settings import Settings
from just_module_creator.tools import registry as registry_tools


def _online() -> Settings:
    return Settings(offline=False, _env_file=None, api_key=None)  # type: ignore[call-arg]


def _seed(target: str, account: str, token: str, namespaces: list[str]) -> None:
    def _add(state: localstore.State) -> None:
        localstore.save_account(
            state,
            target=target,
            account=account,
            token=token,
            install_id=f"install-{account}",
            namespaces=namespaces,
        )

    localstore.update(_add)


class _PeopleStub:
    """Answers the membership calls and records each one with the token it was built with."""

    def __init__(self, *, refuse: RegistryError | None = None) -> None:
        self.refuse = refuse
        self.tokens: list[str | None] = []
        self.calls: list[tuple] = []

    def __call__(self, target, settings, *, token=None, timeout=None):
        self.tokens.append(token)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def _record(self, *call: object) -> None:
        self.calls.append(call)
        if self.refuse is not None:
            raise self.refuse

    def members(self, namespace):
        self._record("members", namespace)
        return [
            {"account": "wolf", "role": "member"},
            {"account": "sheep", "role": "owner"},
            {"account": "goat", "role": "admin"},
        ]

    def add_member(self, namespace, account, role="member"):
        self._record("add_member", namespace, account, role)
        return {"account": account, "role": role}

    def remove_member(self, namespace, account):
        self._record("remove_member", namespace, account)
        return {"account": account, "removed": True}

    def org_members(self, org):
        self._record("org_members", org)
        return [{"account": "sheep", "role": "owner"}]

    def add_org_member(self, org, account, role="member"):
        self._record("add_org_member", org, account, role)
        return {"account": account, "role": role}

    def remove_org_member(self, org, member):
        self._record("remove_org_member", org, member)
        return {"account": member, "removed": True}

    def set_org_role(self, org, member, role):
        self._record("set_org_role", org, member, role)
        return {"account": member, "role": role}

    def update_profile(self, **fields):
        self._record("update_profile", fields)
        return {"account": "sheep", **fields}

    def update_org_settings(self, org, **fields):
        self._record("update_org_settings", org, fields)
        return {"org": org, **fields}


async def _members(make_client, monkeypatch, stub: _PeopleStub, args: dict) -> dict:
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool("registry_members", args)
    return result.structured_content or {}


@pytest.mark.parametrize(
    ("args", "call"),
    [
        ({"namespace": "test-sheep"}, ("members", "test-sheep")),
        (
            {"namespace": "test-sheep", "action": "add", "account": "wolf"},
            ("add_member", "test-sheep", "wolf", "member"),
        ),
        (
            {"namespace": "test-sheep", "action": "role", "account": "wolf", "role": "admin"},
            ("add_member", "test-sheep", "wolf", "admin"),
        ),
        (
            {"namespace": "test-sheep", "action": "remove", "account": "wolf"},
            ("remove_member", "test-sheep", "wolf"),
        ),
        ({"org": "test-herd"}, ("org_members", "test-herd")),
        (
            {"org": "test-herd", "action": "add", "account": "wolf", "role": "admin"},
            ("add_org_member", "test-herd", "wolf", "admin"),
        ),
        (
            {"org": "test-herd", "action": "role", "account": "wolf", "role": "owner"},
            ("set_org_role", "test-herd", "wolf", "owner"),
        ),
        (
            {"org": "test-herd", "action": "remove", "account": "wolf"},
            ("remove_org_member", "test-herd", "wolf"),
        ),
    ],
)
async def test_each_action_reaches_its_own_upstream_call(make_client, monkeypatch, args, call):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _members(make_client, monkeypatch, stub, args)
    assert payload["success"] is True
    assert stub.calls == [call]
    assert stub.tokens == ["mk_sheep_aaaa"]


async def test_a_listing_comes_back_in_a_fixed_order(make_client, monkeypatch):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    payload = await _members(make_client, monkeypatch, _PeopleStub(), {"namespace": "test-sheep"})
    assert [m["account"] for m in payload["data"]["members"]] == ["goat", "wolf", "sheep"]
    assert "3 member(s)" in payload["message"]


async def test_the_token_is_the_one_saved_for_the_namespace_named(make_client, monkeypatch):
    """Two saved accounts on one instance: the one owning the namespace signs the call."""
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    _seed("test", "goat", "mk_goat_bbbb", ["test-goat"])
    stub = _PeopleStub()
    await _members(make_client, monkeypatch, stub, {"namespace": "test-goat"})
    assert stub.tokens == ["mk_goat_bbbb"]


async def test_a_refusal_names_the_action_and_what_it_was_on(make_client, monkeypatch):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub(refuse=RegistryError(403, "owner_required"))
    payload = await _members(
        make_client,
        monkeypatch,
        stub,
        {"org": "test-herd", "action": "role", "account": "wolf", "role": "owner"},
    )
    assert payload["success"] is False
    assert "refused `role` on the organisation test-herd" in payload["message"]
    assert "owner_required" in payload["message"]


@pytest.mark.parametrize(
    ("args", "match"),
    [
        ({}, "exactly one of `namespace` or `org`"),
        ({"namespace": "test-sheep", "org": "test-herd"}, "exactly one of `namespace` or `org`"),
        ({"namespace": "test-sheep", "action": "add"}, "needs the `account`"),
        ({"org": "test-herd", "action": "role", "account": "wolf"}, "needs the new `role`"),
        ({"namespace": "Not A Namespace"}, "Invalid namespace"),
    ],
)
async def test_an_incomplete_request_is_refused_before_any_call(
    make_client, monkeypatch, args, match
):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match=match):
            await client.call_tool("registry_members", args)
    assert stub.calls == [] and stub.tokens == []


async def _profile(make_client, monkeypatch, stub: _PeopleStub, args: dict) -> dict:
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool("registry_profile", args)
    return result.structured_content or {}


async def test_a_profile_edit_sends_only_the_fields_passed(make_client, monkeypatch):
    """`""` clears a field and is sent; a field left out is not sent at all."""
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _profile(
        make_client,
        monkeypatch,
        stub,
        {"display_name": "Sheep Lab", "funding_url": ""},
    )
    assert stub.calls == [("update_profile", {"display_name": "Sheep Lab", "funding_url": ""})]
    assert payload["success"] is True
    assert "(cleared: funding_url)" in payload["message"]


async def test_an_org_profile_goes_to_the_org_route(make_client, monkeypatch):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _profile(
        make_client, monkeypatch, stub, {"org": "test-herd", "display_name": "The Herd"}
    )
    assert stub.calls == [("update_org_settings", "test-herd", {"display_name": "The Herd"})]
    assert "the profile of test-herd" in payload["message"]


async def test_a_profile_edit_with_nothing_to_send_is_refused_before_any_call(
    make_client, monkeypatch
):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match="at least one of"):
            await client.call_tool("registry_profile", {"org": "test-herd"})
    assert stub.calls == [] and stub.tokens == []
