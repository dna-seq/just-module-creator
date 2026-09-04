"""Validate → compile → verify → reverse, on a real (tiny) module.

The round-trip test is the important one: ``content_signature`` surviving
compile → reverse is the fixed point the format guarantees, and it is the only
cheap check that our compile wrapper is not quietly dropping authored content.
"""

from __future__ import annotations

import pytest
from conftest import needs_coded_warnings, needs_format_0_7
from fastmcp.exceptions import ToolError


async def test_validate_passes_on_a_complete_spec(client, spec_dir):
    """Lenient, because the fixture carries no `resolution.csv` and strict now says so.

    This asserted `strict=True` until upstream 0.7. It was encoding a defect: the same
    fixture has always been refused by `compile(strict=True)` two tests below, so a
    green strict validate immediately preceded a red strict compile. Upstream's RM141
    calls one predicate from both sides, and the pair agrees now — which is what
    `test_strict_validate_agrees_with_strict_compile` asserts directly.
    """
    result = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert result.data.valid
    assert result.data.errors == []
    assert result.data.strict is False
    assert result.data.stats["module_name"] == "lactose_test"


@needs_format_0_7
async def test_strict_validate_agrees_with_strict_compile(client, spec_dir, tmp_path):
    """A pre-flight that blesses what the build refuses is worse than no pre-flight.

    The fixture has no `resolution.csv`, so no variant has a position and strict means
    the parquet bytes are not reproducible. Both sides must reach that verdict, and
    both must name it — an agent reading only "invalid" cannot tell which tool to run.
    """
    validated = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": True}
    )
    compiled = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(tmp_path / "out"), "strict": True},
    )
    assert validated.data.valid is False
    assert compiled.data.success is False
    assert any("unresolved" in e for e in validated.data.errors), validated.data.errors
    assert any("unresolved" in e for e in compiled.data.errors), compiled.data.errors


async def test_validate_reports_the_mode_it_answered_for(client, spec_dir):
    """A validation verdict is only meaningful paired with its mode."""
    lenient = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert lenient.data.strict is False


async def test_validate_refuses_an_unreplaced_placeholder(client, tmp_path):
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text(
        "schema_version: '1.0'\n"
        "module:\n  title: <<REPLACE>>\n  description: d\n"
        "  report_title: r\n  name: m\n"
        "genome_build: GRCh38\n"
    )
    (spec / "variants.csv").write_text(
        "rsid,genotype,state,conclusion\nrs4988235,A/A,protective,x\n"
    )
    (spec / "studies.csv").write_text("rsid,pmid\nrs4988235,11788828\n")

    result = await client.call_tool(
        "validate_module", {"spec_dir": str(spec), "strict": True}
    )
    assert not result.data.valid
    assert any("REPLACE" in e for e in result.data.errors)


async def test_missing_spec_dir_is_a_tool_error(client, tmp_path):
    with pytest.raises(ToolError, match="not an existing directory"):
        await client.call_tool("validate_module", {"spec_dir": str(tmp_path / "nope")})


async def test_compile_writes_an_artifact(client, spec_dir, tmp_path):
    out = tmp_path / "out"
    result = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(out), "strict": False},
    )
    assert result.data.success
    assert "weights.parquet" in result.data.files
    assert result.data.artifact_digest
    assert (out / "manifest.json").is_file()


async def test_an_output_dir_inside_the_spec_is_warned_about_and_still_compiles(
    client, spec_dir, tmp_path
):
    """`<spec>/build` is the obvious default and it poisons a later registry call.

    The compile copies `README.md` into `output_dir`; the registry uploader then walks
    the spec tree, finds two, and 422s with `ambiguous_spec_layout`. The cost lands two
    steps away from the argument that caused it, so the warning is here — and it is a
    warning rather than a refusal because real modules in this repo use that layout and
    their artifacts are fine.
    """
    inside = spec_dir / "build"
    result = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(inside), "strict": False},
    )
    assert result.data.success, "the layout is legal — this must not become a refusal"
    assert result.data.warnings, "an output dir inside the spec must be said out loud"
    assert "ambiguous_spec_layout" in result.data.warnings[0]
    assert "inside the spec directory" in result.data.warnings[0]

    beside = tmp_path / "beside"
    quiet = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(beside), "strict": False},
    )
    assert quiet.data.success
    assert not any("ambiguous_spec_layout" in w for w in quiet.data.warnings)


