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

import json

from anyio.to_thread import run_sync
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler, draft, hints, scaffold
from just_dna_format import layout, reference
from just_dna_format.assertions import ClinicalAssertionRow
from just_dna_format.frequency import FrequencyRow
from just_dna_format.gene_metrics import GeneMetricsRow
from just_dna_format.gene_validity import GeneValidityRow
from just_dna_format.gwas import GwasEffectRow
from just_dna_format.integrity import IntegrityError, verify_manifest
from just_dna_format.literature import LiteratureRow
from just_dna_format.manifest import read_manifest
from just_dna_format.resolution import ResolutionRow
from just_dna_registry import specfiles
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    ClosureResult,
    CompileReport,
    LintResult,
    MachineTableDescription,
    ScaffoldResult,
    SignatureResult,
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

# What one row of each kind is *about*, and what makes two rows the same row.
#
# **The subject half is the one deliberate exception to "never hardcode a schema
# fact"**: it answers "which table?", a question the schema cannot answer because it
# is about intent rather than structure. Column lists, vocabularies and requirements
# all still come from the models.
#
# **The key half is structure, and it is here under protest** (RM10, upstream `S48`).
# A key is derivable in principle and nothing public derives it: `draft.natural_key`
# is row-level — it takes an instance and returns key *values*, never the column names
# — and the two registries that hold the names, `compiler._TABLE_DUPE_KEYS` and
# `MeasureBinRow._KEY_FIELDS`, are both private, one of them as lambdas. §2 forbids
# reaching into either. Removing the key from the answer was the alternative and it is
# worse: "what will an append collide on" is the question an author asks before a
# second pass, and answering it nowhere sends them to memory, which is what this whole
# surface exists to stop.
#
# So it stays, with the drift closed by a test instead of by hope: every token below is
# an exact field name on the kind's model, and
# `tests/test_authoring.py::test_every_documented_key_column_is_a_live_undeprecated_field`
# resolves each one against `model_fields` and fails if any is missing or carries
# DEPRECATED in its own description. That guard is what `modifier_cn` needed — it was
# deprecated in favour of `modifier_copy_number` when 0.6 landed and this map went on
# naming it, so an author was told to key on a column upstream removes at 1.0. Three
# more entries were loose prose (`variant`, `a`/`b`/`trait`, `trait`) and are now the
# real column names, because a token that does not resolve cannot be checked.
#
# On the four binning kinds the tuple is the bin GROUP key rather than a uniqueness
# key: upstream declines to give those an equality key at all (`natural_key` returns
# None for them on purpose), because two bins conflict by overlapping ranges within a
# group, not by being equal. `TableKind.keyed_on` says so.
_SUBJECTS: dict[str, tuple[str, str]] = {
    "variants.csv": ("one variant + one genotype", "(variant_key, genotype)"),
    "studies.csv": (
        "one paper and what it says — about a variant, or about a threshold or the "
        "module itself, since 0.6 lets a study row name no variant at all",
        "(variant_key, pmid)",
    ),
    "haplotypes.csv": (
        "which variants make up a named allele",
        "(haplotype_name, variant_key, allele)",
    ),
    "allele_function.csv": ("what a named allele does", "(gene, allele)"),
    "diplotypes.csv": (
        "a pair of alleles (in trans)",
        "(gene, haplotype_a, haplotype_b, trait_efo_id, drug, clinical_context)",
    ),
    "pharm_variants.csv": (
        "one variant + one drug",
        "(variant_key, drug, genotype, phenotype_category, annotation_id)",
    ),
    "activity_phenotype.csv": ("a metabolizer activity-score range", "(gene)"),
    "copynumbers.csv": (
        "a copy-number range",
        "(gene, modifier_gene, modifier_copy_number)",
    ),
    "repeat_alleles.csv": ("a repeat-count range", "(gene, repeat_unit)"),
    "heteroplasmy.csv": (
        "an mtDNA heteroplasmy-fraction range",
        "(gene, reference_sequence, tissue, variant_key)",
    ),
    "pgs.csv": ("a published polygenic score", "(pgs_id, trait_efo_id)"),
    # Draftable as of upstream 0.5.4: the one fact sidecar a human writes, and the
    # only table the compile licence gate reads. `licensing.csv` is its 0.6 spelling;
    # `sources.csv` is the deprecated one and inherits this entry rather than
    # repeating it, so the two can never describe themselves differently.
    "licensing.csv": ("the terms one source's data came under", "(source, layer)"),
}


