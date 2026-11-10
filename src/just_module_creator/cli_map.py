"""What each upstream CLI command is on this surface (F132).

Upstream messages are written for upstream's CLIs: the closure warning says *"Run
`just-dna-compiler close <spec-dir>`"*, a missing snapshot says *"provision one with
`just-dna-enricher clinvar build`"*. An agent driving this server has `close_module` and
`provision_caches`, and nothing told it so. This module is the one map from a command to
its tool, read where upstream text crosses into a result.

The map is our own text, and it never edits upstream's: a result keeps upstream's message
byte for byte and carries this beside it (`on_this_surface`). A structured remedy key from
upstream would replace the text matching here; until then the match is on the command's
own name, which upstream's typer apps enumerate, and
`tests/test_cli_map.py` holds the map to that enumeration in both directions.

Every command is either mapped or abstained from with a reason. The prose twin, for a
reader rather than a result, is `skills/module-101/references/CLI.md`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from just_dna_enricher.caches import CACHE_LANES

ENRICHER = "just-dna-enricher"
COMPILER = "just-dna-compiler"

# The authoring commands, hand-kept: what to call here instead. A value names tools that
# exist (the test checks every identifier-shaped name in it against the live listing).
_AUTHORING: dict[str, str] = {
    f"{COMPILER} validate": "validate_module",
    f"{COMPILER} compile": "compile_module",
    f"{COMPILER} signature": "module_signature",
    f"{COMPILER} verify": "verify_artifact",
    f"{COMPILER} close": "close_module",
    f"{COMPILER} reference": "authoring_reference",
    f"{COMPILER} reverse": "reverse_module",
    f"{COMPILER} template": "get_template",
    f"{COMPILER} stub": "get_template(stub=true)",
    f"{COMPILER} requirements": "table_requirements",
    f"{COMPILER} scaffold": "scaffold_module",
    f"{COMPILER} describe": "describe_table",
    f"{COMPILER} hint": "lint_rows",
    f"{ENRICHER} enrich": "enrich_module",
    f"{ENRICHER} vrs mint": "enrich_module (it mints VRS ids as it resolves)",
    f"{ENRICHER} enrich-and-compile": "enrich_module, then compile_module",
    f"{ENRICHER} frequencies": 'enrich_facts(passes=["frequencies"])',
    f"{ENRICHER} gene-metrics": 'enrich_facts(passes=["gene_metrics"])',
    f"{ENRICHER} dosage": 'enrich_facts(passes=["dosage"])',
    f"{ENRICHER} gwas": "enrich_gwas_effects",
    f"{ENRICHER} literature": "enrich_literature_pass",
    f"{ENRICHER} template": "get_template",
    f"{ENRICHER} draft": "draft_from_cpic",
    f"{ENRICHER} draft-clinpgx": "draft_from_clinpgx",
    f"{ENRICHER} draft-panel": (
        "draft_from_clinvar, draft_from_civic, draft_from_mitomap or draft_from_pubmind "
        "(one tool per authority)"
    ),
    f"{ENRICHER} draft-repeats": "draft_from_strchive",
    f"{ENRICHER} check-identifiers": "check_identifiers",
    f"{ENRICHER} check-acmg": "check_acmg",
    f"{ENRICHER} check-repeat-bands": "check_repeat_bands",
    f"{ENRICHER} pgx": "check_pgx",
    f"{ENRICHER} clinpgx check": "check_clinpgx",
    f"{ENRICHER} litvar coverage": "check_literature_coverage",
    f"{ENRICHER} hint variant": "lookup_variant",
    f"{ENRICHER} hint citation": "lookup_citation",
    f"{ENRICHER} hint gene": 'lookup_identifier(kind="gene")',
    f"{ENRICHER} hint trait": 'lookup_identifier(kind="trait")',
    f"{ENRICHER} alphagenome expression": "enrich_expression_effects",
    f"{ENRICHER} cache status": "registry_caches, or provision_caches(dry_run=true)",
    f"{ENRICHER} cache pull": "provision_caches",
    f"{ENRICHER} cache prepare": "provision_caches",
}

# Commands with no tool here, and why. The CLI is the route for each.
_OPERATOR = (
    "an operator's or publisher's step, deliberately not wrapped: it builds, publishes or "
    "prunes a shared snapshot rather than authoring a module"
)
_SIGNING = (
    "signing is the key holder's act and deliberately not wrapped: a server that held the "
    "private key would sign whatever its caller asked"
)
_NOT_YET = "not wrapped yet; parity is the default, so this is a gap rather than a decision"
_ABSTAINED: dict[str, str] = {
    f"{COMPILER} keygen": _SIGNING,
    f"{COMPILER} sign": _SIGNING,
    f"{COMPILER} sweep": (
        "a release-sequence measurement that needs the previous compiler installed; the "
        "producer's, not an author's"
    ),
    f"{ENRICHER} upload": _OPERATOR,
    f"{ENRICHER} cache prune": _OPERATOR,
    f"{ENRICHER} cache rebuild": _OPERATOR,
    f"{ENRICHER} clinvar citations": _OPERATOR,
    f"{ENRICHER} civic citations": _OPERATOR,
    f"{ENRICHER} civic reproduce": _OPERATOR,
    f"{ENRICHER} atlas generate": (
        "generates the Atlas gRPC bindings once per source checkout; a released wheel "
        "carries them already"
    ),
    f"{ENRICHER} clinpgx check-labels": _NOT_YET,
    f"{ENRICHER} alphagenome check": _NOT_YET,
    f"{ENRICHER} litvar gene": _NOT_YET,
    f"{ENRICHER} hint recover": _NOT_YET,
    f"{ENRICHER} gene-validity": (
        "no tool fills gene_validity.csv the first time; refresh_sidecar re-derives one that exists"
    ),
    f"{ENRICHER} assertions": (
        "no tool fills clinical_assertions.csv the first time; refresh_sidecar re-derives "
        "one that exists"
    ),
}


def _lane_commands() -> dict[str, str]:
    """Snapshot builds, generated from upstream's own lane roster rather than listed."""
    out: dict[str, str] = {}
    for lane in CACHE_LANES:
        build = getattr(lane, "build_command", None)
        if build:
            out[f"{ENRICHER} {build}"] = f'provision_caches(lanes=["{lane.name}"])'
    return out


