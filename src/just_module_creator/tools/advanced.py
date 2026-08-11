"""EXTENDED — registered ONLY when mode == "extended".

The "register on start" half of the hybrid pattern: enrichment, integrity,
round-trip and the full generated schema dump. Real work, but not the loop you
need on every module, so casual clients do not pay the context cost. Opt in via
``JMC_MODE=extended`` / ``--mode extended``.

``enrich_module`` is a real MCP background task: it fetches per variant and a
panel-sized module takes minutes, so the client gets a task id immediately and
polls.
"""

from __future__ import annotations

import json

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler
from just_dna_enricher import lookup as enricher_lookup
from just_dna_enricher.enrich import EnrichmentError, enrich
from just_dna_enricher.identifiers import check_identifiers as _check_identifiers
from just_dna_format import reference
from just_dna_format.integrity import IntegrityError, verify_manifest
from just_dna_format.manifest import read_manifest
from just_dna_registry import RegistryClient, RegistryError
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    EnrichReport,
    IdentifierReport,
    IdentifierStatus,
    OpResult,
    SignatureResult,
    VerifyResult,
)
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import offline_for, resolve_dir

log = get_logger()

_REGENERATE_NOTE = (
    "An existing sidecar is authoritative and merged, never clobbered. To "
    "regenerate resolution.csv after changing the spec you must DELETE it first, "
    "or stale rows persist silently. Moving it aside and re-enriching is also the "
    "only way to ask whether an injected table still agrees with the sources."
)


