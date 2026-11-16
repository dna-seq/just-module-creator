**Where it stands (2026-11-16).** 0.48.12 runs on just-dna 0.8.6 (enricher 0.8.7) and is current with the registry's 0.31 features. Held by the lead, acting for the pm.

**Results**
- ✅ just-dna 0.8 shipped (0.48.7). Both registries accept it; a test-registry dry run of a real module passes.
- ✅ GWAS pass back: one well-studied variant, 223 published associations, about 5 minutes at the Catalog's pace.
- ✅ Rows with no gene now get the genes within reach as query hints, one per position, each with its distance (0.48.8).
- ✅ Registry snapshot data can be looked up by key without downloading it, with each source's licence on every answer, and server-side enrichment can run extra passes and says what each did (0.48.8, fixed in 0.48.9).
- ✅ Renaming your registry account and claiming a namespace for a team, with the saved account kept in step after a rename (0.48.10).
- ✅ Looking up what published modules say about a variant, a gene or a PGS score, with disagreements between modules shown as facts, never verdicts (0.48.10; works on the main registry, the test registry still runs the older release).
- ✅ Every registry call an author would use now has a tool: team members, profiles, card subtitles, changelog and logo fixes, reviews, stars, namespace totals, and finding the rs-number at an old hg19 coordinate. The rest each carry a written reason. Also: enrichment now says which rows look like old-genome coordinates, and a citation can be checked by its PubMed Central id (0.48.11).
- ✅ A compile says which polars and python wrote its artifact, and a comparison with the published version names that version's, so a digest that moved with nothing authored changed has its reason. The review tools say a highlighted negative review still counts as curated (0.48.12).

**Next**
1. Renaming the `test-sheep` rehearsal namespace. Lead; ⏸ waits on the person (desk #255).
2. ✅ A note for Anton on his four published modules is drafted: `docs/HANDOUT-antonkulaga-modules.md`. His published versions hold up; it asks one question about two rows in the personality module. Sending it, or not, is yours.
3. ✅ A tool that searches trait names in the standard vocabularies, so a module's trait id is picked from real candidates rather than guessed (`search_trait_terms`, built; ships in the next release).
4. Row traceability: tried by hand on one module and it works: the record travels with the published module, and every row comes out traced, not traceable, or contradicted, as it should. Next is building the automatic recorder. Lead, after tomorrow's release.
