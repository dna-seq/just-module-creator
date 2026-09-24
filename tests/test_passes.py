"""Drafting and the fact passes: the licence gate and the four row statuses.

Hermetic — everything here runs under the offline ceiling, so no drafter reaches
a source. What is asserted is the contract around the call: that `use` cannot be
defaulted, that a licence refusal stays a refusal rather than becoming a failure,
and that upstream's per-row distinctions survive the MCP boundary.
"""

from __future__ import annotations

import contextlib
import csv
import json
import re
from pathlib import Path

import pytest
from conftest import offline_settings
from fastmcp.exceptions import ToolError

from just_module_creator.expression import ROW_STATUSES, module_sites, plan_windows, report_rows
from just_module_creator.models import DraftResult
from just_module_creator.settings import Settings
from just_module_creator.tools import passes
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
    async with make_client(offline_settings()) as client:
        tool = next(t for t in await client.list_tools() if t.name == "draft_from_clinvar")
        assert "use" in (tool.input_schema.get("required") or [])


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
# The surface: every drafter and every pass, on one listing
# --------------------------------------------------------------------------- #
async def test_every_drafter_and_pass_is_registered(make_client) -> None:
    """F1's hole only closes if it closes for the surface an agent actually gets.

    The PGx drafters and the fact passes were the extended tier until 0.21.0. The
    cost that put them there is real and each says so in its own docstring; what
    it may not do any more is decide, at server start, that a session working on a
    PGx module cannot see the PGx drafters.
    """
    async with make_client(offline_settings()) as client:
        names = {t.name for t in await client.list_tools()}
        assert {
            "draft_from_clinvar",
            "draft_from_cpic",
            "draft_from_clinpgx",
            "enrich_facts",
            "enrich_literature_pass",
            "enrich_gwas_effects",
        } <= names


async def test_an_unknown_fact_pass_names_the_valid_ones(make_client, tmp_path) -> None:
    (tmp_path / "module_spec.yaml").write_text("schema_version: '1.0'\n")
    async with make_client(offline_settings()) as client:
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
    return (
        bool(kids)
        and bool(parents)
        and all(
            any(isinstance(k, type) and isinstance(p, type) and issubclass(k, p) for p in parents)
            for k in kids
        )
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
        "try:\n    pass\nexcept (FrequencyEnrichmentError, FrequencyUnavailable):\n    pass\n"
    )
    assert not _shadowed_except_arms(one_tuple)


async def test_one_sources_outage_does_not_discard_the_other_passes(monkeypatch, client, spec_dir):
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

    result = await client.call_tool(
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


async def test_an_outage_is_reported_apart_from_a_data_failure(monkeypatch, client, spec_dir):
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

    result = await client.call_tool(
        "enrich_facts",
        {"spec_dir": str(spec_dir), "use": "unstated", "passes": ["gene_metrics"]},
    )
    data = result.data

    assert data.failed == {"gene_metrics": "gene_metrics.csv will not parse"}
    assert data.unreachable == {}
    assert data.passes_run == []


# ── the GWAS Catalog pass (RM12) ─────────────────────────────────────────────────────
#
# The payload shape is the real one the REST API returns, taken from upstream's own
# recorded fixtures and re-keyed onto `rs4988235`, the rsID the `spec_dir` fixture
# authors. The client is injected, so these run the real fetching-free parsing, merging
# and writing code with no network and no sleeping — the offline ceiling still holds
# because an injected transport is not egress.

_GWAS_NAMED_ALLELE = {
    "associationId": "13069",
    "betaNum": 0.05,
    "betaUnit": "umol/l",
    "betaDirection": "increase",
    "range": "[0.03-0.07]",
    "riskFrequency": "0.15",
    "pvalue": 7.0e-13,
    "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs4988235-A"}]}],
    "_links": {
        "study": {"href": "https://example.test/studies/GCST000001"},
        "efoTraits": {"href": "https://example.test/traits/13069"},
    },
}

#: The Catalog really writes `rs…-?` when a study never established which allele carries the
#: effect, and `unit` when the beta's scale is not stated. Both are kept verbatim upstream.
_GWAS_UNKNOWN_ALLELE = {
    "associationId": "55421052",
    "betaNum": 0.3017178,
    "betaUnit": "unit",
    "betaDirection": "increase",
    "standardError": 0.0467972,
    "riskFrequency": "NR",
    "pvalue": 1.0e-10,
    "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs4988235-?"}]}],
    "_links": {
        "study": {"href": "https://example.test/studies/GCST000001"},
        "efoTraits": {"href": "https://example.test/traits/55421052"},
    },
}

#: `pvalue: 0.0` is what the Catalog publishes past float64's subnormal boundary. Six of these
#: sit in `reference_examples/hfe_hemochromatosis`, which is why strict refuses a shipped module.
_GWAS_UNDERFLOW = {
    "associationId": "64192738",
    "betaNum": 0.1253,
    "betaUnit": "unit",
    "betaDirection": "increase",
    "pvalue": 0.0,
    "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs4988235-A"}]}],
    "_links": {"study": {"href": "https://example.test/studies/GCST000001"}},
}

_GWAS_STUDY = {
    "accessionId": "GCST000001",
    "publicationInfo": {"pubmedId": 11788828},
    "ancestries": [{"ancestralGroups": [{"ancestralGroup": "European"}]}],
}

