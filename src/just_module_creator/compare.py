"""Compare two spec directories — what moved, at three grains, with no network.

`RM19`, built from `docs/DESIGN-version-compare.md`. A comparator answers *what
moved*, never *which side is right*: the source is not automatically newer than
what an author wrote, and a later version is not automatically more correct than
an earlier one — the published corpus contains a version that reverted its
predecessor's rewrite.

Three grains in one report, always, because the caller does not yet know which one
they need — that is why they called:

1. **signature** — `content_signature` both sides;
2. **table** — presence, row counts, added and removed;
3. **rows** — grouped by the **set of columns that changed**, which is what makes
   the row level readable on a large module. 1,190 rows changing in one column for
   one reason is one fact printed 1,190 times; grouped, it is one line.

Two rules the implementation turns on:

* **Compare the parsed models' `model_dump(mode="json")`, never the CSV text and
  never the parquet.** It is the same normalization `content_signature` applies, so
  the row level cannot contradict the signature level, and formatting differences —
  trailing zeros, a leading `+`, scientific notation — become invisible for free.
* **Never pair rows whose natural key changed.** One removed and one added, never
  one changed. Pairing asserts *this row became that row*, which is a claim about
  identity that two directory listings cannot support.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from just_dna_compiler import compiler, draft
from just_dna_format import layout
from pydantic import BaseModel

#: Authored tables whose edits move `sources.signature` rather than
#: `content_signature`. Hand-authored and outside the compiler's table roster, so
#: an author who edits a licence cell and watches `content_signature` concludes
#: nothing happened. Measured on `hfe_hemochromatosis`.
_SOURCE_SCOPED = {"licensing.csv", "sources.csv"}

_UNKEYED_NOTE = (
    "this kind has no equality key — upstream's `natural_key` returns None for the "
    "binning kinds on purpose, because two bins conflict by overlapping ranges "
    "within a group rather than by being equal. Rows are counted, never paired."
)


@dataclass
class LoadedTable:
    """One authored table, read as models. `errors` means it could not be read."""

    csv: str
    path: Path
    spelling: str
    rows: list[BaseModel] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return not self.errors


def read_build(spec_dir: Path) -> tuple[str | None, dict[str, Any]]:
    """The declared genome build, and the `module:` block, from `module_spec.yaml`."""
    path = spec_dir / "module_spec.yaml"
    if not path.is_file():
        return None, {}
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None, {}
    if not isinstance(doc, dict):
        return None, {}
    module = doc.get("module") if isinstance(doc.get("module"), dict) else {}
    return doc.get("genome_build"), {**(module or {}), "genome_build": doc.get("genome_build")}


def authored_tables(spec_dir: Path, genome_build: str = "GRCh38") -> dict[str, LoadedTable]:
    """Every authored table on disk, keyed by its **preferred** spelling.

    A module carrying the deprecated `sources.csv` spelling is compared against one
    carrying `licensing.csv` as the same table — they are one table with one model,
    and reporting them as two would say a file was removed and another added when
    nothing about the data moved. The spelling each side actually uses is reported
    instead.
    """
    out: dict[str, LoadedTable] = {}
    for name, model in sorted(draft.DRAFTABLE.items()):
        path = spec_dir / name
        if not path.is_file():
            continue
        preferred = layout.preferred_spelling(name)
        rows, errors, _ = compiler.load_csv_rows(path, model, name, genome_build)
        table = LoadedTable(csv=preferred, path=path, spelling=name, rows=list(rows))
        if errors:
            table.errors = list(errors)
            table.rows = []
        # A module carrying both spellings is upstream's error, not ours to merge:
        # keep the first seen and let the caller see the collision in `unknown`.
        out.setdefault(preferred, table)
    return out


def _dump(row: BaseModel) -> dict[str, Any]:
    return row.model_dump(mode="json")


def _key(row: BaseModel) -> tuple | None:
    return draft.natural_key(row)


def changed_columns(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    """Columns whose value differs, sorted. Compared as dumped JSON, never as text."""
    names = set(left) | set(right)
    return sorted(n for n in names if left.get(n) != right.get(n))


@dataclass
class ChangeGroup:
    columns: list[str]
    rows: int
    examples: list[dict[str, Any]]


@dataclass
class TableDiff:
    csv: str
    identity_scope: str
    presence: str
    spelling_left: str | None
    spelling_right: str | None
    rows_left: int | None
    rows_right: int | None
    row_key: str
    key_collisions: int
    unchanged: int | None
    added: int | None
    removed: int | None
    changed: list[ChangeGroup]


def _window(left: Any, right: Any, limit: int = 60) -> list[str]:
    """Render a before/after pair so the **difference** is visible, not the head.

    Truncating from the start renders two long values that differ late as two
    identical strings, which is worse than showing nothing: the reader concludes the
    tool is broken, or worse, that the row did not really change. So when both sides
    are longer than the window, the window is centred on the first character where
    they diverge.
    """
    a = "" if left is None else str(left)
    b = "" if right is None else str(right)
    if len(a) <= limit and len(b) <= limit:
        return [a, b]
    pairs = enumerate(zip(a, b, strict=False))
    cut = next((i for i, (x, y) in pairs if x != y), min(len(a), len(b)))
    start = max(0, cut - limit // 3)

    def clip(text: str) -> str:
        piece = text[start : start + limit]
        return ("…" if start else "") + piece + ("…" if start + limit < len(text) else "")

    return [clip(a), clip(b)]


def compare_table(
    csv: str,
    left: LoadedTable | None,
    right: LoadedTable | None,
    max_groups: int,
    examples_per_group: int,
) -> tuple[TableDiff, list[tuple[str, str]]]:
    """Compare one authored table. Returns the diff and any `unknown` it produced."""
    unknown: list[tuple[str, str]] = []
    scope = "sources.signature" if csv in _SOURCE_SCOPED else "content_signature"

    if left is None or right is None:
        present = right if left is None else left
        side = "right_only" if left is None else "left_only"
        rows = len(present.rows) if present and present.readable else None
        return (
            TableDiff(
                csv=csv,
                identity_scope=scope,
                presence=side,
                spelling_left=left.spelling if left else None,
                spelling_right=right.spelling if right else None,
                rows_left=rows if side == "left_only" else None,
                rows_right=rows if side == "right_only" else None,
                row_key="keyed",
                key_collisions=0,
                unchanged=None,
                added=rows if side == "right_only" else None,
                removed=rows if side == "left_only" else None,
                changed=[],
            ),
            unknown,
        )

    for side, table in (("left", left), ("right", right)):
        if not table.readable:
            unknown.append((f"{csv} ({side})", f"could not be read: {table.errors[0]}"))
    if not (left.readable and right.readable):
        return (
            TableDiff(
                csv=csv,
                identity_scope=scope,
                presence="unknown",
                spelling_left=left.spelling,
                spelling_right=right.spelling,
                rows_left=len(left.rows) if left.readable else None,
                rows_right=len(right.rows) if right.readable else None,
                row_key="keyed",
                key_collisions=0,
                unchanged=None,
                added=None,
                removed=None,
                changed=[],
            ),
            unknown,
        )

    sample = (left.rows or right.rows or [None])[0]
    keyed = sample is not None and _key(sample) is not None
    if not keyed:
        unknown.append((f"{csv} rows", _UNKEYED_NOTE))
        return (
            TableDiff(
                csv=csv,
                identity_scope=scope,
                presence="both",
                spelling_left=left.spelling,
                spelling_right=right.spelling,
                rows_left=len(left.rows),
                rows_right=len(right.rows),
                row_key="unkeyed",
                key_collisions=0,
                unchanged=None,
                added=None,
                removed=None,
                changed=[],
            ),
            unknown,
        )

    def index(rows: Sequence[BaseModel]) -> tuple[dict[tuple, dict[str, Any]], int]:
        by_key: dict[tuple, dict[str, Any]] = {}
        seen: Counter[tuple] = Counter()
        for row in rows:
            key = _key(row)
            if key is None:
                continue
            seen[key] += 1
            by_key.setdefault(key, _dump(row))
        return by_key, sum(count - 1 for count in seen.values() if count > 1)

    left_by, left_dupes = index(left.rows)
    right_by, right_dupes = index(right.rows)
    common = left_by.keys() & right_by.keys()

    grouped: dict[tuple[str, ...], list[tuple[tuple, dict[str, Any]]]] = defaultdict(list)
    unchanged = 0
    for key in common:
        columns = changed_columns(left_by[key], right_by[key])
        if not columns:
            unchanged += 1
            continue
        grouped[tuple(columns)].append((key, {}))

    groups: list[ChangeGroup] = []
    for columns, members in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        examples = []
        for key, _ in members[:examples_per_group]:
            cells = {
                name: _window(left_by[key].get(name), right_by[key].get(name))
                for name in columns
            }
            examples.append({"key": ":".join(str(part) for part in key), "cells": cells})
        groups.append(ChangeGroup(columns=list(columns), rows=len(members), examples=examples))
    if len(groups) > max_groups:
        dropped = len(groups) - max_groups
        rows_dropped = sum(g.rows for g in groups[max_groups:])
        groups = groups[:max_groups]
        unknown.append(
            (
                f"{csv} changed groups",
                f"{dropped} further group(s) covering {rows_dropped} row(s) are not listed — "
                f"raise `max_groups` above {max_groups} to see them. The counts above "
                "include them, so nothing is silently truncated.",
            )
        )

    return (
        TableDiff(
            csv=csv,
            identity_scope=scope,
            presence="both",
            spelling_left=left.spelling,
            spelling_right=right.spelling,
            rows_left=len(left.rows),
            rows_right=len(right.rows),
            row_key="keyed",
            key_collisions=left_dupes + right_dupes,
            unchanged=unchanged,
            added=len(right_by.keys() - left_by.keys()),
            removed=len(left_by.keys() - right_by.keys()),
            changed=groups,
        ),
        unknown,
    )


def content_signature_of(spec_dir: Path) -> str | None:
    """`content_signature`, or None when the spec cannot be read at all."""
    try:
        return compiler.content_signature(spec_dir)
    except Exception:  # noqa: BLE001 — any unreadable spec is `unknown`, not a crash
        return None


# --------------------------------------------------------------------------- #
# The derived side — a different question, with a different actor
# --------------------------------------------------------------------------- #
@dataclass
class DerivedDiff:
    """One machine-written sidecar. Hashed by its **facts**, never by its bytes."""

    csv: str
    verdict: str
    left_signature: str | None
    right_signature: str | None
    signature_source: str
    rows_left: int | None
    rows_right: int | None


def _read_sidecar(path: Path, sidecar: Any, name: str) -> tuple[str | None, int | None, str | None]:
    """A sidecar's fact signature and row count, or why neither could be had."""
    if not path.is_file():
        return None, None, "absent"
    rows, errors, _ = compiler.load_csv_rows(path, sidecar.model, name)
    if errors:
        return None, None, errors[0]
    return sidecar.signature(rows), len(rows), None


