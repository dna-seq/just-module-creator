"""The citation graph, and getting somebody else's module onto disk.

``register_citation_graph`` holds one tool: ``paper_citations`` traverses a graph
whose size the corpus decides rather than the caller. It used to be the whole
content of the extended tier, and that tier is gone (0.21.0) — the cost is real,
so it is said in the docstring where the caller reads it, instead of behind a
flag that hid the tool from the sessions most likely to need it.

``register_artifact_reads`` holds ``reverse_module`` and ``registry_download``,
which moved out of the tier on 2026-08-22 when the clause that put them there —
"or that reads back somebody else's compiled artifact" — was deleted rather than
narrowed. It was never a cost argument. Fetching one named version of one named
module is bounded by exactly what the caller named; reversing one artifact
directory is a local read with no network at all.

That clause cost two unattended runs their whole task. Both ran in the default
tier, neither could see ``registry_download``, and both concluded no tool fetches
a published module — one of them wrote a bespoke script against an undocumented
``/files/`` endpoint to get past it. Worse, ``compare_to_published`` was in the
default tier and its docstring hands the caller a ``registry_download`` +
``compare_modules`` pair, so that tier taught a step it could not run. The same
defect had already been fixed for ``enrich_module`` in 0.4.0 and did not
generalise; removing the axis is what finally generalises it.
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
from just_module_creator.targets import (
    client_for,
    instance_note,
)
from just_module_creator.tools._shared import offline_for, resolve_dir

log = get_logger()


def register_citation_graph(
    mcp: FastMCP, settings: Settings, services: NetworkServices
) -> None:
    """Register ``paper_citations``: one tool, and the corpus sizes its work."""

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
        """Papers that cite this one (`citing`), or the papers it cites (`references`).

        **Read the direction names carefully — one of them is a trap.** Everywhere
        else in bibliometrics "cited by" labels the citations a paper *received*
        (Scholar's "Cited by 1,234"), and here the legacy spelling `cited_by`
        means the opposite: the works in its own bibliography. `references` and
        `cites` are accepted as unambiguous spellings of that, and `cited_by`
        still works so nothing scripted against it breaks. If you want "was this
        replicated", you want **`citing`**.

        This is how you ask **whether a finding was replicated**, which is most of
        the `weight` and `state` judgement. One paper reporting an association and
        forty papers reporting it are different evidence, and no other call here
        distinguishes them.

        Semantic Scholar only — it is the source that publishes the graph. Coverage
        is uneven for older clinical literature, so a short list is weak evidence
        of little citation rather than proof of none.

        **Its size is set by the corpus, not by you.** A well-cited paper has
        thousands of citing works, and a traversal follows whatever is there —
        unlike every lookup beside it, which is bounded by the one thing you
        named. Budget for it: this was the whole content of the extended tier
        until 0.21.0, and the tier is gone because hiding it never made a
        traversal cheaper.

        A rate limit or outage comes back as `results=null`, never an empty list:
        "S2 could not answer" and "nobody cited this" are different facts, and the
        second one is a real finding you would act on.
        """
        # The argument check comes FIRST, before the offline ceiling — the same
        # order `registry_publish` uses for its naming refusal and for the same
        # reason: a bad `direction` is decidable without a network, and answering
        # "you are offline" to a call that could never have succeeded sends the
        # caller to fix the wrong thing.
        # `cited_by` is kept because the surface is a contract, and dropped
        # spellings break callers silently. The two clear names are what the
        # docstring leads with; measured live, `cited_by` reads as its own
        # opposite to anyone who has met the phrase anywhere else.
        backwards = {"references", "cites", "cited_by"}
        if direction not in {"citing", *backwards}:
            raise ToolError(
                "`direction` must be 'citing' (papers that cite this one) or 'references' "
                "(the papers it cites; also spelled 'cites' or 'cited_by')."
            )
        direction = "cited_by" if direction in backwards else direction
        _require_network("Citation lookup")
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

def register_artifact_reads(
    mcp: FastMCP, settings: Settings, services: NetworkServices
) -> None:
    """Always registered: get a published module onto disk, and read an artifact back.

    Both are bounded by what the caller named — one version of one module, one
    artifact directory — so neither belongs behind the mode flag. See the module
    docstring for what the flag used to claim and why it was wrong.
    """
    del services  # Neither tool takes a network client; the signature matches its siblings.

    # ----------------------------------------------------------------- #
    # Round-trip
    # ----------------------------------------------------------------- #
    @mcp.tool(
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
        annotations=ToolAnnotations(
            title="Download a registry module",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_download(
        target: RegistryTarget,
        namespace: str,
        name: str,
        version: str,
        dest: str,
        include_inputs: bool = True,
    ) -> OpResult:
        """Download and integrity-verify a published module version.

        Verification happens as part of the download — a failure raises rather
        than writing a module you cannot trust.

        **`include_inputs` defaults to `true` here, and upstream's client defaults
        it to `false`.** That is deliberate rather than an oversight: without it a
        download is the compiled parquets and `manifest.json` alone, and the
        authored CSVs stay on the server — so the published spec, which is the most
        instructive thing a registry holds, would not arrive. Measured against
        `author-b/lactose_tolerance@1.0.0`: 4 files without, 7 with, and the three
        extra are `module_spec.yaml`, `variants.csv` and `studies.csv`. Pass
        `false` when you genuinely want only the artifact.

        With the inputs present you usually do not need `reverse_module` on a
        downloaded module — that tool reconstructs a spec from parquet, and here the
        spec arrived as itself.

        `target` is REQUIRED and has no default. `prod` is the catalog a module
        is installed from; the polygon holds rehearsals, so downloading from it is
        for checking your own — never for consuming somebody's module.
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
            return OpResult(
                success=False, message=f"Registry error: {exc}{instance_note(exc)}"
            )
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
