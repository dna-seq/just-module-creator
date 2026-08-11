"""Runtime, per-session authentication for the key-gated registry tools.

Design goals (multi-user safe):

* The server ALWAYS boots — a missing token is never a startup error. Authoring
  a module needs no registry account at all; only publishing does.
* A token is resolved PER REQUEST, never stored in a server-global mutable
  field. Resolution precedence:
    1. per-request HTTP header (``settings.api_key_header_for(target)``) -> multi-user safe
    2. per-session store keyed by ``(ctx.session_id, target)`` (set via ``authenticate``)
    3. ``JMC_API_KEY`` / ``JMC_TEST_API_KEY`` env, else ``REGISTRY_TOKEN`` /
       ``REGISTRY_TEST_TOKEN`` (single-tenant / local)
* ``authenticate`` writes ONLY into the caller's own session slot, so one HTTP
  client can never read or clobber another client's token.

**Every credential is scoped to one instance.** Production and the polygon keep
separate databases, so an account minted on one does not exist on the other and a
token is only ever a credential for the instance that issued it. Nothing here
falls back from one to the other: a missing polygon token means "register on the
polygon", not "try the production key and see".

Anti-pattern (documented, off by default): ``mcp.enable(tags=...)`` to "unlock"
gated tools is SERVER-GLOBAL — it would expose tools to every connected client.
Safe only for single-tenant stdio. See ``register_stdio_only_unlock`` below.

``registry_register`` lives here rather than in the gated ``tools/registry.py``
even though it writes to the registry, because it is the one registry write that
**cannot** be token-gated: it is what mints the token. Putting it behind the
extended tier would be the same mistake in a different place — the default
surface would still dead-end at "get a token from somewhere else".
"""

from __future__ import annotations

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_format.identity import NAMESPACE_PATTERN, is_valid_namespace
from just_dna_registry import RegistryError, generate_install_id
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import AuthResult, OpResult, RegistrationResult
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import (
    DEFAULT_WRITE_TARGET,
    TEST_NAMESPACE_PREFIX,
    client_for,
    describe,
    is_test_namespace,
)

log = get_logger()

# Tools tagged with this are token-gated.
GATED_TAG = "registry_write"
GATED_TOOLS = [
    "registry_whoami",
    # The server-side pre-flights. They write nothing, but the registry requires the
    # PUBLISH capability on the namespace to accept a spec upload at all, so a token
    # is not optional. See `tools/registry.py`'s module docstring on the tag's name.
    "registry_validate",
    "registry_check",
    "registry_publish",
    "registry_claim_namespace",
    "registry_delete_version",
    "registry_delete_module",
]


class SessionKeyStore:
    """Per-session, per-instance registry tokens. The ONLY auth state.

    Keyed by ``(session, target)`` rather than by session alone: one author can
    hold an account on production and another on the polygon, and the two keys
    are not interchangeable. A single slot would have the second
    ``authenticate`` silently retarget the first.
    """

    def __init__(self) -> None:
        self._keys: dict[tuple[str, str], str] = {}

    @staticmethod
    def _sid(ctx: Context | None) -> str:
        sid = getattr(ctx, "session_id", None) if ctx else None
        return sid or "__local__"

    def set(self, ctx: Context | None, key: str, target: RegistryTarget) -> None:
        self._keys[(self._sid(ctx), target)] = key

    def get(self, ctx: Context | None, target: RegistryTarget) -> str | None:
        return self._keys.get((self._sid(ctx), target))


def _header_key(settings: Settings, target: RegistryTarget) -> str | None:
    """Read the token for ``target`` from the current HTTP request header, if any."""
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
    except Exception:
        return None  # not an HTTP request (stdio / in-memory)
    return request.headers.get(settings.api_key_header_for(target))


def resolve_api_key(
    ctx: Context | None,
    settings: Settings,
    store: SessionKeyStore,
    target: RegistryTarget,
) -> str | None:
    """Resolve the registry token for THIS request and THIS instance."""
    return (
        _header_key(settings, target) or store.get(ctx, target) or settings.registry_token(target)
    )


