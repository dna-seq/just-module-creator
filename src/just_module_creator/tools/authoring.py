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
from just_dna_format import reference
from just_dna_format.integrity import IntegrityError, verify_manifest
from just_dna_format.manifest import read_manifest
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CompileReport,
    LintResult,
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
    to_alterations,
    to_findings,
)

log = get_logger()

# What one row of each kind is *about*. This is the only domain text in this
# module that is not generated: it answers "which table?", a question the schema
# cannot answer because it is about intent, not structure. Column lists,
# vocabularies and requirements all still come from the models.
_SUBJECTS: dict[str, tuple[str, str]] = {
    "variants.csv": ("one variant + one genotype", "(variant_key, genotype)"),
    "studies.csv": ("the evidence for a variant", "(variant_key, pmid)"),
    "haplotypes.csv": (
        "which variants make up a named allele",
        "(haplotype_name, variant, allele)",
    ),
    "allele_function.csv": ("what a named allele does", "(gene, allele)"),
    "diplotypes.csv": (
        "a pair of alleles (in trans)",
        "(gene, a, b, trait, drug, clinical_context)",
    ),
    "pharm_variants.csv": (
        "one variant + one drug",
        "(variant_key, drug, genotype, phenotype_category, annotation_id)",
    ),
    "activity_phenotype.csv": ("a metabolizer activity-score range", "(gene)"),
    "copynumbers.csv": ("a copy-number range", "(gene, modifier_gene, modifier_cn)"),
    "repeat_alleles.csv": ("a repeat-count range", "(gene, repeat_unit)"),
    "heteroplasmy.csv": (
        "an mtDNA heteroplasmy-fraction range",
        "(gene, reference_sequence, tissue, variant_key)",
    ),
    "pgs.csv": ("a published polygenic score", "(pgs_id, trait)"),
}

_COMPOSITION_NOTE = (
    "A module composes from optional table kinds: module_spec.yaml is the only "
    "always-present file, and at least one recognised table must exist. "
    "studies.csv is required IFF variants.csv is present. A PGx/PRS/binning "
    "module carries only its own tables and no variants.csv — never add an empty "
    "table to keep another company."
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
        """
        tables = [
            TableKind(
                csv=name,
                model=draft.DRAFTABLE[name].__name__,
                subject=_SUBJECTS.get(name, ("(see describe_table)", "—"))[0],
                keyed_on=_SUBJECTS.get(name, ("—", "(see describe_table)"))[1],
                companions=list(scaffold.COMPANION_KINDS.get(name, ())),
            )
            for name in sorted(draft.DRAFTABLE)
        ]
        return TableList(
            tables=tables,
            sidecars=[
                "resolution.csv",
                "frequencies.csv",
                "gene_metrics.csv",
                "literature.csv",
                "sources.csv",
            ],
            note=_COMPOSITION_NOTE,
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
        """
        name = known_kind(csv_name, draft.DRAFTABLE)
        described = hints.describe_table(name)
        # REDUNDANCY_BEARING is global across kinds; narrow it to this table's
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
        return TableDescription(
            csv=described.get("csv", name),
            model=str(described.get("model", "")),
            columns=jsonable(described.get("columns", [])),
            requirements=jsonable(described.get("requirements", {})),
            redundancy_bearing=redundancy,
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
        name = known_kind(csv_name, draft.DRAFTABLE)
        req = draft.authoring_requirements(name)
        return TableRequirements(
            csv=req.get("csv", name),
            always=list(req.get("always", [])),
            any_of=[list(g) for g in req.get("any_of", [])],
            defaulted=jsonable(req.get("defaulted", {})),
            optional=list(req.get("optional", [])),
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
        name = known_kind(csv_name, draft.DRAFTABLE)
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
        requested = [known_kind(k, draft.DRAFTABLE) for k in (kinds or [])]
        if rows < 1:
            raise ToolError("rows must be >= 1.")

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
        return ScaffoldResult(
            spec_dir=str(target),
            created=created,
            refused=refused,
            warnings=list(plan.warnings) + missing_companion,
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
        name = known_kind(csv_name, draft.DRAFTABLE)
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
        every hash — that is the property to test. (Re-*drafting* does not:
        sources.csv re-stamps `fetched_at`, which is inside the digest.)

        A green compile is not evidence the module is correct. Read `warnings`:
        a genotype whose alleles are not at its locus, or a `risk` state with a
        positive weight, compiles cleanly under best-effort.
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
            files=[f.name for f in getattr(artifact, "files", []) or []],
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
        return json.dumps(payload, indent=2, default=str)

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
                "artifact.digest is a different hash and moves whenever sources.csv "
                "re-stamps fetched_at, so a digest change is not evidence that "
                "content changed."
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
            subject, key = _SUBJECTS.get(name, ("—", "—"))
            lines.append(f"| `{name}` | {subject} | `{key}` |")
        lines += [
            "",
            "Enricher-produced sidecars (do not hand-author): `resolution.csv`, "
            "`frequencies.csv`, `gene_metrics.csv`, `literature.csv`, `sources.csv` — "
            "except `sources.csv` when you copied rows from a source by hand.",
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
