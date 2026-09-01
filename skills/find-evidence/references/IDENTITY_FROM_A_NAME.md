# When a source publishes a name and no identifier

`N150fs (c.448delA)`. `IVS2+1G>A`. `D1709N`. A source hands you a variant **name**, leaves every
identifier column empty, and `lookup_variant` cannot help — it needs an rsID or a coordinate, which
is exactly what the record does not have. The name is not a shortfall in the record. It **is** the
record, and an allele registry will hold the allele it names.

**Read this before deciding a record is unresolvable.** In the survey this comes from, 35 of 43
such records resolved, 2 were withheld with both candidates recorded, and 6 had no identity to find.

---

## Where this comes from, and where the full procedure lives

The complete procedure is upstream's, and it is the evidence: **`../just-dna-format/docs/probes/`**
— `IDENTITY_FROM_A_NAME.md` is the source-agnostic handout, `CIVIC_IDENTITY_PROTOCOL.md` names the
variant behind every rule and carries the measurements, `CIVIC_UNRESOLVED.md` is the per-record
answers. **Where this file and the protocol disagree, the protocol wins** — it is the one with the
measurements attached.

Derived from two independent probes over one dated release, 2026-09-01: 43 records, 313 recorded
queries, three read-only credential-free services. Counts here are over those probes and are not a
claim about any other corpus.

**One tool of ours implements one rung of it**: `lookup_allele_identity` asks the ClinGen Allele
Registry what allele an expression names. **Everything else on this page is yours to do** — reading
the name, pinning the transcript, constructing the readings, choosing between two that both resolve.
That split is not tidiness: four of the 33 identities the survey produced needed a judgement no
lookup makes.

---

## The three outcomes, and two of them are not interchangeable

| outcome | means | requires |
|---|---|---|
| **resolved** | one candidate survives, named by a service — or several survive and a ranked discriminator picks one | the query that produced it, and **every** candidate kept beside it when a discriminator chose |
| **not_found** | asked, nothing answered. **Never written as "does not exist"** | the failed queries stored beside it |
| **no_identity_exists** | the name denotes a **class** of event, so no allele can satisfy it. Decided *before* any lookup | a stated reason |

`not_found` is what an ambiguous **allele** produces; `no_identity_exists` is what a class **label**
produces. A pass over a mixed corpus that returns only one of them has a classification bug.

---

## Before you spend a request

**Diff the source's snapshots.** A record the source has since filled needs no probe at all.

**Do not read staleness into a timestamp.** 21 records shared one review date — and so did 753 of
1,999 rows in the same file. It was a bulk-import stamp. A date shared by a third of a corpus says
nothing about any record in it.

---

## 1 · Pin the numbering frame per GENE, not per record

A `c.` or `p.` number means nothing until a transcript is named, and **the frame is a property of the
gene**. This is where the largest mistake in the original survey lived: it looked for a transcript
field on each *record*, found one on 2 of 31, and wrote off the other 29 as unreachable — a false
"permanent floor" that reached three documents and cost 39 variants.

- **Calibrate against the source's own resolved records.** Strongest available whenever the source
  resolved other variants in the same gene: 114 of 114 siblings agreed in one probe. It also gives
  you the frame the *curator* used, which matters when the source predates MANE.
- **MANE Select is a default, not an answer.** Cross-check it against the numbering the name implies.
  Two genes in eleven needed more: one used legacy isoform numbering offset by 27 — settled by
  translating each isoform's CDS and **locating the residue**, never by applying a remembered offset.

### The trap that costs the most time

Submit `NM_000551.3:c.197_220del` and the registry answers titled `NM_000551.4:c.198_221del`. It
looks exactly like a version bump shifting numbering by one. **It is not** — verified live:

```
NM_000551.3:c.499C>T  ->  CA020450
NM_000551.4:c.499C>T  ->  CA020450      identical
```

