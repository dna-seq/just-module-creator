"""The configuration an author gives once has to be there the next time, on every host.

The defect this pins: the skills said "save it in `.env`", the agent wrote the project's,
and a server started anywhere else (Codex starts it in the plugin's own per-version copy)
never read it. So these tests start the loader from a directory that is not the project,
and write through the one file that survives: the user config file.
"""

from __future__ import annotations

import os
import stat

import pytest
from conftest import offline_settings
from dotenv.main import load_dotenv as _real_load_dotenv

from just_module_creator import userconfig


@pytest.fixture
def live_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    """The suite neutralizes every `load_dotenv`; these tests are about the real one.

    Bound at import, which is before the autouse fixture swaps every module's binding.
    """
    monkeypatch.setattr(userconfig, "load_dotenv", _real_load_dotenv)


def _write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_the_user_file_is_read_from_a_directory_that_is_not_the_project(
    live_loader, monkeypatch, tmp_path
):
    """A server started outside any project still finds what the author saved."""
    elsewhere = tmp_path / "plugin-copy" / "0.45.0"
    elsewhere.mkdir(parents=True)
    monkeypatch.chdir(elsewhere)
    _write(userconfig.config_file(), "JMC_USER_EMAIL=author@example.org\n")
    monkeypatch.delenv("JMC_USER_EMAIL", raising=False)

    userconfig.load_env()

    assert os.environ["JMC_USER_EMAIL"] == "author@example.org"
    assert (userconfig.origin("JMC_USER_EMAIL") or "").startswith("user config")


def test_the_project_file_is_found_from_the_working_directory_and_outranks_the_user_file(
    live_loader, monkeypatch, tmp_path
):
    """Walked up from the cwd, never from this package's own location."""
    project = tmp_path / "project"
    _write(project / ".env", "JMC_USER_EMAIL=project@example.org\n")
    (project / "modules" / "lct").mkdir(parents=True)
    monkeypatch.chdir(project / "modules" / "lct")
    _write(userconfig.config_file(), "JMC_USER_EMAIL=user@example.org\nJMC_INSTALL_ID=abc\n")
    for var in ("JMC_USER_EMAIL", "JMC_INSTALL_ID"):
        monkeypatch.delenv(var, raising=False)

    userconfig.load_env()

    assert os.environ["JMC_USER_EMAIL"] == "project@example.org"
    assert (userconfig.origin("JMC_USER_EMAIL") or "").startswith("project .env")
    assert os.environ["JMC_INSTALL_ID"] == "abc", "a name the project lacks still arrives"


def test_the_shell_outranks_both(live_loader, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _write(userconfig.config_file(), "JMC_USER_EMAIL=user@example.org\n")
    monkeypatch.setenv("JMC_USER_EMAIL", "shell@example.org")

    userconfig.load_env()

    assert os.environ["JMC_USER_EMAIL"] == "shell@example.org"
    assert userconfig.origin("JMC_USER_EMAIL") == "environment"


def test_remember_keeps_a_different_saved_value_unless_told_to_replace(monkeypatch):
    monkeypatch.delenv("JMC_TEST_API_KEY", raising=False)
    first = userconfig.remember("JMC_TEST_API_KEY", "mk_first_token", replace=False)
    kept = userconfig.remember("JMC_TEST_API_KEY", "mk_second_token", replace=False)
    assert first.written and not kept.written
    assert kept.previous == "mk_first_token"
    assert userconfig.saved("JMC_TEST_API_KEY") == "mk_first_token"

    replaced = userconfig.remember("JMC_TEST_API_KEY", "mk_second_token", replace=True)
    assert replaced.written and replaced.in_force
    assert userconfig.saved("JMC_TEST_API_KEY") == "mk_second_token"
    assert os.environ["JMC_TEST_API_KEY"] == "mk_second_token"


def test_the_file_holding_tokens_is_owner_only():
    """Including a file that already existed with looser permissions."""
    _write(userconfig.config_file(), "JMC_USER_EMAIL=author@example.org\n")
    userconfig.config_file().chmod(0o664)
    userconfig.remember("JMC_INSTALL_ID", "0000abcd", replace=False)
    mode = stat.S_IMODE(userconfig.config_file().stat().st_mode)
    assert mode & (stat.S_IRWXG | stat.S_IRWXO) == 0, oct(mode)


def test_only_a_setting_this_server_reads_can_be_saved():
    assert "JMC_USER_EMAIL" in userconfig.SAVABLE
    assert "NCBI_API_KEY" in userconfig.SAVABLE
    with pytest.raises(KeyError):
        userconfig.remember("PATH", "/tmp/evil", replace=False)
    assert not userconfig.config_file().exists()


async def test_a_saved_token_and_email_reach_this_session_without_a_restart(make_client):
    settings = offline_settings()
    async with make_client(settings=settings) as client:
        before = await client.call_tool("remember_setting", {"name": "JMC_TEST_API_KEY"})
        assert before.structured_content["in_force"] is None
        await client.call_tool(
            "remember_setting", {"name": "JMC_TEST_API_KEY", "value": "mk_live_polygon_1234"}
        )
        email = await client.call_tool(
            "remember_setting", {"name": "JMC_USER_EMAIL", "value": "author@example.org"}
        )

    assert settings.registry_token("test") == "mk_live_polygon_1234"
    assert settings.user_email == "author@example.org"
    payload = email.structured_content
    assert payload["written"] is True
    assert payload["config_file"] == str(userconfig.config_file())
    assert "author@example.org" in userconfig.config_file().read_text()


async def test_a_secret_is_never_echoed_whole(make_client):
    async with make_client(settings=offline_settings()) as client:
        result = await client.call_tool(
            "remember_setting", {"name": "JMC_TEST_API_KEY", "value": "mk_live_polygon_1234"}
        )
    text = str(result.structured_content)
    assert "…1234" in text
    assert "mk_live_polygon_1234" not in text


async def test_a_yes_no_answer_is_checked_before_it_is_saved(make_client):
    async with make_client(settings=offline_settings()) as client:
        result = await client.call_tool(
            "remember_setting",
            {"name": "JMC_CACHE_PREWARM", "value": "maybe"},
            raise_on_error=False,
        )
    assert result.is_error
    assert not userconfig.config_file().exists()


def test_nothing_tells_an_agent_to_persist_into_a_dotenv_file():
    """The instruction that lost the email under Codex, in any skill or in the server source."""
    import re
    from pathlib import Path

    root = Path(__file__).parent.parent
    files = [*root.glob("skills/**/*.md"), *root.glob("src/just_module_creator/**/*.py")]
    assert len(files) > 40, "the sweep found nothing to read"
    assert any("remember_setting" in f.read_text() for f in files), "haystack not established"
    persist = re.compile(
        r"\b(save|write|put|record|store)\w*\b[^.\n]{0,40}\bin(to)? `?\.env\b", re.I
    )
    offenders = [
        f"{f.relative_to(root)}: {m.group(0)}"
        for f in files
        for m in persist.finditer(f.read_text())
    ]
    assert not offenders, offenders
