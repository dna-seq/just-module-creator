"""The registry's people surface: who may act on a namespace or an organisation.

A stub stands in for the client and records every call, so each test can say which upstream method
an action reached and that a refusal sent nothing.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError
from just_dna_registry import RegistryError
from just_dna_registry.models.api import ReviewRequest
from just_dna_registry.permissions import VALID_NS_ROLES, VALID_ORG_ROLES

from just_module_creator import localstore
from just_module_creator.settings import Settings
from just_module_creator.tools import registry as registry_tools
from just_module_creator.tools import research


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

    def star(self, namespace, name):
        self._record("star", namespace, name)
        return {"namespace": namespace, "name": name, "stars": 1, "starred_by_me": True}

    def unstar(self, namespace, name):
        self._record("unstar", namespace, name)
        return {"namespace": namespace, "name": name, "stars": 0, "starred_by_me": False}

    def review(self, namespace, name, version, *, rating, verdict=None, notes=None):
        self._record("review", namespace, name, version, rating, verdict, notes)
        return [{"reviewer": "sheep", "version": version, "rating": rating, "verdict": verdict}]

    def delete_review(self, namespace, name, version):
        self._record("delete_review", namespace, name, version)
        return []

    def highlight_review(self, namespace, name, version, reviewer, *, highlighted=True):
        self._record("highlight_review", namespace, name, version, reviewer, highlighted)
        # The registry answers with the version's list as it stands; only goat and wolf
        # have reviewed, so a highlight of anyone else changes nothing in it.
        return [
            {"reviewer": who, "version": version, "highlighted": highlighted and who == reviewer}
            for who in ("goat", "wolf")
        ]

    def reviews(self, namespace, name, version=None):
        self._record("reviews", namespace, name, version)
        return [
            {"reviewer": "goat", "version": "1.0.0", "rating": 5, "highlighted": True},
            {"reviewer": "wolf", "version": "1.0.0", "rating": 2, "highlighted": False},
        ]


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


async def test_a_namespace_re_role_checks_membership_first(make_client, monkeypatch):
    """Upstream's re-role is `add_member` again, which would add a stranger."""
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _members(
        make_client,
        monkeypatch,
        stub,
        {"namespace": "test-sheep", "action": "role", "account": "wolf", "role": "admin"},
    )
    assert payload["success"] is True
    assert stub.calls == [("members", "test-sheep"), ("add_member", "test-sheep", "wolf", "admin")]


async def test_re_roling_someone_who_is_not_a_member_sends_nothing(make_client, monkeypatch):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _members(
        make_client,
        monkeypatch,
        stub,
        {"namespace": "test-sheep", "action": "role", "account": "fox", "role": "admin"},
    )
    assert payload["success"] is False
    assert "fox is not a member" in payload["message"] and "Use `add`" in payload["message"]
    assert stub.calls == [("members", "test-sheep")], "only the listing was asked"


async def test_the_roles_offered_are_the_registrys_own(make_client):
    async with make_client(settings=_online()) as client:
        tools = {t.name: t for t in await client.list_tools()}
    described = tools["registry_members"].inputSchema["properties"]["role"]["description"]
    assert VALID_NS_ROLES, "upstream's role set came back empty"
    for role in VALID_NS_ROLES | VALID_ORG_ROLES:
        assert role in described


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
        ({"org": "test-herd", "action": "add", "account": "wolf", "role": "chief"}, "not a role"),
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


MODULE = {"namespace": "test-sheep", "name": "test_big_five_personality_snps"}


async def _tool(make_client, monkeypatch, stub: _PeopleStub, tool: str, args: dict) -> dict:
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool(tool, args)
    return result.structured_content or {}


@pytest.mark.parametrize(("starred", "call"), [(True, "star"), (False, "unstar")])
async def test_a_star_and_its_withdrawal_reach_their_own_calls(
    make_client, monkeypatch, starred, call
):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _tool(
        make_client, monkeypatch, stub, "registry_star", {**MODULE, "starred": starred}
    )
    assert stub.calls == [(call, MODULE["namespace"], MODULE["name"])]
    assert payload["success"] is True


@pytest.mark.parametrize(
    ("args", "call"),
    [
        (
            {"rating": 4, "verdict": "verified", "notes": "Alleles checked against dbSNP."},
            ("review", 4, "verified", "Alleles checked against dbSNP."),
        ),
        ({"action": "delete"}, ("delete_review",)),
        ({"action": "highlight", "reviewer": "goat"}, ("highlight_review", "goat", True)),
        ({"action": "unhighlight", "reviewer": "goat"}, ("highlight_review", "goat", False)),
    ],
)
async def test_each_review_action_reaches_its_own_call(make_client, monkeypatch, args, call):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    payload = await _tool(
        make_client, monkeypatch, stub, "registry_review", {**MODULE, "version": "1.0.0", **args}
    )
    assert payload["success"] is True
    [sent] = stub.calls
    assert sent[0] == call[0] and sent[1:4] == (MODULE["namespace"], MODULE["name"], "1.0.0")
    assert sent[4:] == call[1:]


