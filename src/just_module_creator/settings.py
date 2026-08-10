"""Typed configuration for the MCP server.

Everything has a safe default, so the server boots with no environment set.
Values are read from ``JMC_*`` environment variables and an optional ``.env``.

Note the deliberate split between *this* server's config and the just-dna
toolchain's own environment. Cache paths (``JUST_DNA_*``), NCBI pacing keys and
``PHARMVAR_API_KEY`` are read by the enricher itself, straight from the process
environment — this server neither reads nor forwards them. Documented in
``.env.example`` so an author configures them in one place.
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

    def registry_token(self) -> str | None:
        """The env-tier registry token: ``JMC_API_KEY`` else ``REGISTRY_TOKEN``.

        The fallback matters because ``REGISTRY_TOKEN`` is what ``registry-client``
        and the rest of the just-dna toolchain already read; an author who has
        logged in once should not have to re-declare the token for this server.
        """
        return self.api_key or os.environ.get("REGISTRY_TOKEN") or None
