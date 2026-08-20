# RM15 remediation — replacing title-quotes with what the articles actually say

**Run 2026-08-20, unattended, on `aggression_anger` and then `big_five_personality`.** A dogfooding exercise: the remediation
was the vehicle, the friction map (`F44`–`F47`, `F50` and `F51` in [dogfooding.md](dogfooding.md)) is the deliverable,
and the decision list for the real modules is [HANDOFF-antonkulaga-quotes.md](HANDOFF-antonkulaga-quotes.md).

Working copies live under `data/interim/rm15_remediation/` (git-ignored). The originals in
`../just-dna-format/data/output/corrected_modules/` were read and never written.

---

## What was published

```
test-sheep/test_big_five_personality_snps@1.0.0
https://module-polygon.just-dna.life
artifact.digest      sha256:345184b5f78b8ea53c66af2011962e4378b32dd0280e2d4aa4e60f6a2786d0ef
content_signature    sha256:0bf3caf2924bcec2988082bf5cc1baaa0cbe186962f0f2be1525f0d4ea699bae
published_at         2026-08-20T01:26:22Z

test-sheep/test_aggression_anger_snps@1.0.0
https://module-polygon.just-dna.life
artifact.digest      sha256:b9d2e01d1a9fa828f1606c21c3cbf15df773af3d7b72bd95b3f11090d278eaa0
content_signature    sha256:25c54dfe56eb4675c02d10b0797fe58d5b4e9418daf53fd4c79ac7d6cfcb618e
published_at         2026-08-20T00:46:10Z
```

Polygon only. `registry_whoami(target="test")` first — account `sheep`, namespace `test-sheep`. Both
the namespace and the module name carry the `test` prefix so the operator's purge sweep, which
matches both halves, takes it. The README opens with a banner saying it is a rehearsal and not to
install it. The server's own compile reproduced the local `artifact.digest` byte for byte.

Both read back with `registry_get_module(target="test")`: `manifest.authorship`,
`manifest.provenance` and `manifest.logs` all survived the publish, and `sources.csv` was normalised
to `derived/licensing.csv` with each quoted article's licence row surfacing on the card.

---

# The first module: `aggression_anger`, 69 rows over 3 PMIDs

## The change

**Only `studies.csv:provenance_quote`.** Nothing else in any row — not `conclusion`, `weight`,
`effect_size`, `direction`, `clin_sig`, `p_value`, `population`, `trait_efo_id`. Those are authored
or checked values; where one looked worth questioning it went to the handoff's decision list, not
into the file.

```
before   69 / 69 rows quoted · 3 distinct strings · one per PMID · each the article's title verbatim
after     1 / 69 rows quoted · 68 empty on purpose
```

## The granularity decision, and why

**A `provenance_quote` must be a passage that identifies THIS ROW's own variant and its association
with THIS ROW's trait.** Unit: `(pmid, rsid)`.

Three reasons, in the order they decided it.

1. **The row's grain is the claim's grain.** A `studies.csv` row asserts that *this paper* supports
   *this variant's* association with *this trait*. A passage that does not identify the variant is
   provenance for the study, not for the row, and the row is what a reader is checking.

2. **A trait-level passage repeated across many rows recreates the defect's own signature.** The
   detector for the title problem — the one `S54` asks upstream to build — is *one identical string
   across every row citing a PMID*. Writing one real trait-level sentence onto all 65 Nagel rows
   would have produced exactly that shape with a better string inside it: it would look repaired to a
   human and identical to the defect to any check. A repair that defeats the detector for the thing
   it repairs is the wrong repair.

3. **It makes the empty cells informative.** Under this rule, an empty quote says something
   specific — the article does not name this variant — rather than "nobody got round to it".

The alternative considered and rejected was per `(pmid, trait)`. It is defensible on a module where
one paper contributes rows across several traits, because then the quote genuinely varies. On this
module every paper contributes to one trait, so it degenerates into reason 2. If a future module
uses it, the README has to say so.

## Every row left empty, and why

