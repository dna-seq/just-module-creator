"""The skills are a shipped surface and had no test. This is the guard.

Twenty documents, ~5,000 lines, loaded by an agent rather than imported by code —
so nothing here failed when a link broke, when a skill named one that no longer
shipped, or when a file grew past the size where it stops being read properly.
The 1431-line monolith that was dismantled on 2026-08-20 got that way partly
because no gate ever said it had.

**Two kinds of document, and the difference is who invokes them.** A `SKILL.md`
is a COMMAND: `/`-invocable, listed in every session's prompt, and written for a
person deciding what they want. A `GUIDE.md` is the same content with no
frontmatter contract to the user — it is loaded by a router, by path, when an
agent reaches that step. Thirteen skills became guides at 0.24.0 because a menu of
twenty entries is a menu nobody reads, and because most of them are steps an agent
is mid-way through rather than anything a person types. **The cost of that move is
auto-loading**: a guide cannot be matched from its description any more, so the
router has to name it — which is what `test_every_guide_is_reachable_from_a_command`
holds.

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


def _guides() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if (p / "GUIDE.md").is_file())


def _document(path: Path) -> Path:
    """The one markdown file that IS this directory — command or guide."""
    return path / ("SKILL.md" if (path / "SKILL.md").is_file() else "GUIDE.md")


def _split(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match, f"{path} has no YAML frontmatter"
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


COMMANDS = _skills()
GUIDES = _guides()
ALL = sorted(COMMANDS + GUIDES)
NAMES = {p.name for p in ALL}
COMMAND_NAMES = {p.name for p in COMMANDS}

#: What a person may type. Seven, deliberately: the menu is the first thing a user
#: meets, and twenty entries of it were unreadable. Each is something somebody
#: arrives WANTING — make one, work out what this is, find the papers, publish it,
#: decode this message, run it on my genome, open it again — rather than a step an
#: agent happens to be on.
_EXPECTED_COMMANDS = {
    "create-module",
    "module-status",
    "module-revise",
    "find-evidence",
    "module-publish",
    "module-symptom",
    "module-install-local",
}


def test_the_command_menu_is_what_a_person_would_ask_for():
    """The `/` menu, pinned by name rather than by count.

    A skill added here shows up in every user's menu and in every session's prompt,
    so it is a decision rather than a side effect: twenty entries cost 14,688
    characters of prompt and asked a layman to choose between `module-curate` and
    `module-enrich`. If a new command belongs here, change this set on purpose.

    **The criterion is whether the person can recognise they want it.** Each of
    these seven is something somebody arrives able to name — make one, work out
    what this directory is, find the papers, publish it, decode this message, run it
    on my genome, open it again. `module-101` is the case that proves the rule and
    the reason it is a guide: whoever needs the overview does not know they need it,
    and whoever knows what it is has stopped needing it. A menu entry serves neither,
    while an agent that spots a beginner and loads it serves the first. Anything with
    that shape is a guide, however useful.
    """
    assert COMMAND_NAMES == _EXPECTED_COMMANDS, {
        "unexpected": sorted(COMMAND_NAMES - _EXPECTED_COMMANDS),
        "missing": sorted(_EXPECTED_COMMANDS - COMMAND_NAMES),
    }


def test_the_document_set_is_what_the_manifest_promises():
    """A document added or removed without the count moving is the drift this catches."""
    assert len(ALL) == 20, f"documents shipped: {sorted(NAMES)}"


#: `create-module` is the one skill whose *shape* is pinned rather than only its
#: frontmatter. The name shipped a 1431-line procedure until 2026-08-20 and was
#: deleted; it came back on 2026-08-21 as a router, on the owner's instruction, and
#: the risk it carries is regrowth rather than absence. The old guard here asserted
#: the name was gone — this one asserts what it may hold.
_ROUTER_MAX = 200


def test_the_router_routes_and_does_not_regrow_into_the_procedure():
    """Half the body ceiling, and it must name every stage it routes to.

    A router that names a stage it cannot reach is a dead end; a router past this
    size has started carrying the stage's work, which is exactly how the monolith
    happened the first time.
    """
    front, body = _split(SKILLS / "create-module" / "SKILL.md")
    lines = len(body.splitlines())
    assert lines <= _ROUTER_MAX, (
        f"{lines} lines. `create-module` routes to the stage that owns the step; a "
        "procedure growing back into it is what CLAUDE.md warns about by name"
    )

    spine = {
        "module-start",
        "module-draft",
        "module-curate",
        "module-enrich",
        "module-check",
        "module-compile",
        "module-close",
        "module-publish",
    }
    named = {name for name in NAMES if f"`{name}`" in body}
    assert spine <= named, f"the router does not name {sorted(spine - named)}"

    # The two doors are entered sideways, and a router that only knows the spine
    # sends a second-pass author through a first pass.
    assert {"module-revise", "module-status"} <= named


@pytest.mark.parametrize("skill", ALL, ids=lambda p: p.name)
def test_frontmatter_is_portable_and_within_the_published_limits(skill: Path):
    front, _ = _split(_document(skill))
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
    _, body = _split(_document(skill))
    lines = len(body.splitlines())
    assert lines <= _BODY_MAX, (
        f"{lines} lines. Move detail into references/ — a file this size is one an "
        "agent loads whole to answer any question, which is how the monolith happened"
    )


#: Where a skill delegated a whole subject to a reference, the stub left behind must
#: stay a stub. `find-evidence` is the measured case: it hit the 500-line ceiling on
#: 2026-09-01 and three of its four subjects had already grown past the point where a
#: section is a summary rather than a signpost. Each entry is (skill, heading, ceiling).
_DELEGATED_SECTIONS = (
    ("find-evidence", "## What may honestly go in `provenance_quote`", 30),
    ("find-evidence", "## Copyright: free to read is not free to reuse", 30),
)


@pytest.mark.parametrize(
    ("skill_name", "heading", "ceiling"),
    _DELEGATED_SECTIONS,
    ids=lambda v: v if isinstance(v, str) else str(v),
)
def test_a_delegated_section_stays_a_signpost(skill_name: str, heading: str, ceiling: int):
    """The body ceiling is a whole-file budget, so one section can eat it silently.

    `find-evidence` reached 520 lines with 197 of them under one heading — the quote
    rules, which by then were a reference living inside a skill. Trimming the file to
    fit would have kept the shape and only shortened the prose, which is how the
    monolith grew the first time: the fix is that the subject moved out and what stays
    is a signpost carrying the one fact that decides whether to open it.

    A stub over this ceiling means the section is re-growing. Move the new material
    into the reference it delegates to, rather than raising the number here.
    """
    document = _document(SKILLS / skill_name)
    body = document.read_text(encoding="utf-8")
    assert heading in body, f"{skill_name} no longer has {heading!r} — update this guard"
    section = body.split(heading, 1)[1]
    section = section.split("\n## ", 1)[0]
    lines = len([line for line in section.splitlines() if line.strip()])
    assert lines <= ceiling, (
        f"{skill_name}'s {heading!r} is {lines} non-blank lines, over {ceiling}. It "
        "delegates to a reference, so it must stay a signpost — move the detail there. "
        "The whole-file ceiling cannot catch this: one section can grow while the file "
        "shrinks elsewhere."
    )
    assert "references/" in section, (
        f"{skill_name}'s {heading!r} delegates its subject but names no reference, "
        "so a reader has a summary and no way to the full rules"
    )


@pytest.mark.parametrize("skill", ALL, ids=lambda p: p.name)
def test_every_skill_it_names_actually_ships(skill: Path):
    """A pointer to a skill that does not exist is a dead end an agent cannot recover from."""
    text = _document(skill).read_text(encoding="utf-8")
    named = set(re.findall(r"`(module-[a-z0-9-]+|find-evidence|create-module)`", text))
    missing = named - NAMES
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
        d for d in ALL
        if "../module-101/references/SYMPTOMS.md" in _document(d).read_text(encoding="utf-8")
    ]
    assert len(pointing) >= 10, "the stage guides should route symptom lookups to one place"


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


def test_a_referenced_job_is_cued_from_a_door_not_only_linked_to():
    """Link-reachability is not cue-reachability, and the difference cost a benchmark.

    `test_every_guide_is_reachable_from_a_command` walks the link graph, so it passed
    while `find-evidence/references/SUPPLEMENTARY.md` was unfindable in practice: both
    routers named `find-evidence` as *"which paper stands behind each claim"* and nothing
    said it also owns getting the supplementary table. Two independent agents, given the
    same task on 2026-08-30, each concluded "no plugin tool fetches supplementary
    material" — one inferred it from the MCP listing, the other reconstructed the ESM URL
    pattern from scratch over twelve blind probes. Neither ever opened the skill.

    So a router must name the *job*, not only the skill. This checks the one case that was
    measured; it is not a general theory of discoverability, and a second instance is the
    signal to generalise it rather than to add a second special case.
    """
    doors = [SKILLS / "create-module" / "SKILL.md", SKILLS / "module-start" / "GUIDE.md"]
    blind = []
    for door in doors:
        # Strip link TARGETS before looking: a path ending SUPPLEMENTARY.md satisfies a
        # naive substring search while telling a reader scanning the row nothing. The cue
        # has to be in the prose a router is actually read for.
        raw = door.read_text(encoding="utf-8")
        raw = re.sub(r"\]\([^)]*\)", "]", raw)  # link targets
        raw = re.sub(r"`[^`]*`", "", raw)  # code spans, which is how filenames appear
        prose = raw.lower()
        if "supplementar" not in prose:
            blind.append(door.name)
    assert not blind, (
        f"{blind} route to find-evidence without naming supplementary retrieval. An agent "
        "holding the paper and needing the table inside its supplement has no cue to open it."
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
        body = _document(SKILLS / name).read_text(encoding="utf-8")
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
    text = _document(skill).read_text(encoding="utf-8")
    marks = ("retired", "no longer", "used to", "until", "was the", "the format's")
    for match in re.finditer(r"[Rr]eport, never repair", text):
        window = text[max(0, match.start() - 300) : match.end() + 300].lower()
        assert any(mark in window for mark in marks), (
            f"{skill.name} states the retired stance as current, at character "
            f"{match.start()}. This layer writes; what it owes is the discriminator "
            "and a logged move"
        )


def test_every_guide_is_reachable_from_a_command():
    """A guide cannot be matched from its description, so a router has to name it.

    This is the whole cost of demoting thirteen skills, and the only thing that
    makes the demotion safe. Reachability is transitive — `module-refresh` is
    reached through `module-revise`, and the stage spine through `create-module` —
    so this walks the link graph from the seven commands rather than requiring
    every guide to be named by one.

    The repo has been here before, from the other direction: a `commands/` shim
    shadowed nine skills and the bodies never loaded, and every test then asserted
    that a shim ROUTED to a skill that shipped while none asserted that invoking
    the name DELIVERED one. So this asserts the thing an agent actually does —
    follow a link from the door it came in by.
    """
    reachable: set[str] = set()
    frontier = [d for d in COMMANDS]
    while frontier:
        current = frontier.pop()
        if current.name in reachable:
            continue
        reachable.add(current.name)
        text = _document(current).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(\.\./([a-z0-9-]+)/GUIDE\.md\)", text):
            candidate = SKILLS / target
            if (candidate / "GUIDE.md").is_file() and target not in reachable:
                frontier.append(candidate)

    orphans = sorted({g.name for g in GUIDES} - reachable)
    assert not orphans, (
        f"no command links to {orphans}, directly or through another guide. A guide "
        "nothing names is content that cannot be loaded: it lost description matching "
        "when it stopped being a skill"
    )


def test_claude_md_names_every_skill_that_ships():
    """`CLAUDE.md`'s asset table is the roster an agent reads before touching anything.

    It had gone stale in the quiet way: `module-status` and `module-symptom` shipped and
    the table never learned them, so the layout tree's "sixteen skills" was right about
    the table and wrong about the directory. An agent reading the roster would conclude
    the two doors do not exist and write a third copy of what they hold — the drift
    `CLAUDE.md` warns about by name. Nothing failed, because nothing read it.

    Names only. Whether the table *describes* a skill well is a judgement, and a test
    that tried to hold that would fail on every rewording.
    """
    text = (SKILLS.parent / "CLAUDE.md").read_text(encoding="utf-8")
    table = text.split("### The agent assets this repo ships", 1)[1].split("\n## 1.", 1)[0]
    # Plain substring, not a backtick span: the map is named through its path
    # (`skills/module-101/SKILL.md`) while the stage spine is named bare. Both are
    # the roster naming it, and the test holds the claim rather than the formatting.
    missing = sorted(name for name in NAMES if name not in table)
    assert not missing, (
        f"CLAUDE.md's asset table does not name {missing}. A skill absent from the roster "
        "is one the next agent rebuilds from scratch"
    )
