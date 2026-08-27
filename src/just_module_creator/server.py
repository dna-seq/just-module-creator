"""FastMCP server: assembly, CLI, and deployment entrypoints.

``build_server`` registers **one surface**. There is no mode axis: ``JMC_MODE``,
``--mode`` and the ``extended`` tier were removed in 0.21.0, after three separate
occasions on which the default tier taught a step it could not run —
``enrich_module`` in 0.4.0, ``registry_download`` and ``refresh_sidecar`` in the
two 2026-08-21 unattended runs. The cost the tier was protecting is real and is
now written in the docstring of each expensive tool, where the caller reads it,
instead of hiding the tool from the sessions most likely to need it.

* ``register_essentials`` — the offline authoring loop, the schema dump and the
  integrity checks. Touches no network.
* ``register_checks``     — ``check_identifiers``: puts a question to HGNC and
  OLS4 and records in ``verification.json`` that it was put. Split out of
  ``research.py`` under RM9 so that module's no-writes claim stays literal.
* ``register_research``   — read-only lookups: variants, citations, literature,
  identifiers, papers, registry reads. No token.
* ``register_auth``       — ``registry_register`` (mints a token, so it cannot be
  gated by one) and the per-session ``authenticate``.
* ``register_registry``   — listed, token enforced per call.
* ``register_provenance`` — recording that an authored value outranks a source,
  and the review queue that reads those records back (RM16).
* ``register_comparison`` — ``compare_modules``: two local spec directories,
  offline, at three grains (RM19).
* ``register_passes``     — the two tools that fetch and then write into a spec
  directory: ``draft_from_clinvar`` (step 2) and ``enrich_module`` (step 6).
* ``register_bulk_passes`` — PGx drafting and the three fact passes. Each says
  its own budget; a fact pass rewrites many rows rather than answering about one.
* ``register_artifact_reads`` — ``registry_download`` and ``reverse_module``:
  getting somebody else's published module onto disk, the entry point to a review.
* ``register_citation_graph`` — ``paper_citations``, whose work the corpus sizes.
* ``register_refresh``    — ``refresh_sidecar``: capture, delete, re-derive,
  reapply what is provably the author's, report the rest.

Two axes remain and neither is a tier. **Auth** decides whether the registry
tools *work* (per call, per session, per instance — see ``auth.py``), and
optionally whether they are *listed*, with ``JMC_HIDE_GATED_UNTIL_AUTH``.
**Discovery** decides how the surface is presented: ``JMC_TOOL_SEARCH`` replaces
the listing with ``search_tools`` + ``call_tool`` for clients that would rather
query than receive a catalog.

The server NEVER raises at startup for a missing token (see auth.py): authoring
a module needs no registry account at all.
"""

from __future__ import annotations

import signal
import sys

import typer
from dotenv import load_dotenv
from fastmcp import FastMCP

from just_module_creator import __version__
from just_module_creator.auth import hide_gated_tools, register_auth
from just_module_creator.logging_setup import get_logger, setup_logging
from just_module_creator.net import build_services
from just_module_creator.settings import Settings, ToolSearch
from just_module_creator.tool_search import apply_tool_search
from just_module_creator.toolbox import hide_layer_two, register_toolbox
from just_module_creator.tools._shared import schema_versions
from just_module_creator.tools.advanced import (
    register_artifact_reads,
    register_citation_graph,
)
from just_module_creator.tools.authoring import register_essentials
from just_module_creator.tools.checks import register_checks
from just_module_creator.tools.comparison import register_comparison
from just_module_creator.tools.passes import register_bulk_passes, register_passes
from just_module_creator.tools.provenance import register_provenance
from just_module_creator.tools.refresh import register_refresh
from just_module_creator.tools.registry import register_registry
from just_module_creator.tools.research import register_research

log = get_logger()

# An f-string, and never a literal version: the header names the toolchain that
# is actually loaded, so an agent reading the instructions can see at a glance
# that a stale plugin cache is answering. It said "format 0.5" for two releases
# while the installed format was 0.6.
#
# HARD CEILING: 2048 characters. Claude Code truncates server instructions to
# that and says so only in its MCP debug log — 0.14.0 shipped 9220 chars, so
# three quarters of this silently never reached the model, the cut landing
# mid-rule-3 and taking every registry rule with it. `test_the_instructions_fit`
# fails on a regression. Everything longer belongs in a skill: this file is the
# map plus the rules no skill may soften, and each rule below has a fuller home
# (`module-curate`, `find-evidence`, `module-publish`, `module-start`).
# Bound to short names rather than interpolated as attribute chains: that line has
# to stay one line, because inside a triple-quoted f-string a newline in the
# source is a newline in what the host receives — so it cannot be wrapped.
_FMT = schema_versions().format_version
_COMP = schema_versions().compiler_version

