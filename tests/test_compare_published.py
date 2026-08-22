"""`compare_to_published` — a spec directory against one published manifest (RM19).

The manifest each case compares against is **computed from the real spec by
upstream's own functions** — `compiler.content_signature` and
`compiler.authored_input_entries`, the same two a real publish uses — rather than
hand-written. A typed-out manifest would only prove the comparison agrees with
whatever was typed.

Nothing here opens a socket: `_compare_published` is the pure half, which is the
whole reason the tool's network work is a separate two lines.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from just_dna_compiler import compiler
from just_dna_format.manifest import ModuleManifest

from just_module_creator.tools.comparison import _compare_published

REFERENCE = Path("/data/sources/just-dna-format/reference_examples/hfe_hemochromatosis")

pytestmark = pytest.mark.skipif(
    not REFERENCE.is_dir(),
    reason="the sibling format checkout is not present; these cases are measured on its corpus",
)


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    target = tmp_path / "spec"
    shutil.copytree(REFERENCE, target)
    return target


def _authored_names(spec_dir: Path) -> set[str]:
    """The names a publish records, taken from upstream rather than listed here."""
    return {e.name for e in compiler.authored_input_entries(spec_dir)}


def manifest_of(spec_dir: Path) -> ModuleManifest:
    """A manifest that honestly describes `spec_dir`, built by the publisher's own code."""
    return ModuleManifest.model_validate(
        {
            # The three blocks a manifest cannot exist without. They are scaffolding
            # for the two fields under test and nothing here reads them.
            "identity": {"name": "hfe_hemochromatosis"},
            "display": {
                "title": "HFE",
                "description": "reference example",
                "report_title": "HFE",
            },
            "artifact": {"digest": "sha256:not-under-test"},
            "genome_build": "GRCh38",
            # These two are the point, and both are computed from the real spec by
            # the same functions a real publish uses.
            "content_signature": compiler.content_signature(spec_dir),
            # `file_entries` — the RAW hasher — because that is what fills
            # `manifest.inputs[]` on a real publish, local or server-side. This said
            # `authored_input_entries` (the newline-normalizing one) until 2026-08-22,
            # which is the whole reason the CRLF bug below survived: the fixture
            # manufactured a manifest using the tool's own wrong rule and then
            # confirmed the two agreed. A check whose expected value comes from the
            # thing under test measures nothing, which is a rule this repo holds
            # about module data and had broken in its own suite.
            "inputs": [
                e.model_dump()
                for e in compiler.file_entries(spec_dir, sorted(_authored_names(spec_dir)))
            ],
        }
    )


def compare(spec_dir: Path, manifest: ModuleManifest):
    return _compare_published(spec_dir, "GRCh38", "ns/m@1.0.0", "prod", manifest)


def test_a_spec_against_its_own_manifest_is_same_everywhere(spec: Path) -> None:
    """The round trip. If this ever fails, every other verdict here is noise."""
    result = compare(spec, manifest_of(spec))

    assert result.content == "same"
    assert result.frame.verdict == "same"
    assert result.files, "the reference example should carry authored inputs"
    assert {f.verdict for f in result.files} == {"same"}
    assert "Nothing to chase" in result.next_step


def test_an_edited_row_moves_content_and_names_the_file(spec: Path) -> None:
    """Both layers move together when the change is real, and the handover appears."""
    published = manifest_of(spec)
    variants = spec / "variants.csv"
    rows = variants.read_text(encoding="utf-8").splitlines()
    # A real authored cell, changed to a different real value: the first row's
    # `genotype`. Chosen off the fixture rather than by find-and-replace, so the
    # edit cannot silently be a no-op the way a missing search string would be.
    assert rows[1].startswith("rs776994377,,,,,C/C,"), rows[1][:40]
    rows[1] = rows[1].replace("rs776994377,,,,,C/C,", "rs776994377,,,,,C/T,", 1)
    variants.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = compare(spec, published)

    assert result.content == "moved"
    assert [f.name for f in result.files if f.verdict == "moved"] == ["variants.csv"]
    assert "registry_download" in result.next_step and "compare_modules" in result.next_step


