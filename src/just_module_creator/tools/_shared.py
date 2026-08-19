"""Conversion helpers shared by the tool modules.

Everything here exists to keep one promise from CLAUDE.md: *report, never
repair*, and *preserve three-valued answers*. The upstream dataclasses already
distinguish error/warning/info and applied/refused; these converters carry that
across the MCP boundary field-for-field instead of flattening it.
"""

from __future__ import annotations

from collections.abc import Container
from importlib import metadata
from pathlib import Path
from typing import Any

from fastmcp.exceptions import ToolError

from just_module_creator.models import (
    LintAlteration,
    LintFinding,
    PublishedVersion,
    SchemaVersions,
)
from just_module_creator.settings import Settings

# Read once, at import, and deliberately: a running process keeps the modules it
# already imported, so re-reading package metadata per call would report a
# version this process is not actually executing the moment anything upgrades the
# environment underneath it (`uv sync` while a stdio server is alive). Read here,
# the stamp describes the code that produced the answer — which is the whole
# point of stamping it.
_SCHEMA_VERSIONS = SchemaVersions(
    format_version=metadata.version("just-dna-format"),
    compiler_version=metadata.version("just-dna-compiler"),
)


def resolve_dir(raw: str, settings: Settings, *, must_exist: bool = True) -> Path:
    """Resolve a user-supplied directory, honouring ``JMC_WORKSPACE``.

    ``workspace`` is a containment boundary, not a convenience: an MCP server
    reachable over HTTP would otherwise compile into any path the process can
    write. Unset (the default) means no restriction, which is right for stdio.
    """
    path = Path(raw).expanduser()
    try:
        path = path.resolve()
    except OSError as exc:  # pragma: no cover - unusual filesystem states
        raise ToolError(f"Cannot resolve path {raw!r}: {exc}") from exc

    if settings.workspace:
        root = Path(settings.workspace).expanduser().resolve()
        if not path.is_relative_to(root):
            raise ToolError(
                f"{path} is outside the configured workspace {root}. "
                "Set JMC_WORKSPACE to widen it, or pass a path inside it."
            )

    if must_exist and not path.is_dir():
        raise ToolError(f"{path} is not an existing directory.")
    return path


def offline_for(settings: Settings, requested: bool) -> bool:
    """Resolve the effective offline flag. ``JMC_OFFLINE`` is a ceiling.

    A per-call ``offline=False`` must never punch through a server configured
    for zero egress, so the two combine with OR rather than the argument winning.
    """
    return bool(settings.offline or requested)


def to_findings(items: Any) -> list[LintFinding]:
    """Convert upstream ``Finding`` dataclasses, preserving ``level`` verbatim.

    ``line`` is passed through and never derived. Upstream's ``row`` is a 0-based
    data-row index while ``line`` is the 1-based header-inclusive file line, so
    computing one from the other would bake in an offset that silently becomes
    wrong the day upstream changes either convention.
    """
    out: list[LintFinding] = []
    for f in items or []:
        out.append(
            LintFinding(
                row=getattr(f, "row", None),
                column=getattr(f, "column", None),
                level=getattr(f, "level", "info"),
                message=getattr(f, "message", str(f)),
                line=getattr(f, "line", None),
            )
        )
    return out


def to_alterations(items: Any) -> list[LintAlteration]:
    """Convert upstream ``Alteration`` dataclasses.

    ``applied`` and ``refusal`` are the point of this type — a refused
    suggestion is the tool declining to author a redundancy-bearing cell, and
    dropping it would turn a deliberate abstention into a silent omission.
    """
    out: list[LintAlteration] = []
    for a in items or []:
        out.append(
            LintAlteration(
                row=getattr(a, "row", 0),
                column=getattr(a, "column", ""),
                before=str(getattr(a, "before", "")),
                after=str(getattr(a, "after", "")),
                kind=getattr(a, "kind", "advisory"),
                applied=bool(getattr(a, "applied", False)),
                source=getattr(a, "source", ""),
                refusal=getattr(a, "refusal", None),
                note=getattr(a, "note", "") or "",
            )
        )
    return out


def to_published_versions(refs: Any) -> list[PublishedVersion]:
    """Project upstream ``VersionRef``s. ``yanked`` is kept because it is a trap.

    A yank hides a version from resolution; it does **not** release the content
    claim, so a duplicate match that is already yanked still 409s a publish. An
    author who reads "yanked" as "gone" concludes the name is free.

    Lives here rather than beside either caller because two tools answer the
    duplicate question from different tiers — `registry_is_published` (essentials,
    no token) and the pre-flights (gated) — and two projections of one payload is
    how the two start disagreeing about what a match means.
    """
    out: list[PublishedVersion] = []
    for ref in refs or []:
        ns = str(getattr(ref, "namespace", ""))
        name = str(getattr(ref, "name", ""))
        version = str(getattr(ref, "version", ""))
        out.append(
            PublishedVersion(
                canonical_id=f"{ns}/{name}@{version}",
                namespace=ns,
                name=name,
                version=version,
                yanked=bool(getattr(ref, "yanked", False)),
            )
        )
    return out


def jsonable(value: Any) -> Any:
    """Coerce Paths and nested containers into JSON-safe values."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    return value


def known_kind(csv_name: str, valid: Any, machine_produced: Container[str] = ()) -> str:
    """Normalize and check a table-kind argument, with a usable error.

    ``machine_produced`` is the roster of names that exist in a spec directory but are
    written by a pass rather than by a person. Passing it turns *"Unknown table kind
    'resolution.csv'"* — which was false, and sent a reader looking for a typo — into a
    pointer at the route that does answer. Every caller of this function is an authoring
    route, so the redirect is the same wherever it fires: the file is real, it is not
    yours to write, and its columns are answered elsewhere.
    """
    name = csv_name.strip()
    if not name.endswith(".csv"):
        name = f"{name}.csv"
    if name in valid:
        return name
    if name in machine_produced:
        raise ToolError(
            f"{name} is a machine-produced table, not an authored one: a pass writes it and the "
            f"compiler fact-hashes it, so nothing here templates it, lints it or scaffolds it. "
            f"Call describe_machine_table({name!r}) for its columns — it is yours to read."
        )
    raise ToolError(
        f"Unknown table kind {csv_name!r}. Authorable kinds: {', '.join(sorted(valid))}."
    )


def schema_versions() -> SchemaVersions:
    """The packages that generated a schema answer, for stamping onto it.

    One source for every generated answer, so two tools can never disagree about
    which release they described. A stale plugin cache is the case this exists
    for: it serves an old toolchain silently, and every skill tells an agent to
    ask the tool rather than trust its memory.
    """
    return _SCHEMA_VERSIONS