# The publisher's half of a lane: pushing a built snapshot to where others pull it.
_PUBLISH = (
    "clinvar publish",
    "clinpgx publish",
    "clinpgx publish-labels",
    "cpic publish",
    "civic publish",
    "pubmind publish",
    "gnomad constraint publish",
    "strchive publish",
    "mitomap publish",
    "alphagenome publish",
)

MAPPED: dict[str, str] = {**_lane_commands(), **_AUTHORING}
ABSTAINED: dict[str, str] = {
    **{f"{ENRICHER} {cmd}": _OPERATOR for cmd in _PUBLISH},
    **_ABSTAINED,
}

# Longest first, so `clinpgx build-labels` is tried before `clinpgx build`, and a command
# must end at a boundary that is not part of a longer command name.
_KNOWN = sorted({**MAPPED, **ABSTAINED}, key=len, reverse=True)
_PATTERN = re.compile("|".join(rf"(?<![\w-]){re.escape(cmd)}(?![\w-])" for cmd in _KNOWN))


def describe(command: str) -> str:
    """One line saying what `command` is here."""
    if command in MAPPED:
        return f"`{command}` is `{MAPPED[command]}` on this surface."
    return f"`{command}` has no tool here ({ABSTAINED[command]}); use the CLI."


def on_this_surface(text: str) -> str | None:
    """What the CLI commands `text` names are here, or None when it names none."""
    seen: list[str] = []
    for match in _PATTERN.finditer(text or ""):
        if match.group(0) not in seen:
            seen.append(match.group(0))
    return " ".join(describe(cmd) for cmd in seen) or None


def for_messages(texts: Iterable[str]) -> list[str]:
    """`on_this_surface` over several messages, one line per distinct command."""
    lines: list[str] = []
    for text in texts:
        for match in _PATTERN.finditer(text or ""):
            line = describe(match.group(0))
            if line not in lines:
                lines.append(line)
    return lines
