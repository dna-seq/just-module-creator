# Longevity candidate variants from centenarians

Candidate longevity variants reported in a 21-person centenarian and supercentenarian cohort.

This module records **eight coding variants** named in the body of one 2025 paper, at the genotypes
a carrier could plausibly have. It is a record of what that paper reported, checked against live
reference data. It is **not** a statement that any of these variants lengthens or shortens life, and
no row claims one. On checking, **none of the paper's three variant-level claims survived intact.**

## The single source, and the limit that shapes every row

Raj APMS, Selvakumar G, Clement J, Church GM, Sivasubramaniam S. *Genetic signatures of exceptional
longevity: a comprehensive analysis of coding region single nucleotide polymorphisms (SNPs) in
centenarians and supercentenarians.* Hum Genomics. 2025;19:115. PMID 41057961,
DOI 10.1186/s40246-025-00772-3.

**The study has no control group.** It sequenced 3 centenarians and 18 supercentenarians,
intersected their variant calls, and annotated what all 21 shared. Nothing was compared with people
of ordinary lifespan, and no association test was run on any variant. The authors say so themselves,
and that sentence is quoted in the row data: the findings "may help prioritize candidate variants and
genes for future studies on larger cohorts with appropriate controls".

### What "shared by all 21" actually means

The paper defines it on presence, not genotype: "Common SNPs are those genetic variations found in
all individuals within the dataset." **No zygosity was recorded.** The cohort observation therefore
supports "carried the alternate allele" and nothing finer. The genotypes here are the genotypes a
reader could have at each site, each with its own conclusion — not a claim about what the 21
participants carried.

### Why no row claims a direction

Every row carries `direction=unknown` and `stat_significance=unknown`, and the module authors **no
weights** (see `weighting:` in `module_spec.yaml`). Do not sum these rows into a score.

`state` is written as `alt` (or `ref` for the one reference-homozygous row) rather than `neutral`.
This is deliberate: in this format `neutral` asserts *benign*, which for most of these variants
would be a claim nobody has established. `alt` and `ref` are genotype descriptors that carry no
direction and derive to `direction=unknown`, which is exactly what these rows are.

## Three findings that contradict the source

Each was checked against live gnomAD, ClinVar and Ensembl through the plugin's own lookups, not
inferred from the paper.

**1. rs412051 is not a longevity association.** The paper cites reference [29] (Muntané et al., Mol
Biol Evol 2018) as prior evidence. That paper is a *cross-primate* comparative study. Its Table 2
lists rs412051 in BRD8 as a human polymorphism at a primate parallel-change site, alternative allele
at 97%, SIFT "tolerated", PolyPhen2 "benign" — and reports no human longevity association. Live
gnomAD puts that allele at **99.67%**, so its presence in all 21 participants is what you would
expect of almost anyone. A second `studies.csv` row cites Muntané directly so the discrepancy is
visible in the data rather than only here.

**2. rs9885916's prior association cannot be checked.** Reference [30] is an unpublished 2014
doctoral thesis (Kiel) linked to a file-sharing URL. It carries no PMID and is not indexed. A
literature search for rs9885916 returns only the centenarian paper itself — with the caveat that
Semantic Scholar was rate-limited and did not answer, so that search is incomplete rather than
exhaustive. Live gnomAD has **no record at all** for this position, so the paper's ~50% frequency
figure has no independent corroboration.

**3. Two variants are not rare, and two are far rarer than stated.** The paper's own frequency
figures disagree sharply with live gnomAD:

| Variant | Paper (Additional file 12) | Live gnomAD (global) |
|---|---|---|
| rs141207681 | 0.0083 | 1 allele copy in 1,606,574 |
| rs575564328 | 0.00058 | 27 in 766,224, concentrated in East Asian ancestry |
| rs61849494 | absent | 4 in 1,613,722 |
| rs150316320 | 0 | 938 in 1,500,742 |
| rs75029097 | <0.01 (1000 Genomes) | 0.4996 |
| rs11228733 | <0.01 (1000 Genomes) | 0.4951 |

For rs75029097 ClinVar additionally records **benign** (KCNJ12-related disorder) against the paper's
SIFT "deleterious" call.

### The strongest single result: two of the eight are mapping artefacts

At rs75029097 the alternate allele sits at 49.96% across **every** gnomAD population, and the
homozygote count is **0 out of ~785,000 people**. At rs11228733 it is 49.51% and the homozygote count
is **4 out of ~740,000**. Hardy-Weinberg predicts roughly a quarter of individuals homozygous in each
case — on the order of 180,000–195,000 people. Observing essentially none is not a rare genotype; it
is the signature of a site where every individual is called heterozygous because reads from two
near-identical gene copies pile up on one locus. Both genes (KCNJ12, OR9G1) belong to known
paralogous families. These two rows say so in plain words and are categorised
`Probable mapping artefact, not a usable variant`.

