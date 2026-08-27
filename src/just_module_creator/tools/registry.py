"""KEY-GATED — the registry calls that need a token.

These are ALWAYS listed (so the multi-user HTTP path is safe and discoverable)
and enforce auth PER CALL via ``resolve_api_key``. If no token is resolvable for the
current request they return a friendly ``OpResult`` instead of raising — never a
global state flip, so one client can never ride another client's credential.

Authoring, validating and compiling *locally* need no token. Only these do.

**Not all of them write.** ``registry_whoami`` never did, and the server-side
pre-flights (``registry_validate`` / ``registry_check``) do not either — the
registry requires the PUBLISH capability on the namespace to run them, because
they upload the spec, so they need a credential whatever their effect. The tag is
``registry_write`` for history; read it as "needs a token".
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

from just_module_creator import logscan
from just_module_creator.auth import (
    GATED_TAG,
    resolve_api_key,
    unauthenticated_result,
)
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import OpResult, PublishPreflight
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import (
    DEFAULT_WRITE_TARGET,
    client_for,
    describe,
    instance_note,
    polygon_naming_note,
    prod_refusal,
)
from just_module_creator.tools._shared import (
    jsonable,
    resolve_dir,
    to_published_versions,
)

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


def _unauthenticated_preflight(
    *, spec_dir: str, namespace: str, name: str, target: RegistryTarget
) -> PublishPreflight:
    """"No token" as a pre-flight, not as a verdict.

    The other gated tools return ``OpResult(success=False)``, which is honest there
    because they either did the thing or did not. A pre-flight returns a *verdict*,
    and the one thing this must never do is let "we could not ask" arrive shaped like
    "would not publish". So ``verdict`` stays null, with ``verdict_unavailable``
    naming the reason.

    **The three-valued fields were honest and the plain booleans beside them were not
    (`D22`).** Measured on a module that ``validate_module(strict=true)`` passes clean:
    ``valid: false`` and ``name_matches_path: false``, both of them unrun checks
    defaulting to the negative, and ``valid`` is the field a caller branches on because
    it carries ``validate_module``'s own name. So both are null here, and so is
    ``registry_url`` — no instance answered, and naming one would claim a round trip
    that never left. ``module_level_clear`` is null for the same reason and not false:
    it composes three gates, none of which is asked without a token, and `false` would
    assert that something module-level blocks a publish — as unestablished as the clear
    answer. A check that could not run is not a check that passed, and it did not fail
    either. ``strict`` stays `True` because it echoes the mode the call would grade
    under, which is a statement about the request rather than about a result.
    """
    return PublishPreflight(
        spec_dir=spec_dir,
        namespace=namespace,
        name=name,
        strict=True,
        valid=None,
        module_level_clear=None,
        name_matches_path=None,
        verdict=None,
        verdict_unavailable="no_registry_token",
        blocking=[],
        unchecked=["nothing was checked: no registry token is available for this instance."],
        target=target,
        registry_url=None,
        next_step=(
            "Not a verdict — nothing ran. Get a token with `registry_register`, store it with "
            "`authenticate`, then call this again. Meanwhile `validate_module(strict=true)` is the "
            "local pre-flight and needs no credential."
        ),
    )


def _preflight(
    report: object,
    *,
    spec_dir: str,
    namespace: str,
    name: str,
    target: RegistryTarget,
    registry_url: str,
) -> PublishPreflight:
    """Project a ``ValidationReport`` or a ``CheckReport`` onto one model.

    One model for both because they answer one question at two depths, and a caller
    should not have to reshape its branching to add the network tier. ``verdict``
    stays ``None`` for a bare validate — **that is the honest value**, not a
    placeholder: `/validate` never runs the enrichment tier, so it has no verdict to
    report, and defaulting it to `False` would read as "would not publish".

    The two verdicts are kept apart on purpose. ``would_publish_module_level`` is
    upstream's name and upstream's meaning — the gates that do not scale with variant
    count — and it is surfaced as ``module_level_clear`` so nothing reads it as a
    green light. A skip must never produce a positive verdict.
    """
    # A CheckReport wraps the ValidationReport; a ValidationReport is one.
    validation = getattr(report, "validation", None) or report
    enrichment = getattr(report, "enrichment", None)

    published = to_published_versions(getattr(validation, "published_as", []))
    module_clear = bool(getattr(validation, "would_publish_module_level", False))
    name_ok = bool(getattr(validation, "name_matches_path", False))
    errors = [str(e) for e in getattr(validation, "errors", []) or []]

    # `verdict` exists only on a CheckReport, and only once the tier ran.
    skipped = getattr(report, "skipped_reason", None)
    is_check = hasattr(report, "would_publish")
    verdict: bool | None = None
    if is_check and not skipped:
        verdict = bool(getattr(report, "would_publish", False))

    blocking: list[str] = []
    non_blocking: list[str] = []
    unchecked: list[str] = []
    rerun: list[str] = []

    if errors:
        blocking.append(f"{len(errors)} validation error(s) under strict — see `errors`.")
    if not name_ok:
        blocking.append(
            "`module.name` does not match the name you published under: a publish 422s."
        )
    if published:
        ids = ", ".join(v.canonical_id for v in published)
        blocking.append(
            f"identical authored data is already published as {ids} — a publish would 409 "
            "duplicate_content, and on production that claim is permanent (a yank does not "
            "release it)."
        )

    if enrichment is not None:
        rerun = [str(r) for r in getattr(enrichment, "unreachable_rsids", []) or []]
        if getattr(enrichment, "ref_mismatches", None):
            blocking.append(
                f"{len(enrichment.ref_mismatches)} authored reference allele(s) disagree with the "
                "genome — this blocks in both modes."
            )
        fatal = [s for s in getattr(enrichment, "stale_rsids", []) or [] if getattr(s, "fatal", 0)]
        if fatal:
            blocking.append(
                f"{len(fatal)} rsID(s) have been withdrawn — this blocks in both modes."
            )
        unresolved = [str(u) for u in getattr(enrichment, "unresolved", []) or []]
        if unresolved and getattr(validation, "strict", False):
            blocking.append(
                f"{len(unresolved)} position(s) did not resolve, which blocks under strict."
            )
        elif unresolved:
            non_blocking.append(
                f"{len(unresolved)} position(s) did not resolve — not blocking here, but the "
                "registry compiles with strict, so it will block a real publish."
            )
        if rerun:
            unchecked.append(
                f"{len(rerun)} rsID(s) could not be ASKED about — live Ensembl did not answer, so "
                "their absence is unchecked rather than established. Re-run before treating a "
                "false verdict as something to fix in the spec."
            )
        not_checked = getattr(enrichment, "clin_sig_not_checked", None)
        if not_checked:
            unchecked.append(f"the ClinVar clin_sig cross-check did not run: {not_checked}")
        if getattr(enrichment, "clin_sig_conflicts", None):
            non_blocking.append(
                f"{len(enrichment.clin_sig_conflicts)} clin_sig call(s) disagree with ClinVar — "
                "never blocking, and worth reading: the compiler leaves your row alone."
            )
        identifiers = getattr(enrichment, "identifiers", None)
        if identifiers is not None:
            stale = list(getattr(identifiers, "stale_traits", []) or []) + list(
                getattr(identifiers, "stale_genes", []) or []
            )
            gene_loci = list(getattr(identifiers, "gene_loci", []) or [])
            if stale:
                non_blocking.append(
                    f"{len(stale)} identifier(s) are stale. This NEVER moves the verdict — a "
                    "publish does not run this pass, so a finding predicts nothing about one."
                )
            if gene_loci:
                non_blocking.append(
                    f"{len(gene_loci)} row(s) name a gene on a different chromosome than their "
                    "own variant. Not a publish gate, and the most likely sign of a fabricated "
                    "row: read these."
                )
            skipped_loci = getattr(identifiers, "gene_loci_not_checked", None)
            if skipped_loci:
                unchecked.append(f"the gene/chromosome comparison did not run: {skipped_loci}")
        for note in getattr(enrichment, "notes", []) or []:
            unchecked.append(str(note))

    if skipped:
        next_step = (
            f"No verdict: the network tier was skipped ({skipped}). The validation findings above "
            "are already the answer — fix those and check again."
        )
    elif verdict is True:
        next_step = (
            "The dry run found nothing blocking. Read `non_blocking` and `unchecked` before "
            "publishing anyway — a clean verdict is not a claim that the module is good."
        )
    elif verdict is False and rerun:
        next_step = (
            "Would not publish — but some rsIDs could not be reached, so RE-RUN this before "
            "changing the spec. A strict publish against an unreachable Ensembl really does "
            "refuse; that says nothing about whether the variants exist."
        )
    elif verdict is False:
        next_step = "Would not publish. `blocking` lists what stands in the way."
    elif module_clear:
        next_step = (
            "Nothing module-level blocks this. That is NOT 'it will publish' — the network tier "
            "was not run. Use `registry_check` for the full dry run."
        )
    else:
        next_step = "Module-level gates are not clear yet. `blocking` lists what stands in the way."

    stats = getattr(validation, "stats", None)
    _reported_valid = getattr(validation, "valid", None)
    return PublishPreflight(
        spec_dir=spec_dir,
        namespace=namespace,
        name=name,
        strict=bool(getattr(validation, "strict", False)),
        # `None` when upstream reported no verdict at all, never `False`: a field that is
        # absent is a check whose answer we do not have, and coercing it to the negative is
        # the same defect the no-token path above was fixed for.
        valid=None if _reported_valid is None else bool(_reported_valid),
        errors=errors,
        warnings=[str(w) for w in getattr(validation, "warnings", []) or []],
        info=[str(i) for i in getattr(validation, "info", []) or []],
        module_level_clear=module_clear,
        name_matches_path=name_ok,
        published_as=published,
        content_signature=getattr(validation, "content_signature", None),
        verdict=verdict,
        verdict_unavailable=str(skipped) if skipped else None,
        rerun_rather_than_fix=rerun,
        unchecked=unchecked,
        blocking=blocking,
        non_blocking=non_blocking,
        stats=jsonable(stats.model_dump()) if stats is not None else {},
        elapsed_seconds=getattr(report, "elapsed_seconds", None),
        target=target,
        registry_url=registry_url,
        next_step=next_step,
    )


def register_registry(mcp: FastMCP, settings: Settings) -> None:
    """Register the token-gated registry tools (tag: registry_write)."""

    def _client(token: str, target: RegistryTarget):
        return client_for(target, settings, token=token)

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Registry: would this spec publish (module-level)",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_validate(
        namespace: str,
        name: str,
        spec_dir: str,
        ctx: Context,
        strict: bool = True,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
    ) -> PublishPreflight:
        """Validate a spec **on the registry**, without publishing it or spending a version.

        This is not the same question as `validate_module`. That one asks whether
        the compiler accepts your spec; this one asks the *server* the gates a
        publish would apply — including two your machine cannot know: whether
        `module.name` matches the path, and whether identical authored data is
        already published under some other name.

        **`module_level_clear` means "nothing module-level blocks this", never
        "this will publish".** It composes exactly three gates and deliberately
        leaves out the network tier, so a clear answer is not a green light — use
        `registry_check` for the full dry run. `verdict` stays null here for the
        same reason: this endpoint never runs that tier, and null is not a pass.

        Writes nothing, and the module need not exist yet. Needs a token because
        the registry requires the publish capability on the namespace to accept a
        spec upload at all.
        """
        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return _unauthenticated_preflight(
                spec_dir=spec_dir, namespace=namespace, name=name, target=target
            )
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        spec = resolve_dir(spec_dir, settings)
        try:
            report = await run_sync(
                lambda: _client(token, target).validate(namespace, name, spec, strict=strict)
            )
        except RegistryError as exc:
            raise ToolError(
                f"{describe(target, settings)} could not validate the spec: "
                f"{exc}{instance_note(exc)}"
            ) from exc

        return _preflight(
            report,
            spec_dir=str(spec),
            namespace=namespace,
            name=name,
            target=target,
            registry_url=settings.registry_url_for(target),
        )

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Registry: full publish dry run",
            readOnlyHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def registry_check(
        namespace: str,
        name: str,
        spec_dir: str,
        ctx: Context,
        strict: bool = True,
        offline: bool = False,
        frequencies: bool = False,
        literature: bool = False,
        identifiers: bool = False,
        acmg: bool = False,
        pgx: bool = False,
        declared_use: str | None = None,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
    ) -> PublishPreflight:
        """The full publish dry run: validation plus everything the network tier finds.

        The call that turns "rehearse the publish" into "ask whether it would
        publish" **without spending a version number**. It checks what nothing
        offline can: an authored reference allele against the actual genome, a
        `clin_sig` against ClinVar, an rsID dbSNP has merged away.

        **Read `verdict` with `rerun_rather_than_fix` beside it.** A false verdict
        alongside unreachable rsIDs means *re-run*, not *go fix your spec* — a
        strict publish against an unreachable Ensembl really does refuse, and that
        says nothing about whether the variants exist. And `verdict: null` means
        the tier did not run at all, which is never a pass.

        **Expensive, and the cost is the operator's.** gnomAD is paced at roughly
        six seconds per twenty variants, so this can take minutes and is capped
        process-wide on the server. Use `offline=true` for a large panel: it has
        **no variant ceiling**, because it issues no request for one to bound.
        Online above the ceiling comes back as a refusal that still carries the
        module-level half.

        The optional passes are off by default and each costs egress.
        `identifiers=true` never moves the verdict — a publish does not run that
        pass — but it is where a fabricated row shows up. `pgx=true` needs
        `declared_use="non_commercial"` to actually run: every PGx upstream
        forbids sale, so on `unstated` each source is skipped with a reason rather
        than queried, and `"commercial"` is refused outright.
        """
        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return _unauthenticated_preflight(
                spec_dir=spec_dir, namespace=namespace, name=name, target=target
            )
        # `offline` here is the REGISTRY's egress, not ours — two different ceilings,
        # and conflating them is the trap. Our ceiling still refuses the whole tool,
        # because reaching the registry at all is a network call whatever the server
        # then does. So `offline=true` never buys a way past `JMC_OFFLINE`.
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE). `offline=true` here clamps the "
                "REGISTRY's own egress, not ours — reaching it is still a network call, so this "
                "tool cannot run. `validate_module` is the local pre-flight."
            )

        spec = resolve_dir(spec_dir, settings)
        try:
            report = await run_sync(
                lambda: _client(token, target).check(
                    namespace,
                    name,
                    spec,
                    strict=strict,
                    offline=offline,
                    frequencies=frequencies,
                    literature=literature,
                    identifiers=identifiers,
                    acmg=acmg,
                    pgx=pgx,
                    declared_use=declared_use,
                )
            )
        except RegistryError as exc:
            raise ToolError(
                f"{describe(target, settings)} could not complete the dry run: "
                f"{exc}{instance_note(exc)}"
            ) from exc

        return _preflight(
            report,
            spec_dir=str(spec),
            namespace=namespace,
            name=name,
            target=target,
            registry_url=settings.registry_url_for(target),
        )

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
        token = await resolve_api_key(ctx, settings, target)
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
                    f"one you stored.{instance_note(exc)}"
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
            title="Registry: fix a published module's readme",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
            openWorldHint=True,
        ),
    )
    async def registry_amend_readme(
        namespace: str,
        name: str,
        version: str,
        ctx: Context,
        spec_dir: str | None = None,
        readme_text: str | None = None,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
    ) -> OpResult:
        """Replace a published version's readme — **no version bump, nothing burned**.

        The rare registry write that is cheap and reversible. The readme sits
        **outside `artifact.digest`**, deliberately: prose must not change a
        module's content identity, or editing a caveat would mint a new digest and
        collide with the duplicate-content claim of the module it is a copy of. So
        unlike everything else about a published version, this is repairable.

        It is also the field where a module says what it is **not** — that its rows
        are candidates, that one association was not significant, which population
        the evidence came from. `description` is meant to be the card's
        one-sentence subtitle and cannot carry that -- and being inside the
        attestation binding, lengthening it would cost a version, which is the
        reason this is amendable at all on an otherwise immutable registry.

        Give it **one** of two things, and the distinction matters because both
        arrive as strings over this wire: `spec_dir` reads `README.md` from that
        directory (the usual case — you have the file), or `readme_text` is the
        markdown itself (fixing one sentence). Passing a path as `readme_text`
        would publish the path *as* the prose, so they are separate arguments
        rather than one that guesses.

        Last-publish-wins, and a publish carrying no readme leaves the existing one
        alone rather than blanking it — so this does not fight the next publish.
        """
        if not spec_dir and readme_text is None:
            raise ToolError(
                "Provide either spec_dir (to read README.md from it) or readme_text (the markdown)."
            )
        if spec_dir and readme_text is not None:
            raise ToolError(
                "Provide spec_dir or readme_text, not both — only you know which one is current."
            )

        # Everything decidable without a credential is decided first, the same order
        # `registry_publish` uses and for the same reason: sending an author off to
        # get a token for a call that could never have succeeded is a dead end.
        if spec_dir:
            spec = resolve_dir(spec_dir, settings)
            readme = spec / "README.md"
            if not readme.is_file():
                raise ToolError(
                    f"No README.md in {spec}. The registry reads that exact name — a "
                    "`MODULE.md` is renamed on upload, and any other spelling is carried but "
                    "never read. Write one, or pass the markdown as readme_text."
                )
            body = readme.read_text(encoding="utf-8")
        else:
            body = str(readme_text)

        if not body.strip():
            raise ToolError(
                "The readme is empty, and sending it would blank the card rather than fix it. "
                "Last-publish-wins applies to this field, so an empty body replaces what is "
                "there instead of leaving it alone."
            )

        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            payload = await run_sync(
                lambda: _client(token, target).amend_readme(namespace, name, version, body)
            )
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} refused the readme: "
                    f"{exc}{instance_note(exc)}"
                ),
                data={"target": target},
            )
        log.info("Amended readme for %s/%s@%s on %s", namespace, name, version, target)
        return OpResult(
            success=True,
            message=(
                f"Readme replaced on {namespace}/{name}@{version} at "
                f"{describe(target, settings)}. No version was spent and the artifact digest is "
                "unchanged — the readme is outside it."
            ),
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

        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            payload = await run_sync(lambda: _client(token, target).claim_namespace(namespace))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} refused the claim: "
                    f"{exc}{instance_note(exc)}"
                ),
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
        ctx: Context,
        changelog: str = "",
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
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

        token = await resolve_api_key(ctx, settings, target)
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

        # The log pre-flight (RM25). Every `*.log` in the spec is swept into the
        # artifact with no opt-out, and a published version is immutable — so the
        # one moment this can still be acted on is here, before the upload. It
        # never refuses: publishing a flagged log is a legitimate decision and it
        # is the author's. It only ensures nobody publishes a file unseen.
        log_note = ""
        swept = logscan.logs_in(spec)
        if swept:
            flagged = {
                str(path.relative_to(spec)): flags
                for path in swept
                if (flags := logscan.scan_file(path))
            }
            if flagged:
                kinds = sorted({f.kind for flags in flagged.values() for f in flags})
                log_note = (
                    f" NOTE: {len(swept)} log(s) travelled with this module, and "
                    f"{len(flagged)} carry something worth having seen ({', '.join(kinds)}) — "
                    f"{', '.join(sorted(flagged))}. `review_logs` shows the lines. A published "
                    f"version is immutable, so this is a thing to know now rather than later."
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
                f"confirmed this data is unpublished — the registry's own check decided."
                f"{instance_note(exc)}"
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
                message=(
                    f"{describe(target, settings)} refused the publish: "
                    f"{exc}{instance_note(exc)}"
                ),
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
            + log_note
            + (f" {naming}" if naming else ""),
            data={**receipt, "receipt_file": str(spec / RECEIPTS_FILE)},
        )

    # ----------------------------------------------------------------- #
    # Polygon-only cleanup — what makes a rehearsal repeatable
    # ----------------------------------------------------------------- #
    #
    # `yank` is the production answer to "we published something wrong", and it
    # was reachable from the client and from nowhere on this surface until RM21.
    # An agent that can publish is an agent that can publish a mistake, and the
    # discovery of one ended at a dead end with the bad version still at `latest`
    # — the `F12` shape, where the only route to a fix lives outside the surface
    # that created the need for it.
    #
    # It is NOT a repair and the wording everywhere below says so. Yank stops a
    # version being recommended; it does not correct anything, it does not
    # release the content claim, and publishing the fixed version is a separate
    # act that still has to happen.

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Yank a published version",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_yank(
        namespace: str,
        name: str,
        version: str,
        ctx: Context,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
    ) -> OpResult:
        """Stop recommending a published version. It stays fetchable for anyone pinned to it.

        The production answer to a bad publish. The version drops out of default
        listings and out of `latest`, so nobody new resolves it — and anyone who
        already installed it keeps verifying, which is what an immutable registry
        owes them.

        **This is not a repair, and it fixes nothing on its own.** It stops the
        version being handed out. The corrected module is a separate publish that
        still has to happen, and a yank with no replacement leaves consumers on
        whatever the previous good version was. Say that out loud rather than
        reporting a yank as though the mistake were undone.

        **It does not release the content claim.** The authored data stays claimed
        by its name-independent content hash, so the same rows cannot be published
        under a different name afterwards. On the polygon,
        `registry_delete_version` is the verb that frees both; production has no
        such verb by design.

        Reversible with `registry_unyank` — which is exactly why it is the right
        first move when something looks wrong and you are not yet certain.
        """
        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            await run_sync(lambda: _client(token, target).yank(namespace, name, version))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} refused the yank: {exc}{instance_note(exc)}"
                ),
                data={"target": target},
            )
        log.info("Yanked %s/%s@%s on %s", namespace, name, version, target)
        return OpResult(
            success=True,
            message=(
                f"Yanked {namespace}/{name}@{version} on {describe(target, settings)}. It is "
                "out of default listings and out of `latest`, and still fetchable for anyone "
                "pinned to it. Nothing is corrected by this — publish the fixed version "
                "separately, and until you do, new installs land on the previous good version. "
                "The content claim is NOT released. Reverse with `registry_unyank`."
            ),
            data={"target": target, "yanked": f"{namespace}/{name}@{version}"},
        )

    @mcp.tool(
        tags={GATED_TAG},
        annotations=ToolAnnotations(
            title="Un-yank a version",
            readOnlyHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_unyank(
        namespace: str,
        name: str,
        version: str,
        ctx: Context,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
    ) -> OpResult:
        """Put a yanked version back into listings and `latest` eligibility.

        For a yank made in haste, or one whose reason turned out not to hold. It
        restores nothing about the module itself — the bytes never changed, which
        is why this is safe.
        """
        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            await run_sync(lambda: _client(token, target).unyank(namespace, name, version))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} refused the un-yank: {exc}{instance_note(exc)}"
                ),
                data={"target": target},
            )
        log.info("Un-yanked %s/%s@%s on %s", namespace, name, version, target)
        return OpResult(
            success=True,
            message=(
                f"Un-yanked {namespace}/{name}@{version} on {describe(target, settings)}. It is "
                "listed again and eligible for `latest`."
            ),
            data={"target": target, "unyanked": f"{namespace}/{name}@{version}"},
        )

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
                "entitled to keep resolving it. What production offers instead is "
                "`registry_yank`, which delists a version while leaving it fetchable. Note "
                "that a yank does NOT release the content claim, so the authored data stays "
                "unpublishable under any other name."
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
        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            await run_sync(lambda: _client(token, target).delete_version(namespace, name, version))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} refused the delete: "
                    f"{exc}{instance_note(exc)}"
                ),
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
        token = await resolve_api_key(ctx, settings, target)
        if token is None:
            return unauthenticated_result(settings, target)
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        try:
            await run_sync(lambda: _client(token, target).delete_module(namespace, name))
        except RegistryError as exc:
            return OpResult(
                success=False,
                message=(
                    f"{describe(target, settings)} refused the delete: "
                    f"{exc}{instance_note(exc)}"
                ),
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
