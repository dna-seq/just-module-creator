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
from just_dna_enricher import lookup as enricher_lookup
from just_dna_registry import RegistryClient, RegistryError
from mcp.types import ToolAnnotations

from just_module_creator.discovery import search_literature
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CitationLookup,
    LiteratureSearchResult,
    NamespaceAvailability,
    RegistryModule,
    RegistrySearchResult,
    VariantLookup,
)
from just_module_creator.net import NetworkServices
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


def register_research(mcp: FastMCP, settings: Settings, services: NetworkServices) -> None:
    """Register the always-on read-only lookup tools.

    ``services`` carries the one shared ``LookupClients`` for the whole server.
    Passing it into every upstream call is not an optimization: a fresh client set
    per question throws away the pacing state that keeps NCBI and gnomAD from
    refusing us, and reopens a connection for a single request.
    """

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

        eff_offline = offline_for(settings, offline)
        hint = await run_sync(
            lambda: enricher_lookup.lookup_variant(
                rsid=rsid,
                chrom=chrom,
                start=start,
                ref=ref,
                alts=alts,
                ambiguity=ambiguity,
                frequencies=frequencies,
                offline=eff_offline,
                clients=services.lookup_clients,
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
        """Check that a PMID or DOI **exists** — not that it is the right one.

        This answers existence only, and existence is a weak guard against a
        recalled id: PMIDs are densely allocated, so a number you half-remember is
        usually a real record for a different paper and comes back
        `pmid_exists=true`. Nothing upstream returns a title here, so identity
        cannot be checked from this result. **Use `literature_search(pmids=[...])`
        when the question is "does this id name the paper I meant"**, and take
        every PMID you write from a search result rather than from memory.

        A `null` in `pmid_exists` means the question was not put — not a negative
        answer, and an unasked question is never a passed check. PMIDs are 1-8
        digits; nine-digit ids are not PubMed ids (a few hundred of ClinVar's
        citation ids are exactly that).

        `withheld` carries PubMed's DOI with its refusal rather than as a cell to
        paste: `doi` is redundancy-bearing, and filling it from the record that
        gave you the PMID makes the DOI cross-check compare PubMed with itself.
        """
        if not pmid and not doi:
            raise ToolError("Provide either pmid or doi.")

        eff_offline = offline_for(settings, offline)
        hint = await run_sync(
            lambda: enricher_lookup.lookup_citation(
                pmid=pmid, doi=doi, offline=eff_offline, clients=services.lookup_clients
            )
        )
        return CitationLookup(
            pmid=getattr(hint, "pmid", None) or pmid,
            doi=getattr(hint, "doi", None) or doi,
            pmid_exists=getattr(hint, "pmid_exists", None),
            doi_exists=getattr(hint, "doi_exists", None),
            registry_doi=getattr(hint, "registry_doi", None),
            pmcid=getattr(hint, "pmcid", None),
            open_access=getattr(hint, "open_access", None),
            abstract_available=getattr(hint, "abstract_available", None),
            findings=to_findings(getattr(hint, "findings", [])),
            withheld=to_alterations(getattr(hint, "alterations", [])),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Search the literature",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def literature_search(
        query: str | None = None,
        pmids: list[str] | None = None,
        gene: str | None = None,
        rsid: str | None = None,
        trait: str | None = None,
        year_from: int | None = None,
        sources: list[str] | None = None,
        limit: int = 10,
    ) -> LiteratureSearchResult:
        """Find the papers behind a row — and confirm a PMID names the paper you meant.

        **Take every PMID you write from a result here, never from memory.** A
        recalled 8-digit number is usually a real record for a *different* paper,
        and `lookup_citation` answers `pmid_exists=true` for it. The title in this
        result is what makes the difference checkable. Pass `pmids=[...]` to look
        up ids you already have and read their titles back.

        Combine `query` with `gene`, `rsid` and `trait` — they are ANDed into one
        search string. `sources` narrows which services are asked and can never
        widen what `JMC_LITERATURE_SOURCES` permits.

        **Read `sources` before believing an empty `papers`.** A source that could
        not answer reports `results=null`; only a source that genuinely found
        nothing reports `0`. A miss is not evidence of absence.

        What this refuses, deliberately:

        - **`doi` comes back in `withheld`, not as a cell.** It is
          redundancy-bearing: filling `studies.csv:doi` from the record that gave
          you the PMID makes the DOI cross-check compare a source with itself.
        - **No relevance score across sources.** Each source's own rank is kept
          under its own name, because a combined score is a convention with no
          source behind it and it invites citing the top hit without reading it.
        - **No verdict on whether a paper supports your claim.** That is the
          reading you have to do.

        A result flagged `preprint` has no PMID and is not peer-reviewed, so it
        cannot ground a `studies.csv` row on its own — `pmid` is required there.
        """
        eff_offline = offline_for(settings, False)
        if eff_offline:
            raise ToolError(
                "Literature search needs the network and the server is configured offline "
                "(JMC_OFFLINE). There is no offline literature snapshot — upstream is explicit "
                "that once literature.csv is written it IS the pin."
            )

        terms = [t for t in (query, gene, rsid, trait) if t]
        if not terms and not pmids:
            raise ToolError("Provide a query, or gene/rsid/trait, or pmids to look up.")

        return await run_sync(
            lambda: search_literature(
                services=services,
                terms=terms,
                pmids=pmids,
                year_from=year_from,
                requested=sources,
                limit=limit,
            )
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

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Registry: is this namespace free",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def registry_namespace_available(namespace: str) -> NamespaceAvailability:
        """Check whether a namespace is legal and unclaimed. Read-only, no token needed.

        The pre-flight for `registry_claim_namespace`, which is irreversible: a
        namespace is claimed once and then owns every module published under it.
        Run this first so the claim is a decision rather than a guess.

        `valid` and `available` are separate answers. An illegal name is not a
        free one — lowercase letters and digits with single hyphens, and
        underscores are rejected rather than normalised, so `my_ns` comes back
        `valid: false` however unclaimed it is.
        """
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE), so the registry cannot be reached."
            )

        def _check() -> dict:
            with RegistryClient(settings.registry_url, timeout=settings.registry_timeout) as client:
                return client.namespace_available(namespace)

        try:
            payload = await run_sync(_check)
        except RegistryError as exc:
            raise ToolError(f"Registry error: {exc}") from exc

        valid = bool(payload.get("valid"))
        available = bool(payload.get("available"))
        if not valid:
            message = (
                f"{namespace!r} is not a legal namespace, so it cannot be claimed whatever its "
                "availability says. Use lowercase letters and digits with single hyphens; replace "
                "any underscore with a hyphen."
            )
        elif available:
            message = (
                f"{namespace!r} is free. Claiming it is irreversible and it will own every module "
                "you publish under it, so pick the name you want to keep."
            )
        else:
            message = (
                f"{namespace!r} is already owned. Pick another, or ask its owner to add you as a "
                "member — publishing under it needs a role in it, not a second claim."
            )

        return NamespaceAvailability(
            namespace=str(payload.get("namespace") or namespace),
            valid=valid,
            available=available,
            registry_url=settings.registry_url,
            message=message,
        )