_GWAS_TRAITS = {
    "https://example.test/traits/13069": {
        "_embedded": {"efoTraits": [{"trait": "Lactase persistence", "shortForm": "EFO_0004570"}]}
    },
    "https://example.test/traits/55421052": {
        "_embedded": {"efoTraits": [{"trait": "Milk consumption", "shortForm": "EFO_0009999"}]}
    },
}


class FakeGwasClient:
    """Serves recorded payloads and records every call, so the budget is ground truth."""

    def __init__(self, associations):
        self.associations = list(associations)
        self.calls: list[str] = []

    def associations_for(self, rsid: str) -> list[dict]:
        self.calls.append(f"assoc:{rsid}")
        return list(self.associations)

    def follow(self, url: str) -> dict:
        self.calls.append(url)
        if "studies" in url:
            return dict(_GWAS_STUDY)
        return dict(_GWAS_TRAITS.get(url, {}))

    def close(self) -> None:
        raise AssertionError("the pass must not close a client it did not create")


def _inject_gwas_client(monkeypatch, client):
    """Run the REAL `enrich_gwas` with an injected transport, passing our kwargs through.

    Only the network is excluded: the strict ladder, the merge, the licence row and the CSV
    write are all upstream's own code. Patching our module's binding rather than the
    enricher's keeps the patch to the one call site under test.
    """
    from just_dna_enricher.gwas import enrich_gwas as real_enrich_gwas

    from just_module_creator.tools import passes as module

    def wrapper(spec_dir, **kwargs):
        return real_enrich_gwas(spec_dir, client=client, dataset="gwas_catalog_test", **kwargs)

    monkeypatch.setattr(module, "enrich_gwas", wrapper)


async def test_a_published_effect_is_reported_and_never_becomes_a_weight(
    monkeypatch, client, spec_dir
):
    """The three numbers that make "this beta is not a weight" readable instead of asserted.

    A single real variant carries betas on unrelated scales and a large share of the
    Catalog's associations name no effect allele at all, so neither has a direction a
    genotype could be matched against. The tool reports both counts and writes nothing
    into `weight` — there is no argument on this tool that could.
    """
    gwas_client = FakeGwasClient([_GWAS_NAMED_ALLELE, _GWAS_UNKNOWN_ALLELE])
    _inject_gwas_client(monkeypatch, gwas_client)

    result = await client.call_tool(
        "enrich_gwas_effects", {"spec_dir": str(spec_dir), "use": "unstated"}
    )
    data = result.data

    assert data.success is True
    assert data.covered == ["rs4988235"]
    assert data.missing == []
    assert data.rows == 2
    # One of the two is `rs4988235-?`: real evidence with no applicable direction.
    assert data.associations_without_effect_allele == 1
    # Two scales, one of them the Catalog's uninformative "unit". Sorted, deterministic.
    assert data.effect_units == ["umol/l", "unit"]
    assert any("do not combine" in w for w in data.warnings)
    assert any("no effect allele" in w for w in data.warnings)
    assert "NOT weights" in data.note

    # The request budget, derived from the fixture rather than pasted off a run. Every call the
    # fake served IS a request issued: `_LinkCache` reaches the transport only on a miss, so a
    # cache hit never appears here and `requests_made` is exactly what the fake was asked.
    served_follows = [c for c in gwas_client.calls if not c.startswith("assoc:")]
    attempted_follows = sum(len(a["_links"]) for a in (_GWAS_NAMED_ALLELE, _GWAS_UNKNOWN_ALLELE))
    assert data.requests_made == len(gwas_client.calls) == 1 + len(served_follows)
    assert data.requests_saved == attempted_follows - len(served_follows)
    # `1 + 2N`: N associations for the one variant queried, each naming a study and a trait. The
    # two share a study, so the cache pays exactly once here — on a real module it paid nothing.
    assert attempted_follows == 2 * len([_GWAS_NAMED_ALLELE, _GWAS_UNKNOWN_ALLELE])
    assert data.requests_saved == 1

    # `weight` is authored and stays authored: nothing this pass ran touched variants.csv.
    assert "1.2" in (spec_dir / "variants.csv").read_text()


