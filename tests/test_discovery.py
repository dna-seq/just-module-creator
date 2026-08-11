"""Literature discovery: parsing, merging, and the refusals.

Every fixture under `assets/literature/` is a **real captured response** for a
real identifier — PMID 11788828 is Enattah et al. 2002, the lactase-persistence
paper this repo already uses elsewhere. Ground truth is computed from the fixture
rather than pasted off a dump, per §6.

Nothing here opens a socket: the parsers are pure functions, which is why they
are separated from the clients in the first place.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from just_module_creator.discovery import (
    EUROPEPMC,
    PREPRINTS,
    PUBMED,
    SEMANTICSCHOLAR,
    UNPAYWALL,
    doi_refusals,
    doi_token,
    known_sources,
    merge,
    parse_europepmc,
    parse_pubmed_summaries,
    resolve_sources,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "literature"


def load(name: str) -> dict:
    return json.loads((ASSETS / name).read_text())


@pytest.fixture
def pubmed_records():
    return parse_pubmed_summaries(load("pubmed_esummary.json"))


@pytest.fixture
def europepmc_records():
    return parse_europepmc(load("europepmc_search.json"))


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def test_pubmed_summaries_carry_the_title_that_makes_a_pmid_checkable(pubmed_records) -> None:
    """The whole reason search exists in the essentials tier.

    `lookup_citation` can only say a PMID exists, and PMIDs are dense enough that
    a recalled one is usually a real record for the wrong paper. A title is what
    turns "it exists" into "it is the paper I meant".
    """
    enattah = next(c for c in pubmed_records if c.pmid == "11788828")

    assert enattah.title is not None and "hypolactasia" in enattah.title.lower()
    assert enattah.year == 2002
    assert enattah.doi == "10.1038/ng826"
    assert enattah.venue is not None
    assert enattah.found_in == [PUBMED]
    # Rank is the source's own 1-based position, kept per source rather than
    # merged into a score we invented.
    assert enattah.rank == {PUBMED: 1}


def test_pubmed_order_is_preserved(pubmed_records) -> None:
    """Emitted order is load-bearing, and must never come from dict iteration."""
    payload = load("pubmed_esummary.json")
    expected = [str(uid) for uid in payload["result"]["uids"]]
    assert [c.pmid for c in pubmed_records] == expected


def test_europepmc_open_access_is_three_valued(europepmc_records) -> None:
    """'Y'/'N' become True/False; anything else stays None, never False."""
    payload = load("europepmc_search.json")
    raw = [str(r.get("isOpenAccess") or "").upper() for r in payload["resultList"]["result"]]
    expected = [True if v == "Y" else (False if v == "N" else None) for v in raw]
    assert [c.is_open_access for c in europepmc_records] == expected


def test_europepmc_titles_are_readable_not_raw_markup(europepmc_records) -> None:
    """Europe PMC returns JATS markup and HTML entities in `title`.

    Left raw, the one field that distinguishes two papers arrives as
    `-13910C&gt;T &lt;i&gt;MCM6&lt;/i&gt;` — the least legible thing in the result.
    """
    titles = [c.title for c in europepmc_records if c.title]
    assert titles, "fixture should carry titles"
    for title in titles:
        assert "&gt;" not in title and "&lt;" not in title and "&amp;" not in title
        assert "<i>" not in title and "</i>" not in title

    # And the fixture really does contain markup, so this test can fail.
    raw = json.dumps(load("europepmc_search.json"))
    assert "&gt;" in raw or "&lt;" in raw


def test_a_preprint_has_no_pmid_so_it_cannot_ground_a_studies_row() -> None:
    """`StudyRow.pmid` is required, and a preprint has none until it publishes.

    Asserted against a real SRC:PPR response rather than stated in prose, because
    this is the fact that decides whether a preprint may be cited at all.
    """
    records = parse_europepmc(load("europepmc_preprints.json"))

    assert records, "fixture should carry preprint records"
    for candidate in records:
        assert candidate.preprint is True
        assert candidate.pmid is None
        # They do carry a DOI, which is how you would reach them at all.
        assert candidate.doi


# --------------------------------------------------------------------------- #
# Merging
# --------------------------------------------------------------------------- #
def test_doi_token_normalizes_across_sources() -> None:
    assert doi_token("https://doi.org/10.1038/NG826") == "10.1038/ng826"
    assert doi_token("10.1038/ng826.") == "10.1038/ng826"
    assert doi_token("not a doi") is None
    assert doi_token(None) is None


def test_one_paper_found_twice_merges_and_remembers_both_sources(
    pubmed_records, europepmc_records
) -> None:
    """The two-of-something probe: the same paper from two real sources."""
    enattah = next(c for c in pubmed_records if c.pmid == "11788828")
    # Same paper as Europe PMC would return it: same PMID, different fields filled.
    from just_module_creator.models import LiteratureCandidate

    epmc_view = LiteratureCandidate(
        pmid="11788828",
        doi="https://doi.org/10.1038/NG826",
        title=enattah.title,
        abstract="Lactase persistence is associated with a variant upstream of LCT.",
        is_open_access=False,
        found_in=[EUROPEPMC],
        rank={EUROPEPMC: 4},
    )

    merged = merge([pubmed_records, [epmc_view, *europepmc_records]])
    combined = next(c for c in merged if c.pmid == "11788828")

    assert combined.found_in == [PUBMED, EUROPEPMC]
    assert combined.rank == {PUBMED: 1, EUROPEPMC: 4}
    # The first source to find it wins on fields it supplied...
    assert combined.doi == "10.1038/ng826"
    # ...and the second only fills gaps.
    assert combined.abstract is not None
    assert combined.is_open_access is False
    # One entry, not two.
    assert sum(1 for c in merged if c.pmid == "11788828") == 1


def test_merge_is_deterministic(pubmed_records, europepmc_records) -> None:
    first = merge([pubmed_records, europepmc_records])
    second = merge([pubmed_records, europepmc_records])
    assert [c.model_dump() for c in first] == [c.model_dump() for c in second]


def test_merge_does_not_collapse_distinct_papers(pubmed_records, europepmc_records) -> None:
    """No fuzzy title matching: a false merge hides a paper, which is worse."""
    merged = merge([pubmed_records, europepmc_records])
    assert len(merged) == len(pubmed_records) + len(europepmc_records)


# --------------------------------------------------------------------------- #
# The refusals — the point of the whole design
# --------------------------------------------------------------------------- #
def test_every_candidate_with_a_doi_gets_a_refusal(pubmed_records) -> None:
    refusals = doi_refusals(pubmed_records)

    with_doi = [c for c in pubmed_records if c.doi]
    assert len(refusals) == len(with_doi)
    for alteration in refusals:
        assert alteration.column == "doi"
        assert alteration.applied is False
        # Upstream's own token, so the refusal reads as one rule across every tool.
        assert alteration.refusal == "redundancy_bearing"
        assert "redundancy-bearing" in alteration.note


def test_no_code_path_ever_offers_a_provenance_quote(pubmed_records, europepmc_records) -> None:
    """The guard that fails the day someone adds a helpful quote extractor.

    `enrich_literature` checks `provenance_quote` against the same Europe PMC
    fulltext a tool would have lifted it from, so a machine-supplied quote makes
    `quotes_found` confirm itself — and asserts a curator reading that never
    happened.
    """
    everything = doi_refusals(merge([pubmed_records, europepmc_records]))
    assert not [a for a in everything if a.column in {"provenance_quote", "provenance_regex"}]


# --------------------------------------------------------------------------- #
# The policy ceiling
# --------------------------------------------------------------------------- #
def test_a_per_call_source_list_narrows_the_ceiling_and_cannot_widen_it() -> None:
    """Same shape as the offline ceiling: policy is a maximum, not a default."""
    allowed = frozenset({PUBMED})

    queried, excluded = resolve_sources([PUBMED, EUROPEPMC], allowed)

    assert queried == [PUBMED]
    # Excluded, never silently dropped: an author who asked for Europe PMC and got
    # nothing must be able to tell "policy said no" from "there is nothing".
    assert [s.source for s in excluded] == [EUROPEPMC]
    assert excluded[0].queried is False
    assert excluded[0].results is None
    assert "JMC_LITERATURE_SOURCES" in (excluded[0].reason or "")


def test_an_unset_ceiling_allows_every_searchable_source() -> None:
    queried, excluded = resolve_sources(None, None)
    assert set(queried) == {PUBMED, EUROPEPMC, SEMANTICSCHOLAR, PREPRINTS}
    assert excluded == []


def test_an_empty_ceiling_is_not_the_same_as_an_unset_one() -> None:
    """`None` means every source; `frozenset()` means the operator switched them off."""
    queried, excluded = resolve_sources(None, frozenset())
    assert queried == []
    assert len(excluded) == 4
    assert all(s.results is None for s in excluded)


def test_asking_unpaywall_to_search_is_refused_with_a_reason() -> None:
    """It maps a DOI to locations; it does not answer 'which papers match this'."""
    queried, excluded = resolve_sources([UNPAYWALL], None)
    assert queried == []
    assert excluded[0].source == UNPAYWALL
    assert "free-text search" in (excluded[0].reason or "")


def test_an_unknown_source_names_the_valid_ones() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_sources(["scihub"], None)
    message = str(excinfo.value)
    assert "scihub" in message
    for name in known_sources():
        assert name in message


def test_a_limit_is_spent_across_sources_not_on_the_first_one(
    pubmed_records, europepmc_records
) -> None:
    """Found by dogfooding: `limit=5` over four sources returned five PubMed hits.

    If one source can crowd out the rest, asking several of them stops meaning
    anything. Every source's top hit must outrank anyone's second.
    """
    merged = merge([pubmed_records, europepmc_records])

    top_two = merged[:2]
    assert {s for c in top_two for s in c.found_in} == {PUBMED, EUROPEPMC}
    # And the ordering is by each source's own best rank, ascending.
    ranks = [min(c.rank.values()) for c in merged]
    assert ranks == sorted(ranks)
