"""F105: a row that authors no gene gets the MANE genes within reach, as query hints only.

Upstream's RM259 answers "which genes is this position within the Atlas's horizon of?" from the
MANE lane. The rows pass reports that per `no_gene` row and writes nothing. The snapshot here is
built at test time (no parquet is committed) from three real MANE Select rows: APOE and TOMM40,
which sit within 512 kb of 19:44919171, and LCT on chromosome 2, which does not.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from conftest import MODULE_SPEC, offline_settings

from just_module_creator.expression import module_sites, no_gene_hints
from just_module_creator.tools import passes

#: Real MANE Select rows (symbol, RefSeq contig, start, end), read off the lane on 2026-11-12.
MANE_ROWS = [
    ("APOE", "NC_000019.10", 44905796, 44909393),
    ("TOMM40", "NC_000019.10", 44891254, 44903689),
    ("LCT", "NC_000002.12", 135787850, 135837184),
]

VARIANTS = (
    "rsid,chrom,start,ref,alts,genotype,gene,weight,state,conclusion\n"
    ",19,44919171,A,T,A/T,,0.5,risk,no gene on this row\n"
    ",19,44919171,A,T,T/T,,1.0,risk,the other genotype at the same position\n"
)


def _spec(tmp_path: Path, build: str = "GRCh38") -> Path:
    spec = tmp_path / "spec"
    spec.mkdir()
    assert "genome_build: GRCh38\n" in MODULE_SPEC
    (spec / "module_spec.yaml").write_text(
        MODULE_SPEC.replace("genome_build: GRCh38", f"genome_build: {build}")
    )
    (spec / "variants.csv").write_text(VARIANTS)
    return spec


@pytest.fixture
def mane_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    lane = tmp_path / "mane"
    (lane / "data").mkdir(parents=True)
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE mane (symbol VARCHAR, grch38_chr VARCHAR, chr_start BIGINT, "
        "chr_end BIGINT, mane_status VARCHAR)"
    )
    con.executemany(
        "INSERT INTO mane VALUES (?, ?, ?, ?, 'MANE Select')", [list(r) for r in MANE_ROWS]
    )
    target = str(lane / "data" / "summary.parquet").replace("'", "''")
    con.execute(f"COPY mane TO '{target}' (FORMAT PARQUET)")
    con.close()
    monkeypatch.setenv("JUST_DNA_MANE_CACHE", str(lane))
    return lane


def test_a_row_with_no_gene_is_offered_the_genes_within_reach(tmp_path, mane_lane) -> None:
    spec = _spec(tmp_path)
    hints = no_gene_hints(spec, module_sites(spec)[0])

    # F147: two rows at one position give one hint naming both keys.
    assert len(hints) == 1
    (hint,) = hints
    assert (hint.chrom, hint.position, hint.reason) == ("19", 44919171, None)
    assert set(hint.variant_keys) == {s.variant_key for s in module_sites(spec)[0]}
    assert hint.genes is not None
    # Upstream's order (start, then name), and each distance from the real span.
    by_gene = {g.gene: g for g in hint.genes}
    assert [g.gene for g in hint.genes] == ["TOMM40", "APOE"], "LCT is on another contig"
    for symbol, _chrom, start, end in MANE_ROWS[:2]:
        assert (by_gene[symbol].start, by_gene[symbol].end) == (start, end)
        assert by_gene[symbol].distance_bp == 44919171 - end


def test_without_the_lane_the_row_says_nobody_asked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("JUST_DNA_MANE_CACHE", str(tmp_path / "absent"))
    monkeypatch.setenv("JUST_DNA_PIPELINES_CACHE_DIR", str(tmp_path / "empty-cache"))
    spec = _spec(tmp_path)
    hints = no_gene_hints(spec, module_sites(spec)[0])

    assert [(h.genes, h.reason) for h in hints] == [(None, "no_snapshot")]


def test_a_grch37_module_is_not_looked_up_on_grch38_spans(tmp_path, mane_lane) -> None:
    spec = _spec(tmp_path, build="GRCh37")
    hints = no_gene_hints(spec, module_sites(spec)[0])

    assert len(hints) == 1 and hints[0].genes is None
    assert hints[0].reason and "GRCh37" in hints[0].reason


async def test_the_rows_pass_reports_the_hints_and_writes_no_gene(
    tmp_path, mane_lane, make_client, monkeypatch
) -> None:
    spec = _spec(tmp_path)
    monkeypatch.setattr(passes, "enrich_expression", lambda *_a, **_k: 1 / 0)
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "enrich_expression_effects", {"spec_dir": str(spec), "rows": True, "dry_run": True}
        )
    body = json.loads(out.content[0].text)

    assert body["row_status"]["no_gene"] == 2
    # The key is the loader's, read from the same producer the pass uses.
    keys = {s.variant_key for s in module_sites(spec)[0]}
    (entry,) = body["no_gene_candidates"]
    assert set(entry["variant_keys"]) == keys
    assert (entry["chrom"], entry["position"], entry["reason"]) == ("19", 44919171, None)
    assert [g["gene"] for g in entry["genes"]] == ["TOMM40", "APOE"]
    assert (spec / "variants.csv").read_text() == VARIANTS, "a hint is never written into a row"
