"""Literature discovery: which papers match a question.

This is the half of the literature story upstream does not own and does not
intend to. `just-dna-enricher` *verifies* — PMID existence, DOI existence, open
access, fulltext retrieval, quote matching — and has no free-text search on any
service. Discovery belongs on the app surface, so the clients live here.

What this module must never do, and the tests enforce all three:

* **Never hand over a DOI as an authored cell.** It is redundancy-bearing:
  `enricher.literature._doi_conflicts` compares the DOI you wrote against the
  registry's, so filling it from the record that gave you the PMID makes the
  check compare PubMed with itself. The DOI is returned as an *addressing key*
  and the refusal rides alongside it.
* **Never extract a passage.** No best-matching sentence, no suggested quote, no
  search-within-text. `provenance_quote` exists to record that a curator read the
  paper and found the claim; a machine-located quote asserts a reading that never
  happened.
* **Never render a failure as an absence.** A source that timed out reports
  `results=None`, never `0`. "arXiv could not answer" and "there are no preprints"
  are different facts and an author acts differently on each.

The API bases, the DOI grammar and the PMID grammar are imported from upstream
rather than restated, so a change there reaches us on the next release.
"""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from just_dna_enricher.eutils import DEFAULT_EUTILS_BASE, EutilsSettings
from just_dna_enricher.licensing import TERMS_BY_SOURCE
from just_dna_enricher.literature import DEFAULT_EUROPEPMC_BASE, EuropePmcClient
from just_dna_format.spec import DOI_PATTERN

from just_module_creator.models import (
    CitationGraph,
    FullTextResult,
    LintAlteration,
    LintFinding,
    LiteratureCandidate,
    LiteratureSearchResult,
    OpenAccessLocation,
    OpenAccessResult,
    SourceLicenseNote,
    SourceStatus,
)
from just_module_creator.net import HttpService, NetworkServices, ServiceGate, ServiceUnavailable

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# The source table
# --------------------------------------------------------------------------- #
# Pacing intervals are world-knowledge and they go stale — `api.pharmgkb.org`
# did. Each carries the page it was read from and the date, so the next person
# can check rather than guess.

PUBMED = "pubmed"
EUROPEPMC = "europepmc"
SEMANTICSCHOLAR = "semanticscholar"
PREPRINTS = "preprints"
UNPAYWALL = "unpaywall"


@dataclass(frozen=True)
class SourceSpec:
    """One discovery source: where it lives, how fast we may ask, what it needs."""

    name: str
    base_url: str
    min_interval: float
    #: Environment variable whose absence makes the source *unavailable* rather
    #: than merely slower. Only Unpaywall has one — it requires a contact address
    #: and we will not invent one.
    requires_contact: bool = False
    terms_url: str | None = None


#: NCBI publishes 3 requests/second unkeyed, 10/second with a key. The real
#: interval is derived from `EutilsSettings`, which reads NCBI_API_KEY — the value
#: here is only the fallback. https://www.ncbi.nlm.nih.gov/books/NBK25497/ (2026-08-11)
SOURCES: dict[str, SourceSpec] = {
    PUBMED: SourceSpec(
        name=PUBMED,
        base_url=DEFAULT_EUTILS_BASE,
        min_interval=0.34,
        terms_url="https://www.ncbi.nlm.nih.gov/home/about/policies/",
    ),
    # Europe PMC asks for "no more than a few requests per second" and publishes
    # no hard number. https://europepmc.org/help (2026-08-11)
    EUROPEPMC: SourceSpec(
        name=EUROPEPMC,
        base_url=DEFAULT_EUROPEPMC_BASE,
        min_interval=0.5,
        terms_url="https://europepmc.org/Copyright",
    ),
    # S2's unauthenticated pool is ~1 request/second shared; a key raises it.
    # https://api.semanticscholar.org/api-docs/graph (2026-08-11)
    SEMANTICSCHOLAR: SourceSpec(
        name=SEMANTICSCHOLAR,
        base_url="https://api.semanticscholar.org/graph/v1",
        min_interval=1.0,
        terms_url="https://api.semanticscholar.org/license/",
    ),
    # arXiv asks for one request every 3 seconds and a descriptive User-Agent.
    # https://info.arxiv.org/help/api/tou.html (2026-08-11)
    PREPRINTS: SourceSpec(
        name=PREPRINTS,
        base_url="https://export.arxiv.org/api",
        min_interval=3.0,
        terms_url="https://info.arxiv.org/help/api/tou.html",
    ),
    # Unpaywall requires an email on every request and asks for ~1/second.
    # https://unpaywall.org/products/api (2026-08-11)
    UNPAYWALL: SourceSpec(
        name=UNPAYWALL,
        base_url="https://api.unpaywall.org/v2",
        min_interval=1.0,
        requires_contact=True,
        terms_url="https://unpaywall.org/legal",
    ),
}

#: Sources that answer "which papers match this?". Unpaywall is not one of them —
#: it maps a DOI to open-access locations, which is a different question, so
#: listing it as a search source would make one `sources` value behave unlike the
#: rest. It is reached through `lookup_open_access` instead.
SEARCHABLE = (PUBMED, EUROPEPMC, SEMANTICSCHOLAR, PREPRINTS)


