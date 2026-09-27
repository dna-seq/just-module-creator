"""Is each saved registry token still good? Asked once at server start, and on request.

An agent used to learn a token was dead by spending a publish attempt on it, or a
`registry_whoami` per account. The server asks instead, off the startup path, and writes
the answer onto each saved account with its time: `valid`, `invalid`, `unreachable` or
`timeout`. A valid answer also refreshes the account's namespaces, which is what token
selection by namespace reads.

**Only `invalid` is a verdict on the key.** An instance that did not answer, or answered
with an outage, says nothing about it, so those two are recorded as what they are and the
account stays selectable.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import httpx
from just_dna_registry import RegistryError

from just_module_creator import localstore
from just_module_creator.logging_setup import get_logger
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import client_for

log = get_logger()

#: Short on purpose: this runs for every saved account at start, and a hung instance must
#: not hold the answer for the ones that respond.
STARTUP_TIMEOUT = 10.0

_TOKEN_REFUSED = frozenset({401, 403})


@dataclass(frozen=True)
class TokenCheck:
    target: str
    account: str
    status: str
    namespaces: list[str] | None
    detail: str | None


def check_token(
    target: RegistryTarget, token: str, settings: Settings, timeout: float
) -> tuple[str, list[str] | None, str | None]:
    """`(status, namespaces, detail)` for one token; namespaces only when `valid`."""
    try:
        with client_for(target, settings, token=token, timeout=timeout) as client:
            reply = dict(client.whoami())
    except RegistryError as exc:
        status = "invalid" if exc.status_code in _TOKEN_REFUSED else "unreachable"
        return status, None, str(exc)
    except httpx.TimeoutException as exc:
        return "timeout", None, f"no answer within {timeout:g}s ({type(exc).__name__})"
    except httpx.TransportError as exc:
        return "unreachable", None, f"{type(exc).__name__}: {exc}"
    return "valid", [str(n) for n in reply.get("namespaces") or []], None


def validate_saved(
    settings: Settings, target: str | None = None, timeout: float = STARTUP_TIMEOUT
) -> list[TokenCheck]:
    """Check every saved account (on `target`, or all) and record each answer."""
    state = localstore.load()
    checks: list[TokenCheck] = []
    for saved in state.accounts:
        if target is not None and saved.target != target:
            continue
        which: RegistryTarget = "prod" if saved.target == "prod" else "test"
        status, namespaces, detail = check_token(which, saved.token, settings, timeout)
        checks.append(TokenCheck(saved.target, saved.account, status, namespaces, detail))
    if not checks:
        return checks

    def _record(state: localstore.State) -> None:
        stamp = localstore.now()
        answers = {(c.target, c.account): c for c in checks}
        for account in state.accounts:
            check = answers.get((account.target, account.account))
            if check is None:
                continue
            account.status, account.status_at, account.status_detail = (
                check.status,
                stamp,
                check.detail,
            )
            if check.namespaces is not None:
                account.namespaces = sorted(set(check.namespaces))
                account.namespaces_checked_at = stamp

    localstore.update(_record)
    return checks


def start_background_validation(settings: Settings) -> threading.Thread | None:
    """Validate saved tokens on a daemon thread, so the server answers while it runs.

    Nothing to do offline or with nothing saved. A failure is logged and never stops the
    server: a check that could not run leaves the previous answers in place.
    """
    if settings.offline or not localstore.load().accounts:
        return None

    def _run() -> None:
        try:
            checks = validate_saved(settings)
        except Exception:
            log.exception("Saved-token check at start did not complete")
            return
        log.info(
            "Saved-token check at start: %s",
            ", ".join(f"{c.account}@{c.target}={c.status}" for c in checks),
        )

    thread = threading.Thread(target=_run, name="token-check", daemon=True)
    thread.start()
    return thread
