"""Network, read-only — look things up before you author them.

Curation is not possible without them: to
write a genotype you need the allele pair, to write a PMID you need to know it
exists, to write a `trait_efo_id` you need to know the CURIE is real and current,
and to judge a claim you need the paper's text in front of you.

Each call here is bounded by what you named — one variant, one identifier, one
paper, one spec directory. The unbounded cousin is ``paper_citations``, which
traverses a citation graph the corpus sizes; it is registered like everything
else and says so in its own docstring.

Every tool here **reports and refuses to write**. A value the lookup could fill
comes back as an alteration with ``applied=false`` and a ``refusal``, because
these columns are redundancy-bearing: a later check compares your independently
authored value against the same source, so filling it from that source would
make the check vacuous — and for an rsid-only row the coordinate check would not
run at all, moving the row from honestly unverified to apparently verified.

**No tool in this module writes to a spec directory, and the claim is literal.**
It was true and quietly costing something until `RM9`: ``check_identifiers`` lived
here and therefore left no trace, so a module authored entirely through this server
showed nothing where a CLI-driven author's showed a record. The fix was to move the
tool rather than to narrow the sentence — see ``tools/checks.py``, which writes an
attestation and says so in its first line. A boundary a reader can rely on beats one
qualified by an exception.

"""

from __future__ import annotations

from pathlib import Path

from anyio.to_thread import run_sync
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from just_dna_compiler import compiler
from just_dna_enricher import lookup as enricher_lookup
from just_dna_enricher.literature import EuropePmcClient
from just_dna_enricher.locations import default_ensembl_cache_dir
from just_dna_registry import RegistryError
from mcp.types import ToolAnnotations

from just_module_creator import supplementary
from just_module_creator.discovery import (
    DEFAULT_EUROPEPMC_BASE,
    fulltext,
    open_access,
    search_literature,
)
from just_module_creator.logging_setup import get_logger
from just_module_creator.models import (
    CitationLookup,
    DuplicateCheck,
    FullTextResult,
    IdentifierStatus,
    InstanceHealth,
    LiteratureSearchResult,
    NamespaceAvailability,
    OpenAccessResult,
    OpResult,
    RegistryModule,
    RegistrySearchResult,
    SupplementaryDescription,
    SupplementaryFetch,
    SupplementaryFileInfo,
    SupplementaryList,
    SupplementaryRows,
    VariantLookup,
)
from just_module_creator.net import HttpService, NetworkServices, ServiceGate, ServiceUnavailable
from just_module_creator.settings import RegistryTarget, Settings
from just_module_creator.targets import (
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
        # The catalog truncates `genes` to the first few alphabetically and reports the real
        # total separately. Dropping it made a three-gene sample read as a complete list — a
        # module whose own description names 22 genes showed three, and a caller filtering the
        # returned records in memory got wrong answers with nothing saying so.
        gene_count=pick("gene_count"),
        variant_count=pick("variant_count"),
        license=pick("license"),
    )


