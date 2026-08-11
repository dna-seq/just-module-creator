# Findings blocked on an upstream change

Findings that need a change in `just-dna-format` / `-compiler` / `-enricher` /
`-registry` before they can close here. Each notes the defensive mitigation
already in place on our side.

A finding legitimately appears both here and in [dogfooding.md](dogfooding.md)
when we have mitigated it but upstream still owes the fix.

**Intake:** these are filed into `../just-dna-format/docs/CONSUMER_SUGGESTIONS.md`
as `S<n>` entries. Check there before filing — a second consumer hitting a known
one appends a corroboration rather than opening a new number. Write the note and
stop; never commit in that repo.

---

## F5 — resolution never reaches the non-SNP table families

**Filed upstream:** `CONSUMER_SUGGESTIONS.md` **S9** (opened by just-dna-lite,
2026-08-11; corroborated by us the same day) ·
**Status: the legibility half shipped in 0.5.3; the coordinates themselves are deferred to upstream RM43**

`compile_module` applies `resolution.csv` to the SNP core only. A module led by
`pharm_variants.csv`, `diplotypes.csv` or `pgs.csv` keeps exactly the coordinates
its author typed — so for an rsid-authored module, none.

Reproduced here twice with a one-row `pharm_variants`-only module: `chrom` and
`start` are null in the artifact both with and without a `resolution.csv` that
covers the variant, which rules out "no table was available" and leaves "this
family does not consult it". The same run demonstrably *read* the file — it
warned that VRS coverage in `resolution.csv` was 0/1 — while not applying it.

### What 0.5.3 shipped, and why it is the right half first

`_check_positional_joinability` now warns, per positional table, in both
`validate` and `compile`. Verified reaching our surface unchanged on the same
one-row reproduction:

> `pharm_variants.csv: 1 of 1 row(s) have no chrom+start, so this table joins by
> rsID only — a VCF whose ID column is empty matches none of them.
> **resolution.csv can place 1 of them**, and the compiler applies that table to
> variants.csv only.`

That second count is the actionable half, and it is exactly the distinction our
corroboration argued the run already held both facts to make: it separates *this
module was never enriched* from *the coordinates exist and this tier does not
apply them here*. An author cannot otherwise tell those apart, and they call for
opposite actions.

Deliberately a warning in both modes and never a `strict` error, which we agree
with: rsid-only identity is legal by these models' own rule, so escalating would
have the format tighten a field it left open — and the remedy is a compiler
change, not an authored edit. Refusing would make a correct module uncompilable
for something its author cannot clear.

**What is still open.** The coordinates are not materialized. Upstream's reason
is worth recording because it is not a scheduling excuse: filling them breaks
Principle 7, since `reverse_module` rebuilds the CSV from the parquet and a
filled coordinate returns as an *authored* one. `VariantRow.authored_ident`
exists to prevent exactly that and no 0.4-family model has an equivalent, so the
fix needs a new column on an existing parquet — 0.6 work, tracked upstream as
**RM43** with two smaller constraints alongside (`PharmVariantRow` has no `alts`
column, and `variant_key` is a property on these models so it is materialized in
no PGx parquet).

**Our mitigation is now redundant with upstream's warning** but stays, because it
tells an author what to do rather than what happened:
`skills/create-module/SKILL.md` says to supply the rsID for these tables and that
a consumer joins on `rsid` + `genotype`. We still ship no code workaround —
filling the coordinates ourselves would author a value the compiler did not
derive, which is the redundancy-bearing mistake the rest of this repo exists to
prevent.

**Closes when** RM43 lands.

---

## F10 — `resolve_with_ensembl=False` is the master switch for all resolution, and its name says otherwise

**Filed upstream:** `CONSUMER_SUGGESTIONS.md` **S14** (2026-08-11) · **Status:** open upstream

`compile_module(resolve_with_ensembl=False)` / `--no-resolve` reads as "do not go
out to Ensembl", which is a reasonable thing to want and the obvious flag to
reach for when building offline from a committed `resolution.csv`. It actually
disables resolution **entirely**, injected table included: every row compiles
with `chrom`/`start` null, and the compile **succeeds**.

**How this was mishandled on our side, which is the part worth remembering.** We
found it while building the wrapper, guarded against it, and then described the
guard in `README.md` as a feature — *"the wrapper cannot reach the flag that…"* —
without ever filing it. That is the intake rule backwards. The guard protects our
callers and nobody else's; the flag is still there for the next consumer, who gets
a green build and an empty module. Filed as S14 on 2026-08-11 and removed from the
README, which should describe what this plugin does rather than enumerate what
upstream gets wrong.

**Our mitigation, which stays:** `compile_module` pins `resolve_with_ensembl=True`
with `ensembl_cache=None`, so no agent driving our surface can reach the branch.
`CLAUDE.md` §2 forbids exposing a path to it, and the authoring docs say never to
pass it — that guidance is legitimately ours to give, because an author reading
`references/CLI.md` may well use the CLI directly.

**Closes when** upstream warns that a present `resolution.csv` went unread, or
splits the flag so the name matches the action.
