"""The record behind an authored value that outranks a source.

`RM16`. §2 says this layer may write and revise, and that editing **against** a
source needs a reason that outranks it. This module is where that reason is kept,
so the judgement survives the person who made it.

**The hazard is not vacuity, it is that the source lags the edge.** A retraction, a
refuting meta-analysis, a reclassification an archive has not absorbed: a row that
disagrees with ClinVar may be the module being *more* current. Nothing anywhere
records that today — the value changes, the cross-check warns, and no later reader
can tell a considered outrank from a careless overwrite.

Three properties are load-bearing and each is here for a reason stated in `RM16`:

* **A record is a response to a reported mismatch, never a filter filed ahead of
  one.** An author who could pre-emptively mark a row outranked would destroy the
  only signal that catches the other pathway — an ordinary hallucination or a
  stale recollection, where the warning is doing its job.
* **It never produces a pass.** A recorded outrank is downgraded and still visible.
  The disagreement is real and stays interesting; the record says who decided and
  why.
* **It is bound to the value it justifies.** The digest below is over the authored
  value at the moment of the record, so a later edit to that cell makes the record
  **stale by construction** — the same shape as the attestation binding, and for
  the same reason.

Persistence is `provenance.json`, upstream's own file: `ProvenanceItem` already
carries `variant_key`, `rationale`, `reviewer_verdict`, `confidence` and
`human_reviewed`, it is in the registry's `RECOGNIZED_SPEC_FILES` so it survives a
server-side rebuild, and it is hashed like a log and kept out of `artifact.digest`
— so writing one costs no identity.

**An outrank is per field and their schema is per row.** Upstream is being asked to
pick a shape (`S52`); until they do, this writes **one item per (variant_key,
field)** — their `items` list has no uniqueness rule — and carries the field in a
machine-readable marker appended to `rationale`. That keeps the per-field record
travelling *with the module* rather than in a local cache a second author would
never see, and it re-emits into whatever shape `S52` settles on.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from just_dna_format.manifest import ProvenanceDoc, ProvenanceItem
from pydantic import BaseModel, Field

PROVENANCE_FILE = "provenance.json"
GENERATOR = "just-module-creator"

#: Appended to `rationale`. Machine fields only — the prose before it is the
#: reason a human reads, and nothing is encoded twice.
_MARKER = re.compile(
    r"\s*\[jmc field=(?P<field>[A-Za-z0-9_]+)"
    r" value_sha256=(?P<digest>[0-9a-f]{12})"
    r" source=(?P<source>[A-Za-z0-9_.-]+)"
    r" recorded=(?P<at>[0-9TZ:.-]+)"
    r" by=(?P<by>[^\]]+)\]"
)


def value_digest(value: str) -> str:
    """Bind a record to the cell it justifies. Twelve hex is plenty to notice a change."""
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()[:12]


def utc_now() -> str:
    """ISO-8601 UTC. Stored this way, displayed local — never a naive timestamp."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class OverrideRecord(BaseModel):
    """One authored value that outranks what a source says, and why."""

    variant_key: str = Field(description="rsid or chrom:start:ref, matching the authored row.")
    field: str = Field(description="The column the disagreement is on — `clin_sig`, `state`, …")
    authored_value: str = Field(description="What the module says, at the moment of the record.")
    source_name: str = Field(description="Which source disagrees — `clinvar`, `clingen`, `gwas`.")
    source_value: str | None = Field(
        default=None, description="What that source said when the record was written, if known."
    )
    reason: str = Field(
        description=(
            "Why the authored value outranks the source, in prose. This is the whole "
            "instrument: outranking cannot be formalized — which of a retraction, a "
            "meta-analysis and a larger cohort wins is a judgement — so there is no "
            "vocabulary here, deliberately."
        )
    )
    recorded_at: str = Field(default_factory=utc_now, description="ISO-8601 UTC.")
    recorded_by: str = Field(description="Who decided. A name, a handle, or a model id.")
    human_reviewed: bool = Field(
        default=False,
        description="Whether a human made this call. False is not a defect — it is the truth "
        "about most first passes, and a reviewer routes their scrutiny by it.",
    )
    value_sha256: str = Field(default="", description="Digest of `authored_value` when recorded.")

    def bound_to(self, current_value: str | None) -> bool:
        """Does this record still justify what is in the cell today?"""
        if current_value is None:
            return False
        bound = self.value_sha256 or value_digest(self.authored_value)
        return value_digest(current_value) == bound

    def subject(self) -> tuple[str, str]:
        return (self.variant_key, self.field)


