"""Read a module's logs before the catalog keeps them forever. `RM25`.

`_collect_logs` runs on **every** compile with no flag and no opt-out: any `*.log`
in a spec directory is copied into the artifact, hashed into the manifest and
uploaded on publish. That is correct as designed — the whole point of `logs/` is
that it travels and accumulates across versions — and it means the author is the
only one who can decide a log should not go. Today nothing shows them the file.

**Report, never strip.** A log is a provenance record; silently editing one is the
opposite of what it exists for. This names what is in the file and leaves every
decision, including "publish it anyway", to the person.

**The question is narrow, and widening it is how this becomes noise:** *would the
author be surprised to see this in the catalog?* Not "is this a secret" — this is
not a secret scanner and must not grow into one.

The calibration case is `data/interim/rm15_remediation/*/logs/quote-remediation.log`,
which travelled to two polygon rehearsals and **should produce nothing**: 73 lines,
no paths, no credentials, and an honest header naming the model that did the work
and stating that no human read the articles. A check that flags that log is a check
with a false positive, and the test asserts exactly that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: A line longer than this is the signature of an embedded system prompt or a
#: serialized payload rather than a run log. The remediation fixtures top out at
#: 92 characters; the submitted Agno transcripts carry single lines orders of
#: magnitude past this.
LONG_LINE = 2000

#: Bytes. Above this a log is worth a second look purely on size — it ships to the
#: catalog verbatim and cannot be removed from a published version.
LARGE_FILE = 1_000_000

#: An absolute filesystem path. Anchored on the roots a real machine actually uses,
#: rather than on a bare leading slash, so a URL path and an `/api/v1/` fragment do
#: not match.
_ABSOLUTE_PATH = re.compile(
    r"(?:^|[\s\"'=(\[])((?:/(?:home|Users|root|mnt|media|opt|srv|var|tmp|data|private)/[\w.\-/]+)"
    r"|(?:[A-Za-z]:\\[\w.\-\\]+))"
)

#: Credential SHAPES, never a wordlist. `token` alone is a false positive waiting to
#: happen — the fixture says "every rsID token" — so a name only counts when an
#: assignment and a value of real length follow it.
_CREDENTIAL = re.compile(
    r"(?:(?:api[_\-]?key|secret|password|passwd|auth_token|access_token|bearer_token"
    r"|authorization)\s*[:=]\s*\S{8,})"
    r"|(?:Bearer\s+[\w.\-]{10,})"
    r"|(?:\bsk-[A-Za-z0-9]{16,})"
    r"|(?:\bghp_[A-Za-z0-9]{20,})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Flag:
    """One thing in one log that the author may not mean to publish."""

    kind: str
    line: int | None
    detail: str


def _redact(text: str, limit: int = 120) -> str:
    """Enough of the line to recognise it, never the whole of a long one.

    A flag that reprints a credential in full has copied it somewhere new, and this
    output is read by an agent whose transcript is itself kept.
    """
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


def scan_text(text: str) -> list[Flag]:
    """Every flag in one log's contents. Deterministic order: by line, then kind."""
    flags: list[Flag] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if len(line) > LONG_LINE:
            flags.append(
                Flag(
                    kind="very_long_line",
                    line=number,
                    detail=(
                        f"{len(line)} characters on one line — the shape of an embedded system "
                        f"prompt or a serialized payload rather than a run log"
                    ),
                )
            )
        for match in _ABSOLUTE_PATH.finditer(line):
            flags.append(
                Flag(
                    kind="absolute_path",
                    line=number,
                    detail=f"{match.group(1)} — names this machine, not the module",
                )
            )
        if _CREDENTIAL.search(line):
            flags.append(
                Flag(
                    kind="credential_shaped",
                    line=number,
                    detail=f"credential-shaped assignment: {_redact(line)}",
                )
            )
    return sorted(flags, key=lambda f: (f.line or 0, f.kind))


def scan_file(path: Path) -> list[Flag]:
    """Flags for one log on disk, size included."""
    flags: list[Flag] = []
    size = path.stat().st_size
    if size > LARGE_FILE:
        flags.append(
            Flag(
                kind="large_file",
                line=None,
                detail=(
                    f"{size / 1_000_000:.1f} MB ships to the catalog verbatim and cannot be "
                    f"removed from a published version"
                ),
            )
        )
    # `errors="replace"` rather than a second try/except: a log that is not valid
    # UTF-8 is itself worth seeing, and refusing to read it would hide the file
    # this exists to show.
    flags.extend(scan_text(path.read_text(encoding="utf-8", errors="replace")))
    return flags


def logs_in(spec_dir: Path) -> list[Path]:
    """Every file a compile would sweep up: `logs/**/*.log` and top-level `*.log`.

    Mirrors what `_collect_logs` collects rather than restating a rule — if it
    ever widens, this is the line that has to move with it.
    """
    found = {*spec_dir.glob("*.log"), *(spec_dir / "logs").rglob("*.log")}
    return sorted(found)
