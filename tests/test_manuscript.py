"""The manuscript CLI is a second package; the suite holds it to the sources on disk.

PDF compile needs tectonic and is not hermetic on a cold TeX cache, so these
tests check wiring and Markdown conversion only.
"""

from pathlib import Path

from typer.testing import CliRunner

from manuscript.cli import app
from manuscript.convert import MANUSCRIPT_TEX, TEMPLATE_TEX, latex_to_markdown

REPO = Path(__file__).resolve().parent.parent
MANUSCRIPT_DIR = REPO / "docs" / "manuscript"


def test_the_easrp_sources_are_where_the_cli_looks() -> None:
    assert TEMPLATE_TEX == MANUSCRIPT_DIR / "template.tex"
    assert MANUSCRIPT_TEX == MANUSCRIPT_DIR / "manuscript.tex"
    assert TEMPLATE_TEX.is_file()
    assert MANUSCRIPT_TEX.is_file()
    assert (MANUSCRIPT_DIR / "easrp2026.sty").is_file()
    assert (MANUSCRIPT_DIR / "references.bib").is_file()


def test_the_manuscript_cli_exposes_the_two_build_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "template" in result.stdout
    assert "manuscript" in result.stdout


def test_latex_to_markdown_writes_beside_the_chosen_output(tmp_path: Path) -> None:
    dest = tmp_path / "template.md"
    written = latex_to_markdown(TEMPLATE_TEX, dest)
    assert written == dest
    text = dest.read_text(encoding="utf-8")
    assert "Introduction" in text
    assert "Related work" in text
