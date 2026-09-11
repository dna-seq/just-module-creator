"""Thick or thin: where a snapshot-backed answer comes from, and who says so.

The enricher's lookups read **snapshot caches** — fifteen lanes, several of them
multi-gigabyte, the Ensembl one about 14 GB. A provisioned server has them. A module
author on a laptop, an agent in a container and a plugin installed this morning do not,
and the compiler never fetches, so the whole authoring half of the ecosystem was
available only to whoever had already downloaded them.

`just-dna-registry` 0.25.0 closes that: it turns the registry into a **caching proxy**
whose standing position is *a thin client's cache miss is answered by the registry, and
the registry's own miss is answered by the remote source.* This module is our side of it.

**The switch is per lane, not per install, because that is what the real world looks
like.** A box holding three of fifteen lanes must not have to pick one wrong answer for
everything — and holding the Ensembl snapshot while holding nothing else is the *common*
shape, since it is the one lane `enrich` cannot work without. So `route_for` asks which
lanes an answer needs, checks those, and reports what it decided.

**Every routed answer names who answered it.** That is § 2's *never silently fall back*
at a new grain: the caller cannot see that the source differed, and "the registry had no
snapshot either, so this went to Ensembl's REST API" is a different answer from "this
came off the local snapshot" even when the values agree.

**What is deliberately NOT automatic: anything that uploads the author's spec.** A hint
is a read of a public identifier. `POST /drafts` and `POST .../derived` send the module —
every authored CSV, `module_spec.yaml` and the `logs/` subtree — to a third party, and
that is an outward-facing act a tool may not take on its own initiative to be helpful.
Those are separate tools and an explicit `via=` argument. **Reversal recipe** if that
turns out to be one hop too many: flip `remote_derive` into `enrich_module(via=…)` and
default `via` to `"auto"`; nothing in here has to change.
"""

from __future__ import annotations

from typing import Any, Literal

from just_dna_registry import models as _registry_models
from just_dna_registry.client import RegistryClient

from just_module_creator.logging_setup import get_logger

log = get_logger()

#: The lane registry, and it is a **whole module** the installed 0.6.6 enricher does not
#: have (upstream `RM176`). So this is the one exception `CLAUDE.md` § 2 grants — a
#: guarded module-level import for a dependency that really is optional, and optional
#: only for the length of this interval. An unguarded one does not fail as a missing
#: attribute: it takes this module down, and with it the whole server, on every install
#: that has not upgraded.
#:
#: **`()` here is not "no lanes". It is "cannot ask"**, and the difference reaches the
#: wire — `local_lane_presence` returns `None` rather than an empty map, and
#: `LaneStatus.local` is `bool | None` for the same reason. An enricher without the lane
#: registry is the old world, where a pass looks where it looks and nothing can report on
#: it; saying *this machine holds no snapshots* would be a measurement nobody took.
#:
#: **Delete the guard, not the import, when the floor moves to 0.7.**
try:
    from just_dna_enricher.caches import CACHE_LANES
except ImportError:  # pragma: no cover — only on a pre-0.7 enricher
    CACHE_LANES = ()

#: Whether local lane presence is answerable at all on this install.
LANES_KNOWN = bool(CACHE_LANES)

#: Where a snapshot-backed answer may come from. `auto` is per lane; the other two are
#: overrides for a caller who knows better than the probe — a lane directory that exists
#: but holds a half-downloaded snapshot resolves as present here and will not serve.
SnapshotRoute = Literal["local", "registry", "auto"]

#: Who actually answered, on every routed result. Four states and each is a different
#: fact, which is why this is not a boolean:
#:
#: * ``local`` — a lane on this machine served it.
#: * ``registry`` — the proxy served it, at whatever its own `cost` says.
#: * ``local_online_after_registry_miss`` — the proxy had no snapshot either and this
#:   fell through to the live service. **The slow, metered path**, and the one a caller
#:   most needs told about: the values may be identical and the egress is ours.
#: * ``unrouted`` — no lane is involved, so there was nothing to decide. HGNC and OLS4
#:   publish no snapshot, so a gene or trait lookup is online wherever it runs.
AnsweredBy = Literal["local", "registry", "local_online_after_registry_miss", "unrouted"]


