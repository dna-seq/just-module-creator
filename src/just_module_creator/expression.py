"""`expression_effects.csv` read against the module's OWN rows. Offline, writes nothing.

The AlphaGenome pass answers for every scored SNV in an interval, so its sidecar is
sized by the window rather than by the module. The question an author actually asks
is narrower — *which of my variants does the model call disruptive, for the gene the
row names* — and answering it is a join of three files: `variants.csv` for the gene
and the genotype, `resolution.csv` for the coordinate and the locus reference, and
`expression_effects.csv` keyed on `(chrom, start, alt, gene)`. That join was fifty
lines of script in the longevitymap port (`F106`) and a window planner on top of it
(`F105`); both live here so the planner and the reader cannot disagree about which
rows were scored.

The effect allele is the genotype's allele that is not the locus reference. A
genotype carrying only the reference allele has nothing for the model to score, and
is reported as such rather than as a miss.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from just_dna_compiler.compiler import load_spec_variants
from just_dna_format.vrs import normalize_chrom

#: Per-row outcomes, in the order a reader should worry about them. Every authored
#: row lands in exactly one, so the counts always sum to the rows read. `unreadable`
#: counts the loader's errors — a row that fails validation is not silently absent.
ROW_STATUSES = (
    "scored",
    "gene_not_at_locus",
    "not_scored",
    "reference_only",
    "no_reference",
    "no_gene",
    "unresolved",
    "unreadable",
)

#: Positions closer than this merge into one window. A 21-base window costs about
#: what a 1-base one does, and the longevitymap run found 100 bp a good cut.
MERGE_DISTANCE = 100
#: Bases added either side of a window's outermost position.
WINDOW_PAD = 10


@dataclass(frozen=True)
class ModuleSite:
    """One authored row, placed: where it sits and which alleles it asks about."""

    variant_key: str
    gene: str | None
    chrom: str | None
    start: int | None
    #: The locus reference allele; empty when neither the row nor resolution.csv has
    #: one, in which case no allele can be called non-reference.
    ref: str
    effect_alleles: tuple[str, ...]


@dataclass
class RowReport:
    """The join's answer: a status per row, and which sidecar rows are the module's."""

    status: Counter[str] = field(default_factory=Counter)
    examples: dict[str, list[str]] = field(default_factory=dict)
    #: `(chrom, start, alt, gene)` keys of sidecar rows an authored row asks about.
    matched_keys: set[tuple[str, int, str, str]] = field(default_factory=set)
    rows_read: int = 0


def _resolution(spec_dir: Path) -> dict[str, tuple[str, int, str]]:
    """`variant_key` → `(chrom, start, ref)` from `resolution.csv`, first locus only."""
    path = spec_dir / "resolution.csv"
    placed: dict[str, tuple[str, int, str]] = {}
    if not path.is_file():
        return placed
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            key, chrom, start = row.get("variant_key"), row.get("chrom"), row.get("start")
            if not (key and chrom and start) or key in placed:
                continue
            norm = normalize_chrom(chrom)
            if norm is None or not start.isdigit():
                continue
            placed[key] = (norm, int(start), (row.get("ref") or "").upper())
    return placed


def module_sites(spec_dir: Path) -> tuple[list[ModuleSite], list[str]]:
    """Every readable `variants.csv` row placed, plus the loader's errors for the rest.

    The row's own coordinate wins over `resolution.csv`'s, since it is what the
    author wrote; the resolution table fills what the row left out.
    """
    variants, errors, _warnings = load_spec_variants(spec_dir)
    placed = _resolution(spec_dir)
    sites: list[ModuleSite] = []
    for row in variants:
        key = row.variant_key or row.rsid or ""
        resolved = placed.get(key)
        chrom = normalize_chrom(row.chrom) if row.chrom else (resolved[0] if resolved else None)
        start = row.start if row.start is not None else (resolved[1] if resolved else None)
        ref = (row.ref or (resolved[2] if resolved else "")).upper()
        alleles = [a.strip().upper() for a in (row.genotype or "").split("/") if a.strip()]
        effect = tuple(sorted({a for a in alleles if ref and a != ref}))
        sites.append(
            ModuleSite(
                variant_key=key,
                gene=(row.gene or "").strip() or None,
                chrom=chrom,
                start=start,
                ref=ref,
                effect_alleles=effect,
            )
        )
    return sites, errors


def plan_windows(sites: list[ModuleSite]) -> list[tuple[str, str, int, int]]:
    """`(gene, chrom, start, end)` windows covering every row the model could score.

    Grouped by the row's own `gene` and chromosome, neighbours within
    `MERGE_DISTANCE` merged, each window padded by `WINDOW_PAD`. Rows without a gene
    or a coordinate are left out — the report says so per row. Sorted, so a re-run
    asks the same questions in the same order.
    """
    by_axis: dict[tuple[str, str], list[int]] = {}
    for site in sites:
        if site.gene and site.chrom and site.start is not None and site.effect_alleles:
            by_axis.setdefault((site.gene, site.chrom), []).append(site.start)
    windows: list[tuple[str, str, int, int]] = []
    for (gene, chrom), positions in sorted(by_axis.items()):
        positions = sorted(set(positions))
        lo = hi = positions[0]
        for pos in positions[1:]:
            if pos - hi <= MERGE_DISTANCE:
                hi = pos
                continue
            windows.append((gene, chrom, max(1, lo - WINDOW_PAD), hi + WINDOW_PAD))
            lo = hi = pos
        windows.append((gene, chrom, max(1, lo - WINDOW_PAD), hi + WINDOW_PAD))
    return windows


def effect_key(row: dict) -> tuple[str, int, str, str] | None:
    """The `(chrom, start, alt, gene)` a sidecar row answers for, or `None` if unplaced."""
    try:
        chrom, start = normalize_chrom(row["chrom"]), int(row["start"])
    except (KeyError, TypeError, ValueError):
        return None
    if chrom is None:
        return None
    return chrom, start, (row.get("alt") or "").upper(), (row.get("gene") or "").upper()


def _effect_index(path: Path) -> tuple[set[tuple[str, int, str, str]], set[tuple[str, int]]]:
    """Keys present in the sidecar, and the positions it answers at for ANY gene."""
    keys: set[tuple[str, int, str, str]] = set()
    positions: set[tuple[str, int]] = set()
    if not path.is_file():
        return keys, positions
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            key = effect_key(row)
            if key is not None:
                keys.add(key)
                positions.add(key[:2])
    return keys, positions


def report_rows(spec_dir: Path, *, example_cap: int = 10) -> RowReport:
    """One status per authored row, against the sidecar as it now stands.

    `gene_not_at_locus` is the case the longevitymap planner had to rediscover: the
    model answered at that position, but for other genes — the row's `gene` label is
    not one the Atlas scores there (a `LOC…` symbol, an antisense transcript, a gene
    on another chromosome). `not_scored` means nothing answered at the position at
    all: never queried, outside the window, or withheld upstream.
    """
    keys, positions = _effect_index(spec_dir / "expression_effects.csv")
    report = RowReport()
    sites, errors = module_sites(spec_dir)
    if errors:
        report.status["unreadable"] = len(errors)
        report.rows_read += len(errors)
        report.examples["unreadable"] = errors[:example_cap]
    for site in sites:
        report.rows_read += 1
        if site.chrom is None or site.start is None:
            status = "unresolved"
        elif not site.gene:
            status = "no_gene"
        elif not site.ref:
            # Placed, but with no reference allele — a resolution row written as
            # `source=authored` before enricher 0.7.1 has an empty `ref` (F103). Which
            # allele is the effect allele is then unknown, never "none of them".
            status = "no_reference"
        elif not site.effect_alleles:
            status = "reference_only"
        else:
            wanted = {(site.chrom, site.start, a, site.gene.upper()) for a in site.effect_alleles}
            hits = wanted & keys
            if hits:
                status = "scored"
                report.matched_keys |= hits
            elif (site.chrom, site.start) in positions:
                status = "gene_not_at_locus"
            else:
                status = "not_scored"
        report.status[status] += 1
        if status != "scored":
            bucket = report.examples.setdefault(status, [])
            if len(bucket) < example_cap and site.variant_key not in bucket:
                bucket.append(site.variant_key)
    return report
