"""`trace_module` — a module's rows joined back to its provenance ledger (RM31 part 2).

The ledger in each case is written by the real hook (`tracehook.handle`), driven with the payloads a
host sends, over a copy of `assets/fto_bmi`, so the join reads exactly what a session would leave.
The three negative controls are the hand trial's (DESIGN-traceability §10): a title used as the
quote, a quote not in the fetched text, a PMID no search returned. Each must reach `contradicted`,
or the join could not have failed.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

import pytest
from conftest import offline_settings
from just_dna_compiler import hints
from just_dna_format.spec import StudyRow

from just_module_creator import trace, tracehook

ROOT = Path(__file__).parent.parent
CLAUDE = "mcp__plugin_just-module-creator_just-module-creator__"
#: Verbatim from PMC10445758 (PMID 37621650); the title is that article's, from PubMed.
QUOTE = (
    "The present meta-analysis demonstrates that the C allele of the rs17782313 polymorphism near "
    "MC4R is associated with a higher level of BMI, WC or GLU, but not with blood lipids"
)
TITLE = (
    "The rs17782313 polymorphism near MC4R gene confers a high risk of obesity and hyperglycemia, "
    "while PGC1α rs8192678 polymorphism is weakly correlated with glucometabolic disorder: a "
    "systematic review and meta-analysis."
)
ARTICLE = f"{TITLE} Abstract. Discussion {QUOTE}, in agreement with earlier findings."


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    return {"JMC_TRACE_DIR": str(tmp_path / "buffer")}


@pytest.fixture
def module(tmp_path: Path) -> Path:
    target = tmp_path / "fto_bmi"
    shutil.copytree(ROOT / "assets" / "fto_bmi", target)
    return target


def hook(phase: str, env: dict[str, str], **payload) -> None:
    tracehook.handle(phase, {"session_id": "s-0001", "cwd": "/x", **payload}, env)


def search(env: dict[str, str], returned: list[str]) -> None:
    papers = [{"pmid": p, "title": TITLE if p == "37621650" else f"Paper {p}"} for p in returned]
    result = {"query": "(rs17782313) AND (body mass index)", "papers": papers, "sources": []}
    hook(
        "post",
        env,
        tool_name=f"{CLAUDE}literature_search",
        tool_input={"rsid": "rs17782313"},
        tool_response=json.dumps(result),
    )


def fetch(env: dict[str, str], pmid: str = "37621650") -> None:
    result = {"pmid": pmid, "retrieved": True, "text": ARTICLE, "text_source": "fulltext"}
    hook(
        "post",
        env,
        tool_name=f"{CLAUDE}fetch_fulltext",
        tool_input={"pmid": pmid},
        tool_response=json.dumps(result),
    )


def write_study(
    module: Path, env: dict[str, str], pmid: str = "37621650", quote: str = QUOTE
) -> None:
    studies = module / "studies.csv"
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(studies)}}
    hook("pre", env, **payload)
    rows = tracehook.read_rows(studies.read_text("utf-8"))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=[*rows[0], "provenance_quote"])
    writer.writeheader()
    writer.writerows(rows)
    writer.writerow(
        {
            "rsid": "rs17782313",
            "pmid": pmid,
            "study_design": "meta-analysis",
            "conclusion": "Higher BMI with the C allele.",
            "provenance_quote": quote,
        }
    )
    studies.write_text(out.getvalue(), encoding="utf-8")
    hook("post", env, **payload)


def run(module: Path) -> list[trace.RowState]:
    return trace.trace(module, ["studies.csv", "variants.csv"], frozenset({"studies.csv"}))


def by_rsid(states: list[trace.RowState], file: str, rsid: str, module: Path) -> trace.RowState:
    rows = tracehook.read_rows((module / file).read_text("utf-8"))
    lines = {i + 2 for i, r in enumerate(rows) if r.get("rsid") == rsid}
    (state,) = [s for s in states if s.file == file and s.line in lines]
    return state


def test_a_recorded_chain_is_traced_and_an_older_row_is_not(module, env) -> None:
    search(env, ["38674326", "37621650"])
    fetch(env)
    write_study(module, env)
    states = run(module)

    new = by_rsid(states, "studies.csv", "rs17782313", module)
    assert (new.written, new.citation) == ("recorded", trace.TRACED), new.why
    old = by_rsid(states, "studies.csv", "rs1421085", module)
    assert (old.written, old.citation) == ("not_recorded", trace.NOT_TRACEABLE)
    # A table with no citation column gets no citation state, only whether an edit wrote it.
    variants = [s for s in states if s.file == "variants.csv"]
    assert variants and {(s.written, s.citation) for s in variants} == {("not_recorded", None)}


def test_a_title_used_as_the_quote_is_contradicted(module, env) -> None:
    search(env, ["37621650"])
    fetch(env)  # the title occurs in its own fulltext, so the anchor alone would say traced
    write_study(module, env, quote=TITLE)
    state = by_rsid(run(module), "studies.csv", "rs17782313", module)
    assert state.citation == trace.CONTRADICTED and "title" in state.why


def test_a_quote_not_in_the_fetched_text_is_contradicted(module, env) -> None:
    search(env, ["37621650"])
    fetch(env)
    write_study(module, env, quote=QUOTE.replace("higher", "lower"))
    state = by_rsid(run(module), "studies.csv", "rs17782313", module)
    assert state.citation == trace.CONTRADICTED and "not in the text fetched" in state.why


def test_a_pmid_no_search_returned_is_unknown_never_contradicted(module, env) -> None:
    """F161: a route the ledger cannot see (a drafter, a lookup, a paper handed over) is an
    unknown. The recalled-PMID failure still shows, by its own reason, without being asserted."""
    search(env, ["38674326"])  # 37621650 is not among the results
    fetch(env)
    write_study(module, env)
    state = by_rsid(run(module), "studies.csv", "rs17782313", module)
    assert state.citation == trace.NOT_TRACEABLE
    assert "no recorded search or citation list returned PMID 37621650" in state.why


def test_a_paper_reached_by_citation_traversal_is_traced(module, env) -> None:
    """F161's case: the PMID came from `paper_citations`, then was fetched and quoted."""
    papers = [{"pmid": "37621650", "title": TITLE}]
    hook(
        "post",
        env,
        tool_name=f"{CLAUDE}paper_citations",
        tool_input={"pmid": "31954858", "direction": "citing"},
        tool_response=json.dumps(
            {"paper_id": "31954858", "direction": "citing", "papers": papers, "sources": []}
        ),
    )
    fetch(env)
    write_study(module, env)
    state = by_rsid(run(module), "studies.csv", "rs17782313", module)
    assert state.citation == trace.TRACED, state.why