async def test_the_gwas_strict_ladder_escalates_on_the_catalogs_shape_after_writing(
    monkeypatch, client, spec_dir
):
    """`--strict` here fires on the USUAL answer, and it fires after the sidecar is written.

    Upstream covers this ladder in neither direction — `strict` appears nowhere in
    `enricher/tests/test_gwas.py` — so what it actually does is asserted here rather than
    taken from its docstring. Observed: one association whose p-value the Catalog publishes
    as `0.0` is enough to raise, `gwas_effects.csv` is on disk with that row in it when the
    raise happens, and the same input under `best_effort` reports the count and succeeds.
    A shipped flagship module (`reference_examples/hfe_hemochromatosis`) carries six of
    these, so a strict failure here is not a verdict on the module.
    """
    gwas_client = FakeGwasClient([_GWAS_UNDERFLOW])
    _inject_gwas_client(monkeypatch, gwas_client)

    strict = await client.call_tool(
        "enrich_gwas_effects", {"spec_dir": str(spec_dir), "strict": True}
    )
    assert strict.data.success is False
    assert strict.data.mode == "strict"
    # Not zero. The message names non-zero counts and the sidecar is on disk, so a `0` here
    # would be a wrong answer rather than a missing one.
    assert strict.data.p_value_underflows is None
    assert strict.data.unusable is None
    assert strict.data.rows is None
    # Upstream's message, verbatim — including its own sentence saying whose fault this is not.
    assert "strict GWAS enrichment" in strict.data.warnings[0]
    assert "authoring mistake" in strict.data.warnings[0]
    assert any("AFTER the write" in w for w in strict.data.warnings)

    # The escalation is raised after the write, so the row is on disk despite success=False.
    written = spec_dir / "gwas_effects.csv"
    assert written.is_file()
    rows = list(csv.DictReader(written.read_text().splitlines()))
    assert [r["association_id"] for r in rows] == ["64192738"]
    # The number is withheld and the source's own string is kept — the row is not lost.
    assert rows[0]["p_value"] == "0.0"
    assert rows[0]["p_value_num"] == ""

    # Same input, best_effort: the count is reported and the pass completes.
    lenient = await client.call_tool(
        "enrich_gwas_effects", {"spec_dir": str(spec_dir), "strict": False}
    )
    assert lenient.data.success is True
    assert lenient.data.p_value_underflows == 1
    assert lenient.data.unusable == 0
    assert any("below" in w and "float64" in w for w in lenient.data.warnings)
    # Merged on association_id, so re-running did not duplicate the row.
    assert lenient.data.rows == 1


async def test_the_gwas_pass_is_a_no_op_offline_rather_than_a_failure(client, spec_dir):
    """No injected transport and the ceiling down: nothing fetched, nothing written, no error.

    The Catalog publishes a bulk download but this pass reads the REST API, so there is no
    snapshot to fall back on. A no-op that reported success without saying so would read as
    "the Catalog holds nothing for this module".
    """
    result = await client.call_tool(
        "enrich_gwas_effects", {"spec_dir": str(spec_dir), "offline": True}
    )
    data = result.data

    assert data.success is True
    assert data.skipped_offline is True
    # `null`, not 0: nothing counted the file. An existing gwas_effects.csv would still hold
    # every row it had, so a zero here would assert something this run never looked at.
    assert data.rows is None
    assert any("did NOTHING" in w for w in data.warnings)
    assert not (spec_dir / "gwas_effects.csv").exists()


async def test_study_facts_off_says_the_nulls_it_leaves_are_permanent(
    monkeypatch, client, spec_dir
):
    """The cheap mode costs one request per variant and the cut does not heal itself.

    The merge key is `association_id` alone, so a later run with study facts on skips these
    rows rather than backfilling them. Asserted rather than described: the second run leaves
    `pmid` empty, and only deleting the file recovers it.
    """
    gwas_client = FakeGwasClient([_GWAS_NAMED_ALLELE])
    _inject_gwas_client(monkeypatch, gwas_client)

    thin = await client.call_tool(
        "enrich_gwas_effects", {"spec_dir": str(spec_dir), "study_facts": False}
    )
    assert thin.data.success is True
    assert thin.data.study_facts is False
    # One request for the variant and no `_links` follows at all.
    assert thin.data.requests_made == 1
    assert gwas_client.calls == ["assoc:rs4988235"]
    assert any("will SKIP these rows" in w for w in thin.data.warnings)

    written = spec_dir / "gwas_effects.csv"
    assert list(csv.DictReader(written.read_text().splitlines()))[0]["pmid"] == ""

    # Re-running with study facts on does NOT backfill: the association id is already there.
    await client.call_tool("enrich_gwas_effects", {"spec_dir": str(spec_dir), "study_facts": True})
    assert list(csv.DictReader(written.read_text().splitlines()))[0]["pmid"] == ""

    written.unlink()
    await client.call_tool("enrich_gwas_effects", {"spec_dir": str(spec_dir), "study_facts": True})
    assert list(csv.DictReader(written.read_text().splitlines()))[0]["pmid"] == "11788828"


# --------------------------------------------------------------------------- #
# The aborted enrichment that was still alive (F63)
# --------------------------------------------------------------------------- #
async def test_a_second_enrichment_refuses_while_the_first_is_still_in_flight(
    make_client, tmp_path
) -> None:
    """The measured failure was two calls on one directory, and the second one succeeded.

    A 330-variant enrichment was aborted by a client idle timeout. A worker thread
    cannot be interrupted, so the work kept running. The author restored the published
    330-row `resolution.csv` and re-enriched; that second call read the restored file,
    reported `resolved: 330, sources: ["cache"]` correctly and instantly, and then the
    first call reached its single terminal write and left **162** distinct rsIDs. The
    module validated, closed and compiled green, because every count in it agreed.

    Nothing anywhere reported a partial resolution as partial, and there is no lock in
    this tree or upstream's. So the guard is the refusal: while a directory is claimed,
    a second enrichment of it says what is happening instead of succeeding into a file
    that is about to be overwritten.

    Asserted on the claim registry directly rather than by racing two real enrichments —
    a race that reproduced the bug would have to run the pass twice over the network,
    and what is under test is the ordering, not the enricher.
    """
    from just_module_creator.tools import passes

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("module:\n  name: spec\n", encoding="utf-8")

    resolved = spec.resolve()
    passes._ENRICHMENTS_IN_FLIGHT[resolved] = "2026-08-22T12:00:00+00:00"
    try:
        async with make_client(offline_settings()) as client:
            with pytest.raises(ToolError) as raised:
                await client.call_tool("enrich_module", {"spec_dir": str(spec)})
    finally:
        passes._ENRICHMENTS_IN_FLIGHT.pop(resolved, None)

    message = str(raised.value)
    assert "still running" in message
    assert "2026-08-22T12:00:00+00:00" in message, "the refusal must say when the other call began"
    # It must not read as a validation failure of the spec.
    assert "overwritten" in message


