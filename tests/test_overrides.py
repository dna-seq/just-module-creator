"""Recording that an authored value outranks a source, and reading the queue back.

`RM16`. The property under test throughout is that a record **never produces a
pass**: it downgrades nothing, silences nothing, and stays in the queue until
somebody revisits it or the archive catches up.

Real identifiers: `rs1801133` is the MTHFR c.665C>T variant and ClinVar's own calls
for it are the vocabulary used below.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from just_dna_format.manifest import ProvenanceDoc, ProvenanceItem

from just_module_creator import overrides
from just_module_creator.overrides import OverrideRecord, value_digest

VARIANTS = (
    "rsid,genotype,weight,state,conclusion,gene,clin_sig\n"
    "rs1801133,T/T,-0.5,risk,Reduced MTHFR activity; homozygous,MTHFR,risk_factor\n"
    "rs1801133,C/T,-0.25,risk,Reduced MTHFR activity; heterozygous,MTHFR,risk_factor\n"
    "rs1801133,C/C,0.0,neutral,Normal MTHFR activity,MTHFR,risk_factor\n"
)


def _record(
    variant_key: str = "rs1801133",
    field: str = "clin_sig",
    authored_value: str = "risk_factor",
    source_name: str = "clinvar",
    source_value: str | None = "benign",
    reason: str = (
        "ClinVar's benign call rests on a 2015 submission; the 2021 meta-analysis "
        "(PMID 33417889) restores the association in the folate-replete stratum."
    ),
    recorded_by: str = "ai-module-creator",
) -> OverrideRecord:
    return OverrideRecord(
        variant_key=variant_key,
        field=field,
        authored_value=authored_value,
        source_name=source_name,
        source_value=source_value,
        reason=reason,
        recorded_by=recorded_by,
        value_sha256=value_digest(authored_value),
    )


@pytest.fixture
def module(tmp_path: Path) -> Path:
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "variants.csv").write_text(VARIANTS)
    return spec


# --------------------------------------------------------------------------- #
# The record, in upstream's shape
# --------------------------------------------------------------------------- #
def test_a_record_round_trips_through_upstreams_own_file(module: Path):
    written = _record()
    overrides.write_records(module, [written])
    back, foreign = overrides.read_records(module)
    assert foreign == []
    assert len(back) == 1
    got = back[0]
    assert (got.variant_key, got.field) == ("rs1801133", "clin_sig")
    assert got.source_name == "clinvar"
    assert got.source_value == "benign"
    assert got.recorded_by == "ai-module-creator"
    assert got.reason.startswith("ClinVar's benign call rests on a 2015 submission")
    assert got.value_sha256 == value_digest("risk_factor")


def test_the_file_validates_as_upstreams_provenance_document(module: Path):
    """It must be *their* file, not a lookalike: the registry recognises this name."""
    overrides.write_records(module, [_record()])
    payload = json.loads((module / "provenance.json").read_text())
    doc = ProvenanceDoc.model_validate(payload)
    assert doc.generator == "just-module-creator"
    assert [item.variant_key for item in doc.items] == ["rs1801133"]


def test_one_item_per_field_so_two_fields_on_one_variant_both_survive(module: Path):
    overrides.write_records(module, [_record(), _record(field="state", authored_value="risk")])
    back, _ = overrides.read_records(module)
    assert sorted(r.field for r in back) == ["clin_sig", "state"]


def test_another_writers_provenance_is_kept_rather_than_rewritten(module: Path):
    """Discarding somebody else's record silently is the defect this module prevents."""
    ProvenanceDoc(
        generator="somebody-else",
        items=[ProvenanceItem(variant_key="rs1801131", rationale="hand-written note")],
    )
    (module / "provenance.json").write_text(
        ProvenanceDoc(
            generator="somebody-else",
            items=[ProvenanceItem(variant_key="rs1801131", rationale="hand-written note")],
        ).model_dump_json(exclude_none=True)
    )
    overrides.upsert(module, _record())
    records, foreign = overrides.read_records(module)
    assert [r.field for r in records] == ["clin_sig"]
    assert foreign == ["hand-written note"]


def test_upsert_replaces_the_record_for_one_field_and_says_so(module: Path):
    _, replaced_first = overrides.upsert(module, _record())
    _, replaced_again = overrides.upsert(module, _record(reason="a better reason"))
    assert (replaced_first, replaced_again) == (False, True)
    records, _ = overrides.read_records(module)
    assert len(records) == 1
    assert records[0].reason == "a better reason"