INSTRUCTIONS = f"""\
Authoring surface for just-dna annotation modules (plugin v{__version__}). Schema
answers come from just-dna-format {_FMT} and just-dna-compiler {_COMP}; older
than yours is a stale process.

A module is authored CSVs plus module_spec.yaml, compiled to a parquet
artifact. Work in this order:

  list_tables -> scaffold_module -> draft_from_clinvar -> literature_search
    -> author rows -> lint_rows -> validate_module(strict) -> enrich_module
    -> compile_module(strict)

Load `create-module` to route. Rules no skill softens:

1. Ask the tool, never memory: describe_table / table_requirements /
   describe_machine_table generate every column, vocabulary and requirement.
2. You MAY write — and YOU log it: nothing logs a hand edit, so call
   `record_override` (→ logs/authoring.log). Two cells stay withheld:
   one a later check compares against THAT SAME source, and one only a pilot
   settles — genotype, weight, conclusion, direction.
3. A mismatch means CHECK BOTH SIDES: the row may be wrong, and so may the
   source — archives lag the edge. A source is evidence, never authority: conform
   to a stale one and the check agrees with itself.
4. A check that could not run is not a check that passed: `null` and `unknown`
   never mean pass; warnings on a green run are the real output.
5. Take every PMID from a literature_search result: existence never settles
   identity, only a title does. A `provenance_quote` is a passage you located,
   verbatim, for this row's claim — never the title.
6. `start` is the 1-based VCF position: paste it, never subtract one.

Every registry tool takes `target`; catalog reads REQUIRE it — read back what
you wrote to. target="test" is the polygon: a publish there is a
REHEARSAL you can delete. target="prod" is the catalog, immutable, its data
claimed by a hash `yank` never frees. Writes default to test. Rehearse, say so
aloud, promote only on explicit yes — "publish it" is not that ask.
"""

#: Appended only when the surface is layered, and it has to be short: the host
#: ceiling above applies to the whole string, so this line is why the base above
#: carries slack rather than filling its budget.
LAYERED_NOTE = """
Only the core loop is listed: `toolbox` names the rest and reveals it.
"""


def instructions_for(settings: Settings) -> str:
    """The header this deployment sends, which depends on how much of it is listed."""
    if settings.toolbox == "layered":
        return INSTRUCTIONS + LAYERED_NOTE
    return INSTRUCTIONS


def build_server(
    settings: Settings | None = None, tool_search: ToolSearch | None = None
) -> FastMCP:
    """Construct a fresh, fully-wired FastMCP server.

    A factory (not a singleton) so each test / deployment gets an isolated
    instance. ``tool_search`` overrides the matching setting.
    """
    settings = settings or Settings()
    if tool_search is not None:
        settings = settings.model_copy(update={"tool_search": tool_search})
    setup_logging(settings)

    mcp = FastMCP(
        name=f"just-module-creator v{__version__}",
        instructions=instructions_for(settings),
    )

    # One shared client set for the whole server. Lazy: constructing it opens no
    # connection, so importing this module still touches no network.
    services = build_services(settings)

    register_essentials(mcp, settings)
    register_checks(mcp, settings)
    register_research(mcp, settings, services)
    register_auth(mcp, settings)
    register_registry(mcp, settings)
    register_passes(mcp, settings, services)
    register_provenance(mcp, settings)
    register_comparison(mcp, settings)
    # Always on. `registry_download` / `reverse_module` get a published module onto
    # disk, and `refresh_sidecar` re-derives one against its source; all three are
    # bounded by what the caller named. Two unattended runs in the default tier each
    # concluded the first was impossible and the third did not exist.
    register_artifact_reads(mcp, settings, services)
    register_refresh(mcp, settings, services)
    register_citation_graph(mcp, settings, services)
    register_bulk_passes(mcp, settings, services)
    register_toolbox(mcp, settings)
    if settings.toolbox == "layered":
        hide_layer_two(mcp)
    if settings.hide_gated_until_auth:
        hide_gated_tools(mcp)
    # Last: a search transform indexes whatever is registered when it runs.
    apply_tool_search(mcp, settings)

    log.info(
        "Server built (offline=%s, toolbox=%s, tool_search=%s, registry=%s, polygon=%s)",
        settings.offline,
        settings.toolbox,
        settings.tool_search,
        settings.registry_url,
        settings.registry_test_url,
    )
    return mcp


