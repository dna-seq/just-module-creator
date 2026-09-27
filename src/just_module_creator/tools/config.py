"""ESSENTIALS — keeping an answer the author gave, across sessions, hosts and plugin updates.

The contact email, a registry token, the install-id that is an account's only recovery
path, a cache offer accepted or declined: each is asked once and has to be there next
time. `userconfig` says where that is and why it is not the project's `.env`.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import TypeAdapter, ValidationError

from just_module_creator import userconfig
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import SettingState
from just_module_creator.net import NetworkServices
from just_module_creator.settings import Settings

log = get_logger()

_PREFIX = (Settings.model_config.get("env_prefix") or "").upper()


def _field_for(name: str) -> str | None:
    """The `Settings` field a `JMC_*` name configures, or None for an upstream variable."""
    if not name.startswith(_PREFIX):
        return None
    field = name[len(_PREFIX) :].lower()
    return field if field in Settings.model_fields else None


def _state(
    name: str, note: str, *, written: bool = False, previous: str | None = None
) -> SettingState:
    source = userconfig.origin(name)
    return SettingState(
        name=name,
        in_force=userconfig.shown(name, os.environ.get(name) if source else None),
        source=source,
        saved=userconfig.shown(name, userconfig.saved(name)),
        previous=userconfig.shown(name, previous),
        written=written,
        config_file=str(userconfig.config_file()),
        note=note,
    )


def register_config(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    def _apply_live(name: str, value: str) -> None:
        # The running server read its settings once at start, so a saved value would
        # otherwise wait for a restart. Only what this process actually uses is updated.
        field = _field_for(name)
        if field is not None:
            annotation = Settings.model_fields[field].annotation
            setattr(settings, field, TypeAdapter(annotation).validate_python(value))
        if name == "JMC_USER_EMAIL" or (
            name == "JUST_DNA_CONTACT_EMAIL" and not (settings.user_email or "").strip()
        ):
            services.eutils_settings.email = value

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Remember a setting",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def remember_setting(
        name: str, value: str | None = None, replace: bool = False
    ) -> SettingState:
        """Save a setting for every later session, or, with no `value`, say whether it is set.

        Writes the user config file (`config_file` in the result), which survives plugin
        updates and is shared by every host and project, and applies the value to this
        session at once. Use it for anything an author answers once: `JMC_USER_EMAIL`,
        `JMC_TEST_API_KEY` / `JMC_API_KEY`, `JMC_INSTALL_ID`, `JMC_CACHE_PREWARM` /
        `JMC_CACHE_FULL`, a cache location. Never write these into a project `.env`
        yourself: under some hosts the server does not read it. A different value already
        saved is kept unless `replace=true`; tokens are the case for that, since the last
        key minted is the one that works. A shell variable or a project `.env` outranks the
        file, and `source` says which is in force. Secrets come back as their last four
        characters.
        """
        name = name.strip()
        if name not in userconfig.SAVABLE:
            raise ToolError(
                f"{name!r} is not a setting this server reads. Savable names: "
                f"{', '.join(sorted(userconfig.SAVABLE))}."
            )
        if value is None:
            return _state(name, "Read only; nothing was written.")
        value = value.strip()
        if not value:
            raise ToolError(
                "An empty value saves nothing. To decline a yes/no offer, save `false`."
            )
        field = _field_for(name)
        if field is not None:
            try:
                TypeAdapter(Settings.model_fields[field].annotation).validate_python(value)
            except ValidationError as exc:
                raise ToolError(
                    f"{value!r} is not a valid {name}: {exc.errors()[0]['msg']}"
                ) from exc

        outcome = userconfig.remember(name, value, replace=replace)
        if not outcome.written:
            return _state(
                name,
                "Not written: a different value is already saved. Ask before replacing it, then "
                "call again with replace=true.",
                previous=outcome.previous,
            )
        if outcome.in_force:
            _apply_live(name, value)
            note = "Saved, and in force for this session and every later one."
        else:
            note = (
                "Saved, but a value set in the shell or a project .env outranks the user config "
                "file, so that one stays in force."
            )
        log.info("Saved %s to %s", name, userconfig.config_file())
        return _state(name, note, written=True, previous=outcome.previous)
