# Introduction

Genomic annotation connects variant calls to the knowledge that gives them meaning: trait associations, clinical classifications, effect sizes, and the evidence behind each claim. This knowledge is scattered across papers, databases, and preprints, and it changes as new studies appear. Turning it into something a computational pipeline can use requires structured, validated records with unambiguous variant identifiers, genome-build coordinates, and traceable citations.

Researchers increasingly use AI coding assistants such as Claude Code and Codex for this kind of work. These tools are powerful, but when asked to analyze variants they typically generate a script: code that may fabricate identifiers , attach a real PMID to the wrong paper , reverse an allele, or bypass established filters. Each session may produce slightly different code, and the result must be reviewed for correctness, efficiency, and security before it can be trusted. The output is a one-off answer tied to one session, not a reusable resource.

This paper presents the Just-DNA ecosystem, which gives these same assistants a different job. Instead of generating code, the assistant produces structured data: a *module* of editable CSV tables where each variant is linked to its studies, citations, effect sizes, and supporting passages. The input can be anything the assistant can read, from a single sentence describing a trait to a collection of papers or a summary from another model. Every variant is verified against reference databases such as dbSNP; dedicated checking tools validate gene symbols against HGNC, trait identifiers against ontology services, and flag decisions that require domain expertise. Once compiled to Parquet, Just-DNA-Lite joins the module to a genome . Modules are versioned and shareable: they can be kept locally, rehearsed in a test registry, or published for others to install and use. The same files can also be written or edited entirely by hand.

This paper makes four contributions:

1.  It describes the module contract shared by manual editors, AI-assisted authoring tools, versioned stores, and the genome-analysis consumer.

2.  It presents `just-module-creator`, an authoring plugin that exposes the public capabilities of `just-dna-format`, `just-dna-compiler`, `just-dna-enricher`, and `just-dna-registry` as typed Model Context Protocol (MCP) tools . The plugin reads the installed schema instead of carrying a copy.

3.  It defines how modules move between a local store, a test registry whose publications can be deleted, and the public catalog while preserving provenance and decisions that still require review.

4.  It defines an evaluation protocol for variant recovery, citation identity, and effect-direction agreement, and reports catalog statistics from the first eight published modules across three independent namespaces.

# Related work

#### Genome annotation and catalogs.

A variant call records what differs between a sample and a reference genome. Annotation adds information about that call, such as its predicted consequence, known clinical classification, reported trait association, or the conclusion assigned to a particular genotype. VEP, ANNOVAR, and OpenCRAVAT/OakVar perform this kind of lookup by joining a callset to established resources . ClinVar and the GWAS Catalog publish records that can supply annotation content , HGMD derives variant–disease associations from the literature through manual review , ClinGen provides expert curation within the ACMG/AMP framework , and ClinPGx consolidates PharmGKB, CPIC and PharmCAT into one pharmacogenomic resource . CIViC crowdsources cancer variant interpretation, anchoring every evidence item to a source publication ; its releases are database-wide rather than installable per-topic units, which makes it a source this ecosystem consumes rather than an alternative to it. The GA4GH Genomic Knowledge Standards define interoperable representations for variant annotations . The problem addressed here begins before the join: selected evidence must be turned into a reviewable, machine-checkable collection that can be distributed and applied consistently.

Table <a href="#tab:comparison" data-reference-type="ref" data-reference="tab:comparison">1</a> narrows the comparison to systems adjacent to the authoring task: annotation engines, extension-based annotation platforms, expert-curated knowledgebases, structured literature extraction, unconstrained model drafting, and `just-module-creator`.

<div id="tab:comparison">

