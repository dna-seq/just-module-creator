"""Where this server's configuration lives, and the one place it is written.

**Two files, read in a fixed order, and neither is the plugin's own directory.**
A plugin install is a per-version copy (`~/.claude/plugins/cache/<mkt>/<plugin>/<version>/`,
`~/.codex/plugins/cache/<mkt>/<plugin>/<version>/`), so a `.env` there is gone at the next
update. And the working directory differs by host: Claude Code starts the server in the
author's project, Codex (with `"cwd": "."`) in the plugin copy. The skills told the agent
to put it in "`.env`", the agent wrote the project's, and under Codex the server never
read it — an email asked for and lost after the first run, and a registry token with it.

So, highest precedence first, never overriding a value already set:

1. the process environment (a shell export, a host's `env` block);
2. the project `.env`, found by walking up from the **working directory** — not from this
   file, which is what a bare `load_dotenv()` does, and which under any install is the
   plugin copy;
3. the **user config file**, `platformdirs.user_config_dir("just-module-creator")/.env`
   (`~/.config/just-module-creator/.env` on Linux), or wherever `JMC_CONFIG_FILE` points.
   It survives plugin updates and is the same for every host and every project.

Only the third is ever written, by `remember`, and only for a name on `SAVABLE`: this is a
credential store for a server that runs tools on an agent's behalf, and an unrestricted
key would let a tool call plant `PATH` or `PYTHONPATH` for the next start.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import platformdirs
from dotenv import dotenv_values, find_dotenv, load_dotenv, set_key
from just_dna_enricher.caches import CACHE_LANES
from just_dna_enricher.locations import CACHE_BASE_VAR

from just_module_creator.settings import Settings

APP_NAME = "just-module-creator"
CONFIG_FILE_VAR = "JMC_CONFIG_FILE"

_PREFIX = (Settings.model_config.get("env_prefix") or "").upper()

#: Names `remember` may write. **Derived**: every field of ours (a setting added later is
#: savable without anyone remembering this line), every enricher cache location, and the two
#: upstream variables the contact chain and the NCBI budget read.
SAVABLE: frozenset[str] = frozenset(
    {f"{_PREFIX}{name}".upper() for name in Settings.model_fields}
    | {lane.env_var for lane in CACHE_LANES if lane.env_var}
    | {CACHE_BASE_VAR, "JUST_DNA_CONTACT_EMAIL", "NCBI_API_KEY"}
)

#: Values never echoed back whole. Decided on the name, because a token has no shape to
#: recognise and an install-id is the account's only recovery path.
_SECRET_MARKERS = ("KEY", "TOKEN", "INSTALL_ID", "SECRET", "PASSWORD")

#: Where each variable present after `load_env` came from. Filled once at start; a value
#: `remember` adds later is recorded here too.
_ORIGINS: dict[str, str] = {}


def config_file() -> Path:
    """The user config file: `JMC_CONFIG_FILE` if set, else the platform's config dir."""
    override = os.environ.get(CONFIG_FILE_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False)) / ".env"


def is_secret(name: str) -> bool:
    return any(marker in name.upper() for marker in _SECRET_MARKERS)


def shown(name: str, value: str | None) -> str | None:
    """A value as it may appear in a tool result: secrets keep their last four characters."""
    if value is None or not is_secret(name):
        return value
    return f"…{value[-4:]}" if len(value) > 8 else "…"


def load_env() -> None:
    """Load the project `.env`, then the user config file, under the process environment.

    `override=False` throughout, so the order above is the precedence. Records where each
    variable came from, which is what lets `remember` say *why* a saved value is not the one
    in force.
    """
    _ORIGINS.clear()
    for name in os.environ:
        _ORIGINS[name] = "environment"
    project = find_dotenv(usecwd=True)
    user = config_file()
    for label, path in (("project .env", project), ("user config", str(user))):
        if not path or not Path(path).is_file():
            continue
        for name in dotenv_values(path):
            _ORIGINS.setdefault(name, f"{label} ({path})")
        load_dotenv(path, override=False)


def origin(name: str) -> str | None:
    """Where the value in force came from, or None when the variable is unset."""
    if not os.environ.get(name, "").strip():
        return None
    return _ORIGINS.get(name, "environment")


def saved(name: str) -> str | None:
    """The value the user config file holds for `name`, or None."""
    path = config_file()
    if not path.is_file():
        return None
    value = dotenv_values(path).get(name)
    return value if value and value.strip() else None


@dataclass(frozen=True)
class Remembered:
    written: bool
    previous: str | None
    in_force: bool


def remember(name: str, value: str, *, replace: bool) -> Remembered:
    """Write `name=value` into the user config file, and into this process when nothing outranks it.

    Refuses a name outside `SAVABLE` (`KeyError`). With `replace=False` a different value
    already saved is left alone and reported as `previous`; the caller decides. The file is
    created owner-only, since it holds registry tokens.
    """
    if name not in SAVABLE:
        raise KeyError(name)
    previous = saved(name)
    if previous is not None and previous != value and not replace:
        return Remembered(written=False, previous=previous, in_force=os.environ.get(name) == value)
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.touch(mode=0o600, exist_ok=True)
    # Tightened on every write, not only at creation: a file the author made by hand, or
    # one copied from a project `.env`, would otherwise keep whatever it had.
    path.chmod(0o600)
    set_key(str(path), name, value, quote_mode="auto")
    # The process gets it too unless a higher layer already set it: the shell and the
    # project `.env` outrank this file at the next start, so they outrank it now.
    outranked = _ORIGINS.get(name) not in (None, "user config", f"user config ({path})")
    if not outranked or not os.environ.get(name, "").strip():
        os.environ[name] = value
        _ORIGINS[name] = f"user config ({path})"
    return Remembered(written=True, previous=previous, in_force=os.environ.get(name) == value)
