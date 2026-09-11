# overrides.csv — the one place an author overrules a derived table, on the record

> **Written 2026-09-11 against format 0.7.0 / compiler 0.7.0 / enricher 0.7.0, read from the code
> rather than from a changelog.** The overlay landed in format `RM124` and reached the registry's
> `RECOGNIZED_SPEC_FILES` in registry 0.25.0 (our `S19`), which is the pair of facts that makes it
> safe to teach: the compiler drafts it, and a server-side rebuild carries it instead of dropping
> it. Anchor on symbol names — `overrides.OVERRIDABLE_TABLES`, `overrides.apply_overrides` — not on
> `file:line`. **Neither release is cut**: both are installed here from sibling checkouts, so
> confirm with `describe_spec_file("overrides.csv")` before acting on any specific cell.

## In one paragraph

Every other derived table is something you either accept or re-derive. `overrides.csv` is the third
option: a **declarative correction** laid over a machine-written table at compile time, carrying the
reason it was made. It does not edit the sidecar. The enricher's output stays exactly as the
enricher wrote it, the overlay sits beside it, and the compiler applies one to the other on its way
to the parquet. That asymmetry is the design and it is the single most important thing on this page:
**read the derived parquet for what the module asserts, and the derived CSV for what the source
said.** Those are now two different questions with two different answers.

## Identity card

| | |
|---|---|
| Model + module | `just_dna_format.overrides.OverrideRow` (`schema/src/just_dna_format/overrides.py`) |
| Parquet | `overrides.parquet` — in `ARTIFACT_PARQUETS`, so in `artifact.digest` |
| Natural / dedup key | `(table, subject, member, field)` — the model's own `_KEY_FIELDS`; ask `describe_spec_file` rather than trusting this line |
| Authored or machine-produced | **authored.** An `AuthoredModel`, `extra="forbid"` |
| Who writes it | you. The compiler's drafter can scaffold one; nothing fetches one |
| In `content_signature`? | **Yes**, and only by its value cells — `table`/`subject`/`member`/`field`/`operation`/`value`. `reason`/`decided_by`/`decided_at` are excluded (format `S87`/`RM180`, ours) |
| In `artifact.digest`? | **Yes**, via its parquet, and the `manifest.inputs` entry moves on any byte change — prose included |
| Location | root or `derived/overrides.csv`; one spelling only, like every other sidecar |
| Applied by | `overrides.apply_overrides(table, rows, overrides)` → `(rows, errors, warnings)` |

## The four things to get right

### 1. `reason` is required, and that is the whole point of the file

An empty `reason` is a validation error, not a warning. The column is what makes this a **record**
rather than a knob: a published module carrying an overlay tells a reader which derived values its
author rejected and why, in the author's own sentence. `decided_by` and `decided_at` are optional
and are the rest of that record — who, and when.

**Those three columns sit outside `content_signature` and inside `artifact.digest`.** So rewording a
`reason` is a patch: the content identity does not move, a registry keyed on it treats the module as
the same content, and the parquet bytes change. That was our `S87` and upstream's `RM180`, and the
mechanism is a field marker (`base.OUTSIDE_CONTENT_IDENTITY`) rather than `exclude=True` — our own
candidate fix would have blanked the cells in every writer that serializes through `model_dump()`,
the drafter included, and `reason` is required, so a drafted row would have failed its own compile.
If you ever compute the signature by hand rather than calling `integrity.content_signature`, drop
those three via `base.content_identity_exclusions(OverrideRow)`.

### 2. The three operations are not symmetric, and `member` is where they differ

Ask `describe_spec_file("overrides.csv")` for the operation vocabulary; what the tool cannot tell
you is the asymmetry, so it is here:

- **`update`** corrects one field of one derived row. It is the **only** operation that may go
  group-scoped: an empty `member` on a grouped table corrects **every** row under that subject. An
  update never creates a row and never moves one.
- **`insert`** supplies a row the source has no answer for. It is written as **several overlay rows
  sharing `(table, subject, member)`, one per field** — so the file has one shape rather than two —
  and the row is appended at the **end of its subject's group**, in the order the overlay rows
  appear. Placement is a function of the overlay's authored order, never of a sort over values,
  because a corrected cell must not be able to move a row.
- **`suppress`** removes a derived row you reject. `field` must be empty. It **refuses** an empty
  `member` on a grouped table: dropping a whole group is not recoverable by reading the result.

Order is load-bearing throughout, because parquet bytes depend on it.

### 3. A no-op reports nothing, and that is forced rather than tidy

`reverse_module` emits the **post-overlay** tables *plus* the overlay, so on lap two of a
`compile → reverse → compile` the update already equals, the insert is already present and the
suppress target is already absent — all three at once, on a perfectly healthy module. Reporting any
of them would make a module disagree with its own round trip about
`manifest.compilation.warnings`, which is a published field. So they are silent.

**The consequence to carry: no operation reports its own no-op.** A `suppress` with a typo'd subject
does nothing, and cannot warn. There is no `previous_value` column, and the fixed point is a test
upstream rather than an assumption — all three operations are idempotent, which is why applying the
overlay twice is safe.

**The one mismatch an overlay cannot manufacture for itself is an `update` that reached no row**,
because an update never creates one. That is the finding that does fire, and 0.7 splits it into its
two answerable readings (`RM137`, `overrides.classify_update_targets`):

- **reachable** — the subject *is* cited or positioned, so an artifact of this module could carry
  the row, and the sidecar simply does not have it. Re-run the enrichment.