| System | Kind / primary task |  |  |  |  |  |
|:---|:---|:--:|:--:|:--:|:--:|:--:|
| Ensembl VEP / ANNOVAR | annotation engine / consequence prediction against a callset | – | – | – | – |  |
| OpenCRAVAT / OakVar | annotation platform / user-supplied annotation extensions |  |  | – | – |  |
| CIViC | curated knowledgebase / expert-crowdsourced clinical interpretation | – |  |  | – |  |
| PubMind-DB | text-mined database / LLM extraction of variant–disease–pathogenicity records | – |  |  |  |  |
| Raw LLM | general-purpose model / unconstrained drafting | – | – | – |  | – |
| just-module-creator | authoring plugin / create, review, and publish installable modules |  |  |  |  |  |

Qualitative comparison of systems adjacent to annotation authoring. The rows have different primary tasks; the capability columns compare how their structured outputs are created, checked, and shared. Runtime annotation speed is outside this comparison and is covered in the companion platform paper .

</div>

<div class="minipage">

*Criteria.* *Versioned modules*: user-installable or distributable annotation units with explicit versions. *Schema validation*: structured records are checked against a declared machine-readable schema. *Provenance tracking*: record- or module-level source links travel with the output. *AI-assisted authoring*: a language model participates directly in creating or revising the structured output. *Shared catalog*: outputs or extensions are discoverable through a shared service. A dash means the capability is not part of the system’s core public workflow, not that no related function can be added around it.

</div>

#### Biomedical text mining and variant extraction.

Conventional named entity recognition systems such as tmVar3 and PubTator3 have improved gene and variant tagging in biomedical text . LitVar 2 links literature paragraphs with variant records from external databases, accelerating knowledge retrieval . However, these tools are largely limited to entity-level extraction and do not recover relational information such as variant-specific pathogenicity across disease contexts or the experimental evidence supporting a classification. PubMind applies instruction-tuned LLMs to extract variant–disease–pathogenicity associations directly from over 41 million PubMed abstracts and 5.4 million full-text articles, producing a database of approximately 1.3 million unique variants with contextual annotations . These systems demonstrate that LLM-based literature mining can recover structured variant knowledge at scale, but their output is a flat database rather than a versioned, schema-validated module that an annotation consumer can install and apply to a genome.

#### Factuality and tool use.

Language models can produce fluent text around a false identifier or citation . Benchmarks on genomic question-answering show that models hallucinate gene names, variant identifiers, and functional annotations . Retrieval-augmented approaches and tool use reduce the need to improvise when a model can call a typed operation instead . The Model Context Protocol provides a standard for connecting models to external tools . Biomedical MCP services can search literature, ontologies, and variant databases. just-module-creator uses the same general approach, then carries the result into module files that the rest of the Just-DNA pipeline can inspect and reuse.

#### Agent orchestration.

Many scientific-agent systems assign research and review to several model instances . The plugin described here does not require its own orchestration runtime. Claude Code or Codex supplies the agent, while the plugin supplies the tools and the written workflow. This paper evaluates that authoring path, not a particular choice of language model or agent-team topology.

# Method

## The module artifact

At the artifact boundary, a just-dna annotation module is an editable directory. It always contains `module_spec.yaml` and at least one recognized table. The table records the thing being annotated, such as a genotype, a diplotype, or a measured quantity. Evidence and machine-produced sidecars are stored separately. Compilation converts this human-readable directory into machine-readable Parquet files and a content-addressed `manifest.json` . The compiled artifact is what a consumer installs and joins to a genome.

The authored files are ordinary YAML, CSV, Markdown, and optional image files. A domain expert can open them in a spreadsheet to review and correct an AI draft without special tools. just-module-creator operates on this same directory rather than introducing a separate format for AI-produced content. The module describes how a genotype or measurement should be interpreted if a consumer encounters it. Just-DNA-Lite, or another compatible consumer, supplies the genome or measurement later.

The author does not need to supply this directory, or any CSV file, at the start of a session. Figure <a href="#fig:conversation-to-module" data-reference-type="ref" data-reference="fig:conversation-to-module">1</a> shows how a conversation entry—which can range from a trait name to a collection of papers—moves through routing, scaffolding, and review to a compiled module. The `/create-module` router identifies the appropriate entry point and stage.