def require_key(
    ctx: Context | None,
    settings: Settings,
    store: SessionKeyStore,
    target: RegistryTarget,
) -> str | None:
    """Return the resolved token, or ``None`` if the caller must authenticate.

    Gated tools use this and return a friendly ``OpResult`` on ``None`` rather
    than raising, so agents get an actionable message.
    """
    return resolve_api_key(ctx, settings, store, target)


def resolve_install_id(explicit: str | None, settings: Settings) -> tuple[str | None, str]:
    """The install-id to register with, and where it came from.

    ``(None, "generated")`` means nothing was supplied and one has to be ground.
    That is returned rather than ground here so the caller can put the CPU work
    *after* the offline ceiling and the account-name check — grinding for a
    request that was going to be refused anyway is pure waste.

    The origin travels into the result because a reused id and a fresh one have
    opposite consequences: reusing one reissues a key for its existing account,
    while a fresh one creates a new account that the caller must now save the id
    for. Reporting only the id would make those look identical.
    """
    if explicit and explicit.strip():
        return explicit.strip(), "argument"
    if settings.install_id and settings.install_id.strip():
        return settings.install_id.strip(), "environment"
    return None, "generated"


def _registration_failure(exc: RegistryError, *, account: str, origin: str) -> str:
    """Turn the registry's error slug into something the caller can act on."""
    detail = str(getattr(exc, "detail", "") or exc)

    if "account_taken" in detail:
        return (
            f"{account!r} already exists and is bound to a different install-id. A key can only "
            "be reissued to the install-id that created an account, and there is no email or "
            "admin to recover through, so retrying will not help: either pass the install-id you "
            "saved for that account, or pick another name."
        )
    if "invalid_install_id" in detail:
        origin_note = (
            "the id was generated at this client's default difficulty"
            if origin == "generated"
            else f"the id came from the {origin}"
        )
        return (
            f"The registry rejected the install-id ({origin_note}). It requires more "
            "proof-of-work than was supplied — call again with a higher `difficulty`."
        )
    if "invalid_account" in detail:
        return (
            f"The registry rejected {account!r} as an account name, so its rule is stricter than "
            f"the one checked here ({NAMESPACE_PATTERN.pattern}). Report this — the local check "
            "should not disagree with the server."
        )
    if "self_register_disabled" in detail:
        return (
            "This registry has self-registration switched off, so an account cannot be minted "
            "from here. Its operator has to issue the token."
        )
    return f"The registry refused the registration: {exc}"


def unauthenticated_result(settings: Settings, target: RegistryTarget = "prod") -> OpResult:
    env_var = (
        "JMC_TEST_API_KEY / REGISTRY_TEST_TOKEN"
        if target == "test"
        else ("JMC_API_KEY / REGISTRY_TOKEN")
    )
    return OpResult(
        success=False,
        message=(
            f"This tool needs a registry token for {describe(target, settings)}, and none was "
            f"found. Call `authenticate(token, target={target!r})` for this session, send the "
            f"`{settings.api_key_header_for(target)}` header (HTTP), or set {env_var} in the "
            "environment. A token is issued by one instance and is not valid on the other, so a "
            "key you already hold for the other one will not do — `registry_register` mints one "
            "per instance. Authoring, validating and compiling a module need no token at all."
        ),
        data={"target": target, "registry_url": settings.registry_url_for(target)},
    )