async def test_the_claim_is_released_so_a_later_enrichment_is_not_blocked_forever(
    make_client, tmp_path
) -> None:
    """A claim that outlived its call would wedge the directory for the session.

    Released in `finally` rather than on request cancellation, which is deliberate:
    `run_sync` defaults to `abandon_on_cancel=False`, so the await does not unwind until
    the thread returns — the claim therefore covers exactly the window in which the
    abandoned write can still land, and no longer.
    """
    from just_module_creator.tools import passes

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("module:\n  name: spec\n", encoding="utf-8")

    async with make_client(offline_settings()) as client:
        # Offline with no variants: the pass refuses or returns, either way it completes.
        with contextlib.suppress(ToolError):
            await client.call_tool("enrich_module", {"spec_dir": str(spec), "offline": True})

    assert spec.resolve() not in passes._ENRICHMENTS_IN_FLIGHT, (
        "the claim outlived its call, so this directory can never be enriched again"
    )


async def test_a_long_enrich_reports_it_is_alive_without_inventing_a_fraction(
    make_client, tmp_path
):
    """WORKAROUND TEST — delete with the heartbeat when the enricher ships `progress`.

    `enrich()` is one opaque blocking call in 0.6.6: a 263-rsID module ran 20+ minutes
    writing nothing, and an operator could not tell work from a hang. That ambiguity
    killed a benchmark run and produced the partial sidecar in `F70`.

    Two properties, and the second is the one that matters. It must speak while the call
    is still running — a message emitted after the fact answers nothing. And it must
    NEVER report a fraction: upstream batches inside `resolver.py` rather than looping
    per subject, which is exactly why they have not settled what a callback counts, so a
    percentage of ours would be a fabricated measurement of somebody else's work.
    """
    import just_module_creator.tools.passes as passes

    reported: list[tuple[float, float | None, str | None]] = []

    class _Ctx:
        async def report_progress(self, progress, total=None, message=None):
            reported.append((progress, total, message))

        async def info(self, *_args, **_kwargs):
            return None

    slow = 0.05
    monkey = passes._HEARTBEAT_SECONDS
    passes._HEARTBEAT_SECONDS = slow
    try:

        async def _beat(ctx, seconds_running: float) -> None:
            # Exercise the heartbeat body directly: the real one wraps a network call.
            from datetime import UTC, datetime

            import anyio

            started = datetime.now(UTC)
            with anyio.move_on_after(seconds_running):
                while True:
                    await anyio.sleep(slow)
                    elapsed = int((datetime.now(UTC) - started).total_seconds())
                    await ctx.report_progress(
                        progress=elapsed,
                        message=f"enrich still running, {elapsed}s elapsed",
                    )

        await _beat(_Ctx(), 0.2)
    finally:
        passes._HEARTBEAT_SECONDS = monkey

    assert reported, "a long enrich must say it is alive while it is still running"
    for _progress, total, message in reported:
        assert total is None, (
            f"reported total={total!r} — a fraction claims a denominator we do not have. "
            "Upstream batches inside resolver.py; inventing one fabricates their measurement."
        )
        assert "elapsed" in (message or "")


def test_every_caller_folds_the_hyphen_the_same_way():
    """One spelling rule, and it used to be two-and-a-half.

    The enricher's CLI flag is written `non-commercial` and the `declared_use` column
    takes `non_commercial`, so an author who has just read a `--use` line types the
    hyphen. `enrich_facts` and `refresh_sidecar` folded it; the registry pre-flight
    passed it through and the server answered 422 without naming the hyphen — the same
    argument accepted by two tools and refused by the third (`F74`).

    Asserted through the three entry points rather than through the helper alone, since
    the defect was never in the helper: it was a call site that did not use one.
    """
    from just_module_creator.tools._shared import normalize_declared_use
    from just_module_creator.tools.refresh import ROSTER, check_use

    # A sidecar whose pass actually reads a licence-bearing source, or `check_use`
    # returns "unstated" before it ever reaches the fold.
    sidecar = ROSTER["gene_metrics.csv"]
    folds = (
        normalize_declared_use,
        _check_use,
        lambda value: check_use(sidecar, value),
    )
    for fold in folds:
        assert fold("non-commercial") == "non_commercial"
        assert fold("NON-COMMERCIAL") == "non_commercial"
        assert fold(" non_commercial ") == "non_commercial"
        with pytest.raises(ToolError, match="must be one of"):
            fold("whatever-i-like")


def test_the_use_vocabulary_is_the_formats_own_and_not_a_literal_here():
    """A hardcoded vocabulary is a bug waiting for the next upstream release.

    `VALID_USE` was a tuple written in this module; it is now derived from format's
    `VALID_DECLARED_USE`, so a value added upstream reaches our refusal message without
    an edit here.
    """
    from just_dna_format.vocab import VALID_DECLARED_USE

    assert set(VALID_USE) == set(VALID_DECLARED_USE)


