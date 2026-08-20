"""ESSENTIALS (network, read-only) — look things up before you author them.

Registered in every mode, because curation is not possible without them: to
write a genotype you need the allele pair, to write a PMID you need to know it
exists, to write a `trait_efo_id` you need to know the CURIE is real and current,
and to judge a claim you need the paper's text in front of you.

Each call here is bounded by what you named — one variant, one identifier, one
paper, one spec directory — which is what makes them cheap enough to be default.
The unbounded cousins (``paper_citations`` traverses a citation graph the corpus
sizes) stayed extended.

Every tool here **reports and refuses to write**. A value the lookup could fill
comes back as an alteration with ``applied=false`` and a ``refusal``, because
these columns are redundancy-bearing: a later check compares your independently
authored value against the same source, so filling it from that source would
make the check vacuous — and for an rsid-only row the coordinate check would not
run at all, moving the row from honestly unverified to apparently verified.

No tool in this module writes to a spec directory.

That is still true on format 0.6, and it now costs something worth naming. The
enricher's `check-identifiers` / `check-acmg` **CLI commands** record that the
question was put — a `verification.json` entry, unconditionally and with no flag,
so that "not run" and "ran and found nothing" stop reading alike. The underlying
functions this module calls do not; the write lives in those commands. So a
module authored entirely through this server carries no attestation for these
checks, and a registry rendering its `verification` block shows nothing where a
CLI-driven author's module shows a record. Tracked as RM9 in `docs/ROADMAP.md`. Until it is built,
say so rather than implying the checks left a trace: `close_module` is the only
thing here that writes into `verification.json`.
"""

from __future__ import annotations

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler
from just_dna_enricher import lookup as enricher_lookup
from just_dna_enricher.identifiers import check_identifiers as _check_identifiers
from just_dna_registry import RegistryError
from mcp.types import ToolAnnotations

from just_module_creator.discovery import fulltext, open_access, search_literature
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CitationLookup,
    DuplicateCheck,
    FullTextResult,
    IdentifierReport,
    IdentifierStatus,
    InstanceHealth,
    LiteratureSearchResult,
    NamespaceAvailability,
    OpenAccessResult,
    OpResult,
    RegistryModule,
    RegistrySearchResult,
    VariantLookup,
)
from just_module_creator.net import NetworkServices
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import (
    DEFAULT_CATALOG_TARGET,
    DEFAULT_WRITE_TARGET,
    client_for,
    describe,
    instance_note,
)
from just_module_creator.tools._shared import (
    jsonable,
    offline_for,
    resolve_dir,
    to_alterations,
    to_findings,
    to_published_versions,
)

log = get_logger()


