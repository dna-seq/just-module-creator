"""F136: `lookup_variant` states PubMind's withheld `clin_sig` once, not once per record.

Upstream writes one advisory per PubMind record, each repeating one reason, while every
record is already whole in `pubmind`. The tester's rs1801131 answer carried 29 of them.
"""

from __future__ import annotations

from typing import Any

from conftest import offline_settings
from just_dna_compiler.hints import Alteration
from just_dna_enricher.lookup import VariantHint

from just_module_creator.tools import research

_NOTE = (
    "PubMind {pvid}: an LLM's reading of the literature (confidence high, derivation text). "
    "Yours is cross-examined against it, so filling it from here would have the check agree "
    "with the source it is checking"
)


def _advisory(column: str, value: str, source: str, note: str) -> Alteration:
    return Alteration(
        row=0,
        column=column,
        before="",
        after=value,
        kind="advisory",
        applied=False,
        source=source,
        refusal="redundancy_bearing",
        note=note,
    )


def _hint(pvids: list[tuple[str, str]]) -> VariantHint:
    hint = VariantHint(rsid="rs1801131")
    hint.loci = [{"chrom": "1", "start": 11794419, "ref": "T", "alts": "G"}]
    hint.pubmind = [{"pvid": pvid, "clin_sig": call} for pvid, call in pvids]
    hint.alterations = [
        _advisory("chrom", "1", "ensembl", "the coordinate is yours to author"),
        *(_advisory("clin_sig", call, "pubmind", _NOTE.format(pvid=pvid)) for pvid, call in pvids),
    ]
    return hint


async def _lookup(monkeypatch, make_client, hint: VariantHint) -> Any:
    monkeypatch.setattr(research.enricher_lookup, "lookup_variant", lambda **_: hint)
    async with make_client(offline_settings()) as client:
        return (await client.call_tool("lookup_variant", {"rsid": "rs1801131"})).data


async def test_pubmind_advisories_collapse_to_one_with_the_count_and_calls(
    monkeypatch, make_client
):
    records = [("PV1", "Benign"), ("PV2", "Pathogenic"), ("PV3", "Benign")]
    data = await _lookup(monkeypatch, make_client, _hint(records))

    assert len(data.pubmind) == 3, "every record stays whole in `pubmind`"
    pubmind = [a for a in data.withheld if a.source == "pubmind"]
    assert len(pubmind) == 1
    only = pubmind[0]
    # Upstream's reason is kept verbatim, from the first record.
    assert only.note.startswith(_NOTE.format(pvid="PV1"))
    assert only.refusal == "redundancy_bearing" and only.applied is False
    assert "2 more PubMind advisories" in only.note
    assert "calls across all 3: Benign (2), Pathogenic (1)" in only.note
    # Other withheld cells are untouched, and keep their order.
    assert [a.source for a in data.withheld] == ["ensembl", "pubmind"]


async def test_one_pubmind_advisory_is_left_as_upstream_wrote_it(monkeypatch, make_client):
    data = await _lookup(monkeypatch, make_client, _hint([("PV1", "Benign")]))

    pubmind = [a for a in data.withheld if a.source == "pubmind"]
    assert len(pubmind) == 1
    assert pubmind[0].note == _NOTE.format(pvid="PV1")
