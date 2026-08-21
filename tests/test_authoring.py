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
        ("describe_machine_table", {"csv_name": "resolution.csv"}),
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


async def test_scaffolding_a_binning_module_beside_studies_invites_no_empty_variants_csv(
    essentials_client, tmp_path
):
    """`studies.csv` pulls `variants.csv` in only when it is asked for alone (`S49`).

    RM47 made a study row legal with no variant identity precisely so a binning module
    can ground its thresholds through `pmid`, so the unconditional pull contradicted the
    composition rule this same surface teaches — never add an empty table to keep another
    company — and an empty `variants.csv` compiles strict-green while asserting nothing.
    `companions_for` applies the condition; asserted through the tool, on disk, because
    the warning and the file are two claims that can disagree.
    """
    spec = tmp_path / "bins"
    result = await essentials_client.call_tool(
        "scaffold_module",
        {"spec_dir": str(spec), "name": "m", "kinds": ["repeat_alleles.csv", "studies.csv"]},
    )
    assert result.data.written
    assert not (spec / "variants.csv").exists()
    assert not any("variants.csv" in w for w in result.data.warnings)
    # The unconditional direction is untouched: a variant claim still needs its evidence.
    alone = await essentials_client.call_tool(
        "scaffold_module",
        {"spec_dir": str(tmp_path / "vars"), "name": "m", "kinds": ["variants.csv"]},
    )
    assert (tmp_path / "vars" / "studies.csv").exists()
    assert any("studies.csv" in w for w in alone.data.warnings)


async def test_a_redundancy_reason_says_when_its_checker_cannot_see_this_table(
    essentials_client,
):
    """`REDUNDANCY_BEARING` is keyed on a bare column, so the reason outran the checker.

    `clin_sig` is a column on `variants.csv`, on `diplotypes.csv` and on all four binning
    kinds; `verify_clin_sig` takes `list[VariantRow]` and never sees the others. Naming
    the ClinVar cross-examination on a binning row is right advice with a false reason,
    and a false reason implies a green run was an agreement. Upstream scoped the
    explanation in 0.6.6 (`S59`); this asserts we carry the scope rather than the bare
    reason, on both sides of it.
    """
    scoped = await essentials_client.call_tool(
        "describe_table", {"csv_name": "copynumbers.csv"}
    )
    assert "clin_sig" in scoped.data.redundancy_bearing
    assert "does not read copynumbers.csv" in scoped.data.redundancy_bearing["clin_sig"]

    unscoped = await essentials_client.call_tool("describe_table", {"csv_name": "variants.csv"})
    assert "does not read" not in unscoped.data.redundancy_bearing["clin_sig"]


async def test_describe_table_answers_what_an_append_collides_on(essentials_client):
    """The `key` block upstream's `describe_table` has promised since 0.5, passed through.

    A second pass appends, so "what will this collide with" is the question before
    re-running anything — and the three rules are not interchangeable: two `overlap` rows
    with identical keys are legal, two `equality` ones are a duplicate.
    """
    from just_dna_compiler import hints

    for csv_name in ("variants.csv", "repeat_alleles.csv"):
        described = await essentials_client.call_tool("describe_table", {"csv_name": csv_name})
        key = hints.key_fields(csv_name)
        assert key is not None
        assert described.data.key["columns"] == list(key.columns)
        assert described.data.key["rule"] == key.rule
    listed = await essentials_client.call_tool("list_tables", {})
    rules = {t.csv: t.key_rule for t in listed.data.tables}
    assert rules["repeat_alleles.csv"] == "overlap"
    assert rules["variants.csv"] == "equality"


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


# --------------------------------------------------------------------------- #
# RM10 — three answers restated a schema fact instead of generating it
# --------------------------------------------------------------------------- #
def _key_columns(keyed_on: str) -> list[str]:
    """The column tokens out of a `keyed_on` string like `(gene, repeat_unit)`."""
    return [token.strip() for token in keyed_on.strip("()").split(",") if token.strip()]