def known_sources() -> tuple[str, ...]:
    """Every source name, sorted. Deterministic because it reaches an error message."""
    return tuple(sorted(SOURCES))


# --------------------------------------------------------------------------- #
# The refusal
# --------------------------------------------------------------------------- #
_DOI_REFUSAL = (
    "PubMed's DOI for this record. Not written into studies.csv, because `doi` is "
    "redundancy-bearing: enricher.literature._doi_conflicts compares the DOI you "
    "authored against the registry's, and filling it from the record that gave you "
    "the PMID makes that check compare a source with itself. Read the DOI off the "
    "paper, or leave the cell empty — the enricher records the registry's DOI in "
    "literature.csv either way."
)


def doi_refusals(candidates: list[LiteratureCandidate]) -> list[LintAlteration]:
    """One withheld `doi` per candidate that has one. Ordered with the candidates."""
    return [
        LintAlteration(
            row=index,
            column="doi",
            before="",
            after=candidate.doi or "",
            kind="advisory",
            applied=False,
            source=candidate.found_in[0] if candidate.found_in else "",
            # Upstream's own token, verbatim, so the refusal reads as one rule
            # across lookup_variant, lookup_citation and here.
            refusal="redundancy_bearing",
            note=_DOI_REFUSAL,
        )
        for index, candidate in enumerate(candidates)
        if candidate.doi
    ]


# --------------------------------------------------------------------------- #
# Normalization helpers
# --------------------------------------------------------------------------- #
def doi_token(raw: str | None) -> str | None:
    """The bare lowercased `10.x/y` token, for comparing DOIs across sources.

    Upstream has this as `literature._doi_token`; it is private and two lines, so
    we write our own rather than tunnel into their module.
    """
    if not raw:
        return None
    match = DOI_PATTERN.search(raw)
    return match.group(0).lower().rstrip(".") if match else None


