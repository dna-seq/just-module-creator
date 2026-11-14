**Where it stands (2026-11-14).** Released 0.48.9 runs on just-dna 0.8.5 with the registry's 0.30 features; main runs on 0.8.6 and adds the registry's 0.31 features. Held by the lead, acting for the pm.

**Results**
- ✅ just-dna 0.8 shipped (0.48.7). Both registries accept it; a test-registry dry run of a real module passes.
- ✅ GWAS pass back: one well-studied variant, 223 published associations, about 5 minutes at the Catalog's pace.
- ✅ Rows with no gene now get the genes within reach as query hints, one per position, each with its distance (0.48.8).
- ✅ Registry snapshot data can be looked up by key without downloading it, with each source's licence on every answer, and server-side enrichment can run extra passes and says what each did (0.48.8, fixed in 0.48.9).
- ✅ Renaming your registry account and claiming a namespace for a team, with the saved account kept in step after a rename (on main, not yet released).
- ✅ Looking up what published modules say about a variant, a gene or a PGS score, with disagreements between modules shown as facts, never verdicts (on main, not yet released; works on the main registry, the test registry still runs the older release).

**Next**
1. The next release, carrying the account tools and the variant lookups. Lead; today, after one dry run of a real module against each registry.
2. The other registry calls the plugin has no tool for (team members, reviews, stars, profile edits and more): each gets a tool or a written reason. Lead; waits on nothing.
3. Renaming the `test-sheep` rehearsal namespace. Lead; ⏸ waits on the person (desk #255).
