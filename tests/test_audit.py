"""The offline audit — `RM26`, the arithmetic two curation passes had to hand-write.

Every fixture below is a real row from a real module. The `effect_size` pairs are
verbatim from `big_five_personality_snps`, where a "beta" of 7.389 on a personality
trait is the Z-statistic of that row's own p-value to three decimals; the genuine
betas beside them are from the same table, order 0.02, and the rule must be silent
on those or it is worthless.

The property under test throughout is the three-state contract: a signal that could
not be computed is never folded into the ones that computed clean. That folding is
`F61`'s shape — a question that could not be put, presented as nothing to answer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from just_dna_compiler import draft

from just_module_creator import audit

#: Verbatim from `big_five_personality_snps/studies.csv`. `1e-13` has a two-sided Z
#: of 7.441 and the row calls 7.389 a beta.
Z_ROWS = (
    ("rs1729951", "29255261", "1e-13", "-7.389"),
    ("rs10850137", "29942085", "1e-12", "-7.078"),
    ("rs2734837", "29500382", "1e-09", "-6.05"),
)
#: From the same table: per-allele betas of the order a personality GWAS reports.
REAL_BETAS = (
    ("rs10087341", "30643256", "7e-16", "0.020624"),
    ("rs10096511", "30643256", "9.999999999999999e-32", "0.021721"),
    ("rs10512249", "30643256", "4e-13", "0.01866"),
)

STUDIES_HEADER = "rsid,pmid,p_value,effect_size,effect_measure\n"


def _studies(spec: Path, rows, measure: str = "beta") -> None:
    (spec / "studies.csv").write_text(
        STUDIES_HEADER + "".join(f"{r},{p},{pv},{es},{measure}\n" for r, p, pv, es in rows)
    )


def _verification(spec: Path, *records: dict) -> None:
    (spec / "verification.json").write_text(
        json.dumps(
            {
                "module_hash": "sha256:" + "0" * 64,
                "signature": "sha256:" + "1" * 64,
                "difficulty": 20,
                "nonce": 1,
                "producer": "just-dna-enricher 0.6.6",
                "produced_at": "2026-08-21T18:08:39Z",
                "records": [
                    {
                        "check": r["check"],
                        "subjects": r.get("subjects", 0),
                        "findings": r.get("findings", 0),
                        "skipped": r.get("skipped"),
                        "detail": r.get("detail"),
                        "source": r.get("source", "clinvar"),
                        "release": None,
                        "checked_at": "2026-08-21T18:05:15Z",
                    }
                    for r in records
                ],
            }
        )
    )


@pytest.fixture
def module(tmp_path: Path) -> Path:
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text(
        "schema_version: '0.6'\nmodule:\n  name: lactose_tolerance\n  version: 1.0.0\n"
    )
    return spec


# --------------------------------------------------------------------------- #
# The one thing here that is not generated, and its guard
# --------------------------------------------------------------------------- #
def test_every_column_the_audit_reads_is_a_live_field():
    """`RM10`'s lesson at a different address.

    The audit asks a question of specific cells, and no schema can say which cells a
    question is about — so these names are hardcoded and this is the guard that
    replaces a comment promising somebody checked once. `modifier_cn` sat in a
    hand-kept map naming a column upstream had deprecated for a whole release.
    """
    for column in audit.COLUMNS_READ:
        carriers = audit.tables_with(column)
        assert carriers, (
            f"{column!r} is read by name in audit.py and no authored model carries it any more; "
            "find where it went before changing this test"
        )


def test_which_tables_carry_a_column_is_generated_from_upstreams_roster():
    assert audit.tables_with("weight") == ("variants.csv",)
    assert set(audit.tables_with("clin_sig")) <= set(draft.DRAFTABLE)
    assert "variants.csv" in audit.tables_with("clin_sig")
    assert audit.tables_with("no_such_column_anywhere") == ()


# --------------------------------------------------------------------------- #
# `weighting:` — both directions, because both were measured
# --------------------------------------------------------------------------- #
def test_weights_with_no_declared_scale_is_a_decision(module: Path):
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion\n"
        "rs4988235,T/T,1.2,protective,Lactase persistent\n"
        "rs4988235,C/C,-0.4,risk,Lactase non-persistent\n"
    )
    signal = audit.weight_scale(module)
    assert signal.state == "decide"
    assert "2 of 2" in signal.headline


def test_an_empty_weight_column_with_no_declared_scale_is_the_SAME_decision(module: Path):
    """`weight` empty on every row of 190 and compiling green with `weights_rows: 190`.

    Nothing distinguishes "this author deliberately authors none" from "this author
    forgot", which is the whole reason the block exists.
    """
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion\n"
        "rs4988235,T/T,,protective,Lactase persistent\n"
        "rs4988235,C/C,,risk,Lactase non-persistent\n"
    )
    signal = audit.weight_scale(module)
    assert signal.state == "decide"
    assert "no weight is authored" in signal.headline


def test_a_declared_weighting_block_settles_it(module: Path):
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion\nrs4988235,T/T,1.2,protective,Lactase persistent\n"
    )
    (module / "module_spec.yaml").write_text(
        "schema_version: '0.6'\nmodule:\n  name: lactose_tolerance\n"
        "weighting:\n  scale: arbitrary -2..2\n  method: hand-assigned by effect direction\n"
    )
    assert audit.weight_scale(module).state == "clear"


def test_a_weighting_block_with_every_field_blank_does_not_count_as_declared(module: Path):
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion\nrs4988235,T/T,1.2,protective,Lactase persistent\n"
    )
    (module / "module_spec.yaml").write_text(
        "schema_version: '0.6'\nmodule:\n  name: x\nweighting:\n  scale:\n  method:\n  note:\n"
    )
    assert audit.weight_scale(module).state == "decide"


def test_no_spec_yaml_is_not_computed_rather_than_clear(tmp_path: Path):
    spec = tmp_path / "bare"
    spec.mkdir()
    signal = audit.weight_scale(spec)
    assert signal.state == "not_computed"
    assert signal.why_not and "module_spec.yaml" in signal.why_not


# --------------------------------------------------------------------------- #
# `verification.json` — a check that compared nothing is not a check that passed
# --------------------------------------------------------------------------- #
def test_no_verification_file_at_all_is_a_decision(module: Path):
    signal = audit.checks_that_never_ran(module)
    assert signal.state == "decide"
    assert "no check has ever been recorded" in signal.headline


def test_a_record_over_zero_subjects_with_no_reason_is_the_one_that_looks_clean(module: Path):
    """The measured case: `clinical_significance`, subjects 0, skipped null, on eight modules."""
    _verification(
        module,
        {"check": "clinical_significance", "subjects": 0, "findings": 0},
        {"check": "gene_symbol_currency", "subjects": 22, "findings": 0, "detail": "all current"},
    )
    signal = audit.checks_that_never_ran(module)
    assert signal.state == "decide"
    assert "1 of them silently" in signal.headline
    assert any(
        "clinical_significance" in line and "gives no reason" in line for line in signal.detail
    )


def test_a_skip_is_reported_with_upstreams_own_reason_verbatim(module: Path):
    _verification(
        module,
        {"check": "reference_allele", "skipped": "offline", "detail": "no sequence access"},
        {"check": "gene_symbol_currency", "subjects": 22, "findings": 0},
    )
    signal = audit.checks_that_never_ran(module)
    assert signal.state == "decide"
    assert "none of them silently, 1 saying why" in signal.headline
    assert any("offline" in line for line in signal.detail)


def test_the_absent_roster_is_stated_rather_than_invented(module: Path):
    """We own no list of what should have run, and saying so beats guessing one."""
    _verification(module, {"check": "gene_symbol_currency", "subjects": 22, "findings": 0})
    signal = audit.checks_that_never_ran(module)
    assert signal.state == "clear"


def test_findings_counted_and_not_kept(module: Path):
    """52 across two modules, `detail: null`, no sidecar naming the rows. Upstream `S70`."""
    _verification(
        module,
        {"check": "clinical_significance", "subjects": 300, "findings": 20, "detail": None},
        {"check": "gene_symbol_currency", "subjects": 22, "findings": 0},
    )
    signal = audit.findings_without_detail(module)
    assert signal.state == "decide"
    assert "20 recorded finding(s)" in signal.headline


def test_a_finding_that_kept_its_detail_is_clear(module: Path):
    _verification(
        module,
        {"check": "clinical_significance", "subjects": 300, "findings": 2, "detail": "rs1, rs2"},
    )
    assert audit.findings_without_detail(module).state == "clear"


def test_no_verification_file_leaves_the_detail_signal_uncomputed(module: Path):
    signal = audit.findings_without_detail(module)
    assert signal.state == "not_computed"
    assert signal.why_not


# --------------------------------------------------------------------------- #
# `effect_size` against its own p-value
# --------------------------------------------------------------------------- #
def test_a_beta_that_is_the_z_of_its_own_p_value_is_reported(module: Path):
    _studies(module, Z_ROWS)
    signal = audit.effect_size_is_its_own_z(module)
    assert signal.state == "decide"
    assert "3 of 3" in signal.headline
    assert any("rs1729951" in line for line in signal.detail)


def test_real_per_allele_betas_are_left_alone(module: Path):
    """573 genuine betas in the corpus and none of them match. If this fires, the
    tolerance has been widened past usefulness."""
    _studies(module, REAL_BETAS)
    assert audit.effect_size_is_its_own_z(module).state == "clear"


def test_a_row_already_labelled_z_is_the_label_agreeing_with_the_number(module: Path):
    _studies(module, Z_ROWS, measure="Z")
    assert audit.effect_size_is_its_own_z(module).state == "clear"


def test_one_matching_row_is_a_coincidence_and_two_are_a_signal(module: Path):
    _studies(module, (Z_ROWS[0], *REAL_BETAS))
    assert audit.effect_size_is_its_own_z(module).state == "clear"
    _studies(module, (Z_ROWS[0], Z_ROWS[1], *REAL_BETAS))
    assert audit.effect_size_is_its_own_z(module).state == "decide"


def test_no_studies_table_leaves_the_arithmetic_uncomputed(module: Path):
    signal = audit.effect_size_is_its_own_z(module)
    assert signal.state == "not_computed"
    assert signal.why_not and "studies.csv" in signal.why_not


def test_a_p_value_outside_the_open_unit_interval_is_skipped_not_crashed(module: Path):
    _studies(module, (("rs1729951", "29255261", "0", "-7.389"), ("rs1", "1", "1.5", "2.0")))
    assert audit.effect_size_is_its_own_z(module).state == "not_computed"


# --------------------------------------------------------------------------- #
# Clinical claims, scoped by what the models say rather than by one table name
# --------------------------------------------------------------------------- #
def test_clinical_calls_with_no_studies_table_is_a_decision(module: Path):
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion,clin_sig\n"
        "rs1801133,T/T,-0.5,risk,Reduced MTHFR activity,risk_factor\n"
    )
    signal = audit.clinical_claims_without_studies(module)
    assert signal.state == "decide"
    assert "1 row(s)" in signal.headline


def test_clinical_calls_beside_a_studies_table_are_clear(module: Path):
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion,clin_sig\n"
        "rs1801133,T/T,-0.5,risk,Reduced MTHFR activity,risk_factor\n"
    )
    _studies(module, REAL_BETAS)
    assert audit.clinical_claims_without_studies(module).state == "clear"


def test_the_rule_is_not_scoped_to_variants_csv(module: Path):
    """A 1,482-row PGx module fell outside the old `variants.csv`-only wording.

    `diplotypes.csv` carries `clin_sig` too, per the models, so it is in scope
    without anybody adding it to a list.
    """
    assert "diplotypes.csv" in audit.tables_with("clin_sig")
    (module / "diplotypes.csv").write_text(
        "gene,diplotype,phenotype,clin_sig\nCYP2C19,*1/*2,Intermediate metabolizer,drug_response\n"
    )
    assert audit.clinical_claims_without_studies(module).state == "decide"


# --------------------------------------------------------------------------- #
# Fill counts, and the shape of the whole report
# --------------------------------------------------------------------------- #
def test_fill_counts_every_column_of_every_authored_table_present(module: Path):
    (module / "variants.csv").write_text(
        "rsid,genotype,weight,category\nrs4988235,T/T,1.2,\nrs4988235,C/C,,\n"
    )
    fills = {(f.csv, f.column): f for f in audit.column_fill(module)}
    assert fills[("variants.csv", "rsid")].filled == 2
    assert fills[("variants.csv", "weight")].filled == 1
    assert fills[("variants.csv", "category")].filled == 0, (
        "five of six curated modules had this empty on every row and nothing said so"
    )
    assert all(f.rows == 2 for f in fills.values())


def test_a_signal_that_could_not_be_computed_is_never_folded_into_the_clear_ones(tmp_path: Path):
    """`F61`'s shape, asserted directly: silence and a question nobody could put."""
    spec = tmp_path / "empty"
    spec.mkdir()
    decisions, clear, blocked = audit.run(spec)
    assert blocked, "an empty directory computes almost nothing and must say so"
    assert all(s.why_not for s in blocked)
    assert all(not s.why_not for s in clear + decisions)
    assert len(decisions) + len(clear) + len(blocked) == len(audit.SIGNALS)