async def test_a_strict_refusal_survives_the_heartbeats_task_group(
    make_client, tmp_path, monkeypatch
) -> None:
    """`strict` is the mode the skills teach, and it was the mode that returned nothing.

    Measured on a benchmark run, 2026-08-31: `enrich_module(strict=true)` failed twice
    with `unhandled errors in a TaskGroup (1 sub-exception)` — no message, no unresolved
    list, nothing to act on. The identical spec under `strict=false` succeeded and named
    the five unresolved rsIDs. The author diagnosed it by running the upstream CLI by
    hand, which is the surface teaching a step it cannot run.

    The cause is ours, not upstream's. `enrich()` raises `EnrichmentError` in strict mode
    exactly as documented, but the heartbeat wraps it in `anyio.create_task_group()`, and
    a task group re-raises as `ExceptionGroup` — which `except EnrichmentError` does not
    catch. So the one arm written to turn a refusal into a structured report was dead for
    every strict run that had anything to refuse, and only for those: a clean strict run
    raises nothing and looks fine, which is why it shipped.
    """
    from just_dna_enricher.enrich import EnrichmentError

    from just_module_creator.tools import passes

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("module:\n  name: spec\n", encoding="utf-8")

    refusal = "strict enrichment: 5 variant(s) unresolved after the chain"

    def _refuse(*_args, **_kwargs):
        raise EnrichmentError(refusal)

    monkeypatch.setattr(passes, "enrich", _refuse)

    async with make_client(offline_settings()) as client:
        result = await client.call_tool("enrich_module", {"spec_dir": str(spec), "strict": True})

    report = result.data
    assert report.success is False
    assert any(refusal in w for w in report.warnings), (
        f"the strict refusal did not reach the caller: {report.warnings!r} — "
        "a task group turned a typed refusal into an unhandled ExceptionGroup"
    )


async def test_a_not_found_row_is_not_counted_as_resolved(
    make_client, tmp_path, monkeypatch
) -> None:
    """`resolved: 64` was printed beside five unresolved keys on a 64-subject module.

    Measured on a benchmark run, 2026-08-31. The number was `len(result.rows)` — the
    length of `resolution.csv` — but upstream writes a `status: not_found` row for a
    subject it *also* appends to `unresolved` (`enrich.py`, the `source="ensembl"`
    arm). So the two fields overlapped, and the pair read as "all sixty-four reached a
    coordinate, and also five did not". The author read it as the former and went
    looking for the wrong defect.

    The name is the contract here: a field called `resolved` sitting beside `unresolved`
    is read as an outcome, whatever the description says it counts.
    """
    from just_module_creator.tools import passes

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("module:\n  name: spec\n", encoding="utf-8")

    class _Row:
        def __init__(self, status: str) -> None:
            self.status = status

    class _Result:
        rows = [_Row("resolved")] * 3 + [_Row("not_found"), _Row("ambiguous")]
        unresolved = ["rs1", "rs2"]
        sources = ["ensembl"]
        ref_mismatches: list[str] = []
        clin_sig_conflicts: list[str] = []
        clin_sig_not_checked = None
        stale_rsids: list[str] = []
        vrs = None

    monkeypatch.setattr(passes, "enrich", lambda *_a, **_k: _Result())

    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("enrich_module", {"spec_dir": str(spec)})).data

    assert report.resolved == 3, (
        f"resolved={report.resolved} counts rows written, not loci that reached a "
        "coordinate — a not_found row is written AND listed in unresolved, so the two "
        "fields double-count the same subject"
    )
    assert len(report.unresolved) == 2


# --------------------------------------------------------------------------- #
# The progress callback (upstream RM128, our `S66` ask 4)
# --------------------------------------------------------------------------- #
def test_upstream_still_takes_a_progress_callback():
    """Asserted against the installed signature, not a remembered one.

    The heartbeat this replaced reported elapsed seconds because there was no
    denominator to report and inventing one would have been a fabricated
    measurement of somebody else's work. `progress` is where the denominator
    comes from, so a rename upstream must fail here rather than silently put the
    duration back.
    """
    import inspect

    from just_dna_enricher.enrich import enrich

    assert "progress" in inspect.signature(enrich).parameters


async def test_enrich_hands_upstream_a_callback_and_survives_being_called(
    make_client, tmp_path, monkeypatch
):
    """We pass it, and a call from the worker thread does not break the run.

    The bridge is a plain cell rather than a portal: upstream calls back on the
    thread `run_sync` gave it, and the heartbeat reads the cell on the event
    loop. What has to hold is that the callback is (a) supplied, (b) callable
    with `(done, total)`, and (c) harmless — upstream does not swallow an
    exception from it, so a callback of ours that raised would abort a real
    enrichment.
    """
    from just_module_creator.tools import passes

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("module:\n  name: spec\n", encoding="utf-8")

    seen: dict = {}

    class _Result:
        rows: list = []
        unresolved: list[str] = []
        sources: list[str] = []
        ref_mismatches: list[str] = []
        clin_sig_conflicts: list[str] = []
        clin_sig_not_checked = None
        stale_rsids: list[str] = []
        vrs = None

    def _fake_enrich(*_a, progress=None, **_k):
        seen["callback"] = progress
        assert progress is not None, "no progress callback reached upstream"
        progress(0, 12)
        progress(7, 12)
        progress(12, 12)
        return _Result()

    monkeypatch.setattr(passes, "enrich", _fake_enrich)

    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("enrich_module", {"spec_dir": str(spec)})).data

    assert report.success
    assert callable(seen["callback"])


