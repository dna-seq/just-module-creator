"""Refreshing a derived sidecar: what survives, what is refused, what is recoverable.

Hermetic. The offline ceiling means no pass here reaches a source, and the tool
refuses outright when it is offline — so the classification half is exercised by
substituting the *pass invoker*, which is the network boundary, exactly as
`test_passes.py` substitutes `_run_pass` for a gnomAD outage. The transformation
under test is ours: capture, verify, delete, classify, reapply. The models, the
fact-field tuples and the signature functions are the real upstream ones
throughout, and every expectation is computed from them rather than pasted.
"""

from __future__ import annotations

import ast
import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import offline_settings
from fastmcp.exceptions import ToolError
from just_dna_compiler import hints
from just_dna_enricher.enrich import EnrichmentError
from just_dna_format.gene_validity import GeneValidityRow
from just_dna_format.integrity import resolution_signature
from just_dna_format.layout import DERIVED_SUBDIR, preferred_spelling
from just_dna_format.resolution import RESOLUTION_FACT_FIELDS, ResolutionRow
from just_dna_registry.specfiles import RECOGNIZED_SPEC_FILES, SOURCES_CSV

from just_module_creator.settings import Settings
from just_module_creator.tools import refresh as module
from just_module_creator.tools.refresh import (
    PENDING_CSV,
    PENDING_STATE,
    REFRESHABLE_ROSTER,
    ROSTER,
    UNPRODUCED,
    canonical,
    capture_dir,
    check_sidecar,
    check_use,
    subject_fields,
    subject_of,
)

# --------------------------------------------------------------------------- #
# Fixture data. Real rsIDs; the module fixture in conftest uses rs4988235.
# --------------------------------------------------------------------------- #
#: A resolution table as the enricher would have written it, plus one row a human
#: worked out by hand. `source` is the only column that separates them, and it is
#: outside `RESOLUTION_FACT_FIELDS` — so the two hash identically as facts.
ENSEMBL_ROW = {
    "variant_key": "rs4988235",
    "rsid": "rs4988235",
    "chrom": "2",
    "start": "135851076",
    "ref": "G",
    "alts": "A",
    "genome_build": "GRCh38",
    "locus_index": "0",
    "source": "ensembl",
    "status": "resolved",
}
MANUAL_ROW = {
    "variant_key": "rs1801133",
    "rsid": "rs1801133",
    "chrom": "1",
    "start": "11796321",
    "ref": "G",
    "alts": "A",
    "genome_build": "GRCh38",
    "locus_index": "0",
    "source": "manual",
    "status": "resolved",
}
#: Same subject as `ENSEMBL_ROW`, different coordinate: the shape of both an
#: upstream revision and an author's cell edit, which is why it is unresolvable.
REVISED_ROW = ENSEMBL_ROW | {"start": "135851077"}

HEADER = list(ENSEMBL_ROW)


def write_csv(path: Path, rows: list[dict[str, str]], header: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = header or HEADER
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, restval="")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(handle)]


class Died(Exception):
    """An unhandled failure inside the pass — nothing the tool knows how to catch.

    It is in none of the roster's `unavailable`/`error` tuples, so it escapes the
    tool body exactly as an unexpected crash would. What is under test is the
    state a run leaves ON DISK when it does not reach the reapply, which is the
    same state a killed process leaves.
    """


def fake_pass(rows: list[dict[str, str]], *, crash: str | None = None):
    """A stand-in for the network pass: writes the table a source would have given.

    Substituting here and nowhere else keeps the real models, the real fact
    tuples and the real signature functions in the path — only the fetch is
    replaced, which is what the offline ceiling forbids anyway.

    `crash="before"` dies with the sidecar deleted and nothing written;
    `crash="after"` dies with the fresh table on disk and the reapply still owed.
    Those are the two distinguishable states between the delete and the reapply.
    """

    def run(spec_dir, mode, offline, use, services):
        if crash == "before":
            raise Died("died after the delete, before the pass wrote anything")
        write_csv(spec_dir / "resolution.csv", rows)
        if crash == "after":
            raise Died("died after the pass wrote, before the reapply")

        class Result:
            skipped_offline = False

        return Result()

    return run


