"""Shared pytest fixtures: in-memory FastMCP clients (no network/process).

Passing the server object straight to ``Client`` uses FastMCP's in-memory
transport — fast, deterministic, and ideal for agent-driven TDD loops.

Every fixture here forces ``offline=True``. The offline ceiling in
``Settings`` means no test can reach the network by accident, so the suite
stays deterministic even though half the tool surface is network-capable.

**Hermeticity is a mechanism here, not a convention** (``F24``). See
``_hermetic_configuration`` below: it is autouse, so a construction that forgets
``_env_file=None`` reads nothing rather than reading the developer's real tokens.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastmcp.client import Client
from just_dna_compiler import hints as _hints

# Unconditional since 0.35.0: the floor is `just-dna-enricher>=0.7.0,<0.8` and the 0.7.0
# **wheel** carries `caches` (15 lanes) and `locations.CACHE_BASE_VAR`. This was the
# guarded module-level import § 2 allows for an optional dependency, and it was genuinely
# optional only for the length of that interval — the repo has no optional imports again.
from just_dna_enricher.caches import CACHE_LANES
from just_dna_enricher.locations import CACHE_BASE_VAR
from just_dna_registry import specfiles as _specfiles

from just_module_creator.server import build_server
from just_module_creator.settings import Settings

#: Variables read by code we do **not** control, so no field on our model names them
#: and nothing can derive them. Hand-maintained by necessity; a test asserts the three
#: load-bearing ones are here.
_UPSTREAM_VARS = (
    "REGISTRY_TOKEN",
    "REGISTRY_TEST_TOKEN",
    "JUST_DNA_CONTACT_EMAIL",
    "NCBI_API_KEY",
)

#: Every cache location the enricher reads from the environment — **derived**, since
#: format 0.7 (our ``S89``, their RM184). ``CacheLane.env_var`` is the same constant the
#: lane's own resolver reads, so a lane added upstream arrives here with its variable
#: attached; ``CACHE_BASE_VAR`` is the shared base, deliberately not a lane attribute
#: because no lane owns it.
#:
#: **Nothing in the suite asserts differently with these set today** — measured on
#: 2026-09-03 by exporting all fourteen at a scratch path: 658 passed, unchanged. They
#: are cleared anyway, and the reason is the shape of the leak rather than a known one:
#: ``F24`` was a bare ``Settings()`` reading a developer's real token, found only after
#: it had been possible for weeks, and the repair was to stop reasoning about which
#: variables matter. A derived list costs one expression and removes the question.
_CACHE_VARS = tuple(sorted({lane.env_var for lane in CACHE_LANES} | {CACHE_BASE_VAR} - {""}))


#: The spec files the installed compiler reads and the installed registry does not
#: recognise — **computed, because both sides move on their own cadence** and a literal
#: set would be wrong on every toolchain. Empty on 0.6.6; the two concordance tables on
#: format 0.7 beside registry 0.18.2; `expression_effects.csv` alone on format 0.7
#: beside registry 0.25.0. A file here is one a re-publish **drops silently** — the
#: module recompiles green having quietly lost a table it was compiled with, which is
#: the `licensing.csv`-before-registry-0.16.2 failure.
def registry_lag() -> set[str]:
    """Derived tables the compiler writes and the registry does not recognise.

    **The floor is on the INPUTS, never on the answer.** An empty lag is the good state
    and is what this install reports today, so a floor on the result would fail on
    success. What must not render empty is either enumeration this walks: a subset
    assertion over nothing passes, and an enumeration of a *foreign* symbol goes empty
    when the **import moves** rather than when a name changes — so a restructure upstream
    would read as *every table the compiler writes is recognised here*, which is the one
    sentence these rosters exist to be able to deny.

    Measured 2026-09-11: 12 derived models, 28 recognised spec files. The floors sit well
    under both, because they are asking *did the enumeration happen*, not *is the count
    still 12*. Prompted by the registry finding three unfloored subset guards of their
    own, 2026-09-11.
    """
    assert len(_hints.DERIVED_TABLE_MODELS) >= 8, (
        "the compiler's derived-table roster enumerated almost nothing — the symbol moved, "
        "and every roster guard reading it is now vacuous"
    )
    assert len(_specfiles.RECOGNIZED_SPEC_FILES) >= 20, (
        "the registry's recognised-file roster enumerated almost nothing — the symbol moved"
    )
    return {name for name in _hints.DERIVED_TABLE_MODELS if not _specfiles.is_spec_file(name)}


#: What the lag is *allowed* to be, and the membership is a filed report rather than a
#: convenience. Computing the lag makes the roster tests work on any toolchain; this keeps
#: them a guard rather than a tautology, by failing when an **unreported** name joins.
#:
#: **Empty since 0.35.0, and that is the good direction.** It held three names — the
#: concordance pair (registry-tree `S19`) and `expression_effects.csv` (`S22`) — each kept
#: because an install on the then-current PyPI registry still lagged them. A
#: `just-dna-registry>=0.25.2` floor retires that install: 0.25.2 recognises all three, and
#: `registry_lag()` is empty against it. Shrinking the lag must never fail this suite, which
#: is why the assertion is a `<=` and this can be empty without becoming a tautology — the
#: floors inside `registry_lag()` are what stop that.
#:
#: A name goes back in **with its `S<n>`** and not otherwise: the entry is the filed report,
#: so an addition here without one is the guard being silenced rather than answered.
KNOWN_REGISTRY_LAG: frozenset[str] = frozenset()

#: Every environment variable that could change what a test asserts, cleared for the
#: whole suite by ``_hermetic_configuration``.
#:
#: **Ours are derived, never listed.** Every field on ``Settings`` is readable as
#: ``JMC_<FIELD>``, so a hand-written list drifts the first time a setting is added —
#: and it did: the first draft of this covered the credentials and missed
#: ``JMC_API_KEY_HEADER``, ``JMC_TRANSPORT``, ``JMC_PORT`` and four more, every one of
#: which an exported value would silently change an assertion with. Deriving removes
#: the failure mode instead of testing for it.
#: ``.get`` because ``env_prefix`` is not a required key on ``SettingsConfigDict``. No
#: literal fallback: hardcoding ``"JMC_"`` here would be the second source of truth this
#: derivation exists to avoid, and a missing prefix is caught by a test rather than
#: papered over into a list of unprefixed names that clear nothing.
_ENV_PREFIX = Settings.model_config.get("env_prefix") or ""

_ECOSYSTEM_VARS = (
    tuple(f"{_ENV_PREFIX}{name}".upper() for name in Settings.model_fields)
    + _UPSTREAM_VARS
    + _CACHE_VARS
)


def _refuse_dotenv(*args: object, **kwargs: object) -> bool:
    """Stand-in for ``load_dotenv`` during the suite: reads nothing, reports nothing.

    Returns ``False`` — dotenv's own "no file was loaded" answer — so a caller that
    branches on the result takes the same path it would on a machine with no ``.env``,
    which is the machine the suite is pretending to be.
    """
    return False


@pytest.fixture(autouse=True)
def _hermetic_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make a forgotten ``_env_file=None`` harmless instead of silently live.

    ``F24``: ``CLAUDE.md`` §6 claimed the suite could not read a developer's
    ``.env``, but that held only for as long as every construction remembered the
    kwarg. A bare ``Settings()`` read the real file — and the leak was worse than
    one credential, because it also lost ``offline=True``, so a test could reach the
    network *with* a live token. Reproduced against a real `.env`: a bare
    ``Settings().test_api_key`` returned an ``mk_live_…`` polygon token.

    That is the worst failure shape available — it passes locally, passes in CI where
    ``.env`` is absent, and quietly means something different on each machine. So it
    is closed with a mechanism rather than a rule.

    Two halves, because the file is not the only route:

    1. ``env_file`` is pointed at a path that cannot exist. Not removed from
       ``model_config`` — the product genuinely needs it, and breaking the product to
       protect the suite would be the wrong trade.
    2. The ecosystem's variables are cleared from ``os.environ``, so an *exported*
       shell variable cannot do what the file no longer can.

    ``delenv`` rather than ``setenv(VAR, "")``, because these variables reach typed
    fields: ``JMC_PORT=""`` and ``JMC_OFFLINE=""`` are parse errors, not "unset". A
    test that wants to say "no credential" to a reader doing ``x or
    os.environ.get(...)`` should still use ``setenv(VAR, "")`` — running after this
    fixture, it wins.

    **Third half, and it is the one that had actually stopped holding.** ``delenv``
    is only safe while nothing re-reads ``.env`` mid-test, and the original note
    asserted that nothing did. That was true of *our* code and never true of the
    dependency tree: ``just_dna_enricher.locations`` calls ``load_dotenv`` when a
    cache path is resolved, which ``build_server`` reaches through ``net.py``. And
    ``load_dotenv(override=False)`` skips a key that is *present* — so deleting the
    variable is precisely what lets the file win. Measured on this tree before the
    fix: ``JMC_TEST_API_KEY`` was ``None`` after the fixture and held a live
    ``mk_live_…`` polygon token immediately after ``build_server``.

    So the loader itself is neutralized. **Derived, never listed**: every module that
    did ``from dotenv import load_dotenv`` holds its own binding, so patching
    ``dotenv.load_dotenv`` would miss all of them — the sweep walks ``sys.modules``
    instead, which covers a dependency that starts calling it in some later release
    without anyone remembering this fixture exists.
    """
    monkeypatch.setitem(
        Settings.model_config, "env_file", str(Path(__file__).parent / ".env.nonexistent")
    )
    for module in list(sys.modules.values()):
        if getattr(module, "load_dotenv", None) is not None:
            monkeypatch.setattr(module, "load_dotenv", _refuse_dotenv, raising=False)
    for var in _ECOSYSTEM_VARS:
        monkeypatch.delenv(var, raising=False)


