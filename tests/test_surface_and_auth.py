"""One tool surface, and the axes that are left: auth, offline, containment.

The mode axis is gone (0.21.0). ``JMC_MODE``, ``--mode`` and the ``extended``
tier were removed after three separate occasions on which the default tier taught
a step it could not run, so what used to be *"does this tool exist in this
tier?"* is now *"does this tool exist?"* — a weaker question that still catches
every failure the tier tests were actually built for, because the failure shape
was always a doc naming something the caller could not call.

Auth decides whether the registry tools **work**, per call and per instance. The
offline ceiling is the safety property a per-call ``offline=False`` must never
punch through. Containment is ``JMC_WORKSPACE``.
"""

from __future__ import annotations

import inspect
import re
from importlib import metadata

import pytest
from conftest import offline_settings  # tests/ is on sys.path via pytest rootdir
from fastmcp.exceptions import ToolError
from pydantic import BaseModel

from just_module_creator import models
from just_module_creator.auth import GATED_TOOLS, resolve_install_id
from just_module_creator.server import INSTRUCTIONS, build_server
from just_module_creator.settings import Settings
from just_module_creator.toolbox import CORE

# The authoring loop an agent cannot work without.
AUTHORING_LOOP = {
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
    # mind is real. Without it, an author writes one from memory.
    "lookup_identifier",
    "check_identifiers",
}

# Bounded by a CORPUS rather than by what the caller named. That was the whole
# content of the extended tier, and the cost measurement behind it still stands:
# `enrich_gwas_effects` spends `1 + 2N` requests for a variant with N published
# associations, measured at 382 for one real module.
#
# What changed in 0.21.0 is who is told. Hiding a tool never made its pass
# cheaper; it made the tool invisible to exactly the sessions that needed it, and
# it took cheap tools with it every time the line was drawn — `enrich_module` in
# 0.4.0, `registry_download` and `refresh_sidecar` in the two 2026-08-21
# unattended runs, one of which wrote a script against an undocumented `/files/`
# endpoint rather than conclude the tool existed. So the cost is now a sentence in
# each tool's own docstring, which is where a caller who could weigh it will read
# it, and `test_the_corpus_sized_tools_say_what_they_cost` is what keeps that
# sentence from drifting away from the tool.
CORPUS_SIZED = {
    "paper_citations",
    "draft_from_cpic",
    "draft_from_clinpgx",
    "enrich_facts",
    "enrich_literature_pass",
    "enrich_gwas_effects",
}

#: Prefixes every tool name in this server shares. A backticked word starting with
#: one of these, in a tool description, is a tool being named — which is what makes
#: `test_docstrings_only_name_tools_that_exist` able to tell a tool from a column.
TOOL_PREFIXES = (
    "registry_",
    "draft_from_",
    "enrich_",
    "lookup_",
    "describe_",
    "compare_",
    "refresh_",
    "record_",
    "review_",
    "list_",
    "table_",
    "check_",
    "lint_",
    "audit_",
    "study_",
    "verify_",
    "fetch_",
    "paper_",
    "close_",
    "scaffold_",
    "validate_",
    "compile_",
    "literature_",
    "module_",
    "reverse_",
    "get_template",
    "authenticate",
)


async def _names(client) -> set[str]:
    return {t.name for t in await client.list_tools()}


async def test_the_surface_exposes_the_authoring_loop(client):
    names = await _names(client)
    assert names >= AUTHORING_LOOP


async def test_every_tool_the_taught_workflow_names_exists(client):
    """Every tool the server's own instructions name must be registered.

    The server teaches an order in ``INSTRUCTIONS``. Teaching a step that cannot
    be run is the defect this asserts against — ``enrich_module`` was named in
    that order while being extended-only, so an agent following the instructions
    hit a tool that was not there. The tier is gone and the assertion is weaker
    for it, but the failure shape survives the tier: a taught name that no longer
    resolves (renamed, moved, dropped) fails here exactly as it did before.
    Derived from the text rather than restated, so editing the order re-checks it.
    """
    # Bounded by the blank line that ends the block, not by the prose that
    # follows it: this read `.split("Three rules")` until renumbering those rules
    # silently widened the slice to the whole document and reported an unrelated
    # tool as a tiering bug.
    workflow = INSTRUCTIONS.split("Work in this order:")[1].split("\n\n")[1]
    registered = await _names(client)
    words = {word for word in re.findall(r"[a-z_]{4,}", workflow)}
    named = {word for word in words if word in registered}

    assert named, "parsed no tool names out of the taught workflow — the format changed"
    taught_tools = {w for w in words if w.startswith(TOOL_PREFIXES)}
    assert taught_tools <= registered, sorted(taught_tools - registered)