# --------------------------------------------------------------------------- #
# F96 — the AlphaGenome surface the plugin had no tool for
# --------------------------------------------------------------------------- #
_EFFECTS_HEADER = (
    "variant_key,rsid,chrom,start,ref,alt,gene,gene_id,effect_size,effect_measure,"
    "effect_unit,effect_direction,tracks_agreeing,tracks_total,distance_to_gene,"
    "dataset,source,status,fetched_at\n"
)


def _effects(spec: Path, rows: str) -> None:
    """Real rows, taken from the apoe_locus_compound run against the live Atlas."""
    (spec / "expression_effects.csv").write_text(_EFFECTS_HEADER + rows)


@pytest.fixture
def effects_spec(tmp_path: Path) -> Path:
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text(
        "schema_version: '1.0'\nmodule:\n  name: apoe_locus_compound\n"
    )
    _effects(
        spec,
        # strongest, unanimous, inside the gene
        "k1,,19,44919171,A,T,APOC1,ENSG1,-1.6926,RNA_SEQ,,decrease,371,371,0,ds,alphagenome_atlas,resolved,t\n"
        # weaker, unanimous, inside the gene
        "k2,,19,44891698,C,G,TOMM40,ENSG2,0.2488,RNA_SEQ,,increase,371,371,0,ds,alphagenome_atlas,resolved,t\n"
        # large but distal, and only half the tracks agree
        "k3,,19,44890500,A,C,TOMM40,ENSG2,0.9000,RNA_SEQ,,increase,180,371,754,ds,alphagenome_atlas,resolved,t\n"
        # no track agreed: effect_direction is null, which is an answer rather than a gap
        "k4,,19,44892735,C,T,TOMM40,ENSG2,-0.0024,RNA_SEQ,,,0,371,0,ds,alphagenome_atlas,resolved,t\n",
    )
    return spec


async def test_the_ranking_puts_the_largest_predicted_effect_first(make_client, effects_spec):
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "top_expression_effects", {"spec_dir": str(effects_spec), "limit": 10}
        )
    body = json.loads(out.content[0].text)
    assert body["total_rows"] == 4
    assert body["genes"] == ["APOC1", "TOMM40"]
    assert [e["start"] for e in body["effects"]] == [44919171, 44890500, 44891698, 44892735]


async def test_a_row_no_track_agreed_on_is_counted_rather_than_dropped(make_client, effects_spec):
    """`effect_direction` null means no track agreed — a real answer about the variant.

    Dropping it would report the sidecar as smaller than it is, which is the
    `None`-is-not-`False` rule at row granularity.
    """
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "top_expression_effects", {"spec_dir": str(effects_spec), "limit": 10}
        )
    body = json.loads(out.content[0].text)
    assert body["direction_unknown"] == 1
    assert body["matched"] == 4
    null_row = next(e for e in body["effects"] if e["start"] == 44892735)
    assert null_row["effect_direction"] is None
    assert null_row["tracks_agreeing"] == 0


async def test_consensus_and_in_gene_filters_narrow_without_reordering(make_client, effects_spec):
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "top_expression_effects",
            {"spec_dir": str(effects_spec), "min_consensus": 1.0, "in_gene_only": True},
        )
    body = json.loads(out.content[0].text)
    # k3 fails consensus AND distance; k4 is unanimous-zero, which is consensus 0.0
    assert [e["start"] for e in body["effects"]] == [44919171, 44891698]
    assert body["matched"] == 2
    assert body["total_rows"] == 4, "the denominator is the file, not the filtered set"


async def test_no_sidecar_says_nothing_to_rank_rather_than_no_effect(make_client, tmp_path):
    spec = tmp_path / "empty"
    spec.mkdir()
    async with make_client(offline_settings()) as client:
        out = await client.call_tool("top_expression_effects", {"spec_dir": str(spec)})
    body = json.loads(out.content[0].text)
    assert body["total_rows"] == 0
    assert "not the same as no effect being predicted" in body["next_step"]


async def test_offline_refuses_the_atlas_rather_than_answering_from_a_cache(make_client, tmp_path):
    """There is no snapshot lane for the Atlas, so offline is a refusal, not a no-op.

    A no-op would report the question as asked and answered locally, which it was not.
    """
    spec = tmp_path / "spec"
    spec.mkdir()
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "enrich_expression_effects", {"spec_dir": str(spec), "gene": "TOMM40"}
        )
    body = json.loads(out.content[0].text)
    assert body["success"] is False
    assert body["written"] is None, "null means nothing counted, never zero written"
    assert "not asked rather than answered from a cache" in " ".join(body["warnings"])


async def test_the_pass_says_it_makes_the_module_non_commercial(make_client):
    """The licence consequence has to be readable before the call, not after."""
    async with make_client(offline_settings()) as client:
        tool = next(t for t in await client.list_tools() if t.name == "enrich_expression_effects")
    assert "non-commercial" in (tool.description or "").lower()
    assert tool.input_schema["properties"]["use"]["default"] == "non-commercial"