def _search_next_step(*, total: int, group: str | None, namespace: str | None) -> str:
    """What a search page establishes, and the zero it must not be read as.

    The registry keeps its test/sandbox namespaces out of an unfiltered listing on
    both instances, and counts them in `/health` — so `registry_health` reporting a
    populated polygon beside `total: 0` here is two correct answers to two different
    questions, not a broken catalog. It is documented server policy; the defect was
    ours, in offering no way to ask the other question and no note saying one existed.

    ``group="test"`` selects those namespaces and an explicit ``namespace`` pops the
    exclusion, so a zero under either really is a measured zero. An unfiltered zero
    measured only the part of the instance a listing shows, which is why it gets the
    long sentence and the retry named in it.
    """
    scoped = bool(group) or bool(namespace)
    if total == 0 and not scoped:
        return (
            "Nothing matched — and this listing left the instance's test/sandbox namespaces "
            'out, so the zero is not evidence of absence. Retry with group="test" to list '
            "those instead; on the polygon that is usually where everything is, a rehearsal "
            "you just published included. An explicit `namespace` reaches one directly, and "
            "`registry_get_module` answers for a module you can already name."
        )
    if total == 0:
        return "Nothing matched under this filter."
    if not scoped:
        return (
            "These are the matches outside the instance's test/sandbox namespaces, which a "
            'listing leaves out by default. Pass group="test" or a `namespace` to see those — '
            "no single group lists an instance whole."
        )
    return "These are the matches under this filter."


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

        How you get the allele pair you need to decide a genotype. It writes nothing and
        deliberately refuses to hand you cells to paste — `withheld` carries each value
        with the reason it is yours to author. `start` in the result is the **1-based
        VCF position**, the number Ensembl, dbSNP, ClinVar and gnomAD all show: copy it
        as printed, never subtract one. More than one locus means the rsID is paralogous
        (several genuinely distinct places) or pseudoautosomal (one place spelled
        twice). Pass `ambiguity=true` to be warned when the answer is not unique,
        `frequencies=true` for gnomAD populations, and note that under `offline=true` an
        empty result means unchecked, not absent.
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

        Existence alone is a weak guard: PMIDs are densely allocated, so a half-
        remembered number is usually a real record for a different paper and comes back
        `pmid_exists=true`. Fabrication is a failure of *identity*, so read `title` —
        with `journal`, `year` and `first_author` beside it, all from the same
        `esummary` response at no extra request — and a title that disagrees means the
        id is wrong however true `pmid_exists` is. Still take every PMID you write from
        a `literature_search` result: this checks an id you hold, it cannot tell you
        which paper you should be citing. A `null` in `pmid_exists` or `title` means the
        question was not put, and an unasked question is never a passed check; PMIDs are
        1-8 digits, so a nine-digit id is not one. `withheld` carries PubMed's DOI with
        its refusal rather than as a cell to paste, because filling `doi` from the
        record that gave you the PMID makes the DOI cross-check compare PubMed with
        itself.
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

        **Take every PMID you write from a result here, never from memory**: a recalled
        8-digit number is usually a real record for a *different* paper and existence
        checks pass for it, so only a title settles identity. Pass `pmids=[...]` to read
        back the titles of ids you already hold. Combine `query` with `gene`, `rsid` and
        `trait` — they are ANDed — and `sources` narrows which services are asked, never
        widening what `JMC_LITERATURE_SOURCES` permits. **Read `sources` before
        believing an empty `papers`**: a source that could not answer reports
        `results=null`, only one that found nothing reports `0`, and a miss is not
        evidence of absence. Three deliberate refusals: `doi` comes back in `withheld`
        rather than as a cell (filling `studies.csv:doi` from the record that gave you
        the PMID makes that cross-check compare a source with itself), there is no
        relevance score across sources (a combined score has no source behind it and
        invites citing the top hit unread), and there is no verdict on whether a paper
        supports your claim. A `preprint` result has no PMID and cannot ground a
        `studies.csv` row on its own.
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
        target: RegistryTarget,
        query: str | None = None,
        gene: str | None = None,
        category: str | None = None,
        group: str | None = None,
        namespace: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> RegistrySearchResult:
        """Search the published module registry. Read-only, no token needed.

        Run this before authoring: an existing module covering the same genes is
        either the thing to extend or the reason not to start. Filter by free
        text (`query`), by `gene`, or by `category`.

        `target` is REQUIRED and has no default. `prod` is the published world
        this question is usually about; `test` is the polygon, where a publish is
        a rehearsal. A search that guessed would answer confidently about the
        wrong instance.

        **A default listing is not a listing of the instance.** Both instances
        leave their test/sandbox namespaces out of an unfiltered listing — that is
        the registry's own documented policy, not a defect — while `/health`
        counts every namespace, which is how `registry_health` and this tool can
        disagree about the same instance. On the polygon those namespaces are
        usually where everything is, so a rehearsal you just published comes back
        `total: 0` from a plain search.

        Two ways past it, and neither is a default here: `group="test"` selects
        those namespaces instead of excluding them, and an explicit `namespace`
        reaches one directly. **No single `group` lists an instance whole**, so a
        zero from a plain search is never evidence that nothing is published —
        `next_step` says so on the result. `group` is the registry's own
        vocabulary and it 422s on a value it does not know.

        Nothing here infers `group` from `target`: no rule forces the `test-`
        prefix on a polygon namespace, so a silent default would hide an
        unprefixed one and reproduce the same wrong zero one level up. If you are
        reading back a module you can already name, `registry_get_module` skips
        the listing rules entirely.
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
        if group:
            params["group"] = group
        if namespace:
            params["namespace"] = namespace

        def _search() -> dict:
            client = client_for(target, settings)
            return client.list_modules(**params)

        try:
            payload = await run_sync(_search)
        except RegistryError as exc:
            raise ToolError(f"Registry error: {exc}") from exc

        items = payload.get("items") or payload.get("results") or []
        total = int(payload.get("total", len(items)))
        return RegistrySearchResult(
            total=total,
            page=int(payload.get("page", page)),
            modules=[_module_card(i) for i in items if isinstance(i, dict)],
            target=target,
            registry_url=settings.registry_url_for(target),
            next_step=_search_next_step(total=total, group=group, namespace=namespace),
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
        target: RegistryTarget, namespace: str, name: str
    ) -> OpResult:
        """Fetch one module's full registry record: card, readme, versions, manifest.

        The best available worked example — the published spec of a real module
        is more instructive than any template. `target` is REQUIRED and has no
        default: `prod` for the catalog everyone installs from, `test` for the
        polygon, where you read back a rehearsal of your own. Reading the wrong
        instance is what makes a module you just published look missing.
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
        target: RegistryTarget,
        spec_dir: str | None = None,
        signature: str | None = None,
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

    # Three tools rather than one, because inventory is cheap and fetching is not:
    # an agent that can see 54 files picks one, and an agent that cannot downloads
    # everything. The bulk route measured 224 MB to reach a 14 KB table.
    #
    # They exist because two agents given the same task independently recorded "no
    # plugin tool fetches supplementary material" and dropped a paper's whole
    # contribution — one then rebuilt the publisher URL pattern over twelve blind
    # probes with no pacing. The ladder was documented in a skill at the time; what
    # was missing was a tool, so the calls went out ungated (`F68`).
    @mcp.tool(
        annotations=ToolAnnotations(
            title="List supplementary files", readOnlyHint=True, openWorldHint=True
        )
    )
    async def list_supplementary(
        doi: str | None = None,
        pmid: str | None = None,
        pmcid: str | None = None,
    ) -> SupplementaryList:
        """What a paper published beside itself. Inventory only — fetches no file.

        A GWAS paper's body says *"263 variants across 180 loci"* and lists none of
        them; the rsIDs, effect alleles and per-trait p-values are in the
        supplementary workbook, which `fetch_fulltext` does not return. Call this
        before concluding a paper's numbers are out of reach.

        Two rungs. When the article is in Europe PMC its fulltext XML names every
        file **with its real extension**, which is authoritative — extensions are
        not guessable, and a peer-review PDF and a data workbook sit at adjacent
        indices. Otherwise the publisher's ESM URL pattern is probed, which is the
        common case for a paper published this month, and exactly when somebody is
        writing a module about it.

        **Read `verdict` as three-valued.** `none_published` says the paper has no
        supplementary material. `not_determinable` says no rung could answer —
        usually that no URL pattern is known for this publisher — and it is never
        evidence of absence. `notes` says what the answer is bounded by: the
        pattern rung stops enumerating on a guess, so its file list is a floor.
        """
        _require_network("Supplementary listing")
        if not (doi or pmid or pmcid):
            raise ToolError("Provide a doi, pmid or pmcid.")
        return await run_sync(lambda: _supplementary_list(services, doi, pmid, pmcid))

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Fetch one supplementary file", readOnlyHint=True, openWorldHint=True
        )
    )
    async def fetch_supplementary(url: str) -> SupplementaryFetch:
        """Download **one** supplementary file to the cache. Parses nothing.

        Takes a `url` from `list_supplementary` rather than an identifier, so the
        file you get is one you chose from an inventory you read. There is
        deliberately no fetch-everything form: Europe PMC's bulk endpoint returns a
        single zip of every file *and every figure* with no way to select, measured
        at **224 MB to reach a 14 KB table**.

        Returns a path. Read the file yourself — for a workbook,
        `describe_supplementary` says which sheets are in it.
        """
        _require_network("Supplementary fetch")
        return await run_sync(lambda: _supplementary_fetch(services, url))

    @mcp.tool(
        annotations=ToolAnnotations(
            title="Describe a supplementary workbook", readOnlyHint=True, openWorldHint=False
        )
    )
    async def describe_supplementary(path: str) -> SupplementaryDescription:
        """The sheets in a downloaded workbook, and what they call themselves.

        Offline, and needs no spreadsheet library — it reads the xlsx container
        directly, which is why it works where `openpyxl` is not installed.

        Sheets are commonly named `ST1`…`ST14` while the titles written *inside*
        them read `Supplementary Table S8: …`; both are returned because neither
        alone tells you which sheet holds what. The article's own body is the third
        half of that map — it cites *(Supplementary Table S5)* at the sentence whose
        claim you are trying to support.

        **Returns no rows, on purpose.** Which sheet supports a given row's claim is
        a judgement about that row, the same reason `fetch_fulltext` returns no
        best-matching passage. `read_supplementary` returns the rows once you have
        named a sheet.
        """
        return await run_sync(lambda: _describe_workbook(path, settings))

    # The last rung, and the argument for building it is a measurement rather than a
    # preference. `F68` deferred this as "the wrong layer" — but the thing it was
    # right to refuse is *choosing which sheet answers a row's claim*, and it filed
    # returning the cells under the same heading. Four independent authoring runs
    # then hand-wrote an xlsx parser to get past the gap, two of them with a
    # column-alignment bug, one calling it 40% of the run. Deciding is a judgement;
    # decoding a zip container is not, and this decodes.
    @mcp.tool(
        annotations=ToolAnnotations(
            title="Read rows from a supplementary workbook", readOnlyHint=True, openWorldHint=False
        )
    )
    async def read_supplementary(
        path: str, sheet: str, offset: int = 0, limit: int = 200
    ) -> SupplementaryRows:
        """The rows of one sheet in a workbook you already downloaded.

        Offline — a local file, no request. `fetch_supplementary` gets the workbook,
        `describe_supplementary` names its sheets, this reads one of them. Name the
        `sheet` exactly as that inventory spells it; a wrong name lists the real ones
        rather than guessing at the nearest.

        **Rows come back as the sheet has them**, from row 0: a title line, a blank,
        a two-level header and then the data, in order. Which row is the header is
        yours to read off them — a guess followed silently is worse than no guess.
        Every row is padded to `width`, so zipping against a header cannot shift
        columns.

        **Page on `last_populated_row`, never on `total_rows`.** They disagree
        whenever a producer left trailing blank rows, and on the one real workbook
        measured they disagreed by 734. `truncated` says populated rows remain.

        Costs context rather than egress: a 22-column sheet at `limit=200` is a
        large result, so read the first few rows to find the header before pulling
        the table. Legacy `.xls`, PDF and CSV are not read here, and that is
        reported as this reader's limit — never as a file with no rows.
        """
        return await run_sync(lambda: _read_workbook(path, sheet, offset, limit))