def _module_card(card: dict) -> RegistryModule:
    """Project a registry card onto our trimmed model, tolerating an older server.

    Against a 0.13 registry the answer is `latest_version` with no `identity` key, and
    upstream says outright that this tolerance is safe to delete there (their `S2`). It
    stays for a narrower reason than the one it was written for: `get_module` is **not**
    one of the six methods `RegistryClient.assert_compatible` guards, so a self-hosted
    instance older than 0.13 answers it with no compatibility check in front of it. Our
    dependency floor pins the *client*; the server on the other end is someone else's
    deployment. `pick` costs one dict lookup and keeps that answer readable.
    """
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
        """Check a PMID or DOI, and read back **which paper it names**.

        Existence alone is a weak guard against a recalled id: PMIDs are densely
        allocated, so a number you half-remember is usually a real record for a
        different paper and comes back `pmid_exists=true`. Fabrication is a failure
        of *identity*, so read `title` — with `journal`, `year` and `first_author`
        beside it — and compare it against the paper you meant. A title that
        disagrees means the id is wrong however true `pmid_exists` is. They cost no
        extra request: the same `esummary` response answers both questions.

        Still take every PMID you write from a `literature_search` result rather
        than from memory. This tool checks an id you already hold; it cannot tell
        you which paper you *should* be citing.

        A `null` in `pmid_exists` — or in `title` — means the question was not put,
        not a negative answer, and an unasked question is never a passed check.
        PMIDs are 1-8 digits; nine-digit ids are not PubMed ids (a few hundred of
        ClinVar's citation ids are exactly that).

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
            title=getattr(hint, "title", None),
            journal=getattr(hint, "journal", None),
            year=getattr(hint, "year", None),
            first_author=getattr(hint, "first_author", None),
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
        and existence checks pass for it — only a title settles identity. Pass
        `pmids=[...]` to look up ids you already have and read their titles back.
        `lookup_citation` now reports a title too, so either tool can check an id
        you hold; this one is also how you find the id in the first place, across
        several services at once.

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
        target: RegistryTarget = DEFAULT_CATALOG_TARGET,
    ) -> RegistrySearchResult:
        """Search the published module registry. Read-only, no token needed.

        Run this before authoring: an existing module covering the same genes is
        either the thing to extend or the reason not to start. Filter by free
        text (`query`), by `gene`, or by `category`.

        `target` defaults to **production** — unlike the write tools, because the
        question here is about the published world. Point it at the polygon only
        to see your own rehearsals; its catalog is other people's rehearsals plus
        yours, and says nothing about what is published.
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
            client = client_for(target, settings)
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
            target=target,
            registry_url=settings.registry_url_for(target),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Registry: is this namespace free",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def registry_namespace_available(
        namespace: str, target: RegistryTarget = DEFAULT_WRITE_TARGET
    ) -> NamespaceAvailability:
        """Check whether a namespace is legal and unclaimed. Read-only, no token needed.

        The pre-flight for `registry_claim_namespace`, which is irreversible: a
        namespace is claimed once and then owns every module published under it.
        Run this first so the claim is a decision rather than a guess.

        `target` follows the claim it precedes and defaults to the polygon. The
        two instances keep separate namespace tables, so an answer about one is
        not an answer about the other — ask twice if you intend to rehearse and
        then publish for real.

        `valid` and `available` are separate answers. An illegal name is not a
        free one — lowercase letters and digits with single hyphens, and
        underscores are rejected rather than normalised, so `my_ns` comes back
        `valid: false` however unclaimed it is.

        **`available: true` with `requires_allow_test_data: true` is not a green
        light.** A `test-`prefixed name on production is unclaimed *and* refused
        there by default; the registry has an explicit override and this server
        does not offer it, so claim such a name on the polygon instead. Read
        `warnings` — they are the instance's own words about what it will do.
        """
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE), so the registry cannot be reached."
            )

        def _check() -> dict:
            with client_for(target, settings) as client:
                return client.namespace_available(namespace)

        try:
            payload = await run_sync(_check)
        except RegistryError as exc:
            raise ToolError(f"Registry error: {exc}") from exc

        valid = bool(payload.get("valid"))
        available = bool(payload.get("available"))
        # null, not False, when the instance is too old to report it: "did not say"
        # is not "does not require it", and the difference decides whether a claim
        # that reads as free will actually be accepted.
        needs_override = payload.get("requires_allow_test_data")
        needs_override = None if needs_override is None else bool(needs_override)
        warnings = [str(w) for w in payload.get("warnings") or []]

        if not valid:
            message = (
                f"{namespace!r} is not a legal namespace, so it cannot be claimed whatever its "
                "availability says. Use lowercase letters and digits with single hyphens; replace "
                "any underscore with a hyphen."
            )
        elif available and needs_override:
            # `available: true` that this surface still cannot act on. Upstream fixed
            # the older contradiction — the pre-flight used to say free where the claim
            # refused — and this is the honest reading of the fix rather than a
            # re-flattening of it: the name IS claimable there, just not by us.
            message = (
                f"{namespace!r} is unclaimed on production, but a `test-`prefixed name is refused "
                "there by default and this server does not offer the override. Claim it on the "
                'polygon (target="test") instead, or drop the prefix if the module is real. Read '
                "`warnings` — they are the instance's own words."
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
            target=target,
            registry_url=settings.registry_url_for(target),
            requires_allow_test_data=needs_override,
            warnings=warnings,
            message=message,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Get a registry module",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def registry_get_module(
        namespace: str, name: str, target: RegistryTarget = DEFAULT_CATALOG_TARGET
    ) -> OpResult:
        """Fetch one module's full registry record: card, readme, versions, manifest.

        The best available worked example — the published spec of a real module
        is more instructive than any template. `target` defaults to production
        for that reason; point it at the polygon to inspect a rehearsal of your
        own.
        """
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        def _get() -> dict:
            client = client_for(target, settings)
            return client.get_module(namespace, name)

        try:
            payload = await run_sync(_get)
        except RegistryError as exc:
            return OpResult(
                success=False, message=f"Registry error: {exc}", data={"target": target}
            )
        return OpResult(
            success=True, message=f"{namespace}/{name}", data={**dict(payload), "target": target}
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Registry: is this data already published",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def registry_is_published(
        spec_dir: str | None = None,
        signature: str | None = None,
        target: RegistryTarget = DEFAULT_CATALOG_TARGET,
    ) -> DuplicateCheck:
        """Has this authored data already been published — **under any name**?

        The question an author has well before they are ready to publish, and the
        one a name check cannot answer. It matches on the *content signature* of
        the authored rows, so it catches a rename or a rebrand that a digest
        lookup would miss: the same data under a different module name is still a
        duplicate as far as the registry is concerned.

        Pass a `spec_dir` and the signature is computed locally — **nothing is
        uploaded and no token is needed**. Pass a `signature` instead to ask about
        one you already hold.

        Why it matters more here than a duplicate check usually would: on
        production a `409 duplicate_content` is permanent. The claim belongs to the
        data, and **yanking the version that made it does not release it** — so a
        match that is already `yanked: true` still blocks. Rehearse on the
        polygon, where `registry_delete_version` frees it.

        `free_to_publish` is a duplicate verdict and nothing else. It says the data
        is unclaimed, never that the spec is valid — that is `validate_module`, and
        `registry_check` for the full dry run.
        """
        if not spec_dir and not signature:
            raise ToolError("Provide either spec_dir or signature.")
        if spec_dir and signature:
            raise ToolError(
                "Provide spec_dir or signature, not both — two answers to one question, and "
                "nothing here can tell you which one you meant."
            )
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE), so the registry cannot be asked. "
                "`module_signature` computes the signature locally if that is what you need."
            )

        if spec_dir:
            spec = resolve_dir(spec_dir, settings)
            sig = await run_sync(lambda: compiler.content_signature(spec))
        else:
            sig = str(signature)

        def _lookup() -> list:
            with client_for(target, settings) as client:
                return client.lookup_by_signature(sig)

        try:
            matches = await run_sync(_lookup)
        except RegistryError as exc:
            raise ToolError(f"Registry error: {exc}{instance_note(exc)}") from exc

        published = to_published_versions(matches)
        return DuplicateCheck(
            content_signature=sig,
            published_as=published,
            free_to_publish=not published,
            target=target,
            registry_url=settings.registry_url_for(target),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Registry: instance health and mode",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        )
    )
    async def registry_health(target: RegistryTarget = DEFAULT_WRITE_TARGET) -> InstanceHealth:
        """Is this registry instance up, and **which instance does it say it is**?

        The write tools already refuse when the instance's mode disagrees with the
        target you named. This is how you *see* that before it matters — it
        reports the deployment's own answer to "am I production or the polygon?",
        so a rehearsal can be confirmed rather than assumed.

        **`mode: null` is not a pass.** An instance too old to report its mode
        cannot have the target verified against it, and the write tools refuse
        rather than guess, so a null here predicts a refused publish. That is the
        cheap direction: the remedy is a server upgrade, where the other
        direction's remedy is nothing, because the publish already happened.

        `mode_matches_target` is null in exactly that case — never false, because
        an instance that did not answer is not an instance that disagreed.
        """
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        url = settings.registry_url_for(target)

        def _health() -> dict:
            with client_for(target, settings) as client:
                return client.health()

        try:
            payload = await run_sync(_health)
        except RegistryError as exc:
            return InstanceHealth(
                reachable=False,
                target=target,
                registry_url=url,
                message=f"{describe(target, settings)} did not answer: {exc}",
            )

        mode = payload.get("mode")
        matches = None if mode is None else (str(mode) == target)
        if mode is None:
            note = (
                "It reports no mode, so the target cannot be verified against it. Every write "
                "tool will refuse rather than guess — that needs a server upgrade, not a retry."
            )
        elif matches:
            note = f"Confirmed: this really is {describe(target, settings)}."
        else:
            note = (
                f"MISMATCH: you asked for {target!r} and it reports {str(mode)!r}. Writes will "
                "refuse before spending anything; fix the configured URL."
            )
        return InstanceHealth(
            reachable=True,
            target=target,
            registry_url=url,
            status=payload.get("status"),
            version=payload.get("version"),
            mode=str(mode) if mode is not None else None,
            mode_matches_target=matches,
            catalog=dict(payload.get("catalog") or {}),
            message=(
                f"{payload.get('status', 'unknown')}, registry "
                f"{payload.get('version')}. {note}"
            ),
        )

    # ----------------------------------------------------------------- #
    # Identifiers — is the symbol or CURIE you wrote still current
    # ----------------------------------------------------------------- #
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Check identifiers",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def check_identifiers(spec_dir: str) -> IdentifierReport:
        """Check every gene symbol (HGNC) and trait CURIE (OLS4) in a spec is current.

        Writes nothing, and reports instead of correcting — rewriting an authored
        value would destroy the evidence that the identifier moved, and a rename
        is exactly the kind of change an author needs to see rather than inherit.

        **`gene_locus_conflicts` is the one to read even when `stale` is empty.**
        It names rows whose gene sits on a different chromosome than the row's own
        variant — a relationship that is false while both halves are individually
        true, so no per-identifier check can catch it. That pairing is what a
        machine-written summary produces: a real symbol beside an invented rsID
        that resolves anyway. And an empty list only means "nothing disagreed"
        while `gene_locus_check_skipped` is null; otherwise the comparison never
        ran, which is not a pass.
        """
        target = resolve_dir(spec_dir, settings)
        if settings.offline:
            raise ToolError(
                "The server is configured offline (JMC_OFFLINE); this check needs HGNC and OLS4."
            )
        report = await run_sync(lambda: _check_identifiers(spec_dir=target))

        genes = [
            IdentifierStatus(
                identifier=g.symbol,
                kind="gene",
                state=g.state,
                current=g.current,
                label=g.hgnc_id,
            )
            for g in getattr(report, "genes", []) or []
        ]
        traits = [
            IdentifierStatus(
                identifier=t.curie,
                kind="trait",
                state=t.state,
                current=t.replaced_by,
                label=t.label,
            )
            for t in getattr(report, "traits", []) or []
        ]
        stale = [
            f"{s.kind} {s.identifier}: {s.state}" + (f" -> {s.current}" if s.current else "")
            for s in genes + traits
            if s.state not in {"approved", "current"}
        ]
        return IdentifierReport(
            spec_dir=str(target),
            genes=genes,
            traits=traits,
            stale=stale,
            # `str(conflict)` is upstream's own sentence, which already says which
            # chromosome each half claims and what to do about it. Reformatting it
            # here would put a second wording in front of one finding.
            gene_locus_conflicts=[str(c) for c in getattr(report, "gene_loci", []) or []],
            gene_locus_check_skipped=getattr(report, "gene_loci_not_checked", None),
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Look up a gene or trait",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def lookup_identifier(kind: str, identifier: str) -> IdentifierStatus:
        """Check one gene symbol or trait CURIE. `kind` is "gene" or "trait".

        A gene comes back approved / retired / unknown; a trait current /
        obsolete / absent. Writes nothing.

        This is what `trait_efo_id` is for: `describe_table` tells you the column
        takes an ontology CURIE, and this is the only thing that tells you the one
        you have in mind is real and current. Writing an ontology id from memory
        is the failure this exists to prevent.
        """
        if kind not in {"gene", "trait"}:
            raise ToolError('kind must be "gene" or "trait".')
        if settings.offline:
            raise ToolError("The server is configured offline (JMC_OFFLINE).")

        if kind == "gene":
            status = await run_sync(lambda: enricher_lookup.lookup_gene(identifier))
            return IdentifierStatus(
                identifier=status.symbol,
                kind="gene",
                state=status.state,
                current=status.current,
                label=status.hgnc_id,
            )
        status = await run_sync(lambda: enricher_lookup.lookup_trait(identifier))
        return IdentifierStatus(
            identifier=status.curie,
            kind="trait",
            state=status.state,
            current=status.replaced_by,
            label=status.label,
        )

    # ----------------------------------------------------------------- #
    # Reading a paper
    # ----------------------------------------------------------------- #
    def _require_network(what: str) -> None:
        if offline_for(settings, False):
            raise ToolError(
                f"{what} needs the network and the server is configured offline (JMC_OFFLINE). "
                "There is no offline literature snapshot."
            )

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Find a legal open-access copy",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def lookup_open_access(
        pmid: str | None = None, doi: str | None = None, pmcid: str | None = None
    ) -> OpenAccessResult:
        """Where a paper may legally be read, and **on what terms**.

        The licence is the point, not the URL. **Free to read is not free to
        reuse**: a `bronze` location has no licence recorded at all, and a passage
        copied from a CC-BY-NC article into `studies.csv` is publisher text sitting
        in your module's annotation layer — where `commercial_use=false` actually
        bites on a module you intend to sell.

        These terms are **per article**, not per source, which is why no table on
        our side could answer this and why `licensing.csv` needs a row carrying the
        *article's* licence rather than PubMed's.

        A `null` in `is_open_access` means unchecked. Europe PMC omits ids it does
        not know without an error, so a miss there is "not retrievable", never
        "does not exist".
        """
        _require_network("Open-access lookup")
        if not (pmid or doi or pmcid):
            raise ToolError("Provide a pmid, doi or pmcid.")
        return await run_sync(lambda: open_access(services, pmid=pmid, doi=doi, pmcid=pmcid))

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Fetch a paper's text",
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def fetch_fulltext(
        pmid: str | None = None,
        pmcid: str | None = None,
        doi: str | None = None,
        max_chars: int | None = None,
    ) -> FullTextResult:
        """Retrieve a paper's text so **you** can read it — and you may quote it.

        Reversed 2026-08-20. This tool used to refuse to return a passage on the
        grounds that a machine-located quote asserts a reading that never
        happened. It does not: it hands you the article, you read it, and the
        reading is real. What that rule actually protected was a fiction about
        *who* read the paper, and it left `provenance_quote` empty for the only
        reader present. See CLAUDE.md §2.

        So: locate the passage, quote it **verbatim**, and make it the passage
        that supports **this row's own claim** — its variant, its trait, its
        direction. Say who located it. A quote that is right for the article but
        not for the row is not provenance for that row.

        **Never the article's title.** A title occurs in its own fulltext, so
        `quotes_found` matches it every time and reports full coverage over
        metadata nobody had to read. Four published modules carry a quote on all
        3668 rows and every one is the title (`F42`). One identical string across
        every row citing a PMID is the signature — a real passage varies with the
        claim.

        **The honest cost of using this tool**, stated so you can weigh it: having
        read the fulltext here, `quotes_found` on that row is no longer independent
        evidence that the claim is in the paper. It has become a citation-pairing
        check — still useful, since it catches a quote filed against the wrong
        PMID. State that; do not let it stop you quoting.

        `text_source` says what you actually got: `fulltext`, `abstract` (named as
        a substitute, never passed off as the article), or `null` — which means
        **nothing was retrieved**, not that the paper has no text. An abstract
        *miss* is not a verdict: the claim may still be in the paper.
        """
        _require_network("Fulltext retrieval")
        if not (pmid or pmcid or doi):
            raise ToolError("Provide a pmid, pmcid or doi.")
        return await run_sync(
            lambda: fulltext(services, pmid=pmid, pmcid=pmcid, doi=doi, max_chars=max_chars)
        )
