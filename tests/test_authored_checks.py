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
    conclusion_genotype_findings,
    findings_for_csv_text,
    findings_for_spec_dir,
    repeated_quote_findings,
    shared_conclusion_findings,
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
async def test_lint_rows_reports_it_and_counts_it_as_a_warning(client):
    text = HEADER + f"rs1042173,24489884,{TITLE},x\nrs2769605,24489884,{TITLE},y\n"
    out = await client.call_tool(
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
    client, spec_dir: Path
):
    (spec_dir / "studies.csv").write_text(
        "rsid,pmid,provenance_quote,conclusion\n"
        f"rs4988235,11788828,{TITLE},Original identification\n"
        f"rs4988235,11788828,{TITLE},Second row citing the same paper\n"
    )
    out = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert len(out.data.authored_findings) == 1
    assert out.data.authored_findings[0].source == OURS
    assert not any("provenance_quote" in w for w in out.data.warnings), (
        "ours must not be mixed into the list that transports upstream's strings"
    )


@pytest.mark.anyio
async def test_an_authored_finding_does_not_change_validity(client, spec_dir: Path):
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
    before = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    (spec_dir / "studies.csv").write_text(repeated)
    after = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert before.data.valid == after.data.valid
    assert before.data.authored_findings == []
    assert len(after.data.authored_findings) == 1


# --------------------------------------------------------------------------- #
# `RM27` — the conclusion against the row it sits on
# --------------------------------------------------------------------------- #
#: `rs17514846` is the FURIN/FES coronary-artery-disease variant, and the rows below
#: are the real ones from the module the rule was measured on: the `C/C` and `A/A`
#: conclusions are swapped, and all three rows read `neutral, 0.0` — so nothing else
#: in the module distinguishes them either.
SWAPPED = (
    "rsid,genotype,weight,state,conclusion\n"
    "rs17514846,C/C,0.0,neutral,AA genotype is associated with an increased risk of CAD\n"
    "rs17514846,A/C,0.0,neutral,Heterozygous carriers show an intermediate association\n"
    "rs17514846,A/A,0.0,neutral,CC genotype is NOT associated with an increased risk of CAD\n"
)


def _variant_rows(text: str):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text)))


def test_a_swapped_pair_of_conclusions_is_reported_once_for_the_locus():
    findings = conclusion_genotype_findings(_variant_rows(SWAPPED))
    assert len(findings) == 1, "one decision per locus, not one per row"
    assert findings[0].level == "warning", "measured precision is ~60%; an error would be a lie"
    assert findings[0].source == OURS
    assert "rs17514846" in findings[0].message
    assert "C/C names AA" in findings[0].message
    assert "A/A names CC" in findings[0].message


def test_a_conclusion_naming_its_own_genotype_is_not_reported():
    text = (
        "rsid,genotype,weight,state,conclusion\n"
        "rs17514846,C/C,0.0,neutral,CC genotype is NOT associated with an increased risk of CAD\n"
        "rs17514846,A/A,0.0,neutral,AA genotype is associated with an increased risk of CAD\n"
    )
    assert conclusion_genotype_findings(_variant_rows(text)) == []


def test_a_two_letter_word_that_is_not_an_allele_at_this_locus_is_left_alone():
    """The false positive that killed the first version of this rule.

    `TG` in "raised plasma triglyceride (TG) levels" is genotype-shaped, and at a
    site whose alleles are C and G it cannot be a genotype. The locus constraint
    excludes it by construction rather than by a stop-list — so the same sentence
    IS flagged at a T/G site, which is the second half of the property.
    """
    at_cg = (
        "rsid,genotype,weight,state,conclusion\n"
        "rs1260326,C/C,0.1,risk,Associated with raised plasma triglyceride (TG) levels\n"
        "rs1260326,C/G,0.1,risk,Associated with raised plasma triglyceride (TG) levels\n"
    )
    assert conclusion_genotype_findings(_variant_rows(at_cg)) == []

    at_tg = at_cg.replace("C/C", "T/T").replace("C/G", "T/G")
    assert len(conclusion_genotype_findings(_variant_rows(at_tg))) == 1


