"""Drafting and the fact passes: the licence gate and the four row statuses.

Hermetic — everything here runs under the offline ceiling, so no drafter reaches
a source. What is asserted is the contract around the call: that `use` cannot be
defaulted, that a licence refusal stays a refusal rather than becoming a failure,
and that upstream's per-row distinctions survive the MCP boundary.
"""

from __future__ import annotations

import json

import pytest
from conftest import offline_settings
from fastmcp.exceptions import ToolError

from just_module_creator.models import DraftResult
from just_module_creator.tools.passes import (
    VALID_USE,
    _check_use,
    _draft_result,
    _tables,
    _translate,
)
from just_module_creator.tools.registry import RECEIPTS_FILE, _record_receipt


class FakeOutcome:
    def __init__(self, status: str, key: tuple = ("rs4988235",), differences: dict | None = None):
        self.status = status
        self.key = key
        self.differences = differences or {}


class FakeReport:
    """Shaped like `just_dna_compiler.draft.DraftReport`, including its properties."""

    def __init__(
        self, csv_name: str, outcomes: list[FakeOutcome], shifted: list[int] | None = None
    ):
        self.csv_name = csv_name
        self.outcomes = outcomes
        self.written = True
        self.shifted = shifted or []

    @property
    def added(self):
        return [o for o in self.outcomes if o.status in {"added", "appended_unkeyed"}]

    @property
    def already_present(self):
        return [o for o in self.outcomes if o.status == "already_present"]

    @property
    def differs(self):
        return [o for o in self.outcomes if o.status == "differs"]

    @property
    def invalid(self):
        return [o for o in self.outcomes if o.status == "invalid"]


class FakeDraft:
    def __init__(self, reports=None, warnings=None, skipped=False):
        self.reports = reports or []
        self.warnings = warnings or []
        self.skipped = skipped


# --------------------------------------------------------------------------- #
# The licence gate
# --------------------------------------------------------------------------- #
def test_use_has_no_default_and_names_the_valid_values() -> None:
    for value in VALID_USE:
        assert _check_use(value) == value
    assert _check_use("NON-COMMERCIAL") == "non_commercial"

    with pytest.raises(ToolError) as excinfo:
        _check_use("free")
    message = str(excinfo.value)
    for value in VALID_USE:
        assert value in message


async def test_use_is_a_required_argument_not_a_defaulted_one(make_client) -> None:
    """Inheriting upstream's `declared_use='unstated'` would silently skip sources.

    Rejected at the schema layer rather than by a check inside the tool, so an
    agent cannot reach the source at all without stating a position.
    """
    async with make_client("essentials", offline_settings()) as client:
        tool = next(t for t in await client.list_tools() if t.name == "draft_from_clinvar")
        assert "use" in (tool.inputSchema.get("required") or [])


async def test_a_licence_refusal_is_reported_not_raised() -> None:
    """`skipped=True` must stay a first-class field, never `success=False`.

    A failure invites retrying with a different `use` to make the tool work,
    which is precisely fabricating a licence position to get data.
    """
    refusal = FakeDraft(warnings=["clinpgx forbids sale; declared_use='commercial'"], skipped=True)

    result = _draft_result(
        refusal,
        spec_dir=__import__("pathlib").Path("/tmp/x"),
        source="clinpgx",
        use="commercial",
        dry_run=False,
    )

    assert isinstance(result, DraftResult)
    assert result.skipped is True
    assert result.warnings, "the refusal reason must survive"
    assert "do not" in result.next_step.lower()


# --------------------------------------------------------------------------- #
# Report, never repair
# --------------------------------------------------------------------------- #
def test_the_four_row_statuses_survive_the_boundary() -> None:
    """Collapsing them to one count would hide the rows worth reading."""
    report = FakeReport(
        "variants.csv",
        [
            FakeOutcome("added"),
            FakeOutcome("added", key=("rs1801133",)),
            FakeOutcome("already_present"),
            FakeOutcome("differs", differences={"clin_sig": ("benign", "pathogenic")}),
            FakeOutcome("invalid"),
        ],
        shifted=[3, 4],
    )

    tables = _tables(FakeDraft([report]), written=True)

    assert len(tables) == 1
    table = tables[0]
    assert (table.added, table.already_present, table.differs, table.invalid) == (2, 1, 1, 1)
    # `shifted` explains a digest change that is not a content change.
    assert table.shifted == 2