# Module-level instance for `fastmcp run` / `fastmcp dev` discovery.
# Safe to import: no token required, no network calls.
mcp = build_server()


# --------------------------------------------------------------------------- #
# Graceful shutdown
# --------------------------------------------------------------------------- #
class GracefulShutdownHandler:
    """Handle SIGINT/SIGTERM so the server stops cleanly; double-signal forces."""

    def __init__(self) -> None:
        self.shutdown_requested = False
        self._orig_sigint = None
        self._orig_sigterm = None

    def register_handlers(self) -> None:
        self._orig_sigint = signal.signal(signal.SIGINT, self._handle)
        self._orig_sigterm = signal.signal(signal.SIGTERM, self._handle)

    def restore_handlers(self) -> None:
        if self._orig_sigint is not None:
            signal.signal(signal.SIGINT, self._orig_sigint)
        if self._orig_sigterm is not None:
            signal.signal(signal.SIGTERM, self._orig_sigterm)

    def _handle(self, signum: int, frame) -> None:
        if self.shutdown_requested:
            log.warning("Force shutdown requested")
            sys.exit(1)
        self.shutdown_requested = True
        name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        log.info("Received %s, shutting down gracefully...", name)
        raise KeyboardInterrupt()


def run_with_graceful_shutdown(server: FastMCP, **run_kwargs) -> None:
    """Run ``server.run(**run_kwargs)`` with graceful shutdown handling."""
    handler = GracefulShutdownHandler()
    try:
        handler.register_handlers()
        log.info("Starting server: %s", run_kwargs or "stdio")
        server.run(**run_kwargs)
    except KeyboardInterrupt:
        log.info("Shutdown signal received, cleaning up...")
    except Exception:
        log.exception("Server error")
        raise
    finally:
        handler.restore_handlers()
        log.info("Server stopped")


# --------------------------------------------------------------------------- #
# Typer CLI — `just-module-creator [main|stdio|http|sse]`
# --------------------------------------------------------------------------- #
app = typer.Typer(add_completion=False, help="just-dna module authoring MCP server.")

_SEARCH_OPT = typer.Option(
    None, "--tool-search", help="off | regex | bm25 (collapse the listing into search)"
)


def _load_env() -> None:
    """Load ``.env`` before any configuration is read.

    ``override=False`` so a variable already exported in the shell wins over the
    file. The just-dna toolchain reads its own cache/API-key variables straight
    from ``os.environ``, so loading here is what makes a single ``.env`` serve
    both this server and the enricher it calls.
    """
    load_dotenv(override=False)


def _run(
    transport: str, host: str | None, port: int | None, tool_search: str | None = None
) -> None:
    _load_env()
    settings = Settings()
    server = build_server(settings=settings, tool_search=tool_search)  # type: ignore[arg-type]
    kwargs: dict = {"transport": transport}
    if transport != "stdio":
        kwargs["host"] = host or settings.host
        kwargs["port"] = port or settings.port
        # Print the URL before binding: a server whose address you have to guess
        # from the config is a server you cannot connect to.
        typer.echo(f"just-module-creator listening on http://{kwargs['host']}:{kwargs['port']}")
    run_with_graceful_shutdown(server, **kwargs)


@app.command()
def main(
    transport: str = typer.Option(None, help="stdio | http | sse"),
    host: str = typer.Option(None, help="Host to bind (network transports)."),
    port: int = typer.Option(None, help="Port to bind (network transports)."),
    tool_search: str = _SEARCH_OPT,
) -> None:
    """Run the server (transport from --transport or JMC_TRANSPORT)."""
    settings = Settings()
    _run(transport or settings.transport, host, port, tool_search)


@app.command()
def stdio(tool_search: str = _SEARCH_OPT) -> None:
    """Run with the stdio transport (for local MCP clients)."""
    _run("stdio", None, None, tool_search)


@app.command()
def http(
    host: str = typer.Option(None),
    port: int = typer.Option(None),
    tool_search: str = _SEARCH_OPT,
) -> None:
    """Run with the streamable-HTTP transport."""
    _run("http", host, port, tool_search)


@app.command()
def sse(
    host: str = typer.Option(None),
    port: int = typer.Option(None),
    tool_search: str = _SEARCH_OPT,
) -> None:
    """Run with the (legacy) SSE transport."""
    _run("sse", host, port, tool_search)


def cli_app() -> None:
    """Console-script entrypoint (see [project.scripts])."""
    app()


if __name__ == "__main__":
    app()