def _subject_for(name: str) -> tuple[str, str]:
    """Subject and key for a table kind, following a deprecated spelling to its own.

    `draft.DRAFTABLE` lists both `sources.csv` and `licensing.csv` in 0.6 and backs
    them with one model, so answering "which table?" twice would be answering it
    twice differently the first time somebody edits one line. Which spelling is
    which is upstream's fact, read from `layout`, not restated here.
    """
    canonical = layout.preferred_spelling(name)
    fallback = ("(see describe_table)", "(see describe_table)")
    return _SUBJECTS.get(canonical, _SUBJECTS.get(name, fallback))

_COMPOSITION_NOTE = (
    "A module composes from optional table kinds: module_spec.yaml is the only "
    "always-present file, and at least one recognised table must exist. "
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
# **Derived, and from the public roster rather than the authoritative one.**
# `just_dna_compiler.compiler._FACT_TABLES` is the tuple the compiler actually loads
# and it carries the row model too, which is exactly what the map below needs — and it
# is private, so §2 rules it out. `just_dna_registry.specfiles` publishes the same
# roster (`FACT_CSVS` + `RESOLUTION_CSV`) because the registry has to recognise every
# file the compiler reads. Filed upstream as `S47`, asking for the compiler tuple or a
# `model_for` that covers these names.
#
# **What happens when upstream adds a fact table.** `FACT_CSVS` grows, so `sidecars`
# below grows with it and needs no edit here — that is the whole point of deriving it,
# and it is the half that went stale as a four-item literal while 0.6 shipped three new
# fact tables. `_PRODUCED_MODELS` does *not* grow by itself, so `describe_machine_table`
# refuses the new name explicitly (naming it as real and undescribable by this build
# rather than as unknown), and `test_the_produced_roster_and_its_models_agree` fails the
# moment the two disagree. One further cost, accepted knowingly: the roster now comes
# from a different package than the loader it describes, so a registry release lagging a
# compiler release makes this answer lag too. The test is the guard, not the version pin.
#
# **The licensing carve-out is derived, not special-cased.** `licensing.csv` /
# `sources.csv` is a fact sidecar that a human writes, and it is in `draft.DRAFTABLE`;
# subtracting the draftable kinds takes it out of this roster and leaves it a table kind
# with a template and a linter, which is what it is.
_PRODUCED_CSVS: tuple[str, ...] = tuple(
    sorted({specfiles.RESOLUTION_CSV, *specfiles.FACT_CSVS} - set(draft.DRAFTABLE))
)

#: `csv name -> row model` for the tables above. Hand-kept because nothing public maps
#: the two in the installed toolchain (`S47`); every model here is public and imported
#: from where it lives.
#:
#: **This map and `_PRODUCED_CSVS` above both retire together, and not yet.** `S47` was
#: accepted and fixed upstream the same day it was filed (their RM112): `hints.DERIVED_TABLE_MODELS`
#: and `hints.derived_model_for(csv_name)` are public **in their tree**, keyed on the
#: filename, derived from `_FACT_TABLES` rather than restated, and answering both
#: spellings of the licence table. Verified against what we install rather than against
#: their checkout, which is the rule: compiler 0.6.1 has **neither** symbol
#: (`hasattr(hints, "derived_model_for") is False`), so dropping this map now would break
#: the plugin for everyone installing from PyPI. Retire both — and the roster's
#: cross-package hop — in the change that raises the compiler floor to the release
#: carrying that symbol, together with `test_the_produced_roster_and_its_models_agree`,
#: which upstream's own set-equality guard then subsumes.
_PRODUCED_MODELS: dict[str, type[BaseModel]] = {
    "resolution.csv": ResolutionRow,
    "frequencies.csv": FrequencyRow,
    "gene_metrics.csv": GeneMetricsRow,
    "literature.csv": LiteratureRow,
    "gene_validity.csv": GeneValidityRow,
    "clinical_assertions.csv": ClinicalAssertionRow,
    "gwas_effects.csv": GwasEffectRow,
}

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
    if csv_name in _PRODUCED_CSVS:
        raise ToolError(
            f"{csv_name} is a machine-produced table of the installed toolchain that this build "
            "cannot describe: it has no row model registered here. That is our gap, not yours — "
            "upgrade just-module-creator, and read the file itself meanwhile."
        )
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
    # Schema discovery
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="List table kinds", readOnlyHint=True, idempotentHint=True
        )
    )
    def list_tables() -> TableList:
        """List the authorable table kinds and what each row is about.

        Start here when deciding which table a finding belongs in. The question
        is what the row's *subject* is — not what data you happen to have. A
        quantity with a threshold (repeat count, copy number, heteroplasmy
        fraction, activity score) is a binning table, not a variant row.

        `tables` is what you write; `sidecars` is what a pass writes for you, and
        `describe_machine_table` answers those columns. `licensing.csv` sits under
        `tables` on purpose — it is the one fact sidecar a human authors.
        """
        tables = []
        for name in sorted(draft.DRAFTABLE):
            subject, keyed_on = _subject_for(name)
            canonical = layout.preferred_spelling(name)
            tables.append(
                TableKind(
                    csv=name,
                    model=draft.DRAFTABLE[name].__name__,
                    subject=subject,
                    keyed_on=keyed_on,
                    companions=list(scaffold.COMPANION_KINDS.get(name, ())),
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

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Describe a table kind", readOnlyHint=True, idempotentHint=True
        )
    )
    def describe_table(csv_name: str) -> TableDescription:
        """Describe one table kind: every column, its type, vocabulary and pick-list.

        Generated from the live pydantic models, so it cannot drift from what the
        compiler accepts. Ask this before writing any vocabulary cell — several
        vocabularies are not what intuition suggests (`direction` is an axis, not
        a magnitude: neutral/protective/risk/unknown, never increase/decrease).

        The `redundancy_bearing` map names columns a later check compares against
        a source. Author those yourself from independent reading; filling one
        from the source that checks it makes the check vacuous.

        `attestation_bearing` is the stronger case, and it is a subset: those
        cells assert that a *human read something*, so filling one from a fetched
        document states something false rather than merely unverifiable.

        **Authored kinds only.** A machine-produced sidecar is answered by
        `describe_machine_table`, and asking for one here says so rather than
        calling it unknown. `licensing.csv` is answered *here*: it is a fact
        sidecar, and it is the one a human writes.
        """
        name = known_kind(csv_name, draft.DRAFTABLE, _PRODUCED_CSVS)
        described = hints.describe_table(name)
        # Both constants are global across kinds; narrow each to this table's
        # columns so an agent is not told to hand-author a column it has not got.
        present = {
            str(c["name"])
            for c in described.get("columns", [])
            if isinstance(c, dict) and c.get("name")
        }
        redundancy = {
            str(col): str(why)
            for col, why in getattr(hints, "REDUNDANCY_BEARING", {}).items()
            if str(col) in present
        }
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
            redundancy_bearing=redundancy,
            attestation_bearing=attestation,
            produced_by=schema_versions(),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Describe a machine-produced table", readOnlyHint=True, idempotentHint=True
        )
    )
    def describe_machine_table(csv_name: str) -> MachineTableDescription:
        """Describe a sidecar a PASS wrote: every column, type and vocabulary. Read-only.

        `resolution.csv` plus the fact sidecars — `list_tables().sidecars` is the live
        roster, and it is derived, so ask it rather than trusting a list in prose (a
        docstring cannot be generated, which is why this one names none). Generated
        from the live pydantic models, like every other schema answer here, so
        "ask the tool, never memory" now holds for the files an author *reads* as
        well as the ones they write. It used to stop at the authored kinds, which
        left the hole exactly where an author is looking at a produced file and
        deciding whether to touch it.

        **Nothing here writes, templates or lints these tables, and this being a
        separate tool is the reason why.** Extending `describe_table` was the other
        option and it would have had to answer three fields whose whole subject is
        authoring — `requirements` (what you must supply), `redundancy_bearing` and
        `attestation_bearing` (which cells you must reason out independently) — with
        empty values, and an empty `requirements` reads as *no requirements* rather
        than as *the question does not apply*. So the separation is structural: a
        produced table has no template, no linter and no requirements answer, it
        carries `hand_authored: false`, and the four authoring routes redirect here
        instead of pretending the name is unknown.

        **`licensing.csv` is refused here on purpose.** It is a fact sidecar and a
        human writes it — the only one — so it stays on `describe_table` with its
        template and its linter. That exception is derived from `draft.DRAFTABLE`
        rather than special-cased, so a table upstream makes hand-authorable moves
        surface without an edit here.

        A row here is not evidence of anything you authored. Read `refusal` before
        editing one of these files by hand.
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
        return MachineTableDescription(
            csv=name,
            model=model.__name__,
            columns=columns,
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

        Re-runnable: run it again with a different `kinds` to add a table later,
        and anything already present is refused rather than clobbered. Pass
        `dry_run=true` to see the plan first.

        `name` must be lowercase alphanumeric with underscores (`my-module` is
        rejected). Afterwards, replace every `<<REPLACE>>` in module_spec.yaml —
        title, description and report_title are required and the placeholder
        blocks validation.
        """
        target = resolve_dir(spec_dir, settings, must_exist=False)
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

        missing_companion = [
            f"{k} needs {c}"
            for k in requested
            for c in scaffold.COMPANION_KINDS.get(k, ())
            if c not in requested and not (target / c).exists()
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
                "report_title are required), then author the CSV rows and lint them "
                "with lint_rows before validating."
            ),
        )

    @mcp.tool(
        annotations=ToolAnnotations(title="Lint CSV rows", readOnlyHint=True, idempotentHint=True)
    )
    def lint_rows(csv_name: str, csv_text: str) -> LintResult:
        """Lint CSV text against a table kind. Writes nothing, anywhere.

        Pass the rows as text — this needs no file on disk, so use it *before*
        writing. Read all three finding levels: `error` blocks a compile,
        `warning` does not (and several known traps arrive only as warnings —
        a `risk` state with a positive weight compiles happily), and `info`
        names the columns deliberately left to you.

        **Where the redundancy-bearing columns show up here is `findings`, at
        `info` level** — one per column the linter is deliberately leaving to you.
        `alterations` on this tool carries normalizations that were *applied*, and
        on a valid table it is usually empty; upstream's `inspect_rows` reports the
        left-to-you columns as findings rather than as refused alterations. It is
        `lookup_variant` and `lookup_citation` that return refusals with
        `applied=false` and a `refusal`, because they are the tools holding a value
        they could have written.

        Either way the rule is the same: a redundancy-bearing cell is yours to
        author independently, since filling it from the source that later checks it
        makes that check vacuous. `describe_table` names the columns under
        `redundancy_bearing`.
        """
        name = known_kind(csv_name, draft.DRAFTABLE, _PRODUCED_CSVS)
        report = hints.inspect_rows(name, csv_text)
        findings = to_findings(report.findings)
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

        Pass the SAME `strict` you intend to compile with. Several checks are a
        ladder — a warning under best-effort and an error under strict — so a
        modeless pre-flight answers for the other compile. Default is strict
        because that is what the registry runs.

        `strict` means *reproducible*, not *correct*: it refuses when resolution
        left something it could not reproduce, and has no opinion on whether your
        coordinates name the variant you meant. Read `warnings` even on a pass.
        """
        target = resolve_dir(spec_dir, settings)
        result = await run_sync(lambda: compiler.validate_spec(target, strict=strict))
        return ValidationReport(
            valid=result.valid,
            strict=strict,
            errors=list(result.errors),
            warnings=list(result.warnings),
            info=list(result.info),
            stats=jsonable(result.stats),
        )

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

        Offline and deterministic: it consumes the `resolution.csv` that enrich
        produced and never fetches one. Recompiling an untouched spec reproduces
        every hash **under one compiler version** — that is the property to test.
        Upgrading the compiler moves `artifact_digest` on purpose and moves
        `content_signature` on nothing, so compare the second one across versions.
        (Re-*drafting* moves the digest too: the licence table re-stamps
        `fetched_at`, which is inside it.)

        A green compile is not evidence the module is correct. Read `warnings`:
        a genotype whose alleles are not at its locus, or a `risk` state with a
        positive weight, compiles cleanly under best-effort.

        Read `resolution_subjects` beside `fully_resolved` — over an empty list
        that flag is vacuously true. All five counters are null on a pre-0.6
        artifact, and **null never means zero**.
        """
        source = resolve_dir(spec_dir, settings)
        out = resolve_dir(output_dir, settings, must_exist=False)
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
            warnings=list(result.warnings),
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
            "| CSV | Row subject | Keyed on |",
            "|---|---|---|",
        ]
        for name in sorted(draft.DRAFTABLE):
            # `_subject_for`, not a bare `.get`: a deprecated spelling follows the
            # canonical one to its entry, so `sources.csv` describes itself rather than
            # rendering two em-dashes in a table an author is reading to choose a kind.
            subject, key = _subject_for(name)
            lines.append(f"| `{name}` | {subject} | `{key}` |")
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
            "5. `validate_module(strict=true)`, then `enrich_module` (extended mode) "
            "for coordinates and the ref check, then `compile_module(strict=true)`.\n"
            "6. Read the warnings on every green run.\n\n"
            "Never invent a PMID, never fill a cell from the source that checks it, "
            "and drop a row you cannot justify rather than picking a value to make "
            "the compile pass."
        )
