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
        """Record that an authored value deliberately outranks what a source says.

        **Call this in response to a reported mismatch, never ahead of one.** That
        ordering is the whole design. A cross-check that flags a row against ClinVar
        is doing one of two jobs and they are indistinguishable at the moment it
        fires: either the row is wrong — a hallucination, or somebody's stale
        recollection — and the warning has just caught it, or the module is right and
        *current* while the archive lags, because of a retraction, a refuting
        meta-analysis or a larger cohort the archive has not absorbed. An author able
        to mark a row outranked **before** the mismatch is reported would destroy the
        only signal that catches the first case.

        So: read the finding, decide, then record the decision here.

        `reason` is prose and there is deliberately no vocabulary for it. Which of a
        retraction, a meta-analysis and a single larger cohort outranks an archive
        call is a natural-language judgement; a pick-list would invite an agent to
        choose the nearest label instead of thinking. Say what changed, name the
        evidence, and give a PMID where there is one.

        **This does not silence anything.** The cross-check still reports the
        mismatch — whether upstream downgrades its severity on the presence of a
        record is their contract question, filed as `S52` — and the row stays in the
        review queue precisely so somebody revisits it. "Somebody decided this" never
        means green.

        The record is bound to the value it justifies by digest, so editing that cell
        again makes the record stale rather than silently carrying the old reason onto
        a new value. Written into `provenance.json` — upstream's own file, recognised
        by the registry, outside `artifact.digest` — and logged into
        `logs/authoring.log`, which travels with the module.
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
                f"{record.recorded_at} override {record.variant_key} {record.field}="
                f"{authored_value!r} outranks {source_name}"
                + (f" ({source_value!r})" if source_value else "")
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

        `still_bound: false` is the one to read first: the authored cell was edited
        again after the record was written, so the reason on file no longer describes
        the value it is attached to.
        """
        target = resolve_dir(spec_dir, settings)
        queued = await run_sync(lambda: overrides.review_queue(target))
        _, foreign = await run_sync(lambda: overrides.read_records(target))
        return ReviewQueue(
            spec_dir=str(target),
            total=len(queued),
            unbound=sum(1 for q in queued if not q.still_bound),
            retirable=sum(1 for q in queued if q.mismatch_state == "resolved"),
            entries=queued,
            other_provenance=list(foreign),
        )