#: Which lanes each proxied answer actually needs. **An explicit map rather than a rule**,
#: because the rule does not exist: `hint_variant` needs Ensembl to place an rsID and
#: ClinVar to say anything about significance, while `hint_gene` and `hint_trait` reach
#: HGNC and OLS4, which publish no snapshot at all and are therefore online on a fully
#: provisioned server too. Deriving this from lane names would invent a correspondence.
#:
#: Keyed on OUR tool name, not upstream's route, so a reader of this file can see which
#: of our tools changes behaviour. Empty tuple = no lane, so no routing decision.
LANES_FOR: dict[str, tuple[str, ...]] = {
    "lookup_variant": ("ensembl", "clinvar"),
    "lookup_citation": (),
    "lookup_identifier": (),
    "lookup_allele_identity": (),
    "lookup_open_access": (),
}


def local_lane_presence() -> dict[str, bool] | None:
    """Which snapshot lanes this machine holds, or ``None`` when that cannot be asked.

    `caches.CACHE_LANES` replaced a hand-kept list that had drifted three lanes behind
    reality (upstream RM176), so it is read rather than restated — and `lane.resolve()`
    is the same resolver the pass itself calls, so this cannot disagree with what a pass
    would find.

    **`None` means the installed enricher predates the lane registry**, which is a
    different fact from an empty map and must not be folded into it: a pass on that
    toolchain still finds whatever it finds, and reporting *no snapshots* would be a
    measurement nobody took. Same rule as `None`-is-not-`False`, one grain coarser.

    **Two-valued here and three-valued on the server, and the difference is real.** The
    registry's `/caches` reports `partial` for a directory holding something that is not
    a readable snapshot, because provisioning *refuses* to act on that rather than
    overwriting. `resolve()` gives us present-or-not, so a half-downloaded lane reads as
    present and then fails in the pass. `JMC_SNAPSHOT_ROUTE=registry` is the override for
    exactly that case, which is why it exists.
    """
    if not LANES_KNOWN:
        return None
    return {lane.name: lane.resolve() is not None for lane in CACHE_LANES}


#: The proxy surface, probed by symbol on the INSTALLED client rather than gated on a
#: version. Our floor is `just-dna-registry>=0.18.1` with no ceiling, so the thin path
#: activates by itself the day 0.25.0 reaches PyPI and refuses with a named reason until
#: then — no era branch, and `main` ships this code inert rather than not shipping it.
#:
#: **Delete this and call the methods outright once the floor moves to 0.25.** Grep
#: `_PROXY_METHODS` and `proxy_gap`.
_PROXY_METHODS: tuple[str, ...] = (
    "cache_status",
    "derived",
    "draft",
    "hint_variant",
    "hint_variants",
    "hint_citation",
    "hint_gene",
    "hint_trait",
    "hint_old_assembly",
)

#: One response model, probed the same way. A method could in principle exist while the
#: model did not; more usefully, this is what the translation layer needs to be able to
#: read, and `just_dna_registry.models.api` on 0.18.2 has none of these names.
_PROXY_MODEL = "VariantHintReport"


def proxy_gap() -> str | None:
    """``None`` when the installed client can proxy, else the sentence to refuse with.

    A refusal that names the release and the reason, because the alternative — a tool
    that is absent, or one that says "Unknown tool" — reproduces the dead end the tier
    axis cost us four times. The surface must never teach a step it cannot run, and
    "cannot run *yet*, here is what would make it run" is the honest form of that.
    """
    missing = [name for name in _PROXY_METHODS if not hasattr(RegistryClient, name)]
    api = getattr(_registry_models, "api", None)
    if api is not None and not hasattr(api, _PROXY_MODEL):
        missing.append(f"models.api.{_PROXY_MODEL}")
    if not missing:
        return None
    return (
        "the installed just-dna-registry client cannot proxy: it is missing "
        f"{', '.join(missing)}. The caching-proxy surface — GET /api/v1/caches, "
        "POST /drafts, POST .../derived and the six /hint/* routes — arrived in "
        "just-dna-registry 0.25.0, which is not on PyPI yet: its release is gated on "
        "both instances being deployed on just-dna-format 0.7 first, because publishing "
        "it earlier would take the write surface off every install that upgraded. "
        "Nothing here is broken and nothing needs configuring. Until that release, this "
        "machine answers from its own snapshot lanes or not at all — `registry_caches` "
        "lists which lanes it holds, and `just-dna-enricher cache prepare` provisions "
        "the rest."
    )