<figure id="fig:conversation-to-module" data-latex-placement="ht">

<figcaption>From conversation to a usable module. Module files are intermediate artifacts created by the workflow, not required user inputs. Authored claims remain distinct from derived source records inside the editable workspace.</figcaption>
</figure>

Different claim types—variant associations, study evidence, pharmacogenomic diplotypes, copy-number ranges—belong to separate tables, each with its own schema. The plugin reads column definitions from the installed schema, so an author always sees the version accepted by the current compiler.

## Architecture and lifecycle

Module authoring and sample analysis remain separate until Just-DNA-Lite joins a compiled module to a local genome. On the authoring path, a person may edit the files directly or use an AI assistant to draft them. Both routes then pass through the same enrichment and compilation steps before the module enters a local or shared store. Figure <a href="#fig:architecture" data-reference-type="ref" data-reference="fig:architecture">2</a> shows the two paths and the boundary between them.

<figure id="fig:architecture" data-latex-placement="ht">

<figcaption>The two paths of the Just-DNA ecosystem. The knowledge path (top) produces a compiled module; the sample path (bottom) joins selected modules with a local genome. Modules reach the sample path through a local install or by downloading from the catalog. The compiler is deterministic and offline. Just-DNA-Lite produces an annotated report and enriched data that the user can filter.</figcaption>
</figure>

On the sample path, Just-DNA-Lite normalizes variants, joins them with selected modules, and produces annotated reports and enriched data that the user can filter. A whole-genome VCF is annotated in under 40 seconds; the companion paper  describes the sample path and polygenic risk score computation in detail.

Within `just-module-creator` the language model participates only in the knowledge path: it searches, reads and drafts. VCF filtering, module joins and polygenic scoring remain ordinary software steps with explicit inputs and repeatable code.

Table <a href="#tab:packages" data-reference-type="ref" data-reference="tab:packages">2</a> lists each component’s responsibility and boundary.

<div id="tab:packages">

| Component | Responsibility | Does not |
|:---|:---|:---|
| `just-module-creator` | research and authoring workflow | process a genome |
| `just-dna-format` | schema and identity rules | access the network |
| `just-dna-compiler` | validate, compile, reverse, and sign | access the network |
| `just-dna-enricher` | resolve, draft, and cross-check | decide scientific meaning |
| `just-dna-registry` | publish, discover, and download modules | author module rows |
| Just-DNA-Lite | filter VCFs, join annotations, and produce reports | define module schema or compiler rules |

Responsibilities across the Just-DNA ecosystem.

</div>

## Determinism, evidence, and responsibility

Within one compiler version, `just-dna-compiler` tests that a valid specification can be compiled, reversed, and compiled again without changing its authored content signature. just-module-creator calls that compiler and pins the resolution setting. [^2] It does not implement a second compiler or present the upstream round-trip tests as evidence that an assistant extracted a paper correctly.

First, authored values and their checks are kept independent: a value filled from the source that will later check it makes the check compare the source with itself. The design test is: *could this check have failed?* If not, it measured nothing (Section <a href="#sec:checks" data-reference-type="ref" data-reference="sec:checks">4</a>).

The compiler reports problems but does not edit authored values. just-module-creator is the authoring application, so its workflow permits edits. That permission comes with limits.

First, tool-mediated overrides append a record to `logs/authoring.log` and preserve a reason in `provenance.json`. A general hand edit is not captured automatically. The server therefore instructs an assistant to call `record_override` after such a change. This is a known gap between the desired provenance record and what the current tools can enforce.

Second, the workflow does not fill a value from the source that will later be used to check that same value. Such a check would compare the source with itself. The same problem appears when a row uses an article title as its `provenance_quote`: the title is guaranteed to occur in the article, so the resulting match provides no evidence that anyone located support for the row’s claim.