**PMID 29500382** — Nagel M et al., *Item-level analyses reveal genetic heterogeneity in
neuroticism*, Nat Commun 2018. cc-by. **65 rows. Class: read and not found.**

Fulltext retrieved via Europe PMC (PMC5834468), 58 257 characters, `truncated: false`, read in full.
The article's text names exactly two rsIDs — `rs3130618` and `rs45510500` — and neither is one of
the 65. The associations these rows carry come from GWAS Catalog `GCST006941`, which extracted them
from the study's summary statistics; the article itself points at 50 Supplementary Data files and at
downloadable sumstats. `fetch_fulltext` returns the JATS body and no supplementary file, so there is
nothing in reach to quote.

The 65 rows, read off the file:

```
rs10071595, rs102275, rs10228350, rs10905619, rs10905638, rs11067376, rs1158960, rs11682175,
rs12886000, rs13223152, rs1422192, rs1542212, rs16884419, rs17151565, rs17592462, rs17650842,
rs17661015, rs1916977, rs2106785, rs2217127, rs2261201, rs2587410, rs2717033, rs28758902,
rs2959025, rs3026401, rs3110417, rs3124405, rs343949, rs35255819, rs3772556, rs3774800,
rs4411173, rs4570961, rs4634342, rs4734804, rs4781534, rs4820434, rs4953152, rs507078,
rs58446129, rs6087607, rs62055701, rs62065453, rs62211616, rs62212173, rs631140, rs6549048,
rs6596771, rs6711058, rs6718682, rs6800177, rs6861691, rs6969188, rs70600, rs7231748, rs7265992,
rs7535528, rs776472, rs7973253, rs9403716, rs9527336, rs9630740, rs9938550, rs999483
```

Note that `rs3130618` — one of the two rsIDs the article's text does name — is **not** among them.

**PMID 20585324** — Dick DM et al., *Genome-wide association study of conduct disorder
symptomatology*, Mol Psychiatry 2011. **Not open access. 3 rows. Class: unchecked.**

`fetch_fulltext` returned `text_source: "abstract"` with the warning that an abstract miss is not a
verdict. The abstract states that four markers reached genome-wide significance and names the gene
`C1QTNF7`; it names no rsID. So no variant-level passage could be located from anything reachable.
Rows: `rs11838918`, `rs16891867`, `rs7950811`. A human with journal access could settle all three —
it is decision 4 in the handoff.

## The one quote written

**PMID 24489884** — Mick E et al., *Genome-Wide Association Study of Proneness to Anger*, PLoS One
2014. `cc-by` on the publisher's published version (`lookup_open_access`). Fulltext retrieved via
Europe PMC (PMC3905014), not truncated, read in full.

Row `rs2148710`, trait `EFO_0003015`:

> The most statistically significant association in the current study was with rs2148710 and the
> Angry Temperament score in FYN.

Discussion section, verbatim. It names the row's variant and the row's trait. The row's
`effect_allele` (T), `effect_size` (0.22) and `p_value` (2.9E-08) are in the article's Table 1 and
this sentence does not restate them — a quote locates the claim, it does not duplicate the columns.

Located by `claude-opus-5` reading the article through `fetch_fulltext`. No human read it in this
run. Verified verbatim against the retrieved text with the enricher's own `quote_matches`
(whitespace- and case-insensitive literal containment).

## Where the whodunit went, given there is no column for it

`StudyRow` has no attributor (`F43` / upstream `S55`), so it went to three places, and all three
were verified to survive the publish by reading the manifest back:

- **`module_spec.yaml: authorship`** — `who: claude-opus-5`, `role: edited`, `kind: [ai, agent]`,
  `at: 2026-08-20`. Per version. Only `edited` is claimed: the spec as handed over declared no
  authorship, so claiming `created` would have been a false claim about somebody else's work.
- **`provenance.json`** — 69 `ProvenanceItem`s, one per `variant_key`, each `rationale` naming who
  located the quote or exactly why the cell is empty and which of the two kinds of empty it is.
  Header carries `generator`, `model` and `agent_version`. Summarised into `manifest.provenance`.
