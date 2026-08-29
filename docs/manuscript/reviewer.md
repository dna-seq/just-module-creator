# Simulated Peer Review

**Paper:** "Creating and Sharing Genomic Annotation Modules with AI: The Just-DNA Ecosystem"
**Venue:** EASRP 2026

---

## Strengths

1. **Clean architectural separation.** The knowledge-path / sample-path split is the paper's best idea. Keeping the LLM out of VCF processing and genotype calling is a real design decision that most "AI for genomics" papers dodge. The compiler-is-not-a-correctness-gate argument (Section 3.4) is unusually honest for this space.

2. **The title-as-quote finding is genuinely useful.** 3,668 rows with a vacuous provenance check is a concrete, measured observation that applies beyond this system. It illustrates a class of verification failure (instrument that cannot fail) that other curation pipelines share but rarely surface.

3. **Honest limitations section.** No recall/precision claim is made, and the paper says why. That is stronger than reporting inflated numbers on two fixtures. The "how to read a green result" subsection is something most tool papers would never write.

4. **Practical registry design.** The polygon/production split with immutable production hashes is a real engineering contribution. The fact that three independent namespaces from non-developers published modules is meaningful adoption evidence, even at small scale.

5. **Schema-from-code, not schema-from-prose.** `describe_table` reading pydantic models rather than a hardcoded list is the right call. Most authoring tools carry a stale copy of whatever schema they launched with.

6. **The comparison table is fair.** Raw LLM gets all dashes except AI-assisted. ClinVar/ClinGen get most checkmarks. The paper does not overclaim its own column.

---

## Weaknesses

1. **N=8 modules, N=3 owners — this is a case report, not an evaluation.** The paper acknowledges this, but the Results section is still mostly a catalog inventory. Eight modules across three people (one of whom is the developer) cannot support a claim about usability or accuracy. The "five namespaces" framing inflates: two namespaces belong to one person's two modules.

2. **No creation evaluation was actually run.** Section 4.4 proposes a protocol and names two fixtures but reports no numbers. The paper promises "a framework for future evaluation" — that is a methods-only contribution at best. A reviewer expecting empirical results will find none.

3. **The comparison table (Table 1) compares unlike things.** VEP/ANNOVAR are annotation *engines*, not authoring tools. ClinVar is a *database*. GA4GH GKS is a *standard*. The "authoring capabilities" framing papers over a category error. PubMind-DB extracts from 41M abstracts at scale; the comparison gives it a dash on "versioned modules" without noting it solves a fundamentally different (and arguably harder) problem.

4. **No direct comparison with PubMind on overlapping variants.** PubMind is the closest actual competitor (LLM-based, produces structured variant annotations from literature). The paper describes PubMind in Related Work but never compares output quality, variant overlap, or even schema differences on the same gene. This is the comparison a reviewer will ask for.

5. **The companion paper does not exist yet.** It is cited six times and carries all the runtime benchmarks. If it is truly "in preparation," this paper cannot lean on it for performance claims. A reviewer may refuse to evaluate half the system on a promise.

6. **MCP/Claude Code dependency is deep but underexamined.** The tool surface is Anthropic-specific (MCP, Claude Code, Codex). The paper claims model-agnosticism in Section 3 but the skills and plugin manifests are Claude-specific. What happens with a different LLM host? This is a practical limitation that matters for reproducibility.

7. **No user study, no task timing, no error analysis.** How long does it take a non-specialist to create a module? How many corrections were needed on the AI drafts? What fraction of the 885 variants were AI-drafted vs hand-authored? These are the numbers that would make the usability claim land.

---

## Recommendations (ranked easy to hard)

### Tier 1 — Straightforward text edits (hours)

1. **Reframe Table 1 honestly.** Add a "Kind" column (engine / database / standard / authoring tool / extraction system) so the reader sees what is being compared. Drop the implicit claim that all rows solve the same problem. Alternatively, restrict the table to systems that produce author-editable, versionable annotation packages — which narrows it to OpenCRAVAT/OakVar, PubMind-DB, and just-module-creator.

2. **Report what you actually have on the 8 modules.** How many variants were AI-drafted vs hand-entered? How many curator corrections? How many revision passes? How many `record_override` entries exist in the logs? This is data you already have and it converts the catalog table from an inventory into evidence.

3. **Qualify the companion paper citation.** Either submit simultaneously or say "planned companion paper" and remove any claims that depend on its content (the 40-second annotation benchmark, the PRS engine). A reviewer cannot evaluate a citation to a paper that does not exist.

4. **State the model(s) used.** Which Claude model(s) produced the published modules? Which model(s) would the fixtures be tested on? Reproducibility requires this.

5. **Acknowledge the platform lock-in.** MCP is open-spec but the skills are Claude Code / Codex specific. A sentence in Limitations about what would need to change for another host is enough.

### Tier 2 — Modest new work (days to a week)

6. **Run the proposed evaluation on at least the two named fixtures.** Even N=2 with a single model gives a concrete number for variant recall, citation identity, and weight-sign accuracy. "We propose a protocol and here is what it measured on two cases" is much stronger than "we propose a protocol."

7. **Add a PubMind overlap analysis.** Pick one gene covered by both systems (the big_five_personality module with 330 variants is a candidate). Show the variant intersection, where PubMind found variants you missed and vice versa, and where the extracted annotations differ. This does not require running PubMind — their database is published.

8. **Report token / cost / time per module.** How many API calls and tokens did the largest module (474 variants) consume? How long did the authoring session take? This is the practical question any adopter will ask.

### Tier 3 — Substantial but doable (weeks)

9. **Build a proper evaluation set.** 5-10 expert-curated fixtures covering different table kinds (variant, pharmacogenomic, binning). Run the creation protocol 3 times each (to show variance). Report recall, precision, citation accuracy, and weight-sign agreement. This is what turns the paper from a systems description into an empirical contribution.

10. **A minimal user study.** Even 3-5 geneticists or bioinformaticians trying to create a module from a provided paper, with think-aloud or task-completion metrics, would be evidence. Compare time and error rate with "just give them the CSV template and the paper."

### Tier 4 — Hard / probably out of scope for this submission

11. **Cross-model comparison.** Run the same fixtures with GPT-4, Gemini, and an open model via a generic MCP client. The architecture claims model-agnosticism; testing it would be a contribution on its own.

12. **Scale test against PubMind's 1.3M variants.** Take PubMind's full database as ground truth for a large-scale recall analysis. This is a different paper, but the comparison table implicitly invites it.

---

## Overall Assessment

This is a well-written systems paper with honest limitations. The architecture is sound. The main gap is empirical: the paper proposes an evaluation without running it, compares to tools that solve different problems, and rests adoption evidence on 8 modules from 3 people. The title-as-quote observation and the polygon/production registry design are genuine contributions.

Academic code is typically 1-2 years behind shipping systems, and that cuts both ways here. The system is clearly ahead of what most groups ship — live schema, MCP tools, a working registry with content-addressed hashes. But the paper format still expects the kind of evaluation that a fast-moving tool cannot easily produce: controlled benchmarks on frozen fixtures. The strongest version of this paper leans into what it actually has — the authoring logs, the revision history, the measured vacuous-check problem — rather than gesturing at a benchmark it has not yet run.

**Recommendation:** Major revision. Run the evaluation protocol on the available fixtures, add the PubMind overlap, and reframe the comparison table. The system is further along than the paper currently shows.
