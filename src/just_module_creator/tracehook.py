"""The provenance ledger's host hook (RM31, `docs/DESIGN-traceability.md` §11).

Claude Code and Codex run this after (and, for edits, before) a tool call. It records what an
authoring session was shown and what it changed, into the module's `logs/trace/` ledger, one JSON
Lines file per session. That ledger publishes with the module, so it holds metadata only: queries,
the identifiers that came back, the hash and length of each article text, and the hash of each table
row written. Never article text, never a path, never the conversation.

**Stdlib only, on purpose.** It runs on every matched call, started by
`uv run --no-project python -I`, which costs about 20 ms where importing the compiler costs about
450. So it knows no schema: a row is the sha256 of its cell values, and a quote's anchor is found
by looking for any long cell verbatim in the texts fetched this session. Which column held it, and
which columns are a row's key, the join decides later with the compiler in hand.

**Fails open.** A hook that raises must not break the host's tool call, so `main` reports to stderr
and exits 0 whatever happens. A ledger that missed an event is caught by the join, which reports the
row as not traceable; a broken edit is not recoverable.

Events wait in a per-session buffer outside the module until the session edits a table in a
module directory, then go to that module's ledger. A session that never edits a module leaves no
ledger. The buffer is deleted when the session ends. `JMC_TRACE=0` turns all of this off.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LEDGER_VERSION = 1

#: Our tools whose results the ledger records, by the name after the server prefix. Each host
#: spells the prefix its own way (Claude Code: `mcp__plugin_just-module-creator_<server>__`), so
#: a name is matched on its suffix and on carrying the server's name.
SEARCH_TOOLS = frozenset({"literature_search"})
FETCH_TOOLS = frozenset({"fetch_fulltext"})
LOOKUP_TOOLS = frozenset({"lookup_variant"})
RECORDED_TOOLS = SEARCH_TOOLS | FETCH_TOOLS | LOOKUP_TOOLS

#: The hosts' file-writing tools. Codex reports a patch as `apply_patch`, paths inside the patch.
EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "apply_patch"})

#: The file that makes a directory a module.
SPEC_FILE = "module_spec.yaml"

#: A cell this long found verbatim in a fetched text is anchored to it. Short cells (an rsID, a
#: genotype) occur everywhere and would anchor to nothing in particular.
ANCHOR_MIN_CHARS = 40

#: A buffer older than this is a session that ended without its end hook (a crash); swept at start.
STALE_SECONDS = 2 * 24 * 3600

_SERVER = re.compile(r"^mcp__.*just[-_]module[-_]creator.*__(?P<tool>[a-z_]+)$")
_PATCH_PATH = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File: (?P<path>.+)$|^\*\*\* Move to: (?P<to>.+)$"
)


def trace_root(env: dict[str, str]) -> Path:
    """Where session buffers live: `JMC_TRACE_DIR`, else the user's cache. Never a spec dir."""
    if env.get("JMC_TRACE_DIR"):
        return Path(env["JMC_TRACE_DIR"])
    base = Path(env["XDG_CACHE_HOME"]) if env.get("XDG_CACHE_HOME") else Path.home() / ".cache"
    return base / "just-module-creator" / "trace"


def enabled(env: dict[str, str]) -> bool:
    return env.get("JMC_TRACE", "").strip().lower() not in {"0", "false", "no", "off"}


def our_tool(name: str) -> str | None:
    """The bare tool name if `name` is one of ours, else None."""
    match = _SERVER.match(name or "")
    return match.group("tool") if match else None