def test_a_quote_cut_from_the_title_is_contradicted(module, env) -> None:
    """A piece of the title is verbatim in the fulltext too, so its text anchor proves nothing."""
    search(env, ["37621650"])
    fetch(env)
    piece = "The rs17782313 polymorphism near MC4R gene confers a high risk of obesity"
    write_study(module, env, quote=piece)
    state = by_rsid(run(module), "studies.csv", "rs17782313", module)
    assert (
        state.citation == trace.CONTRADICTED
        and "piece of the cited article's own title" in state.why
    )


def test_an_unreadable_search_is_named_in_the_reason(module, env) -> None:
    hook(
        "post",
        env,
        tool_name=f"{CLAUDE}literature_search",
        tool_input={"rsid": "rs17782313"},
        tool_response="not json at all",
    )
    fetch(env)
    write_study(module, env)
    state = by_rsid(run(module), "studies.csv", "rs17782313", module)
    assert state.citation == trace.NOT_TRACEABLE and "could not be read" in state.why


def test_a_bad_ledger_line_is_counted_never_skipped_silently(module, env) -> None:
    search(env, ["37621650"])
    fetch(env)
    write_study(module, env)
    ledger_file = next((module / "logs" / "trace").glob("*.jsonl"))
    ledger_file.write_text(ledger_file.read_text("utf-8") + "{truncated\n", encoding="utf-8")
    assert trace.read_ledger(module).unreadable_lines == 1


def test_the_citation_column_is_the_formats() -> None:
    """Two names the join cannot generate, guarded against the format and the compiler.

    The quote-bearing table comes from `hints.REDUNDANCY_BEARING_TABLES`; both names must be fields
    of the model of the row it holds, or the join would read a column no module has.
    """
    tables = hints.REDUNDANCY_BEARING_TABLES[trace.QUOTE_COLUMN]
    assert "studies.csv" in tables  # the anchor: the table this join was built against
    assert {trace.CITATION_COLUMN, trace.QUOTE_COLUMN} <= set(StudyRow.model_fields)


async def test_the_tool_reports_every_row_with_its_scope(module, env, make_client) -> None:
    search(env, ["37621650"])
    fetch(env)
    write_study(module, env)
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("trace_module", {"spec_dir": str(module)})).data
    assert report.ledgers and report.events["edit"] == 1
    assert report.counts["citation:traced"] == 1
    assert report.counts["citation:not_traceable"] == 1
    assert report.counts["written:recorded"] == 1
    assert "weight" in report.scope and "Not whether any row is right" in report.scope


