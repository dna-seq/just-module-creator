"""KEY-GATED — registry writes that need a token.

These are ALWAYS listed (so the multi-user HTTP path is safe and discoverable)
and enforce auth PER CALL via ``require_key``. If no token is resolvable for the
current request they return a friendly ``OpResult`` instead of raising — never a
global state flip, so one client can never ride another client's credential.

Authoring, validating and compiling a module need no token. Only these do.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler
from just_dna_format.identity import is_valid_version, validate_namespace
from just_dna_registry import RegistryClient, RegistryError
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

#: Where a publish receipt lands, beside the spec it describes.
#:
#: **The registry is the authority on module identity** — it stamps `namespace`,
#: `owner`, `version` and `canonical_id` on publish and overrides anything
#: authored. Those keys must therefore be *received* and kept, and until now this
#: tool returned them in a message and dropped them: nothing on disk recorded that
#: a spec had ever been published, under what identity, or against which digest.
#:
#: It cannot go into `module_spec.yaml`: `module:` is `extra="forbid"` and those
#: exact keys are rejected there precisely because the registry owns them
#: (upstream `S1`). So it is a sibling file, committed with the spec, in the spec
#: directory rather than a cache or a temp dir — a receipt that does not survive
#: the session is not a record.
RECEIPTS_FILE = "published.json"


def _record_receipt(
    spec_dir: Path,
    *,
    registry_url: str,
    identity: object,
    artifact: object,
    manifest: object,
    fallback: tuple[str, str, str],
) -> tuple[dict, str]:
    """Append the registry-stamped identity to ``published.json``. Never overwrites.

    A published version is **immutable**, so a second receipt for a version we
    already recorded is a fact worth surfacing rather than quietly replacing: the
    existing entry is kept and the difference is reported.
    """
    ns, name, version = fallback
    receipt = {
        "canonical_id": getattr(identity, "canonical_id", None) or f"{ns}/{name}@{version}",
        "namespace": getattr(identity, "namespace", None) or ns,
        "name": getattr(identity, "name", None) or name,
        "version": getattr(identity, "version", None) or version,
        "owner": getattr(identity, "owner", None),
        "artifact_digest": getattr(artifact, "digest", None),
        "content_signature": getattr(manifest, "content_signature", None),
        "registry_url": registry_url,
        # ISO-8601 UTC. Never a naive local timestamp — it is misparsed as local
        # time and breaks string comparison against every other ISO value here.
        "published_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }

    path = spec_dir / RECEIPTS_FILE
    existing: list[dict] = []
    if path.is_file():
        loaded = json.loads(path.read_text() or "[]")
        existing = loaded if isinstance(loaded, list) else [loaded]

    prior = next((r for r in existing if r.get("version") == receipt["version"]), None)
    if prior is not None:
        changed = [
            k
            for k in ("canonical_id", "artifact_digest", "content_signature")
            if prior.get(k) != receipt[k]
        ]
        note = (
            f"{RECEIPTS_FILE} already records {receipt['version']}; kept the original receipt. "
            + (
                f"The registry now reports a different {', '.join(changed)} — a published version "
                "is immutable, so investigate rather than assume the new value is right."
                if changed
                else "It matches."
            )
        )
        return prior, note

    existing.append(receipt)
    path.write_text(json.dumps(existing, indent=2) + "\n")
    return receipt, f"Identity recorded in {RECEIPTS_FILE}; commit it with the spec."


def register_registry(mcp: FastMCP, settings: Settings, store: SessionKeyStore) -> None:
    """Register the token-gated registry tools (tag: registry_write)."""

    def _client(token: str):
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

        if not is_valid_version(version):
            raise ToolError(
                f"{version!r} is not a SemVer version. Use e.g. '1.0.0' — and quote it "
                "in YAML, where an unquoted 1 parses as an int and is rejected."
            )

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

        receipt, note = _record_receipt(
            target,
            registry_url=settings.registry_url,
            identity=identity,
            artifact=artifact,
            manifest=manifest,
            fallback=(namespace, name, version),
        )
        return OpResult(
            success=True,
            message=f"Published {canonical}. {note}",
            data={**receipt, "receipt_file": str(target / RECEIPTS_FILE)},
        )
