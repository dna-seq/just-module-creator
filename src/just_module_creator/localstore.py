"""This machine's memory for the plugin: registry accounts, and the author's todo list.

`userconfig`'s `.env` holds one value per name, which is right for an email and wrong for
an author who has a polygon account, a production account and a second production
account for an organisation's namespace. So the lists live beside it in `state.json`, in
the same directory (so `JMC_CONFIG_FILE` moves both), and it survives plugin updates for
the same reason.

**Every write takes a verified backup first.** `backup` copies the current file into
`backups/`, reads the copy back and compares hashes, and only then may the write go ahead;
a copy that does not verify refuses the write. It is the capture-before-destroy rule the
sidecar refresh follows, applied to the files here that hold credentials; `userconfig.backup`
is shared with the settings file.

A lock serialises writers, because two sessions on one machine are two server processes.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from just_module_creator import userconfig

STATE_NAME = "state.json"

#: What a token check can answer. `invalid` is the registry refusing the key (401/403);
#: `unreachable` and `timeout` are the instance not answering, which proves nothing about it.
TOKEN_STATUSES = frozenset({"unchecked", "valid", "invalid", "unreachable", "timeout"})


class StoredAccount(BaseModel):
    target: str
    account: str
    token: str
    install_id: str | None = None
    namespaces: list[str] = Field(default_factory=list)
    default: bool = False
    saved_at: str
    namespaces_checked_at: str | None = None
    #: The last check's answer — one of `TOKEN_STATUSES` — and when it was given. Only
    #: `invalid` takes an account out of token selection; the others say nothing about the
    #: key. The record is kept whatever the answer.
    status: str = "unchecked"
    status_at: str | None = None
    status_detail: str | None = None


class TodoRecord(BaseModel):
    id: int
    text: str
    module: str | None = None
    created_at: str
    done_at: str | None = None


class State(BaseModel):
    version: int = 1
    accounts: list[StoredAccount] = Field(default_factory=list)
    todos: list[TodoRecord] = Field(default_factory=list)
    next_todo_id: int = 1


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def state_file() -> Path:
    return userconfig.config_file().with_name(STATE_NAME)


def write_atomic(path: Path, text: str) -> None:
    """Replace `path` with `text`, owner-only, never leaving a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, path)


def load() -> State:
    path = state_file()
    if not path.is_file():
        return State()
    return State.model_validate_json(path.read_text(encoding="utf-8"))


def update[T](change: Callable[[State], T]) -> T:
    """Read, apply `change`, back up, write — all under the lock. Returns what `change` returns."""
    path = state_file()
    with userconfig.lock(path):
        state = load()
        result = change(state)
        userconfig.backup(path)
        write_atomic(path, state.model_dump_json(indent=2) + "\n")
    return result


# --- accounts -------------------------------------------------------------------------


def accounts_for(state: State, target: str) -> list[StoredAccount]:
    return [a for a in state.accounts if a.target == target]


def pick_token(state: State, target: str, namespace: str | None) -> str | None:
    """The saved token a call should use, or None when none answers the question.

    With a namespace: the one saved account on `target` that owns it; when several do (an
    organisation's namespace shared between accounts), the default among them, and None if
    the default is not one of them. Without: the default account on `target`.
    """
    usable = [a for a in accounts_for(state, target) if a.status != "invalid"]
    if namespace is not None:
        owners = [a for a in usable if namespace in a.namespaces]
        if len(owners) > 1:
            owners = [a for a in owners if a.default]
        return owners[0].token if len(owners) == 1 else None
    defaults = [a for a in usable if a.default]
    return defaults[0].token if defaults else None


def save_account(
    state: State,
    *,
    target: str,
    account: str,
    token: str,
    install_id: str | None,
    namespaces: list[str],
) -> StoredAccount:
    """Insert or refresh one (target, account). The first account on a target is its default."""
    existing = next(
        (a for a in state.accounts if a.target == target and a.account == account), None
    )
    stamp = now()
    if existing is None:
        existing = StoredAccount(
            target=target,
            account=account,
            token=token,
            saved_at=stamp,
            default=not accounts_for(state, target),
        )
        state.accounts.append(existing)
    existing.token = token
    existing.install_id = install_id or existing.install_id
    existing.namespaces = sorted(set(namespaces))
    existing.namespaces_checked_at = stamp
    existing.saved_at = stamp
    # The registry has just answered for this token (it minted it, or whoami named it).
    existing.status, existing.status_at, existing.status_detail = "valid", stamp, None
    return existing


def account_for_token(state: State, target: str, token: str) -> StoredAccount | None:
    return next((a for a in accounts_for(state, target) if a.token == token), None)


def saved_install_id(state: State) -> str | None:
    """The most recently saved install-id on any account, for a register that names none."""
    with_ids = [a for a in state.accounts if a.install_id]
    return max(with_ids, key=lambda a: a.saved_at).install_id if with_ids else None


# --- todos ----------------------------------------------------------------------------


def add_todo(state: State, text: str, module: str | None) -> TodoRecord:
    record = TodoRecord(id=state.next_todo_id, text=text, module=module, created_at=now())
    state.todos.append(record)
    state.next_todo_id += 1
    return record