Third, disagreement with an archive requires review of both sides. An archive may lag a retraction, a meta-analysis, or a later reclassification. Replacing the module’s value with the archive’s value can therefore make a module worse. `record_override` stores which field differs, what the source said, who made the decision, and why the authored value should remain. The record does not turn the disagreement into a passed check.

An assistant may read retrieved full text and locate a `provenance_quote`. It must copy the passage verbatim and identify who located it in `StudyRow.curator`. This attribution helps a reviewer decide where to look closely. It does not transfer responsibility away from the human author. The assistant can also follow a citation into its supplementary tables to locate per-variant statistics—effect sizes, p-values, and allele frequencies—that the main text often summarizes but does not reproduce row by row.

## Local and shared module stores

A compiled module can reach a consumer through three routes (Figure <a href="#fig:architecture" data-reference-type="ref" data-reference="fig:architecture">2</a>): local installation into a Just-DNA-Lite checkout for testing with a VCF, publication to the test registry for a deletable rehearsal, or publication to the immutable public catalog. The registry runs its own enrichment and strict compilation on publish, so the stored artifact is the one the server produced, not a locally claimed digest. Inclusion in either catalog distributes a module; it is not scientific review, clinical validation, or endorsement.

## Evaluation dimensions

A scorer ships with the plugin. It measures variant recall over rsID–genotype pairs, citation identity (each PMID must name the intended paper, not merely exist), and effect-direction agreement, against an expert’s curation rather than a system output—scoring authored modules against a module the same system authored measures agreement with itself.

Two measurement choices are load-bearing. Recall is reported at two grains, because recovering the right variant with wrong genotypes and recovering half the variants exactly are distinct failures that partial credit averages away. *Decoy rate* replaces precision: a variant absent from one curation may still be correct, whereas a decoy is one an expert designated non-associated.

<div id="tab:scores">

| Run | rsID recall | Pair recall | Decoy rate | Citation recall | Direction |
|:----|------------:|------------:|-----------:|----------------:|----------:|
| 1   |        1.00 |        0.67 |       0.00 |            1.00 |      1.00 |
| 2   |        1.00 |        1.00 |       0.00 |            1.00 |      1.00 |
| 3   |        1.00 |        1.00 |       0.00 |            1.00 |      1.00 |

Three runs of one prompt scored against an expert-curated reference module, plugin version fixed.

</div>

Table <a href="#tab:scores" data-reference-type="ref" data-reference="tab:scores">3</a> reports three runs of one prompt on one paper. All three recovered the variant the paper supports, cited both it and the earlier study it replicates, agreed on effect direction, and introduced no decoy. Two matched the reference on every genotype row, including a homozygous row that asserts nothing because neither cohort observed a carrier. All three declined to propagate the seed paper’s description of the variant as stop-gained, which the study it cites classifies as intronic at the same coordinate.

The one divergence is a significance verdict at $`p \approx 0.07`$, read as *suggestive* by two runs and *not significant* by the third, which an aggregate score would have hidden. Agreement also measures the guidance and not only the runs: the validator names the missing genotype and a written rule states that a zero weight is a claim where a blank is not, so convergence shows the workflow is prescriptive, not that its output is confirmed.

A module can also be scored where no reference curation exists, by reading what it asserts against what it withholds. That reading corrected a prediction of ours: we expected a paper running no association test to yield no variant rows, and a run produced sixty—each recording the observation with direction and significance withheld. Row count is therefore not scored; whether the cells assert more than the source supports is.

# Results

The plugin can be installed from its GitHub repository in a single command (`/install-plugin` in Claude Code, or a repository URL in the Codex plugin marketplace). Once installed, the assistant gains access to 60 typed MCP tools (Appendix <a href="#app:tools" data-reference-type="ref" data-reference="app:tools">9</a>) and 20 skills—written workflow instructions that teach the assistant when to call which tool. In both Claude Code and Codex, skills marked as commands can be invoked directly by typing `/name` in the prompt.

