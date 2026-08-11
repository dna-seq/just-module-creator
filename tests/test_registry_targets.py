"""The prod/polygon split: which instance a call reaches, and with whose token.

Three properties are load-bearing here and each has a test that fails loudly:

* **Every registry tool takes a `target`**, so a new one cannot quietly inherit
  a single endpoint.
* **The defaults are asymmetric on purpose** — writes rehearse on the polygon,
  catalog reads ask production — and an accidental flip is the failure this
  whole split exists to prevent.
* **Credentials never cross instances.** The two registries keep separate
  databases, so a production token is not a weaker key on the polygon; it is a
  key for an account that is not there.

The suite stays hermetic: nothing here opens a socket. The refusals under test
happen before any request, which is exactly why they are worth having.
"""

from __future__ import annotations

import pytest
from conftest import offline_settings

from just_module_creator.auth import SessionKeyStore, resolve_api_key, unauthenticated_result
from just_module_creator.settings import (
    DEFAULT_POLYGON_URL,
    DEFAULT_REGISTRY_URL,
    RegistryTarget,
    Settings,
)
from just_module_creator.targets import (
    TEST_MODULE_PREFIX,
    TEST_NAMESPACE_PREFIX,
    client_for,
    polygon_naming_note,
    prod_refusal,
)

#: Everything that speaks to a registry, and which instance it must default to.
#: Writes rehearse; catalog reads ask the published world. `authenticate` is a
#: write in this sense — it stores a credential *for* an instance.
REGISTRY_TOOL_DEFAULTS = {
    "registry_register": "test",
    "authenticate": "test",
    "registry_whoami": "test",
    "registry_namespace_available": "test",
    "registry_claim_namespace": "test",
    "registry_publish": "test",
    "registry_delete_version": "test",
    "registry_delete_module": "test",
    "registry_search": "prod",
    "registry_get_module": "prod",
    "registry_download": "prod",
}


def _no_credentials(monkeypatch) -> None:
    """Say "this environment has no registry token", for all four variables.

    ``setenv(..., "")`` rather than ``delenv``: an empty value is how a test says
    "no credential" to a reader that does ``x or os.environ.get(...)``, and
    ``load_dotenv(override=False)`` skips a key that is merely absent. All four
    because a developer's own ``.env`` must never decide what a test asserts.
    """
    for var in ("JMC_API_KEY", "JMC_TEST_API_KEY", "REGISTRY_TOKEN", "REGISTRY_TEST_TOKEN"):
        monkeypatch.setenv(var, "")


async def _schemas(client) -> dict[str, dict]:
    return {t.name: t.inputSchema for t in await client.list_tools()}


# --------------------------------------------------------------------------- #
# The prefixes are upstream's, and drift is a suite failure rather than a surprise
# --------------------------------------------------------------------------- #
def test_the_test_data_prefixes_match_the_ones_the_registry_enforces():
    """We duplicate two upstream values; this is what stops the copy going stale.

    They are duplicated rather than imported because both live outside the
    client's exported surface — see ``targets`` — so the guard has to be a test.
    """
    from just_dna_registry.config import Settings as RegistrySettings
    from just_dna_registry.services.purge import module_name_prefix

    upstream_prefix = RegistrySettings.model_fields["test_data_prefix"].default
    assert upstream_prefix == TEST_NAMESPACE_PREFIX
    assert module_name_prefix(upstream_prefix) == TEST_MODULE_PREFIX


# --------------------------------------------------------------------------- #
# Endpoints and tokens
# --------------------------------------------------------------------------- #
def test_each_target_resolves_to_its_own_endpoint():
    settings = offline_settings()
    assert settings.registry_url_for("prod") == DEFAULT_REGISTRY_URL
    assert settings.registry_url_for("test") == DEFAULT_POLYGON_URL
    assert settings.registry_url_for("prod") != settings.registry_url_for("test")


