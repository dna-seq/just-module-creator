"""The provenance ledger's host hook (RM31, `docs/DESIGN-traceability.md` §11).

Each case drives the hook the way a host does: one JSON payload per call, the shape measured from
a real Claude Code session on 2026-11-17 (an MCP result arrives as its JSON string; `Write` and
`Edit` carry their content), or documented for Codex (`apply_patch` with the patch in `command`).
The module is a copy of `assets/fto_bmi`, and the article text is a real passage of PMC10445758.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from just_module_creator import tracehook

ROOT = Path(__file__).parent.parent
FTO = ROOT / "assets" / "fto_bmi"
CLAUDE = "mcp__plugin_just-module-creator_just-module-creator__"

#: Verbatim from PMC10445758 (PMID 37621650), as fetched on 2026-11-16.
QUOTE = (
    "The present meta-analysis demonstrates that the C allele of the rs17782313 polymorphism near "
    "MC4R is associated with a higher level of BMI, WC or GLU, but not with blood lipids"
)
ARTICLE = f"Discussion {QUOTE}, which is in agreement with the previous findings. Methods follow."


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    return {"JMC_TRACE_DIR": str(tmp_path / "buffer")}


@pytest.fixture
def module(tmp_path: Path) -> Path:
    target = tmp_path / "work" / "fto_bmi"
    shutil.copytree(FTO, target)
    return target


def call(phase: str, env: dict[str, str], **payload) -> None:
    tracehook.handle(phase, {"session_id": "s-1234567890", "cwd": "/somewhere", **payload}, env)


def fetch(env: dict[str, str], text: str = ARTICLE) -> None:
    result = {
        "pmid": "37621650",
        "pmcid": "PMC10445758",
        "retrieved": True,
        "text": text,
        "text_source": "fulltext",
        "truncated": False,
    }
    call(
        "post",
        env,
        tool_name=f"{CLAUDE}fetch_fulltext",
        tool_input={"pmid": "37621650"},
        tool_response=json.dumps(result),
    )


def search(env: dict[str, str]) -> None:
    result = {
        "query": "(rs17782313) AND (body mass index)",
        "papers": [{"pmid": "38674326"}, {"pmid": "37621650"}],
        "sources": [{"source": "pubmed", "queried": True, "results": 2}],
    }
    call(
        "post",
        env,
        tool_name=f"{CLAUDE}literature_search",
        tool_input={"rsid": "rs17782313", "trait": "body mass index", "gene": None},
        tool_response=json.dumps(result),
    )


def add_study_row(module: Path, env: dict[str, str], quote: str = QUOTE) -> None:
    """Append one studies.csv row through a `Write`, with the pre and post hooks around it."""
    studies = module / "studies.csv"
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(studies)}}
    call("pre", env, **payload)
    rows = tracehook.read_rows(studies.read_text("utf-8"))
    header = list(rows[0]) + ["provenance_quote"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    writer.writerow(
        {
            "rsid": "rs17782313",
            "pmid": "37621650",
            "study_design": "meta-analysis",
            "conclusion": "Higher BMI.",
            "provenance_quote": quote,
        }
    )
    studies.write_text(out.getvalue(), encoding="utf-8")
    call("post", env, **payload)


def ledger(module: Path) -> list[dict]:
    files = sorted((module / "logs" / "trace").glob("*.jsonl"))
    assert len(files) == 1, files
    return [json.loads(line) for line in files[0].read_text("utf-8").splitlines()]


def test_a_session_that_edits_a_module_gets_its_chain_in_order(module, env) -> None:
    search(env)
    fetch(env)
    add_study_row(module, env)

    events = ledger(module)
    assert [e["kind"] for e in events] == ["search", "fetch", "edit"]
    assert events[0]["returned"] == ["38674326", "37621650"]
    assert events[0]["asked"] == {"rsid": "rs17782313", "trait": "body mass index"}
    sha = events[1]["sha256"]
    assert events[1]["chars"] == len(ARTICLE) and sha
    (added,) = events[2]["added"]
    assert events[2]["removed"] == []
    # The quote is anchored where it sits, in the text this session fetched; short cells are not.
    assert added["anchors"] == [
        {
            "column": "provenance_quote",
            "sha256": sha,
            "offset": ARTICLE.index(QUOTE),
            "len": len(QUOTE),
        }
    ]
    # The row is identified by value, so the join can find it again whatever its key columns are.
    current = tracehook.read_rows((module / "studies.csv").read_text("utf-8"))
    assert added["row_sha256"] == tracehook.row_sha256(current[-1])
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", e["t"]) for e in events)


def test_adding_a_column_rewrites_no_row(module, env) -> None:
    """A new column is empty on every old row, so no old row reads as written by this edit."""
    fetch(env)
    add_study_row(module, env)  # adds `provenance_quote`, empty on the one fto_bmi row
    event = ledger(module)[-1]
    assert len(event["added"]) == 1 and event["removed"] == []


def test_a_quote_not_in_any_fetched_text_gets_no_anchor(module, env) -> None:
    fetch(env)
    add_study_row(module, env, quote=QUOTE.replace("higher", "lower"))
    (added,) = ledger(module)[-1]["added"]
    assert added["anchors"] == []


def test_the_ledger_holds_no_text_no_path_and_no_conversation(module, env) -> None:
    """It publishes: the article text, the module's absolute path and the session's cwd stay out."""
    search(env)
    fetch(env)
    add_study_row(module, env)
    raw = next((module / "logs" / "trace").glob("*.jsonl")).read_text("utf-8")
    assert QUOTE not in raw and "Discussion" not in raw
    assert str(module) not in raw and "/somewhere" not in raw and str(Path.home()) not in raw


def test_a_session_that_never_edits_a_module_leaves_no_ledger(module, env, tmp_path) -> None:
    search(env)
    fetch(env)
    loose = tmp_path / "work" / "notes.csv"  # a CSV with no module_spec.yaml beside it
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(loose)}}
    call("pre", env, **payload)
    loose.write_text("a,b\n1,2\n", encoding="utf-8")
    call("post", env, **payload)
    assert not (module / "logs" / "trace").exists()
    assert not (loose.parent / "logs").exists()


def test_off_means_nothing_written_anywhere(module, env) -> None:
    off = {**env, "JMC_TRACE": "0"}
    search(off)
    fetch(off)
    add_study_row(module, off)
    assert not (module / "logs" / "trace").exists()
    assert not Path(env["JMC_TRACE_DIR"]).exists()


def test_an_edit_without_its_pre_copy_says_unknown_never_all_rows(module, env) -> None:
    studies = module / "studies.csv"
    studies.write_text(studies.read_text("utf-8") + "", encoding="utf-8")
    call("post", env, tool_name="Edit", tool_input={"file_path": str(studies)})
    (event,) = ledger(module)
    assert event["baseline"] is None
    assert "added" not in event


def test_a_removed_row_is_named_by_its_hash(module, env) -> None:
    variants = module / "variants.csv"
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(variants)}}
    rows = variants.read_text("utf-8").splitlines(keepends=True)
    gone = tracehook.read_rows("".join(rows))[-1]
    call("pre", env, **payload)
    variants.write_text("".join(rows[:-1]), encoding="utf-8")
    call("post", env, **payload)
    (event,) = ledger(module)
    assert event["removed"] == [tracehook.row_sha256(gone)] and event["added"] == []


def _spill_notice(path: Path) -> str:
    """Claude Code's notice for a result over its inline limit, as measured on 2026-11-17."""
    return (
        f"Error: result (73,785 characters) exceeds maximum allowed tokens. Output has been saved "
        f"to {path}.\nFormat: JSON with schema: {{pmid: string, text: string}}\n- For targeted "
        "queries (find a value, filter by field): use jq on the file directly."
    )


