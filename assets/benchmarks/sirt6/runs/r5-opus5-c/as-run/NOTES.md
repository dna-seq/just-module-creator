# Verification log — `longevity_sirt6`

Every external fact in the module, what it was checked against, and the
verdict. Checks run 2026-11-26.

## Layout

```
longevity_sirt6/   compiled module: 7 parquet tables + README.md   <- the deliverable
source/            authoring layer: 7 CSVs
build/authored.py  single source of truth for all authored content
build/compile.py   CSV + parquet writer; asserts schema conformance against examples-c
build/validate.py  post-build consistency, licence and arithmetic checks
NOTES.md           this file
```

Rebuild: `python build/compile.py && python build/validate.py`.

## The central finding: rs117385980 is intronic, not stop-gained

The focal article (PMID 41249831) calls rs117385980 "a stop gained variant
within the exon 2 of SIRT6 gene". Checked five ways; all disagree with the
article and agree with each other.

| Check | Source | Result |
|---|---|---|
| Canonical HGVS | ClinGen Allele Registry, `?hgvs=NC_000019.10:g.4180588C>T` | `CA15948970`, `NM_016539.4(SIRT6):c.194+194G>A` |
| Transcript consequence | Ensembl REST `/vep/human/id/rs117385980` | `intron_variant` on 28 of 30 *SIRT6* transcripts incl. MANE Select ENST00000337491 / NM_016539.4; the remaining two place it up/downstream |
| Exon arithmetic | Ensembl REST `/lookup/id/ENST00000337491?expand=1` | exon 2 = chr19:4,180,782–4,180,909; variant at 4,180,588 is 194 bp away, matching `c.194+194` |
| Repeat context | Ensembl REST `/overlap/region/19:4180580-4180600?feature=repeat` | inside **AluSx4**, chr19:4,180,385–4,180,624, minus strand |
| Origin of the error | NCBI eutils `esummary db=snp id=117385980` | `fxn_class = coding_sequence_variant,stop_gained,intron_variant`; the only transcript HGVS offered is `XM_024451539.2:c.114G>A` / `XP_024307307.1:p.Trp38Ter` — a Gnomon-predicted RefSeq model, no curated `NM_` |

The `p.Trp38Ter` prediction is internally correct for that model: *SIRT6* is on
the minus strand, so plus-strand bases 4,180,590/4,180,589/4,180,588 = A/C/C
read as TGG (Trp) on the transcript, and the plus-strand T allele makes TGA
(stop). Verified directly against the GRCh38 sequence fetched from Ensembl.
The problem is the exon, not the codon.

Hirvonen 2017, the original report, says "situated 23 bases downstream of the
exon/intron border of exon 2" and types it `intron variant` in both tables.
The "23 bases" was also checked and is traceable: scanning all 48 distinct exon
intervals in chr19:4,174,000–4,183,000 found that ENST00000594341
(retained_intron) carries an extended exon 2 ending at chr19:4,180,612 — 23
intronic bases from the variant. Nothing places it 194 bp *and* in an exon.

## The genotyping assay, reproduced in silico

Fetched chr19:4,173,000–4,186,000 from Ensembl REST and ran the focal article's
published PCR-RFLP design against it.

| Published | Computed | Match |
|---|---|---|
| Amplicon 661 bp | primers map to chr19:4,180,347–4,181,007 = 661 bp | exact |
| C allele → 43, 161, 216, 241 bp | HaeIII `GG^CC` cuts at amplicon offsets 241/402/618 → 43, 161, 216, 241 | exact |
| T allele → 43, 216, 402 bp | C>T destroys the `GGCC` at 4,180,586–4,180,589 → 43, 216, 402 | exact |

Additional checks not in the paper:
- The forward primer `CTCAGGCAAGACAGGGACAG` is **identical** to Hirvonen 2017's
  forward primer; the reverse primer differs (Hirvonen used
  `TTAACGAACTTGGACCCTCC`).