- **`logs/quote-remediation.log`** — the run account: what changed, the granularity rule, the per-PMID
  outcome, and what the record cannot say.

**None of the three is per `(row, quote)`, which is the grain the work has.** `ProvenanceItem` is
keyed on `variant_key` alone, so a variant cited by two papers would collapse into one item — it
happens not to here, since every rsID appears once in `studies.csv`. And `provenance.json` and
`logs/` are both deliberately dropped by a registry contract `upgrade`, so an upgraded version keeps
the quotes and loses who found them. Both limits are stated upstream in `S55` rather than designed
around.

## Also changed, and why each was mechanical rather than a judgement

- **`sources.csv`** gained one row: `source: pmid:24489884`, `layer: annotation`, `license: CC-BY`,
  with the article's own credit line. Quoting an article's text puts publisher prose in the module's
  annotation layer, and that row is what records the terms. Written to `sources.csv` — the file that
  was there — not to a new `licensing.csv`; the registry normalised the name on upload, which is its
  job and not ours.
- **`module_spec.yaml: module.name`** → `test_aggression_anger_snps`, and the title got a `TEST —`
  prefix, so the polygon card cannot be mistaken for the catalog module.
- **`README.md`** gained the rehearsal banner and three rows in its file table.
- **`close_module`** was run before publishing, `closed_by` naming the agent and the run.

## What was run, in order

```
lookup_citation × 3            identity, not existence — every title read and compared
lookup_open_access × 2         where it may be read, and on what terms
fetch_fulltext × 3             the articles, read in full
describe_table × 2             studies.csv and licensing.csv — column shapes asked, never recalled
[hand edit]                    <- no tool writes an authored cell; see F45
validate_module(strict)        valid; 2 warnings (deprecated spelling, no closure)
enrich_module                  sources: ["authored"] — merged, nothing re-fetched, vrs_minted 0
compile_module(strict)         green
registry_check(literature)     verdict true, everything empty — see F44
close_module
registry_publish(target=test)
registry_get_module(target=test)
```

## The probe that produced `F44`

A second spec directory, `data/interim/rm15_remediation/baseline_original`, identical to the
remediated one except that `studies.csv` is the original with its 69 title-quotes. Both were put
through `registry_check(target="test", literature=true, strict=true)`, the most expensive check on
the surface.

```
remediated   verdict: true   blocking: []   non_blocking: []   unchecked: []
baseline     verdict: true   blocking: []   non_blocking: []   unchecked: []
```

Identical. Nothing on the pre-flight distinguishes a module whose entire evidence layer is article
metadata from one where 68 cells are honestly empty and one carries a located passage. That is the
finding.

---

# The second module: `big_five_personality`, 859 rows over 26 PMIDs

Taken once the first was published and every deliverable committed. Same rule, same tools, and it is
where all the interesting cases are — `aggression_anger` is 1:1 variant-to-row and hides most of them.

```
before   859 / 859 quoted · 26 distinct strings · one per PMID · each the article's title
after     21 / 859 quoted · 21 DISTINCT strings · 838 empty on purpose
```

## The measurement, before any editing

Every one of the 26 cited PMIDs was retrieved with `fetch_fulltext`, every `rsNNNN` token in the
retrieved text was listed, and the lists were intersected with the rsIDs the module cites to that
paper. All 859 rows land in four classes:

```
quotable            — the retrievable text names this row's variant            25 rows
read and not found  — fulltext retrieved and read, variant not in it          300 rows
unchecked           — no open-access fulltext; abstract only                  527 rows
unchecked           — nothing retrievable at all (pmid 31972866)                7 rows
```

Every one of the 25 swept fetches reported `truncated: false`, checked across the sweep records
rather than assumed — the classification of 300 rows as *read and not found* depends entirely on it.

**The relationship is inverse and it is the useful result: the more rows a paper grounds, the less
likely its text names any of them.** The three biggest contributors returned nothing — `30643256`
(298 rows), `29500382` (197), `29255261` (69). `29500382`'s fulltext *was* retrieved in full and
names exactly two rsIDs, neither among the 197 it is cited for.