- **unreachable** — nothing in this module could ever carry it. **A mistyped identifier lands
  here**, not in the reachable bucket: a mistyped pmid is also an uncited one.

Both readings need `studies.csv` and the citing tables, which is why they are classified where those
are in scope rather than where the overlay is applied. `overrides.LOSSY_OVERLAY_TABLES` is the pair
where the split can actually be computed; the other tables get one withholding message naming both
readings, which is the three-valued rule again — **the caller could not ask, so it does not accuse.**

### 4. The vindication signal, and why it exists nowhere else

`overrides.VINDICATING_OVERLAY_TABLE` is `clin_sig_concordance.csv`, and it is one table for a
reason that does not generalise. That record holds **contested subjects only** and is **rewritten
whole** on every run. So an overlay row against it that reaches nothing means one specific thing:
the authorities have since agreed, the subject left the record, and **the author's correction is no
longer needed**. On every other table that state is ambiguous.

This is the one trust signal in the format available nowhere else, and it costs nobody a decision.
It replaced a message that was actively misleading — the generic *"the subject may be mistyped, or
the correction may be aimed at a row the compiler drops"*, put to an author in the one case where
their judgement had been vindicated.

**Read the wording carefully and reproduce its restraint.** It says the authorities agreed and the
row is now unnecessary. It says **nothing about who was right about the biology** — that the archive
moved toward the author is an observation about the record, not a verdict.

## Which tables may be overlaid

**The roster is `overrides.OVERRIDABLE_TABLES` — run the call.** It grew in 0.7 and will grow again,
and it is longer than the *covered set* `INTEGRATION_0_7.md` § 2.3 enumerates, which is the
discrepancy the last paragraph of this section is about. Each entry names the target model plus its
**subject** column and its **member** column, which is where `subject` and `member` get their
meaning:

```
uv run python -c "
from just_dna_format.overrides import OVERRIDABLE_TABLES
for csv, t in sorted(OVERRIDABLE_TABLES.items()):
    print(f'{csv:28} subject={t.subject_field:16} member={t.member_field}')"
```

Two shapes fall out of that and both matter. A table with `member_field=None` is **ungrouped** —
`literature.csv` keyed on `pmid`, `gwas_effects.csv` on `association_id` — so `member` is empty and
the group-scoped `update` and the refused group-wide `suppress` do not arise. Everything else is
grouped, and `member` is the within-group discriminator in that table's own column.

**`expression_effects.csv` is an overlay target and the sidecar behind it is a special case.** It is
a compiler-recognised derived table whose parquet is in `ARTIFACT_PARQUETS`, and for one afternoon it
was in none of the registry's three rosters, so a rebuild dropped the sidecar and an overlay against
it corrected a table the publish did not carry — registry-tree `S22`, filed and closed 2026-09-11.
What remains is narrower: the sidecar's producer is the enricher's `expression` pass, gated on an
AlphaGenome Atlas credential, and nothing here wraps it — so an overlay row against this table is
fine, and `refresh_sidecar` will refuse to rebuild the table under it.

## What this is NOT: `record_override` and `logs/authoring.log`

These are two mechanisms with similar names and no overlap, and conflating them is the mistake this
section exists to prevent.

| | `overrides.csv` | `record_override` → `logs/authoring.log` |
|---|---|---|
| Acts on | a **derived** table's row | an **authored** cell you edited by hand |
| Mechanism | declarative; the compiler applies it at build | a log entry; nothing is applied |
| Changes the artifact | **yes** — the parquet is built post-overlay | **no** — it silences nothing and changes nothing |
| Reaches `content_signature` | yes, by its value cells | no |
| Keyed on | `(table, subject, member, field)` | `(variant_key, field)` |

So: you corrected a `weight` in `variants.csv` → that is a hand edit, and `record_override` is the
tool that puts it on the record. You disagree with a `faf95` gnomAD wrote → that is
`overrides.csv`, and the compile carries your number. **Neither one is a licence to conform a row to
a source that disagrees with it** — see `module-weights` and the discriminator in `module-curate`.

## How to write one

`describe_spec_file("overrides.csv")` for the live columns and the operation vocabulary, then
`lint_rows` and `validate_module` — the overlay's file-level rules run in both. Two of those rules
are newer than the column list and are worth knowing before you hit them:

- **One operation per key group.** An `update` and a `suppress` under the same key, or two `update`s
  of one field, are an error rather than a last-writer-wins.
- **Spelling counts at the file level even where matching forgives it.** The overlay's key cells are
  raw author text and the derived rows are canonical, so `member=AFR` and `member=afr` each *match*
  the same `afr` row — but the **grouping** did not see them as one, so the one-operation rule had
  nothing to refuse. Both are errors now, from `apply_overrides`, so `validate` catches it. Spell
  the member as the derived table spells it.

`overlay_coherence_errors` is the file-level check by name if you want to run it directly.

## Related

- [`LAYOUT.md`](LAYOUT.md) — where the file sits, and what a rebuild keeps
- [`resolution.md`](resolution.md), [`frequencies.md`](frequencies.md),
  [`literature.md`](literature.md), [`gene_metrics.md`](gene_metrics.md),
  [`gene_validity.md`](gene_validity.md), [`clinical_assertions.md`](clinical_assertions.md),
  [`gwas_effects.md`](gwas_effects.md) — the targets with a dossier of their own
- [`clin_sig_concordance.md`](clin_sig_concordance.md) — the only target that can vindicate you
- [`logs.md`](logs.md) — the other record, and the one that applies nothing