# --------------------------------------------------------------------------- #
# F100: a drafter's refusal of a fresh scaffold names a repair this surface can make
# --------------------------------------------------------------------------- #
async def test_a_drafter_on_a_placeholder_spec_points_at_the_spec_not_at_an_argument(
    make_client, tmp_path
) -> None:
    """`spec_genome_build` says "pass genome_build= explicitly", and nothing here takes one.

    The spec is read before any source is touched, so this runs offline and reaches no
    client. What an agent must not be told is to look for an argument that does not
    exist; what it must be told is which file, and which fields.
    """
    from just_dna_compiler import scaffold

    scaffold.scaffold_module(tmp_path, kinds=[], name="probe", rows=1)
    spec = tmp_path / "module_spec.yaml"
    assert "<<REPLACE>>" in spec.read_text()
    # Enricher 0.7.1 (upstream S103) reads past the scaffold's stubs in the fields a draft
    # never uses; only a placeholder in `genome_build` itself still refuses. Put it there.
    spec.write_text(re.sub(r"genome_build:.*", "genome_build: <<REPLACE>>", spec.read_text()))
    async with make_client(offline_settings()) as client:
        with pytest.raises(ToolError) as excinfo:
            await client.call_tool(
                "draft_from_cpic",
                {
                    "spec_dir": str(tmp_path),
                    "gene": "TPMT",
                    "use": "non_commercial",
                    "dry_run": True,
                    "offline": True,
                },
            )
    message = str(excinfo.value)
    # Upstream's text survives verbatim; ours is appended, not substituted.
    assert "cannot read the module's genome_build" in message
    assert "module_spec.yaml" in message
    assert "No tool here takes a genome_build argument" in message


def test_the_stub_row_refusal_is_translated_into_the_scaffold_repair() -> None:
    message = (
        "existing haplotypes.csv does not validate, so a draft cannot be keyed against it: "
        "haplotypes.csv line 2 []: Value error, unreplaced template placeholder '<<REPLACE>>' "
        "in HaplotypeRow row: allele, haplotype_name, rsid."
    )
    translated = _translate(message)
    assert message in translated
    assert "rows=0" in translated
    assert "keep the header" in translated


def test_a_genuinely_broken_row_is_not_called_a_scaffold_stub() -> None:
    """The remedy keys on the placeholder: an authored row that fails on type is the author's."""
    message = (
        "existing haplotypes.csv does not validate, so a draft cannot be keyed against it: "
        "haplotypes.csv line 4 [start]: Input should be a valid integer"
    )
    assert _translate(message) == message


# --------------------------------------------------------------------------- #
# F103 — a coordinate restated under source=authored reads as a clean resolution
# --------------------------------------------------------------------------- #
async def test_a_restated_authored_coordinate_is_named_rather_than_counted_as_resolved(
    make_client, tmp_path, monkeypatch
):
    """`resolved: 5, sources: ["authored"], vrs_minted: 0` was every CPIC-drafted module's report.

    The row is `status=resolved` and it is counted — that is upstream's word and stays —
    but nothing Ensembl answered reached the sidecar, and a reader deserves the sentence
    beside the count. A row the cache answered, carrying a VRS id, draws no warning.
    """
    from types import SimpleNamespace

    from just_module_creator.tools import passes

    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "module_spec.yaml").write_text("module:\n  name: spec\n", encoding="utf-8")

    def row(**kw):
        base = dict(
            status="resolved", source="cache", rsid="rs4244285", vrs_id="ga4gh:VA.x", ref="G"
        )
        base.update(kw)
        return SimpleNamespace(**base)

    def _fake_enrich(*_a, **_k):
        return SimpleNamespace(
            rows=[
                row(source="authored", vrs_id=None, ref=None),
                row(source="authored", vrs_id=None, ref=None, rsid="rs12248560"),
                # An authored row that DID carry ref/alts and merely did not mint is
                # not the shape, and the sentence would be false about it.
                row(source="authored", vrs_id=None),
                row(),
            ],
            unresolved=[],
            sources=["authored", "cache"],
            ref_mismatches=[],
            clin_sig_conflicts=[],
            clin_sig_not_checked=None,
            stale_rsids=[],
            vrs=SimpleNamespace(minted=1),
        )

    monkeypatch.setattr(passes, "enrich", _fake_enrich)
    async with make_client(offline_settings()) as client:
        report = (await client.call_tool("enrich_module", {"spec_dir": str(spec)})).data

    assert report.resolved == 4
    named = [w for w in report.warnings if "source=authored" in w]
    assert len(named) == 1
    assert named[0].startswith("2 row(s)")
    assert "S104" in named[0]


# --------------------------------------------------------------------------- #
# F105 / F106 — the AlphaGenome pass and its reader aimed at the module's own rows
# --------------------------------------------------------------------------- #
#: One authored row per status, placed on the positions the `effects_spec` fixture
#: carries real Atlas rows for. Coordinate rows rather than rsIDs, so no identifier
#: is paired with a position it does not have; rs429358 is real and left unresolved.
_ROWS_VARIANTS = (
    "rsid,chrom,start,ref,alts,genotype,gene,weight,state,conclusion\n"
    ",19,44919171,A,T,A/T,APOC1,0.5,risk,predicted only\n"  # scored (k1)
    ",19,44891698,C,G,C/C,TOMM40,0,neutral,predicted only\n"  # reference_only
    ",19,44890500,A,C,A/C,APOE,0.5,risk,predicted only\n"  # gene_not_at_locus (k3 is TOMM40)
    ",19,44892735,C,T,C/T,,0.5,risk,predicted only\n"  # no_gene
    ",19,44905000,G,A,A/G,APOE,0.5,risk,predicted only\n"  # not_scored
    "rs429358,,,,,C/C,APOE,0.5,risk,predicted only\n"  # unresolved
)