def test_instructions_name_the_running_toolchain():
    """The header states the loaded format/compiler, and never a literal (RM13).

    It said "format 0.5" for two releases while the installed format was 0.6 — a
    hardcoded version that a stale build reports just as confidently as a current
    one. Computed here rather than pasted, for the same reason.
    """
    assert f"just-dna-format {metadata.version('just-dna-format')}" in INSTRUCTIONS
    assert f"just-dna-compiler {metadata.version('just-dna-compiler')}" in INSTRUCTIONS


async def test_docstrings_only_name_tools_that_exist(client):
    """A docstring that hands you a tool you cannot call is a dead end.

    `test_every_tool_the_taught_workflow_names_exists` guards the taught order and
    nothing else, so this went unnoticed until an unattended run hit it:
    `compare_to_published`'s docstring ended "`next_step` names the
    `registry_download` + `compare_modules` pair that gets it", naming a tool the
    default tier did not have. The run followed the sentence, found nothing, and
    concluded the capability existed nowhere.

    Removing the tier removes that particular way of being wrong, and leaves this
    one: a renamed or retired tool still named in a sibling's description. A
    backticked word starting with one of `TOOL_PREFIXES` is a tool being named,
    which is what tells a tool from a column or a file.
    """
    listed = await client.list_tools()
    registered = {t.name for t in listed}

    # A backticked word can be a tool, a field we return or an argument a tool
    # takes, and only the first kind can be a dead end. Both exclusions are
    # GENERATED — from the live input schemas and from our own result models — so
    # neither goes stale the way a hand-kept allowlist of "words that look like
    # tools but are not" would.
    data_words: set[str] = set()
    for tool in listed:
        data_words |= set((tool.inputSchema or {}).get("properties", {}))
    for obj in vars(models).values():
        if inspect.isclass(obj) and issubclass(obj, BaseModel):
            data_words |= set(obj.model_fields)

    offenders: list[str] = []
    for tool in listed:
        text = tool.description or ""
        for named in sorted(set(re.findall(r"`([a-z][a-z0-9_]{3,})`", text))):
            if named in registered or named in data_words:
                continue
            if named.startswith(TOOL_PREFIXES):
                offenders.append(f"{tool.name} names `{named}`, which is not registered")
    assert not offenders, "\n".join(offenders)


async def test_the_corpus_sized_tools_say_what_they_cost(client):
    """They are all reachable, and each one warns in its own description.

    This is the whole replacement for the tier: nothing refuses, and the caller is
    told before spending the budget. A tool that stops saying so is a tool whose
    cost became invisible, which is how the flag got added in the first place.
    """
    names = await _names(client)
    assert names >= CORPUS_SIZED

    silent = []
    for tool in await client.list_tools():
        if tool.name not in CORPUS_SIZED:
            continue
        text = (tool.description or "").lower()
        if not any(
            phrase in text
            for phrase in ("corpus", "published rather than", "how much has been published",
                           "requests", "budget")
        ):
            silent.append(tool.name)
    assert not silent, f"corpus-sized tools with no cost warning: {silent}"


async def test_gated_tools_are_listed_by_default(client):
    """Listed and refusing per call, so an agent can discover them without a token.

    Hiding them is now possible per session — `ctx.enable_components` is
    session-scoped, unlike `mcp.enable` — and is opt-in behind
    `JMC_HIDE_GATED_UNTIL_AUTH`. The default stays *listed*, because a hidden tool
    answers a call by name with "Unknown tool" instead of a message saying how to
    get a token.
    """
    assert set(GATED_TOOLS) <= await _names(client)


async def test_gated_tool_without_a_token_returns_not_raises(client):
    result = await client.call_tool("registry_whoami", {})
    assert result.data.success is False
    assert "registry token" in result.data.message


async def test_authenticate_stores_a_token_for_this_session(client):
    result = await client.call_tool("authenticate", {"token": "tok_abc123"})
    assert result.data.authenticated
    assert set(result.data.unlocked_tools) == set(GATED_TOOLS)
    # It stores; it does not claim the registry accepted anything.
    assert "registry_whoami" in result.data.message


async def test_authenticate_rejects_an_empty_token(client):
    result = await client.call_tool("authenticate", {"token": "   "})
    assert result.data.authenticated is False


