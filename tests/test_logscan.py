"""Reading a log before the catalog keeps it forever (RM25).

**The calibration is the point of this file.** `assets/logs/quote-remediation.log`
is a real log that really travelled to two polygon rehearsals, and it must come
back clean — a check that flags an honest hand-written run log is a check whose
false positives will teach everyone to ignore it.

The positive cases are built here rather than committed. A real agent transcript
is 450 KB of somebody else's system prompts, and committing one to prove a
scanner works would be the leak the scanner exists to prevent. Where a value is
constructed below, its **shape** is the subject under test and the value carries
no information — which is the one case §2's "no fabricated example value" rule is
not about.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import offline_settings

from just_module_creator.logscan import LONG_LINE, logs_in, scan_file, scan_text

FIXTURE = Path(__file__).resolve().parent.parent / "assets" / "logs" / "quote-remediation.log"


def test_the_honest_run_log_is_clean() -> None:
    """The calibration case. If this ever flags, fix the scanner, not the log.

    It is 73 lines of hand-written provenance naming the model that did the work
    and stating that no human read the articles — exactly what a published log
    should look like.
    """
    assert scan_file(FIXTURE) == []
    # And it must really be the file that travelled, not an empty stand-in.
    body = FIXTURE.read_text(encoding="utf-8")
    assert "provenance_quote remediation" in body
    assert "human_confirmation" in body


def test_the_word_token_alone_is_not_a_credential() -> None:
    """The fixture says "every rsID token" — a wordlist scanner would flag it.

    Credential detection is on SHAPE: a name, an assignment, and a value with
    real length. This is the specific false positive that was measured before the
    scanner was written.
    """
    assert scan_text("Each of the 26 cited PMIDs was retrieved and every rsID token matched") == []
    assert scan_text("the access token was rotated") == []


def test_an_assigned_credential_is_flagged() -> None:
    """Shape under test; the value is a run of one character and means nothing."""
    flags = scan_text("api_key=" + "A" * 32)
    assert [f.kind for f in flags] == ["credential_shaped"]


def test_a_flag_does_not_reprint_the_whole_line() -> None:
    """A finding that echoes a credential in full has copied it somewhere new.

    This output is read by an agent whose transcript is itself retained, so the
    detail is a recognisable fragment and never the entire line.
    """
    secret = "B" * 400
    flags = scan_text(f"authorization: {secret}")
    assert flags and secret not in flags[0].detail
    assert flags[0].detail.endswith("…")


def test_an_absolute_path_is_flagged_and_a_url_path_is_not() -> None:
    """`/api/v1/` in a URL is not a filesystem path, and flagging it would be noise."""
    real = "wrote /data/sources/just-module-creator/out/module.parquet"
    assert [f.kind for f in scan_text(real)] == ["absolute_path"]

    assert scan_text("GET https://example.org/api/v1/paper/search?query=lactase") == []


def test_a_system_prompt_sized_line_is_flagged() -> None:
    """Measured signature: the honest fixture tops out at 92 characters.

    A real submitted transcript carries single lines past 8000. The threshold sits
    far above the first and far below the second, so neither is a close call.
    """
    assert scan_text("x" * (LONG_LINE + 1))[0].kind == "very_long_line"
    assert scan_text("x" * (LONG_LINE - 1)) == []

    longest = max(len(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines())
    assert longest < LONG_LINE / 10, "the clean fixture should not be anywhere near the threshold"


def test_it_finds_every_log_a_compile_would_sweep(tmp_path: Path) -> None:
    """`logs/**/*.log` plus top-level `*.log` — nested included, other files not."""
    spec = tmp_path / "spec"
    (spec / "logs" / "nested").mkdir(parents=True)
    for relative in ("run.log", "logs/researcher.log", "logs/nested/deep.log"):
        (spec / relative).write_text("clean\n", encoding="utf-8")
    (spec / "logs" / "notes.txt").write_text("not swept\n", encoding="utf-8")

    assert [p.relative_to(spec).as_posix() for p in logs_in(spec)] == [
        "logs/nested/deep.log",
        "logs/researcher.log",
        "run.log",
    ]


async def test_review_logs_reports_and_changes_nothing(make_client, tmp_path: Path) -> None:
    """The tool is a read. It refuses nothing and it rewrites nothing."""
    spec = tmp_path / "spec"
    (spec / "logs").mkdir(parents=True)
    target = spec / "logs" / "run.log"
    target.write_text("resolved /home/somebody/uploads/paper.pdf\n", encoding="utf-8")
    before = target.read_bytes()

    async with make_client(offline_settings()) as client:
        data = (await client.call_tool("review_logs", {"spec_dir": str(spec)})).data

    assert data.logs == ["logs/run.log"]
    assert [f.kind for f in data.findings] == ["absolute_path"]
    assert data.total_bytes == len(before)
    assert "Nothing was changed" in data.note
    assert target.read_bytes() == before


async def test_a_module_with_no_logs_says_so(make_client, tmp_path: Path) -> None:
    """Absence is reported as absence, not as a clean bill of health."""
    spec = tmp_path / "spec"
    spec.mkdir()
    async with make_client(offline_settings()) as client:
        data = (await client.call_tool("review_logs", {"spec_dir": str(spec)})).data

    assert data.logs == [] and data.findings == [] and data.total_bytes == 0
    assert "No logs found" in data.note


@pytest.mark.parametrize("kind", ["absolute_path", "credential_shaped", "very_long_line"])
def test_findings_are_ordered_deterministically(kind: str) -> None:
    """Never from set iteration: this output is compared and read by an agent."""
    text = "\n".join(
        ["clean line", "/home/a/b.pdf", "api_key=" + "C" * 32, "x" * (LONG_LINE + 1)]
    )
    flags = scan_text(text)
    assert [f.line for f in flags] == sorted(f.line or 0 for f in flags)
    assert kind in {f.kind for f in flags}