def _never_fetch(spec_dir, mode, offline, use, services):
    """The stand-in every pass gets while the offline ceiling is down.

    Hermetic by mechanism rather than by discipline: a test that lowers the
    ceiling and forgets to substitute the pass it exercises fails here instead of
    opening a socket.
    """
    raise AssertionError(
        "a pass ran for real with the offline ceiling down — substitute it in the test"
    )


@pytest.fixture
def online(tmp_path, monkeypatch) -> Settings:
    """Settings whose offline ceiling is DOWN, with every roster pass neutralized.

    `refresh_sidecar` refuses offline on purpose, so a test of the classification
    has to say it is online. `_never_fetch` is what keeps that safe; the test then
    substitutes the one pass it means to exercise.

    The workspace is `tmp_path`, which contains the `spec_dir` fixture — so the
    captures land under `tmp_path` too rather than in the developer's cache.
    """
    for name, sidecar in list(module.ROSTER.items()):
        monkeypatch.setitem(
            module.ROSTER,
            name,
            replace(
                sidecar,
                passes=tuple(replace(step, run=_never_fetch) for step in sidecar.passes),
            ),
        )
    # Not `offline_settings`, which forces the ceiling up. The autouse hermetic
    # fixture still points `env_file` at nothing and clears the environment, so
    # this reads no developer configuration.
    # `_env_file` is a pydantic-settings init kwarg, absent from the generated
    # __init__ signature, so pyright cannot see it — same note as `offline_settings`.
    return Settings(
        offline=False,
        api_key=None,
        workspace=str(tmp_path),
        _env_file=None,  # type: ignore[call-arg]
    )


def patch_resolution_pass(monkeypatch, run) -> None:
    """Point `resolution.csv`'s single pass at `run`, leaving the roster shape alone."""
    sidecar = module.ROSTER["resolution.csv"]
    monkeypatch.setitem(
        module.ROSTER,
        "resolution.csv",
        replace(sidecar, passes=(replace(sidecar.passes[0], run=run),)),
    )


# --------------------------------------------------------------------------- #
# Row identity is derived, not written down
# --------------------------------------------------------------------------- #
def test_the_subject_key_is_the_one_the_writing_pass_merges_on() -> None:
    """Row identity is upstream's merge key since 0.6.5, not an approximation of it.

    What stood here recomputed the format's fact tuple narrowed to the required columns,
    which is what `S51` was filed about: it was *different* on the two tables where one
    subject legitimately carries several rows. Both are asserted by name because both
    were wrong in a way that changed what the tool reported — `clinical_assertions.csv`
    keyed on `dataset` collapsed two ClinVar assertions on one variant into one subject
    and called them a conflict, and `gene_validity.csv` keyed on `(gene, dataset)` did the
    same to two ClinGen curations of one gene.
    """
    for csv_name in ROSTER:
        key = hints.key_fields(csv_name)
        assert key is not None, f"{csv_name} declares no merge key"
        assert subject_fields(ROSTER[csv_name]) == tuple(key.columns)

    assert subject_fields(ROSTER["clinical_assertions.csv"]) == ("variant_key", "variation_id")
    assert subject_fields(ROSTER["gene_validity.csv"]) == ("assertion_id",)


def test_a_two_level_key_falls_back_rather_than_making_every_row_one_subject() -> None:
    """`gene_validity.csv` keys on `assertion_id` and a hand-written row has none.

    Reducing such a row over the absent column alone leaves `{}` — every id-less
    curation the same subject, so the first one captured would answer for all of them.
    The fallback level is upstream's own (`TableKey.fallback`), and this is the row shape
    it exists for.
    """
    key = hints.key_fields("gene_validity.csv")
    assert key is not None and key.fallback
    rows = [
        GeneValidityRow(
            gene=gene,
            disease_id="MONDO:0007739",
            classification="definitive",
            dataset="clingen",
            source="clingen",
        )
        for gene in ("HFE", "MLH1")
    ]
    assert all(row.assertion_id is None for row in rows)
    subjects = {subject_of(row, key) for row in rows}
    assert len(subjects) == 2, "two id-less curations of different genes are two subjects"