def _esm_service(services: NetworkServices) -> HttpService:
    """The ESM host as a paced service, built once and closed at shutdown.

    Its own gate rather than a shared one: this is an object store, not an API with
    a published budget, and it is nobody else's rate limit to spend.
    """
    for existing in services._extra:  # noqa: SLF001 — the registry is ours
        if existing.name == "publisher_esm":
            return existing
    return services.register(
        HttpService(
            name="publisher_esm",
            base_url=supplementary.ESM_HOST,
            gate=ServiceGate(interval=0.5),
            headers={"User-Agent": f"just-module-creator (mailto:{services.contact_email()})"},
        )
    )


def _supplementary_cache(settings: Settings) -> Path:
    """Beside the ecosystem's other caches, never inside a spec directory.

    A name absent from `specfiles.RECOGNIZED_SPEC_FILES` is dropped by the next
    server-side rebuild, so our own downloads live where the enricher keeps its
    snapshots. `JMC_WORKSPACE` wins when it is set, so containment still holds.
    """
    if settings.workspace:
        return resolve_dir(str(settings.workspace), settings, must_exist=False) / "supplementary"
    return default_ensembl_cache_dir().parent / "supplementary"


def _supplementary_list(
    services: NetworkServices, doi: str | None, pmid: str | None, pmcid: str | None
) -> SupplementaryList:
    client = services.lookup_clients.europepmc or EuropePmcClient()
    if pmid and not (pmcid and doi):
        record = client.lookup([pmid]).get(pmid) or {}
        pmcid = pmcid or record.get("pmcid")
        doi = doi or record.get("doi")

    xml: str | None = None
    xml_base: str | None = None
    if pmcid:
        service = services.register(
            HttpService(
                name="europepmc_xml",
                base_url=DEFAULT_EUROPEPMC_BASE,
                gate=ServiceGate(interval=0.5),
                headers={"User-Agent": f"just-module-creator (mailto:{services.contact_email()})"},
            )
        )
        try:
            xml = service.get(f"{pmcid}/fullTextXML").text
            xml_base = f"https://europepmc.org/articles/{pmcid}/bin"
        except ServiceUnavailable as exc:
            log.warning("fullTextXML unavailable for %s: %s", pmcid, exc)

    result = supplementary.inventory(
        doi=doi, xml=xml, xml_base_url=xml_base, probe=_esm_service(services)
    )
    return SupplementaryList(
        doi=result.doi,
        pmcid=pmcid,
        verdict=result.verdict,
        rung=result.rung,
        publisher=result.publisher,
        why_not=result.why_not,
        notes=result.notes,
        files=[
            SupplementaryFileInfo(
                name=f.name, url=f.url, extension=f.extension,
                caption=f.caption, size_bytes=f.size_bytes,
            )
            for f in result.files
        ],
    )


