"""ESSENTIALS (network, read-only) — look things up before you author them.

Registered in every mode, because curation is not possible without them: to
write a genotype you need the allele pair, and to write a PMID you need to know
it exists.

Every tool here **reports and refuses to write**. A value the lookup could fill
comes back as an alteration with ``applied=false`` and a ``refusal``, because
these columns are redundancy-bearing: a later check compares your independently
authored value against the same source, so filling it from that source would
make the check vacuous — and for an rsid-only row the coordinate check would not
run at all, moving the row from honestly unverified to apparently verified.

No tool in this module writes to a spec directory.
"""

from __future__ import annotations

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CitationLookup,
    RegistryModule,
    RegistrySearchResult,
    VariantLookup,
)
from just_module_creator.settings import Settings
from just_module_creator.tools._shared import (
    jsonable,
    offline_for,
    to_alterations,
    to_findings,
)

log = get_logger()


def _module_card(card: dict) -> RegistryModule:
    """Project a registry card onto our trimmed model, tolerating shape drift."""
    identity = card.get("identity") or {}
    display = card.get("display") or {}
    stats = card.get("stats") or {}

    def pick(*keys: str, default=None):
        for source in (card, identity, display, stats):
            for key in keys:
                if isinstance(source, dict) and source.get(key) is not None:
                    return source[key]
        return default

    namespace = pick("namespace") or ""
    name = pick("name") or ""
    version = pick("version", "latest_version")
    canonical = pick("canonical_id") or (f"{namespace}/{name}" + (f"@{version}" if version else ""))
    return RegistryModule(
        canonical_id=str(canonical),
        namespace=str(namespace),
        name=str(name),
        version=str(version) if version else None,
        title=pick("title"),
        description=pick("description"),
        genes=list(pick("genes", default=[]) or []),
        variant_count=pick("variant_count"),
        license=pick("license"),
    )


def register_research(mcp: FastMCP, settings: Settings) -> None:
    """Register the always-on read-only lookup tools."""

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Look up a variant",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def lookup_variant(
        rsid: str | None = None,
        chrom: str | None = None,
        start: int | None = None,
        ref: str | None = None,
        alts: str | None = None,
        ambiguity: bool = False,
        frequencies: bool = False,
        offline: bool = False,
    ) -> VariantLookup:
        """Look up one variant: its loci, alleles, ClinVar calls and rsID currency.

        This is how you get the allele pair you need to decide a genotype. It
        writes nothing and deliberately refuses to hand you cells to paste: the
        `withheld` list carries each value with the reason it is yours to author.

        `start` in the result is the **1-based VCF position** — the number
        Ensembl, dbSNP, ClinVar and gnomAD all show. Copy it as printed; never
        subtract one. More than one locus means the rsID is paralogous (several
        genuinely distinct places) or pseudoautosomal (one place spelled twice).

        Pass `ambiguity=true` to be warned when the answer is not unique, and
        `frequencies=true` for gnomAD populations. `offline=true` restricts to
        local caches — where an empty result means unchecked, not absent.
        """
        if not rsid and not (chrom and start):
            raise ToolError("Provide either rsid, or chrom and start.")

        from just_dna_enricher import lookup as L

        eff_offline = offline_for(settings, offline)
        hint = await run_sync(
            lambda: L.lookup_variant(
                rsid=rsid,
                chrom=chrom,
                start=start,
                ref=ref,
                alts=alts,
                ambiguity=ambiguity,
                frequencies=frequencies,
                offline=eff_offline,
            )
        )
        status = getattr(hint, "rsid_status", None)
        return VariantLookup(
            rsid=getattr(hint, "rsid", None) or rsid,
            rsid_state=getattr(status, "state", None) if status else None,
            loci=jsonable(getattr(hint, "loci", []) or []),
            rsid_candidates=list(getattr(hint, "rsid_candidates", []) or []),
            clin_sig=jsonable(getattr(hint, "clin_sig", []) or []),
            populations=jsonable(getattr(hint, "populations", []) or []),
            vrs_id=getattr(hint, "vrs_id", None),
            findings=to_findings(getattr(hint, "findings", [])),
            withheld=to_alterations(getattr(hint, "alterations", [])),
            checked=sorted(str(c) for c in (getattr(hint, "checked", set()) or set())),
            offline=eff_offline,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Look up a citation",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def lookup_citation(
        pmid: str | None = None, doi: str | None = None, offline: bool = False
    ) -> CitationLookup:
        """Check that a PMID or DOI exists before you write it into studies.csv.

        Never invent a PMID. A `null` in `pmid_exists` means the question was not
        put — which is not the same as a negative answer, and an unasked question
        is never a passed check. PMIDs are 1-8 digits; nine-digit ids are not
        PubMed ids (a few hundred of ClinVar's citation ids are exactly that).
        """
        if not pmid and not doi:
            raise ToolError("Provide either pmid or doi.")

        from just_dna_enricher import lookup as L

        eff_offline = offline_for(settings, offline)
        hint = await run_sync(lambda: L.lookup_citation(pmid=pmid, doi=doi, offline=eff_offline))
        return CitationLookup(
            pmid=getattr(hint, "pmid", None) or pmid,
            doi=getattr(hint, "doi", None) or doi,
            pmid_exists=getattr(hint, "pmid_exists", None),
            doi_exists=getattr(hint, "doi_exists", None),
            registry_doi=getattr(hint, "registry_doi", None),
            pmcid=getattr(hint, "pmcid", None),
            open_access=getattr(hint, "open_access", None),
            findings=to_findings(getattr(hint, "findings", [])),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Search the module registry",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def registry_search(
        query: str | None = None,
        gene: str | None = None,
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> RegistrySearchResult:
        """Search the published module registry. Read-only, no token needed.

        Run this before authoring: an existing module covering the same genes is
        either the thing to extend or the reason not to start. Filter by free
        text (`query`), by `gene`, or by `category`.
        """
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE), so the registry cannot be reached."
            )
        from just_dna_registry import RegistryClient, RegistryError

        params: dict = {"page": page, "per_page": per_page}
        if query:
            params["q"] = query
        if gene:
            params["gene"] = gene
        if category:
            params["category"] = category

        def _search() -> dict:
            client = RegistryClient(settings.registry_url, timeout=settings.registry_timeout)
            return client.list_modules(**params)

        try:
            payload = await run_sync(_search)
        except RegistryError as exc:
            raise ToolError(f"Registry error: {exc}") from exc

        items = payload.get("items") or payload.get("results") or []
        return RegistrySearchResult(
            total=int(payload.get("total", len(items))),
            page=int(payload.get("page", page)),
            modules=[_module_card(i) for i in items if isinstance(i, dict)],
            registry_url=settings.registry_url,
        )