def register_auth(mcp: FastMCP, settings: Settings, store: SessionKeyStore) -> None:
    """Register the always-on auth tools: ``registry_register`` and ``authenticate``."""

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Registry: register an account and mint a token",
            readOnlyHint=False,
            # Each call issues a NEW api key, even when the account already
            # exists, so repeating it is not a no-op.
            idempotentHint=False,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def registry_register(
        account: str,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
        install_id: str | None = None,
        difficulty: int | None = None,
        ctx: Context | None = None,
    ) -> RegistrationResult:
        """Create a registry account and mint its API key. No token needed — this makes one.

        Onboarding is self-service: no admin, no email, no approval. The only
        gate is an install-id, a proof-of-work string ground locally in about a
        second. Omit `install_id` and one is ground for you.

        **`target` picks the instance, and defaults to the polygon.** The two
        keep separate databases, so registering is per instance: an account on
        the polygon does not exist in production and its token is not a
        production credential. Register on both — the same install-id may be
        reused, and reusing it is what keeps the two accounts recognisably
        yours.

        **Save the install-id this returns.** It is the account's only recovery
        path. Re-registering the SAME install-id reissues a key for the SAME
        account and ignores the `account` argument; calling again WITHOUT one
        grinds a fresh id, which is a different account, and the first account
        becomes unreachable if you did not keep its id. Put it in `.env` as
        `JMC_INSTALL_ID`, and the tokens as `JMC_API_KEY` (production) and
        `JMC_TEST_API_KEY` (polygon).

        `account` obeys the namespace rule — lowercase letters and digits with
        single hyphens. Underscores are rejected, not normalised. Note that
        *module* names are the opposite convention and take underscores. A
        `test-` handle is fine on the polygon and refused by production.

        The token is stored for this session against this target, so
        `authenticate` is not needed afterwards. Claiming a namespace is a
        separate, irreversible step: check it with
        `registry_namespace_available` first, then `registry_claim_namespace`.
        """
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE), so the registry cannot be reached."
            )

        # No local test-prefix refusal here, deliberately: production's own
        # `test_data_refusal` guards the namespace claim, the publish and the
        # `issue-key` CLI, and NOT the self-register route — a `test-` handle is
        # accepted there today. Refusing it locally would invent a rule the
        # server does not have. The consequence is reported after the fact
        # instead, where it is true: the handle registers, its namespaces will
        # not.
        if not is_valid_namespace(account):
            raise ToolError(
                f"{account!r} is not a legal account name. Accounts obey the same rule as "
                f"namespaces, {NAMESPACE_PATTERN.pattern} — lowercase letters and digits with "
                "single hyphens between them. Underscores are REJECTED rather than normalised, so "
                "'my_account' has to be 'my-account'. (Module names use the opposite rule and do "
                "take underscores, which is why the two look inconsistent.)"
            )

        resolved, origin = resolve_install_id(install_id, settings)
        if resolved is None:
            if ctx:
                await ctx.info("Grinding a fresh install-id (proof-of-work, about a second)…")
            resolved = await run_sync(
                lambda: generate_install_id(difficulty) if difficulty else generate_install_id()
            )

        url = settings.registry_url_for(target)

        def _register() -> dict:
            # Through `client_for` like every other call, so the construction point
            # stays single. `register` is not one of the methods upstream's mode
            # guard fires on, so this is a no-op today — which is the point: no site
            # has to know which methods are guarded in the version we happen to run.
            with client_for(target, settings) as client:
                return client.register(resolved, account)

        try:
            payload = await run_sync(_register)
        except RegistryError as exc:
            log.warning("Registration of %s on %s failed: %s", account, target, exc)
            return RegistrationResult(
                registered=False,
                # Returned even on failure: it cost CPU to grind and is worth
                # retrying with rather than replacing.
                install_id=resolved,
                install_id_origin=origin,
                target=target,
                registry_url=url,
                message=_registration_failure(exc, account=account, origin=origin),
            )

        token = str(payload.get("token") or "")
        granted = str(payload.get("account") or account)
        namespaces = [str(n) for n in (payload.get("namespaces") or [])]

        if token:
            store.set(ctx, token, target)
        # The token is a secret and never reaches the log.
        log.info(
            "Registered account %s on %s (install-id origin=%s, namespaces=%d)",
            granted,
            target,
            origin,
            len(namespaces),
        )

        notes = [f"Registered {granted!r} on {describe(target, settings)}."]
        if target == "test":
            notes.append(
                "This is the polygon, so this account and its token exist only there. Publishing "
                'for real needs a second registration with target="prod".'
            )
        elif is_test_namespace(granted):
            notes.append(
                f"Production accepted a {TEST_NAMESPACE_PREFIX!r} account handle — it refuses the "
                "prefix on namespaces and module names, not on accounts — but it will refuse "
                "every namespace you try to claim under that spelling."
            )
        if granted != account:
            notes.append(
                f"This is NOT the name you asked for: that install-id already belonged to "
                f"{granted!r}, so the registry reissued a key for it and ignored {account!r}. No "
                "new account was created."
            )
        key_var = "JMC_TEST_API_KEY" if target == "test" else "JMC_API_KEY"
        notes.append(
            f"SAVE BOTH SECRETS in .env — {key_var} for the token, JMC_INSTALL_ID for the "
            "install-id. The install-id is the only way back to this account, and reusing it on "
            "the other instance registers its counterpart there."
            if origin == "generated"
            else f"Token stored; save it in .env as {key_var}. The install-id is unchanged."
        )
        notes.append(
            "The token is stored for this session, so registry tools work now without "
            "`authenticate`."
            if token
            else "The registry returned no token, so nothing was stored — report this."
        )
        notes.append(
            f"Namespaces owned: {', '.join(namespaces)}."
            if namespaces
            else "No namespace yet: check one with `registry_namespace_available`, then claim it "
            "with `registry_claim_namespace`. A claim cannot be undone."
        )

        return RegistrationResult(
            registered=bool(token),
            account=granted,
            namespaces=namespaces,
            token=token or None,
            install_id=resolved,
            install_id_origin=origin,
            stored_for_session=bool(token),
            target=target,
            registry_url=url,
            message=" ".join(notes),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Authenticate to the registry (this session)",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        )
    )
    def authenticate(
        token: str, ctx: Context, target: RegistryTarget = DEFAULT_WRITE_TARGET
    ) -> AuthResult:
        """Provide a registry token to unlock the registry write tools for THIS session.

        The token is stored only against your own session and is never shared
        with other clients. Use this when you already hold a token; if you do not
        have an account yet, `registry_register` mints one and stores its token
        for you, so this call is unnecessary after it. No token is needed to
        author, validate or compile a module — only to publish one.

        **A token belongs to one instance.** `target` says which, and defaults to
        the polygon. The two registries keep separate databases, so storing a
        production key against the polygon does not make it work there — it
        makes the next polygon call fail as an unknown key. Authenticate twice,
        once per instance, if you work with both.
        """
        # No format check: the registry issues the token and is the only thing
        # that can judge it. Inventing a prefix rule here would reject valid
        # tokens the moment upstream changes its issuer.
        if not token.strip():
            return AuthResult(authenticated=False, message="Empty token — nothing was stored.")
        store.set(ctx, token.strip(), target)
        log.info("Session %s stored a registry token for %s", SessionKeyStore._sid(ctx), target)
        return AuthResult(
            authenticated=True,
            unlocked_tools=GATED_TOOLS,
            target=target,
            registry_url=settings.registry_url_for(target),
            message=(
                f"Token stored for this session against {describe(target, settings)}. Call "
                f"`registry_whoami(target={target!r})` to confirm that instance accepts it — "
                "nothing here validated it, and a token for the other instance would look "
                "identical until it is used."
            ),
        )


def register_stdio_only_unlock(mcp: FastMCP, store: SessionKeyStore) -> None:
    """OPTIONAL, SINGLE-TENANT ONLY: hide gated tools until authenticated.

    This disables the gated tools at startup and re-enables them globally on a
    successful ``authenticate`` (emitting ``tools/list_changed``). Because
    ``mcp.enable`` is SERVER-GLOBAL, enabling for one client exposes the tools
    to ALL connected clients — so this is appropriate ONLY for single-tenant
    stdio. Do NOT use under multi-user HTTP. Not wired up by default.
    """
    mcp.disable(tags={GATED_TAG})
    # A real implementation would wrap `authenticate` to call
    # `mcp.enable(tags={GATED_TAG})` after storing the token. Left as a
    # documented pattern; per-call enforcement in resolve_api_key is the gate.