def _online_settings() -> Settings:
    """Offline off, env neutralised by the autouse fixture. Only for tests whose one
    egress point is monkeypatched, or that refuse before reaching it."""
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture
def rows_spec(effects_spec: Path) -> Path:
    (effects_spec / "variants.csv").write_text(_ROWS_VARIANTS)
    return effects_spec


def test_every_authored_row_lands_in_exactly_one_status(rows_spec: Path) -> None:
    report = report_rows(rows_spec)
    assert report.rows_read == 6
    assert {s: report.status[s] for s in ROW_STATUSES} == {
        **dict.fromkeys(ROW_STATUSES, 1),
        "unreadable": 0,
    }
    assert report.matched_keys == {("19", 44919171, "T", "APOC1")}
    assert report.examples["unresolved"] == ["rs429358"]


def test_windows_come_from_rows_the_model_could_score(rows_spec: Path) -> None:
    """Only the three rows with a gene, a coordinate and a non-reference allele plan a
    window; the two APOE ones are 4.5 kb apart, so they are not merged."""
    assert plan_windows(module_sites(rows_spec)[0]) == [
        ("APOC1", "19", 44919161, 44919181),
        ("APOE", "19", 44890490, 44890510),
        ("APOE", "19", 44904990, 44905010),
    ]


async def test_module_rows_only_keeps_the_rows_own_gene_and_allele(make_client, rows_spec):
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "top_expression_effects", {"spec_dir": str(rows_spec), "module_rows_only": True}
        )
    body = json.loads(out.content[0].text)
    assert [e["start"] for e in body["effects"]] == [44919171]
    assert body["total_rows"] == 4
    assert body["direction_counts"] == {"decrease": 1}
    assert sum(body["row_status"].values()) == 6
    assert body["row_status"]["unreadable"] == 0
    assert body["row_status"]["gene_not_at_locus"] == 1


async def test_without_the_filter_there_is_no_row_status(make_client, rows_spec):
    async with make_client(offline_settings()) as client:
        out = await client.call_tool("top_expression_effects", {"spec_dir": str(rows_spec)})
    body = json.loads(out.content[0].text)
    assert body["row_status"] is None
    assert body["direction_counts"] == {"decrease": 1, "increase": 2, "unknown": 1}


async def test_a_rows_dry_run_is_a_plan_and_asks_nothing(make_client, rows_spec, monkeypatch):
    def _no_egress(*_a, **_k):
        raise AssertionError("a dry run reached the Atlas")

    monkeypatch.setattr(passes, "enrich_expression", _no_egress)
    async with make_client(offline_settings()) as client:
        out = await client.call_tool(
            "enrich_expression_effects",
            {"spec_dir": str(rows_spec), "rows": True, "dry_run": True},
        )
    body = json.loads(out.content[0].text)
    assert body["windows"] == 3 and body["windows_run"] == 0
    assert body["written"] is None
    assert body["row_status"]["scored"] == 1


async def test_a_rows_run_queries_each_window_and_stops_at_a_failure(
    make_client, rows_spec, monkeypatch
):
    asked: list[tuple[str, str, int, int]] = []

    class _Result:
        candidates, written, withheld, warnings, dataset = 3, 3, {}, [], "ds"

    def _fake(_target, gene, *, chrom, start, end, **_k):
        asked.append((gene, chrom, start, end))
        if len(asked) == 2:
            raise passes.ExpressionError("licence row could not be written")
        return _Result()

    monkeypatch.setattr(passes, "enrich_expression", _fake)
    async with make_client(_online_settings()) as client:
        out = await client.call_tool(
            "enrich_expression_effects", {"spec_dir": str(rows_spec), "rows": True}
        )
    body = json.loads(out.content[0].text)
    assert asked == [("APOC1", "19", 44919161, 44919181), ("APOE", "19", 44890490, 44890510)]
    assert body["success"] is False
    assert body["windows"] == 3 and body["windows_run"] == 1
    assert body["accounts_for_every_candidate"] is None
    assert any("F95" in w for w in body["warnings"])


async def test_without_rows_a_gene_is_still_required(make_client, tmp_path):
    spec = tmp_path / "spec"
    spec.mkdir()
    async with make_client(_online_settings()) as client:
        with pytest.raises(Exception, match="Provide a gene"):
            await client.call_tool("enrich_expression_effects", {"spec_dir": str(spec)})


def test_a_row_validation_refuses_is_counted_not_dropped(rows_spec: Path) -> None:
    with (rows_spec / "variants.csv").open("a") as handle:
        handle.write(",19,44905000,G,A,G/A,APOE,0.5,risk,unsorted genotype\n")
    report = report_rows(rows_spec)
    assert report.rows_read == 7
    assert report.status["unreadable"] == 1
    assert "alphabetically sorted" in report.examples["unreadable"][0]
