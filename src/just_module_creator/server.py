"""FastMCP server: assembly, CLI, and deployment entrypoints.

The hybrid registration pattern lives in ``build_server``:

* ``register_essentials`` — always. The offline authoring loop, the schema dump
  and the integrity checks. Touches no network.
* ``register_research``   — always. Read-only lookups: variants, citations,
  literature, identifiers, papers, registry reads. No token, network-tier.
* ``register_auth``       — always. ``registry_register`` (mints a token, so it
  cannot be gated by one) and the per-session ``authenticate``.
* ``register_registry``   — always listed, token enforced per call.
* ``register_passes``     — always. The two tools that fetch and then write into
  a spec directory: ``draft_from_clinvar`` (step 2) and ``enrich_module``
  (step 6). Both are named in the workflow INSTRUCTIONS teach, which is why
  neither can sit behind a mode flag.
* ``register_extended``   — ONLY when mode == "extended" (registered on start).
* ``register_extended_passes`` — extended. PGx drafting and the bulk fact passes.
* ``register_refresh``    — extended. ``refresh_sidecar``: capture, delete,
  re-derive, reapply what is provably the author's, report the rest. Extended
  because it runs whichever pass owns the sidecar, up to and including the
  GWAS one, so essentials would reach an extended budget by another door.

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
from just_module_creator.net import build_services
from just_module_creator.settings import Mode, Settings
from just_module_creator.tools._shared import schema_versions
from just_module_creator.tools.advanced import register_extended
from just_module_creator.tools.authoring import register_essentials
from just_module_creator.tools.passes import register_extended_passes, register_passes
from just_module_creator.tools.refresh import register_refresh
from just_module_creator.tools.registry import register_registry
from just_module_creator.tools.research import register_research

log = get_logger()

# An f-string, and never a literal version: the header names the toolchain that
# is actually loaded, so an agent reading the instructions can see at a glance
# that a stale plugin cache is answering. It said "format 0.5" for two releases
# while the installed format was 0.6.
INSTRUCTIONS = f"""\
Authoring surface for just-dna annotation modules. Every schema answer here is
generated from just-dna-format {schema_versions().format_version} and
just-dna-compiler {schema_versions().compiler_version}: if either is older than
what you installed, a stale process is answering and its column lists are wrong.

A module is a directory of authored CSVs plus module_spec.yaml, compiled into a
parquet artifact with a content-addressed manifest. Work in this order:

  list_tables -> scaffold_module -> draft_from_clinvar (if a source publishes
    the table) -> literature_search -> author rows -> lint_rows
    -> validate_module(strict) -> enrich_module -> compile_module(strict)

Five rules this server enforces rather than merely documents:

1. Ask the tool, never memory. Every column list, vocabulary and requirement is
   generated from the live pydantic models, so describe_table /
   table_requirements cannot drift from what the compiler accepts. That holds for
   the files a pass writes too: describe_machine_table answers the columns of
   resolution.csv and the fact sidecars, and says what a hand-written cell there
   costs and how to mark one so it stays distinguishable from a fetched fact.
2. You may WRITE, and every write is logged. This is the authoring layer and the
   business decision is delegated here, so filling or correcting a cell is
   legitimate where the same act inside the compiler would not be. Two kinds of
   cell are still withheld, and neither is a refusal to write on principle: a
   value a later check compares against THAT SAME source (filling `doi` from the
   record that just gave you the PMID makes the check compare PubMed with
   itself — the value is shown so you can compare it, not paste it), and a value
   only a pilot can settle (a genotype, a weight, a conclusion, a direction).
   Where a lookup reports `applied: false` with a `refusal`, that is upstream
   reporting what IT did and is passed through verbatim; your own writes are
   yours, logged as yours, never laundered as upstream's.
3. A mismatch against a source is not a defect report. Archives lag the edge: a
   paper is retracted, a meta-analysis refutes it, a bigger cohort moves the
   call. A row that disagrees with ClinVar may be the module being right and
   current while the archive is stale, so conforming it to the source silently
   DEGRADES the module — and the check then agrees with itself and reports
   green. Editing against a source needs a reason that outranks the source, and
   that reason gets written down. An outranked row keeps warning: "somebody
   decided this" never means green, because two releases on nobody remembers
   whether the retraction that motivated it was itself superseded.
4. A check that could not run is not a check that passed. `null` and `unknown`
   never collapse into a pass, and warnings on a green run are the interesting
   output.

5. Take every PMID from a literature_search result, never from memory. PMIDs are
   dense enough that a recalled one is usually a real record for a different
   paper, so existence never settles identity — only a title does. Both
   lookup_citation and literature_search report one; read it and compare it
   against the paper you meant.

`start` is always the 1-based VCF position: paste it, never subtract one.

The tiers split on COST, not on usefulness. Essentials is everything whose work
is bounded by what you named — one identifier, one paper, one spec directory —
which is the whole order above plus the checks around it. extended
(JMC_MODE=extended) adds only what a corpus sizes: the citation graph, the PGx
drafters, the bulk fact passes, and reading back somebody else's compiled
artifact. Publishing needs a registry token; nothing else does.

