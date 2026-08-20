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
import re
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


_SKILL_COUNT_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
}


def test_the_declared_skill_directory_holds_the_skills_the_description_promises(manifest):
    """The description states a skill COUNT, so the number and the directory must agree.

    Derived rather than hand-kept. The set was pinned literally until the skill surface
    started growing, and then every addition failed this test for the wrong reason — the
    fault it reports would be "you added a skill", not "the plugin misdescribes itself".
    What must not drift is the *promise*: the count a user reads in the description, and
    the two skills every other document sends a reader to.
    """
    skills_dir = REPO / manifest["skills"].removeprefix("./")
    shipped = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()}

    # `module-101` is the declared entry point and `module-start` is where it sends anyone
    # actually beginning a module; CLAUDE.md, the server instructions and module-101 itself
    # all point at them by name, so their absence is a broken link rather than a smaller
    # surface. This pin named `create-module` until 2026-08-20, when the 1431-line procedure
    # skill was dismantled into the ten stage skills and deleted — the entry point moved, so
    # the pin moved with it.
    assert {"module-101", "module-start"} <= shipped

    promised = _SKILL_COUNT_WORDS[len(shipped)]
    assert f"{promised} skills" in manifest["description"], (
        f"{len(shipped)} skills ship, so the description must say '{promised} skills'"
    )


def test_the_marketplace_entry_points_at_this_plugin():
    """`/plugin marketplace add ./` resolves through this file, so its name must match."""
    marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    names = {p["name"] for p in marketplace["plugins"]}
    assert "just-module-creator" in names
    # Deliberately no third version copy in the marketplace entry.
    assert all("version" not in p for p in marketplace["plugins"])


def test_the_codex_manifest_matches_the_package_and_skills(codex_manifest, manifest):
    """Both manifests must serve the SAME skills, which is a property of the path they name.

    The Codex description states no count, so there is nothing to keep in step there — what
    would break silently is the two manifests pointing at different directories, which is how
    one host would ship a skill the other does not.
    """
    assert codex_manifest["version"] == version("just-module-creator")
    codex_dir = REPO / codex_manifest["skills"].removeprefix("./")
    claude_dir = REPO / manifest["skills"].removeprefix("./")
    assert codex_dir.resolve() == claude_dir.resolve()

    shipped = {p.name for p in codex_dir.iterdir() if (p / "SKILL.md").is_file()}
    assert {"module-101", "module-start"} <= shipped


def test_the_codex_mcp_config_launches_this_checkout(codex_manifest):
    server = codex_manifest["mcpServers"]["just-module-creator"]
    assert server["type"] == "stdio"
    assert server["command"] == "uv"
    assert "${PLUGIN_ROOT}" in server["args"]
    assert "just-module-creator" in server["args"]


# --------------------------------------------------------------------------- #
# Commands (RM20)
# --------------------------------------------------------------------------- #
COMMANDS = REPO / "commands"
COMMAND_FILES = sorted(COMMANDS.glob("*.md"))


def test_both_manifests_declare_the_commands_directory():
    """A command surface nothing points at is a directory, not a feature."""
    for path in (MANIFEST, CODEX_MANIFEST):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert "commands" in manifest, f"{path.name} does not declare commands"
        declared = REPO / manifest["commands"].lstrip("./").rstrip("/")
        assert declared.is_dir(), f"{path.name} points at {declared}, which is not a directory"


@pytest.mark.parametrize("command", COMMAND_FILES, ids=lambda p: p.stem)
def test_every_command_routes_to_a_skill_that_ships(command: Path):
    """The whole design of the command layer: it routes, and the skill is the procedure.

    A command naming a skill that does not exist sends a user into nothing, and a
    command that stopped naming one has quietly become a second copy of the
    procedure — the drift `CLAUDE.md` calls out by name.
    """
    body = command.read_text(encoding="utf-8")
    skills = {p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file()}

    named = {name for name in skills if f"`{name}`" in body}
    assert named, f"{command.name} names no skill in backticks, so it routes nowhere"
    assert named <= skills


def _front_and_body(path: Path) -> tuple[dict, str]:
    """Frontmatter as plain key/value, and the body. No YAML dependency needed here."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(encoding="utf-8"), re.DOTALL)
    assert match, f"{path} has no frontmatter"
    front = dict(
        (k.strip(), v.strip())
        for line in match.group(1).splitlines()
        if ":" in line
        for k, v in [line.split(":", 1)]
    )
    return front, match.group(2)


@pytest.mark.parametrize("command", COMMAND_FILES, ids=lambda p: p.stem)
def test_a_command_stays_thin(command: Path):
    """The ceiling is what keeps a command from growing into the skill it points at.

    Generous on purpose — this fails on a command that has started carrying a
    procedure, not on one that got a paragraph longer.
    """
    front, body = _front_and_body(command)
    assert front.get("description"), f"{command.name} has no description"
    assert len(body.splitlines()) <= 30, (
        f"{command.name} is {len(body.splitlines())} lines; a command routes to a skill "
        "and the skill owns the procedure"
    )


def test_the_commands_are_the_eight_that_were_chosen():
    """Sixteen skills, eight commands. A command per skill is the crowding RM20 refused."""
    assert {p.stem for p in COMMAND_FILES} == {
        "module-101",
        "module-start",
        "find-evidence",
        "module-tables",
        "module-check",
        "module-compile",
        "module-publish",
        "module-revise",
    }