def test_a_production_token_is_never_offered_to_the_polygon(monkeypatch):
    """No cross-instance fallback, in either direction."""
    _no_credentials(monkeypatch)
    settings = Settings(_env_file=None, api_key="mk_live_prod")  # type: ignore[call-arg]

    assert settings.registry_token("prod") == "mk_live_prod"
    assert settings.registry_token("test") is None, (
        "a production key on the polygon is an unknown key, not a weaker one"
    )

    settings = Settings(_env_file=None, test_api_key="mk_live_poly")  # type: ignore[call-arg]
    assert settings.registry_token("test") == "mk_live_poly"
    assert settings.registry_token("prod") is None


def test_the_toolchain_env_vars_are_read_per_instance(monkeypatch):
    _no_credentials(monkeypatch)
    monkeypatch.setenv("REGISTRY_TOKEN", "from-toolchain")
    monkeypatch.setenv("REGISTRY_TEST_TOKEN", "from-toolchain-test")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.registry_token("prod") == "from-toolchain"
    assert settings.registry_token("test") == "from-toolchain-test"


def test_the_session_store_keeps_one_token_per_instance(monkeypatch):
    _no_credentials(monkeypatch)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    store = SessionKeyStore()

    store.set(None, "poly-key", "test")
    assert resolve_api_key(None, settings, store, "test") == "poly-key"
    assert resolve_api_key(None, settings, store, "prod") is None, (
        "authenticating against one instance must not unlock the other"
    )

    store.set(None, "prod-key", "prod")
    assert resolve_api_key(None, settings, store, "test") == "poly-key"
    assert resolve_api_key(None, settings, store, "prod") == "prod-key"


def test_the_two_instances_read_different_http_headers():
    settings = offline_settings()
    assert settings.api_key_header_for("prod") != settings.api_key_header_for("test")


def test_the_unauthenticated_message_names_the_instance_and_its_variable():
    settings = offline_settings()
    prod = unauthenticated_result(settings, "prod")
    test = unauthenticated_result(settings, "test")

    assert "JMC_API_KEY" in prod.message and DEFAULT_REGISTRY_URL in prod.message
    assert "JMC_TEST_API_KEY" in test.message and DEFAULT_POLYGON_URL in test.message
    assert prod.data == {"target": "prod", "registry_url": DEFAULT_REGISTRY_URL}
    assert test.data == {"target": "test", "registry_url": DEFAULT_POLYGON_URL}


# --------------------------------------------------------------------------- #
# The naming rules, checked before a round trip rather than after a 422
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"namespace": "test-modules"}, True),
        ({"name": "test_panel"}, True),
        ({"namespace": "eric-mods", "name": "lactose_tolerance"}, False),
        # The hyphen/underscore split is upstream's, not a normalisation we may
        # apply: a module named `test-panel` is refused as an illegal name long
        # before anything asks whether it is test data.
        ({"namespace": "testing-lab"}, False),
    ],
)
def test_production_refuses_test_data_by_its_own_spelling(kwargs, expected):
    assert (prod_refusal("prod", **kwargs) is not None) is expected
    assert prod_refusal("test", **kwargs) is None, "the polygon is where test data belongs"


def test_an_unprefixed_polygon_rehearsal_is_advised_not_refused():
    note = polygon_naming_note("test", namespace="eric-mods", name="lactose_tolerance")
    assert note is not None and "purge-test-data" in note
    assert polygon_naming_note("test", namespace="test-mods", name="test_lactose") is None
    assert polygon_naming_note("prod", namespace="eric-mods") is None


# --------------------------------------------------------------------------- #
# The surface itself
# --------------------------------------------------------------------------- #
async def test_every_registry_tool_takes_a_target(make_client):
    """A new registry tool that forgets `target` fails here rather than in the field."""
    async with make_client(mode="extended") as client:
        schemas = await _schemas(client)

    registry_tools = {
        name for name in schemas if name.startswith("registry_") or name == "authenticate"
    }
    assert registry_tools == set(REGISTRY_TOOL_DEFAULTS), (
        "a registry tool was added or renamed without deciding its default instance"
    )
    for name in registry_tools:
        assert "target" in schemas[name]["properties"], f"{name} cannot be aimed at an instance"


