# SIRT6 rs117385980 and longevity

One SIRT6 variant, two studies, and a trend that has never reached statistical significance.

## What this module says

`rs117385980` (chr19:4180588, C>T, GRCh38) is a rare SIRT6 variant. Two candidate-gene
case-control studies have looked at it, in two unrelated populations, and both found the
minor **T allele under-represented among the longest-lived** — at p = 0.074 and p = 0.073
respectively. Neither is significant. The module records that trend, hedged, and nothing
stronger.

| Genotype | State | Weight | Basis |
|---|---|---|---|
| C/C | neutral | 0 | The common genotype. No positive claim is made for it. |
| C/T | risk | -0.1 | Two concordant but non-significant trends. |

## What this module does NOT say

- **It does not say the T allele shortens your life.** Two under-powered studies pointing the
  same way is a reason to look again, not a finding. Hirvonen et al. report their own power as
  28.4%.
- **There is no T/T row.** Neither cohort observed a single T/T homozygote — 8 heterozygotes in
  227 Iranians, 12 in 198 Finnish men, and no homozygotes in either. gnomAD does record 183
  homozygotes globally (allele frequency ~0.022), so T/T people exist; no study has measured
  them. A consumer whose genome is T/T will get no row from this module, and that is the
  honest outcome rather than an omission to fix.
- **It is not about frailty**, even though the 2025 paper's primary outcome was. That analysis
  was null in every model (final adjusted OR 0.96, 95% CI 0.10–9.66, p = 0.98) and is recorded
  in `studies.csv` as such.

## Ancestry

Both studies are ancestry-specific and neither is broadly generalisable:

- Hirvonen 2017 — **Finnish men only.** No women were studied. gnomAD puts the T allele at
  2.4% in Finnish and 2.7% in non-Finnish European samples.
- Sheikholmolouki 2025 — **Iranian adults aged 60–90** from one county (Birjand).

gnomAD frequency varies by two orders of magnitude across populations (East Asian 0.003%,
African/African-American 0.47%, Ashkenazi Jewish 3.4%). Nothing here has been tested outside
European and Iranian samples.

## Provenance and quotes

Both `provenance_quote` values were **located by an agent (`claude-opus-5`) reading the full
text** retrieved through Europe PMC, and `curator` records that on each row. The human author
holds responsibility for them regardless.

One consequence, stated rather than hidden: because those same full texts are what
`enrich_literature_pass` checks the quotes against, `quotes_found` on these rows is a
**citation-pairing check** — it confirms the passage belongs to the PMID it is filed under —
and is *not* independent evidence that the claim appears in the literature.

## Licensing — read this before selling anything

Sheikholmolouki 2025 is **CC BY-NC-ND 4.0**. The quoted passage is a verbatim quotation with
attribution, which that licence permits as reproduction; adapted reuse is not permitted. The
consequence is recorded rather than routed around: **this module's `commercial_use` is false.**
Hirvonen 2017 is CC BY 4.0 and imposes nothing.

The compile emits `module declares license 'CC-BY-NC-ND-4.0' but annotation-layer sources report
['CC-BY-4.0']`. That is the **conservative** direction and is intended: the module declares the
more restrictive of its two sources' licences, because the NC-ND article's terms govern the
combined work. The warning cannot tell a deliberately conservative declaration from an
incompatible one, so it is recorded here rather than cleared.

## Decisions still open — for a human

1. **`authorship` names only an AI.** A human author must add themselves before this is
   published anywhere. Responsibility does not sit with the model.
2. **The two papers disagree about what this variant *is*.** Hirvonen 2017 calls it an
   "intron variant" 23 bases downstream of the exon 2 boundary; Sheikholmolouki 2025 calls it
   "a stop gained variant within the exon 2 of SIRT6". Both cannot be right, and the molecular
   consequence changes how seriously the association should be taken. Ensembl returned no
   ClinVar significance for it. Unresolved here; `clin_sig` is deliberately empty.