MODULE_SPEC = """\
schema_version: '1.0'
module:
  title: Lactose Tolerance (test)
  description: MCM6 lactase persistence variants
  report_title: Lactose Tolerance
  icon: leaf
  icon_set: fomantic
  color: '#a5673f'
  name: lactose_test
defaults:
  curator: ai-module-creator
  method: literature-review
genome_build: GRCh38
"""

VARIANTS = (
    "rsid,genotype,weight,state,conclusion,gene\n"
    "rs4988235,A/A,1.2,protective,Lactase persistence; lactose tolerant,MCM6\n"
    "rs4988235,G/G,-0.5,risk,Lactase non-persistence,MCM6\n"
)

STUDIES = (
    "rsid,pmid,population,conclusion\n"
    "rs4988235,11788828,Finnish,Original identification of the -13910 variant\n"
)


def offline_settings(**overrides) -> Settings:
    """Settings with the network ceiling down. Tests must never fetch.

    ``_env_file=None`` keeps the suite hermetic: a developer's own ``.env``
    must not change what the tests assert.
    """
    overrides.setdefault("api_key", None)
    # _env_file is a pydantic-settings init kwarg, absent from the generated
    # __init__ signature, so pyright cannot see it.
    return Settings(offline=True, _env_file=None, **overrides)  # type: ignore[call-arg]


