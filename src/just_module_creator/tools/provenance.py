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

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import hints
from mcp.types import ToolAnnotations

from just_module_creator import overrides
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import OverrideResult, PruneResult, ReviewQueue
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import resolve_dir
from just_module_creator.tools.refresh import capture_dir, capture_now, finalize_capture

log = get_logger()

AUTHORING_LOG = "logs/authoring.log"


def move_line(record: overrides.OverrideRecord, replaced: bool) -> str:
    """The one line an override record publishes in `logs/authoring.log`.

    Three verbs, because the record has three jobs and the log once published only
    one of them. `source_value` is the discriminator between the first two: with one,
    the author read a source and disagreed; without, they authored a cell no source
    supplies — a weight, a conclusion — and calling that "outranks" claims a dispute
    that never happened. Six of the seven records in a 2026-08-31 benchmark were the
    second kind, and this file publishes verbatim (`F71`). The third is a move on a
    whole table (`F104`).
    """
    value = record.authored_value
    return (
        f"{record.recorded_at} "
        + (
            f"table {record.variant_key} {record.field}={value!r} "
            f"(source {record.source_name}; {' '.join(record.reason.split())})"
            if overrides.is_table_scope(record)
            else f"override {record.variant_key} {record.field}="
            f"{value!r} outranks {record.source_name} ({record.source_value!r})"
            if record.source_value
            else f"authored {record.variant_key} {record.field}="
            f"{value!r} (judged; no value from {record.source_name} to disagree with)"
        )
        + f" by={record.recorded_by} human_reviewed={str(record.human_reviewed).lower()}"
        + (" [replaced an earlier record]" if replaced else "")
    )


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
            read_only_hint=False,
            idempotent_hint=True,
            destructive_hint=False,
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
        `reason` how the set was derived. **A move on a whole table** — a trim to a
        key set, a file removed — is one record too: `variant_key` is the table's
        file name (`pharm_variants.csv`), `field` is `rows` or `file`,
        `authored_value` states what was kept and dropped with counts, and `reason`
        how the kept set was derived; `review_queue` lists it as table-scope rather
        than as a row it cannot find. `reason` is prose with no vocabulary on
        purpose, since which of a retraction, a meta-analysis or a larger cohort
        outranks an archive call is a judgement a pick-list would replace with the
        nearest label. It **silences nothing**: the check still reports the mismatch and
        the row stays in the review queue. And `reason` and `recorded_by` are
        **PUBLISHED verbatim** — every compile sweeps `logs/**.log` in with no opt-out
        and a published version is immutable — so write a reason, never a paste: no
        credential, no absolute path, no transcript fragment.
        """
        target = resolve_dir(spec_dir, settings)
        # A `.csv` in the row slot is the table-scope convention (F104), and the only
        # fields it admits are the two the queue can classify; anything else would be
        # a cell record naming a file as its row, which `review_queue` reads as a
        # missing subject and nobody reads as a trim.
        if variant_key.endswith(".csv") and field not in overrides.TABLE_SCOPE_FIELDS:
            raise ToolError(
                f"{variant_key} names a table, so `field` must be one of "
                f"{sorted(overrides.TABLE_SCOPE_FIELDS)}: `rows` for a set of rows kept "
                "or dropped, `file` for the whole table removed. Put the counts in "
                "`authored_value` and how the set was derived in `reason`."
            )
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
            append_move(target, move_line(record, replaced))
            return path, replaced

        path, replaced = await run_sync(write)
        log.info("recorded override %s.%s in %s", variant_key, field, path.name)
        return OverrideResult(
            written_to=str(path),
            logged_to=str(target / AUTHORING_LOG),
            replaced_existing=replaced,
            record=record,
            # The same split as the log line above, and it was missed when that one
            # was made (`F71` fixed the persisted half and left this). The
            # unconditional sentence told an author who had recorded an *authored*
            # cell that "the cross-check still reports this mismatch" — there was no
            # mismatch, no source and nothing to downgrade, so the one field the
            # caller reads back described a mode it had not used. A returned note is
            # the tool's answer to what just happened; getting it wrong is the same
            # defect as getting the log wrong, one field over.
            note=(
                (
                    "Recorded as a table-scope move: the counts and the derivation are "
                    "the record, and `review_queue` lists it apart from cell records. "
                    "It deleted nothing — the rows are already gone or kept by your "
                    "hand, and this is the attribution."
                )
                if overrides.is_table_scope(record)
                else (
                    "Recorded, not resolved. The cross-check still reports this mismatch "
                    "and the row stays in `review_queue` — a recorded outrank is "
                    "downgraded, never passed."
                )
                if source_value
                else (
                    "Recorded as an authored cell, not an outrank. No source supplied a "
                    "value here, so nothing was disputed and nothing is silenced: the "
                    "record is the attribution, and `review_queue` ranks it by the "
                    "judgement it carries rather than by a disagreement."
                )
            ),
        )

    # The trim was a hand move with a table-scope log record until 2026-09-24 (F104), and
    # module-curate says in bold that no tool makes it. That still holds: the keep-list is
    # the decision and it arrives as an argument; this applies it and decides nothing —
    # "making decision != executing it", in the owner's words (CLAUDE.md §10). Hence the
    # refusal on unmatched keep values: guessing that a typo meant the nearby rsID would be
    # the tool deciding. Rows are destroyed, so the capture-then-verify rule from
    # refresh_sidecar applies, reusing its capture root outside the spec directory.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Apply an author's keep-list to one authored table",
            read_only_hint=False,
            idempotent_hint=True,
            destructive_hint=True,
        )
    )
    async def prune_rows(
        spec_dir: str,
        table: str,
        keep: list[str],
        reason: str,
        recorded_by: str,
        source_name: str,
        key_column: str = "rsid",
        allow_unmatched: bool = False,
        dry_run: bool = False,
    ) -> PruneResult:
        """Keep only the rows of one authored table whose `key_column` is in `keep`.

        **The keep-list is the curation decision, and it is yours; this tool makes
        none.** It applies the list it is handed — trimming a drafted
        `pharm_variants.csv` to a panel's rsIDs, say — and logs the trim as one
        table-scope record (`field="rows"`, counts in `authored_value`, your `reason`
        saying how the list was derived). A keep value that matches no row is usually a
        typo that would drop the row it meant, so a real run **refuses** on any unless
        `allow_unmatched=true`; `dry_run` shows the counts, the dropped keys and the
        unmatched values and writes nothing.

        Before rewriting, the table's bytes are copied **outside** the spec directory,
        read back and hash-verified; a capture that does not verify means nothing is
        touched, and `capture` says where the old rows are. Derived sidecars are refused
        — re-derive those with `refresh_sidecar` — and so is a trim that keeps nothing,
        which is removing the file: do that by hand and log it with `record_override`
        (`field="file"`). `reason` and `recorded_by` publish verbatim in the log.
        """
        target = resolve_dir(spec_dir, settings)
        path = target / table
        if not table.endswith(".csv") or "/" in table or table != path.name:
            raise ToolError(f"{table!r} is not a table file name in the spec directory.")
        if table in hints.DERIVED_TABLE_MODELS:
            raise ToolError(
                f"{table} is a machine-written sidecar; trimming it by hand is overwritten by the "
                "next pass. Re-derive it with refresh_sidecar, or correct a row with an overlay."
            )
        if not path.is_file():
            raise ToolError(f"{table} is not in {target.name}.")
        if not keep:
            raise ToolError("An empty keep-list removes the table; do that by hand and log it.")

        def run() -> PruneResult:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            newline = "\r\n" if b"\r\n" in raw.split(b"\n", 1)[0] + b"\n" else "\n"
            reader = csv.DictReader(io.StringIO(text, newline=""))
            header = list(reader.fieldnames or [])
            if key_column not in header:
                raise ToolError(
                    f"{table} has no column {key_column!r}; its columns are {', '.join(header)}."
                )
            rows = list(reader)
            wanted = {k.strip() for k in keep if k.strip()}
            kept_rows = [r for r in rows if (r.get(key_column) or "").strip() in wanted]
            gone = [r for r in rows if (r.get(key_column) or "").strip() not in wanted]
            present = {(r.get(key_column) or "").strip() for r in rows}
            unmatched = sorted(wanted - present)
            dropped_keys = sorted({(r.get(key_column) or "").strip() for r in gone} - {""})
            result = PruneResult(
                table=table,
                key_column=key_column,
                dry_run=dry_run,
                rows_before=len(rows),
                kept=len(kept_rows),
                dropped=len(gone),
                dropped_keys=dropped_keys[:50],
                blank_key_rows=sum(1 for r in gone if not (r.get(key_column) or "").strip()),
                unmatched_keep=unmatched,
            )
            if dry_run:
                return result
            if unmatched and not allow_unmatched:
                result.refused = (
                    f"{len(unmatched)} keep value(s) match no row in {table} "
                    f"({', '.join(unmatched[:10])}). A typo there drops the row it meant to "
                    "keep. Fix the list, or pass allow_unmatched=true if they are meant to be "
                    "absent. Nothing was touched."
                )
                return result
            if not kept_rows:
                result.refused = "The keep-list keeps no row. Nothing was touched."
                return result
            if not gone:
                return result
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            directory = capture_dir(settings, target, f"prune-{table}")
            capture, verified = capture_now(
                directory,
                path,
                {"table": table, "rows": len(rows), "captured_at": stamp, "key": key_column},
            )
            if not verified:
                result.capture = str(capture)
                result.refused = (
                    f"The capture at {capture} did not read back byte-identical, so {table} "
                    "was not rewritten."
                )
                return result
            out = io.StringIO(newline="")
            writer = csv.DictWriter(out, fieldnames=header, lineterminator=newline)
            writer.writeheader()
            writer.writerows(kept_rows)
            path.write_text(out.getvalue(), encoding="utf-8", newline="")
            result.capture = str(finalize_capture(directory, stamp))
            record = overrides.OverrideRecord(
                variant_key=table,
                field="rows",
                authored_value=(
                    f"kept {len(kept_rows)} of {len(rows)} by {key_column}; "
                    f"dropped {len(gone)}"
                ),
                source_name=source_name,
                reason=reason,
                recorded_by=recorded_by,
                value_sha256=overrides.value_digest(
                    f"kept {len(kept_rows)} of {len(rows)} by {key_column}; dropped {len(gone)}"
                ),
            )
            _, replaced = overrides.upsert(target, record)
            result.logged_to = str(append_move(target, move_line(record, replaced)))
            result.record = record
            return result

        return await run_sync(run)

    @mcp.tool(
        annotations=ToolAnnotations(
            title="The overridden rows a reviewer should open first",
            read_only_hint=True,
            idempotent_hint=True,
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
        the reason on file no longer describes the value it is attached to. A variant is
        several rows, so a record may name one cell's value or the joined rendering
        `current_value` shows for all of them; both bind. **`null` means there is no such
        cell to compare** — the row is gone, or `variants.csv` does not carry that
        column — so nobody edited anything and the question could not be put.
        Those are counted separately, as `unbound` and `subject_absent`.
        """
        target = resolve_dir(spec_dir, settings)
        queued = await run_sync(lambda: overrides.review_queue(target))
        _, foreign = await run_sync(lambda: overrides.read_records(target))
        return ReviewQueue(
            spec_dir=str(target),
            total=len(queued),
            unbound=sum(1 for q in queued if q.still_bound is False),
            subject_absent=sum(1 for q in queued if q.still_bound is None and q.scope == "cell"),
            table_scope=sum(1 for q in queued if q.scope == "table"),
            retirable=sum(1 for q in queued if q.mismatch_state == "resolved"),
            entries=queued,
            other_provenance=list(foreign),
        )