class Route:
    """What was decided, why, and who is expected to answer. Not a pydantic model.

    It crosses no wire: the tools copy its fields into their own response models, which
    is where the field descriptions an agent reads belong. Keeping it a plain object
    stops it becoming a second place those descriptions live.
    """

    __slots__ = ("answered_by", "lanes_needed", "lanes_local", "why", "offline", "target")

    def __init__(
        self,
        *,
        answered_by: AnsweredBy,
        lanes_needed: tuple[str, ...],
        lanes_local: tuple[str, ...],
        why: str,
        offline: bool,
        target: str | None,
    ) -> None:
        self.answered_by = answered_by
        self.lanes_needed = lanes_needed
        self.lanes_local = lanes_local
        self.why = why
        self.offline = offline
        self.target = target

    def as_dict(self) -> dict[str, Any]:
        return {
            "answered_by": self.answered_by,
            "lanes_needed": list(self.lanes_needed),
            "lanes_local": list(self.lanes_local),
            "why": self.why,
            "offline": self.offline,
            "target": self.target,
        }


def route_for(
    tool: str,
    *,
    snapshot_route: SnapshotRoute,
    offline: bool,
    target: str | None,
    presence: dict[str, bool] | None = None,
    lanes_known: bool | None = None,
) -> Route:
    """Decide where `tool`'s answer should come from, and say why in a sentence.

    **`offline` wins over everything, and it is not a preference.** `JMC_OFFLINE`
    combines with a per-call `offline` by OR before this is called, and a routed call to
    the registry is egress — so an offline run answers locally or reports that the
    question was not put. Sending a "cache-only" lookup over the network would be lying
    about the ceiling, which is the one thing the flag must never be made to do.

    **A lane we do not hold is the only reason to route out under `auto`.** Not
    slowness, not a stale snapshot, not a preference: those are the caller's to judge
    with `snapshot_route`, because this cannot tell a lane that will serve from one that
    resolves and then fails.
    """
    lanes = LANES_FOR.get(tool, ())
    if presence is None:
        probed = local_lane_presence()
        known = probed is not None
        presence = probed or {}
    else:
        known = LANES_KNOWN if lanes_known is None else lanes_known
    local = tuple(name for name in lanes if presence.get(name))
    missing = tuple(name for name in lanes if not presence.get(name))

    if not lanes:
        return Route(
            answered_by="unrouted",
            lanes_needed=(),
            lanes_local=(),
            why=(
                f"{tool} reads no snapshot lane — its sources publish none — so it is "
                "online wherever it runs and there was nothing to route."
            ),
            offline=offline,
            target=None,
        )

    if not known:
        # The old world, and the honest thing to do in it is to behave exactly as this
        # tool behaved before the switch existed. Routing out on the strength of a probe
        # that could not run would send every lookup to a registry on the basis of no
        # measurement at all — a check that could not run is not a check that failed.
        return Route(
            answered_by="local",
            lanes_needed=lanes,
            lanes_local=(),
            why=(
                "the installed just-dna-enricher predates the cache registry "
                "(0.7, RM176), so which snapshots this machine holds cannot be asked — "
                "and a route chosen on an unanswerable probe would be a guess. This ran "
                "exactly as it did before the switch existed: the pass looks where it "
                "looks. `lanes_local` is empty because nothing was measured, not because "
                "nothing is here."
            ),
            offline=offline,
            target=None,
        )

    if offline:
        return Route(
            answered_by="local",
            lanes_needed=lanes,
            lanes_local=local,
            why=(
                "offline: answered from local snapshots only, because routing to the "
                "registry is egress and the offline ceiling may not be loosened by a "
                "routing decision. "
                + (
                    f"Missing {', '.join(missing)}, so any answer that needed them is "
                    "unchecked rather than absent."
                    if missing
                    else "Every lane it needs is present."
                )
            ),
            offline=True,
            target=None,
        )

    if snapshot_route == "local":
        return Route(
            answered_by="local",
            lanes_needed=lanes,
            lanes_local=local,
            why="JMC_SNAPSHOT_ROUTE=local: never routed out, whatever is missing here.",
            offline=False,
            target=None,
        )

    gap = proxy_gap()
    if snapshot_route == "registry":
        if gap:
            return Route(
                answered_by="local",
                lanes_needed=lanes,
                lanes_local=local,
                why=f"JMC_SNAPSHOT_ROUTE=registry was asked for and cannot be honoured — {gap}",
                offline=False,
                target=None,
            )
        return Route(
            answered_by="registry",
            lanes_needed=lanes,
            lanes_local=local,
            why="JMC_SNAPSHOT_ROUTE=registry: routed out even where a local lane exists.",
            offline=False,
            target=target,
        )

    # auto
    if not missing:
        return Route(
            answered_by="local",
            lanes_needed=lanes,
            lanes_local=local,
            why=f"every lane this needs is on this machine: {', '.join(lanes)}.",
            offline=False,
            target=None,
        )
    if gap:
        return Route(
            answered_by="local",
            lanes_needed=lanes,
            lanes_local=local,
            why=(
                f"missing {', '.join(missing)} locally and the proxy is unavailable, so "
                f"this ran against the live services instead — {gap}"
            ),
            offline=False,
            target=None,
        )
    return Route(
        answered_by="registry",
        lanes_needed=lanes,
        lanes_local=local,
        why=(
            f"missing {', '.join(missing)} on this machine, so this was answered by the "
            "registry's snapshots rather than by fetching."
        ),
        offline=False,
        target=target,
    )


