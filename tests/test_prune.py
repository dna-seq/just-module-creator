"""F104: `prune_rows` applies an author's keep-list and decides nothing.

Fixture: the real `pharm_variants.csv` of the ClawBio DPYD rehearsal — ClinPGx rows
for rs3918290 (*2A), rs55886062 (*13) and rs67376798 (c.2846A>T).
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
from conftest import offline_settings
from fastmcp.exceptions import ToolError

FIXTURE = Path(__file__).resolve().parent.parent / "assets" / "pgx" / "dpyd_pharm_variants.csv"
KEEP = ["rs3918290", "rs55886062"]


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    spec = tmp_path / "dpyd"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("schema_version: '1.0'\nmodule:\n  name: dpyd\n")
    shutil.copy(FIXTURE, spec / "pharm_variants.csv")
    return spec


def _args(spec: Path, **extra) -> dict:
    return {
        "spec_dir": str(spec),
        "table": "pharm_variants.csv",
        "keep": KEEP,
        "reason": "ClawBio panel: the two DPYD alleles the reporter calls",
        "recorded_by": "test-suite",
        "source_name": "clinpgx",
        **extra,
    }


def _expected() -> tuple[int, int]:
    rows = _rows(FIXTURE)
    kept = sum(1 for r in rows if r["rsid"] in KEEP)
    return kept, len(rows) - kept


async def test_a_dry_run_counts_and_touches_nothing(make_client, spec: Path) -> None:
    before = (spec / "pharm_variants.csv").read_bytes()
    async with make_client(offline_settings(workspace=str(spec.parent))) as client:
        out = (await client.call_tool("prune_rows", _args(spec, dry_run=True))).data
    kept, dropped = _expected()
    assert kept > 0 and dropped > 0
    assert (out.kept, out.dropped) == (kept, dropped)
    assert out.dropped_keys == ["rs67376798"]
    assert out.capture is None and out.record is None
    assert (spec / "pharm_variants.csv").read_bytes() == before
    assert not (spec / "logs").exists()


async def test_a_trim_keeps_the_list_captures_first_and_logs_once(make_client, spec: Path) -> None:
    original = (spec / "pharm_variants.csv").read_bytes()
    async with make_client(offline_settings(workspace=str(spec.parent))) as client:
        out = (await client.call_tool("prune_rows", _args(spec))).data
    after = _rows(spec / "pharm_variants.csv")
    assert {r["rsid"] for r in after} == set(KEEP)
    assert after == [r for r in _rows(FIXTURE) if r["rsid"] in KEEP]
    capture = Path(out.capture)
    assert capture.read_bytes() == original
    assert spec not in capture.parents, "the capture must never sit in the spec directory"
    logged = (spec / "logs" / "authoring.log").read_text()
    assert logged.count("\n") == 1
    assert "table pharm_variants.csv rows='kept " in logged
    provenance = json.loads((spec / "provenance.json").read_text())
    assert "pharm_variants.csv" in json.dumps(provenance)


async def test_a_keep_value_matching_no_row_refuses(make_client, spec: Path) -> None:
    """rs391829 is rs3918290 with a digit lost — the typo that would drop *2A."""
    before = (spec / "pharm_variants.csv").read_bytes()
    async with make_client(offline_settings(workspace=str(spec.parent))) as client:
        out = (
            await client.call_tool("prune_rows", _args(spec, keep=["rs391829", "rs55886062"]))
        ).data
    assert out.unmatched_keep == ["rs391829"]
    assert out.refused and "match no row" in out.refused
    assert (spec / "pharm_variants.csv").read_bytes() == before


async def test_a_derived_sidecar_is_refused(make_client, spec: Path) -> None:
    (spec / "resolution.csv").write_text("variant_key,rsid\nrs3918290,rs3918290\n")
    async with make_client(offline_settings(workspace=str(spec.parent))) as client:
        with pytest.raises(ToolError, match="refresh_sidecar"):
            await client.call_tool("prune_rows", _args(spec, table="resolution.csv"))


async def test_a_missing_key_column_names_the_real_ones(make_client, spec: Path) -> None:
    async with make_client(offline_settings(workspace=str(spec.parent))) as client:
        with pytest.raises(ToolError, match="columns are rsid, gene"):
            await client.call_tool("prune_rows", _args(spec, key_column="variant_key"))
