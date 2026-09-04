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

import inspect as _inspect
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from fastmcp.client import Client
from just_dna_compiler import draft as _draft
from just_dna_compiler import hints as _hints
from just_dna_enricher.enrich import enrich as _enrich
from just_dna_format import base as _format_base
from just_dna_format.manifest import Compilation as _Compilation
from just_dna_registry import specfiles as _specfiles

from just_module_creator.server import build_server
from just_module_creator.settings import Settings

# The cache registry is 0.7's (RM176) and the whole MODULE is absent on 0.6.6, so this is
# the guarded module-level import `CLAUDE.md` § 2 allows for an optional dependency — and
# it is genuinely optional only for the length of this interval. On the older toolchain
# there is nothing to clear, because the lanes those variables steer do not exist yet.
#
# It sits below the other imports so the fallbacks are bound and annotated first: the
# names then exist unconditionally for a reader and for pyright, which cannot resolve a
# module the installed package does not have and would otherwise report the import rather
# than the interval. Every suppression here is scoped to its own line and goes with the
# guard.
#
# **Delete the guard, not the import, when the floor moves to 0.7.**
CACHE_LANES: Sequence[Any] = ()
CACHE_BASE_VAR: str = ""
try:
    from just_dna_enricher.caches import CACHE_LANES  # type: ignore[no-redef]  # noqa: E402
    from just_dna_enricher.locations import CACHE_BASE_VAR  # type: ignore[no-redef]  # noqa: E402
except ImportError:  # pragma: no cover — only on a pre-0.7 enricher
    pass


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
_CACHE_VARS = tuple(
    sorted({lane.env_var for lane in CACHE_LANES} | {CACHE_BASE_VAR} - {""})
)

#: **Capability probes, never a version string.** Six assertions below are about
#: behaviour format 0.7 introduced, and this branch runs against an uncut 0.7 while a
#: released install is still on 0.6.6 — so they must skip honestly rather than fail on
#: the toolchain a user actually has. Each probes the narrowest symbol that answers its
#: own question, because `CLAUDE.md` § 8's rule holds here too: a version string says
#: nothing about what is installed, and `hasattr` against the *installed* package does.
#:
#: `_FORMAT_0_7` is the one stand-in. `OUTSIDE_CONTENT_IDENTITY` is RM180's field marker,
#: used because the two behaviours it gates — RM141's shared strict predicate and the
#: overlay's presence in the content hash — ship no symbol of their own. **Delete every
#: one of these the day the floor moves to 0.7**; they exist for the interval, not
#: forever.
_FORMAT_0_7 = hasattr(_format_base, "OUTSIDE_CONTENT_IDENTITY")
_ENRICH_TAKES_PROGRESS = "progress" in _inspect.signature(_enrich).parameters
_COMPILER_CODES_WARNINGS = "warnings_summary" in _Compilation.model_fields
_COMPILER_DRAFTS_OVERLAY = "overrides.csv" in _draft.DRAFTABLE

needs_format_0_7 = pytest.mark.skipif(
    not _FORMAT_0_7, reason="installed format predates 0.7 (no OUTSIDE_CONTENT_IDENTITY)"
)
needs_progress_callback = pytest.mark.skipif(
    not _ENRICH_TAKES_PROGRESS, reason="installed enricher has no progress callback (RM128)"
)
needs_coded_warnings = pytest.mark.skipif(
    not _COMPILER_CODES_WARNINGS, reason="installed compiler writes no warnings_summary (RM131)"
)
needs_overlay = pytest.mark.skipif(
    not _COMPILER_DRAFTS_OVERLAY, reason="installed compiler does not draft overrides.csv (RM124)"
)

#: The spec files the installed compiler reads and the installed registry does not
#: recognise — **computed, because both sides move on their own cadence** and a literal
#: pair would be wrong on either toolchain. Empty on 0.6.6; the two concordance tables
#: on 0.7. A file here is one a re-publish drops silently (registry-tree `S19`, `F88`).
def registry_lag() -> set[str]:
    return {
        name for name in _hints.DERIVED_TABLE_MODELS if not _specfiles.is_spec_file(name)
    }


#: What the lag is *allowed* to be. Computing the lag makes the roster tests work on
#: either toolchain; this keeps them a guard rather than a tautology, by failing when a
#: THIRD name joins — which would be a new file nobody has reported yet.
KNOWN_REGISTRY_LAG = frozenset({"clin_sig_concordance.csv", "clin_sig_authority_calls.csv"})

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


@pytest.fixture
async def client():
    """The whole tool surface. There is one — the mode axis went in 0.21.0."""
    server = build_server(settings=offline_settings())
    async with Client(transport=server) as connected:
        yield connected


@pytest.fixture
def make_client():
    """Factory returning a fresh in-memory client (its own session)."""

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
