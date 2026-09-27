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
from datetime import UTC, datetime, timedelta

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

#: How long a `valid` answer is trusted at start before the token is asked about again.
FRESH_FOR = timedelta(hours=1)


@dataclass(frozen=True)
class TokenCheck:
    target: str
    account: str
    status: str
    namespaces: list[str] | None
    detail: str | None


def check_token(
    target: RegistryTarget, token: str, settings: Settings, timeout: float
) -> tuple[str, list[str] | None, str | None, str | None]:
    """`(status, namespaces, detail, account)` for one token; the last two only when `valid`."""
    try:
        with client_for(target, settings, token=token, timeout=timeout) as client:
            reply = dict(client.whoami())
    except RegistryError as exc:
        status = "invalid" if exc.status_code in _TOKEN_REFUSED else "unreachable"
        return status, None, str(exc), None
    except httpx.TimeoutException as exc:
        return "timeout", None, f"no answer within {timeout:g}s ({type(exc).__name__})", None
    except httpx.TransportError as exc:
        return "unreachable", None, f"{type(exc).__name__}: {exc}", None
    namespaces = [str(n) for n in reply.get("namespaces") or []]
    return "valid", namespaces, None, str(reply.get("account") or "") or None


def _fresh(saved: localstore.StoredAccount, now: datetime) -> bool:
    """A `valid` answer younger than `FRESH_FOR` — worth trusting instead of asking again."""
    if saved.status != "valid" or saved.status_at is None:
        return False
    return now - datetime.fromisoformat(saved.status_at) < FRESH_FOR


def validate_saved(
    settings: Settings,
    target: str | None = None,
    timeout: float = STARTUP_TIMEOUT,
    *,
    skip_fresh: bool = False,
) -> list[TokenCheck]:
    """Check every saved account (on `target`, or all) and record each answer.

    `skip_fresh` leaves alone an account answered `valid` within `FRESH_FOR`: the start-up
    check passes it, because several sessions start servers on one machine and the polygon
    rate-limits a burst, which would record an outage over a good answer. `refresh` does not.
    """
    state = localstore.load()
    now = datetime.now(UTC)
    checks: list[TokenCheck] = []
    for saved in state.accounts:
        if target is not None and saved.target != target:
            continue
        if skip_fresh and _fresh(saved, now):
            continue
        which: RegistryTarget = "prod" if saved.target == "prod" else "test"
        status, namespaces, detail, _ = check_token(which, saved.token, settings, timeout)
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


def import_env_tokens(settings: Settings, timeout: float = STARTUP_TIMEOUT) -> list[str]:
    """Save the environment's registry token for each instance, if no saved account holds it.

    The single-token setup (`JMC_API_KEY` / `JMC_TEST_API_KEY`, and `JMC_INSTALL_ID`) predates
    the store, and a token left outside it is one a second saved account would silently
    outrank as the default. So at start it goes in, with the environment's install-id, after
    one `whoami` says whose it is. A token already saved only gains a missing install-id —
    no request. A token the registry does not answer for is left where it is.
    """
    env_install = (settings.install_id or "").strip() or None
    state = localstore.load()
    imported: list[str] = []
    for which in ("prod", "test"):
        target: RegistryTarget = "prod" if which == "prod" else "test"
        token = (settings.registry_token(target) or "").strip()
        if not token:
            continue
        held = localstore.account_for_token(state, target, token)
        if held is not None:
            if env_install and not held.install_id:
                account = held.account

                def _fill(state: localstore.State, target=target, account=account) -> None:
                    for a in localstore.accounts_for(state, target):
                        if a.account == account and not a.install_id:
                            a.install_id = env_install

                localstore.update(_fill)
                imported.append(f"{account}@{target} install-id")
            continue
        status, namespaces, _, name = check_token(target, token, settings, timeout)
        if status != "valid" or namespaces is None or not name:
            continue
        localstore.update(
            lambda state, target=target, name=name, token=token, namespaces=namespaces: (
                localstore.save_account(
                    state,
                    target=target,
                    account=name,
                    token=token,
                    install_id=env_install,
                    namespaces=namespaces,
                )
            )
        )
        imported.append(f"{name}@{target}")
    return imported


def start_background_validation(settings: Settings) -> threading.Thread | None:
    """Import the environment's tokens and validate saved ones on a daemon thread.

    Nothing to do offline, or with nothing saved and no environment token. A failure is
    logged and never stops the server: a check that could not run leaves the previous
    answers in place.
    """
    has_env = any(settings.registry_token(t) for t in ("prod", "test"))
    if settings.offline or not (localstore.load().accounts or has_env):
        return None

    def _run() -> None:
        try:
            imported = import_env_tokens(settings)
            if imported:
                log.info("Saved from the environment at start: %s", ", ".join(imported))
            checks = validate_saved(settings, skip_fresh=True)
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
