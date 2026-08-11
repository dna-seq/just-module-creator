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
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Mode = Literal["essentials", "extended"]

DEFAULT_REGISTRY_URL = "https://module-registry.just-dna.life"


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
    api_key: str | None = None
    api_key_header: str = "X-Registry-Token"

    # The proof-of-work id an account was registered with. OURS, not the
    # ecosystem's: `registry-client` takes it as a flag and prints it, and reads
    # no variable for it, so there is nothing upstream to inherit here.
    #
    # It is the account's only recovery path — the registry has no email and no
    # admin — and re-registering it reissues a key for the SAME account. Reading
    # it from the environment is what lets `registry_register` be re-run in a
    # later session without minting a second, unreachable account.
    install_id: str | None = None

    # Registry endpoint. The published instance by default.
    registry_url: str = DEFAULT_REGISTRY_URL
    registry_timeout: float = 600.0

    # Tool surface. "essentials" is the authoring loop you cannot work without;
    # "extended" adds enrichment, integrity, round-trip and registry reads.
    mode: Mode = "essentials"

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

    def registry_token(self) -> str | None:
        """The env-tier registry token: ``JMC_API_KEY`` else ``REGISTRY_TOKEN``.

        The fallback matters because ``REGISTRY_TOKEN`` is what ``registry-client``
        and the rest of the just-dna toolchain already read; an author who has
        logged in once should not have to re-declare the token for this server.
        """
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
