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
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from just_module_creator.discovery import (
    _ATOM,
    EUROPEPMC,
    PREPRINTS,
    PUBMED,
    SEMANTICSCHOLAR,
    UNPAYWALL,
    doi_refusals,
    doi_token,
    known_sources,
    merge,
    parse_arxiv,
    parse_europepmc,
    parse_pubmed_summaries,
    parse_semantic_scholar,
    resolve_sources,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "literature"


def load(name: str) -> dict:
    return json.loads((ASSETS / name).read_text())


def load_text(name: str) -> str:
    return (ASSETS / name).read_text()


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

    PMIDs are dense enough that a recalled one is usually a real record for the
    wrong paper, so existence never settles identity — a title is what turns "it
    exists" into "it is the paper I meant". `lookup_citation` reports a title too
    as of upstream 0.5.4, but only search finds the id in the first place, and
    only search asks several services at once.
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
# arXiv and Semantic Scholar
#
# Both parsers went untested until 2026-08-20 for want of a fixture (`RM6`): the
# services were believed to block this machine outright. Re-probed through our
# own client, arXiv answers 200 and the S2 throttle is intermittent and
# endpoint-specific, so both fixtures below are real captured responses to the
# exact request `Discovery` makes.
# --------------------------------------------------------------------------- #
@pytest.fixture
def arxiv_records():
    return parse_arxiv(load_text("arxiv_query.xml"))


@pytest.fixture
def s2_records():
    return parse_semantic_scholar(load("semanticscholar_search.json"))


def test_arxiv_reads_the_doi_of_a_preprint_that_was_later_published(arxiv_records) -> None:
    """`arxiv:doi` is present only once a posting appears in a journal.

    The branch matters because a DOI is the only handle that reaches Unpaywall,
    so a published preprint parsed without one is a paper whose full text cannot
    be looked for.
    """
    xml = load_text("arxiv_query.xml")
    root = ET.fromstring(xml)
    expected = [
        (el.text or "").strip() if (el := entry.find("arxiv:doi", _ATOM)) is not None else None
        for entry in root.findall("atom:entry", _ATOM)
    ]

    assert [c.doi for c in arxiv_records] == expected
    # The fixture must exercise both sides, or this test cannot fail.
    assert any(d for d in expected), "fixture should carry at least one published entry"
    assert any(d is None for d in expected), "fixture should carry at least one unpublished entry"


def test_every_arxiv_result_is_a_preprint_with_no_pmid(arxiv_records) -> None:
    """The fact that decides whether an arXiv hit may ground a `studies.csv` row.

    `StudyRow.pmid` is required. An arXiv posting outside the NIH pilot has none,
    however well it matches the query — see `find-evidence`'s Preprints section,
    where the rule is "check the record, do not assume the class".
    """
    assert arxiv_records, "fixture should carry entries"
    for candidate in arxiv_records:
        assert candidate.preprint is True
        assert candidate.pmid is None
        assert candidate.venue == "arXiv"
        assert candidate.found_in == [PREPRINTS]


def test_arxiv_rank_is_the_feeds_own_order(arxiv_records) -> None:
    """Rank stays per source and is never merged into a score we invented."""
    assert [c.rank[PREPRINTS] for c in arxiv_records] == list(range(1, len(arxiv_records) + 1))


def test_semantic_scholar_splits_external_ids_into_their_own_columns(s2_records) -> None:
    """S2 nests every identifier under `externalIds`; downstream wants columns.

    Computed from the payload rather than pasted, so a shape change upstream
    fails here rather than silently dropping the one field that makes a hit
    citable.
    """
    payload = load("semanticscholar_search.json")
    external = [r.get("externalIds") or {} for r in payload["data"]]

    assert [c.pmid for c in s2_records] == [e.get("PubMed") for e in external]
    assert [c.doi for c in s2_records] == [e.get("DOI") for e in external]
    assert any(c.pmid for c in s2_records), "fixture should carry at least one PMID"


def test_semantic_scholar_open_access_is_three_valued(s2_records) -> None:
    """`None` is never `False` — an unstated flag is not a closed-access verdict."""
    payload = load("semanticscholar_search.json")
    expected = [
        r.get("isOpenAccess") if isinstance(r.get("isOpenAccess"), bool) else None
        for r in payload["data"]
    ]
    assert [c.is_open_access for c in s2_records] == expected


def test_semantic_scholar_counts_only_a_real_integer(s2_records) -> None:
    """`citationCount` is type-guarded, so a string or null becomes None.

    Zero is a real answer and must survive; the guard exists so that "not
    reported" cannot arrive as `0`.
    """
    payload = load("semanticscholar_search.json")
    expected = [
        r.get("citationCount") if isinstance(r.get("citationCount"), int) else None
        for r in payload["data"]
    ]
    assert [c.citation_count for c in s2_records] == expected


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


# --------------------------------------------------------------------------- #
# Identity, not just existence (F9, closed by upstream 0.5.4)
# --------------------------------------------------------------------------- #
def test_upstream_supplies_the_bibliographic_fields_identity_needs() -> None:
    """The contract F9 waited on. If these vanish, our docstring becomes a lie.

    `lookup_citation` promises a caller can compare a title against the paper they
    meant. That promise is only keepable while upstream's `CitationHint` carries
    the field, and it arrived in 0.5.4 — so assert against the installed package
    rather than trusting the floor in `pyproject.toml`.
    """
    import dataclasses

    from just_dna_enricher.lookup import CitationHint

    fields = {f.name for f in dataclasses.fields(CitationHint)}
    assert {"title", "journal", "year", "first_author"} <= fields


async def test_an_offline_citation_lookup_withholds_the_title_rather_than_denying_it(
    essentials_client,
) -> None:
    """A check that could not run is not a check that failed.

    Offline, every existence answer is null — and `title` has to be null too. A
    falsy-but-present title would read as "this id names no paper", which is the
    fabricated-citation fingerprint, on a run that asked nobody.
    """
    result = await essentials_client.call_tool(
        "lookup_citation", {"pmid": "11788828", "offline": True}
    )
    data = result.data

    assert data.pmid == "11788828"
    assert data.pmid_exists is None
    assert data.title is None
    assert (data.journal, data.year, data.first_author) == (None, None, None)
    # And the run says so out loud rather than looking like a clean pass.
    assert any("offline" in f.message.lower() for f in data.findings)


# --------------------------------------------------------------------------- #
# The gene/chromosome check, and the fact that it might not have run
# --------------------------------------------------------------------------- #
def test_the_gene_locus_conflict_check_reaches_our_model_three_valued() -> None:
    """A conflict list is only a pass when the skip reason is null (S24, 0.5.4).

    Built against upstream's real report object rather than a stub, because the
    whole finding is that `gene_loci` is empty in two opposite situations and only
    `gene_loci_not_checked` tells them apart.
    """
    from just_dna_enricher.identifiers import GeneLocusConflict, IdentifierReport

    from just_module_creator.models import IdentifierReport as OurReport

    ran_and_found_nothing = IdentifierReport()
    assert ran_and_found_nothing.gene_loci == []
    assert ran_and_found_nothing.gene_loci_not_checked is None

    conflict = GeneLocusConflict(
        gene="MCM6", gene_chrom="2", variant_key="1-11796321-G-A", variant_chrom="1"
    )
    # Upstream's own sentence carries both chromosomes and the advice; we pass it
    # through rather than writing a second wording for one finding.
    rendered = str(conflict)
    assert "MCM6" in rendered and "chromosome 2" in rendered and "chromosome 1" in rendered

    ours = OurReport(
        spec_dir="/tmp/spec",
        genes=[],
        traits=[],
        stale=[],
        gene_locus_conflicts=[rendered],
        gene_locus_check_skipped=None,
    )
    assert ours.gene_locus_conflicts == [rendered]

    # And an unrun comparison is distinguishable from a clean one.
    skipped = OurReport(
        spec_dir="/tmp/spec",
        genes=[],
        traits=[],
        stale=[],
        gene_locus_check_skipped="no chromosome is known for any row",
    )
    assert skipped.gene_locus_conflicts == []
    assert skipped.gene_locus_check_skipped is not None