With the plugin active, the assistant calls typed tools instead of generating code (Figure <a href="#fig:conversation-to-module" data-reference-type="ref" data-reference="fig:conversation-to-module">1</a>): enrichment adds coordinates and derived sidecars, compilation validates against the live schema, and the compiled artifact can be published to the registry and immediately applied to a genome. The checks described in Section 3.3 catch citation misattributions, identifier drift, and schema violations in practice—a measurement across 33 published `studies.csv` files (44,342 rows) found 3,668 rows where the `provenance_quote` was the article’s title, a passage that always matches its own full text and evidences nothing.

## Command menu

Seven of the 20 skills are user-invocable commands (Table <a href="#tab:skills-commands" data-reference-type="ref" data-reference="tab:skills-commands">15</a>), exposing the workflow through intentions rather than internal stages. `/create-module` is the entry point: it reads where the author is actually standing—a trait, a handed bundle, a directory somebody else left—and routes to the stage that owns the work. The remaining thirteen skills are guides, which a router loads by naming their path when the assistant reaches the corresponding lifecycle stage. A guide is deliberately not matched from its own description: that is what keeps thirteen documents out of every session’s prompt, and it is why a guide nothing links to is unreachable rather than merely quiet.

## Production catalog

At the time of writing, the public catalog holds eight published modules across 19 versions and three independent namespaces. Table <a href="#tab:catalog" data-reference-type="ref" data-reference="tab:catalog">4</a> summarizes the published modules.

<div id="tab:catalog">

| Module                  | Variants | Studies | Genes | Versions        |
|:------------------------|---------:|--------:|------:|:----------------|
| big_five_personality    |      330 |     390 |   185 | 4               |
| risk_impulsivity        |      474 |       – |   325 | 1               |
| cognitive_intelligence  |       32 |       – |    31 | 1               |
| aggression_anger        |       28 |       – |    22 | 1               |
| bodybuilding            |       13 |       – |    13 | 1               |
| placebo_response (v2)   |        3 |       – |     3 | 2               |
| placebo_response_claude |        3 |       – |     3 | 1               |
| lactose_tolerance       |        2 |       8 |     1 | 2               |
| **Total**               |  **885** |         |       | **19 versions** |

Modules published to the public catalog as of August 2026. All modules target GRCh38 and were compiled with strict resolution.

</div>

The modules span three independent namespaces from three owners. The largest module (`risk_impulsivity_snps`, 474 variants across 325 genes) and the smallest (`lactose_tolerance`, 2 variants in 1 gene) both compiled with strict resolution and fully resolved coordinates. The `big_five_personality_snps` module went through four published versions (1.0.0 through 2.1.0), illustrating the revision workflow: 1.0.0 was the initial GWAS Catalog extraction, 1.0.1 back-populated schema axes, 2.0.0 added polygenic score references, and 2.1.0 corrected the weight normalization.

Modules authored with `just-module-creator` carry `curator: ai-module-creator` in their manifest authorship records. Three modules were authored by people who are not the plugin’s developers, indicating that the tool surface is usable beyond the original team.

## Evaluation protocol

The creation evaluation begins with an expert-checked fixture. Each fixture contains a free-text prompt and the `module_spec.yaml`, `variants.csv`, and `studies.csv` that the assistant should recover. The generated module is compared with the fixture on three questions:

- Variant recall is the fraction of ground-truth $`(\textit{rsID},\textit{genotype})`$ rows present in the generated module.

- Citation identity requires every cited PMID to exist and to name the paper indicated by the title returned during search. Existence alone is insufficient.

- Weight-sign accuracy measures whether the generated effect direction agrees with the fixture. Magnitude is reported separately because a module weight is an authored choice and is not copied from a GWAS beta.

