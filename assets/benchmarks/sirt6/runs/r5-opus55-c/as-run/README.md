# SIRT6 rs117385980 and longevity (Sheikholmolouki 2025)

This module records one variant, **SIRT6 rs117385980** (GRCh38 chr19:4180588 C>T), from
[Sheikholmolouki et al., Scientific Reports 15:40251 (2025)](https://doi.org/10.1038/s41598-025-24018-3),
PMID 41249831, PMC12624115. That exploratory study genotyped 227 adults aged 60–90 from
the Birjand Longitudinal Aging Study (Iran) and compared the variant across frailty
groups and age groups. The study it builds on,
[Hirvonen et al., BMC Medical Genetics 18:41 (2017)](https://doi.org/10.1186/s12881-017-0401-z)
(PMID 28399814), is included as a second study row. Its figures come from the PubMed
abstract.

**Bottom line: none of the evidence is statistically significant.** Both studies point
the same way: the T allele is rarer in people who reach old age. Each study had 8–12 T
carriers in total, and both P-values sit around 0.07. The frailty association, which is
the paper's primary hypothesis, is null (P = 0.36). It also runs against the longevity
direction: no frail participant carried T.

## Contents

| Table | Rows | Notes |
|---|---|---|
| weights / annotations | 3 | C/C `neutral`; C/T and T/T `risk`, all `not_significant`. **No numeric weights.** Do not sum into a score. |
| studies | 4 | Paper: frailty allelic test, frailty adjusted logistic model, age-group test. Hirvonen 2017: long-lived vs early death. |
| literature | 2 | Both open access (CC BY-NC-ND 4.0 and CC BY 4.0). |
| sources | 6 | Ensembl, ClinVar (no record), ClinGen Allele Registry, both papers, PubMed. |
| clin_sig_* | 0 | The variant has no ClinVar record. |

Traits: longevity is `OBA_VT0005372` (life span determination trait). The term most
modules use, `EFO_0004300`, is obsolete in EFO and points here. Frailty is
`EFO_0009885` (frailty measurement).

Outcome flags: `outcome_lifespan` and `outcome_healthspan` are true. Survival to older
age and frailty were both studied. `outcome_exceptional` is false, because no
centenarian or nonagenarian data exist. `eur_only_evidence` is false: one study is
Iranian and one is Finnish.

## The T/T row

T/T was never observed, in 0 of 227 Iranian and 0 of 198 Finnish participants. That is
consistent with a T allele frequency of 0.5–3.5% (gnomAD v4 genomes). The T/T `risk`
label only extends the heterozygote direction under an additive assumption. The row
says this explicitly.

## Corrections to the source paper (verified independently)

1. **The paper calls the variant "a stop gained variant within the exon 2". It is
   intronic.** Ensembl VEP (release 116) calls it `intron_variant` on every SIRT6
   transcript. ClinGen CA15948970 gives NM_016539.4:c.194+194G>A. Hirvonen 2017 itself
   describes it as "23 bases downstream of the exon 2 exon/intron border". The module
   text does not repeat the stop-gain claim.
2. **The allele is placed by reproducing the paper's own assay.** In-silico PCR on
   GRCh38 with the paper's primers gives the stated 661 bp amplicon. The HaeIII digest
   gives exactly 43/161/216/241 bp for C and 43/216/402 bp for T. So the paper's
   "C>T" is the plus-strand GRCh38 ref>alt, and there is no strand ambiguity.
3. **The pairwise age-group P-values are one-sided.** The paper reports 0.08, 0.06 and
   0.37, which match one-sided Fisher tests (0.086, 0.070, 0.373). The two-sided values
   are 0.086, 0.12 and 0.58. The 3-group P = 0.073 and the frailty P = 0.36 reproduce
   exactly.
4. **Several reported ORs cannot be reproduced:**
   - The frailty OR of 1.4 (Table 3) and the logistic ORs of 1.42 → 0.96 (Table 6)
     can't come from the published counts. The frail group has zero T alleles, so the
     OR is undefined, and a finite logistic estimate with those confidence intervals
     should not be estimable.
   - The 70–79 vs 80–90 OR of 3.9 could not be reproduced either. The
     Haldane-corrected value is 8.8.

   The Table 6 numbers are kept in one studies row with this caveat. No OR is used for
   the Table 3 row.
5. **The paper misquotes Hirvonen's long-lived count as 1/42. The abstract says 1/43.**
6. Minor: Table 1 prints hypertensive pre-frail participants as "87 (0.58)" where it
   should be 58%, and Table 2 percentages are of the total sample, not of each group.

## Caveats for anyone reusing this

- **Candidate-gene evidence, tiny numbers.** The Iranian study saw 8 heterozygotes in
  227 people; the Finnish study saw 12 in 198. Neither found a significant result, and
  the GWAS Catalog has no association for rs117385980 (REST v2, checked 2026-11-26).
- **Weak survival proxy.** "Longevity" in the 2025 paper means age at a single
  baseline visit. There is no follow-up or mortality data, so the comparison is
  exposed to cohort and survivor effects.
- **Men only in Hirvonen.**
- **No functional evidence.** No study shows rs117385980 changes SIRT6 expression or
  function. The SIRT6 biology in the paper's discussion (DNA repair, mouse lifespan) is
  about the gene, not this variant.
- **Other SIRT6 variants are out of scope.** The paper's discussion cites rs107251
  (TenNapel 2014), rs350846 (You 2016) and five null SNPs (Lin 2016). They are not
  authored here, because they would need their own primary-paper review.

## Licensing

The 2025 article is **CC BY-NC-NoDerivatives 4.0**. Only short verbatim
`provenance_quote` strings are reproduced, and they were checked character-for-character
against the full text. All conclusions are newly written. The source row is marked
`commercial_use = false` and `declared_use = non_commercial`. Whether quoting under an
ND licence is acceptable for your distribution channel should be confirmed before
commercial use. Hirvonen 2017 is CC BY 4.0.

## Provenance and method

AI-authored (Claude, claude-opus-5-5), 2026-11-26, from the user-supplied full text.
Authored inputs are in `../src/`, and `../scripts/build.py` compiles them into these
parquets. The output schemas are cast to snapshots of published example modules.

| Item | How it was checked |
|---|---|
| PMIDs, DOIs, PMCIDs | PubMed E-utilities and Europe PMC |
| Licences | Europe PMC |
| Coordinates and consequence | Ensembl REST, release 116 |
| Canonical allele id | ClinGen Allele Registry |
| ClinVar status | E-utilities (no record) |
| VRS 2.0 ids | Computed by a hand-written digest (`../scripts/vrs.py`). Validated against a published example's ids. The chr19 refget accession was computed from the full Ensembl chr19 sequence. |
| Statistics | Recomputed from the published counts (`../scripts/recompute_stats.py`) |

Research and informational use only. Not a diagnostic or prognostic test.