def register_extended(mcp: FastMCP, settings: Settings) -> None:
    """Register the extended-only tools."""

    # ----------------------------------------------------------------- #
    # Full schema dump
    # ----------------------------------------------------------------- #
    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Authoring reference", readOnlyHint=True, idempotentHint=True
        ),
    )
    def authoring_reference(schemas: bool = False) -> str:
        """The complete generated description of the authoring DSL, as JSON.

        Every model, column, vocabulary and one-of rule at once, generated from
        the live pydantic models. Large — prefer `describe_table` for one table.
        Pass `schemas=true` for raw JSON Schema instead of the summary form.
        """
        payload = reference.json_schemas() if schemas else reference.authoring_reference()
        return json.dumps(payload, indent=2, default=str)

    # ----------------------------------------------------------------- #
    # Enrichment (network)
    # ----------------------------------------------------------------- #
    @mcp.tool(
        tags={"extended"},
        task=True,
        annotations=ToolAnnotations(
            title="Enrich a spec (resolve coordinates)",
            readOnlyHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def enrich_module(
        spec_dir: str,
        strict: bool = False,
        offline: bool = False,
        ctx: Context | None = None,
    ) -> EnrichReport:
        """Resolve rsIDs to coordinates and mint VRS ids, writing resolution.csv.

        The only step that fetches, and the only thing that can catch the mistake
        no offline gate can: it compares your authored `ref` against the actual
        genome and reports `ref mismatch: N row(s) — coordinate shifted 1 base`.
        **Read that line as being about `start`, not `ref`** — it is what
        subtracting one from a VCF position produces. It is a floor, not a total:
        only rows whose neighbouring base differs from `ref` are visible.

        Runs as a background task: you get a task id immediately and poll.

        Curate before you enrich. A `<<REPLACE>>` anywhere makes every loader
        refuse the file, this one included — deliberately, since forward
        resolution is allele-aware and a placeholder genotype would skip the
        allele filter on exactly the rsIDs that need it.

        `offline=true` restricts to local caches, where the ref check does not
        run at all. A check that could not run is not a check that passed.
        """
        target = resolve_dir(spec_dir, settings)
        eff_offline = offline_for(settings, offline)
        mode = "strict" if strict else "best_effort"

        if ctx:
            await ctx.info(
                f"Enriching {target.name} (mode={mode}, "
                f"{'cache-only' if eff_offline else 'network'})"
            )
            await ctx.report_progress(progress=1, total=3)

        try:
            result = await run_sync(
                lambda: enrich(target, mode=mode, offline=eff_offline, write=True)
            )
        except EnrichmentError as exc:
            return EnrichReport(
                success=False,
                spec_dir=str(target),
                mode=mode,
                offline=eff_offline,
                resolved=0,
                unresolved=[],
                sources=[],
                ref_mismatches=[],
                clin_sig_conflicts=[],
                stale_rsids=[],
                warnings=[str(exc)],
                note=_REGENERATE_NOTE,
            )

        if ctx:
            await ctx.report_progress(progress=3, total=3)

        vrs = getattr(result, "vrs", None)
        mismatches = [str(m) for m in getattr(result, "ref_mismatches", []) or []]
        warnings: list[str] = []
        if eff_offline and not mismatches:
            warnings.append(
                "No ref mismatches reported — but this ran offline, where the check "
                "needs sequence access and therefore did not run at all."
            )
        return EnrichReport(
            success=True,
            spec_dir=str(target),
            mode=mode,
            offline=eff_offline,
            resolved=len(getattr(result, "rows", []) or []),
            unresolved=[str(u) for u in getattr(result, "unresolved", []) or []],
            sources=[str(s) for s in getattr(result, "sources", []) or []],
            ref_mismatches=mismatches,
            clin_sig_conflicts=[str(c) for c in getattr(result, "clin_sig_conflicts", []) or []],
            clin_sig_not_checked=getattr(result, "clin_sig_not_checked", None),
            stale_rsids=[str(s) for s in getattr(result, "stale_rsids", []) or []],
            vrs_minted=getattr(vrs, "minted", None) if vrs else None,
            warnings=warnings,
            note=_REGENERATE_NOTE,
        )

    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Check identifiers",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_identifiers(spec_dir: str) -> IdentifierReport:
        """Check every gene symbol (HGNC) and trait CURIE (OLS4) in a spec is current.

        Reports, never repairs — rewriting an authored value would destroy the
        evidence of the upstream change. Writes nothing.
        """
        target = resolve_dir(spec_dir, settings)
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE); this check needs HGNC and OLS4."
            )
        report = await run_sync(lambda: _check_identifiers(spec_dir=target))

        genes = [
            IdentifierStatus(
                identifier=g.symbol,
                kind="gene",
                state=g.state,
                current=g.current,
                label=g.hgnc_id,
            )
            for g in getattr(report, "genes", []) or []
        ]
        traits = [
            IdentifierStatus(
                identifier=t.curie,
                kind="trait",
                state=t.state,
                current=t.replaced_by,
                label=t.label,
            )
            for t in getattr(report, "traits", []) or []
        ]
        stale = [
            f"{s.kind} {s.identifier}: {s.state}" + (f" -> {s.current}" if s.current else "")
            for s in genes + traits
            if s.state not in {"approved", "current"}
        ]
        return IdentifierReport(spec_dir=str(target), genes=genes, traits=traits, stale=stale)

    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Look up a gene or trait",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def lookup_identifier(kind: str, identifier: str) -> IdentifierStatus:
        """Check one gene symbol or trait CURIE. `kind` is "gene" or "trait".

        A gene comes back approved / retired / unknown; a trait current /
        obsolete / absent. Writes nothing.
        """
        if kind not in {"gene", "trait"}:
            raise ToolError('kind must be "gene" or "trait".')
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        if kind == "gene":
            status = await run_sync(lambda: enricher_lookup.lookup_gene(identifier))
            return IdentifierStatus(
                identifier=status.symbol,
                kind="gene",
                state=status.state,
                current=status.current,
                label=status.hgnc_id,
            )
        status = await run_sync(lambda: enricher_lookup.lookup_trait(identifier))
        return IdentifierStatus(
            identifier=status.curie,
            kind="trait",
            state=status.state,
            current=status.replaced_by,
            label=status.label,
        )

    # ----------------------------------------------------------------- #
    # Integrity and round-trip
    # ----------------------------------------------------------------- #
    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Content signature", readOnlyHint=True, idempotentHint=True
        ),
    )
    async def module_signature(spec_dir: str) -> SignatureResult:
        """The content signature of the raw authored data. No compile, no network.

        Use it to tell whether two specs are the same content, and to check a
        `reverse` round-trip. It folds module_spec.yaml's `defaults:` into each
        row before hashing, so a value written once under `defaults:` and the
        same value repeated on every row are one content.
        """
        target = resolve_dir(spec_dir, settings)
        sig = await run_sync(lambda: compiler.content_signature(target))
        return SignatureResult(
            spec_dir=str(target),
            content_signature=sig,
            note=(
                "Covers the authored content only — not the compiled artifact. "
                "artifact.digest is a different hash and moves whenever sources.csv "
                "re-stamps fetched_at, so a digest change is not evidence that "
                "content changed."
            ),
        )

    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Verify an artifact", readOnlyHint=True, idempotentHint=True
        ),
    )
    async def verify_artifact(
        module_dir: str, public_key: str | None = None, require_marketplace: bool = False
    ) -> VerifyResult:
        """Re-hash every file in a compiled artifact and recompute the digest.

        Without `public_key` the signature is NOT checked — `signature_checked`
        says so, and an unchecked signature is not a valid one.
        """
        target = resolve_dir(module_dir, settings)
        manifest_path = target / "manifest.json"
        if not manifest_path.is_file():
            raise ToolError(f"No manifest.json in {target}.")

        manifest = await run_sync(lambda: read_manifest(manifest_path))
        identity = getattr(manifest, "identity", None)
        artifact = getattr(manifest, "artifact", None)

        try:
            await run_sync(
                lambda: verify_manifest(
                    target,
                    manifest,
                    require_marketplace=require_marketplace,
                    public_key=public_key,
                )
            )
        except IntegrityError as exc:
            return VerifyResult(
                verified=False,
                module_dir=str(target),
                artifact_digest=getattr(artifact, "digest", None),
                canonical_id=getattr(identity, "canonical_id", None),
                signature_checked=public_key is not None,
                message=str(exc),
            )
        return VerifyResult(
            verified=True,
            module_dir=str(target),
            artifact_digest=getattr(artifact, "digest", None),
            canonical_id=getattr(identity, "canonical_id", None),
            signature_checked=public_key is not None,
            message=(
                "Every file re-hashed and the digest recomputed."
                if public_key
                else "Digests verified. The SIGNATURE was not checked — pass "
                "public_key to check it."
            ),
        )

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
            title="Get a registry module",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_get_module(namespace: str, name: str) -> OpResult:
        """Fetch one module's full registry record: card, readme, versions, manifest.

        The best available worked example — the published spec of a real module
        is more instructive than any template.
        """
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        def _get() -> dict:
            client = RegistryClient(settings.registry_url, timeout=settings.registry_timeout)
            return client.get_module(namespace, name)

        try:
            payload = await run_sync(_get)
        except RegistryError as exc:
            return OpResult(success=False, message=f"Registry error: {exc}")
        return OpResult(success=True, message=f"{namespace}/{name}", data=dict(payload))

    @mcp.tool(
        tags={"extended"},
        annotations=ToolAnnotations(
            title="Download a registry module",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_download(namespace: str, name: str, version: str, dest: str) -> OpResult:
        """Download and integrity-verify a published module version.

        Verification happens as part of the download — a failure raises rather
        than writing a module you cannot trust.
        """
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")
        target = resolve_dir(dest, settings, must_exist=False)

        def _download():
            client = RegistryClient(settings.registry_url, timeout=settings.registry_timeout)
            return client.download(namespace, name, version, target)

        try:
            manifest = await run_sync(_download)
        except RegistryError as exc:
            return OpResult(success=False, message=f"Registry error: {exc}")
        identity = getattr(manifest, "identity", None)
        return OpResult(
            success=True,
            message=f"Downloaded and verified into {target}.",
            data={
                "dest": str(target),
                "canonical_id": getattr(identity, "canonical_id", None),
            },
        )