def test_provenance_moves_no_fact_signature_which_is_why_source_is_the_only_proof() -> None:
    """The premise the whole classification rests on, asserted rather than assumed.

    `source` sits outside every fact set but `sources.csv`'s, so a hand-authored
    row and a fetched row with identical facts are the SAME fact. That is what
    makes `source` the one column able to prove who wrote a row — and what makes
    fact equality unable to.
    """
    fetched = ResolutionRow.model_validate(ENSEMBL_ROW)
    by_hand = ResolutionRow.model_validate(ENSEMBL_ROW | {"source": "manual"})

    assert "source" not in RESOLUTION_FACT_FIELDS
    assert resolution_signature([fetched]) == resolution_signature([by_hand])
    assert canonical(fetched, RESOLUTION_FACT_FIELDS) == canonical(
        by_hand, RESOLUTION_FACT_FIELDS
    )
    assert fetched.source != by_hand.source


def test_the_roster_covers_every_public_sidecar_or_says_why_not() -> None:
    """An eighth fact table must fail this suite, not be silently unrefreshable."""
    assert set(ROSTER) | UNPRODUCED == set(REFRESHABLE_ROSTER) | UNPRODUCED
    assert set(REFRESHABLE_ROSTER) - set(ROSTER) == {SOURCES_CSV}
    for name, sidecar in ROSTER.items():
        assert sidecar.csv == name
        assert sidecar.passes, f"{name} is in the roster with no pass to re-derive it"
        assert sidecar.fact_fields
        # Every roster member is a file the registry recognises, in some spelling.
        assert any(
            spelling in RECOGNIZED_SPEC_FILES for spelling in (name, preferred_spelling(name))
        )


def test_gene_metrics_runs_both_of_its_producers() -> None:
    """Two passes write this one file, and re-deriving with one rebuilds half a table.

    `enrich_dosage_sensitivity` puts ClinGen's haploinsufficiency and
    triplosensitivity onto `gene_metrics.csv` rather than a file of its own, so a
    refresh that ran only the constraint pass would report every dosage row as one
    the source had withdrawn.
    """
    names = [p.name for p in ROSTER["gene_metrics.csv"].passes]
    assert names == ["enrich_gene_metrics", "enrich_dosage_sensitivity"]
    licensed = [p.name for p in ROSTER["gene_metrics.csv"].passes if p.reads_licence_bearing_source]
    assert licensed == ["enrich_dosage_sensitivity"]


# --------------------------------------------------------------------------- #
# The refusals
# --------------------------------------------------------------------------- #
def test_licensing_is_refused_with_the_reason_rather_than_attempted() -> None:
    """No pass derives it, so deleting it would discard the whole declaration."""
    for spelling in (SOURCES_CSV, preferred_spelling(SOURCES_CSV)):
        with pytest.raises(ToolError) as excinfo:
            check_sidecar(spelling)
        message = str(excinfo.value)
        assert "no pass derives this table" in message
        assert "compile gate" in message


def test_an_unknown_sidecar_names_the_refreshable_ones() -> None:
    with pytest.raises(ToolError) as excinfo:
        check_sidecar("variants.csv")
    message = str(excinfo.value)
    for name in ROSTER:
        assert name in message


def test_use_is_required_exactly_where_a_pass_reads_a_licence() -> None:
    """Never defaulted: 'unstated' silently skips, anything else asserts a position."""
    with pytest.raises(ToolError) as excinfo:
        check_use(ROSTER["gene_metrics.csv"], None)
    assert "enrich_dosage_sensitivity" in str(excinfo.value)

    with pytest.raises(ToolError):
        check_use(ROSTER["gwas_effects.csv"], None)

    # A sidecar whose passes read no licence needs none, and says so by omission.
    assert check_use(ROSTER["resolution.csv"], None) == "unstated"
    assert check_use(ROSTER["gene_metrics.csv"], "NON-COMMERCIAL") == "non_commercial"
    with pytest.raises(ToolError):
        check_use(ROSTER["gene_metrics.csv"], "free")


