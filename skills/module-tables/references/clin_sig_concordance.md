# clin_sig_concordance.csv + clin_sig_authority_calls.csv — where the authorities disagree with you

> **Written 2026-09-11 against format 0.7.0 / compiler 0.7.0 / enricher 0.7.0, read from the code.**
> Both tables landed in format `RM130` and reached the registry's rosters in 0.25.0 (our `S19`).
> **One dossier for two tables on purpose**: they are a parent and its detail, the join is the whole
> point, and splitting them would put the join in two places. Anchor on symbol names —
> `concordance.concordance_tables`, `concordance.write_concordance_tables` — not on `file:line`.
> Neither release is cut; confirm any specific cell with `describe_machine_table`.

## In one paragraph

Your module says a variant is `pathogenic`. ClinVar says `uncertain_significance`. PubMind's
records say something else again. **The concordance record is where that disagreement is written
down** — the parent table holds one row per *contested* subject with two separate verdicts, and the
detail table holds one row per authority consulted, in that authority's own words and units. It
exists because the alternative is a module that quietly asserts one answer while the archives assert
another, and nothing downstream can tell.

**It is not a correctness verdict and there is no consensus field.** The omission is deliberate:
resolving a split needs a weighting model this format does not have. What the record gives you is
the shape of the disagreement, so somebody can decide.

## Identity card

| | | |
|---|---|---|
| | **parent** | **detail** |
| File | `clin_sig_concordance.csv` | `clin_sig_authority_calls.csv` |
| Model | `concordance.ClinSigConcordanceRow` | `concordance.ClinSigAuthorityCallRow` |
| One row is | one **contested** subject | what **one authority** said about it |
| Key | `(variant_key, genotype)` | `(variant_key, genotype, authority)` |
| Parquet | `clin_sig_concordance.parquet` | `clin_sig_authority_calls.parquet` |
| Fact signature | `integrity.clin_sig_concordance_signature` | `integrity.clin_sig_authority_call_signature` |
| Overlayable | **yes** — and it is the only table that can vindicate you | **no**, structurally |
| Authored | no. Machine-produced, `extra="forbid"` | no |
| Written by | `enrich_module`'s clin_sig leg, via `write_concordance_tables` | same call, same moment |

## Four facts that change how you read it

### 1. Only *contested* subjects reach the record, and it is rewritten whole

A record of every agreement would be a copy of your own `clin_sig` column with a second opinion
attached — and the count of subjects compared is already published as the check's denominator, so
recording it again as rows would be the same number in two places.

**`write_concordance_tables` replaces both tables entirely on every run, and merging would be
actively wrong.** A subject the authorities stopped contesting has to *leave* the record, because a
conflict that stops being reported is exactly how you learn the archive caught up with you. Two
consequences:

- **A run that found nothing contested writes two empty tables**, and that is a claim — *nothing is
  contested* — which is a different claim from **no record at all**, which is what a run that could
  not put the question leaves behind by writing nothing. The three-valued rule, on disk.
- **`refresh_sidecar` refuses both tables**, and for a reason that is not the licence rows' reason.
  There is no curation here to protect and no merge to classify against, so a capture would protect
  nothing and every row would read as withdrawn or added on every run. Re-derive by re-running
  `enrich_module`.

### 2. The two verdicts are two questions, and reading one as the other is the trap

| column | asks |
|---|---|
| `authority_concordance` | do the authorities agree with **each other**? |
| `authored_position` | where does **your** call sit relative to the ones that spoke? |

They are separate fields because they are separate questions. A single field would have to name the
authority inside the member to say the same thing, which is the combinatorial explosion a stress
test at five sources found. Ask `describe_machine_table("clin_sig_concordance.csv")` for both
vocabularies; each carries an `unchecked` member, and **`unchecked` is not agreement**.

`opposed` is the one to render first: it is `True` when two calls in play sit in **opposite camps** —
a pathogenic-class call against a benign-class one — rather than merely differing. `opposed` is the
disagreement that crosses the line; everything else may be two words for one degree of uncertainty.

### 3. Read `unchecked_count` beside the row count, or you will misread an outage as progress

`manifest.clin_sig_concordance` summarises the record: `row_count`, `call_count`, **`opposed_count`**
and **`unchecked_count`**, the authorities and datasets consulted, both signatures, and the value
sets present.

**A shrinking record with a rising `unchecked_count` is a missing snapshot, not an improving
module.** Those two counters are the pair that earns its place; the others are context.

### 4. The detail table is outside the overlay, and the parent is inside

`overrides.csv` may correct `clin_sig_concordance.csv`. It may **not** correct
`clin_sig_authority_calls.csv`, and the asymmetry is structural rather than an oversight: **an
authority's words are not the author's to correct.** You answer the question; you do not get to
rewrite what an archive published.

That is also where the format's one vindication signal lives. An overlay row against the parent that
reaches nothing means the authorities have since agreed and your correction is no longer needed —
unambiguous *here* and nowhere else, precisely because the record holds contested subjects only and
is rewritten whole. See [`overrides.md`](overrides.md) for the wording and its restraint: the
archive moved toward you, which is an observation about the record and not a verdict about the
biology.

## Two column pairs worth knowing before you read a row

- **`clin_sig` beside `clin_sig_raw`.** The first is the authority's call normalized into this
  format's own vocabulary by the one shared normalizer; the second is its verbatim wording
  (`Conflicting_classifications_of_pathogenicity`). Quote the raw one when you are telling somebody
  what an archive said; compare on the normalized one.
- **`confidence` beside `confidence_unit`.** The magnitude is in the authority's **own units and
  unconverted** — ClinVar's review stars stay review stars — and `confidence_unit` is the instrument.
  They travel together: a magnitude with no instrument beside it is refused at the model. The same
  pair arrived on `StudyRow` in 0.7 for the same reason (see [`studies.md`](studies.md)).

`status` on the detail table is what happened when the authority was consulted, and `no_record` is a
real answer — the authority was reached and holds nothing — which is different from `unchecked`,
where nobody was reached at all.

**The detail table has no `source` column**, because `authority` already names where the row came
from and a second column holding the same string would be two spellings of one fact. The consequence
is that this table is exempt from the orphan check that asks which declared licence rows a module's
tables actually use — correct, because the pass that consulted the authority writes its own
`sources.csv` row, and that is where the licence position is recorded.

## Related

- [`overrides.md`](overrides.md) — how to overrule the parent, and the vindication signal
- [`clinical_assertions.md`](clinical_assertions.md) — ClinVar's own call and the review behind it,
  which is a *record of what an archive says* rather than a comparison against you
- [`variants.md`](variants.md) — where `clin_sig` and `genotype` are authored
- [`verification.md`](verification.md) — whether the comparison ran at all
