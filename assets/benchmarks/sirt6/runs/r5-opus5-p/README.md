# SIRT6 and reaching very old age

One variant, `rs117385980` in *SIRT6*, and what two small studies say about whether carrying it
makes reaching very old age less likely. The honest summary is: **a consistent hint, shown by
neither study.** This module exists to say that precisely, not to assert an effect.

## Where this module came from

Built from one paper the author supplied:

- **Sheikholmolouki E et al. (2025)**, *The association of the SIRT6 rs117385980 variant with
  frailty and longevity: an exploratory study.* Sci Rep 15:40251. PMID 41249831,
  doi 10.1038/s41598-025-24018-3. CC BY-NC-ND 4.0.

That paper's longevity claim rests on the study it replicates, which was read in full and carries
its own row:

- **Hirvonen K et al. (2017)**, *SIRT6 polymorphism rs117385980 is associated with longevity and
  healthy aging in Finnish men.* BMC Med Genet 18:35. PMID 28399814,
  doi 10.1186/s12881-017-0401-z. CC BY 4.0.

A PubMed search on the rsID returns exactly these two papers, so the module's two study rows are
the complete primary literature for this variant as of 2026-11-26. No row was authored from a
source that was not read in full. Nothing here was drafted from a database panel.

Authored by an AI agent (`claude-opus-5`), recorded as `[ai, agent]` in `authorship:`. It has not
been reviewed by a human or by a second agent — see *What this module still needs*.

## What the two studies actually found

| | Hirvonen 2017 | Sheikholmolouki 2025 |
|---|---|---|
| Who | 198 Finnish men (106 longer-living and healthy, 92 died at mean age 66.6) | 227 adults aged 60-90 in Birjand, Iran, both sexes |
| Measured | survival to old age in good health | frailty (primary), age band (secondary) |
| Result | OR 3.58 for the T allele in the earlier-death group, 95% CI 0.96-13.4, **p = 0.074** | T allele 1.39% at 60-69, 4.65% at 70-79, **0% at 80-90**, p = 0.073 |
| Frailty | not measured | **no association**, p = 0.36 |
| Verdict | not significant; authors report 28.4% power | not significant; authors call it exploratory |

Both point the same way on age — the T allele is scarcer among the oldest — and neither reaches its
own significance threshold. The Iranian study also found the T allele **absent from its frail
group** and present only in the non-frail, which points the other way; that reading is recorded in
the `negatives` column of the C/T row rather than dropped.

### Orientation of the odds ratio, because no column states it

`studies.csv` carries `effect_size` and `effect_allele` but has no column saying which direction an
OR runs. Hirvonen's 3.58 is the odds of the T allele **in the earlier-death control group relative
to the longer-living group**: OR > 1 means T goes with dying earlier. Recomputed here from the
paper's own counts — longer-living 3 T of 212 alleles, controls 9 T of 184 — as
(9/175)/(3/209) = 3.583, which reproduces the published figure to three significant figures. That
also settles two ambiguities in the paper: the estimate is **allelic** rather than carrier-level
(the carrier calculation gives 3.72), and the correct value is the **3.58** of the Results text and
Table 2 rather than the **3.53** of the abstract.

## A disagreement between the two sources, left standing

The 2025 paper describes rs117385980 as *"a stop gained variant within the exon 2 of SIRT6 gene"*.
The 2017 paper it cites for the variant says it sits **23 bases downstream of the exon 2
exon/intron border** and types it as an **"intron variant"** in both of its tables, in a table that
types its neighbours as missense and splice-region — so the classification was deliberate.

These cannot both be right, and the module does not pick a side beyond reporting what each source
says. Three things bear on it, none of them decisive on its own:

- the primary report of the variant calls it intronic, and gives a distance that is intronic;
- gnomAD v4.1 records the T allele at 2.4% in Finland with **183 living homozygotes**, which is not
  the profile of a nonsense allele in a gene whose knockout is lethal in mice;
- *SIRT6* is not loss-of-function depleted in humans (pLI 6.3e-05, LOEUF 0.90, o/e LoF 0.62), so
  constraint neither confirms nor refutes it.

**The table that would settle it is `consequences.csv`, and no tool in this plugin writes it** — it
comes from `just-dna-enricher opentargets enrich`, recorded in the plugin's own source as "a parity
gap, not a decision". The Open Targets cache is present on this machine; only the wrapper is
missing. Resolving this is the first thing a second pass should do.

Two further relay errors in the 2025 paper's account of the 2017 one, found by reading both: it
reports Hirvonen's heterozygote count as 1/42 where Hirvonen says 1/43, and attributes p = 0.074 to
the 83-year-old HBS group where in Hirvonen it is the combined HBCS+HBS test. Neither changes any
conclusion; both are reasons the module's study rows were written from each paper's own text rather
than from the newer paper's summary of the older.

## How frequencies were decided

The conclusions originally quoted "about 6 in 100 copies in Finland", taken from Hirvonen's citation
of 1000 Genomes (0.056). `enrich_facts` pulled gnomAD v4.1 joint, which gives **2.4%** in Finland
over 17,394 individuals against 1000 Genomes' ~99 Finnish samples. The lay figures in the
conclusions are computed from gnomAD's global counts (AC 12,545 / AN 574,784, 183 homozygotes):
about 5 in 100 people of European, Finnish or Middle Eastern background carry one copy, about 95 in
100 carry none, and about 1 in 1,500 carries two. The correction is logged in `logs/authoring.log`.

## The three rows, and why T/T exists

| Genotype | state | direction | weight | Basis |
|---|---|---|---|---|
| C/C | neutral | neutral | 0.0 | Both papers treat it as the population norm; Hirvonen states CC has no effect on lifespan |
| C/T | risk | risk | -0.15 | Two cohorts agree on direction, neither is significant, one counter-signal in frailty |
| T/T | alt | unknown | *(blank)* | **Nobody has measured it** |

Neither study observed a single T/T individual, yet gnomAD says about 1 person in 1,500 carries
two copies. Leaving the genotype unrowed would mean a real carrier runs this module and matches
nothing, so the row exists and its conclusion says plainly that nothing has measured two copies and
that the one-copy finding may not be read as a double dose. `state=alt` is the genotype descriptor
that carries no direction and derives to `direction=unknown`; `neutral` would assert benign and
`risk` would assert a sign nobody measured. `weight` is blank rather than `0.0`, because `0.0` is
the claim "this genotype changes nothing", which is precisely what is unknown.

## Weights

Declared in full in `weighting:`. Bounded [-1, 1], positive is protective, ordinal **within this
module only** and not comparable with any other module's weights. The magnitudes are deliberately
small: -1 is reserved for a large, replicated, established effect, and this module has nothing of
the kind. Do not read the sum of this module as a longevity score — it has one variant.

## What this module still needs

1. **The consequence question** (stop-gained vs intronic) settled from `consequences.csv` once a
   producer for it is available.
2. **The two independent reviews** `module-voice` requires before publication — a lay reader and a
   scientific reviewer, on the rendered report. Neither has run. This is the main reason the module
   is not published.
3. **A human curator.** Every row here was located and written by an agent; `curator` on both study
   rows is `claude-opus-5` and `authorship:` says `[ai, agent]`.
4. A re-read when a better-powered cohort reports on this variant. Both current studies explicitly
   ask for one.

## Limits

This module describes one variant with a suggestive, unreplicated-at-significance association. It
does not interpret a genome, call a genotype, or give medical or health advice. The `logs/`
directory, including `logs/authoring.log` and the provenance trace, publishes with the module.
