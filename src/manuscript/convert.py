"""Build Markdown and PDF from manuscript LaTeX sources."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pypandoc

MANUSCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "manuscript"
TEMPLATE_TEX = MANUSCRIPT_DIR / "template.tex"
MANUSCRIPT_TEX = MANUSCRIPT_DIR / "manuscript.tex"
LOG_TAIL_LINES = 40
TECTONIC_ENV_VAR = "MANUSCRIPT_TECTONIC"
TECTONIC_MISSING = (
    f"tectonic not found. Install dev dependencies with: uv sync, "
    f"or set {TECTONIC_ENV_VAR} to a working binary."
)


def latex_to_markdown(source: Path, output: Path | None = None) -> Path:
    """Convert a LaTeX file to Markdown next to the source (or to ``output``)."""
    if not source.exists():
        raise FileNotFoundError(f"{source} not found")

    dest = output if output is not None else source.with_suffix(".md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    pypandoc.convert_file(
        str(source),
        "gfm",
        outputfile=str(dest),
        extra_args=["--wrap=none"],
    )
    return dest


def latex_to_pdf(source: Path, output: Path | None = None) -> Path:
    """Compile a LaTeX file to PDF with the venv ``tectonic`` binary."""
    if not source.exists():
        raise FileNotFoundError(f"{source} not found")

    dest = output if output is not None else source.with_suffix(".pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tectonic = _resolve_tectonic()
    proc = _run(
        [
            str(tectonic),
            "--keep-logs",
            "--outdir",
            str(dest.parent.resolve()),
            source.name,
        ],
        source.parent,
    )
    if proc.returncode != 0:
        raise RuntimeError(_tectonic_error(source, dest.parent, proc))

    built = dest.parent / f"{source.stem}.pdf"
    if not built.exists():
        raise RuntimeError(f"tectonic did not produce {built}")
    if dest.resolve() != built.resolve():
        shutil.copy2(built, dest)
    return dest


def _resolve_tectonic() -> Path:
    """Find a tectonic to run, letting the environment override the venv's.

    The override exists because the wheel's binary is not portable: `tecto`
    publishes one manylinux build, and it needs a newer glibc than some hosts
    have, with nothing older on PyPI to fall back to. The same release also
    ships a static musllinux build that runs anywhere, so the fix is to point
    this variable at one rather than to change the dependency.
    """
    override = os.environ.get(TECTONIC_ENV_VAR)
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"{TECTONIC_ENV_VAR}={override} is not a file")
        return candidate

    venv_bin = Path(sys.executable).resolve().parent
    for name in ("tectonic", "tecto"):
        candidate = venv_bin / name
        if candidate.is_file():
            return candidate
    found = shutil.which("tectonic") or shutil.which("tecto")
    if found is None:
        raise FileNotFoundError(TECTONIC_MISSING)
    return Path(found)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def _tectonic_error(
    source: Path,
    outdir: Path,
    proc: subprocess.CompletedProcess[str],
) -> str:
    log = outdir / f"{source.stem}.log"
    if log.exists():
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-LOG_TAIL_LINES:])
    else:
        tail = (proc.stderr or proc.stdout or "").strip()
    return f"tectonic failed for {source.name}\n{tail}"
