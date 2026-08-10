"""Runtime, per-session authentication for the key-gated registry tools.

Design goals (multi-user safe):

* The server ALWAYS boots — a missing token is never a startup error. Authoring
  a module needs no registry account at all; only publishing does.
* A token is resolved PER REQUEST, never stored in a server-global mutable
  field. Resolution precedence:
    1. per-request HTTP header (``settings.api_key_header``)  -> multi-user safe
    2. per-session store keyed by ``ctx.session_id`` (set via ``authenticate``)
    3. ``JMC_API_KEY`` env, else ``REGISTRY_TOKEN`` (single-tenant / local)
* ``authenticate`` writes ONLY into the caller's own session slot, so one HTTP
  client can never read or clobber another client's token.

Anti-pattern (documented, off by default): ``mcp.enable(tags=...)`` to "unlock"
gated tools is SERVER-GLOBAL — it would expose tools to every connected client.
Safe only for single-tenant stdio. See ``register_stdio_only_unlock`` below.
"""

from __future__ import annotations

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import AuthResult, OpResult
from just_module_creator.settings import Settings

log = get_logger()

# Tools tagged with this are token-gated.
GATED_TAG = "registry_write"
GATED_TOOLS = ["registry_whoami", "registry_publish", "registry_claim_namespace"]


class SessionKeyStore:
    """Per-session registry tokens. The ONLY auth state — no shared/global token."""

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    @staticmethod
    def _sid(ctx: Context | None) -> str:
        sid = getattr(ctx, "session_id", None) if ctx else None
        return sid or "__local__"

    def set(self, ctx: Context | None, key: str) -> None:
        self._keys[self._sid(ctx)] = key

    def get(self, ctx: Context | None) -> str | None:
        return self._keys.get(self._sid(ctx))


def _header_key(settings: Settings) -> str | None:
    """Read the token from the current HTTP request header, if any."""
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
    except Exception:
        return None  # not an HTTP request (stdio / in-memory)
    return request.headers.get(settings.api_key_header)


def resolve_api_key(ctx: Context | None, settings: Settings, store: SessionKeyStore) -> str | None:
    """Resolve the registry token for THIS request (see module docstring)."""
    return _header_key(settings) or store.get(ctx) or settings.registry_token()


def require_key(ctx: Context | None, settings: Settings, store: SessionKeyStore) -> str | None:
    """Return the resolved token, or ``None`` if the caller must authenticate.

    Gated tools use this and return a friendly ``OpResult`` on ``None`` rather
    than raising, so agents get an actionable message.
    """
    return resolve_api_key(ctx, settings, store)


def unauthenticated_result(settings: Settings) -> OpResult:
    return OpResult(
        success=False,
        message=(
            "This tool needs a registry token. Call `authenticate` with a token for "
            f"this session, send the `{settings.api_key_header}` header (HTTP), or set "
            "JMC_API_KEY / REGISTRY_TOKEN in the environment. Authoring, validating "
            "and compiling a module need no token — only registry writes do."
        ),
    )


def register_auth(mcp: FastMCP, settings: Settings, store: SessionKeyStore) -> None:
    """Register the always-on ``authenticate`` tool (per-session scope)."""

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Authenticate to the registry (this session)",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        )
    )
    def authenticate(token: str, ctx: Context) -> AuthResult:
        """Provide a registry token to unlock the registry write tools for THIS session.

        The token is stored only against your own session and is never shared
        with other clients. Get one by registering with the registry
        (``registry-client register``). No token is needed to author, validate or
        compile a module — only to publish one.
        """
        # No format check: the registry issues the token and is the only thing
        # that can judge it. Inventing a prefix rule here would reject valid
        # tokens the moment upstream changes its issuer.
        if not token.strip():
            return AuthResult(authenticated=False, message="Empty token — nothing was stored.")
        store.set(ctx, token.strip())
        log.info("Session %s stored a registry token", SessionKeyStore._sid(ctx))
        return AuthResult(
            authenticated=True,
            unlocked_tools=GATED_TOOLS,
            message=(
                "Token stored for this session. Call `registry_whoami` to confirm the "
                "registry accepts it — nothing here validated it."
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