- Specificity was tested exhaustively, not by spot check: all 661 positions x
  3 substitutions were simulated. 51 positions can alter the fragment pattern.
  The only common variant at any of them is rs117385980. rs7260071 (AF 0.27)
  and rs352493 (AF 0.08), the other two common variants inside the amplicon,
  leave the pattern unchanged. The remaining sensitive positions carry only
  singleton-level dbSNP entries with no frequency data.
  This check is re-run by `build/rflp_check.py` against a committed copy of the
  reference window, so it fails the build if anything drifts.
- Both primers lie outside the AluSx4 element in unique flanking sequence;
  240 bp of the amplicon, including the variant, lies inside it.

Conclusion: the assay is correctly designed and the published gel sizes are
right. The disagreement with the paper is only about what the position is.

## Placements, HGVS and allele registry identifiers

All 14 variants. `chrom/start/ref/alts` from Ensembl REST
`/variation/human/{rs}`; reference bases independently confirmed by reading the
fetched GRCh38 sequence at each coordinate; `caid` and MANE HGVS from the
ClinGen Allele Registry.

| rsid | GRCh38 | ref>alt | CAID | MANE HGVS | Gene |
|---|---|---|---|---|---|
| rs117385980 | 19:4180588 | C>T | CA15948970 | `NM_016539.4:c.194+194G>A` | SIRT6 |
| rs107251 | 19:4176088 | T>C | CA14695556 | `NM_016539.4:c.438-151A>G` | SIRT6 |
| rs350846 | 19:4174401 | C>G | CA14695555 | `NM_016539.4:c.*216G>C` | SIRT6 |
| rs352493 | 19:4180839 | C>T | CA9092052 | `NM_016539.4:c.137G>A (p.Ser46Asn)` | SIRT6 |
| rs350844 | 19:4177054 | A>G | CA9091921 | `NM_016539.4:c.437+25T>C` | SIRT6 |
| rs4807546 | 19:4182063 | T>C | CA14695558 | `NM_016539.4:c.66+411A>G` | SIRT6 |
| rs192661013 | 19:4174661 | G>C | CA9091717 | `NM_016539.4:c.1024C>G (p.His342Asp)` | SIRT6 |
| rs350845 | 19:4174953 | A>G | CA9091776 | `NM_016539.4:c.739-7T>C` | SIRT6 |
| rs352491 | 19:4177025 | G>A | CA304472042 | `NM_016539.4:c.437+54C>T` | SIRT6 |
| rs11554579 | 19:4179253 | T>C | CA9092010 | `NM_016539.4:c.228A>G (p.Arg76=)` | SIRT6 |
| rs7260071 | 19:4180693 | T>C | CA2319267551 | `NM_016539.4:c.194+89A>G` | SIRT6 |
| rs117833511 | 19:4180315 | C>T | CA15948059 | `NM_016539.4:c.194+467G>A` | SIRT6 |
| rs3760905 | 19:4182942 | G>T | CA14695559 | `NM_001393985.1:c.-37+202G>T` | **ANKRD24** |
| rs350852 | 19:4170001 | G>A | CA14695550 | `NM_032607.3:c.822-139G>A` | **CREB3L3** |

Hirvonen 2017's Table 1 positions match GRCh38 exactly for all eight of its
variants, confirming that paper used GRCh38 coordinates.

No allele has a ClinVar record (checked via the Allele Registry
`externalRecords` payload for each) except rs350852, which is not in *SIRT6*
and is not annotated here. Hence the two empty `clin_sig_*` tables.

## Errors found in the sources