def _text(value: Any) -> str | None:
    """Coerce to a stripped string, mapping empty to None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_TAG = re.compile(r"<[^>]+>")


def _title(value: Any) -> str | None:
    """A title an agent can read: entities decoded, inline markup dropped.

    Europe PMC returns JATS inline markup and HTML entities in `title`, so a real
    record arrives as ``Frequency ... of the -13910C&gt;T &lt;i&gt;MCM6&lt;/i&gt;``.
    Left raw, the one field that distinguishes two papers is the least legible
    thing in the result. Only presentation is touched — no word is changed.
    """
    text = _text(value)
    if text is None:
        return None
    return _text(_TAG.sub("", html.unescape(text)))


def _year(value: Any) -> int | None:
    """First four-digit year in a free-form date, or None."""
    text = _text(value)
    if not text:
        return None
    for chunk in text.replace("-", " ").replace("/", " ").split():
        if len(chunk) == 4 and chunk.isdigit():
            return int(chunk)
    return None


# --------------------------------------------------------------------------- #
# Per-source parsers — pure, so the suite can test them against real payloads
# --------------------------------------------------------------------------- #
def parse_pubmed_summaries(payload: dict) -> list[LiteratureCandidate]:
    """`esummary` JSON -> candidates, in the order PubMed returned them."""
    result = payload.get("result") or {}
    order = [str(uid) for uid in (result.get("uids") or [])]
    out: list[LiteratureCandidate] = []
    for rank, uid in enumerate(order, start=1):
        record = result.get(uid)
        if not isinstance(record, dict):
            continue
        ids = {
            str(entry.get("idtype", "")).lower(): _text(entry.get("value"))
            for entry in record.get("articleids") or []
            if isinstance(entry, dict)
        }
        out.append(
            LiteratureCandidate(
                pmid=uid,
                pmcid=ids.get("pmcid"),
                doi=ids.get("doi"),
                title=_title(record.get("title")),
                authors=[
                    name
                    for a in record.get("authors") or []
                    if isinstance(a, dict) and (name := _text(a.get("name")))
                ],
                year=_year(record.get("pubdate") or record.get("sortpubdate")),
                venue=_text(record.get("fulljournalname")) or _text(record.get("source")),
                found_in=[PUBMED],
                rank={PUBMED: rank},
            )
        )
    return out


def parse_europepmc(payload: dict) -> list[LiteratureCandidate]:
    """Europe PMC `search` JSON -> candidates.

    `isOpenAccess` arrives as the strings 'Y'/'N'; anything else stays `None`,
    because "the field was absent" is not "not open access".
    """
    records = (payload.get("resultList") or {}).get("result") or []
    out: list[LiteratureCandidate] = []
    for rank, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            continue
        oa_raw = str(record.get("isOpenAccess") or "").upper()
        source = str(record.get("source") or "").upper()
        out.append(
            LiteratureCandidate(
                # A preprint record has no PMID; keep it None rather than "".
                pmid=_text(record.get("pmid")),
                pmcid=_text(record.get("pmcid")),
                doi=_text(record.get("doi")),
                title=_title(record.get("title")),
                authors=[name for name in [_text(record.get("authorString"))] if name is not None],
                year=_year(record.get("firstPublicationDate") or record.get("pubYear")),
                venue=_text(record.get("journalTitle")),
                abstract=_title(record.get("abstractText")),
                citation_count=record.get("citedByCount")
                if isinstance(record.get("citedByCount"), int)
                else None,
                is_open_access=True if oa_raw == "Y" else (False if oa_raw == "N" else None),
                # SRC:PPR is Europe PMC's preprint index.
                preprint=source == "PPR" or None,
                found_in=[EUROPEPMC],
                rank={EUROPEPMC: rank},
            )
        )
    return out


def parse_semantic_scholar(payload: dict) -> list[LiteratureCandidate]:
    """S2 graph `paper/search` JSON -> candidates."""
    out: list[LiteratureCandidate] = []
    for rank, record in enumerate(payload.get("data") or [], start=1):
        if not isinstance(record, dict):
            continue
        external = record.get("externalIds") or {}
        out.append(
            LiteratureCandidate(
                pmid=_text(external.get("PubMed")),
                pmcid=_text(external.get("PubMedCentral")),
                doi=_text(external.get("DOI")),
                arxiv_id=_text(external.get("ArXiv")),
                title=_title(record.get("title")),
                authors=[
                    name
                    for a in record.get("authors") or []
                    if isinstance(a, dict) and (name := _text(a.get("name")))
                ],
                year=record.get("year") if isinstance(record.get("year"), int) else None,
                venue=_text(record.get("venue")),
                abstract=_text(record.get("abstract")),
                citation_count=record.get("citationCount")
                if isinstance(record.get("citationCount"), int)
                else None,
                is_open_access=record.get("isOpenAccess")
                if isinstance(record.get("isOpenAccess"), bool)
                else None,
                url=_text((record.get("openAccessPdf") or {}).get("url"))
                if isinstance(record.get("openAccessPdf"), dict)
                else None,
                found_in=[SEMANTICSCHOLAR],
                rank={SEMANTICSCHOLAR: rank},
            )
        )
    return out


_ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def parse_arxiv(xml_text: str) -> list[LiteratureCandidate]:
    """arXiv Atom feed -> candidates. Always `preprint=True`."""
    root = ET.fromstring(xml_text)
    out: list[LiteratureCandidate] = []
    for rank, entry in enumerate(root.findall("atom:entry", _ATOM), start=1):
        identifier = _text(entry.findtext("atom:id", default="", namespaces=_ATOM))
        arxiv_id = identifier.rsplit("/abs/", 1)[-1] if identifier else None
        doi_el = entry.find("arxiv:doi", _ATOM)
        out.append(
            LiteratureCandidate(
                arxiv_id=arxiv_id,
                doi=_text(doi_el.text) if doi_el is not None else None,
                title=_title(entry.findtext("atom:title", default="", namespaces=_ATOM)),
                authors=[
                    name
                    for a in entry.findall("atom:author", _ATOM)
                    if (name := _text(a.findtext("atom:name", default="", namespaces=_ATOM)))
                ],
                year=_year(entry.findtext("atom:published", default="", namespaces=_ATOM)),
                venue="arXiv",
                abstract=_text(entry.findtext("atom:summary", default="", namespaces=_ATOM)),
                url=identifier,
                # Not peer-reviewed, and it has no PMID — so it cannot ground a
                # studies.csv row on its own. The tool says so; this flag is how.
                preprint=True,
                found_in=[PREPRINTS],
                rank={PREPRINTS: rank},
            )
        )
    return out


# --------------------------------------------------------------------------- #
# Merge
# --------------------------------------------------------------------------- #
def merge(groups: list[list[LiteratureCandidate]]) -> list[LiteratureCandidate]:
    """One candidate per distinct paper, carrying every source that found it.

    Identity is PMID first, then the normalized DOI token, then the arXiv id. No
    fuzzy title matching: a false merge silently hides a paper, and on a corpus
    this small the cost of a duplicate is far lower than the cost of a
    disappearance.

    Ordering interleaves the sources by their own rank — every source's top hit
    before anyone's second — so a `limit` is spent across them rather than on
    whoever was asked first. Ties break on first appearance, so the result is
    deterministic and never emitted from set or dict iteration.
    """
    merged: list[LiteratureCandidate] = []
    index: dict[str, int] = {}

    for group in groups:
        for candidate in group:
            keys = [
                f"pmid:{candidate.pmid}" if candidate.pmid else None,
                f"doi:{token}" if (token := doi_token(candidate.doi)) else None,
                f"arxiv:{candidate.arxiv_id}" if candidate.arxiv_id else None,
            ]
            hit = next((index[k] for k in keys if k and k in index), None)
            if hit is None:
                merged.append(candidate)
                position = len(merged) - 1
            else:
                merged[position := hit] = _combine(merged[hit], candidate)
            for key in keys:
                if key:
                    index[key] = position

    # Interleave by each source's own best position, so a `limit` spends itself
    # across the sources rather than on whichever one was asked first. Without
    # this, `limit=5` over four sources returns five PubMed hits and the reason
    # to ask anyone else disappears. Ties break on first appearance, so the order
    # stays deterministic and never depends on set or dict iteration.
    order = {id(c): i for i, c in enumerate(merged)}
    return sorted(
        merged,
        key=lambda c: (min(c.rank.values()) if c.rank else 10**6, order[id(c)]),
    )


def _combine(kept: LiteratureCandidate, extra: LiteratureCandidate) -> LiteratureCandidate:
    """Fold a second source's record into the first, filling gaps only.

    The first source to find a paper wins on every field it supplied. Nothing is
    overwritten, so the result stays attributable: `found_in` says who
    contributed, and the caller can go back to any of them.
    """
    data = kept.model_dump()
    for name, value in extra.model_dump().items():
        if name in {"found_in", "rank"}:
            continue
        if data.get(name) in (None, "", []) and value not in (None, "", []):
            data[name] = value
    data["found_in"] = list(dict.fromkeys([*kept.found_in, *extra.found_in]))
    data["rank"] = {**extra.rank, **kept.rank}
    return LiteratureCandidate(**data)


# --------------------------------------------------------------------------- #
# The clients
# --------------------------------------------------------------------------- #
@dataclass
class Discovery:
    """The search clients, sharing the server's gates and connection pools."""

    services: NetworkServices
    _built: dict[str, HttpService] = field(default_factory=dict, repr=False)

    def service(self, name: str) -> HttpService:
        """The `HttpService` for a source, built once and reused.

        PubMed shares the server's NCBI gate rather than getting its own: two
        independently correct 3/s clients against one IP is a 6/s client, and the
        enricher's `EutilsClient` is the other one.
        """
        if name not in self._built:
            spec = SOURCES[name]
            gate = (
                self.services.ncbi_gate
                if name == PUBMED
                else ServiceGate(interval=spec.min_interval)
            )
            headers = {"User-Agent": self._user_agent()}
            if name == SEMANTICSCHOLAR and (key := self.services.settings.semantic_scholar_key()):
                headers["x-api-key"] = key
            self._built[name] = self.services.register(
                HttpService(name=name, base_url=spec.base_url, gate=gate, headers=headers)
            )
        return self._built[name]

    def _user_agent(self) -> str:
        """Descriptive, with a contact. Never invented — see ``contact_email``."""
        return f"just-module-creator (mailto:{self.services.contact_email()})"

    # -- PubMed ---------------------------------------------------------- #
    def pubmed(self, term: str, limit: int) -> list[LiteratureCandidate]:
        """`esearch` for the ids, then `esummary` for the records.

        Two calls because `esearch` returns bare ids — and a bare id is exactly
        what an author must not write down. The title is the point.
        """
        settings: EutilsSettings = self.services.eutils_settings
        service = self.service(PUBMED)
        found = service.get(
            "esearch.fcgi",
            {
                **settings.identity_params(),
                "db": "pubmed",
                "term": term,
                "retmax": str(limit),
                "retmode": "json",
                "sort": "relevance",
            },
        ).json()
        ids = [str(i) for i in (found.get("esearchresult") or {}).get("idlist") or []]
        return self.pubmed_summaries(ids) if ids else []

    def pubmed_summaries(self, pmids: list[str]) -> list[LiteratureCandidate]:
        """`esummary` for known ids — the "does this PMID name the paper I meant" path."""
        if not pmids:
            return []
        settings: EutilsSettings = self.services.eutils_settings
        payload = (
            self.service(PUBMED)
            .get(
                "esummary.fcgi",
                {
                    **settings.identity_params(),
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "json",
                },
            )
            .json()
        )
        return parse_pubmed_summaries(payload)

    # -- Europe PMC ------------------------------------------------------ #
    def europepmc(
        self, query: str, limit: int, *, preprints: bool = False
    ) -> list[LiteratureCandidate]:
        """Free-text search. `preprints=True` restricts to the SRC:PPR index."""
        term = f"({query}) AND SRC:PPR" if preprints else query
        payload = (
            self.service(EUROPEPMC)
            .get(
                "search",
                {"query": term, "resultType": "core", "format": "json", "pageSize": str(limit)},
            )
            .json()
        )
        return parse_europepmc(payload)

    # -- Semantic Scholar ------------------------------------------------ #
    _S2_FIELDS = (
        "title,abstract,year,venue,authors,externalIds,citationCount,isOpenAccess,openAccessPdf"
    )

    def semantic_scholar(self, query: str, limit: int) -> list[LiteratureCandidate]:
        payload = (
            self.service(SEMANTICSCHOLAR)
            .get(
                "paper/search",
                {"query": query, "limit": str(limit), "fields": self._S2_FIELDS},
            )
            .json()
        )
        return parse_semantic_scholar(payload)

    def citations(self, paper_id: str, direction: str, limit: int) -> list[LiteratureCandidate]:
        """Papers citing this one, or cited by it. The 'has it been replicated' question."""
        edge = "citations" if direction == "citing" else "references"
        wrapper = "citingPaper" if direction == "citing" else "citedPaper"
        payload = (
            self.service(SEMANTICSCHOLAR)
            .get(
                f"paper/{paper_id}/{edge}",
                {"limit": str(limit), "fields": self._S2_FIELDS},
            )
            .json()
        )
        unwrapped = {
            "data": [
                item[wrapper]
                for item in payload.get("data") or []
                if isinstance(item, dict) and isinstance(item.get(wrapper), dict)
            ]
        }
        return parse_semantic_scholar(unwrapped)

    # -- arXiv ----------------------------------------------------------- #
    def preprints(self, query: str, limit: int) -> list[LiteratureCandidate]:
        """Europe PMC's SRC:PPR index plus arXiv, merged.

        Named `preprints` rather than `arxiv` because bioRxiv/medRxiv have no
        free-text search API of their own — `api.biorxiv.org` does date-interval
        listing and per-DOI detail only — and naming a server we do not query
        would be a lie in the argument schema.
        """
        from_epmc: list[LiteratureCandidate] = []
        try:
            from_epmc = self.europepmc(query, limit, preprints=True)
        except ServiceUnavailable as exc:
            # One index failing must not hide the other; the caller still learns
            # the source was degraded through the ServiceStatus if BOTH fail.
            log.info("preprints: Europe PMC leg unavailable (%s)", exc.reason)
        return merge([from_epmc, self._arxiv(query, limit)])

    def _arxiv(self, query: str, limit: int) -> list[LiteratureCandidate]:
        text = (
            self.service(PREPRINTS)
            .get(
                "query",
                {"search_query": f"all:{query}", "start": "0", "max_results": str(limit)},
            )
            .text
        )
        return parse_arxiv(text)

    # -- Unpaywall ------------------------------------------------------- #
    def unpaywall(self, doi: str) -> dict[str, Any]:
        """DOI -> open-access locations and the *article's* licence.

        The licence is the fact that decides whether a quote may travel inside a
        module you intend to publish, and it is per-article — which is why no
        static table on our side could answer it.
        """
        # No "contact is unset" branch any more: `contact_email` resolves to the
        # project default when nothing is configured, so Unpaywall is always
        # askable. That removed the one source that used to sit out every call on a
        # fresh checkout — and it is why setting JMC_USER_EMAIL matters, since the
        # address is now always somebody's.
        return self.service(UNPAYWALL).get(doi, {"email": self.services.contact_email()}).json()


