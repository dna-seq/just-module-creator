"""Thick or thin: the routing decision, and what a routed answer owes its caller (RM30).

**The network boundary is the one thing this suite may exclude**, so the `RegistryClient`
method is where the double goes — never the decision, never the translation, never the
capture. Everything above the socket is the code under test.

The proxy surface is `just-dna-registry` 0.25.0, which is **not released**: these run
against the editable sibling checkout on `preview-0.7`, and against a PyPI 0.18.2 they
skip by naming the symbol they looked for. That is the honest state and the producer says
the same of their own tests — those routes have never been exercised over a network by
anyone, only through `TestClient`.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path
from typing import Any

import pytest
from conftest import offline_settings

from just_module_creator import routing
from just_module_creator.settings import Settings

needs_proxy = pytest.mark.skipif(
    routing.proxy_gap() is not None,
    reason="installed just-dna-registry client has no caching-proxy surface (0.25.0)",
)

#: The lane registry is a whole MODULE the 0.6.6 enricher does not ship (upstream RM176),
#: so these read it through `routing`'s single guarded import rather than importing it a
#: second time — a direct import here is a collection error, not a skip, and it took the
#: whole conftest down once already.
needs_lanes = pytest.mark.skipif(
    not routing.LANES_KNOWN,
    reason="installed just-dna-enricher has no cache registry (just_dna_enricher.caches, 0.7)",
)


# --------------------------------------------------------------------------- #
# The decision
# --------------------------------------------------------------------------- #
def test_a_lane_nobody_holds_is_the_only_reason_auto_routes_out():
    """`auto` is per lane, which is the whole point of the switch the owner chose.

    A global mode would make a box holding three of fifteen lanes pick one wrong answer
    for everything — and holding Ensembl and nothing else is the *common* shape, since
    it is the one lane `enrich` cannot work without.
    """
    both = {"ensembl": True, "clinvar": True}
    one = {"ensembl": True, "clinvar": False}
    neither = {"ensembl": False, "clinvar": False}

    # `lanes_known=True` is passed explicitly so this asserts the DECISION rather than
    # this machine's install: the same logic has to be exercised on a toolchain whose
    # enricher has no lane registry at all.
    assert routing.route_for(
        "lookup_variant",
        snapshot_route="auto",
        offline=False,
        target="test",
        presence=both,
        lanes_known=True,
    ).answered_by == "local"
    for presence in (one, neither):
        route = routing.route_for(
            "lookup_variant",
            snapshot_route="auto",
            offline=False,
            target="test",
            presence=presence,
            lanes_known=True,
        )
        # **Two outcomes and both are correct**, which is the point: a missing lane is
        # what makes `auto` reach for the proxy, and where the proxy is unavailable the
        # answer falls back to the live services and SAYS SO. A test asserting only the
        # first would pass on this branch and fail for a user on PyPI, which is the
        # reverse of what a guard is for.
        if routing.proxy_gap() is None:
            assert route.answered_by == "registry"
        else:
            assert route.answered_by == "local"
            assert "proxy is unavailable" in route.why
        # The sentence names what was missing either way, because "routed out" without
        # the reason is the silent fall-back this whole sub-model exists to prevent.
        for lane, held in presence.items():
            if not held:
                assert lane in route.why


def test_offline_outranks_every_route_because_routing_out_is_egress():
    """The ceiling may not be loosened by a routing decision — §2, at a new grain.

    A "cache-only" lookup that quietly went to a registry would be lying about the
    flag, which is the one thing it must never be made to do.
    """
    for wanted in ("auto", "registry", "local"):
        route = routing.route_for(
            "lookup_variant",
            snapshot_route=wanted,  # type: ignore[arg-type]
            offline=True,
            target="test",
            presence={"ensembl": False, "clinvar": False},
            lanes_known=True,
        )
        assert route.answered_by == "local"
        assert route.target is None, "an offline run names no instance, because none was asked"
        assert route.offline is True


def test_a_tool_with_no_lane_is_unrouted_rather_than_local():
    """Four states, not two, and the fourth is *there was nothing to decide*.

    HGNC and OLS4 publish no snapshot, so a gene or trait lookup is online on a fully
    provisioned server too. Calling that `local` would claim a snapshot answered it.
    """
    route = routing.route_for(
        "lookup_citation", snapshot_route="auto", offline=False, target="test", presence={}
    )
    assert route.answered_by == "unrouted"
    assert route.lanes_needed == ()
    assert "no snapshot lane" in route.why


@needs_lanes
def test_the_lane_map_names_only_lanes_the_producer_declares():
    """An explicit map is still a hand-kept one, so it is pinned against `CACHE_LANES`.

    The map cannot be *derived* — `hint_variant` needs Ensembl and ClinVar while
    `hint_gene` reaches HGNC, and no rule relates a tool to a lane — but a typo in it
    would silently make a tool route out forever, since a lane nobody holds is exactly
    the trigger.
    """
    declared = {lane.name for lane in routing.CACHE_LANES}
    for tool, lanes in routing.LANES_FOR.items():
        unknown = set(lanes) - declared
        assert not unknown, f"{tool} names lanes no producer declares: {sorted(unknown)}"


def test_local_presence_is_read_from_the_producers_own_resolver():
    """Not a directory walk of ours: `lane.resolve()` is what the pass itself calls.

    A second implementation of "is this snapshot here" would disagree with the pass on
    exactly the cases that matter — a lane pointed at by an env var, a lane whose
    release file is unreadable.
    """
    presence = routing.local_lane_presence()
    if not routing.LANES_KNOWN:
        # The whole module is absent on a pre-0.7 enricher, and `None` says so rather
        # than claiming a measurement — an empty map would read as "holds none".
        assert presence is None
        return
    assert presence is not None
    assert set(presence) == {lane.name for lane in routing.CACHE_LANES}
    assert all(isinstance(v, bool) for v in presence.values())


def test_an_unanswerable_probe_routes_local_and_says_the_probe_could_not_run():
    """A check that could not run is not a check that failed — and not a reason to route.

    On a pre-0.7 enricher there is no lane registry, so "is this snapshot here" has no
    answer. Routing out on the strength of that would send every lookup to a registry on
    the basis of no measurement at all; behaving exactly as the tool did before the
    switch existed is the honest default.
    """
    route = routing.route_for(
        "lookup_variant",
        snapshot_route="auto",
        offline=False,
        target="test",
        presence={},
        lanes_known=False,
    )
    assert route.answered_by == "local"
    assert route.lanes_local == ()
    assert "cannot be asked" in route.why
    assert "not because" in route.why, "empty must be distinguished from absent in the text"


def test_the_miss_relabel_keeps_the_original_reason_and_adds_the_fall_back():
    """A proxy miss falls through to the live service, and that must be *visible*.

    The values may be identical and the egress is ours, which is a different answer
    from "this came off a snapshot" however equal the cells.
    """
    route = routing.route_for(
        "lookup_variant",
        snapshot_route="auto",
        offline=False,
        target="test",
        presence={"ensembl": False, "clinvar": True},
        lanes_known=True,
    )
    relabelled = routing.missed_at_registry(route, detail="503 snapshot_unavailable: ensembl")
    assert relabelled.answered_by == "local_online_after_registry_miss"
    assert route.why in relabelled.why, "the original decision survives the relabel"
    assert "503" in relabelled.why
    assert relabelled.lanes_needed == route.lanes_needed


# --------------------------------------------------------------------------- #
# The capability probe
# --------------------------------------------------------------------------- #
def test_the_probe_asks_the_installed_client_by_symbol_not_by_version():
    """A version string is not a capability — the `curator` case is why.

    Both trees read `just-dna-format 0.6.1` while `StudyRow.curator` was present in one
    and absent in the other, and the same shape applies to a client: our floor is
    `>=0.18.1` with no ceiling, so what is installed is a fact to measure.
    """
    from just_dna_registry.client import RegistryClient

    gap = routing.proxy_gap()
    has_all = all(hasattr(RegistryClient, name) for name in routing._PROXY_METHODS)
    assert (gap is None) == has_all


def test_a_refusal_names_the_release_and_says_nothing_needs_configuring(monkeypatch):
    """The surface must never teach a step it cannot run — and a bare "no" is that.

    **Forced rather than skipped, so this runs on both toolchains.** On the preview
    branch the installed client *can* proxy, so the refusal path would otherwise never
    be read — and the refusal is the half that ships to `main` and is the half a user on
    PyPI actually meets. Naming a method that does not exist is the same condition the
    real probe finds.

    Asserted on the *text* because the text is the deliverable: an author who reads
    "unavailable" goes and debugs their configuration, and there is nothing to debug.
    """
    monkeypatch.setattr(
        routing, "_PROXY_METHODS", (*routing._PROXY_METHODS, "no_such_method_on_any_client")
    )
    gap = routing.proxy_gap()
    assert gap is not None
    assert "0.25.0" in gap, "an author needs the release number to know what would fix it"
    assert "nothing needs configuring" in gap.lower()
    assert "no_such_method_on_any_client" in gap, "the refusal names what was missing"
    # And it routes the author somewhere that works today rather than stopping at "no".
    assert "registry_caches" in gap and "cache prepare" in gap



# --------------------------------------------------------------------------- #
# registry_caches
# --------------------------------------------------------------------------- #
async def test_registry_caches_reports_every_lane_and_requires_a_target(make_client):
    """It walks `CACHE_LANES`, not the instance's list, so an unknown lane reads *null*.

    `remote=None` is *not asked*; `remote="absent"` is a deployment that answered and
    does not hold it. Folding those together would tell an operator to provision a lane
    nobody has ever asked about.
    """
    async with make_client(offline_settings()) as client:
        result = await client.call_tool("registry_caches", {"target": "test"})
    report = result.data

    if not routing.LANES_KNOWN:
        # The install the proxy exists for: no lane registry, so the rows would come
        # from the instance — and offline reaches none, so there is nothing to enumerate
        # and `local_count` is null rather than zero.
        assert report.lanes == []
        assert report.local_count is None
        assert report.proxy_gap is not None
        return

    assert {row.lane for row in report.lanes} == {lane.name for lane in routing.CACHE_LANES}
    assert report.local_count == sum(1 for row in report.lanes if row.local)
    # Offline settings never reach an instance, so the far side is unasked rather than
    # empty — and a null count is the honest shape for that.
    assert report.remote_count is None
    assert all(row.remote is None for row in report.lanes)
    assert report.snapshot_route in ("auto", "local", "registry")


async def test_registry_caches_says_what_neither_side_holds(make_client):
    """`unreachable` is the field to read first, and it is an intersection of absences.

    A lane neither side holds is the one case where no route exists, so a tool needing
    it fetches live or reports the question as unasked — which is a different sentence
    from either "this machine is unprovisioned" or "the registry is".
    """
    async with make_client(offline_settings()) as client:
        result = await client.call_tool("registry_caches", {"target": "test"})
    report = result.data
    # Nothing was asked of the instance here, so nothing can be known to be held by
    # neither — the field withholds rather than accusing both sides.
    assert report.unreachable == []


# --------------------------------------------------------------------------- #
# remote_derive: the capture, and the decision list
# --------------------------------------------------------------------------- #
def _archive(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


_RESOLUTION_HEADER = (
    "variant_key,locus_index,rsid,chrom,start,ref,alt,genome_build,status,source,fetched_at\n"
)


def _resolution(rows: list[tuple[str, str, str]]) -> bytes:
    """A minimal real `resolution.csv`. Real rsIDs — `rs4988235` is the lactase one."""
    out = io.StringIO()
    out.write(_RESOLUTION_HEADER)
    for key, rsid, source in rows:
        out.write(
            f"{key},0,{rsid},2,135851076,G,A,GRCh38,resolved,{source},2026-09-11T00:00:00Z\n"
        )
    return out.getvalue().encode()


def test_a_displaced_row_is_a_decision_line_and_names_a_hand_curated_one():
    """The core of the capture rule: what the incoming tree drops is put in front of you.

    **Not a defect report.** A row missing from the new tree is either the source
    withdrawing an answer or the remote run being unable to ask, and only the author
    tells those apart. A `source="manual"` row is called out because nothing will
    re-derive one.
    """
    import tempfile

    from just_module_creator.tools.proxy import _displacement_lines

    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        (spec_dir / "resolution.csv").write_bytes(
            _resolution(
                [
                    ("2-135851076-G-A", "rs4988235", "ensembl"),
                    ("1-11796321-G-A", "rs1801133", "manual"),
                ]
            )
        )
        incoming = {"resolution.csv": _resolution([("2-135851076-G-A", "rs4988235", "ensembl")])}
        lines, displaced = _displacement_lines(spec_dir, incoming)

    assert displaced and displaced[0].name == "resolution.csv"
    assert len(lines) == 1, lines
    assert "1-11796321-G-A" in lines[0]
    assert 'source="manual"' in lines[0], "a hand-curated row must be marked as one"


def test_a_row_the_new_tree_still_carries_produces_no_line():
    """Because the server gap-fills: the ordinary round trip reports nothing.

    The uploaded spec carries the existing sidecars and `enrich_spec` merges, so a
    hand-curated row normally travels up and comes back. A decision list that fired on
    every run would be noise that hides the real lines — the tautology-zero rule.
    """
    import tempfile

    from just_module_creator.tools.proxy import _displacement_lines

    rows = [("2-135851076-G-A", "rs4988235", "ensembl"), ("1-11796321-G-A", "rs1801133", "manual")]
    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        (spec_dir / "resolution.csv").write_bytes(_resolution(rows))
        lines, displaced = _displacement_lines(spec_dir, {"resolution.csv": _resolution(rows)})

    assert displaced, "the file is still displaced — it is being replaced"
    assert lines == [], "nothing left the table, so there is nothing to decide"


def test_the_concordance_pair_is_not_diffed_and_says_why():
    """Their producer rewrites both whole, so every row would read as withdrawn.

    Skipping the diff is the same reasoning `refresh_sidecar` refuses them on, and
    stating it is what stops the skip looking like an oversight.
    """
    import tempfile

    from just_module_creator.tools.proxy import _WHOLE_REWRITE, _displacement_lines

    header = "variant_key,genotype,authority_concordance,authored_position\n"
    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        for name in _WHOLE_REWRITE:
            (spec_dir / name).write_text(header + "2-135851076-G-A,A/A,discordant,matches_some\n")
        lines, displaced = _displacement_lines(
            spec_dir, {name: header.encode() for name in _WHOLE_REWRITE}
        )

    assert len(displaced) == len(_WHOLE_REWRITE)
    assert len(lines) == len(_WHOLE_REWRITE)
    for line in lines:
        assert "rewrites both concordance tables on every run" in line
        assert "Nothing to decide" in line


def test_the_archive_reader_takes_only_recognised_sidecars_by_basename():
    """A third party's bytes: a traversing member name must not reach the spec directory.

    Members are taken by basename and only where the name is a recognised derived file,
    so `derived/../../../etc/passwd` contributes nothing rather than escaping.
    """
    from just_module_creator.tools.proxy import _unpack

    archive = _archive(
        {
            "derived/resolution.csv": _resolution([("2-135851076-G-A", "rs4988235", "ensembl")]),
            "derived/../../evil.csv": b"nope",
            "derived/not_a_spec_file.csv": b"nope",
            "check.json": b"{}",
            "WHERE-THIS-CAME-FROM.md": b"# note",
        }
    )
    tables, extras, absent = _unpack(archive)

    assert set(tables) == {"resolution.csv"}
    assert "check.json" in extras and "WHERE-THIS-CAME-FROM.md" in extras
    assert not any("evil" in name for name in tables)
    # `{}` is a report that does not say, which is not the same fact as a clean run.
    assert absent is None


def test_what_the_run_did_not_produce_is_read_and_kept_three_valued():
    """A table missing from the archive is not a table with nothing in it.

    Upstream's own note: `files_absent` means *"not produced here"*, never *"this module
    has none"* — a gated source whose credential the deployment lacks writes nothing and
    records no reason at all, so the absence has two readings and the archive cannot tell
    them apart. What it can do is enumerate, and what we must not do is flatten the three
    states: a report that lists nothing is a clean run, and **no report at all is a
    question that could not be put**.
    """
    from just_module_creator.tools.proxy import _absent_from, _unpack

    archive = _archive(
        {
            "derived/resolution.csv": _resolution([("2-135851076-G-A", "rs4988235", "ensembl")]),
            "check.json": b'{"files_absent": ["expression_effects.csv", "frequencies.csv"]}',
        }
    )
    _, _, absent = _unpack(archive)
    assert absent == ["expression_effects.csv", "frequencies.csv"]

    clean = _archive({"check.json": b'{"files_absent": []}'})
    assert _unpack(clean)[2] == [], "a report that lists nothing is a clean run"

    # A third party's bytes: every malformed shape answers "it did not say" rather than
    # raising or being read as an empty list.
    for payload in (b"not json at all", b"[1, 2]", b'{"files_absent": "frequencies.csv"}'):
        assert _absent_from(payload) is None, payload


@needs_proxy
async def test_a_table_the_run_could_not_produce_reaches_the_caller_as_a_question(
    monkeypatch, make_client, tmp_path
):
    """And the sentence names both readings, because upstream deliberately names neither.

    The pass may be gated on a credential this deployment lacks, or the snapshot may be
    missing — `registry_caches` answers the second and nothing answers the first, so the
    honest output is the enumerable fact plus what it does not settle.
    """
    from just_module_creator.tools import proxy

    (tmp_path / "module_spec.yaml").write_text("module:\n  name: x\n")
    archive = _archive(
        {
            "derived/resolution.csv": _resolution([("2-135851076-G-A", "rs4988235", "ensembl")]),
            "check.json": b'{"files_absent": ["expression_effects.csv"]}',
        }
    )

    class _Stub:
        def derived(self, namespace, name, spec_dir):
            return archive

    monkeypatch.setattr(proxy, "client_for", lambda *_a, **_k: _Stub())

    async with make_client(offline_settings(workspace=str(tmp_path))) as client:
        result = await client.call_tool(
            "remote_derive",
            {"spec_dir": str(tmp_path), "namespace": "test-sheep", "name": "test_lactose"},
        )
    report = result.data

    assert report.not_produced == ["expression_effects.csv"]
    assert "not_produced" in report.next_step
    assert "registry_caches" in report.next_step
    assert report.decisions == [], "a file nobody produced is not a row decision"


_LICENSING_HEADER = "source,layer,license,fetched_at\n"


def _licensing(rows: list[tuple[str, str]]) -> bytes:
    """A minimal real `licensing.csv` — the keyed columns are `(source, layer)`."""
    body = "".join(
        f"{source},{layer},CC0-1.0,2026-09-11T00:00:00Z\n" for source, layer in rows
    )
    return (_LICENSING_HEADER + body).encode()


def test_an_incoming_table_lands_on_the_spelling_the_author_already_has():
    """`sources.csv` on disk and `licensing.csv` in the archive is ONE table, not two.

    **`_dest_for` is a mitigation with a deletion trigger, and the trigger is a release
    rather than an upstream tree.** Filed as format-tree `S96` and fixed the same hour as
    their RM224: `sidecar_spellings` now normalises through a filename → key map, published
    as `layout.sidecar_key`, so every caller is right for either spelling and their reply
    says outright *"delete the shim"*. It stays until that reaches PyPI, because our own
    floor is 0.6.6 and an install from PyPI still has the defect — §8's rule, and the whole
    reason a fix in a sibling checkout is not a fix our users have.

    So the upstream half is asserted **by symbol**, both ways round: on a toolchain with
    `sidecar_key` the helper must already follow the file you read, and without it the
    answer must be the second spelling. A third behaviour fails here rather than being
    absorbed, and either way `_dest_for` answers the same.
    """
    import tempfile

    from just_dna_format import layout

    from just_module_creator.tools.proxy import _dest_for

    upstream_normalises = hasattr(layout, "sidecar_key")
    expected_upstream = "sources.csv" if upstream_normalises else "licensing.csv"

    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        (spec_dir / "sources.csv").write_bytes(_licensing([("ensembl", "resolution")]))

        assert _dest_for(spec_dir, "licensing.csv").name == "sources.csv"
        assert layout.sidecar_write_path(spec_dir, "licensing.csv").name == expected_upstream, (
            "upstream's own answer is neither of the two recorded states — re-read "
            "`layout.SIDECAR_SPELLINGS` and F93 before touching `_dest_for`"
        )

    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        (spec_dir / "licensing.csv").write_bytes(_licensing([("ensembl", "resolution")]))
        assert _dest_for(spec_dir, "licensing.csv").name == "licensing.csv"

    with tempfile.TemporaryDirectory() as raw:
        assert _dest_for(Path(raw), "licensing.csv").name == "licensing.csv"


def test_a_displaced_deprecated_spelling_still_produces_its_decision_lines():
    """The diff has to find the file too, not only the write.

    Looking for `licensing.csv` over a spec carrying `sources.csv` finds nothing, reports
    no displacement and captures nothing — so the author's rows would be replaced with no
    line naming what left. Same translation, and this is the half that fails silently.
    """
    import tempfile

    from just_module_creator.tools.proxy import _displacement_lines

    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        (spec_dir / "sources.csv").write_bytes(
            _licensing([("ensembl", "resolution"), ("clinvar", "clinical_assertions")])
        )
        lines, displaced = _displacement_lines(
            spec_dir, {"licensing.csv": _licensing([("ensembl", "resolution")])}
        )

    assert [path.name for path in displaced] == ["sources.csv"]
    assert len(lines) == 1, lines
    assert "clinvar" in lines[0] and "sources.csv" in lines[0]


def test_a_spec_carrying_both_spellings_is_refused_rather_than_chosen_between():
    """Two copies of one table are two claims, and neither can be preferred.

    Upstream raises `SidecarCollision` for exactly that reason; the refusal is passed
    through because there is no correct silent behaviour available to us either.
    """
    import tempfile

    from just_dna_format.layout import SidecarCollision

    from just_module_creator.tools.proxy import _displacement_lines

    with tempfile.TemporaryDirectory() as raw:
        spec_dir = Path(raw)
        rows = _licensing([("ensembl", "resolution")])
        (spec_dir / "sources.csv").write_bytes(rows)
        (spec_dir / "licensing.csv").write_bytes(rows)
        with pytest.raises(SidecarCollision):
            _displacement_lines(spec_dir, {"licensing.csv": rows})


@needs_proxy
async def test_remote_derive_writes_over_the_deprecated_spelling_not_beside_it(
    monkeypatch, make_client, tmp_path
):
    """Asserted through the tool, because the write is the thing that leaves two files.

    The capture lands under the workspace rather than the developer's cache, and the
    installed name is the author's spelling — a module that arrived carrying
    `sources.csv` goes on carrying exactly one table.
    """
    from just_module_creator.tools import proxy

    spec_dir = tmp_path / "module"
    spec_dir.mkdir()
    (spec_dir / "module_spec.yaml").write_text("module:\n  name: x\n")
    (spec_dir / "sources.csv").write_bytes(_licensing([("ensembl", "resolution")]))

    incoming = _licensing([("ensembl", "resolution"), ("clinvar", "clinical_assertions")])
    archive = _archive({"derived/licensing.csv": incoming})

    class _Stub:
        def derived(self, namespace, name, spec_dir):
            return archive

    monkeypatch.setattr(proxy, "client_for", lambda *_a, **_k: _Stub())

    async with make_client(offline_settings(workspace=str(tmp_path))) as client:
        result = await client.call_tool(
            "remote_derive",
            {
                "spec_dir": str(spec_dir),
                "namespace": "test-sheep",
                "name": "test_lactose",
                "dry_run": False,
            },
        )
    report = result.data

    assert report.installed == ["sources.csv"]
    assert not (spec_dir / "licensing.csv").exists(), "two spellings is an error, not a merge"
    assert (spec_dir / "sources.csv").read_bytes() == incoming
    assert report.capture_dir is not None, "the displaced file must have been captured first"


async def test_remote_derive_refuses_with_the_release_name_when_it_cannot_proxy(
    make_client,
):
    """And when it CAN, it is still a registered tool rather than a hidden one.

    A hidden tool answers a call by name with "Unknown tool", which teaches the caller
    nothing — the dead end the tier axis cost four times over.
    """
    async with make_client(offline_settings()) as client:
        names = {t.name for t in await client.list_tools()}
    assert {"registry_caches", "remote_derive"} <= names


def test_the_key_columns_come_from_the_producers_generated_map():
    """`hints.key_fields` reads the model's own `_KEY_FIELDS`, so it cannot name a
    retired column — which is what `modifier_cn` cost for a whole minor.

    Asserted against the live model rather than against a tuple of ours: a guard that
    compared our copy with our copy would measure nothing.
    """
    from just_dna_format.resolution import ResolutionRow

    from just_module_creator.tools.proxy import _key_columns

    columns = _key_columns("resolution.csv")
    assert columns, "resolution.csv declares a key and this found none"
    for column in columns:
        assert column in ResolutionRow.model_fields, (
            f"the generated key names {column!r}, which is not a live field on the model"
        )


def test_settings_default_to_auto_and_the_polygon():
    """Both defaults are decisions, so both are pinned.

    `auto` because per-lane is the real world; the polygon because prod and polygon
    resolve to the same IP and share gnomAD's single unbuyable allowance, so spending
    the rehearsal box's ledger is the courteous default.
    """
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.snapshot_route == "auto"
    assert settings.proxy_target == "test"


def test_the_snapshot_route_is_not_the_stdio_transport():
    """Two settings, two unrelated questions, and the names must not blur.

    `transport` is stdio-versus-http. Reusing that word for thick-versus-thin would
    have made one env var change the other's meaning in a reader's head.
    """
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.transport == "stdio"
    assert settings.snapshot_route != settings.transport


@needs_proxy
def test_the_registry_hint_models_are_theirs_so_a_translation_is_owed():
    """Measured, because it is the reason a translation layer exists at all.

    Their `VariantHintReport` flattens `rsid_status` into `rsid_state`/`rsid_current`,
    maps `checked`'s absolute snapshot paths to lane names under `cost.served_from`, and
    promotes `ambiguous` — a `@property` upstream, which does not survive serialization
    — to a real field. Reading their model as the enricher's would drop three answers.
    """
    from just_dna_registry.models.api import VariantHintReport

    fields = set(VariantHintReport.model_fields)
    assert "rsid_status" not in fields, "if this reappears, the flattening was reverted"
    assert {"rsid_state", "cost"} <= fields


# --------------------------------------------------------------------------- #
# The translation, and the routed path end to end
# --------------------------------------------------------------------------- #
@needs_proxy
def test_the_translation_recovers_three_answers_a_naive_read_would_drop():
    """Their model is theirs, and reading it as the enricher's loses `rsid_current`,
    `ambiguous` and the lane names.

    Built from a **real** `VariantHintReport` rather than a stub, so the field names are
    the producer's own: a stub would agree with whatever this function happens to do.
    `rs1801133` is MTHFR c.665C>T and `rs4988235` is the lactase one — real ids, per §6.
    """
    from just_dna_registry.models.api import HintCost, VariantHintReport

    from just_module_creator import routing as r

    report = VariantHintReport(
        rsid="rs1801133",
        rsid_state="merged",
        rsid_current="rs1801133",
        loci=[{"chrom": "1", "start": 11796321, "ref": "G", "alts": ["A"]}],
        rsid_candidates=[],
        populations=[],
        clin_sig=[{"clin_sig": "benign"}],
        pubmind=[{"pvid": "PV1"}],
        vrs_id="ga4gh:VA.example",
        ambiguous=True,
        findings=[],
        alterations=[],
        cost=HintCost(charged={}, served_from=["ensembl", "clinvar"], limit=None),
    )
    fields = r.variant_fields(report, proxied=True)

    assert fields["rsid_current"] == "rs1801133", "the flattened currency field survives"
    assert fields["ambiguous"] is True, "a @property upstream is a real field here"
    assert fields["pubmind"] == [{"pvid": "PV1"}], "the field added at our asking survives"
    # `checked` comes from cost.served_from, which is LANE NAMES — the producer maps the
    # absolute snapshot paths out deliberately, so nothing here may look like a path.
    assert fields["checked"] == ["clinvar", "ensembl"]
    assert not any("/" in c for c in fields["checked"]), "no filesystem path on the wire"


@needs_proxy
def test_the_cost_translation_keeps_an_empty_charge_as_a_real_answer():
    """An empty `charged` is the product: it is what teaches a caller their traffic is free.

    Dropping the block when nothing was charged would leave "you are being throttled"
    with two opposite histories and opposite remedies.
    """
    from just_dna_registry.models.api import HintCost, VariantHintReport

    from just_module_creator import routing as r

    free = VariantHintReport(
        rsid="rs4988235",
        cost=HintCost(charged={}, served_from=["ensembl"], limit=None),
    )
    cost = r.cost_from(free)
    assert cost is not None, "an empty charge is still an answer and must not become null"
    assert cost["charged"] == {}
    assert cost["served_from"] == ["ensembl"]

    paid = VariantHintReport(
        rsid="rs4988235",
        cost=HintCost(
            charged={"gnomad": 3}, served_from=[], limit="10 per 60s", remedy="provision it"
        ),
    )
    paid_cost = r.cost_from(paid)
    assert paid_cost is not None
    assert paid_cost["charged"] == {"gnomad": 3}
    assert paid_cost["limit"] == "10 per 60s", "the allowance is what separates the two histories"


def test_the_local_translation_flattens_the_enrichers_own_status_object():
    """The other half of the seam, read from the enricher's real dataclass.

    `RsidStatus` is a nested object there and two flat fields on the far side; a reader
    that only knew one shape would return `rsid_state=None` for a merged rsID.
    """
    from just_dna_enricher.lookup import RsidStatus, VariantHint

    from just_module_creator import routing as r

    hint = VariantHint(
        rsid="rs1801133",
        rsid_status=RsidStatus(rsid="rs1801133", state="merged", current="rs1801131"),
    )
    fields = r.variant_fields(hint, proxied=False)
    assert fields["rsid_state"] == "merged"
    assert fields["rsid_current"] == "rs1801131"
    # `ambiguous` is a @property here, and reading it is legitimate in-process — it is
    # only serialization that drops it, which is why the far side promoted it.
    assert fields["ambiguous"] in (True, False)


def test_what_was_consulted_is_labels_on_both_sides_and_never_a_path():
    """`VariantHint.checked` changed meaning under an unchanged name, and this pins it.

    Before the enricher's RM205 (our `S93`) it mixed `str(reference)` — an absolute
    snapshot path — with live-source labels; after it, labels only, with the paths moved
    to `snapshots`, *"the one place a path lives in the payload"*. So a reader written
    against either shape is right about one toolchain and wrong about the other, and the
    field a host is expected to **drop** is the one we must never serialize.

    Both shapes are asserted as data rather than probed for, because the point is the
    output vocabulary: labels, whichever side and whichever release answered.
    """
    from just_module_creator import routing as r

    # Post-split: the producer's own map is reversed rather than a lane name guessed.
    assert r._labels_only(
        {"/data/just-dna-cache/ensembl/ensembl.db", "ensembl-live"},
        snapshots={"ensembl": "/data/just-dna-cache/ensembl/ensembl.db"},
    ) == ["ensembl", "ensembl-live"]

    # Pre-split: no map exists, so the path is WITHHELD rather than emitted or guessed at.
    assert r._labels_only({"/data/just-dna-cache/clinvar/clinvar.db", "ensembl-live"}) == [
        "ensembl-live"
    ]
    assert r._labels_only(None) == []


def test_the_local_side_serializes_no_snapshot_path_and_no_snapshot_map():
    """Read off the enricher's real dataclass, so it is the installed contract being pinned.

    Two separate promises. The values we emit are labels — asserted by shape (no separator
    can appear) rather than against a known path, so it fails earlier than a string match
    would. And `snapshots` is never carried across the boundary at all: a host that does
    not want to publish its layout drops that field, and this layer is a host.
    """
    from just_dna_enricher.lookup import VariantHint

    from just_module_creator import routing as r
    from just_module_creator.models import VariantLookup

    hint = VariantHint(rsid="rs4988235")
    hint.checked.add("ensembl")
    hint.checked.add("ensembl-live")
    if hasattr(hint, "snapshots"):
        hint.snapshots["ensembl"] = "/data/just-dna-cache/ensembl/ensembl.db"
        hint.checked.add("/data/just-dna-cache/ensembl/ensembl.db")

    fields = r.variant_fields(hint, proxied=False)
    assert fields["checked"] == ["ensembl", "ensembl-live"]
    for value in fields["checked"]:
        assert "/" not in value and "\\" not in value, "no filesystem path in a hint payload"
    assert "snapshots" not in fields
    assert "snapshots" not in VariantLookup.model_fields


@needs_proxy
async def test_a_routed_lookup_reports_the_registry_and_its_cost(monkeypatch, make_client):
    """The whole seam, with the double at the `RegistryClient` method — the one boundary
    the suite is allowed to exclude, because it is the socket.

    The decision, the batch choice, the translation and the reporting are all real code.
    """
    from just_dna_registry.models.api import HintCost, VariantHintBatchResponse, VariantHintReport

    from just_module_creator import routing as r
    from just_module_creator.settings import Settings
    from just_module_creator.tools import research

    report = VariantHintReport(
        rsid="rs4988235",
        rsid_state="current",
        loci=[{"chrom": "2", "start": 135851076, "ref": "G", "alts": ["A"]}],
        cost=HintCost(charged={}, served_from=["ensembl"], limit=None),
    )

    class _Double:
        def __init__(self) -> None:
            self.batched: list[Any] = []

        def hint_variants(self, *, keys, frequencies=False, offline=True):
            self.batched.append(keys)
            return VariantHintBatchResponse(
                results=[report], total_charged={}, cost=HintCost(charged={})
            )

        def hint_variant(self, **_: Any):  # pragma: no cover — the batch is the path
            raise AssertionError("the single form egresses unconditionally; use the batch")

    double = _Double()
    monkeypatch.setattr(research, "client_for", lambda *_a, **_k: double)
    # Force the routed branch: no lane held, proxy available, not offline.
    monkeypatch.setattr(r, "local_lane_presence", lambda: {"ensembl": False, "clinvar": False})

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        offline=False,
        snapshot_route="auto",
        proxy_target="test",
    )
    async with make_client(settings) as client:
        result = await client.call_tool("lookup_variant", {"rsid": "rs4988235"})
    data = result.data

    assert data.route is not None
    assert data.route.answered_by == "registry"
    assert data.route.target == "test"
    assert "ensembl" in data.route.why
    assert data.cost is not None and data.cost.charged == {}
    assert data.checked == ["ensembl"], "lane names from cost.served_from"
    assert data.loci and data.loci[0]["start"] == 135851076
    # The batch, not the single form: an online single lookup egresses unconditionally
    # because dbSNP merge status has no snapshot in that tree.
    assert double.batched == [[{"rsid": "rs4988235"}]]


@needs_proxy
async def test_a_proxy_failure_falls_back_live_and_says_so(monkeypatch, make_client):
    """A 503 means the deployment lacks the lane too — so the fall-back is legitimate
    and **must be visible**.

    Answering `local` here would claim a snapshot served it. It did not: nothing did.
    """
    from just_module_creator import routing as r
    from just_module_creator.settings import Settings
    from just_module_creator.tools import research

    class _Broken:
        def hint_variants(self, **_: Any):
            raise RuntimeError("503 snapshot_unavailable: ensembl")

    monkeypatch.setattr(research, "client_for", lambda *_a, **_k: _Broken())
    monkeypatch.setattr(r, "local_lane_presence", lambda: {"ensembl": False, "clinvar": False})

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        offline=True,
        snapshot_route="registry",
        proxy_target="test",
    )
    async with make_client(settings) as client:
        result = await client.call_tool("lookup_variant", {"rsid": "rs4988235"})
    data = result.data

    # `offline=True` here, so the route never left the machine in the first place —
    # which is the assertion that matters: the ceiling outranks `snapshot_route`.
    assert data.route is not None
    assert data.route.answered_by == "local"
    assert data.route.offline is True
    assert data.cost is None


@needs_proxy
async def test_remote_draft_refuses_a_stray_parameter_rather_than_dropping_it(
    monkeypatch, make_client, tmp_path
):
    """A silently ignored filter produces a draft answering a different question.

    The refusal is the server's; what is asserted here is that its text reaches the
    caller naming the parameter, rather than being flattened into "the draft failed".
    """
    from just_module_creator.tools import proxy

    class _Fussy:
        def draft(self, spec_dir, **kwargs):
            if kwargs.get("source") == "clinvar" and "min_evidence_level" in kwargs:
                raise RuntimeError(
                    "422 unsupported_parameter: min_evidence_level is not read by clinvar"
                )
            raise AssertionError("expected the refusal")

    monkeypatch.setattr(proxy, "client_for", lambda *_a, **_k: _Fussy())
    (tmp_path / "module_spec.yaml").write_text("module:\n  name: x\n")

    async with make_client(offline_settings()) as client:
        result = await client.call_tool(
            "remote_draft",
            {
                "spec_dir": str(tmp_path),
                "source": "clinvar",
                "min_evidence_level": "1A",
            },
            raise_on_error=False,
        )
    text = str(result.content)
    assert "min_evidence_level" in text
    assert "refusal rather than a dropped filter" in text


@needs_proxy
async def test_remote_draft_names_the_lane_a_deployment_lacks(
    monkeypatch, make_client, tmp_path
):
    """`503 snapshot_unavailable` naming a lane is a different failure from the tier
    being absent, and only one of the two is fixed by provisioning.

    So the error text has to carry the lane through and point at `registry_caches`,
    rather than collapsing both into "the registry could not draft".
    """
    from just_module_creator.tools import proxy

    class _Unprovisioned:
        def draft(self, spec_dir, **kwargs):
            raise RuntimeError("503 snapshot_unavailable: civic")

    monkeypatch.setattr(proxy, "client_for", lambda *_a, **_k: _Unprovisioned())
    (tmp_path / "module_spec.yaml").write_text("module:\n  name: x\n")

    async with make_client(offline_settings()) as client:
        result = await client.call_tool(
            "remote_draft",
            {"spec_dir": str(tmp_path), "source": "civic"},
            raise_on_error=False,
        )
    text = str(result.content)
    assert "civic" in text
    assert "registry_caches" in text
    assert "build_command" in text


@needs_proxy
async def test_a_draft_archive_writes_only_recognised_spec_files(
    monkeypatch, make_client, tmp_path
):
    """A third party's tar: a member outside the recognised set has nowhere to land.

    Asserted through the tool rather than on the helper, because it is the write that
    matters — the containment is pointless if the write path does not honour it.
    """
    import json as _json

    from just_module_creator.tools import proxy

    payload = {
        "variants.csv": b"variant_key,genotype\n2-135851076-G-A,A/A\n",
        "../../escaped.csv": b"nope",
        "draft-report.json": _json.dumps(
            {"added": 1, "already_present": 0, "differs": 0, "needs_curation": ["variants.csv"]}
        ).encode(),
    }
    archive = _archive(payload)

    class _Stub:
        def draft(self, spec_dir, **kwargs):
            return archive

    monkeypatch.setattr(proxy, "client_for", lambda *_a, **_k: _Stub())
    (tmp_path / "module_spec.yaml").write_text("module:\n  name: x\n")

    async with make_client(offline_settings()) as client:
        result = await client.call_tool(
            "remote_draft",
            {"spec_dir": str(tmp_path), "source": "clinvar", "dry_run": False},
        )
    report = result.data

    assert report.installed == ["variants.csv"]
    assert report.added == 1
    assert report.needs_curation == ["variants.csv"]
    assert not (tmp_path.parent.parent / "escaped.csv").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["module_spec.yaml", "variants.csv"]


@needs_proxy
async def test_an_archive_with_no_report_counts_zero_and_says_it_did_not_describe_itself(
    monkeypatch, make_client, tmp_path
):
    """Empty is not zero, and the counts cannot be recovered from the merged result.

    `already_present` and `differs` are about the merge the server performed; reading
    them off the rows that came back would invent them.
    """
    from just_module_creator.tools import proxy

    class _Terse:
        def draft(self, spec_dir, **kwargs):
            return _archive({"variants.csv": b"variant_key,genotype\n2-135851076-G-A,A/A\n"})

    monkeypatch.setattr(proxy, "client_for", lambda *_a, **_k: _Terse())
    (tmp_path / "module_spec.yaml").write_text("module:\n  name: x\n")

    async with make_client(offline_settings()) as client:
        result = await client.call_tool(
            "remote_draft", {"spec_dir": str(tmp_path), "source": "clinvar"}
        )
    report = result.data
    assert (report.added, report.already_present, report.differs) == (0, 0, 0)
    assert report.needs_curation == []
    assert report.dry_run is True
    assert report.installed == [], "a dry run writes nothing"