async def test_the_sidecar_roster_is_derived_from_the_installed_toolchain(essentials_client):
    """`sidecars` was a four-item literal and the installed toolchain has seven.

    It named `resolution.csv` and the three 0.5 fact tables, so the three format-0.6
    ones (`gene_validity.csv`, `clinical_assertions.csv`, `gwas_effects.csv`) were
    absent from the one answer that claims to list what a machine writes — while
    `authoring_reference` in the same module described all of them. Computed here from
    the same public roster the tool derives from, so a fact table added upstream
    changes both sides at once instead of dating this assertion.
    """
    from just_dna_compiler import draft
    from just_dna_registry import specfiles

    expected = {specfiles.RESOLUTION_CSV, *specfiles.FACT_CSVS} - set(draft.DRAFTABLE)
    result = await essentials_client.call_tool("list_tables", {})
    assert set(result.data.sidecars) == expected
    assert result.data.sidecars == sorted(result.data.sidecars)  # deterministic order
    # The licensing carve-out, derived rather than special-cased: a fact sidecar that
    # is also draftable belongs under `tables`, where it has a template and a linter.
    assert not set(result.data.sidecars) & set(draft.DRAFTABLE)


async def test_every_documented_key_column_is_a_live_undeprecated_field(essentials_client):
    """`keyed_on` is generated now, and this asks whether the generated answer is usable.

    It was written when the strings were hand-kept (`S48`), and that is exactly how
    `copynumbers.csv` went on naming `modifier_cn` across all of 0.6, after upstream
    deprecated it in favour of `modifier_copy_number`: an author was being told to key on
    a column that is removed at format 1.0. `hints.key_fields` answers it since 0.6.5, so
    the drift this caught cannot recur from our side — it can still arrive from theirs,
    and an author reading a deprecated key column is misled either way. So the assertion
    stays and its subject moves: every column we surface must resolve on the live model
    and must not be retired.
    """
    from just_dna_compiler import draft

    result = await essentials_client.call_tool("list_tables", {})
    missing: list[str] = []
    deprecated: list[str] = []
    for table in result.data.tables:
        model = draft.DRAFTABLE[table.csv]
        for column in _key_columns(table.keyed_on):
            field = model.model_fields.get(column)
            if field is None:
                # A key column is not always an authored field: on `studies.csv`,
                # `variant_key` is a **property** derived from rsid / chrom:start:ref
                # (and null since RM47 for a row that grounds a threshold rather than a
                # variant), while on `variants.csv` and `haplotypes.csv` the same name is
                # a real column. A property counts; anything that resolves to neither is
                # prose masquerading as a column name, which is what three of these were.
                if not isinstance(getattr(model, column, None), property):
                    missing.append(f"{table.csv}:{column}")
                continue
            # Upstream's convention is to OPEN a retired column's description with the
            # marker — `modifier_cn` reads "DEPRECATED since 0.6, removed at 1.0 — use
            # modifier_copy_number". Anchored at the start rather than searched for,
            # because its replacement's description mentions the word too ("Replaces the
            # deprecated integer modifier_cn"), and a substring test flagged the live
            # column instead of the retired one when this was first written.
            if (field.description or "").lstrip().upper().startswith("DEPRECATED"):
                deprecated.append(f"{table.csv}:{column}")
    assert not missing, f"keyed_on names tokens that are not columns: {missing}"
    assert not deprecated, f"keyed_on names deprecated columns: {deprecated}"


async def test_the_studies_subject_no_longer_says_a_row_must_name_a_variant(essentials_client):
    """RM47 relaxed `StudyRow`'s identifier rule, and our answer said otherwise.

    `REQUIRED_ANY_OF` went from `({rsid}, {chrom})` to `()`: a paper grounding a bin
    threshold, a method or a population is a legal `studies.csv` row with no variant
    identity at all. The subject text still read "the evidence for a variant", which
    would have an author drop exactly the row RM47 was added to allow. The upstream
    state is asserted first, so if it is ever tightened again this test says which half
    moved.
    """
    from just_dna_format.spec import StudyRow

    assert StudyRow.REQUIRED_ANY_OF == ()
    # Ground truth, not prose: the model itself accepts a row with only a pmid.
    assert StudyRow(pmid="11788828", conclusion="x").variant_key is None

    result = await essentials_client.call_tool("list_tables", {})
    subject = {t.csv: t.subject for t in result.data.tables}["studies.csv"]
    assert "no variant" in subject.lower(), subject


