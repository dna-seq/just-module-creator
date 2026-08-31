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


def test_the_column_is_written_where_a_reader_who_is_not_us_can_find_it():
    """`ProvenanceItem.outranks` answered `S52` in 0.6.5; the record uses it.

    Before it existed the column name lived only inside our own marker, so the file
    travelled with the module and the one fact a second tool most needs from it — WHICH
    column disagrees with the source — was legible to our regex alone. The marker is not
    a duplicate of it: it carries the digest that binds the record to the cell, the
    source disagreed with, when and by whom, none of which upstream's schema holds.
    """
    record = _record()
    item = overrides.to_items([record])[0]

    assert item.outranks == {
        "clin_sig": (
            "ClinVar's benign call rests on a 2015 submission; the 2021 meta-analysis "
            "(PMID 33417889) restores the association in the folate-replete stratum. "
            "Source said: benign."
        )
    }
    # Round-tripping still goes through the marker, which is what carries the binding.
    back, foreign = overrides.from_items([item])
    assert not foreign
    assert back[0].field == "clin_sig"
    assert back[0].value_sha256 == value_digest("risk_factor")

def test_a_judged_cell_claims_no_dispute_it_did_not_have():
    """No `source_value` means no disagreement, so `outranks` stays empty.

    Upstream scopes the field precisely — "per-column justification for this row
    deliberately DISAGREEING with a source" — and a key's *presence* is the
    machine-readable bit. We were writing one for every record, including the cells no
    source can supply: a `weight`, a `conclusion`, a `direction`. That put a
    non-disagreement in a disagreement field and diluted the signal the map exists to
    carry.

    Measured 2026-08-31: six of seven records across two benchmark runs were judged
    cells, and `provenance.json` publishes. One agent reported the wording itself
    without being asked. `F71`.
    """
    judged = overrides.OverrideRecord(
        variant_key="rs117385980",
        field="weight",
        authored_value="-0.2",
        source_name="no source consulted",
        source_value=None,
        reason="Two underpowered cohorts, both non-significant; the sign is a judgement.",
        recorded_at="2026-08-31T00:00:00Z",
        recorded_by="claude-opus-5",
        human_reviewed=False,
        value_sha256=value_digest("-0.2"),
    )
    item = overrides.to_items([judged])[0]

    assert item.outranks == {}, "a judged cell must not claim it outranks anything"
    # The judgement is still recorded and still travels — it goes to `rationale`,
    # which upstream documents as "why this annotation was made".
    assert "judgement" in (item.rationale or "")
    # And it still round-trips, so nothing is lost by not claiming a dispute.
    back, foreign = overrides.from_items([item])
    assert not foreign
    assert back[0].field == "weight"
    assert back[0].value_sha256 == value_digest("-0.2")


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


def test_a_record_for_a_column_the_table_does_not_carry_is_unknown_not_unbound(module: Path):
    """Found by dogfooding on `assets/fto_bmi`, whose `variants.csv` has no `clin_sig`.

    The queue said `still_bound: false`, which reads as *somebody edited this cell after
    the reason was written* — an accusation about an edit nobody made. There is no cell,
    so the question could not be put, and `null` is the only honest answer. §2: never
    collapse unknown into a boolean.
    """
    (module / "variants.csv").write_text(
        "rsid,genotype,state,conclusion,gene\nrs1801133,C/T,risk,Reduced MTHFR activity,MTHFR\n"
    )
    overrides.upsert(module, _record())
    entry = overrides.review_queue(module)[0]
    assert entry.still_bound is None
    assert entry.current_value is None


def test_a_record_for_a_row_that_is_gone_is_also_unknown(module: Path):
    overrides.upsert(module, _record(variant_key="rs1801131", authored_value="benign"))
    entry = overrides.review_queue(module)[0]
    assert entry.still_bound is None, "the row is absent, so nothing was edited"