def test_a_result_the_host_saved_to_a_file_is_read_from_it(module, env, tmp_path) -> None:
    """A long article arrives as a notice naming the file; its text is hashed all the same."""
    saved = tmp_path / "tool-results" / "fetch_fulltext-1.txt"
    saved.parent.mkdir()
    saved.write_text(json.dumps({"pmid": "37621650", "retrieved": True, "text": ARTICLE}), "utf-8")
    call(
        "post",
        env,
        tool_name=f"{CLAUDE}fetch_fulltext",
        tool_input={"pmid": "37621650"},
        tool_response=_spill_notice(saved),
    )
    add_study_row(module, env)
    fetched, edit = ledger(module)
    assert fetched["kind"] == "fetch" and fetched["chars"] == len(ARTICLE)
    assert edit["added"][0]["anchors"][0]["sha256"] == fetched["sha256"]
    assert str(saved) not in next((module / "logs" / "trace").glob("*.jsonl")).read_text("utf-8")


def test_an_unreadable_result_is_recorded_as_unknown_not_dropped(module, env, tmp_path) -> None:
    call(
        "post",
        env,
        tool_name=f"{CLAUDE}fetch_fulltext",
        tool_input={"pmid": "37621650"},
        tool_response=_spill_notice(tmp_path / "gone.txt"),
    )
    add_study_row(module, env)
    fetched = ledger(module)[0]
    assert fetched["kind"] == "fetch" and fetched["result"] is None
    assert fetched["asked"] == {"pmid": "37621650"} and fetched["why"] == "FileNotFoundError"