def test_a_formatting_only_edit_moves_the_bytes_and_not_the_content(spec: Path) -> None:
    """The distinction the whole report is ordered around.

    A reordered row changes the file digest and leaves `content_signature` where
    it was. A tool that read the per-file layer first would report this as a
    content change, which is the false alarm the design refuses to raise.
    """
    published = manifest_of(spec)
    variants = spec / "variants.csv"
    lines = variants.read_text(encoding="utf-8").splitlines()
    header, body = lines[0], lines[1:]
    assert len(body) > 1, "need at least two rows to reorder"
    variants.write_text("\n".join([header, *reversed(body)]) + "\n", encoding="utf-8")

    result = compare(spec, published)

    assert result.content == "same"
    assert any(f.verdict == "moved" and f.name == "variants.csv" for f in result.files)
    # And the report must say so in its own words, not leave it to the reader.
    assert "byte inequality" in result.note.lower()


def test_a_different_build_is_the_whole_answer(spec: Path) -> None:
    """Coordinates in two assemblies are not comparable, whatever the counts say."""
    published = manifest_of(spec)
    result = _compare_published(spec, "GRCh37", "ns/m@1.0.0", "prod", published)

    assert result.frame.verdict == "moved"
    assert "not comparable" in result.frame.note


def test_a_manifest_with_no_content_signature_is_unknown_never_moved(spec: Path) -> None:
    """A field the published version predates says nothing, and must not say 'changed'."""
    published = manifest_of(spec)
    published.content_signature = None

    result = compare(spec, published)

    assert result.content == "unknown"
    assert any(u.subject == "content_signature (published)" for u in result.unknown)
    assert any("never 'moved'" in u.reason for u in result.unknown)


def test_a_missing_local_file_is_reported_rather_than_dropped(spec: Path) -> None:
    """A file the publish recorded and this directory no longer has."""
    published = manifest_of(spec)
    (spec / "studies.csv").unlink()

    result = compare(spec, published)

    studies = next(f for f in result.files if f.name == "studies.csv")
    assert studies.verdict in {"moved", "unknown"}
    assert studies.published_sha256 is not None


def test_a_crlf_file_that_did_not_change_is_reported_as_same(spec: Path) -> None:
    """The comparator must hash the local side the way the publisher hashed it.

    It did not. It used `newline_normalized_file_entries`, whose normalization
    exists for the closure attestation so that rewriting line endings cannot
    un-close a module — and `manifest.inputs[]` is deliberately raw, which upstream's
    RM82 docstring states outright. Borrowing the normalizer here inverted its
    purpose: it fired on exactly the CRLF files it was meant to protect.

    Measured on the eight modules published to the production registry: 31 of the 34
    authored CSVs carry CRLF, because Python's `csv` module writes `\r\n`, so the
    per-file verdict was wrong for effectively every file of every module. The digest
    printed as "local" matched no bytes anyone had ever recorded.

    This asserts the property rather than a digest: unchanged bytes are `same`, and
    the digest reported for the local side is the digest of the bytes on disk.
    """
    crlf = spec / "variants.csv"
    body = crlf.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    crlf.write_bytes(body)
    assert b"\r\n" in crlf.read_bytes(), "the fixture did not end up with CRLF"

    result = compare(spec, manifest_of(spec))

    entry = next(f for f in result.files if f.name == "variants.csv")
    assert entry.verdict == "same", (
        f"a byte-identical CRLF file was reported {entry.verdict!r}; "
        f"local={entry.local_sha256} published={entry.published_sha256}"
    )
    assert entry.local_sha256 is not None
    assert entry.local_sha256.endswith(hashlib.sha256(crlf.read_bytes()).hexdigest())
    assert result.content == "same"
