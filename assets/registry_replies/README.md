# Registry replies captured live

Real responses from the registry, kept so a test's stub answers in the shape the server gives
rather than one written from the model's docstring (F150 was a reader built on an invented shape).

- `rename_account_dry_run.json`: `RegistryClient.rename_account("sheep-dryrun", dry_run=True)` on the
  polygon (registry 0.30.0, format 0.8.4), 2026-11-13, by the saved rehearsal account `sheep`. A dry run
  changes nothing. The applied form could not be captured without renaming that account; the tests build it
  from this reply plus the fields `AccountRename` documents, and say so.
- `variant_claims_rs429358.json`, `variant_claims_rs1801133.json`, `gene_claims_apoe.json`:
  `RegistryClient.variant_claims("rs429358")`, `variant_claims("rs1801133")` and `gene_claims("APOE")` on
  production (registry 0.31.0, format 0.8.6), 2026-11-14 around 01:00 UTC, no token (catalog reads). rs429358
  is the case where nothing could be compared (`compared: 0`, `incomparable: {no_trait: 15}`); APOE carries 57
  claims, more than `registry_claims`' default `limit`. **No capture has a non-empty `conflicts.pairs`**: no
  pair of published modules disagreed on anything we asked, so the tests that read a pair build it in the
  shape `services/claims.conflicts` writes (`modules`, `genotype`, `trait_efo_id`, `effect_allele`,
  `directions`), and say so.
- Not kept as a file, measured the same night: the polygon (registry 0.30.0) answers both claims routes with
  `HTTP 404: Not Found`, and ignores `?pgs_id=` (47 of 47 modules for `PGS000018`), while production finds
  `antonkulaga/risk_impulsivity_snps` for `PGS000205` (and for `pgs000205`).