def test_a_codex_patch_is_read_for_its_paths(module, env) -> None:
    patch = "*** Begin Patch\n*** Update File: studies.csv\n@@\n-a\n+b\n*** End Patch\n"
    files = tracehook.edited_files("apply_patch", {"command": patch}, str(module))
    assert files == [module / "studies.csv"]


def test_a_codex_mcp_result_is_unwrapped() -> None:
    wrapped = {"content": [{"type": "text", "text": json.dumps({"pmid": "37621650"})}]}
    assert tracehook._result(wrapped) == {"pmid": "37621650"}
    assert tracehook._result({"structuredContent": {"pmid": "1"}}) == {"pmid": "1"}


def test_only_our_server_is_recorded() -> None:
    assert tracehook.our_tool(f"{CLAUDE}fetch_fulltext") == "fetch_fulltext"
    assert tracehook.our_tool("mcp__just-module-creator__fetch_fulltext") == "fetch_fulltext"
    assert tracehook.our_tool("mcp__just-dna-lite__start_annotation") is None
    assert tracehook.our_tool("Bash") is None


def test_the_end_hook_deletes_the_buffer(module, env) -> None:
    fetch(env)
    buffers = list(Path(env["JMC_TRACE_DIR"]).iterdir())
    assert len(buffers) == 1 and any(buffers[0].rglob("*.txt"))
    call("end", env)
    assert not any(Path(env["JMC_TRACE_DIR"]).iterdir())


def test_a_failing_hook_exits_zero(tmp_path) -> None:
    """A hook that raised would break the host's tool call; this one reports and lets it pass."""
    script = ROOT / "src" / "just_module_creator" / "tracehook.py"
    done = subprocess.run(
        [sys.executable, "-I", str(script), "post"],
        input="not json",
        capture_output=True,
        text=True,
        env={"JMC_TRACE_DIR": str(tmp_path / "b"), "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert done.returncode == 0
    assert "trace hook (post)" in done.stderr


def test_the_hook_imports_nothing_outside_the_standard_library() -> None:
    """It runs as `python -I` with no project environment, so any third-party import fails there."""
    tree = (ROOT / "src" / "just_module_creator" / "tracehook.py").read_text("utf-8")
    imported = set(re.findall(r"^(?:from|import) ([a-zA-Z_][\w]*)", tree, flags=re.M))
    assert "json" in imported  # the anchor: the scan reads imports at all
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}, imported


@pytest.mark.parametrize(
    ("hooks_file", "root_var", "prefix", "edits"),
    [
        ("hooks/hooks.json", "${CLAUDE_PLUGIN_ROOT}", CLAUDE, ["Write", "Edit", "MultiEdit"]),
        ("hooks/codex-hooks.json", "${PLUGIN_ROOT}", "mcp__just-module-creator__", ["apply_patch"]),
    ],
)
def test_each_host_runs_the_hook_where_it_must(hooks_file, root_var, prefix, edits) -> None:
    """Each matcher, compiled as the host compiles it, catches every recorded tool by its full name,
    every edit tool before and after, any of our tools before (to know its module) and after, and
    the shell after (F165). Never just-dna-lite's tools; only through the host's root variable."""
    config = json.loads((ROOT / hooks_file).read_text("utf-8"))["hooks"]
    pre = re.compile(config["PreToolUse"][0]["matcher"])
    post = re.compile(config["PostToolUse"][0]["matcher"])
    for tool in tracehook.RECORDED_TOOLS | {"prune_rows", "validate_module"}:
        assert post.fullmatch(f"{prefix}{tool}") and pre.fullmatch(f"{prefix}{tool}"), tool
    for tool in edits:
        assert pre.fullmatch(tool) and post.fullmatch(tool), tool
    assert post.fullmatch("Bash") and not pre.fullmatch("Bash")
    assert not post.fullmatch("mcp__just-dna-lite__start_annotation")
    commands = [h["command"] for event in config.values() for e in event for h in e["hooks"]]
    assert commands and all(root_var in c and "tracehook.py" in c for c in commands)


def test_codex_reads_its_own_hooks_file() -> None:
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text("utf-8"))
    assert manifest["hooks"] == "./hooks/codex-hooks.json"