def resolve_sources(
    requested: list[str] | None,
    allowed: frozenset[str] | None,
    *,
    catalogue: tuple[str, ...] = SEARCHABLE,
) -> tuple[list[str], list[SourceStatus]]:
    """Split a request into (sources to query, statuses for the ones excluded).

    `allowed` is the deployment ceiling (`JMC_LITERATURE_SOURCES`). A per-call
    `requested` can only narrow it: anything the operator excluded comes back as a
    `SourceStatus` with `queried=False` and a reason, **never silently dropped** —
    an author who asked for preprints and got none must be able to tell "policy
    said no" from "there are none".
    """
    wanted = list(requested) if requested else list(catalogue)
    unknown = [s for s in wanted if s not in SOURCES]
    if unknown:
        raise ValueError(
            f"Unknown literature source(s): {', '.join(sorted(unknown))}. "
            f"Known: {', '.join(known_sources())}."
        )

    queried: list[str] = []
    excluded: list[SourceStatus] = []
    for name in wanted:
        if name not in catalogue:
            excluded.append(
                SourceStatus(
                    source=name,
                    queried=False,
                    results=None,
                    reason=f"{name} does not answer free-text search; "
                    f"searchable sources are {', '.join(catalogue)}.",
                )
            )
        elif allowed is not None and name not in allowed:
            excluded.append(
                SourceStatus(
                    source=name,
                    queried=False,
                    results=None,
                    reason="excluded by JMC_LITERATURE_SOURCES",
                )
            )
        else:
            queried.append(name)
    return queried, excluded