def missed_at_registry(route: Route, *, detail: str) -> Route:
    """Re-label a routed answer the proxy could not serve, so the fall-back is visible.

    The proxy answers a lane it lacks with `503 snapshot_unavailable` naming the lane;
    falling through to the live service is the right behaviour and a **silent** fall-back
    is not. Called by the tool, not by `route_for`, because only the tool knows whether
    the retry actually happened.
    """
    return Route(
        answered_by="local_online_after_registry_miss",
        lanes_needed=route.lanes_needed,
        lanes_local=route.lanes_local,
        why=(
            f"{route.why} The registry could not serve it either ({detail}), so this "
            "fell through to the live service: the egress is this machine's and the "
            "answer is not from any snapshot."
        ),
        offline=route.offline,
        target=route.target,
    )


def cost_from(hint: Any) -> dict[str, Any] | None:
    """Their `HintCost` as a plain mapping, or ``None`` when nothing was proxied.

    **`served_from` holds lane NAMES and never a path**, which is the producer mapping
    our own finding out: their `VariantHint.checked` carries absolute snapshot paths and
    one finding interpolated one into prose, so a payload that cannot leak a filesystem
    layout is safe by construction rather than by audit. Do not reconstruct paths from it.
    """
    cost = getattr(hint, "cost", None)
    if cost is None:
        return None
    return {
        "charged": dict(getattr(cost, "charged", {}) or {}),
        "limit": getattr(cost, "limit", None),
        "waited_seconds": float(getattr(cost, "waited_seconds", 0.0) or 0.0),
        "served_from": list(getattr(cost, "served_from", []) or []),
        "remedy": getattr(cost, "remedy", None),
    }


def variant_fields(hint: Any, *, proxied: bool) -> dict[str, Any]:
    """One variant answer as our own field names, from either side of the seam.

    **The two shapes are genuinely different and this is why a translation is owed.**
    The registry's models are theirs, not the enricher's: `rsid_status` is flattened into
    `rsid_state` + `rsid_current`, `checked`'s absolute snapshot paths become
    `cost.served_from` lane names, and `ambiguous` — a `@property` upstream, which does
    not survive serialization — is a real field there. Reading one as the other drops
    three answers silently.

    So this reads whichever is in front of it and returns our names. `proxied` picks the
    shape rather than sniffing for a field, because a sniff would guess wrong on the day
    either side adds the other's spelling.
    """
    if proxied:
        return {
            "rsid": getattr(hint, "rsid", None),
            "rsid_state": getattr(hint, "rsid_state", None),
            "rsid_current": getattr(hint, "rsid_current", None),
            "loci": list(getattr(hint, "loci", []) or []),
            "rsid_candidates": list(getattr(hint, "rsid_candidates", []) or []),
            "clin_sig": list(getattr(hint, "clin_sig", []) or []),
            "populations": list(getattr(hint, "populations", []) or []),
            "pubmind": list(getattr(hint, "pubmind", []) or []),
            "vrs_id": getattr(hint, "vrs_id", None),
            "ambiguous": getattr(hint, "ambiguous", None),
            # Lane names, deliberately — see `cost_from`. On the local side the same
            # field carries the enricher's own `checked`, which is paths; the two are
            # not the same vocabulary and the `route` beside them says which you have.
            "checked": sorted(
                str(c) for c in (getattr(getattr(hint, "cost", None), "served_from", []) or [])
            ),
        }

    status = getattr(hint, "rsid_status", None)
    return {
        "rsid": getattr(hint, "rsid", None),
        "rsid_state": getattr(status, "state", None) if status else None,
        "rsid_current": getattr(status, "current", None) if status else None,
        "loci": list(getattr(hint, "loci", []) or []),
        "rsid_candidates": list(getattr(hint, "rsid_candidates", []) or []),
        "clin_sig": list(getattr(hint, "clin_sig", []) or []),
        "populations": list(getattr(hint, "populations", []) or []),
        "pubmind": list(getattr(hint, "pubmind", []) or []),
        "vrs_id": getattr(hint, "vrs_id", None),
        "ambiguous": getattr(hint, "ambiguous", None),
        "checked": sorted(str(c) for c in (getattr(hint, "checked", set()) or set())),
    }
