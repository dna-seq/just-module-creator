"""KEY-GATED — registry writes that need a token.

These are ALWAYS listed (so the multi-user HTTP path is safe and discoverable)
and enforce auth PER CALL via ``require_key``. If no token is resolvable for the
current request they return a friendly ``OpResult`` instead of raising — never a
global state flip, so one client can never ride another client's credential.

Authoring, validating and compiling a module need no token. Only these do.
"""

from __future__ import annotations

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from just_module_creator.auth import (
    GATED_TAG,
    SessionKeyStore,
    require_key,
    unauthenticated_result,
)
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import OpResult
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import resolve_dir

log = get_logger()


def register_registry(mcp: FastMCP, settings: Settings, store: SessionKeyStore) -> None:
    """Register the token-gated registry tools (tag: registry_write)."""

    def _client(token: str):
        from just_dna_registry import RegistryClient

        return RegistryClient(settings.registry_url, token=token, timeout=settings.registry_timeout)

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Registry: who am I",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_whoami(ctx: Context) -> OpResult:
        """Confirm the registry accepts your token, and report the account it maps to.

        Call this after `authenticate` — nothing local validated the token, so
        this is the first thing that actually checks it.
        """
        token = require_key(ctx, settings, store)
        if token is None:
            return unauthenticated_result(settings)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        from just_dna_registry import RegistryError

        try:
            payload = await run_sync(lambda: _client(token).whoami())
        except RegistryError as exc:
            return OpResult(success=False, message=f"Registry rejected the token: {exc}")
        return OpResult(success=True, message="Token accepted.", data=dict(payload))

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Registry: claim a namespace",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
            openWorldHint=True,
        ),
    )
    async def registry_claim_namespace(namespace: str, ctx: Context) -> OpResult:
        """Claim a publishing namespace. Lowercase, hyphen-separated.

        A namespace is claimed once and then owns every module published under
        it, so this is not a step to run speculatively.
        """
        token = require_key(ctx, settings, store)
        if token is None:
            return unauthenticated_result(settings)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        from just_dna_format.identity import validate_namespace
        from just_dna_registry import RegistryError

        try:
            validate_namespace(namespace)
        except Exception as exc:
            raise ToolError(f"Invalid namespace {namespace!r}: {exc}") from exc

        try:
            payload = await run_sync(lambda: _client(token).claim_namespace(namespace))
        except RegistryError as exc:
            return OpResult(success=False, message=f"Registry error: {exc}")
        return OpResult(success=True, message=f"Claimed {namespace}.", data=dict(payload))

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Registry: publish a module version",
            readOnlyHint=False,
            idempotentHint=False,
            destructiveHint=False,
            openWorldHint=True,
        ),
    )
    async def registry_publish(
        namespace: str,
        name: str,
        version: str,
        spec_dir: str,
        changelog: str = "",
        ctx: Context | None = None,
    ) -> OpResult:
        """Publish a spec directory as a module version. The server recompiles it.

        A published version is immutable, so this is the one irreversible tool
        here. Before calling it: `validate_module(strict=true)` must pass — the
        registry compiles with strict, so a best-effort-only pre-flight answers
        for a different compile.

        Version deliberately. A rebuild that changes *what variants are in the
        module* or how they are grounded is a **major** — someone pinned to the
        old major would otherwise silently receive different content. Write the
        changelog as a continuation of the previous one, not a fresh
        "initial release".
        """
        token = require_key(ctx, settings, store)
        if token is None:
            return unauthenticated_result(settings)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        target = resolve_dir(spec_dir, settings)

        from just_dna_format.identity import is_valid_version
        from just_dna_registry import RegistryError

        if not is_valid_version(version):
            raise ToolError(
                f"{version!r} is not a SemVer version. Use e.g. '1.0.0' — and quote it "
                "in YAML, where an unquoted 1 parses as an int and is rejected."
            )

        # Refuse locally rather than shipping a spec the server will reject.
        from just_dna_compiler import compiler

        pre = await run_sync(lambda: compiler.validate_spec(target, strict=True))
        if not pre.valid:
            return OpResult(
                success=False,
                message=(
                    "Not published: the spec does not pass validate --strict, which is "
                    "what the registry runs. Fix these first."
                ),
                data={"errors": list(pre.errors), "warnings": list(pre.warnings)},
            )

        if ctx:
            await ctx.info(f"Publishing {namespace}/{name}@{version}")

        try:
            manifest = await run_sync(
                lambda: _client(token).publish(
                    namespace, name, version, target, changelog=changelog
                )
            )
        except RegistryError as exc:
            return OpResult(success=False, message=f"Registry refused the publish: {exc}")

        identity = getattr(manifest, "identity", None)
        artifact = getattr(manifest, "artifact", None)
        canonical = getattr(identity, "canonical_id", None) or f"{namespace}/{name}@{version}"
        return OpResult(
            success=True,
            message=f"Published {canonical}.",
            data={
                "canonical_id": getattr(identity, "canonical_id", None),
                "artifact_digest": getattr(artifact, "digest", None),
                "content_signature": getattr(manifest, "content_signature", None),
            },
        )