def row_sha256(row: dict[str, str]) -> str:
    """The identity of one authored row: its non-empty cells, keyed by header, nothing else.

    The join hashes the module's current rows the same way, so a row a recorded edit wrote is found
    again by value, whatever its key columns are and wherever it moved in the file. Empty cells are
    left out so that adding a column, empty on every old row, does not claim to rewrite them all.
    """
    cells = {k: v for k, v in row.items() if k is not None and v not in (None, "")}
    canonical = json.dumps(cells, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_rows(text: str) -> list[dict[str, str]]:
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


#: Claude Code's notice when a result is over its inline limit: the JSON is in a file it names
#: (measured 2026-11-17 on a 73,785-character article). The path is read, never recorded.
_SPILLED = re.compile(r"Output has been saved to (?P<path>\S+?\.txt)\.?(?:\s|$)")


def _result(response: Any) -> dict[str, Any] | None:
    """The tool's own JSON result, from whichever wrapping the host handed over.

    Claude Code passes an MCP result as the JSON string (measured 2026-11-17), and one over its
    inline limit as a notice naming the file it saved the JSON to. Codex passes "the MCP call
    result", which carries the text in `content` or the object in `structuredContent`.
    """
    if isinstance(response, str):
        spilled = _SPILLED.search(response)
        if spilled and not response.lstrip().startswith("{"):
            response = Path(spilled.group("path")).read_text("utf-8")
        loaded = json.loads(response)
        return loaded if isinstance(loaded, dict) else None
    if not isinstance(response, dict):
        return None
    if isinstance(response.get("structuredContent"), dict):
        return response["structuredContent"]
    content = response.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return _result(item.get("text"))
    return response


class Session:
    """One session's buffer: pending events, fetched texts by hash, and pre-edit copies."""

    def __init__(self, root: Path, session_id: str) -> None:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "unknown")
        self.id = safe
        self.dir = root / safe
        self.texts = self.dir / "texts"
        self.before = self.dir / "before"
        self.pending = self.dir / "pending.jsonl"

    def ensure(self) -> None:
        self.texts.mkdir(parents=True, exist_ok=True)
        self.before.mkdir(parents=True, exist_ok=True)

    def queue(self, event: dict[str, Any]) -> None:
        self.ensure()
        with self.pending.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def take_pending(self) -> list[dict[str, Any]]:
        if not self.pending.exists():
            return []
        events = [json.loads(line) for line in self.pending.read_text("utf-8").splitlines() if line]
        self.pending.unlink()
        return events

    def keep_text(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.ensure()
        target = self.texts / f"{digest}.txt"
        if not target.exists():
            target.write_text(text, encoding="utf-8")
        return digest

    def known_texts(self) -> dict[str, str]:
        if not self.texts.exists():
            return {}
        return {p.stem: p.read_text("utf-8") for p in sorted(self.texts.glob("*.txt"))}

    def before_path(self, file: Path) -> Path:
        return self.before / (hashlib.sha256(str(file).encode("utf-8")).hexdigest() + ".csv")


def module_dir(file: Path) -> Path | None:
    """The module a written file belongs to: a top-level CSV beside a `module_spec.yaml`."""
    if file.suffix.lower() != ".csv":
        return None
    return file.parent if (file.parent / SPEC_FILE).is_file() else None


def edited_files(tool: str, tool_input: dict[str, Any], cwd: str) -> list[Path]:
    """The files an edit tool writes, resolved against the session's directory."""
    if tool == "apply_patch":
        command = tool_input.get("command") or tool_input.get("input") or ""
        if isinstance(command, list):
            command = "\n".join(str(part) for part in command)
        paths: list[str] = []
        for line in str(command).splitlines():
            match = _PATCH_PATH.match(line.strip())
            if match:
                paths.append(match.group("path") or match.group("to") or "")
    else:
        paths = [str(tool_input["file_path"])] if tool_input.get("file_path") else []
    paths = [p for p in paths if p]
    base = Path(cwd) if cwd else Path.cwd()
    return [(base / p).resolve() if not Path(p).is_absolute() else Path(p) for p in paths]


def ledger_path(module: Path, session: Session) -> Path:
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    return module / "logs" / "trace" / f"{day}-{session.id[:8]}.jsonl"


def append(ledger: Path, events: list[dict[str, Any]]) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def anchors(row: dict[str, str], texts: dict[str, str]) -> list[dict[str, Any]]:
    """Where each long cell of `row` sits verbatim in a text this session fetched."""
    found = []
    for column, value in row.items():
        cell = (value or "").strip()
        if len(cell) < ANCHOR_MIN_CHARS:
            continue
        for digest, text in texts.items():
            offset = text.find(cell)
            if offset >= 0:
                found.append(
                    {"column": column, "sha256": digest, "offset": offset, "len": len(cell)}
                )
    return found


def record_tool(session: Session, tool: str, tool_input: dict[str, Any], response: Any) -> None:
    """Queue a search, fetch or lookup. Nothing reaches a ledger until a module is edited."""
    event: dict[str, Any] = {"v": LEDGER_VERSION, "t": _now(), "via": tool}
    # A call whose result cannot be read is still a call that happened: recorded with what was
    # asked and `result: null`, so the join sees an unknown rather than nothing at all.
    try:
        result = _result(response)
    except (OSError, ValueError) as exc:
        result, why = None, type(exc).__name__
    else:
        why = "not an object" if result is None else None
    if result is None:
        kind = "search" if tool in SEARCH_TOOLS else "fetch" if tool in FETCH_TOOLS else "lookup"
        asked = {k: v for k, v in tool_input.items() if v not in (None, "", [])}
        session.queue({**event, "kind": kind, "asked": asked, "result": None, "why": why})
        return
    if tool in SEARCH_TOOLS:
        papers = result.get("papers") or []
        event |= {
            "kind": "search",
            "query": result.get("query"),
            "asked": {k: v for k, v in tool_input.items() if v not in (None, "", [])},
            "returned": [p.get("pmid") or p.get("doi") or p.get("arxiv_id") for p in papers],
            "sources": [
                {"source": s.get("source"), "results": s.get("results")}
                for s in result.get("sources") or []
            ],
        }
    elif tool in FETCH_TOOLS:
        text = result.get("text")
        event |= {
            "kind": "fetch",
            "pmid": result.get("pmid"),
            "pmcid": result.get("pmcid"),
            "doi": result.get("doi"),
            "retrieved": result.get("retrieved"),
            "text_source": result.get("text_source"),
            "truncated": result.get("truncated"),
            "sha256": session.keep_text(text) if isinstance(text, str) and text else None,
            "chars": len(text) if isinstance(text, str) else None,
        }
    else:
        event |= {
            "kind": "lookup",
            "asked": {k: v for k, v in tool_input.items() if v not in (None, "", [])},
            "rsid_state": result.get("rsid_state"),
            "loci": result.get("loci"),
        }
    session.queue(event)


def snapshot(session: Session, files: list[Path]) -> None:
    """Before an edit: keep each module table as it stands, to diff the after against."""
    for file in files:
        if module_dir(file) is None:
            continue
        session.ensure()
        target = session.before_path(file)
        if file.exists():
            shutil.copyfile(file, target)
        else:
            target.write_text("", encoding="utf-8")


def record_edit(session: Session, tool: str, files: list[Path]) -> None:
    """After an edit: flush pending events to the module's ledger, then record rows written."""
    for file in files:
        module = module_dir(file)
        if module is None:
            continue
        before_copy = session.before_path(file)
        after_rows = read_rows(file.read_text("utf-8")) if file.exists() else []
        event: dict[str, Any] = {
            "v": LEDGER_VERSION,
            "t": _now(),
            "kind": "edit",
            "via": tool,
            "file": file.name,
        }
        if before_copy.exists():
            before_rows = read_rows(before_copy.read_text("utf-8"))
            before_copy.unlink()
            old = {row_sha256(r) for r in before_rows}
            new = {row_sha256(r): r for r in after_rows}
            texts = session.known_texts()
            event["added"] = [
                {"row_sha256": digest, "anchors": anchors(row, texts)}
                for digest, row in new.items()
                if digest not in old
            ]
            event["removed"] = sorted(old - set(new))
        else:
            # No pre-edit copy (the pre hook did not run): which rows changed is unknown, not "all".
            event["baseline"] = None
        append(ledger_path(module, session), [*session.take_pending(), event])


def sweep(root: Path, keep: str) -> None:
    """Remove buffers of sessions that ended without their end hook."""
    if not root.is_dir():
        return
    cutoff = time.time() - STALE_SECONDS
    for child in root.iterdir():
        if child.is_dir() and child.name != keep and child.stat().st_mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)


def handle(phase: str, payload: dict[str, Any], env: dict[str, str]) -> None:
    if not enabled(env):
        return
    root = trace_root(env)
    session = Session(root, str(payload.get("session_id") or ""))
    if phase == "end":
        shutil.rmtree(session.dir, ignore_errors=True)
        return
    name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    if name in EDIT_TOOLS:
        files = edited_files(name, tool_input, str(payload.get("cwd") or ""))
        if phase == "pre":
            sweep(root, session.id)
            snapshot(session, files)
        else:
            record_edit(session, name, files)
        return
    tool = our_tool(name)
    if phase == "post" and tool in RECORDED_TOOLS:
        record_tool(session, tool, tool_input, payload.get("tool_response"))


def main(argv: list[str]) -> int:
    phase = argv[1] if len(argv) > 1 else "post"
    try:
        handle(phase, json.loads(sys.stdin.read() or "{}"), dict(os.environ))
    except Exception as exc:  # noqa: BLE001 — a hook that raises would break the host's tool call
        print(
            f"just-module-creator trace hook ({phase}): {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
