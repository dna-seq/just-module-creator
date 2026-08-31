"""The manuscript CLI is a second package; the suite holds it to the sources on disk.

PDF compile needs tectonic and is not hermetic on a cold TeX cache, so these
tests check wiring and Markdown conversion only.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from manuscript import convert
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


def test_the_tectonic_binary_can_be_overridden_from_the_environment(tmp_path, monkeypatch):
    """The wheel's binary is not portable, so the environment must be able to replace it.

    `tecto` publishes one manylinux build and nothing older on PyPI, so a host
    whose glibc is too old has no version to fall back to — only the static
    musllinux build from the same release. Without this override that host
    cannot render at all, which is how a stale PDF gets read as a fresh one.
    """
    stand_in = tmp_path / "tectonic-musl"
    stand_in.write_text("#!/bin/sh\nexit 0\n")
    stand_in.chmod(0o755)

    monkeypatch.setenv(convert.TECTONIC_ENV_VAR, str(stand_in))
    assert convert._resolve_tectonic() == stand_in

    monkeypatch.setenv(convert.TECTONIC_ENV_VAR, str(tmp_path / "absent"))
    with pytest.raises(FileNotFoundError):
        convert._resolve_tectonic()

    # An unset override must not shadow the venv's binary.
    monkeypatch.delenv(convert.TECTONIC_ENV_VAR, raising=False)
    assert convert._resolve_tectonic() != stand_in
