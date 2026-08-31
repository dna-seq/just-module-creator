"""ESSENTIALS — recording that an authored value outranks a source, and reading the queue back.

`RM16`. §2 says this layer may write and revise; what it owes in return is that
every authoring move goes through a log, and that an edit made **against** a source
carries a reason that outranks it. These two tools are that half of the bargain.

Both are essentials because both are bounded by what the caller named — one row,
one field, one spec directory — and neither touches the network.

**Neither of them makes anything pass.** A recorded outrank is downgraded and still
visible: the disagreement between a module and an archive is real and stays
interesting forever. What the record adds is *who decided and why*, so a reader two
source releases later can tell a considered judgement from a careless overwrite.
"""

from __future__ import annotations

from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from just_module_creator import overrides
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import OverrideResult, ReviewQueue
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import resolve_dir

log = get_logger()

AUTHORING_LOG = "logs/authoring.log"


def append_move(spec_dir: Path, line: str) -> Path:
    """Append one authoring move to the module's own log.

    `logs/**.log` is swept up by every compile and published with **no opt-out**,
    which is exactly why it is the right home: a record that travels with the module
    costs the author nothing and cannot be quietly dropped. It moves no signature and
    no identity — a log is never parsed into rows — so writing one is free.

    Nothing here writes an absolute path or a credential into that file, because
    everything in it is published verbatim.
    """
    directory = spec_dir / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    path = spec_dir / AUTHORING_LOG
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")
    return path


    # This said 'in response to a reported mismatch, never ahead of one', full stop, until
    # 2026-08-22 — which contradicted the server's own rule 2, and an unattended run hit it
    # exactly: every edit it made was prompted by its own arithmetic, the checks having come
    # back clean, so it could satisfy one instruction only by violating the other.
    # `source_value` was already the discriminator; the docstring just did not say so. Whether
    # upstream downgrades a check's severity on the presence of a record is their contract
    # question, filed as S52. The digest is of the authored VALUE STRING, not the cell, so two
    # rows corrected to the same value carry the same `value_sha256`; the record is identified
    # by (variant_key, field) and the digest says whether that cell still holds what was
    # justified.
