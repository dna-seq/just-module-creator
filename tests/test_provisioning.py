"""What the cache offer says, and — mostly — when it says nothing at all.

The interesting half of this feature is the refusals: an offer withheld because the cache
directory is unset, a lane never named because it does not fit, a second offer never made
to somebody who declined the first. Each of those is a sentence somebody would otherwise
have to read at a prompt, so each gets a test.

Every test here works on a `tmp_path`, and the two that need a machine state this box does
not have build it out of upstream's own `LaneStatus`. **Nothing touches the real cache
directory**: it holds 14 GB of Ensembl and a `du` over it is not a unit test.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from conftest import offline_settings

from just_module_creator import provisioning, routing
from just_module_creator.models import CachePlanLane

pytestmark = pytest.mark.skipif(
    not routing.LANES_KNOWN,
    reason="needs just_dna_enricher.caches (the lane registry, enricher 0.7)",
)


@dataclass(frozen=True)
class _Status:
    """Upstream's `LaneStatus` shape, as this layer reads it — name, state, path, release."""

    lane: object
    state: str
    path: Path | None = None
    release: str | None = None
    release_unreadable: bool = False
    looked_in: Path | None = None


def _empty_box(monkeypatch, tmp_path: Path, *, free_mb: float = 5000.0) -> None:
    """A machine with the cache directory set, configured, and holding nothing."""
    monkeypatch.setenv(provisioning.CACHE_DIR_VAR, str(tmp_path))
    monkeypatch.setattr(provisioning, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(provisioning, "free_mb_at", lambda _path: free_mb)
    # Real `tmp_path`, so usability is answered by the filesystem rather than faked.
    monkeypatch.setattr(
        provisioning,
        "lane_status",
        lambda *_a, **_k: [_Status(lane=lane, state="absent") for lane in routing.CACHE_LANES],
    )


def test_the_offer_is_the_lanes_nothing_publishes(monkeypatch, tmp_path):
    """The prewarm set is derived from the route, never from a list of names.

    A lane with an `ensure` is published parquet — pull it, or let a proxy answer. A lane
    without one carries the reason in `unpublished`, and building is the only route there
    will ever be. So the set is *whatever has no pull*, and it must still be non-empty
    here or the assertion below is a subset check over nothing.
    """
    _empty_box(monkeypatch, tmp_path)
    plan = provisioning.plan(settings=offline_settings())

    assert plan.prewarm_lanes, "no lane classified as build-only; the route ladder moved"
    buildable = {lane.name for lane in routing.CACHE_LANES if lane.ensure is None and lane.rebuild}
    assert set(plan.prewarm_lanes) <= buildable
    # Anchored on a member that must be there: ACMG is Elsevier supplementary material
    # and there is nowhere for it to be published from, so a plan that drops it has
    # stopped answering the question this feature was built for.
    assert "acmg" in plan.prewarm_lanes
    for row in plan.lanes:
        if row.lane in plan.prewarm_lanes:
            assert row.route == "build"
            assert row.state == "absent"


def test_a_derived_lane_prices_the_parent_it_pins_separately(monkeypatch, tmp_path):
    """13 MB built and 270 MB downloaded are two numbers, and one of them is the surprise.

    `mitomap_miss` is 0.06 MB built and pins ClinVar. Reporting one total would let an
    offer that says *"about 12 MB"* start a quarter-gigabyte download.
    """
    _empty_box(monkeypatch, tmp_path)
    plan = provisioning.plan(settings=offline_settings())

    assert plan.prewarm_build_mb < plan.prewarm_pull_mb
    assert plan.prewarm_mb == pytest.approx(plan.prewarm_build_mb + plan.prewarm_pull_mb, abs=0.2)
    derived = next(r for r in plan.lanes if r.lane == "mitomap_miss")
    assert "clinvar" in derived.parents_absent
    assert derived.total_mb is not None and derived.estimate_mb is not None
    assert derived.total_mb > derived.estimate_mb * 100


def test_an_unset_cache_directory_still_gets_the_offer(monkeypatch, tmp_path):
    """**Nobody sets an environment variable as their first act**, and this used to require it.

    The offer was withheld until `JUST_DNA_PIPELINES_CACHE_DIR` was configured, which made
    it conditional on the one thing an author has no reason to have done — a developer's
    mindset wearing a prompt. Unset means the place the resolvers already use, and the
    15 MB set fits there. The location is reported, and moving it is a suggestion before a
    multi-gigabyte pull rather than a step to take first.
    """
    _empty_box(monkeypatch, tmp_path)
    monkeypatch.delenv(provisioning.CACHE_DIR_VAR, raising=False)
    plan = provisioning.plan(settings=offline_settings())

    assert plan.cache_dir_configured is False
    assert plan.offer_withheld is None
    assert plan.offer == "prewarm"
    assert plan.prewarm_lanes
    # The fact is reported, with the variable named for whoever does want to move them.
    assert plan.cache_dir and plan.cache_dir in plan.note
    assert any(provisioning.CACHE_DIR_VAR in line for line in plan.record_with)


def test_a_cache_directory_that_cannot_be_written_withholds_and_names_what_is_in_the_way(
    monkeypatch, tmp_path
):
    """The real blocker, and it is a path rather than a missing variable.

    Some boxes keep a read-only **file** at the platformdirs location on purpose, so an
    unconfigured run raises instead of quietly filling the root filesystem. An author who
    meets that needs the obstruction named and one `.env` line — not a prerequisite.
    """
    blocked = tmp_path / "in-the-way"
    blocked.write_bytes(b"not a directory")
    monkeypatch.setenv(provisioning.CACHE_DIR_VAR, str(blocked))
    monkeypatch.setattr(provisioning, "cache_root", lambda: blocked)
    monkeypatch.setattr(
        provisioning,
        "lane_status",
        lambda *_a, **_k: [_Status(lane=lane, state="absent") for lane in routing.CACHE_LANES],
    )
    plan = provisioning.plan(settings=offline_settings())

    assert plan.cache_dir_usable is False
    assert plan.offer is None
    assert plan.offer_withheld
    assert str(blocked) in plan.offer_withheld
    assert provisioning.CACHE_DIR_VAR in plan.offer_withheld


def test_usability_is_three_valued_and_a_first_run_creates_the_directory(tmp_path):
    """A directory that does not exist yet is usable — that is the ordinary first run."""
    assert provisioning.cache_dir_usable(tmp_path / "not-yet") is True
    assert provisioning.cache_dir_usable(tmp_path) is True
    blocked = tmp_path / "file"
    blocked.write_bytes(b"x")
    assert provisioning.cache_dir_usable(blocked) is False
    assert provisioning.cache_dir_usable(None) is None


def test_a_lane_too_large_for_the_disk_is_reported_and_never_offered(monkeypatch, tmp_path):
    """Twenty gigabytes of Ensembl on an eight-gigabyte volume is the canonical nag."""
    _empty_box(monkeypatch, tmp_path, free_mb=8_000.0)
    plan = provisioning.plan(settings=offline_settings())

    ensembl = next(r for r in plan.lanes if r.lane == "ensembl")
    assert ensembl.fits is False
    assert "ensembl" not in plan.full_lanes
    assert any(line.startswith("ensembl:") for line in plan.too_large)
    # Reported rather than hidden: the answer is a bigger volume, not a smaller ask.
    assert "8000.0" in " ".join(plan.too_large)


def test_free_space_is_never_read_off_the_wrong_volume(tmp_path):
    """`None` beats a number measured on a different disk, and the unmounted case is real.

    The cache directory is normally the thing that has not been created yet, so this walks
    up to the nearest ancestor that exists — but it **stops before `/`**. A variable
    pointing into an unmounted volume (`/mnt/big/cache` with `/mnt/big` not mounted) would
    otherwise be priced against the root filesystem, which is the disk the variable exists
    to keep a 14 GB snapshot off.
    """
    assert provisioning.free_mb_at(None) is None
    assert provisioning.free_mb_at(Path("/nonexistent-mount-xyz/cache")) is None
    # A directory that does not exist yet under one that does is the ordinary first run,
    # and it is answerable: the volume is the parent's.
    assert provisioning.free_mb_at(tmp_path / "cache" / "deep") is not None
    # A cache directory really at the root is the one case where `/` is the answer.
    assert provisioning.free_mb_at(Path("/")) is not None


def test_fits_is_three_valued():
    """A lane nobody could price and a disk nobody could read are both `None`, not `False`."""
    assert provisioning._fits(None, 5000.0) is None
    assert provisioning._fits(10.0, None) is None
    assert provisioning._fits(10.0, 5000.0) is True
    assert provisioning._fits(10_000.0, 5000.0) is False
    # Headroom, not equality: a disk that fits the estimate exactly does not fit it.
    assert provisioning._fits(1000.0, 1000.0) is False


def test_a_declined_small_offer_is_never_escalated_to_the_big_one():
    """The escalation a helpful agent would make, and the one this refuses.

    Someone who said no to 12 MB is not asked about 14 GB. A refusal answers whether they
    want caches at all.
    """
    declined = offline_settings(cache_prewarm=False)
    assert (
        provisioning._offer(
            withheld=None, prewarm=["acmg"], full=["clinvar"], settings=declined
        )
        is None
    )
    # And with the small set done — nothing left to build — the second offer does arrive.
    accepted = offline_settings(cache_prewarm=True)
    assert (
        provisioning._offer(withheld=None, prewarm=[], full=["clinvar"], settings=accepted)
        == "full"
    )
    # Answered is answered, both ways.
    answered = offline_settings(cache_prewarm=True, cache_full=False)
    assert (
        provisioning._offer(withheld=None, prewarm=[], full=["clinvar"], settings=answered)
        is None
    )


def test_an_unset_preference_is_asked_once_and_a_withheld_offer_outranks_it():
    unasked = offline_settings()
    assert unasked.cache_prewarm is None, "an unset preference must not default to a boolean"
    assert (
        provisioning._offer(withheld=None, prewarm=["acmg"], full=[], settings=unasked)
        == "prewarm"
    )
    assert (
        provisioning._offer(
            withheld="the directory is unset", prewarm=["acmg"], full=[], settings=unasked
        )
        is None
    )


def test_a_provisioned_lane_reports_what_it_measures_beside_the_estimate(monkeypatch, tmp_path):
    """The estimate is dated and ours; the measurement is the machine's, and both are shown.

    A size drifts faster than a name does — ClinVar grows every release — so a present
    lane's real number must never be replaced by the constant in our source.
    """
    lane = next(lane for lane in routing.CACHE_LANES if lane.name == "acmg")
    here = tmp_path / "acmg_sf"
    here.mkdir()
    (here / "acmg_sf.parquet").write_bytes(b"x" * 4096)
    monkeypatch.setenv(provisioning.CACHE_DIR_VAR, str(tmp_path))
    monkeypatch.setattr(provisioning, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(provisioning, "free_mb_at", lambda _p: 5000.0)
    monkeypatch.setattr(
        provisioning,
        "lane_status",
        lambda *_a, **_k: [
            _Status(lane=lane, state="present", path=here, release="acmg_sf_v3.3")
            if other.name == "acmg"
            else _Status(lane=other, state="absent")
            for other in routing.CACHE_LANES
        ],
    )
    plan = provisioning.plan(settings=offline_settings())

    row = next(r for r in plan.lanes if r.lane == "acmg")
    assert row.route == "present"
    assert row.measured_mb == pytest.approx(4096 / 1024 / 1024, abs=0.0005)
    assert row.estimate_mb is not None and row.estimate_basis
    assert row.release == "acmg_sf_v3.3"
    assert "acmg" not in plan.prewarm_lanes


def test_an_occupied_directory_is_neither_present_nor_absent(monkeypatch, tmp_path):
    """Provisioning refuses to build over it, so the plan must not call it absent.

    `absent` sends an operator to run a build that `prepare_lane` is going to decline;
    `occupied` sends them to move the directory aside, which is the fix.
    """
    lane = next(lane for lane in routing.CACHE_LANES if lane.name == "mane")
    stray = tmp_path / "mane"
    monkeypatch.setenv(provisioning.CACHE_DIR_VAR, str(tmp_path))
    monkeypatch.setattr(provisioning, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(provisioning, "free_mb_at", lambda _p: 5000.0)
    monkeypatch.setattr(
        provisioning,
        "lane_status",
        lambda *_a, **_k: [
            _Status(lane=lane, state="occupied", path=stray)
            if other.name == "mane"
            else _Status(lane=other, state="absent")
            for other in routing.CACHE_LANES
        ],
    )
    plan = provisioning.plan(settings=offline_settings())

    row = next(r for r in plan.lanes if r.lane == "mane")
    assert row.state == "occupied"
    assert row.occupied_path == str(stray)
    assert "occupied" in plan.note.lower() and "mane" in plan.note
    assert "prune" in plan.note


def test_every_lane_field_this_layer_reads_is_still_a_lane_field():
    """Read by name off upstream's dataclass, so a rename here fails loudly rather than quietly.

    Anchored on a field that must be present — a `getattr` sweep over a renamed class
    returns nothing and an all-absent check would pass.
    """
    fields = {f for lane in routing.CACHE_LANES for f in vars(lane)}
    assert "name" in fields, "CacheLane no longer exposes its own fields by name"
    for needed in (
        "name",
        "serves",
        "ensure",
        "rebuild",
        "unpublished",
        "unbuilt",
        "parents",
        "build_command",
        "env_var",
        "default_dir",
        "terms",
    ):
        assert needed in fields, f"CacheLane.{needed} moved; provisioning.py reads it"


def test_every_estimate_names_a_lane_that_exists():
    """A dated constant with no live counterpart is a lane that was renamed under us.

    The reverse — a lane with no estimate — is legitimate and reports `None`, so it is not
    asserted: `alphagenome_avi` is priced from the producer's own prose because no box here
    has ever held it.
    """
    live = {lane.name for lane in routing.CACHE_LANES}
    stale = (set(provisioning._LANE_KB) | set(provisioning._DECLARED_KB)) - live
    assert not stale, f"estimates for lanes that no longer exist: {sorted(stale)}"


def test_a_row_carries_the_producers_own_sentence_for_a_lane_with_no_route(monkeypatch, tmp_path):
    """Ensembl is built by just-dna-pipelines, and saying so is better than saying nothing."""
    _empty_box(monkeypatch, tmp_path, free_mb=8_000.0)
    plan = provisioning.plan(settings=offline_settings())

    ensembl = next(r for r in plan.lanes if r.lane == "ensembl")
    assert ensembl.caution and "just-dna-pipelines" in ensembl.caution
    alphagenome = next(r for r in plan.lanes if r.lane == "alphagenome_avi")
    assert alphagenome.caution and "sign-in" in alphagenome.caution
    assert "alphagenome_avi" not in plan.full_lanes
    # On this 8 GB volume it is out on size, and that is the reason reported.
    assert any(line.startswith("alphagenome_avi:") for line in plan.too_large)


def test_an_artifact_the_operator_accepts_themselves_is_not_offered_even_where_it_fits(
    monkeypatch, tmp_path
):
    """The ceiling, and why it is not a size rule wearing a number.

    Give the box four terabytes and AlphaGenome's 88.5 GB artifact *fits* — and it is
    still not offered, because upstream records it as taken under the operator's own
    acceptance of a sign-in whose eligibility clause bars classes of holder. A prompt
    cannot accept terms on somebody's behalf. It is reported with its reason instead, so a
    caller who wants it can name the lane.
    """
    _empty_box(monkeypatch, tmp_path, free_mb=4_000_000.0)
    plan = provisioning.plan(settings=offline_settings())

    alphagenome = next(r for r in plan.lanes if r.lane == "alphagenome_avi")
    assert alphagenome.fits is True
    assert "alphagenome_avi" not in plan.full_lanes
    assert any(line.startswith("alphagenome_avi:") for line in plan.unavailable)
    assert plan.too_large == []
    # And Ensembl's 14 GB is inside the ceiling, so a box with room is offered it.
    assert "ensembl" in plan.full_lanes


def test_terms_that_forbid_sale_are_skipped_rather_than_assumed(monkeypatch, tmp_path):
    """`unstated` is not permission, and the plan must not offer what the fetch would skip."""
    _empty_box(monkeypatch, tmp_path)
    unstated = provisioning.plan(declared_use="unstated", settings=offline_settings())
    declared = provisioning.plan(declared_use="non_commercial", settings=offline_settings())

    skipped = {r.lane for r in unstated.lanes if r.licence_skip}
    assert skipped, "no lane's terms gate an unstated fetch; upstream's ladder moved"
    assert not skipped & set(unstated.full_lanes)
    # The same lanes become offerable once a purpose is declared — which is the author's
    # word to give, never ours.
    assert skipped <= set(declared.full_lanes)


def test_an_unmeasurable_install_says_so_rather_than_reporting_no_lanes(monkeypatch):
    """`lanes_known=false` is not an empty plan: one is a missing instrument, the other a fact."""
    monkeypatch.setattr(provisioning, "LANES_KNOWN", False)
    plan = provisioning.plan(settings=offline_settings())

    assert plan.lanes_known is False
    assert plan.lanes == []
    assert plan.offer is None
    assert "predates" in plan.note


def test_the_model_keeps_null_apart_from_false():
    """A defaulted row must not answer questions nobody asked."""
    row = CachePlanLane(lane="x", route="none")
    assert row.fits is None
    assert row.state is None
    assert row.estimate_mb is None


async def test_the_tool_reads_the_plan_and_refuses_to_build_under_the_offline_ceiling(
    client, monkeypatch, tmp_path
):
    """Two properties of the wire surface, and the second is the one that matters.

    A plan is read-only, so it runs under `JMC_OFFLINE` — that is what makes it safe to
    call at the top of every session. **Provisioning is egress**: a pull downloads and four
    of the five buildable lanes fetch their own inputs, so `dry_run=false` is refused under
    the ceiling rather than half-running. The suite's client is offline by construction.
    """
    monkeypatch.setenv(provisioning.CACHE_DIR_VAR, str(tmp_path))
    monkeypatch.setattr(provisioning, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(provisioning, "free_mb_at", lambda _p: 5000.0)

    read = await client.call_tool("provision_caches", {})
    assert read.data.lanes_known is routing.LANES_KNOWN

    with pytest.raises(Exception, match="JMC_OFFLINE"):
        await client.call_tool("provision_caches", {"dry_run": False})


def test_a_build_lane_is_gated_by_its_terms_too(monkeypatch, tmp_path):
    """The offer must not name a lane whose *build* upstream would decline.

    A build takes bytes as surely as a download does, and upstream's gate runs inside
    `rebuild_lane` as well as before an `ensure` — PharmVar forbids sale, so on an
    undeclared run its build is skipped. Checking only the pull would put it in the offer
    and have the build refuse it.
    """
    _empty_box(monkeypatch, tmp_path)
    undeclared = provisioning.plan(declared_use="unstated", settings=offline_settings())
    declared = provisioning.plan(declared_use="non_commercial", settings=offline_settings())

    assert "pharmvar" not in undeclared.prewarm_lanes
    assert "pharmvar" in declared.prewarm_lanes
    row = next(r for r in undeclared.lanes if r.lane == "pharmvar")
    assert row.route == "build" and row.licence_skip


def test_the_second_offer_survives_a_lane_that_can_never_be_built(monkeypatch, tmp_path):
    """Accepted, not exhausted — and on a PyPI install those are different states.

    `acmg` builds from a workbook that ships in the format checkout and not in the wheel,
    so on most installs it stays absent and buildable for ever. A second offer gated on an
    *empty* small set would never arrive there.
    """
    accepted = offline_settings(cache_prewarm=True)
    assert (
        provisioning._offer(
            withheld=None, prewarm=["acmg"], full=["clinvar"], settings=accepted
        )
        == "full"
    )


def test_the_status_shape_this_suite_fakes_is_still_upstreams_shape():
    """A stub that has drifted from the dataclass passes the suite and fails live."""
    from dataclasses import fields

    from just_dna_enricher.caches import LaneStatus

    upstream = {field.name for field in fields(LaneStatus)}
    assert "state" in upstream, "LaneStatus no longer exposes its fields by name"
    assert {"lane", "state", "path", "release"} <= upstream


def test_the_size_comes_from_the_lane_when_the_install_declares_one():
    """Ours is the fallback, and which one answered is reported rather than assumed.

    `S97` asked for an order of magnitude on the lane and upstream added `approx_mb` the
    same afternoon — in their tree. `main` installs from PyPI, where the whole module is
    absent, so this reads the attribute and keeps the measured table for every install
    without it.
    """
    lane = next(lane for lane in routing.CACHE_LANES if lane.name == "clinvar")
    kb, basis = provisioning._kb_for(lane)
    assert kb and basis
    declared = getattr(lane, "approx_mb", None)
    if declared is not None:
        assert basis and "approx_mb" in basis
        assert kb == int(declared) * 1024
    else:
        assert basis and "measured" in basis
    # Asked by name — all a parent lane gives us — the fallback answers and says so.
    by_name_kb, by_name_basis = provisioning._kb_for("clinvar")
    assert by_name_kb == provisioning._LANE_KB["clinvar"]
    assert by_name_basis and "measured" in by_name_basis
