"""Shared pytest fixtures: in-memory FastMCP clients (no network/process).

Passing the server object straight to ``Client`` uses FastMCP's in-memory
transport — fast, deterministic, and ideal for agent-driven TDD loops.

Every fixture here forces ``offline=True``. The offline ceiling in
``Settings`` means no test can reach the network by accident, so the suite
stays deterministic even though half the tool surface is network-capable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp.client import Client

from just_module_creator.server import build_server
from just_module_creator.settings import Mode, Settings

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
    return Settings(offline=True, _env_file=None, **overrides)


@pytest.fixture
async def essentials_client():
    server = build_server(mode="essentials", settings=offline_settings())
    async with Client(transport=server) as client:
        yield client


@pytest.fixture
async def extended_client():
    server = build_server(mode="extended", settings=offline_settings())
    async with Client(transport=server) as client:
        yield client


@pytest.fixture
def make_client():
    """Factory returning a fresh in-memory client (its own session)."""

    def _make(mode: Mode = "essentials", settings: Settings | None = None):
        server = build_server(mode=mode, settings=settings or offline_settings())
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
