"""The two-layer surface: what `core` must hold, and what a reveal must do.

`JMC_TOOLBOX=layered` lists the core authoring loop and holds the other nine
groups behind `toolbox`. The failure this is written against is the one the
removed `extended` tier kept producing — a surface that teaches a step it cannot
run — so the guards here are about **reachability and knowability**, not about
the size of the saving:

* every registered tool is in exactly one group, so nothing can fall off the
  roster by being forgotten;
* everything `server.INSTRUCTIONS` teaches is in `core`, derived from the text;
* `toolbox` names every hidden tool before any of them is revealed;
* a reveal reaches the session that asked and no other.

The sizes are guarded too, because they are the one fact here that cannot be
computed at runtime: a layered server cannot measure what it is hiding.
"""

from __future__ import annotations

import re

from conftest import offline_settings

from just_module_creator.server import INSTRUCTIONS, LAYERED_NOTE, instructions_for
from just_module_creator.toolbox import BY_NAME, CORE, GROUPS, HIDDEN

_CEILING = 2048
_VERSION_SLACK = 36


def _layered():
    return offline_settings(toolbox="layered")


async def _names(client) -> set[str]:
    return {t.name for t in await client.list_tools()}


# --------------------------------------------------------------------------- #
# The roster is complete and disjoint
# --------------------------------------------------------------------------- #
async def test_every_registered_tool_is_in_exactly_one_group(client):
    """A tool nobody grouped is a tool a layered server hides and never offers back."""
    registered = await _names(client)
    grouped: list[str] = [*CORE, *HIDDEN, "toolbox"]

    assert len(grouped) == len(set(grouped)), "a tool is in two groups"
    assert set(grouped) == registered, {
        "ungrouped": sorted(registered - set(grouped)),
        "grouped but not registered": sorted(set(grouped) - registered),
    }


async def test_the_core_group_covers_the_taught_workflow(client):
    """Derived from the instruction text, so editing the taught order re-checks it.

    This is the guard that makes layering survivable where the tier did not: the
    order the server teaches has to run without a single `toolbox` call.
    """
    workflow = INSTRUCTIONS.split("Work in this order:")[1].split("\n\n")[1]
    registered = await _names(client)
    taught = {word for word in re.findall(r"[a-z_]{4,}", workflow) if word in registered}

    assert taught, "parsed no tool names out of the taught workflow — the format changed"
    assert taught <= set(CORE), sorted(taught - set(CORE))


def test_the_layered_header_still_fits_what_the_host_keeps():
    """The ceiling applies to the whole string, so the note has to be paid for."""
    budget = _CEILING - _VERSION_SLACK
    assert len(INSTRUCTIONS) <= budget
    assert len(INSTRUCTIONS + LAYERED_NOTE) <= budget, (
        f"{len(INSTRUCTIONS + LAYERED_NOTE)} chars against {budget}: a layered server would "
        "lose the tail of its own instructions, which is where the registry rules live"
    )
    assert "toolbox" in instructions_for(_layered())
    assert "toolbox" not in instructions_for(offline_settings())


# --------------------------------------------------------------------------- #
# Layered: what is listed, and what says so
# --------------------------------------------------------------------------- #
async def test_layered_lists_the_core_and_nothing_else(make_client):
    async with make_client(_layered()) as client:
        listed = await _names(client)
        assert listed == set(CORE) | {"toolbox"}
        assert not (listed & set(HIDDEN))


async def test_the_roster_names_every_hidden_tool_before_anything_is_revealed(make_client):
    """"Knows what is on the second layer" is the whole condition for layering at all."""
    async with make_client(_layered()) as client:
        answer = await client.call_tool("toolbox", {})
        named = {tool for group in answer.data.groups for tool in group.tools}

        assert answer.data.layered is True
        assert named == set(HIDDEN)
        assert {g.name for g in answer.data.groups} == set(BY_NAME)
        assert all(g.approx_tokens > 0 for g in answer.data.groups)


async def test_a_reveal_reaches_the_asking_session_only(make_client):
    settings = _layered()
    async with make_client(settings) as first, make_client(settings) as second:
        answer = await first.call_tool("toolbox", {"groups": ["evidence"]})
        assert answer.data.revealed == ["evidence"]

        assert set(BY_NAME["evidence"].tools) <= await _names(first)
        assert not (set(BY_NAME["evidence"].tools) & await _names(second))
        # And only that group: revealing one is not revealing everything.
        assert "registry_publish" not in await _names(first)


async def test_a_revealed_tool_is_callable(make_client, tmp_path):
    async with make_client(_layered()) as client:
        await client.call_tool("toolbox", {"groups": ["closing"]})
        answer = await client.call_tool("authoring_reference", {})
        assert answer.data is not None


async def test_all_reveals_every_group(make_client):
    async with make_client(_layered()) as client:
        answer = await client.call_tool("toolbox", {"groups": ["all"]})
        assert set(answer.data.revealed) == set(BY_NAME)
        assert set(HIDDEN) <= await _names(client)