def register_provenance(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Record why an authored value outranks a source",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        )
    )
    async def record_override(
        spec_dir: str,
        variant_key: str,
        field: str,
        authored_value: str,
        source_name: str,
        reason: str,
        recorded_by: str,
        source_value: str | None = None,
        human_reviewed: bool = False,
    ) -> OverrideResult:
        """Record that an authored value deliberately outranks a source, or that you edited
        a cell.

        **`source_value` is the discriminator.** Given, this is an *outranking claim* —
        you assert the cell beats what that source says — and the ordering binds: read
        the finding first, decide, then record, because a cross-check that flags a row
        is doing one of two indistinguishable jobs (catching a wrong row, or lagging
        behind a module that is right and current) and marking a row outranked *before*
        the mismatch is reported destroys the only signal that catches the first.
        Omitted, this is an *edit log*: you changed a cell and are recording who and
        why, which is the server's rule 2 and waits for nothing — and it is written as
        an authored move, not an outranking one, with `provenance.json`'s `outranks`
        map left empty. Claiming a dispute you never had dilutes the signal a reviewer
        routes scrutiny by, and this log publishes verbatim. One call is one
        `(variant_key, field)` pair with no bulk form, so a column-wide correction is
        that many calls — where the set is too large, write one record and say in
        `reason` how the set was derived. `reason` is prose with no vocabulary on
        purpose, since which of a retraction, a meta-analysis or a larger cohort
        outranks an archive call is a judgement a pick-list would replace with the
        nearest label. It **silences nothing**: the check still reports the mismatch and
        the row stays in the review queue. And `reason` and `recorded_by` are
        **PUBLISHED verbatim** — every compile sweeps `logs/**.log` in with no opt-out
        and a published version is immutable — so write a reason, never a paste: no
        credential, no absolute path, no transcript fragment.
        """
        target = resolve_dir(spec_dir, settings)
        record = overrides.OverrideRecord(
            variant_key=variant_key,
            field=field,
            authored_value=authored_value,
            source_name=source_name,
            source_value=source_value,
            reason=reason,
            recorded_by=recorded_by,
            human_reviewed=human_reviewed,
            value_sha256=overrides.value_digest(authored_value),
        )

        def write() -> tuple[Path, bool]:
            path, replaced = overrides.upsert(target, record)
            append_move(
                target,
                # Two verbs, because this tool has two jobs and the log published
                # only one of them. `source_value` is the discriminator: with one,
                # the author read a source and disagreed; without, they authored a
                # cell no source supplies — a weight, a conclusion — and calling
                # that "outranks" claims a dispute that never happened. Six of the
                # seven records in a 2026-08-31 benchmark were the second kind, and
                # this file publishes verbatim (`F71`).
                f"{record.recorded_at} "
                + (
                    f"override {record.variant_key} {record.field}="
                    f"{authored_value!r} outranks {source_name} ({source_value!r})"
                    if source_value
                    else f"authored {record.variant_key} {record.field}="
                    f"{authored_value!r} (judged; no value from {source_name} to disagree with)"
                )
                + f" by={recorded_by} human_reviewed={str(human_reviewed).lower()}"
                + (" [replaced an earlier record]" if replaced else ""),
            )
            return path, replaced

        path, replaced = await run_sync(write)
        log.info("recorded override %s.%s in %s", variant_key, field, path.name)
        return OverrideResult(
            written_to=str(path),
            logged_to=str(target / AUTHORING_LOG),
            replaced_existing=replaced,
            record=record,
            note=(
                "Recorded, not resolved. The cross-check still reports this mismatch and the row "
                "stays in `review_queue` — a recorded outrank is downgraded, never passed."
            ),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="The overridden rows a reviewer should open first",
            readOnlyHint=True,
            idempotentHint=True,
        )
    )
    async def review_queue(spec_dir: str) -> ReviewQueue:
        """Rank the rows where somebody overruled a source. Offline; writes nothing.

        A review pass has had no priority list: a reviewer opens a module and picks
        somewhere to start. **These are the rows to start with.** They are the
        highest-value judgements in the module and the easiest to forget — whoever
        wrote the justification understood it, and six months and two source releases
        later nobody remembers whether the retraction that motivated it was itself
        superseded.

        Three states, and the third is not a pass:

        * **`standing`** — the module and the archive still disagree. Read the reason
          and decide whether it still holds.
        * **`resolved`** — the archive now agrees with the authored value. The
          override turned out to be **right**, which is the only evidence anywhere in
          this format that an authored judgement was later vindicated, and the record
          is retirable.
        * **`unknown`** — the question could not be put offline. **Not agreement.**
          Only `clin_sig` has the archive's current answer recorded inside the module,
          in `clinical_assertions.csv`; without that sidecar, or for any other field,
          nothing here can say.

        `still_bound` is three-valued and `null` is not `false`. **`false` is the one to
        read first**: the authored cell was edited again after the record was written, so
        the reason on file no longer describes the value it is attached to. **`null` means
        there is no such cell to compare** — the row is gone, or `variants.csv` does not
        carry that column — so nobody edited anything and the question could not be put.
        Those are counted separately, as `unbound` and `subject_absent`.
        """
        target = resolve_dir(spec_dir, settings)
        queued = await run_sync(lambda: overrides.review_queue(target))
        _, foreign = await run_sync(lambda: overrides.read_records(target))
        return ReviewQueue(
            spec_dir=str(target),
            total=len(queued),
            unbound=sum(1 for q in queued if q.still_bound is False),
            subject_absent=sum(1 for q in queued if q.still_bound is None),
            retirable=sum(1 for q in queued if q.mismatch_state == "resolved"),
            entries=queued,
            other_provenance=list(foreign),
        )