def test_a_disagreement_is_reported_with_both_values() -> None:
    """The source disagrees with an authored row; upstream leaves the row alone.

    Rewriting it would destroy the evidence that the two disagree, and only the
    author knows which side is right — so the detail has to reach the caller.
    """
    report = FakeReport(
        "variants.csv",
        [FakeOutcome("differs", differences={"clin_sig": ("benign", "pathogenic")})],
    )

    table = _tables(FakeDraft([report]), written=True)[0]

    assert table.differs == 1
    assert len(table.differences) == 1
    detail = table.differences[0]
    assert "clin_sig" in detail
    assert "benign" in detail and "pathogenic" in detail


def test_a_dry_run_reports_nothing_written() -> None:
    report = FakeReport("variants.csv", [FakeOutcome("added")])
    tables = _tables(FakeDraft([report]), written=False)
    assert tables[0].written is False


# --------------------------------------------------------------------------- #
# Upstream's message, kept
# --------------------------------------------------------------------------- #
def test_an_upstream_message_is_kept_verbatim_and_annotated() -> None:
    """Rewriting it would corrupt the CLI commands it legitimately contains."""
    original = (
        "no ClinVar snapshot found. Drop --offline to download the published one, pass "
        "--snapshot PATH, or build it yourself with `just-dna-enricher clinvar build --download`."
    )

    translated = _translate(original)

    # Verbatim: the real CLI command inside it still works if you paste it.
    assert original in translated
    assert "clinvar build --download" in translated
    # Annotated: our argument names are reachable without guessing.
    assert "offline=false" in translated
    assert "snapshot=<path>" in translated


def test_a_message_with_no_cli_flags_is_left_completely_alone() -> None:
    plain = "gnomAD returned no constraint entry for MCM6."
    assert _translate(plain) == plain


# --------------------------------------------------------------------------- #
# The findings boundary
# --------------------------------------------------------------------------- #
def test_the_editor_line_survives_the_boundary_and_is_never_derived() -> None:
    """`row` and `line` are different conventions and both have to arrive (F14).

    Upstream's `row` is a 0-based data-row index; `line` is the 1-based
    header-inclusive file line an editor shows. They disagree by design for the
    same finding, so `to_findings` passes both through rather than computing one
    from the other — an offset baked in here would silently go wrong the day
    upstream changed either convention.
    """
    from just_dna_compiler.hints import Finding

    from just_module_creator.tools._shared import to_findings

    # A real upstream Finding, not a stub: the field has to exist to be carried.
    upstream = Finding(0, "unresolved", "error", "Input should be a valid boolean", 3)

    (carried,) = to_findings([upstream])

    assert (carried.row, carried.line) == (0, 3)
    assert carried.column == "unresolved"
    assert carried.level == "error"


def test_an_absent_line_stays_null_rather_than_becoming_row_plus_one() -> None:
    """A table-wide finding has no line; inventing one would point at real text."""
    from just_dna_compiler.hints import Finding

    from just_module_creator.tools._shared import to_findings

    (carried,) = to_findings([Finding(None, None, "warning", "table-wide note")])

    assert carried.line is None
    assert carried.row is None


# --------------------------------------------------------------------------- #
# Tiering
# --------------------------------------------------------------------------- #
async def test_clinvar_drafting_is_available_in_essentials(make_client) -> None:
    """F1's hole only closes if it closes in the default mode."""
    async with make_client("essentials", offline_settings()) as client:
        names = {t.name for t in await client.list_tools()}
        assert "draft_from_clinvar" in names
        # The specialist path stays behind the opt-in.
        assert "draft_from_cpic" not in names
        assert "draft_from_clinpgx" not in names
        assert "enrich_facts" not in names


async def test_the_pgx_drafters_and_fact_passes_are_extended(make_client) -> None:
    async with make_client("extended", offline_settings()) as client:
        names = {t.name for t in await client.list_tools()}
        assert {
            "draft_from_cpic",
            "draft_from_clinpgx",
            "enrich_facts",
            "enrich_literature_pass",
        } <= names


async def test_an_unknown_fact_pass_names_the_valid_ones(make_client, tmp_path) -> None:
    (tmp_path / "module_spec.yaml").write_text("schema_version: '1.0'\n")
    async with make_client("extended", offline_settings()) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool(
                "enrich_facts", {"spec_dir": str(tmp_path), "passes": ["frequences"]}
            )
        message = str(excinfo.value)
        assert "frequences" in message
        for name in ("frequencies", "gene_metrics", "dosage"):
            assert name in message


# --------------------------------------------------------------------------- #
# The registry owns module identity, so a receipt has to survive the session
# --------------------------------------------------------------------------- #
class FakeIdentity:
    canonical_id = "eric-mods/lactose_tolerance@1.0.0"
    namespace = "eric-mods"
    name = "lactose_tolerance"
    version = "1.0.0"
    owner = "eric"


class FakeArtifact:
    digest = "sha256:8173dab7"