async def test_a_binning_module_may_carry_studies_without_variants(essentials_client, tmp_path):
    """The composition note now says this, so the note is checked against a compile.

    Post-RM47 the honest advice to a binning author is *cite your thresholds*, and a
    study row can now carry that citation without naming a variant. If upstream ever
    required `variants.csv` beside `studies.csv`, this fails and the note is wrong.
    """
    spec = tmp_path / "bins"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text(
        "schema_version: '1.0'\n"
        "module:\n"
        "  title: SMN1 copy number (test)\n"
        "  description: SMN1 dosage bins\n"
        "  report_title: SMN1\n"
        "  name: smn1_test\n"
        "genome_build: GRCh38\n"
    )
    (spec / "copynumbers.csv").write_text(
        "measure_kind,measure_min,measure_max,measure_tiling,direction,conclusion,"
        "unresolved,gene,pmid\n"
        "copy_number,0,0,continuous,risk,No SMN1 copies,false,SMN1,9382095\n"
        "copy_number,1,1,continuous,risk,One SMN1 copy,false,SMN1,9382095\n"
    )
    (spec / "studies.csv").write_text(
        "pmid,conclusion\n9382095,SMN1 deletion and SMA severity\n"
    )

    result = await essentials_client.call_tool(
        "validate_module", {"spec_dir": str(spec), "strict": True}
    )
    assert result.data.valid, result.data.errors
    assert not any("variants.csv" in e for e in result.data.errors)


# --------------------------------------------------------------------------- #
# RM11 — the machine-produced tables are answerable, and marked unauthorable
# --------------------------------------------------------------------------- #
def test_the_produced_roster_agrees_with_the_registry_that_recognises_the_same_files():
    """Two packages enumerate the machine-produced tables, and they must not disagree.

    The roster and its models both come from `hints.DERIVED_TABLE_MODELS` since 0.6.5
    (`S47`), which is the compiler's own loader tuple published rather than restated —
    so asserting the map against itself would measure nothing. The registry publishes the
    same roster independently, because it has to recognise every file the compiler reads,
    and it is a *different* package on a *different* release cadence. That is the
    comparison worth making: a fact table that reaches one and not the other is a file an
    author can be handed and cannot be told about.
    """
    from just_dna_compiler import draft, hints
    from just_dna_registry import specfiles

    from just_module_creator.tools.authoring import _PRODUCED_CSVS, _PRODUCED_MODELS

    assert set(_PRODUCED_MODELS) == set(_PRODUCED_CSVS)
    assert set(_PRODUCED_CSVS) == {specfiles.RESOLUTION_CSV, *specfiles.FACT_CSVS} - set(
        draft.DRAFTABLE
    )
    for csv_name, model in _PRODUCED_MODELS.items():
        assert hints.derived_model_for(csv_name) is model


