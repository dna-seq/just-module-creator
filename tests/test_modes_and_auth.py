"""The two gating axes: mode (which tools exist) and auth (whether they work).

Plus the offline ceiling, which is this server's third safety property: a
per-call ``offline=False`` must never punch through a server configured for zero
egress.
"""

from __future__ import annotations

import pytest
from conftest import offline_settings  # tests/ is on sys.path via pytest rootdir
from fastmcp.exceptions import ToolError

from just_module_creator.auth import GATED_TOOLS, resolve_install_id
from just_module_creator.settings import Settings

# The authoring loop an agent cannot work without. Present in EVERY mode.
ESSENTIAL_TOOLS = {
    "list_tables",
    "describe_table",
    "table_requirements",
    "get_template",
    "scaffold_module",
    "lint_rows",
    "validate_module",
    "compile_module",
    # Discovery is essentials because the anti-fabrication promise depends on it:
    # lookup_citation proves a PMID exists, which a wrong-but-real id also does.
    "literature_search",
}


async def _names(client) -> set[str]:
    return {t.name for t in await client.list_tools()}


async def test_essentials_mode_exposes_the_authoring_loop(essentials_client):
    names = await _names(essentials_client)
    assert names >= ESSENTIAL_TOOLS


async def test_extended_only_tools_are_absent_by_default(essentials_client):
    names = await _names(essentials_client)
    assert "enrich_module" not in names
    assert "authoring_reference" not in names
    assert "reverse_module" not in names
    assert "fetch_fulltext" not in names
    assert "lookup_open_access" not in names


async def test_extended_mode_is_a_superset(essentials_client, extended_client):
    essentials = await _names(essentials_client)
    extended = await _names(extended_client)
    assert essentials < extended
    assert {
        "enrich_module",
        "authoring_reference",
        "reverse_module",
        "fetch_fulltext",
        "lookup_open_access",
    } <= extended


async def test_gated_tools_are_always_listed(essentials_client, extended_client):
    """Listed in both modes: hiding them per-client is not multi-tenant safe."""
    for client in (essentials_client, extended_client):
        assert set(GATED_TOOLS) <= await _names(client)


async def test_gated_tool_without_a_token_returns_not_raises(essentials_client):
    result = await essentials_client.call_tool("registry_whoami", {})
    assert result.data.success is False
    assert "registry token" in result.data.message


async def test_authenticate_stores_a_token_for_this_session(essentials_client):
    result = await essentials_client.call_tool("authenticate", {"token": "tok_abc123"})
    assert result.data.authenticated
    assert set(result.data.unlocked_tools) == set(GATED_TOOLS)
    # It stores; it does not claim the registry accepted anything.
    assert "registry_whoami" in result.data.message


async def test_authenticate_rejects_an_empty_token(essentials_client):
    result = await essentials_client.call_tool("authenticate", {"token": "   "})
    assert result.data.authenticated is False


# --------------------------------------------------------------------------- #
# Onboarding — the one registry write that cannot be token-gated
# --------------------------------------------------------------------------- #
async def test_onboarding_tools_are_in_every_mode(essentials_client, extended_client):
    """The route to a token must exist in the DEFAULT surface.

    Behind `extended` it would be the same dead end in a different place: every
    other registry tool needs a token, and only this one produces one.
    """
    for client in (essentials_client, extended_client):
        names = await _names(client)
        assert {"registry_register", "registry_namespace_available"} <= names


async def test_the_tool_that_mints_the_token_is_not_gated_by_one():
    assert "registry_register" not in GATED_TOOLS


async def test_onboarding_tools_respect_the_offline_ceiling(make_client):
    async with make_client("essentials", offline_settings()) as client:
        for tool, args in (
            ("registry_register", {"account": "test-creator"}),
            ("registry_namespace_available", {"namespace": "test-modules"}),
        ):
            with pytest.raises(ToolError, match="offline|JMC_OFFLINE"):
                await client.call_tool(tool, args)


async def test_an_illegal_account_name_is_refused_before_any_socket(make_client, monkeypatch):
    """`test_creator` is the name that has to fail, and fail locally.

    Accounts are validated with the namespace rule, so an underscore is rejected
    rather than normalised. Spending a round trip to learn that is a round trip
    wasted, and the message has to name the pattern — "lowercase,
    hyphen-separated" reads as a style preference rather than a hard reject.
    """
    import httpx

    def explode(*args, **kwargs):
        raise AssertionError("a socket was opened for a name that could be rejected locally")

    monkeypatch.setattr(httpx.Client, "__init__", explode)
    async with make_client("essentials", Settings(offline=False, _env_file=None)) as client:  # type: ignore[call-arg]
        with pytest.raises(ToolError, match="not a legal account name") as caught:
            await client.call_tool("registry_register", {"account": "test_creator"})
    # The pattern itself, so the author does not have to guess what "legal" means.
    assert "[a-z0-9]" in str(caught.value)


async def test_install_id_precedence_and_origin():
    """Argument beats environment beats grinding, and the origin is reported.

    The origin is load-bearing: a reused id reissues a key for its existing
    account, a fresh one creates a new account whose only recovery path the
    caller now has to save. Returning just the id makes those indistinguishable.
    """
    from_env = Settings(offline=True, install_id="jdi1_from_env_0", _env_file=None)  # type: ignore[call-arg]
    assert resolve_install_id("jdi1_explicit_0", from_env) == ("jdi1_explicit_0", "argument")
    assert resolve_install_id(None, from_env) == ("jdi1_from_env_0", "environment")
    assert resolve_install_id("   ", from_env) == ("jdi1_from_env_0", "environment")

    unset = Settings(offline=True, _env_file=None)  # type: ignore[call-arg]
    assert resolve_install_id(None, unset) == (None, "generated")
    # Whitespace-only in the environment is not a credential either.
    blank = Settings(offline=True, install_id="  ", _env_file=None)  # type: ignore[call-arg]
    assert resolve_install_id(None, blank) == (None, "generated")