The development fixtures `fto_bmi` (one locus at rs1421085) and `longevity_2026` are available in the repository. A larger adjudicated set and repeated runs are needed to support a performance claim. We therefore report no recall or precision estimate in this paper and present the protocol as a framework for future evaluation.

## Passing checks and what they actually measure

Several outputs look reassuring while answering a narrower question than a reader may expect. Strict compilation checks reproducibility and applies the compiler’s blocking rules; it does not establish biological correctness. A digest match likewise shows that bytes or authored content agree under a specified comparison.

A source timeout produces an unknown result, not a negative one and not a pass. The tools preserve this distinction with null and unknown values. The title-as-quote observation above is another illustration: a green check can mean that the instrument could not have failed rather than that it found something.

The evaluation protocol counts none of these as evidence of accurate extraction. Compiler round-trip behaviour is tested by `just-dna-compiler` and is not counted again as module creation accuracy.

# Discussion

Genomic data is becoming personally accessible, and people already use AI assistants—coding tools such as Claude Code and Codex, or plain chat applications such as ChatGPT—to interpret their results . Restricting this is not viable, so the more effective response is to make the work happen in the open, where domain professionals can review what others publish and the tools enforce structure. A module is visible, reviewable, and correctable; a one-off chat session is none of these.

The safety concern is real but cuts deeper than AI. Candidate-gene studies have failed to replicate , GWAS effect sizes routinely shrink in independent cohorts , direct-to-consumer tests have produced false-positive rates above 40% , and variant reclassifications have led to genetic misdiagnoses . The ecosystem is therefore explicitly research-only: a module that faithfully reflects a study which later fails to replicate is not wrong on its own terms, but a user acting on it may be harmed all the same.

The registry turns individual effort into shared infrastructure: authors version, extend, correct, and republish modules—the pattern software engineering solved with package registries. The catalog already holds modules from independent authors, and the plugin’s MCP tools are listed on a public listing service so other agent platforms can use them independently. Modules contain no individual-level data; Just-DNA-Lite applies them locally, so a person’s VCF never leaves their machine and annotation runs raise no GDPR concerns. The knowledge travels through the registry; the genome does not.

#### Limitations.

The module system launched in August 2026. We are developing mechanisms to involve genetic counselors and domain-expert agents in quality evaluation, and to communicate to citizen scientists that many modules reflect early-stage research rather than clinical-grade evidence. Every run scored here used one model through one host, so the results say nothing about model or host sensitivity. Free-text conclusions are not scored at all, and the assistant’s judgement about whether a source supports a claim remains a reviewer’s question. Coordinates are declared rather than translated: `module_spec.yaml` names a `genome_build` and the toolchain refuses to infer one. Liftover belongs to the source or the consumer; the PGS Catalog already distributes per-assembly positions . Runtime benchmarks are in the companion paper .

# Conclusion

Annotation knowledge that lives in a chat session dies with it. The Just-DNA ecosystem gives an AI assistant a different job—producing a versioned, schema-validated module instead of a script—so the work survives review, correction and reuse by someone else. What makes that more than a file format is what a module keeps separate: authored claims stay distinct from derived records, a check that could not run says so, and every published module carries the evidence for its own rows. Eight modules from three namespaces, half of them from authors outside the development team, show the path is functional today.

The software is open-source and intended for research use only.

# Code and data availability

- **just-dna-format, just-dna-compiler, and just-dna-enricher**: <https://anonymous.4open.science/r/just-dna-compiler> (schema, reference compiler, and enricher).

- **just-module-creator**: <https://anonymous.4open.science/r/just-dna-registry> (MCP server, Claude Code and Codex plugin manifests, skills; MIT).

- **Just-DNA-Lite**: <https://anonymous.4open.science/r/just-dna-lite> (local VCF processing, annotation, and reporting; described in the companion paper ).

- The public catalog and the test registry are live at URLs provided in the anonymized repositories.

