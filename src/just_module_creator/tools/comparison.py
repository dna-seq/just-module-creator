"""ESSENTIALS — comparing two spec directories, offline.

`RM19`, built from `docs/DESIGN-version-compare.md`. **Essentials because the cost
is bounded by the two directories the caller named** — no network, no compile, no
parquet, and nothing here is sized by a corpus. The largest reference example
compares in under a fifth of a second.

It is also the tool the taught workflow needs: `module-diff`'s standing advice is
*download both versions and diff the CSVs*, which is a shell recipe an author in a
chat session cannot run, and a tier that teaches a step it cannot run is the
failure mode this repo tests for by name.
"""

from __future__ import annotations

from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from just_module_creator import compare
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    ChangeGroupOut,
    ComparedSide,
    DerivedComparison,
    FrameVerdict,
    MetadataDelta,
    ModuleComparison,
    TableComparison,
    Unknown,
)
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import resolve_dir
from just_module_creator.tools.refresh import ROSTER

log = get_logger()

_FRAME_SAME = "Both sides declare the same build, so the counts below are comparable."
_FRAME_MOVED = (
    "The two sides declare DIFFERENT builds, so the row comparison below is **not comparable** "
    "rather than clean. Identical coordinate rows on two assemblies name loci hundreds of bases "
    "apart, and the natural key is build-independent — so a row-level report of 'nothing changed' "
    "is the dangerous answer, not the reassuring one. Read this line before any count."
)
_FRAME_UNKNOWN = (
    "At least one side declares no build, or its `module_spec.yaml` could not be read. The row "
    "comparison is reported, and it is not known to be comparable."
)


def _verdict(left: object, right: object) -> str:
    if left is None or right is None:
        return "unknown"
    return "same" if left == right else "moved"


def register_comparison(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Compare two spec directories", readOnlyHint=True, idempotentHint=True
        )
    )
    async def compare_modules(
        left_dir: str,
        right_dir: str,
        max_groups: int = 12,
        examples_per_group: int = 2,
    ) -> ModuleComparison:
        """What moved between two spec directories. Offline; writes nothing, anywhere.

        Answers at three grains in one report, because the caller does not yet know
        which one they need — that is why they called:

        1. **`content` / `frame`** — did anything an author typed change, and do the
           two sides even mean coordinates in the same assembly.
        2. **`tables[]`** — presence, row counts, added and removed, plus
           `identity_scope`, which says *which hash your edit will move*.
        3. **`tables[].changed[]`** — rows grouped by **the set of columns that
           changed**. That grouping is what makes the row level readable: 1,190 rows
           changing in one column for one reason is one fact printed 1,190 times, and
           grouped it is one line.

        **Read `frame` before any row count.** When the declared builds differ, the
        row comparison is *not comparable* rather than clean — the natural key is
        build-independent, so two assemblies produce character-identical keys naming
        loci hundreds of bases apart, and "zero rows changed" is then the dangerous
        answer.

        **`derived[]` is a separate section on purpose.** The authored side answers
        *did somebody edit this module*; the derived side answers *did a source say
        something different*. Merging them into one count would destroy the one
        distinction the identity ledger exists to preserve. Sidecars are compared on
        their **fact signatures**, recomputed from the files on disk, so a fresh
        `fetched_at` — which moves the bytes and no signature — is excluded by
        construction rather than by filtering.

        **What it will not do, and none of it is "not yet".** It has no write path and
        no parameter that could become one. It never says which side is right: a later
        version is not automatically more correct, and the published corpus contains a
        version that reverted its predecessor. It never pairs rows whose natural key
        changed — one removed and one added, never one changed, because pairing asserts
        *this row became that row*. It writes no changelog prose and suggests no
        version bump. And it cannot perform the canary: detecting that a source revised
        an answer means deleting a sidecar and re-deriving it, which is
        `refresh_sidecar`'s job, and that tool knows which side it just derived.

        For the raw cells, run `diff`. This reports what moved and groups it; it does
        not reproduce a line-by-line diff, badly.
        """
        left = resolve_dir(left_dir, settings)
        right = resolve_dir(right_dir, settings)

        def work() -> ModuleComparison:
            return _compare(left, right, max_groups, examples_per_group)

        result = await run_sync(work)
        log.info(
            "compared %s <-> %s: content %s", left.name, right.name, result.content
        )
        return result


