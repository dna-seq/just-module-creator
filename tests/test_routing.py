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
    tables, extras = _unpack(archive)

    assert set(tables) == {"resolution.csv"}
    assert "check.json" in extras and "WHERE-THIS-CAME-FROM.md" in extras
    assert not any("evil" in name for name in tables)


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
