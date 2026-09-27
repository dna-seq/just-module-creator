"""This machine's memory: saved registry accounts, the todo list, and the backups behind both.

Every test runs against the per-test config directory the autouse fixture sets, so nothing
here can touch the developer's real `state.json`. The network is stubbed at `client_for`,
the one construction point for a registry client.
"""

from __future__ import annotations

import httpx
import pytest
from conftest import offline_settings
from just_dna_registry import RegistryError

from just_module_creator import accountcheck, auth, localstore, userconfig
from just_module_creator.settings import Settings
from just_module_creator.tools import registry as registry_tools


def _online() -> Settings:
    return Settings(offline=False, _env_file=None)  # type: ignore[call-arg]


def _seed(*accounts: tuple[str, str, str, list[str]]) -> None:
    def _add(state: localstore.State) -> None:
        for target, account, token, namespaces in accounts:
            localstore.save_account(
                state,
                target=target,
                account=account,
                token=token,
                install_id=f"install-{account}",
                namespaces=namespaces,
            )

    localstore.update(_add)


class _Ctx:
    """The one piece of `Context` the resolver reads: a session with nothing stored."""

    async def get_state(self, key: str) -> None:
        return None


# --- backups ----------------------------------------------------------------------------


def test_every_write_is_preceded_by_a_verified_copy_of_what_it_replaces():
    _seed(("test", "sheep", "mk_first_aaaa", ["test-sheep"]))
    before = localstore.state_file().read_bytes()
    _seed(("test", "goat", "mk_second_bbbb", ["test-goat"]))

    copies = sorted((localstore.state_file().parent / userconfig.BACKUP_DIR).glob("state.json.*"))
    assert copies, "no backup was taken"
    assert copies[-1].read_bytes() == before
    assert copies[-1].stat().st_mode & 0o077 == 0


def test_backups_are_kept_to_the_newest_fifty():
    for n in range(userconfig.KEEP_BACKUPS + 6):
        localstore.update(lambda state, n=n: localstore.add_todo(state, f"item {n}", None))
    folder = localstore.state_file().parent / userconfig.BACKUP_DIR
    copies = sorted(folder.glob("state.json.*"))
    assert len(copies) == userconfig.KEEP_BACKUPS
    newest = localstore.State.model_validate_json(copies[-1].read_text())
    assert [t.text for t in newest.todos][-1] == f"item {userconfig.KEEP_BACKUPS + 4}"


def test_a_settings_write_is_backed_up_too():
    userconfig.remember("JMC_USER_EMAIL", "first@example.org", replace=False)
    userconfig.remember("JMC_USER_EMAIL", "second@example.org", replace=True)
    folder = userconfig.config_file().parent / userconfig.BACKUP_DIR
    kept = [p.read_text() for p in folder.glob(".env.*")]
    assert any("first@example.org" in text for text in kept)


# --- choosing a token -------------------------------------------------------------------