class FakeManifest:
    content_signature = "sha256:fb91ffa2"


def test_a_publish_receipt_is_written_beside_the_spec(tmp_path) -> None:
    """The registry stamps identity and overrides anything authored, so it must be kept.

    It cannot go into module_spec.yaml — `module:` is extra="forbid" and these
    exact keys are rejected there because the registry owns them (upstream S1).
    """
    receipt, note = _record_receipt(
        tmp_path,
        target="prod",
        registry_url="https://module-registry.just-dna.life",
        identity=FakeIdentity(),
        artifact=FakeArtifact(),
        manifest=FakeManifest(),
        fallback=("eric-mods", "lactose_tolerance", "1.0.0"),
    )

    path = tmp_path / RECEIPTS_FILE
    assert path.is_file(), "a receipt that does not survive the session is not a record"
    stored = json.loads(path.read_text())
    assert stored == [receipt]
    assert receipt["canonical_id"] == "eric-mods/lactose_tolerance@1.0.0"
    assert receipt["owner"] == "eric"
    assert receipt["artifact_digest"] == "sha256:8173dab7"
    # ISO-8601 UTC, never a naive local timestamp.
    assert receipt["published_at"].endswith("+00:00")
    assert "commit it" in note


def test_a_second_version_appends_rather_than_replacing(tmp_path) -> None:
    for version in ("1.0.0", "1.1.0"):
        _record_receipt(
            tmp_path,
            target="prod",
            registry_url="https://module-registry.just-dna.life",
            identity=None,
            artifact=None,
            manifest=None,
            fallback=("eric-mods", "lactose_tolerance", version),
        )
    stored = json.loads((tmp_path / RECEIPTS_FILE).read_text())
    assert [r["version"] for r in stored] == ["1.0.0", "1.1.0"]


def test_a_republished_version_keeps_the_original_and_reports_the_difference(tmp_path) -> None:
    """A published version is immutable, so a changed digest is a fact, not an update."""
    first, _ = _record_receipt(
        tmp_path,
        target="prod",
        registry_url="https://module-registry.just-dna.life",
        identity=FakeIdentity(),
        artifact=FakeArtifact(),
        manifest=FakeManifest(),
        fallback=("eric-mods", "lactose_tolerance", "1.0.0"),
    )

    class Moved:
        digest = "sha256:deadbeef"

    kept, note = _record_receipt(
        tmp_path,
        target="prod",
        registry_url="https://module-registry.just-dna.life",
        identity=FakeIdentity(),
        artifact=Moved(),
        manifest=FakeManifest(),
        fallback=("eric-mods", "lactose_tolerance", "1.0.0"),
    )

    assert kept == first, "the original receipt must not be overwritten"
    assert "artifact_digest" in note and "immutable" in note
    stored = json.loads((tmp_path / RECEIPTS_FILE).read_text())
    assert len(stored) == 1


# --------------------------------------------------------------------------- #
# The 0.6.2 exception contract (RM101 upstream, S38 in the registry's tree)
# --------------------------------------------------------------------------- #
def _shadowed_except_arms(path):
    """Every `except` clause in `path` that an earlier arm of the same `try` already catches.

    Compares each clause against *earlier arms only*. A parent and its subclass inside
    one tuple is redundant, not dead — every instance is still caught and the arm still
    runs — so reporting that would be crying wolf on working code, which is how a guard
    gets deleted instead of fixed.
    """
    import ast

    tree = ast.parse(path.read_text())
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        seen: list[set[str]] = []
        for handler in node.handlers:
            if handler.type is None:
                names = {"BaseException"}
            elif isinstance(handler.type, ast.Tuple):
                names = {ast.unparse(e) for e in handler.type.elts}
            else:
                names = {ast.unparse(handler.type)}
            for earlier in seen:
                for caught in names:
                    for parent in earlier:
                        if _is_subclass_by_name(caught, parent):
                            findings.append(
                                f"line {handler.lineno}: `except {caught}` is already caught "
                                f"by the earlier `except {parent}`"
                            )
            seen.append(names)
    return findings


def _is_subclass_by_name(child: str, parent: str) -> bool:
    """Resolve two source-level names against the real classes the module imports."""
    from just_module_creator.tools import passes as module

    def resolve(expr: str):
        # `_PASS_UNAVAILABLE[name]` and friends are subscripts, not names — resolve the
        # mapping to the set of classes it can yield, since any of them may be raised.
        table = {"_PASS_UNAVAILABLE": module._PASS_UNAVAILABLE, "_PASS_ERROR": module._PASS_ERROR}
        for key, mapping in table.items():
            if expr.startswith(f"{key}["):
                return tuple(mapping.values())
        obj = getattr(module, expr, None)
        return obj if obj is not None else ()

    kids, parents = resolve(child), resolve(parent)
    kids = kids if isinstance(kids, tuple) else (kids,)
    parents = parents if isinstance(parents, tuple) else (parents,)
    return bool(kids) and bool(parents) and all(
        any(isinstance(k, type) and isinstance(p, type) and issubclass(k, p) for p in parents)
        for k in kids
    )