# --------------------------------------------------------------------------- #
# Orchestration — one query, several sources, one honest answer
# --------------------------------------------------------------------------- #
def _licensing_notes(sources_used: list[str]) -> list[SourceLicenseNote]:
    """The `sources.csv` rows the author now owes, and why none was written.

    `sources.csv` must cover every source a fact table cites, and a missing row is
    a **warning, not an error**, so it ships unnoticed. Upstream's
    `TERMS_BY_SOURCE` has no entry for any literature service — not even `pubmed`,
    which `enrich_literature` writes itself — so nothing can state these terms
    today. We report that and refuse to invent it: `declared_use` is a licence
    position only the author can take, and a fabricated licence string would be
    worse than the missing warning.
    """
    notes: list[SourceLicenseNote] = []
    for name in sorted(set(sources_used)):
        spec = SOURCES[name]
        notes.append(
            SourceLicenseNote(
                source=name,
                layer="literature",
                terms_url=spec.terms_url,
                stateable_upstream=name in TERMS_BY_SOURCE,
                note=(
                    f"You read {name} by hand, so nothing wrote a sources.csv row for it and the "
                    "compile gate cannot see it. Add the row yourself. If you copy a passage from "
                    "an article into studies.csv, that is a SECOND row at layer='annotation' "
                    "carrying the ARTICLE's licence, not this service's — use lookup_open_access "
                    "to read it, because those terms are per-article."
                ),
            )
        )
    return notes


