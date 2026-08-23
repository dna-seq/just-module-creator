# Roadmap history

Items no longer on [ROADMAP.md](ROADMAP.md) — **shipped**, or **deferred with a
reason**. Nothing is deleted; it is relocated. Newest first.

An item that left the roadmap because the work turned out not to be ours is not
here: it is filed upstream as an `S<n>` and tracked in
[just-dna-format-pending-fixes.md](just-dna-format-pending-fixes.md).

---

## RM27 — check the conclusion against the row it sits on

**Severity:** medium · **Status: CLOSED 2026-08-24 — shipped, both rules, and the measurement
reproduces exactly.** · **Opened** 2026-08-22

`conclusion` is the sentence a person reads about themselves, it is `required: true`, and
nothing checks it against anything — including the other cells on its own row. `lint_rows`
was given twelve real rows in run 2 and returned zero errors and zero warnings while four of
them said something that contradicts the row they are on: a homozygous-alt row opening with
the reference homozygote's sentence, a `risk` state under prose reading *"is not
increased"*, and two rows whose conclusions are byte-identical under different genotypes.

**This proposal is unusually well founded for a roadmap entry, because that run implemented
it and measured it.** Over 1,418 rows in six modules, the rule "the conclusion names a
genotype token built from alleles that appear at **this rsID's own locus**" found 20 rows,
of which roughly twelve are real and six severe — one module has the `C/C` and `A/A`
conclusions swapped at a locus where all three rows carry `state: neutral, weight: 0.0`,
and another scores `T/T` as `protective, +1.2` under text saying `GG` is protective. Measured
precision about 60%, **which is why the recommendation is `warning` and not `error`**. The
locus constraint is what makes it usable: an earlier version flagged `"TG"` inside *"raised
plasma triglyceride (TG) levels"*, and requiring the token to be built from alleles at that
site excludes it by construction.

A second rule — two rows at one rsID carrying identical conclusions under different
`state`/`weight` — found 492 groups, 480 of them in one GWAS port where a heterozygote and a
homozygote share one sentence and differ only in dose. **That one is a question rather than a
defect**, and the point is that nothing raises it and the author has no way to record having
decided it. File it as a hint, not a warning.

`module-curate` names the conclusion as a cell only a pilot may settle, which is right and
is not in tension with this: "only a human may write it" is not "nothing may check it", and
the plugin currently treats them as the same.

> **Shipped in `authored_checks.py`, surfaced through `lint_rows("variants.csv", …)` and
> `validate_module`'s `authored_findings`.** Both entry points were already plumbed for the
> repeated-quote rule from `RM17`; this widened them from `studies.csv` to both tables.
>
> **The measurement was reproduced before the rule was believed.** The six curated modules
> are still on disk in `just-dna-lite/data/interim/v1_port/`, so the implementation was run
> over the same 1,418 rows rather than written from the prose: **20 rows on rule 1 and 492
> groups on rule 2, per module identical to the published table.** That is what makes the
> quoted ~60% precision a property of *this* code rather than of a script nobody kept.
>
> **One thing the run's numbers taught that its prose did not.** A first pass here also matched
> the *slashed* spelling — `C/A`, the one `genotype` itself uses — and got 24 instead of 20. All
> four extras were the same sentence: `"rs2943634 C/A single nucleotide polymorphism"`,
> `"Two SNPs, rs1042718 (C/A) and rs1042719 (G/C)"`. In prose the slashed form names *the SNP's
> alleles*; only a doubled bare letter is unambiguously a claim about somebody's genotype. So the
> matcher is bare-token-only, and the reason is in its docstring — the count is the evidence, not
> the authority.
>
> **Levels are as the roadmap specified and for its stated reason.** Rule 1 is a `warning`
> because precision is ~60% and a rule right six times in ten belongs in front of a reviewer,
> not in front of a compile; rule 2 is `info` and aggregated into **one** finding for the table,
> because 480 of its 492 groups were one module and a finding per group is the spam aggregation
> exists to prevent. Rule 1 aggregates per rsID: a swapped pair is one decision, not two.
>
> **The third rule from `D14` — `state: risk` under prose containing a negation — was NOT
> built.** It is cited as motivation in both the finding and this entry, and it was never
> implemented and never measured. Adding it on the strength of four hand-read rows would put an
> unmeasured precision behind a rule whose sibling needed its precision measured to pick a level.
>
> **`module-curate` said "Nothing checks a conclusion" and now says what the two rules do and do
> not reach**, in the same commit — an enforcement claim with its surface named, per §8.
>
> **Reversal recipe**, if the warning turns out to be noise in the field: delete
> `conclusion_genotype_findings` / `shared_conclusion_findings` and their constants from
> `authored_checks.py`, restore `findings_for_csv_text` and `findings_for_spec_dir` to
> `studies.csv` only, drop the `RM27` block from `tests/test_authored_checks.py`, and restore the
> two paragraphs in `skills/module-curate/SKILL.md` and the `lint_rows` docstring. Nothing else
> reads them, and no artifact carries them: these are findings, never cells.


---

## RM23 — five literature sources where twenty-five exist

**Severity:** medium · **Status: CLOSED 2026-08-20 — shipped in 0.14.0 as a PORT, not a dependency
and not a fork.**

> **Two sources, 5 → 7, and none of the three costs the other options carried.** OpenAlex and Crossref
> are now in `discovery.py` and in `SEARCHABLE`, written against `ServiceGate`, `HttpService` and
> `LiteratureCandidate`. `NOTICE` carries the MIT text **byte-identical to their `LICENSE`**, and a
> test pins the attribution — attribution that lives only in a comment is one refactor from vanishing,
> and its disappearance is a licence violation rather than an untidiness.
>
> **What was taken is API knowledge**: endpoints, parameter names, the response shapes, and OpenAlex's
> inverted-index abstract encoding. Not the code — every call of theirs goes out through `requests`
> with a hardcoded contact, and both are rules here.
>
> **Two upstream defects were fixed in the port rather than inherited**, and a test forbids the first
> coming back:
> - `openags@example.com` / `paper-search@example.org` as polite-pool contacts. Ours resolve through
>   the three-step chain; the captured fixtures were fetched with a real address.
> - `Paper.citations: int = 0`, which types "not reported" as zero. Ours is `int | None`, and
>   Crossref's absent open-access verdict is `None` rather than `False` — it says nothing about OA,
>   so `False` would be a claim it never made.
>
> **One defect found by using the parser, not by reading it:** Crossref carries HTML entities in
> `container-title` as well as in titles, so a real fixture record's venue arrived as
> `http://isrctn.org/&gt;`. Fixed by routing it through `_title`, the same decoder the Europe PMC
> parser already used, and a test asserts the fixture really contains entities so it cannot pass
> vacuously.
>
> **Fixtures are real captured responses** to the request `Discovery` actually makes, contact
> included: `assets/literature/openalex_works.json` and `crossref_works.json`, both on
> `lactase persistence`. Eight tests. Suite 443 → 452.
>
> **What we gave up, stated rather than glossed:** seven further sources (CORE, DOAJ, Zenodo, HAL,
> OpenAIRE, BASE, dblp), and two clients are now ours to maintain. Their tests covered neither of the
> two we took, so those were ours to write either way.
>
> **`RM24` is answered by construction** — a ported client goes through our gate, so there is no
> unpaced third-party transport to reconcile. It stays deferred only for the sources we did not take.
>
> **The Sci-Hub question stopped existing rather than being managed**, which was the whole argument
> for this shape over the other two.

<details>
<summary>The item as it stood on the roadmap</summary>

VENDOR TWO.** Licence confirmed MIT in both the PyPI field and the README. · **Owner:** unassigned ·
**Opened** 2026-08-20

> **Take OpenAlex and Crossref only, vendored with MIT attribution. Not the dependency, not the
> fork.** Measured on a clone of `main` that is byte-identical to `v0.1.4` for the package tree.
>
> **The haul is small at the size that matters.** Package total 10,058 lines. All nine sources we
> lack: 4,050. **OpenAlex + Crossref + the substrate they need: 661 lines (519 SLOC.)** Substrate is
> tiny — `paper.py` 58, `base.py` 54, `config.py` 82, `utils.py` 8.
>
> **Vendoring is clean, and that is a measurement rather than a hope.**
> `academic_platforms/__init__.py` is **0 lines**, so importing one platform pulls no sibling, and
> there are **zero `sci.?hub` matches across all ten platform files and all four substrate files**
> — verified independently. OpenAlex and Crossref need only `requests`, so none of the
> `beautifulsoup4` / `lxml` / `pypdf` / `feedparser` bloat comes with them; `lxml` is declared and
> imported nowhere at all.
>
> **The fact that settles the dependency option: `download_with_fallback(..., use_scihub: bool =
> True)` at `server.py:763` — the default is ON**, contradicting the project's own README, which says
> Sci-Hub is for "users who explicitly choose to enable it". Verified. There is no extra and no env
> var; `[project.optional-dependencies]` is `dev` only. A plain `import paper_search_mcp` does not
> reach it, but **running the server does**, and a wheel ships the whole package regardless.
>
> **Three defects we would inherit and that we must fix anyway**, each of which a vendored copy lets
> us fix and a dependency does not:
> - **Fabricated polite-pool contacts.** `openalex.py:21` sends `mailto:openags@example.com` and
>   `crossref.py:19/57/278` send `paper-search@example.org`. Verified. §5 forbids exactly this — an
>   invented address misattributes the traffic — and our three-step contact chain is the fix.
> - **`__init__.py` calls `load_env_file()` at import**, mutating `os.environ`. That is our `F35`
>   arriving from a new direction, and it is the specific thing that once made the suite silently
>   non-hermetic.
> - **`Paper.citations: int = 0`** writes the `F6` tri-state loss into the type: "not reported"
>   becomes zero.
>
> **The legal picture, and it is research informing a risk decision rather than legal advice.** Both
> US judgments are **defaults**, so neither is precedent. **No court anywhere has ordered a software
> distributor to stop shipping Sci-Hub client code**; GitHub's DMCA archive holds zero Sci-Hub
> notices and PyPI has never removed such a package. Enforcement has landed on app stores, one blog
> post and a website host — never on code distribution. Doctrinally **Cox v. Sony (25 March 2026,
> unanimous)** now requires **inducement or tailoring**, and knowledge alone is not enough; a
> 25-source client is not tailored, which makes the whole question turn on defaults and framing —
> and `use_scihub=True` is precisely the framing fact. The most adverse document is the **ACS
> injunction as amended 28 March 2018**, which added "and other service or software providers", a
> phrase absent from the 2017 order that secondary coverage quotes.
>
> **Why vendoring two still wins even though the legal risk reads low.** It is the only option where
> the question **stops existing** rather than being managed, and it takes the split NCBI budget, the
> second HTTP stack, the import-time `.env` mutation, the fabricated contacts and the `F6` tri-state
> loss out with it. `RM24`'s pacing problem also disappears, because a vendored client is one we
> rewrite onto `ServiceGate`.
>
> **What we give up, stated plainly:** seven further sources (CORE, DOAJ, Zenodo, HAL, OpenAIRE,
> BASE, dblp), and the maintenance of two clients becomes ours. Their tests do not cover OpenAlex,
> so we would be writing those either way.
>
> Full evaluation, 1010 lines, in the session scratchpad as `paper-search-mcp-evaluation.md`.

