"""The offline arithmetic a curation pass had to write by hand — `RM26`.

Two independent unattended runs curated eighteen real modules between them, and
**every real defect either found was found by writing Python over the CSVs** while
five tools answered *"will this build?"* in different words. `F60` and `F61` carry
the measurements. The offline gate is right to pass those modules and says so
itself — *strict means reproducible, not correct* — so this is not a broken check.
It is that the entry point to a curation pass told you nothing.

**Every signal here is computable offline from files the plugin already reads.**
That is the boundary as much as the enabling condition: anything needing a live
source is a *check* and belongs beside `check_identifiers`, not here.

Three properties are load-bearing.

* **It reports and never repairs.** Several of these have honest explanations, and
  a run that produced this shape retracted two of its own three findings. A
  disagreement is not a defect report.
* **The output is a decision list.** If a human must choose, it goes in
  `decisions`; if nothing must be chosen, it does not. An old module is out of
  date, not defective — never *broken*, never *invalid*.
* **A signal that could not be computed says so, in its own list.** Collapsing
  "nothing to decide" and "the file this reads is not here" is the exact shape
  `F61` documents: a question that could not be put, presented as nothing to
  answer.

**Column names are the one thing here that is not generated**, because the audit
asks a question of specific cells and no schema can say which cells a question is
about. Which *tables* carry each column is generated, from `draft.DRAFTABLE`, and
`tests/test_audit.py::test_every_column_the_audit_reads_is_a_live_field` fails if
a name stops resolving — the `keyed_on` pattern, and the reason it exists.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from statistics import NormalDist
from typing import Any

import yaml
from just_dna_compiler import draft
from just_dna_enricher.verification import read_verification

from just_module_creator.models import AuditSignal, ColumnFill

SPEC_YAML = "module_spec.yaml"
VERIFICATION_JSON = "verification.json"
STUDIES = "studies.csv"
VARIANTS = "variants.csv"

#: Every column this module reads by name. Not generated and it cannot be: a schema
#: says what columns exist, never which one a question is about. The guard is a test
#: that resolves each against the live models rather than a comment promising it was
#: checked once.
COLUMNS_READ = frozenset(
    {"weight", "conclusion", "clin_sig", "effect_size", "effect_measure", "p_value", "p_value_num"}
)

#: How many names a headline lists before it stops listing them.
_EXAMPLES = 5

#: `|effect_size|` counts as "this is the Z of its own p-value" within this much of
#: `-Φ⁻¹(p/2)`. Relative, with a floor, because Z runs from about 2 to about 40 and a
#: fixed window is either useless at the top or credulous at the bottom.
_Z_RELATIVE = 0.01
_Z_FLOOR = 0.01

#: One row whose effect size happens to equal the Z of its own p-value is a
#: coincidence. The measured case was 242 of them. Below this the module is left
#: alone: a decision list that reports coincidences stops being read.
_Z_MIN_ROWS = 2

#: Spellings of `effect_measure` that already say Z, so a match is the label agreeing
#: with the number rather than contradicting it. `effect_measure` is documented as an
#: open set, so this cannot be generated and is matched loosely on purpose.
_Z_MEASURES = frozenset({"z", "zscore", "z-score", "z_score", "z score", "z-statistic", "zstat"})

_NORMAL = NormalDist()


# --------------------------------------------------------------------------- #
# Reading, and saying which read failed
# --------------------------------------------------------------------------- #
def tables_with(column: str) -> tuple[str, ...]:
    """Every authored table whose model carries this column, from upstream's roster.

    Generated rather than listed: `pharm_variants.csv` grew a `conclusion` and
    `pgs.csv` did not, and a hand-kept answer to that is a hand-kept schema fact.
    """
    return tuple(sorted(n for n, m in draft.DRAFTABLE.items() if column in m.model_fields))


def read_rows(path: Path) -> list[dict[str, str | None]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_spec(spec_dir: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    """`module_spec.yaml` as a plain mapping, or the reason it could not be read.

    Parsed here rather than through upstream's loader because
    `compiler._load_yaml` is private and nothing public returns a
    `ModuleSpecConfig` — asked for as format-tree `S74`, tracked here as `F67`. So
    this reads the two or three top-level keys it needs and folds no defaults,
    which is the honest limit
    rather than a shortcut: anything requiring the validated shape belongs in
    `validate_module`, which has it.
    """
    path = spec_dir / SPEC_YAML
    if not path.is_file():
        return None, f"there is no {SPEC_YAML} here, so nothing declares anything about the module"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, f"{SPEC_YAML} did not parse as YAML ({exc.__class__.__name__}); validate first"
    if not isinstance(doc, Mapping):
        return None, f"{SPEC_YAML} is not a mapping, so it declares no blocks to read"
    return doc, None


def _filled(rows: Sequence[Mapping[str, str | None]], column: str) -> int:
    return sum(1 for row in rows if (row.get(column) or "").strip())


def _listed(names: Iterable[str]) -> str:
    ordered = sorted(set(names))
    head = ", ".join(ordered[:_EXAMPLES])
    return head + (f", and {len(ordered) - _EXAMPLES} more" if len(ordered) > _EXAMPLES else "")


def _decide(name: str, headline: str, detail: Sequence[str] = ()) -> AuditSignal:
    return AuditSignal(name=name, state="decide", headline=headline, detail=list(detail))


def _clear(name: str, headline: str) -> AuditSignal:
    return AuditSignal(name=name, state="clear", headline=headline)


def _blocked(name: str, why: str) -> AuditSignal:
    return AuditSignal(
        name=name,
        state="not_computed",
        headline="this signal could not be computed, which is not the same as nothing to decide",
        why_not=why,
    )


# --------------------------------------------------------------------------- #
# The signals
# --------------------------------------------------------------------------- #
def weight_scale(spec_dir: Path) -> AuditSignal:
    """`weight` is filled, or deliberately empty, and `weighting:` says which.

    **Both directions are the same defect and both were measured.** One run found
    modules carrying weights on every row with no `weighting:` block anywhere; the
    other found a 190-row module with an **empty** `weight` on every row, no
    `weighting:`, passing strict and compiling green with `weights_rows: 190`.
    Nothing distinguishes "this author deliberately authors none" from "this author
    forgot", and that distinction is the entire reason the block exists — `weight`
    is the one magnitude in the format with no unit beside it.
    """
    name = "weight_scale"
    doc, why = read_spec(spec_dir)
    if doc is None:
        return _blocked(name, why or "")
    carried = tables_with("weight")
    present = [t for t in carried if (spec_dir / t).is_file()]
    if not present:
        return _blocked(
            name,
            f"no table that can carry a weight is here (looked for {', '.join(carried)}), so "
            "there is no scale to declare",
        )
    weighting = doc.get("weighting")
    declared = isinstance(weighting, Mapping) and any(
        str(weighting.get(key) or "").strip() for key in ("scale", "method", "note")
    )
    loaded = {t: read_rows(spec_dir / t) for t in present}
    counts = {t: (_filled(rows, "weight"), len(rows)) for t, rows in loaded.items()}
    filled = sum(f for f, _ in counts.values())
    total = sum(r for _, r in counts.values())
    if declared:
        return _clear(name, "`weighting:` declares what this module's weight column means")
    if filled:
        return _decide(
            name,
            f"{filled} of {total} row(s) carry a weight and nothing says what the scale is",
            [f"{t}: {f} of {r} rows carry a weight" for t, (f, r) in sorted(counts.items())],
        )
    if total:
        return _decide(
            name,
            f"no weight is authored on any of {total} row(s), and nothing says whether that "
            "was deliberate",
            [
                "an empty column and a deliberately unweighted module are the same bytes; "
                "`weighting:` is where the difference is recorded",
            ],
        )
    return _blocked(name, "the weight-bearing table(s) here carry no rows")


def checks_that_never_ran(spec_dir: Path) -> AuditSignal:
    """Records in `verification.json` that did not actually compare anything.

    Three states read very differently and only one of them says so out loud: a
    record with `skipped` set announces itself, a record that ran over **zero
    subjects** looks exactly like a clean one, and a check with no record at all is
    invisible from here.

    **That third one is a limit and is stated rather than papered over.** There is
    no public roster of which checks a module should have, and inventing one would
    be a hardcoded schema fact of the worst kind — a list that goes stale the next
    time upstream adds a check. So this reports on the records that are present, and
    the absence of the whole file is its own decision.
    """
    name = "checks_that_never_ran"
    path = spec_dir / VERIFICATION_JSON
    if not path.is_file():
        return _decide(
            name,
            "no check has ever been recorded against this module",
            [
                f"there is no {VERIFICATION_JSON}, so nothing here attests that any identifier, "
                "coordinate or reference-base comparison was ever put. A consumer holding the "
                "artifact cannot tell 'asked and clean' from 'never asked'.",
            ],
        )
    try:
        doc = read_verification(path)
    except (ValueError, OSError) as exc:
        return _blocked(name, f"{VERIFICATION_JSON} could not be read: {exc}")
    records = list(doc.records)
    if not records:
        return _decide(name, f"{VERIFICATION_JSON} carries no records at all")
    skipped = [r for r in records if r.skipped]
    empty = [r for r in records if not r.skipped and not r.subjects]
    if not skipped and not empty:
        return _clear(
            name,
            f"every one of {len(records)} recorded check ran over at least one subject",
        )
    # The silent ones first, and the ordering is the point: a record carrying
    # `skipped` announces itself and a reader can dismiss it in a glance, while
    # `subjects: 0` with no reason is indistinguishable from a clean pass. Both are
    # not-a-pass; only one of them says so.
    detail = [
        f"{r.check}: ran over 0 subjects and gives no reason, so it reads exactly like a clean "
        "check and established nothing"
        for r in sorted(empty, key=lambda r: r.check)
    ]
    # Upstream's own reason string, verbatim. Never matched against a list of ours:
    # the skip vocabulary is theirs and a copy of it here would go stale the next
    # time they add one — the reader routes on the word, which is why it is quoted
    # rather than classified.
    detail += [
        f"{r.check}: did not run — {r.skipped}"
        + (f" ({r.detail})" if (r.detail or "").strip() else "")
        for r in sorted(skipped, key=lambda r: r.check)
    ]
    detail.append(
        "a check with no record at all is invisible here: there is no published roster of what "
        "should have run, so this reads the records present and nothing else."
    )
    stated = f", {len(skipped)} saying why" if skipped else ""
    silent = f"{len(empty)} of them silently" if empty else "none of them silently"
    return _decide(
        name,
        f"{len(skipped) + len(empty)} of {len(records)} recorded check(s) compared nothing — "
        f"{silent}{stated}",
        detail,
    )


def findings_without_detail(spec_dir: Path) -> AuditSignal:
    """A record that counted disagreements and kept none of them.

    Measured at 52 unresolved ClinVar disagreements across two modules, with
    `detail: null` and no sidecar naming the rows — so the module publishes the
    number and nobody can ever find out which rows it counted. **The retention is
    upstream's** and is filed as format-tree `S70`; the rollup is ours, because
    this is the surface somebody reads before deciding whether the module is done.
    """
    name = "findings_without_detail"
    path = spec_dir / VERIFICATION_JSON
    if not path.is_file():
        return _blocked(name, f"there is no {VERIFICATION_JSON} to read counts out of")
    try:
        doc = read_verification(path)
    except (ValueError, OSError) as exc:
        return _blocked(name, f"{VERIFICATION_JSON} could not be read: {exc}")
    mute = [r for r in doc.records if r.findings and not (r.detail or "").strip()]
    if not mute:
        counted = sum(r.findings for r in doc.records)
        return _clear(
            name,
            f"every recorded check that counted a finding also kept one ({counted} counted)",
        )
    return _decide(
        name,
        f"{sum(r.findings for r in mute)} recorded finding(s) across "
        f"{len(mute)} check(s) name no row",
        [
            f"{r.check}: {r.findings} finding(s), detail null"
            for r in sorted(mute, key=lambda r: r.check)
        ]
        + [
            "re-run the check that produced them and read its report, which does name rows; "
            "the record itself cannot be made to say more from here."
        ],
    )


def _z_for(p_value: float) -> float | None:
    """`-Φ⁻¹(p/2)`, the two-sided Z of a p-value. `None` outside (0, 1]."""
    if not 0 < p_value <= 1:
        return None
    return -_NORMAL.inv_cdf(p_value / 2)


def _p_of(row: Mapping[str, str | None]) -> float | None:
    for column in ("p_value_num", "p_value"):
        raw = (row.get(column) or "").strip()
        if raw:
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def effect_size_is_its_own_z(spec_dir: Path) -> AuditSignal:
    """`effect_size` labelled as something it is not, caught by arithmetic.

    A "beta" of 7.29 on an item-level irritability score is not a possible effect
    size; it is the Z-statistic for that row's own p-value, to three decimals. One
    module then held Z-statistics beside genuine per-allele betas of order 0.02
    under one unit label, which makes every downstream comparison of that column
    meaningless. Measured at 242 variants across four published modules.

    Two authored columns and a normal quantile — nothing external, which is what
    makes it belong here rather than in a check.
    """
    name = "effect_size_is_its_own_z"
    path = spec_dir / STUDIES
    rows = read_rows(path)
    if not rows:
        return _blocked(
            name,
            f"no {STUDIES} with rows: the p-value and the effect size have to sit on one row for "
            "this arithmetic, and that table is where they do",
        )
    comparable = 0
    matched: list[tuple[str, str, float, float]] = []
    for row in rows:
        p_value, raw = _p_of(row), (row.get("effect_size") or "").strip()
        if p_value is None or not raw:
            continue
        try:
            size = abs(float(raw))
        except ValueError:
            continue
        z_value = _z_for(p_value)
        if z_value is None:
            continue
        comparable += 1
        measure = (row.get("effect_measure") or "").strip()
        if measure.lower() in _Z_MEASURES:
            continue
        if abs(size - z_value) <= max(_Z_RELATIVE * z_value, _Z_FLOOR):
            matched.append(((row.get("rsid") or "?").strip(), measure or "(blank)", size, z_value))
    if not comparable:
        return _blocked(
            name,
            f"no row in {STUDIES} carries both a usable p-value and an effect size",
        )
    if len(matched) < _Z_MIN_ROWS:
        return _clear(
            name,
            f"no effect size in {comparable} comparable row(s) is the Z of its own p-value"
            + (
                f" ({len(matched)} single row does, which is a coincidence at this scale)"
                if matched
                else ""
            ),
        )
    return _decide(
        name,
        f"{len(matched)} of {comparable} comparable row(s) carry an effect size equal to the Z "
        "of that row's own p-value, under a label that says otherwise",
        [
            f"{rsid}: {size:.4g} labelled {measure}, Z of its p-value is {z:.4g}"
            for rsid, measure, size, z in matched[:_EXAMPLES]
        ]
        + (
            [f"and {len(matched) - _EXAMPLES} more row(s)"] if len(matched) > _EXAMPLES else []
        )
        + [
            "if these are Z-statistics, `effect_measure` should say so — and check whether the "
            "same column also holds genuine effect sizes under that one label, which is what "
            "makes the column uncomparable rather than merely mislabelled."
        ],
    )


def clinical_claims_without_studies(spec_dir: Path) -> AuditSignal:
    """Rows asserting clinical significance with no paper anywhere behind them.

    The rule existed in `module-status` and was scoped to `variants.csv`, so a
    1,482-row PGx module fell outside it and nothing fired — which is §8's first
    prose trap exactly: a check is only as wide as the table it reads. Which tables
    can carry a clinical call is generated here, so a new one is in scope the day
    upstream adds it.
    """
    name = "clinical_claims_without_studies"
    bearing = tables_with("clin_sig")
    counts = {
        table: _filled(read_rows(spec_dir / table), "clin_sig")
        for table in bearing
        if (spec_dir / table).is_file()
    }
    claimed = {table: n for table, n in counts.items() if n}
    if not counts:
        return _blocked(
            name,
            f"none of the tables that can carry a clinical call are here ({', '.join(bearing)})",
        )
    if not claimed:
        return _clear(name, "no row in this module asserts a clinical significance")
    if (spec_dir / STUDIES).is_file() and read_rows(spec_dir / STUDIES):
        return _clear(
            name,
            f"{sum(claimed.values())} clinical call(s) sit beside a {STUDIES} with rows",
        )
    return _decide(
        name,
        f"{sum(claimed.values())} row(s) assert a clinical significance and no {STUDIES} carries "
        "a paper behind them",
        [f"{table}: {n} row(s) with clin_sig filled" for table, n in sorted(claimed.items())]
        + [
            "the module may be right and simply uncited, which is a decision to state rather "
            "than a defect to repair — but a reader has no way to check any of it."
        ],
    )


def column_fill(spec_dir: Path) -> list[ColumnFill]:
    """How full every column of every authored table is. Data, not a decision.

    The cheapest thing in this module and the one most asked for: it turns "what is
    there to curate" from a question into a table. Five of six curated modules had
    `category` empty on every row, reported as `categories: []` and read as
    unremarkable.

    Deliberately **not** a signal. Nobody has to decide anything about a fill count;
    a person reading one decides something, which is a different act and belongs to
    them.
    """
    out: list[ColumnFill] = []
    for table in sorted(draft.DRAFTABLE):
        path = spec_dir / table
        if not path.is_file():
            continue
        rows = read_rows(path)
        if not rows:
            continue
        columns = [c for c in rows[0] if c]
        for column in columns:
            out.append(
                ColumnFill(csv=table, column=column, rows=len(rows), filled=_filled(rows, column))
            )
    return out


#: Every signal, in the order a reader should meet them. A list rather than a
#: registry: adding one is adding a line here, and nothing dispatches by name.
SIGNALS = (
    weight_scale,
    checks_that_never_ran,
    findings_without_detail,
    effect_size_is_its_own_z,
    clinical_claims_without_studies,
)


def run(spec_dir: Path) -> tuple[list[AuditSignal], list[AuditSignal], list[AuditSignal]]:
    """Every signal, split into decide / clear / could-not-compute."""
    computed = [signal(spec_dir) for signal in SIGNALS]
    return (
        [s for s in computed if s.state == "decide"],
        [s for s in computed if s.state == "clear"],
        [s for s in computed if s.state == "not_computed"],
    )
