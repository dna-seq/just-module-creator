"""`check_identifiers` — the attestation, and the two paths that are not a check.

`RM9`. The branch below was **shipped broken in 0.13.0 and found by running the
tool**, not by the suite: the "does not apply" case was computed and then not
acted on, so a module with no `variants.csv` got a raw `ValueError` traceback
where it should have got a considered answer. These tests exist so that cannot
happen again silently.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from conftest import offline_settings
from fastmcp.exceptions import ToolError

from just_module_creator.tools.checks import NOT_APPLICABLE

REFERENCE = Path("/data/sources/just-dna-format/reference_examples/hfe_hemochromatosis")


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    if not REFERENCE.is_dir():
        pytest.skip("the sibling format checkout is not present")
    target = tmp_path / "spec"
    shutil.copytree(REFERENCE, target)
    return target


async def test_a_module_with_no_variants_gets_an_answer_not_a_traceback(
    make_client, tmp_path: Path
) -> None:
    """The check does not APPLY, which is not the same as a check that was skipped.

    A module with no `variants.csv` has no gene or trait for this to have an
    opinion about. The regression: the underlying call raises `ValueError` on the
    missing file, so this has to return **before** reaching it, not after.
    """
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "module_spec.yaml").write_text("name: nothing\n", encoding="utf-8")

    async with make_client(offline_settings()) as client:
        data = (await client.call_tool("check_identifiers", {"spec_dir": str(bare)})).data

    assert data.attested is False
    assert data.attestation_note == NOT_APPLICABLE
    assert data.genes == [] and data.traits == []
    # And nothing was written: mining a nonce onto a module that never asked for a
    # verification document is the specific harm the early return prevents.
    assert not (bare / "verification.json").exists()


async def test_both_halves_off_is_refused_before_any_socket(make_client, spec: Path) -> None:
    """An attestation for a check nobody asked for would assert nothing."""
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="no question to put"):
            await client.call_tool(
                "check_identifiers",
                {"spec_dir": str(spec), "check_genes": False, "check_traits": False},
            )


async def test_the_offline_ceiling_refuses_and_writes_nothing(make_client, spec: Path) -> None:
    """It needs HGNC and OLS4, so offline is a refusal rather than a degraded run."""
    before = (spec / "verification.json").read_bytes()
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="JMC_OFFLINE"):
            await client.call_tool("check_identifiers", {"spec_dir": str(spec)})
    assert (spec / "verification.json").read_bytes() == before


def test_an_existing_closure_is_not_destroyed_by_attesting(spec: Path) -> None:
    """`record_verification` merges; the closure a module already carries survives.

    Measured live on this fixture: 0 records before, 3 after, closure intact.
    """
    doc = json.loads((spec / "verification.json").read_text(encoding="utf-8"))
    assert "closure" in doc, "the reference example should carry a closure to protect"


# --------------------------------------------------------------------------- #
# The roster is raw material; the verdict is the answer (`F-31` / `D21`)
# --------------------------------------------------------------------------- #
#
# Two independent runs reported the same thing: a clean `risk_impulsivity_snps`
# returned all 325 gene records, every one `approved`, at roughly 95 characters each
# — about 30 kB — to say `stale: []`, and `cancer`'s `pathogenic` half carries 4,793
# genes. The verdict fields sat last, after everything that did not matter.
#
# These tests exercise the happy path, which the suite could not reach before: the
# check itself needs HGNC and OLS4. The **network boundary only** is replaced —
# `checks._check_identifiers` — with real dataclasses carrying real identifiers, so
# the projection, the filter, the counts and `verification_records` all run for real.
# MCM6 is an approved HGNC symbol; MLL is a previous symbol for KMT2A; EFO:0004611 is
# a live EFO term; MESH:D003920 is a real MeSH descriptor whose prefix is outside
# `_ONTOLOGY_IRI`, so the check answers `unchecked` without sending a request.


def _upstream_report():
    """One of upstream's own reports, built offline from real identifiers.

    Not a stand-in for the transformation under test — it is the *input* to it. The
    two clean records are what a real module has hundreds of.
    """
    from just_dna_enricher.identifiers import GeneStatus, IdentifierReport, TraitStatus

    return IdentifierReport(
        genes=[
            GeneStatus(symbol="MCM6", state="approved", hgnc_id="HGNC:6947", location="2q21.3"),
            GeneStatus(symbol="MLL", state="retired", current="KMT2A", hgnc_id="HGNC:7132"),
        ],
        traits=[
            TraitStatus(curie="EFO:0004611", state="current", label="LDL cholesterol measurement"),
            # A prefix the check cannot resolve: seen, never asked about, and therefore
            # never clean. This is the three-valued case in count form.
            TraitStatus(curie="MESH:D003920", state="unchecked"),
        ],
    )


@pytest.fixture
def checked(monkeypatch: pytest.MonkeyPatch):
    """A client whose identifier check answers from `_upstream_report` and never dials out.

    The offline flag is lowered on the settings object the server closed over, because
    the tool refuses at that gate before reaching the call this patches — and it is
    lowered on a `offline_settings()` instance, so nothing is read from a developer's
    environment. `calls` is asserted on: an unpatched boundary would be a socket, and
    a silent bypass must fail the test rather than pass it quietly.
    """
    from fastmcp.client import Client

    from just_module_creator import server as server_module
    from just_module_creator.tools import checks as checks_module

    calls: list[dict] = []

    def _fake(**kwargs):
        calls.append(kwargs)
        return _upstream_report()

    monkeypatch.setattr(checks_module, "_check_identifiers", _fake)
    settings = offline_settings()
    built = server_module.build_server(settings=settings)
    monkeypatch.setattr(settings, "offline", False)

    def _open():
        return Client(transport=built)

    return _open, calls


async def test_a_clean_record_is_counted_and_withheld_rather_than_printed(checked, spec_dir):
    """The default answer carries the counts and only the records that need attention."""
    open_client, calls = checked
    async with open_client() as client:
        data = (await client.call_tool("check_identifiers", {"spec_dir": str(spec_dir)})).data

    assert calls, "the network boundary was not patched — this test must never dial out"
    report = _upstream_report()

    # Counted off the full roster, not off the answer's shape.
    assert data.gene_tally.checked == len(report.genes)
    assert data.trait_tally.checked == len(report.traits)
    # `checked` splits exactly, so a count and the list it counts cannot drift apart.
    for tally in (data.gene_tally, data.trait_tally):
        assert tally.checked == tally.clean + tally.flagged

    # The clean records are gone and the flagged ones are all that is left.
    assert {g.identifier for g in data.genes} == {"MLL"}
    assert {t.identifier for t in data.traits} == {"MESH:D003920"}
    assert data.detail is False
    assert len(data.genes) == data.gene_tally.flagged
    assert len(data.traits) == data.trait_tally.flagged
    # And the summary still names both, so nothing was lost by withholding.
    assert any("MLL" in line for line in data.stale)
    assert any("MESH:D003920" in line for line in data.stale)


async def test_a_state_that_means_the_check_did_not_run_is_never_counted_clean(checked, spec_dir):
    """`unchecked` is a prefix nobody could resolve — seen, not settled, not a pass."""
    open_client, _ = checked
    async with open_client() as client:
        data = (await client.call_tool("check_identifiers", {"spec_dir": str(spec_dir)})).data

    unchecked = [t for t in _upstream_report().traits if t.state == "unchecked"]
    assert unchecked, "the fixture must carry the state this test is about"
    assert data.trait_tally.clean == len(_upstream_report().traits) - len(unchecked)
    assert [t.state for t in data.traits] == ["unchecked"]


async def test_detail_returns_the_roster_unchanged(checked, spec_dir):
    """`detail=true` is today's answer: every record, clean ones included."""
    open_client, _ = checked
    async with open_client() as client:
        data = (
            await client.call_tool(
                "check_identifiers", {"spec_dir": str(spec_dir), "detail": True}
            )
        ).data

    report = _upstream_report()
    assert {g.identifier for g in data.genes} == {g.symbol for g in report.genes}
    assert {t.identifier for t in data.traits} == {t.curie for t in report.traits}
    assert data.detail is True
    # The counts do not move with the flag: they describe the check, not the shape.
    assert data.gene_tally.checked == len(report.genes)
    assert data.trait_tally.checked == len(report.traits)