Both versions return the same identifier. The shift is HGVS's 3′ rule renormalizing a deletion inside
a repeat, plus the registry independently titling in the newest version it knows — two unrelated
behaviours that read as one causal story. Believing it invites correcting a whole gene's positions by
one, **and** teaches you to wave through a genuine one-base mismatch as an artefact. The CDS *mRNA
offset* does move on a version bump; `c.` numbering is CDS-relative and is untouched.

---

## 2 · Classify the name before any lookup

Two classes are terminal, and getting this wrong spends requests on records that can never resolve.

| class | looks like | route |
|---|---|---|
| class label | `TRUNCATING MUTATION`, `Rearrangement`, a cytoband range | terminal → `no_identity_exists`. **Do no allele lookup** |
| multi-alteration | two alterations in one name | split; run everything per part. **Never mint one identity for the record** |
| legacy insertion | `c.204insG` | two readings — generate both |
| legacy redundant-base | `c.430delG` | drop the asserted bases *after* checking them |
| legacy intronic / protein | `IVS2+1G>A`, `R135fsX177` | do **not** convert structurally; use the discriminators |
| modern HGVS | `c.180del` | one reading |
| protein substitution | `D1709E` | every single-substitution route to that residue; often more than one |

**Never send a legacy form itself** — it returns HTTP 400. Measured: across one gene's 314 records,
legacy-spelled insertions were **0 of 14 resolved** against a corpus otherwise ~83% resolved. A
resolver that passes the source's name through unmodified fails on exactly this class, silently.

`c.204insG` does not say which side of position 204 the base goes. Generate both — `c.204_205insG`
and `c.203_204insG` — and send them together. Verified live: both return `CA913189244`, so there was
never a choice to make. A **different** id on each proves the readings are genuinely different
alleles, and then it is a judgement about your row.

---

## 3 · Ask — `lookup_allele_identity`

```
lookup_allele_identity(expressions=["NM_000551.3:c.204_205insG", "NM_000551.3:c.203_204insG"])
```

Send every candidate reading in one call. `collapsed: true` means they named one allele.

**Five outcomes, and the tool keeps them apart because they mean different things:**

- **`registered`** — the registry holds it and names it (`caid`).
- **`unregistered`** — well-formed, not held. **Not "does not exist"**: 9 of 20 resolved identities
  in the survey carried no external cross-reference at all. Registration is not fame.
- **`reference_mismatch`** — the base you called reference is not the one at that position. This is
  the most informative answer the service gives: it is **evidence about direction**, it names the
  actual base, and it is how an inverted ref/alt is caught. Submit the opposite expression.
- **`malformed`** — the expression could not be read, so **no allele was asked about** and no
  negative may be recorded from it.
- **`unavailable`** — the service did not answer. Never a negative.

**A 200 is not a hit.** The registry returns HTTP 200 with a populated payload and a blank-node id
for an allele it does not hold; the tool decides on the identifier, never the status. If you ever
drive the endpoint by hand, that is the control you must run.

---

## 4 · Discriminate — ranked by what each one *cannot* settle

When more than one candidate registers, these separate them. **The half that matters is the second
column**, and none of it is a tool call.

| | discriminator | cannot settle |
|---|---|---|
| 1 | Which allele does a curated record attribute to **the paper this record itself cites**? Settled four records single-handedly | an allele the curated database does not hold. Silent, not negative |
| 2 | **Legacy alias lists** in the curated record — the only thing that resolves legacy notation, and it resolves it outright | anything uncurated; and it cannot say a legacy name is *absent* rather than differently spelled |
| 3 | Only one candidate is registered | anything where both are — 5 of 11 legacy insertions |
| 4 | The **direction test**: submit both opposite expressions and let the service reject one | which allele the curator *meant*. It says which base is reference, nothing more |
| 5 | External corroboration on exactly one candidate | a row where both carry one, or where two databases disagree in *kind* |
| 6 | Protein-consequence concordance | anything alone, where the source's protein names drift — see the binding rule |
| 7 | Second-service agreement on an identifier (19 of 19 agreed) | which of two alleles at one position is meant. A corroborator, never a discriminator |
| 8 | General web search | indels, effectively. Run it last, believe it least |