def test_the_slashed_spelling_in_prose_is_the_snps_alleles_and_is_not_matched():
    """`C/A` in a conclusion names the SNP, not a genotype — the measured case.

    All four findings this spelling added across the six-module corpus were this one
    sentence, on rows whose prose was otherwise right.
    """
    text = (
        "rsid,genotype,weight,state,conclusion\n"
        "rs2943634,A/A,0.3,protective,rs2943634 C/A SNP has been associated with CAD. "
        "AA-carriers have lower risk\n"
        "rs2943634,C/C,-0.3,risk,rs2943634 C/A SNP has been associated with CAD. "
        "CC-carriers have higher risk\n"
    )
    assert conclusion_genotype_findings(_variant_rows(text)) == []


def test_a_row_whose_genotype_cannot_be_read_gets_no_opinion():
    """A star allele is not a base pair, and a check that cannot run has not passed."""
    text = (
        "rsid,genotype,weight,state,conclusion\n"
        "rs3892097,*4/*4,0.0,neutral,CC genotype is the normal metabolizer\n"
        "rs3892097,C/C,0.0,neutral,CC genotype is the normal metabolizer\n"
    )
    assert conclusion_genotype_findings(_variant_rows(text)) == []


def test_one_conclusion_across_genotypes_that_score_differently_is_a_question():
    text = (
        "rsid,genotype,weight,state,conclusion\n"
        "rs4880,C/C,0.0,neutral,MnSOD activity varies with this polymorphism\n"
        "rs4880,C/T,0.4,risk,MnSOD activity varies with this polymorphism\n"
        "rs4880,T/T,0.8,risk,MnSOD activity varies with this polymorphism\n"
    )
    findings = shared_conclusion_findings(_variant_rows(text))
    assert len(findings) == 1
    assert findings[0].level == "info", "a question the author has not been asked, not a defect"
    assert "rs4880" in findings[0].message


def test_one_conclusion_across_genotypes_that_score_the_SAME_is_not_raised():
    """Nothing to decide: the reader sees one sentence and one number."""
    text = (
        "rsid,genotype,weight,state,conclusion\n"
        "rs4880,C/T,0.4,risk,MnSOD activity varies with this polymorphism\n"
        "rs4880,T/T,0.4,risk,MnSOD activity varies with this polymorphism\n"
    )
    assert shared_conclusion_findings(_variant_rows(text)) == []


def test_the_second_rule_is_one_finding_however_many_groups_there_are():
    """480 of 492 measured groups were in one module. Per-group would be the spam."""
    rows = [
        {
            "rsid": f"rs{1000000 + n}",
            "genotype": genotype,
            "weight": weight,
            "state": "risk",
            "conclusion": "Associated with the trait",
        }
        for n in range(40)
        for genotype, weight in (("C/T", "0.4"), ("T/T", "0.8"))
    ]
    findings = shared_conclusion_findings(rows)
    assert len(findings) == 1
    assert findings[0].message.startswith("40 rsID(s)")
    assert "and 35 more" in findings[0].message


# --------------------------------------------------------------------------- #
# Wiring: both surfaces carry the conclusion findings too
# --------------------------------------------------------------------------- #
@pytest.mark.anyio
async def test_lint_rows_carries_the_conclusion_warning_on_variants(client):
    out = await client.call_tool(
        "lint_rows", {"csv_name": "variants.csv", "csv_text": SWAPPED}
    )
    ours = [f for f in out.data.findings if f.source == OURS]
    assert len(ours) == 1
    assert ours[0].level == "warning"
    assert out.data.warnings >= 1, "the count must include ours"


@pytest.mark.anyio
async def test_validate_module_carries_them_from_variants_csv_too(
    client, spec_dir: Path
):
    (spec_dir / "variants.csv").write_text(SWAPPED)
    out = await client.call_tool(
        "validate_module", {"spec_dir": str(spec_dir), "strict": False}
    )
    ours = [f for f in out.data.authored_findings if f.column == "conclusion"]
    assert len(ours) == 1
    assert ours[0].source == OURS
