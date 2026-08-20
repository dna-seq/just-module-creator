"""The skills are a shipped surface and had no test. This is the guard.

Eighteen skills, ~4,600 lines, loaded by an agent rather than imported by code — so
nothing here failed when a link broke, when a skill named one that no longer
shipped, or when a file grew past the size where it stops being read properly.
The 1431-line monolith that was dismantled on 2026-08-20 got that way partly
because no gate ever said it had.

These are structural checks only. Whether a skill is *correct* is what the
dossiers, the dogfooding loop and upstream's own docs are for; what a test can
hold is that the surface is well-formed and internally consistent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILLS = Path(__file__).resolve().parent.parent / "skills"

#: Anthropic's published limits for a portable skill. `name` is also the directory
#: name, and `description` is the whole of what an agent matches a request against.
_NAME_MAX = 64
_DESCRIPTION_MAX = 1024

#: "Keep SKILL.md under 500 lines. Move detailed reference material to separate
#: files." A file past this stops being read as a whole, which is the failure the
#: split was for.
_BODY_MAX = 500

_RESERVED = ("anthropic", "claude")

#: The six fields a skill may carry outside Claude Code. Anything else makes the
#: skill unpackageable elsewhere, and it is a hard error rather than an ignored key.
_LEGAL_FRONTMATTER = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}


def _skills() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())


def _split(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match, f"{path} has no YAML frontmatter"
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


ALL = _skills()
NAMES = {p.name for p in ALL}


def test_the_skill_set_is_what_the_manifest_promises():
    """A skill added or removed without the count moving is the drift this catches."""
    assert len(ALL) == 18, f"skills shipped: {sorted(NAMES)}"
    assert "create-module" not in NAMES, (
        "the 1431-line procedure skill was dismantled on 2026-08-20; recreating it is "
        "the drift CLAUDE.md warns about by name"
    )


@pytest.mark.parametrize("skill", ALL, ids=lambda p: p.name)
def test_frontmatter_is_portable_and_within_the_published_limits(skill: Path):
    front, _ = _split(skill / "SKILL.md")
    extra = set(front) - _LEGAL_FRONTMATTER
    assert not extra, f"{extra} would make this skill unpackageable outside Claude Code"

    name = front.get("name", "")
    assert name == skill.name, "the frontmatter name must match the directory"
    assert len(name) <= _NAME_MAX
    assert re.fullmatch(r"[a-z0-9-]+", name), "lowercase letters, digits and hyphens only"
    assert not any(word in name for word in _RESERVED)

    description = " ".join((front.get("description") or "").split())
    assert description, "the description is the whole of what an agent matches against"
    assert len(description) <= _DESCRIPTION_MAX, (
        f"{len(description)} chars; over the limit the tail is what gets truncated, "
        "and the tail is where the trigger phrases are"
    )


@pytest.mark.parametrize("skill", ALL, ids=lambda p: p.name)
def test_the_body_stays_under_the_size_where_it_stops_being_read(skill: Path):
    _, body = _split(skill / "SKILL.md")
    lines = len(body.splitlines())
    assert lines <= _BODY_MAX, (
        f"{lines} lines. Move detail into references/ — a file this size is one an "
        "agent loads whole to answer any question, which is how the monolith happened"
    )


@pytest.mark.parametrize("skill", ALL, ids=lambda p: p.name)
def test_every_skill_it_names_actually_ships(skill: Path):
    """A pointer to a skill that does not exist is a dead end an agent cannot recover from."""
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    named = set(re.findall(r"`(module-[a-z0-9-]+|find-evidence|create-module)`", text))
    missing = named - NAMES
    # `create-module` may be *named* in the one paragraph explaining its removal.
    if "create-module" in missing and "no longer" in text:
        missing.discard("create-module")
    assert not missing, f"{skill.name} points at {sorted(missing)}"


@pytest.mark.parametrize(
    "markdown", sorted(SKILLS.rglob("*.md")), ids=lambda p: str(p.relative_to(SKILLS))
)
def test_every_relative_link_resolves(markdown: Path):
    text = markdown.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#][^)]*\.md)\)", text):
        assert (markdown.parent / target).resolve().is_file(), (
            f"{markdown.relative_to(SKILLS)} links to {target}, which does not exist"
        )


def test_the_shared_references_are_where_every_skill_says_they_are():
    """`SYMPTOMS.md` and `CLI.md` are read *from* every stage, so they live with the map.

    They moved out of the deleted procedure skill on 2026-08-20 and thirteen skills
    point at the new path; a move without the pointers is a broken surface.
    """
    for name in ("SYMPTOMS.md", "CLI.md"):
        assert (SKILLS / "module-101" / "references" / name).is_file()

    pointing = [
        p
        for p in SKILLS.glob("*/SKILL.md")
        if "../module-101/references/SYMPTOMS.md" in p.read_text(encoding="utf-8")
    ]
    assert len(pointing) >= 10, "the stage skills should route symptom lookups to one place"


@pytest.mark.parametrize(
    "reference",
    sorted(p for p in SKILLS.rglob("references/*.md")),
    ids=lambda p: str(p.relative_to(SKILLS)),
)
def test_a_long_reference_opens_with_a_way_in(reference: Path):
    """Over ~100 lines a reference may be read partially, so the top must show its scope.

    A table of contents, or an audit banner naming what the file is — either tells a
    reader who got the first `head -100` whether the answer is further down.
    """
    lines = reference.read_text(encoding="utf-8").splitlines()
    if len(lines) <= 100:
        return
    head = "\n".join(lines[:40])
    assert "|" in head or ">" in head or "##" in head, (
        f"{reference.name} is {len(lines)} lines and its first 40 carry no index, "
        "banner or section heading"
    )


def test_the_stage_spine_is_complete_and_each_carries_its_lifecycle_stage():
    """Every stage an agent is taught must have somewhere to go."""
    spine = [
        "module-start",
        "module-draft",
        "module-curate",
        "module-enrich",
        "module-check",
        "module-compile",
        "module-close",
        "module-publish",
    ]
    assert set(spine) <= NAMES
    for name in spine:
        body = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
        assert "**Lifecycle stage:**" in body, f"{name} does not say which stage it is"


@pytest.mark.parametrize("skill", ALL, ids=lambda p: p.name)
def test_the_retired_stance_only_appears_as_something_retired(skill: Path):
    """`RM15` retired "report, never repair" as a rule *of ours* on 2026-08-20.

    The phrase is not banned — three skills quote it in order to say it was retired,
    and one of those is the canonical statement of what replaced it. What is banned is
    stating it **as current**, so this asserts every occurrence sits near a word that
    marks it as past. It survives legitimately elsewhere too, describing what an
    *upstream* check does on a mismatch: true of the compiler, and not a rule here.
    """
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    marks = ("retired", "no longer", "used to", "until", "was the", "the format's")
    for match in re.finditer(r"[Rr]eport, never repair", text):
        window = text[max(0, match.start() - 300) : match.end() + 300].lower()
        assert any(mark in window for mark in marks), (
            f"{skill.name} states the retired stance as current, at character "
            f"{match.start()}. This layer writes; what it owes is the discriminator "
            "and a logged move"
        )