def test_a_namespace_picks_the_account_that_owns_it():
    _seed(
        ("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]),
        ("test", "goat", "mk_goat_bbbb", ["test-goat", "test-herd"]),
        ("prod", "goat", "mk_prod_cccc", ["goat"]),
    )
    state = localstore.load()
    assert localstore.pick_token(state, "test", "test-herd") == "mk_goat_bbbb"
    assert localstore.pick_token(state, "test", "test-sheep") == "mk_sheep_aaaa"
    assert localstore.pick_token(state, "test", None) == "mk_sheep_aaaa", "first saved is default"
    assert localstore.pick_token(state, "test", "goat") is None, "never crosses instances"
    assert localstore.pick_token(state, "test", "test-nobody") is None


def test_a_refused_token_is_never_picked_and_an_unanswered_one_still_is():
    _seed(("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]))

    def _mark(status: str):
        def _set(state: localstore.State) -> None:
            state.accounts[0].status = status

        return _set

    localstore.update(_mark("timeout"))
    assert localstore.pick_token(localstore.load(), "test", "test-sheep") == "mk_sheep_aaaa"
    localstore.update(_mark("invalid"))
    assert localstore.pick_token(localstore.load(), "test", "test-sheep") is None


async def test_the_resolver_asks_rather_than_guessing_when_no_saved_account_matches():
    _seed(
        ("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]),
        ("test", "goat", "mk_goat_bbbb", ["test-goat"]),
    )
    settings = offline_settings()
    assert await auth.resolve_api_key(_Ctx(), settings, "test", "test-goat") == "mk_goat_bbbb"  # type: ignore[arg-type]
    assert await auth.resolve_api_key(_Ctx(), settings, "test", "test-elsewhere") is None  # type: ignore[arg-type]

    refusal = auth.unauthenticated_result(settings, "test", "test-elsewhere")
    assert not refusal.success
    assert refusal.data and refusal.data["needs"] == "choose_account"
    assert "sheep" in refusal.message and "goat" in refusal.message
    assert "mk_sheep_aaaa" not in refusal.message, "the listing names accounts, never tokens"


# --- saving what the registry hands back --------------------------------------------------


class _RegistryStub:
    def __init__(self, **replies) -> None:
        self.replies = replies
        self.tokens: list[str | None] = []

    def __call__(self, target, settings, *, token=None, timeout=None):
        self.tokens.append(token)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def register(self, install_id, account):
        return self.replies["register"]

    def claim_namespace(self, namespace, **kwargs):
        return {"namespace": namespace}

    def whoami(self):
        reply = self.replies["whoami"]
        if isinstance(reply, BaseException):
            raise reply
        return reply


async def test_registering_saves_the_account_its_install_id_and_namespaces(
    make_client, monkeypatch
):
    stub = _RegistryStub(
        register={"token": "mk_minted_9999", "account": "sheep", "namespaces": ["test-sheep"]}
    )
    monkeypatch.setattr(auth, "client_for", stub)
    async with make_client(settings=_online()) as client:
        result = await client.call_tool(
            "registry_register",
            {"account": "sheep", "target": "test", "install_id": "a1b2c3d4e5f6"},
        )

    saved = localstore.load().accounts
    assert [(a.account, a.token, a.install_id, a.namespaces) for a in saved] == [
        ("sheep", "mk_minted_9999", "a1b2c3d4e5f6", ["test-sheep"])
    ]
    assert saved[0].default and saved[0].status == "valid"
    assert "Saved on this machine" in str(result.structured_content)


async def test_a_later_register_reuses_the_saved_install_id():
    _seed(("prod", "sheep", "mk_prod_aaaa", ["sheep"]))
    resolved, origin = auth.resolve_install_id(None, offline_settings())
    assert (resolved, origin) == ("install-sheep", "saved account")


async def test_a_claimed_namespace_is_recorded_on_the_account_that_claimed_it(
    make_client, monkeypatch
):
    _seed(("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]))
    stub = _RegistryStub()
    monkeypatch.setattr(registry_tools, "client_for", stub)
    async with make_client(settings=_online()) as client:
        await client.call_tool(
            "registry_claim_namespace", {"namespace": "test-flock", "target": "test"}
        )

    assert stub.tokens == ["mk_sheep_aaaa"], "the default account made the claim"
    assert localstore.load().accounts[0].namespaces == ["test-flock", "test-sheep"]
    assert localstore.pick_token(localstore.load(), "test", "test-flock") == "mk_sheep_aaaa"


# --- the check at start ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("reply", "status"),
    [
        ({"account": "sheep", "namespaces": ["test-sheep", "test-new"]}, "valid"),
        (RegistryError(401, "unknown key"), "invalid"),
        (RegistryError(503, "maintenance"), "unreachable"),
        (httpx.ReadTimeout("slow"), "timeout"),
        (httpx.ConnectError("refused"), "unreachable"),
    ],
)
def test_each_saved_token_is_recorded_as_what_the_registry_answered(monkeypatch, reply, status):
    _seed(("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]))
    monkeypatch.setattr(accountcheck, "client_for", _RegistryStub(whoami=reply))

    checks = accountcheck.validate_saved(_online())

    assert [c.status for c in checks] == [status]
    saved = localstore.load().accounts[0]
    assert saved.status == status and saved.status_at is not None
    assert saved.namespaces == (
        ["test-new", "test-sheep"] if status == "valid" else ["test-sheep"]
    ), "only an answer from the registry moves the namespaces"


def test_nothing_is_checked_offline_or_with_nothing_saved():
    assert accountcheck.start_background_validation(_online()) is None
    _seed(("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]))
    assert accountcheck.start_background_validation(offline_settings()) is None


# --- the tools --------------------------------------------------------------------------


async def test_accounts_are_listed_shortened_and_the_default_can_move(make_client):
    _seed(
        ("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]),
        ("test", "goat", "mk_goat_bbbb", ["test-goat"]),
    )
    async with make_client(settings=offline_settings()) as client:
        listed = await client.call_tool("registry_accounts", {})
        moved = await client.call_tool(
            "registry_accounts", {"action": "set_default", "target": "test", "account": "goat"}
        )

    assert "mk_sheep_aaaa" not in str(listed.structured_content)
    defaults = {a["account"]: a["default"] for a in moved.structured_content["accounts"]}
    assert defaults == {"goat": True, "sheep": False}


async def test_forgetting_an_account_leaves_it_in_the_backup(make_client):
    _seed(("test", "sheep", "mk_sheep_aaaa", ["test-sheep"]))
    async with make_client(settings=offline_settings()) as client:
        await client.call_tool(
            "registry_accounts", {"action": "forget", "target": "test", "account": "sheep"}
        )
    assert localstore.load().accounts == []
    folder = localstore.state_file().parent / userconfig.BACKUP_DIR
    assert any("mk_sheep_aaaa" in p.read_text() for p in folder.glob("state.json.*"))


async def test_todos_carry_a_module_close_and_stay(make_client):
    async with make_client(settings=offline_settings()) as client:
        await client.call_tool("todo", {"action": "add", "text": "register on prod"})
        first = await client.call_tool(
            "todo",
            {"action": "add", "text": "decide the rs4988235 weight", "module": "eric-mods/lct"},
        )
        await client.call_tool(
            "todo", {"action": "add", "text": "read PMID 11788828", "module": "eric-mods/lct"}
        )
        record_id = first.structured_content["todos"][0]["id"]
        await client.call_tool("todo", {"action": "done", "id": record_id})
        open_for_module = await client.call_tool("todo", {"module": "eric-mods/lct"})
        everything = await client.call_tool("todo", {"include_done": True})

    texts = [t["text"] for t in open_for_module.structured_content["todos"]]
    assert texts == ["read PMID 11788828"]
    assert open_for_module.structured_content["open_count"] == 1
    assert len(everything.structured_content["todos"]) == 3, "a closed record is kept"
