"""ESSENTIALS — what this machine remembers between sessions: registry accounts and the todo list.

Both live in `localstore`'s `state.json` beside the user config file, so they survive
plugin updates and are the same for every host and project. Every write backs the file
up first and verifies the copy.

The two tools share a module because they share the store and nothing else. What they
are for differs: accounts decide which token a registry call uses (`auth.resolve_api_key`
picks by namespace), and the todo list is where an agent leaves the next session what
still has to be done or decided, since nothing else carries it across a restart.
"""

from __future__ import annotations

from typing import Literal

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_registry import RegistryError
from mcp.types import ToolAnnotations

from just_module_creator import accountcheck, localstore
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import AccountsResult, AccountView, TodoResult, TodoView
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import client_for, describe

log = get_logger()


def _tail(value: str | None) -> str | None:
    if value is None:
        return None
    return f"…{value[-4:]}" if len(value) > 8 else "…"


def _views(state: localstore.State, target: str | None) -> list[AccountView]:
    return [
        AccountView(
            target=a.target,
            account=a.account,
            token=_tail(a.token) or "…",
            install_id=_tail(a.install_id),
            namespaces=a.namespaces,
            default=a.default,
            saved_at=a.saved_at,
            namespaces_checked_at=a.namespaces_checked_at,
            status=a.status,
            status_at=a.status_at,
            status_detail=a.status_detail,
        )
        for a in sorted(state.accounts, key=lambda a: (a.target, a.account))
        if target is None or a.target == target
    ]


def _todo_views(records: list[localstore.TodoRecord]) -> list[TodoView]:
    return [TodoView(**r.model_dump()) for r in sorted(records, key=lambda r: r.id)]


def register_memory(mcp: FastMCP, settings: Settings) -> None:
    def _whoami(target: RegistryTarget, token: str) -> dict:
        with client_for(target, settings, token=token) as client:
            return dict(client.whoami())

    def _result(success: bool, message: str, target: str | None) -> AccountsResult:
        return AccountsResult(
            success=success,
            message=message,
            accounts=_views(localstore.load(), target),
            state_file=str(localstore.state_file()),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Registry accounts saved on this machine",
            readOnlyHint=False,
            idempotentHint=False,
            destructiveHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_accounts(
        action: Literal["list", "add", "refresh", "set_default", "forget"] = "list",
        target: RegistryTarget | None = None,
        account: str | None = None,
        token: str | None = None,
        install_id: str | None = None,
    ) -> AccountsResult:
        """The registry accounts saved on this machine, each with its token and namespaces.

        Registry calls pick the saved account that owns the namespace they name, or the
        default account when they name none, and ask when nothing matches.
        `registry_register` saves a new account itself. `add` saves a token you already hold
        (omit `token` to import this instance's env token and `JMC_INSTALL_ID`), asking the
        registry for its account and namespaces; `refresh` re-checks every token, recording `valid`,
        `invalid`, `unreachable` or `timeout` with its time, and re-reads namespaces — the
        server already does this when it starts, so read `list` first. `set_default` needs
        `target` and `account`; `forget` deletes one saved account — ask the author first.
        Every change backs the file up; secrets come back shortened.
        """
        if action == "list":
            return _result(True, "Saved accounts.", target)

        if action in ("set_default", "forget"):
            if target is None or account is None:
                raise ToolError(f"`{action}` needs both `target` and `account`.")

            def _change(state: localstore.State) -> bool:
                found = [a for a in localstore.accounts_for(state, target) if a.account == account]
                if not found:
                    return False
                if action == "forget":
                    state.accounts.remove(found[0])
                else:
                    for a in localstore.accounts_for(state, target):
                        a.default = a.account == account
                return True

            changed = localstore.update(_change)
            verb = "Forgot" if action == "forget" else "Default is now"
            return _result(
                changed,
                f"{verb} {account} on {describe(target, settings)}."
                if changed
                else f"No saved account {account!r} on {describe(target, settings)}.",
                target,
            )

        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        if action == "add":
            if target is None:
                raise ToolError("`add` needs `target`: a token is valid on one instance only.")
            key = (token or "").strip() or settings.registry_token(target)
            # Importing the environment's token brings the environment's install-id with it:
            # the two were set up together, and a saved account without its install-id has
            # lost the one recovery path the store exists to keep.
            given_id = (install_id or "").strip() or (
                (settings.install_id or "").strip() or None if not (token or "").strip() else None
            )
            if not key:
                raise ToolError(
                    f"No token given and none in the environment for {describe(target, settings)}."
                )
            try:
                payload = await run_sync(lambda: _whoami(target, key))
            except RegistryError as exc:
                return _result(
                    False,
                    f"{describe(target, settings)} refused this token ({exc}); nothing was saved.",
                    target,
                )
            name = str(payload.get("account") or "")
            if not name:
                return _result(False, "The registry named no account; nothing was saved.", target)
            namespaces = [str(n) for n in payload.get("namespaces") or []]
            localstore.update(
                lambda state: localstore.save_account(
                    state,
                    target=target,
                    account=name,
                    token=key,
                    install_id=given_id,
                    namespaces=namespaces,
                )
            )
            return _result(True, f"Saved {name} on {describe(target, settings)}.", target)

        # refresh: the same check the server runs at start, on request.
        checks = await run_sync(lambda: accountcheck.validate_saved(settings, target))
        counts: dict[str, int] = {}
        for check in checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        summary = ", ".join(f"{n} {status}" for status, n in sorted(counts.items())) or "none saved"
        return _result(
            all(c.status == "valid" for c in checks),
            f"Checked {len(checks)} account(s): {summary}.",
            target,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Todo list kept on this machine",
            readOnlyHint=False,
            idempotentHint=False,
            destructiveHint=False,
            openWorldHint=False,
        ),
    )
    def todo(
        action: Literal["list", "add", "done", "reopen"] = "list",
        text: str | None = None,
        module: str | None = None,
        id: int | None = None,
        include_done: bool = False,
    ) -> TodoResult:
        """A todo list that outlives the session: what is left to do or decide, and for what.

        `add` takes `text` and optionally `module` (`namespace/name` or a spec directory);
        `done` / `reopen` take the `id`; `list` filters by `module` and shows closed records
        with `include_done`. Leave a record whenever work stops with something undone or a
        decision pending, and read the list for a module before resuming it. Nothing is
        deleted; every change backs the file up.
        """
        message = "Todo list."
        if action == "add":
            body = (text or "").strip()
            if not body:
                raise ToolError("`add` needs `text`.")
            record = localstore.update(
                lambda state: localstore.add_todo(state, body, (module or "").strip() or None)
            )
            message = f"Added #{record.id}."
        elif action in ("done", "reopen"):
            if id is None:
                raise ToolError(f"`{action}` needs `id`.")
            target_id = id

            def _close(state: localstore.State) -> bool:
                for record in state.todos:
                    if record.id == target_id:
                        record.done_at = localstore.now() if action == "done" else None
                        return True
                return False

            if not localstore.update(_close):
                raise ToolError(f"No todo #{target_id}.")
            message = f"#{target_id} {'closed' if action == 'done' else 'reopened'}."

        state = localstore.load()
        wanted = (module or "").strip() or None
        records = [
            r
            for r in state.todos
            if (wanted is None or r.module == wanted) and (include_done or r.done_at is None)
        ]
        open_count = sum(
            1 for r in state.todos if r.done_at is None and (wanted is None or r.module == wanted)
        )
        return TodoResult(
            message=message,
            todos=_todo_views(records),
            open_count=open_count,
            state_file=str(localstore.state_file()),
        )
