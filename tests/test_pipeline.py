"""Validate → compile → verify → reverse, on a real (tiny) module.

The round-trip test is the important one: ``content_signature`` surviving
compile → reverse is the fixed point the format guarantees, and it is the only
cheap check that our compile wrapper is not quietly dropping authored content.
"""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError


async def test_validate_passes_on_a_complete_spec(client, spec_dir):
    result = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": True}
    )
    assert result.data.valid
    assert result.data.errors == []
    assert result.data.strict is True
    assert result.data.stats["module_name"] == "lactose_test"


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
