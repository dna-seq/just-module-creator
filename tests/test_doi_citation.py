"""A DOI looked up on its own: the work it names, and its PMID as an advisory, never a cell.

From enricher 0.8 the DOI path names the work (RM262) and resolves a PMID through Europe PMC
as an advisory (RM263), which retired our Crossref read for F113. What stays ours is the
projection: the advisory must reach `withheld` with `applied=false`, and `pmid` must stay
null, because a PMID read off the DOI's own record is the author's to type after checking
the title, not ours to fill.

The values are Enattah 2002 (PMID 11788828, DOI 10.1038/ng826), the lactase-persistence paper.
"""

from __future__ import annotations

from just_dna_compiler.hints import Alteration, Finding
from just_dna_enricher.lookup import CitationHint

from just_module_creator.settings import Settings
from just_module_creator.tools import research

DOI = "10.1038/ng826"
PMID = "11788828"
TITLE = "Identification of a variant associated with adult-type hypolactasia."


def _online() -> Settings:
    return Settings(offline=False, api_key=None, _env_file=None)  # type: ignore[call-arg]


def _upstream_names_the_work(monkeypatch) -> None:
    """What enricher 0.8 answers for a bare DOI with one Europe PMC match."""

    def lookup_citation(*, pmid, doi, offline, clients):
        hint = CitationHint(pmid=pmid, doi=doi, doi_exists=True, pmid_exists=True, title=TITLE)
        hint.alterations.append(
            Alteration(
                row=0,
                column="pmid",
                before="",
                after=PMID,
                kind="advisory",
                applied=False,
                source="europepmc",
                refusal="redundancy_bearing",
            )
        )
        hint.findings.append(Finding(None, None, "info", f"PMID {PMID} names: {TITLE!r}"))
        return hint

    monkeypatch.setattr(research.enricher_lookup, "lookup_citation", lookup_citation)


async def test_a_bare_doi_names_the_work_and_offers_its_pmid_without_filling_it(
    make_client, monkeypatch
) -> None:
    _upstream_names_the_work(monkeypatch)
    async with make_client(_online()) as client:
        data = (await client.call_tool("lookup_citation", {"doi": DOI})).data

    assert data.title == TITLE
    assert data.pmid is None, "a PMID read off the DOI's record is never filled"
    offered = [w for w in data.withheld if w.column == "pmid"]
    assert len(offered) == 1
    assert (offered[0].after, offered[0].applied) == (PMID, False)
    # The enricher answered; nothing of ours speaks for it any more.
    assert not [f for f in data.findings if f.source == "just-module-creator"]
