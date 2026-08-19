"""The essentials tier: schema discovery, scaffolding, linting.

These assert *behaviour we promise*, not upstream's schema. Where a test does
name a column or a vocabulary member it is because our tool contract mentions it
(the "rsid or chrom+start" identity rule, the sorted-genotype error), never
because we are re-testing just-dna-format.
"""

from __future__ import annotations

import json
from importlib import metadata

import pytest

# The versions the stamp must report, computed here rather than pasted. A literal
# would be the very defect these tests guard: a version written down once agrees
# with itself forever, including inside a process serving a stale toolchain.
FORMAT_VERSION = metadata.version("just-dna-format")
COMPILER_VERSION = metadata.version("just-dna-compiler")


async def test_list_tables_covers_every_draftable_kind(essentials_client):
    from just_dna_compiler import draft

    result = await essentials_client.call_tool("list_tables", {})
    listed = {t.csv for t in result.data.tables}
    assert listed == set(draft.DRAFTABLE)
    # Every kind gets a subject and a key, so "which table?" is answerable here.
    # Truthiness alone is not enough: `_SUBJECTS.get` falls back to a placeholder,
    # so a kind upstream adds would satisfy `all(t.subject)` while telling an author
    # nothing. sources.csv arrived exactly that way in 0.5.4 and this assertion did
    # not notice. Name the placeholders instead.
    unanswered = [
        t.csv
        for t in result.data.tables
        if "see describe_table" in t.subject or "see describe_table" in t.keyed_on
    ]
    assert not unanswered, f"no subject/key for: {unanswered}"


async def test_sources_csv_is_a_table_kind_not_a_sidecar(essentials_client):
    """0.5.4 made sources.csv draftable; it must not be described as both.

    It is the one fact sidecar a human writes and the only table the compile
    licence gate reads, so listing it under `sidecars` ("do not hand-author")
    while also listing it as a table told an author two opposite things.
    """
    result = await essentials_client.call_tool("list_tables", {})
    assert "sources.csv" in {t.csv for t in result.data.tables}
    assert "sources.csv" not in result.data.sidecars
    # And it is answerable through the same surface as any other kind.
    described = await essentials_client.call_tool("describe_table", {"csv_name": "sources.csv"})
    assert {c["name"] for c in described.data.columns} >= {"source", "layer"}
    req = await essentials_client.call_tool("table_requirements", {"csv_name": "sources.csv"})
    assert set(req.data.always) == {"source", "layer"}


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
    # variants.csv holds no attestation cell, so the stronger list stays empty
    # rather than echoing the redundancy map.
    assert result.data.attestation_bearing == []


async def test_describe_table_separates_attestation_from_redundancy(essentials_client):
    """The provenance cells carry BOTH reasons, and the sharper one must survive.

    `provenance_quote` is redundancy-bearing (compared against the fulltext) and
    attestation-bearing (it asserts a curator read the passage). Reporting only the
    first would let a caller conclude that a fetched quote is merely an unverifiable
    cell rather than a false claim of provenance.
    """
    result = await essentials_client.call_tool("describe_table", {"csv_name": "studies.csv"})
    assert set(result.data.attestation_bearing) == {"provenance_quote", "provenance_regex"}
    # Subset, never an alternative to it.
    assert set(result.data.attestation_bearing) <= set(result.data.redundancy_bearing)


async def test_attestation_bearing_is_narrowed_to_the_table(essentials_client):
    """A table without the provenance columns must not be told to hand-author them."""
    result = await essentials_client.call_tool("describe_table", {"csv_name": "sources.csv"})
    columns = {c["name"] for c in result.data.columns}
    assert not set(result.data.attestation_bearing) - columns


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("list_tables", {}),
        ("describe_table", {"csv_name": "variants.csv"}),
        ("table_requirements", {"csv_name": "variants.csv"}),
        ("get_template", {"csv_name": "variants.csv"}),
    ],
)
async def test_every_generated_schema_answer_names_its_producing_versions(
    essentials_client, tool, args
):
    """A schema answer must say which toolchain generated it (RM13).

    Every skill tells an agent to ask the tool rather than trust its memory, and a
    stale serving process — a cached plugin build is the measured case — answers
    with an old schema and no signal at all: 11 columns where the installed format
    has 14. The stamp is the only thing in the payload that can be compared.
    """
    result = await essentials_client.call_tool(tool, args)
    assert result.data.produced_by.format_version == FORMAT_VERSION
    assert result.data.produced_by.compiler_version == COMPILER_VERSION


@pytest.mark.parametrize("schemas", [False, True])
async def test_authoring_reference_stamps_both_payload_forms(essentials_client, schemas):
    """The whole-DSL dump carries the stamp inside its JSON, in both forms.

    It returns a JSON string rather than a model because the dossiers document the
    access path ``authoring_reference()["models"][...]``; the stamp therefore goes
    in as a key, and the documented path has to keep working.
    """
    result = await essentials_client.call_tool("authoring_reference", {"schemas": schemas})
    payload = json.loads(result.data)
    assert payload["produced_by"] == {
        "format_version": FORMAT_VERSION,
        "compiler_version": COMPILER_VERSION,
    }
    documented_key = "VariantRow" if schemas else "models"
    assert documented_key in payload


async def test_the_tables_resource_names_its_producing_versions(essentials_client):
    """The resource is generated from the same models, so it carries the same stamp."""
    contents = await essentials_client.read_resource("resource://just-dna/tables")
    text = "\n".join(getattr(c, "text", "") for c in contents)
    assert f"just-dna-format {FORMAT_VERSION}" in text
    assert f"just-dna-compiler {COMPILER_VERSION}" in text


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