3. **`state` = risk on C/T is a judgement call.** The vocabulary offers no "suggestive" state,
   so the hedge lives in `stat_significance` and the conclusion text. A curator who thinks
   p = 0.07 does not earn "risk" should change it to `neutral`; the case for either is in the
   conclusion.
4. **Hirvonen's own numbers disagree internally.** The abstract says OR 3.53; the results text
   and Table 2 both say 3.58. The module carries 3.58. Worth a note to the authors.
5. **Second-pass candidates, deliberately not included.** The 2025 discussion names three other
   SIRT6 longevity variants — `rs107251` (TenNapel 2014, Iowa, >5-year survival difference),
   `rs350846` (You 2016, Bama County China) — and one null study of five further SNPs (Lin 2016,
   Hainan). None was read for this module and none was authored from a summary. Adding them is
   a real second pass, not a fill-in.
6. **`weight` = -0.1 is arbitrary.** See `weighting:` in the spec. It encodes confidence, not
   effect size.
7. **Four of eleven recorded checks compared nothing, and that is not four passes.**
   `audit_module` flags this and it is worth reading rather than clearing:
   - `clinical_significance` ran over **0 subjects and gives no reason**, so in the raw record it
     looks exactly like a clean check. It is not: no row here authors a `clin_sig`, and Ensembl
     returns no ClinVar significance for this variant at all. `clin_sig` is deliberately left
     empty — filling it from ClinVar is precisely the fill-from-the-checking-source move that
     would make the check compare a source with itself.
   - `citation_identifier` did not run because neither study row authors a DOI. That is also
     deliberate: `doi` is compared against the registry's own, so authoring it from the search
     result that supplied the PMID would make that check vacuous. The DOIs are recorded in
     `literature.csv` regardless.
   - `genome_build_agreement` and `rsid_coordinate_agreement` did not run because the rows are
     rsID-only and author no coordinate. The coordinate was verified by hand against Hirvonen
     et al., who print `19:4180588` in their Results — the same position `resolution.csv`
     resolved to independently.

## What was checked, and what that check is worth

| Check | Result | What it actually establishes |
|---|---|---|
| rsID currency (dbSNP) | live | The rsID has not been merged or withdrawn. |
| Reference allele (SeqRepo) | 1/1, no mismatch | `start` is not off by one. |
| Gene symbol (HGNC) | SIRT6 approved | Current symbol. |
| Gene/locus agreement | 2/2 agree | The gene and the variant are on the same chromosome. |
| Trait CURIE (OLS4) | current | `OBA_VT0005372` is live. `EFO:0004300` (the term most people reach for) is **obsolete** and was rejected. |
| PMID existence (PubMed) | 2/2 exist | Both citations are real records. |
| Quote in fulltext (Europe PMC) | 2/2 found, 0 titles | Citation pairing — see Provenance above. Not independent confirmation. |
| ClinVar significance | **0 subjects** | Nothing. No claim was made and none was checked. |

## Publish readiness

Everything local is green: `validate_module(strict)` passes, `compile_module(strict)` succeeds and
is byte-reproducible across runs (`artifact_digest`
`sha256:1db940ae…`, identical on two independent compiles), the module is closed, and
`verify_artifact` re-hashes clean.

**One thing blocks a publish today, and it is not a defect in this module.**
`registry_check(target="test")` returns:

```
studies.csv line 2 [curator]: Extra inputs are not permitted
studies.csv line 3 [curator]: Extra inputs are not permitted
```

The `curator` column shipped in **just-dna-format 0.6.5**; both live registry instances currently
serve **format 0.6.1** (registry 0.18.2), and `StudyRow` is `extra="forbid"`. Removing that one
column flips the same call to `verdict: true, blocking: []` — verified on a scratch copy, not on
this module.

**The column stays.** It is the per-row record of who located each quote, and dropping it to satisfy
a registry that lags the format would conform the module to a stale source and delete the only
attribution the quotes carry. This is a wait-for-the-registry decision, not an edit.

## Sources

- Sheikholmolouki E et al. *Sci Rep* 15, 40251 (2025). PMID 41249831.
- Hirvonen K et al. *BMC Med Genet* 18, 41 (2017). PMID 28399814.