def _marker(record: OverrideRecord) -> str:
    return (
        f" [jmc field={record.field}"
        f" value_sha256={record.value_sha256 or value_digest(record.authored_value)}"
        f" source={record.source_name}"
        f" recorded={record.recorded_at}"
        f" by={record.recorded_by}]"
    )


def to_items(records: Iterable[OverrideRecord]) -> list[ProvenanceItem]:
    """Our records in upstream's shape, one item per (variant_key, field)."""
    items: list[ProvenanceItem] = []
    for record in records:
        said = f" Source said: {record.source_value}." if record.source_value else ""
        items.append(
            ProvenanceItem(
                variant_key=record.variant_key,
                rationale=f"{record.reason.rstrip()}{said}{_marker(record)}",
                human_reviewed=record.human_reviewed,
            )
        )
    return items


def from_items(items: Sequence[ProvenanceItem]) -> tuple[list[OverrideRecord], list[str]]:
    """Read our records back, and report every item that is not one of ours.

    An item without our marker is somebody else's provenance — another tool's, or a
    hand-written one — and it is **kept, never rewritten**. This returns it as an
    unparsed note rather than dropping it, because silently discarding another
    writer's record would be the same defect this module exists to prevent.
    """
    records: list[OverrideRecord] = []
    foreign: list[str] = []
    for item in items:
        rationale = item.rationale or ""
        match = _MARKER.search(rationale)
        if not match:
            foreign.append(rationale or f"(no rationale) {item.variant_key}")
            continue
        reason = rationale[: match.start()].rstrip()
        source_value: str | None = None
        if " Source said: " in reason:
            reason, _, tail = reason.partition(" Source said: ")
            source_value = tail.rstrip(".") or None
        records.append(
            OverrideRecord(
                variant_key=item.variant_key,
                field=match["field"],
                authored_value="",  # not stored; the digest is what binds
                source_name=match["source"],
                source_value=source_value,
                reason=reason,
                recorded_at=match["at"],
                recorded_by=match["by"],
                human_reviewed=item.human_reviewed,
                value_sha256=match["digest"],
            )
        )
    return records, foreign


def read_doc(spec_dir: Path) -> ProvenanceDoc | None:
    path = spec_dir / PROVENANCE_FILE
    if not path.is_file():
        return None
    return ProvenanceDoc.model_validate_json(path.read_text(encoding="utf-8"))


def read_records(spec_dir: Path) -> tuple[list[OverrideRecord], list[str]]:
    doc = read_doc(spec_dir)
    if doc is None:
        return [], []
    return from_items(doc.items)


def write_records(
    spec_dir: Path,
    records: Sequence[OverrideRecord],
    foreign: Sequence[ProvenanceItem] = (),
    model: str | None = None,
) -> Path:
    """Write `provenance.json`, ours plus anything already there that is not ours."""
    doc = ProvenanceDoc(
        generator=GENERATOR,
        model=model,
        items=[*foreign, *to_items(records)],
    )
    path = spec_dir / PROVENANCE_FILE
    payload = json.loads(doc.model_dump_json(exclude_none=True))
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def upsert(
    spec_dir: Path, record: OverrideRecord, model: str | None = None
) -> tuple[Path, bool]:
    """Add or replace the record for one (variant_key, field). Returns (path, replaced)."""
    doc = read_doc(spec_dir)
    existing, _ = from_items(doc.items) if doc else ([], [])
    keep_foreign = [
        item for item in (doc.items if doc else []) if not _MARKER.search(item.rationale or "")
    ]
    replaced = any(r.subject() == record.subject() for r in existing)
    merged = [r for r in existing if r.subject() != record.subject()]
    merged.append(record)
    merged.sort(key=lambda r: (r.variant_key, r.field))
    inherited = model or (doc.model if doc else None)
    return write_records(spec_dir, merged, keep_foreign, model=inherited), replaced


# --------------------------------------------------------------------------- #
# The queue: what a reviewer should look at first
# --------------------------------------------------------------------------- #
def _key_for(row: dict[str, str]) -> str | None:
    """`variant_key` as upstream documents it: the rsID, else `chrom:start:ref`."""
    rsid = (row.get("rsid") or "").strip()
    if rsid:
        return rsid
    chrom, start, ref = (
        (row.get("chrom") or "").strip(),
        (row.get("start") or "").strip(),
        (row.get("ref") or "").strip(),
    )
    return f"{chrom}:{start}:{ref}" if chrom and start and ref else None