# --------------------------------------------------------------------------- #
# Through the tool
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_audit_module_is_in_the_default_tier_and_reports_the_three_states(
    client, spec_dir: Path
):
    (spec_dir / "variants.csv").write_text(
        "rsid,genotype,weight,state,conclusion,clin_sig\n"
        "rs1801133,T/T,-0.5,risk,Reduced MTHFR activity,risk_factor\n"
    )
    out = await client.call_tool("audit_module", {"spec_dir": str(spec_dir)})
    assert out.data.spec_dir == str(spec_dir)
    assert "weight_scale" in {s.name for s in out.data.decisions}
    # The fixture ships a `studies.csv`, so the clinical-claim signal computes and
    # finds nothing — it belongs in `clear`, and asserting that is the point: the
    # three lists must be a partition, not three ways of saying "look at this".
    assert "clinical_claims_without_studies" in {s.name for s in out.data.clear}
    assert all(s.state == "decide" for s in out.data.decisions)
    assert all(s.why_not for s in out.data.not_computed)
    assert any(f.csv == "variants.csv" for f in out.data.fill)


@pytest.mark.anyio
async def test_fill_false_drops_the_counts_and_nothing_else(client, spec_dir: Path):
    (spec_dir / "variants.csv").write_text("rsid,genotype,weight\nrs1801133,T/T,-0.5\n")
    with_fill = await client.call_tool("audit_module", {"spec_dir": str(spec_dir)})
    without = await client.call_tool(
        "audit_module", {"spec_dir": str(spec_dir), "fill": False}
    )
    assert with_fill.data.fill and without.data.fill == []
    assert [s.name for s in with_fill.data.decisions] == [s.name for s in without.data.decisions]