def _query_string(terms: list[str], year_from: int | None) -> str:
    """One search string. Deterministic, so the same request reads the same way."""
    joined = (
        " AND ".join(f"({t})" for t in terms) if len(terms) > 1 else (terms[0] if terms else "")
    )
    if year_from:
        joined = f"{joined} AND {year_from}:3000[dp]" if joined else f"{year_from}:3000[dp]"
    return joined


def search_literature(
    *,
    services: NetworkServices,
    terms: list[str],
    pmids: list[str] | None,
    year_from: int | None,
    requested: list[str] | None,
    limit: int,
) -> LiteratureSearchResult:
    """Ask each permitted source, merge, and report what every one of them did.

    Blocking: the tool wraps this in ``anyio.to_thread.run_sync``. One source
    failing never fails the call — it becomes a ``SourceStatus`` with
    ``results=None``, because a partial answer that says which part is missing is
    far more useful than an exception.
    """
    discovery = Discovery(services=services)
    query = _query_string(terms, year_from)

    # An explicit `pmids` lookup is its own path: it is the "does this id name the
    # paper I meant" question, and only PubMed can answer it.
    if pmids and not terms:
        return _lookup_by_pmid(discovery, pmids)

    queried, statuses = resolve_sources(requested, services.settings.allowed_literature_sources())
    groups: list[list[LiteratureCandidate]] = []

    for name in queried:
        try:
            found = _run_source(discovery, name, query, limit)
        except ServiceUnavailable as exc:
            # results=None, never 0 — a source that failed is not a source that
            # found nothing, and an author acts differently on each.
            statuses.append(
                SourceStatus(
                    source=name,
                    queried=True,
                    results=None,
                    reason=exc.reason,
                    rate_limited=exc.rate_limited,
                )
            )
            log.info("literature: %s could not answer (%s)", name, exc.reason)
            continue
        statuses.append(SourceStatus(source=name, queried=True, results=len(found), reason=None))
        groups.append(found)

    papers = merge(groups)[:limit] if groups else []
    findings = _search_findings(statuses, papers)
    return LiteratureSearchResult(
        query=query,
        papers=papers,
        sources=sorted(statuses, key=lambda s: s.source),
        withheld=doi_refusals(papers),
        findings=findings,
        licensing=_licensing_notes([s.source for s in statuses if s.queried]),
    )


def _run_source(
    discovery: Discovery, name: str, query: str, limit: int
) -> list[LiteratureCandidate]:
    """Dispatch to one source. Kept explicit rather than a dict of lambdas."""
    if name == PUBMED:
        return discovery.pubmed(query, limit)
    if name == EUROPEPMC:
        return discovery.europepmc(query, limit)
    if name == SEMANTICSCHOLAR:
        return discovery.semantic_scholar(query, limit)
    if name == PREPRINTS:
        return discovery.preprints(query, limit)
    raise ValueError(f"{name} is not a searchable source")


def _lookup_by_pmid(discovery: Discovery, pmids: list[str]) -> LiteratureSearchResult:
    """Read back the titles for ids the caller already has.

    This is the anti-fabrication path: `lookup_citation` proves a PMID exists,
    which a wrong-but-real id also does. Only a title settles it.
    """
    try:
        found = discovery.pubmed_summaries(pmids)
    except ServiceUnavailable as exc:
        return LiteratureSearchResult(
            query=f"pmids: {', '.join(pmids)}",
            papers=[],
            sources=[
                SourceStatus(
                    source=PUBMED,
                    queried=True,
                    results=None,
                    reason=exc.reason,
                    rate_limited=exc.rate_limited,
                )
            ],
            findings=[
                LintFinding(
                    level="warning",
                    message=(
                        "PubMed could not answer, so NONE of these ids was checked. An empty "
                        "result here means unchecked, not absent."
                    ),
                )
            ],
        )

    returned = {c.pmid for c in found if c.pmid}
    missing = [p for p in pmids if p not in returned]
    findings = [
        LintFinding(
            level="info",
            message=(
                "Compare each title against the paper you meant. A PMID that exists but names a "
                "different paper is the failure mode this call is for."
            ),
        )
    ]
    if missing:
        findings.append(
            LintFinding(
                level="error",
                message=(
                    f"PubMed returned no record for: {', '.join(missing)}. Do not write these "
                    "into studies.csv."
                ),
            )
        )
    return LiteratureSearchResult(
        query=f"pmids: {', '.join(pmids)}",
        papers=found,
        sources=[SourceStatus(source=PUBMED, queried=True, results=len(found), reason=None)],
        withheld=doi_refusals(found),
        findings=findings,
        licensing=_licensing_notes([PUBMED]),
    )


