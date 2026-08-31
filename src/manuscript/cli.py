"""Typer CLI for building manuscript Markdown and PDF from LaTeX."""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from manuscript.convert import (
    MANUSCRIPT_TEX,
    TEMPLATE_TEX,
    latex_to_markdown,
    latex_to_pdf,
)

app = typer.Typer(
    name="manuscript",
    help="Build Markdown and PDF from manuscript LaTeX sources.",
    add_completion=False,
    pretty_exceptions_enable=False,
    no_args_is_help=True,
)


def _load_env() -> None:
    """Load ``.env`` before the build reads any configuration.

    ``override=False`` so an exported variable still wins. This is what lets
    ``MANUSCRIPT_TECTONIC`` and ``TECTONIC_CACHE_DIR`` live beside the rest of
    the toolchain's settings instead of being retyped on every invocation.
    """
    load_dotenv(override=False)


def _build(
    source: Path,
    markdown_output: Path | None,
    pdf_output: Path | None,
    build_pdf: bool = True,
) -> None:
    _load_env()
    try:
        markdown_path = latex_to_markdown(source, markdown_output)
        pdf_path = latex_to_pdf(source, pdf_output) if build_pdf else None
    except (FileNotFoundError, RuntimeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {markdown_path}")
    if pdf_path is not None:
        typer.echo(f"Wrote {pdf_path}")


@app.command("template")
def build_template(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output Markdown file. Defaults to docs/manuscript/template.md.",
        ),
    ] = None,
    pdf_output: Annotated[
        Path | None,
        typer.Option(
            "--pdf-output",
            help="Output PDF file. Defaults to docs/manuscript/template.pdf.",
        ),
    ] = None,
    no_pdf: Annotated[
        bool,
        typer.Option(
            "--no-pdf",
            "--nopdf",
            help="Write only the Markdown. Use when reviewing prose without churning the PDF.",
        ),
    ] = False,
) -> None:
    """Build Markdown and PDF from the EASRP template."""
    _build(TEMPLATE_TEX, output, pdf_output, build_pdf=not no_pdf)


@app.command("manuscript")
def build_manuscript(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output Markdown file. Defaults to docs/manuscript/manuscript.md.",
        ),
    ] = None,
    pdf_output: Annotated[
        Path | None,
        typer.Option(
            "--pdf-output",
            help="Output PDF file. Defaults to docs/manuscript/manuscript.pdf.",
        ),
    ] = None,
    no_pdf: Annotated[
        bool,
        typer.Option(
            "--no-pdf",
            "--nopdf",
            help="Write only the Markdown. Use when reviewing prose without churning the PDF.",
        ),
    ] = False,
) -> None:
    """Build Markdown and PDF from the paper LaTeX."""
    _build(MANUSCRIPT_TEX, output, pdf_output, build_pdf=not no_pdf)


if __name__ == "__main__":
    app()