@pytest.mark.parametrize(
    ("args", "match"),
    [({}, "`post` needs a `rating`"), ({"action": "highlight"}, "needs the `reviewer`")],
)
async def test_a_review_missing_its_argument_is_refused_before_any_call(
    make_client, monkeypatch, args, match
):
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    stub = _PeopleStub()
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        with pytest.raises(ToolError, match=match):
            await client.call_tool("registry_review", {**MODULE, "version": "1.0.0", **args})
    assert stub.calls == [] and stub.tokens == []


async def test_the_review_fields_are_described_by_the_registry_model(make_client):
    """The rating range and verdict tiers are upstream's; the listing carries their words."""
    async with make_client(settings=_online()) as client:
        tools = {t.name: t for t in await client.list_tools()}
    properties = tools["registry_review"].inputSchema["properties"]
    for field in ("rating", "verdict"):
        expected = ReviewRequest.model_fields[field].description
        assert expected, f"upstream's {field} lost its description"
        assert properties[field]["description"] == expected


async def test_reading_reviews_needs_no_token_and_counts_the_highlighted(make_client, monkeypatch):
    stub = _PeopleStub()
    payload = await _tool(
        make_client, monkeypatch, stub, "registry_reviews", {"target": "prod", **MODULE}
    )
    assert stub.calls == [("reviews", MODULE["namespace"], MODULE["name"], None)]
    assert stub.tokens == [None]
    assert "2 review(s)" in payload["message"] and "1 highlighted" in payload["message"]


class _StatsStub:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def catalog_stats(self, namespace=None, *, group=None):
        self.calls.append(("catalog_stats", namespace, group))
        return {"modules": 1, "downloads": 40, "stars": 0, "reviews": 0, "curated": 0}


@pytest.mark.parametrize(
    ("args", "call", "scope"),
    [
        (
            {"namespace": "winternewt"},
            ("catalog_stats", "winternewt", None),
            "namespace winternewt",
        ),
        ({"group": "test"}, ("catalog_stats", None, "test"), "listing group test"),
        ({}, ("catalog_stats", None, None), "the default listing"),
    ],
)
async def test_totals_name_the_listing_they_were_counted_over(
    make_client, monkeypatch, args, call, scope
):
    stub = _StatsStub()
    monkeypatch.setattr(research, "client_for", lambda *a, **kw: stub)
    async with make_client(settings=_online()) as client:
        payload = (
            await client.call_tool("registry_stats", {"target": "prod", **args})
        ).structured_content or {}
    assert stub.calls == [call]
    assert f"Totals over {scope}" in payload["message"]
    assert payload["data"]["downloads"] == 40


@pytest.mark.parametrize(
    ("args", "signed_by"),
    [
        ({"action": "highlight", "reviewer": "wolf"}, "mk_goat_bbbb"),
        ({"rating": 4}, "mk_sheep_aaaa"),
    ],
)
async def test_a_highlight_is_signed_by_the_namespaces_owner_and_a_review_by_the_default(
    make_client, monkeypatch, args, signed_by
):
    """Two saved accounts: the one owning the module's namespace highlights; a review is the
    default account's own."""
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    _seed("test", "goat", "mk_goat_bbbb", ["test-goat"])
    stub = _PeopleStub()
    await _tool(
        make_client,
        monkeypatch,
        stub,
        "registry_review",
        {"namespace": "test-goat", "name": "test_goat_module", "version": "1.0.0", **args},
    )
    assert stub.tokens == [signed_by]


@pytest.mark.parametrize(
    ("args", "said"),
    [
        ({"action": "delete"}, "No review of yours is on"),
        ({"action": "unhighlight", "reviewer": "fox"}, "The registry lists no review by fox"),
    ],
)
async def test_a_review_message_reads_the_registrys_answer_not_the_request(
    make_client, monkeypatch, args, said
):
    """F153: the registry answers these two with the list as it stands, review or not."""
    _seed("test", "sheep", "mk_sheep_aaaa", ["test-sheep"])
    payload = await _tool(
        make_client,
        monkeypatch,
        _PeopleStub(),
        "registry_review",
        {**MODULE, "version": "1.0.0", **args},
    )
    assert payload["success"] is True
    assert said in payload["message"]
    assert "removed" not in payload["message"] and "no longer" not in payload["message"]