async def test_offline_refuses_before_anything_is_touched(make_client, spec_dir) -> None:
    """A cache-relative refresh answers a different question, so it does not run.

    And the file has to be exactly where it was afterwards: the refusal is only
    honest if nothing was deleted on the way to it.
    """
    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    before = original.read_bytes()

    async with make_client("extended", offline_settings(workspace=str(spec_dir.parent))) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is False
    assert data.offline is True
    assert data.refused is not None and "Offline" in data.refused
    assert original.read_bytes() == before
    assert data.capture is None


async def test_a_sidecar_that_does_not_validate_is_refused_before_the_delete(
    make_client, online, spec_dir, tmp_path
) -> None:
    """A file this tool cannot classify is a file it will not delete."""
    original = spec_dir / "resolution.csv"
    original.write_text("variant_key,start\nrs4988235,not-a-number\n", encoding="utf-8")
    before = original.read_bytes()

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is False
    assert data.capture is None and data.capture_verified is False
    assert original.read_bytes() == before, "an unclassifiable sidecar must not be deleted"
    assert any(f.level == "error" for f in data.findings)


# --------------------------------------------------------------------------- #
# The three the task names
# --------------------------------------------------------------------------- #
async def test_a_captured_override_survives_a_refresh(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """The whole point: a hand-worked row is still there after the file is re-derived.

    The source is made to return only its own row, so the manual row's subject is
    absent from the fresh table and its `source` proves a human wrote it — the one
    combination that is put back.
    """
    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW]))

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is True
    assert data.restored is False
    assert [row.source for row in data.reapplied] == ["manual"]
    assert data.reapplied[0].source_proves_authored is True
    assert data.withheld == []
    assert data.conflicts == []
    # On disk, not merely in the report.
    keys = {row["variant_key"] for row in read_csv(original)}
    assert keys == {ENSEMBL_ROW["variant_key"], MANUAL_ROW["variant_key"]}
    # And the reapplied cells are the ones that were captured, verbatim.
    restored = next(r for r in read_csv(original) if r["source"] == "manual")
    assert {k: restored[k] for k in MANUAL_ROW} == MANUAL_ROW
    # The fact signature is unchanged, because the table's facts are unchanged.
    assert data.signature_moved is False
    # The reported capture must EXIST. It said `pending.csv` until the in-flight
    # copy was renamed into the audit trail on success — a path in a report that
    # is not on disk is worse than no path, because it reads as recoverable.
    assert data.capture is not None and Path(data.capture).is_file()
    assert Path(data.capture).name != PENDING_CSV


async def test_an_ambiguous_row_is_reported_and_never_resolved(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """Same subject, different facts: an author's edit and a revision look alike.

    So neither side is preferred, nothing is merged, and the file keeps exactly
    what the source now says while the captured version stays readable in the
    capture. The report names the differing fact column.
    """
    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW])
    patch_resolution_pass(monkeypatch, fake_pass([REVISED_ROW]))

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is True
    assert len(data.conflicts) == 1
    conflict = data.conflicts[0]
    assert conflict.differing_fact_fields == ["start"]
    assert [r.cells["start"] for r in conflict.captured] == [ENSEMBL_ROW["start"]]
    assert [r.cells["start"] for r in conflict.rederived] == [REVISED_ROW["start"]]
    assert "cannot tell those apart" in conflict.unresolvable
    # Not resolved: nothing was reapplied, nothing was merged, one row on disk.
    assert data.reapplied == [] and data.only_in_capture == []
    on_disk = read_csv(original)
    assert len(on_disk) == 1 and on_disk[0]["start"] == REVISED_ROW["start"]
    # A moved signature with no reapplied row is the canary this tool exists for.
    assert data.signature_moved is True
    assert any("LEFT ALONE" in w for w in data.warnings)