The registry runs TWO instances and every registry tool takes `target`:

  target="test"  the polygon — where a publish is a REHEARSAL. It accepts
                 `test-`prefixed data and, alone, will delete it again.
  target="prod"  the published catalog everyone installs from.

Rehearse first, always. On production a version is immutable AND its authored
data is claimed by a content hash that `yank` does not release, so one botched
publish burns the version number and the right to publish that data under any
other name, permanently. On the polygon, `registry_delete_version` frees both.

So the write tools — register, authenticate, whoami, namespace_available,
claim_namespace, publish, and the pre-flights validate/check — default to `test`,
and going live is an explicit `target="prod"`. The catalog reads — registry_search,
registry_get_module, registry_download, registry_is_published — default to `prod`,
because that is the world they ask about.

BEFORE a publish, ask whether it would publish. registry_check is the full dry run
and spends no version number; registry_validate is its module-level half. Read
`verdict` with care: `null` means the dry run did not reach one and is NEVER a
pass, and `module_level_clear` means "nothing module-level blocks this", never
"this will publish". A false verdict beside `rerun_rather_than_fix` means RE-RUN,
not go and change the spec — a strict publish against an unreachable Ensembl
really does refuse while the variants may be perfectly findable.

registry_health reports an instance's own mode, so a rehearsal can be confirmed
rather than assumed. registry_is_published needs no token and uploads nothing: it
answers "is this data already published, under any name" from a local signature.
The instances share no database: an account, a token and a namespace exist on one
of them only, so register on each and promote by publishing again.

The polygon is the default ANSWER too, not merely the default argument. Publish
there, name it out loud, and stop — unless the author asked for the real catalog
in their own words. "Publish it", "put it online", "share it with my friends" is
NOT that ask: it is somebody who does not know there are two registries. Promoting
is a separate decision they make after seeing a clean run, and it wants an explicit
yes with the cost stated IN the question, because neither
claim_namespace(target="prod") nor publish(target="prod") can be undone by anyone.
For a first module prefix the module name as well as the namespace — the operator's
purge sweep matches both halves, so `test_x` under `test-ns` cleans itself up where
a bare `x` is litter the author must remember to delete.

That default is against ASSUMING, not against advocating. When the catalog is
genuinely missing a module — `registry_search` reads prod, so ask it rather than
guessing — and yours clears every bar (strict validate and strict compile,
fully_resolved, produced not authored resolution.csv, every PMID from a search
result whose title you read, a declared licence, no state or direction settled by
guessing, a rehearsal read back, and enough breadth to be worth an immutable
version), then raise production yourself, with the search result and the checks as
evidence. Underrepresented is necessary and nowhere near sufficient: an honest
module and a module worth an immutable 1.0.0 are different standards, and a stub
occupies the search result a real module would have had. Advocating never skips the
explicit yes on claim_namespace(target="prod") or publish(target="prod").

Onboarding is self-service and needs no token to start: `registry_register` mints
an account and stores its key for the session, `registry_namespace_available`
checks a name, and `registry_claim_namespace` takes it — that last step is
irreversible on production. `authenticate` is for a token you already hold.

Account and namespace names are lowercase-with-hyphens and reject underscores;
module names are the opposite and take underscores. Both rules are enforced, not
normalised.

A provenance_quote is a passage located in the article, and YOU may locate it:
fetch_fulltext returns the text so you can read it, and a passage you found there
is a real reading. Quote it verbatim, for the specific claim the row makes, and
say who located it. Never the article's TITLE — a title appears in its own
fulltext, so quotes_found goes green over metadata nobody had to read, which is
how four published modules came to carry a quote on all 3668 rows with the title
in every one. Say plainly that a quote you located is not independent evidence of
the claim once you have read that fulltext: it has become a citation-pairing
check, which still catches a passage filed against the wrong paper.

Ask the author, once, near the start: do they want the papers read at all (it
costs requests and time, and some modules do not need it), and may their email be
used for lookups? NCBI's polite pool and Unpaywall
meter and contact PER ADDRESS, so unconfigured means their usage shares one budget
with every other unconfigured install and a problem reaches the project rather
than them. Ask only when neither JMC_USER_EMAIL nor JUST_DNA_CONTACT_EMAIL is set,
write an agreed address to `.env` as JMC_USER_EMAIL so it outlives the session, and
take no for an answer — a default is configured, so nothing breaks. NEVER invent or
INFER an address (not from git config, a commit, or the registry account): one the
author did not offer is personal data volunteered on their behalf.
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
    # One shared client set for the whole server. Lazy: constructing it opens no
    # connection, so importing this module still touches no network.
    services = build_services(settings)

    register_essentials(mcp, settings)
    register_research(mcp, settings, services)
    register_auth(mcp, settings, store)
    register_registry(mcp, settings, store)
    register_passes(mcp, settings, services)
    if resolved_mode == "extended":
        register_extended(mcp, settings, services)
        register_extended_passes(mcp, settings, services)
        register_refresh(mcp, settings, services)

    log.info(
        "Server built (mode=%s, offline=%s, registry=%s, polygon=%s)",
        resolved_mode,
        settings.offline,
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