async def test_a_ground_install_id_satisfies_upstreams_own_validator():
    """The grind is ours to call but upstream's to judge, so ask upstream.

    Hermetic: proof-of-work is CPU only and opens no socket.
    """
    from just_dna_registry import generate_install_id, validate_install_id

    assert validate_install_id(generate_install_id())


async def test_a_token_does_not_leak_between_sessions(make_client):
    """The core multi-tenant property: one session's token is invisible to another."""
    async with make_client() as first:
        await first.call_tool("authenticate", {"token": "tok_first"})
    async with make_client() as second:
        result = await second.call_tool("registry_whoami", {})
        assert result.data.success is False


async def test_env_token_is_picked_up_without_authenticate():
    settings = offline_settings(api_key="tok_from_env")
    assert settings.registry_token() == "tok_from_env"


async def test_registry_token_falls_back_to_the_toolchain_variable(monkeypatch):
    """An author already logged in with REGISTRY_TOKEN should not re-declare it."""
    monkeypatch.delenv("JMC_API_KEY", raising=False)
    monkeypatch.setenv("REGISTRY_TOKEN", "tok_toolchain")
    assert Settings(_env_file=None).registry_token() == "tok_toolchain"  # type: ignore[call-arg]


# --------------------------------------------------------------------------- #
# The offline ceiling
# --------------------------------------------------------------------------- #
async def test_offline_settings_block_the_registry(make_client):
    async with make_client("essentials", offline_settings()) as client:
        with pytest.raises(ToolError, match="offline"):
            await client.call_tool("registry_search", {"query": "lactose"})


async def test_offline_settings_block_every_literature_tool(make_client):
    """There is no offline literature snapshot, so `offline` refuses rather than degrades.

    Upstream is explicit that one will never exist — once literature.csv is
    written it IS the pin — so serving a stale answer here would be inventing a
    guarantee nobody made.
    """
    async with make_client("essentials", offline_settings()) as client:
        with pytest.raises(ToolError, match="offline|JMC_OFFLINE"):
            await client.call_tool("literature_search", {"query": "lactase persistence"})

    async with make_client("extended", offline_settings()) as client:
        for tool, args in (
            ("fetch_fulltext", {"pmid": "11788828"}),
            ("lookup_open_access", {"pmid": "11788828"}),
        ):
            with pytest.raises(ToolError, match="offline|JMC_OFFLINE"):
                await client.call_tool(tool, args)


async def test_the_offline_check_runs_before_any_client_is_constructed(make_client, monkeypatch):
    """A tripwire on the boundary, now that this server owns sockets.

    Hermeticity used to be free — every call went out through the enricher. It is
    not free any more, so this proves the refusal happens before httpx is touched
    rather than trusting that it does.
    """
    import httpx

    def explode(*args, **kwargs):
        raise AssertionError("a socket was opened under JMC_OFFLINE")

    monkeypatch.setattr(httpx.Client, "__init__", explode)
    async with make_client("essentials", offline_settings()) as client:
        with pytest.raises(ToolError, match="offline|JMC_OFFLINE"):
            await client.call_tool("literature_search", {"query": "lactase persistence"})


async def test_a_call_argument_cannot_override_the_offline_ceiling():
    from just_module_creator.tools._shared import offline_for

    strict = offline_settings()
    assert offline_for(strict, requested=False) is True  # ceiling wins
    lenient = Settings(offline=False, _env_file=None)  # type: ignore[call-arg]
    assert offline_for(lenient, requested=True) is True  # per-call still works
    assert offline_for(lenient, requested=False) is False


# --------------------------------------------------------------------------- #
# Workspace containment
# --------------------------------------------------------------------------- #
async def test_workspace_confines_writes(make_client, tmp_path):
    inside = tmp_path / "allowed"
    inside.mkdir()
    settings = offline_settings(workspace=str(inside))

    async with make_client("essentials", settings) as client:
        ok = await client.call_tool(
            "scaffold_module", {"spec_dir": str(inside / "spec"), "name": "m"}
        )
        assert ok.data.written

        with pytest.raises(ToolError, match="outside the configured workspace"):
            await client.call_tool(
                "scaffold_module", {"spec_dir": str(tmp_path / "elsewhere"), "name": "m"}
            )


async def test_no_workspace_means_no_restriction(make_client, tmp_path):
    async with make_client("essentials", offline_settings()) as client:
        result = await client.call_tool(
            "scaffold_module", {"spec_dir": str(tmp_path / "anywhere"), "name": "m"}
        )
        assert result.data.written


# --------------------------------------------------------------------------- #
# Server-level contract
# --------------------------------------------------------------------------- #
async def test_server_boots_with_no_environment(monkeypatch):
    """Authoring needs no registry account, so a bare env must never fail."""
    for var in ("JMC_API_KEY", "JMC_MODE", "REGISTRY_TOKEN", "JMC_OFFLINE"):
        monkeypatch.delenv(var, raising=False)
    from just_module_creator.server import build_server

    assert build_server() is not None


async def test_resource_and_prompt_are_registered(essentials_client):
    resources = {str(r.uri) for r in await essentials_client.list_resources()}
    assert "resource://just-dna/tables" in resources
    prompts = {p.name for p in await essentials_client.list_prompts()}
    assert "create_module" in prompts
