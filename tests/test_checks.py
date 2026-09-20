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


async def test_every_half_off_is_refused_before_any_socket(make_client, spec: Path) -> None:
    """An attestation for a check nobody asked for would assert nothing.

    **Three halves now, and the count is load-bearing rather than cosmetic.** This test
    passed `check_genes=False, check_traits=False` and asserted the refusal while the PGS
    leg was already running on upstream's `check_pgs=True` default — so it was asserting
    *nothing to ask* about a call that still had a registry to put a question to. Turning
    two of three off is a narrowed run, not an empty one.
    """
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError, match="no question to put"):
            await client.call_tool(
                "check_identifiers",
                {
                    "spec_dir": str(spec),
                    "check_genes": False,
                    "check_traits": False,
                    "check_pgs": False,
                },
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
    from just_dna_enricher.identifiers import (
        GeneStatus,
        IdentifierReport,
        PgsComparison,
        PgsDrift,
        PgsStatus,
        TraitStatus,
    )

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
        # The third half, which ran on upstream's `check_pgs=True` default and reached
        # no field of ours until 0.31.3. `PGS000027` is a real Catalog accession;
        # `PGS999999` is shape-valid and the Catalog holds nothing under it, which is
        # the finding a shape check cannot make.
        pgs=[
            PgsStatus(
                pgs_id="PGS000027",
                state="known",
                name="GRS53",
                date_release="2020-04-30",
                trait_efo_ids=("EFO:0004611",),
                variants_number=53,
                license="Not specified",
            ),
            PgsStatus(pgs_id="PGS999999", state="unrecognised"),
        ],
        pgs_release="2026-08-01",
        pgs_metadata=PgsComparison(
            drift=[
                PgsDrift(
                    pgs_id="PGS000027",
                    field_name="variants_number",
                    authored="52",
                    published="53",
                )
            ],
            # `compared` is the roster of what was put to the Catalog, not a count —
            # `(pgs_id, field, value)` triples, and pyright caught the assumption.
            compared=[("PGS000027", "variants_number", "53")],
        ),
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


async def test_the_pgs_half_reaches_the_caller_rather_than_only_the_attestation(
    checked, spec_dir
):
    r"""It was running and reporting to nobody, which is worse than not running.

    Upstream's `check_identifiers` takes `check_pgs=True` and `verification_records`
    writes a PGS record on the same default — so a module was being attested as having
    had its accessions checked while the answer reached no field here. An attestation for
    a check whose result the caller never sees is the vacuous-green shape the rulebook
    is about, one layer up: the record is true and the module still tells you nothing.

    `unrecognised` is the finding the shape check cannot make — `^PGS\d+$` passes on an
    accession the Catalog holds no score under.
    """
    open_client, _ = checked
    async with open_client() as client:
        data = (await client.call_tool("check_identifiers", {"spec_dir": str(spec_dir)})).data

    assert data.pgs_tally.checked == 2
    assert data.pgs_tally.clean == 1, "`known` is the clean state; `unrecognised` is not"
    assert data.pgs_tally.flagged == 1
    # Withheld like the other two halves: only what needs attention on a default run.
    assert [s.identifier for s in data.pgs] == ["PGS999999"]
    assert any("PGS999999" in line for line in data.stale)
    # Drift is named with both values and never applied — the Catalog re-releases.
    assert len(data.pgs_drift) == 1
    assert "PGS000027" in data.pgs_drift[0] and "variants_number" in data.pgs_drift[0]
    assert "'52'" in data.pgs_drift[0] and "'53'" in data.pgs_drift[0]
    # The release makes a drift line re-checkable later.
    assert data.pgs_release == "2026-08-01"
    # Null, not a sentence: the half ran.
    assert data.pgs_check_skipped is None


async def test_a_narrowed_pgs_run_counts_null_rather_than_zero(checked, spec_dir):
    """`check_pgs=False` must say *not asked*, never *nothing found*."""
    open_client, calls = checked
    async with open_client() as client:
        data = (
            await client.call_tool(
                "check_identifiers", {"spec_dir": str(spec_dir), "check_pgs": False}
            )
        ).data

    assert calls[-1]["check_pgs"] is False, "the flag never reached upstream"
    assert data.pgs_tally.checked is None
    assert data.pgs_tally.clean is None


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


# --------------------------------------------------------------------------- #
# The three catalogue checks wrapped in 0.35.0
# --------------------------------------------------------------------------- #
async def test_acmg_on_a_module_with_no_variants_is_not_applicable_rather_than_clean(
    make_client, tmp_path: Path
) -> None:
    """Same shape as `check_identifiers`, and it is the shape that ships broken.

    A module with no `variants.csv` states no `acmg_sf`, so there is nothing to have
    an opinion about — and `clean=true` would be the tool saying every stated value
    agrees when none was read. Null throughout is the honest answer.
    """
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("check_acmg", {"spec_dir": str(spec_dir)})).data

    assert report.clean is None, "a check that could not run is not a check that passed"
    assert report.checked is None, "null is not zero — nothing was established"
    assert report.version is None
    assert report.attested is False
    assert report.attestation_note == NOT_APPLICABLE
    assert not (spec_dir / "verification.json").exists(), (
        "a check that does not apply must not mint a verification.json"
    )