# --------------------------------------------------------------------------- #
# Onboarding — the one registry write that cannot be token-gated
# --------------------------------------------------------------------------- #
async def test_onboarding_tools_are_on_the_surface(client):
    """The route to a token must be visible.

    Behind a flag it would be a dead end in a different place: every other
    registry tool needs a token, and only this one produces one. That is also why
    `registry_register` is pinned visible when the listing is narrowed — by tool
    search, or by hiding the gated tools until a session authenticates.
    """
    names = await _names(client)
    assert {"registry_register", "registry_namespace_available"} <= names


async def test_the_tool_that_mints_the_token_is_not_gated_by_one():
    assert "registry_register" not in GATED_TOOLS


async def test_onboarding_tools_respect_the_offline_ceiling(make_client):
    async with make_client(offline_settings()) as client:
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
    async with make_client(Settings(offline=False, _env_file=None)) as client:  # type: ignore[call-arg]
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
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="offline"):
            await client.call_tool("registry_search", {"target": "prod", "query": "lactose"})


async def test_offline_settings_block_every_literature_tool(make_client):
    """There is no offline literature snapshot, so `offline` refuses rather than degrades.

    Upstream is explicit that one will never exist — once literature.csv is
    written it IS the pin — so serving a stale answer here would be inventing a
    guarantee nobody made.
    """
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="offline|JMC_OFFLINE"):
            await client.call_tool("literature_search", {"query": "lactase persistence"})
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
    async with make_client(offline_settings()) as client:
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

    async with make_client(settings) as client:
        ok = await client.call_tool(
            "scaffold_module", {"spec_dir": str(inside / "spec"), "name": "m"}
        )
        assert ok.data.written

        with pytest.raises(ToolError, match="outside the configured workspace"):
            await client.call_tool(
                "scaffold_module", {"spec_dir": str(tmp_path / "elsewhere"), "name": "m"}
            )


async def test_no_workspace_means_no_restriction(make_client, tmp_path):
    async with make_client(offline_settings()) as client:
        result = await client.call_tool(
            "scaffold_module", {"spec_dir": str(tmp_path / "anywhere"), "name": "m"}
        )
        assert result.data.written


# --------------------------------------------------------------------------- #
# Server-level contract
# --------------------------------------------------------------------------- #
def test_a_stale_jmc_mode_in_the_environment_is_ignored(monkeypatch) -> None:
    """Every install that predates 0.21.0 has `JMC_MODE` somewhere — it must be inert.

    A shell export, an old `.mcp.json`, a `.env` nobody edited. `Settings` no longer
    has a `mode` field, so the variable is an extra, and `extra="ignore"` is what
    makes an upgrade silent rather than a ValidationError at boot for everybody.
    The suite cannot catch this by accident: `conftest`'s clear-list is derived from
    `Settings.model_fields`, which no longer names `mode`, so the variable is never
    set under the suite unless a test sets it — as this one does.
    """
    monkeypatch.setenv("JMC_MODE", "extended")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert not hasattr(settings, "mode")
    assert build_server(settings=settings) is not None


async def test_server_boots_with_no_environment(monkeypatch):
    """Authoring needs no registry account, so a bare env must never fail."""
    for var in ("JMC_API_KEY", "REGISTRY_TOKEN", "JMC_OFFLINE"):
        monkeypatch.delenv(var, raising=False)
    from just_module_creator.server import build_server

    assert build_server() is not None


async def test_resource_and_prompt_are_registered(client):
    resources = {str(r.uri) for r in await client.list_resources()}
    assert "resource://just-dna/tables" in resources
    prompts = {p.name for p in await client.list_prompts()}
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

    build_server(settings=offline_settings())

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


async def test_paper_citations_accepts_an_unambiguous_direction(client):
    """`cited_by` reads as its own opposite, so two clear spellings were added.

    Everywhere else in bibliometrics "cited by" labels the citations a paper
    RECEIVED — Scholar's "Cited by 1,234". Here the legacy spelling means the
    papers in its own bibliography, which is what `citing` is not. Found by
    running the tool rather than by reading it.

    The legacy spelling stays accepted: the tool surface is the contract, and a
    dropped spelling breaks a caller silently.
    """
    schema = None
    for tool in await client.list_tools():
        if tool.name == "paper_citations":
            schema = tool
            break
    assert schema is not None

    described = schema.description or ""
    assert "trap" in described
    assert "`citing`" in described and "`references`" in described

    # All three backwards spellings are legal, and a wrong one names the choices.
    with pytest.raises(ToolError) as caught:
        await client.call_tool(
            "paper_citations", {"pmid": "11788828", "direction": "sideways"}
        )
    for spelling in ("citing", "references", "cites", "cited_by"):
        assert spelling in str(caught.value)