async def test_writes_rehearse_and_catalog_reads_ask_production(make_client):
    """The asymmetry is the design. A flip here is the accident it prevents."""
    async with make_client(mode="extended") as client:
        schemas = await _schemas(client)

    for name, expected in REGISTRY_TOOL_DEFAULTS.items():
        actual = schemas[name]["properties"]["target"].get("default")
        assert actual == expected, f"{name} defaults to {actual!r}, expected {expected!r}"


async def test_the_delete_verbs_refuse_production_before_sending_anything(make_client):
    """Polygon-only, and the refusal is ours: a 405 from the far end is not an answer.

    Reaching the network would fail the offline ceiling instead, so a passing
    assertion here also proves nothing was sent.
    """
    async with make_client() as client:
        for tool, args in (
            (
                "registry_delete_version",
                {"namespace": "eric-mods", "name": "lactose_tolerance", "version": "1.0.0"},
            ),
            ("registry_delete_module", {"namespace": "eric-mods", "name": "lactose_tolerance"}),
        ):
            result = await client.call_tool(tool, {**args, "target": "prod"})
            payload = result.structured_content or {}
            assert payload.get("success") is False
            assert "yank" in payload.get("message", ""), (
                "the refusal has to name what production offers instead"
            )


async def test_publishing_test_data_to_production_is_refused_locally(make_client):
    async with make_client() as client:
        result = await client.call_tool(
            "registry_publish",
            {
                "namespace": "test-modules",
                "name": "lactose_tolerance",
                "version": "1.0.0",
                "spec_dir": ".",
                "target": "prod",
            },
        )
    payload = result.structured_content or {}
    assert payload.get("success") is False
    assert "test_data_on_prod" in payload.get("message", "")


async def test_the_instructions_teach_the_split(make_client):
    """The tiers doc is the agent's map; a split it does not mention is not adopted."""
    from just_module_creator.server import INSTRUCTIONS

    assert 'target="test"' in INSTRUCTIONS and 'target="prod"' in INSTRUCTIONS
    assert "polygon" in INSTRUCTIONS


# --------------------------------------------------------------------------- #
# The declared target is verified by the server (F16, closed by registry 0.13)
# --------------------------------------------------------------------------- #
def test_a_client_pins_the_mode_its_target_names():
    """Our config says which instance we *meant*; the guard checks which answered.

    `expect_mode` is why `targets.py` no longer has to end with "we deliberately
    do not verify this". It costs no request — upstream asserts it lazily, on the
    calls that spend something — so it is passed uniformly rather than per site.
    """
    settings = offline_settings()

    assert client_for("test", settings)._expect_mode == "test"
    assert client_for("prod", settings)._expect_mode == "prod"


def test_the_mode_pin_uses_the_url_for_the_same_target():
    """A pin naming one instance while the URL names the other would be worse than none."""
    settings = offline_settings()

    pairs: tuple[tuple[RegistryTarget, str], ...] = (
        ("test", DEFAULT_POLYGON_URL),
        ("prod", DEFAULT_REGISTRY_URL),
    )
    for target, url in pairs:
        client = client_for(target, settings)
        assert client.base_url == url.rstrip("/")
        assert client._expect_mode == target


def test_every_client_in_the_server_is_built_through_client_for():
    """The guard is only real if no site constructs a client of its own.

    Asserted against the source rather than by behaviour: a forgotten
    `RegistryClient(...)` somewhere would publish to an unverified instance, and
    that is exactly the failure that cannot be undone.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src" / "just_module_creator"
    offenders = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if path.name != "targets.py" and "RegistryClient(" in path.read_text()
    }
    assert not offenders, f"construct these through targets.client_for: {sorted(offenders)}"


def test_a_token_reaches_the_client_and_absence_of_one_does_not_invent_a_header():
    settings = offline_settings()

    with_token = client_for("test", settings, token="abc")
    assert with_token._http.headers["Authorization"] == "Bearer abc"
    # No token means no header at all, not an empty bearer.
    assert "Authorization" not in client_for("test", settings)._http.headers
