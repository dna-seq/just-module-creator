"""Typed configuration for the MCP server.

Everything has a safe default, so the server boots with no environment set.
Values are read from ``JMC_*`` environment variables and an optional ``.env``.

Note the deliberate split between *this* server's config and the just-dna
toolchain's own environment. Cache paths (``JUST_DNA_*``) and ``PHARMVAR_API_KEY``
are read by the enricher itself, straight from the process environment — this
server never *forwards* them. Documented in ``.env.template`` so an author
configures everything in one place.

Reading is a different matter from forwarding. Since literature discovery landed,
this server makes outbound calls of its own, and for those it reads the same
variables the enricher reads — ``JUST_DNA_CONTACT_EMAIL`` for the polite-pool
contact, ``NCBI_API_KEY`` for PubMed pacing — through ``EutilsSettings`` rather
than ``os.environ``, so upstream's precedence is inherited rather than copied.
One ``.env`` configures both surfaces.

The polite-pool contact resolves in three steps, and only the first is ours:
``JMC_USER_EMAIL`` → the enricher's own ``JUST_DNA_CONTACT_EMAIL`` →
:data:`DEFAULT_CONTACT_EMAIL`. Ours goes first because the address identifies
*whose* rate-limit budget is being spent, and the middle step is still inherited
rather than copied — ``build_services`` passes ``None`` when ours is unset and
lets ``EutilsSettings.__post_init__`` do that read, so a change to upstream's
precedence is followed rather than reimplemented.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

#: Which registry instance a call is aimed at. The registry runs two deployments
#: of one image (0.12): production, and the **polygon** — a test instance that
#: accepts `test-`prefixed data and, unlike production, will delete it again.
#:
#: This is OUR vocabulary, not a wire value. The server's own setting is
#: ``REGISTRY_MODE`` and no client ever sends it; a target picks *which host*
#: to call, and each host decides for itself what it is.
RegistryTarget = Literal["prod", "test"]

#: How the tool listing is presented. See ``tool_search.py``.
ToolSearch = Literal["off", "regex", "bm25"]

#: Whether the surface is one layer or two. See ``toolbox.py``.
ToolboxMode = Literal["flat", "layered"]

DEFAULT_REGISTRY_URL = "https://module-registry.just-dna.life"
DEFAULT_POLYGON_URL = "https://module-polygon.just-dna.life"

#: Last-resort polite-pool contact: the **project's own** address, supplied by its
#: owner. This is not the "never invent a contact address" rule being bent — an
#: invented address misattributes traffic to a stranger, and this one attributes it
#: to the people who ship this tool, who accept that.
#:
#: It does mean an author who sets nothing has their traffic pooled under one
#: identity, which is precisely what ``JMC_USER_EMAIL`` exists to undo: NCBI and
#: Unpaywall meter and contact *per address*, so a shared default concentrates both
#: the budget and any abuse report. ``.env.template`` says so where an author will
#: read it. Setting your own is the polite thing and costs one line.
DEFAULT_CONTACT_EMAIL = "contact@example.org"


class Settings(BaseSettings):
    """Server settings sourced from ``JMC_*`` env vars / ``.env`` (all optional)."""

    model_config = SettingsConfigDict(
        env_prefix="JMC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Registry auth — NEVER required at boot. Resolved per-request (see auth.py).
    # Falls back to the toolchain's own REGISTRY_TOKEN via `registry_token()`.
    #
    # There are TWO tokens because there are two instances and they do not share
    # a database: an account on production does not exist on the polygon, and a
    # production token presented there is simply an unknown key. The two never
    # fall back to one another — using a prod token against the polygon would be
    # the silent-substitution mistake, and it would fail confusingly rather than
    # informatively.
    api_key: str | None = None
    test_api_key: str | None = None
    api_key_header: str = "X-Registry-Token"
    test_api_key_header: str = "X-Registry-Test-Token"

    # Hide the token-gated registry tools from a session until it authenticates.
    # OFF by default, and the default is the considered answer: listed-but-refusing
    # keeps them discoverable by an agent that has no token yet, and the refusal
    # says how to get one. Hidden, a call by name gets "Unknown tool" instead —
    # which is the shape of dead end this repo keeps closing. Turn it on where the
    # surface is shared with people who must not see a publish route at all.
    hide_gated_until_auth: bool = False

    # Tool discovery. "off" lists every registered tool; "regex"/"bm25" replace the
    # listing with search_tools + call_tool so an agent finds tools by querying.
    # This narrows what is LISTED and never what is callable — see tool_search.py,
    # and do not read it as the mode axis coming back.
    tool_search: ToolSearch = "off"
    tool_search_max_results: int = 5

    # Two-layer surface. "flat" (default) lists all 56 tools; "layered" lists the
    # core authoring loop and holds the other nine groups behind `toolbox`, which
    # names them and reveals one to the calling session. Worth about 40k tokens of
    # context — measured, see toolbox.py — and it defaults OFF because a reveal
    # only lands mid-session on a client that honours tools/list_changed.
    toolbox: ToolboxMode = "flat"

    # The proof-of-work id an account was registered with. OURS, not the
    # ecosystem's: `registry-client` takes it as a flag and prints it, and reads
    # no variable for it, so there is nothing upstream to inherit here.
    #
    # It is the account's only recovery path — the registry has no email and no
    # admin — and re-registering it reissues a key for the SAME account. Reading
    # it from the environment is what lets `registry_register` be re-run in a
    # later session without minting a second, unreachable account.
    install_id: str | None = None

    # The polite-pool contact, ours-first in a three-step chain resolved in
    # `net.build_services`: this → JUST_DNA_CONTACT_EMAIL → DEFAULT_CONTACT_EMAIL.
    #
    # Named for the *user* rather than for the project because that is what the
    # address means to the services reading it: NCBI's polite pool and Unpaywall
    # both meter and contact per address, so it identifies whose quota is being
    # spent. Left as `None` here rather than defaulted, so `build_services` can
    # tell "unset" from "set", and pass None on to let upstream do its own read.
    user_email: str | None = None

    # The two registry endpoints. `registry_url` is production — the catalog
    # everyone installs from — and `registry_test_url` is the polygon, where a
    # publish can be rehearsed and then deleted.
    #
    # The polygon URL ships as the documented hostname even though a deployment
    # may not be answering on it yet: a `target="test"` call then fails saying
    # the polygon did not answer, which is the honest outcome. The alternative —
    # leaving it unset and silently resolving to production — is the one failure
    # this whole split exists to prevent.
    registry_url: str = DEFAULT_REGISTRY_URL
    registry_test_url: str = DEFAULT_POLYGON_URL
    registry_timeout: float = 600.0

    # Network policy. When true, every tool that could fetch runs cache-only.
    # A hard ceiling: an `offline=False` argument cannot override it.
    offline: bool = False

    # Transport / network (used by the CLI; overridable per command).
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 3011

    # Logging (stdlib logging -> stderr; stdout stays a clean JSON-RPC channel).
    log_level: str = "INFO"

    # Refuse to write outside this directory, when set. Unset = no restriction.
    workspace: str | None = None

    # Which third-party literature services this deployment will talk to.
    # A policy ceiling with the same shape as `offline`: a per-call `sources`
    # argument can NARROW it and can never widen it.
    #   None (unset) -> every source        ""  -> none
    #   "pubmed,europepmc" -> just those two
    # `None` and `""` are deliberately different, so "unset" stays distinguishable
    # from "explicitly nothing".
    literature_sources: str | None = None

    # Semantic Scholar raises the rate limit for a keyed caller. Absent means
    # unauthenticated and slower, never unavailable.
    s2_api_key: str | None = None

    def api_key_header_for(self, target: RegistryTarget) -> str:
        """Which request header carries the token for ``target``.

        Two headers, for the same reason there are two tokens: one HTTP client
        may drive both instances in one session, and a single header would make
        the second call reuse the first instance's credential.
        """
        return self.test_api_key_header if target == "test" else self.api_key_header

    def registry_url_for(self, target: RegistryTarget) -> str:
        """The endpoint for ``target``. The only place a target becomes a URL."""
        return self.registry_test_url if target == "test" else self.registry_url

    def registry_token(self, target: RegistryTarget = "prod") -> str | None:
        """The env-tier registry token for ``target``.

        Production is ``JMC_API_KEY`` else ``REGISTRY_TOKEN``; the polygon is
        ``JMC_TEST_API_KEY`` else ``REGISTRY_TEST_TOKEN``. The toolchain-level
        fallback matters because ``REGISTRY_TOKEN`` is what ``registry-client``
        and the rest of the just-dna toolchain already read; an author who has
        logged in once should not have to re-declare the token for this server.

        **The two never substitute for each other.** The instances keep separate
        databases, so a production token is not a weaker credential on the
        polygon — it is a key for an account that does not exist there. Falling
        back would turn "you have no polygon account yet" into "the registry
        rejected your token", which sends the author to fix the wrong thing.
        """
        if target == "test":
            return self.test_api_key or os.environ.get("REGISTRY_TEST_TOKEN") or None
        return self.api_key or os.environ.get("REGISTRY_TOKEN") or None

    def semantic_scholar_key(self) -> str | None:
        """``JMC_S2_API_KEY`` else ``S2_API_KEY`` — the name S2's own docs use."""
        return self.s2_api_key or os.environ.get("S2_API_KEY") or None

    def allowed_literature_sources(self) -> frozenset[str] | None:
        """The sources this deployment permits, or ``None`` for "no restriction".

        ``None`` (unset) and an empty string are different answers and must stay
        that way: unset means every source, ``""`` means the operator switched
        them all off. Collapsing the two would turn a deliberate refusal into a
        default, which is the same mistake as reading ``None`` as ``False``.
        """
        if self.literature_sources is None:
            return None
        return frozenset(s.strip() for s in self.literature_sources.split(",") if s.strip())
