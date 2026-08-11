"""FastMCP server: assembly, CLI, and deployment entrypoints.

The hybrid registration pattern lives in ``build_server``:

* ``register_essentials`` — always. The offline authoring loop.
* ``register_research``   — always. Read-only lookups; no token, network-tier.
* ``register_auth``       — always. The per-session ``authenticate`` tool.
* ``register_registry``   — always listed, token enforced per call.
* ``register_extended``   — ONLY when mode == "extended" (registered on start).

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
from just_module_creator.auth import SessionKeyStore, register_auth
from just_module_creator.logging_setup import get_logger, setup_logging
from just_module_creator.settings import Mode, Settings
from just_module_creator.tools.advanced import register_extended
from just_module_creator.tools.authoring import register_essentials
from just_module_creator.tools.registry import register_registry
from just_module_creator.tools.research import register_research

log = get_logger()

INSTRUCTIONS = """\
Authoring surface for just-dna annotation modules (format 0.5).

A module is a directory of authored CSVs plus module_spec.yaml, compiled into a
parquet artifact with a content-addressed manifest. Work in this order:

  list_tables -> scaffold_module -> author rows -> lint_rows
    -> validate_module(strict) -> enrich_module -> compile_module(strict)

Three rules this server enforces rather than merely documents:

1. Ask the tool, never memory. Every column list, vocabulary and requirement is
   generated from the live pydantic models, so describe_table /
   table_requirements cannot drift from what the compiler accepts.
2. Report, never repair. Lookups show you a value and refuse to write it into an
   authored cell — a later check compares your independent value against that
   same source, so filling it from the source makes the check vacuous. Those
   refusals are the feature.
3. A check that could not run is not a check that passed. `null` and `unknown`
   never collapse into a pass, and warnings on a green run are the interesting
   output.

`start` is always the 1-based VCF position: paste it, never subtract one.

Extended mode (JMC_MODE=extended) adds enrichment, integrity, round-trip and
registry reads. Publishing needs a registry token via `authenticate`; nothing
else does.
"""


def build_server(mode: Mode | None = None, settings: Settings | None = None) -> FastMCP:
    """Construct a fresh, fully-wired FastMCP server.

    A factory (not a singleton) so each test / deployment gets an isolated
    instance. Pass ``mode`` to override ``settings.mode``.
    """
    settings = settings or Settings()
    resolved_mode: Mode = mode or settings.mode
    setup_logging(settings)

    mcp = FastMCP(
        name=f"just-module-creator v{__version__}",
        instructions=INSTRUCTIONS,
    )

    store = SessionKeyStore()
    register_essentials(mcp, settings)
    register_research(mcp, settings)
    register_auth(mcp, settings, store)
    register_registry(mcp, settings, store)
    if resolved_mode == "extended":
        register_extended(mcp, settings)

    log.info(
        "Server built (mode=%s, offline=%s, registry=%s)",
        resolved_mode,
        settings.offline,
        settings.registry_url,
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
# Typer CLI — `just-module-creator [main|stdio|http|sse] --mode ...`
# --------------------------------------------------------------------------- #
app = typer.Typer(add_completion=False, help="just-dna module authoring MCP server.")

_MODE_OPT = typer.Option(None, "--mode", help="essentials | extended")


def _load_env() -> None:
    """Load ``.env`` before any configuration is read.

    ``override=False`` so a variable already exported in the shell wins over the
    file. The just-dna toolchain reads its own cache/API-key variables straight
    from ``os.environ``, so loading here is what makes a single ``.env`` serve
    both this server and the enricher it calls.
    """
    load_dotenv(override=False)


def _run(transport: str, mode: str | None, host: str | None, port: int | None) -> None:
    _load_env()
    settings = Settings()
    server = build_server(mode=mode, settings=settings)  # type: ignore[arg-type]
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
    mode: str = _MODE_OPT,
    transport: str = typer.Option(None, help="stdio | http | sse"),
    host: str = typer.Option(None, help="Host to bind (network transports)."),
    port: int = typer.Option(None, help="Port to bind (network transports)."),
) -> None:
    """Run the server (transport from --transport or JMC_TRANSPORT)."""
    settings = Settings()
    _run(transport or settings.transport, mode, host, port)


@app.command()
def stdio(mode: str = _MODE_OPT) -> None:
    """Run with the stdio transport (for local MCP clients)."""
    _run("stdio", mode, None, None)


@app.command()
def http(
    mode: str = _MODE_OPT,
    host: str = typer.Option(None),
    port: int = typer.Option(None),
) -> None:
    """Run with the streamable-HTTP transport."""
    _run("http", mode, host, port)


@app.command()
def sse(
    mode: str = _MODE_OPT,
    host: str = typer.Option(None),
    port: int = typer.Option(None),
) -> None:
    """Run with the (legacy) SSE transport."""
    _run("sse", mode, host, port)


def cli_app() -> None:
    """Console-script entrypoint (see [project.scripts])."""
    app()


if __name__ == "__main__":
    app()