async def test_no_ledger_reads_as_unknown_never_as_a_defect(module, make_client) -> None:
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("trace_module", {"spec_dir": str(module)})).data
    assert report.ledgers == []
    assert {r.written for r in report.rows} == {"not_recorded"}
    assert "unknown, not a defect" in report.next_step


def decide(env: dict[str, str], **arguments) -> None:
    hook(
        "post",
        env,
        tool_name=f"{CLAUDE}record_decision",
        tool_input=arguments,
        tool_response=json.dumps({"recording": "hook"}),
    )


def decisions(module: Path) -> list[trace.DecisionState]:
    return trace.decision_states(trace.read_ledger(module))


def test_a_reason_anchored_to_a_paper_that_never_names_its_variant_is_declared(module, env) -> None:
    """The tester's first finding on the hand trial: an LD reason about rs1421085 anchored to an
    FTO x depression passage that never names rs1421085. The anchor is real; the support is not."""
    fetch(env)  # the fetched article names rs17782313, never rs1421085
    decide(
        env,
        spec_dir=str(module),
        subject="rsid:rs17782313",
        verdict="not_used",
        basis="read",
        why="In strong linkage disequilibrium with rs1421085, already in the module.",
        passage=QUOTE,
    )
    write_study(module, env)
    (state,) = decisions(module)
    assert state.witness == "declared" and "never names rs1421085" in state.because


def test_a_reason_whose_passage_names_its_variants_is_anchored_with_where_to_read_it(
    module, env
) -> None:
    fetch(env)
    decide(
        env,
        spec_dir=str(module),
        subject="pmid:37621650",
        verdict="used",
        basis="read",
        why="States the rs17782313 C allele association with BMI.",
        passage=QUOTE,
    )
    write_study(module, env)
    (state,) = decisions(module)
    assert state.witness == "anchored", state.because
    (where,) = state.passages
    assert (where["pmid"], where["offset"], where["len"]) == (
        "37621650",
        ARTICLE.index(QUOTE),
        len(QUOTE),
    )
    assert "for a reader" in state.because


def test_a_reason_naming_no_variant_is_declared_whatever_the_passage(module, env) -> None:
    """F162 case C: a weight's reason usually names no rsID, and "names every variant it names"
    is vacuous over none, so a methods sentence about mice once read as evidence for it."""
    fetch(env)
    decide(
        env,
        spec_dir=str(module),
        subject="variants.csv weight",
        verdict="-0.5",
        basis="read",
        why="Because the effect on body mass is large.",
        passage=QUOTE,
    )
    write_study(module, env)
    (state,) = decisions(module)
    assert state.witness == "declared" and "names no variant" in state.because


def test_anchored_never_claims_the_passage_supports_the_reason(module, env) -> None:
    """F162 case B: the same passage under a reason it contradicts. No check here can tell, so
    the label says located, not supported, and points the reader at the passage."""
    fetch(env)
    decide(
        env,
        spec_dir=str(module),
        subject="rsid:rs17782313",
        verdict="not_used",
        basis="read",
        why="rs17782313 is not associated with BMI.",
        passage=QUOTE,
    )
    write_study(module, env)
    (state,) = decisions(module)
    assert state.witness == "anchored"  # located, and names rs17782313: all a check can know
    assert "whether it supports the reason is for a reader" in state.because
    assert state.passages


def test_a_recalled_reason_is_kept_and_never_counted(module, env) -> None:
    decide(
        env,
        spec_dir=str(module),
        subject="rsid:rs6567160",
        verdict="not_used",
        basis="recalled",
        why="Dropped in the original README; reason not re-read here.",
    )
    write_study(module, env)
    (state,) = decisions(module)
    assert state.witness == "recalled"


def test_a_passage_from_no_fetched_text_is_declared(module, env) -> None:
    fetch(env)
    decide(
        env,
        spec_dir=str(module),
        subject="pmid:37621650",
        verdict="used",
        basis="read",
        why="Supports rs17782313.",
        passage=QUOTE.replace("higher", "lower"),
    )
    write_study(module, env)
    (state,) = decisions(module)
    assert state.witness == "declared" and "no text fetched" in state.because


