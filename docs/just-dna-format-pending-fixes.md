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
2026-08-11; corroborated by us the same day) · **Status:** open upstream

`compile_module` applies `resolution.csv` to the SNP core only. A module led by
`pharm_variants.csv`, `diplotypes.csv` or `pgs.csv` keeps exactly the coordinates
its author typed — so for an rsid-authored module, none. Nothing warns.

Reproduced here twice with a one-row `pharm_variants`-only module: `chrom` and
`start` are null in the artifact both with and without a `resolution.csv` that
covers the variant, which rules out "no table was available" and leaves "this
family does not consult it". The same run demonstrably *read* the file — it
warned that VRS coverage in `resolution.csv` was 0/1 — while not applying it.

**Our mitigation:** documentation only, which is all an authoring surface can do.
`skills/create-module/SKILL.md` tells authors to supply the rsID for these tables
and states that the compiled rows carry no coordinate, so a consumer joins on
`rsid` + `genotype`. We ship no code workaround: filling the coordinates
ourselves would author a value the compiler did not derive, which is exactly the
redundancy-bearing mistake the rest of this repo exists to prevent.

**Closes when** upstream either resolves those families too (a digest-moving
change, so 1.0) or warns at compile time that resolvable rows were left without
coordinates (cheap, non-breaking, digest-neutral).