async def test_the_recorded_tools_exist(client) -> None:
    names = {t.name for t in await client.list_tools()}
    assert "fetch_fulltext" in names  # the anchor
    assert names >= tracehook.RECORDED_TOOLS


def test_this_repository_turns_the_hook_off() -> None:
    """Editing `assets/` here must not grow a ledger in a committed fixture."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text("utf-8"))
    assert settings["env"]["JMC_TRACE"] == "0"


def _append_row(module: Path) -> None:
    """A write the hook cannot see: what a Python `csv` script run through the shell does."""
    studies = module / "studies.csv"
    rows = tracehook.read_rows(studies.read_text("utf-8"))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=[*rows[0], "provenance_quote"])
    writer.writeheader()
    writer.writerows(rows)
    writer.writerow(
        {
            "rsid": "rs17782313",
            "pmid": "37621650",
            "study_design": "meta-analysis",
            "conclusion": "Higher BMI.",
            "provenance_quote": QUOTE,
        }
    )
    studies.write_text(out.getvalue(), encoding="utf-8")


def _our(env, phase, tool, module, **extra) -> None:
    call(
        phase,
        env,
        tool_name=f"{CLAUDE}{tool}",
        tool_input={"spec_dir": str(module), **extra},
        tool_response=json.dumps({}),
    )


def test_a_table_written_through_the_shell_still_reaches_the_ledger(module, env) -> None:
    """F165: the session's search, fetch and decision were dropped with no ledger at all, because
    the row went in through a shell command the hook cannot see as an edit."""
    search(env)
    fetch(env)
    _our(env, "pre", "record_decision", module)  # any call of ours naming the module makes it known
    _our(env, "post", "record_decision", module)
    _append_row(module)
    call("post", env, tool_name="Bash", tool_input={"command": "uv run python write_rows.py"})
    events = ledger(module)
    assert [e["kind"] for e in events] == ["search", "fetch", "decision", "edit"]
    edit = events[-1]
    assert edit["via"] == "Bash" and len(edit["added"]) == 1
    assert edit["added"][0]["anchors"][0]["column"] == "provenance_quote"
    # Nothing of the command reaches the ledger.
    raw = next((module / "logs" / "trace").glob("*.jsonl")).read_text("utf-8")
    assert "write_rows.py" not in raw


def test_a_tool_that_writes_tables_is_named_as_the_route(module, env) -> None:
    _our(env, "pre", "prune_rows", module)
    _append_row(module)  # stands in for what the tool itself wrote while it ran
    _our(env, "post", "prune_rows", module)
    (edit,) = ledger(module)
    assert edit["via"] == "prune_rows" and len(edit["added"]) == 1


def test_a_change_found_only_at_session_end_is_still_recorded(module, env) -> None:
    fetch(env)
    _our(env, "post", "validate_module", module)
    _append_row(module)
    call("end", env)
    kinds = [e["kind"] for e in ledger(module)]
    assert kinds == ["fetch", "edit"] and ledger(module)[-1]["via"] == "unobserved"
    assert not any(Path(env["JMC_TRACE_DIR"]).iterdir())


def test_a_shell_call_in_a_session_that_knows_no_module_writes_nothing(module, env) -> None:
    search(env)
    _append_row(module)
    call("post", env, tool_name="Bash", tool_input={"command": "ls"})
    call("end", env)
    assert not (module / "logs" / "trace").exists()
