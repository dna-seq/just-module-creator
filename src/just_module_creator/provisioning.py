"""What provisioning the snapshot caches on THIS machine would cost, and doing it.

The enricher's lookups read fifteen snapshot lanes, and five of them cannot be pulled
from anywhere: PharmVar's bulk data is behind a personal key, PubMind's ANNOVAR table
states no terms, `mitomap_miss` is a join nobody publishes, NCBI states a policy rather
than a licence for MANE, and the ACMG SF list is Elsevier supplementary material. Each
carries that sentence in `lane.unpublished`, and each has a local build route instead.

**Those five are the set worth offering at the top of a session.** They are ~15 MB
together, they are the lanes a registry proxy cannot serve either — so a thin client is
not a substitute — and building them here costs one command instead of a metered round
trip per question for the rest of the session.

**The route is never ours to choose.** `lane.ensure` means published, so pulling is
right; no `ensure` and a `rebuild` means building is the only route there will ever be.
Upstream's `prepare_lane` already encodes that ladder, licence check included, and this
module calls it rather than restating it. What is ours is the part upstream does not
answer: *does it fit, what does it cost, and should the author be asked at all.*
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import CachePlan, CachePlanLane
from just_module_creator.routing import CACHE_LANES, LANES_KNOWN
from just_module_creator.settings import Settings

#: The provisioning half of the lane registry, guarded exactly as `routing` guards
#: `CACHE_LANES` and for the same measured reason: `just_dna_enricher.caches` is a whole
#: MODULE that `just-dna-enricher>=0.6.6` does not have, so an unguarded import takes the
#: server down at start-up rather than failing later as a missing attribute. The names are
#: `None` on that toolchain and `LANES_KNOWN` is what every caller here branches on, so
#: the two cannot disagree.
try:
    from just_dna_enricher.caches import (
        LicenseRefusal,
        RebuildRequest,
        check_declared_use,
        lane_status,
        parent_snapshots,
        prepare_lane,
    )
except ImportError:  # pragma: no cover — only on a pre-0.7 enricher
    LicenseRefusal = None  # type: ignore[assignment,misc]
    RebuildRequest = None  # type: ignore[assignment,misc]
    check_declared_use = None  # type: ignore[assignment]
    lane_status = None  # type: ignore[assignment]
    parent_snapshots = None  # type: ignore[assignment]
    prepare_lane = None  # type: ignore[assignment]

#: A second guarded import, for a different fact: `provisioning_closure` is upstream's
#: `S97` answer and landed hours after the module it lives in, so an install can have the
#: lane registry and not this. Folding it into the block above would null every name when
#: only this one is missing. Delete the fallback when the floor names a release with it.
try:
    from just_dna_enricher.caches import provisioning_closure
except ImportError:  # pragma: no cover — a 0.7 enricher predating S97
    provisioning_closure = None  # type: ignore[assignment]

log = get_logger()

#: The ecosystem's own variable for where every lane lives. Read, never forwarded (§5):
#: we are the one deciding whether to make an offer, and an unset value is the one case
#: where measuring a disk would measure the wrong one. The lanes' `default_dir()` is
#: still what says where they go — this only answers *was it configured*.
CACHE_DIR_VAR = "JUST_DNA_PIPELINES_CACHE_DIR"

#: Measured, dated, and the command that produced it, because **no lane declares a
#: size**: `CacheLane` carries fifteen fields about whether and how, and none about how
#: much (filed upstream as `S97`, asking for an order of magnitude on the lane).
#:
#:   du -sk --apparent-size /data/just-dna-cache/*/     # 2026-09-11, enricher 0.7.0
#:
#: Kilobytes as measured, so the small lanes keep a real number instead of rounding to
#: zero. **A size drifts faster than a name does** — ClinVar grows every release — so
#: this is reported as an *estimate* beside whatever a present lane actually measures,
#: never in place of it, and a lane missing from here reports `None` rather than a guess.
_LANE_KB: dict[str, int] = {
    "acmg": 13,
    "civic": 32,
    "clinpgx": 588,
    "clinvar": 276_528,
    "constraint": 855,
    "cpic": 257,
    "drug_labels": 48,
    "ensembl": 14_382_879,
    "mane": 2_003,
    "mitomap": 593,
    "mitomap_miss": 65,
    "pharmvar": 39,
    "pubmind": 10_280,
    "strchive": 494,
}

#: `alphagenome_avi` is the one lane no box here has ever held, so it is not in the table
#: above and its number is not ours: upstream's own terms note states 88.5 GB. Kept apart
#: rather than folded in, because "somebody else wrote this down" and "we measured it on
#: this machine" are different claims and the caller is told which one they got.
_DECLARED_KB: dict[str, int] = {"alphagenome_avi": 88_500 * 1024}

#: Headroom, because a disk that fits a download exactly does not fit it. Twenty percent
#: over the estimate and never less than 256 MB of slack — the estimate is stale by
#: construction and a snapshot is unpacked beside its download.
_MARGIN = 1.2
_MIN_SLACK_MB = 256.0

#: The size above which a lane is **reported with its cost instead of offered**, even on a
#: volume with room for it. Twenty gigabytes, which puts Ensembl (14 GB) inside the offer —
#: it is the lane `enrich` cannot work without, and a workstation provisioning the full
#: surface wants it — and holds AlphaGenome's AVI artifact (88.5 GB) out of it.
#:
#: **The reason is not the number; the number is where the reason bites.** At this size the
#: fetch stops being a yes/no at a prompt and becomes an operator's deliberate act, and
#: upstream records AlphaGenome's as exactly that: the artifact is *"behind a sign-in whose
#: eligibility clause bars classes of holder outright"*, taken *"under their own
#: acceptance"*. A prompt cannot accept terms on somebody's behalf, and one that offered to
#: is worse than one that stayed quiet. So the lane still appears — in `ask_first`, with its
#: price — and is provisioned only when a caller names it.
_OFFER_CEILING_MB = 20 * 1024.0


def _kb_for(lane: Any | str) -> tuple[int | None, str | None]:
    """The lane's own declared size when it has one, else our dated measurement.

    **`approx_mb` is why the table below is a fallback rather than the answer.** `S97`
    asked for an order of magnitude on the lane and upstream added the field the same
    afternoon — but `main` installs from PyPI, where the whole `caches` module is absent,
    so this reads the attribute rather than a version and keeps the measurement for every
    install that does not have it. Deleting the table is gated on the **release**, never
    on the symbol being in their tree.

    A string is accepted for a parent named by another lane, where only the name is to
    hand; it takes the fallback path, which is the honest limit of asking by name.
    """
    declared = getattr(lane, "approx_mb", None)
    if declared is not None:
        return int(declared) * 1024, "declared by the lane (approx_mb)"
    name = lane if isinstance(lane, str) else lane.name
    if name in _LANE_KB:
        return _LANE_KB[name], "measured on a provisioned box, 2026-09-11"
    if name in _DECLARED_KB:
        return _DECLARED_KB[name], "stated by the producer, not measured here"
    return None, None


#: Three decimals, not two. The smallest lane is 13 KB and rounding to two would report
#: `0.0 MB` — a number that reads as "nothing measured this" for the lanes this whole
#: feature is about. The estimates are held in kilobytes for the same reason.
_MB_PLACES = 3


def _mb(kb: int | None) -> float | None:
    return None if kb is None else round(kb / 1024, _MB_PLACES)


def cache_root() -> Path | None:
    """Where the lanes actually go, taken from the resolver rather than from the variable.

    `lane.default_dir()` is the same call the resolvers make, so this cannot name a
    directory the enricher ignores — which is exactly what reconstructing
    ``$CACHE_DIR/<lane>`` would do for `constraint` (`gnomad_constraint`) and `acmg`
    (`acmg_sf`). ``None`` when there are no lanes to ask, i.e. a pre-0.7 enricher.
    """
    parents = {lane.default_dir().parent for lane in CACHE_LANES}
    if len(parents) != 1:
        return None
    return next(iter(parents))


def free_mb_at(path: Path | None) -> float | None:
    """Free space on the volume that would hold ``path``, or ``None`` if unanswerable.

    Walks up to the nearest ancestor that exists, because the cache directory itself is
    usually the thing that has not been created yet and `disk_usage` on a missing path
    raises.

    **It stops before ``/``, and that is not fussiness.** `JUST_DNA_PIPELINES_CACHE_DIR`
    pointing into an unmounted volume — ``/mnt/big/cache`` with ``/mnt/big`` not mounted —
    walks all the way up, and answering with the root filesystem's free space would offer
    a 14 GB snapshot against the disk the variable exists to keep it off. So a path whose
    only existing ancestor is ``/`` reports ``None``, the offer is withheld, and nobody is
    asked a question priced on the wrong volume. A cache directory that really is at the
    root is the one case where ``/`` is the answer, and it is passed through.
    """
    if path is None:
        return None
    root = Path(path.anchor or "/")
    for candidate in (path, *path.parents):
        if candidate == root and path != root:
            return None
        if candidate.exists():
            try:
                return round(shutil.disk_usage(candidate).free / 1024 / 1024, 1)
            except OSError:  # pragma: no cover — a vanished mount between the two calls
                return None
    return None


def _measured_mb(path: Path | None) -> float | None:
    if path is None or not path.is_dir():
        return None
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return round(total / 1024 / 1024, _MB_PLACES)


def _closure(lane: Any) -> tuple[str, ...]:
    """Every lane this one needs before it can be built, transitively, excluding itself.

    `lane.parents` is one level. A grandparent is not hypothetical — `mitomap_miss` pins
    ClinVar today and a future derived lane pinning *it* would be priced at a megabyte —
    so upstream's own `provisioning_closure` is used where the install has it (their `S97`
    answer, same afternoon) and `parents` is the fallback that names what it can.
    """
    if provisioning_closure is None:
        return tuple(lane.parents or ())
    return tuple(item.name for item in provisioning_closure(lane) if item.name != lane.name)


def _route_for(lane: Any, present: bool) -> tuple[str, str | None]:
    """Which of upstream's four routes this lane has, and why it has none.

    Mirrors `prepare_lane`'s own ladder in the same order — present, then `ensure`, then
    `rebuild`, then nothing — so a plan cannot promise a route the provisioner would
    then decline. It is read off the lane rather than off a list of names, because the
    licensing story that decides it is upstream's to tell and changes per release.
    """
    if present:
        return "present", None
    if lane.ensure is not None:
        return "pull", None
    if lane.rebuild is not None:
        return "build", None
    return "none", lane.unbuilt or lane.unpublished or "no route on this install"


def _fits(cost_mb: float | None, free: float | None) -> bool | None:
    """Three-valued: fits, does not fit, or **nobody could measure it**.

    A missing estimate and a missing disk reading both give ``None``, and ``None`` is not
    ``False`` — an unmeasurable lane is not one that failed to fit, and an offer made on
    it would be an offer nobody priced.
    """
    if cost_mb is None or free is None:
        return None
    return free >= cost_mb * _MARGIN + _MIN_SLACK_MB


def plan(*, declared_use: str = "unstated", settings: Settings | None = None) -> CachePlan:
    """Price every lane on this machine, and say which offer is still open.

    Read-only: nothing is downloaded, nothing is written, and no lane directory is
    created. Safe to call on every session start, which is what the onboarding flow does.
    """
    # Narrowed on the symbols rather than on `LANES_KNOWN` alone, which is the same fact
    # said twice: the guarded import left them `None` on a pre-0.7 enricher, and a check
    # against the thing actually used cannot drift away from the thing actually imported.
    if (
        not LANES_KNOWN
        or lane_status is None
        or check_declared_use is None
        or LicenseRefusal is None
    ):
        return CachePlan(
            lanes_known=False,
            note=(
                "The installed just-dna-enricher predates the lane registry, so which "
                "caches exist cannot be enumerated here — which is not the same answer "
                "as there being none. Nothing was measured and nothing is offered."
            ),
        )

    root = cache_root()
    configured = bool(os.environ.get(CACHE_DIR_VAR, "").strip())
    free = free_mb_at(root)
    state_by_lane = {
        (status.lane.name if hasattr(status.lane, "name") else str(status.lane)): status
        for status in lane_status()
    }

    by_name = {lane.name: lane for lane in CACHE_LANES}
    rows: list[CachePlanLane] = []
    for lane in CACHE_LANES:
        status = state_by_lane.get(lane.name)
        state = getattr(status, "state", None)
        path = getattr(status, "path", None)
        present = state == "present"
        route, why_none = _route_for(lane, present)

        # **Both routes are gated, not just the pull.** Upstream runs the declared-use
        # gate inside `rebuild_lane` as well as before an `ensure`, because a build takes
        # bytes too — PharmVar's terms forbid sale, so on an undeclared run its *build* is
        # skipped exactly as a download would be. Checking only the pull would put
        # PharmVar in the offer and have the build decline it, which is the surface
        # teaching a step it cannot run.
        skip: str | None = None
        if route in ("pull", "build") and lane.terms is not None:
            try:
                skip = check_declared_use(lane.terms, declared_use)
            except LicenseRefusal as exc:
                # Caught by type: a typo in `declared_use` raises from the vocabulary
                # checker, and swallowing that here would report every terms-bearing lane
                # as licence-skipped instead of failing the call.
                skip = f"refused: {exc}"

        kb, basis = _kb_for(lane)
        cost = _mb(kb)
        parent_cost = 0.0
        parents_needed: list[str] = []
        for parent in _closure(lane):
            parent_status = state_by_lane.get(parent)
            if getattr(parent_status, "state", None) == "present":
                continue
            parents_needed.append(parent)
            parent_kb, _ = _kb_for(by_name.get(parent, parent))
            parent_cost += _mb(parent_kb) or 0.0

        total = None if cost is None else round(cost + parent_cost, 2)
        rows.append(
            CachePlanLane(
                lane=lane.name,
                serves=lane.serves,
                state=state,
                route=route,
                why_no_route=why_none,
                caution=lane.unbuilt if route == "pull" else None,
                licence_skip=skip,
                estimate_mb=cost,
                estimate_basis=basis,
                measured_mb=_measured_mb(path) if present else None,
                parents_absent=parents_needed,
                parents_mb=round(parent_cost, 2) if parents_needed else None,
                total_mb=total,
                fits=_fits(total, free),
                build_command=lane.build_command,
                env_var=lane.env_var,
                release=getattr(status, "release", None),
                occupied_path=str(path) if state == "occupied" and path else None,
            )
        )

    return _decide(rows, root=root, configured=configured, free=free, settings=settings)


def _offerable(row: CachePlanLane) -> bool:
    """A lane an offer may name: it has a route, it is permitted, and it fits.

    `fits is True` rather than `is not False` on purpose — a lane nobody could price is
    not offered, because the whole point of the offer is that it states the cost.
    """
    return (
        row.route in ("pull", "build")
        and row.licence_skip is None
        and row.fits is True
        and (row.total_mb or 0.0) <= _OFFER_CEILING_MB
    )


def _offer(
    *, withheld: str | None, prewarm: list[str], full: list[str], settings: Settings | None
) -> str | None:
    """Which offer is open, or ``None`` for *say nothing* — and that is the common answer.

    **The one escalation this refuses is the one a helpful agent would make.** An author
    who declined the 15 MB set is not asked about the 14 GB one: a refusal is an answer to
    the question of whether they want caches at all, and coming back with a bigger number
    is the nag that gets a first-run prompt turned off for good. So the full offer needs
    the small one *satisfied* — accepted, or already on disk with nothing left to build —
    rather than merely not-refused.
    """
    if withheld is not None or settings is None:
        return None
    if prewarm and settings.cache_prewarm is None:
        return "prewarm"
    if settings.cache_prewarm is False:
        return None
    # **Accepted, not exhausted.** `acmg` builds from a workbook that ships in the format
    # checkout and not in the wheel, so on a PyPI install it stays absent and buildable
    # for ever — and a second offer gated on an *empty* small set would then never arrive
    # on the installs most people have. An explicit yes is the condition; nothing left to
    # build is the other way to satisfy it.
    if full and (settings.cache_prewarm is True or not prewarm) and settings.cache_full is None:
        return "full"
    return None


def _decide(
    rows: list[CachePlanLane],
    *,
    root: Path | None,
    configured: bool,
    free: float | None,
    settings: Settings | None,
) -> CachePlan:
    prewarm = [r for r in rows if r.route == "build" and _offerable(r)]
    full = [r for r in rows if _offerable(r)]

    def _sum(items: list[CachePlanLane]) -> tuple[float, float]:
        """What the set costs to build, and what it costs to pull — two numbers, not one.

        **A derived lane's price is dominated by a parent it pins.** `mitomap_miss` is a
        megabyte built and pins ClinVar, which is 300 MB to download, so *"the five
        unpublishable lanes are about 15 MB"* is true of the build and false of the
        session. One number would make the offer understate itself twentyfold, and an
        author who said yes to 15 MB did not say yes to a third of a gigabyte.

        The parents are counted once across the whole set rather than per lane: adding
        ClinVar again for `clinvar` itself would double a download that happens once.
        """
        named = {r.lane for r in items}
        own = sum(r.estimate_mb or 0.0 for r in items if r.route == "build")
        pull = sum(r.estimate_mb or 0.0 for r in items if r.route == "pull")
        extra: set[str] = set()
        for r in items:
            extra.update(p for p in r.parents_absent if p not in named)
        pull += sum(r.estimate_mb or 0.0 for r in rows if r.lane in extra)
        return round(own, 2), round(pull, 1)

    withheld: str | None = None
    if not configured:
        withheld = (
            f"{CACHE_DIR_VAR} is unset, so the caches would go to the platformdirs "
            "fallback under $HOME — which is where a 14 GB Ensembl snapshot once filled a "
            "root filesystem. Set it to a volume with room before anything is offered."
        )
    elif free is None:
        withheld = (
            "Free space on the volume holding the caches could not be read, and an offer "
            "that cannot state what it costs is not an offer."
        )

    return CachePlan(
        lanes_known=True,
        cache_dir=str(root) if root else None,
        cache_dir_configured=configured,
        cache_dir_var=CACHE_DIR_VAR,
        free_mb=free,
        lanes=rows,
        prewarm_lanes=[r.lane for r in prewarm],
        prewarm_build_mb=_sum(prewarm)[0],
        prewarm_pull_mb=_sum(prewarm)[1],
        prewarm_mb=round(sum(_sum(prewarm)), 1),
        full_lanes=[r.lane for r in full],
        full_mb=round(sum(_sum(full)), 1),
        unavailable=[
            f"{r.lane}: {r.why_no_route or r.licence_skip or r.caution}"
            for r in rows
            if r.route == "none"
            or r.licence_skip is not None
            or (
                r.route in ("pull", "build")
                and r.fits is True
                and (r.total_mb or 0.0) > _OFFER_CEILING_MB
            )
        ],
        too_large=[
            f"{r.lane}: {r.estimate_mb} MB estimated, {free} MB free"
            for r in rows
            if r.fits is False
        ],
        prewarm_answered=None if settings is None else settings.cache_prewarm,
        full_answered=None if settings is None else settings.cache_full,
        offer=_offer(
            withheld=withheld,
            prewarm=[r.lane for r in prewarm],
            full=[r.lane for r in full],
            settings=settings,
        ),
        record_with=[
            "JMC_CACHE_PREWARM=true    # built the locally-built lanes",
            "JMC_CACHE_PREWARM=false   # declined; do not ask again",
            "JMC_CACHE_FULL=true       # provisioned the whole surface",
            "JMC_CACHE_FULL=false      # declined the whole surface",
        ],
        offer_withheld=withheld,
        note=_note(rows, prewarm, full),
    )


def _note(
    rows: list[CachePlanLane], prewarm: list[CachePlanLane], full: list[CachePlanLane]
) -> str:
    held = sum(1 for r in rows if r.state == "present")
    occupied = [r.lane for r in rows if r.state == "occupied"]
    parts = [
        f"{held} of {len(rows)} lanes are already here; "
        f"{len(prewarm)} of the remainder can be built locally and {len(full)} provisioned at all."
    ]
    if occupied:
        parts.append(
            "Occupied, which is neither present nor absent — the directory exists and holds no "
            "snapshot, and provisioning refuses rather than building over it: "
            f"{', '.join(occupied)}. "
            "Move it aside or `cache prune --only <lane>`."
        )
    parts.append(
        "Every size but one is an estimate measured on a provisioned box on 2026-09-11, not a "
        "declaration by the lane (upstream S97); a present lane reports what it actually measures "
        "beside it."
    )
    return " ".join(parts)


def provision(
    lanes: list[str] | None, *, declared_use: str = "unstated", settings: Settings
) -> CachePlan:
    """Actually provision, then re-plan so the result reports the machine as it now is.

    Each lane goes through upstream's `prepare_lane` — one call per lane rather than
    `prepare_caches` over the whole registry — so a caller who asked for the five
    buildable ones does not silently start a 14 GB download, and so a lane's own
    refusal (`already provisioned`, `needs the ACMG SF workbook`, a licence skip) comes
    back verbatim instead of being re-derived here.
    """
    before = plan(declared_use=declared_use, settings=settings)
    if not before.lanes_known or before.offer_withheld:
        return before
    if RebuildRequest is None or parent_snapshots is None or prepare_lane is None:
        return before  # pragma: no cover — unreachable while `lanes_known` is true

    wanted = set(lanes or before.prewarm_lanes)
    by_name = {lane.name: lane for lane in CACHE_LANES}
    unknown = sorted(wanted - set(by_name))
    outcomes: list[str] = []
    for name in sorted(wanted & set(by_name)):
        lane = by_name[name]
        request = RebuildRequest(out_dir=lane.default_dir(), declared_use=declared_use, parents={})
        found, missing = parent_snapshots(lane, request)
        if missing:
            outcomes.append(
                f"{name}: not attempted — its parents are not here yet ({', '.join(missing)}); "
                "provision those first."
            )
            continue
        outcome = prepare_lane(
            lane,
            RebuildRequest(out_dir=lane.default_dir(), declared_use=declared_use, parents=found),
        )
        ready = (
            "ready"
            if outcome.ready is True
            else ("failed" if outcome.ready is False else "skipped")
        )
        outcomes.append(f"{name}: {ready} via {outcome.route} — {outcome.detail}")
        log.info("provisioned lane %s: %s", name, ready)

    after = plan(declared_use=declared_use, settings=settings)
    return after.model_copy(
        update={
            "provisioned": outcomes,
            "note": (
                (f"Not a lane on this install: {', '.join(unknown)}. " if unknown else "")
                + after.note
            ),
        }
    )
