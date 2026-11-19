# EASRP 2026 reviews of this paper (Europe AI Summer Research 2026, EuroTech Federation)

Received by the corresponding author and recorded here on the person's word, 2026-11-19 ("record in full
somewhere and put in as todos"). The text below is the letter as it arrived, except the sender's email address,
left out because this repository is public. The reviews concern the EASRP submission, the version titled
"Creating and Sharing Genomic Annotation Modules with AI: The Just-DNA Ecosystem" (before the October
improvement run and the November changes). Each comment's handling is in `review-ledger.yaml` beside this file.

---

Dear Anton,

Thank you again for submitting your paper "Creating and Sharing Genomic Annotation Modules with AI: The Just-DNA Ecosystem" to Europe AI Summer Research 2026. As promised, here is the feedback from the researchers who reviewed it. Reviewers are anonymous; their comments are reproduced as they wrote them.

Each reviewer scored the paper out of 100 on five criteria: Technical soundness & methodology (/30), Originality & novelty (/25), Significance & impact (/20), Reproducibility & open science (/15) and Clarity & presentation (/10).

————————————————————
REVIEWER 1 — 70/100
Technical 17/30 · Originality 18/25 · Significance 14/20 · Reproducibility 12/15 · Clarity 9/10

Summary
This paper presents Just-DNA: an ecosystem for creating, validating, versioning, and distributing structured genomic annotation modules, including an MCP plugin that lets AI coding assistants draft and curate those modules. Its central contribution is moving AI-assisted genomic interpretation from transient code or chat output into editable, schema-validated artifacts with provenance, verification logs, deterministic compilation, and registry publication.

Strengths
Strong artifact design will logically separation. This makes review and correction feasible.
Authoring and individual-genome processing are separated, reducing unnecessary exposure of sensitive data.
Evaluation metrics distinguish multiple feature instead of collapsing errors into one score.
Research-only framing and limitations are explicit.

Weaknesses and limitations
Evaluation is too narrow for central reliability claims: three runs of one prompt on one paper is not sufficient.
No comparative experiment quantifies improvement over raw LLM, retrieval-only, or existing curation workflows.
Runtime claim for genome annotation belongs to companion paper; this paper should avoid using it as evidence for authoring-plugin performance or provide a minimal end-to-end benchmark.

Suggestions for improvement
Build blinded benchmark suite. publish prompts, source snapshots, gold curation, and scoring code.
Compare raw LLM, retrieval-augmented LLM, tool-only workflow, and full Just-DNA workflow across multiple models and hosts.
Add adversarial security evaluation: malicious papers, conflicting citations, false-but-valid identifiers, instruction-like source text, and attempted unauthorized registry actions.

————————————————————
REVIEWER 2 — 52/100
Technical 12/30 · Originality 12/25 · Significance 7/20 · Reproducibility 15/15 · Clarity 6/10

Summary
This paper presents the Just-DNA ecosystem, a set of tools that redirect general-purpose AI coding assistants from generating disposable analysis code towards authoring structured, versioned genomic annotation modules. The just-module-creator plugin exposes the toolchain as typed MCP tools inside Claude Code and Codex, so an assistant drafts CSV and YAML tables of variants, evidence, effect sizes and verbatim source quotes that are validated against a live schema and checked against reference databases such as dbSNP and HGNC. Modules can be compiled to Parquet, versioned, rehearsed on a test registry, and published to a shared catalog, with the consumer Just-DNA-Lite later joining them to a genome. The paper defines an evaluation protocol for variant recall, citation identity and effect-direction agreement, and reports catalog statistics from the first eight published modules across three independent namespaces.

Strengths
1) A timely and well-motivated premise: general-purpose language models are unreliable for genomics, fabricating variant identifiers and attaching real PMIDs to the wrong paper, and redirecting the assistant from generating disposable code to producing structured, reviewable data is a sensible response. 2) A thoughtful evidence and auditability design: authored values are kept independent of the checks that verify them (could this check have failed?), disagreements with reference archives are logged rather than silently resolved, and checks have three states (passed, failed, never ran) with the third recorded as a null. 3) Open, reusable engineering: the plugin is open-source (MIT), the module format is plain editable YAML and CSV, and the package-registry pattern lets independent authors version and share modules.

