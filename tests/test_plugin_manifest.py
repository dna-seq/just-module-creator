"""Plugin manifests are additional sources of truth, so the suite holds them to the first.

The Claude and Codex manifests cannot read `importlib.metadata`, so their `version`
has to be bumped by hand alongside `pyproject.toml` — the packaging boundary where
`CLAUDE.md` §2's "never hardcode a version string" cannot be obeyed. Discipline
alone already failed once
(0.3.0 shipped with a manifest still declaring 0.2.0, caught in review rather than by
the suite), and the failure is quiet: loading is unaffected, so the only symptom is an
installed plugin misreporting itself.

These tests turn every hand-maintained claim in the manifests into a failing assertion
instead. They read files and import nothing over the network.
"""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / ".claude-plugin" / "plugin.json"
CODEX_MANIFEST = REPO / ".codex-plugin" / "plugin.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def codex_manifest() -> dict:
    return json.loads(CODEX_MANIFEST.read_text())


def test_the_manifest_version_matches_the_package(manifest):
    """The bump that is easy to forget, and invisible when forgotten."""
    assert manifest["version"] == version("just-module-creator"), (
        "`.claude-plugin/plugin.json` has drifted from pyproject.toml. It cannot read "
        "importlib.metadata, so bump it by hand in the same commit as the release."
    )


def test_the_manifest_launches_the_console_script_pyproject_declares(manifest):
    """A renamed entry point would leave the plugin launching a command that is gone.

    `CLAUDE.md` §2 forbids renaming a user-facing command to dodge a stale `uv run`
    wrapper; this pins the other half — that the manifest still names the command
    `[project.scripts]` actually installs.
    """
    args = manifest["mcpServers"]["just-module-creator"]["args"]
    assert "just-module-creator" in args
    assert "${CLAUDE_PLUGIN_ROOT}" in args, "the project path must stay plugin-relative"

    pyproject = (REPO / "pyproject.toml").read_text()
    assert 'just-module-creator = "just_module_creator.server:cli_app"' in pyproject


def test_the_declared_skill_directory_holds_the_skills_the_description_promises(manifest):
    """The manifest says "two skills"; a deleted or renamed one would make that a lie."""
    skills_dir = REPO / manifest["skills"].removeprefix("./")
    shipped = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()}
    assert shipped == {"create-module", "find-evidence"}


def test_the_marketplace_entry_points_at_this_plugin():
    """`/plugin marketplace add ./` resolves through this file, so its name must match."""
    marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    names = {p["name"] for p in marketplace["plugins"]}
    assert "just-module-creator" in names
    # Deliberately no third version copy in the marketplace entry.
    assert all("version" not in p for p in marketplace["plugins"])


def test_the_codex_manifest_matches_the_package_and_skills(codex_manifest):
    assert codex_manifest["version"] == version("just-module-creator")
    skills_dir = REPO / codex_manifest["skills"].removeprefix("./")
    shipped = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()}
    assert shipped == {"create-module", "find-evidence"}


def test_the_codex_mcp_config_launches_this_checkout(codex_manifest):
    server = codex_manifest["mcpServers"]["just-module-creator"]
    assert server["type"] == "stdio"
    assert server["command"] == "uv"
    assert "${PLUGIN_ROOT}" in server["args"]
    assert "just-module-creator" in server["args"]