def _compare(
    left: Path, right: Path, max_groups: int, examples_per_group: int
) -> ModuleComparison:
    left_build, left_module = compare.read_build(left)
    right_build, right_module = compare.read_build(right)
    unknown: list[Unknown] = []

    left_tables = compare.authored_tables(left, left_build or "GRCh38")
    right_tables = compare.authored_tables(right, right_build or "GRCh38")

    frame_verdict = _verdict(left_build, right_build)
    frame = FrameVerdict(
        left_build=left_build,
        right_build=right_build,
        verdict=frame_verdict,
        note={"same": _FRAME_SAME, "moved": _FRAME_MOVED}.get(frame_verdict, _FRAME_UNKNOWN),
    )

    tables: list[TableComparison] = []
    for csv in sorted(set(left_tables) | set(right_tables)):
        diff, notes = compare.compare_table(
            csv, left_tables.get(csv), right_tables.get(csv), max_groups, examples_per_group
        )
        unknown += [Unknown(subject=s, reason=r) for s, r in notes]
        tables.append(
            TableComparison(
                csv=diff.csv,
                identity_scope=diff.identity_scope,
                presence=diff.presence,
                spelling_left=diff.spelling_left,
                spelling_right=diff.spelling_right,
                rows_left=diff.rows_left,
                rows_right=diff.rows_right,
                row_key=diff.row_key,
                key_collisions=diff.key_collisions,
                unchanged=diff.unchanged,
                added=diff.added,
                removed=diff.removed,
                changed=[
                    ChangeGroupOut(columns=g.columns, rows=g.rows, examples=g.examples)
                    for g in diff.changed
                ],
            )
        )

    derived_diffs, derived_notes = compare.compare_derived(left, right, ROSTER)
    unknown += [Unknown(subject=s, reason=r) for s, r in derived_notes]
    derived = [
        DerivedComparison(
            csv=d.csv,
            verdict=d.verdict,
            left_signature=d.left_signature,
            right_signature=d.right_signature,
            signature_source=d.signature_source,
            rows_left=d.rows_left,
            rows_right=d.rows_right,
        )
        for d in derived_diffs
    ]

    left_sig = compare.content_signature_of(left)
    right_sig = compare.content_signature_of(right)
    for side, sig, path in (("left", left_sig, left), ("right", right_sig, right)):
        if sig is None:
            unknown.append(
                Unknown(
                    subject=f"content_signature ({side})",
                    reason=f"{path.name} could not be read as a spec directory, so the "
                    "content verdict is unknown rather than moved.",
                )
            )

    metadata: list[MetadataDelta] = []
    for key in sorted(set(left_module) | set(right_module)):
        a, b = left_module.get(key), right_module.get(key)
        if a != b:
            metadata.append(
                MetadataDelta(what=f"module_spec.yaml:{key}", left=_text(a), right=_text(b))
            )
    for name in ("README.md", "logo.png"):
        a, b = (left / name).is_file(), (right / name).is_file()
        if a != b:
            metadata.append(
                MetadataDelta(
                    what=name,
                    left="present" if a else "absent",
                    right="present" if b else "absent",
                )
            )

    return ModuleComparison(
        left=ComparedSide(path=str(left), genome_build=left_build, tables=len(left_tables)),
        right=ComparedSide(path=str(right), genome_build=right_build, tables=len(right_tables)),
        frame=frame,
        content=_verdict(left_sig, right_sig),
        left_content_signature=left_sig,
        right_content_signature=right_sig,
        tables=tables,
        derived=derived,
        metadata=metadata,
        unknown=unknown,
        note=(
            "What moved, never which side is right. `metadata[]` carries what moved that no "
            "identity records, and `unknown[]` says what this report is not telling you. "
            "`artifact.digest` is deliberately absent: comparing it needs both manifests, and "
            "across two compiler versions it differs for a reason nobody asked about."
        ),
    )


def _text(value: object) -> str | None:
    return None if value is None else str(value)