The same shape is visible, less conclusively, across the paper's wider deleterious set: of its 64
rsID-bearing variants the **median of the supplement's own `Average` frequency column is 0.79**, and
the genes are paralog-rich (ANKRD36C, FRG1B, TIMM23/TIMM23B, PRIM2, HNRNPCL1, OR4C3/OR4C5/OR9G1,
TRBV7-3). That median was read from the supplement's summary column only; per-population columns were
checked live for the two artefact sites above and not for the rest.

## What was checked, and what it is worth

| Check | Result |
|---|---|
| All 8 rsIDs resolve on GRCh38 | yes, `resolution.csv`, 0 unresolved |
| Authored ref vs. the genome | no mismatches |
| Genotype alleles vs. resolved alleles | no mismatches |
| Gene symbols (HGNC) | 8 of 8 approved |
| Gene sits on the variant's own chromosome | checked, 0 conflicts |
| Trait CURIE `OBA_VT0005372` | current |
| All 9 provenance quotes present verbatim | yes, 0 titles-as-quotes |
| Authored DOI vs. the registry | no conflict |

**One honest caveat about the quotes.** The full texts were retrieved and read in order to locate
these passages. That makes `quotes_found` a citation-pairing check — it catches a quote filed against
the wrong paper — and *not* independent evidence that the claim is in the literature.

**`clin_sig` is deliberately empty on every row**, so the clinical-significance and
published-refutation checks ran over zero subjects. They established nothing and must not be read as
clean. ClinVar's own call for rs75029097 is reported above rather than copied into a cell that
ClinVar would then be checked against.

**Sentences describing what each gene does** (mitochondrial import, trypsin-3, T-cell receptor
segments, potassium channels, odour receptors, DNA primase, chromatin) are general background from
the curator's own knowledge, not quoted from either cited paper. Only the frequency, significance and
cohort statements are sourced.

## Scope: what was reached and not authored

The paper's 110 deleterious variants are reachable (Additional file 12, sheet
`Deleterious SNPs gnomAD`; 64 carry rsIDs, 46 do not, counted on that sheet's `dbSNP` column). They
are **not** authored here, and this is recorded in `logs/authoring.log`. The paper's own funnel ends
at "deleterious *and* under 1%", and its two `<0.01` sheets contain exactly the six rsIDs its body
names — which, with the two it calls previously associated, are the eight here. The other 102 receive
no statement in the paper beyond membership in a filtered list. Widening the module is a decision for
the author, not a gap.

Three rare sites could not be authored at all: TIMM23B (chr10:51381481) and OR4C5 (listed at both
chr11:48387894 and chr11:48387582 in different sheets of the same file — the file contradicts
itself) carry no rsID, and their coordinates are GRCh37 while this module is GRCh38. Placing them
needs `lookup_old_assembly`, which returned `unchecked` on four attempts across this session
(2026-11-26): the GRCh37 service could not be reached. That is an outage, **not** evidence that dbSNP
does not know these coordinates, and it is worth retrying before concluding anything.

The paper's `dbSNP` column also contradicts itself: the main sheet leaves PRSS3 and HNRNPCL1 blank
where the `<0.01` sheets give rs150316320 and rs141207681. Those pairings are the paper's own and
could not be independently confirmed, for the same outage reason.

## Licensing

| Source | Layer | Licence | Commercial use |
|---|---|---|---|
| Raj 2025 (Hum Genomics) | annotation | CC-BY-NC-**ND**-4.0 | no |
| Muntané 2018 (Mol Biol Evol) | annotation | CC-BY-NC-4.0 | no |

`module_spec.yaml` declares `CC-BY-NC-ND-4.0`, the more restrictive of the two, which is why a
compile warns that one annotation source differs. That is the ordinary mixed-licence case: the most
restrictive term binds. **This module cannot be sold**, and the ND clause on the primary source
states that adapted material derived from the article may not be shared — the passages here are
short verbatim quotations identifying where each claim is stated.

## Open decisions for the author

1. **Authorship.** `authorship:` lists only the agent that built this. A human author should add
   themselves before publishing; responsibility rests with them regardless.
2. **The two artefact rows.** They are kept because a reader whose file reports that genotype
   deserves to be told it is probably an artefact. Removing them instead is defensible.
3. **Scope.** Widen to the 64 rsID-bearing deleterious variants, or keep the eight the body names.
4. **Closure.** The module is not closed. Closing is a deliberate act and is the author's.
5. **Whether to publish at all.** The underlying study supports no longevity claim, and two of its
   eight named variants appear to be sequencing artefacts. A module that says so honestly is
   truthful and arguably useful as a corrective; whether it belongs in a longevity catalogue is a
   judgement for the author.
