"""ESSENTIALS — the offline authoring loop, present in every mode.

Scaffold, learn a table, lint rows, validate, compile, then check what you
shipped is what you meant (``module_signature``, ``verify_artifact``). Nothing
here touches the network and nothing here invents a value: every schema answer
is generated from the live pydantic models in ``just-dna-format``, so it cannot
drift from what the compiler accepts.

``authoring_reference`` lives here rather than behind the mode flag because the
guidelines tell an agent to call it — a rule pointing at a tool the default tier
does not have is a rule that gets ignored.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from typing import get_args, get_origin

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler, draft, hints, scaffold
from just_dna_format import layout, reference
from just_dna_format.integrity import IntegrityError, verify_manifest
from just_dna_format.manifest import read_manifest
from just_dna_format.spec import ModuleSpecConfig
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from just_module_creator import audit, authored_checks, logscan
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    AuditReport,
    ClosureResult,
    CompileReport,
    LintResult,
    LogFinding,
    LogReview,
    MachineTableDescription,
    ScaffoldResult,
    SignatureResult,
    SpecBlock,
    SpecFileDescription,
    StudyFact,
    StudyFacts,
    TableDescription,
    TableKind,
    TableList,
    TableRequirements,
    TemplateResult,
    ValidationReport,
    VerifyResult,
)
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import (
    jsonable,
    known_kind,
    resolve_dir,
    schema_versions,
    to_alterations,
    to_findings,
)

log = get_logger()

# What one row of each kind is *about*. The key half used to live here too, and does not
# any more.
#
# **The subject half is the one deliberate exception to "never hardcode a schema
# fact"**: it answers "which table?", a question the schema cannot answer because it
# is about intent rather than structure. Column lists, vocabularies and requirements
# all still come from the models.
#
# **The key half is GENERATED as of upstream 0.6.5** — our `S48`, their RM113.
# `hints.key_fields(csv)` returns a `TableKey`: the columns two rows collide on, the
# `rule` that decides what a collision even is, the columns the compiler stamps, and a
# fallback key for the one kind that has two levels. It answers for the machine-produced
# sidecars too, so `describe_machine_table` gets the same route, and it reads each
# model's own `_KEY_FIELDS` — the same source `draft.natural_key` reads, so the two
# cannot drift by construction rather than by agreement.
#
# The hand-kept tuple that stood here under RM10 is what the report was about: it named
# `modifier_cn` for all of 0.6, after upstream deprecated that column at 0.6.0. Its
# guard (`test_every_documented_key_column_is_a_live_undeprecated_field`) retires with
# it, subsumed by upstream's own.
_SUBJECTS: dict[str, str] = {
    "variants.csv": "one variant + one genotype",
    "studies.csv": (
        "one paper and what it says — about a variant, or about a threshold or the "
        "module itself, since 0.6 lets a study row name no variant at all"
    ),
    "haplotypes.csv": "which variants make up a named allele",
    "allele_function.csv": "what a named allele does",
    "diplotypes.csv": "a pair of alleles (in trans)",
    "pharm_variants.csv": "one variant + one drug",
    "activity_phenotype.csv": "a metabolizer activity-score range",
    "copynumbers.csv": "a copy-number range",
    "repeat_alleles.csv": "a repeat-count range",
    "heteroplasmy.csv": "an mtDNA heteroplasmy-fraction range",
    "pgs.csv": "a published polygenic score",
    # Draftable as of upstream 0.5.4: the one fact sidecar a human writes, and the
    # only table the compile licence gate reads. `licensing.csv` is its 0.6 spelling;
    # `sources.csv` is the deprecated one and inherits this entry rather than
    # repeating it, so the two can never describe themselves differently.
    "licensing.csv": "the terms one source's data came under",
}


def _subject_for(name: str) -> str:
    """What one row of this kind is about, following a deprecated spelling to its own.

    `draft.DRAFTABLE` lists both `sources.csv` and `licensing.csv` in 0.6 and backs
    them with one model, so answering "which table?" twice would be answering it
    twice differently the first time somebody edits one line. Which spelling is
    which is upstream's fact, read from `layout`, not restated here.
    """
    canonical = layout.preferred_spelling(name)
    return _SUBJECTS.get(canonical, _SUBJECTS.get(name, "(see describe_table)"))


def _key_for(name: str) -> tuple[str, str | None]:
    """What an append collides on, rendered, and the rule that decides a collision.

    Both halves come from `hints.key_fields`. `None` — a kind that declares no key —
    is passed through as "no declared key" rather than guessed at, and the rule is
    returned beside the columns because on a binning kind the columns are a GROUP key
    and equality is not the duplicate rule at all.
    """
    key = hints.key_fields(name)
    if key is None:
        return "(no declared key)", None
    columns = f"({', '.join(key.columns)})"
    if key.fallback:
        columns += f", or ({', '.join(key.fallback)}) on a row that has no {key.columns[0]}"
    return columns, key.rule


_COMPOSITION_NOTE = (
    "A module composes from optional table kinds: module_spec.yaml is the only "
    "always-present file — it is not a table and describe_spec_file answers it — "
    "and at least one recognised table must exist. "
    "studies.csv is required IFF variants.csv is present. A PGx/PRS/binning "
    "module carries only its own tables and no variants.csv — never add an empty "
    "table to keep another company. It may still carry studies.csv, and often "
    "should: since 0.6 a study row may name no variant, so it can ground a bin "
    "threshold or the module itself, and a binning table whose thresholds are "
    "grounded nowhere is reported at compile. Where a kind carries `preferred`, "
    "the two spellings are one table: write to whichever is already there, create "
    "only the preferred one, and never both — a module carrying both is refused, "
    "because two copies of a hand-editable fact table are two claims and picking "
    "one would discard somebody's curation silently."
)

# The machine-produced tables: the fact sidecars plus `resolution.csv`.
#
# **Derived from the compiler's own loader roster**, as of upstream 0.6.5 — our `S47`,
# their RM112. `hints.DERIVED_TABLE_MODELS` is `compiler._FACT_TABLES` published rather
# than restated, keyed on the filename and carrying the row model, and
# `hints.derived_model_for(csv)` is its lookup. So a fact table upstream adds arrives
# here with its model attached and needs no edit, which is what the hand-kept map this
# replaces could not do: it went stale as a four-item literal while 0.6 shipped three
# new fact tables, and the roster then had to be borrowed from a *third* package
# (`just_dna_registry.specfiles`) to grow by itself while the models stayed by hand.
# One source now, and it is the loader's.
#
# **The licensing carve-out is derived, not special-cased.** Upstream's map answers both
# spellings of the licence table with `SourceRow`, because the compiler fact-hashes it
# like any other sidecar. Here it is a table kind: it is in `draft.DRAFTABLE`, a human
# writes it, and it has a template and a linter — so subtracting the draftable kinds
# takes it out of this roster, and a table upstream makes hand-authorable moves across
# the same way without an edit.
_PRODUCED_MODELS: dict[str, type[BaseModel]] = {
    csv_name: model
    for csv_name, model in sorted(hints.DERIVED_TABLE_MODELS.items())
    if csv_name not in draft.DRAFTABLE
}

#: The same roster as names, for the surfaces that list it rather than describe it.
_PRODUCED_CSVS: tuple[str, ...] = tuple(_PRODUCED_MODELS)


#: `module_spec.yaml`, from the constant held by the code that creates it rather than
#: as a literal. The authored DSL has exactly one legal name in exactly one legal place
#: — upstream's `layout` docstring says so and that asymmetry is deliberate — so there
#: is no spelling question here of the kind `licensing.csv` has.
_SPEC_FILE = scaffold.MODULE_SPEC

_SPEC_REDIRECT = (
    f"{_SPEC_FILE} is the module's spec FILE, not a table kind: it is YAML, it holds nested "
    f"blocks rather than rows, and nothing about it has columns, a row key or a per-column "
    f"cross-check. Call describe_spec_file() for its top-level keys and every block it carries "
    f"— `weighting:`, `authorship:`, `module:` and the rest — generated from the same live "
    f"models as every other schema answer here. scaffold_module writes the file itself."
)


def _refuse_spec_file(csv_name: str) -> None:
    """Redirect the spec file to the route that answers it, before anything calls it unknown.

    The four authoring routes here take a *table kind*, and `module_spec.yaml` reaching one
    of them is a reader asking a reasonable question at the wrong door — the same situation
    as a machine-produced sidecar, which `_shared.known_kind` already redirects. Left to
    fall through, it arrived as *"Unknown table kind 'module_spec.yaml'"* followed by a list
    of CSV kinds: false, and it sent the reader to `authoring_reference`, which answers in
    164k characters and has to be grepped for three field names.
    """
    if csv_name.strip() == _SPEC_FILE:
        raise ToolError(_SPEC_REDIRECT)


def _spec_block_models(model: type[BaseModel]) -> dict[str, tuple[type[BaseModel], bool]]:
    """Which of a model's authored fields open a nested block, and whether the key repeats.

    Read off the live annotations, so a block upstream adds or removes moves here with it.
    `list[Contribution]` and `GenePanelSpec | None` both arrive as their inner model — the
    repetition is the part worth reporting, because a single mapping under `authorship:` is
    the wrong shape rather than a missing field.
    """
    found: dict[str, tuple[type[BaseModel], bool]] = {}
    for name in reference.authored_field_names(model):
        annotation = model.model_fields[name].annotation
        repeated = get_origin(annotation) is list
        for candidate in (annotation, *get_args(annotation)):
            if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                found[name] = (candidate, repeated)
    return found


def _spec_blocks(
    model: type[BaseModel],
    described: dict[str, object],
    prefix: str = "",
    seen: frozenset[type[BaseModel]] = frozenset(),
) -> list[SpecBlock]:
    """Every block reachable from `model`, depth-first, keyed by its dotted YAML path.

    Recursive although the spec is one level deep today: the walk is the same length
    either way, and a block that grows a sub-block would otherwise be reported as a field
    of an unknown type. `seen` guards a model that reaches itself.
    """
    blocks: list[SpecBlock] = []
    for key, (nested, repeated) in _spec_block_models(model).items():
        if nested in seen:
            continue
        fields = described.get(nested.__name__)
        if fields is None:
            # Refused rather than reported as a block with no fields: an empty field list
            # reads as "this block takes nothing", which is the opposite of the truth.
            raise ToolError(
                f"{prefix}{key} opens a {nested.__name__} block that "
                f"just_dna_format.reference.authoring_reference() does not describe, so its "
                f"fields cannot be generated. This is an upstream registration gap — report it "
                f"rather than writing the block from memory."
            )
        blocks.append(
            SpecBlock(
                key=f"{prefix}{key}",
                model=nested.__name__,
                repeated=repeated,
                category=reference.field_category(model, key),
                description=model.model_fields[key].description,
                fields=jsonable(fields),
            )
        )
        blocks.extend(
            _spec_blocks(nested, described, prefix=f"{prefix}{key}.", seen=seen | {nested})
        )
    return blocks


_MACHINE_REFUSAL = (
    "An enricher pass writes this file and the compiler fact-hashes it into the "
    "artifact. Read it — for several of these facts this sidecar is the only place they "
    "exist in the module. The hazard in writing here is ATTRIBUTION, not authorship: the "
    "passes MERGE into what is already there rather than overwriting, so a value you type "
    "survives every later run, and the compile checks these rows for type and coherence "
    "while no check asks where a value came from. An unmarked cell of yours is therefore "
    "indistinguishable from a fetched one and is hashed as though the source had said it. "
    "So if you do write here, MARK IT: `source` is that marker, and it is upstream's own "
    "vocabulary — resolution.csv documents `manual` for exactly this, and a row marked "
    "that way is one refresh_sidecar can recognise and protect. Writing an unmarked cell "
    "is what to avoid; re-running a pass will not remove one, because the merge keeps it. "
    "Prefer fixing the input where the input is what is wrong. licensing.csv is the one "
    "fact sidecar authored outright, and describe_table answers it."
)


def _machine_kind(name: str) -> str:
    """Normalize a machine-produced table name, redirecting anything that is not one."""
    csv_name = name.strip()
    if not csv_name.endswith(".csv"):
        csv_name = f"{csv_name}.csv"
    if csv_name in _PRODUCED_MODELS:
        return csv_name
    if csv_name in draft.DRAFTABLE:
        raise ToolError(
            f"{csv_name} is YOURS to author, not machine-produced — call "
            f"describe_table({csv_name!r}) instead. It answers the columns, the requirements and "
            "which cells you must reason out independently, none of which apply to a produced "
            "table."
        )
    raise ToolError(
        f"Unknown table {name!r}. Machine-produced tables: {', '.join(_PRODUCED_CSVS)}. "
        f"Authored kinds are on describe_table."
    )


def register_essentials(mcp: FastMCP, settings: Settings) -> None:
    """Register the always-on authoring tools, a resource, and a prompt."""

    # ----------------------------------------------------------------- #
    # Logs, read before the catalog keeps them forever (RM25)
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Review the logs before publishing", readOnlyHint=True, idempotentHint=True
        )
    )
    def review_logs(spec_dir: str) -> LogReview:
        """Show what is in this module's logs, because publishing them is permanent.

        `_collect_logs` runs on **every** compile with no flag and no opt-out: any
        `*.log` in a spec directory is copied into the artifact, hashed into the
        manifest and uploaded. A published version is immutable and `yank` delists
        without removing, so the first log nobody read stays in the catalog.

        That sweep is correct as designed — `logs/` exists to travel and to
        accumulate across versions. What was missing is anyone looking first.

        **It reports and never strips.** A log is a provenance record; editing one
        silently is the opposite of what it is for. A flagged log is often fine to
        publish, and that call is the author's.

        The question is deliberately narrow — *would the author be surprised to see
        this in the catalog?* — not "is this a secret". Real agent transcripts carry
        the full team system prompt, every model id and local upload paths; a
        hand-written run log carries none of that and comes back clean.
        """
        target = resolve_dir(spec_dir, settings)
        paths = logscan.logs_in(target)
        findings: list[LogFinding] = []
        total = 0
        for path in paths:
            total += path.stat().st_size
            findings.extend(
                LogFinding(
                    log=str(path.relative_to(target)),
                    kind=flag.kind,
                    line=flag.line,
                    detail=flag.detail,
                )
                for flag in logscan.scan_file(path)
            )
        return LogReview(
            spec_dir=str(target),
            logs=[str(p.relative_to(target)) for p in paths],
            total_bytes=total,
            findings=findings,
            note=(
                "No logs found — nothing would be swept into the artifact."
                if not paths
                else (
                    f"{len(paths)} log(s), {total} bytes, all of which travel to the catalog on "
                    f"publish. {len(findings)} finding(s). Nothing was changed and nothing is "
                    "refused: a flagged log may still be the right thing to publish, and an "
                    "unflagged one is not thereby approved — only a person can decide that."
                )
            ),
        )

    # ----------------------------------------------------------------- #
    # What the module already knows about its own studies (RM22)
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Study facts already in this module", readOnlyHint=True, idempotentHint=True
        )
    )
    def study_facts(spec_dir: str) -> StudyFacts:
        """Per-study facts the GWAS pass already wrote into this module's `gwas_effects.csv`.

        **Answers `population` without leaving the module.** `studies.csv`'s
        `population` is the studied cohort's ancestry, and when a GWAS pass has
        run with study facts on, the Catalog's own answer is already sitting in
        `gwas_effects.csv` under `ancestry` — joined by `pmid` or
        `study_accession`. Until this tool existed nothing surfaced it, and the
        measured consequence is a published module carrying
        `"Nagel M et al. — GWAS Catalog GCST006941"` in every `population` cell:
        a citation label written into a column that wanted an ancestry, by an
        author who had the ancestry in the next file over.

        **Surfaced, never written.** `population` is not redundancy-bearing, so
        filling it from here would make no check vacuous — that is not the
        reason. The reason is that a study carries several ancestries and
        `ancestry` is a joined string, so *which* of them belongs in a given row
        is a judgement. Take the value, or take part of it, or disagree with it.

        A null `ancestry` means the pass ran with `study_facts` off or the
        Catalog published none. It is not a statement that the cohort is unknown,
        and it is never a reason to put something else in the column.
        """
        target = resolve_dir(spec_dir, settings)
        path = target / "gwas_effects.csv"
        if not path.is_file():
            return StudyFacts(
                spec_dir=str(target),
                studies=[],
                with_ancestry=0,
                note=(
                    "No gwas_effects.csv in this module, so there is nothing to read. That is "
                    "not a defect: the file exists only after a GWAS pass has run. `population` "
                    "still wants the studied cohort's ancestry, from the paper itself."
                ),
            )

        # Keyed on the study rather than the association: `studies.csv` has one row
        # per (paper, variant) and the ancestry is a property of the study, so
        # collapsing here is what makes the answer usable at the grain it is wanted.
        seen: dict[tuple[str | None, str | None], dict] = {}
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (row.get("pmid") or None, row.get("study_accession") or None)
                entry = seen.setdefault(
                    key,
                    {
                        "pmid": key[0],
                        "study_accession": key[1],
                        "ancestry": row.get("ancestry") or None,
                        "trait": row.get("trait") or None,
                        "trait_efo_id": row.get("trait_efo_id") or None,
                        "rows": 0,
                    },
                )
                entry["rows"] += 1
                # First non-null wins per field rather than last: a later row that
                # happens to be blank must not erase an answer an earlier one gave.
                for field in ("ancestry", "trait", "trait_efo_id"):
                    if entry[field] is None and row.get(field):
                        entry[field] = row[field]

        studies = [
            StudyFact(**entry)
            # Deterministic, and never from dict iteration order.
            for _, entry in sorted(seen.items(), key=lambda kv: (kv[0][0] or "", kv[0][1] or ""))
        ]
        with_ancestry = sum(1 for s in studies if s.ancestry)
        return StudyFacts(
            spec_dir=str(target),
            studies=studies,
            with_ancestry=with_ancestry,
            note=(
                f"{len(studies)} distinct studies in gwas_effects.csv, {with_ancestry} carrying an "
                "ancestry. Join to studies.csv on pmid. These are the Catalog's answers, not "
                "verdicts: a study spanning several cohorts arrives as one joined string, and "
                "which part applies to a given row is yours to decide."
            ),
        )

    # ----------------------------------------------------------------- #
    # Schema discovery
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="List table kinds", readOnlyHint=True, idempotentHint=True
        )
    )
    def list_tables() -> TableList:
        """List the authorable table kinds and what each row is about.

        Start here when deciding which table a finding belongs in: the question is what
        the row's *subject* is, not what data you happen to have — a quantity with a
        threshold (repeat count, copy number, heteroplasmy fraction, activity score) is
        a binning table, not a variant row. `tables` is what you write; `sidecars` is
        what a pass writes for you, answered by `describe_machine_table`;
        `licensing.csv` sits under `tables` because it is the one fact sidecar a human
        authors; and `module_spec.yaml` is in neither, because it holds nested blocks
        rather than rows — `describe_spec_file` answers it.
        """
        tables = []
        for name in sorted(draft.DRAFTABLE):
            keyed_on, key_rule = _key_for(name)
            canonical = layout.preferred_spelling(name)
            tables.append(
                TableKind(
                    csv=name,
                    model=draft.DRAFTABLE[name].__name__,
                    subject=_subject_for(name),
                    keyed_on=keyed_on,
                    key_rule=key_rule,
                    companions=scaffold.companions_for([name]),
                    deprecated=layout.is_deprecated_spelling(name),
                    preferred=canonical if canonical != name else None,
                )
            )
        return TableList(
            tables=tables,
            sidecars=list(_PRODUCED_CSVS),
            note=_COMPOSITION_NOTE,
            produced_by=schema_versions(),
        )
    # Upstream glosses the somebody behind an attestation cell as a human, which is right for a
    # layer where nothing can record a reader. Here an agent reading a fetched article is a
    # reading that happened, so the rule is attribution rather than abstention — CLAUDE.md §2,
    # reversed 2026-08-20.

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Describe a table kind", readOnlyHint=True, idempotentHint=True
        )
    )
    def describe_table(csv_name: str) -> TableDescription:
        """Describe one table kind: every column, its type, vocabulary and pick-list.

        Generated from the live pydantic models, so it cannot drift from what the
        compiler accepts. Ask before writing any vocabulary cell — several are not what
        intuition suggests (`direction` is an axis: neutral/protective/risk/unknown,
        never increase/decrease). `redundancy_bearing` names the columns a later check
        compares against a source, so author those independently: filling one from the
        source that checks it makes the check vacuous. `attestation_bearing` is a subset
        and the stronger case — those cells assert that somebody read something, so
        quote what you located, verbatim, and record who located it, never the article's
        title (`fetch_fulltext`). Authored kinds only: a machine-produced sidecar goes
        to `describe_machine_table`, and `licensing.csv` is answered here.
        """
        _refuse_spec_file(csv_name)
        name = known_kind(csv_name, draft.DRAFTABLE, _PRODUCED_CSVS)
        described = hints.describe_table(name)
        # Both constants are global across kinds; narrow each to this table's
        # columns so an agent is not told to hand-author a column it has not got.
        present = {
            str(c["name"])
            for c in described.get("columns", [])
            if isinstance(c, dict) and c.get("name")
        }
        # A check is only as wide as the table it reads, and `REDUNDANCY_BEARING` is
        # keyed on a bare column name — so `clin_sig` on a binning kind used to be
        # answered with the reason `verify_clin_sig` gives, and that checker takes
        # `list[VariantRow]` and never sees the row. Right advice, false reason, and a
        # false reason implies a green run was an agreement. `REDUNDANCY_BEARING_TABLES`
        # (upstream 0.6.6, our `S59` / their RM123) scopes the EXPLANATION; an absent key
        # means unscoped, which is the honest answer for more columns than not. The
        # advice itself does not soften: nothing cross-examines the cell, so an
        # independently authored value is more load-bearing here, not less.
        scopes = getattr(hints, "REDUNDANCY_BEARING_TABLES", {})
        redundancy = {}
        for col, why in getattr(hints, "REDUNDANCY_BEARING", {}).items():
            if str(col) not in present:
                continue
            reads = scopes.get(col)
            note = str(why)
            if reads is not None and name not in reads:
                note = (
                    f"{note} — but that checker does not read {name}: it loads "
                    f"{', '.join(sorted(reads))} only. Nothing cross-examines this column here, "
                    "so an independent reading is the ONLY thing standing behind the cell."
                )
            redundancy[str(col)] = note
        attestation = sorted(
            str(col)
            for col in getattr(hints, "ATTESTATION_BEARING", frozenset())
            if str(col) in present
        )
        return TableDescription(
            csv=described.get("csv", name),
            model=str(described.get("model", "")),
            columns=jsonable(described.get("columns", [])),
            requirements=jsonable(described.get("requirements", {})),
            key=jsonable(described.get("key", {})),
            redundancy_bearing=redundancy,
            attestation_bearing=attestation,
            produced_by=schema_versions(),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Describe module_spec.yaml", readOnlyHint=True, idempotentHint=True
        )
    )
    def describe_spec_file() -> SpecFileDescription:
        """Describe `module_spec.yaml`: every top-level key and every block it carries.

        The one file a module always has, and the only one that is not a table — so
        `describe_table` cannot answer it and redirects here instead. Everything below is
        generated from the live model that validates the file, so the answer cannot drift
        from what the compiler accepts, and it arrives in ONE call: `weighting:` and its
        three fields, `authorship:` and what a contribution entry takes, `defaults:`,
        `module:` and which of its keys a registry stamps for you.

        Read `category`, and read it as YAML. A `defaulted` key here may be left out
        altogether and its default applies — a spec carrying nothing but `module:`
        validates — which is the opposite of the CSV rule about writing a default out
        rather than leaving a cell blank, because there are no cells in this file. On a
        block, `optional` plus required fields means write it completely or leave the key
        out: opening it commits you to what is under it.

        Two things this does not do. It writes nothing — `scaffold_module` creates the
        file, with a `<<REPLACE>>` in every cell you must settle. And it has no opinion on
        what belongs in a value: `weighting.scale` is free text on purpose, and what your
        weights mean is yours to state rather than ours to offer a pick-list for.
        """
        reference_doc = reference.authoring_reference()
        models = reference_doc["models"]
        root = ModuleSpecConfig.__name__
        blocks = _spec_blocks(ModuleSpecConfig, models)
        opens = {block.key: block.model for block in blocks}
        keys = []
        for field in jsonable(models[root]):
            # Copied rather than mutated: upstream's dict is its answer, and the pointer
            # into `blocks` is ours.
            entry = dict(field)
            entry["block"] = opens.get(str(entry.get("name")))
            keys.append(entry)
        return SpecFileDescription(
            file=_SPEC_FILE,
            model=root,
            keys=keys,
            blocks=blocks,
            registry_stamped=dict(reference_doc["registry_stamped_keys"]),
            note=(
                f"{_SPEC_FILE} is the module's identity and its authoring defaults, not data: "
                "no variant, no study and no threshold lives here. It is the only file a spec "
                "directory always has, and the compiler reads it before any table."
            ),
            produced_by=schema_versions(),
        )

    # Separate from `describe_table` structurally, not stylistically: that tool would
    # have had to answer `requirements`, `redundancy_bearing` and `attestation_bearing`
    # with empty values, and an empty `requirements` reads as *no requirements* rather
    # than *the question does not apply*. The `licensing.csv` carve-out is derived from
    # `draft.DRAFTABLE`, so a table upstream makes authorable moves on its own. Both are
    # pinned by `tests/test_authoring.py`, which is why neither is in the docstring: a
    # description is context every session pays for, and this is reasoning for whoever
    # edits the code.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Describe a machine-produced table", readOnlyHint=True, idempotentHint=True
        )
    )
    def describe_machine_table(csv_name: str) -> MachineTableDescription:
        """Describe a sidecar a PASS wrote: every column, type and vocabulary. Read-only.

        `resolution.csv` plus the fact sidecars — ask `list_tables().sidecars` for the
        live roster rather than trusting a list in prose, this one included. Generated
        from the models, so "ask the tool, never memory" holds for the files an author
        *reads* as well as the ones they write. A produced table has no template, no
        linter and no requirements: nothing here writes or lints one, the answer says
        `hand_authored: false`, and the authoring routes redirect here rather than call
        the name unknown. `licensing.csv` is the exception and stays on `describe_table`
        — it is the one fact sidecar a human writes. A row here is not evidence of
        anything you authored; read `refusal` before editing one of these files by hand.
        """
        name = _machine_kind(csv_name)
        model = _PRODUCED_MODELS[name]
        # Upstream's own assembled column list, not a second assembly of ours. Its
        # per-table `describe_table` covers authored kinds only, but the whole-schema
        # `authoring_reference()` describes every model including these — and the two
        # are generated side by side, so taking this one keeps the column dicts the
        # same shape rather than re-deriving type/category/vocabulary here and drifting.
        payload = reference.authoring_reference()
        columns = jsonable(payload.get("models", {}).get(model.__name__, []))
        notes = payload.get("vocabulary_notes", {})
        for column in columns:
            # Per-member prose, merged the way `hints.describe_table` merges it for an
            # authored kind. No produced model carries a noted vocabulary today; the
            # merge is here so one added upstream reaches this surface too, which is the
            # drift upstream's own D1-4 was.
            if isinstance(column, dict) and column.get("vocabulary") in notes:
                column["notes"] = jsonable(notes[column["vocabulary"]])
        # The merge key, from the same accessor `describe_table` renders for an authored
        # kind — it answers for the machine-produced tables too since 0.6.5 (`S51`), which
        # is the half that matters here: these files are merge-not-clobber, so the key is
        # what decides whether a re-run updates your row or appends beside it.
        key = hints.key_fields(name)
        return MachineTableDescription(
            csv=name,
            model=model.__name__,
            columns=columns,
            key=jsonable(asdict(key)) if key is not None else {},
            refusal=_MACHINE_REFUSAL,
            produced_by=schema_versions(),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Table requirements", readOnlyHint=True, idempotentHint=True
        )
    )
    def table_requirements(csv_name: str) -> TableRequirements:
        """The three shapes of requiredness for a table kind — read all three.

        A list of required fields alone is not enough. `defaulted` columns are
        the trap: not required, and yet an empty cell arrives as None rather than
        as the field's default and fails on type. Write the default out
        explicitly. `any_of` carries the identity rules (rsid OR chrom+start)
        that no per-field flag can express.
        """
        _refuse_spec_file(csv_name)
        name = known_kind(csv_name, draft.DRAFTABLE, _PRODUCED_CSVS)
        req = draft.authoring_requirements(name)
        return TableRequirements(
            csv=req.get("csv", name),
            always=list(req.get("always", [])),
            any_of=[list(g) for g in req.get("any_of", [])],
            defaulted=jsonable(req.get("defaulted", {})),
            optional=list(req.get("optional", [])),
            produced_by=schema_versions(),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Get a CSV template", readOnlyHint=True, idempotentHint=True
        )
    )
    def get_template(csv_name: str, stub: bool = False, rows: int = 1) -> TemplateResult:
        """Get a CSV template for a table kind: header only, or header plus stub rows.

        A stub row carries `<<REPLACE>>` in the cells a human must decide. That
        placeholder is rejected before type coercion by every loader — including
        enrich — so a half-filled table fails loudly on exactly the rows still to
        do, rather than compiling into a module that asserts nothing.
        """
        _refuse_spec_file(csv_name)
        name = known_kind(csv_name, draft.DRAFTABLE, _PRODUCED_CSVS)
        if rows < 1:
            raise ToolError("rows must be >= 1.")
        content = draft.stub_template(name, rows=rows) if stub else draft.blank_template(name)
        return TemplateResult(
            csv=name,
            content=content,
            stub=stub,
            note=(
                "Write CSVs with a CSV writer, never by splitting on commas — several "
                "conclusion values contain commas, and a column shift usually surfaces "
                "as a bizarre validation error three columns away."
                + (
                    " Every <<REPLACE>> must be replaced before any loader will read the file."
                    if stub
                    else ""
                )
            ),
            produced_by=schema_versions(),
        )

    # ----------------------------------------------------------------- #
    # Authoring
    # The 5-15 words is a norm rather than a validator: a length ceiling would refuse a merely
    # verbose spec, refuse it after the prose was written, and make six published modules
    # retroactively invalid. F58 / format-tree S63 — four of five reference specs end with the
    # byte-identical methodology sentence, so the field's one job was spent on the shared half.
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Scaffold a spec directory",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        )
    )
    def scaffold_module(
        spec_dir: str,
        name: str | None = None,
        kinds: list[str] | None = None,
        rows: int = 1,
        dry_run: bool = False,
    ) -> ScaffoldResult:
        """Create module_spec.yaml plus a stub CSV per table kind. Never overwrites.

        Re-runnable: run it again with a different `kinds` to add a table later, and
        anything already present is refused rather than clobbered — `dry_run=true` shows
        the plan first. `name` must be lowercase alphanumeric with underscores (`my-
        module` is rejected). Afterwards replace every `<<REPLACE>>` in
        module_spec.yaml; title, description and report_title are required and the
        placeholder blocks validation. Keep `description` to **one short sentence,
        roughly 5-15 words**: it becomes the catalog card's subtitle and is rendered
        whole. Say what this module distinguishes — methodology belongs in `weighting:`,
        `authorship:` and `README.md`.
        """
        target = resolve_dir(spec_dir, settings, must_exist=False)
        for kind in kinds or []:
            _refuse_spec_file(kind)
        requested = [known_kind(k, draft.DRAFTABLE, _PRODUCED_CSVS) for k in (kinds or [])]
        if rows < 1:
            raise ToolError("rows must be >= 1.")

        # Write to the file you read. Upstream's scaffold creates whatever spelling it
        # is handed, so asking for `sources.csv` on a fresh module would create the
        # deprecated one — a file that stops being read at format 1.0, in a module
        # being written today. `sidecar_write_path` answers with the copy that already
        # exists and the preferred spelling otherwise, which is the same rule the
        # enricher's passes follow, so the two cannot produce a second copy between them.
        renamed: list[str] = []
        resolved: list[str] = []
        for kind in requested:
            if layout.preferred_spelling(kind) == kind:
                resolved.append(kind)
                continue
            actual = layout.sidecar_write_path(target, kind).name
            if actual != kind:
                renamed.append(f"{kind} -> {actual}")
            resolved.append(actual)
        requested = resolved

        plan = scaffold.scaffold_module(
            target, kinds=requested, name=name, rows=rows, dry_run=dry_run
        )
        created = [str(p) for p in plan.created]
        refused = [f"{p}: {why}" for p, why in plan.refused]

        # `companions_for` applies the conditional half of the mapping upstream 0.6.5
        # made public (our `S49`, their RM114): `studies.csv` pulls `variants.csv` in
        # only when nothing else recognised was asked for, so scaffolding a binning
        # module beside its evidence no longer invites an empty `variants.csv` that
        # would compile strict-green while asserting nothing. `scaffold_module` uses the
        # same function, so this warning cannot contradict what the run did.
        missing_companion = [
            f"{c} is needed beside {', '.join(requested)}"
            for c in scaffold.companions_for(requested)
            if not (target / c).exists()
        ]
        spelling_notes = [
            f"created {swap} instead: that is the current spelling, and the one you asked for "
            f"is read but deprecated, and removed at format 1.0"
            for swap in renamed
        ]
        return ScaffoldResult(
            spec_dir=str(target),
            created=created,
            refused=refused,
            warnings=list(plan.warnings) + missing_companion + spelling_notes,
            written=plan.written,
            next_step=(
                "Replace every <<REPLACE>> in module_spec.yaml (title, description, "
                "report_title are required; keep description to one short sentence, "
                "roughly 5-15 words - it is the catalog card's subtitle, rendered "
                "whole, and methodology belongs in weighting:, authorship: and "
                "README.md instead), then author the CSV rows and lint them "
                "with lint_rows before validating."
            ),
        )
    # `alterations` here carries normalizations that were APPLIED and is usually empty on a
    # valid table; upstream's `inspect_rows` reports the left-to-you columns as findings
    # instead. The refusals with `applied=false` come from `lookup_variant` and
    # `lookup_citation`, the tools actually holding a value they could have written. Roughly six
    # in ten conclusion warnings are real, the rest comparative or quoted prose, which is why it
    # is not an error.

    @mcp.tool(
        annotations=ToolAnnotations(title="Lint CSV rows", readOnlyHint=True, idempotentHint=True)
    )
    def lint_rows(csv_name: str, csv_text: str) -> LintResult:
        """Lint CSV text against a table kind. Writes nothing, anywhere.

        Pass the rows as text, so use it *before* writing anything to disk, and read all
        three levels: `error` blocks a compile, `warning` does not (a `risk` state with
        a positive weight compiles happily), and `info` names the columns deliberately
        left to you — the redundancy-bearing ones, yours to author independently because
        filling one from the source that later checks it makes that check vacuous.
        **Read `source` on each finding**: `upstream` is the compiler's own, carried
        across field-for-field, while `just-module-creator` is one this layer computed
        and never blocks a compile whatever its level — on `variants.csv` those are two
        rules over `conclusion` (a warning where the prose names a genotype that is not
        the row's own, an info where genotypes that score differently share one
        sentence), and on `studies.csv` the repeated-quote shape.
        """
        _refuse_spec_file(csv_name)
        name = known_kind(csv_name, draft.DRAFTABLE, _PRODUCED_CSVS)
        report = hints.inspect_rows(name, csv_text)
        findings = to_findings(report.findings)
        # Ours, not upstream's, and each says so in `source`. Appended rather than
        # merged into upstream's order so the transported half stays untouched.
        findings += authored_checks.findings_for_csv_text(name, csv_text)
        return LintResult(
            csv=report.csv_name,
            rows_in=report.rows_in,
            errors=sum(1 for f in findings if f.level == "error"),
            warnings=sum(1 for f in findings if f.level == "warning"),
            findings=findings,
            alterations=to_alterations(report.alterations),
            normalized_csv="\n".join(report.csv_out),
        )

    # ----------------------------------------------------------------- #
    # Validate / compile
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(title="Validate a spec", readOnlyHint=True, idempotentHint=True)
    )
    async def validate_module(spec_dir: str, strict: bool = True) -> ValidationReport:
        """Pre-flight a spec directory. Writes nothing.

        Pass the SAME `strict` you intend to compile with — several checks are a ladder,
        a warning under best-effort and an error under strict, so a modeless pre-flight
        answers for the other compile; the default is strict because that is what the
        registry runs. `strict` means *reproducible*, not *correct*: it refuses when
        resolution left something it could not reproduce and has no opinion on whether
        your coordinates name the variant you meant, so read `warnings` even on a pass.
        A green answer says the module builds and nothing more — `audit_module` asks
        what somebody still has to decide, over the same files and without a network.
        """
        target = resolve_dir(spec_dir, settings)
        result = await run_sync(lambda: compiler.validate_spec(target, strict=strict))
        return ValidationReport(
            valid=result.valid,
            strict=strict,
            errors=list(result.errors),
            warnings=list(result.warnings),
            info=list(result.info),
            authored_findings=await run_sync(lambda: authored_checks.findings_for_spec_dir(target)),
            stats=jsonable(result.stats),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Audit a module offline", readOnlyHint=True, idempotentHint=True
        )
    )
    async def audit_module(spec_dir: str, fill: bool = True) -> AuditReport:
        """Ask what a curation pass would ask. Offline, reads only; writes nothing.

        **Every other gate here answers "will this build?".** `validate_module`,
        `compile_module`, `lint_rows`, `registry_check` and `registry_validate` all
        answer that question in different words, and they are right to pass a module
        that builds. Two unattended curation passes over eighteen real modules found
        every genuine defect by writing arithmetic over the CSVs instead, while every
        one of those tools returned green.

        The output is a **decision list**, not a findings dump. `decisions` is what
        somebody has to choose about; `clear` is what computed and found nothing;
        `not_computed` is what could not be computed and why, which is **not** a pass
        — the file it reads is missing, so nothing about that signal is established.

        What it asks today: whether `weighting:` says what the `weight` column means
        (in both directions — an empty weight column and a deliberately unweighted
        module are the same bytes); whether any recorded check ran over zero subjects
        or was skipped; whether a check counted disagreements and kept none of them;
        whether an `effect_size` is really the Z-statistic of its own p-value under a
        label saying otherwise; and whether rows asserting a clinical significance
        have any paper behind them. `fill` adds a per-column fill count for every
        authored table — data rather than a decision, and the cheapest way to see
        what is there to curate.

        **It reports and never repairs, and a signal is not a verdict on the work.**
        A module that raises one is out of date or undeclared, not broken; several of
        these have honest explanations and a run producing this shape retracted two
        of its own three findings. Nothing here moves whether the module compiles,
        and a clean audit is not evidence the module is right — it is evidence that
        five specific questions computable without a network came back quiet.
        """
        target = resolve_dir(spec_dir, settings)

        def read() -> AuditReport:
            decisions, clear, blocked = audit.run(target)
            return AuditReport(
                spec_dir=str(target),
                decisions=decisions,
                clear=clear,
                not_computed=blocked,
                fill=audit.column_fill(target) if fill else [],
                note=(
                    "Offline, over the authored files only. A quiet audit means these signals "
                    "found nothing, never that the module is correct — nothing here reads a "
                    "source, and anything that would is a check rather than an audit."
                ),
            )

        return await run_sync(read)
    # Re-drafting moves the digest too: the licence table re-stamps `fetched_at`, which is
    # inside it. A `risk` state with a positive weight is the other warning that compiles clean.

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Compile a module",
            readOnlyHint=False,
            idempotentHint=True,
            destructiveHint=False,
        )
    )
    async def compile_module(
        spec_dir: str,
        output_dir: str,
        strict: bool = True,
        ctx: Context | None = None,
    ) -> CompileReport:
        """Compile a spec directory into a parquet artifact plus manifest.json.

        Offline and deterministic: it consumes the `resolution.csv` that enrich produced
        and never fetches one. Recompiling an untouched spec reproduces every hash
        **under one compiler version** — upgrading the compiler moves `artifact_digest`
        on purpose and moves `content_signature` on nothing, so compare the second
        across versions. A green compile is not evidence the module is correct: read
        `warnings`, since a genotype whose alleles are not at its locus compiles cleanly
        under best-effort. Read `resolution_subjects` beside `fully_resolved` — over an
        empty list that flag is vacuously true, and all five counters are null on a
        pre-0.6 artifact, where **null never means zero**.
        """
        source = resolve_dir(spec_dir, settings)
        out = resolve_dir(output_dir, settings, must_exist=False)
        # Warned, not refused, and the difference is deliberate. `<spec>/build` is the
        # obvious place to put it and real modules here do exactly that, so refusing
        # would condemn working layouts. What it costs shows up two steps later and
        # nowhere near the cause: the compile copies `README.md` into `output_dir`, the
        # registry uploader walks the spec tree recursively, and `registry_check` then
        # answers `ambiguous_spec_layout — README.md arrives from more than one path`
        # with a 422. A benchmark run lost a confusing detour and a full restructure to
        # it, with nothing pointing back at this call (`F76`).
        layout_note: list[str] = []
        if out == source or source in out.parents:
            layout_note.append(
                f"{out.name!r} is inside the spec directory. The compile copies "
                "README.md into it, and a later registry call walks the spec tree and "
                "refuses two of them: 'ambiguous_spec_layout — README.md arrives from "
                "more than one path'. Nothing is wrong with the artifact; move the "
                "output beside the spec rather than under it before publishing."
            )
        if ctx:
            await ctx.info(f"Compiling {source.name} -> {out}")

        # resolve_with_ensembl stays True with no cache: despite the name it is
        # the master switch for ALL resolution, injected resolution.csv included.
        # Turning it off compiles every row with chrom=None and still succeeds.
        result = await run_sync(
            lambda: compiler.compile_module(
                source,
                out,
                resolve_with_ensembl=True,
                ensembl_cache=None,
                strict=strict,
            )
        )

        manifest = result.manifest
        comp = getattr(manifest, "compilation", None) if manifest else None
        artifact = getattr(manifest, "artifact", None) if manifest else None
        return CompileReport(
            success=result.success,
            output_dir=str(result.output_dir) if result.output_dir else None,
            errors=list(result.errors),
            # Ours first: it is about this call's arguments and is actionable now,
            # where the compiler's are about the module. Never merged into the
            # compiler's list — a warning of ours must be legible as ours.
            warnings=layout_note + list(result.warnings),
            stats=jsonable(result.stats),
            artifact_digest=getattr(artifact, "digest", None),
            content_signature=getattr(manifest, "content_signature", None),
            resolution_signature=getattr(comp, "resolution_signature", None),
            fully_resolved=getattr(comp, "fully_resolved", None),
            # RM44/S31/S33. `getattr(..., None)` is the honest default rather than a
            # convenience: on a pre-0.6 manifest these are genuinely absent, and each
            # has a meaningful zero, so coalescing to 0 would report a module with no
            # positional rows where nothing had counted them.
            resolution_subjects=getattr(comp, "resolution_subjects", None),
            positional_rows=getattr(comp, "positional_rows", None),
            positional_rows_placed=getattr(comp, "positional_rows_placed", None),
            expanded_keys=getattr(comp, "expanded_keys", None),
            expanded_rows=getattr(comp, "expanded_rows", None),
            files=[f.name for f in getattr(artifact, "files", []) or []],
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Close a module", readOnlyHint=False, idempotentHint=True
        )
    )
    async def close_module(
        spec_dir: str,
        closed_by: str | None = None,
    ) -> ClosureResult:
        """Declare this module's authoring phase finished, bound to its authored bytes.

        Authoring had no end, so every check that needed to know whether a stub
        was still a stub was guessing. This is the end. It writes a `closure`
        into the module's `verification.json` naming the hash of
        `module_spec.yaml` and the authored CSVs **as they stand right now**.
        Edit any of them afterwards and the hash moves, the compiler drops the
        closure, and the module is open again — which is the point, not a bug.

        **Nothing does this for you and nothing should.** `validate_module` stays
        read-only however cleanly it passes: a record stamped by whatever
        happened to run says only that something ran. Run this when the module is
        done, not to clear the warning a compile prints — an unclosed module is a
        true statement about a module still being written.

        It does **not** refuse on warnings. An unresolved rsID or an ungrounded
        threshold is a legitimate thing to call finished; only a spec that will
        not validate is refused.

        `closed_by` is legibility, never proof — it is a string nobody checks.
        Signing a closure needs a private key, which this server deliberately
        does not take: a key that reaches a tool argument has been logged.
        Use `just-dna-compiler close <spec-dir> --private-key …` for that.
        """
        target = resolve_dir(spec_dir, settings)
        result = await run_sync(
            lambda: compiler.close_module(target, closed_by=closed_by or None)
        )
        return ClosureResult(
            closed=result.closed,
            spec_dir=str(target),
            path=str(result.path) if result.path else None,
            module_hash=result.module_hash,
            signed=result.signed,
            dropped_checks=list(result.dropped_checks),
            errors=list(result.errors),
            warnings=list(result.warnings),
        )

    # ----------------------------------------------------------------- #
    # Full schema dump
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Authoring reference", readOnlyHint=True, idempotentHint=True
        ),
    )
    def authoring_reference(schemas: bool = False) -> str:
        """The complete generated description of the authoring DSL, as JSON.

        Every model, column, vocabulary and one-of rule at once, generated from
        the live pydantic models. Large — prefer `describe_table` for one table.
        Pass `schemas=true` for raw JSON Schema instead of the summary form.
        """
        payload = reference.json_schemas() if schemas else reference.authoring_reference()
        # A dict rather than a model here, because ~30 dossiers document the access
        # path `authoring_reference()["models"][...]` and a wrapper would break every
        # one. Shallow-copied rather than mutated: the payload is upstream's to own.
        # `produced_by` cannot collide in either form — the summary form's keys are
        # fixed and the `schemas=True` form's are CamelCase model names.
        stamped = {**payload, "produced_by": schema_versions().model_dump()}
        return json.dumps(stamped, indent=2, default=str)

    # ----------------------------------------------------------------- #
    # Integrity — did the content change, and is the artifact intact
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Content signature", readOnlyHint=True, idempotentHint=True
        ),
    )
    async def module_signature(spec_dir: str) -> SignatureResult:
        """The content signature of the raw authored data. No compile, no network.

        Use it to tell whether two specs are the same content, and to check a
        `reverse` round-trip. It folds module_spec.yaml's `defaults:` into each
        row before hashing, so a value written once under `defaults:` and the
        same value repeated on every row are one content.
        """
        target = resolve_dir(spec_dir, settings)
        sig = await run_sync(lambda: compiler.content_signature(target))
        return SignatureResult(
            spec_dir=str(target),
            content_signature=sig,
            note=(
                "Covers the authored content only — not the compiled artifact. "
                "artifact.digest is a different hash: it moves whenever licensing.csv "
                "re-stamps fetched_at, AND on a compiler upgrade, so a digest change is "
                "not evidence that content changed. This signature is the one that holds "
                "across both."
            ),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Verify an artifact", readOnlyHint=True, idempotentHint=True
        ),
    )
    async def verify_artifact(
        module_dir: str, public_key: str | None = None, require_marketplace: bool = False
    ) -> VerifyResult:
        """Re-hash every file in a compiled artifact and recompute the digest.

        Without `public_key` the signature is NOT checked — `signature_checked`
        says so, and an unchecked signature is not a valid one.
        """
        target = resolve_dir(module_dir, settings)
        manifest_path = target / "manifest.json"
        if not manifest_path.is_file():
            raise ToolError(f"No manifest.json in {target}.")

        manifest = await run_sync(lambda: read_manifest(manifest_path))
        identity = getattr(manifest, "identity", None)
        artifact = getattr(manifest, "artifact", None)

        try:
            await run_sync(
                lambda: verify_manifest(
                    target,
                    manifest,
                    require_marketplace=require_marketplace,
                    public_key=public_key,
                )
            )
        except IntegrityError as exc:
            return VerifyResult(
                verified=False,
                module_dir=str(target),
                artifact_digest=getattr(artifact, "digest", None),
                canonical_id=getattr(identity, "canonical_id", None),
                signature_checked=public_key is not None,
                message=str(exc),
            )
        return VerifyResult(
            verified=True,
            module_dir=str(target),
            artifact_digest=getattr(artifact, "digest", None),
            canonical_id=getattr(identity, "canonical_id", None),
            signature_checked=public_key is not None,
            message=(
                "Every file re-hashed and the digest recomputed."
                if public_key
                else "Digests verified. The SIGNATURE was not checked — pass "
                "public_key to check it."
            ),
        )

    # ----------------------------------------------------------------- #
    # Resource + prompt
    # ----------------------------------------------------------------- #
    @mcp.resource("resource://just-dna/tables")
    def tables_resource() -> str:
        """The table kinds and the composition rule, as markdown."""
        lines = [
            "# just-dna table kinds",
            "",
            _COMPOSITION_NOTE,
            "",
            "| CSV | Row subject | Keyed on | Collides by |",
            "|---|---|---|---|",
        ]
        for name in sorted(draft.DRAFTABLE):
            # `_subject_for`, not a bare `.get`: a deprecated spelling follows the
            # canonical one to its entry, so `sources.csv` describes itself rather than
            # rendering two em-dashes in a table an author is reading to choose a kind.
            key, rule = _key_for(name)
            lines.append(f"| `{name}` | {_subject_for(name)} | `{key}` | {rule or "—"} |")
        lines += [
            "",
            "Machine-produced sidecars (read them, never hand-finish them): "
            + ", ".join(f"`{name}`" for name in _PRODUCED_CSVS)
            + ". `describe_machine_table` answers the columns of any of them. That list is "
            "derived from the installed toolchain rather than written here, so it grows when "
            "upstream adds a fact table. `licensing.csv` is a table kind of its own, listed "
            "above: it is the one fact sidecar you write by hand, and the only table the "
            "compile licence gate reads. It was called `sources.csv` before 0.6; both "
            "spellings read, only the new one is created, and a module carrying both is "
            "refused rather than merged.",
            "",
            f"Generated by just-dna-format {schema_versions().format_version} and "
            f"just-dna-compiler {schema_versions().compiler_version}. Compare those against "
            "what you installed: an older pair means a stale process is serving this.",
        ]
        return "\n".join(lines)

    @mcp.prompt
    def create_module(topic: str = "a trait or gene of interest") -> str:
        """Prompt template: author a new just-dna module end to end."""
        return (
            f"Author a just-dna annotation module about {topic}.\n\n"
            "Work in this order and do not skip ahead:\n"
            "1. Decide the table kind from the row's subject (`list_tables`), and "
            "check the registry for an existing module first (`registry_search`).\n"
            "2. `scaffold_module`, then replace every <<REPLACE>> in module_spec.yaml.\n"
            "3. Author rows. Prefer the rsID alone and let enrichment find the "
            "coordinate — an rsid-only row cannot carry a coordinate mistake. If you "
            "must author a coordinate, `start` is the 1-based VCF position: paste it, "
            "never subtract one.\n"
            "4. `lint_rows` on the text before writing it; act on the refusals yourself.\n"
            "5. `validate_module(strict=true)`, then `enrich_module` "
            "for coordinates and the ref check, then `compile_module(strict=true)`.\n"
            "6. Read the warnings on every green run.\n\n"
            "Never invent a PMID, never fill a cell from the source that checks it, "
            "and drop a row you cannot justify rather than picking a value to make "
            "the compile pass."
        )
