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
from just_dna_registry import RegistryError
from mcp.types import ToolAnnotations

from just_module_creator.auth import (
    GATED_TAG,
    SessionKeyStore,
    require_key,
    unauthenticated_result,
)
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import OpResult
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import (
    DEFAULT_WRITE_TARGET,
    client_for,
    describe,
    polygon_naming_note,
    prod_refusal,
)
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
    target: RegistryTarget,
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

    **Prior receipts are matched on version AND target.** A polygon rehearsal of
    1.0.0 is not a prior publish of production's 1.0.0 — treating it as one would
    make the real publish look like a duplicate and hide the identity the
    registry stamped on it. Rehearsals stay in the file on purpose: which
    versions were rehearsed, and where, is part of the record.
    """
    ns, name, version = fallback
    receipt = {
        "target": target,
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

    prior = next(
        (
            r
            for r in existing
            # `target` is absent from receipts written before the split; those
            # were all production publishes, which is what the default reads as.
            if r.get("version") == receipt["version"] and r.get("target", "prod") == target
        ),
        None,
    )
    if prior is not None:
        changed = [
            k
            for k in ("canonical_id", "artifact_digest", "content_signature")
            if prior.get(k) != receipt[k]
        ]
        note = (
            f"{RECEIPTS_FILE} already records {receipt['version']} on {target}; kept the original "
            "receipt. "
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

    def _client(token: str, target: RegistryTarget):
        return client_for(target, settings, token=token)

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Registry: who am I",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_whoami(
        ctx: Context, target: RegistryTarget = DEFAULT_WRITE_TARGET
    ) -> OpResult:
        """Confirm one registry instance accepts your token, and report the account.

        Call this after `authenticate` — nothing local validated the token, so
        this is the first thing that actually checks it.

        `target` picks the instance and defaults to the polygon. An account lives
        on one instance only, so this answers for that one: a token accepted here
        says nothing about the other.
        """
        token = require_key(ctx, settings, store, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            payload = await run_sync(lambda: _client(token, target).whoami())
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} rejected the token: {exc}. A token issued by "
                    "the other instance is an unknown key here, not a weaker one — check which "
                    "one you stored."
                ),
                data={"target": target, "registry_url": settings.registry_url_for(target)},
            )
        return OpResult(
            success=True,
            message=f"Token accepted by {describe(target, settings)}.",
            data={**dict(payload), "target": target},
        )

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
    async def registry_claim_namespace(
        namespace: str, ctx: Context, target: RegistryTarget = DEFAULT_WRITE_TARGET
    ) -> OpResult:
        """Claim a publishing namespace. Irreversible on production — check it first.

        A namespace is claimed once and then owns every module published under
        it, so this is not a step to run speculatively. Call
        `registry_namespace_available` first: it is read-only, needs no token, and
        answers both halves of the question.

        `target` picks the instance and defaults to the polygon, where a claim is
        recoverable — an operator's `purge-test-data` sweeps `test-`prefixed
        namespaces. On production a claim is permanent, and production refuses a
        `test-`prefixed namespace outright: rehearse under that spelling on the
        polygon, and claim the real name on production once.

        Legal names are lowercase letters and digits with single hyphens between
        them. An underscore is **rejected**, not normalised, so `my_ns` fails —
        and the same rule governs your *account* name. Module names use the
        opposite convention and do take underscores, which is why a spec can hold
        `my-ns/lactose_tolerance`.
        """
        # Name checks before credentials, for the reason given in registry_publish.
        try:
            validate_namespace(namespace)
        except Exception as exc:
            raise ToolError(f"Invalid namespace {namespace!r}: {exc}") from exc

        refusal = prod_refusal(target, namespace=namespace)
        if refusal is not None:
            return OpResult(
                success=False,
                message=f"Nothing was claimed. {refusal}",
                data={"target": target, "namespace": namespace},
            )

        token = require_key(ctx, settings, store, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            payload = await run_sync(lambda: _client(token, target).claim_namespace(namespace))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=f"{describe(target, settings)} refused the claim: {exc}",
                data={"target": target, "namespace": namespace},
            )
        note = polygon_naming_note(target, namespace=namespace)
        return OpResult(
            success=True,
            message=f"Claimed {namespace} on {describe(target, settings)}."
            + (f" {note}" if note else ""),
            data={**dict(payload), "target": target},
        )

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
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
        ctx: Context | None = None,
    ) -> OpResult:
        """Publish a spec directory as a module version. The server recompiles it.

        **`target` defaults to the polygon, where publishing is a rehearsal.**
        Rehearse first, always. On production a published version is immutable
        AND its authored data is claimed by a content hash that `yank` does not
        release, so a botched publish there burns the version number *and* the
        right to publish that data under any other name — permanently. On the
        polygon, `registry_delete_version` frees both and you go again.

        Publish for real with `target="prod"` once the rehearsal is clean. The
        two instances share no data, so a polygon publish never becomes a
        production one: promoting means publishing again.

        Before either: `validate_module(strict=true)` must pass — the registry
        compiles with strict, so a best-effort-only pre-flight answers for a
        different compile.

        Version deliberately. A rebuild that changes *what variants are in the
        module* or how they are grounded is a **major** — someone pinned to the
        old major would otherwise silently receive different content. Write the
        changelog as a continuation of the previous one, not a fresh
        "initial release".
        """
        # The naming refusal comes FIRST, before the credential and before the
        # offline ceiling: it needs neither to be decided, and telling an author
        # to go and get a token for a call that could never succeed is the dead
        # end this surface keeps removing.
        refusal = prod_refusal(target, namespace=namespace, name=name)
        if refusal is not None:
            return OpResult(
                success=False,
                message=f"Nothing was published. {refusal}",
                data={"target": target, "namespace": namespace, "name": name},
            )

        token = require_key(ctx, settings, store, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        spec = resolve_dir(spec_dir, settings)

        if not is_valid_version(version):
            raise ToolError(
                f"{version!r} is not a SemVer version. Use e.g. '1.0.0' — and quote it "
                "in YAML, where an unquoted 1 parses as an int and is rejected."
            )

        pre = await run_sync(lambda: compiler.validate_spec(spec, strict=True))
        if not pre.valid:
            return OpResult(
                success=False,
                message=(
                    "Not published: the spec does not pass validate --strict, which is "
                    "what the registry runs. Fix these first."
                ),
                data={"errors": list(pre.errors), "warnings": list(pre.warnings)},
            )

        # The dedup pre-flight. `content_signature` is computed locally from the
        # authored rows — no upload, no recompile — and the registry gates
        # `409 duplicate_content` on that same value. Worth asking BEFORE the
        # publish because on production the claim is what a later publish under
        # any other name will collide with, and `yank` never releases it.
        #
        # Its failure is reported, never swallowed: a check that could not run is
        # not a check that passed, and the publish still goes ahead because the
        # server runs the authoritative version of it anyway.
        duplicate_note = ""
        try:
            already = await run_sync(lambda: _client(token, target).is_published(spec))
        except RegistryError as exc:
            already = None
            duplicate_note = (
                f" The duplicate-content pre-flight could not run ({exc}), so nothing here "
                "confirmed this data is unpublished — the registry's own check decided."
            )
        if already:
            refs = ", ".join(str(getattr(r, "canonical_id", None) or r) for r in already)
            return OpResult(
                success=False,
                message=(
                    f"Not published: {describe(target, settings)} already holds this exact "
                    f"authored data as {refs}. The content claim is name-independent, so "
                    "republishing it under another name is refused too. Change the rows, or "
                    "publish a new version of the module that already has them."
                ),
                data={"target": target, "published_as": [str(r) for r in already]},
            )

        if ctx:
            await ctx.info(
                f"Publishing {namespace}/{name}@{version} to {describe(target, settings)}"
            )

        try:
            manifest = await run_sync(
                lambda: _client(token, target).publish(
                    namespace, name, version, spec, changelog=changelog
                )
            )
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=f"{describe(target, settings)} refused the publish: {exc}",
                data={"target": target},
            )

        identity = getattr(manifest, "identity", None)
        artifact = getattr(manifest, "artifact", None)
        canonical = getattr(identity, "canonical_id", None) or f"{namespace}/{name}@{version}"

        receipt, note = _record_receipt(
            spec,
            target=target,
            registry_url=settings.registry_url_for(target),
            identity=identity,
            artifact=artifact,
            manifest=manifest,
            fallback=(namespace, name, version),
        )
        rehearsal = (
            " This was a rehearsal on the polygon, not a release: publish again with "
            'target="prod" when it is right, and delete this one with '
            "`registry_delete_version` so the data is free to publish again here."
            if target == "test"
            else ""
        )
        naming = polygon_naming_note(target, namespace=namespace, name=name)
        return OpResult(
            success=True,
            message=f"Published {canonical} to {describe(target, settings)}. {note}"
            + rehearsal
            + duplicate_note
            + (f" {naming}" if naming else ""),
            data={**receipt, "receipt_file": str(spec / RECEIPTS_FILE)},
        )

    # ----------------------------------------------------------------- #
    # Polygon-only cleanup — what makes a rehearsal repeatable
    # ----------------------------------------------------------------- #
    #
    # These are the reason the polygon exists. A published version is immutable
    # and its authored data is claimed by a name-independent content hash that
    # `yank` does NOT release, so without a hard delete every rehearsal
    # permanently spends a version number and the right to publish that data
    # under any other name. Deleting frees both.
    #
    # Production does not mount the verb at all and answers 405. We refuse before
    # sending rather than letting the 405 be the answer: a 405 is a safe failure
    # but an uninformative one, and the useful reply here names `yank` — the
    # thing production actually offers, with the different guarantee that
    # anyone who already installed the version keeps verifying it.

    def _prod_delete_refusal(target: RegistryTarget, what: str) -> OpResult | None:
        if target != "prod":
            return None
        return OpResult(
            success=False,
            message=(
                f"Nothing was deleted. Hard deletion is a polygon verb: production does not "
                f"mount it (405) because a published {what} is immutable and consumers are "
                "entitled to keep resolving it. What production offers instead is `yank`, which "
                "delists a version while leaving it fetchable — not wrapped here, so use "
                "`registry-client` or ask the operator. Note that a yank does NOT release the "
                "content claim, so the authored data stays unpublishable under any other name."
            ),
            data={"target": target},
        )

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Polygon: delete a rehearsed version",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_delete_version(
        namespace: str,
        name: str,
        version: str,
        ctx: Context,
        target: RegistryTarget = "test",
    ) -> OpResult:
        """Hard-delete one rehearsed version from the polygon. Frees its content claim.

        The cleanup half of a rehearsal: it removes the rows, the artifacts and
        the content claim, so the same authored data can be published again —
        which `yank` does not do. Use it between rehearsal rounds, and before
        publishing the same data to production if you rehearsed it under a
        different name.

        Polygon only. `target` exists so the refusal on production is explicit
        rather than a 405 from the far end; there is no way to make this work
        there, by design.
        """
        blocked = _prod_delete_refusal(target, "version")
        if blocked is not None:
            return blocked
        token = require_key(ctx, settings, store, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            await run_sync(lambda: _client(token, target).delete_version(namespace, name, version))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=f"{describe(target, settings)} refused the delete: {exc}",
                data={"target": target},
            )
        log.info("Deleted %s/%s@%s from %s", namespace, name, version, target)
        return OpResult(
            success=True,
            message=(
                f"Deleted {namespace}/{name}@{version} from {describe(target, settings)}. The "
                "version number and the content claim are both free again. `published.json` "
                "still records the rehearsal — that is the history, not a live claim."
            ),
            data={"target": target, "deleted": f"{namespace}/{name}@{version}"},
        )

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Polygon: delete a rehearsed module",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_delete_module(
        namespace: str,
        name: str,
        ctx: Context,
        target: RegistryTarget = "test",
    ) -> OpResult:
        """Hard-delete every rehearsed version of a module from the polygon.

        The whole-module form, because a rehearsal usually leaves several
        versions behind and deleting them one at a time is how a cleanup
        half-finishes. Polygon only, for the same reason as
        `registry_delete_version`.
        """
        blocked = _prod_delete_refusal(target, "module")
        if blocked is not None:
            return blocked
        token = require_key(ctx, settings, store, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            await run_sync(lambda: _client(token, target).delete_module(namespace, name))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=f"{describe(target, settings)} refused the delete: {exc}",
                data={"target": target},
            )
        log.info("Deleted module %s/%s from %s", namespace, name, target)
        return OpResult(
            success=True,
            message=(
                f"Deleted every version of {namespace}/{name} from "
                f"{describe(target, settings)}, with their artifacts and content claims."
            ),
            data={"target": target, "deleted": f"{namespace}/{name}"},
        )