def compare_derived(
    left_dir: Path, right_dir: Path, roster: Mapping[str, Any]
) -> tuple[list[DerivedDiff], list[tuple[str, str]]]:
    """Compare the derived sidecars on their fact signatures, recomputed from disk.

    **This is a different question from the authored side and the report must not
    merge them.** The authored section answers *did somebody edit this module*; this
    one answers *did a source say something different*. A single merged count cannot
    tell an edit from an upstream revision, which is the one distinction the identity
    ledger exists to preserve.

    A fact signature is **recomputable**, not merely quotable: running upstream's own
    `*_FACT_FIELDS` over the files on disk reproduces the manifest's signatures
    exactly. So two directories can be compared with no manifest at all — and the
    provenance noise is excluded by construction rather than by our filtering, because
    `fetched_at`, `source` and `status` are not fact fields. A fresh `fetched_at`
    moves the file's bytes and moves no signature.

    **It cannot perform the canary.** Detecting that a source revised an answer means
    deleting a sidecar and re-deriving it, which is `refresh_sidecar`'s job — that tool
    knows which side it just derived, and this one only sees two recorded files. What
    a comparator adds is the case refresh cannot serve: two states no single refresh
    run produced.
    """
    out: list[DerivedDiff] = []
    unknown: list[tuple[str, str]] = []
    for name, sidecar in sorted(roster.items()):
        left_path, right_path = left_dir / name, right_dir / name
        if not left_path.is_file() and not right_path.is_file():
            continue

        left_sig, left_rows, left_why = _read_sidecar(left_path, sidecar, name)
        right_sig, right_rows, right_why = _read_sidecar(right_path, sidecar, name)

        for side, why in (("left", left_why), ("right", right_why)):
            if why and why != "absent":
                unknown.append((f"{name} ({side})", f"could not be read: {why}"))

        if left_sig is None or right_sig is None:
            # Absent on one side is knowledge when a directory listing is the
            # evidence; unreadable is not. Both land as `unknown` here because a
            # signature cannot be compared against nothing either way.
            verdict = "unknown"
            if left_why == "absent" and right_why is None:
                unknown.append((name, "present on the right only, so there is nothing to compare"))
            elif right_why == "absent" and left_why is None:
                unknown.append((name, "present on the left only, so there is nothing to compare"))
        else:
            verdict = "same" if left_sig == right_sig else "moved"

        out.append(
            DerivedDiff(
                csv=name,
                verdict=verdict,
                left_signature=left_sig,
                right_signature=right_sig,
                signature_source="recomputed",
                rows_left=left_rows,
                rows_right=right_rows,
            )
        )
    return out, unknown