| Source | Claim | Verdict |
|---|---|---|
| PMID 41249831 | rs117385980 is "stop gained ... within the exon 2" | **Wrong.** Intronic, `c.194+194G>A`. See above. |
| PMID 41249831 | Hirvonen found T in "1/42 long-lived men (aged 77+)" | **Wrong.** Hirvonen: 1/43. "77+" appears to be a misread of Hirvonen's note that Finnish male life expectancy is 77.5 y; the replication group had mean age 83. |
| PMID 41249831 | rs350846 "C allele ... associated with longevity" | **Inverted.** You/Li's Table 4: C is 28.7 % in the long-lived vs 38.6 % in external controls, OR 0.639. Repeats You/Li's own mis-stated conclusion. |
| PMID 41249831 | TenNapel studied "1192 participants from four groups" | n=1,192 is right; it is one cohort (Iowa 65+RHS), not four groups. |
| PMID 41249831 | Table 3 OR 1.4; 70–79 vs 80–90 OR 3.9 | **Not estimable.** Both have a zero cell → complete separation; no finite unpenalised OR exists, and the outcome coding is unstated. Recorded with the caveat, not propagated. |
| PMID 41249831 | sex difference p=0.87 (Discussion) | Table 5 gives Fisher p=1.00, χ² p=0.84/0.85 for the same test. Not used. |
| PMID 41249831 | Table 1, hypertensive pre-frail "87 (0.58)" | Typo for 58 %. Cosmetic; not used. |
| PMID 28399814 | Table 1 types rs11554579 as "missense" | **Wrong.** `c.228A>G` = `p.Arg76=`, synonymous (Ensembl VEP and ClinGen agree). |
| PMID 28399814 | Table 1 types rs7260071 "non coding transcript exon variant" | **Reclassified.** Intronic on all current transcripts, `c.194+89A>G`. |
| PMID 28399814 | Abstract OR 3.53 vs Results/Table 2 OR 3.58 | Internal inconsistency. Tabulated 3.58 used. |
| PMID 28399814 | Finnish T frequency 0.056 (1000 Genomes) | Correct for 1000G's 98 Finns; gnomAD v4's 10,618 Finnish alleles give 0.027. |
| PMID 28032059 | Abstract: "C allele ... associated with longevity" | Contradicted by its own Table 4; the two control groups differ from each other at p=0.003. |
| PMID 26802595 (via 41249831) | five "*SIRT6*" SNPs | Two are not in *SIRT6*: rs3760905 is in ANKRD24, rs350852 in CREB3L3. |

## Linkage disequilibrium

Ensembl REST `/ld/human/rs117385980/1000GENOMES:phase_3:EUR` (r² ≥ 0.2, 100 kb):
31 pairs. Key values in `source/ld.csv`.

- rs117833511 r²=1.000 D′=1.000 — perfect proxy, used as `proxy_rsid`.
- rs192661013 (p.His342Asp) r²=0.571 D′=1.000 — the only coding candidate.
- rs107251, rs350846, rs350844, rs350845, rs4807546 all r²≈0.301 D′=1.000.
- rs7260071 and rs352493: r² < 0.2, not in LD.

D′ = 1.00 throughout means the rare rs117385980-T allele sits wholly on one
haplotype background; r² is held down only by the frequency gap. This is the
basis for the README's claim that the three published associations may be one
signal.

## Frequencies

gnomAD v4.1 GraphQL API, genome callset. Full table for rs117385980 in
`source/frequencies.csv`. Exome callset gives 0.0232 global against 0.0181 for
genomes, consistent with exome capture bias near an exon boundary.

Two orientation traps found, both recorded in the affected `conclusion` text
and in `flags` as `reference_allele_is_minor`:

- **rs107251**: GRCh38 reference base is **T**, and T is the global minor
  allele (0.116). TenNapel's adverse "minor allele T/T" genotype is the
  homozygous *reference* genotype.