async def test_every_machine_produced_sidecar_answers_its_columns(essentials_client):
    """The hole RM11 closed: an author reads these files and could not ask what is in them.

    Expected columns come from `reference.authored_field_names`, not from the assembly
    the tool passes through, so this is a comparison rather than an echo.
    """
    from just_dna_compiler import hints
    from just_dna_format.reference import authored_field_names

    from just_module_creator.tools.authoring import _PRODUCED_MODELS

    listed = (await essentials_client.call_tool("list_tables", {})).data.sidecars
    assert set(listed) == set(_PRODUCED_MODELS)
    for csv_name, model in sorted(_PRODUCED_MODELS.items()):
        result = await essentials_client.call_tool(
            "describe_machine_table", {"csv_name": csv_name}
        )
        assert result.data.csv == csv_name
        assert result.data.model == model.__name__
        assert [c["name"] for c in result.data.columns] == list(authored_field_names(model))
        # Every column carries the model's own description, which is the whole point of
        # asking rather than remembering.
        assert all("description" in c for c in result.data.columns)
        # And the key the pass merges on: these files are merge-not-clobber, so an
        # author asking what is in one is one question away from asking what a re-run
        # will do to a row they wrote.
        key = hints.key_fields(csv_name)
        assert key is not None
        assert result.data.key["columns"] == list(key.columns)
        assert result.data.key["rule"] == key.rule
        assert result.data.hand_authored is False
        assert result.data.refusal
    # `resolution.csv` is the one whose rule is neither equality nor overlap: one rsID
    # legitimately resolves to several loci, so a repeated subject is not a duplicate.
    resolution = await essentials_client.call_tool(
        "describe_machine_table", {"csv_name": "resolution.csv"}
    )
    assert resolution.data.key["rule"] == "subject"


async def test_a_machine_table_answer_carries_no_authoring_fields(essentials_client):
    """`hand_authored: false` plus the absence of the three author-only fields.

    Extending `describe_table` would have had to answer `requirements`,
    `redundancy_bearing` and `attestation_bearing` with empty values, and an empty
    `requirements` reads as *no requirements* rather than as *the question does not
    apply*. The separate model is how that stays unsayable.
    """
    result = await essentials_client.call_tool(
        "describe_machine_table", {"csv_name": "frequencies.csv"}
    )
    for author_only in ("requirements", "redundancy_bearing", "attestation_bearing"):
        assert not hasattr(result.data, author_only)
    assert result.data.hand_authored is False
    # And the other side of the pair says the opposite, in the same key.
    authored = await essentials_client.call_tool("describe_table", {"csv_name": "variants.csv"})
    assert authored.data.hand_authored is True


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("describe_table", {"csv_name": "resolution.csv"}),
        ("table_requirements", {"csv_name": "resolution.csv"}),
        ("get_template", {"csv_name": "resolution.csv"}),
        ("lint_rows", {"csv_name": "resolution.csv", "csv_text": "variant_key\nrs4988235\n"}),
        ("scaffold_module", {"spec_dir": "/nonexistent", "kinds": ["resolution.csv"]}),
    ],
)
async def test_an_authoring_route_redirects_a_sidecar_instead_of_calling_it_unknown(
    essentials_client, tool, args
):
    """"Unknown table kind 'resolution.csv'" was false and sent the reader hunting a typo.

    The file is real, it is in every enriched module, and it is simply not authored.
    Each authoring route now says that and names the route that answers.
    """
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError) as raised:
        await essentials_client.call_tool(tool, args)
    message = str(raised.value)
    assert "describe_machine_table" in message
    assert "Unknown" not in message


@pytest.mark.parametrize("spelling", ["licensing.csv", "sources.csv"])
async def test_the_licence_table_is_refused_by_the_machine_route(essentials_client, spelling):
    """`licensing.csv` must NOT get the do-not-author treatment, under either spelling.

    It is a fact sidecar and it is the one a human writes — the only table the compile
    licence gate reads. The carve-out is derived from `draft.DRAFTABLE`, so it needs no
    entry of its own here and cannot fall out of step with the roster.
    """
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="describe_table"):
        await essentials_client.call_tool("describe_machine_table", {"csv_name": spelling})
    answered = await essentials_client.call_tool("describe_table", {"csv_name": spelling})
    assert {c["name"] for c in answered.data.columns} >= {"source", "layer"}
    assert answered.data.hand_authored is True


async def test_an_unknown_name_is_still_reported_as_unknown(essentials_client):
    """The redirect must not swallow a genuine typo into a reassuring answer."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError, match="Unknown table"):
        await essentials_client.call_tool("describe_machine_table", {"csv_name": "nonsense.csv"})
