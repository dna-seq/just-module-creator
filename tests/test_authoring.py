"""The essentials tier: schema discovery, scaffolding, linting.

These assert *behaviour we promise*, not upstream's schema. Where a test does
name a column or a vocabulary member it is because our tool contract mentions it
(the "rsid or chrom+start" identity rule, the sorted-genotype error), never
because we are re-testing just-dna-format.
"""

from __future__ import annotations

import pytest


async def test_list_tables_covers_every_draftable_kind(essentials_client):
    from just_dna_compiler import draft

    result = await essentials_client.call_tool("list_tables", {})
    listed = {t.csv for t in result.data.tables}
    assert listed == set(draft.DRAFTABLE)
    # Every kind gets a subject and a key, so "which table?" is answerable here.
    assert all(t.subject and t.keyed_on for t in result.data.tables)


async def test_list_tables_states_the_companion_rule(essentials_client):
    result = await essentials_client.call_tool("list_tables", {})
    by_name = {t.csv: t for t in result.data.tables}
    assert by_name["variants.csv"].companions == ["studies.csv"]
    assert by_name["studies.csv"].companions == ["variants.csv"]
    # A PGx module carries no variants.csv; nothing may imply otherwise.
    assert by_name["pharm_variants.csv"].companions == []


async def test_sidecars_are_listed_as_not_hand_authored(essentials_client):
    result = await essentials_client.call_tool("list_tables", {})
    assert "resolution.csv" in result.data.sidecars
    assert "resolution.csv" not in {t.csv for t in result.data.tables}


async def test_table_requirements_reports_all_three_shapes(essentials_client):
    result = await essentials_client.call_tool("table_requirements", {"csv_name": "variants.csv"})
    data = result.data
    assert set(data.always) == {"genotype", "state", "conclusion"}
    # The identity rule no per-field flag can express.
    assert data.any_of == [["rsid"], ["chrom", "start"]]
    assert isinstance(data.defaulted, dict)


async def test_kind_argument_accepts_a_bare_name(essentials_client):
    bare = await essentials_client.call_tool("table_requirements", {"csv_name": "variants"})
    full = await essentials_client.call_tool("table_requirements", {"csv_name": "variants.csv"})
    assert bare.data.always == full.data.always


async def test_unknown_kind_lists_the_valid_ones(essentials_client):
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="variants.csv"):
        await essentials_client.call_tool("describe_table", {"csv_name": "nonsense.csv"})


async def test_describe_table_flags_redundancy_bearing_columns(essentials_client):
    result = await essentials_client.call_tool("describe_table", {"csv_name": "variants.csv"})
    # These are the cells a later check compares against a source. If upstream
    # ever stops marking them, our "report, never repair" promise is hollow.
    assert result.data.redundancy_bearing
    assert "chrom" in result.data.redundancy_bearing


async def test_template_header_only_vs_stub(essentials_client):
    blank = await essentials_client.call_tool("get_template", {"csv_name": "variants.csv"})
    stub = await essentials_client.call_tool(
        "get_template", {"csv_name": "variants.csv", "stub": True, "rows": 2}
    )
    assert "<<REPLACE>>" not in blank.data.content
    assert "<<REPLACE>>" in stub.data.content
    assert stub.data.stub is True


async def test_scaffold_creates_then_refuses_to_overwrite(essentials_client, tmp_path):
    target = str(tmp_path / "spec")
    args = {"spec_dir": target, "name": "my_module", "kinds": ["variants.csv", "studies.csv"]}

    first = await essentials_client.call_tool("scaffold_module", args)
    assert first.data.written
    assert {p.rsplit("/", 1)[-1] for p in first.data.created} == {
        "module_spec.yaml",
        "variants.csv",
        "studies.csv",
    }

    second = await essentials_client.call_tool("scaffold_module", args)
    assert second.data.created == []
    assert len(second.data.refused) == 3  # never overwrites


async def test_scaffold_dry_run_writes_nothing(essentials_client, tmp_path):
    target = tmp_path / "spec"
    result = await essentials_client.call_tool(
        "scaffold_module",
        {"spec_dir": str(target), "name": "m", "kinds": ["variants.csv"], "dry_run": True},
    )
    assert result.data.written is False
    assert not (target / "module_spec.yaml").exists()


async def test_scaffold_warns_when_a_companion_is_missing(essentials_client, tmp_path):
    result = await essentials_client.call_tool(
        "scaffold_module",
        {"spec_dir": str(tmp_path / "spec"), "name": "m", "kinds": ["variants.csv"]},
    )
    assert any("studies.csv" in w for w in result.data.warnings)


async def test_lint_catches_unsorted_genotype(essentials_client):
    result = await essentials_client.call_tool(
        "lint_rows",
        {
            "csv_name": "variants.csv",
            "csv_text": "rsid,genotype,state,conclusion\nrs4988235,G/A,protective,x\n",
        },
    )
    assert result.data.errors == 1
    assert any(f.level == "error" and f.column == "genotype" for f in result.data.findings)


async def test_lint_writes_nothing_and_keeps_info_findings(essentials_client, tmp_path):
    text = "rsid,genotype,state,conclusion\nrs4988235,A/A,protective,x\n"
    result = await essentials_client.call_tool(
        "lint_rows", {"csv_name": "variants.csv", "csv_text": text}
    )
    assert result.data.errors == 0
    # The info tier names the columns deliberately left to the author. Losing it
    # would turn a documented abstention into a silent omission.
    assert any(f.level == "info" for f in result.data.findings)
    assert list(tmp_path.iterdir()) == []


async def test_lint_normalized_csv_never_invents_a_value(essentials_client):
    text = "rsid,genotype,state,conclusion\nrs4988235,A/A,protective,x\n"
    result = await essentials_client.call_tool(
        "lint_rows", {"csv_name": "variants.csv", "csv_text": text}
    )
    assert "<<REPLACE>>" not in result.data.normalized_csv
    for alteration in result.data.alterations:
        # Anything not applied must say why. A bare refusal is unactionable.
        if not alteration.applied:
            assert alteration.refusal