async def test_a_crash_between_delete_and_reapply_leaves_the_capture_recoverable(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """The durability claim, exercised by actually dying mid-cycle.

    The capture is written and hashed BEFORE the delete, so a process that stops
    after the delete has already lost nothing — and a re-run continues from the
    capture rather than capturing over it, which is what makes the second attempt
    a repair instead of a second loss.
    """
    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    captured_bytes = original.read_bytes()
    settings = online
    directory = capture_dir(settings, spec_dir.resolve(), "resolution.csv")

    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW], crash="after"))
    async with make_client("extended", settings) as client:
        with pytest.raises(ToolError, match="died"):
            await client.call_tool(
                "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
            )

    # The author's rows are recoverable from disk with no tool at all.
    pending = directory / PENDING_CSV
    assert pending.is_file(), "a capture that does not survive the crash is not insurance"
    assert pending.read_bytes() == captured_bytes
    state = json.loads((directory / PENDING_STATE).read_text())
    assert state["read_from"] == str(original)
    assert state["fact_signature"].startswith("sha256:")

    # A re-run continues from it rather than capturing the half-derived file over it.
    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW]))
    async with make_client("extended", settings) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.resumed is True
    assert [row.source for row in data.reapplied] == ["manual"]
    keys = {row["variant_key"] for row in read_csv(original)}
    assert keys == {ENSEMBL_ROW["variant_key"], MANUAL_ROW["variant_key"]}
    # The capture is retired into the audit trail, never deleted.
    assert not pending.is_file()
    assert [p.name for p in directory.glob("*.csv")], "the audit copy must be kept"


async def test_a_crash_before_the_pass_wrote_anything_resumes_by_re_deriving(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """The other half of the window: deleted, nothing written, process gone.

    Here there is no fresh table to classify, so the resume runs the pass. What
    must not happen is the second run capturing the *absence* over a good capture,
    which would be the loss the capture exists to prevent.
    """
    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    captured_bytes = original.read_bytes()
    settings = online
    directory = capture_dir(settings, spec_dir.resolve(), "resolution.csv")

    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW], crash="before"))
    async with make_client("extended", settings) as client:
        with pytest.raises(ToolError, match="died"):
            await client.call_tool(
                "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
            )

    assert not original.exists(), "the delete is what makes this the dangerous window"
    assert (directory / PENDING_CSV).read_bytes() == captured_bytes

    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW]))
    async with make_client("extended", settings) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.resumed is True
    assert data.passes_run == ["enrich"], "with nothing on disk the pass has to run"
    assert {row["variant_key"] for row in read_csv(original)} == {
        ENSEMBL_ROW["variant_key"],
        MANUAL_ROW["variant_key"],
    }


# --------------------------------------------------------------------------- #
# Degrading honestly
# --------------------------------------------------------------------------- #
async def test_an_empty_re_derivation_restores_rather_than_reporting_a_withdrawal(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """A table that was never filled would report every real row as withdrawn."""
    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    before = original.read_bytes()
    patch_resolution_pass(monkeypatch, fake_pass([]))

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is False
    assert data.restored is True
    assert data.refused is not None and "EMPTY" in data.refused
    # The restoration sentence is appended from what the restore actually did, not
    # baked into the message before it ran — on a module with no prior sidecar the
    # same refusal has to say the opposite.
    assert "restored exactly as it was" in data.refused
    assert original.read_bytes() == before, "the captured bytes must go back verbatim"
    assert data.only_in_capture == [] and data.conflicts == []


async def test_an_unreachable_source_restores_and_is_told_apart_from_a_failure(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """`unavailable` and `error` are different answers; both leave the file intact."""
    from just_dna_enricher.identifiers import IdentifierUnavailable

    original = spec_dir / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    before = original.read_bytes()

    def outage(spec_dir_, mode, offline, use, services):
        raise IdentifierUnavailable("Ensembl returned 503")

    patch_resolution_pass(monkeypatch, outage)
    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is False and data.restored is True
    assert data.refused is not None and "never answered" in data.refused
    assert original.read_bytes() == before


async def test_a_row_whose_source_proves_nothing_is_withheld_not_reapplied(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """A vanished row with a fetcher-valued `source` may be one the source withdrew.

    Nothing separates that from an authored addition, so it is reported and left
    out — and the capture is named so it can be put back by hand.
    """
    original = spec_dir / "resolution.csv"
    withdrawn = MANUAL_ROW | {"source": "ensembl"}
    write_csv(original, [ENSEMBL_ROW, withdrawn])
    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW]))

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is True
    assert data.reapplied == []
    assert [row.source for row in data.withheld] == ["ensembl"]
    assert data.withheld[0].source_proves_authored is False
    assert len(read_csv(original)) == 1
    assert data.capture is not None and Path(data.capture).parent.is_dir()


