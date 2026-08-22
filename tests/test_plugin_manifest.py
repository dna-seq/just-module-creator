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
# Commands: the layer that shadowed nine skills (RM20, withdrawn 2026-08-22)
# --------------------------------------------------------------------------- #
COMMANDS = REPO / "commands"


def test_no_command_file_shares_a_name_with_a_skill():
    """A command shadows the same-named skill, and the skill body never loads.

    RM20 shipped nine routing shims whose whole body was "load the `<name>` skill
    and do not work from memory of it". Invoking any of those nine names returned
    the shim's own text instead of the skill — so the instruction not to work from
    memory was delivered by the thing that prevented loading the memory's source.
    Nine of twenty skills were unreachable, `create-module` among them, which is
    the entry point `server.INSTRUCTIONS` names.

    Every RM20 test passed throughout, because each asserted that a shim *routes*
    to a skill that ships and none asserted that invoking the name *delivers* one.
    That is why this test is about the collision and not about the shim's contents.

    Reproduced four ways before the shims were deleted: two independent unattended
    runs, the split in a live session's own skill listing (the nine showed their
    command's short description, the eleven others their skill's), and a live
    `Skill(create-module)` call that returned `commands/create-module.md` verbatim.

    Commands are not forbidden — a command that does something a skill cannot is
    fine. Sharing a skill's name is what breaks, so that is what this pins.
    """
    if not COMMANDS.is_dir():
        return
    skills = {p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file()}
    collisions = sorted({p.stem for p in COMMANDS.glob("*.md")} & skills)
    assert not collisions, (
        f"{collisions} exist as both a command and a skill; the command wins and the "
        "skill body never loads. Rename the command or delete it."
    )


def test_neither_manifest_declares_a_commands_directory_while_none_ships():
    """A manifest pointing at a directory that is not there is a promise nothing keeps.

    The declaration comes back with the directory, not before it.
    """
    for path in (MANIFEST, CODEX_MANIFEST):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if COMMANDS.is_dir():
            assert "commands" in manifest, f"{path.name} does not declare commands"
        else:
            assert "commands" not in manifest, (
                f"{path.name} declares a commands directory, but none ships"
            )


#: Wire name -> the name a human reads in the description. Hand-kept on purpose:
#: only a person can decide that `preprints` reads as "preprints" and
#: `semanticscholar` as "Semantic Scholar". What must NOT be hand-kept is the
#: *set*, which is why the test below fails on a source this map has not been
#: taught rather than quietly skipping it.
_SOURCE_PROSE = {
    "pubmed": "PubMed",
    "europepmc": "Europe PMC",
    "semanticscholar": "Semantic Scholar",
    "preprints": "preprints",
    "openalex": "OpenAlex",
    "crossref": "Crossref",
}


def test_the_description_names_every_literature_source_that_ships(manifest):
    """The description enumerates the search sources, so the list rots when one lands.

    It did: OpenAlex and Crossref shipped in 0.14.0 and the manifest declaring 0.14.0
    still named the four that preceded them, which is `CLAUDE.md` §8's second
    claim-shape — a counted claim in prose rotting exactly like a hand-kept list.
    Derived from `discovery.SEARCHABLE` so the failure arrives with the source, not
    with the next person who reads the plugin listing.
    """
    from just_module_creator.discovery import SEARCHABLE

    untaught = set(SEARCHABLE) - set(_SOURCE_PROSE)
    assert not untaught, (
        f"{sorted(untaught)} search the literature but have no reader-facing name here; "
        "add one and put it in the manifest description"
    )

    description = manifest["description"]
    missing = [_SOURCE_PROSE[name] for name in SEARCHABLE if _SOURCE_PROSE[name] not in description]
    assert not missing, (
        f"`.claude-plugin/plugin.json` does not mention {missing}, which literature_search asks"
    )
