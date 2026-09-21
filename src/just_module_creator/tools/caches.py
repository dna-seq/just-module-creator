"""Provisioning this machine's snapshot lanes, and the offer that goes with it.

One tool, because there is one question — *what would it cost and shall I do it* — and
splitting it would let a caller act on a price it never read. `dry_run` defaults to
`True`, so the expensive answer is never the default one.

The logic is in `provisioning.py`; this file is the wire shape and the docstring an agent
reads. Local only: there is no `target`, because the question is about this box.
"""

from __future__ import annotations

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from just_module_creator import provisioning
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import CachePlan
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import offline_for

log = get_logger()


def register_caches(mcp: FastMCP, settings: Settings) -> None:
    """Register `provision_caches`.

    Registered unconditionally, which used to be the interesting claim: on an enricher
    with no lane registry it reported `lanes_known=false` rather than vanishing, because
    a tool that is absent teaches nothing about why. The `>=0.7.0` floor retired that
    state — every install has the registry — so the field went and the tool stayed.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            title="What the snapshot caches would cost here, and build them",
            read_only_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        )
    )
    async def provision_caches(
        dry_run: bool = True,
        lanes: list[str] | None = None,
        declared_use: str = "unstated",
    ) -> CachePlan:
        """Price this machine's snapshot caches, and provision them when asked.

        **Call this once at the top of a session, before offering anything.** It measures
        the disk, prices every lane, and answers the only question a prompt needs:
        `offer` names the offer still open, or is null for *say nothing*. Null is the
        common answer — already provisioned, already answered, nothing that fits — and it
        means exactly that.

        Ten of the fifteen lanes are published parquet, so a pull or a registry proxy
        serves them. **Five are not ours to publish**: PharmVar's bulk data needs a
        personal key, PubMind's source states no terms, NCBI states a policy rather than
        a licence for MANE, the ACMG list is Elsevier supplementary material, and
        `mitomap_miss` is a join nobody distributes. Each carries that sentence. For those
        five there is no pull and no proxy — building here is the only route there will
        ever be, and together they are about 15 MB. That is the `prewarm` offer. `full` is
        the whole provisionable surface, Ensembl's 14 GB included, offered only once the
        small set is done and the disk has room.

        `dry_run=True` (the default) measures and writes nothing. `dry_run=False`
        provisions `lanes`, or the `prewarm` set when you name none, each through the
        enricher's own route; a lane already here is left alone, and a directory holding
        no snapshot is refused rather than built over. State `prewarm_build_mb` and
        `prewarm_pull_mb` separately when you ask: a derived lane is small and pins a
        parent that is not.

        `declared_use` records the author's own licence declaration and its vocabulary is
        upstream's (`just_dna_format`'s `VALID_DECLARED_USE`, reported by
        `authoring_reference`). Four lanes forbid sale, and with nothing declared their
        download is **skipped** rather than assumed — the tool may not declare a purpose
        on somebody's behalf. Sizes are estimates measured on a provisioned box and dated
        in the source, not declarations by the lane; a lane already here reports what it
        measures beside the estimate, and an unmeasured one reports null rather than a guess.
        """
        if not dry_run and offline_for(settings, False):
            raise ToolError(
                "JMC_OFFLINE is set and provisioning is egress — a pull downloads and four "
                "of the five buildable lanes fetch their inputs. Re-run with dry_run=true "
                "to read the plan, which touches nothing."
            )
        if dry_run:
            return await run_sync(
                lambda: provisioning.plan(declared_use=declared_use, settings=settings)
            )
        return await run_sync(
            lambda: provisioning.provision(lanes, declared_use=declared_use, settings=settings)
        )