def _supplementary_fetch(services: NetworkServices, url: str) -> SupplementaryFetch:
    if not url.startswith(("http://", "https://")):
        raise ToolError("Pass a url from list_supplementary.")
    service = _esm_service(services)
    on_esm_host = url.startswith(supplementary.ESM_HOST)
    path = url[len(supplementary.ESM_HOST) :] if on_esm_host else url
    try:
        response = service.probe(path)
    except ServiceUnavailable as exc:
        return SupplementaryFetch(url=url, retrieved=False, note=f"{exc}")
    if response.status_code >= 400:
        return SupplementaryFetch(
            url=url, retrieved=False,
            note=(
                f"HTTP {response.status_code}. On this host a 403 means no such object — "
                "the file is not published under that name, which is not the same as the "
                "article having no supplementary material."
            ),
        )
    target = _supplementary_cache(services.settings)
    target.mkdir(parents=True, exist_ok=True)
    destination = target / url.rsplit("/", 1)[-1]
    destination.write_bytes(response.content)
    return SupplementaryFetch(
        url=url,
        path=str(destination),
        retrieved=True,
        size_bytes=len(response.content),
        content_type=response.headers.get("content-type"),
    )


def _describe_workbook(path: str, settings: Settings) -> SupplementaryDescription:
    resolved = Path(path)
    if not resolved.is_file():
        raise ToolError(f"No such file: {path}")
    sheets, titles = supplementary.workbook_sheets(resolved)
    if not sheets and not titles:
        return SupplementaryDescription(
            path=str(resolved), is_workbook=False,
            note=(
                "Not an xlsx workbook, or a workbook with no sheet table. A PDF, CSV or text "
                "supplement is read directly — this tool describes spreadsheet structure only."
            ),
        )
    return SupplementaryDescription(
        path=str(resolved), is_workbook=True, sheets=sheets, table_titles=titles
    )


def _read_workbook(path: str, sheet: str, offset: int, limit: int) -> SupplementaryRows:
    resolved = Path(path)
    if not resolved.is_file():
        raise ToolError(f"No such file: {path}")
    if offset < 0 or limit < 1:
        raise ToolError("`offset` is 0-based and `limit` is at least 1.")
    try:
        window = supplementary.workbook_rows(resolved, sheet, offset=offset, limit=limit)
    except supplementary.SupplementaryError as exc:
        raise ToolError(str(exc)) from exc
    last = window.last_populated_row
    return SupplementaryRows(
        path=str(resolved),
        sheet=sheet,
        sheets_available=window.sheet_names,
        rows=window.rows,
        offset=offset,
        width=window.width,
        total_rows=window.total_rows,
        last_populated_row=last,
        # Against the last POPULATED row: trailing blanks are not rows anybody is
        # waiting for, and counting them would report every sheet as truncated.
        truncated=last is not None and last >= offset + limit,
    )