#: Claude Code truncates MCP server instructions to this and reports it only in its
#: own debug log — `Server instructions truncated from 9220 to 2048 chars`, seen on
#: 2.1.238. Nothing on our side raises, so the failure is invisible from here.
_INSTRUCTIONS_CEILING = 2048

#: Held back from the ceiling because the text interpolates version numbers that grow:
#: `0.6.1` becomes `0.10.12` and the string is four characters longer for a reason no
#: edit to this file caused. A test that passed at exactly the ceiling would start
#: failing on somebody else's release.
#:
#: Raised from 24 to 36 on 2026-08-22, when the block gained a THIRD interpolated
#: version — the plugin's own, added because two unattended runs each spent their
#: opening calls working out which of two installed copies had answered. The
#: reservation is per version string, so adding one and leaving the slack alone would
#: have left a single character of headroom against an upstream patch release.
_VERSION_SLACK = 36


def test_the_instructions_fit_in_what_the_host_will_actually_keep():
    """0.14.0 shipped 9220 characters into a 2048 window and nobody could tell.

    Three quarters of the server's own instructions never reached the model. The cut
    landed mid-rule-3, so the surviving text ended on *"A mismatch against a source is
    not a defect report. Archi"* and every registry rule — the polygon default, the
    irreversibility of production, the explicit-yes requirement — was silently absent
    from a surface whose whole job is to carry them.

    The fix was not a shorter list of rules but moving the *procedure* into the skills
    that already owned it, leaving the map plus what no skill may soften. So this
    asserts the budget, not the wording.
    """
    budget = _INSTRUCTIONS_CEILING - _VERSION_SLACK
    assert len(INSTRUCTIONS) <= budget, (
        f"{len(INSTRUCTIONS)} chars, and the host keeps {_INSTRUCTIONS_CEILING}. "
        f"Everything past that is dropped without an error. Move detail into a skill "
        f"— the tail is where the registry rules live, and the tail is what is lost"
    )


# --------------------------------------------------------------------------- #
# A description is context, and the core group's is context every session pays for
# --------------------------------------------------------------------------- #
_CORE_CEILING = 2
_ESSAY_CEILING = 6


def _paragraphs(tool) -> int:
    return len([b for b in (tool.description or "").strip().split("\n\n") if b.strip()])


async def test_the_core_tools_keep_their_descriptions_short(client):
    """One paragraph is right, two is acceptable, three is water — for `core`.

    A docstring here is not documentation: it is the tool's description, sent to
    every client on every connection. The listing measured 61,458 tokens — 31% of a
    200k window — with 70,528 characters in descriptions when this ceiling was
    written, and `core` is the part nobody can decline: it is what a layered server
    lists and what a flat one puts in front of every session regardless. The pass
    that brought it under this rule took descriptions to 59,751 characters, the flat
    listing to 58,586 tokens and the layered one to 17,759.

    Prose explaining *why the tool is shaped this way* — the defect it closed, the
    measurement behind it, the option that was rejected — belongs in a comment
    above it, where whoever edits the code reads it and no session pays for it.
    """
    # `toolbox` is not in CORE and is held to CORE's ceiling anyway: it is the one
    # tool listed in EVERY configuration — flat, layered, and as one of five pinned
    # tools under layered+search, where its description would otherwise be a
    # double-digit share of a 2,507-token surface. The roster is what the *call*
    # returns; the description only has to get you there.
    un_declinable = set(CORE) | {"toolbox"}
    offenders = [
        f"{t.name}: {_paragraphs(t)} paragraphs"
        for t in await client.list_tools()
        if t.name in un_declinable and _paragraphs(t) > _CORE_CEILING
    ]
    assert not offenders, "\n".join(sorted(offenders))


async def test_no_description_anywhere_becomes_an_essay(client):
    """Outside `core` the ceiling is looser, because the cost is opt-in and real.

    A tool a session reveals deliberately — a drafter, a bulk pass, a registry
    write — can carry five paragraphs when five is what the thing genuinely takes,
    and several here do. What this catches is the other shape: the rule, then its
    history, then the defect that motivated it, then the measurement, then the
    upstream ticket. Those have homes that cost nobody context.
    """
    offenders = [
        f"{t.name}: {_paragraphs(t)} paragraphs"
        for t in await client.list_tools()
        if _paragraphs(t) > _ESSAY_CEILING
    ]
    assert not offenders, "\n".join(sorted(offenders))