async def test_an_unknown_group_is_named_back_with_the_real_ones(make_client):
    async with make_client(_layered()) as client:
        answer = await client.call_tool("toolbox", {"groups": ["registry"]})
        assert answer.data.revealed == []
        assert "registry" in answer.data.message
        assert "catalog" in answer.data.message and "publish" in answer.data.message


# --------------------------------------------------------------------------- #
# Flat is the default, and stays honest about it
# --------------------------------------------------------------------------- #
async def test_flat_hides_nothing_and_a_reveal_says_so(client):
    listed = await _names(client)
    assert set(HIDDEN) <= listed

    answer = await client.call_tool("toolbox", {"groups": ["publish"]})
    assert answer.data.layered is False
    assert "Nothing was hidden" in answer.data.message
    # The roster is still readable, because it is also a map of the surface.
    assert {g.name for g in answer.data.groups} == set(BY_NAME)


# --------------------------------------------------------------------------- #
# The sizes, which are the one fact here that cannot be computed at runtime
# --------------------------------------------------------------------------- #
async def test_the_group_sizes_are_still_true(client):
    """Two producers: the hand-written estimate, and a FLAT server measured now.

    `Group.approx_tokens` is written down because visibility filtering applies to
    us too — a layered server's `get_tool` returns `None` for what it is hiding,
    so it cannot measure its own second layer. A number an agent uses to decide
    whether to spend context is worth 20% tolerance and no more.
    """
    payloads = {t.name: t.model_dump_json(exclude_none=True) for t in await client.list_tools()}

    drifted = []
    for group in GROUPS:
        live = sum(len(payloads[name]) for name in group.tools) // 4
        if abs(live - group.approx_tokens) > 0.2 * live:
            drifted.append(f"{group.name}: says {group.approx_tokens}, measures {live}")
    assert not drifted, "\n".join(drifted)


async def test_layering_saves_what_it_claims(client):
    """The claim in `toolbox.py`'s docstring, in numbers, from the running server."""
    payloads = {t.name: t.model_dump_json(exclude_none=True) for t in await client.list_tools()}
    everything = sum(len(p) for p in payloads.values()) // 4
    layer_one = sum(len(payloads[n]) for n in [*CORE, "toolbox"]) // 4

    assert layer_one < everything / 2, (
        f"layer one is {layer_one} of {everything} approx-tokens — layering that saves less "
        "than half is not worth a round trip, so either core has grown or the claim has"
    )


async def test_a_reveal_does_not_route_around_the_auth_policy(make_client):
    """Layered + `JMC_HIDE_GATED_UNTIL_AUTH`: which rule wins, measured not assumed.

    Two mechanisms disable `publish` at startup — by name (layering) and by tag
    (the auth lever) — and a reveal re-enables by name. Session rules override
    global ones, so the name-enable **does** beat the tag-disable: without the
    check in `toolbox`, any session could list the publish route by asking for it,
    which is exactly what an operator setting that flag was preventing. So the
    group is withheld until the session holds a token, and the answer says how to
    get one rather than going quiet.
    """
    settings = offline_settings(toolbox="layered", hide_gated_until_auth=True)
    async with make_client(settings) as client:
        answer = await client.call_tool("toolbox", {"groups": ["publish"]})

        assert "publish" not in answer.data.revealed
        assert "authenticate" in answer.data.message
        assert "registry_publish" not in await _names(client)

        # And authenticating is the way in, as the message says.
        await client.call_tool("authenticate", {"token": "tok_abc123", "target": "test"})
        assert "registry_publish" in await _names(client)


async def test_a_reveal_still_serves_the_other_groups_when_publish_is_withheld(make_client):
    """One refused group must not cost a session the ones it may have."""
    settings = offline_settings(toolbox="layered", hide_gated_until_auth=True)
    async with make_client(settings) as client:
        answer = await client.call_tool("toolbox", {"groups": ["all"]})

        assert "publish" not in answer.data.revealed
        assert "evidence" in answer.data.revealed
        listed = await _names(client)
        assert "paper_citations" in listed and "registry_publish" not in listed


async def test_a_hidden_tool_is_not_callable_until_revealed(make_client):
    """The one way layering is stricter than tool search, and it belongs in a test.

    Search leaves an unlisted tool callable by name; layering *disables* it, so a
    call before the reveal fails with "Unknown tool". That is still not a dead
    end — `toolbox` is listed and names it — but it is the difference between the
    two levers, and a caller who assumes search's behaviour would misread it.
    """
    from fastmcp.exceptions import ToolError

    async with make_client(_layered()) as client:
        try:
            await client.call_tool("paper_citations", {"pmid": "11788828"})
        except ToolError as exc:
            assert "paper_citations" in str(exc)
        else:
            raise AssertionError("a hidden tool answered a call; it is disabled, not unlisted")

        await client.call_tool("toolbox", {"groups": ["evidence"]})
        assert "paper_citations" in await _names(client)
