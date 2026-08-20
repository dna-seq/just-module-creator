"""The two gating axes: mode (which tools exist) and auth (whether they work).

Plus the offline ceiling, which is this server's third safety property: a
per-call ``offline=False`` must never punch through a server configured for zero
egress.
"""

from __future__ import annotations

import re
from importlib import metadata

import pytest
from conftest import offline_settings  # tests/ is on sys.path via pytest rootdir
from fastmcp.exceptions import ToolError

from just_module_creator.auth import GATED_TOOLS, resolve_install_id
from just_module_creator.server import INSTRUCTIONS
from just_module_creator.settings import Settings

# The authoring loop an agent cannot work without. Present in EVERY mode.
ESSENTIAL_TOOLS = {
    "list_tables",
    "describe_table",
    # The read-only half of the same rule: an author meets `resolution.csv` and the
    # fact sidecars in every enriched module, and "ask the tool, never memory" has to
    # hold for a file they read as much as for one they write (RM11).
    "describe_machine_table",
    "table_requirements",
    "get_template",
    "scaffold_module",
    "lint_rows",
    "validate_module",
    "enrich_module",
    "compile_module",
    # Discovery is essentials because the anti-fabrication promise depends on it:
    # lookup_citation proves a PMID exists, which a wrong-but-real id also does.
    "literature_search",
    # And so does identifier checking: describe_table says trait_efo_id takes an
    # ontology CURIE, and this is the only thing that says the one you have in
    # mind is real. Without it the default tier invites writing one from memory.
    "lookup_identifier",
    "check_identifiers",
}

# Bounded by a corpus rather than by what you named, or about reading back
# somebody else's artifact. The only things a mode flag still hides.
EXTENDED_ONLY = {
    "paper_citations",
    "reverse_module",
    "registry_download",
    "draft_from_cpic",
    "draft_from_clinpgx",
    "enrich_facts",
    "enrich_literature_pass",
    # `1 + 2N` requests for a variant with N published associations, measured at 382
    # for one real module: sized by how much has been published, not by what you named.
    "enrich_gwas_effects",
    # `refresh_sidecar` runs whichever pass owns the sidecar, up to and including the
    # GWAS one, so essentials would reach an extended budget by another door — the
    # rationale its author states in `server.py`'s module docstring, transcribed here
    # rather than decided here.
    "refresh_sidecar",
}


async def _names(client) -> set[str]:
    return {t.name for t in await client.list_tools()}


async def test_essentials_mode_exposes_the_authoring_loop(essentials_client):
    names = await _names(essentials_client)
    assert names >= ESSENTIAL_TOOLS


async def test_the_taught_workflow_runs_in_the_default_tier(essentials_client, extended_client):
    """Every tool the server's own instructions name must exist in essentials.

    The server teaches an order in ``INSTRUCTIONS``. Teaching a step the default
    tier cannot run is the specific defect this asserts against — ``enrich_module``
    was named in that order while being extended-only, so an agent following the
    instructions hit a tool that was not there. Derived from the text rather than
    restated, so editing the taught order re-checks it.
    """
    # Bounded by the blank line that ends the block, not by the prose that
    # follows it: this read `.split("Three rules")` until renumbering those rules
    # silently widened the slice to the whole document and reported an unrelated
    # tool as a tiering bug.
    workflow = INSTRUCTIONS.split("Work in this order:")[1].split("\n\n")[1]
    every_tool = await _names(extended_client)
    named = {word for word in re.findall(r"[a-z_]{4,}", workflow) if word in every_tool}

    assert named, "parsed no tool names out of the taught workflow — the format changed"
    assert named <= await _names(essentials_client)


def test_instructions_name_the_running_toolchain():
    """The header states the loaded format/compiler, and never a literal (RM13).

    It said "format 0.5" for two releases while the installed format was 0.6 — a
    hardcoded version that a stale build reports just as confidently as a current
    one. Computed here rather than pasted, for the same reason.
    """
    assert f"just-dna-format {metadata.version('just-dna-format')}" in INSTRUCTIONS
    assert f"just-dna-compiler {metadata.version('just-dna-compiler')}" in INSTRUCTIONS


async def test_extended_only_tools_are_absent_by_default(essentials_client):
    assert not (EXTENDED_ONLY & await _names(essentials_client))


async def test_extended_mode_is_a_superset(essentials_client, extended_client):
    essentials = await _names(essentials_client)
    extended = await _names(extended_client)
    assert essentials < extended
    assert extended >= EXTENDED_ONLY
    # The mode flag hides these and nothing else.
    assert extended - essentials == EXTENDED_ONLY


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


# --------------------------------------------------------------------------- #
# Hermeticity is a mechanism, not a convention (F24)
# --------------------------------------------------------------------------- #
def test_a_bare_settings_reads_no_developer_configuration() -> None:
    """The guard `F24` asked for: forgetting `_env_file=None` must be harmless.

    A real `.env` sits in this repo root and holds a live polygon token. Before the
    autouse fixture in `conftest.py`, `Settings()` here returned it — and lost
    `offline=True` with it, so a test could reach the network holding a real
    credential. Asserted on the bare constructor on purpose: `offline_settings()`
    was never the problem, the constructions that bypass it were.
    """
    from just_module_creator.settings import Settings

    bare = Settings()

    assert bare.api_key is None
    assert bare.test_api_key is None
    assert bare.install_id is None
    assert bare.user_email is None


