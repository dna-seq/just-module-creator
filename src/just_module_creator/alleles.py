"""Turning a constructed HGVS expression into a canonical allele identity.

A source publishes ``N150fs (c.448delA)`` and leaves every identifier column
empty. The name is not a shortfall in the record — it **is** the record, and an
allele registry will hold the allele it names. This module is the one *mechanical*
rung of that procedure: given expressions somebody constructed, it asks the ClinGen
Allele Registry and reports what came back, keeping the outcomes apart.

**What it deliberately does not do.** It does not read a variant name, pin a
transcript, generate candidate readings, or choose between candidates that both
resolve. Those are the judgements upstream's own handout hands back to a human —
its §08 lists ten of them, and four of the 33 identities it produced needed one.
Constructing the expression is the author's; asking is ours.

Derived from ``../just-dna-format/docs/probes/IDENTITY_FROM_A_NAME.md``, whose
rules are re-verified against the live service in ``tests/test_alleles.py`` rather
than trusted from the prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from just_module_creator.net import HttpService, ServiceUnavailable

#: Read-only and credential-free. One request per second is the courtesy budget
#: the handout used and is not a published limit.
REGISTRY_HOST = "https://reg.genome.network"

#: The registry answers an allele it does not hold with **HTTP 200** and a
#: blank-node id. A classifier keying on the status code records that as a hit,
#: which is the handout's second negative control and is why every outcome here is
#: decided on the identifier.
_BLANK_NODE = "_:CA"


@dataclass(frozen=True)
class AlleleAnswer:
    """One expression's outcome. `outcome` is the field to read; `caid` may be null."""

    expression: str
    outcome: str
    caid: str | None = None
    title: str | None = None
    external_records: list[str] = None  # type: ignore[assignment]
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.external_records is None:
            object.__setattr__(self, "external_records", [])


def _outcome_from_error(status: int, payload: dict) -> tuple[str, str]:
    """A 4xx from this service is an ANSWER, and which one matters.

    Three of the four are evidence about the expression rather than a failure of
    the request, and collapsing them loses exactly what the caller needs:

    * ``IncorrectReferenceAllele`` says the base you called reference is not the
      one at that position — the handout's direction test, and what catches an
      inverted ref/alt. It carries the actual base, so it is the most informative
      answer the service gives.
    * ``IncorrectHgvsPosition`` / ``HgvsParsingError`` say the expression is
      malformed. **Never record a negative from these** — nothing was asked about
      an allele.
    * A 500 here is usually a 400 in disguise: a position past the end of the
      transcript returns ``InternalServerError``. Retrying it spends the budget
      three times to learn the same thing.
    """
    kind = str(payload.get("errorType") or "")
    message = str(payload.get("description") or payload.get("message") or f"HTTP {status}")
    if kind == "IncorrectReferenceAllele":
        given = payload.get("givenAllele")
        actual = payload.get("actualAllele")
        return "reference_mismatch", (
            f"The reference base at this position is {actual!r}, not the {given!r} this "
            f"expression asserts. That is evidence about direction, not a failed request: "
            f"the opposite expression is the one this locus can host."
        )
    if kind in {"IncorrectHgvsPosition", "HgvsParsingError"}:
        return "malformed", (
            f"{message} Nothing was asked about an allele, so this is not a negative."
        )
    if status >= 500:
        return "malformed", (
            f"{message} A 5xx from this service is usually a position past the end of the "
            f"transcript rather than an outage — check the position before retrying."
        )
    return "malformed", message


def lookup_allele(service: HttpService, expression: str) -> AlleleAnswer:
    """One expression, one answer. Outcomes are kept apart and never collapsed.

    ``registered`` — the registry holds this allele and names it.
    ``unregistered`` — well-formed, and the registry does not hold it. **Not
    "does not exist"**: 9 of 20 identities the handout resolved carried no external
    cross-reference at all, so registration is not fame and absence is not proof.
    ``reference_mismatch`` — the base asserted as reference is not there.
    ``malformed`` — the expression could not be read; no allele was asked about.
    ``unavailable`` — the service did not answer. Never a negative.
    """
    try:
        response = service.probe(f"/allele?hgvs={quote(expression, safe='')}")
    except ServiceUnavailable as exc:
        return AlleleAnswer(expression=expression, outcome="unavailable", detail=str(exc))
    try:
        payload = response.json()
    except ValueError:
        return AlleleAnswer(
            expression=expression, outcome="unavailable",
            detail=f"HTTP {response.status_code} with a body that is not JSON.",
        )
    if response.status_code >= 400 or "errorType" in payload:
        outcome, detail = _outcome_from_error(response.status_code, payload)
        return AlleleAnswer(expression=expression, outcome=outcome, detail=detail)
    identifier = str(payload.get("@id") or "")
    caid = identifier.rsplit("/", 1)[-1] if identifier else ""
    # Decided on the identifier, never on the status: this service returns 200 with
    # a populated payload for an allele it does not hold.
    if not caid or caid == _BLANK_NODE:
        return AlleleAnswer(
            expression=expression, outcome="unregistered",
            detail=(
                "Well-formed, and the registry does not hold it. That is not evidence the "
                "allele does not exist — registration is not fame."
            ),
        )
    external = payload.get("externalRecords") or {}
    return AlleleAnswer(
        expression=expression,
        outcome="registered",
        caid=caid,
        title=_title(payload.get("communityStandardTitle")),
        external_records=sorted(str(k) for k in external),
    )


def _title(value: object) -> str | None:
    """`communityStandardTitle` is a LIST, and a fixture written from a dump says string.

    Measured against the live service: every registered allele returned it as a
    one-element list. Caught only because the tool was run end to end against the
    real registry before shipping — a frozen fixture agreed with itself.
    """
    if isinstance(value, list):
        return "; ".join(str(item) for item in value) or None
    return str(value) if value else None


def collapse(answers: list[AlleleAnswer]) -> tuple[list[str], str | None]:
    """Distinct identifiers across the answers, and what having several means.

    The step the handout puts *before* discrimination, because it dissolves most
    of the ambiguity for free: two spellings of one legacy insertion routinely
    return the **same** id, and then there was never a choice to make. A different
    id on each proves the readings are genuinely different alleles — which is a
    question for the author, not for this module.
    """
    ids = sorted({a.caid for a in answers if a.caid})
    if len(ids) <= 1:
        return ids, None
    return ids, (
        f"{len(ids)} of these expressions name DIFFERENT alleles, so the readings are not "
        "spellings of one thing and choosing between them is a judgement about this row. "
        "Registration alone does not rank them: keep every candidate beside whatever settles it."
    )