def test_the_queue_ranks_broken_bindings_first_then_unanswerable_then_live(module: Path):
    overrides.upsert(module, _record())  # bound
    overrides.upsert(module, _record(variant_key="rs1801131", authored_value="gone"))  # absent
    overrides.upsert(module, _record(field="state", authored_value="stale"))  # edited since
    queue = overrides.review_queue(module)
    assert [q.still_bound for q in queue] == [False, None, True]


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
async def test_record_override_writes_the_file_and_logs_the_move(client, module: Path):
    out = await client.call_tool(
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
async def test_the_log_appends_rather_than_replacing(client, module: Path):
    for reason in ("first reason", "second reason"):
        await client.call_tool(
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
async def test_review_queue_reports_what_it_could_not_decide(client, module: Path):
    await client.call_tool(
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
    out = await client.call_tool("review_queue", {"spec_dir": str(module)})
    assert out.data.total == 1
    assert out.data.retirable == 0
    assert out.data.entries[0].mismatch_state == "unknown"


@pytest.mark.anyio
async def test_an_empty_module_has_an_empty_queue(client, module: Path):
    out = await client.call_tool("review_queue", {"spec_dir": str(module)})
    assert out.data.total == 0
    assert out.data.entries == []


# --------------------------------------------------------------------------- #
# F61 — the record that was written and then read back as somebody else's
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "source_name",
    [
        "clinvar",
        "GWAS Catalog",
        "ClinVar 2024-06",
        "gnomAD v4.1 (non-neuro)",
        "the row's own p-value",
    ],
)
def test_a_source_named_with_a_space_survives_the_round_trip(source_name: str):
    """`F61`: the marker used to encode `source` as `[A-Za-z0-9_.-]+`.

    Every one of these is a source somebody would actually type, and every one of
    them was written to `provenance.json` happily and then failed to parse on the
    way back — so the record became *foreign* provenance, `review_queue` returned
    `{"total": 0}`, and a reviewer opening the module was told there was nothing to
    review while the evidence sat in the file beside them.

    Written as a round-trip rather than a regex assertion, because the defect was
    precisely that the writer and the reader disagreed and neither was wrong alone.
    """
    record = _record(source_name=source_name)
    back, foreign = overrides.from_items(overrides.to_items([record]))
    assert foreign == []
    assert len(back) == 1
    assert back[0].source_name == source_name
    assert back[0].source_value == "benign"
    assert back[0].value_sha256 == value_digest("risk_factor")


def test_markers_already_written_still_parse():
    """The loosened pattern must recover records, not orphan a second batch.

    This rationale is verbatim what the pre-fix writer produced, pasted rather than
    generated: a test that builds the string with `to_items` would agree with
    whatever the writer does today and could never fail.
    """
    item = ProvenanceItem(
        variant_key="rs1801133",
        rationale=(
            "The 2021 meta-analysis restores the association. Source said: benign. "
            "[jmc field=clin_sig value_sha256=0d1e2f3a4b5c source=clinvar "
            "recorded=2026-08-21T04:17:09Z by=ai-module-creator]"
        ),
        human_reviewed=False,
    )
    back, foreign = overrides.from_items([item])
    assert foreign == []
    assert back[0].source_name == "clinvar"
    assert back[0].recorded_by == "ai-module-creator"
    assert back[0].recorded_at == "2026-08-21T04:17:09Z"
    assert back[0].reason == "The 2021 meta-analysis restores the association."


def test_a_reason_that_quotes_the_phrase_keeps_its_own_prose():
    """`Source said:` is appended, so the LAST occurrence is ours.

    "the source said: X" is a natural sentence in a justification. Splitting on the
    first occurrence read the author's own prose back as the archive's answer.
    """
    record = _record(
        reason="ClinVar's summary said: pathogenic, but the submitter withdrew it in 2024.",
        source_value="pathogenic",
    )
    back, foreign = overrides.from_items(overrides.to_items([record]))
    assert foreign == []
    assert back[0].reason == (
        "ClinVar's summary said: pathogenic, but the submitter withdrew it in 2024."
    )
    assert back[0].source_value == "pathogenic"


def test_a_newline_in_a_handle_is_collapsed_rather_than_breaking_the_marker():
    record = _record(recorded_by="ai-module-creator\n(overnight run)")
    back, foreign = overrides.from_items(overrides.to_items([record]))
    assert foreign == []
    assert back[0].recorded_by == "ai-module-creator (overnight run)"


def test_a_field_that_is_not_a_column_name_is_refused_rather_than_written():
    """Refused, not collapsed: a marker that cannot be read is published verbatim."""
    with pytest.raises(ValueError, match="column name"):
        _record(field="clin sig")


@pytest.mark.anyio
async def test_the_queue_holds_a_record_whose_source_has_a_space_in_its_name(
    client, module: Path
):
    """`F61` end to end, through the two tools rather than through the codec."""
    await client.call_tool(
        "record_override",
        {
            "spec_dir": str(module),
            "variant_key": "rs1801133",
            "field": "weight",
            "authored_value": "-0.5",
            "source_name": "GWAS Catalog",
            "source_value": "-1.0",
            "reason": "the published beta is per-allele; this row is the homozygote",
            "recorded_by": "ai-module-creator",
        },
    )
    out = await client.call_tool("review_queue", {"spec_dir": str(module)})
    assert out.data.other_provenance == []
    assert out.data.total == 1
    assert out.data.entries[0].record.source_name == "GWAS Catalog"
    assert out.data.entries[0].mismatch_state == "unknown"


@pytest.mark.anyio
async def test_the_returned_note_describes_the_mode_the_call_actually_used(
    client, module: Path
):
    """`F71` split the log line on `source_value` and left the returned note alone.

    The note is the one field a caller reads back to learn what just happened, and it
    told an author who had recorded a judged cell that "the cross-check still reports
    this mismatch" — there was no source, no mismatch and nothing to downgrade. Both
    branches are asserted here, because fixing one and leaving the other is exactly the
    defect this closes.
    """
    disagreed = await client.call_tool(
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
    assert "outrank" in disagreed.data.note
    assert "mismatch" in disagreed.data.note

    authored = await client.call_tool(
        "record_override",
        {
            "spec_dir": str(module),
            "variant_key": "rs1801133",
            "field": "weight",
            "authored_value": "-0.2",
            "source_name": "clinvar",
            "reason": "a judged magnitude; no source supplies a weight",
            "recorded_by": "ai-module-creator",
        },
    )
    assert "authored cell" in authored.data.note
    assert "outrank" not in authored.data.note.replace("not an outrank", "")
    assert "mismatch" not in authored.data.note

    logged = (module / "logs" / "authoring.log").read_text()
    assert "authored rs1801133 weight=" in logged
    assert "outranks clinvar ('benign')" in logged


def test_the_only_value_the_queue_shows_for_a_multi_row_variant_can_bind(module: Path):
    """Five records, five `still_bound: false`, and nothing had been edited.

    Measured on a benchmark run, 2026-08-31. A variant is several rows, so a column
    like `genotype` has several current values, and `current_value` renders them
    joined — `"C/C, C/T, T/T"`. That joined string is the only value this surface ever
    shows for such a record, and recording it back verbatim used to hash to nothing,
    because `bound_to` was asked one cell at a time. The queue then reported the signal
    it calls *the one to read first* — the authored cell was edited again — over a file
    nobody had touched. The proof was arithmetic: the stored `value_sha256` was
    byte-identical to the digest of the rendering the same call printed.
    """
    rendered = "C/C, C/T, T/T"
    overrides.upsert(module, _record(field="genotype", authored_value=rendered))
    entry = overrides.review_queue(module)[0]
    assert entry.current_value == rendered, "the queue's own rendering changed"
    assert entry.still_bound is True, (
        f"still_bound={entry.still_bound!r} for the exact string the queue prints — "
        "recording back what the surface shows must not read as an edit nobody made"
    )