async def test_a_derived_layout_is_not_migrated_by_a_refresh(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """Write to the file you read: a module keeping sidecars under `derived/` keeps it.

    With the original deleted, `sidecar_write_path` creates the file at the spec
    root — right for a fresh file and wrong here, so it is moved back.
    """
    original = spec_dir / DERIVED_SUBDIR / "resolution.csv"
    write_csv(original, [ENSEMBL_ROW, MANUAL_ROW])
    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW]))

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is True
    assert data.read_from == str(original)
    assert original.is_file(), "the sidecar must stay where the module kept it"
    # Two copies of one sidecar is the collision `resolve_sidecar` refuses outright.
    assert not (spec_dir / "resolution.csv").exists()
    keys = {row["variant_key"] for row in read_csv(original)}
    assert keys == {ENSEMBL_ROW["variant_key"], MANUAL_ROW["variant_key"]}


async def test_a_module_with_no_sidecar_yet_is_a_plain_derivation(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """Nothing to capture means nothing at risk, and it must not read as a refresh."""
    patch_resolution_pass(monkeypatch, fake_pass([ENSEMBL_ROW]))

    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is True
    assert data.capture is None and data.rows_before is None
    assert data.signature_moved is None, "no before means no comparison, never a 'no'"
    assert "nothing was at risk" in data.next_step


# --------------------------------------------------------------------------- #
# Tiering, stamping, and the structural guard
# --------------------------------------------------------------------------- #
async def test_refresh_is_in_every_tier_and_the_gate_moved_to_the_sidecar(make_client) -> None:
    """Cost, not usefulness — but the cost is per sidecar, not per tool (2026-08-22).

    It was extended-only because it can run the pass measured at 382 requests. True
    of two of the seven entries; the other five are bounded by the rows you wrote,
    and gating the tool gated those too. Two unattended runs then each reported that
    nothing re-derives a stale sidecar and that `rm resolution.csv` is the sanctioned
    interface — the run's own highest-value action, spelled as a delete because the
    tool that does it with a verified capture was invisible to them.
    """
    async with make_client("essentials", offline_settings()) as client:
        assert "refresh_sidecar" in {t.name for t in await client.list_tools()}
    async with make_client("extended", offline_settings()) as client:
        assert "refresh_sidecar" in {t.name for t in await client.list_tools()}


def test_the_corpus_sized_sidecars_are_the_ones_whose_pass_is_extended() -> None:
    """Two independent producers, so the marker cannot quietly disagree with the tier.

    `Sidecar.corpus_sized` is hand-set beside each entry; `EXTENDED_ONLY` in
    `test_modes_and_auth` is the tool roster. A sidecar marked corpus-sized whose
    pass is NOT gated as a tool would be friction with nothing behind it, and the
    reverse would be the budget door the old tiering existed to shut.
    """
    from just_module_creator.tools.refresh import ROSTER

    marked = {csv for csv, sidecar in ROSTER.items() if sidecar.corpus_sized}
    assert marked == {"literature.csv", "gwas_effects.csv"}
    # And every unmarked one really is reachable in the default tier.
    for name, sidecar in ROSTER.items():
        if name not in marked:
            assert check_sidecar(name, mode="essentials") is sidecar
    for name in marked:
        with pytest.raises(ToolError, match="extended"):
            check_sidecar(name, mode="essentials")


async def test_the_answer_names_the_toolchain_that_derived_the_row_identity(
    make_client, spec_dir
) -> None:
    """`fact_fields` and `subject_fields` are generated, so RM13's stamp travels.

    A stale process would classify rows against an old fact set and answer with
    the same confidence as a current one; nothing else in the payload says which
    release produced the identity.
    """
    from importlib import metadata

    async with make_client("extended", offline_settings(workspace=str(spec_dir.parent))) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.produced_by.format_version == metadata.version("just-dna-format")
    assert data.produced_by.compiler_version == metadata.version("just-dna-compiler")
    # Reported even on a refusal: the identity it *would* have used is the thing
    # a caller checks when the answer surprises them.
    assert data.fact_fields == list(RESOLUTION_FACT_FIELDS)
    assert data.subject_fields == list(subject_fields(ROSTER["resolution.csv"]))


def test_no_except_arm_in_this_module_is_shadowed_by_an_earlier_one() -> None:
    """The 0.6.2 failure, checked here too: an outage arm dead behind its parent.

    A copy rather than a shared helper on purpose — `test_passes.py` owns the
    version that walks `passes.py`, and importing across test modules would couple
    two files that are edited independently. The check is twelve lines.
    """
    path = Path(module.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    shadowed: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        seen: list[str] = []
        for handler in node.handlers:
            names = (
                [ast.unparse(e) for e in handler.type.elts]
                if isinstance(handler.type, ast.Tuple)
                else [ast.unparse(handler.type)]
                if handler.type is not None
                else ["BaseException"]
            )
            for caught in names:
                for earlier in seen:
                    if _catches(earlier, caught):
                        shadowed.append(
                            f"line {handler.lineno}: `except {caught}` is already caught by "
                            f"the earlier `except {earlier}`"
                        )
            seen.extend(names)
    assert not shadowed, shadowed


def _catches(earlier: str, caught: str) -> bool:
    """Whether an earlier arm's class already catches a later arm's, by real classes.

    `step.unavailable` / `step.error` are attribute expressions, so they resolve to
    the set of classes any roster entry can put there — any of which may be raised.
    """
    table = {
        "step.unavailable": tuple(
            exc for s in ROSTER.values() for p in s.passes for exc in p.unavailable
        ),
        "step.error": tuple(exc for s in ROSTER.values() for p in s.passes for exc in p.error),
    }

    def resolve(expr: str) -> tuple[type, ...]:
        if expr in table:
            return table[expr]
        found = getattr(module, expr, None)
        return (found,) if isinstance(found, type) else ()

    kids, parents = resolve(caught), resolve(earlier)
    return bool(kids) and bool(parents) and all(
        any(issubclass(k, p) for p in parents) for k in kids
    )


def test_the_shadow_guard_can_actually_report_one() -> None:
    """A guard reporting zero proves nothing until it is shown able to report one."""
    from just_dna_enricher.frequencies import FrequencyEnrichmentError, FrequencyUnavailable

    assert _catches("FrequencyEnrichmentError", "FrequencyUnavailable")
    assert not _catches("FrequencyUnavailable", "FrequencyEnrichmentError")
    assert issubclass(FrequencyUnavailable, FrequencyEnrichmentError)


async def test_a_refusal_never_claims_a_restoration_that_did_not_happen(
    make_client, online, spec_dir, tmp_path, monkeypatch
) -> None:
    """No prior sidecar plus a failed pass: there is nothing to put back, and it says so.

    The restoration sentence is appended after `_restore` returns rather than
    written into the refusal, because the message is built before the restore runs
    and would be plainly false here — a refusal that overstates what happened is
    worse than a terse one.
    """
    def outage(spec_dir_, mode, offline, use, services):
        raise EnrichmentError("Ensembl returned 503")

    patch_resolution_pass(monkeypatch, outage)
    async with make_client("extended", online) as client:
        result = await client.call_tool(
            "refresh_sidecar", {"spec_dir": str(spec_dir), "sidecar": "resolution.csv"}
        )
    data = result.data

    assert data.success is False
    assert data.restored is False
    assert data.refused is not None
    assert "no prior file to restore" in data.refused
    assert "restored exactly as it was" not in data.refused
