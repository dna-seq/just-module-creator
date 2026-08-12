"""EXTENDED — registered ONLY when mode == "extended".

What is left here after the tier was widened: the three tools whose cost is not
bounded by what you named. ``paper_citations`` traverses a citation graph whose
size the corpus decides, and ``reverse_module`` / ``registry_download`` are about
reading back somebody *else's* compiled artifact rather than authoring your own.
Opt in via ``JMC_MODE=extended`` / ``--mode extended``.

Everything a module of your own actually needs now lives in the always-on tiers:
the schema dump and integrity checks in ``authoring``, identifier and paper reads
in ``research``, and ``enrich_module`` beside ``draft_from_clinvar`` in
``passes`` — the two tools that fetch and then write into a spec directory.
"""

from __future__ import annotations

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler
from just_dna_registry import RegistryError
from mcp.types import ToolAnnotations

from just_module_creator.discovery import citation_graph
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CitationGraph,
    OpResult,
)
from just_module_creator.net import NetworkServices
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import DEFAULT_CATALOG_TARGET, client_for
from just_module_creator.tools._shared import offline_for, resolve_dir

log = get_logger()


def register_extended(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the extended-only tools."""

    # ----------------------------------------------------------------- #
    # Reading a paper
    # ----------------------------------------------------------------- #
    def _require_network(what: str) -> None:
        if offline_for(settings, False):
            raise ToolError(
                f"{what} needs the network and the server is configured offline (JMC_OFFLINE). "
                "There is no offline literature snapshot."
            )

    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Who cited this paper",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def paper_citations(
        pmid: str | None = None,
        doi: str | None = None,
        arxiv_id: str | None = None,
        direction: str = "citing",
        limit: int = 20,
    ) -> CitationGraph:
        """Papers citing this one (`citing`) or cited by it (`cited_by`).

        This is how you ask **whether a finding was replicated**, which is most of
        the `weight` and `state` judgement. One paper reporting an association and
        forty papers reporting it are different evidence, and no other call here
        distinguishes them.

        Semantic Scholar only — it is the source that publishes the graph. Coverage
        is uneven for older clinical literature, so a short list is weak evidence
        of little citation rather than proof of none.

        A rate limit or outage comes back as `results=null`, never an empty list:
        "S2 could not answer" and "nobody cited this" are different facts, and the
        second one is a real finding you would act on.
        """
        _require_network("Citation lookup")
        if direction not in {"citing", "cited_by"}:
            raise ToolError("`direction` must be 'citing' or 'cited_by'.")
        identifier = (
            f"PMID:{pmid}"
            if pmid
            else (f"DOI:{doi}" if doi else (f"ARXIV:{arxiv_id}" if arxiv_id else None))
        )
        if not identifier:
            raise ToolError("Provide a pmid, doi or arxiv_id.")
        return await run_sync(
            lambda: citation_graph(services, paper_id=identifier, direction=direction, limit=limit)
        )

    # ----------------------------------------------------------------- #
    # Round-trip
    # ----------------------------------------------------------------- #
    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Reverse an artifact to a spec",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        ),
    )
    async def reverse_module(parquet_dir: str, output_dir: str) -> OpResult:
        """Turn a compiled artifact back into an authored spec directory.

        Use it to recover a spec from a compiled-only module, or to prove a
        round-trip: `module_signature` on the original spec and on the reversed
        one must match. That fixed point is what the format guarantees.
        """
        source = resolve_dir(parquet_dir, settings)
        out = resolve_dir(output_dir, settings, must_exist=False)
        written = await run_sync(lambda: compiler.reverse_module(source, out))
        return OpResult(
            success=True,
            message=f"Spec written to {written}.",
            data={
                "spec_dir": str(written),
                "next": "Compare `module_signature` on this and on the original spec.",
            },
        )

    # ----------------------------------------------------------------- #
    # Registry reads
    # ----------------------------------------------------------------- #
    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Download a registry module",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_download(
        namespace: str,
        name: str,
        version: str,
        dest: str,
        include_inputs: bool = True,
        target: RegistryTarget = DEFAULT_CATALOG_TARGET,
    ) -> OpResult:
        """Download and integrity-verify a published module version.

        Verification happens as part of the download — a failure raises rather
        than writing a module you cannot trust.

        **`include_inputs` defaults to `true` here, and upstream's client defaults
        it to `false`.** That is deliberate rather than an oversight: without it a
        download is the compiled parquets and `manifest.json` alone, and the
        authored CSVs stay on the server — so the published spec, which is the most
        instructive thing a registry holds, would not arrive. Measured against
        `eric-mods/lactose_tolerance@1.0.0`: 4 files without, 7 with, and the three
        extra are `module_spec.yaml`, `variants.csv` and `studies.csv`. Pass
        `false` when you genuinely want only the artifact.

        With the inputs present you usually do not need `reverse_module` on a
        downloaded module — that tool reconstructs a spec from parquet, and here the
        spec arrived as itself.

        `target` defaults to production, the catalog a module is installed from.
        The polygon holds rehearsals, so downloading from it is for checking your
        own — never for consuming somebody's module.
        """
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")
        dest_dir = resolve_dir(dest, settings, must_exist=False)

        def _download():
            client = client_for(target, settings)
            # `layout` stays flat and is not exposed. 0.14 added `layout="split"`,
            # which emits the enricher's files under `derived/` — genuinely useful
            # for seeing which files an author wrote, and a tree
            # `just-dna-compiler compile` REFUSES, because it wants the authored
            # tables at the spec root. Offering it from an authoring surface would
            # hand someone a directory that cannot be rebuilt.
            return client.download(
                namespace, name, version, dest_dir, include_inputs=include_inputs
            )

        try:
            manifest = await run_sync(_download)
        except RegistryError as exc:
            return OpResult(success=False, message=f"Registry error: {exc}")
        identity = getattr(manifest, "identity", None)
        return OpResult(
            success=True,
            message=f"Downloaded and verified into {dest_dir}.",
            data={
                "dest": str(dest_dir),
                "target": target,
                "canonical_id": getattr(identity, "canonical_id", None),
            },
        )