def authored_values(spec_dir: Path, field: str) -> dict[str, set[str]]:
    """Every distinct value of one column, per `variant_key`, from `variants.csv`.

    A set rather than a value because a variant is several rows — one per genotype —
    and a column like `clin_sig` is a property of the variant that repeats across
    them. One distinct value is the ordinary case; several means the module itself
    disagrees, which the caller should see rather than have averaged away.
    """
    path = spec_dir / "variants.csv"
    out: dict[str, set[str]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = _key_for(row)
            value = (row.get(field) or "").strip()
            if key and value:
                out.setdefault(key, set()).add(value)
    return out


def archive_values(spec_dir: Path) -> dict[str, set[str]]:
    """What the archive currently says, per `variant_key`, from `clinical_assertions.csv`.

    This is the one source whose current answer is recorded **offline, in the
    module**, which is what makes a terminal state detectable without a network
    call. Absent sidecar means the question cannot be put — never that the source
    agrees.
    """
    path = spec_dir / "clinical_assertions.csv"
    out: dict[str, set[str]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = _key_for(row)
            value = (row.get("clin_sig") or row.get("clinical_significance") or "").strip()
            if key and value:
                out.setdefault(key, set()).add(value)
    return out


def _days_since(stamp: str) -> int | None:
    try:
        then = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return max(0, (datetime.now(UTC) - then).days)


class QueuedOverride(BaseModel):
    """One record, with everything that can be decided about it offline."""

    record: OverrideRecord
    still_bound: bool = Field(
        description="Whether the authored cell still hashes to what the record justifies. "
        "False means the value was edited again, so the reason no longer describes it — "
        "stale by construction, exactly like a verification record over moved bytes."
    )
    current_value: str | None = Field(
        default=None, description="What the cell says now, or null if the row is gone."
    )
    mismatch_state: str = Field(
        description=(
            "`resolved` — the archive now agrees with the authored value, so the override "
            "turned out to be right and the record is retirable. `standing` — they still "
            "disagree. `unknown` — the question could not be put offline, which is NOT "
            "agreement: only `clin_sig` has an archive answer recorded in the module."
        )
    )
    age_days: int | None = Field(default=None, description="Since the record was written.")


def review_queue(spec_dir: Path) -> list[QueuedOverride]:
    """The rows a reviewer should open first, ranked, computed offline.

    A review pass has no priority list today — a reviewer opens a module and picks
    somewhere to start. These are the rows where somebody overruled a source, which
    are simultaneously the highest-value judgements in the module and the easiest to
    forget: the person who wrote the justification understood it, and two source
    releases later nobody remembers whether the retraction that motivated it was
    itself superseded.

    Ranked worst-first: unbound records (the value moved under the reason), then
    standing ones oldest-first, then resolved ones — which are retirable and are the
    only evidence in the whole format that an authored judgement was **vindicated**.
    """
    records, _ = read_records(spec_dir)
    if not records:
        return []
    archive = archive_values(spec_dir)
    by_field: dict[str, dict[str, set[str]]] = {}
    queued: list[QueuedOverride] = []
    for record in records:
        values = by_field.setdefault(record.field, authored_values(spec_dir, record.field))
        current = values.get(record.variant_key) or set()
        one = sorted(current)[0] if len(current) == 1 else None
        bound = any(record.bound_to(value) for value in current)
        state = "unknown"
        if record.field == "clin_sig" and record.variant_key in archive:
            said = archive[record.variant_key]
            state = "resolved" if current and current <= said else "standing"
        elif record.field == "clin_sig" and archive:
            state = "standing"
        queued.append(
            QueuedOverride(
                record=record,
                still_bound=bound,
                current_value=one if one else (", ".join(sorted(current)) or None),
                mismatch_state=state,
                age_days=_days_since(record.recorded_at),
            )
        )
    order = {"standing": 0, "unknown": 1, "resolved": 2}
    queued.sort(
        key=lambda q: (
            q.still_bound,
            order.get(q.mismatch_state, 1),
            -(q.age_days or 0),
            q.record.variant_key,
        )
    )
    return queued