def routed_settings(**overrides) -> Settings:
    """Hermetic settings with the offline ceiling **up**, for a stubbed egress route.

    `offline_settings` is the default and stays that way. This exists for the handful of
    tests that monkeypatch `client_for` and then exercise what the route *does* — the
    tools that leave this machine refuse under `JMC_OFFLINE` before they reach the stub,
    so asserting on their behaviour needs the ceiling down and the socket closed by the
    stub instead.

    It is not a hole in the suite's socket ceiling: nothing here resolves a real client.
    A test that forgets the stub fails on a connection rather than passing quietly, and
    `_hermetic_configuration` still clears the ecosystem's variables either way.
    """
    overrides.setdefault("api_key", None)
    return Settings(offline=False, _env_file=None, **overrides)  # type: ignore[call-arg]


@pytest.fixture
async def client():
    """The whole tool surface, over a fresh in-memory client.

    Under the fastmcp <4 pin (CLAUDE.md §11) a client speaks the initialize handshake: one
    connection for the whole session, so session state persists and a `task=True` tool runs
    inline. That is why this and `make_client` now build the same client — the fastmcp-4
    mode axis they used to straddle is gone with the pin, and the docstrings are kept as the
    record of what a re-upgrade has to re-split.
    """
    server = build_server(settings=offline_settings())
    async with Client(transport=server) as connected:
        yield connected


@pytest.fixture
def make_client():
    """Factory returning a fresh in-memory client (its own session).

    Dormant under the pin, kept for a re-upgrade: on fastmcp 4 this passed `mode="legacy"`
    (the initialize handshake — one connection, session state survives across calls) so that
    reveal/token tests had a wire where `ctx.set_state` and `ctx.enable_components` hold,
    while the `client` fixture exercised the modern (2026-07-28) worker path where they do
    not. Under fastmcp 3 the handshake is the only wire, so the `mode` kwarg is gone (it does
    not exist there) and the two fixtures coincide. Re-add `mode="legacy"` here and re-split
    `client` to the modern default when a 4.x is re-adopted.
    """

    def _make(settings: Settings | None = None):
        server = build_server(settings=settings or offline_settings())
        return Client(transport=server)

    return _make


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """A minimal but complete, compilable spec directory."""
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text(MODULE_SPEC)
    (spec / "variants.csv").write_text(VARIANTS)
    (spec / "studies.csv").write_text(STUDIES)
    return spec
