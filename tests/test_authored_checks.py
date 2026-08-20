"""The findings this layer computes itself, and the layer marker that keeps them ours.

`RM17`. The shape under test is the one that reached production four times: every
row citing a paper carries the same `provenance_quote`, and every gate in the
toolchain is silent about it — `registry_check(literature=true, strict=true)`
returns byte-identical output for the honest module and the title-quoted one.

The quotes below are the real ones. PMID `24489884` is *Genome-wide association
study of proneness to anger*, and the published module carries its **title** on
every row that cites it; the honest quotes are ordinary sentences of the kind a
located passage actually is.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from just_module_creator.authored_checks import (
    OURS,
    findings_for_csv_text,
    findings_for_spec_dir,
    repeated_quote_findings,
)

TITLE = "Genome-wide association study of proneness to anger."

HEADER = "rsid,pmid,provenance_quote,conclusion\n"


def _rows(*triples: tuple[str, str, str]) -> list[dict[str, str]]:
    return [{"rsid": r, "pmid": p, "provenance_quote": q} for r, p, q in triples]


def test_one_string_across_every_quoted_row_is_reported():
    findings = repeated_quote_findings(
        _rows(
            ("rs1042173", "24489884", TITLE),
            ("rs2769605", "24489884", TITLE),
            ("rs6296", "24489884", TITLE),
        )
    )
    assert len(findings) == 1, "aggregated per PMID, never one finding per row"
    finding = findings[0]
    assert finding.level == "warning"
    assert finding.source == OURS
    assert finding.column == "provenance_quote"
    assert "24489884" in finding.message
    assert "3" in finding.message, "the row count is what makes the shape legible"


def test_distinct_passages_for_one_paper_are_not_reported():
    """A real passage varies with the claim, because rows cite one paper for different findings."""
    findings = repeated_quote_findings(
        _rows(
            ("rs1042173", "24489884", "we observed association at the SLC6A4 locus"),
            ("rs2769605", "24489884", "no evidence of association was seen for HTR2A"),
            ("rs6296", "24489884", "the effect was attenuated after adjustment for sex"),
        )
    )
    assert findings == []


def test_a_paper_quoted_on_one_row_says_nothing_either_way():
    """A module citing a paper once has no repetition to detect — that is not the defect."""
    assert repeated_quote_findings(_rows(("rs1042173", "24489884", TITLE))) == []


def test_blank_quotes_are_not_counted_as_repetition():
    """One quote on one row of five is a module with one quote, not a repeated one.

    An honestly empty cell is the *correct* output of a search that found nothing —
    the remediation measured a 2-3% yield — so a module full of blanks beside one
    real quote must not be reported.
    """
    findings = repeated_quote_findings(
        _rows(
            ("rs1042173", "24489884", "we observed association at the SLC6A4 locus"),
            ("rs2769605", "24489884", ""),
            ("rs6296", "24489884", ""),
        )
    )
    assert findings == []


def test_each_offending_pmid_gets_its_own_finding_and_they_are_ordered():
    findings = repeated_quote_findings(
        _rows(
            ("rs1042173", "24489884", TITLE),
            ("rs2769605", "24489884", TITLE),
            ("rs53576", "11788828", "lactase persistence is associated with the -13910 variant"),
            ("rs4988235", "11788828", "lactase persistence is associated with the -13910 variant"),
            ("rs1801133", "7647779", "a distinct passage for a different claim"),
            ("rs1801131", "7647779", "another distinct passage for another claim"),
        )
    )
    assert [f.message.split(":")[0] for f in findings] == ["pmid 11788828", "pmid 24489884"]


def test_the_check_is_the_shape_not_the_title():
    """The next variant of this is one real sentence pasted onto every row, so the
    detector must not key on the title. Nothing here is a title and it still fires."""
    sentence = "carriers of the minor allele showed higher trait anger scores"
    findings = repeated_quote_findings(
        _rows(
            ("rs1042173", "24489884", sentence),
            ("rs2769605", "24489884", sentence),
        )
    )
    assert len(findings) == 1


def test_only_studies_carries_this_check():
    text = HEADER + f"rs1042173,24489884,{TITLE},x\nrs2769605,24489884,{TITLE},y\n"
    assert findings_for_csv_text("studies.csv", text)
    assert findings_for_csv_text("variants.csv", text) == []


def test_a_spec_directory_with_no_studies_file_is_silent(tmp_path: Path):
    assert findings_for_spec_dir(tmp_path) == []


def test_it_reads_the_authored_file_rather_than_literature_csv(tmp_path: Path):
    """`literature.csv`'s counters are stale on every module that has this problem
    (`F49`), so the check must not depend on them."""
    (tmp_path / "studies.csv").write_text(
        HEADER + f"rs1042173,24489884,{TITLE},x\nrs2769605,24489884,{TITLE},y\n"
    )
    (tmp_path / "literature.csv").write_text("pmid,exists,quotes_found\n24489884,true,2\n")
    findings = findings_for_spec_dir(tmp_path)
    assert len(findings) == 1
    assert findings[0].source == OURS


# --------------------------------------------------------------------------- #
# Wiring: both surfaces report it, and the layer that computed it stays legible
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_lint_rows_reports_it_and_counts_it_as_a_warning(essentials_client):
    text = HEADER + f"rs1042173,24489884,{TITLE},x\nrs2769605,24489884,{TITLE},y\n"
    out = await essentials_client.call_tool(
        "lint_rows", {"csv_name": "studies.csv", "csv_text": text}
    )
    ours = [f for f in out.data.findings if f.source == OURS]
    assert len(ours) == 1
    assert out.data.warnings >= 1, "our finding is a warning and the count must include it"
    assert all(f.source == "upstream" for f in out.data.findings if f not in ours), (
        "upstream's own findings must keep their marker"
    )


@pytest.mark.anyio
async def test_validate_module_reports_it_beside_upstreams_own_strings(
    essentials_client, spec_dir: Path
):
    (spec_dir / "studies.csv").write_text(
        "rsid,pmid,provenance_quote,conclusion\n"
        f"rs4988235,11788828,{TITLE},Original identification\n"
        f"rs4988235,11788828,{TITLE},Second row citing the same paper\n"
    )
    out = await essentials_client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert len(out.data.authored_findings) == 1
    assert out.data.authored_findings[0].source == OURS
    assert not any("provenance_quote" in w for w in out.data.warnings), (
        "ours must not be mixed into the list that transports upstream's strings"
    )


@pytest.mark.anyio
async def test_an_authored_finding_does_not_change_validity(essentials_client, spec_dir: Path):
    """It is a warning about a shape, not a refusal: the compiler would still build this."""
    honest = (
        "rsid,pmid,provenance_quote,conclusion\n"
        "rs4988235,11788828,lactase persistence maps to the -13910 variant,Original\n"
    )
    repeated = (
        "rsid,pmid,provenance_quote,conclusion\n"
        f"rs4988235,11788828,{TITLE},Original\n"
        f"rs4988235,11788828,{TITLE},Second\n"
    )
    (spec_dir / "studies.csv").write_text(honest)
    before = await essentials_client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    (spec_dir / "studies.csv").write_text(repeated)
    after = await essentials_client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert before.data.valid == after.data.valid
    assert before.data.authored_findings == []
    assert len(after.data.authored_findings) == 1