`discovery.py` reaches PubMed, Europe PMC, Semantic Scholar, arXiv and Unpaywall.
[`paper-search-mcp`](https://github.com/openags/paper-search-mcp) (MIT per its README, 2.5k stars,
active, with tests) reaches 25+ — and the ones we lack are not exotic: **OpenAlex** and **Crossref**
above all, then CORE, DOAJ, Zenodo, HAL, OpenAIRE, BASE, dblp. All official APIs.

**The objection against bundling, corrected 2026-08-20 — the first draft of this entry led with the
wrong one.**

*It led with `JMC_OFFLINE`*: a second process has no offline concept, so `JMC_OFFLINE=1` would
silence our tools while it kept fetching. True, and **not worth what it was being used for**. The
owner's ruling: *"air-gapped stuff is a very niche usecase, we're handicapping 99.9 in favour of 0.1;
this is not a security tool"* — and the sharper half, *"offline makes sense annotation-time, not
author-time."* That is right and it generalises: offline belongs to `just-dna-lite`, where somebody's
**genome** is being read and privacy is the whole point. Authoring is networked by nature — literature
search, rsID resolution, identifier checks and publishing are all network steps, and a module cannot
be written without them. If a genuinely offline authoring build is ever wanted it ships as a separate
`-offline` entity rather than shaping this one.

The flag itself stays and costs nobody anything: it is **off by default**, and the suite's socket
ceiling is built on it (`offline_settings()`, seven test files). What it must not do again is **veto
a broad improvement on behalf of a niche one**, which is what it was doing here.

**The objection that actually stands, on its own:**

- **The NCBI budget would split.** Ours is one budget because `ServiceGate` shares the *same*
  `PacingGate` instance with the enricher's `EutilsClient`. Two processes is two budgets against one
  contact address, which overspends somebody's allowance rather than doubling it. That server also
  declares no contact address at all, where our three-step chain exists so the traffic is
  attributable to whoever is spending it.

It also ships an optional **Sci-Hub** fallback, which is the thing settled the same day: shipping the
code is the act, and vendoring somebody else's is the same act at one remove.

**The shape to build instead: depend on the library, not the server.** `academic_platforms/` is one
module per source, separate from `server.py`, so the clients are importable plainly. Called from
inside our own tools they inherit our `LiteratureCandidate`, our per-source rank and the
`results=null` + `rate_limited=true` tri-state that `F6` exists to preserve — which is the reason
that survives the correction above, because it is about what an author is told rather than about a
switch nobody sets. **PubMed and
Europe PMC stay ours** — that is what keeps the NCBI budget whole — and theirs are used only for
sources we lack.

**Costs to settle before adding it**, none of them disqualifying and none of them ignorable: it is
**v0.1.4**; PyPI carries **no license metadata** while the README says MIT, which wants resolving
before we depend on it; and it brings `beautifulsoup4`, `lxml`, `requests`, `pypdf` and `feedparser`
— a second HTTP stack beside `httpx`, against an install story that is one `uv sync`.

**Fallback if the imports turn out entangled with their config layer:** fork, and move Sci-Hub behind
a `[scihub]` extra so the install is a user decision that carries its own liability. Deliberately the
second option — a fork is a 25-client maintenance commitment.

**Blocked on a decision, not on work.** Adding a dependency is the owner's call.

</details>

---

## RM22 — the enricher fetches the ancestry that `population` wants, and nothing here surfaces it

**Severity:** low · **Status: CLOSED 2026-08-20 — shipped in 0.13.0 as `study_facts`.**