async def test_repeat_bands_on_a_module_with_no_repeat_table_says_which_tool_writes_one(
    make_client, tmp_path: Path
) -> None:
    """The refusal routes somewhere rather than stopping at "no".

    `draft_from_strchive` writes `repeat_alleles.csv` from the same catalogue this
    would check it against, and naming it is the difference between a dead end and a
    next step — the defect the tier axis cost this repo four times.
    """
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("check_repeat_bands", {"spec_dir": str(spec_dir)})).data

    assert report.attested is False
    assert report.compared == []
    assert report.next_step and "draft_from_strchive" in report.next_step
    assert not (spec_dir / "verification.json").exists()


async def test_the_offline_ceiling_reaches_the_two_catalogue_checks_that_leave(
    make_client, spec: Path
) -> None:
    """`JMC_OFFLINE` is OR-combined for these too, and it is not a per-call preference.

    `check_acmg` degrades rather than refusing — offline with no `sf_list` means no
    list is obtained, which is a **skip** that gets attested, because an empty report
    with no record reads exactly like a clean one. That is upstream's own distinction
    and this asserts we keep it rather than inventing a refusal.
    """
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("check_acmg", {"spec_dir": str(spec)})).data

    # Either a list was already provisioned on this box, or it was not; both are real
    # answers and the assertion is about what an unavailable list must NOT report.
    if report.version is None:
        # Upstream's `AcmgReport.clean` is `not mismatches`, so with every verdict
        # `unchecked` it returns **True** — a green that could not have failed (filed as
        # format-tree `S100`). This is the assertion that pins our re-derivation: if the
        # guard is ever dropped, a run that read no list reports as one where everything
        # agreed, which is the single worst thing this tool could say.
        assert report.clean is None, "no list read means no verdict, never a clean one"
        assert report.checked is None, "null is not zero rows checked"
        assert report.skipped, "a check that did not run must say why"
        assert report.next_step and "not a pass" in report.next_step


def test_every_enricher_check_command_has_a_tool_or_a_written_reason() -> None:
    """Parity is the default and abstention is what needs an argument — 2026-09-12.

    **This guard exists because the last three gaps were found by using the product,
    not by the suite.** `check-acmg`, `check-repeat-bands` and `litvar` were all
    upstream CLI commands with no tool here; `check_repeat_bands` was the loud one,
    because `draft_from_strchive` writes the very table it checks, so the surface
    taught a step it could not finish.

    Scope is deliberately the CHECK commands only. A snapshot builder is a
    provisioning concern that `provision_caches` covers, and an operator's sweep is
    the one abstention the rule allows — so this asks about the commands that put a
    question to a catalogue about an authored cell, which is squarely an author's job.
    """
    from just_dna_enricher import cli as enricher_cli

    commands = {
        c.name or (c.callback.__name__.replace("_", "-") if c.callback else "")
        for c in enricher_cli.app.registered_commands
    }
    commands = {name for name in commands if name}
    assert len(commands) > 15, "the enumeration found almost nothing — the app moved"
    checks = {name for name in commands if name.startswith("check-")} | {"litvar"}
    assert "check-identifiers" in checks, "the roster lost the command it is modelled on"

    # Our side, enumerated from the live server rather than from a list here: a tool
    # renamed without this being updated must fail, not quietly pass.
    from just_module_creator import toolbox

    ours = {name for group in toolbox.GROUPS for name in group.tools} | set(toolbox.CORE)
    assert len(ours) > 40, "the tool enumeration found almost nothing"

    wrapped = {
        "check-identifiers": "check_identifiers",
        "check-acmg": "check_acmg",
        "check-repeat-bands": "check_repeat_bands",
        "litvar": "check_literature_coverage",
    }
    unwrapped = sorted(name for name in checks if name not in wrapped)
    assert not unwrapped, (
        f"upstream ships check command(s) {unwrapped} with no tool here. Parity is the "
        "default: wrap it, or write the reason in docs/just-dna-format-pending-fixes.md "
        "and add it to this map with that note. 'Nobody has exercised it' is an argument "
        "for a test, not for withholding it."
    )
    missing = sorted(tool for tool in wrapped.values() if tool not in ours)
    assert not missing, f"{missing} are mapped here but are in no toolbox group"


# --------------------------------------------------------------------------- #
# F101: the two PGx cross-checks, wrapped
# --------------------------------------------------------------------------- #
PGX_REFERENCE = Path("/data/sources/just-dna-format/reference_examples/cyp2c19_star_alleles")


@pytest.fixture
def pgx_spec(tmp_path: Path) -> Path:
    if not PGX_REFERENCE.is_dir():
        pytest.skip("the sibling format checkout is not present")
    target = tmp_path / "pgx"
    shutil.copytree(PGX_REFERENCE, target)
    return target