### The binding rule — settle this before using 6

**The DNA-level edit is the identity anchor. The protein fragment discriminates between candidate
readings; it is never a veto.**

In one probe the source's protein name was off by one from the correct consequence of the source's
**own** cDNA fragment in 6 of 22 rows. The discordance is internal to the name, so any correct
identity disagrees with it the same way — treating the protein name as a veto rejects every true
answer. What must match is the **consequence class** (frameshift / nonsense / in-frame / synonymous /
missense); the **residue number is advisory**.

One correlation worth knowing: rows whose protein name was exactly right were the ones spelled in
modern HGVS. A legacy protein name was transcribed from a paper; a modern one was computed.

---

## 5 · When to withhold — each rule exists because a record forced it

Withholding is a result, not a failure to finish.

| | rule |
|---|---|
| **R1** | Two candidates both register and nothing separates them — **withhold and report both ids**. Resolve neither |
| **R2** | The source's name matches **neither** candidate: that is a second defect, not a tiebreak |
| **R3** | A name whose two halves name different **real** alleles is a defective name. Resolve both, adjudicate by literature, and **record the defect as a finding** — it is worth more than the resolution |
| **R4** | If the direction test says the source means the **reference** allele, the identity is a reference expression. `variants.csv` cannot carry it: a row needs an alt |
| **R5** | A **position-level** identifier does not distinguish alleles at that position. Say which allele is meant and whether the identifier can carry it |

---

## What this cannot do, and it is the section to read first

Roughly **one record in eight needed a human**. These are decisions the procedure reaches and hands
back — no tool here will make them, and a script that appears to has guessed:

- **Which legacy convention a paper used.** A structural derivation from the exon table gave one
  intron; the right answer was another, because legacy papers numbered exons from the first *coding*
  exon. Both readings were real registered alleles ~9 kb apart, so nothing in the lookup flagged it —
  a confident wrong answer.
- **Which half of a self-contradictory name to believe.**
- **Whether the source's protein name is wrong rather than the identity.** That rests on a pattern
  noticed *across the set*; on a single row in isolation there is nothing to notice.
- **Whether one line of evidence is enough.** Record it resolved with both candidates kept and the
  single-line basis stated, so a stricter reader can take it as withheld.
- **Whether a database's *kind* is an argument.** Preferring a germline database because the row is
  germline is an argument about database kind, not evidence about the allele. Decide it explicitly.
- **When a negative is wide enough.** "Not in the database" from a name search is nearly worthless.

**Then: `no_identity_exists` and `not_found` are different, `unregistered` is neither, and a name
that resolved to two alleles resolved to none.**

---

## Two things that will bite the corpus, not the record

- **The premise is half wrong.** "A name-only record must be a famous allele with a forgotten
  identifier" held for fewer than half. The *identity* existed for nearly all of them; the *fame* did
  not. Do not size this work by how well-known the variants look.
- **Sources duplicate themselves.** Three unresolved records named alleles the same source had
  already resolved under a different record. A pass that reaches both maps two record ids onto **one
  allele** — which touches deduplication, grouping, and any "already present" logic downstream.

---

## The ordered procedure

```
 0. diff the source's snapshots       -> already filled? stop.
 1. pin the numbering frame PER GENE  -> siblings if any, else MANE, justified
 2. read the name, classify           -> class label | multi | legacy | modern
 3. class label?   -> no_identity_exists, with a reason. NO allele lookup.
 4. multi?         -> split; run per part; NEVER one identity per record.
 5. construct EVERY candidate reading -> both readings of a legacy insertion
 6. lookup_allele_identity(all of them)
 7. collapsed?     -> same id for both readings? there was no ambiguity.
 8. discriminate in rank order        -> stop at the first that answers
 9. still >1?      -> withhold. Report BOTH ids.
10. writing a row? assert the ref base against the sequence, and mind R4/R5.
```