def _search_findings(
    statuses: list[SourceStatus], papers: list[LiteratureCandidate]
) -> list[LintFinding]:
    """Say out loud what the status list already implies, once."""
    findings: list[LintFinding] = []
    unanswered = sorted(s.source for s in statuses if s.queried and s.results is None)
    if unanswered:
        findings.append(
            LintFinding(
                level="warning",
                message=(
                    f"These sources could not answer: {', '.join(unanswered)}. Their part of the "
                    "literature is UNCHECKED, not empty — do not read this result as 'nothing "
                    "was published'."
                ),
            )
        )
    preprints = [p for p in papers if p.preprint]
    if preprints:
        # "Preprints carry no PMID" was false and cost a real citation (F28). bioRxiv and
        # medRxiv postings are indexed in PubMed under the NIH preprint pilot, so they carry a
        # PMID and often a PMCID; arXiv-index results typically carry neither. Asserting the
        # arXiv shape for both talked an author out of a row the schema accepts, while burying
        # the part that is always true and always matters — that none of them has been peer
        # reviewed. Count, never assume.
        with_pmid = [p for p in preprints if p.pmid]
        without_pmid = len(preprints) - len(with_pmid)
        parts = [
            f"{len(preprints)} result(s) are preprints: NOT peer-reviewed. A row grounded on "
            "one is legitimate and must say so in its conclusion, because a PMID alone does "
            "not show it."
        ]
        if with_pmid:
            parts.append(
                f"{len(with_pmid)} of them DO carry a PMID and can ground a studies.csv row."
            )
        if without_pmid:
            parts.append(
                f"{without_pmid} carry no PMID and cannot ground one (pmid is required), though "
                "they may still inform a hedged conclusion."
            )
        findings.append(LintFinding(level="warning", message=" ".join(parts)))
    if papers:
        findings.append(
            LintFinding(
                level="info",
                message=(
                    "Titles and abstracts are for you to read. No passage was extracted and no "
                    "paper was judged to support anything — that reading is the authoring work."
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# Reading a paper — locations, then text
# --------------------------------------------------------------------------- #
def _locations_from_unpaywall(payload: dict) -> list[OpenAccessLocation]:
    """Unpaywall's `oa_locations`, keeping the *article's* licence verbatim."""
    out: list[OpenAccessLocation] = []
    for entry in payload.get("oa_locations") or []:
        if not isinstance(entry, dict):
            continue
        url = _text(entry.get("url_for_pdf")) or _text(entry.get("url"))
        if not url:
            continue
        out.append(
            OpenAccessLocation(
                url=url,
                version=_text(entry.get("version")),
                # `license` is null for bronze OA — free to read, no reuse grant.
                # Null and "cc-by" are different answers and must stay that way.
                license=_text(entry.get("license")),
                host_type=_text(entry.get("host_type")),
            )
        )
    return out


def open_access(
    services: NetworkServices, *, pmid: str | None, doi: str | None, pmcid: str | None
) -> OpenAccessResult:
    """Where a paper may legally be read, and on what terms.

    Two sources, and they answer different halves. Europe PMC says whether *it*
    holds the article; Unpaywall says where else a legal copy lives and, crucially,
    under **which licence** — a per-article fact that decides whether a quoted
    passage may travel inside a module you intend to publish and sell. No static
    table on our side could answer that, which is why this tool exists.
    """
    discovery = Discovery(services=services)
    statuses: list[SourceStatus] = []
    findings: list[LintFinding] = []
    is_oa: bool | None = None
    locations: list[OpenAccessLocation] = []
    best: OpenAccessLocation | None = None

    if pmid:
        try:
            record = (
                (services.lookup_clients.europepmc or EuropePmcClient()).lookup([pmid]).get(pmid)
            )
        except Exception as exc:  # noqa: BLE001 - any client failure is "could not answer"
            statuses.append(
                SourceStatus(source=EUROPEPMC, queried=True, results=None, reason=str(exc))
            )
        else:
            # Europe PMC omits ids it does not know, with no error marker — so a
            # miss here means "not retrievable", NEVER "does not exist".
            if record is None:
                statuses.append(SourceStatus(source=EUROPEPMC, queried=True, results=0))
                findings.append(
                    LintFinding(
                        level="info",
                        message=(
                            "Europe PMC has no record for this id. It omits ids it does not know "
                            "without an error, so read this as 'not retrievable there', not as "
                            "'does not exist'."
                        ),
                    )
                )
            else:
                statuses.append(SourceStatus(source=EUROPEPMC, queried=True, results=1))
                is_oa = record.get("is_open_access")
                pmcid = pmcid or record.get("pmcid")
                doi = doi or record.get("doi")

    if doi:
        try:
            payload = discovery.unpaywall(doi)
        except ServiceUnavailable as exc:
            statuses.append(
                SourceStatus(
                    source=UNPAYWALL,
                    # A missing contact address means we never asked, which is a
                    # different fact from asking and being refused.
                    queried="contact address" not in exc.reason,
                    results=None,
                    reason=exc.reason,
                    rate_limited=exc.rate_limited,
                )
            )
            findings.append(
                LintFinding(
                    level="warning",
                    message=(
                        f"Unpaywall did not answer ({exc.reason}). Open-access status here is "
                        "UNCHECKED — do not read it as 'no free copy exists'."
                    ),
                )
            )
        else:
            locations = _locations_from_unpaywall(payload)
            best_raw = payload.get("best_oa_location")
            if isinstance(best_raw, dict):
                best = next(
                    (loc for loc in _locations_from_unpaywall({"oa_locations": [best_raw]})), None
                )
            unpaywall_oa = payload.get("is_oa")
            if isinstance(unpaywall_oa, bool):
                is_oa = unpaywall_oa if is_oa is None else (is_oa or unpaywall_oa)
            statuses.append(SourceStatus(source=UNPAYWALL, queried=True, results=len(locations)))

    if any(loc.license is None for loc in [*locations, *([best] if best else [])]):
        findings.append(
            LintFinding(
                level="warning",
                message=(
                    "At least one location has no licence recorded — typically bronze open "
                    "access: free to read, with NO reuse grant. Free to read is not free to "
                    "reuse, and a quoted passage inside a published module is a reuse."
                ),
            )
        )
    return OpenAccessResult(
        doi=doi,
        is_open_access=is_oa,
        best_location=best,
        locations=locations,
        sources=sorted(statuses, key=lambda s: s.source),
        findings=findings,
    )


#: Said on every fulltext retrieval, because it is the cost of using this tool.
_NO_PASSAGE_NOTE = (
    "No passage was extracted for you, and none ever will be. `enrich_literature` checks "
    "provenance_quote against this same Europe PMC fulltext, so a quote copied out of this "
    "response would make quotes_found confirm itself — and a machine-located quote asserts a "
    "reading that did not happen. Locate the passage yourself. Note the honest consequence: "
    "having read this text here, quotes_found on that row is no longer independent evidence. It "
    "has become a citation-pairing check, which still catches a quote written against the wrong "
    "PMID."
)


def fulltext(
    services: NetworkServices,
    *,
    pmid: str | None,
    pmcid: str | None,
    doi: str | None,
    max_chars: int | None,
) -> FullTextResult:
    """The document, or an honest account of why not and where else to look.

    Never silently substitutes: an abstract is *named* as an abstract in
    `text_source`, and when nothing could be retrieved `text_source` is null with
    the open-access locations attached rather than an empty string that reads
    like an empty paper.
    """
    client = services.lookup_clients.europepmc or EuropePmcClient()
    findings = [LintFinding(level="info", message=_NO_PASSAGE_NOTE)]
    record: dict | None = None

    if pmid:
        record = client.lookup([pmid]).get(pmid)
        pmcid = pmcid or (record or {}).get("pmcid")
        doi = doi or (record or {}).get("doi")

    text: str | None = None
    source: str | None = None
    if pmcid:
        text = client.fulltext(pmcid)
        source = "fulltext" if text else None

    if not text and record and record.get("abstract"):
        # Named as a substitute, never passed off as the article. Europe PMC
        # returns abstracts for paywalled records too, which is why this is worth
        # falling back to at all.
        text = record["abstract"]
        source = "abstract"
        findings.append(
            LintFinding(
                level="warning",
                message=(
                    "Fulltext was not retrievable, so this is the ABSTRACT. A claim you cannot "
                    "find in an abstract may still be in the paper — an abstract miss is not a "
                    "verdict."
                ),
            )
        )

    truncated = False
    if text and max_chars and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    locations: list[OpenAccessLocation] = []
    if not text:
        findings.append(
            LintFinding(
                level="warning",
                message=(
                    "Nothing was retrieved. `text_source` is null, which means UNCHECKED — not "
                    "that the paper has no text. Try the locations below."
                ),
            )
        )
        if doi:
            locations = open_access(services, pmid=None, doi=doi, pmcid=None).locations

    return FullTextResult(
        pmid=pmid,
        pmcid=pmcid,
        doi=doi,
        retrieved=bool(text),
        text=text,
        text_source=source,
        truncated=truncated,
        locations=locations,
        findings=findings,
    )


def citation_graph(
    services: NetworkServices, *, paper_id: str, direction: str, limit: int
) -> CitationGraph:
    """Papers citing this one, or cited by it — the replication question.

    Semantic Scholar only: it is the source that publishes the graph. A failure
    comes back as `results=None` rather than an empty list, because "S2 is rate
    limiting us" and "nobody has cited this" would otherwise look identical, and
    the second one is a real finding about the evidence.
    """
    discovery = Discovery(services=services)
    try:
        found = discovery.citations(paper_id, direction, limit)
    except ServiceUnavailable as exc:
        return CitationGraph(
            paper_id=paper_id,
            direction=direction,
            papers=[],
            sources=[
                SourceStatus(
                    source=SEMANTICSCHOLAR,
                    queried=True,
                    results=None,
                    reason=exc.reason,
                    rate_limited=exc.rate_limited,
                )
            ],
        )
    return CitationGraph(
        paper_id=paper_id,
        direction=direction,
        papers=found,
        sources=[SourceStatus(source=SEMANTICSCHOLAR, queried=True, results=len(found))],
        withheld=doi_refusals(found),
    )