# Appendix

# Research use only

Annotation modules summarize published association findings. They are not clinical-grade evidence. The authoring plugin does not make individual-level predictions and does not open a genome. Just-DNA-Lite and `just-prs` process sample data for research and educational use; their reports and scores are not diagnoses or medical advice. Language that implies causation, such as “causes” or “guarantees,” is outside the scope of a module written with this plugin.

# Plugin surface: tools and skills

A Claude Code or Codex plugin is a bundle of two kinds of asset. **MCP tools** are typed operations the assistant can call—each has a name, typed inputs, and a structured return value. **Skills** are written instructions loaded into the assistant’s context on demand; they teach the workflow that the tools serve, including when to call which tool and what to do with the result.

## Tools (60)

The tools are organized into a core set (always listed) and nine optional groups that a session can reveal incrementally via `toolbox`. Table <a href="#tab:tools-core" data-reference-type="ref" data-reference="tab:tools-core">5</a> lists the 18 core and meta tools; Tables <a href="#tab:tools-evidence" data-reference-type="ref" data-reference="tab:tools-evidence">6</a>–<a href="#tab:tools-closing" data-reference-type="ref" data-reference="tab:tools-closing">14</a> list the nine groups. Registry writes require a token obtained through `authenticate`. Literature and enrichment requests share a single pacing gate, including the NCBI budget.

<div id="tab:tools-core">

| Tool | Purpose |
|:---|:---|
| `list_tables` | List authorable table kinds and what each row represents |
| `describe_table` | Describe one table kind: every column, type, vocabulary, and pick-list |
| `table_requirements` | The three shapes of requiredness for a table kind |
| `describe_machine_table` | Describe a machine-written sidecar: columns, types, vocabulary |
| `get_template` | Get a CSV template (header only, or header plus stub rows) |
| `scaffold_module` | Create `module_spec.yaml` plus stub CSVs; never overwrites |
| `lint_rows` | Lint CSV text against a table kind (writes nothing) |
| `validate_module` | Pre-flight a spec directory (writes nothing) |
| `compile_module` | Compile a spec directory into Parquet plus `manifest.json` |
| `draft_from_clinvar` | Draft `variants.csv` and `studies.csv` from ClinVar |
| `enrich_module` | Resolve rsIDs to coordinates and mint VRS identifiers |
| `literature_search` | Find papers behind a row; confirm a PMID names the intended paper |
| `lookup_citation` | Check a PMID or DOI and read back which paper it names |
| `lookup_variant` | Look up one variant: loci, alleles, ClinVar calls, rsID currency |
| `record_override` | Log that an authored value deliberately outranks a source |
| `registry_register` | Create a registry account and mint its API key |
| `authenticate` | Provide a registry token to unlock write tools for this session |
| `toolbox` | List optional tool groups and reveal them to the session |

Core tools (always listed) and the meta-tool.

</div>

<div id="tab:tools-evidence">

| Tool | Purpose |
|:---|:---|
| `lookup_open_access` | Where a paper may legally be read, and on what terms |
| `fetch_fulltext` | Retrieve a paper’s text so the assistant can read and quote it |
| `paper_citations` | Papers that cite this one, or the papers it cites |
| `list_supplementary` | Inventory the supplementary files attached to a paper |
| `fetch_supplementary` | Download one supplementary file to the cache |
| `describe_supplementary` | Sheets in a downloaded workbook and their column names |

[^1]: Anonymized repositories: <https://anonymous.4open.science/r/just-module-creator>, <https://anonymous.4open.science/r/just-dna-format>, <https://anonymous.4open.science/r/just-dna-registry>.

[^2]: The plugin always calls the compiler with `resolve_with_ensembl=True`. The parameter name is misleading: setting it to false disables all resolution, including an injected `resolution.csv`, and the compiler can then succeed with null coordinates that cannot match a VCF.
