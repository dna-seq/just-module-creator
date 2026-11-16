"""Finding a trait CURIE by name, so `trait_efo_id` is picked from candidates rather than recalled.

`lookup_identifier` checks a CURIE you already hold, and memory is the only place one came from.
In the `a2` benchmark run (RM28, `F79`) memory produced `EFO_0007796`: real and current, and
"parental longevity", a different trait. The checker answered `current`, which turned a wrong
guess into a confident wrong answer. A search puts the candidates and their labels side by side.

**Obsolete terms are reported, never filtered.** In that run the one record that led anywhere was
the obsolete `EFO_0004300`, whose successor is `OBA_VT0005372` ("life span determination trait"),
the term the module carries. OLS4 leaves obsolete terms out of a search unless asked, and asked it
returns obsolete terms only, so this makes two searches and keeps the halves apart. Each obsolete
hit's successor comes from upstream's own `lookup_trait`, since the search response does not
carry it.

The ranking is OLS4's relevance order. Nothing here judges which candidate is right: choosing a
trait for a row is the author's.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from just_dna_enricher.identifiers import DEFAULT_OLS4_BASE, TraitStatus

from just_module_creator.net import HttpService, ServiceUnavailable

#: Upstream's public OLS4 root. Its search endpoint sits beside the term endpoints
#: upstream's checker reads.
OLS4_BASE = DEFAULT_OLS4_BASE

#: The ontologies searched when the caller names none: the four `trait_efo_id`'s own field
#: description names (`just_dna_format.spec.StudyRow`). A fact this module cannot generate, so
#: `tests/test_trait_search.py` compares it with that description rather than trusting a comment.
DEFAULT_ONTOLOGIES: tuple[str, ...] = ("efo", "mondo", "oba", "hp")

#: The most hits asked for per half. Each obsolete hit costs one more request (its successor),
#: so an unbounded `limit` is an unbounded bill, and OLS4 answers HTTP 400 to a huge one.
MAX_LIMIT = 100

_FIELDS = "short_form,label,ontology_prefix,description,is_defining_ontology"


@dataclass(frozen=True)
class TermHit:
    """One candidate. `replaced_by` is asked of upstream for an obsolete hit only."""

    curie: str
    label: str | None
    ontology: str | None
    state: str  # current | obsolete
    description: str | None = None
    replaced_by: str | None = None
    #: Upstream's state for the successor question: `obsolete` when it answered,
    #: `unchecked` when it could not be asked. None on a current hit (nothing to ask).
    replacement_checked: str | None = None


@dataclass
class TermSearch:
    """Both halves. A half that could not be asked is None, never an empty list."""

    current: list[TermHit] | None
    obsolete: list[TermHit] | None
    current_found: int | None
    obsolete_found: int | None
    failures: list[str] = field(default_factory=list)
    #: True when OLS4 refused a request with a 4xx: the arguments are at fault, and asking
    #: again gets the same answer. Distinct from an outage, which a retry may clear.
    refused: bool = False


def missing_ontologies(service: HttpService, names: tuple[str, ...]) -> list[str]:
    """The names OLS4 holds no ontology under. One request each.

    OLS4's search ignores an ontology it does not hold, so a misspelt one (`ebo`) would read
    as "no term matched" rather than as a wrong argument. A name the endpoint could not be
    asked about is not reported: it is unknown, and the search itself will say so if it fails.
    """
    missing: list[str] = []
    for name in names:
        try:
            response = service.probe(f"ontologies/{name}")
        except ServiceUnavailable:
            continue
        if response.status_code == 404:
            missing.append(name)
    return missing


def _refused(exc: Exception) -> bool:
    return (
        isinstance(exc, ServiceUnavailable)
        and exc.reason.startswith("HTTP 4")
        and not (exc.rate_limited)
    )


def _hits(payload: dict[str, Any], state: str) -> tuple[list[TermHit], int | None]:
    response = payload.get("response")
    if not isinstance(response, dict):
        raise ValueError("OLS4 answered with no `response` block")
    docs = response.get("docs")
    if not isinstance(docs, list):
        raise ValueError("OLS4 answered with no `docs` list")
    found = response.get("numFound")
    hits: list[TermHit] = []
    for doc in docs:
        curie = doc.get("short_form")
        # Belt and braces with `local=true`: a copy OLS4 itself marks as imported is dropped
        # here too, so the filter holds if the server-side flag is ever ignored. That is not
        # hypothetical: `isDefiningOntology=true`, the first flag tried, is ignored (2026-11-16).
        if not curie or doc.get("is_defining_ontology") is False:
            continue
        description = doc.get("description")
        if isinstance(description, list):
            description = " ".join(str(d) for d in description) or None
        hits.append(
            TermHit(
                curie=curie,
                label=doc.get("label"),
                ontology=doc.get("ontology_prefix"),
                state=state,
                description=description,
            )
        )
    return hits, found if isinstance(found, int) else None


def _ask(
    service: HttpService, query: str, ontologies: tuple[str, ...], limit: int, obsolete: bool
) -> tuple[list[TermHit], int | None]:
    params: dict[str, Any] = {
        "q": query,
        "ontology": ",".join(ontologies),
        "rows": limit,
        # A term imported into another ontology comes back once per importer, under a
        # prefix that is not its own (`PR_…` under EFO for "longevity"), and upstream's checker
        # answers such an id `unchecked`. `local=true` keeps the defining copy only.
        "local": "true",
        "fieldList": _FIELDS,
    }
    if obsolete:
        params["obsoletes"] = "true"
    response = service.get("search", params)
    return _hits(response.json(), "obsolete" if obsolete else "current")


def search(
    service: HttpService,
    query: str,
    *,
    ontologies: tuple[str, ...] = DEFAULT_ONTOLOGIES,
    limit: int = 10,
    successor: Callable[[str], TraitStatus],
) -> TermSearch:
    """Two searches, current and obsolete, plus one successor lookup per obsolete hit."""
    failures: list[str] = []
    refused = False
    current: list[TermHit] | None
    current_found: int | None
    try:
        current, current_found = _ask(service, query, ontologies, limit, obsolete=False)
    except (ServiceUnavailable, ValueError) as exc:
        current, current_found = None, None
        failures.append(f"current terms: {exc}")
        refused = refused or _refused(exc)

    obsolete: list[TermHit] | None
    obsolete_found: int | None
    try:
        found_obsolete, obsolete_found = _ask(service, query, ontologies, limit, obsolete=True)
    except (ServiceUnavailable, ValueError) as exc:
        obsolete, obsolete_found = None, None
        failures.append(f"obsolete terms: {exc}")
        refused = refused or _refused(exc)
    else:
        obsolete = []
        for hit in found_obsolete:
            status = successor(hit.curie)
            obsolete.append(
                TermHit(
                    curie=hit.curie,
                    label=hit.label,
                    ontology=hit.ontology,
                    state="obsolete",
                    description=hit.description,
                    replaced_by=status.replaced_by,
                    replacement_checked=status.state,
                )
            )
    return TermSearch(
        current=current,
        obsolete=obsolete,
        current_found=current_found,
        obsolete_found=obsolete_found,
        failures=failures,
        refused=refused,
    )
