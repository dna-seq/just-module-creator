"""F132: upstream text names its CLI commands; a result says what each one is here.

The map in `cli_map` is held to upstream's own typer apps in both directions, so a
command upstream adds without an entry fails here, and an entry naming a command or a
tool that does not exist fails too.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from just_dna_compiler import cli as compiler_cli
from just_dna_enricher import cli as enricher_cli

from just_module_creator import cli_map, routing, toolbox
from just_module_creator.models import LintFinding


def _leaves(app: typer.Typer, prefix: list[str]) -> set[str]:
    """Every runnable command, nested groups included (`gnomad constraint build`)."""
    out = {
        " ".join([*prefix, c.name or (c.callback.__name__.replace("_", "-") if c.callback else "")])
        for c in app.registered_commands
    }
    for group in app.registered_groups:
        if group.typer_instance is not None and group.name:
            out |= _leaves(group.typer_instance, [*prefix, group.name])
    return out


def _upstream() -> set[str]:
    return _leaves(enricher_cli.app, [cli_map.ENRICHER]) | _leaves(
        compiler_cli.app, [cli_map.COMPILER]
    )


def test_every_upstream_command_is_mapped_or_abstained_with_a_reason() -> None:
    upstream = _upstream()
    assert len(upstream) > 60, "the enumeration found almost nothing: the apps moved"
    assert "just-dna-enricher gnomad constraint build" in upstream, "the walk lost nested groups"
    covered = set(cli_map.MAPPED) | set(cli_map.ABSTAINED)
    assert not set(cli_map.MAPPED) & set(cli_map.ABSTAINED), "a command is both"
    missing = sorted(upstream - covered)
    assert not missing, (
        f"upstream ships {missing} with no entry in cli_map. Map it to the tool that does it "
        "here, or abstain with the reason no tool does."
    )
    # A lane's build may be an invocation, not a bare command (0.9's `ensembl_rsid_index` is
    # `cache rebuild --only ensembl_rsid_index`): its command part must be registered, and the
    # mapping stays whole so upstream text naming that invocation reads as the one lane.
    stale = sorted(c for c in covered if c.split(" --", 1)[0] not in upstream)
    assert not stale, f"cli_map names {stale}, which upstream does not register"
    assert cli_map.MAPPED["just-dna-compiler close"] == "close_module"


def test_every_tool_a_mapping_names_exists() -> None:
    ours = {name for group in toolbox.GROUPS for name in group.tools} | set(toolbox.CORE)
    assert "close_module" in ours, "the tool enumeration lost a tool it must hold"
    named = {
        word
        for value in cli_map.MAPPED.values()
        for word in re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", value)
    }
    # Argument names and values that are not tools: lane names (`provision_caches(lanes=[...])`),
    # read from the installed lane registry so a new lane (0.9's `ensembl_rsid_index`) is not
    # mistaken for a tool, plus two argument names.
    lanes = {lane.name for lane in routing.CACHE_LANES}
    assert "mitomap_miss" in lanes, "the lane enumeration lost a lane it must hold"
    named -= lanes | {"dry_run", "gene_metrics"}
    assert "provision_caches" in named and "close_module" in named
    assert not named - ours, f"cli_map names tools that do not exist: {sorted(named - ours)}"


def test_a_lane_built_by_an_invocation_reads_as_that_lane() -> None:
    """`cache rebuild` is an operator's sweep; with `--only ensembl_rsid_index` it is one lane."""
    lane = next(lane for lane in routing.CACHE_LANES if lane.name == "ensembl_rsid_index")
    assert lane.build_command and " --" in lane.build_command
    line = cli_map.on_this_surface(f"Run `just-dna-enricher {lane.build_command}` first.")
    assert line is not None and 'lanes=["ensembl_rsid_index"]' in line
    bare = cli_map.on_this_surface("Run `just-dna-enricher cache rebuild` first.")
    assert bare is not None and "has no tool here" in bare


def test_a_longer_command_is_not_read_as_its_prefix() -> None:
    """`clinpgx build` is a prefix of `clinpgx build-labels`, and upstream quotes both."""
    text = "Build it: `just-dna-enricher clinpgx build-labels`."
    line = cli_map.on_this_surface(text)
    assert line is not None and 'lanes=["drug_labels"]' in line
    assert 'lanes=["clinpgx"]' not in line


def test_a_command_upstream_does_not_register_is_not_mapped() -> None:
    """Upstream text quotes `clinvar pull`, which no app registers: nothing to say about it."""
    assert cli_map.on_this_surface("Provision one with `just-dna-enricher clinvar pull`.") is None


def test_an_upstream_finding_keeps_its_message_and_gains_the_mapping() -> None:
    message = "Run `just-dna-compiler close <spec-dir>` when the module is complete."
    finding = LintFinding(source="upstream", level="warning", message=message)
    assert finding.message == message
    assert finding.on_this_surface == "`just-dna-compiler close` is `close_module` on this surface."


async def test_the_closure_warning_names_close_module(client, spec_dir: Path) -> None:
    """The F132 trigger: the compiler's own closure warning on an unclosed spec."""
    out = await client.call_tool("validate_module", {"spec_dir": str(spec_dir), "strict": False})
    closure = [w for w in out.data.warnings if "just-dna-compiler close <spec-dir>" in w]
    assert closure, "the compiler no longer emits the closure warning this test reads"
    assert "`just-dna-compiler close` is `close_module` on this surface." in (
        out.data.on_this_surface
    )