async def test_pgx_check_offline_with_no_snapshot_is_a_skip_with_a_reason(
    make_client, pgx_spec: Path, monkeypatch
) -> None:
    """`compared: 0` beside empty `conflicts` is not agreement, and the report says so.

    The cache base is pointed at an empty directory so no lane resolves: both legs
    land in `skipped_offline`, `routes` is empty, and `next_step` refuses to read the
    empty conflict list as a pass. Hermetic — the ceiling is on and nothing is fetched.
    """
    monkeypatch.setenv("JUST_DNA_PIPELINES_CACHE_DIR", str(pgx_spec.parent / "no-cache"))
    async with make_client(offline_settings()) as client:
        report = (
            await client.call_tool(
                "check_pgx", {"spec_dir": str(pgx_spec), "use": "non_commercial"}
            )
        ).data

    assert report.compared == 0
    assert report.conflicts == []
    assert report.routes == {}
    assert {"pharmvar", "cpic"} <= {s.split(":")[0] for s in report.skipped_offline}
    assert "not agreement" in report.next_step


async def test_pgx_check_on_a_module_with_no_pgx_table_mints_no_record(
    make_client, tmp_path: Path
) -> None:
    """The check does not apply and upstream writes nothing — read back, never assumed."""
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "module_spec.yaml").write_text("schema_version: '1.0'\n")
    async with make_client(offline_settings()) as client:
        report = (
            await client.call_tool(
                "check_pgx", {"spec_dir": str(spec_dir), "use": "non_commercial"}
            )
        ).data
    assert report.compared == 0
    assert report.attested is False
    assert not (spec_dir / "verification.json").exists()


async def test_pgx_check_carries_a_conflict_field_for_field(
    make_client, pgx_spec: Path, monkeypatch
) -> None:
    """A snapshot client that disagrees on one allele: the difference arrives, and is not applied.

    Only the client is faked — the comparison, the licence row and the attestation are
    upstream's real code. A snapshot subclass is used because `offline` admits a
    snapshot client and refuses a live one by type.
    """
    from just_dna_enricher import pgx as upstream_pgx
    from just_dna_enricher.cpic import CpicAllele, CpicSnapshotClient

    from just_module_creator.tools import checks

    class Disagreeing(CpicSnapshotClient):
        def __init__(self) -> None:  # no parquet behind it
            self.release = {"dataset": "cpic_snapshot_test"}

        def alleles_for_gene(self, gene: str) -> list[CpicAllele]:
            return [CpicAllele(gene="CYP2C19", allele="*2", function_status="increased_function")]

        def close(self) -> None:
            return None

    real = upstream_pgx.enrich_pgx

    def with_fake(spec_dir, **kwargs):
        kwargs["use_pharmvar"] = False
        return real(spec_dir, cpic_client=Disagreeing(), **kwargs)

    monkeypatch.setattr(checks, "enrich_pgx", with_fake)
    before = (pgx_spec / "allele_function.csv").read_bytes()
    async with make_client(offline_settings()) as client:
        report = (
            await client.call_tool(
                "check_pgx", {"spec_dir": str(pgx_spec), "use": "non_commercial"}
            )
        ).data

    assert report.routes == {"cpic": "snapshot"}
    assert report.compared >= 1
    assert [(c.gene, c.allele, c.authored, c.reported, c.source) for c in report.conflicts] == [
        ("CYP2C19", "*2", "no_function", "increased_function", "cpic")
    ]
    assert (pgx_spec / "allele_function.csv").read_bytes() == before, "reported, never applied"
    assert report.attested is True
    assert report.licence_rows >= 1
    assert "record_override" in report.next_step


async def test_clinpgx_check_on_a_module_with_no_pharm_table_says_nothing_to_check(
    make_client, pgx_spec: Path
) -> None:
    """`not_checked` is the third value and `nothing_to_check` mints no record — upstream's rule."""
    assert not (pgx_spec / "pharm_variants.csv").exists()
    record = pgx_spec / "verification.json"
    before = record.read_bytes() if record.exists() else None
    async with make_client(offline_settings()) as client:
        report = (
            await client.call_tool(
                "check_clinpgx", {"spec_dir": str(pgx_spec), "use": "non_commercial"}
            )
        ).data
    assert report.not_checked == "nothing_to_check"
    assert report.compared == 0
    assert report.conflicts == []
    assert report.attested is False
    assert "not agreement" in report.next_step
    assert (record.read_bytes() if record.exists() else None) == before


async def test_a_commercial_use_is_refused_by_both_pgx_checks(make_client, pgx_spec: Path) -> None:
    """Every PGx source carries a no-sale clause; `commercial` is a contradiction, not a skip."""
    (pgx_spec / "pharm_variants.csv").write_text(
        "rsid,gene,drug,genotype,evidence_level,phenotype_category,conclusion\n"
    )
    async with make_client(offline_settings()) as client:
        for tool in ("check_pgx", "check_clinpgx"):
            with pytest.raises(ToolError) as excinfo:
                await client.call_tool(tool, {"spec_dir": str(pgx_spec), "use": "commercial"})
            assert "could not run" in str(excinfo.value)