# --------------------------------------------------------------------------- #
# The binding: a record justifies one value, not the cell forever
# --------------------------------------------------------------------------- #
def test_editing_the_cell_again_makes_the_record_stale(module: Path):
    overrides.upsert(module, _record())
    assert overrides.review_queue(module)[0].still_bound

    (module / "variants.csv").write_text(VARIANTS.replace("risk_factor", "pathogenic"))
    entry = overrides.review_queue(module)[0]
    assert not entry.still_bound, "the reason no longer describes the value it is attached to"
    assert entry.current_value == "pathogenic"


def test_an_unbound_record_ranks_ahead_of_a_bound_one(module: Path):
    overrides.upsert(module, _record())
    overrides.upsert(module, _record(variant_key="rs1801131", authored_value="not_in_the_file"))
    queue = overrides.review_queue(module)
    assert [q.still_bound for q in queue] == [False, True]


# --------------------------------------------------------------------------- #
# The terminal state, and the three-valued answer that makes it honest
# --------------------------------------------------------------------------- #
def test_without_the_archive_sidecar_the_state_is_unknown_not_agreement(module: Path):
    overrides.upsert(module, _record())
    assert overrides.review_queue(module)[0].mismatch_state == "unknown"


def test_a_standing_disagreement_is_standing(module: Path):
    (module / "clinical_assertions.csv").write_text(
        "rsid,clin_sig\nrs1801133,benign\n",
    )
    overrides.upsert(module, _record())
    assert overrides.review_queue(module)[0].mismatch_state == "standing"


def test_when_the_archive_catches_up_the_record_becomes_retirable(module: Path):
    """The one piece of evidence in the format that an authored judgement was vindicated."""
    (module / "clinical_assertions.csv").write_text(
        "rsid,clin_sig\nrs1801133,risk_factor\n",
    )
    overrides.upsert(module, _record())
    entry = overrides.review_queue(module)[0]
    assert entry.mismatch_state == "resolved"
    assert entry.still_bound, "it is retirable because it was right, not because it went stale"


def test_a_field_with_no_archive_answer_stays_unknown_even_with_the_sidecar(module: Path):
    (module / "clinical_assertions.csv").write_text("rsid,clin_sig\nrs1801133,benign\n")
    overrides.upsert(module, _record(field="state", authored_value="risk"))
    assert overrides.review_queue(module)[0].mismatch_state == "unknown"


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_record_override_writes_the_file_and_logs_the_move(essentials_client, module: Path):
    out = await essentials_client.call_tool(
        "record_override",
        {
            "spec_dir": str(module),
            "variant_key": "rs1801133",
            "field": "clin_sig",
            "authored_value": "risk_factor",
            "source_name": "clinvar",
            "source_value": "benign",
            "reason": "the 2021 meta-analysis (PMID 33417889) restores the association",
            "recorded_by": "ai-module-creator",
        },
    )
    assert out.data.replaced_existing is False
    assert (module / "provenance.json").is_file()

    logged = (module / "logs" / "authoring.log").read_text()
    assert "override rs1801133 clin_sig=" in logged
    assert "outranks clinvar" in logged
    assert str(module) not in logged, "the log publishes verbatim — no absolute paths in it"


@pytest.mark.anyio
async def test_the_log_appends_rather_than_replacing(essentials_client, module: Path):
    for reason in ("first reason", "second reason"):
        await essentials_client.call_tool(
            "record_override",
            {
                "spec_dir": str(module),
                "variant_key": "rs1801133",
                "field": "clin_sig",
                "authored_value": "risk_factor",
                "source_name": "clinvar",
                "reason": reason,
                "recorded_by": "ai-module-creator",
            },
        )
    lines = (module / "logs" / "authoring.log").read_text().strip().splitlines()
    assert len(lines) == 2
    assert "[replaced an earlier record]" in lines[1]


@pytest.mark.anyio
async def test_review_queue_reports_what_it_could_not_decide(essentials_client, module: Path):
    await essentials_client.call_tool(
        "record_override",
        {
            "spec_dir": str(module),
            "variant_key": "rs1801133",
            "field": "clin_sig",
            "authored_value": "risk_factor",
            "source_name": "clinvar",
            "reason": "a reason",
            "recorded_by": "ai-module-creator",
        },
    )
    out = await essentials_client.call_tool("review_queue", {"spec_dir": str(module)})
    assert out.data.total == 1
    assert out.data.retirable == 0
    assert out.data.entries[0].mismatch_state == "unknown"


@pytest.mark.anyio
async def test_an_empty_module_has_an_empty_queue(essentials_client, module: Path):
    out = await essentials_client.call_tool("review_queue", {"spec_dir": str(module)})
    assert out.data.total == 0
    assert out.data.entries == []
