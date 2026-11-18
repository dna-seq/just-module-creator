**Where it stands (2026-11-18).** 0.48.14 runs on just-dna 0.8.6 (enricher 0.8.8) and is current with the registry's 0.32 features. Held by the lead, acting for the pm.

**Results**
- ✅ just-dna 0.8 shipped (0.48.7). Both registries accept it; a test-registry dry run of a real module passes.
- ✅ GWAS pass back: one well-studied variant, 223 published associations, about 5 minutes at the Catalog's pace.
- ✅ Rows with no gene now get the genes within reach as query hints, one per position, each with its distance (0.48.8).
- ✅ Registry snapshot data can be looked up by key without downloading it, with each source's licence on every answer, and server-side enrichment can run extra passes and says what each did (0.48.8, fixed in 0.48.9).
- ✅ Renaming your registry account and claiming a namespace for a team, with the saved account kept in step after a rename (0.48.10).
- ✅ Looking up what published modules say about a variant, a gene or a PGS score, with disagreements between modules shown as facts, never verdicts (0.48.10; works on the main registry, the test registry still runs the older release).
- ✅ Every registry call an author would use now has a tool: team members, profiles, card subtitles, changelog and logo fixes, reviews, stars, namespace totals, and finding the rs-number at an old hg19 coordinate. The rest each carry a written reason. Also: enrichment now says which rows look like old-genome coordinates, and a citation can be checked by its PubMed Central id (0.48.11).
- ✅ A compile says which polars and python wrote its artifact, and a comparison with the published version names that version's, so a digest that moved with nothing authored changed has its reason. The review tools say a highlighted negative review still counts as curated (0.48.12).
- ✅ Searching trait names to pick a module's ontology id from real candidates; the check before publishing now reads every log file that ships; a publish whose files name another version is refused; comparing with the published version lists files added or removed (0.48.13).

- ✅ Each module now keeps a record of how its rows came to be (searches, articles read, rows written, decisions no edit shows), and `trace_module` reads every row back against it; registry 0.32 adopted; publishing refuses a module name that differs from its spec (0.48.14).
**Next**
1. Release 0.48.15 (on main now: the ledger survives tables written by script, the author's answered questions are counted beside the decisions recorded as theirs, two leftover upstream workarounds removed). Lead; 📅 2026-11-19.
2. Letting the author see and approve the wording of a decision before it is recorded. Lead; 🔨 next, unattended.
3. Renaming the `test-sheep` rehearsal namespace. Lead; ⏸ waits on the person (desk #255).