def test_the_repo_really_does_hold_a_dotenv_for_that_test_to_be_meaningful() -> None:
    """Otherwise the assertion above passes for the wrong reason, on every machine.

    Not an assertion that `.env` exists — it legitimately may not, in CI or a fresh
    clone. It records which case ran, so a green suite cannot be mistaken for proof
    that the leak is closed when there was nothing to leak.
    """
    from pathlib import Path

    dotenv = Path(__file__).resolve().parent.parent / ".env"
    if not dotenv.exists():
        pytest.skip("no .env in this checkout: the leak has nothing to expose here")
    # It exists, so the test above was a real probe rather than a tautology.
    assert dotenv.read_text().strip(), ".env exists but is empty"


def test_the_clear_list_covers_every_variable_settings_reads() -> None:
    """The drift guard, and the half that cannot be derived.

    Asserting "these vars are absent" would pass trivially on a machine where nobody
    exported them, which proves nothing. Coverage is what is checkable. Our own half is
    *derived* from `Settings.model_fields` rather than listed, so it cannot drift — this
    pins that it stays derived, because a hand-written list is exactly what leaked
    seven variables (`JMC_API_KEY_HEADER`, `JMC_TRANSPORT`, `JMC_PORT` among them) on
    the first attempt at this fixture.

    The upstream names are the part no field can derive, so those are asserted
    explicitly: they are read by code we do not control, which is the side where a
    missing entry is invisible.
    """
    from conftest import _ECOSYSTEM_VARS, _ENV_PREFIX

    from just_module_creator.settings import Settings

    # An empty prefix would make the derivation produce bare names that clear nothing,
    # silently. Fail here instead.
    assert _ENV_PREFIX, "Settings lost its env_prefix; the derived clear-list is now wrong"
    readable = {f"{_ENV_PREFIX}{name}".upper() for name in Settings.model_fields}

    missing = readable - set(_ECOSYSTEM_VARS)
    assert not missing, f"_ECOSYSTEM_VARS stopped being derived from the model: {sorted(missing)}"
    # More than the credentials: an exported JMC_TRANSPORT or JMC_PORT changes what a
    # test asserts just as effectively as a token does, and far less visibly.
    assert {"JMC_API_KEY_HEADER", "JMC_TRANSPORT", "JMC_PORT"} <= set(_ECOSYSTEM_VARS)
    assert {"JUST_DNA_CONTACT_EMAIL", "NCBI_API_KEY", "REGISTRY_TOKEN"} <= set(_ECOSYSTEM_VARS)


async def test_building_a_server_cannot_repopulate_the_environment_from_dotenv():
    """`F24`'s other half: `delenv` is only safe while nothing re-reads `.env` mid-test.

    The original fixture reasoned that `delenv` was fine because "nothing in the suite
    calls `load_dotenv`". That was true of our code and never true of the dependency
    tree — `just_dna_enricher.locations` calls it when a cache path is resolved, which
    `build_server` reaches through `net.py`. And `load_dotenv(override=False)` skips a
    key that is *present*, so deleting the variable is exactly what lets the file win.

    Measured before the fix, on a machine with a real `.env`: `JMC_TEST_API_KEY` was
    `None` after the fixture and held a live `mk_live_…` token immediately after
    `build_server` — a fresh session then resolved a credential nobody passed it.

    Asserted over `build_server` rather than over the loader, because the loader is an
    implementation detail of a package we do not own and the property is about ours.
    """
    import os

    from conftest import _ECOSYSTEM_VARS, offline_settings

    from just_module_creator.server import build_server

    before = {var: os.environ.get(var) for var in _ECOSYSTEM_VARS}
    assert before.get("JMC_TEST_API_KEY") is None  # the fixture ran

    build_server(mode="essentials", settings=offline_settings())

    after = {var: os.environ.get(var) for var in _ECOSYSTEM_VARS}
    repopulated = {var: value for var, value in after.items() if value != before[var]}
    assert not repopulated, (
        "building a server put these back into os.environ from .env: "
        f"{sorted(repopulated)} — the dotenv sweep in conftest has stopped covering "
        "whoever loads it now"
    )


def test_the_dotenv_sweep_actually_finds_the_loader_that_broke_this():
    """A sweep that patched nothing would pass the test above on a machine with no `.env`.

    So assert the mechanism directly: the module that reintroduced the leak is one of
    the ones the sweep reaches, and what it holds is the refusal rather than the real
    loader. Named explicitly because this is the concrete case that failed.
    """
    import just_dna_enricher.locations as locations
    from conftest import _refuse_dotenv

    assert locations.load_dotenv is _refuse_dotenv