Two things were not wrong: every module p-value checked against its paper's own table agreed to one
significant figure, on all 18 rows where both were available, and every PMID named the paper the row
meant. The citations and the numbers are right; only the quotes were metadata.

## Three situations `aggression_anger` never produced

**1. Named only in a table.** 15 of the 21 quotes are a row of a flattened JATS table, because that
is the only place the article states the association for that variant. Verbatim, matching, and each
carries the variant, its alleles, its effect and its p-value — but `provenance_quote` is documented
as *human-legible*, and a table row is legible only to somebody holding the paper. Written anyway:
strictly better than empty, enormously better than a title, and it varies per row so it cannot
recreate the F42 shape. Recorded as an authoring decision the skill does not currently help anyone
make.

**2. Named, but for a different claim — the finding only locating the quote could produce.**
`rs34588274`, `rs3742021`, `rs4245154` and `rs527528` cite PMID `34054130` (Bralten J et al.,
*Genetic underpinnings of sociability in the general population*, Neuropsychopharmacology 2021) for
trait `EFO_0009589`, *"Worry too long after an embarrassing experience"*, via GWAS Catalog
`GCST012111`. The article names all four rsIDs — in a table of genome-wide significant hits for
**sociability**, at `1.01E-13`, `7.43E-09`, `7.17E-09`, `4.02E-10`, against the module's `2e-17`,
`1e-09`, `9e-09`, `4e-11`. It contains no analysis of that neuroticism item; *worry* appears once, in
an unrelated sentence.

So a passage naming the variant exists and does not support the row's claim. **Left empty rather than
quoted** — attaching a real sentence to the wrong assertion is worse than an empty cell — and
escalated to the handoff's decision list, because `trait_efo_id`, `p_value` and `conclusion` are all
authored values and none is ours to change. Settling it needs the GWAS Catalog record for
`GCST012111`, which `enrich_gwas_effects` would fetch and which is extended-tier.

Under the old rule these four rows carried the article's title and looked exactly like the other 855.

**3. Quotable, but with no reuse licence.** `27089181` (Okbay A et al., Nat Genet 2016) is free to
read with **no** reuse grant on any location — every one came back `other-oa`. The quote was kept and
its `sources.csv` row records the three rights as **unknown** rather than assuming them. The
consequence is visible and correct on the published card: `unknown_terms_sources: ["pmid:27089181"]`,
and the module's own `licensing.commercial_use` and `redistribution` both drop to `null`. One article
with unclear terms makes the whole module's commercial-use answer unknown, which is the honest
result and worth knowing before quoting.

## Whodunit, and the collapse made concrete

Same three places, all verified on the published manifest: `authorship` (per version),
`provenance.json` (735 items, per variant), `logs/quote-remediation.log` (per run).

This module is where `S55`'s argument stops being hypothetical. 95 of its 735 variants are cited by
more than one paper — 75 by two, 14 by three, 3 by four, 3 by five — and 37 of those by different
papers for **different traits**. `ProvenanceItem` is keyed on `variant_key` alone while a
`studies.csv` row is `(variant, pmid)`, so for those 95 the notes for every citing paper are merged
into one item, spelled out in the rationale text. One row in eight, on a module of ordinary size.

## Not done, and why

**No third or fourth module.** `cognitive_intelligence` and `risk_impulsivity` were not touched.** They are the two largest (2045
and 695 rows) and both are dominated by papers cited for hundreds of variants each, which is the
class measured above as yielding nothing. The handoff carries the numbers a maintainer needs; a third
and fourth rehearsal would repeat the method rather than test it.

**`literature.csv` was left exactly as found** in both modules — `quotes_authored: 0` on all three rows, beside one
authored quote. Correcting it needs `enrich_literature_pass` or `refresh_sidecar`, both of which are
extended-tier and absent from a default install (`F47`). The module was published with the stale
sidecar and its log says so. Filed upstream as `S56`, because the compiler holds both files and
compares neither.
