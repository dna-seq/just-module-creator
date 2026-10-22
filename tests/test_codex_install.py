"""Codex installs this plugin from git and starts the server itself: test that path end to end.

Gated on a `codex` binary, because nothing short of Codex resolves the manifest the way Codex
does. The test never touches the developer's real install: it gives Codex a throwaway
`CODEX_HOME` and a one-plugin marketplace whose source is this checkout as a `file://` git URL,
pinned to `HEAD`. So it installs **what is committed**, not the working tree.

Why it exists (2026-10-22): a Codex install of 0.48.0 reported "handshaking with MCP server
failed: connection closed: initialize response" on every start. It looked like a startup timeout
and was not one; Codex had resolved `startup_timeout_sec = 300` correctly. The per-version cache
held a `.venv` with packages but no interpreter and no `pyvenv.cfg`, and `uv run` refuses such a
directory without repairing it, so each start exited within milliseconds. Codex has no reinstall
control in its UI, but `codex plugin remove` / `add` is one, and a reinstall lands in an empty
cache directory, so the first start always builds the venv cold. That cold start is what these
tests drive. A single killed first start and several concurrent ones both recovered under
uv 0.12.23, so how the 19:23 venv lost its interpreter is still unexplained; the second test pins
the recovery that was measured, not the cause.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CODEX_MANIFEST = REPO / ".codex-plugin" / "plugin.json"
PLUGIN = "just-module-creator"
MARKETPLACE = "jmc-install-test"

pytestmark = pytest.mark.skipif(
    shutil.which("codex") is None or shutil.which("uv") is None,
    reason="needs the codex CLI and uv on PATH; this drives a real Codex install",
)


def _codex(codex_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["codex", *args],
        env={**os.environ, "CODEX_HOME": str(codex_home)},
        capture_output=True,
        text=True,
        timeout=300,
        check=True,
    )


def _resolved_server(codex_home: Path) -> dict:
    """The server entry exactly as Codex resolved it from the installed manifest."""
    listing = json.loads(_codex(codex_home, "mcp", "list", "--json").stdout)
    (entry,) = [s for s in listing if s["name"] == PLUGIN]
    return entry


def _launch(entry: dict) -> subprocess.Popen[str]:
    """Start the command Codex would start: its command, args, cwd and env, nothing else.

    `JMC_OFFLINE` keeps the start from re-checking saved registry tokens over the network; the
    autouse fixture has already pointed `JMC_CONFIG_FILE` at an empty per-test path.
    `VIRTUAL_ENV` is the suite's own venv under `uv run pytest`, which Codex would not pass.
    """
    transport = entry["transport"]
    inherited = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    return subprocess.Popen(
        [transport["command"], *transport["args"]],
        cwd=transport["cwd"],
        env={**inherited, **transport["env"], "JMC_OFFLINE": "1"},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class _Wire:
    """Newline-delimited JSON-RPC over a child's stdio, with a deadline on every read."""

    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self.proc = proc
        self.lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put("")

    def send(self, message: dict) -> None:
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        self.proc.stdin.flush()

    def answer(self, request_id: int, deadline: float) -> dict:
        while True:
            line = self.lines.get(timeout=max(deadline - time.monotonic(), 0.1))
            if not line:
                raise AssertionError(
                    f"the server closed stdout before answering: {self.proc.stderr.read()[-1500:]}"
                )
            message = json.loads(line)
            if message.get("id") == request_id:
                return message


def _handshake(entry: dict) -> tuple[float, set[str]]:
    """Initialize and list tools inside Codex's own startup budget; return (seconds, names)."""
    proc = _launch(entry)
    started = time.monotonic()
    deadline = started + entry["startup_timeout_sec"]
    try:
        wire = _Wire(proc)
        wire.send({"id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "codex-install-test", "version": "0"},
        }})
        initialized = wire.answer(1, deadline)
        assert "result" in initialized, initialized
        elapsed = time.monotonic() - started
        wire.send({"method": "notifications/initialized"})
        wire.send({"id": 2, "method": "tools/list"})
        tools = wire.answer(2, deadline)["result"]["tools"]
        return elapsed, {tool["name"] for tool in tools}
    finally:
        proc.kill()
        proc.wait()


@pytest.fixture
def codex_home(tmp_path: Path) -> Path:
    """A throwaway Codex home with this checkout's `HEAD` as a one-plugin marketplace."""
    head = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    marketplace = tmp_path / "marketplace"
    (marketplace / ".agents" / "plugins").mkdir(parents=True)
    (marketplace / ".agents" / "plugins" / "marketplace.json").write_text(json.dumps({
        "name": MARKETPLACE,
        "plugins": [{
            "name": PLUGIN,
            "source": {"source": "url", "url": REPO.as_uri(), "ref": head},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Research",
        }],
    }))
    home = tmp_path / "codex-home"
    home.mkdir()
    _codex(home, "plugin", "marketplace", "add", str(marketplace))
    _codex(home, "plugin", "add", f"{PLUGIN}@{MARKETPLACE}")
    return home


def _install_root(entry: dict) -> Path:
    return Path(entry["transport"]["cwd"]).resolve()


def test_a_reinstall_starts_cold_and_answers_inside_codexs_budget(codex_home: Path):
    """Remove and re-add, then start the server exactly as Codex would.

    The reinstall must leave no venv behind (otherwise this would not be a cold start), and
    Codex must have read our timeouts rather than its defaults: the two are compared as
    independent producers, the manifest JSON against Codex's parse of it.
    """
    _codex(codex_home, "plugin", "remove", f"{PLUGIN}@{MARKETPLACE}")
    _codex(codex_home, "plugin", "add", f"{PLUGIN}@{MARKETPLACE}")
    entry = _resolved_server(codex_home)
    root = _install_root(entry)

    assert (root / ".codex-plugin" / "plugin.json").is_file()
    assert not (root / ".venv").exists(), "a reinstall reused a venv; the start below is not cold"

    declared = json.loads(CODEX_MANIFEST.read_text())["mcpServers"][PLUGIN]
    assert entry["startup_timeout_sec"] == declared["startup_timeout_sec"]
    assert entry["tool_timeout_sec"] == declared["tool_timeout_sec"]

    elapsed, names = _handshake(entry)
    assert elapsed < entry["startup_timeout_sec"]
    assert "describe_table" in names
    assert len(names) >= 20, sorted(names)


def test_a_killed_first_start_does_not_poison_the_next(codex_home: Path):
    """Codex ends a session's servers when the session ends, even mid-`uv sync`.

    A one-shot `codex exec` finished in 13 s while the first start was still building the venv,
    and listed none of our tools. So the first start is killed partway through the build, then the
    next start has to come up anyway.
    """
    entry = _resolved_server(codex_home)
    root = _install_root(entry)
    assert not (root / ".venv").exists()

    first = _launch(entry)
    deadline = time.monotonic() + 60
    while not (root / ".venv" / "lib").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert (root / ".venv" / "lib").exists(), "the first start never began building a venv"
    first.send_signal(signal.SIGKILL)
    first.wait()

    _, names = _handshake(entry)
    assert "describe_table" in names