def test_no_except_arm_is_shadowed_by_an_earlier_one():
    """The 0.6.2 upgrade's silent failure: an outage arm dead behind its own parent.

    Since enricher 0.6.2 every `*Unavailable` is a subclass of the type beside it, so a
    parent-first pair of arms catches every outage in the parent and reports `unreachable`
    as empty on precisely the run where a source was down. Nothing raises and nothing
    fails loudly, which is why this is a structural check rather than a behavioural one.
    """
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "src/just_module_creator/tools/passes.py"
    assert path.is_file()
    assert not _shadowed_except_arms(path)


def test_the_guard_can_actually_report_a_shadowed_arm(tmp_path):
    """A guard reporting zero proves nothing until it is shown able to report one."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        "try:\n    pass\n"
        "except FrequencyEnrichmentError:\n    pass\n"
        "except FrequencyUnavailable:\n    pass\n"
    )
    findings = _shadowed_except_arms(bad)
    assert findings and "FrequencyUnavailable" in findings[0]

    good = tmp_path / "good.py"
    good.write_text(
        "try:\n    pass\n"
        "except FrequencyUnavailable:\n    pass\n"
        "except FrequencyEnrichmentError:\n    pass\n"
    )
    assert not _shadowed_except_arms(good)

    one_tuple = tmp_path / "tuple.py"
    one_tuple.write_text(
        "try:\n    pass\n"
        "except (FrequencyEnrichmentError, FrequencyUnavailable):\n    pass\n"
    )
    assert not _shadowed_except_arms(one_tuple)


async def test_one_sources_outage_does_not_discard_the_other_passes(
    monkeypatch, extended_client, spec_dir
):
    """The bug the per-pass `try` exists for: three sources' work lost to one being down.

    Before this, `enrich_facts` ran the passes inside no `try` at all, so a gnomAD 503
    propagated out of the tool and took `gene_metrics` and `dosage` with it — including
    whatever they had already written. Asserted as a partition: every requested pass ends
    up in exactly one of ran / unreachable / failed.
    """
    from just_dna_enricher.frequencies import FrequencyUnavailable

    from just_module_creator.tools import passes as module

    class Result:
        rows, covered, missing, skipped_offline = [], ["PCSK9"], [], False

    def fake_run_pass(name, target, mode, offline, use):
        if name == "frequencies":
            raise FrequencyUnavailable("gnomAD returned 503")
        return Result()

    monkeypatch.setattr(module, "_run_pass", fake_run_pass)

    result = await extended_client.call_tool(
        "enrich_facts",
        {"spec_dir": str(spec_dir), "use": "unstated", "offline": True},
    )
    data = result.data

    assert data.unreachable == {"frequencies": "gnomAD returned 503"}
    assert data.failed == {}
    # The other two still ran and their findings survived.
    assert sorted(data.passes_run) == ["dosage", "gene_metrics"]
    assert data.covered["gene_metrics"] == ["PCSK9"]
    # A pass that never reached its source did not complete.
    assert data.success is False
    # Partition: nothing is silently dropped.
    requested = {"frequencies", "gene_metrics", "dosage"}
    assert set(data.passes_run) | set(data.unreachable) | set(data.failed) == requested


async def test_an_outage_is_reported_apart_from_a_data_failure(
    monkeypatch, extended_client, spec_dir
):
    """`unreachable` and `failed` answer different questions and must not merge.

    `covered: []` reads identically whether the source had nothing or was never asked,
    which is the whole reason the outage gets its own field rather than a warning line.
    """
    from just_dna_enricher.gene_metrics import GeneMetricsEnrichmentError

    from just_module_creator.tools import passes as module

    def fake_run_pass(name, target, mode, offline, use):
        if name == "gene_metrics":
            raise GeneMetricsEnrichmentError("gene_metrics.csv will not parse")
        raise AssertionError("only gene_metrics was requested")

    monkeypatch.setattr(module, "_run_pass", fake_run_pass)

    result = await extended_client.call_tool(
        "enrich_facts",
        {"spec_dir": str(spec_dir), "use": "unstated", "passes": ["gene_metrics"]},
    )
    data = result.data

    assert data.failed == {"gene_metrics": "gene_metrics.csv will not parse"}
    assert data.unreachable == {}
    assert data.passes_run == []