Weaknesses and limitations
1) The central benefit is not evaluated. The motivation is that an assistant generating code is unreliable, yet there is no empirical comparison against that baseline (raw LLM script generation or direct answering), so the claim that the workflow improves reliability is asserted rather than shown. 2) The evaluation is a smoke test. The quantitative evidence is three runs of a single prompt on one paper, scored near-perfectly against one expert curation, which cannot support claims about reliability or generality. 3) The catalog evidence is adoption-level. Eight modules across three namespaces, half of them from the development team, is a feasibility signal rather than evidence of correctness or usefulness, and the comparison to VEP, CIViC and PubMind is qualitative. 4) The validation does not measure what matters most. The provenance audit (using an article's title as its quote) is interesting but is not a hallucination rate, while free-text conclusions and the assistant's judgement about whether a source supports a claim are explicitly not scored.

Suggestions for improvement
1) Evaluate against the baseline the paper argues against: compare the module-authoring workflow with (a) an assistant generating analysis code and (b) an assistant answering directly, on the same tasks, scoring factual correctness (variant ID, citation identity, effect direction) and the reviewer effort each requires. 2) Scale and diversify the evaluation: multiple models and hosts, many papers and traits, several expert curators, with inter-rater agreement, and report per-module error rates against held-out expert-curated references. 3) Demonstrate downstream value: show that a module built with the pipeline yields correct genome annotations (or results comparable to a manual workflow) and quantify the review effort saved. 4) Report an explicit error or hallucination rate before and after the workflow rather than only an aggregate agreement score.

Questions for the authors
1) How was the expert-curated reference module constructed, who produced it, and how were disagreements between the three runs and the reference adjudicated? 2) Given that free-text conclusions and the judgement about whether a source supports a claim are not scored, how is a user to know that a published module reflects the source rather than the assistant's interpretation? 3) What fraction of the assistant's drafted rows require expert correction, and how does that compare with the raw-LLM baseline the paper argues against?

————————————————————
REVIEWER 3 — 48/100
Technical 15/30 · Originality 10/25 · Significance 8/20 · Reproducibility 10/15 · Clarity 5/10

Summary
The paper introduces the Just-DNA ecosystem, a framework designed to mitigate the inherent unreliability of LLMs in genomics. While researchers increasingly use assistants for genomic analysis, these models produce variant IDs, misattributing citations, or reversing allele directions. Instead of allowing LLMs to generate unverified output, the project shifts the LLMs role to producing structured, versioned, and schema-validated data modules. These modules consist of editable files (CSV, YAML) that link genomic variants to their genotypes, effect sizes, and verbatim evidence from literature.

Strengths
The paper addresses the problems of LLMs to hallucinate and producing unreliable output using structured schema validation. The method is designed for a human-in-the-loop and real passages from sources approach to further foster reliability and traceability.

Weaknesses and limitations
First of all, deriving health-related conclusions from personal genomic variation using LLMs should be treated with utmost care and the interpretation should be performed by experts. The audience of the paper remains unclear. The topic is very specialized and does not nicely introduce the topic, even though the bigger picture of personalized medicine, individual genetic analysis is a huge research topic and future field. The paper misses a clear benchmark of the proposed tool against pure LLM output or other methods.

Suggestions for improvement
The authors should clarify the audience of the paper and rewrite accordingly. Does it adress individuals, physicians or the ML community? A comparison to other tools would strengthen the claims, i.e. against the raw output of an LLM.

————————————————————
REVIEWER 4 — 86/100
Technical 25/30 · Originality 20/25 · Significance 18/20 · Reproducibility 15/15 · Clarity 8/10

Summary
This paper, together with a companion one that I did not review, is providing a way to use agentic AI in a more useful and rigorous way with genomic annotation data. It reports on the provision of a plugin 'ecosystem' for these assistants that allows a better division of labor between their ability to read papers, etc, and methods for storing, validating and sharing the results at scale.

(This reviewer provided a summary and scores only.)

————————————————————

We hope this feedback is useful for the next version of your work. If anything in the reviews is unclear, feel free to reply to this email.

Best regards,
Nicolas Bigeard
Co-Founder & Head of Research, EuroTech Federation
[email address left out: this repository is public]
