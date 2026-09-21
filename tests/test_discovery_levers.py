"""The two levers that narrow what a session SEES, and what neither of them does.

Both are off by default and both were adopted from the template this repo is
built on. They are worth pinning carefully because the thing they resemble —
the mode axis, removed in 0.21.0 — failed for a reason that neither of these
repeats: it decided at startup, for everybody, that a tool did not exist.

* ``JMC_HIDE_GATED_UNTIL_AUTH`` hides the registry writes from a session until
  that session authenticates. Per session, not server-global, because
  ``ctx.enable_components`` is session-scoped where ``mcp.enable`` is not.
* ``JMC_TOOL_SEARCH`` replaces the listing with ``search_tools`` + ``call_tool``.
  It narrows what is LISTED and nothing else: an unlisted tool stays callable.
* ``JMC_TOOLBOX=layered`` holds nine groups behind ``toolbox`` until a session
  asks for one — see ``test_toolbox.py``; the composition of the two is here.
"""

from __future__ import annotations

from conftest import offline_settings

from just_module_creator.auth import GATED_TOOLS
from just_module_creator.tool_search import ALWAYS_VISIBLE


async def _names(client) -> set[str]:
    return {t.name for t in await client.list_tools()}


def _text(result) -> str:
    """Whatever `search_tools` answered, as one searchable string."""
    return str(result.content[0].text if result.content else result.data)


# --------------------------------------------------------------------------- #
# JMC_HIDE_GATED_UNTIL_AUTH
# --------------------------------------------------------------------------- #
def _hidden() -> object:
    return offline_settings(hide_gated_until_auth=True)


async def test_hidden_gated_tools_appear_when_that_session_authenticates(make_client):
    async with make_client(_hidden()) as client:
        before = await _names(client)
        # **Anchor the listing before asserting anything is missing from it.** An empty
        # listing satisfies every `not in` below and reports *the gated tools are hidden*
        # about a session that was shown nothing at all — the lever is "hide the gated
        # ones", so the positive half is what makes the negative half mean anything.
        # `registry_register` is the right anchor rather than any ungated name: it is
        # pinned visible on purpose, because hiding the only route to a credential is F12.
        assert "registry_register" in before, "the listing came back empty, not narrowed"
        assert "registry_publish" not in before

        stored = await client.call_tool("authenticate", {"token": "tok_abc123", "target": "test"})
        assert stored.data.authenticated is True

        assert set(GATED_TOOLS) <= await _names(client)


async def test_revealing_them_for_one_session_does_not_reveal_them_to_another(make_client):
    """The property `mcp.enable` cannot provide, which is why it is not used here."""
    settings = _hidden()
    async with make_client(settings) as first, make_client(settings) as second:
        await first.call_tool("authenticate", {"token": "tok_abc123", "target": "test"})
        assert "registry_publish" in await _names(first)
        assert "registry_publish" not in await _names(second)


async def test_an_empty_token_reveals_nothing(make_client):
    async with make_client(_hidden()) as client:
        auth = await client.call_tool("authenticate", {"token": "   "})
        assert auth.data.authenticated is False
        names = await _names(client)
        assert "registry_register" in names, "the listing came back empty, not narrowed"
        assert "registry_publish" not in names


async def test_the_route_to_a_token_is_never_hidden(make_client):
    """`registry_register` mints the credential, so hiding it is the F12 dead end."""
    async with make_client(_hidden()) as client:
        assert "registry_register" in await _names(client)
        assert "registry_register" not in GATED_TOOLS


# --------------------------------------------------------------------------- #
# JMC_TOOL_SEARCH
# --------------------------------------------------------------------------- #
async def test_search_replaces_the_listing_and_pins_the_way_in(make_client):
    async with make_client(offline_settings(tool_search="regex")) as client:
        names = await _names(client)
        assert {"search_tools", "call_tool"} <= names
        # The control plane stays listed: a client that has to search for the
        # route to a credential is the dead end, arriving by a different door.
        assert set(ALWAYS_VISIBLE) <= names
        assert "compile_module" not in names


async def test_an_unlisted_tool_is_still_callable(make_client):
    """Search controls discovery, never access — that is the whole difference from a tier.

    `result.data` degrades to a plain dict on the direct call, because the client
    never received a schema to validate against.
    """
    async with make_client(offline_settings(tool_search="regex")) as client:
        names = await _names(client)
        assert set(ALWAYS_VISIBLE) <= names, "the listing came back empty, not replaced"
        assert "list_tables" not in names
        direct = await client.call_tool("list_tables", {})
        assert "tables" in direct.data


async def test_search_finds_a_tool_by_what_it_does(make_client):
    """`regex` matches name, description and parameter docs, and does not rank.

    So the query has to be as specific as the answer wanted — "compile" alone
    matches a dozen descriptions and `max_results` cuts before the one you meant.
    That bluntness is the documented cost of this strategy; `bm25` ranks.
    """
    async with make_client(offline_settings(tool_search="regex")) as client:
        found = await client.call_tool("search_tools", {"pattern": "compile_module"})
        assert "compile_module" in _text(found)


async def test_search_sees_only_what_this_session_may_see(make_client):
    """It composes with the auth lever rather than working around it."""
    settings = offline_settings(tool_search="regex", hide_gated_until_auth=True)
    async with make_client(settings) as client:
        before = await client.call_tool("search_tools", {"pattern": "registry_publish"})
        assert "registry_publish" not in _text(before)

        await client.call_tool("authenticate", {"token": "tok_abc123", "target": "test"})

        after = await client.call_tool("search_tools", {"pattern": "registry_publish"})
        assert "registry_publish" in _text(after)


# --------------------------------------------------------------------------- #
# The three compose: layering decides what exists for a session, search how it is listed
# --------------------------------------------------------------------------- #
async def test_search_indexes_only_what_this_session_has_revealed(make_client):
    """Layered + search: the roster stays findable, the hidden groups do not.

    This is the combination worth checking, because each lever narrows a different
    thing — layering narrows what the session *has*, search narrows what is
    *listed* — and a client that cannot find `toolbox` under both is back at the
    dead end neither is allowed to reproduce.
    """
    settings = offline_settings(toolbox="layered", tool_search="regex")
    async with make_client(settings) as client:
        assert "toolbox" in await _names(client)

        blind = await client.call_tool("search_tools", {"pattern": "paper_citations"})
        assert "paper_citations" not in _text(blind)

        await client.call_tool("toolbox", {"groups": ["evidence"]})

        found = await client.call_tool("search_tools", {"pattern": "paper_citations"})
        assert "paper_citations" in _text(found)


async def test_a_session_that_cannot_keep_a_token_says_so_instead_of_storing_it(client):
    """The modern-era in-memory client has no session id, so `set_state` cannot survive
    the call. `authenticate` must refuse and name the env var, never report a success
    that the next gated call cannot find (fastmcp 4, 2026-09-21)."""
    result = await client.call_tool("authenticate", {"token": "tok_abc123", "target": "test"})
    assert result.data.authenticated is False
    assert "JMC_TEST_API_KEY" in result.data.message
    assert result.data.unlocked_tools == []
