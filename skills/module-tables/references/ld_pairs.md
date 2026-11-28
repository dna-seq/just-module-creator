# ld_pairs.csv — how well a study's proxy stands in for the variant the row is about

> **Written 2026-11-28 against format 0.9.0 / compiler 0.9.0 / enricher 0.9.0 / registry client
> 0.35.0, read from the installed code.** The table landed in format 0.8 (upstream `RM331`). Anchor on
> symbol names: `ld_pairs.LdPairRow`, `ld_pairs.enrich_ld_pairs` in the enricher, `StudyRow.proxy_rsid`,
> `licensing.ENSEMBL_TERMS`. Never on `file:line`.
>
> **Columns, types, requiredness and the `status` vocabulary are generated upstream**, at
> <https://just-dna.life/just-dna-compiler/tables/ld_pairs/>, and live in-session from
> `describe_machine_table("ld_pairs.csv")`. This file keeps who decides which cell, what a re-run moves,
> and the symptom when the table is wrong.

## In one paragraph

Some studies did not genotype the variant a `studies.csv` row is filed under. They measured a nearby
**proxy** in linkage disequilibrium with it. The author records that with one authored cell,
`StudyRow.proxy_rsid`, and nothing else: r² means nothing without the population it was computed in,
so upstream decided the number is computed from a reference panel and never typed. This table is that
computation. One row is one `(proxy, lead, panel)`: r² and D′ between the proxy and the row's lead in
the study's own superpopulation, or the reason no number was given.

## Identity card

| | |
|---|---|
| Model | `just_dna_format.ld_pairs.LdPairRow`, `extra="forbid"` |
| One row is | one study row's proxy/lead pair in one reference panel |
| Natural key | run `hints.key_fields("ld_pairs.csv")` |
| Becomes | `ld_pairs.parquet`, in `compiler.ARTIFACT_PARQUETS` |
| Machine-produced | yes; written by `just-dna-enricher ld-pairs`, which no tool runs on this machine |
| Fact signature | `integrity.ld_pair_signature` over `LD_PAIR_FACT_FIELDS`; `answered_rsid`, `source` and `fetched_at` are outside |
| Overlayable | **no.** `ld_pairs.csv` is not in `overrides.VALID_OVERRIDE_TABLES` |
| Compiler cross-check | **none** on this table (`_no_checks`) |
| Manifest | `manifest.ld_pairs`, an `LdPairs` block: signature, datasets, populations, `row_count`, `with_r2` |

## Who decides which cell

- **The author decides the inputs, on `studies.csv`**: `proxy_rsid` (which variant the study
  measured) and `ancestry` (whose panel the pair is asked in). Those two cells are the whole of the
  authored surface. Getting the proxy from the paper is evidence work; see `find-evidence`.
  `describe_table("studies.csv")` says what each cell holds.
- **The pass fills every cell here**, from Ensembl REST's pairwise LD endpoint over the 1000 Genomes
  phase 3 superpopulations. `ld_population` is the panel's own name (`1000GENOMES:phase_3:EUR`), not
  the study's code, so a different reference would be a different key rather than the same word.
- **One superpopulation or nothing.** A study naming several, or none, gets its row with no population
  and no number, and `status` says which (`ancestry_mixed`, `ancestry_unstated`). The pass never picks
  a panel for a mixed study, and neither should an agent.
- **The lead's rsID** is the study row's own, else the one `resolution.csv` (after overrides) placed at
  the row's coordinate. A place two rows resolve to different rsIDs is left out rather than guessed. With
  neither, the row says `lead_has_no_rsid`: the endpoint only takes rsIDs.
- **`answered_rsid` is the reference's current name** when dbSNP merged the author's id (upstream's
  probe: rs1624712 answers as rs646776). The row stays keyed on what the author wrote.
- **Whether the proxy is good enough is a pilot's call.** No threshold lives in the format or here. A
  low r², or no number at all, says the study's effect may not transfer to the lead; whether the study
  row stays, and how its conclusion is worded, goes in front of the author.

## Withheld is a status, never a zero

`r2` is set exactly when `status` is `resolved`, and the model refuses any other combination. An empty
answer from the reference is `not_reported`: Ensembl returns the same empty answer for a pair below its
reporting floor and for two variants on different chromosomes, so it cannot mean r² = 0. A pair the
reference does not know is `rsid_unknown`. Read `manifest.ld_pairs.with_r2` beside `row_count`; the two
differ by design.

## Running it

**No tool here runs this pass on the author's machine**; `cli_map` records it as a parity gap. It is
**online only**: there is no LD snapshot, so `--offline` asks nothing and writes nothing.

```
uv run just-dna-enricher ld-pairs <spec-dir>
remote_derive(spec_dir, namespace, name, target="test", passes=["ld-pairs"], live=True)
```

On a registry the pass needs `live=True`, because with only snapshots to answer from it is skipped. That
route **uploads the authored spec**, and the live leg is charged to your registry account per Ensembl
request, so it is the author's call. **Licence:** a `licensing.csv` row for source `ensembl` at layer `ld_pair`, terms from
`licensing.ENSEMBL_TERMS` (Apache-2.0, commercial use and redistribution permitted), written only when
Ensembl actually answered that run. A run that wrote only withheld rows consulted no source and adds none.

## What a re-run moves, and how to correct a row

- **A pair already in the file is never asked again.** To pick up a newer Ensembl release, delete the
  file and re-run. `refresh_sidecar` refuses this table and names the CLI; copy the file out of the spec
  directory before deleting it ([`module-refresh`](../../module-refresh/GUIDE.md)).
- **A pair no study row names any more is dropped**, with a warning. So editing a study's `proxy_rsid`
  or `ancestry` and re-running removes the old row and asks the new pair. That is the correction route.
- **An outage commits what was answered.** If Ensembl stays down past the retries, the pairs answered
  this run are written and the rest are named; a re-run asks only those.
- **There is no overlay.** Upstream left this table out of `overrides.csv`, so a hand-edited row has no
  sanctioned form: nothing logs it, the fact hash cannot tell it from Ensembl's answer (`source` is
  outside the hash), and deleting the file to re-ask loses it. Correct the authored input on
  [`studies.csv`](studies.md) instead, log the edit with `record_override`, and re-run.

## How it relates to the rest of the module

- **Resolution.** `enrich_module` resolves each study's proxy as well as its lead, so `resolution.csv`
  carries proxy rows on purpose; the compiler does not report them as orphans. See
  [`resolution.md`](resolution.md).
- **Alleles.** When `proxy_rsid` is set, the study's `effect_allele` is an allele of the proxy, and the
  compiler checks it against the proxy's alleles, not the lead's.
- **No other table joins it.** The compiler reads it into the manifest and the parquet and checks
  nothing between it and `studies.csv`. A row whose study was edited without a re-run compiles green.

## Ask the live schema

```
describe_machine_table("ld_pairs.csv")      # columns and the status vocabulary
describe_table("studies.csv")               # proxy_rsid and ancestry, the two cells you author
```