async def test_record_decision_writes_nothing_and_refuses_a_bad_basis(module, make_client) -> None:
    before = sorted(p.name for p in module.rglob("*"))
    async with make_client(offline_settings()) as client:
        stated = (
            await client.call_tool(
                "record_decision",
                {
                    "spec_dir": str(module),
                    "subject": "pmid:37621650",
                    "verdict": "used",
                    "why": "States the association.",
                    "basis": "recalled",
                },
            )
        ).data
        with pytest.raises(Exception, match="basis"):
            await client.call_tool(
                "record_decision",
                {
                    "spec_dir": str(module),
                    "subject": "x",
                    "verdict": "y",
                    "why": "z",
                    "basis": "guessed",
                },
            )
    assert sorted(p.name for p in module.rglob("*")) == before
    assert stated.recording in {"hook", "off"} and stated.basis == "recalled"


def test_a_ledger_without_the_tie_field_reads_the_tie_from_the_reason(module, env) -> None:
    """A ledger from the hook before `tied` existed: the join derives the tie itself (the tester's
    leftover on F162), so a reason naming rs17782313 is not read as naming no variant."""
    fetch(env)
    decide(
        env,
        spec_dir=str(module),
        subject="pmid:37621650",
        verdict="used",
        basis="read",
        why="States the rs17782313 C allele association with BMI.",
        passage=QUOTE,
    )
    write_study(module, env)
    ledger_file = next((module / "logs" / "trace").glob("*.jsonl"))
    lines = []
    for line in ledger_file.read_text("utf-8").splitlines():
        event = json.loads(line)
        event.pop("tied", None)
        lines.append(json.dumps(event))
    ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (state,) = decisions(module)
    assert state.witness == "anchored", state.because


def test_an_old_ledger_never_claims_a_check_it_did_not_make(module, env) -> None:
    """F163: the hook before `tied` checked a passage against the reason's variants only. A
    decision naming rs1421085 in its subject alone was never checked for it, so it reads
    declared, not anchored, however the stale `unnamed` reads."""
    fetch(env)  # the article names rs17782313, never rs1421085
    decide(
        env,
        spec_dir=str(module),
        subject="rsid:rs1421085",
        verdict="-0.5",
        basis="read",
        why="Because the effect on body mass is large.",
        passage=QUOTE,
    )
    write_study(module, env)
    ledger_file = next((module / "logs" / "trace").glob("*.jsonl"))
    lines = []
    for line in ledger_file.read_text("utf-8").splitlines():
        event = json.loads(line)
        if event.get("kind") == "decision":
            event.pop("tied", None)
            event["unnamed"] = []  # what the older hook stored: the reason names no rsID
        lines.append(json.dumps(event))
    ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (state,) = decisions(module)
    assert state.witness == "declared" and "never checked for rs1421085" in state.because


async def test_the_description_says_what_the_states_mean_now(make_client) -> None:
    """F164: the released description still listed 'a citation no search returned' under
    contradicted after F161 made it not_traceable, and said nothing of decisions (F162)."""
    async with make_client(offline_settings()) as client:
        tools = {t.name: t for t in await client.list_tools()}
    text = " ".join((tools["trace_module"].description or "").split())
    assert "contradicted" in text  # the anchor: the states are described at all
    contradicted = text.split("`contradicted`", 1)[1].split("`not_traceable`", 1)[0]
    assert "no search" not in contradicted and "no recorded search" not in contradicted
    assert "never evidence against the row" in text
    assert "`anchored`" in text and "Anchored is never support" in text


def ask(env: dict[str, str], answers: object) -> None:
    """The host's question tool, answered (RM32). Text written for this test."""
    hook(
        "post",
        env,
        tool_name="AskUserQuestion",
        tool_input={"questions": [{"question": "Keep the trans-ancestry rows?", "options": []}]},
        tool_response={"answers": answers} if isinstance(answers, dict) else answers,
    )


async def test_answered_questions_are_set_beside_the_authors_recorded_decisions(
    module, env, make_client
) -> None:
    ask(env, {"Keep the trans-ancestry rows?": "No"})
    ask(env, "unreadable")
    decide(
        env,
        spec_dir=str(module),
        subject="studies.csv",
        verdict="trans-ancestry rows left out",
        basis="author",
        why="Author decided to keep only European-ancestry effect sizes.",
    )
    write_study(module, env)
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("trace_module", {"spec_dir": str(module)})).data
    counted = (report.questions_answered, report.questions_unread, report.author_decisions)
    assert counted == (1, 1, 1)
    assert "answered 2 question(s)" in report.next_step
    assert "record_decision(basis='author')" in report.next_step
    # Never evidence against a row.
    assert report.counts.get("citation:contradicted", 0) == 0


async def test_no_question_asked_adds_nothing_to_the_next_step(module, env, make_client) -> None:
    search(env, ["37621650"])
    fetch(env)
    write_study(module, env)
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("trace_module", {"spec_dir": str(module)})).data
    assert report.ledgers and report.questions_answered == 0
    assert "question" not in report.next_step
