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
key would let a tool call plant `PATH`, or a registry URL that collects the next token.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import platformdirs
from dotenv import dotenv_values, find_dotenv, load_dotenv, set_key
from filelock import FileLock
from just_dna_enricher.caches import CACHE_LANES
from just_dna_enricher.locations import CACHE_BASE_VAR

from just_module_creator.settings import Settings

APP_NAME = "just-module-creator"
CONFIG_FILE_VAR = "JMC_CONFIG_FILE"
BACKUP_DIR = "backups"
#: The newest backups kept per file; the owner chose the number.
KEEP_BACKUPS = 50

_PREFIX = (Settings.model_config.get("env_prefix") or "").upper()

#: The `Settings` fields an author answers once, and which `remember` may therefore write.
#: **An allowlist, not a derivation, and that is deliberate** — it answers a question about
#: intent (what is an author's own answer?) that the schema cannot. Deriving it from every
#: field made `JMC_REGISTRY_URL` writable, so one tool call, from a session reading untrusted
#: fulltext, could send every later session's token to another host; `JMC_WORKSPACE` and
#: `JMC_OFFLINE` would have moved the containment boundary and the egress ceiling. A test
#: puts every field in exactly one of these two, so a new setting forces the decision.
SAVABLE_FIELDS: frozenset[str] = frozenset(
    {
        "user_email",
        "cache_prewarm",
        "cache_full",
        "s2_api_key",
    }
)

#: Every other field, with why an agent may not set it. Deployment configuration belongs to
#: whoever starts the server; the boundaries are not an author's answer at all.
NOT_SAVABLE_FIELDS: dict[str, str] = {
    # Many per instance, each with its namespaces: `localstore` holds them, and a token
    # saved here as well would be a second home for the same fact.
    "api_key": "registry_accounts",
    "test_api_key": "registry_accounts",
    "install_id": "registry_accounts",
    "registry_url": "redirects tokens",
    "registry_test_url": "redirects tokens",
    "api_key_header": "wire",
    "test_api_key_header": "wire",
    "workspace": "containment",
    "offline": "egress ceiling",
    "hide_gated_until_auth": "deployment",
    "tool_search": "deployment",
    "tool_search_max_results": "deployment",
    "toolbox": "deployment",
    "registry_timeout": "deployment",
    "snapshot_route": "deployment",
    "proxy_target": "deployment",
    "transport": "deployment",
    "host": "deployment",
    "port": "deployment",
    "log_level": "deployment",
    "literature_sources": "deployment",
}

#: Names `remember` may write: the fields above, every enricher cache location, and the two
#: upstream variables the contact chain and the NCBI budget read.
SAVABLE: frozenset[str] = frozenset(
    {f"{_PREFIX}{name}".upper() for name in SAVABLE_FIELDS}
    | {lane.env_var for lane in CACHE_LANES if lane.env_var}
    | {CACHE_BASE_VAR, "JUST_DNA_CONTACT_EMAIL", "NCBI_API_KEY"}
)

#: Values never echoed back whole. Decided on the name, because a token has no shape to
#: recognise and an install-id is the account's only recovery path.
_SECRET_MARKERS = ("KEY", "TOKEN", "INSTALL_ID", "SECRET", "PASSWORD")


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

    `override=False` throughout, so the order above is the precedence.
    """
    for path in (find_dotenv(usecwd=True), str(config_file())):
        if path and Path(path).is_file():
            load_dotenv(path, override=False)


def origin(name: str) -> str | None:
    """Where the value in force came from, or None when the variable is unset.

    **Decided by value, not by recording what `load_env` loaded**, because we are not the
    first loader in the process: constructing the enricher's `EutilsSettings` (which
    `net.build_services` does) runs `locations.load_env`, exporting the working directory's
    whole `.env`, and so does resolving a cache path. A snapshot taken after that called a
    project `.env` value "environment" (`F115`, format-tree `S124`). The cost of deciding by value: a shell export identical to a file's value
    is attributed to the file, which names a place that does hold it.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    for label, path in (
        ("project .env", find_dotenv(usecwd=True)),
        ("user config", str(config_file())),
    ):
        if path and Path(path).is_file() and (dotenv_values(path).get(name) or "").strip() == value:
            return f"{label} ({path})"
    return "environment"


def saved(name: str) -> str | None:
    """The value the user config file holds for `name`, or None."""
    path = config_file()
    if not path.is_file():
        return None
    value = dotenv_values(path).get(name)
    return value if value and value.strip() else None


def lock(path: Path) -> FileLock:
    """Serialise writers of `path`: two sessions on one machine are two server processes."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return FileLock(str(path.with_name(path.name + ".lock")))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(path: Path) -> Path | None:
    """Copy `path` into `backups/`, verify the copy, prune past `KEEP_BACKUPS`.

    Returns the copy, or None when there was nothing to back up. Raises `OSError` when the
    copy does not read back identical, and the caller must then not write.
    """
    if not path.is_file():
        return None
    folder = path.parent / BACKUP_DIR
    folder.mkdir(exist_ok=True, mode=0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    copy = folder / f"{path.name}.{stamp}"
    shutil.copyfile(path, copy)
    copy.chmod(0o600)
    if _digest(copy) != _digest(path):
        raise OSError(f"backup of {path} did not verify; nothing was written")
    # The stamp sorts lexically in time order, so the oldest are at the front.
    older = sorted(folder.glob(f"{path.name}.*"))[:-KEEP_BACKUPS]
    for stale in older:
        stale.unlink()
    return copy


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
    with lock(path):
        return _remember_locked(path, name, value, previous)


def _remember_locked(path: Path, name: str, value: str, previous: str | None) -> Remembered:
    # The shell and the project `.env` outrank this file at the next start, so they outrank
    # it now; a value the file itself supplied is the one being replaced.
    source = origin(name)
    outranked = source is not None and not source.startswith("user config")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.touch(mode=0o600, exist_ok=True)
    # Tightened on every write, not only at creation: a file the author made by hand, or
    # one copied from a project `.env`, would otherwise keep whatever it had.
    path.chmod(0o600)
    backup(path)
    set_key(str(path), name, value, quote_mode="auto")
    if not outranked:
        os.environ[name] = value
    return Remembered(written=True, previous=previous, in_force=os.environ.get(name) == value)