- **rs350846**: GRCh38 reference base is **C**, the global minor allele
  (0.112; 0.30 in East Asians, matching You/Li's observed 0.319).

Also: rs117385980 is absent from East Asians (0/5,182 alleles), so the Chinese
rs350846 cohort cannot be carrying the same haplotype signal.

## Arithmetic reproduced from the focal paper

`build/validate.py` recomputes and asserts, so these fail the build if touched:

- All ten minor-allele frequencies in the paper's Table 2 from its heterozygote
  counts (max deviation 0.0006, i.e. rounding only). The paper's MAF column is
  internally consistent.
- Hardy–Weinberg for the full Birjand sample: 7.85 heterozygotes expected at
  q=8/454, 8 observed. The paper's HWE claim holds.
- Expected T/T count: 0.14 across all 425 people in the three cohorts at
  gnomAD AF 0.0181. Observing zero T/T is exactly what should happen; the
  paper's T/T genotype category was never going to be populated.

## Literature and licences

NCBI eutils `esearch`/`esummary` for PMIDs; Europe PMC `search?resultType=core`
for PMCIDs, open-access status and licence strings; full text pulled from
Europe PMC `fullTextXML` for the two CC BY sources.

| PMID | Licence | Full text read | Quotes authored |
|---|---|---|---|
| 41249831 Sheikholmolouki 2025 | CC BY-NC-ND 4.0 | supplied by user | 0 |
| 28399814 Hirvonen 2017 | CC BY | yes (PMC5387321) | 2 |
| 25541994 TenNapel 2014 | CC BY | yes (PMC4277407) | 1 |
| 28032059 You/Li 2016 | CC BY-NC 3.0 | yes (PMC5182250) | 0 |
| 26802595 Lin 2016 | unknown, closed | **no** | 0 |
| 37754211 Zhu 2023 | CC BY-NC-ND 4.0 | no | 0 |
| 32550207 Moodi 2020 (BLAS) | not OA | no | 0 |
| 34050173 Roichman 2021 | CC BY | no | 0 |
| 29555651 Ferrer 2018 | closed | no | 0 |

You/Li 2016 has no DOI indexed by Europe PMC or Crossref; `doi_exists` is false
for that row rather than a DOI being invented.

Licence policy, enforced by `build/validate.py`: a `provenance_quote` may only
be authored from a source whose `literature` row has
`commercial_use AND redistribution`. Both NC sources therefore contribute facts
only, and the module's own text carries no NC or ND encumbrance.

## Trait ontology

- `OBA:VT0005372` "life span determination trait" — used for longevity.
  `EFO:0004300` "longevity" was **obsoleted in EFO 3.74.0** with
  `term replaced by: OBA:VT0005372`; checked via EBI OLS4.
- `EFO:0005056` "age at death" — TenNapel's actual outcome variable.
- `EFO:0009885` "frailty measurement" — the frailty study rows.

`build/validate.py` rejects any trait id outside this verified set.

## Known gaps

1. **No VRS 2.0 identifiers.** `vrs_id`/`vrs_spec` are null. A `ga4gh:VA`
   digest requires the GA4GH VRS serialisation and a refget sequence digest;
   the library was unavailable and hand-rolling the digest risked publishing a
   wrong identifier. CAIDs are supplied instead. The reference modules populate
   `vrs_id` from an enrichment step this curator could not run.
2. **Lin 2016 not read.** The largest and best-powered study in the module
   (n=1,462) is closed access. Its five rows carry secondary provenance from
   the focal article's description and no per-SNP statistics. If the module is
   published, this is the first thing to fix.
3. **Field semantics guessed nowhere, left null instead.** `requires_callable`,
   `callable_from`, `quality_from`, `min_quality` and `priority` are null
   throughout. Their intended semantics were not documented to this curator and
   both reference modules leave them null. The genuine calling caveat for a
   rare variant inside an Alu is carried in `flags`
   (`alu_embedded_check_call_quality`, `rare_allele_maf_0.018`) and in the
   README prose instead.
4. **The 1.4 / 3.9 odds ratios are unresolved, not reconciled.** They are
   recorded as published with an explanation of why they cannot be reproduced.
   Resolving them needs the authors' analysis code or the individual-level
   data, which the paper states are not available.
5. **No supplementary material.** The paper directory contained only
   `paper.md`; no supplementary tables were available to cross-check Tables 1–6.
