"""The plugin manifest is a second source of truth, so the suite holds it to the first.

`.claude-plugin/plugin.json` cannot read `importlib.metadata`, so its `version` has
to be bumped by hand alongside `pyproject.toml` — the one place `CLAUDE.md` §2's "never
hardcode a version string" cannot be obeyed. Discipline alone already failed once
(0.3.0 shipped with a manifest still declaring 0.2.0, caught in review rather than by
the suite), and the failure is quiet: loading is unaffected, so the only symptom is an
installed plugin misreporting itself.

These tests turn every hand-maintained claim in the manifest into a failing assertion
instead. They read files and import nothing over the network.
"""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / ".claude-plugin" / "plugin.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


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
    # Deliberately no version here: one hand-maintained version string is the ceiling.
    assert all("version" not in p for p in marketplace["plugins"])