> The finding was ours, by the rule that decided it: *"file an item into the enricher if it doesn't
> provide ancestry data by id; if it provides but is not wired in our tool, it's our bug."* **It
> provides** — `gwas.py::_study_facts` reads `ancestries` from the Catalog study payload and
> `GwasEffectRow.ancestry` carries it — and nothing here surfaced it.
>
> So an author writing `studies.csv` had the answer sitting in their own module, one file over, with
> no route to it. The measured consequence is a published module carrying *"Nagel M et al. — GWAS
> Catalog GCST006941"* in every `population` cell: a citation label in a column that wanted a cohort.
>
> **Surfaced, never filled.** `population` is not in `hints.REDUNDANCY_BEARING`, so filling it would
> make no check vacuous — that was never the reason. The reason is that the Catalog frequently
> answers with several cohorts at once (*"African American or Afro-Caribbean, European, Hispanic or
> Latin American"* is a real value from the HFE corpus), so which applies to a row is a judgement.
> Tests are measured on that corpus for exactly that property. `find-evidence` now says where the
> answer is, which is the half that would have prevented the original mistake.

<details>
<summary>The item as it stood on the roadmap</summary>

Opened out of `RM18` item 3, where `population` in every `aggression_anger_snps` row holds a citation
label rather than a population. The owner's rule decided where it lands: *"file an item into the
enricher if it doesn't provide ancestry data by id; if it provides but is not wired in our tool, it's
our bug to fix in MCP + skills."* **It provides.** So this is ours.

**Measured.** `GwasEffectRow.ancestry` exists and is populated — `gwas.py::_study_facts` reads
`ancestries` out of the GWAS Catalog study payload and `gwas_effect_row` writes it, whenever
`study_facts` is on. Its description: *"The study population, free text as the Catalog records it
('European', 'East Asian', 'Hispanic or Latin American')"*, deliberately free rather than a
vocabulary. `StudyRow.population` is the authored twin, `str | None`, described only as *"Study
population"*. Nothing in `src/just_module_creator/` joins them; our four mentions of ancestry are all
docstrings warning that `--no-study-facts` nulls it.

**So an author writing `studies.csv` after a GWAS pass has the answer sitting in their own module,
in a derived sidecar, and no surface offers it.** The join is `pmid` or `study_accession`, both of
which sit on `GwasEffectRow` and `pmid` on `StudyRow`.

**Surface it; do not fill it.** `population` is **not** in `hints.REDUNDANCY_BEARING` (checked), so
filling it would not be vacuous — but a study carries several ancestries and `ancestry` is a joined
string, so the grain is a judgement and the discriminator says surface. Offer the value, name where
it came from, let the pilot take it.

**The skill half is the other deliverable**, and it is the one that would have prevented `RM18`
item 3: `find-evidence`'s *"Population is where modules overreach"* section tells an author what the
column is not, and cannot yet tell them where the answer already is.

</details>

---

## RM21 — a publish that turns out to be wrong has no route back

**Severity:** medium · **Status: CLOSED 2026-08-20 — shipped in 0.13.0.**

> `registry_yank` and `registry_unyank`. Nothing upstream was missing: the client had both and we
> wrapped neither, so an agent that published a mistake had no route back and the bad version stayed
> at `latest` — the `F12` shape, where the only fix lives outside the surface that created the need.
>
> Token-gated like every registry write, and **defaulting to the polygon like every other write**: an
> unaimed yank that silently delisted a production version would be the same class of mistake the
> tool exists to recover from, committed by the tool itself. A test pins that default.
>
> **The wording is the load-bearing part** and a test asserts it: yank stops a version being
> recommended, **corrects nothing**, does not release the content claim, and the fixed publish is a
> separate act that still has to happen. An agent must not report a yank as though the mistake were
> undone.

<details>
<summary>The item as it stood on the roadmap</summary>

*"Expose the yank feature to the toolset if an agent publishes and spots a grave error."* Opened out
of `RM18`, where the question *"does Anton yank the four?"* had no tool behind it either way.

**Nothing upstream is missing.** `RegistryClient.yank` and `.unyank` both exist and we wrap neither.
The semantics are already the right ones for this: yank *"drops the version from default listings and
`latest`, keeps it fetchable"* — so anyone who already installed it keeps verifying, which is exactly
what an immutable registry should do. It is **not** `delete_version`, which is test-instance-only and
does not release the name-independent content claim.

**Why it matters more here than a wrapper usually would.** An agent that publishes is an agent that
can publish a mistake, and right now the discovery of a grave error ends at a dead end with the bad
version still sitting at `latest`. That is `F12`'s shape — the only route to a fix existing outside
the surface that created the need for it.

**Tier and gating:** a registry write, so token-gated, tagged `registry_write`, listed in
`auth.GATED_TOOLS` — no exception applies, since the token is not its output.

**Care to take in the skill, not in the tool.** Yank is not a correction and never repairs anything;
it stops recommending a version. Publishing the fixed version is a separate act, and an agent must not
present a yank as having undone the mistake.

</details>

---

## RM20 — two questions about the skill surface that nobody has answered

**Severity:** low · **Status: CLOSED 2026-08-20 — both questions answered, and the answers shipped.**

> **1. `find-evidence` keeps its name, and the principle inverted.** The test is *does this task
> exist without a module?* Searching literature, verifying a PMID and reading a paper all do; nothing
> else in the set does. So the inconsistency is the naming working rather than failing. One
> borderline recorded rather than decided: `module-consumer` documents the far side of the seam, but
> its own description also says *"what an author can do to make a module readable"*, which is what
> keeps the prefix.
>
> **2. Eight commands, not sixteen** — `module-101`, `module-start`, `find-evidence`,
> `module-tables`, `module-check`, `module-compile`, `module-publish`, `module-revise`. A command is
> what somebody deliberately types to start something, never a stage an agent walks through. The one
> judgement call: `/module-compile` took the last slot over `/module-diff`; swap it without argument
> if it reads wrong in use. Two tests hold the line — one pins the set, one keeps a command thin
> enough to stay a router.
>
> **Two meta-skills shipped with them**, and both answer a question a *stuck* person asks where the
> only previous route was already knowing which skill to load: `module-status` (*where is this module
> and what is the next decision*, output as a decision list) and `module-symptom` (the door to
> `SYMPTOMS.md`). A `module-doctor` was considered and rejected for overlapping `module-check`.

<details>
<summary>The item as it stood on the roadmap</summary>

Carried out of `docs/HANDOFF-skills-split.md`. Both are cheap, both are reversible, and neither should be
decided by an agent on its own — they are about what the surface *is*, not about what it says.

1. **Does `find-evidence` become `module-evidence`?** Fifteen of the sixteen skills share a `module-`
   prefix and this one does not. Against renaming: the name is the clearest trigger in the set and it
   predates the family. For: an agent scanning a listing groups by prefix.
2. **Do the stage skills also become slash commands (`commands/`)?** This was *the original ask that
   started the split*, and nothing has been added to either manifest. The scaffolds were written
   command-shaped, so the cost is low; the question is whether sixteen commands help or crowd the
   picker.

> **Both answered 2026-08-20.**
>
> **1. `find-evidence` keeps its name, and the principle is inverted.** *"Keep it as find-evidence and
> actually revisit the rest, in terms of not having module-spam."* Applied, the test is **does this
> task exist without a module?** — searching literature, verifying a PMID and reading a paper all do.
> Nothing else in the set passes: eight are lifecycle stages, three are second-pass kinds, and
> `module-101` / `module-tables` / `module-weights` are a module's map, structure and columns. So the
> inconsistency is the naming working. **One borderline recorded rather than decided:**
> `module-consumer` documents the far side of the seam — the join contract, the unobservable-allele
> marker, float32 comparison — and its subject is the consumer's obligations; its own description
> also says *"what an author can do to make a module readable"*, which is what keeps the prefix.
>
> **2. Commands: eight, not sixteen.** *"Up to 8 — find-evidence can be user-requested during the
> creative process; place yourself in user shoes, but keep the surface clean."* A command is what
> somebody **deliberately types to start something**, never a stage an agent walks through:
> `/module-101`, `/module-start`, `/find-evidence`, `/module-tables`, `/module-check`,
> `/module-compile`, `/module-publish`, `/module-revise`. The eight left out — `draft`, `curate`,
> `enrich`, `close`, `refresh`, `diff`, `weights`, `consumer` — are reached from inside a session by
> an agent that already knows where it is. **The one judgement call:** `/module-compile` took the
> last slot over `/module-diff`; compile is usually an agent step between check and publish, while
> diff answers a question a user asks out loud. Swap without argument if it reads wrong in use.
>
> **3. Two meta-skills to add**, both proposed and both answering a question a *stuck* user asks,
> where today the only route is already knowing which skill to load:
> - **`module-status`** — point it at a spec directory, get *where is this module now and what is the
>   next decision*. The lifecycle is spread across eight stage skills and nothing answers it; an agent
>   resuming somebody else's module infers it from which files exist. Its output is the **decision
>   list** §10 asks for, not a diff and not a findings dump.
> - **`module-symptom`** — paste the message, get cause and action. `references/SYMPTOMS.md` already
>   holds the mapping and the only door to it is `module-101` plus knowing to look.
>
> A `module-doctor` was considered and **rejected**: it would overlap `module-check` and split one
> job across two surfaces.

**A third question from the same file is answered and recorded**: `create-module` did not survive as a
thin index — it was deleted, and `CLAUDE.md` says why.

</details>

---

## RM19 — build `compare_modules` and `compare_to_published`

**Severity:** medium · **Status: CLOSED 2026-08-20 — both halves shipped.** `compare_modules` in the
night run, `compare_to_published` in 0.13.0.

> **`compare_to_published` is manifest-only**: `resolve_version` when the version is `latest`, then
> the manifest, and nothing else. It never downloads, and it **hands over** rather than escalating —
> the result names the `registry_download` + `compare_modules` pair for row detail.
>
> **A defect the design carried, found by testing rather than by reading.** The study specified
> `compiler.file_entries` for the per-file layer. The publisher hashes through
> `authored_input_entries`, which **normalizes newlines**. Measured on the HFE reference example the
> two disagree on **two of three files**, so the first implementation would have reported a byte
> difference on every module authored on a machine whose newlines differ, forever. Upstream states
> the reason that function is public: *"two tiers must agree on it byte for byte."* The lesson
> generalises past this tool — a design that names an upstream function has named an assumption, and
> the assumption is testable.
>
> The ordering the design insisted on holds in the output: `content` first and governing, per-file
> digests as a pointer to where to look and never as a content claim. A reordered row moves the file
> digest and leaves `content_signature` untouched, and there is a test that says so.

<details>
<summary>The item as it stood on the roadmap</summary>

> **Shipped: `compare_modules`.** `src/just_module_creator/compare.py` plus `tools/comparison.py`,
> essentials, offline, with 15 tests built on the `hfe_hemochromatosis` reference example rather than on
> synthetic rows — the design's decisions were measured on that corpus and invented tables would not
> reproduce them.
>
> The cases where the naive answer is wrong all behave as specified, verified against the real module:
> a **row reorder** reports `content: same` and 13 unchanged rows; a **licence edit** reports
> `content: same` with the change under `identity_scope: sources.signature`; a **retyped rsID** reports
> one added and one removed and **zero changed**; a **changed `genome_build`** reports `frame: moved`
> with the note that the clean row counts beneath it are *not comparable*; and the deprecated
> `sources.csv` spelling compares as the same table as `licensing.csv`, reporting each side's spelling.
>
> **One defect found by using it rather than by testing it**: an example whose two cells differ past
> the truncation point rendered as two identical strings, which reads as *the row did not really
> change*. The window is now centred on the first character where the two diverge.
>
> **Still open: `compare_to_published`** — manifest-only, one or two bounded GETs, no download. The
> design specifies it fully; it was not started rather than half-built.

[DESIGN-version-compare.md](DESIGN-version-compare.md) is a completed design study, 699 lines, and its
recommendation is **build it now**. This entry exists because the study had no roadmap item, so its
ranking lived only in a primer that has been deleted.

**Both essentials**, because both are bounded by what the caller named. `compare_modules(left_dir,
right_dir)` is a pure function of two local spec directories — no network, no compile, no parquet;
measured at 0.18 s on the largest reference example. `compare_to_published(spec_dir)` is manifest-only:
one or two bounded GETs and no download, ending by **handing over** the `registry_download` +
`compare_modules` pair rather than escalating to a tier of its own.

**Build `compare_modules` first** — it is useful alone, and the other without it is a signature
comparison with no way to look inside.

Output is a three-level ladder — signature, then table, then rows **grouped by the set of columns that
changed** — with eight named refusals and a three-valued verdict per axis. **Read `genome_build` before
any row count**: when the declared builds differ the comparison is *not comparable* rather than clean,
and the reassuring answer is the dangerous one.

**Nothing waits on an upstream release.** The in-tree additions the study names (`hints.key_fields`,
`hints.DERIVED_TABLE_MODELS`, registry 0.19's per-version `content_signature`) are symbol-gated
improvements, not prerequisites.

**Why it matters beyond convenience:** `module-diff` currently teaches a two-command download-and-diff
recipe that an author in a chat session cannot run without shelling out, and
`test_the_taught_workflow_runs_in_the_default_tier` exists precisely because a tier that teaches a step
it cannot run is the failure mode to watch for.

</details>

---

## RM9 — a module authored only through this server carries no check attestation

**Severity:** medium · **Status: CLOSED 2026-08-20 — shipped in 0.13.0.**

> **The policy question was answered by moving the tools, not by narrowing the promise.**
> `tools/research.py` opens with *"no tool in this module writes to a spec directory"*. The
> alternative was to soften it to "writes no authored cell" — upstream's own wording, and the
> narrower claim that arguably matters — and it was **rejected**: a module whose opening line is a
> literal claim keeps it literal, and a boundary a reader can rely on beats one qualified by an
> exception. `tools/checks.py` now holds `check_identifiers`, writes the attestation, and says so in
> its first line. Nothing about the tiers moved with it; the tier line is cost, not
> read-versus-write.
>
> **Three rules taken from the enricher's CLI rather than invented:** no record where the check does
> not **apply** (a module with no `variants.csv` has no gene or trait to have an opinion about, and
> writing one would mine a nonce onto a module that never asked); a record **on the outage path**,
> because that is the run whose report is empty and an empty report with no record reads exactly like
> a clean one; and **one call for every record**, since the proof-of-work binds the whole document.
>
> `check_genes` / `check_traits` became arguments and are recorded, so narrowing a run narrows what
> the record claims rather than making the unasked half look passed.
>
> **Reversal recipe**, unchanged from the decision: if the split ever reads as ceremony, narrow the
> promise and move them back. What must not happen either way is the promise quietly becoming false
> while the sentence stays.

<details>
<summary>The item as it stood on the roadmap</summary>

Format 0.6 made `verification.json` a real surface: the registry projects a
`verification` block onto the module page, and a record says *the question was put*
rather than *the answer was clean*. The enricher writes those records from its
**CLI commands** — `check-identifiers` and `check-acmg` do it unconditionally, with
no flag, precisely so that "not run" and "ran and found nothing" stop reading alike.

The underlying functions do not, and the functions are what we call. So `close_module`
is the only thing on this surface that writes into `verification.json`, and a module
authored entirely through these tools shows nothing where a CLI-driven author's module
shows two records. That is the `F33` shape again — our own pin being what keeps an
author off a surface that exists.

It is not a missing upstream API: `identifiers.verification_records()` and
`verification.merge_records()` are both public, and `close_module` already proves the
write path works from here. What has to be decided first is a policy question, because
`tools/research.py` opens by promising that **no tool in it writes to a spec directory**
— a line that is currently true and load-bearing for how the read-only tier is
understood.

> **Decided 2026-08-20: the check tools move out.** Not the narrowed promise. A module whose
> opening sentence is a literal claim keeps it literal, and the boundary then means something a
> reader can rely on rather than something qualified by an exception. The tier line is cost, not
> read-versus-write, so nothing about the tiers moves with them — they stay essentials.
>
> **Reversal recipe:** if the split ever reads as ceremony, narrow the promise to "writes no
> authored cell" (upstream's own wording) and move them back. What must not happen either way is
> the promise quietly becoming false while the sentence stays.

---

## Idea book

Freeform, unscheduled, no commitment implied.

- A `module_diff` tool: two spec directories in, the authored rows that differ
  out. `module_signature` answers *whether* two specs differ but not *where*, and
  "diff the tables" is the standing advice whenever a digest moves without an
  intended content change.
- Surfacing `hints.REDUNDANCY_BEARING` as a resource rather than only as a field
  on `describe_table`, so an agent can read the whole list once instead of per table.

</details>

---

## RM6 — two literature parsers have no fixture, so nothing tests them

**Severity:** medium · **Status: CLOSED 2026-08-20 — both fixtures captured, both parsers tested,
and the premise turned out to be stale.** · **Owner:** unassigned

> **The block was real in February and gone by August, and nobody re-probed.** This item rested on
> *"both services answer HTTP 429 to this machine's IP regardless of user-agent or pacing — arXiv on
> a first request with no prior traffic, confirmed with plain curl."* Re-measured through
> `Discovery` itself, using the exact endpoint, params and pacing the client uses:
>
> - **arXiv answers 200.** Six requests, no throttling, no special headers needed. arXiv had a
>   genuine rate-limit incident starting ~25 February 2026 which its maintainers acknowledged and
>   fixed; we measured during that window and kept the conclusion for six months.
> - **Semantic Scholar's 429 is intermittent and endpoint-specific**, not an IP block. `paper/search`
>   is shed under shared-pool pressure (roughly one attempt in four succeeds); `paper/{id}` answers
>   reliably. The throttle sends **no `Retry-After` and no `X-RateLimit-*`**, so a client cannot pace
>   against it — only blind backoff works, which is what the capture used: it succeeded on attempt 2
>   at 25-second spacing.
>
> **Captured, and both are real responses to the request `Discovery` actually makes** — not curl
> approximations:
>
> - `assets/literature/arxiv_query.xml` — `all:population genetics selection`, 5 entries, **3 with
>   `arxiv:doi` and 2 without**, so the published-preprint DOI branch is exercised in both
>   directions. That branch matters because a DOI is the only handle that reaches Unpaywall.
> - `assets/literature/semanticscholar_search.json` — `lactase persistence`, 3 records, captured with
>   the **full `_S2_FIELDS` list** so `authors`, `venue`, `abstract`, `citationCount`, `isOpenAccess`
>   and `openAccessPdf` are all present. Real PMIDs (40063818, 41278663, 40880079) on the trait this
>   repo already uses for its other fixtures.
>
> Six tests in `tests/test_discovery.py`, ground truth computed from each payload rather than pasted.
> Suite 385 → 391.
>
> **The standing lesson is the re-probe, not the block.** An environmental verdict is a measurement
> with a date on it, and this one had no expiry — it hardened into a premise and then into a roadmap
> item. `F6` in `dogfooding.md` keeps the entry, because the tri-state result it was really about
> (`results=null` + `rate_limited=true` reading as *unchecked*, never as *no preprints exist*) is
> unaffected and still the best evidence that design earns its keep.
>
> **Still worth doing, and not blocking:** request a Semantic Scholar API key. It gives 1 RPS
> dedicated instead of a globally shared unauthenticated pool, the client already sends
> `x-api-key` when `settings.semantic_scholar_key()` is set, and the form is human-only with a
> historically ~1-month backlog. Insurance for live use, not a prerequisite for anything.

<details>
<summary>The item as it stood on the roadmap</summary>

**Severity:** medium · **Status:** open · **Owner:** unassigned

`parse_semantic_scholar` and `parse_arxiv` are exercised by nothing. Every other
parser has a real captured payload under `assets/literature/`; these two do not,
because both services answer HTTP 429 to this machine's IP regardless of
user-agent or pacing — arXiv on a first request with no prior traffic, confirmed
with plain `curl` outside the client.

The block itself is not a defect anywhere and not ours to fix. **The untested
parser is ours**, and a parser with no test breaks silently when the API shape
moves.

> **Decided 2026-08-20.** Take the `S2_API_KEY` route for the Semantic Scholar half, and
> **research the block itself** before conceding the arXiv half — the 429 shape has never been
> investigated, only worked around. A hand-written payload is not on the table: §2 forbids a
> fabricated example value in committed code, and every other parser here has a real captured one.

Two ways out, not exclusive: capture the fixtures from a host that is not
blocked, or set `S2_API_KEY` — Semantic Scholar's keyed pool is not the one being
throttled — and capture at least that half. Recorded as **F6** in
[dogfooding.md](dogfooding.md).

</details>

---

## RM15 — we absorbed the format layer's philosophy wholesale, and it is load-bearing in 19 files

**Severity: HIGH** · **Status: CLOSED 2026-08-20** — every "done when" condition met, and the last
loose thread reproduced and dismissed the same night. · **Owner:** agent A · **Opened** 2026-08-20

> **The loose thread, settled.** This item was held open for one unreproduced report of
> `describe_table` returning a 0.5 shape under format 0.6.1. **Reproduced, and it is not a
> `describe_table` defect.** The plugin cache holds two stale servers — `0.2.0` running format
> **0.5.0** and `0.7.0` running format **0.5.4** — while the workspace venv runs **0.6.1**. So a 0.5
> server answered while the caller believed they were on 0.6.1; the shape was correct for the code
> that produced it. It is the same cause `RM13` shipped the fix for, and that fix is live:
> `produced_by: SchemaVersions` is a **required** field on all five schema tools, so a payload now
> names the release that made it.
>
> **The standing lesson, which is workspace-shaped rather than code-shaped:** *ask the tool, never
> memory* only beats memory when the tool is current, and a plugin-cache server is a second install
> that upgrades on its own schedule. Check `produced_by` before trusting a schema answer that looks
> wrong.

<details>
<summary>The item as it stood on the roadmap</summary>

**Severity: HIGH** · **Status:** audit complete; narrowed to the residue below · **Owner:** agent A · **Opened** 2026-08-20

> **Done, 2026-08-20 night run.** All three "done when" conditions are met for every surface this item
> named. `server.INSTRUCTIONS` rewritten (rule 2 replaced; a new rule 3 carries the lag hazard) and it
> agrees with `CLAUDE.md` §2. All sixteen §2 domain bullets judged — thirteen stand, "never widen the
> write surface" split, the `provenance_quote` prohibition reversed. Code surfaces re-justified
> (`models.py`, `_shared.py`, `research.py`, `authoring.py`); `refresh.py` audited as *conditional*
> physics — it is two data points because we keep no third, and a filled log settles it. Skills swept:
> `module-101` realigned, the ten scaffold seeds disarmed, `create-module`'s last prohibition removed,
> seven slogan sites and five "a human read it" sites corrected. **§1's questionnaire ran with the
> owner; the attestation contradiction is settled and recorded in §10 — do not re-open it.** Filed
> upstream as `S54`/`S55`, tracked as `F42`/`F43`.
>
> **The residue is closed, 2026-08-20 later the same night.**
> `docs/DESIGN-version-compare.md` — the one surface this item named that had not been read — has had
> the pass. Two sites: §3.6's heading was the retired stance, and the reason a comparator refuses is
> its own (**pairing two rows is an assertion** that two directory listings cannot support); and the
> changelog refusal argued by analogy to a machine-located quote, which is now the legitimate act. The
> refusal survives on a sharper distinction — a located quote is a found passage a check can test, a
> generated changelog sentence is a claim about **motive** that nothing can test.
>
> Three of the four "create-module is stale" dossier claims were resolved when that skill was
> dismantled: two described a pre-0.6 claim already corrected, and the third is now carried as a
> ROADWORKS in `module-curate`. **`RM15` may be closed.** The one unreproduced report of
> `describe_table` returning a 0.5 shape under 0.6.1 still stands and is not this item's.
>
> The three delegated files landed and were then swept against the same stance grep: `find-evidence`
> and `studies.md` were already correct, `literature.md` still carried the reversed proposition live
> and is fixed. The six contradicted dossier banners are all fixed; of the four "create-module is
> stale" claims, one was checked and was largely a false alarm, three remain. One unreproduced report
> of `describe_table` returning a 0.5 shape under 0.6.1 stands.
>
> The **discriminator** this item was blocking is now specified in part: `INSTRUCTIONS` rule 3 and §2
> state it, upstream `S52` is the mask's schema half, and what remains is the record — RM16's capture.
> The auto-correct rulebook stays unpopulated on purpose; it is built from real transcripts, not
> designed.

> **Progress, 2026-08-20.** `server.INSTRUCTIONS` rewritten (rule 2 replaced, a new rule 3 for the
> lag hazard). All sixteen `CLAUDE.md` §2 bullets judged — thirteen stand, "never widen the write
> surface" split, the `provenance_quote` prohibition reversed. Code surfaces re-justified
> (`models.py`, `_shared.py`, `research.py`, `authoring.py`'s `_MACHINE_REFUSAL`), `refresh.py`
> audited as *conditional* physics. **§1's questionnaire ran with the owner and the attestation
> contradiction is settled** — recorded in §10; do not re-open it. Filed upstream as `S54`/`S55`,
> tracked as `F42`/`F43`. The skills sweep landed too, and the verdicts that guided it are absorbed
> into this entry, `CLAUDE.md` §2/§10/§11 and `CHANGELOG.md`; the relay file they were written in is
> retired, and stays readable in `git log`.

**This is an audit item, not a code change.** Nothing here is known to be wrong yet. What is known is
that a stance was adopted without ever being tested against this layer's own purpose, and it then
propagated into the surface an agent reads first.

### What happened

`report, never repair` is `just-dna-format`'s stance and is **correct for that layer**: the compiler
cannot record who decided a value, so writing one would launder a machine's guess as an author's
judgement. This repo adopted it as a **non-negotiable of its own** — §2, `server.INSTRUCTIONS` rule 2,
and from there into fourteen skills and four table dossiers.

The user's correction, 2026-08-20: *"report-never-repair is format's stance, correct for that layer:
they delegate business decision to us here; we're more high-level user-facing app level, we have a
counterstance."* §2 now states the counterstance — we may write, every authoring move is logged, and
the agent is owed a discriminator.

**Flipping one bullet does not undo the propagation.** The stance is quoted, argued and built on
across the surface, and each instance has to be read on its own terms.

### The test to apply to each instance

For every rule, refusal and piece of prose below, decide which of three it is:

1. **Physics** — true at any layer, keep. *A check that could not run is not a check that passed.*
   *A determinism gate is not a correctness gate.* `None` is not `False`.
2. **Format's policy, correctly ours too** — keep, but say **why it is ours**, not "because upstream
   does it". A rule whose only justification is another layer's stance is the defect this item is about.
3. **Format's policy that we should NOT hold** — replace with the counterstance, and follow it through
   to the tool behaviour, not just the prose.

**And the deeper correction the pivot came with, which changes what "safe" means.** The vacuity
argument — *fill `clin_sig` from ClinVar, then a check compares the two and agrees with itself* — is
true but shallow, and reading only it is how the stance survived unexamined. The real hazard is that
**the source lags the edge**: an article is retracted, meta-research refutes the conclusion. So *"your
row disagrees with ClinVar"* is not a defect report; it may be the module being right and current while
the archive is stale, and an agent that silently conforms the row **degrades** the module while the
check reports green. Every instance below should be re-read against *that* hazard, which several of
them do not mention at all.

### Surfaces to read, most load-bearing first

- **`src/just_module_creator/server.py` — `INSTRUCTIONS` rule 2.** *"Lookups show you a value and
  refuse to write it into an authored cell… Those refusals are the feature."* This is the **first thing
  an agent reads**, before any tool call, and it now contradicts §2.
- **`CLAUDE.md` §2, "the domain rules this server exists to enforce".** Every bullet, against the
  three-way test. Named individually because they are not all the same kind:
  - *never fill a value from the same source that checks it* — the vacuity rule. Physics or policy?
  - *never let a tool write a checked value from a lookup* — already flipped in §2; check that the
    flip is coherent with the rest of the section.
  - *never extract a passage from a document a tool fetched* — **see the contradiction below.**
  - *never collapse unknown into a boolean*, *never treat a determinism gate as a correctness gate*,
    *never silently fall back* — these look like physics; confirm rather than assume.
- **Fourteen skills and four dossiers** carry the stance as instruction to an author or an agent:
  `module-101`, `create-module`, `module-check`, `module-close`, `module-compile`, `module-consumer`,
  `module-curate`, `module-draft`, `module-enrich`, `module-publish`, `module-start`, `module-weights`,
  plus `module-tables/references/{studies,gwas_effects,pharm_variants,repeat_alleles}.md`. Several
  frame a refusal as a **feature**, which is exactly the framing under review.
- **`models.py` field descriptions and every lookup tool's docstring.** An agent reads these as the
  contract. A description that says a tool refuses on principle is a behavioural claim.
- **`tools/refresh.py`** — written 2026-08-20 *from a brief that cited the old stance*, so it inherited
  it by construction rather than by decision.

### The contradiction this audit must resolve, and it needs §1

**§2 forbids extracting a passage from a fetched document; §10 records the user saying the opposite
about who can read a paper.**

- §2: *"Never extract a passage from a document a tool fetched… a machine-located quote asserts a
  reading that never happened, which is a false claim of provenance."*
- §10: *"Here you kinda ask v2 work from a wrong person"* — asking a gardener for a
  `provenance_quote` is a reviewer's job and a different person's — and, flatly, **"AI totaly can
  read articles."**

Under the pivot these cannot both stand as written. If the agent is a legitimate reader, a located
quote is a reading that *did* happen, and the attestation question becomes *whose* reading was
recorded rather than whether one occurred. **Run §1's questionnaire; do not resolve this by
inference** — it is the highest-stakes instance of exactly the absorption this item is about, and
`hints.ATTESTATION_BEARING` shipped upstream on the argument now in question.

### What this unblocks

The **discriminator** (§2 part 3) cannot be specified until this read is done — it is the thing that
tells an evident auto-correction from a judgement call, and its shape depends on which refusals
survive. The auto-correct rulebook (§10, *to-populate-later*) waits on the same answer.

### Done when

Every surface above carries a rule that is justified **from this layer's own purpose**, with no
prohibition standing only on "upstream does it that way"; `server.INSTRUCTIONS` and §2 agree; the
§1 questionnaire on the attestation contradiction has been run and its answer recorded in §10.

---

</details>

---

## RM17 — nothing on the authored side can see that one quote is repeated across every row citing a paper

**Severity:** high · **Status:** SHIPPED 2026-08-20 (night run) · **Owner:** agent B · **Opened** 2026-08-20

The measured case is `F44`. `registry_check(target="test", literature=true, strict=true)` returns
byte-identical output — `verdict: true`, every finding list empty — for a module whose 69
`provenance_quote` cells are all the article's title and for the same module remediated. `lint_rows`
on three rows carrying the same title string reports `0 errors, 0 warnings`. `validate_module` and
`compile_module` say nothing either. Four published modules reached production through this workflow
carrying 3668 title-quotes.

**Why waiting for upstream is not the plan.** `S54` asks the compiler to compare a quote against
`CitationHint.title` inside `_study_quote_found`. That is the right fix for their layer and it will
not fire on the modules that motivated it, because `S56` established that the quote check never ran
on any of them. Ours is a different check in a different place.

### What to build

A finding over `studies.csv` alone, offline, no pass and no network:

> group the rows by `pmid`; for any `pmid` with more than one row, count the **distinct** non-empty
> `provenance_quote` values. One distinct value across many rows is reported.

`warning` level, aggregated by reason with a count (never one per row), in **both** `lint_rows` and
`validate_module`, beside the other authored-table findings. The message should name the PMID, the
row count and the quote's first few words, because the author needs to recognise which paper it is.

The title comparison is a *second*, stronger signal and needs a network call
(`lookup_citation(pmid).title`), so it does not belong in the offline linter. It fits
`registry_check`, where a round trip is already being paid for.

### Decisions already taken, so they are not re-argued

- **Warning, never error.** One quote per PMID is legitimate when a module cites a paper for one
  row, and a deliberate trait-level grain is a defensible authoring choice — see `find-evidence`'s
  *what may honestly go in `provenance_quote`*. The signal is one quote across *many* rows.
- **The grain is the shape, not the string.** A rule that only catches the title would miss the next
  variant of this, which is one real sentence pasted onto 2000 rows.
- **It reads the authored file directly.** It must not depend on `literature.csv`, whose counters
  are stale on every module that has the problem (`F49` / `S56`).

### The one thing to settle before writing code, and it is why this was not built the night it was found

**Whose finding is it, in a tool that transports upstream's verbatim?** `validate_module`'s
`warnings` are upstream's own, carried across the MCP boundary field-for-field by
`_shared.to_findings` precisely so `error`/`warning`/`info` and `None`-means-unchecked survive.
Mixing a finding **we** computed into that same list makes it impossible for a caller to tell which
layer said what — which is the distinction §2 exists to protect, one level up.

Three shapes, none obviously right:

1. **A separate field** — `authored_findings`, beside `warnings`. Honest and additive; costs every
   caller a second list to read, and invites a second one after it.
2. **A `source` on `LintFinding`** — `upstream` vs `just-module-creator`. Preserves the ladder and
   the distinction in one list; changes a model every tool returns.
3. **`lint_rows` only, and never `validate_module`.** `lint_rows` is already ours end to end, so
   nothing blurs. Costs the check its reach: the pre-publish path an author actually runs is
   `validate_module`, and a linter you have to remember to call is the one that does not get called.

The third is tempting and is probably wrong for exactly the reason `F44` exists. Run §1 rather than
picking one.

### Done when

`lint_rows` and `validate_module` both report it — with the layer that computed it legible — a test
builds the failing shape from a real module copy and watches the finding appear, and
`find-evidence` + `studies.md` point at the tool instead of at a hand-written group-by.

### How the open question was settled, and how to reverse it if that was wrong

`RM17` said to run §1 rather than pick one of the three shapes. The owner was unreachable — the night
brief was explicit that a defensible decision written down beats a blocked night — so it was decided
and this is the reasoning.

**None of the three shapes was taken whole, because the two surfaces cannot express the same thing.**
`LintResult.findings` is a list of `LintFinding`; `ValidationReport.warnings` is a list of **bare
strings**. Option 2 (a `source` on the finding) is unavailable on validate; option 1 (a separate
field) is redundant on lint; option 3 gives up the surface an author actually runs before publishing,
which is the reason `F44` happened at all.

So the rule is stated once and each surface expresses it in the only way it can:

> **Upstream's own strings stay in `errors` / `warnings` / `info`, untouched. Anything this layer
> computed is a `LintFinding` carrying `source`.**

On `lint_rows` that means our findings append to `findings` with `source="just-module-creator"`; on
`validate_module` it means a new `authored_findings` list, because appending a string to `warnings`
would be irreversible — a caller could never separate the layers again.

**To reverse:** the whole decision is one field on `LintFinding` and one on `ValidationReport`. Moving
to option 3 is deleting the `validate_module` line in `tools/authoring.py`; moving to option 1
everywhere is adding a second list to `LintResult`. Nothing else depends on the shape.

### Measured against the corpus that motivated it, 2026-08-20

Run over the five externally authored modules in
`../just-dna-format/data/output/corrected_modules/`:

| Module | studies rows | rows quoted | distinct PMIDs | distinct quotes | flagged |
|---|---|---|---|---|---|
| `aggression_anger` | 69 | 69 | 3 | **3** | 2 |
| `big_five_personality` | 859 | 859 | 26 | **26** | 24 |
| `cognitive_intelligence` | 2045 | 2045 | 33 | **33** | 28 |
| `risk_impulsivity` | 695 | 695 | 19 | **19** | 14 |
| `muscle_lean_mass` | 11 | 0 | 0 | 0 | 0 |

**One distinct quote per PMID, exactly, on all four** — the `F42` signature, reproduced by counting
rather than by trusting the earlier measurement. The check flags **68 of the 81** PMIDs; the thirteen
it does not are cited on a **single row each**, which is legitimately one quote and is the decision
`RM17` recorded in advance.

**`muscle_lean_mass`'s zero is not a discrimination** and should not be read as one: its `studies.csv`
has no `provenance_quote` column at all. It is the same module that was immune to the coordinate-shift
class, for the same reason — it authors the least it can get away with.

### Shipped

`src/just_module_creator/authored_checks.py`, wired into `lint_rows` and `validate_module`, with
`tests/test_authored_checks.py` — twelve tests including the discrimination the whole item exists for:
the honest `studies.csv` and the repeated-quote one produce the same `valid` and a different
`authored_findings`, which is exactly the pair `registry_check` returned byte-identically.

Left for the network surface, as the item specified: comparing the repeated string against
`lookup_citation(pmid).title` inside `registry_check`, where a round trip is already paid for. Upstream
`S54` may also land it in `_study_quote_found`; check before duplicating.

---

## RM14 — `provenance.json` is recognised by the registry and by nothing here

**Absorbed into RM16 on 2026-08-20, the same day it was opened. Not shipped, not dropped —
re-scoped, because it had been read from the wrong end.**

Opened as a low-severity tidiness item: `provenance.json` is in the registry's
`RECOGNIZED_SPEC_FILES`, survives a storage round-trip, and no tool or dossier here writes or reads
one. True, and the wrong frame.

What it actually is: the **missing half of the counterstance**. §2 was corrected the same day to say we
may write and revise, with the agent owed a discriminator for when editing against a source is right —
and the hazard there is not vacuity but that **the source lags the edge** (a retraction, a refuting
meta-analysis). An override may be the module being more current than the archive, and nothing recorded
that judgement anywhere. `ProvenanceItem.rationale` is exactly the freeform record such a judgement
needs, and it already exists upstream, AI-aware, unread by any check.

So the item is not "write a file nobody reads". It is "capture the reason an authored value outranks a
source, at the moment of the override". Re-opened at **high** severity as `RM16`, with the contract half
— whether a check downgrades a mismatch to INFO when a record exists — filed upstream as `S52`.

## RM12 — `enrich_gwas` is wrapped by no MCP tool

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**What shipped.** `enrich_gwas_effects(spec_dir, strict, use, study_facts, offline)` in
`tools/passes.py`, registered in `register_extended_passes`, returning a new
`GwasReport`. `gwas_effects.csv` was the last enricher pass an author driving this plugin
had to shell out for, and the shelling-out was documented as a gap in
`skills/module-tables/references/gwas_effects.md`.

**Extended, and the cost rule decides it cleanly.** The budget is `1 + 2N` requests for
a variant with N published associations, because `pmid`, `trait`, `ancestry` and
`study_accession` all sit behind `_links` — measured upstream at **382 requests and 0
cache hits** for one real module, since rs1800562's 189 associations each name their own
study. The size is set by how much has been published about the variant, not by anything
the caller named, which is the definition CLAUDE.md §5 gives. It sits beside
`enrich_facts` and `enrich_literature_pass`, and `test_modes_and_auth.EXTENDED_ONLY`
pins it there.

**Three upstream facts the wrapper had to carry rather than smooth over.**

- **`strict` fires on the usual answer.** It escalates on `unusable` and
  `p_value_underflows` — never on `missing`, because the Catalog holding nothing for a
  variant is a fact about the variant and true of most clinically authored ones.
  `reference_examples/hfe_hemochromatosis`, a shipped flagship, carries **six** p-values
  the Catalog publishes as `0.0`, so strict refuses it while nothing about it is wrong.
  The docstring says that in those words, and the failure path says it again on the
  result. It also escalates *after* the write, so a strict failure leaves the sidecar
  holding everything `best_effort` would have written — which is the difference between
  an escalation and a fetch failure, and the message is what tells them apart.
- **Published betas are not weights, and the tool makes that readable rather than
  asserted.** `associations_without_effect_allele` and the sorted distinct `effect_units`
  are computed from the rows upstream returned: `not_found` rows are excluded from the
  first, because their null `effect_allele` means *no association exists* while a
  recorded association's null means *the study never established which allele carries
  the effect*. On one real module those come out at 33 of 186 and 12 distinct units for a
  single variant. There is no argument on this tool that could write `weight`.
- **`study_facts=false` is a sticky cut.** It drops two thirds of the budget and leaves
  `pmid`/`trait`/`trait_efo_id`/`ancestry`/`study_accession` null — and the merge is keyed
  on `association_id` alone, so a later run with study facts **on** skips those rows
  rather than backfilling them. Only deleting the file recovers them. Warned on the
  result and asserted in the test; filed upstream as a doc gap.

**No counter is coalesced to zero.** The five numeric fields are `int | None` and the failure path
passes `None` for every one. On a strict escalation `0` would be wrong rather than merely absent —
upstream's message names non-zero counts and the sidecar is already written — and `rows` is `None` on
an offline no-op as well, since an existing file keeps what it held and nothing counted it.

**No `produced_by`.** RM13 stamps *generated schema answers*; this is a verdict about a
directory at a moment, which that item explicitly left unstamped, and `SchemaVersions`
carries the format and compiler versions where a pass answer would need the **enricher's**
— a stamp naming the wrong package is worse than none.

**One `except` arm on purpose.** `GwasNotFound` is a subclass of `GwasError`, so an arm
for it would have to come first, but it cannot arrive: `associations_for` catches the
Catalog's 404 and returns the empty *answer* that becomes a `not_found` row, and `follow`
catches it so an association whose study record moved keeps null study facts. An arm for
a type that never arrives reads as if it did.

**The strict ladder now has a test, which upstream still does not have.** `strict`
appears nowhere in `enricher/tests/test_gwas.py` in either direction, so
`test_the_gwas_strict_ladder_escalates_on_the_catalogs_shape_after_writing` drives the
real `enrich_gwas` with an injected transport and asserts what it observably does: one
underflowing association raises, the row is on disk when it raises, and `best_effort` on
the same input reports the count and succeeds.

## RM10 — three tool answers restated a schema fact instead of generating it

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**Why it was worth a roadmap item at all.** Every one of the three was a *hardcoded schema
fact*, which §2 forbids — and all three had already gone stale, which is the argument for the
rule rather than a coincidence.

**1. `keyed_on` named a deprecated column.** `_SUBJECTS["copynumbers.csv"]` said
`(gene, modifier_gene, modifier_cn)`, and `modifier_cn`'s own field description has read
*DEPRECATED since 0.6, removed at 1.0 — use modifier_copy_number* since format 0.6 landed. So the
one surface that tells an author what an append collides on was pointing at a column upstream
removes at 1.0, while `modifier_copy_number` — which holds the fractional dosages VCF 4.4 §7.2
allows — went unmentioned.

**The key half stays in `_SUBJECTS`, and that is the decision worth recording.** The
subject half is the documented exception ("which table?" is about intent, and the schema cannot
answer it); a key is structure, so the obvious move was to derive it. Nothing public derives it:
`draft.natural_key` is **row-level** — an instance in, key *values* out, never column names — and
returns `None` for the four binning kinds on purpose. The two registries that hold the names,
`compiler._TABLE_DUPE_KEYS` and `MeasureBinRow._KEY_FIELDS`, are both private, one of them as
lambdas. Removing the field was the other option and it is worse: "what will an append collide on"
is a real question, and answering it nowhere sends an author to memory.

So the string stays and the drift class is closed by a **test** instead: every token is now an
exact model field name, and
`test_every_documented_key_column_is_a_live_undeprecated_field` resolves each one against
`model_fields` (accepting a property, because `StudyRow.variant_key` is derived rather than
authored) and fails if any is missing or opens its description with `DEPRECATED`. Run against the
old map it flags six tokens: `modifier_cn`, plus `variant`, `a`, `b` and two `trait`s that were
loose prose rather than column names — which is why they were corrected too, since a token that
does not resolve cannot be checked. Filed upstream as **`S48`**, asking for a public
`key_fields(csv_name)`.

**2. `list_tables().sidecars` was a literal four and the toolchain has seven.** It named
`resolution.csv` and the three 0.5 fact tables, so the three format-0.6 ones —
`gene_validity.csv`, `clinical_assertions.csv`, `gwas_effects.csv` — were missing from the one
answer that claims to say what a machine writes, while `authoring_reference` in the same module
described all of them. Now derived from `just_dna_registry.specfiles.FACT_CSVS` + `RESOLUTION_CSV`,
minus the draftable kinds.

**Why the registry's public roster and not the compiler's authoritative one.**
`compiler._FACT_TABLES` is the tuple the compiler actually loads and carries the row model too,
which is exactly what RM11 needed — and it is private. The registry publishes the same roster
because it has to recognise every file the compiler reads. The cost is real and recorded in the
code: the roster now comes from a different package than the loader it describes, so a registry
release lagging a compiler release makes the answer lag too. Filed upstream as **`S47`**. When a
fact table is added upstream, `sidecars` grows with no edit here; `describe_machine_table` refuses
the new name explicitly (real, undescribable by this build) and
`test_the_produced_roster_and_its_models_agree` fails, which is the intended sequence.

**`S47` was answered and fixed in tree within the hour** (their RM112): `hints.DERIVED_TABLE_MODELS`
and `hints.derived_model_for` are public in their checkout and retire both the map and the
cross-package roster — in the change that raises our compiler floor, because compiler 0.6.1 is what
we install and has neither symbol. Answered is not installable; the mitigation stays until it is.

**The `licensing.csv` carve-out is derived, not special-cased.** It is a fact sidecar that a human
writes, and it is in `draft.DRAFTABLE`; subtracting the draftable kinds removes it from the roster
and leaves it a table kind with a template and a linter. A table upstream makes hand-authorable
moves surface with no edit here. It is deliberately **not** listed under `sidecars` even though
`FACT_CSVS` names it: that field means *do not hand-finish this*, and licensing is the one you do.

**3. `studies.csv` was described in pre-RM47 terms.** Upstream's RM47 relaxed
`StudyRow.REQUIRED_ANY_OF` from `({rsid}, {chrom})` to `()`: a paper grounding a bin threshold, a
method or a population is a legal row with no variant identity at all, and `variant_key` may be
`None`. Our subject read "the evidence for a variant", which would have an author drop exactly the
row the relaxation was for. The subject now names the relaxation, `_COMPOSITION_NOTE` says a
binning module may carry `studies.csv` without `variants.csv`, and a test validates such a spec
strict-green rather than asserting the prose. `create-module/SKILL.md`'s studies section carries the
same pre-RM47 claim and was **not** edited here — a parallel session owns `skills/`, and it is
reported to them rather than changed underneath them.

**One upstream defect surfaced by the same probe**: `scaffold.COMPANION_KINDS` still pulls
`variants.csv` in behind `studies.csv` unconditionally, so a binning module doing the right thing is
told it owes an empty `variants.csv`. Passed through rather than patched — it is upstream's answer —
and filed as **`S49`**.

**The resource was fixed in the same change**, since it restated the same roster in prose and read
`_SUBJECTS` with a bare `.get`, so `sources.csv` rendered two em-dashes in the table an author reads
to choose a kind.

---

## RM11 — no route answered a machine-produced table's columns

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**The hole.** `describe_table` gates on `draft.DRAFTABLE`, which is authored kinds only, so
`resolution.csv` and the six fact tables answered *"Unknown table kind 'resolution.csv'"* — a
sentence that is false twice: the file is known, and it is in every enriched module. Meanwhile every
skill on this surface says *ask the tool, never memory*. The rule therefore had a hole exactly where
an author is looking at a produced file and deciding whether to touch it, and the only answer was
prose in a dossier, which is the thing that drifts.

**What shipped: `describe_machine_table`, essentials tier.** One name in, the live column list out —
type, category, description, vocabulary and pick-list — for `resolution.csv`, `frequencies.csv`,
`gene_metrics.csv`, `literature.csv`, `gene_validity.csv`, `clinical_assertions.csv` and
`gwas_effects.csv`. Essentials by the cost rule: one table named, pure model reflection, no network.
It carries `produced_by: SchemaVersions` like every other generated answer (RM13).

**The columns come from upstream's own assembly, not a second one of ours.**
`reference.authoring_reference()["models"][ModelName]` already describes every derived model in the
same shape `hints.describe_table` produces for an authored kind, so the tool projects that rather
than re-deriving type/category/vocabulary — the drift upstream's own D1-4 was. `vocabulary_notes` is
merged per column for parity, a no-op today because no produced model carries a noted vocabulary.

**A separate tool rather than a flag on `describe_table`, and this is the design decision.** The
brief asked for the do-not-author signal to be *structural rather than advisory*. Extending
`describe_table` would have had to answer three fields whose entire subject is authoring —
`requirements` (what you must supply), `redundancy_bearing` and `attestation_bearing` (which cells
you must reason out independently) — with empty values, and an empty `requirements` reads as *no
requirements* rather than as *the question does not apply*. Worse, `redundancy_bearing` is a global
map narrowed to a table's columns, so a produced table carrying `chrom` would have been told to
hand-author it, which is the opposite of true.

So the separation is the signal, in four places at once: a produced table has no template, no
linter and no requirements answer; its answer model carries `hand_authored: Literal[False]` where
`TableDescription` now carries `Literal[True]`, so the distinction is in the *schema* an agent reads
before calling; and the four authoring routes (`describe_table`, `table_requirements`,
`get_template`, `lint_rows`, plus `scaffold_module`) redirect by name instead of calling the file
unknown. `refusal` states what a hand-written cell costs: the passes merge rather than overwrite, so
it survives every later run wearing the source's authority, and no check asks where a value came
from.

**`licensing.csv` gets none of that treatment, and the exemption is derived.** It is refused by
`describe_machine_table` — under both spellings — with a pointer back to `describe_table`, because
it is a fact sidecar that a human writes. The rule is `in the produced roster AND in
draft.DRAFTABLE`, computed, so nothing has to remember it.

**Deliberately not built.** No write path, no template, no linter for these tables, and no
`table_requirements` equivalent: requiredness is a question about authoring. Nothing was added to
`hints`-style refusal wording upstream either — the redirect is ours, in `_shared.known_kind`, which
every authoring route already funnels through.

**The dossiers in `skills/` now claim the opposite in about eight places** (each fact table's
reference says `describe_table` refuses it and quotes the old wording). A parallel session owns
`skills/`; the list was handed to them rather than edited here.

---

## RM13 — every generated schema answer names the toolchain that produced it

**Shipped:** 2026-08-20, in tree after 0.10.2 (no version bump in that change)

**Why it was high.** A stale plugin cache serves a stale toolchain silently, and every
skill on this surface tells an agent to *ask the tool, never memory*. Measured: the
cache at 0.7.0 was serving format 0.5.4, so `describe_table("activity_phenotype.csv")`
answered with 11 columns where the installed 0.6.1 has 14 — a wrong answer, delivered
with the same confidence as a right one, from the tool the rule points at. Nothing in
the payload distinguished the two, so the rule was unreliable in exactly the case it
exists for.

**What shipped.** `_shared.schema_versions()` — one source for the whole surface, read
from `importlib.metadata` — and a `produced_by: SchemaVersions` field carrying
`format_version` and `compiler_version` on `list_tables`, `describe_table`,
`table_requirements` and `get_template`. `authoring_reference` carries the same pair as
a `produced_by` key inside its JSON, in both the summary and the `schemas=True` form.
The `resource://just-dna/tables` resource ends with the same line in prose.

**The compiler is stamped beside the format, and that is not padding.** The table
roster, the requirement shapes, the templates and the redundancy/attestation maps all
come from `just_dna_compiler.draft` / `hints` / `scaffold` — the compiler's projection
of the format's models. Since 0.6 the two no longer move in lockstep, so a skew in
either package moves these answers and one version cannot describe them.

**Read once at import, and the cache is correctness rather than speed.** A running
process keeps the modules it already imported; re-reading package metadata per call
would report the *new* distribution the moment anything upgrades the environment under
a live stdio server, while the answers still came from the old imported code. Reading at
import makes the stamp describe the code that actually produced the answer, which is the
only thing worth stamping. The RM13 text said "at call time"; that would have made the
stamp lie in precisely the scenario it is for.

**`authoring_reference` keeps returning a JSON string.** Around thirty dossiers document
the access path `authoring_reference()["models"][...]`, so a wrapper model would have
broken every one of them to add a field. The stamp goes in as a top-level key of a
shallow copy — upstream's dict is not ours to mutate — and cannot collide in either
form: the summary form's keys are fixed, and the `schemas=True` form's are CamelCase
model names.

**`server.INSTRUCTIONS` was fixed in the same change**, because it hardcoded
`(format 0.5)` while the installed format was 0.6.1 — a literal version, which §2
forbids for this exact reason, and the candidate fix `F19` and `F26` both named as the
*stronger* one: instructions are in front of an agent before the first call, where a tool field has
to be asked for. It now names the live format and compiler from the same helper.

**What was deliberately left unstamped.** `lint_rows`, `validate_module` and
`compile_module` are verdicts about a directory at a moment, not schema knowledge an
agent carries forward, and a compile is already stamped upstream inside `manifest.json`
— the catalog's one module still reads `just-dna-compiler 0.5.1` off exactly that field.
`list_tables`' hardcoded `sidecars` literal and `_SUBJECTS` were left alone too: they are
**RM10**, still open, and a stamp on a restated fact would only date the restatement.

## RM8 — the registry client surface is wrapped

**Shipped:** 2026-08-12 in 0.8.0

Four releases of `RegistryClient` had gone unwrapped since we adopted 0.12.0 for the
test/prod split. The precondition was registry 0.13.0 on PyPI, so
`would_publish_module_level` could be *wrapped* rather than feature-detected; it landed
2026-08-11 and this followed.

**What shipped, and the shape it took.** Two gated pre-flights and two ungated reads:

- **`registry_validate`** — the server's own module-level gates, including the two a
  local `validate_module` cannot know: whether `module.name` matches the path, and
  whether identical authored data is already published under some other name.
- **`registry_check`** — the full dry run, `F11`'s other half. This is what turns
  "rehearse the publish" into "ask whether it would publish" **without spending a
  version number**, which on production is irreversible.
- **`registry_is_published`** — ungated and needs no upload: the content signature is
  computed locally, so an author can ask "is this data already out there, under any
  name" before they have a token.
- **`registry_health`** — reports the instance's own mode, so a rehearsal can be
  *confirmed* rather than assumed. `expect_mode` (shipped in 0.7.0) already refuses a
  mismatch; this is how you see it before it matters.

**One bullet turned out to be already done.** RM8 listed `content_signature`, but
`module_signature` has always called `just_dna_compiler.compiler.content_signature` —
the same function the client method wraps. Wrapping the client's would have been a
second path to one answer, so `registry_is_published` calls the compiler directly and
sends only the resulting signature.

**One bullet is deliberately not done.** `issue_jwt_token` returns 501 unless the
deployment configures a signing secret, and nothing in this surface consumes a JWT —
every call authenticates with the registry token. A tool that is usually a 501 and
useful to nobody here is worse than no tool.

**Where the design work actually was: not letting a skip look like a verdict.** Both
pre-flights return one `PublishPreflight`, and it carries *two* verdicts on purpose:

- `module_level_clear` is upstream's `would_publish_module_level`, renamed so nothing
  reads it as a green light — it composes exactly three gates and excludes the network
  tier entirely.
- `verdict` is the whole dry run, and it is **`None` whenever the tier did not run** —
  on a bare validate, on `skipped_reason`, and when no token was resolvable. Defaulting
  it to `False` would let "we could not ask" arrive shaped like "would not publish",
  which is the same error as a skip producing a pass, one sign flipped.

`rerun_rather_than_fix` carries the `S20` distinction all the way to the author's next
action: a false verdict beside unreachable rsIDs means *re-run*, not *go fix your
spec*, because a strict publish against an unreachable Ensembl really does refuse while
the variants may be perfectly findable. Telling an author to fix that is how real rows
get deleted.

`unchecked` and `non_blocking` keep the distinctions upstream is careful about — a
`clin_sig` check the operator has no snapshot for never blocks and is never dropped
either, and identifier findings never move the verdict because a publish does not run
that pass, so a finding predicts nothing about one.

**Verified live against the polygon**, not just in the suite: a clean `assets/fto_bmi`
returned `verdict: true` in 1.3s, and the same spec with one invalid `state` returned
`verdict: null` with `verdict_unavailable: "invalid_spec"` — null rather than false,
which is the whole point.

## The essentials tier was defined by the wrong axis

**Shipped:** 2026-08-11 in 0.4.0 · *"If you find essentials surface lacking
before I even started, maybe reconsider the essential stack?"*

Never a numbered roadmap item — it arrived as a dogfooding observation (the
default tier could not verify a trait CURIE) and was widened into a rule change
because the survey found the observation was a symptom.

The old rule, *essentials = everything that only reads, plus the ClinVar draft*,
was false in both directions: `scaffold_module` and `compile_module` write and
were always in it, and six read-only tools were not. The decisive case was
`enrich_module` — extended-only while being step 6 of the workflow the server's
own `INSTRUCTIONS` teach. **A tier that teaches a step it cannot run is the
failure mode**, and it is now asserted rather than remembered: a test parses the
tool names out of that instruction text and requires all of them in essentials.

The replacement axis is **cost**: essentials is everything bounded by what the
caller named (one identifier, one paper, one spec directory); extended is what a
corpus sizes, plus reading back somebody else's artifact. Nine tools moved in,
none moved out.

**The scope decision was the user's**, and it went wider than the recommendation.
The proposal was the three tools that closed the gap; the answer was "6 +
fulltexts + lookup_openaccess + enrich which can be useful for common snip
modules" — reading the tier from the perspective of the module people actually
write first, which is what surfaced `enrich_module` as the real defect.

## RM3 — signing is unwrapped

**Deferred:** 2026-08-11 · *"signing thing is a prototype rather than a real
thing. Currently the registry is the authority and gives out identity keys."*

`keygen` / `sign` stay CLI-only, and not for the key-hygiene reason this item
originally gave. The reason is that **module identity is the registry's**: it
stamps `namespace`, `owner`, `version` and `canonical_id` on publish and
overrides anything authored (upstream `S1` documents this). Ed25519 signing sits
beside that as a prototype of a second, author-held identity scheme, and wrapping
a prototype would give it a durability its design has not earned.

`keygen` writing an unencrypted PKCS#8 key remains true and remains a reason not
to have an agent generate one on its own initiative, but it is now the second
argument rather than the first.

**What came out of this instead**, because it is the half that mattered: the
registry hands back the authoritative identity on publish and `registry_publish`
was returning it in a message and dropping it. It now writes a `published.json`
receipt beside the spec — the identity keys, the digest, the content signature and
an ISO-8601 UTC timestamp — because a receipt that does not survive the session is
not a record, and it cannot live in `module_spec.yaml` where `extra="forbid"`
rejects those exact keys.

**Reopens if** author-held signing stops being a prototype.

## RM4 — nothing verifies `enrich_module` or `registry_publish` end to end

**Reclassified:** 2026-08-11 · *"RM4 is a dogfooding run."*

Correct, and it was mis-filed. This was never a thing to build — it is a probe to
run, and a probe belongs in [dogfooding.md](dogfooding.md) under "Probes not yet
run", where it now is. Keeping it on the roadmap implied a deliverable and made
the roadmap look longer than the work.

The substance is unchanged: the offline ceiling keeps the suite hermetic, so
neither tool can be a normal test. What fits is a marked, opt-in integration run
plus authoring a small real module all the way through.

---

## RM1 — the drafting path is unwrapped, so the authoring loop has a hole in the middle

**Shipped:** 2026-08-11 · `draft_from_clinvar` (essentials), `draft_from_cpic` and
`draft_from_clinpgx` (extended), in `tools/passes.py`.

The skill taught `scaffold -> draft -> curate -> ...` and `draft` was CLI-only, so
an agent left the tool surface at step 2 and came back at step 4.

**Its stated difficulty was stale and is worth recording as such.** RM1 said
wrapping was hard because `draft` "refuses and lists the choices when a
`(phenotype, drug)` pair spans several populations". Upstream removed that in
0.5.1: `DiplotypeRow.clinical_context` keeps the settings as distinct rows and
the consumer picks at query time, so `population` is now a plain filter. Our own
`SKILL.md` and `DOMAIN.md` still claimed the old behaviour and were corrected in
the same change.

What *did* constrain the design was licensing, and that part held: `use` is
required with no default on all three tools, enforced at the schema layer, and a
licence refusal comes back as `skipped=true` with its reason rather than as a
failure — because a failure invites retrying with a different `use`, which is
fabricating a licence position to get data.

Three tools rather than one with a `source` argument: the upstream signatures
share almost nothing, and a merged tool would carry twelve arguments most of
which are inapplicable per source. `lookup_identifier(kind=...)` merges because
both kinds take the same pair; these do not.

## RM2 — the fact passes are unwrapped

**Shipped:** 2026-08-11 · `enrich_facts` (frequencies, gene_metrics, dosage) and
`enrich_literature_pass`, both extended and both background tasks.

One tool for the three sidecar passes because they share a shape — spec in,
sidecar out — and `dosage` writes onto `gene_metrics.csv` rather than a file of
its own. `use` applies only to `dosage`, so the result names where it landed in
`declared_use_applied_to` rather than letting the argument look universally
meaningful. That remains the softest seam in the design.

`enrich_literature_pass` stayed separate: it is keyed on `studies.csv` rather
than on variants, and its answer is a coverage sentence rather than a row count.

## RM5 — `lint_rows` promises refusals it does not currently produce

**Shipped:** 2026-08-11 · docstring and field description narrowed.

Resolved by narrowing the promise rather than by synthesizing alterations
upstream never made: `to_alterations` exists to carry upstream's distinctions
field-for-field, not to fabricate them. The docstring now says where the
redundancy-bearing columns actually appear on this tool — as `info` findings —
and that refusals come from the lookup tools.

Recorded as **F2**, now in [previous_issues.md](previous_issues.md).
