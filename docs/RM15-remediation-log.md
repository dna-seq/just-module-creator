# RM15 remediation — replacing 69 title-quotes with what the articles actually say

**Run 2026-08-20, unattended, on `aggression_anger` only.** A dogfooding exercise: the remediation
was the vehicle, the friction map (`F44`–`F47` in [dogfooding.md](dogfooding.md)) is the deliverable,
and the decision list for the real modules is [HANDOFF-antonkulaga-quotes.md](HANDOFF-antonkulaga-quotes.md).

Working copies live under `data/interim/rm15_remediation/` (git-ignored). The originals in
`../just-dna-format/data/output/corrected_modules/` were read and never written.

---

## What was published

```
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

Read back with `registry_get_module(target="test")`: `manifest.authorship`, `manifest.provenance` and
`manifest.logs` all survived the publish, and `sources.csv` was normalised to `derived/licensing.csv`
with the quoted article's CC-BY row surfacing on the card's `licensing.attributions`.

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

## Not done, and why

**`big_five_personality` was not remediated.** 859 rows over 26 PMIDs. The decision it needs is the
same one this module answered, the yield would be dominated by the same catalog-extraction case, and
the deliverables are worth more finished than a second module is worth started. The handoff carries
what a maintainer needs to decide it; the first module carries the worked method.

**`literature.csv` was left exactly as found** — `quotes_authored: 0` on all three rows, beside one
authored quote. Correcting it needs `enrich_literature_pass` or `refresh_sidecar`, both of which are
extended-tier and absent from a default install (`F47`). The module was published with the stale
sidecar and its log says so. Filed upstream as `S56`, because the compiler holds both files and
compares neither.
