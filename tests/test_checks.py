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

    async with make_client("extended", offline_settings()) as client:
        data = (await client.call_tool("check_identifiers", {"spec_dir": str(bare)})).data

    assert data.attested is False
    assert data.attestation_note == NOT_APPLICABLE
    assert data.genes == [] and data.traits == []
    # And nothing was written: mining a nonce onto a module that never asked for a
    # verification document is the specific harm the early return prevents.
    assert not (bare / "verification.json").exists()


async def test_both_halves_off_is_refused_before_any_socket(make_client, spec: Path) -> None:
    """An attestation for a check nobody asked for would assert nothing."""
    async with make_client("extended", offline_settings()) as client:
        with pytest.raises(ToolError, match="no question to put"):
            await client.call_tool(
                "check_identifiers",
                {"spec_dir": str(spec), "check_genes": False, "check_traits": False},
            )


async def test_the_offline_ceiling_refuses_and_writes_nothing(make_client, spec: Path) -> None:
    """It needs HGNC and OLS4, so offline is a refusal rather than a degraded run."""
    before = (spec / "verification.json").read_bytes()
    async with make_client("extended", offline_settings()) as client:
        with pytest.raises(ToolError, match="JMC_OFFLINE"):
            await client.call_tool("check_identifiers", {"spec_dir": str(spec)})
    assert (spec / "verification.json").read_bytes() == before


def test_an_existing_closure_is_not_destroyed_by_attesting(spec: Path) -> None:
    """`record_verification` merges; the closure a module already carries survives.

    Measured live on this fixture: 0 records before, 3 after, closure intact.
    """
    doc = json.loads((spec / "verification.json").read_text(encoding="utf-8"))
    assert "closure" in doc, "the reference example should carry a closure to protect"