async def test_strict_compile_refuses_unresolved_rows(client, spec_dir, tmp_path):
    """Strict means *reproducible*: without resolution.csv there is nothing to reproduce.

    The failure must arrive as a structured refusal with the reason, not as an
    exception — an agent has to be able to read why and go run enrich.
    """
    result = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(tmp_path / "out"), "strict": True},
    )
    assert result.data.success is False
    assert any("unresolved" in e for e in result.data.errors)


async def test_compile_surfaces_warnings_on_success(client, spec_dir, tmp_path):
    """A green compile is not a correct module — the warnings must survive."""
    result = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(tmp_path / "out"), "strict": False},
    )
    assert result.data.success
    assert any("resolution.csv" in w for w in result.data.warnings)


async def test_recompiling_an_untouched_spec_reproduces_the_digest(
    client, spec_dir, tmp_path
):
    first = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(tmp_path / "a"), "strict": False},
    )
    second = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(tmp_path / "b"), "strict": False},
    )
    assert first.data.artifact_digest == second.data.artifact_digest


async def test_verify_reports_an_unchecked_signature_as_unchecked(
    client, spec_dir, tmp_path
):
    out = tmp_path / "out"
    await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(out), "strict": False},
    )
    result = await client.call_tool("verify_artifact", {"module_dir": str(out)})
    assert result.data.verified
    # Digests verified is NOT the same claim as signature verified.
    assert result.data.signature_checked is False
    assert "SIGNATURE was not checked" in result.data.message


async def test_reverse_round_trip_preserves_the_content_signature(
    client, spec_dir, tmp_path
):
    out, rev = tmp_path / "out", tmp_path / "rev"
    await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(out), "strict": False},
    )
    reversed_ = await client.call_tool(
        "reverse_module", {"parquet_dir": str(out), "output_dir": str(rev)}
    )
    assert reversed_.data.success

    original = await client.call_tool("module_signature", {"spec_dir": str(spec_dir)})
    recovered = await client.call_tool(
        "module_signature", {"spec_dir": reversed_.data.data["spec_dir"]}
    )
    assert original.data.content_signature == recovered.data.content_signature


# --------------------------------------------------------------------------- #
# The coded-warning channel (upstream RM131)
# --------------------------------------------------------------------------- #
@needs_coded_warnings
async def test_a_compile_says_which_warnings_the_author_can_actually_clear(
    client, spec_dir, tmp_path
):
    """`carried` is the discriminator that used to need substring-matching prose.

    The fixture compiles green with warnings, and at least one of them is carried:
    a module with no closure and no resolution table draws findings an author
    cannot edit away without doing the work the finding names. The assertion is
    the relationship rather than a count — a code list upstream tunes must not
    date this — and the two lists must partition the whole.
    """
    result = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(tmp_path / "out"), "strict": False},
    )
    data = result.data
    assert data.success
    assert data.warnings, "the fixture must draw warnings or this asserts nothing"

    assert data.warnings_summary, "a 0.7 compiler classifies; an empty summary here is a lie"
    assert sum(data.warnings_summary.values()) == len(data.warnings), (
        "upstream's contract: the summary is complete or it is empty, never short"
    )

    assert data.carried is not None, "classified, so the carried question was answered"
    assert data.actionable is not None
    # The partition, which is the whole point: nothing may be in both, and together
    # they must be the warning list. An author reading `actionable` has to be able to
    # trust that nothing was dropped on the way.
    assert not set(data.carried) & set(data.actionable)
    assert set(data.carried) | set(data.actionable) == set(data.warnings)


@needs_coded_warnings
async def test_a_warning_of_ours_is_never_reported_as_upstreams_to_carry(
    client, spec_dir, tmp_path
):
    """Our own layout warning is about the arguments, so it is always actionable.

    This is why `actionable` is derived here rather than read off the manifest: no
    compiler can classify a warning about a call it did not receive, and folding
    ours into upstream's list would make it either uncounted or wrongly carried.
    """
    inside = spec_dir / "build"
    result = await client.call_tool(
        "compile_module",
        {"spec_dir": str(spec_dir), "output_dir": str(inside), "strict": False},
    )
    data = result.data
    ours = [w for w in data.warnings if "ambiguous_spec_layout" in w]
    assert ours, "the layout warning must still fire or this test moved"
    assert data.actionable is not None
    assert set(ours) <= set(data.actionable)
    assert not set(ours) & set(data.carried or [])
    # And it stays outside upstream's count, which is over upstream's own list.
    assert sum(data.warnings_summary.values()) == len(data.warnings) - len(ours)
