"""Runtime, per-session authentication for the key-gated registry tools.

Design goals (multi-user safe):

* The server ALWAYS boots — a missing token is never a startup error. Authoring
  a module needs no registry account at all; only publishing does.
* A token is resolved PER REQUEST, never stored in a server-global mutable
  field. Resolution precedence:
    1. per-request HTTP header (``settings.api_key_header_for(target)``) -> multi-user safe
    2. FastMCP session state, under ``registry_token:<target>`` (set via ``authenticate``)
    3. ``JMC_API_KEY`` / ``JMC_TEST_API_KEY`` env, else ``REGISTRY_TOKEN`` /
       ``REGISTRY_TEST_TOKEN`` (single-tenant / local)
* The session store is FastMCP's own (``ctx.set_state`` / ``ctx.get_state``),
  namespaced by ``ctx.session_id`` for us, so one HTTP client can never read or
  clobber another client's token. **The target stays in the key** rather than
  being flattened away: an author may hold an account on production and another
  on the polygon, the two tokens are not interchangeable, and a single slot
  would have the second ``authenticate`` silently retarget the first.

Two properties of that store to plan around, because they differ from the
hand-rolled dict this replaced: entries **expire after 24h**, after which a
session is asked for its token again; and the default backend is an in-process
``MemoryStore``, so a multi-process HTTP deployment must pass a shared one —
``FastMCP(session_state_store=...)`` — or the worker fielding the next request
will not see what another worker stored.

**Every credential is scoped to one instance.** Production and the polygon keep
separate databases, so an account minted on one does not exist on the other and a
token is only ever a credential for the instance that issued it. Nothing here
falls back from one to the other: a missing polygon token means "register on the
polygon", not "try the production key and see".

Tool VISIBILITY is a separate question from tool AUTHORIZATION, and the two
enable APIs are not interchangeable: ``mcp.enable()`` / ``mcp.disable()`` are
SERVER-GLOBAL and safe only at startup, while ``ctx.enable_components()`` is
scoped to the calling session and is the only one a client's own request may
drive. The gated tools are listed to everyone by default and refuse politely per
call, so an agent can discover them before it holds a token.

``registry_register`` lives here rather than in the gated ``tools/registry.py``
even though it writes to the registry, because it is the one registry write that
**cannot** be token-gated: it is what mints the token. Hiding it would be the
same mistake in a different place — the surface would still dead-end at "get a
token from somewhere else", which is why it is pinned visible everywhere the
listing can be narrowed.
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
    # Out-of-digest and no version bump, so it is the one published-module write that
    # is genuinely repairable rather than permanent.
    "registry_amend_readme",
    "registry_claim_namespace",
    # The production answer to a bad publish (RM21). Not a repair: it stops a
    # version being recommended and corrects nothing, and it does not release the
    # content claim. `registry_unyank` reverses it, which is what makes yank the
    # right first move when something looks wrong and certainty has not arrived.
    "registry_yank",
    "registry_unyank",
    "registry_delete_version",
    "registry_delete_module",
]


def state_key(target: RegistryTarget) -> str:
    """The session-state slot holding this session's token for ``target``.

    FastMCP prefixes it with the session id, so this only has to separate the two
    instances from each other.
    """
    return f"registry_token:{target}"


def hide_gated_tools(mcp: FastMCP) -> None:
    """Hide the token-gated tools until a session authenticates (opt-in).

    Disabling by tag is server-global, which is what we want as the *starting*
    state: nobody sees the registry writes. ``authenticate`` and
    ``registry_register`` then call ``ctx.enable_components(tags={GATED_TAG})``,
    which is scoped to the calling session — other clients stay in the dark, and
    the authenticated one gets a ``tools/list_changed`` notification.

    Off by default, and the reason is this repo's own history: a tool that is not
    listed cannot be discovered, and calling one by name fails with "Unknown
    tool" rather than the message saying how to get a token. That is the same
    dead end the mode axis kept producing. Turn this on for a shared HTTP
    deployment where an unauthenticated client should not even see a publish
    route; leave it off for an authoring session.
    """
    mcp.disable(tags={GATED_TAG})


def _header_key(settings: Settings, target: RegistryTarget) -> str | None:
    """Read the token for ``target`` from the current HTTP request header, if any."""
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
    except Exception:
        return None  # not an HTTP request (stdio / in-memory)
    return request.headers.get(settings.api_key_header_for(target))


async def resolve_api_key(
    ctx: Context, settings: Settings, target: RegistryTarget
) -> str | None:
    """Resolve the registry token for THIS request and THIS instance.

    Returns ``None`` if the caller must authenticate. Gated tools take that
    branch and return a friendly ``OpResult`` rather than raising, so an agent
    gets an actionable message instead of a traceback.
    """
    return (
        _header_key(settings, target)
        or await ctx.get_state(state_key(target))
        or settings.registry_token(target)
    )


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


def register_auth(mcp: FastMCP, settings: Settings) -> None:
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
        ctx: Context,
        target: RegistryTarget = DEFAULT_WRITE_TARGET,
        install_id: str | None = None,
        difficulty: int | None = None,
    ) -> RegistrationResult:
        """Create a registry account and mint its API key. No token needed — this makes
        one.

        Onboarding is self-service: no admin, no email, no approval, just an install-id
        — a proof-of-work string ground locally in about a second, and omitting
        `install_id` grinds one for you. **`target` picks the instance and defaults to
        the polygon**, and the two keep separate databases, so an account on one does
        not exist on the other; register on both with the same install-id. **Save the
        install-id this returns**: it is the account's only recovery path, re-
        registering it reissues a key for the SAME account and ignores `account`, while
        calling again without one silently creates a different account. Put it in `.env`
        as `JMC_INSTALL_ID`, the tokens as `JMC_API_KEY` and `JMC_TEST_API_KEY`.
        `account` obeys the namespace rule — lowercase letters and digits with single
        hyphens, underscores rejected rather than normalised, and a `test-` handle is
        fine on the polygon and refused by production. The token is stored for this
        session, so `authenticate` is unnecessary afterwards; claiming a namespace is a
        separate, irreversible step behind `registry_namespace_available`.
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
            await ctx.set_state(state_key(target), token)
            if settings.hide_gated_until_auth:
                # Session-scoped: reveals the gated tools to THIS client only.
                await ctx.enable_components(tags={GATED_TAG})
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
    async def authenticate(
        token: str, ctx: Context, target: RegistryTarget = DEFAULT_WRITE_TARGET
    ) -> AuthResult:
        """Provide a registry token to unlock the registry write tools for THIS session.

        Stored against your own session and never shared with other clients. Use it when
        you already hold a token — `registry_register` mints one and stores it for you,
        so this is unnecessary after that — and note no token is needed to author,
        validate or compile a module, only to publish one. **A token belongs to one
        instance**: `target` says which and defaults to the polygon, and storing a
        production key against the polygon does not make it work there, it makes the
        next polygon call fail as an unknown key. Authenticate twice if you work with
        both.
        """
        # No format check: the registry issues the token and is the only thing
        # that can judge it. Inventing a prefix rule here would reject valid
        # tokens the moment upstream changes its issuer.
        if not token.strip():
            return AuthResult(authenticated=False, message="Empty token — nothing was stored.")
        await ctx.set_state(state_key(target), token.strip())
        if settings.hide_gated_until_auth:
            # Session-scoped, unlike `mcp.enable`: this client only.
            await ctx.enable_components(tags={GATED_TAG})
        log.info("Session %s stored a registry token for %s", ctx.session_id, target)
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