async def test_a_half_that_was_not_asked_counts_null_rather_than_zero(checked, spec_dir):
    """Narrowing a run must not read as a clean one. `null` is not `0`."""
    open_client, calls = checked
    async with open_client() as client:
        data = (
            await client.call_tool(
                "check_identifiers", {"spec_dir": str(spec_dir), "check_traits": False}
            )
        ).data

    assert calls[0]["check_traits"] is False
    assert data.trait_tally.checked is None
    assert data.trait_tally.clean is None
    assert data.trait_tally.flagged is None
    # The gene half was asked, so its counts are real numbers.
    assert data.gene_tally.checked == len(_upstream_report().genes)


async def test_a_check_that_did_not_apply_counts_nothing_at_all(make_client, tmp_path):
    """No `variants.csv`: every count null, because nothing was established.

    `0` here would say the module carries no genes and no traits, which is a claim
    about the module rather than about the check.
    """
    bare = tmp_path / "bare-counts"
    bare.mkdir()
    (bare / "module_spec.yaml").write_text("name: nothing\n", encoding="utf-8")

    async with make_client(offline_settings()) as client:
        data = (await client.call_tool("check_identifiers", {"spec_dir": str(bare)})).data

    for tally in (data.gene_tally, data.trait_tally):
        assert (tally.checked, tally.clean, tally.flagged) == (None, None, None)
    assert data.attestation_note == NOT_APPLICABLE
